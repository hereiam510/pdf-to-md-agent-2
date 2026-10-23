import { app, BrowserWindow, dialog, ipcMain, safeStorage, session } from 'electron'
import { spawn, type ChildProcess } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { promises as fs, existsSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

let window: BrowserWindow | null = null
let child: ChildProcess | null = null
let origin = ''
let apiKey = ''
let selectedPdf = ''
let startupError = ''
let stopping = false
const token = randomBytes(32).toString('hex')
const root = resolve(__dirname, '../..')
const dataRoot = process.env.PDFMD_DATA || join(app.getPath('userData'), 'workspace')
const settingsPath = join(dirname(dataRoot), 'connection.json')
if (process.argv.includes('--preview-worker')) {
  app.setPath('userData', join(app.getPath('temp'), `pdfmd-preview-${randomBytes(12).toString('hex')}`))
}

async function settings() {
  const encryptionAvailable = await safeStorage.isAsyncEncryptionAvailable()
  try {
    const data = JSON.parse(await fs.readFile(settingsPath, 'utf8'))
    if (data.secret && encryptionAvailable) {
      const decrypted = await safeStorage.decryptStringAsync(Buffer.from(data.secret, 'base64'))
      apiKey = decrypted.result
      if (decrypted.shouldReEncrypt) {
        data.secret = (await safeStorage.encryptStringAsync(apiKey)).toString('base64')
        await fs.writeFile(settingsPath, JSON.stringify(data, null, 2), { mode: 0o600 })
      }
    }
    delete data.secret
    return { ...data, hasKey: Boolean(apiKey), encryptionAvailable }
  } catch {
    return { hasKey: Boolean(apiKey), encryptionAvailable }
  }
}

async function call(path: string, method = 'GET', body?: unknown) {
  if (!origin) throw new Error(startupError || 'The local engine is starting. Try again in a moment.')
  const response = await fetch(origin + path, {
    method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(30000)
  })
  const value = await response.json()
  if (!response.ok) throw new Error(value.error || value.detail || `Local engine returned ${response.status}.`)
  return value
}

function id(value: unknown): string {
  if (typeof value !== 'string' || !/^[a-zA-Z0-9:_-]+$/.test(value)) throw new Error('Invalid saved reference.')
  return encodeURIComponent(value)
}

async function launchBackend() {
  await fs.mkdir(dataRoot, { recursive: true })
  await settings()
  const packaged = app.isPackaged
  const python = process.env.PDFMD_PYTHON || join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
  const executable = packaged ? join(process.resourcesPath, 'engine', 'pdf-md-engine', process.platform === 'win32' ? 'pdf-md-engine.exe' : 'pdf-md-engine') : python
  if (!existsSync(executable)) throw new Error('The Python engine is missing. Run tools/setup.ps1, then restart the app.')
  const args = packaged ? ['--workspace', dataRoot] : ['-m', 'pdfmd.server', '--workspace', dataRoot]
  const previewLaunch = packaged ? [process.execPath] : [process.execPath, join(root, 'out/main/index.js')]
  child = spawn(executable, args, {
    cwd: packaged ? process.resourcesPath : root, windowsHide: true,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PDFMD_LOCAL_TOKEN: token,
      LANGSMITH_TRACING: 'false', LANGCHAIN_TRACING_V2: 'false',
      PDFMD_NODE: process.execPath, PDFMD_PREVIEW_LAUNCH: JSON.stringify(previewLaunch),
      PDFMD_OCR_WORKER: packaged ? join(process.resourcesPath, 'ocr-worker.cjs') : join(root, 'tools/ocr-worker.cjs'),
      NODE_PATH: packaged ? join(app.getAppPath(), 'node_modules') : join(root, 'node_modules') }
  })
  let buffer = ''
  child.stdout?.on('data', (chunk: Buffer) => {
    buffer += chunk.toString('utf8')
    const lines = buffer.split('\n'); buffer = lines.pop() || ''
    for (const line of lines) {
      try {
        const event = JSON.parse(line)
        if (event.type === 'ready' && Number.isInteger(event.port) && event.port > 0 && event.port < 65536) {
          origin = `http://127.0.0.1:${event.port}`
        }
      } catch { /* Native-library diagnostic output is not a protocol message. */ }
    }
    if (buffer.length > 8192) buffer = ''
  })
  child.stderr?.on('data', (chunk: Buffer) => {
    let text = chunk.toString('utf8').split(token).join('[local token]')
    if (apiKey) text = text.split(apiKey).join('[credential]')
    void fs.appendFile(join(dataRoot, 'engine.log'), text).catch(() => undefined)
  })
  child.on('error', (error) => { startupError = `Cannot start the local engine: ${error.message}` })
  child.on('exit', (code) => { origin = ''; if (!stopping) startupError = `The local engine exited (${code}). Saved work remains on disk.` })
}

async function previewWorker(args: string[]) {
  const [folder, output, topText, widthText, heightText] = args
  const allowed = resolve(folder)
  const preview = join(allowed, 'preview.html')
  const isolated = session.fromPartition(`preview-${randomBytes(12).toString('hex')}`)
  isolated.webRequest.onBeforeRequest((details, callback) => {
    if (details.url.startsWith('data:')) return callback({ cancel: false })
    try {
      const path = resolve(fileURLToPath(details.url))
      callback({ cancel: !(path === preview || path.startsWith(allowed + (process.platform === 'win32' ? '\\' : '/'))) })
    } catch { callback({ cancel: true }) }
  })
  const win = new BrowserWindow({ show: false, width: Number(widthText), height: Number(heightText),
    webPreferences: { sandbox: true, contextIsolation: true, nodeIntegration: false, session: isolated } })
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  await win.loadFile(preview)
  await win.webContents.executeJavaScript(`Promise.all([document.fonts.ready, ...Array.from(document.images, i => i.decode().catch(() => {}))])`)
  await win.webContents.executeJavaScript(`window.scrollTo(0, ${Math.max(0, Number(topText))})`)
  await win.webContents.executeJavaScript('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
  const viewport = await win.webContents.executeJavaScript(`({
    top: window.scrollY, left: window.scrollX, viewport_width: window.innerWidth,
    viewport_height: window.innerHeight, document_width: document.documentElement.scrollWidth,
    document_height: document.documentElement.scrollHeight, device_pixel_ratio: window.devicePixelRatio
  })`)
  const png = await win.webContents.capturePage()
  await fs.writeFile(output + '.json', JSON.stringify({ ...viewport, ...png.getSize(),
    requested_top: Number(topText), requested_width: Number(widthText), requested_height: Number(heightText) }), { flag: 'wx' })
  await fs.writeFile(output, png.toPNG(), { flag: 'wx' })
  win.destroy()
  app.quit()
}

app.whenReady().then(async () => {
  const workerFlag = process.argv.indexOf('--preview-worker')
  if (workerFlag >= 0) {
    await previewWorker(process.argv.slice(workerFlag + 1))
    return
  }
  if (!app.requestSingleInstanceLock()) { app.quit(); return }
  app.on('second-instance', () => { window?.show(); window?.focus() })
  ipcMain.handle('workbench', async (event, action: string, args: Record<string, any>) => {
    if (!window || event.sender !== window.webContents || event.senderFrame !== window.webContents.mainFrame) throw new Error('Untrusted IPC sender.')
    switch (action) {
      case 'health': return origin ? call('/health') : { ready: false, error: startupError }
      case 'settings': return settings()
      case 'saveSettings': {
        if (typeof args.key === 'string' && args.key) apiKey = args.key
        if (args.clearKey) apiKey = ''
        const saved: Record<string, unknown> = { route: args.route, limits: args.limits, remember: Boolean(args.remember) }
        const encryptionAvailable = await safeStorage.isAsyncEncryptionAvailable()
        if (args.remember && apiKey && encryptionAvailable) saved.secret = (await safeStorage.encryptStringAsync(apiKey)).toString('base64')
        await fs.mkdir(dirname(settingsPath), { recursive: true })
        await fs.writeFile(settingsPath, JSON.stringify(saved, null, 2), { mode: 0o600 })
        return { ...saved, secret: undefined, hasKey: Boolean(apiKey), encryptionAvailable }
      }
      case 'choosePdf': {
        const result = await dialog.showOpenDialog(window, { properties: ['openFile'], filters: [{ name: 'PDF documents', extensions: ['pdf'] }] })
        selectedPdf = result.canceled ? '' : result.filePaths[0]
        return selectedPdf ? { name: selectedPdf.split(/[\\/]/).pop() } : null
      }
      case 'importPdf': {
        if (!selectedPdf) throw new Error('Choose a source PDF first.')
        const value = await call('/jobs', 'POST', { path: selectedPdf, scope: args.scope })
        selectedPdf = ''
        return value
      }
      case 'jobs': return call('/jobs')
      case 'job': return call(`/jobs/${id(args.job)}`)
      case 'page': return call(`/jobs/${id(args.job)}/page/${Number(args.page)}`)
      case 'version': return call(`/jobs/${id(args.job)}/versions/${id(args.version)}`)
      case 'evidence': return call(`/jobs/${id(args.job)}/evidence/${id(args.ref)}`)
      case 'start': {
        const configuration = await settings()
        return call(`/jobs/${id(args.job)}/start`, 'POST', { key: apiKey, route: configuration.route, limits: configuration.limits,
          amendment: args.amendment || '', scripts: args.scripts === true })
      }
      case 'cancel': return call(`/jobs/${id(args.job)}/cancel`, 'POST', {})
      case 'edit': return call(`/jobs/${id(args.job)}/edit`, 'POST', args.edit)
      case 'export': {
        const destination = await dialog.showSaveDialog(window, { defaultPath: `${String(args.name || 'document').replace(/[<>:"/\\|?*]/g, '_')}.zip`,
          filters: [{ name: 'Portable Markdown package', extensions: ['zip'] }] })
        if (destination.canceled || !destination.filePath) return null
        return call(`/jobs/${id(args.job)}/export`, 'POST', { version_id: args.version, destination: destination.filePath })
      }
      default: throw new Error('This desktop action is not available.')
    }
  })
  window = new BrowserWindow({ width: 1440, height: 940, minWidth: 1080, minHeight: 740, backgroundColor: '#f6f7f9',
    title: 'PDF Markdown Workbench', autoHideMenuBar: true,
    webPreferences: { preload: join(__dirname, '../preload/index.js'), nodeIntegration: false, contextIsolation: true, sandbox: true } })
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.webContents.on('will-navigate', (event) => event.preventDefault())
  window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false))
  window.webContents.session.on('will-download', (event) => event.preventDefault())
  if (!app.isPackaged && process.env.ELECTRON_RENDERER_URL) await window.loadURL(process.env.ELECTRON_RENDERER_URL)
  else await window.loadFile(join(__dirname, '../renderer/index.html'))
  void launchBackend().catch((error: Error) => { startupError = error.message })
})

app.on('window-all-closed', () => app.quit())
app.on('before-quit', () => { stopping = true; child?.kill() })
