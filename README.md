# DBGuardian

## Overview
DBGuardian is a backend system for **automated database backup and point-in-time recovery**, designed to improve reliability and reduce the risk of data loss in production environments.

## Problem
In many backend systems, database backups are either **manual or poorly automated**, making recovery unreliable and increasing the risk of data loss during failures.

## Solution
DBGuardian automates the entire backup lifecycle by:
- Scheduling periodic backups
- Encrypting and securely storing backups
- Handling failures with retry and fallback mechanisms
- Enabling point-in-time recovery

## Architecture
The system is built using a **distributed architecture**:

```
FastAPI – Core API service for managing backup operations
PostgreSQL – Primary database
MinIO (S3-compatible) – Backup storage layer
Redis – Message broker and caching
Celery Worker – Asynchronous background task execution
Celery Beat – Scheduled backup jobs
Prometheus – Metrics collection
Grafana – Monitoring dashboards
```

## Key Features
- ✅ Automated scheduled backups using Celery Beat
- ✅ Asynchronous backup processing via Celery workers
- ✅ Backup encryption using secure keys
- ✅ Failure handling with retry and fallback storage
- ✅ Point-in-time recovery capability
- ✅ Monitoring and metrics visualization

## How It Works
1. **Celery Beat** schedules periodic backup jobs
2. **Celery workers** execute database dump operations asynchronously
3. Backups are **encrypted** before storage
4. Encrypted backups are stored in **MinIO**
5. Failures trigger **retry mechanisms** or fallback storage
6. **Metrics** are collected and visualized

## Tech Stack
| Category | Technologies |
|----------|--------------|
| Backend | Python (FastAPI) |
| Database | PostgreSQL |
| Queue/Cache | Redis |
| Tasks | Celery, Celery Beat |
| Storage | MinIO |
| Monitoring | Prometheus & Grafana |
| Deployment | Docker & Docker Compose |

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/Harshdeepjoshi/DBguardian.git
cd DBguardian
```

### 2. Copy environment file
```bash
cp .env.example .env
```

### 3. Update environment variables
See [Environment Variables](#-environment-variables) section.

### 4. Start services
```bash
docker-compose up --build
```

## Environment Variables
Refer to the `.env` file.

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `BACKUP_ENCRYPTION_KEY` | Generate using: `openssl rand -base64 32` | `your-32-byte-base64-key` |
| `MINIO_BUCKET_NAME` | Default: `backups` | `backups` |

### MinIO Bucket Setup
- Opens automatically on first backup
- Optional manual setup via console: **http://localhost:9003**

## Volumes
- `postgres_data`
- `minio_data`
- `redis_data`
- `fallback_volume`
- `prometheus_data`
- `grafana_data`

## Network
All services run within `dbguardian_network`.

## Use Case
Designed for **backend systems requiring reliable, automated backup and recovery pipelines**.

## Future Improvements
- 📧 Alerting system (email/Slack)
- 🗄️ Multi-database support
- 🔐 Role-based access control

## Author
**Harshdeep Joshi**


