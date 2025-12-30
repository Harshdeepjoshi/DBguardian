import { useEffect, useState } from 'react'
import { backupsApi } from '../lib/api'
import { BackupInfo, BackupRequest, BackupResponse, TaskStatus } from '../types/api'
import { Button } from '../components/ui/button'
import { useToast } from '../hooks/use-toast'

const Backups = () => {
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [creatingBackup, setCreatingBackup] = useState(false)
  const [selectedDatabase, setSelectedDatabase] = useState('')
  const [taskStatuses, setTaskStatuses] = useState<Record<string, TaskStatus>>({})
  const { toast } = useToast()

  useEffect(() => {
    fetchBackups()
  }, [])

  const fetchBackups = async () => {
    try {
      const response = await backupsApi.listBackups()
      setBackups(response.backups)
    } catch (error) {
      console.error('Failed to fetch backups:', error)
      toast({
        title: 'Error',
        description: 'Failed to load backups',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCreateBackup = async () => {
    if (!selectedDatabase.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter a database name',
        variant: 'destructive'
      })
      return
    }

    setCreatingBackup(true)
    try {
      const request: BackupRequest = {
        database_name: selectedDatabase
      }
      const response: BackupResponse = await backupsApi.createBackup(request)

      toast({
        title: 'Backup Started',
        description: `Backup task ${response.task_id} has been started`,
      })

      // Start polling for task status
      pollTaskStatus(response.task_id)

      // Clear the input
      setSelectedDatabase('')
    } catch (error) {
      console.error('Failed to create backup:', error)
      toast({
        title: 'Error',
        description: 'Failed to start backup',
        variant: 'destructive'
      })
    } finally {
      setCreatingBackup(false)
    }
  }

  const pollTaskStatus = (taskId: string) => {
    const poll = async () => {
      try {
        const status = await backupsApi.getBackupStatus(taskId)
        setTaskStatuses(prev => ({ ...prev, [taskId]: status }))

        if (status.status === 'pending' || status.status === 'progress') {
          setTimeout(poll, 2000) // Poll every 2 seconds
        } else {
          // Refresh backups list when task completes
          fetchBackups()
        }
      } catch (error) {
        console.error('Failed to get task status:', error)
      }
    }
    poll()
  }

  const handleDeleteBackup = async (backup: BackupInfo) => {
    if (!confirm('Are you sure you want to delete this backup?')) return

    try {
      await backupsApi.deleteBackup(backup.filename)
      toast({
        title: 'Success',
        description: 'Backup deleted successfully',
      })
      fetchBackups()
    } catch (error) {
      console.error('Failed to delete backup:', error)
      toast({
        title: 'Error',
        description: 'Failed to delete backup',
        variant: 'destructive'
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading backups...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Backups</h1>

      {/* Create Backup Form */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Create New Backup</h2>
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Database name"
            value={selectedDatabase}
            onChange={(e) => setSelectedDatabase(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Button
            onClick={handleCreateBackup}
            disabled={creatingBackup}
          >
            {creatingBackup ? 'Creating...' : 'Create Backup'}
          </Button>
        </div>
      </div>

      {/* Active Tasks */}
      {Object.keys(taskStatuses).length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Active Backup Tasks</h2>
          <div className="space-y-3">
            {Object.entries(taskStatuses).map(([taskId, status]) => (
              <div key={taskId} className="flex justify-between items-center p-3 bg-blue-50 rounded">
                <div>
                  <div className="font-medium">Task {taskId}</div>
                  <div className="text-sm text-gray-600">{status.message || 'Processing...'}</div>
                </div>
                <div className={`text-sm px-2 py-1 rounded ${
                  status.status === 'success' ? 'bg-green-100 text-green-800' :
                  status.status === 'failure' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {status.status}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Backups List */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Backup History</h2>
        {backups.length > 0 ? (
          <div className="space-y-3">
            {backups.map((backup) => (
              <div key={backup.id} className="flex justify-between items-center p-4 border border-gray-200 rounded">
                <div>
                  <div className="font-medium">{backup.database_name}</div>
                  <div className="text-sm text-gray-600">{backup.backup_name}</div>
                  <div className="text-xs text-gray-500">
                    Created: {backup.created_at ? new Date(backup.created_at).toLocaleString() : 'N/A'}
                  </div>
                  {backup.size_bytes && (
                    <div className="text-xs text-gray-500">
                      Size: {(backup.size_bytes / 1024 / 1024).toFixed(2)} MB
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <div className={`text-sm px-2 py-1 rounded ${
                    backup.status === 'completed' ? 'bg-green-100 text-green-800' :
                    backup.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {backup.status}
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteBackup(backup)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No backups found</p>
        )}
      </div>
    </div>
  )
}

export { Backups }
