import { safeStorage } from 'electron'
import { promises as fs } from 'node:fs'
import { dirname, join } from 'node:path'

const fileError = 'Cannot load the development credential file. Use a nonempty UTF-8 file containing one credential, or disable file loading.'

// The only credential owner. Construct after app readiness, before loading the UI.
export class ConnectionState {
  private key = ''
  private revision = 0
  private credentialRevision = 0
  private data: Record<string, any> = {}
  private encryptionAvailable = false
  private error = ''
  private initialization: Promise<void>
  private writes: Promise<unknown> = Promise.resolve()

  constructor(private path: string, root: string, packaged: boolean) {
    this.initialization = this.initialize(root, packaged)
  }

  private async fileCandidate(root: string, packaged: boolean): Promise<string | undefined> {
    if (packaged || process.env.PDFMD_SKIP_CREDENTIAL_FILE === '1') return undefined
    const explicit = process.env.PDFMD_CREDENTIAL_FILE
    const filename = explicit || join(root, 'private', 'api-key.txt')
    const metadata = await fs.stat(filename).catch((error: NodeJS.ErrnoException) => {
      // Only initial discovery can establish benign default-file absence. Once
      // selected, a disappearing/unreadable file must never enable fallback.
      if (!explicit && error.code === 'ENOENT') return undefined
      throw new Error(fileError)
    })
    if (metadata === undefined) return undefined
    try {
      if (!metadata.isFile() || metadata.size > 65536) throw new Error()
      const bytes = await fs.readFile(filename)
      if (bytes.length > 65536) throw new Error()
      const value = new TextDecoder('utf-8', { fatal: true }).decode(bytes).trim()
      if (!value || /\s|[\x00-\x20\x7f]/u.test(value)) throw new Error()
      return value
    } catch {
      throw new Error(fileError)
    }
  }

  private async initialize(root: string, packaged: boolean) {
    const basis = this.credentialRevision
    // Attach all rejection handlers immediately; no unhandled file failure while
    // waiting for settings or OS encryption availability.
    const file = this.fileCandidate(root, packaged).then(value => ({ value, failed: false }), () => ({ value: undefined, failed: true }))
    const raw = fs.readFile(this.path, 'utf8').then(value => {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    }).catch(() => ({}))
    const available = safeStorage.isAsyncEncryptionAvailable().catch(() => false)
    const [candidate, data, encryptionAvailable] = await Promise.all([file, raw, available])
    this.data = data
    this.encryptionAvailable = encryptionAvailable
    if (candidate.failed) { this.error = fileError; return }
    if (candidate.value !== undefined) {
      if (basis === this.credentialRevision) this.key = candidate.value
      return
    }
    // File absence/opt-out is established. Ordinary settings reads never hydrate.
    if (!data.secret || !encryptionAvailable || basis !== this.credentialRevision) return
    try {
      const decrypted = await safeStorage.decryptStringAsync(Buffer.from(data.secret, 'base64'))
      if (basis !== this.credentialRevision) return
      this.key = decrypted.result
      if (decrypted.shouldReEncrypt) {
        const secret = (await safeStorage.encryptStringAsync(decrypted.result)).toString('base64')
        if (basis !== this.credentialRevision) return
        await this.persist({ ...data, secret })
      }
    } catch {
      // Unavailable remembered credentials leave manual entry available. Do not
      // forward OS errors or ciphertext to the renderer.
    }
  }

  private snapshot() {
    return { route: this.data.route, limits: this.data.limits, remember: this.data.remember,
      hasKey: Boolean(this.key), encryptionAvailable: this.encryptionAvailable,
      revision: this.revision, credentialState: this.error ? 'failed' as const : 'ready' as const,
      ...(this.error ? { error: this.error } : {}) }
  }

  async settings() {
    await this.settled()
    return this.snapshot()
  }

  private async settled() {
    await this.initialization
    let pending: Promise<unknown>
    do { pending = this.writes; await pending } while (pending !== this.writes)
  }

  private async persist(data: Record<string, any>) {
    await fs.mkdir(dirname(this.path), { recursive: true })
    await fs.writeFile(this.path, JSON.stringify(data, null, 2), { mode: 0o600 })
    this.data = data
  }

  save(args: Record<string, any>) {
    const revision = ++this.revision
    const changesKey = args.clearKey || (typeof args.key === 'string' && args.key)
    if (changesKey) {
      ++this.credentialRevision
      this.key = args.clearKey ? '' : args.key
    }
    // Capture explicit intent on receipt, before any async encryption. Blank key
    // means retain the initialized session key, not an early empty placeholder.
    const chosenKey = changesKey ? this.key : undefined
    const saved = { route: args.route, limits: args.limits, remember: Boolean(args.remember) }
    const write = this.writes.then(async () => {
      await this.initialization
      const data: Record<string, any> = { ...saved }
      const key = chosenKey ?? this.key
      try {
        if (data.remember && key && this.encryptionAvailable) {
          data.secret = (await safeStorage.encryptStringAsync(key)).toString('base64')
        }
        // Newer accepted settings own persistence; an old encryption completion
        // need not write a secret that Clear has already invalidated.
        if (revision === this.revision) await this.persist(data)
      } catch { throw new Error('Cannot save connection settings. Please try again.') }
    })
    this.writes = write.catch(() => undefined)
    return write.then(() => this.settings())
  }

  async forStart() {
    await this.settled()
    if (this.error) throw new Error(this.error)
    return { configuration: this.snapshot(), key: this.key }
  }

  redact(text: string) { return this.key ? text.split(this.key).join('[credential]') : text }
}
