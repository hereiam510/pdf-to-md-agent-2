// Actual built main/preload/renderer, with gated native I/O and a zero-network
// engine stand-in. No Python/controller/model process can start in this harness.
const electron = require('electron')
const { app, safeStorage, ipcMain } = electron
const fs = require('node:fs')
const { resolve, join, dirname } = require('node:path')
const { EventEmitter } = require('node:events')
const { createHash } = require('node:crypto')
const directory = resolve(process.env.PDFMD_CREDENTIAL_TEST_ROOT)
app.setPath('userData', join(directory, 'profile'))
const options = JSON.parse(process.env.PDFMD_CREDENTIAL_TEST_OPTIONS || '{}')
const state = globalThis.credentialsTest = {
  holds: { ...options.holds }, pending: {}, calls: {}, starts: [], saves: 0, spawned: 0,
  configured: false, capturedSettings: [],
  release(name) {
    this.holds[name] = false
    for (const done of this.pending[name] || []) done()
    this.pending[name] = []
  },
  settle(name, index) {
    this.pending[name].splice(index, 1)[0]()
  }
}
async function gate(name) {
  state.calls[name] = (state.calls[name] || 0) + 1
  if (state.holds[name]) await new Promise(done => (state.pending[name] ||= []).push(done))
}
const original = { ...fs.promises }
const defaultFile = resolve('private/api-key.txt')
function owned(path) {
  const filename = resolve(String(path))
  if (filename === defaultFile) return join(directory, 'default-key.txt')
  if (filename !== directory && !filename.startsWith(directory + require('node:path').sep)) throw new Error('Test refused non-fixture I/O')
  return filename
}
fs.promises.stat = async path => {
  await gate('fileStat')
  if (options.unreadable) throw new Error('Synthetic private error withheld')
  return original.stat(owned(path))
}
fs.promises.readFile = async (path, encoding) => {
  const target = owned(path)
  await gate(target === join(directory, 'connection.json') ? 'raw' : 'file')
  return original.readFile(target, encoding)
}
fs.promises.mkdir = (path, options) => original.mkdir(owned(path), options)
fs.promises.writeFile = async (path, data, options) => {
  await gate('write')
  return original.writeFile(owned(path), data, options)
}
fs.promises.appendFile = (path, data) => original.appendFile(owned(path), data)
const available = safeStorage.isAsyncEncryptionAvailable.bind(safeStorage)
const decrypt = safeStorage.decryptStringAsync.bind(safeStorage)
const encrypt = safeStorage.encryptStringAsync.bind(safeStorage)
safeStorage.isAsyncEncryptionAvailable = async () => {
  await gate('availability')
  return options.unavailable ? false : available()
}
safeStorage.decryptStringAsync = async value => {
  await gate('decrypt')
  if (options.decryptFailure) throw new Error('Synthetic secret decrypt error')
  const result = await decrypt(value)
  return { ...result, shouldReEncrypt: Boolean(options.reencrypt) || result.shouldReEncrypt }
}
safeStorage.encryptStringAsync = async value => {
  await gate('encrypt')
  if (state.encryptFailure) throw new Error('Synthetic secret encrypt error')
  return encrypt(value)
}
if (options.packaged) {
  Object.defineProperty(app, 'isPackaged', { value: true })
  const exists = fs.existsSync
  fs.existsSync = path => String(path).endsWith('pdf-md-engine.exe') || exists(path)
}
require('node:child_process').spawn = () => {
  state.spawned++
  const child = new EventEmitter()
  child.stdout = new EventEmitter(); child.stderr = new EventEmitter(); child.kill = () => {}
  setImmediate(() => child.stdout.emit('data', Buffer.from('{"type":"ready","port":54321}\n')))
  return child
}
const route = { endpoint: 'http://127.0.0.1:1/v1/chat/completions', model: 'synthetic-offline', protocol: 'chat_completions',
  context_tokens: 131072, output_tokens: 8192, image_tokens: 4096, vision: true, timeout_seconds: 180, parameters: {} }
const limits = { max_requests: 12, max_active_seconds: 1200, max_response_repairs: 2, replay_unknown: false, max_attempts_per_request: 1 }
const job = { id: 'credential-job', name: 'Credential fixture', scope: 'No conversion', status: 'ready', page_count: 1,
  head: null, delivery: null, attempts: 0, active_seconds: 0, running: false, cancel_requested: false, versions: [], requests: [], route: null, limits }
globalThis.fetch = async (url, options = {}) => {
  const parsed = new URL(url)
  if (parsed.origin !== 'http://127.0.0.1:54321') throw new Error('Network is forbidden in this harness')
  let value
  if (parsed.pathname === '/health') value = { ready: true }
  else if (parsed.pathname === '/jobs') value = [job]
  else if (parsed.pathname.endsWith('/page/1')) value = { url: '' }
  else if (parsed.pathname.endsWith('/start')) {
    const { key, ...body } = JSON.parse(options.body)
    state.starts.push({ digest: createHash('sha256').update(key).digest('hex'), ...body })
    value = { captured: true } // End before controller/model dispatch.
  } else if (parsed.pathname.endsWith('/settings')) {
    const body = JSON.parse(options.body); state.taskSettings = body; value = { ...job, ...body }
  } else if (parsed.pathname === '/jobs/credential-job') {
    await gate('job')
    value = { ...job, route: state.configured ? { ...route, model: 'saved-task-model' } : null }
  } else throw new Error('Unexpected local API path')
  return { ok: true, json: async () => value }
}
const handle = ipcMain.handle.bind(ipcMain)
ipcMain.handle = (channel, handler) => {
  if (channel !== 'workbench') throw new Error('Unexpected IPC channel')
  state.invoke = (action, args = {}) => {
    state.calls[action + 'Action'] = (state.calls[action + 'Action'] || 0) + 1
    const win = electron.BrowserWindow.getAllWindows()[0]
    return handler({ sender: win.webContents, senderFrame: win.webContents.mainFrame }, action, args)
  }
  handle(channel, async (event, action, args) => {
    if (action === 'saveSettings') state.saves++
    const result = await handler(event, action, args)
    if (action === 'settings') {
      state.capturedSettings.push(result)
      await gate('reply')
    }
    if (action === 'saveSettings') await gate('saveReply')
    return result
  })
}
require(resolve('out/main/index.js'))
