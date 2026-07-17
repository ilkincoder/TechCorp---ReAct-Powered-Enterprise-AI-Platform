import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffMonth = Math.floor(diffDay / 30);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
  if (diffDay < 30) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
  if (diffMonth < 12) return `${diffMonth} month${diffMonth > 1 ? 's' : ''} ago`;
  return formatDate(dateString);
}

export function formatDate(dateString: string): string {
  if (!dateString) return '—';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function getSeverityColor(severity: string): string {
  switch (severity.toUpperCase()) {
    case 'P1':
    case 'CRITICAL':
      return 'bg-red-500/10 text-red-500 border-red-500/20';
    case 'P2':
    case 'HIGH':
      return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
    case 'P3':
    case 'MEDIUM':
      return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    default:
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
  }
}

export function getSeverityLabel(severity: string): string {
  switch (severity.toUpperCase()) {
    case 'P1': return 'Critical';
    case 'P2': return 'High';
    case 'P3': return 'Medium';
    default: return severity;
  }
}

export function getStatusColor(status: string): string {
  const s = status.toLowerCase();
  if (['active', 'completed', 'resolved', 'closed'].includes(s)) {
    return 'bg-green-500/10 text-green-500 border-green-500/20';
  }
  if (['in progress', 'planning', 'open', 'investigating'].includes(s)) {
    return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
  }
  if (['on hold', 'trial'].includes(s)) {
    return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
  }
  if (['cancelled', 'expired'].includes(s)) {
    return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
  }
  return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
}
