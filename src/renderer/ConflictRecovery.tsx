import React, { useEffect, useState } from 'react'

type Diagnosis = {
  status: string; eligible: boolean; reasons: string[]; job?: string; request?: string; attempt?: string;
  basis?: string; head?: string | null; versions?: string[]; resolution_ref?: string; projection?: string;
  accepted_staging_ref?: string; native_ref?: string; stream_ref?: string; original_usage?: unknown; saved_usage?: unknown;
  storage?: { status: string }; provenance?: { status: string }; reconstruction?: { status: string };
  receive_boundary?: { status: string; reason?: string }; publication?: { status: string; accepted_ref?: string | null };
  effects?: { status: string; operations?: { operation: string; certainty: string; prior_skipping: boolean }[] };
  preparation?: { status: string; candidate_refs: string[]; authoritative: false };
}

const labels: Record<string, string> = {
  verified: 'Verified', matches: 'Matches saved native response', unknown: 'Not established',
  finish_conflict: 'Saved terminal response has an unfinished received tail', compatible: 'Compatible with the current receive rule',
  feed_error: 'Unsupported error while replaying received data', published: 'Original accepted pointer exists', unpublished: 'Acceptance was not published',
  established: 'All effects established', completed: 'Completed and retained', not_started: 'Not started',
  verified_at_resolution: 'Verified in the saved resolution',
  evidence_unconfirmed: 'Evidence needs investigation', missing_graph: 'Saved graph unavailable', unsupported_schema: 'Saved schema unsupported',
  busy: 'Task is busy', stale_view: 'Task changed; refresh the diagnosis', unsupported: 'Local recovery is unavailable for this case',
  missing_staging: 'Complete acceptance staging is unavailable', no_resumable_request: 'No current request to recover',
  eligible: 'Local recovery is available', resolved: 'Local recovery decision saved',
}
const text = (value?: string) => value ? labels[value] ?? value : 'Not established'

export function ConflictRecovery({ job, running, refresh, viewEvidence }: {
  job: string; running: boolean; refresh: () => Promise<void>; viewEvidence: (ref: string, raw?: boolean) => void
}) {
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setDiagnosis(null); setError('') }, [job])
  const inspect = async () => {
    setBusy(true); setError('')
    try { setDiagnosis(await window.workbench.invoke('diagnoseConflict', { job })) }
    catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }
  const resolve = async () => {
    if (!diagnosis?.request) return
    setBusy(true); setError('')
    try {
      const result = await window.workbench.invoke('resolveConflict', { job, request: diagnosis.request, basis: diagnosis.basis ?? '' })
      setDiagnosis({ ...diagnosis, ...result, eligible: false, status: 'resolved', reasons: [] })
      await refresh()
    } catch (e) {
      setError(String(e))
      // A timeout may follow a committed decision. Refresh exposes that same decision.
      try { setDiagnosis(await window.workbench.invoke('diagnoseConflict', { job })) } catch { /* Keep the last observed facts. */ }
    } finally { setBusy(false) }
  }
  return <section className="conflict-recovery" aria-label="Saved acceptance recovery">
    <button disabled={running || busy} onClick={() => void inspect()}>Inspect saved acceptance</button>
    {diagnosis && <div aria-live="polite">
      <h3>{text(diagnosis.status)}</h3>
      <p>Diagnosis and local recovery send no model request. Saved versions remain available for review and export.</p>
      {diagnosis.request && <p className="hint">Request: <code>{diagnosis.request}</code>{diagnosis.attempt && <> · Attempt: <code>{diagnosis.attempt}</code></>}</p>}
      <dl>{(['storage', 'provenance', 'reconstruction', 'receive_boundary', 'publication', 'effects'] as const).map(key =>
        diagnosis[key] && <React.Fragment key={key}><dt>{({ storage: 'Saved bytes', provenance: 'Source links', reconstruction: 'Native reconstruction', receive_boundary: 'Receive rule', publication: 'Original publication', effects: 'Tool effects' })[key]}</dt><dd>{text(diagnosis[key]?.status)}</dd></React.Fragment>)}</dl>
      {diagnosis.receive_boundary?.reason && <p>{diagnosis.receive_boundary.reason}</p>}
      {diagnosis.reasons?.map((reason, i) => <p key={i}>{reason}</p>)}
      {diagnosis.status !== 'resolved' && diagnosis.preparation?.status === 'uncommitted_candidates' && <p>Earlier local recovery candidates were saved, but no recovery decision was committed. They have no execution effect; selecting recovery will validate the current task again.</p>}
      {diagnosis.effects?.operations?.map(op => <p className="hint" key={op.operation}><code>{op.operation}</code>: {text(op.certainty)}{op.prior_skipping ? ' (earlier skip intent retained)' : ''}</p>)}
      {diagnosis.versions && <p>{diagnosis.versions.length} retained saved version(s). Current head: <code>{diagnosis.head ?? 'empty'}</code></p>}
      {diagnosis.accepted_staging_ref && <details><summary>Evidence references and usage</summary>
        <p>Staging: <button className="text-button" aria-label="Open acceptance staging" onClick={() => viewEvidence(diagnosis.accepted_staging_ref!)}>{diagnosis.accepted_staging_ref}</button></p>
        {diagnosis.native_ref && <p>Native: <button className="text-button" aria-label="Open native response" onClick={() => viewEvidence(diagnosis.native_ref!)}>{diagnosis.native_ref}</button></p>}
        {diagnosis.stream_ref && <p>Raw stream: <button className="text-button" aria-label="Open complete raw bytes" onClick={() => viewEvidence(diagnosis.stream_ref!, true)}>{diagnosis.stream_ref}</button></p>}
        <p>Original recorded usage: {JSON.stringify(diagnosis.original_usage ?? 'unknown')}. Saved reply usage: {JSON.stringify(diagnosis.saved_usage ?? 'unknown')}.</p>
      </details>}
      {diagnosis.eligible && <><p>Preserve proven completed effects, record unstarted calls as not executed, and prepare a new planning boundary. Uncommitted context choices require explicit agent reselection.</p>
        <button disabled={busy || running} onClick={() => void resolve()}>Preserve work and prepare to re-plan</button></>}
      {diagnosis.status === 'resolved' && <>
        <p>Resolution: <button className="text-button" aria-label="Open saved resolution" onClick={() => viewEvidence(diagnosis.resolution_ref!)}>{diagnosis.resolution_ref}</button></p>
        {diagnosis.projection === 'ready' ? <p role="status">Local recovery is ready. Review or export saved work, add instructions if needed, then use the separate Continue button. The original stop record is retained.</p>
          : diagnosis.projection === 'pending' ? <><p>Local decision committed; graph projection is pending. This task is not yet ready to continue.</p><button disabled={busy || running} onClick={() => void resolve()}>Finish this local recovery</button></>
            : <p>Local decision retained; graph projection cannot be confirmed safely. Review the explanation before continuing.</p>}
      </>}
    </div>}
    {error && <p role="alert" className="error">{error}</p>}
  </section>
}
