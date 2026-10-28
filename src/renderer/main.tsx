import React, { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import type { Job, Limits, Route, Settings } from './types'
import { useDocumentSession } from './useDocumentSession'
import { TaskSettings } from './TaskSettings'
import { initialWaitPolicy, WaitingSettings } from './WaitingSettings'
import { ReceiveProgress } from './ReceiveProgress'
import { ConflictRecovery } from './ConflictRecovery'
import './style.css'

const api = window.workbench.invoke
const statusNames: Record<string, string> = { ready: 'Ready to convert', running: 'Working', completed: 'Completed', paused: 'Paused', waiting: 'Needs your input', blocked: 'Needs attention', cancelled: 'Stopped', interrupted: 'Interrupted' }
const defaults: Route = { endpoint: '', model: '', protocol: 'chat_completions', context_tokens: 131072, output_tokens: 8192, image_tokens: 4096, vision: false, timeout_seconds: 180, wait_policy: initialWaitPolicy, parameters: {} }
const defaultLimits: Limits = { max_requests: 80, max_active_seconds: 7200, replay_unknown: false, max_attempts_per_request: 1, max_response_repairs: 2 }

function Icon({ name, size = 20 }: { name: 'plus' | 'file' | 'settings' | 'arrow' | 'download' | 'stop' | 'close' | 'book'; size?: number }) {
  const paths = { plus: 'M12 5v14M5 12h14', file: 'M14 3H5v18h14V8l-5-5ZM14 3v5h5M8 12h8M8 16h6', settings: 'M4 7h16M4 17h16M8 4v6M16 14v6', arrow: 'm9 5 7 7-7 7', download: 'M12 3v12m-5-5 5 5 5-5M5 16v5h14v-5', stop: 'M6 6h12v12H6Z', close: 'm6 6 12 12M18 6 6 18', book: 'M12 5c-4-3-9-2-9-2v16s5-1 9 2c4-3 9-2 9-2V3s-5-1-9 2Zm0 0v16' }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}

function Connection({ initial, close, onSave }: { initial: Settings; close: () => void; onSave: (settings: Settings) => void }) {
  const [route, setRoute] = useState<Route>({ ...defaults, ...initial.route,
    wait_policy: initial.route ? initial.route.wait_policy : { ...initialWaitPolicy } })
  const [limits, setLimits] = useState<Limits>({ ...defaultLimits, ...initial.limits })
  const [key, setKey] = useState('')
  const [remember, setRemember] = useState(initial.remember ?? true)
  const [parameters, setParameters] = useState(JSON.stringify(route.parameters, null, 2))
  const [error, setError] = useState('')
  const field = (name: keyof Route, value: unknown) => setRoute(r => ({ ...r, [name]: value }))
  return <div className="overlay"><form className="modal connection" onSubmit={async e => {
    e.preventDefault(); setError('')
    try {
      const value = await api<Settings>('saveSettings', { route: { ...route, parameters: JSON.parse(parameters) }, limits, key, remember })
      onSave(value); close()
    } catch (e) { setError(String(e)) }
  }}>
    <div className="modal-heading"><div><span className="eyebrow">MODEL ACCESS</span><h2>Nexus connection</h2></div><button className="icon-button" type="button" onClick={close} aria-label="Close settings"><Icon name="close" /></button></div>
    <p className="muted">Use the endpoint and model from your Nexus subscription connector.</p>
    <label>Full endpoint URL<input required type="url" placeholder="https://your-nexus-host/v1/chat/completions" value={route.endpoint} onChange={e => field('endpoint', e.target.value)} /></label>
    <div className="form-row"><label>Protocol<select value={route.protocol} onChange={e => field('protocol', e.target.value)}><option value="chat_completions">Chat Completions</option><option value="responses">Responses</option></select></label><label>Model alias<input required placeholder="Your Nexus model alias" value={route.model} onChange={e => field('model', e.target.value)} /></label></div>
    <label>Nexus credential<input type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)} placeholder={initial.hasKey ? 'Saved credential — leave blank to keep' : 'Enter credential'} /></label>
    <label className="check"><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />Remember with operating-system encryption</label>
    {initial.encryptionAvailable === false && <p className="hint">Encryption is unavailable. The credential stays in memory for this session.</p>}
    <details open><summary>Context and execution limits</summary><p className="hint">Set the effective limits for this Nexus route. These starter values are not verified model specifications.</p>
      <div className="form-row"><label>Context capacity<input type="number" min="2048" required value={route.context_tokens} onChange={e => field('context_tokens', Number(e.target.value))} /></label><label>Output reserve<input type="number" min="256" required value={route.output_tokens} onChange={e => field('output_tokens', Number(e.target.value))} /></label></div>
      <label className="check"><input type="checkbox" checked={route.vision} onChange={e => field('vision', e.target.checked)} />This route accepts image inputs</label>
      {route.vision && <label>Conservative token allowance per image<input type="number" required min="1" value={route.image_tokens ?? ''} onChange={e => field('image_tokens', Number(e.target.value))} /></label>}
      <div className="form-row"><label>Maximum model requests<input type="number" min="1" value={limits.max_requests} onChange={e => setLimits(l => ({ ...l, max_requests: Number(e.target.value) }))} /></label><label>Active time limit (minutes)<input type="number" min="1" value={limits.max_active_seconds / 60} onChange={e => setLimits(l => ({ ...l, max_active_seconds: Number(e.target.value) * 60 }))} /></label></div>
      <WaitingSettings value={route.wait_policy} deadline={route.timeout_seconds} onChange={value => field('wait_policy', value)} onDeadline={value => field('timeout_seconds', value)} legacyLabel="Request timeout (seconds)" />
    </details>
    <details><summary>Optional recovery and model parameters</summary><p className="hint">Limits remain in force after resume. An interrupted request can have unknown upstream usage.</p>
      <label>Automatic response corrections<input type="number" min="0" value={limits.max_response_repairs} onChange={e => setLimits(l => ({ ...l, max_response_repairs: Number(e.target.value) }))} /></label>
      <p className="hint">Correct text-only continuations or invalid handoffs before asking for attention. Corrections use the task's request budget. Zero disables them.</p>
      <label className="check"><input type="checkbox" checked={limits.replay_unknown} onChange={e => setLimits(l => ({ ...l, replay_unknown: e.target.checked, max_attempts_per_request: e.target.checked ? 2 : 1 }))} />Allow bounded replay after an unknown outcome</label>
      {limits.replay_unknown && <label>Maximum attempts per request<input type="number" min="1" max="10" value={limits.max_attempts_per_request} onChange={e => setLimits(l => ({ ...l, max_attempts_per_request: Number(e.target.value) }))} /></label>}
      <label>Additional native parameters (JSON)<textarea rows={3} value={parameters} onChange={e => setParameters(e.target.value)} /></label>
    </details>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="modal-footer"><span className="hint">Defaults for unconfigured tasks. Use Task limits to adjust an existing task.</span><button className="primary" type="submit">Save connection</button></div>
  </form></div>
}

function App() {
  const [ready, setReady] = useState(false)
  const [settings, setSettings] = useState<Settings>({})
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsJob, setSettingsJob] = useState<Job | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [page, setPage] = useState(1)
  const [pageUrl, setPageUrl] = useState('')
  const [tab, setTab] = useState('preview')
  const [amendment, setAmendment] = useState('')
  const [scripts, setScripts] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [importName, setImportName] = useState('')
  const [scope, setScope] = useState('Convert the complete document, preserving substantive text, tables, footnotes, and source images.')
  const { version, saved, editing, loadError, selectVersion, beginEdit, changeBlock, finishEdit, discardEdit, retryLoad } = useDocumentSession(job?.id === active ? job : null)
  const [evidence, setEvidence] = useState<any>(null)
  const [activityOpen, setActivityOpen] = useState(false)
  const refresh = useRef<() => Promise<void>>(async () => {})

  useEffect(() => { void api<Settings>('settings').then(setSettings) }, [])
  useEffect(() => {
    let alive = true, pending = false
    const load = async () => {
      if (pending) return
      pending = true
      try {
        const health = await api('health')
        if (!alive) return
        setReady(health.ready)
        if (health.error) setError(health.error)
        if (health.ready) {
          const list = await api<Job[]>('jobs')
          if (!alive) return
          setJobs(list)
          if (active) {
            const detail = await api<Job>('job', { job: active })
            if (alive) setJob(detail)
          }
        }
      } catch (error) { if (alive) setError(String(error)) }
      finally { pending = false }
    }
    refresh.current = load
    void load(); const timer = setInterval(load, 1500)
    return () => { alive = false; clearInterval(timer) }
  }, [active])
  useEffect(() => {
    setPage(1); setPageUrl(''); setEvidence(null); setJob(null)
    setError(''); setNotice(''); setAmendment('')
  }, [active])
  useEffect(() => {
    if (!active) return
    let alive = true; setPageUrl('')
    void api('page', { job: active, page }).then(value => { if (alive) setPageUrl(value.url) }).catch(e => { if (alive) setError(String(e)) })
    return () => { alive = false }
  }, [active, page])

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setError(''); setNotice('')
    try { await fn(); await refresh.current() } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  const choose = () => act(async () => { const file = await api('choosePdf'); if (file) setImportName(file.name) })
  const select = (id: string) => { if (id !== active) setActive(id) }
  const running = Boolean(job?.running)
  const recoveryRequest = !running ? job?.compaction_recovery?.request : undefined
  const latestCapacity = job?.requests?.at(-1)?.capacity
  const latestRequest = job?.requests?.at(-1)
  const unmeasuredIntervals = (job?.active_time_gaps?.length || 0) + (job?.active_since != null && !running ? 1 : 0)
  const continueTask = (recover_compaction_request?: string) => {
    if (!settings.hasKey || !settings.route?.model) { setSettingsOpen(true); return }
    void act(async () => {
      await api('start', { job: active, amendment, scripts, recover_compaction_request })
      setAmendment('')
    })
  }

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><span className="brand-icon"><Icon name="book" size={22} /></span><div>PDF <strong>Workbench</strong><small>MARKDOWN EDITION</small></div></div>
      <button className="new-document" onClick={choose} disabled={!ready || busy || Boolean(editing)}><Icon name="plus" />New document</button>
      <div className="section-label">YOUR DOCUMENTS <span>{jobs.length}</span></div>
      <nav className="document-list" aria-label="Documents">{jobs.map(item => <button className={`document-item ${active === item.id ? 'selected' : ''}`} disabled={busy || Boolean(editing)} onClick={() => select(item.id)} key={item.id}>
        <Icon name="file" /><span><strong>{item.name}</strong><small><i className={`dot ${item.status}`} />{statusNames[item.status] || item.status}</small></span>
      </button>)}{jobs.length === 0 && <p className="sidebar-hint">Your documents and saved versions will appear here.</p>}</nav>
      <div className="sidebar-bottom"><button className="connection-button" onClick={() => setSettingsOpen(true)}><Icon name="settings" /><span>Nexus connection<small>{settings.route?.model || 'Choose your model'}</small></span><Icon name="arrow" size={14} /></button>
        <div className="engine-state"><i className={`dot ${ready ? 'completed' : 'paused'}`} />{ready ? 'Local engine ready' : 'Starting local engine…'}<span>v0.1</span></div>
      </div>
    </aside>
    <main className="main">
      {!active ? <>
        <header className="topbar"><span className="breadcrumb">WORKSPACE</span><span className="local-badge">Saved on this device</span></header>
        <section className="welcome">
          <div className="paper-stack"><div className="paper back" /><div className="paper front"><span>PDF</span><i /><i /><i /><b>↗</b></div><div className="md-badge">M↓</div></div>
          <span className="eyebrow">FROM SOURCE TO SOMETHING USEFUL</span><h1>Your documents.<br />Ready for what comes next.</h1>
          <p>Turn PDFs into readable, reusable Markdown.<br />Keep the details, the source images, and every saved version.</p>
          <button className="primary large" onClick={choose} disabled={!ready || busy}><Icon name="plus" />Choose a PDF</button>
          <span className="welcome-note">Native, scanned, or mixed documents</span>
          <div className="welcome-features"><div><span>01</span><strong>Give it a scope</strong><p>A whole document or a complete section.</p></div><div><span>02</span><strong>Let the agent work</strong><p>Read, extract, and reconstruct with Nexus.</p></div><div><span>03</span><strong>Keep useful work</strong><p>Review and export any saved version.</p></div></div>
        </section>
      </> : <>
        <header className="topbar"><div className="document-heading"><span className="breadcrumb">DOCUMENT WORKSPACE</span><h1>{job?.name || 'Opening document…'}</h1></div><div className="header-actions"><span className={`status ${job?.status || ''}`}><i className={`dot ${job?.status || ''}`} />{statusNames[job?.status || ''] || 'Loading'}</span><button className="primary" disabled={!saved || busy} onClick={() => act(async () => {
          if (!saved) return
          const result = await api('export', { job: saved.job, version: saved.version, name: job?.name }); if (result) setNotice(`Exported ${result.claim === 'complete' ? 'completed version' : 'partial draft'} to ${result.path}`)
        })}><Icon name="download" size={17} />Export ZIP</button></div></header>
        <div className="scope-bar"><span>SCOPE</span><p>{job?.scope}</p></div>
        <div className="reading-area">
          <section className="panel source-panel"><div className="panel-toolbar"><span className="panel-title"><Icon name="file" size={17} />Source PDF</span><div className="page-picker"><button aria-label="Previous page" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>‹</button><label><input aria-label="Physical page" type="number" min="1" max={job?.page_count || 1} value={page} onChange={e => { const p = Number(e.target.value); if (p >= 1 && p <= (job?.page_count || 1)) setPage(p) }} /><span>/ {job?.page_count || '—'}</span></label><button aria-label="Next page" disabled={page >= (job?.page_count || 1)} onClick={() => setPage(p => p + 1)}>›</button></div></div>
            <div className="pdf-canvas">{pageUrl ? <img src={pageUrl} alt={`Source PDF physical page ${page}`} /> : <span className="loading">Rendering source page…</span>}</div><div className="panel-footnote">Physical page {page} · Source retained unchanged</div>
          </section>
          <section className="panel output-panel"><div className="panel-toolbar"><div className="tabs">{['preview', 'markdown', 'evidence'].map(name => <button key={name} className={tab === name ? 'active' : ''} onClick={() => setTab(name)}>{name[0].toUpperCase() + name.slice(1)}</button>)}</div>
            {job?.versions?.length ? <select aria-label="Saved version" value={version} disabled={busy || Boolean(editing)} onChange={e => selectVersion(e.target.value)}>{job.versions.map((v, i) => <option key={v.id} value={v.id}>{i === 0 ? 'Latest' : `Version ${job.versions!.length - i}`} · {v.claim} · {v.id.slice(0, 6)}</option>)}</select> : <span className="muted small">No saved version</span>}</div>
            {tab === 'evidence' ? <div className="evidence-view"><div className="evidence-list">{job?.evidence?.map(item => <button key={item.ref} onClick={() => act(async () => setEvidence(await api('evidence', { job: active, ref: item.ref })))}><span className="tag">{item.kind.replace('_', ' ')}</span><code>{item.ref.slice(0, 18)}</code><small>{(item.bytes / 1024).toFixed(1)} KB</small></button>)}{!job?.evidence?.length && <p className="muted">Source reads and retained candidates will appear here.</p>}</div>{evidence && <div className="evidence-detail">{evidence.url ? <img src={evidence.url} alt="Saved evidence" /> : <pre>{JSON.stringify(evidence, null, 2)}</pre>}</div>}</div>
              : editing ? <div className="block-editor"><p className="hint">{editing.mode === 'rebuild' ? 'Rebuilding from' : 'Editing'} saved version {editing.baseVersion.slice(0, 6)}. {editing.mode === 'rebuild' && 'Later saved changes will not be included. '}Export ZIP uses this saved version until you save your edits.</p>{job?.head !== editing.expectedHead && <p className="error">A newer version was saved while you were editing. Your draft is retained; saving will report a conflict.</p>}{editing.blocks.map((block, index) => <label key={block.id}><span>{block.id} · PDF {block.pages.join(', ')}</span><textarea disabled={busy} rows={Math.max(4, Math.min(16, block.markdown.split('\n').length + 1))} value={block.markdown} onChange={e => changeBlock(index, e.target.value)} /></label>)}</div>
                : saved ? tab === 'preview' ? <iframe title="Saved document preview" sandbox="" srcDoc={saved.preview} /> : <pre className="markdown-view">{saved.markdown}</pre>
                  : version ? <div className="output-empty">{loadError ? <><p className="error" role="alert">Could not load the selected version: {loadError}</p><button onClick={retryLoad}>Retry loading version</button></> : <p>Loading selected version…</p>}</div>
                    : <div className="output-empty"><Icon name="book" size={38} /><h3>Your Markdown takes shape here</h3><p>Start the conversion when your scope and Nexus connection are ready. Saved drafts stay available as the agent works.</p></div>}
            <div className="panel-footnote output-footer"><span>{editing ? `Unsaved draft · ${editing.blocks.length} blocks` : saved ? `${saved.content.claim === 'complete' ? 'Agent marked complete' : 'Partial draft'} · ${saved.content.blocks.length} blocks` : 'Immutable versions · portable images'}</span>{tab !== 'evidence' && <div>{editing ? <><button className="text-button" disabled={busy} onClick={discardEdit}>Discard edits</button><button className="text-button accent" disabled={busy || running} onClick={() => act(async () => {
              const result = await api('edit', { job: editing.job, edit: { mode: editing.mode, base_version: editing.baseVersion, expected_head: editing.expectedHead, replace_blocks: editing.blocks, claim: 'partial' } })
              if (!result.ok) throw new Error(result.data.error)
              setJob(current => current?.id === editing.job ? { ...current, head: result.data.version_id } : current)
              finishEdit(); setNotice('Saved your edits as a new partial version.')
            })}>Save new version</button></> : version && (saved && saved.version !== job?.head ? <button className="text-button" disabled={busy || running} title="Create a new version from this older version. Content added in later versions will not be included." onClick={() => beginEdit('rebuild')}>Rebuild from this version</button> : <button className="text-button" disabled={!saved || busy || running} onClick={() => beginEdit('edit')}>Edit content</button>)}</div>}</div>
          </section>
        </div>
        <section className="agent-panel"><div className="agent-header"><div><span className={`agent-indicator ${running ? 'working' : ''}`} /><strong>Conversion agent</strong><span className="muted small">{job?.route?.model || settings.route?.model || 'Connect Nexus to begin'}</span></div><button className="text-button" onClick={() => setActivityOpen(!activityOpen)}>{activityOpen ? 'Hide activity' : 'View activity'} <span className="event-count">{job?.events?.length || 0}</span></button></div>
          {job?.last_message && <div className="agent-message">{job.last_message}</div>}
          {latestRequest?.receive && <ReceiveProgress receive={latestRequest.receive} status={latestRequest.status} running={running} />}
          {activityOpen && <div className="activity-log">{job?.events?.map(event => <div key={event.seq}><time>{new Date(event.created * 1000).toLocaleTimeString()}</time><span>{event.type.replaceAll('_', ' ')}</span><code>{String(event.data.tool || event.data.reason || event.data.kind || event.data.version_id || '')}</code></div>)}</div>}
          <div className="agent-controls"><textarea aria-label="Instructions or reply" rows={2} placeholder={job?.status === 'waiting' ? 'Reply to the agent…' : 'Add an instruction or correction for the next step…'} value={amendment} onChange={e => setAmendment(e.target.value)} disabled={running} />
            {running ? <button className="stop-button" disabled={job?.cancel_requested || busy} onClick={() => act(() => api('cancel', { job: active }))}><Icon name="stop" size={16} />{job?.cancel_requested ? 'Stopping…' : 'Stop'}</button> : <button className="primary" disabled={busy || !ready || Boolean(editing)} onClick={() => continueTask()}>{job?.attempts ? 'Continue' : 'Start conversion'}<Icon name="arrow" size={16} /></button>}
          </div>
          {recoveryRequest && <div className="agent-meta"><p className="hint">The interrupted context organization has no accepted reply. Resume permits one replacement for that request, then continues the task. It may repeat upstream work. Saved content and recorded usage stay intact.</p><button className="text-button accent" disabled={busy || !ready || Boolean(editing)} onClick={() => continueTask(recoveryRequest)}>Resume context organization</button></div>}
          {job && <ConflictRecovery key={job.id} job={job.id} running={running} refresh={() => refresh.current()}
            viewEvidence={(ref, raw) => { void act(async () => { setEvidence(await api('evidence', { job: active, ref, view: raw ? 'raw' : 'full' })); setTab('evidence') }) }} />}
          <div className="agent-meta"><span>{job?.attempts || 0} / {job?.limits.max_requests || defaultLimits.max_requests} model requests{latestCapacity ? ` · Estimated input ${latestCapacity.input_estimate.toLocaleString()} / ${(latestCapacity.capacity - latestCapacity.output_reserve).toLocaleString()}` : ''}</span><label className="check"><input type="checkbox" checked={scripts} onChange={e => setScripts(e.target.checked)} disabled={running} />Enable trusted task scripts</label></div>
          {job?.route && <div className="agent-meta"><span data-testid="effective-task-limits">Recorded active time {job.active_seconds.toFixed(1)} / {job.limits.max_active_seconds} s · New-request context {job.route.context_tokens.toLocaleString()} · Output reserve {job.route.output_tokens.toLocaleString()}</span><button className="text-button" disabled={running || busy} onClick={() => setSettingsJob(job)}>Task limits</button></div>}
          {unmeasuredIntervals > 0 && <p className="hint script-note" role="status">{unmeasuredIntervals} interrupted interval(s) have unknown active time. They remain recorded separately. The time budget uses known active time; this is not a complete usage total.</p>}
          {scripts && <p className="hint script-note">Scripts run with your user permissions. This is enabled for this session and is not an OS sandbox.</p>}
        </section>
      </>}
      {error && <div className="toast error" role="alert"><span>{error.replace(/^Error: /, '')}</span><button onClick={() => setError('')} aria-label="Dismiss error"><Icon name="close" size={16} /></button></div>}
      {notice && <div className="toast success" role="status"><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss notice"><Icon name="close" size={16} /></button></div>}
    </main>
    {settingsOpen && <Connection initial={settings} close={() => setSettingsOpen(false)} onSave={setSettings} />}
    {settingsJob && <TaskSettings key={settingsJob.id} job={settingsJob} close={() => setSettingsJob(null)} onSave={updated => {
      setJob(current => current?.id === updated.id ? { ...current, ...updated } : current)
      setNotice('Task limits saved. Recorded usage and pending requests are preserved.')
    }} />}
    {importName && <div className="overlay"><form className="modal" onSubmit={e => { e.preventDefault(); void act(async () => {
      const value = await api<Job>('importPdf', { scope }); setImportName(''); setActive(value.id)
    }) }}><div className="modal-heading"><div><span className="eyebrow">NEW DOCUMENT</span><h2>What should we convert?</h2></div><button type="button" className="icon-button" aria-label="Close import" onClick={() => setImportName('')}><Icon name="close" /></button></div><div className="selected-file"><Icon name="file" /><strong>{importName}</strong></div><label>Requested scope<textarea required rows={5} value={scope} onChange={e => setScope(e.target.value)} /></label><p className="hint">For a section, describe its heading or physical pages and any boundaries within a page.</p><div className="modal-footer"><span className="hint">The original PDF stays unchanged.</span><button type="submit" className="primary" disabled={busy}>Open document<Icon name="arrow" size={16} /></button></div></form></div>}
  </div>
}

createRoot(document.getElementById('root')!).render(<App />)
