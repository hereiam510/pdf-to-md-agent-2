import React, { useEffect, useRef, useState } from 'react'
import type { DiagnosticDetail, DiagnosticPage } from '../../types'
import { readDiagnosticRecord } from './diagnosticClient'
import { retryDisplay } from '../recovery/retryDisplay'

const api = window.workbench.invoke
const kinds = [['activity', 'Activity'], ['request', 'Requests'], ['operation', 'Operations'], ['version', 'Versions'],
  ['context_commit', 'Context decisions'], ['context_disposition', 'Context dispositions'], ['context_policy', 'Active context'],
  ['conflict_resolution', 'Resolutions'], ['event_receipt', 'Boundary receipts'], ['blob', 'Evidence records']]
const json = (value: unknown) => JSON.stringify(value, null, 2)

function activityLabel({ type, data }: DiagnosticPage['events'][number]) {
  if (type === 'request_started' && typeof data.attempt_number === 'number' && typeof data.max_attempts === 'number')
    return `Attempt ${data.attempt_number} of ${data.max_attempts}`
  if (type === 'retry_scheduled' && typeof data.due_wall === 'number'
      && typeof data.next_attempt === 'number' && typeof data.max_attempts === 'number')
    return retryDisplay({ due_wall: data.due_wall, next_attempt: data.next_attempt, max_attempts: data.max_attempts,
      failure_class: String(data.failure_class), detail: typeof data.detail === 'string' ? data.detail : undefined })
  if (type === 'resumed_after_sleep' && typeof data.duration_seconds === 'number')
    return `Resumed after sleep (${data.duration_seconds.toFixed(1)} seconds)`
  return type.replaceAll('_', ' ')
}
// Raw observations remain unknown. Narrow only the selected display value;
// retain unsupported shapes as JSON in both the cell and the complete record.
const field = (value: unknown, key: string): unknown =>
  value !== null && typeof value === 'object' ? Object.getOwnPropertyDescriptor(value, key)?.value : undefined
const observed = (value: unknown) => typeof value === 'string' || typeof value === 'number'
  ? value : value == null ? undefined : json(value)

export function TaskDiagnostics({ job, latest, observation }: { job: string; latest: number | null; observation: string }) {
  const [events, setEvents] = useState<DiagnosticPage | null>(null)
  const [list, setList] = useState<DiagnosticPage | null>(null)
  const [kind, setKind] = useState('activity')
  const [detail, setDetail] = useState<DiagnosticDetail | null>(null)
  const [detailObservation, setDetailObservation] = useState('')
  const [evidence, setEvidence] = useState<any>(null)
  const [selectedRef, setSelectedRef] = useState('')
  const [mode, setMode] = useState('full')
  const [pointer, setPointer] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const request = useRef(0)
  const views = useRef(new Set<string>())
  const stale = detail !== null && detailObservation !== observation

  async function loadEvents(cursor?: string) {
    const generation = ++request.current
    setBusy(true); setError(''); setDetail(null); setEvidence(null); setSelectedRef('')
    try {
      const page = await api<DiagnosticPage>('activity', { job, cursor })
      if (generation !== request.current) {
        if (page.view && !cursor) void api('closeDiagnostics', { job, view: page.view }).catch(() => {})
        return
      }
      if (page.view) views.current.add(page.view)
      if (page.status !== 'ok') throw Error(page.reason || page.status)
      setEvents(page); setKind('activity'); setList(null)
      // A refresh supersedes old private copies. Pages retain the same token.
      for (const token of views.current) if (token !== page.view) {
        void api('closeDiagnostics', { job, view: token }).catch(() => {})
        views.current.delete(token)
      }
    } catch (e) { if (generation === request.current) { setError(String(e)); setEvents(null) } }
    finally { if (generation === request.current) setBusy(false) }
  }
  useEffect(() => {
    void loadEvents()
    return () => {
      ++request.current
      for (const view of views.current) void api('closeDiagnostics', { job, view }).catch(() => {})
    }
  }, [job])

  async function loadRecords(nextKind: string, cursor?: string) {
    if (!events) return
    const generation = ++request.current
    setKind(nextKind); setDetail(null); setEvidence(null); setSelectedRef(''); setBusy(true); setError(''); setList(null)
    if (nextKind === 'activity') { setBusy(false); return }
    try {
      const page = await api<DiagnosticPage>('diagnostics', { job, view: events.view, kind: nextKind, cursor })
      if (generation !== request.current) return
      if (page.status !== 'ok') throw Error(page.reason || page.status)
      setList(page)
    } catch (e) { if (generation === request.current) setError(String(e)) }
    finally { if (generation === request.current) setBusy(false) }
  }
  async function openRecord(recordKind: string, key: string) {
    if (!events) return
    const generation = ++request.current
    setBusy(true); setError(''); setDetail(null); setEvidence(null); setSelectedRef('')
    try {
      const value = await readDiagnosticRecord({ job, view: events.view, kind: recordKind, key })
      if (generation !== request.current) return
      if (value.status !== 'ok') throw Error(`${value.status}: ${value.reason}`)
      setDetail(value); setDetailObservation(observation)
    } catch (e) { if (generation === request.current) setError(String(e)) }
    finally { if (generation === request.current) setBusy(false) }
  }
  async function openEvidence(ref: string, selectedMode = 'full', selectors = false) {
    if (!events) return
    const generation = ++request.current
    setSelectedRef(ref); setMode(selectedMode); setBusy(true); setError(''); setEvidence(null)
    if (!selectors) { setPointer(''); setStart(''); setEnd('') }
    try {
      const value = await api('diagnosticEvidence', { job, view: events.view, ref, mode: selectedMode,
        pointer: selectors ? pointer : '', start: selectors && start !== '' ? Number(start) : undefined, end: selectors && end !== '' ? Number(end) : undefined })
      if (generation !== request.current) return
      if (value.status !== 'ok') throw Error(`${value.status}: ${value.reason}`)
      setEvidence(value)
    } catch (e) { if (generation === request.current) setError(String(e)) }
    finally { if (generation === request.current) setBusy(false) }
  }

  return <section className="task-diagnostics" aria-label="Task activity and diagnostics">
    <div className="diagnostic-toolbar"><strong>Task activity and diagnostics</strong><button disabled={busy} onClick={() => void loadEvents()}>Refresh diagnostics and recent activity</button></div>
    <p className="hint">Read-only catalog facts. Graph position and readiness are unchecked here; use the saved acceptance inspector below. Missing history remains unknown. Metadata does not expose hidden model reasoning.</p>
    {events && <>
      <p className="hint">Task <code>{job}</code> · Captured {new Date(events.captured_at * 1000).toLocaleString()} · {events.consistency}. Navigation expires after 15 minutes.</p>
      <p className="hint">Event boundary {events.boundary_seq ?? 'empty'} · {events.total} task events. Global sequence numbers are identities, not task counts. The event boundary is not a mutable-record snapshot or exporter change cursor.</p>
      {latest !== events.boundary_seq && <p role="status">New activity is available. Refresh to establish a new boundary.</p>}
      <label>Diagnostic view<select aria-label="Diagnostic view" value={kind} disabled={busy} onChange={e => void loadRecords(e.target.value)}>{kinds.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      {kind === 'activity' ? <>
        <p role="status">Showing {events.first}–{events.last} of {events.total} events in this boundary; {events.events.length} loaded. Each page is ordered oldest to newest.</p>
        <div className="diagnostic-toolbar">{[['Oldest events', events.oldest], ['Older events', events.older], ['Newer events', events.newer], ['Recent events', events.recent]].map(([label, cursor]) => <button key={label} disabled={busy || !cursor} onClick={() => void loadEvents(cursor!)}>{label}</button>)}</div>
        <div className="activity-log">{events.events.map(event => <div key={event.id} data-event-seq={event.seq}><time>{new Date(event.created * 1000).toLocaleString()}</time><span>#{event.seq} · {activityLabel(event)}</span><details><summary>Event details</summary><pre>{json(event.data)}</pre></details></div>)}{!events.events.length && <p>No events in this task boundary.</p>}</div>
      </> : list && <>
        <p role="status">Showing {list.items?.length ? (list.offset || 0) + 1 : 0}–{(list.offset || 0) + (list.items?.length || 0)} of {list.total} {kind} records. Newest catalog creation first; this is not graph execution order.</p>
        <table><thead><tr><th>Identity</th><th>Recorded facts</th><th>Detail</th></tr></thead><tbody>{list.items?.map(item => <tr key={item.id}><td><code>{item.id}</code></td><td>{[item.diagnostic_status && `Diagnostic ${item.diagnostic_status}`, item.status, item.tool, item.claim, item.reason, item.attempts != null ? `${item.attempts} attempts` : ''].filter(Boolean).join(' · ')}</td><td><button disabled={busy} onClick={() => void openRecord(kind, item.id)}>Inspect {item.id}</button></td></tr>)}</tbody></table>
        <div className="diagnostic-toolbar"><button disabled={busy || !list.offset} onClick={() => void loadRecords(kind)}>First records</button><button disabled={busy || !list.next} onClick={() => void loadRecords(kind, list.next!)}>More records</button></div>
      </>}
    </>}
    {error && <p role="alert" className="error">{error} · Refresh to retry. Independent previously displayed facts retain their captured scope.</p>}
    {busy && <p role="status">Reading selected local facts…</p>}
    {detail && <section className="diagnostic-detail" aria-label="Diagnostic record detail">
      <h3>{detail.kind} · {detail.id}</h3>
      {detail.record.status && <p><strong>Recorded status: </strong>{detail.record.status}</p>}
      {stale && <p role="alert">Task observation changed. These are historical captured facts; refresh before opening more evidence.</p>}
      {detail.boundary && <p><strong>Established boundary: </strong>{detail.boundary}</p>}
      {detail.publication && <p><strong>Acceptance publication: </strong>{detail.publication.pointer ? `pointer ${detail.publication.pointer}` : 'no published pointer'} · Staging: {detail.publication.staging_ref || 'not recorded'}. {detail.publication.meaning}</p>}
      {detail.frozen_preparation && <details open><summary>Recorded preparation, capacity and context</summary><pre>{json(detail.frozen_preparation)}</pre></details>}
      {detail.attempts && <><table><thead><tr><th>Attempt</th><th>Status</th><th>Observed success-body bytes</th><th>Recorded usage</th></tr></thead><tbody>{detail.attempts.map(item => <tr key={item.id}><td><code>{item.id}</code></td><td>{observed(field(item.record, 'status')) || item.status}</td><td>{observed(field(field(item.record, 'transport'), 'received_body_bytes')) ?? 'unknown'}</td><td>{item.usage_state === 'not_sent' ? 'No inference (unsent)' : `${item.usage_state}: ${json(field(item.record, 'usage') ?? null)}`}</td></tr>)}</tbody></table><details><summary>Attempts, receive boundaries and reported usage</summary><pre>{json(detail.attempts)}</pre></details></>}
      {detail.usage_comparison && <p><strong>Usage comparison: </strong>{detail.usage_comparison}</p>}
      {detail.raw_usage && <details><summary>Reported and derived usage (separate from settlement)</summary><pre>{json(detail.raw_usage)}</pre></details>}
      {detail.saved_acceptance_facts && <details><summary>Saved acceptance facts and usage provenance</summary><pre>{json(detail.saved_acceptance_facts)}</pre></details>}
      {detail.effect && <p><strong>Effect: </strong>{detail.effect}</p>}
      {detail.execution_history && <p>{detail.execution_history}</p>}
      {detail.origin && <p><strong>Origin: </strong>{detail.origin} · Parent {detail.record.parent ?? observed(field(detail.result, 'parent')) ?? 'none / unknown'}</p>}
      {detail.request_association && <p><strong>Request association: </strong>{detail.request_association.status} · {detail.request_association.publication || detail.request_association.reason}. {detail.request_association.meaning || ''}</p>}
      {detail.unconfirmed_operations?.map(op => <p key={op.id}><strong>Unconfirmed operation association: </strong><code>{op.id}</code> · {op.reason}</p>)}
      {detail.verification && <p>{detail.verification}</p>}
      {detail.projection && <p>{detail.projection}</p>}
      <div className="diagnostic-toolbar">
        {detail.request && <button disabled={busy || stale} onClick={() => { if (detail.request) void openRecord('request', detail.request) }}>Open linked request</button>}
        {detail.version && <button disabled={busy || stale} onClick={() => { if (detail.version) void openRecord('version', detail.version) }}>Open committed version</button>}
        {detail.operations?.map(op => <React.Fragment key={op.id}><button disabled={busy || stale} onClick={() => void openRecord('operation', op.id)}>Open operation {op.id} ({op.origin})</button>{op.publication && <span>{op.publication} · recorded call relationship; acceptance and readiness not inferred</span>}</React.Fragment>)}
        {detail.related?.map(item => <button key={item.id} disabled={busy || stale} onClick={() => void openRecord(item.kind, item.id)}>Open {item.kind} {item.id}</button>)}
      </div>
      {detail.related && <details open><summary>Explicit context / handoff / resolution links</summary><pre>{json(detail.related)}</pre></details>}
      {detail.events && <details><summary>Related recorded events (not a complete effects log)</summary><pre>{json(detail.events)}</pre></details>}
      {detail.links?.map((link, index) => <div className="diagnostic-link" key={`${link.ref}-${index}`}><code>{link.ref}</code><p>{link.status} · Artifact owner attempt: {link.status === 'unavailable' ? 'unconfirmed' : link.facts.attempt || 'not applicable / unknown'} · {link.status === 'unavailable' ? link.reason : link.facts.relation || ''}</p>{['full', 'raw', 'index'].map(view => <button key={view} disabled={busy || stale || link.status === 'unavailable' || !link.facts} onClick={() => void openEvidence(link.ref, view)}>Open {view} {link.ref}</button>)}{link.raw_descriptor !== undefined && <details><summary>Raw descriptor observation (not verified facts)</summary><pre>{json(link.raw_descriptor)}</pre></details>}</div>)}
      <details><summary>Complete selected catalog record</summary><pre>{json(detail.record)}</pre></details>
      {detail.limitations?.map(text => <p className="hint" key={text}>{text}</p>)}
      {detail.limitation && <p role="alert">{detail.limitation}</p>}
    </section>}
    {selectedRef && <form className="diagnostic-selectors" onSubmit={e => { e.preventDefault(); void openEvidence(selectedRef, mode, true) }}>
      <p>Exact evidence selection: <code>{selectedRef}</code>. Empty selectors request the complete representation. Ranges are zero-based and half-open; raw uses bytes, decoded strings use Unicode characters.</p>
      <label>Representation<select value={mode} onChange={e => setMode(e.target.value)}><option>full</option><option>raw</option><option>index</option></select></label>
      <label>JSON Pointer<input value={pointer} onChange={e => setPointer(e.target.value)} /></label><label>Range start<input type="number" min="0" value={start} onChange={e => setStart(e.target.value)} /></label><label>Range end<input type="number" min="0" value={end} onChange={e => setEnd(e.target.value)} /></label><button disabled={busy || stale}>Read exact selection</button>
    </form>}
    {evidence && <section aria-label="Diagnostic evidence" className="diagnostic-evidence"><p>Coverage is reported in the response below; index is metadata only. Full/raw access is available above.</p>{evidence.url && <img src={evidence.url} alt="Exact saved diagnostic image" />}<pre>{json(evidence)}</pre></section>}
  </section>
}
