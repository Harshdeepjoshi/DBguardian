from fastapi import FastAPI
from celery import Celery
import redis
import minio
import psycopg2
from prometheus_client import make_asgi_app, Counter, Histogram
import os
import random
from contextlib import asynccontextmanager
from urllib.parse import urlparse

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
    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_data (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            value INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Insert random data
    for _ in range(10):  # Insert 10 random rows
        name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=10))
        value = random.randint(1, 1000)
        cursor.execute("INSERT INTO test_data (name, value) VALUES (%s, %s)", (name, value))
    conn.commit()
    cursor.close()
    conn.close()
    print("Database seeded with test data")

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_database()
    yield

app = FastAPI(lifespan=lifespan)

# Prometheus metrics
REQUEST_COUNT = Counter('request_count', 'App Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'])

# Celery setup
celery = Celery(
    'tasks',
    broker=os.getenv('CELERY_BROKER_URL'),
    backend=os.getenv('CELERY_RESULT_BACKEND')
)

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

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
