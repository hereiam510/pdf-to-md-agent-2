import { useLayoutEffect, useState } from 'react'
import type { Saved } from '../../types'

export function SavedPreview({ saved, onUnavailable }: { saved: Saved; onUnavailable: (generation: string, error: unknown) => void }) {
  const [frame, setFrame] = useState<{ name: string; bind: (node: HTMLIFrameElement | null) => void } | null>(null)
  const [bound, setBound] = useState(false)
  const generation = saved.preview_generation, lease = saved.preview_lease
  useLayoutEffect(() => {
    // Non-resource renderer fixtures retain their ordinary inert preview.
    if (!generation || !lease) return
    let alive = true
    let binding = false
    const identity = { generation, lease, mount: crypto.randomUUID() }
    const unavailable = (error: unknown) => { if (alive) onUnavailable(generation, error) }
    const bind = (node: HTMLIFrameElement | null) => {
      if (!node || !alive || binding) return
      binding = true
      void window.workbench.invoke('bindPreview', identity).then(() => {
        if (alive) setBound(true)
      }).catch(unavailable)
    }
    void window.workbench.invoke<string>('mountPreview', identity).then(name => {
      if (alive) setFrame({ name, bind })
    }).catch(unavailable)
    return () => { alive = false; void window.workbench.invoke('unmountPreview', identity).catch(() => {}) }
  }, [generation, lease, onUnavailable])
  if (lease && !frame) return <div className="output-empty">Preparing selected preview…</div>
  // Register the initial empty child before assigning its first document.
  return <iframe name={frame?.name} title="Saved document preview" sandbox="" ref={frame?.bind}
    srcDoc={!lease || bound ? saved.preview : undefined} />
}
