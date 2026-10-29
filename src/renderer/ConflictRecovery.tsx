import React, { useEffect, useRef, useState } from 'react'

type Diagnosis = {
  status: string; eligible: boolean; reasons: string[]; job?: string; request?: string; attempt?: string;
  basis?: string; head?: string | null; head_verification?: string; versions?: string[]; resolution_ref?: string; projection?: string;
  accepted_staging_ref?: string; native_ref?: string; stream_ref?: string; original_usage?: unknown; saved_usage?: unknown;
  original_usage_state?: string; saved_usage_state?: string; original_failure?: unknown;
  subject?: { kind: string }; original_request_status?: string; original_attempt_status?: string; original_finish?: unknown;
  resolution_head?: string | null;
  verification?: { original?: string; saved?: string; raw?: string; operations?: string };
  evidence_availability?: Record<string, { status: string; reason?: string }>;
  historical_resolutions?: { request: string; resolution_ref?: string; projection?: string; verification?: string; reason?: string }[];
  storage?: { status: string }; provenance?: { status: string }; reconstruction?: { status: string };
  receive_boundary?: { status: string; reason?: string }; publication?: { status: string; accepted_ref?: string | null };
  effects?: { status: string; operations?: { operation: string; certainty: string; prior_skipping: boolean; candidate_ref?: string; result_ref?: string }[] };
  preparation?: { status: string; candidate_refs: string[]; authoritative: false };
}

const labels: Record<string, string> = {
  verified: 'Verified', matches: 'Matches saved native response', unknown: 'Not established',
  finish_conflict: 'Saved terminal response has an unfinished received tail', compatible: 'Compatible with the current receive rule',
  feed_error: 'Unsupported error while replaying received data', published: 'Original accepted pointer exists', unpublished: 'Acceptance was not published',
  established: 'All effects established', completed: 'Completed and retained', not_started: 'Not started',
  verified_at_resolution: 'Verified in the saved resolution',
  checked_now: 'Checked in this inspection', unavailable: 'Unavailable', inconsistent: 'Inconsistent evidence',
  current_request: 'Current request', recovery_boundary: 'Current local recovery boundary', none: 'No current recovery subject',
  evidence_unconfirmed: 'Evidence needs investigation', missing_graph: 'Saved graph unavailable', unsupported_schema: 'Saved schema unsupported',
  busy: 'Task is busy', stale_view: 'Task changed; refresh the diagnosis', unsupported: 'Local recovery is unavailable for this case',
  missing_staging: 'Complete acceptance staging is unavailable', no_resumable_request: 'No current request to recover',
  eligible: 'Local recovery is available', resolved: 'Local recovery decision saved',
}
const text = (value?: string) => value ? labels[value] ?? value : 'Not established'
const usage = (value: unknown, state?: string) => state === 'unavailable' || value === undefined ? 'unavailable'
  : state === 'unknown' || value === null ? 'unknown' : JSON.stringify(value)

export function ConflictRecovery({ job, running, observation = '', refresh, viewEvidence }: {
  job: string; running: boolean; observation?: string; refresh: () => Promise<void>; viewEvidence: (ref: string, raw?: boolean) => void
}) {
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [stale, setStale] = useState(false)
  const generation = useRef(0)
  const [observed, setObserved] = useState({ job, running, observation })
  const observationChanged = observed.job === job && (observed.running !== running || observed.observation !== observation)
  const staleView = stale || observationChanged || running
  useEffect(() => {
    generation.current += 1
    setDiagnosis(null); setError(''); setStale(false); setBusy(false)
    return () => { generation.current += 1 }
  }, [job])
  useEffect(() => {
    if (observed.job === job && observed.running === running && observed.observation === observation) return
    setObserved({ job, running, observation })
    if (observed.job === job) {
      // Job polling supplies only a small change signal. It never performs
      // an evidence audit, and cannot certify the older inspection as current.
      generation.current += 1
      setStale(true); setBusy(false)
    }
  }, [job, running, observation, observed])
  const inspect = async () => {
    const current = generation.current
    setBusy(true); setError('')
    try {
      const result = await window.workbench.invoke('diagnoseConflict', { job })
      if (generation.current === current) { setDiagnosis(result); setStale(false) }
    } catch (e) {
      if (generation.current === current) { setError(String(e)); setStale(true) }
    } finally { if (generation.current === current) setBusy(false) }
  }
  const resolve = async () => {
    if (!diagnosis?.request || staleView || busy) return
    const current = generation.current
    setBusy(true); setError('')
    let mutationError = ''
    try {
      await window.workbench.invoke('resolveConflict', { job, request: diagnosis.request, basis: diagnosis.basis ?? '' })
    } catch (e) { mutationError = String(e) }
    if (generation.current !== current) return
    // Both a successful response and a timeout-after-commit need authoritative
    // facts. A mutation acknowledgement is not a complete fresh diagnosis.
    try {
      const result = await window.workbench.invoke('diagnoseConflict', { job })
      if (generation.current !== current) return
      setDiagnosis(result); setStale(false)
      if (mutationError) setError(mutationError)
    } catch (e) {
      if (generation.current !== current) return
      setStale(true)
      setError([mutationError, `Diagnosis refresh failed: ${String(e)}`].filter(Boolean).join(' '))
    }
    try { await refresh() }
    catch (e) { if (generation.current === current) setError(previous => [previous, `Task refresh failed: ${String(e)}`].filter(Boolean).join(' ')) }
    finally { if (generation.current === current) setBusy(false) }
  }
  const evidenceLink = (ref: string, label: string, raw = false, availability?: { status: string; reason?: string }) => {
    const available = availability ?? diagnosis?.evidence_availability?.[ref]
    return <><button className="text-button" aria-label={label} disabled={available?.status === 'unavailable' || available?.status === 'inconsistent'} onClick={() => viewEvidence(ref, raw)}>{ref}</button>
      {available && available.status !== 'available' && <span> — {text(available.status)}{available.reason && `: ${available.reason}`}</span>}</>
  }
  return <section className="conflict-recovery" aria-label="Saved acceptance recovery">
    <button disabled={running || busy} onClick={() => void inspect()}>Inspect saved acceptance</button>
    {diagnosis && <div aria-live="polite">
      <h3>{text(diagnosis.status)}</h3>
      {staleView && <p role="alert">Stale diagnosis: the last observed facts are retained. Inspect again before selecting local recovery.</p>}
      <p>Diagnosis and local recovery send no model request. Saved versions remain available for review and export.</p>
      {diagnosis.subject && <p>{text(diagnosis.subject.kind)}</p>}
      {diagnosis.request && <p className="hint">Request: <code>{diagnosis.request}</code>{diagnosis.attempt && <> · Attempt: <code>{diagnosis.attempt}</code></>}</p>}
      <dl>{(['storage', 'provenance', 'reconstruction', 'receive_boundary', 'publication', 'effects'] as const).map(key =>
        diagnosis[key] && <React.Fragment key={key}><dt>{({ storage: 'Saved bytes', provenance: 'Source links', reconstruction: 'Native reconstruction', receive_boundary: 'Receive rule', publication: 'Original publication', effects: 'Tool effects' })[key]}</dt><dd>{text(diagnosis[key]?.status)}</dd></React.Fragment>)}</dl>
      {diagnosis.receive_boundary?.reason && <p>{diagnosis.receive_boundary.reason}</p>}
      {diagnosis.reasons?.map((reason, i) => <p key={i}>{reason}</p>)}
      {diagnosis.status !== 'resolved' && diagnosis.preparation?.status === 'uncommitted_candidates' && <p>Earlier local recovery candidates were saved, but no recovery decision was committed. They have no execution effect; selecting recovery will validate the current task again.</p>}
      {(diagnosis.original_request_status || diagnosis.original_attempt_status || Object.hasOwn(diagnosis, 'original_finish')) && <p className="hint">Original request status: {text(diagnosis.original_request_status)}. Original attempt status: {text(diagnosis.original_attempt_status)}. Original finish: {usage(diagnosis.original_finish)}.</p>}
      {diagnosis.original_failure != null && <p className="hint">Original failure: {JSON.stringify(diagnosis.original_failure)}</p>}
      {diagnosis.effects?.operations?.map(op => <div className="hint" key={op.operation}><p><code>{op.operation}</code>: {text(op.certainty)}{op.prior_skipping ? ' (earlier skip intent retained)' : ''}</p>
        {op.candidate_ref && <p>Candidate: {evidenceLink(op.candidate_ref, `Open candidate ${op.operation}`)}</p>}
        {op.result_ref && <p>Result: {evidenceLink(op.result_ref, `Open result ${op.operation}`)}</p>}
      </div>)}
      {diagnosis.versions && <p>{diagnosis.versions.length} retained saved version(s). Current head: <code>{diagnosis.head ?? 'empty'}</code></p>}
      {diagnosis.head_verification && <p className="hint">Current head verification: {text(diagnosis.head_verification)}.</p>}
      {Object.hasOwn(diagnosis, 'resolution_head') && <p>Head observed at resolution: <code>{diagnosis.resolution_head ?? 'empty'}</code> (historical).</p>}
      {(diagnosis.request || diagnosis.accepted_staging_ref) && <details><summary>Evidence references and usage</summary>
        {diagnosis.accepted_staging_ref && <p>Staging: {evidenceLink(diagnosis.accepted_staging_ref, 'Open acceptance staging')}</p>}
        {diagnosis.native_ref && <p>Native: {evidenceLink(diagnosis.native_ref, 'Open native response')}</p>}
        {diagnosis.stream_ref && <p>Raw stream: {evidenceLink(diagnosis.stream_ref, 'Open complete raw bytes', true)}</p>}
        <p>Original recorded usage: {usage(diagnosis.original_usage, diagnosis.original_usage_state)}. Saved reply usage: {usage(diagnosis.saved_usage, diagnosis.saved_usage_state)}.</p>
        {diagnosis.verification && <div className="hint">
          <p>Original facts verification: {text(diagnosis.verification.original)}. Saved reply verification: {text(diagnosis.verification.saved)}.</p>
          <p>Raw stream verification: {text(diagnosis.verification.raw)}. Operation verification: {text(diagnosis.verification.operations)}.</p>
        </div>}
      </details>}
      {diagnosis.eligible && <><p>Preserve proven completed effects, record unstarted calls as not executed, and prepare a new planning boundary. Uncommitted context choices require explicit agent reselection.</p>
        <button disabled={busy || staleView} onClick={() => void resolve()}>Preserve work and prepare to re-plan</button></>}
      {diagnosis.status === 'resolved' && <>
        {diagnosis.resolution_ref && <p>Resolution: {evidenceLink(diagnosis.resolution_ref, 'Open saved resolution')}</p>}
        {staleView ? <p>Current projection and readiness need a fresh inspection.</p> : diagnosis.projection === 'ready' ? <p role="status">Local recovery is ready. Review or export saved work, add instructions if needed, then use the separate Continue button. The original stop record is retained.</p>
          : diagnosis.projection === 'pending' ? <><p>Local decision committed; graph projection is pending. This task is not yet ready to continue.</p><button disabled={busy || staleView} onClick={() => void resolve()}>Finish this local recovery</button></>
            : <p>Local decision retained; graph projection cannot be confirmed safely. Review the explanation before continuing.</p>}
      </>}
      {!!diagnosis.historical_resolutions?.length && <details><summary>Historical local recovery decisions</summary><p>These earlier decisions do not establish current readiness.</p>
        {diagnosis.historical_resolutions.map(item => <p key={item.request}>Historical request: <code>{item.request}</code>{item.resolution_ref && <> · {evidenceLink(item.resolution_ref, `Open historical resolution ${item.request}`, false,
          item.verification === 'unavailable' ? { status: 'unavailable', reason: item.reason } : undefined)}</>} · Verification: {text(item.verification)}{item.projection && <> · Recorded projection: {text(item.projection)}</>}{item.reason && item.verification !== 'unavailable' && <> · {item.reason}</>}</p>)}
      </details>}
    </div>}
    {error && <p role="alert" className="error">{error}</p>}
  </section>
}
