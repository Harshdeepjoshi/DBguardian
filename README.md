# DBGuardian

## Overview
DBGuardian is a backend system for automated database backup and point-in-time recovery, designed to improve reliability and reduce the risk of data loss in production environments.

## Problem
In many backend systems, database backups are either manual or poorly automated, making recovery unreliable and increasing the risk of data loss during failures.

## Solution
DBGuardian automates the entire backup lifecycle by:
- Scheduling periodic backups
- Encrypting and securely storing backups
- Handling failures with retry and fallback mechanisms
- Enabling point-in-time recovery

## Architecture
The system is built using a distributed architecture:

- **FastAPI**: Core API service for managing backup operations  
- **PostgreSQL**: Primary database  
- **MinIO (S3-compatible)**: Backup storage layer  
- **Redis**: Message broker and caching  
- **Celery Worker**: Asynchronous background task execution  
- **Celery Beat**: Scheduled backup jobs  
- **Prometheus + Grafana**: Monitoring and observability  

## Key Features
- Automated scheduled backups using Celery Beat  
- Asynchronous backup processing via Celery workers  
- Backup encryption using secure keys  
- Failure handling with retry and fallback storage  
- Point-in-time recovery capability  
- Monitoring and metrics visualization using Prometheus and Grafana  

## How It Works
1. Celery Beat schedules periodic backup jobs  
2. Worker processes execute database dumps asynchronously  
3. Backups are encrypted and stored in MinIO (S3-compatible storage)  
4. Failures trigger retry mechanisms or fallback storage  
5. Metrics are collected and visualized for monitoring  

## Tech Stack
- Python (FastAPI)
- PostgreSQL
- Redis
- Celery
- Docker & Docker Compose
- MinIO (S3-compatible storage)
- Prometheus & Grafana

## Setup

1. Clone the repository  
2. Copy `.env` and update variables  
3. Run:

```bash
docker-compose up --build
