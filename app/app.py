from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
import os
import random
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import psycopg2
# Prometheus imports moved to runtime to avoid import-time failures

# Global metrics to avoid duplication
_request_count = None
_request_latency = None

def get_prometheus_metrics():
    """Get prometheus metrics at runtime to avoid import-time failures"""
    global _request_count, _request_latency
    if _request_count is None:
        try:
            from prometheus_client import Counter, Histogram
            _request_count = Counter('request_count', 'App Request Count', ['method', 'endpoint', 'http_status'])
            _request_latency = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'])
        except ImportError:
            # Return dummy objects if prometheus is not available
            class DummyMetric:
                def labels(self, **kwargs):
                    return self
                def inc(self):
                    pass
                def observe(self, value):
                    pass
            _request_count = DummyMetric()
            _request_latency = DummyMetric()
    return _request_count, _request_latency

def seed_database():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set, skipping seeding")
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
    # Insert random data into test_data
    for _ in range(10):  # Insert 10 random rows
        name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=10))
        value = random.randint(1, 1000)
        cursor.execute("INSERT INTO test_data (name, value) VALUES (%s, %s)", (name, value))
    conn.commit()
    cursor.close()
    conn.close()
    print("Database seeded with test data and backups table")

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_database()
    yield

app = FastAPI(lifespan=lifespan)

# Mount metrics endpoint at runtime to avoid import-time failures
try:
    from prometheus_client import make_asgi_app
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
except ImportError:
    pass  # Prometheus not available, skip metrics

@app.get("/")
async def root():
    REQUEST_COUNT, _ = get_prometheus_metrics()
    REQUEST_COUNT.labels(method='GET', endpoint='/', http_status=200).inc()
    return {"message": "DB Guardian API"}

@app.get("/health")
async def health():
    REQUEST_COUNT, _ = get_prometheus_metrics()
    REQUEST_COUNT.labels(method='GET', endpoint='/health', http_status=200).inc()
    return {"status": "healthy"}

# Pydantic models
class BackupRequest(BaseModel):
    database_name: Optional[str] = Field(default="default", description="Name of the database to backup")

class BackupResponse(BaseModel):
    task_id: str
    status: str
    message: str

class BackupInfo(BaseModel):
    id: int
    database_name: str
    backup_name: str
    storage_type: str
    storage_location: str
    created_at: Optional[str]
    size_bytes: Optional[int]
    status: str

class BackupListResponse(BaseModel):
    backups: List[BackupInfo]

# Security dependency
def verify_api_key(api_key: str = Depends(lambda: os.getenv('API_KEY', 'default-key'))):
    """Basic API key authentication - replace with proper auth later"""
    expected_key = os.getenv('API_KEY', 'default-key')
    if api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

# Backup endpoints
@app.post("/api/backups", response_model=BackupResponse)
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
        from .tasks import backup_database_task
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

@app.get("/api/backups/{task_id}")
async def get_backup_status(task_id: str, api_key: str = Depends(verify_api_key)):
    """Get the status of a backup task"""
    try:
        from celery.result import AsyncResult
        from .celery_app import celery
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

@app.get("/api/backups", response_model=BackupListResponse)
async def list_backups_endpoint(
    database_name: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """List all backups or backups for a specific database"""
    try:
        from .tasks import list_backups
        backups = list_backups(database_name)

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/backups', http_status=200).inc()

        return BackupListResponse(backups=backups)

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/backups', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

# Add more endpoints as needed for backup and retrieval

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
