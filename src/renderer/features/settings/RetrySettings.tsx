import React from 'react'

export type RetryPolicy = { automatic_retry: boolean; max_attempts_per_request: number; max_server_wait_seconds: number }

export function RetrySettings({ value, onChange }: { value: RetryPolicy; onChange: (value: RetryPolicy) => void }) {
  return <>
    <label className="check"><input type="checkbox" checked={value.automatic_retry}
      onChange={e => onChange({ ...value, automatic_retry: e.target.checked })} />Retry automatically after network problems</label>
    <div className="form-row">
      <label>Maximum attempts per request<input type="number" min="1" max="10" required value={value.max_attempts_per_request}
        onChange={e => onChange({ ...value, max_attempts_per_request: Number(e.target.value) })} /></label>
      <label>Maximum automatic server wait (seconds)<input type="number" min="0" required value={value.max_server_wait_seconds}
        onChange={e => onChange({ ...value, max_server_wait_seconds: Number(e.target.value) })} /></label>
    </div>
  </>
}
