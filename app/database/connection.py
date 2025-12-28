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

def init_database():
    """Initialize database tables with retry logic"""
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

            print("Database seeded with test data and tables")
            return  # Success, exit the function

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database initialization failed (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Database initialization failed after {max_retries} attempts: {str(e)}")
                print(f"Warning: Database initialization failed: {str(e)}. The application will continue without database seeding.")
                return
