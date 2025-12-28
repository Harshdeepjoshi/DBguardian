import { useEffect, useState } from 'react'
import { systemApi, backupsApi, schedulesApi } from '../lib/api'
import { SystemStatus, BackupInfo, ScheduleInfo } from '../types/api'

const Dashboard = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [recentBackups, setRecentBackups] = useState<BackupInfo[]>([])
  const [activeSchedules, setActiveSchedules] = useState<ScheduleInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [statusResponse, backupsResponse, schedulesResponse] = await Promise.all([
          systemApi.getSystemStatus(),
          backupsApi.listBackups(),
          schedulesApi.listSchedules(undefined, true)
        ])

        setSystemStatus(statusResponse)
        setRecentBackups(backupsResponse.backups.slice(0, 5)) // Show last 5 backups
        setActiveSchedules(schedulesResponse.schedules.slice(0, 5)) // Show first 5 active schedules
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>

      {/* System Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">System Status</h2>
        {systemStatus && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className={`p-4 rounded-lg ${systemStatus.database === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              <div className="font-medium">Database</div>
              <div className="text-sm capitalize">{systemStatus.database}</div>
            </div>
            <div className={`p-4 rounded-lg ${systemStatus.celery === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
              <div className="font-medium">Celery</div>
              <div className="text-sm capitalize">{systemStatus.celery}</div>
            </div>
            <div className={`p-4 rounded-lg ${systemStatus.storage === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              <div className="font-medium">Storage</div>
              <div className="text-sm capitalize">{systemStatus.storage}</div>
            </div>
            <div className={`p-4 rounded-lg ${systemStatus.overall === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
              <div className="font-medium">Overall</div>
              <div className="text-sm capitalize">{systemStatus.overall}</div>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Backups */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Backups</h2>
          {recentBackups.length > 0 ? (
            <div className="space-y-3">
              {recentBackups.map((backup) => (
                <div key={backup.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <div>
                    <div className="font-medium">{backup.database_name}</div>
                    <div className="text-sm text-gray-600">{backup.backup_name}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm px-2 py-1 rounded ${
                      backup.status === 'completed' ? 'bg-green-100 text-green-800' :
                      backup.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {backup.status}
                    </div>
                    <div className="text-xs text-gray-500">
                      {backup.created_at ? new Date(backup.created_at).toLocaleDateString() : 'N/A'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No backups found</p>
          )}
        </div>

        {/* Active Schedules */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Active Schedules</h2>
          {activeSchedules.length > 0 ? (
            <div className="space-y-3">
              {activeSchedules.map((schedule) => (
                <div key={schedule.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <div>
                    <div className="font-medium">{schedule.database_name}</div>
                    <div className="text-sm text-gray-600">
                      {schedule.schedule_type === 'interval' 
                        ? `Every ${schedule.interval_minutes} minutes`
                        : `Cron: ${schedule.cron_expression}`
                      }
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm px-2 py-1 rounded ${
                      schedule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {schedule.enabled ? 'Enabled' : 'Disabled'}
                    </div>
                    <div className="text-xs text-gray-500">
                      Next: {schedule.next_run ? new Date(schedule.next_run).toLocaleString() : 'N/A'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No active schedules</p>
          )}
        </div>
      </div>
    </div>
  )
}

export { Dashboard }
