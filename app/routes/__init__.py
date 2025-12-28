from .backups import router as backups_router
from .schedules import router as schedules_router
from .database import router as database_router
from .system import router as system_router

# Re-export for convenience
backups = backups_router
schedules = schedules_router
database = database_router
system = system_router
