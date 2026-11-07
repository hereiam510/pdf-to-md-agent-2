import { test, expect, _electron as electron, type ElectronApplication } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { testRunRoot } from '../support/artifacts'

const fileKey = 'synthetic-file-key-CRED'
const manualKey = 'synthetic-replacement-key-CRED'
const rememberedKey = 'synthetic-remembered-key-CRED'
const fileError = 'Cannot load the development credential file. Use a nonempty UTF-8 file containing one credential, or disable file loading.'
const digest = (key: string) => createHash('sha256').update(key).digest('hex')
const route = { endpoint: 'http://127.0.0.1:1/v1/chat/completions', model: 'synthetic-offline', protocol: 'chat_completions',
  context_tokens: 131072, output_tokens: 8192, image_tokens: 4096, vision: true, timeout_seconds: 180, parameters: {} }
const limits = { max_requests: 12, max_active_seconds: 1200, max_response_repairs: 2, replay_unknown: false, max_attempts_per_request: 1 }
const config = { route, limits, remember: false }
const inspect = (app: ElectronApplication) => app.evaluate(() => {
  const s = (globalThis as any).credentialsTest
  return { calls: s.calls, pending: Object.fromEntries(Object.entries(s.pending).map(([k, v]) => [k, (v as any[]).length])),
    starts: s.starts, spawned: s.spawned, saves: s.saves, results: s.results, capturedSettings: s.capturedSettings }
})
const release = (app: ElectronApplication, name: string) => app.evaluate((_, name) => (globalThis as any).credentialsTest.release(name), name)
const invoke = (app: ElectronApplication, action: string, args: any = {}) => app.evaluate((_, { action, args }) =>
  (globalThis as any).credentialsTest.invoke(action, args), { action, args })
async function begin(app: ElectronApplication, action: string, args: any = {}) {
  await app.evaluate((_, { action, args }) => {
    const s = (globalThis as any).credentialsTest
    s.results ||= []
    void s.invoke(action, args).then((value: any) => s.results.push({ value }), (error: Error) => s.results.push({ error: error.message }))
  }, { action, args })
}
const waitGate = (app: ElectronApplication, name: string) => expect.poll(async () => (await inspect(app)).pending[name] || 0).toBeGreaterThan(0)
async function fixture() {
  const directory = await fs.mkdtemp(join(testRunRoot, 'cr-'))
  await fs.mkdir(join(directory, 'workspace'))
  await fs.writeFile(join(directory, 'connection.json'), JSON.stringify(config, null, 2))
  await fs.writeFile(join(directory, 'key.txt'), fileKey + '\r\n')
  return directory
}
async function open(directory: string, options: any = {}, file = 'key.txt', skip = false) {
  const app = await electron.launch({ args: [resolve('tests/desktop/support/credential-host.cjs')], env: {
    ...process.env, PDFMD_CREDENTIAL_TEST_ROOT: directory, PDFMD_CREDENTIAL_TEST_OPTIONS: JSON.stringify(options),
    PDFMD_DATA: join(directory, 'workspace'), PDFMD_SKIP_CREDENTIAL_FILE: skip ? '1' : '0',
    PDFMD_CREDENTIAL_FILE: file ? join(directory, file) : '' } })
  return { app, page: await app.firstWindow() }
}
async function seed(directory: string) {
  const { app } = await open(directory, {}, '', true)
  try {
    expect((await invoke(app, 'settings')).encryptionAvailable).toBe(true)
    await invoke(app, 'saveSettings', { ...config, key: rememberedKey, remember: true })
  } finally { await app.close() }
}
async function capture(app: ElectronApplication, key: string) {
  await expect.poll(async () => (await invoke(app, 'health')).ready).toBe(true)
  await invoke(app, 'start', { job: 'credential-job' })
  expect((await inspect(app)).starts.at(-1).digest).toBe(digest(key))
}

for (const first of ['file', 'remembered-settings', 'serial']) {
  test(`file precedence: ${first} readiness, no unnecessary remembered decryption`, async () => {
    const directory = await fixture(); await seed(directory)
    const original = await fs.readFile(join(directory, 'connection.json'))
    const { app, page } = await open(directory, { holds: first === 'serial' ? {} : { file: true, raw: true } })
    try {
      if (first !== 'serial') {
        await waitGate(app, 'file'); await waitGate(app, 'raw')
        const gate = first === 'file' ? 'file' : 'raw'
        await release(app, gate)
        expect((await inspect(app)).calls.decrypt || 0).toBe(0)
        await release(app, gate === 'file' ? 'raw' : 'file')
      }
      await expect(page.getByText('Local engine ready')).toBeVisible()
      for (let i = 0; i < 3; i++) expect(await invoke(app, 'settings')).toMatchObject({ hasKey: true, remember: true, route, limits })
      await capture(app, fileKey)
      expect((await inspect(app)).calls.decrypt || 0).toBe(0)
      expect(await fs.readFile(join(directory, 'connection.json'))).toEqual(original)
    } finally { await app.close() }
  })
}

for (const gate of ['file', 'reply']) {
  test(`ordinary Start waits for delayed ${gate}, without settings detour or state repair`, async () => {
    const directory = await fixture()
    const { app, page } = await open(directory, { holds: { [gate]: true } })
    try {
      await waitGate(app, gate)
      await expect(page.locator('.connection-button')).toBeDisabled()
      if (gate === 'reply') {
        await expect(page.getByText('Local engine ready')).toBeVisible()
        await page.getByRole('button', { name: 'Credential fixture' }).click()
        await expect(page.getByRole('button', { name: 'Start conversion' })).toBeDisabled()
      }
      await release(app, gate)
      await expect(page.getByText('Local engine ready')).toBeVisible()
      if (gate === 'file') await page.getByRole('button', { name: 'Credential fixture' }).click()
      await page.getByRole('button', { name: 'Start conversion' }).click()
      await expect.poll(async () => (await inspect(app)).starts.length).toBe(1)
      expect((await inspect(app)).starts[0]).toMatchObject({ digest: digest(fileKey), route, limits })
      expect((await inspect(app)).saves).toBe(0)
      await expect(page.getByRole('heading', { name: 'Nexus connection' })).toHaveCount(0)
      await page.screenshot({ path: join(directory, `start-${gate}.png`) })
    } finally { await app.close() }
  })
}

for (const gate of ['file', 'decrypt', 'encrypt']) for (const clear of [false, true]) {
  test(`${clear ? 'Clear' : 'replacement'} defeats delayed ${gate} completion`, async () => {
    const directory = await fixture()
    if (gate !== 'file') await seed(directory)
    const { app } = await open(directory, { holds: gate === 'encrypt' ? {} : { [gate]: true } }, 'key.txt', gate === 'decrypt')
    try {
      if (gate === 'encrypt') {
        await invoke(app, 'settings')
        await app.evaluate(() => { (globalThis as any).credentialsTest.holds.encrypt = true })
        await begin(app, 'saveSettings', { ...config, key: rememberedKey, remember: true })
      }
      await waitGate(app, gate)
      await begin(app, 'saveSettings', { ...config, route: { ...route, model: 'new-default' },
        key: clear ? '' : manualKey, clearKey: clear, remember: !clear })
      await release(app, gate)
      await expect.poll(async () => (await inspect(app)).results?.length || 0).toBe(gate === 'encrypt' ? 2 : 1)
      const settings = await invoke(app, 'settings')
      expect(settings).toMatchObject({ hasKey: !clear, remember: !clear, route: { model: 'new-default' } })
      await expect.poll(async () => (await inspect(app)).spawned).toBe(1)
      await capture(app, clear ? '' : manualKey)
      const disk = JSON.parse(await fs.readFile(join(directory, 'connection.json'), 'utf8'))
      expect(Boolean(disk.secret)).toBe(!clear)
      expect(JSON.stringify(disk)).not.toContain(manualKey)
      expect((await inspect(app)).calls.file || 0).toBe(gate === 'decrypt' ? 0 : 1)
    } finally { await app.close() }
  })
}

test('Remember uses OS ciphertext across restart; opt-out, uncheck and Clear preserve session intent', async () => {
  const directory = await fixture()
  let { app, page } = await open(directory)
  try {
    await expect(page.getByText('Local engine ready')).toBeVisible()
    await page.locator('.connection-button').click()
    await page.getByLabel('Nexus credential', { exact: true }).fill(manualKey)
    await page.getByLabel('Remember with operating-system encryption').check()
    await page.getByRole('button', { name: 'Save connection' }).click()
    await expect(page.locator('.overlay')).toHaveCount(0)
    await capture(app, manualKey)
    const bytes = await fs.readFile(join(directory, 'connection.json'), 'utf8')
    expect(JSON.parse(bytes).secret).toBeTruthy(); expect(bytes).not.toContain(manualKey)
  } finally { await app.close() }
  ;({ app, page } = await open(directory, {}, 'missing-ignored.txt', true))
  try {
    await expect(page.getByText('Local engine ready')).toBeVisible()
    await capture(app, manualKey)
    expect((await inspect(app)).calls.fileStat || 0).toBe(0)
    await invoke(app, 'saveSettings', { ...config, remember: false })
    await capture(app, manualKey)
    expect(JSON.parse(await fs.readFile(join(directory, 'connection.json'), 'utf8')).secret).toBeUndefined()
    await page.locator('.connection-button').click()
    await page.getByRole('button', { name: 'Clear credential', exact: true }).click()
    await page.getByRole('button', { name: 'Save connection' }).click()
    await expect(page.locator('.overlay')).toHaveCount(0)
    expect(await invoke(app, 'settings')).toMatchObject({ hasKey: false, remember: false })
    await capture(app, '')
  } finally { await app.close() }
  ;({ app } = await open(directory))
  try { await capture(app, fileKey) } finally { await app.close() }
})

test('missing default permits manual entry; alternate selection and packaged exclusion', async () => {
  const directory = await fixture()
  let { app } = await open(directory, {}, '')
  try {
    expect(await invoke(app, 'settings')).toMatchObject({ hasKey: false })
    await invoke(app, 'saveSettings', { ...config, key: manualKey })
    await capture(app, manualKey)
  } finally { await app.close() }
  await fs.writeFile(join(directory, 'default-key.txt'), rememberedKey)
  for (const [file, packaged, key] of [['', false, rememberedKey], ['key.txt', false, fileKey], ['invalid-path', true, '']] as const) {
    ;({ app } = await open(directory, { packaged }, file))
    try {
      await capture(app, key)
      if (packaged) expect((await inspect(app)).calls.fileStat || 0).toBe(0)
    } finally { await app.close() }
  }
  for (const flag of ['-CredentialFile', '-NoCredentialFile']) {
    let output = ''
    try { execFileSync('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', resolve('tools/dev/start.ps1'), '-Packaged', flag,
      ...(flag === '-CredentialFile' ? ['fixture-only'] : [])], { encoding: 'utf8', stdio: 'pipe' }) } catch (error: any) { output = String(error.stderr) }
    expect(output).toContain('Credential-file options apply only to development launches.')
  }
  const manifest = JSON.parse(await fs.readFile('package.json', 'utf8')).build
  expect(manifest.files).toEqual(['out/**', 'package.json'])
  expect(manifest.extraResources.map((r: any) => r.from)).toEqual(['build/engine', 'tools/runtime/ocr-worker.cjs'])
})

for (const invalid of ['missing', 'empty', 'malformed', 'unicode-space', 'utf8', 'large', 'directory', 'unreadable']) {
  test(`invalid selected credential: ${invalid} fails safely before engine startup`, async () => {
    const directory = await fixture()
    const file = join(directory, 'bad')
    if (invalid === 'directory') await fs.mkdir(file)
    else if (invalid !== 'missing') await fs.writeFile(file,
      invalid === 'empty' ? ' \n' : invalid === 'malformed' ? 'synthetic secret\nsecond-line' :
        invalid === 'unicode-space' ? 'synthetic\u00a0secret' : invalid === 'utf8' ? Buffer.from([255]) : invalid === 'large' ? 'x'.repeat(65537) : 'synthetic-unreadable')
    const { app, page } = await open(directory, { unreadable: invalid === 'unreadable' }, 'bad')
    try {
      const settings = await invoke(app, 'settings')
      expect(settings).toMatchObject({ credentialState: 'failed', hasKey: false, route, limits })
      await expect(page.locator('body')).toContainText('Cannot load the development credential file')
      expect(JSON.stringify(settings)).not.toMatch(/synthetic secret|second-line|private error|synthetic-unreadable/)
      expect((await inspect(app)).spawned).toBe(0)
      await expect(page.locator('.connection-button')).toBeEnabled()
    } finally { await app.close() }
  })
}

for (const scenario of [
  { name: 'default read ENOENT after discovery', file: '', fileReadError: 'ENOENT', discovered: true },
  { name: 'explicit read ENOENT after discovery', file: 'key.txt', fileReadError: 'ENOENT', discovered: true },
  { name: 'default read EACCES after discovery', file: '', fileReadError: 'EACCES', discovered: true },
  { name: 'default invalid UTF-8 after discovery', file: '', invalid: true, discovered: true },
  { name: 'default discovery EACCES', file: '', fileStatError: 'EACCES', discovered: false },
  { name: 'explicit discovery ENOENT', file: 'missing-key.txt', discovered: false },
]) {
  test(`CRED-03 ${scenario.name} blocks startup without remembered fallback`, async () => {
    const directory = await fixture(); await seed(directory)
    await fs.writeFile(join(directory, 'default-key.txt'), scenario.invalid ? Buffer.from([255]) : fileKey)
    const original = await fs.readFile(join(directory, 'connection.json'))
    const { app, page } = await open(directory, scenario, scenario.file)
    const logs: string[] = []
    app.process().stdout?.on('data', chunk => logs.push(String(chunk)))
    app.process().stderr?.on('data', chunk => logs.push(String(chunk)))
    try {
      for (let i = 0; i < 3; i++) expect(await invoke(app, 'settings')).toEqual({
        route, limits, remember: true, hasKey: false, encryptionAvailable: true,
        revision: 0, credentialState: 'failed', error: fileError,
      })
      await expect(page.locator('body')).toContainText(fileError)
      await expect.poll(async () => (await invoke(app, 'health')).error).toBe(fileError)
      await expect(invoke(app, 'start', { job: 'credential-job' })).rejects.toThrow(fileError)
      const state = await inspect(app)
      expect(state.calls.fileStat).toBe(1)
      expect(state.calls.fileDiscovered || 0).toBe(scenario.discovered ? 1 : 0)
      expect(state.calls.file || 0).toBe(scenario.discovered ? 1 : 0)
      expect(state.calls.fileReadFailure || 0).toBe(scenario.fileReadError ? 1 : 0)
      expect(state.calls.decrypt || 0).toBe(0)
      expect(state.spawned).toBe(0)
      expect(state.starts).toEqual([])
      expect(await fs.readFile(join(directory, 'connection.json'))).toEqual(original)
      expect(await fs.readdir(join(directory, 'workspace'))).toEqual([])
      const visible = JSON.stringify(state) + logs.join('') + await page.locator('body').innerText()
      expect(visible).not.toMatch(/Synthetic private|ENOENT|EACCES/)
      for (const key of [fileKey, rememberedKey]) expect(visible).not.toContain(key)
      await expect(page.locator('.connection-button')).toBeEnabled()
    } finally { await app.close() }
  })
}

for (const mode of ['unavailable', 'decryptFailure', 'reencrypt']) {
  test(`remembered storage ${mode} preserves safe settings and newer choices`, async () => {
    const directory = await fixture(); await seed(directory)
    const { app } = await open(directory, { [mode]: true, holds: mode === 'reencrypt' ? { encrypt: true } : {} }, '', true)
    try {
      if (mode === 'reencrypt') {
        await waitGate(app, 'encrypt')
        await begin(app, 'saveSettings', { ...config, clearKey: true })
        await release(app, 'encrypt')
      }
      expect(await invoke(app, 'settings')).toMatchObject({ hasKey: false, credentialState: 'ready' })
      await invoke(app, 'saveSettings', { ...config, key: manualKey, remember: true })
      await capture(app, manualKey)
      expect(Boolean(JSON.parse(await fs.readFile(join(directory, 'connection.json'), 'utf8')).secret)).toBe(mode !== 'unavailable')
    } finally { await app.close() }
  })
}

test('Start reads the current accepted key after delayed job lookup and retains task settings', async () => {
  const directory = await fixture(); const { app } = await open(directory)
  try {
    await invoke(app, 'settings')
    await expect.poll(async () => (await inspect(app)).spawned).toBe(1)
    await app.evaluate(() => { const s = (globalThis as any).credentialsTest; s.holds.job = true; s.configured = true })
    await begin(app, 'start', { job: 'credential-job' }); await waitGate(app, 'job')
    await invoke(app, 'saveSettings', { ...config, key: manualKey })
    await release(app, 'job')
    await expect.poll(async () => (await inspect(app)).starts.length).toBe(1)
    expect((await inspect(app)).starts[0]).toEqual({ digest: digest(manualKey), amendment: '', scripts: false })
    await invoke(app, 'taskSettings', { job: 'credential-job', route: { context_tokens: 9000 }, limits: { max_requests: 5 } })
    const state = await app.evaluate(() => (globalThis as any).credentialsTest.taskSettings)
    expect(state).toEqual({ route: { context_tokens: 9000 }, limits: { max_requests: 5 } })
    expect(JSON.stringify(await inspect(app))).not.toContain(manualKey)
    expect((await fs.readdir(join(directory, 'workspace')))).toEqual([])
  } finally { await app.close() }
})

for (const clear of [true, false]) test(`older save reply cannot undo newer ${clear ? 'Clear' : 'replacement'} in the actual renderer`, async () => {
  const directory = await fixture(); const { app, page } = await open(directory, { holds: { saveReply: true } })
  try {
    await expect(page.locator('.connection-button')).toBeEnabled()
    await page.locator('.connection-button').click()
    if (clear) await page.getByLabel('Nexus credential', { exact: true }).fill(manualKey)
    else await page.getByRole('button', { name: 'Clear credential', exact: true }).click()
    await page.getByLabel('Model alias').fill('older-default')
    await page.getByRole('button', { name: 'Save connection' }).click()
    await waitGate(app, 'saveReply')
    await page.getByRole('button', { name: 'Close settings' }).click()
    await page.locator('.connection-button').click()
    await page.getByLabel('Model alias').fill('newer-default')
    if (clear) await page.getByRole('button', { name: 'Clear credential', exact: true }).click()
    else await page.getByLabel('Nexus credential', { exact: true }).fill(manualKey)
    await page.getByRole('button', { name: 'Save connection' }).click()
    await expect.poll(async () => (await inspect(app)).pending.saveReply).toBe(2)
    await app.evaluate(() => (globalThis as any).credentialsTest.settle('saveReply', 1))
    await expect(page.locator('.overlay')).toHaveCount(0)
    await release(app, 'saveReply')
    await expect(page.locator('.connection-button')).toContainText('newer-default')
    await page.locator('.connection-button').click()
    await expect(page.getByLabel('Nexus credential', { exact: true })).toHaveAttribute('placeholder', clear ? 'Enter credential' : 'Saved credential — leave blank to keep')
    expect(await invoke(app, 'settings')).toMatchObject({ hasKey: !clear, revision: 2 })
  } finally { await app.close() }
})

test('Start waits for an earlier accepted Remember save and never exposes its key', async () => {
  const directory = await fixture(); const { app, page } = await open(directory)
  const logs: string[] = []
  app.process().stdout?.on('data', chunk => logs.push(String(chunk)))
  app.process().stderr?.on('data', chunk => logs.push(String(chunk)))
  try {
    await expect(page.getByText('Local engine ready')).toBeVisible()
    await app.evaluate(() => { (globalThis as any).credentialsTest.holds.encrypt = true })
    await begin(app, 'saveSettings', { ...config, key: manualKey, remember: true })
    await waitGate(app, 'encrypt')
    await begin(app, 'start', { job: 'credential-job' })
    await expect.poll(async () => (await inspect(app)).calls.startAction || 0).toBe(1)
    expect((await inspect(app)).calls.job || 0).toBe(0)
    expect((await inspect(app)).starts).toHaveLength(0)
    await release(app, 'encrypt')
    await expect.poll(async () => (await inspect(app)).starts.length).toBe(1)
    expect((await inspect(app)).starts[0].digest).toBe(digest(manualKey))
    const visible = JSON.stringify(await inspect(app)) + logs.join('') + await page.locator('body').innerText()
    expect(visible).not.toContain(manualKey); expect(visible).not.toContain(fileKey)
    expect(await fs.readdir(join(directory, 'workspace'))).toEqual([])
  } finally { await app.close() }
})

test('remembered key rotation rewrites only the secret; encryption failure is safe and recoverable', async () => {
  const directory = await fixture(); await seed(directory)
  const before = JSON.parse(await fs.readFile(join(directory, 'connection.json'), 'utf8'))
  const { app } = await open(directory, { reencrypt: true }, '', true)
  try {
    await capture(app, rememberedKey)
    const after = JSON.parse(await fs.readFile(join(directory, 'connection.json'), 'utf8'))
    expect(after).toMatchObject({ route, limits, remember: true })
    expect(after.secret).not.toBe(before.secret)
    await app.evaluate(() => { (globalThis as any).credentialsTest.encryptFailure = true })
    await expect(invoke(app, 'saveSettings', { ...config, key: manualKey, remember: true })).rejects.toThrow('Cannot save connection settings')
    expect(JSON.parse(await fs.readFile(join(directory, 'connection.json'), 'utf8'))).toEqual(after)
    await app.evaluate(() => { (globalThis as any).credentialsTest.encryptFailure = false })
    await invoke(app, 'saveSettings', { ...config, clearKey: true })
    await capture(app, '')
  } finally { await app.close() }
})

test('missing default restores remembered key without rewriting connection bytes', async () => {
  const directory = await fixture(); await seed(directory)
  const original = await fs.readFile(join(directory, 'connection.json'))
  const { app } = await open(directory, {}, '')
  try {
    await capture(app, rememberedKey)
    expect((await inspect(app)).calls.fileStat).toBe(1)
    expect((await inspect(app)).calls.fileDiscovered || 0).toBe(0)
    expect((await inspect(app)).calls.file || 0).toBe(0)
    expect((await inspect(app)).calls.decrypt).toBe(1)
    for (let i = 0; i < 3; i++) await invoke(app, 'settings')
    expect((await inspect(app)).calls.decrypt).toBe(1)
    expect(await fs.readFile(join(directory, 'connection.json'))).toEqual(original)
  } finally { await app.close() }
})
