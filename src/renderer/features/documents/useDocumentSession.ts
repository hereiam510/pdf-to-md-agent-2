import { useCallback, useEffect, useState } from 'react'
import type { EditSession, Job, Saved } from '../../types'

type Loaded = { job: string; version: string; attempt: number } & (
  { status: 'loading' } | { status: 'ready'; value: Saved } | { status: 'error'; error: string }
)

export function useDocumentSession(job: Job | null) {
  // A null selection follows the head. An edit freezes its own source and commit precondition.
  const [selection, setSelection] = useState<{ job: string; version: string } | null>(null)
  const [session, setSession] = useState<EditSession | null>(null)
  const [loaded, setLoaded] = useState<Loaded | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [previewRevision, setPreviewRevision] = useState(0)
  const editing = session?.job === job?.id ? session : null
  const version = editing?.baseVersion ?? (selection?.job === job?.id ? selection?.version : job?.head) ?? ''
  const jobId = job?.id
  const matches = loaded?.job === jobId && loaded?.version === version && loaded?.attempt === attempt
  const saved = matches && loaded?.status === 'ready' ? loaded.value : null
  const loadError = matches && loaded?.status === 'error' ? loaded.error : ''

  useEffect(() => {
    if (!jobId || !version || editing) return
    let alive = true
    const generation = crypto.randomUUID()
    setLoaded({ job: jobId, version, attempt, status: 'loading' })
    void window.workbench.invoke<Saved>('version', { job: jobId, version, generation }).then(async value => {
      if (value.job !== jobId || value.version !== version) throw new Error('The loaded document does not match the selected version.')
      if (!alive) return
      if (value.preview_lease) await window.workbench.invoke('activatePreview', { job: jobId, version, generation, lease: value.preview_lease })
      if (alive) setLoaded({ job: jobId, version, attempt, status: 'ready', value })
    }).catch(error => {
      if (alive) setLoaded({ job: jobId, version, attempt, status: 'error', error: String(error) })
    })
    return () => { alive = false; void window.workbench.invoke('releasePreview', { generation }).catch(() => {}) }
  }, [jobId, version, attempt, Boolean(editing)])

  const selectVersion = (value: string) => {
    if (jobId && !editing) setSelection({ job: jobId, version: value })
  }
  const beginEdit = (mode: EditSession['mode']) => {
    if (!job || !saved || job.running || (mode === 'edit' && saved.version !== job.head)) return
    setPreviewRevision(value => value + 1)
    setSession({ job: job.id, baseVersion: saved.version, expectedHead: job.head, mode,
      blocks: saved.content.blocks.map(block => ({ ...block, pages: [...block.pages] })), submissionKey: crypto.randomUUID() })
  }
  const changeBlock = (index: number, markdown: string) => setSession(current => current && {
    // A changed draft is a new logical submission; an unchanged retry keeps its key.
    ...current, blocks: current.blocks.map((block, i) => i === index ? { ...block, markdown } : block), submissionKey: crypto.randomUUID()
  })
  const finishEdit = () => { setSession(null); setSelection(null); setAttempt(value => value + 1) }
  const discardEdit = () => {
    if (editing) setSelection({ job: editing.job, version: editing.baseVersion })
    setSession(null)
    setAttempt(value => value + 1)
  }
  const previewFailed = useCallback((generation: string, error: unknown) => {
    void window.workbench.invoke('releasePreview', { generation }).catch(() => {})
    setLoaded(current => current?.status === 'ready' && current.value.preview_generation === generation ? {
      ...current, value: { ...current.value, preview: '', preview_error: `Preview unavailable: ${String(error)}` }
    } : current)
  }, [])
  return { version, saved, editing, loadError, selectVersion, beginEdit, changeBlock, finishEdit, discardEdit,
    previewKey: `${jobId}:${version}:${attempt}:${previewRevision}`, previewFailed,
    returnToDocument: () => { if (saved && !editing) setPreviewRevision(value => value + 1) },
    retryLoad: () => setAttempt(value => value + 1) }
}
