import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { useToast } from '../hooks/use-toast'
import { credentialsApi } from '../lib/api'
import { DatabaseCredentials } from '../types/api'
import { Plus, Edit, Trash2, TestTube, CheckCircle, XCircle } from 'lucide-react'

const Credentials: React.FC = () => {
  const [credentials, setCredentials] = useState<DatabaseCredentials[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingCredential, setEditingCredential] = useState<DatabaseCredentials | null>(null)
  const [testingConnection, setTestingConnection] = useState<number | null>(null)
  const [formData, setFormData] = useState<Partial<DatabaseCredentials>>({
    name: '',
    host: '',
    port: 5432,
    database: '',
    username: '',
    password: '',
    version: ''
  })
  const { toast } = useToast()

  useEffect(() => {
    loadCredentials()
  }, [])

  const loadCredentials = async () => {
    try {
      const response = await credentialsApi.listCredentials()
      setCredentials(response.databases)
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load database credentials',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingCredential) {
        await credentialsApi.updateCredentials(editingCredential.id!, formData as DatabaseCredentials)
        toast({
          title: 'Success',
          description: 'Database credentials updated successfully'
        })
      } else {
        await credentialsApi.createCredentials(formData as DatabaseCredentials)
        toast({
          title: 'Success',
          description: 'Database credentials created successfully'
        })
      }
      await loadCredentials()
      resetForm()
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save database credentials',
        variant: 'destructive'
      })
    }
  }

  const handleEdit = (credential: DatabaseCredentials) => {
    setEditingCredential(credential)
    setFormData(credential)
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete these credentials?')) return

    try {
      await credentialsApi.deleteCredentials(id)
      toast({
        title: 'Success',
        description: 'Database credentials deleted successfully'
      })
      await loadCredentials()
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete database credentials',
        variant: 'destructive'
      })
    }
  }

  const handleTestConnection = async (id: number) => {
    setTestingConnection(id)
    try {
      await credentialsApi.testConnection(id)
      toast({
        title: 'Success',
        description: 'Database connection successful'
      })
    } catch (error) {
      toast({
        title: 'Connection Failed',
        description: 'Unable to connect to database',
        variant: 'destructive'
      })
    } finally {
      setTestingConnection(null)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      host: '',
      port: 5432,
      database: '',
      username: '',
      password: '',
      version: ''
    })
    setEditingCredential(null)
    setShowForm(false)
  }

  if (loading) {
    return <div className="flex justify-center items-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Database Credentials</h1>
          <p className="text-gray-600">Manage connections to multiple databases</p>
        </div>
        <Button onClick={() => setShowForm(true)} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Add Database
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{editingCredential ? 'Edit Database' : 'Add New Database'}</CardTitle>
            <CardDescription>
              Configure connection details for a PostgreSQL database
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Database Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    placeholder="e.g., production-db"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="host">Host</Label>
                  <Input
                    id="host"
                    value={formData.host}
                    onChange={(e) => setFormData({...formData, host: e.target.value})}
                    placeholder="localhost"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="port">Port</Label>
                  <Input
                    id="port"
                    type="number"
                    value={formData.port}
                    onChange={(e) => setFormData({...formData, port: parseInt(e.target.value)})}
                    placeholder="5432"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="database">Database Name</Label>
                  <Input
                    id="database"
                    value={formData.database}
                    onChange={(e) => setFormData({...formData, database: e.target.value})}
                    placeholder="postgres"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    placeholder="postgres"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="version">PostgreSQL Version</Label>
                  <Select value={formData.version} onValueChange={(value) => setFormData({...formData, version: value})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select version" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="13">PostgreSQL 13</SelectItem>
                      <SelectItem value="14">PostgreSQL 14</SelectItem>
                      <SelectItem value="15">PostgreSQL 15</SelectItem>
                      <SelectItem value="16">PostgreSQL 16</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit">
                  {editingCredential ? 'Update' : 'Create'} Database
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
        {credentials.map((credential) => (
          <Card key={credential.id}>
            <CardContent className="pt-6">
              <div className="flex justify-between items-start">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold">{credential.name}</h3>
                    <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      PostgreSQL {credential.version || 'Unknown'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p><strong>Host:</strong> {credential.host}:{credential.port}</p>
                    <p><strong>Database:</strong> {credential.database}</p>
                    <p><strong>Username:</strong> {credential.username}</p>
                    <p><strong>Created:</strong> {new Date(credential.created_at!).toLocaleDateString()}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleTestConnection(credential.id!)}
                    disabled={testingConnection === credential.id}
                  >
                    {testingConnection === credential.id ? (
                      <div className="flex items-center gap-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
                        Testing...
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <TestTube className="h-4 w-4" />
                        Test
                      </div>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(credential)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(credential.id!)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {credentials.length === 0 && (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <p className="text-gray-500">No database credentials configured yet.</p>
                <Button onClick={() => setShowForm(true)} className="mt-4">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Your First Database
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default Credentials
