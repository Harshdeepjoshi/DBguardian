import axios from 'axios'
import {
  BackupInfo,
  BackupListResponse,
  ScheduleInfo,
  ScheduleListResponse,
  ScheduleRequest,
  BackupRequest,
  DatabaseInfo,
  SystemInfo,
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
  createBackup: async (request: BackupRequest): Promise<{ task_id: string }> => {
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

  deleteBackup: async (backupId: string): Promise<void> => {
    await api.delete(`/api/backups/${backupId}`)
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

  deleteSchedule: async (scheduleId: number): Promise<void> => {
    await api.delete(`/api/schedules/${scheduleId}`)
  },
}

// Databases API
export const databasesApi = {
  listDatabases: async (): Promise<DatabaseInfo[]> => {
    const response = await api.get('/api/databases')
    return response.data
  },

  getDatabaseInfo: async (databaseName: string): Promise<DatabaseInfo> => {
    const response = await api.get(`/api/databases/${databaseName}`)
    return response.data
  },
}

// System API
export const systemApi = {
  getSystemInfo: async (): Promise<SystemInfo> => {
    const response = await api.get('/api/system/info')
    return response.data
  },

  getConfig: async (): Promise<any> => {
    const response = await api.get('/api/system/config')
    return response.data
  },
}

export default api
