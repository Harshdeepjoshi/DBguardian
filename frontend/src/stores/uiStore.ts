import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UIState {
  theme: 'light' | 'dark'
  sidebarCollapsed: boolean
  refreshInterval: number // in seconds
  setTheme: (theme: 'light' | 'dark') => void
  toggleSidebar: () => void
  setRefreshInterval: (interval: number) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: 'light',
      sidebarCollapsed: false,
      refreshInterval: 30,
      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setRefreshInterval: (interval) => set({ refreshInterval: interval }),
    }),
    {
      name: 'dbguardian-ui-store',
    }
  )
)
