# Fix Celery Circular Import Issue

## Tasks
- [x] Rename app/celery.py to app/celery_app.py and update to use environment variables
- [x] Update app/app.py to import Celery instance from app.celery_app
- [x] Update app/tasks.py to import Celery instance from app.celery_app
- [x] Update Dockerfile to use -A app.celery_app
- [x] Update docker-compose.yml to use -A app.celery_app
- [x] Delete old app/celery.py file
- [x] Fix circular import by moving Celery imports to runtime in app.py
- [x] Container now running successfully on port 8000
