from fastapi import FastAPI
from contextlib import asynccontextmanager
from .database.connection import init_database
from .routes import backups_router, schedules_router, database_router, system_router
from .dependencies import get_prometheus_metrics

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield

app = FastAPI(
    title="DB Guardian API",
    description="Database backup and monitoring system",
    version="1.0.0",
    lifespan=lifespan
)

# Mount metrics endpoint at runtime to avoid import-time failures
try:
    from prometheus_client import make_asgi_app
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
except ImportError:
    pass  # Prometheus not available, skip metrics

# Include routers
app.include_router(backups_router, prefix="/api", tags=["backups"])
app.include_router(schedules_router, prefix="/api", tags=["schedules"])
app.include_router(database_router, prefix="/api", tags=["database"])
app.include_router(system_router, prefix="/api", tags=["system"])

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
