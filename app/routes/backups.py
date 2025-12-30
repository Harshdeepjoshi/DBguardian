from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional
from ..models.schemas import BackupRequest, BackupResponse, BackupInfo, BackupListResponse
from ..database.connection import get_db_connection
from ..dependencies import verify_api_key, get_prometheus_metrics

router = APIRouter()

@router.post("/backups", response_model=BackupResponse)
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Trigger a database backup"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Received backup request for database: {request.database_name}")
        # Import celery task at runtime to avoid import-time failures
        from ..tasks import backup_database_task
        logger.info("About to call backup_database_task.delay")
        # Start the backup task asynchronously
        task = backup_database_task.delay(request.database_name)
        logger.info(f"Backup task created with ID: {task.id}")

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint='/api/backups', http_status=202).inc()

        return BackupResponse(
            task_id=task.id,
            status="accepted",
            message="Backup task started"
        )

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start backup: {str(e)}", exc_info=True)
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint='/api/backups', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to start backup: {str(e)}")

@router.get("/backups/{task_id}")
async def get_backup_status(task_id: str, api_key: str = Depends(verify_api_key)):
    """Get the status of a backup task"""
    try:
        from celery.result import AsyncResult
        from ..celery_app import celery
        result = AsyncResult(task_id, app=celery)

        if result.state == "PENDING":
            response = {"task_id": task_id, "status": "pending", "message": "Task is pending"}
        elif result.state == "PROGRESS":
            response = {"task_id": task_id, "status": "progress", "message": result.info.get('message', '')}
        elif result.state == "SUCCESS":
            response = {"task_id": task_id, "status": "success", "result": result.result}
        else:
            response = {"task_id": task_id, "status": "failure", "error": str(result.info)}

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint=f'/api/backups/{task_id}', http_status=200).inc()
        return response

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint=f'/api/backups/{task_id}', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@router.get("/backups", response_model=BackupListResponse)
async def list_backups_endpoint(
    database_name: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """List all backups or backups for a specific database"""
    try:
        from ..tasks import list_backups
        backups = list_backups(database_name)

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/backups', http_status=200).inc()

        return BackupListResponse(backups=backups)

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/backups', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@router.delete("/backups/{filename:path}")
async def delete_backup(filename: str, api_key: str = Depends(verify_api_key)):
    """Delete a backup from storage using filename/object_name as identifier"""
    import logging
    logger = logging.getLogger(__name__)

    print(f"DELETE BACKUP REQUEST: filename='{filename}'")  # Debug print
    logger.info(f"DELETE BACKUP REQUEST: filename='{filename}'")

    try:
        deleted_from_storage = False
        backup_name = "unknown"

        # Try MinIO first - filename is the object_name (e.g., "database/backup_name.dump")
        logger.info(f"Attempting to delete from MinIO: filename='{filename}'")
        try:
            import os
            from minio import Minio
            minio_endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
            minio_access_key = os.getenv('MINIO_ACCESS_KEY')
            minio_secret_key = os.getenv('MINIO_SECRET_KEY')
            bucket_name = os.getenv('MINIO_BUCKET_NAME', 'backups')

            logger.info(f"MinIO config: endpoint='{minio_endpoint}', bucket='{bucket_name}', access_key present={bool(minio_access_key)}")

            client = Minio(
                minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
                secure=False
            )

            # Check if the object exists and delete it
            logger.info(f"Checking if object exists in MinIO: bucket='{bucket_name}', object='{filename}'")
            try:
                stat = client.stat_object(bucket_name, filename)
                logger.info(f"Object found in MinIO: size={stat.size}, last_modified={stat.last_modified}")

                logger.info(f"Deleting object from MinIO: bucket='{bucket_name}', object='{filename}'")
                client.remove_object(bucket_name, filename)
                deleted_from_storage = True
                backup_name = filename.split('/')[-1]  # Get backup name from path
                logger.info(f"Successfully deleted from MinIO: backup_name='{backup_name}'")
            except Exception as minio_error:
                logger.warning(f"Object not found in MinIO or delete failed: {str(minio_error)}")
                # Object doesn't exist in MinIO
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client or delete from MinIO: {str(e)}")

        # If not found in MinIO, try local storage - filename is the filename
        if not deleted_from_storage:
            logger.info(f"MinIO delete failed, trying local storage: filename='{filename}'")
            try:
                import os
                fallback_dir = os.getenv('FALLBACK_STORAGE_DIR', '/fallback')
                file_path = os.path.join(fallback_dir, filename)

                logger.info(f"Checking local file: path='{file_path}'")
                if os.path.exists(file_path):
                    logger.info(f"Local file exists, deleting: path='{file_path}'")
                    os.remove(file_path)
                    deleted_from_storage = True
                    backup_name = filename
                    logger.info(f"Successfully deleted local file: backup_name='{backup_name}'")
                else:
                    logger.warning(f"Local file does not exist: path='{file_path}'")
            except Exception as e:
                logger.error(f"Failed to delete local file: {str(e)}")

        # Also try to clean up any database records if they exist
        logger.info("Attempting to clean up database records")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Try to find and delete by storage_location
                bucket_name = os.getenv('MINIO_BUCKET_NAME', 'backups')
                s3_location = f"s3://{bucket_name}/{filename}"
                local_location = os.path.join(os.getenv('FALLBACK_STORAGE_DIR', '/fallback'), filename)

                logger.info(f"Searching for database records: s3_location='{s3_location}', local_location='{local_location}'")

                cursor.execute("SELECT COUNT(*) FROM backups WHERE storage_location = %s OR storage_location = %s",
                             (s3_location, local_location))
                count_before = cursor.fetchone()[0]
                logger.info(f"Found {count_before} matching database records")

                cursor.execute("DELETE FROM backups WHERE storage_location = %s OR storage_location = %s",
                             (s3_location, local_location))
                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"Deleted {deleted_count} database records")
        except Exception as e:
            logger.error(f"Failed to clean up database records: {str(e)}")

        if not deleted_from_storage:
            logger.error(f"BACKUP NOT FOUND: filename='{filename}' - not found in MinIO or local storage")
            raise HTTPException(status_code=404, detail="Backup not found")

        logger.info(f"DELETE BACKUP SUCCESS: filename='{filename}', backup_name='{backup_name}'")

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='DELETE', endpoint=f'/api/backups/{filename}', http_status=200).inc()

        return {"message": f"Backup {backup_name} deleted from storage", "backup_name": backup_name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE BACKUP ERROR: filename='{filename}', error='{str(e)}'", exc_info=True)
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='DELETE', endpoint=f'/api/backups/{filename}', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")
