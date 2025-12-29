from celery import Celery
from celery.schedules import crontab
import psycopg2
from urllib.parse import urlparse
import os
from datetime import datetime, timedelta
import logging
import threading
import time
import select
import json

logger = logging.getLogger(__name__)

def get_celery():
    try:
        from .celery_app import celery
    except ImportError:
        from celery_app import celery
    return celery

def get_db_connection():
    """Get database connection for scheduler"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL not set")

    parsed = urlparse(database_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip('/')
    )
    return conn

def get_active_schedules():
    """Fetch all enabled schedules from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, database_name, schedule_type, interval_minutes, cron_expression, enabled, last_run
            FROM backup_schedules
            WHERE enabled = true
        """)

        schedules = []
        for row in cursor.fetchall():
            schedules.append({
                'id': row[0],
                'database_name': row[1],
                'schedule_type': row[2],
                'interval_minutes': row[3],
                'cron_expression': row[4],
                'enabled': row[5],
                'last_run': row[6]
            })

        cursor.close()
        conn.close()
        return schedules

    except Exception as e:
        logger.error(f"Failed to fetch schedules: {str(e)}")
        return []

def update_schedule_run_time(schedule_id, last_run=None, next_run=None):
    """Update last_run and next_run times for a schedule"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if last_run:
            cursor.execute("""
                UPDATE backup_schedules
                SET last_run = %s
                WHERE id = %s
            """, (last_run, schedule_id))

        if next_run:
            cursor.execute("""
                UPDATE backup_schedules
                SET next_run = %s
                WHERE id = %s
            """, (next_run, schedule_id))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to update schedule run time: {str(e)}")

def parse_cron_expression(cron_expr):
    """Parse cron expression into Celery crontab format"""
    # Simple cron parser for basic expressions
    # Format: "MINUTE HOUR DAY MONTH DAYOFWEEK"
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}")

    minute, hour, day, month, day_of_week = parts

    # Convert * to None for Celery
    def convert_to_int_or_none(value):
        return int(value) if value != '*' else None

    return crontab(
        minute=convert_to_int_or_none(minute),
        hour=convert_to_int_or_none(hour),
        day_of_month=convert_to_int_or_none(day),
        month_of_year=convert_to_int_or_none(month),
        day_of_week=convert_to_int_or_none(day_of_week)
    )

def setup_scheduler():
    """Set up Celery Beat scheduler with database schedules"""
    celery = get_celery()

    # Clear existing schedules
    celery.conf.beat_schedule = {}

    schedules = get_active_schedules()

    for schedule in schedules:
        task_name = f"backup_schedule_{schedule['id']}"

        if schedule['schedule_type'] == 'interval':
            # Interval-based schedule
            interval_minutes = schedule['interval_minutes'] or 60
            celery.conf.beat_schedule[task_name] = {
                'task': 'app.tasks.backup_database_task',
                'schedule': timedelta(minutes=interval_minutes),
                'args': (schedule['id'],)
            }
            logger.info(f"Added interval schedule: {task_name} every {interval_minutes} minutes")

        elif schedule['schedule_type'] == 'crontab':
            # Cron-based schedule
            if schedule['cron_expression']:
                try:
                    cron_schedule = parse_cron_expression(schedule['cron_expression'])
                    celery.conf.beat_schedule[task_name] = {
                        'task': 'app.tasks.backup_database_task',
                        'schedule': cron_schedule,
                        'args': (schedule['id'],)
                    }
                    logger.info(f"Added cron schedule: {task_name} with expression '{schedule['cron_expression']}'")
                except ValueError as e:
                    logger.error(f"Invalid cron expression for schedule {schedule['id']}: {e}")
            else:
                logger.error(f"No cron expression for schedule {schedule['id']}")

    logger.info(f"Set up {len(celery.conf.beat_schedule)} scheduled tasks")

def refresh_scheduler():
    """Refresh the Celery Beat scheduler by reloading schedules from database"""
    try:
        # Clear existing schedules first
        celery = get_celery()
        old_schedule = celery.conf.beat_schedule.copy()
        celery.conf.beat_schedule = {}

        # Reload schedules from database
        schedules = get_active_schedules()

        for schedule in schedules:
            task_name = f"backup_schedule_{schedule['id']}"

            if schedule['schedule_type'] == 'interval':
                # Interval-based schedule
                interval_minutes = schedule['interval_minutes'] or 60
                celery.conf.beat_schedule[task_name] = {
                    'task': 'app.tasks.backup_database_task',
                    'schedule': timedelta(minutes=interval_minutes),
                    'args': (schedule['id'],)
                }
                logger.info(f"Refreshed interval schedule: {task_name} every {interval_minutes} minutes")

            elif schedule['schedule_type'] == 'crontab':
                # Cron-based schedule
                if schedule['cron_expression']:
                    try:
                        cron_schedule = parse_cron_expression(schedule['cron_expression'])
                        celery.conf.beat_schedule[task_name] = {
                            'task': 'app.tasks.backup_database_task',
                            'schedule': cron_schedule,
                            'args': (schedule['id'],)
                        }
                        logger.info(f"Refreshed cron schedule: {task_name} with expression '{schedule['cron_expression']}'")
                    except ValueError as e:
                        logger.error(f"Invalid cron expression for schedule {schedule['id']}: {e}")
                else:
                    logger.error(f"No cron expression for schedule {schedule['id']}")

        logger.info(f"Refreshed scheduler with {len(celery.conf.beat_schedule)} scheduled tasks")

        # Force scheduler reload by triggering configuration change
        try:
            # Check if schedule actually changed
            schedule_changed = False
            if len(old_schedule) != len(celery.conf.beat_schedule):
                schedule_changed = True
            else:
                for key in old_schedule:
                    if key not in celery.conf.beat_schedule or old_schedule[key] != celery.conf.beat_schedule[key]:
                        schedule_changed = True
                        break

            if schedule_changed:
                logger.info("Schedule configuration changed, forcing reload")

                # Force immediate sync by updating the configuration
                celery.conf.beat_schedule = dict(celery.conf.beat_schedule)

                # Try to notify the scheduler to reload immediately
                try:
                    from celery.apps.beat import Beat
                    # Access the running beat instance if available
                    if hasattr(Beat, '_running_beat') and Beat._running_beat:
                        beat_instance = Beat._running_beat
                        if hasattr(beat_instance, 'scheduler') and beat_instance.scheduler:
                            scheduler = beat_instance.scheduler
                            # Force scheduler to reload its schedule
                            if hasattr(scheduler, '_schedule'):
                                scheduler._schedule = None  # Clear cached schedule
                                if hasattr(scheduler, 'setup_schedule'):
                                    scheduler.setup_schedule()
                                    logger.info("Forced scheduler to reload schedule immediately")
                except Exception as beat_error:
                    logger.warning(f"Could not access running beat instance: {beat_error}")

            else:
                logger.info("Schedule configuration unchanged")

        except Exception as reload_error:
            logger.warning(f"Could not force scheduler reload: {reload_error}")

        return True
    except Exception as e:
        logger.error(f"Failed to refresh scheduler: {str(e)}")
        return False

def listen_for_schedule_changes():
    """Listen for PostgreSQL notifications when schedules are added or deleted"""
    logger.info("Starting database listener for schedule changes...")

    while True:
        try:
            conn = get_db_connection()
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

            cursor = conn.cursor()
            cursor.execute("LISTEN schedule_changes;")
            logger.info("Listening for schedule changes...")

            while True:
                if select.select([conn], [], [], 60) == ([], [], []):
                    # Timeout - check if connection is still alive
                    cursor.execute("SELECT 1;")
                    continue

                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    logger.info(f"Received notification: {notify.payload}")

                    try:
                        # Parse the notification payload
                        data = json.loads(notify.payload)
                        action = data.get('action')
                        schedule_id = data.get('schedule_id')

                        logger.info(f"Schedule {action}d: ID {schedule_id}")

                        # Refresh scheduler when schedule is added or deleted
                        refresh_scheduler()

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse notification payload: {e}")
                    except Exception as e:
                        logger.error(f"Failed to refresh scheduler on notification: {e}")

        except Exception as e:
            logger.error(f"Database listener error: {e}")
            time.sleep(5)  # Wait before reconnecting
        finally:
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass

# Global variable to store the listener thread
_listener_thread = None

def start_schedule_listener():
    """Start the database listener in a separate thread"""
    global _listener_thread
    if _listener_thread is None or not _listener_thread.is_alive():
        _listener_thread = threading.Thread(target=listen_for_schedule_changes, daemon=True)
        _listener_thread.start()
        logger.info("Schedule change listener started")

def stop_schedule_listener():
    """Stop the database listener thread"""
    global _listener_thread
    if _listener_thread and _listener_thread.is_alive():
        # Note: Daemon threads will be terminated when main process exits
        logger.info("Schedule change listener will be stopped with application")

def trigger_backup_for_schedule(schedule_id):
    """Manually trigger a backup for a specific schedule"""
    from .tasks import backup_database_task

    schedules = get_active_schedules()
    schedule = next((s for s in schedules if s['id'] == schedule_id), None)

    if not schedule:
        logger.error(f"Schedule {schedule_id} not found or not enabled")
        return None

    # Update last_run time
    now = datetime.now()
    update_schedule_run_time(schedule_id, last_run=now)

    # Trigger the backup task
    result = backup_database_task.delay(schedule_id)
    logger.info(f"Triggered backup for schedule {schedule_id}, task ID: {result.id}")

    return result.id

if __name__ == "__main__":
    # For testing scheduler setup
    setup_scheduler()
