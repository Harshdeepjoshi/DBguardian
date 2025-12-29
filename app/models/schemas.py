from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Backup related models
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

# Schedule related models
class ScheduleRequest(BaseModel):
    database_name: str = Field(..., description="Name of the database to backup")
    schedule_type: str = Field(..., description="Type of schedule: 'interval', 'crontab'")
    interval_minutes: Optional[int] = Field(None, description="Interval in minutes (for interval schedules)")
    cron_expression: Optional[str] = Field(None, description="Cron expression (for crontab schedules)")
    enabled: bool = Field(True, description="Whether the schedule is enabled")

class ScheduleInfo(BaseModel):
    id: int
    database_name: str
    schedule_type: str
    interval_minutes: Optional[int]
    cron_expression: Optional[str]
    enabled: bool
    created_at: str
    last_run: Optional[str]
    next_run: Optional[str]

class ScheduleListResponse(BaseModel):
    schedules: List[ScheduleInfo]

# Database info models
class DatabaseInfo(BaseModel):
    name: str
    size: str
    table_count: int
    status: str

class DatabaseListResponse(BaseModel):
    databases: List[DatabaseInfo]

class TableInfo(BaseModel):
    name: str
    type: str
    column_count: int

class TableListResponse(BaseModel):
    tables: List[TableInfo]

# System status model
class SystemStatus(BaseModel):
    database: str
    celery: str
    storage: str
    overall: str

# Database credentials model
class DatabaseCredentials(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., description="Unique name for this database configuration")
    host: str = Field(..., description="Database host")
    port: int = Field(5432, description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    version: Optional[str] = Field(None, description="PostgreSQL version")
    created_at: Optional[str] = None

class DatabaseCredentialsList(BaseModel):
    databases: List[DatabaseCredentials]

# Configuration model
class ConfigInfo(BaseModel):
    database_configured: bool
    minio_configured: bool
    encryption_enabled: bool
    prometheus_enabled: bool
    celery_enabled: bool
    postgres_version: str
