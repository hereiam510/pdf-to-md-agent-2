import type { BrowserWindow, WebContents, WebFrameMain, OnBeforeRequestListenerDetails } from 'electron'
import { createHash, randomBytes } from 'node:crypto'

export const previewScheme = 'pdfmd-preview'
const nonce = () => randomBytes(24).toString('hex')
type Resource = { bytes: Buffer; mime: string; asset: string; representation: string; sha256: string }
type Snapshot = { job: string; version: string; generation: string; lease: string; resources: Map<string, Resource> }

/** One window/session owns one loaded snapshot. No path is ever resolved here. */
export class PreviewResources {
  private contents: WebContents
  private ownerId: number
  private intent = ''
  private prepared: Snapshot | null = null
  private active: Snapshot | null = null
  private mountName = ''
  private frames = new Set<number>()
  private grants = new Map<string, { url: string; lease: string; frame: WebFrameMain }>()

  constructor(private win: BrowserWindow) {
    this.contents = win.webContents
    this.ownerId = this.contents.id
    const ses = this.contents.session
    ses.webRequest.onBeforeRequest((details, callback) => {
      if (details.url.startsWith(`${previewScheme}:`)) return callback({ cancel: !this.allowed(details) })
      // All child-frame network/file requests are denied, including redirects.
      // about:srcdoc is supplied by the trusted shell, not a network resource.
      try {
        if (details.webContentsId === this.ownerId && !this.isAlive()) return callback({ cancel: true })
        const child = details.webContentsId === this.ownerId && details.frame && details.frame !== this.contents.mainFrame
        callback({ cancel: Boolean(child && details.url !== 'about:srcdoc' && details.url !== 'about:blank') })
      } catch { callback({ cancel: true }) } // A disposed caller context is never authority.
    })
    ses.webRequest.onBeforeSendHeaders((details, callback) => {
      if (!details.url.startsWith(`${previewScheme}:`)) return callback({})
      if (!this.allowed(details) || !details.frame || !this.active) return callback({ cancel: true })
      const grant = nonce()
      this.grants.set(grant, { url: details.url, lease: this.active.lease, frame: details.frame })
      callback({ requestHeaders: { ...details.requestHeaders, 'X-Pdfmd-Preview-Grant': grant } })
    })
    ses.protocol.handle(previewScheme, request => {
      const grant = request.headers.get('X-Pdfmd-Preview-Grant') || ''
      const authorization = this.grants.get(grant)
      this.grants.delete(grant)
      const resource = this.active?.resources.get(request.url)
      if (request.method !== 'GET' || !authorization || authorization.url !== request.url ||
          authorization.lease !== this.active?.lease || !this.frameAllowed(authorization.frame) || !resource) {
        return new Response(null, { status: 403 })
      }
      return new Response(new Uint8Array(resource.bytes), { headers: {
        'Content-Type': resource.mime, 'Content-Length': String(resource.bytes.length),
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store',
        'Content-Security-Policy': `default-src 'none'; img-src ${previewScheme}:; style-src 'unsafe-inline'; sandbox`
      } })
    })
    win.webContents.on('will-frame-navigate', event => {
      if (event.isMainFrame || !this.active?.resources.has(event.url) || !this.frameAllowed(event.frame)) event.preventDefault()
    })
    win.webContents.on('will-redirect', event => event.preventDefault())
    win.webContents.on('render-process-gone', () => this.release())
    win.webContents.on('destroyed', () => this.release())
  }

  private isAlive() { return !this.win.isDestroyed() && !this.contents.isDestroyed() }

  private frameAllowed(frame: WebFrameMain | null | undefined): boolean {
    if (!frame || !this.active || !this.isAlive()) return false
    try {
      if (!this.mountName || frame.detached || frame.parent !== this.contents.mainFrame || frame.name !== this.mountName) return false
      const peers = this.contents.mainFrame.frames.filter(f => f.name === frame.name)
      if (peers.length !== 1 || peers[0].frameTreeNodeId !== frame.frameTreeNodeId) return false
      if (!this.frames.has(frame.frameTreeNodeId)) {
        if (frame.url !== 'about:srcdoc') return false
        this.frames.clear()
        this.frames.add(frame.frameTreeNodeId)
      }
      return true
    } catch { return false }
  }

  private allowed(details: Pick<OnBeforeRequestListenerDetails, 'method' | 'webContentsId' | 'resourceType' | 'url' | 'frame'>): boolean {
    try {
      return details.method === 'GET' && details.webContentsId === this.ownerId &&
        (details.resourceType === 'image' || details.resourceType === 'subFrame') &&
        Boolean(this.active?.resources.has(details.url)) && this.frameAllowed(details.frame)
    } catch { return false }
  }

  begin(generation: string) {
    if (typeof generation !== 'string' || !/^[a-f0-9-]{36}$/.test(generation)) throw new Error('Invalid document load generation.')
    this.release()
    this.intent = generation
  }

  prepare(value: any, job: string, version: string, generation: string) {
    if (this.intent !== generation) throw new Error('Obsolete selected-version load.')
    if (value.job !== job || value.version !== version) throw new Error('Selected-version transfer identity mismatch.')
    const { preview_transfer: transfer, ...saved } = value
    try {
      if (transfer?.job !== job || transfer?.version !== version || !Array.isArray(transfer.resources) || !Array.isArray(transfer.slots)) throw new Error('Missing verified preview transfer.')
      const lease = nonce(), resources = new Map<string, Resource>(), urls = new Map<string, string>()
      for (const item of transfer.resources) {
        const bytes = Buffer.from(item.base64, 'base64')
        const signature = item.mime === 'image/png' ? bytes.subarray(0, 8).equals(Buffer.from('89504e470d0a1a0a', 'hex')) :
          item.mime === 'image/jpeg' && bytes.subarray(0, 3).equals(Buffer.from('ffd8ff', 'hex'))
        if (!signature || bytes.length !== item.length || createHash('sha256').update(bytes).digest('hex') !== item.sha256 || urls.has(item.key)) throw new Error('Verified preview payload length, hash or MIME mismatch.')
        const url = `${previewScheme}://snapshot/${lease}/${nonce()}`
        urls.set(item.key, url)
        resources.set(url, { bytes, mime: item.mime, asset: item.asset, representation: item.representation, sha256: item.sha256 })
      }
      let preview = String(value.preview), last = preview.length
      for (const slot of [...transfer.slots].sort((a, b) => b.start - a.start)) {
        const url = urls.get(slot.key)
        if (!url || !Number.isInteger(slot.start) || !Number.isInteger(slot.end) || slot.start < 0 || slot.end < slot.start || slot.end > last || preview.slice(slot.start, slot.end) !== slot.expected) throw new Error('Verified preview binding mismatch.')
        preview = preview.slice(0, slot.start) + url + preview.slice(slot.end)
        last = slot.start
      }
      if (new Set(transfer.slots.map((s: any) => s.key)).size !== urls.size) throw new Error('Unreferenced preview transfer.')
      // The engine's sanitized page is a fixed envelope. Only its derived CSP
      // changes; authored source never gains an internal-protocol scheme.
      preview = preview.replace("img-src 'self' data:", `img-src ${previewScheme}:`)
      this.prepared = { job, version, generation, lease, resources }
      return { ...saved, preview, preview_generation: generation, preview_lease: lease }
    } catch (error) {
      this.prepared = null
      this.active = null
      return { ...saved, preview: '', preview_generation: generation, preview_error: `Preview unavailable: ${String(error)}` }
    }
  }

  activate(job: string, version: string, generation: string, lease: string) {
    const s = this.prepared
    if (!s || s.job !== job || s.version !== version || s.generation !== generation || s.lease !== lease || this.intent !== generation) throw new Error('Obsolete preview activation.')
    this.active = s
    this.prepared = null
    return true
  }

  mount(generation: string, lease: string, mount: string) {
    if (!this.active || this.active.generation !== generation || this.active.lease !== lease || !/^[a-f0-9-]{36}$/.test(mount)) throw new Error('Obsolete preview frame registration.')
    this.mountName = `pdfmd-preview-${lease}-${mount}`
    this.frames.clear()
    this.grants.clear()
    return this.mountName
  }

  unmount(generation: string, lease: string, mount: string) {
    if (this.active?.generation === generation && this.active.lease === lease && this.mountName === `pdfmd-preview-${lease}-${mount}`) {
      this.mountName = ''
      this.frames.clear()
      this.grants.clear()
    }
  }

  release(generation?: string) {
    if (generation && generation !== this.intent) return
    this.intent = ''
    this.active = null
    this.prepared = null
    this.mountName = ''
    this.frames.clear()
    this.grants.clear()
  }
}
