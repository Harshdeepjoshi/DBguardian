# DB Guardian

A database backup and point-in-time retrieval application using FastAPI.

## Services

- **FastAPI**: Main application
- **PostgreSQL**: Database
- **MinIO**: S3-compatible storage
- **Redis**: Caching and message broker
- **Celery Worker**: Background task processing
- **Celery Beat**: Scheduled tasks
- **pgAdmin**: Database administration
- **Prometheus**: Monitoring
- **Grafana**: Dashboards

## Setup

1. Clone the repository
2. Copy `.env` and update the variables as needed
3. Run `docker-compose up --build`

## Environment Variables

See `.env` file for all configurable variables.

## Volumes

- `postgres_data`: PostgreSQL data
- `minio_data`: MinIO data
- `redis_data`: Redis data
- `fallback_volume`: Fallback storage when S3 fails
- `prometheus_data`: Prometheus data
- `grafana_data`: Grafana data

## Network

All services are connected via `dbguardian_network`.

