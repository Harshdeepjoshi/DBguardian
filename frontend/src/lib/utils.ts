import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString()
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'success':
    case 'completed':
      return 'text-green-600'
    case 'pending':
      return 'text-yellow-600'
    case 'progress':
      return 'text-blue-600'
    case 'failure':
    case 'error':
      return 'text-red-600'
    default:
      return 'text-gray-600'
  }
}

export function getStatusBadgeColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'success':
    case 'completed':
      return 'bg-green-100 text-green-800'
    case 'pending':
      return 'bg-yellow-100 text-yellow-800'
    case 'progress':
      return 'bg-blue-100 text-blue-800'
    case 'failure':
    case 'error':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}
