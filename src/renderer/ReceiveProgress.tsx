import React from 'react'
import type { ReceiveObservation } from './types'

export function ReceiveProgress({ receive, status, running }: { receive: ReceiveObservation; status: string; running: boolean }) {
  const causeNames: Record<string, string> = {
    first_progress_timeout: 'First progress wait expired', progress_idle_timeout: 'Generation progress wait expired',
    total_deadline: 'Total request deadline reached', request_deadline: 'Total request deadline reached',
    user_stop: 'Stopped by user', active_time_limit: 'Task active time limit reached',
    http_error: 'HTTP request failed', stream_error: 'Stream could not be accepted',
    transport_error: 'Connection interrupted', connect_timeout: 'Connection wait expired',
    read_timeout: 'Receive wait expired', write_timeout: 'Send wait expired', pool_timeout: 'Connection availability wait expired'
  }
  let label: string
  if (status === 'accepted') label = 'Complete response accepted'
  else if (status === 'rejected') label = 'Response not accepted'
  else if (receive.stop_cause && receive.stop_cause !== 'complete') label = causeNames[receive.stop_cause] || 'Request stopped'
  else if (status === 'in_flight' && !running) label = 'Interrupted; completion is unknown'
  else if (receive.protocol_complete) label = 'Complete stream received; checking response'
  else if (receive.first_progress_elapsed_seconds != null) label = 'Receiving generation progress'
  else if (receive.mode === 'streaming_progress') label = 'Waiting for first generation progress'
  else label = 'Waiting for a complete response'
  return <div className="agent-meta" data-testid="receive-progress" role="status">
    <span>{label} · {(receive.received_body_bytes || 0).toLocaleString()} bytes received
      {receive.mode === 'streaming_progress' ? ` · ${receive.progress_count || 0} progress updates` : ''}
      {receive.http_status != null ? ` · HTTP ${receive.http_status}` : ''}</span>
    <span className="hint">Receive activity is not a saved conversion result. Tools wait for a complete validated response.</span>
  </div>
}
