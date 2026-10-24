import { useEffect, useState } from 'react'
import type { EditSession, Job, Saved } from './types'

type Loaded = { job: string; version: string } & (
  { status: 'loading' } | { status: 'ready'; value: Saved } | { status: 'error'; error: string }
)

export function useDocumentSession(job: Job | null) {
  // A null selection follows the head. An edit freezes its own source and commit precondition.
  const [selection, setSelection] = useState<{ job: string; version: string } | null>(null)
  const [session, setSession] = useState<EditSession | null>(null)
  const [loaded, setLoaded] = useState<Loaded | null>(null)
  const [attempt, setAttempt] = useState(0)
  const editing = session?.job === job?.id ? session : null
  const version = editing?.baseVersion ?? (selection?.job === job?.id ? selection?.version : job?.head) ?? ''
  const jobId = job?.id
  const matches = loaded?.job === jobId && loaded?.version === version
  const saved = matches && loaded?.status === 'ready' ? loaded.value : null
  const loadError = matches && loaded?.status === 'error' ? loaded.error : ''

  useEffect(() => {
    if (!jobId || !version) return
    let alive = true
    setLoaded({ job: jobId, version, status: 'loading' })
    void window.workbench.invoke<Saved>('version', { job: jobId, version }).then(value => {
      if (value.job !== jobId || value.version !== version) throw new Error('The loaded document does not match the selected version.')
      if (alive) setLoaded({ job: jobId, version, status: 'ready', value })
    }).catch(error => {
      if (alive) setLoaded({ job: jobId, version, status: 'error', error: String(error) })
    })
    return () => { alive = false }
  }, [jobId, version, attempt])

  const selectVersion = (value: string) => {
    if (jobId && !editing) setSelection({ job: jobId, version: value })
  }
  const beginEdit = (mode: EditSession['mode']) => {
    if (!job || !saved || job.running || (mode === 'edit' && saved.version !== job.head)) return
    setSession({ job: job.id, baseVersion: saved.version, expectedHead: job.head, mode,
      blocks: saved.content.blocks.map(block => ({ ...block, pages: [...block.pages] })) })
  }
  const changeBlock = (index: number, markdown: string) => setSession(current => current && {
    ...current, blocks: current.blocks.map((block, i) => i === index ? { ...block, markdown } : block)
  })
  const finishEdit = () => { setSession(null); setSelection(null) }
  const discardEdit = () => {
    if (editing) setSelection({ job: editing.job, version: editing.baseVersion })
    setSession(null)
  }
  return { version, saved, editing, loadError, selectVersion, beginEdit, changeBlock, finishEdit, discardEdit,
    retryLoad: () => setAttempt(value => value + 1) }
}
