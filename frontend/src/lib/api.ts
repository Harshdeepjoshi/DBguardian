import axios from 'axios'
import {
  BackupInfo,
  BackupListResponse,
  ScheduleInfo,
  ScheduleListResponse,
  ScheduleRequest,
  BackupRequest,
  BackupResponse,
  DatabaseInfo,
  DatabaseListResponse,
  TableInfo,
  TableListResponse,
  SystemStatus,
  ConfigInfo,
  TaskStatus
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || 'default-key'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json',
  },
})

// Backups API
export const backupsApi = {
  createBackup: async (request: BackupRequest): Promise<BackupResponse> => {
    const response = await api.post('/api/backups', request)
    return response.data
  },

  getBackupStatus: async (taskId: string): Promise<TaskStatus> => {
    const response = await api.get(`/api/backups/${taskId}`)
    return response.data
  },

  listBackups: async (databaseName?: string): Promise<BackupListResponse> => {
    const params = databaseName ? { database_name: databaseName } : {}
    const response = await api.get('/api/backups', { params })
    return response.data
  },

  deleteBackup: async (backupId: number): Promise<{ message: string; backup_name: string }> => {
    const response = await api.delete(`/api/backups/${backupId}`)
    return response.data
  },
}

// Schedules API
export const schedulesApi = {
  createSchedule: async (request: ScheduleRequest): Promise<ScheduleInfo> => {
    const response = await api.post('/api/schedules', request)
    return response.data
  },

  listSchedules: async (databaseName?: string, enabledOnly?: boolean): Promise<ScheduleListResponse> => {
    const params: any = {}
    if (databaseName) params.database_name = databaseName
    if (enabledOnly !== undefined) params.enabled_only = enabledOnly

    const response = await api.get('/api/schedules', { params })
    return response.data
  },

  getSchedule: async (scheduleId: number): Promise<ScheduleInfo> => {
    const response = await api.get(`/api/schedules/${scheduleId}`)
    return response.data
  },

  updateSchedule: async (scheduleId: number, request: ScheduleRequest): Promise<ScheduleInfo> => {
    const response = await api.put(`/api/schedules/${scheduleId}`, request)
    return response.data
  },

  deleteSchedule: async (scheduleId: number): Promise<{ message: string; database_name: string }> => {
    const response = await api.delete(`/api/schedules/${scheduleId}`)
    return response.data
  },
}

// Databases API
export const databasesApi = {
  listDatabases: async (): Promise<DatabaseListResponse> => {
    const response = await api.get('/api/databases')
    return response.data
  },

  getDatabaseInfo: async (databaseName: string): Promise<DatabaseInfo> => {
    const response = await api.get(`/api/databases/${databaseName}`)
    return response.data
  },

  listTables: async (databaseName: string): Promise<TableListResponse> => {
    const response = await api.get(`/api/databases/${databaseName}/tables`)
    return response.data
  },
}

// Credentials API
export const credentialsApi = {
  createCredentials: async (credentials: DatabaseCredentials): Promise<DatabaseCredentials> => {
    const response = await api.post('/api/credentials', credentials)
    return response.data
  },

  listCredentials: async (): Promise<DatabaseCredentialsList> => {
    const response = await api.get('/api/credentials')
    return response.data
  },

  getCredentials: async (credentialId: number): Promise<DatabaseCredentials> => {
    const response = await api.get(`/api/credentials/${credentialId}`)
    return response.data
  },

  updateCredentials: async (credentialId: number, credentials: DatabaseCredentials): Promise<DatabaseCredentials> => {
    const response = await api.put(`/api/credentials/${credentialId}`, credentials)
    return response.data
  },

  deleteCredentials: async (credentialId: number): Promise<{ message: string }> => {
    const response = await api.delete(`/api/credentials/${credentialId}`)
    return response.data
  },

  testConnection: async (credentialId: number): Promise<{ message: string }> => {
    const response = await api.post(`/api/credentials/${credentialId}/test`)
    return response.data
  },
}

// System API
export const systemApi = {
  getSystemStatus: async (): Promise<SystemStatus> => {
    const response = await api.get('/api/system/status')
    return response.data
  },

  getConfig: async (): Promise<ConfigInfo> => {
    const response = await api.get('/api/config')
    return response.data
  },
}

export default api
