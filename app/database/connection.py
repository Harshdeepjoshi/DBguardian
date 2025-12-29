import os
import psycopg2
from urllib.parse import urlparse
from contextlib import contextmanager

def get_database_config():
    """Get database configuration from environment"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        return None

    parsed = urlparse(database_url)
    return {
        'host': parsed.hostname,
        'port': parsed.port,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/')
    }

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    config = get_database_config()
    if not config:
        raise ValueError("Database not configured")

    conn = None
    try:
        conn = psycopg2.connect(**config)
        yield conn
    finally:
        if conn:
            conn.close()

def check_trigger_exists(cursor, trigger_name):
    """Check if a trigger exists in the database"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_trigger
            WHERE tgname = %s
        )
    """, (trigger_name,))
    return cursor.fetchone()[0]

def check_function_exists(cursor, function_name):
    """Check if a function exists in the database"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_proc
            WHERE proname = %s
        )
    """, (function_name,))
    return cursor.fetchone()[0]

def init_database_triggers(cursor):
    """Initialize database triggers for schedule change notifications"""
    try:
        # Check if the notify function exists
        if not check_function_exists(cursor, 'notify_schedule_change'):
            # Create the notification function
            cursor.execute("""
                CREATE OR REPLACE FUNCTION notify_schedule_change()
                RETURNS TRIGGER AS $$
                DECLARE
                    payload JSON;
                BEGIN
                    -- Build notification payload
                    IF TG_OP = 'INSERT' THEN
                        payload := json_build_object(
                            'action', 'inserted',
                            'schedule_id', NEW.id,
                            'database_name', NEW.database_name,
                            'enabled', NEW.enabled
                        );
                    ELSIF TG_OP = 'UPDATE' THEN
                        payload := json_build_object(
                            'action', 'updated',
                            'schedule_id', NEW.id,
                            'database_name', NEW.database_name,
                            'enabled', NEW.enabled,
                            'old_enabled', OLD.enabled
                        );
                    ELSIF TG_OP = 'DELETE' THEN
                        payload := json_build_object(
                            'action', 'deleted',
                            'schedule_id', OLD.id,
                            'database_name', OLD.database_name,
                            'enabled', OLD.enabled
                        );
                    END IF;

                    -- Send notification
                    PERFORM pg_notify('schedule_changes', payload::text);

                    -- Return appropriate value based on operation
                    IF TG_OP = 'DELETE' THEN
                        RETURN OLD;
                    ELSE
                        RETURN NEW;
                    END IF;
                END;
                $$ LANGUAGE plpgsql;
            """)
            print("Created notify_schedule_change function")

        # Check if the trigger exists
        if not check_trigger_exists(cursor, 'schedule_change_trigger'):
            # Create the trigger
            cursor.execute("""
                CREATE TRIGGER schedule_change_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON backup_schedules
                    FOR EACH ROW EXECUTE FUNCTION notify_schedule_change();
            """)
            print("Created schedule_change_trigger")

    except Exception as e:
        print(f"Warning: Failed to initialize database triggers: {str(e)}")
        # Don't fail the entire initialization if triggers fail

def init_database():
    """Initialize database tables and triggers with retry logic"""
    import time
    import logging

    logger = logging.getLogger(__name__)
    max_retries = 30  # Retry for up to 30 attempts
    retry_delay = 2   # 2 seconds between retries

    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Create test_data table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_data (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255),
                        value INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create backups table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS backups (
                        id SERIAL PRIMARY KEY,
                        database_name VARCHAR(255) NOT NULL,
                        backup_name VARCHAR(255) NOT NULL,
                        storage_type VARCHAR(50) NOT NULL,
                        storage_location TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        size_bytes BIGINT,
                        status VARCHAR(50) DEFAULT 'completed'
                    )
                """)

                # Create database_credentials table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS database_credentials (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        host VARCHAR(255) NOT NULL,
                        port INTEGER DEFAULT 5432,
                        database VARCHAR(255) NOT NULL,
                        username VARCHAR(255) NOT NULL,
                        password TEXT NOT NULL,
                        version VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create backup_schedules table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS backup_schedules (
                        id SERIAL PRIMARY KEY,
                        database_name VARCHAR(255) NOT NULL,
                        schedule_type VARCHAR(50) NOT NULL,
                        interval_minutes INTEGER,
                        cron_expression VARCHAR(255),
                        enabled BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_run TIMESTAMP,
                        next_run TIMESTAMP
                    )
                """)

                # Initialize database triggers
                init_database_triggers(cursor)

                # Insert random data into test_data (only if table is empty)
                cursor.execute("SELECT COUNT(*) FROM test_data")
                if cursor.fetchone()[0] == 0:
                    import random
                    for _ in range(10):  # Insert 10 random rows
                        name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=10))
                        value = random.randint(1, 1000)
                        cursor.execute("INSERT INTO test_data (name, value) VALUES (%s, %s)", (name, value))

                conn.commit()
                cursor.close()

            print("Database seeded with test data, tables, and triggers")
            return  # Success, exit the function

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database initialization failed (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Database initialization failed after {max_retries} attempts: {str(e)}")
                print(f"Warning: Database initialization failed: {str(e)}. The application will continue without database seeding.")
                return
