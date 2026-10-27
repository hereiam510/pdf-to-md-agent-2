import React from 'react'
import type { WaitPolicy } from './types'

export const initialWaitPolicy: WaitPolicy = { first_progress_seconds: 600, idle_progress_seconds: 300, total_seconds: null }

export function WaitingSettings({ value, deadline, onChange, onDeadline, legacyLabel = 'Request deadline (seconds)' }: {
  value: WaitPolicy | null | undefined; deadline: number;
  onChange: (value: WaitPolicy | null) => void; onDeadline: (value: number) => void; legacyLabel?: string
}) {
  return <>
    <label>Response waiting<select aria-label="Response waiting" value={value == null ? 'complete' : 'streaming'} onChange={event => onChange(event.target.value === 'streaming' ? { ...initialWaitPolicy } : null)}>
      <option value="streaming">Wait while generation progresses</option>
      <option value="complete">Complete response with a total deadline</option>
    </select></label>
    {value == null ? <>
      <label>{legacyLabel}<input type="number" min="1" max="3600" step="any" required value={deadline} onChange={event => onDeadline(Number(event.target.value))} /></label>
      <p className="hint">Total elapsed time for each new request, including context organization. Incoming bytes do not reset this deadline.</p>
    </> : <>
      <div className="form-row">
        <label>First progress wait (seconds)<input type="number" min="1" max="3600" step="any" required value={value.first_progress_seconds} onChange={event => onChange({ ...value, first_progress_seconds: Number(event.target.value) })} /></label>
        <label>Progress idle wait (seconds)<input type="number" min="1" max="3600" step="any" required value={value.idle_progress_seconds} onChange={event => onChange({ ...value, idle_progress_seconds: Number(event.target.value) })} /></label>
      </div>
      <p className="hint">Wait for generated text or tool arguments, then for further progress. Connection activity alone does not extend waiting. The 600 / 300 second starting values need reassessment with this route.</p>
      <label className="check"><input type="checkbox" checked={value.total_seconds != null} onChange={event => onChange({ ...value, total_seconds: event.target.checked ? 600 : null })} />Set a total request deadline</label>
      {value.total_seconds != null ? <>
        <label>Total request deadline (seconds)<input type="number" min="1" max="3600" step="any" required value={value.total_seconds} onChange={event => onChange({ ...value, total_seconds: Number(event.target.value) })} /></label>
        <p className="hint">This optional deadline stops the request even if generation is still progressing.</p>
      </> : <p className="hint">No total request deadline while progress continues. Stop and task budgets still apply.</p>}
    </>}
  </>
}
