// Controlled IPC fixture for the real built renderer. It starts no backend or model service.
const { app, BrowserWindow, ipcMain } = require('electron')
const { resolve } = require('node:path')
const { mkdirSync, mkdtempSync } = require('node:fs')
mkdirSync(resolve('.local'), { recursive: true })
app.setPath('userData', mkdtempSync(resolve('.local/session-ui-')))
const versions = {}
function saved(version, blocks) {
  return { job: 'job1', version, markdown: blocks.map(b => b.markdown).join('\n\n'),
    preview: `<html><body>${blocks.map(b => `<p>${b.markdown}</p>`).join('')}</body></html>`,
    content: { title: 'Session fixture', scope: 'Two pages', blocks, claim: 'partial', known_gaps: [] } }
}
const first = { id: 'p1', pages: [1], markdown: 'Retained first page.', source_note: '' }
versions.v1 = saved('v1', [first])
versions.v2 = saved('v2', [first, { id: 'p2', pages: [2], markdown: 'Retained second page.', source_note: '' }])
const job = { id: 'job1', name: 'Session fixture', scope: 'Two pages', status: 'paused', page_count: 2,
  head: 'v2', delivery: null, attempts: 1, active_seconds: 0, limits: { max_requests: 10 },
  running: false, route: null, versions: [{ id: 'v2', claim: 'partial' }, { id: 'v1', claim: 'partial' }] }
const harness = globalThis.sessionHarness = {
  hold: false, pending: [], captures: [], versionReads: [],
  settle(index, fail = false) {
    const item = this.pending.splice(index, 1)[0]
    if (fail) item.reject(new Error('Injected version read failure'))
    else item.resolve(versions[item.version])
  },
  advance() {
    versions.v3 = saved('v3', [...versions.v2.content.blocks, { id: 'p3', pages: [2], markdown: 'Newer saved work.', source_note: '' }])
    job.head = 'v3'; job.versions.unshift({ id: 'v3', claim: 'partial' })
  }
}
app.whenReady().then(async () => {
  ipcMain.handle('workbench', async (_event, action, args) => {
    if (action === 'health') return { ready: true }
    if (action === 'settings') return {}
    if (action === 'jobs') return [job]
    if (action === 'job') return job
    if (action === 'page') return { url: '' }
    if (action === 'version') {
      harness.versionReads.push(args.version)
      if (harness.hold) return new Promise((resolve, reject) => harness.pending.push({ version: args.version, resolve, reject }))
      return versions[args.version]
    }
    if (action === 'edit') {
      harness.captures.push({ action, ...args })
      if (args.edit.expected_head !== job.head) return { ok: false, data: { error: 'Head changed. Candidate retained.' } }
      versions.v4 = saved('v4', args.edit.replace_blocks)
      job.head = 'v4'; job.versions.unshift({ id: 'v4', claim: 'partial' })
      return { ok: true, data: { version_id: 'v4' } }
    }
    if (action === 'export') {
      harness.captures.push({ action, ...args })
      return { claim: 'partial', path: 'fixture.zip' }
    }
    throw new Error(`Unexpected IPC action: ${action}`)
  })
  const window = new BrowserWindow({ width: 1440, height: 1000, show: false,
    webPreferences: { preload: resolve('out/preload/index.js'), sandbox: true, contextIsolation: true, nodeIntegration: false } })
  await window.loadFile(resolve('out/renderer/index.html'))
})
app.on('window-all-closed', () => app.quit())
