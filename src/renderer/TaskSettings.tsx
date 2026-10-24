import React, { useState } from 'react'
import type { Job } from './types'

export function TaskSettings({ job, close, onSave }: { job: Job; close: () => void; onSave: (job: Job) => void }) {
  const [capacity, setCapacity] = useState(job.route!.context_tokens)
  const [output, setOutput] = useState(job.route!.output_tokens)
  const [image, setImage] = useState(job.route!.image_tokens)
  const [requests, setRequests] = useState(job.limits.max_requests)
  const [seconds, setSeconds] = useState(job.limits.max_active_seconds)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  return <div className="overlay"><form className="modal connection" aria-label="Task limits" onSubmit={async event => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const updated = await window.workbench.invoke<Job>('taskSettings', { job: job.id,
        route: { context_tokens: capacity, output_tokens: output, image_tokens: image },
        limits: { max_requests: requests, max_active_seconds: seconds } })
      onSave(updated); close()
    } catch (error) { setError(String(error)) } finally { setBusy(false) }
  }}>
    <div className="modal-heading"><div><span className="eyebrow">THIS DOCUMENT</span><h2>Task limits</h2></div><button type="button" onClick={close} disabled={busy}>Close</button></div>
    <p className="muted">{job.name} · {job.route!.model} · {job.route!.protocol === 'responses' ? 'Responses' : 'Chat Completions'}</p>
    <p className="hint">These values apply to this task. Recorded usage stays consumed. Capacity changes apply to newly prepared requests; a pending request keeps its saved input and original limits.</p>
    <fieldset disabled={busy} style={{ border: 0, padding: 0, margin: 0 }}>
      <div className="form-row"><label>Task context capacity<input type="number" min="2048" required value={capacity} onChange={e => setCapacity(Number(e.target.value))} /></label><label>Task output reserve<input type="number" min="256" required value={output} onChange={e => setOutput(Number(e.target.value))} /></label></div>
      {job.route!.vision && <label>Task allowance per image<input type="number" min="1" required value={image ?? ''} onChange={e => setImage(Number(e.target.value))} /></label>}
      <div className="form-row"><label>Task total model requests<input type="number" min="1" max="10000" required value={requests} onChange={e => setRequests(Number(e.target.value))} /></label><label>Task active time limit (seconds)<input type="number" min="1" required value={seconds} onChange={e => setSeconds(Number(e.target.value))} /></label></div>
    </fieldset>
    <p className="hint">Consumed: {job.attempts} requests and {job.active_seconds.toFixed(1)} recorded active seconds. Recovery and automatic correction settings remain unchanged.</p>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="modal-footer"><span className="hint">Save, then Continue when ready.</span><button className="primary" type="submit" disabled={busy}>Save task limits</button></div>
  </form></div>
}
