import { useEffect, useState } from 'react'
import type { Saved } from '../../types'

export function SavedPreview({ saved, onUnavailable }: { saved: Saved; onUnavailable: (generation: string, error: unknown) => void }) {
  const [name, setName] = useState('')
  const generation = saved.preview_generation, lease = saved.preview_lease
  useEffect(() => {
    // Non-resource renderer fixtures retain their ordinary inert preview.
    if (!generation || !lease) return
    let alive = true
    const mount = crypto.randomUUID()
    void window.workbench.invoke<string>('mountPreview', { generation, lease, mount }).then(value => {
      if (alive) setName(value)
    }).catch(error => { if (alive) onUnavailable(generation, error) })
    return () => { alive = false; void window.workbench.invoke('unmountPreview', { generation, lease, mount }).catch(() => {}) }
  }, [generation, lease])
  if (lease && !name) return <div className="output-empty">Preparing selected preview…</div>
  return <iframe name={name} title="Saved document preview" sandbox="" srcDoc={saved.preview} />
}
