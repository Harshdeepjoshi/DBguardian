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

@router.delete("/backups/{backup_id}")
async def delete_backup(backup_id: int, api_key: str = Depends(verify_api_key)):
    """Delete a backup (from database metadata only - actual file deletion would need additional logic)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if backup exists
            cursor.execute("SELECT id, backup_name, storage_location FROM backups WHERE id = %s", (backup_id,))
            backup = cursor.fetchone()

            if not backup:
                raise HTTPException(status_code=404, detail="Backup not found")

            # Delete from database (Note: actual file deletion from storage would need additional implementation)
            cursor.execute("DELETE FROM backups WHERE id = %s", (backup_id,))
            conn.commit()

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='DELETE', endpoint=f'/api/backups/{backup_id}', http_status=200).inc()

        return {"message": f"Backup {backup_id} deleted from metadata", "backup_name": backup[1]}

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='DELETE', endpoint=f'/api/backups/{backup_id}', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")
