import os
import subprocess
import tempfile
import shutil
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
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
    """Get encryption key from environment - supports both direct key and password-based generation"""
    # First, try to get a direct Fernet key (backward compatibility)
    key = os.getenv('BACKUP_ENCRYPTION_KEY')
    if key:
        return key.encode()

    # If no direct key, try to generate from password/seed
    password = os.getenv('BACKUP_ENCRYPTION_PASSWORD')
    if not password:
        raise BackupError("Either BACKUP_ENCRYPTION_KEY or BACKUP_ENCRYPTION_PASSWORD environment variable must be set")

    # Generate a deterministic Fernet key from the password using PBKDF2
    salt = b'dbguardian_backup_salt'  # Fixed salt for deterministic key generation
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key_bytes = kdf.derive(password.encode())

    # Convert to base64-encoded Fernet key format
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return fernet_key

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
def backup_database_task(self, schedule_id: int):
    """Celery task to backup database"""
    try:
        # First, check if the schedule is still enabled
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise BackupError("DATABASE_URL not set")

        # Check if schedule exists and is enabled
        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/')
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT database_name, enabled FROM backup_schedules
            WHERE id = %s
        """, (schedule_id,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result or not result[1]:  # Not found or not enabled
            logger.info(f"Schedule {schedule_id} is disabled or deleted, skipping backup")
            self.update_state(state='SUCCESS', meta={'message': 'Schedule disabled, backup skipped'})
            return {'status': 'skipped', 'reason': 'schedule_disabled'}

        database_name = result[0]

        # Update task state
        self.update_state(state='PROGRESS', meta={'message': 'Starting backup'})

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

            # Step 2: Upload unencrypted backup directly
            self.update_state(state='PROGRESS', meta={'message': 'Uploading backup to storage'})
            object_name = f"{db_name}/{backup_name}"

            if upload_to_minio(backup_path, object_name):
                storage_location = f"s3://{object_name}"
                storage_type = "minio"
            else:
                # Fallback to local storage
                local_path = save_to_local(backup_path, backup_name)
                storage_location = local_path
                storage_type = "local"

            # Clean up temporary files
            os.remove(backup_path)

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

@get_celery().task
def list_backups(database_name: str = None):
    """List available backups from storage locations"""
    backups = []

    # Try to list from MinIO/S3 first
    try:
        client = Minio(
            os.getenv('MINIO_ENDPOINT', 'minio:9000'),
            access_key=os.getenv('MINIO_ACCESS_KEY'),
            secret_key=os.getenv('MINIO_SECRET_KEY'),
            secure=False
        )
        bucket_name = os.getenv('MINIO_BUCKET_NAME', 'backups')

        prefix = f"{database_name}/" if database_name else ""
        objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)

        for obj in objects:
            if obj.object_name.endswith('.dump'):
                # Parse db_name/backup_name.dump (unencrypted)
                parts = obj.object_name.split('/')
                if len(parts) == 2:
                    db_name, backup_name = parts
                    if not database_name or db_name == database_name:
                        backups.append({
                            'id': hash(obj.object_name),  # Use hash as id
                            'database_name': db_name,
                            'backup_name': backup_name,
                            'storage_type': 'minio',
                            'storage_location': f"s3://{obj.object_name}",
                            'created_at': obj.last_modified.isoformat() if obj.last_modified else None,
                            'size_bytes': obj.size,
                            'status': 'completed'
                        })

    except Exception as e:
        logger.warning(f"Failed to list backups from MinIO: {str(e)}")

    # If MinIO failed or no backups found, try local storage
    if not backups:
        try:
            fallback_dir = os.getenv('FALLBACK_STORAGE_DIR', '/fallback')
            if os.path.exists(fallback_dir):
                for file in os.listdir(fallback_dir):
                    if file.endswith('.enc'):
                        # Parse backup_default_20231001_120000.dump.enc
                        backup_name = file[:-4]  # remove .enc
                        if backup_name.startswith('backup_'):
                            parts = backup_name.split('_')
                            if len(parts) >= 3:
                                db_name = parts[1]
                                if not database_name or db_name == database_name:
                                    file_path = os.path.join(fallback_dir, file)
                                    backups.append({
                                        'id': hash(file),  # Use hash as id
                                        'database_name': db_name,
                                        'backup_name': backup_name,
                                        'storage_type': 'local',
                                        'storage_location': file_path,
                                        'created_at': None,  # Can't easily get creation time
                                        'size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else None,
                                        'status': 'completed'
                                    })
        except Exception as e:
            logger.error(f"Failed to list backups from local storage: {str(e)}")

    # Sort by created_at if available, else by backup_name
    backups.sort(key=lambda x: (x['created_at'] or '9999-99-99', x['backup_name']), reverse=True)

    return backups
