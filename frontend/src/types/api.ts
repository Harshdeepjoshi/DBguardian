export interface BackupRequest {
  database_name?: string
}

export interface BackupResponse {
  task_id: string
  status: string
  message: string
}

export interface BackupInfo {
  id: number
  database_name: string
  backup_name: string
  storage_type: string
  storage_location: string
  created_at?: string
  size_bytes?: number
  status: string
}

export interface BackupListResponse {
  backups: BackupInfo[]
}

export interface ScheduleRequest {
  database_name: string
  schedule_type: string
  interval_minutes?: number
  cron_expression?: string
  enabled: boolean
}

export interface ScheduleInfo {
  id: number
  database_name: string
  schedule_type: string
  interval_minutes?: number
  cron_expression?: string
  enabled: boolean
  created_at: string
  last_run?: string
  next_run?: string
}

export interface ScheduleListResponse {
  schedules: ScheduleInfo[]
}

export interface DatabaseInfo {
  name: string
  size: string
  table_count: number
  status: string
}

export interface DatabaseListResponse {
  databases: DatabaseInfo[]
}

export interface TableInfo {
  name: string
  type: string
  column_count: number
}

export interface TableListResponse {
  tables: TableInfo[]
}

export interface SystemStatus {
  database: string
  celery: string
  storage: string
  overall: string
}

export interface ConfigInfo {
  database_configured: boolean
  minio_configured: boolean
  encryption_enabled: boolean
  prometheus_enabled: boolean
  celery_enabled: boolean
  postgres_version: string
}

export interface DatabaseCredentials {
  id?: number
  name: string
  host: string
  port: number
  database: string
  username: string
  password: string
  version?: string
  created_at?: string
}

export interface DatabaseCredentialsList {
  databases: DatabaseCredentials[]
}

export interface TaskStatus {
  task_id: string
  status: string
  message?: string
  result?: any
  error?: string
}
