import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from './components/ui/toaster'
import { Navbar } from './components/Navbar'
import { Dashboard } from './pages/Dashboard'
import { Backups } from './pages/Backups'
import { Schedules } from './pages/Schedules'
import { Databases } from './pages/Databases'
import { System } from './pages/System'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-background">
          <Navbar />
          <main className="container mx-auto px-4 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/backups" element={<Backups />} />
              <Route path="/schedules" element={<Schedules />} />
              <Route path="/databases" element={<Databases />} />
              <Route path="/system" element={<System />} />
            </Routes>
          </main>
        </div>
        <Toaster />
      </Router>
    </QueryClientProvider>
  )
}

export default App
