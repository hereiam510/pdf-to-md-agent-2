import type { RetrySchedule } from '../../types'

const labels: Record<string, string> = {
  unsent: 'Connection failed before sending',
  lost_after_send: 'Connection lost after possible send',
  transient_status: 'Temporary HTTP failure'
}

export function retryDisplay(retry: RetrySchedule) {
  const label = labels[retry.failure_class] ?? 'Network failure'
  const detail = retry.detail ? ` ${retry.detail}` : ''
  return `${label}.${detail} Next retry at ${new Date(retry.due_wall * 1000).toLocaleTimeString()}`
}
