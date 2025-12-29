from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from ..models.schemas import ScheduleRequest, ScheduleInfo, ScheduleListResponse
from ..database.connection import get_db_connection
from ..dependencies import verify_api_key, get_prometheus_metrics
from ..scheduler import refresh_scheduler

router = APIRouter()

@router.post("/schedules", response_model=ScheduleInfo)
async def create_schedule(request: ScheduleRequest, api_key: str = Depends(verify_api_key)):
    """Create a new backup schedule"""
    try:
        # Validate schedule parameters
        if request.schedule_type == "interval" and not request.interval_minutes:
            raise HTTPException(status_code=400, detail="interval_minutes is required for interval schedules")
        if request.schedule_type == "crontab" and not request.cron_expression:
            raise HTTPException(status_code=400, detail="cron_expression is required for crontab schedules")

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO backup_schedules
                (database_name, schedule_type, interval_minutes, cron_expression, enabled)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, database_name, schedule_type, interval_minutes, cron_expression, enabled, created_at, last_run, next_run
            """, (
                request.database_name,
                request.schedule_type,
                request.interval_minutes,
                request.cron_expression,
                request.enabled
            ))

            result = cursor.fetchone()
            conn.commit()

        schedule = ScheduleInfo(
            id=result[0],
            database_name=result[1],
            schedule_type=result[2],
            interval_minutes=result[3],
            cron_expression=result[4],
            enabled=result[5],
            created_at=str(result[6]),
            last_run=str(result[7]) if result[7] else None,
            next_run=str(result[8]) if result[8] else None
        )

        # Refresh scheduler configuration after creating a schedule
        try:
            refresh_scheduler()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Warning: Failed to refresh scheduler: {e}")

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint='/api/schedules', http_status=201).inc()

        return schedule

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint='/api/schedules', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")

@router.get("/schedules", response_model=ScheduleListResponse)
async def list_schedules(
    database_name: Optional[str] = None,
    enabled_only: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """List all backup schedules"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, database_name, schedule_type, interval_minutes, cron_expression, enabled, created_at, last_run, next_run
                FROM backup_schedules
            """
            params = []

            conditions = []
            if database_name:
                conditions.append("database_name = %s")
                params.append(database_name)
            if enabled_only:
                conditions.append("enabled = true")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC"

            cursor.execute(query, params)

            schedules = []
            for row in cursor.fetchall():
                schedules.append(ScheduleInfo(
                    id=row[0],
                    database_name=row[1],
                    schedule_type=row[2],
                    interval_minutes=row[3],
                    cron_expression=row[4],
                    enabled=row[5],
                    created_at=str(row[6]),
                    last_run=str(row[7]) if row[7] else None,
                    next_run=str(row[8]) if row[8] else None
                ))

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/schedules', http_status=200).inc()

        return ScheduleListResponse(schedules=schedules)

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/schedules', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}")

@router.get("/schedules/{schedule_id}", response_model=ScheduleInfo)
async def get_schedule(schedule_id: int, api_key: str = Depends(verify_api_key)):
    """Get a specific backup schedule"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, database_name, schedule_type, interval_minutes, cron_expression, enabled, created_at, last_run, next_run
                FROM backup_schedules
                WHERE id = %s
            """, (schedule_id,))

            result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Schedule not found")

        schedule = ScheduleInfo(
            id=result[0],
            database_name=result[1],
            schedule_type=result[2],
            interval_minutes=result[3],
            cron_expression=result[4],
            enabled=result[5],
            created_at=str(result[6]),
            last_run=str(result[7]) if result[7] else None,
            next_run=str(result[8]) if result[8] else None
        )

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint=f'/api/schedules/{schedule_id}', http_status=200).inc()

        return schedule

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint=f'/api/schedules/{schedule_id}', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")

@router.put("/schedules/{schedule_id}", response_model=ScheduleInfo)
async def update_schedule(
    schedule_id: int,
    request: ScheduleRequest,
    api_key: str = Depends(verify_api_key)
):
    """Update a backup schedule"""
    try:
        # Validate schedule parameters
        if request.schedule_type == "interval" and not request.interval_minutes:
            raise HTTPException(status_code=400, detail="interval_minutes is required for interval schedules")
        if request.schedule_type == "crontab" and not request.cron_expression:
            raise HTTPException(status_code=400, detail="cron_expression is required for crontab schedules")

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE backup_schedules
                SET database_name = %s, schedule_type = %s, interval_minutes = %s, cron_expression = %s, enabled = %s
                WHERE id = %s
                RETURNING id, database_name, schedule_type, interval_minutes, cron_expression, enabled, created_at, last_run, next_run
            """, (
                request.database_name,
                request.schedule_type,
                request.interval_minutes,
                request.cron_expression,
                request.enabled,
                schedule_id
            ))

            result = cursor.fetchone()
            conn.commit()

        if not result:
            raise HTTPException(status_code=404, detail="Schedule not found")

        schedule = ScheduleInfo(
            id=result[0],
            database_name=result[1],
            schedule_type=result[2],
            interval_minutes=result[3],
            cron_expression=result[4],
            enabled=result[5],
            created_at=str(result[6]),
            last_run=str(result[7]) if result[7] else None,
            next_run=str(result[8]) if result[8] else None
        )

        # Refresh scheduler configuration after updating a schedule
        try:
            refresh_scheduler()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Warning: Failed to refresh scheduler: {e}")

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='PUT', endpoint=f'/api/schedules/{schedule_id}', http_status=200).inc()

        return schedule

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='PUT', endpoint=f'/api/schedules/{schedule_id}', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int, api_key: str = Depends(verify_api_key)):
    """Delete a backup schedule"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if schedule exists
            cursor.execute("SELECT id, database_name FROM backup_schedules WHERE id = %s", (schedule_id,))
            schedule = cursor.fetchone()

            if not schedule:
                raise HTTPException(status_code=404, detail="Schedule not found")

            # Delete the schedule
            cursor.execute("DELETE FROM backup_schedules WHERE id = %s", (schedule_id,))
            conn.commit()

        # Refresh scheduler configuration after deleting a schedule
        try:
            refresh_scheduler()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Warning: Failed to refresh scheduler: {e}")

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='DELETE', endpoint=f'/api/schedules/{schedule_id}', http_status=200).inc()

        return {"message": f"Schedule {schedule_id} deleted", "database_name": schedule[1]}

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='DELETE', endpoint=f'/api/schedules/{schedule_id}', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")

@router.post("/schedules/{schedule_id}/trigger")
async def trigger_schedule(schedule_id: int, api_key: str = Depends(verify_api_key)):
    """Manually trigger a backup schedule"""
    try:
        from ..scheduler import trigger_backup_for_schedule

        task_id = trigger_backup_for_schedule(schedule_id)

        if task_id:
            REQUEST_COUNT, _ = get_prometheus_metrics()
            REQUEST_COUNT.labels(method='POST', endpoint=f'/api/schedules/{schedule_id}/trigger', http_status=200).inc()

            return {"message": f"Schedule {schedule_id} triggered", "task_id": task_id}
        else:
            raise HTTPException(status_code=404, detail="Schedule not found or not enabled")

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint=f'/api/schedules/{schedule_id}/trigger', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to trigger schedule: {str(e)}")

@router.post("/schedules/refresh")
async def refresh_schedules(api_key: str = Depends(verify_api_key)):
    """Refresh the Celery Beat scheduler with current database schedules"""
    try:
        success = refresh_scheduler()

        if success:
            message = "Scheduler refreshed successfully"
            status_code = 200
        else:
            message = "Scheduler refresh failed"
            status_code = 500

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint='/api/schedules/refresh', http_status=status_code).inc()

        return {"message": message, "success": success}

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='POST', endpoint='/api/schedules/refresh', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to refresh scheduler: {str(e)}")
