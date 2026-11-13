// The normal application/backend with a private profile. Only version-response
// delivery is held/failed; every value comes from the real version endpoint.
const { app, ipcMain } = require('electron')
const { mkdirSync, appendFileSync } = require('node:fs')
const { resolve } = require('node:path')
const profile = process.env.PDFMD_UI_PROFILE
if (!profile) throw new Error('A private test profile is required.')
mkdirSync(profile, { recursive: true })
app.setPath('userData', resolve(profile))
process.on('uncaughtExceptionMonitor', error => appendFileSync(resolve(profile, 'uncaught-errors.log'), String(error.stack || error) + '\n'))
const control = globalThis.referenceControl = { hold: false, pending: [], calls: [],
  network: [], responses: [], transferFault: false, holdMount: false, pendingMounts: [],
  settle(index, fail = false) {
    const item = this.pending.splice(index, 1)[0]
    if (fail) item.reject(new Error('Injected selected-version delivery failure'))
    else item.resolve(item.value)
  }
}
const nativeFetch = globalThis.fetch
globalThis.fetch = async (...args) => {
  const response = await nativeFetch(...args)
  if (control.transferFault && String(args[0]).includes('/versions/')) {
    const value = await response.json()
    if (value.preview_transfer?.resources.length) value.preview_transfer.resources[0].length++
    return new Response(JSON.stringify(value), { status: response.status, headers: response.headers })
  }
  return response
}
app.on('browser-window-created', (_event, win) => {
  win.webContents.on('will-frame-navigate', event => {
    const row = { hook: 'will-frame-navigate', url: event.url, main: event.isMainFrame, frame: null, cancel: false }
    try { row.frame = event.frame && { url: event.frame.url, name: event.frame.name, node: event.frame.frameTreeNodeId } } catch {}
    setImmediate(() => { row.cancel = event.defaultPrevented; control.network.push(row) })
  })
})
app.whenReady().then(() => {
  const { session } = require('electron')
  const { createHash } = require('node:crypto')
  const ses = session.defaultSession
  for (const name of ['onBeforeRequest', 'onBeforeSendHeaders']) {
    const original = ses.webRequest[name].bind(ses.webRequest)
    ses.webRequest[name] = listener => original((details, callback) => listener(details, result => {
      if (details.url.startsWith('pdfmd-preview:')) {
        let frame = null
        try { frame = details.frame && { url: details.frame.url, name: details.frame.name, node: details.frame.frameTreeNodeId, detached: details.frame.detached } } catch {}
        control.network.push({ hook: name, url: details.url, type: details.resourceType, contents: details.webContentsId, frame, cancel: result.cancel || false })
      }
      callback(result)
    }))
  }
  const handle = ses.protocol.handle.bind(ses.protocol)
  ses.protocol.handle = (scheme, handler) => handle(scheme, async request => {
    const response = await handler(request)
    const body = Buffer.from(await response.clone().arrayBuffer())
    control.responses.push({ url: request.url, status: response.status, length: body.length,
      sha256: createHash('sha256').update(body).digest('hex'), headers: Object.fromEntries(response.headers) })
    return response
  })
})
const register = ipcMain.handle.bind(ipcMain)
ipcMain.handle = (channel, handler) => register(channel, async (event, action, args) => {
  control.calls.push({ action, job: args?.job, version: args?.version })
  if (['start', 'continue'].includes(action)) throw new Error('Provider execution denied in the T2 desktop fixture.')
  if (control.holdMount && ['bindPreview', 'unmountPreview'].includes(action)) {
    await new Promise(resolve => control.pendingMounts.push({ action, args, resolve }))
  }
  if (action === 'bindPreview') {
    const name = `pdfmd-preview-${args.lease}-${args.mount}`
    const frame = event.senderFrame.frames.find(frame => frame.name === name)
    const row = { hook: action, ...args, name, node: frame?.frameTreeNodeId, url: frame?.url, accepted: false }
    control.network.push(row)
    const value = await handler(event, action, args)
    row.accepted = true
    return value
  }
  const held = action === 'version' && control.hold
  const value = await handler(event, action, args)
  if (held) return new Promise((resolve, reject) => control.pending.push({ value, resolve, reject }))
  return value
})
require(resolve(process.env.PDFMD_DIAGNOSTIC_BUILD || 'out', 'main/index.js'))
