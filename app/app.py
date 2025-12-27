from fastapi import FastAPI
from celery import Celery
import redis
import minio
import psycopg2
from prometheus_client import make_asgi_app, Counter, Histogram
import os

app = FastAPI()

# Prometheus metrics
REQUEST_COUNT = Counter('request_count', 'App Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'])

# Celery setup
celery = Celery(
    'tasks',
    broker=os.getenv('CELERY_BROKER_URL'),
    backend=os.getenv('CELERY_RESULT_BACKEND')
)

@app.get("/")
async def root():
    REQUEST_COUNT.labels(method='GET', endpoint='/', http_status=200).inc()
    return {"message": "DB Guardian API"}

@app.get("/health")
async def health():
    REQUEST_COUNT.labels(method='GET', endpoint='/health', http_status=200).inc()
    return {"status": "healthy"}

# Add more endpoints as needed for backup and retrieval

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
