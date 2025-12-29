from fastapi import APIRouter, HTTPException, Depends
import os
import logging
from ..models.schemas import SystemStatus, ConfigInfo
from ..database.connection import get_db_connection
from ..dependencies import verify_api_key, get_prometheus_metrics
from ..scheduler import refresh_scheduler

router = APIRouter()

@router.get("/system/status", response_model=SystemStatus)
async def get_system_status(api_key: str = Depends(verify_api_key)):
    """Get overall system status"""
    try:
        # Check database connectivity
        db_status = "healthy"
        try:
            with get_db_connection() as conn:
                pass  # Connection test
        except Exception:
            db_status = "unhealthy"

        # Check Celery connectivity (simplified)
        celery_status = "unknown"  # Would need more complex checking

        # Check storage connectivity
        storage_status = "unknown"
        try:
            from minio import Minio
            client = Minio(
                os.getenv('MINIO_ENDPOINT', 'minio:9000'),
                access_key=os.getenv('MINIO_ACCESS_KEY'),
                secret_key=os.getenv('MINIO_SECRET_KEY'),
                secure=False
            )
            client.list_buckets()
            storage_status = "healthy"
        except Exception:
            storage_status = "unhealthy"

        status = SystemStatus(
            database=db_status,
            celery=celery_status,
            storage=storage_status,
            overall="healthy" if all(s in ["healthy", "unknown"] for s in [db_status, celery_status, storage_status]) else "degraded"
        )

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/system/status', http_status=200).inc()

        return status

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/system/status', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.get("/config", response_model=ConfigInfo)
async def get_config(api_key: str = Depends(verify_api_key)):
    """Get current configuration (sanitized)"""
    config = ConfigInfo(
        database_configured=bool(os.getenv('DATABASE_URL')),
        minio_configured=bool(os.getenv('MINIO_ENDPOINT') and os.getenv('MINIO_ACCESS_KEY')),
        encryption_enabled=bool(os.getenv('BACKUP_ENCRYPTION_KEY') or os.getenv('BACKUP_ENCRYPTION_PASSWORD')),
        prometheus_enabled=True,  # Since we have the import check
        celery_enabled=True  # Assuming it's configured
    )

    REQUEST_COUNT, _ = get_prometheus_metrics()
    REQUEST_COUNT.labels(method='GET', endpoint='/api/config', http_status=200).inc()

    return config

@router.post("/system/scheduler/reset")
async def reset_scheduler(api_key: str = Depends(verify_api_key)):
    """Reset the Celery Beat scheduler state"""
    try:
        logger = logging.getLogger(__name__)
        logger.info("Manually resetting scheduler state...")

        # Attempt to refresh the scheduler
        success = refresh_scheduler()

        if success:
            message = "Scheduler reset successfully"
            status_code = 200
        else:
            message = "Scheduler reset failed, but continuing with degraded mode"
            status_code = 207  # Partial success

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint='/api/system/scheduler/reset', http_status=status_code).inc()

        return {"message": message, "success": success}

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint='/api/system/scheduler/reset', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to reset scheduler: {str(e)}")
