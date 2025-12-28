import React, { useState, useEffect } from 'react'
import { schedulesApi, databasesApi } from '../lib/api'
import { ScheduleInfo, ScheduleRequest, DatabaseInfo } from '../types/api'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Switch } from '../components/ui/switch'
import { useToast } from '../hooks/use-toast'
import { Loader2, Plus, Edit, Trash2, Clock } from 'lucide-react'

const Schedules = () => {
  const [schedules, setSchedules] = useState<ScheduleInfo[]>([])
  const [databases, setDatabases] = useState<DatabaseInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState<ScheduleInfo | null>(null)
  const [formData, setFormData] = useState<ScheduleRequest>({
    database_name: '',
    schedule_type: 'interval',
    interval_minutes: 60,
    cron_expression: '',
    enabled: true
  })
  const { toast } = useToast()

  useEffect(() => {
    loadSchedules()
    loadDatabases()
  }, [])

  const loadSchedules = async () => {
    try {
      const response = await schedulesApi.listSchedules()
      setSchedules(response.schedules)
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load schedules',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const loadDatabases = async () => {
    try {
      const response = await databasesApi.listDatabases()
      setDatabases(response.databases)
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load databases',
        variant: 'destructive'
      })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingSchedule) {
        await schedulesApi.updateSchedule(editingSchedule.id, formData)
        toast({
          title: 'Success',
          description: 'Schedule updated successfully'
        })
      } else {
        await schedulesApi.createSchedule(formData)
        toast({
          title: 'Success',
          description: 'Schedule created successfully'
        })
      }
      loadSchedules()
      resetForm()
    } catch (error) {
      toast({
        title: 'Error',
        description: editingSchedule ? 'Failed to update schedule' : 'Failed to create schedule',
        variant: 'destructive'
      })
    }
  }

  const handleEdit = (schedule: ScheduleInfo) => {
    setEditingSchedule(schedule)
    setFormData({
      database_name: schedule.database_name,
      schedule_type: schedule.schedule_type,
      interval_minutes: schedule.interval_minutes,
      cron_expression: schedule.cron_expression,
      enabled: schedule.enabled
    })
    setShowForm(true)
  }

  const handleDelete = async (scheduleId: number) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return

    try {
      await schedulesApi.deleteSchedule(scheduleId)
      toast({
        title: 'Success',
        description: 'Schedule deleted successfully'
      })
      loadSchedules()
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete schedule',
        variant: 'destructive'
      })
    }
  }

  const resetForm = () => {
    setFormData({
      database_name: '',
      schedule_type: 'interval',
      interval_minutes: 60,
      cron_expression: '',
      enabled: true
    })
    setEditingSchedule(null)
    setShowForm(false)
  }

  const formatScheduleType = (type: string, interval?: number, cron?: string) => {
    if (type === 'interval') {
      return `Every ${interval} minutes`
    } else if (type === 'crontab') {
      return `Cron: ${cron}`
    }
    return type
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Backup Schedules</h1>
        <Button onClick={() => setShowForm(true)} disabled={showForm}>
          <Plus className="h-4 w-4 mr-2" />
          New Schedule
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{editingSchedule ? 'Edit Schedule' : 'Create New Schedule'}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="database_name">Database</Label>
                <Select
                  value={formData.database_name}
                  onValueChange={(value) => setFormData({ ...formData, database_name: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select database" />
                  </SelectTrigger>
                  <SelectContent>
                    {databases.map((db) => (
                      <SelectItem key={db.name} value={db.name}>
                        {db.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="schedule_type">Schedule Type</Label>
                <Select
                  value={formData.schedule_type}
                  onValueChange={(value) => setFormData({ ...formData, schedule_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="interval">Interval</SelectItem>
                    <SelectItem value="crontab">Cron Expression</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {formData.schedule_type === 'interval' && (
                <div>
                  <Label htmlFor="interval_minutes">Interval (minutes)</Label>
                  <Input
                    id="interval_minutes"
                    type="number"
                    value={formData.interval_minutes || ''}
                    onChange={(e) => setFormData({ ...formData, interval_minutes: parseInt(e.target.value) })}
                    min="1"
                  />
                </div>
              )}

              {formData.schedule_type === 'crontab' && (
                <div>
                  <Label htmlFor="cron_expression">Cron Expression</Label>
                  <Input
                    id="cron_expression"
                    value={formData.cron_expression || ''}
                    onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                    placeholder="0 0 * * *"
                  />
                </div>
              )}

              <div className="flex items-center space-x-2">
                <Switch
                  id="enabled"
                  checked={formData.enabled}
                  onCheckedChange={(checked) => setFormData({ ...formData, enabled: checked })}
                />
                <Label htmlFor="enabled">Enabled</Label>
              </div>

              <div className="flex space-x-2">
                <Button type="submit">
                  {editingSchedule ? 'Update' : 'Create'} Schedule
                </Button>
                <Button type="button" variant="outline" onClick={resetForm}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4">
        {schedules.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Clock className="h-12 w-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No schedules yet</h3>
              <p className="text-gray-500 text-center mb-4">
                Create your first backup schedule to automate database backups.
              </p>
              <Button onClick={() => setShowForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Schedule
              </Button>
            </CardContent>
          </Card>
        ) : (
          schedules.map((schedule) => (
            <Card key={schedule.id}>
              <CardContent className="flex items-center justify-between p-6">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="font-medium">{schedule.database_name}</h3>
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      schedule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {schedule.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-1">
                    {formatScheduleType(schedule.schedule_type, schedule.interval_minutes, schedule.cron_expression)}
                  </p>
                  <p className="text-xs text-gray-500">
                    Created: {new Date(schedule.created_at).toLocaleString()}
                    {schedule.last_run && ` • Last run: ${new Date(schedule.last_run).toLocaleString()}`}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(schedule)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(schedule.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}

export { Schedules }
