import os
import subprocess
import tempfile
import shutil
from datetime import datetime
from cryptography.fernet import Fernet
from minio import Minio
from minio.error import S3Error
import psycopg2
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# Celery import moved to functions to avoid circular import

class BackupError(Exception):
    pass

def get_encryption_key():
    """Get encryption key from environment"""
    key = os.getenv('BACKUP_ENCRYPTION_KEY')
    if not key:
        raise BackupError("BACKUP_ENCRYPTION_KEY environment variable not set")
    return key.encode()

def encrypt_file(file_path: str, key: bytes) -> str:
    """Encrypt a file using Fernet symmetric encryption"""
    fernet = Fernet(key)

    with open(file_path, 'rb') as file:
        data = file.read()

    encrypted_data = fernet.encrypt(data)

    encrypted_path = file_path + '.enc'
    with open(encrypted_path, 'wb') as file:
        file.write(encrypted_data)

    return encrypted_path

def decrypt_file(encrypted_path: str, key: bytes) -> str:
    """Decrypt a file using Fernet symmetric encryption"""
    fernet = Fernet(key)

    with open(encrypted_path, 'rb') as file:
        encrypted_data = file.read()

    decrypted_data = fernet.decrypt(encrypted_data)

    decrypted_path = encrypted_path.replace('.enc', '')
    with open(decrypted_path, 'wb') as file:
        file.write(decrypted_data)

    return decrypted_path

def upload_to_minio(file_path: str, object_name: str) -> bool:
    """Upload file to MinIO/S3"""
    try:
        client = Minio(
            os.getenv('MINIO_ENDPOINT', 'minio:9000'),
            access_key=os.getenv('MINIO_ACCESS_KEY'),
            secret_key=os.getenv('MINIO_SECRET_KEY'),
            secure=False
        )

        bucket_name = os.getenv('MINIO_BUCKET_NAME', 'backups')

        # Create bucket if it doesn't exist
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        # Upload the file
        client.fput_object(bucket_name, object_name, file_path)
        logger.info(f"Successfully uploaded {object_name} to MinIO")
        return True

    except S3Error as e:
        logger.error(f"MinIO upload failed: {e}")
        return False

def save_to_local(file_path: str, backup_name: str) -> str:
    """Save file to local fallback storage"""
    fallback_dir = os.getenv('FALLBACK_STORAGE_DIR', '/fallback')
    os.makedirs(fallback_dir, exist_ok=True)

    local_path = os.path.join(fallback_dir, backup_name)
    shutil.copy2(file_path, local_path)
    logger.info(f"Saved backup to local storage: {local_path}")
    return local_path

def create_database_backup(database_url: str, backup_name: str) -> str:
    """Create PostgreSQL database backup using pg_dump"""
    parsed = urlparse(database_url)

    # Build pg_dump command
    cmd = [
        'pg_dump',
        '-h', parsed.hostname,
        '-p', str(parsed.port),
        '-U', parsed.username,
        '-d', parsed.path.lstrip('/'),
        '-f', backup_name,
        '--no-password',
        '--format=custom',  # Use custom format for better compression
        '--compress=9',     # Maximum compression
        '--verbose'
    ]

    # Set password environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = parsed.password

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Database backup created: {backup_name}")
        return backup_name

    except subprocess.CalledProcessError as e:
        logger.error(f"pg_dump failed: {e.stderr}")
        raise BackupError(f"Database backup failed: {e.stderr}")

def get_celery():
    try:
        from .celery_app import celery
    except ImportError:
        from celery_app import celery
    return celery

@get_celery().task(bind=True)
def backup_database_task(self, database_name: str = None):
    """Celery task to backup database"""
    try:
        # Update task state
        self.update_state(state='PROGRESS', meta={'message': 'Starting backup'})

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise BackupError("DATABASE_URL not set")

        # Generate backup name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_name = database_name or 'default'
        backup_name = f"backup_{db_name}_{timestamp}.dump"

        # Create temporary directory for backup
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = os.path.join(temp_dir, backup_name)

            # Step 1: Create database backup
            self.update_state(state='PROGRESS', meta={'message': 'Creating database dump'})
            create_database_backup(database_url, backup_path)

            # Step 2: Encrypt the backup
            self.update_state(state='PROGRESS', meta={'message': 'Encrypting backup'})
            key = get_encryption_key()
            encrypted_path = encrypt_file(backup_path, key)

            # Step 3: Try to upload to MinIO/S3
            self.update_state(state='PROGRESS', meta={'message': 'Uploading to storage'})
            object_name = f"{db_name}/{backup_name}.enc"

            if upload_to_minio(encrypted_path, object_name):
                storage_location = f"s3://{object_name}"
                storage_type = "minio"
            else:
                # Fallback to local storage
                local_path = save_to_local(encrypted_path, f"{backup_name}.enc")
                storage_location = local_path
                storage_type = "local"

            # Clean up temporary files
            os.remove(backup_path)
            os.remove(encrypted_path)

        # Record backup metadata in database
        record_backup_metadata(db_name, backup_name, storage_type, storage_location)

        self.update_state(state='SUCCESS', meta={
            'message': 'Backup completed successfully',
            'storage_type': storage_type,
            'storage_location': storage_location
        })

        return {
            'status': 'success',
            'backup_name': backup_name,
            'storage_type': storage_type,
            'storage_location': storage_location
        }

    except Exception as e:
        logger.error(f"Backup task failed: {str(e)}")
        self.update_state(state='FAILURE', meta={'message': str(e)})
        raise

def record_backup_metadata(database_name: str, backup_name: str, storage_type: str, storage_location: str):
    """Record backup metadata in database"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return

        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/')
        )
        cursor = conn.cursor()

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

        # Insert backup record
        cursor.execute("""
            INSERT INTO backups (database_name, backup_name, storage_type, storage_location)
            VALUES (%s, %s, %s, %s)
        """, (database_name, backup_name, storage_type, storage_location))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to record backup metadata: {str(e)}")

@celery.task
def list_backups(database_name: str = None):
    """List available backups"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return []

        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/')
        )
        cursor = conn.cursor()

        if database_name:
            cursor.execute("""
                SELECT id, database_name, backup_name, storage_type, storage_location, created_at, size_bytes, status
                FROM backups
                WHERE database_name = %s
                ORDER BY created_at DESC
            """, (database_name,))
        else:
            cursor.execute("""
                SELECT id, database_name, backup_name, storage_type, storage_location, created_at, size_bytes, status
                FROM backups
                ORDER BY created_at DESC
            """)

        backups = []
        for row in cursor.fetchall():
            backups.append({
                'id': row[0],
                'database_name': row[1],
                'backup_name': row[2],
                'storage_type': row[3],
                'storage_location': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'size_bytes': row[6],
                'status': row[7]
            })

        cursor.close()
        conn.close()

        return backups

    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        return []
