from celery import Celery
import os
import logging
from .scheduler import setup_scheduler, refresh_scheduler

logger = logging.getLogger(__name__)

celery = Celery(
    'app',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={},  # Will be populated by setup_scheduler
    beat_scheduler='celery.beat.Scheduler',  # Use in-memory scheduler instead of persistent
    beat_max_loop_interval=30,  # Reduce max interval for faster recovery
    beat_schedule_filename=None,  # Disable persistent schedule file
)

# Import tasks to register them with Celery
from . import tasks

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic tasks after Celery configuration"""
    try:
        logger.info("Setting up periodic tasks...")
        setup_scheduler()

        # Start the database listener for real-time schedule changes
        from .scheduler import start_schedule_listener
        start_schedule_listener()

        logger.info("Periodic tasks and schedule listener set up successfully")
    except Exception as e:
        logger.error(f"Failed to set up periodic tasks: {e}")
        # Don't fail the entire startup, just log the error
        logger.warning("Continuing with empty schedule due to setup failure")
