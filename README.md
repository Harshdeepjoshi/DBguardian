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

### Required for Backup Functionality
- `BACKUP_ENCRYPTION_KEY`: Base64-encoded key for encrypting backups (generate with `openssl rand -base64 32`)
- `MINIO_BUCKET_NAME`: Name of the MinIO bucket for storing backups (default: 'backups')

## MinIO Bucket Setup

The application automatically creates the MinIO bucket when the first backup is performed. However, if you want to create it manually:

1. Access MinIO Console at `http://localhost:9003` (or your configured port)
2. Login with your `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`
3. Click "Create Bucket" and enter the bucket name (default: 'backups')
4. The bucket will be created automatically during the first backup if it doesn't exist

## Volumes

- `postgres_data`: PostgreSQL data
- `minio_data`: MinIO data
- `redis_data`: Redis data
- `fallback_volume`: Fallback storage when S3 fails
- `prometheus_data`: Prometheus data
- `grafana_data`: Grafana data

## Network

All services are connected via `dbguardian_network`.

