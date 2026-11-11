import { test, expect, _electron as electron } from '@playwright/test'
import type { ElectronApplication, Page } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { join, resolve } from 'node:path'
import { execFileSync } from 'node:child_process'
import { testRunRoot } from '../support/artifacts'
import { createServer } from 'vite'
import { createHash } from 'node:crypto'

const hold = (app: ElectronApplication, value: boolean) => app.evaluate((_electron, value) => {
  (globalThis as any).referenceControl.hold = value
}, value)
const pending = (app: ElectronApplication) => app.evaluate(() => (globalThis as any).referenceControl.pending.length)
const settle = (app: ElectronApplication, index: number, fail = false) => app.evaluate((_electron, { index, fail }) => {
  (globalThis as any).referenceControl.settle(index, fail)
}, { index, fail })
const calls = (app: ElectronApplication) => app.evaluate(() => (globalThis as any).referenceControl.calls)
const reads = async (app: ElectronApplication) => (await calls(app)).filter((c: any) => c.action === 'version').length

async function nativeLink(page: Page, name: string) {
  const link = page.frameLocator('iframe').getByRole('link', { name, exact: true })
  await link.scrollIntoViewIfNeeded()
  // Chromium can silently discard input to recently moved cross-origin frames.
  // Observe a full second of stable frame/target geometry; never disable that
  // protection, synthesize a DOM click or retry a discarded native click.
  let previous = '', stableSince = Date.now()
  await expect.poll(async () => {
    const state = JSON.stringify([await page.locator('iframe').getAttribute('name'),
      await page.locator('iframe').boundingBox(), await link.boundingBox()])
    if (state !== previous) { previous = state; stableSince = Date.now() }
    return Date.now() - stableSince >= 1000
  }, { timeout: 10000, intervals: [100] }).toBe(true)
  await link.click()
}

async function viewImage(page: Page, width: number, height: number) {
  await nativeLink(page, 'Open selected image')
  await expect.poll(() => page.frames().some(f => f.url().startsWith('pdfmd-preview://snapshot/'))).toBe(true)
  const image = page.frameLocator('iframe').locator('img')
  await image.evaluate(async item => (item as HTMLImageElement).decode())
  expect(await image.evaluate(item => [(item as HTMLImageElement).naturalWidth, (item as HTMLImageElement).naturalHeight])).toEqual([width, height])
}

async function returnDocument(page: Page) {
  const previous = await page.locator('iframe').getAttribute('name').catch(() => null)
  await page.getByRole('button', { name: 'Return to document' }).click()
  await expect.poll(() => page.locator('iframe').getAttribute('name')).not.toBe(previous)
  await expect.poll(() => page.frames().some(f => f !== page.mainFrame() && f.url() === 'about:srcdoc')).toBe(true)
  const frame = page.frames().find(f => f !== page.mainFrame() && f.url() === 'about:srcdoc')!
  await frame.waitForLoadState('load')
  await page.frameLocator('iframe').locator('img').evaluateAll(async images => Promise.all(images.map(i => (i as HTMLImageElement).decode())))
}

for (const shell of ['file', 'development-url']) test(`normal isolated desktop (${shell}) uses selected immutable references, returns, diagnoses and rejects stale loads`, async () => {
  test.setTimeout(240000)
  const directory = await fs.mkdtemp(join(testRunRoot, 'asset-references-'))
  const fixtureCommand = (command: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
    ['-X', 'utf8', '-m', 'tests.desktop.fixtures.asset_references', command, directory], { windowsHide: true, encoding: 'utf-8' }))
  const fixture = fixtureCommand('prepare')
  const server = shell === 'development-url' ? await createServer({ configFile: false, root: resolve('src/renderer'),
    server: { host: '127.0.0.1', port: 0, hmr: false } }) : null
  await server?.listen()
  const rendererURL = server?.resolvedUrls?.local[0] || ''
  const launch = () => electron.launch({ args: [resolve('tests/desktop/support/reference-workbench.cjs')], env: { ...process.env,
    PDFMD_UI_PROFILE: join(directory, 'profile'), PDFMD_DATA: join(directory, 'workspace'),
    PDFMD_PYTHON: resolve('.venv/Scripts/python.exe'), PDFMD_SKIP_CREDENTIAL_FILE: '1', ELECTRON_RENDERER_URL: rendererURL } })
  let app = await launch()
  const observations: unknown[] = []
  const requests: string[] = []
  const browserMessages: string[] = []
  const addresses = new Map<string, string>()
  let page: Page
  const recordNetwork = async (name: string) => fs.writeFile(join(directory, name), JSON.stringify(await app.evaluate(() => ({
    network: (globalThis as any).referenceControl.network, responses: (globalThis as any).referenceControl.responses
  })), null, 2))
  try {
    for (const stage of ['opened', 'reopened']) {
      page = await app.firstWindow()
      page.on('console', message => { if (message.type() === 'warning' || message.type() === 'error') browserMessages.push(message.text()) })
      page.on('request', request => { if (request.url().startsWith('http') && !request.url().startsWith(rendererURL || 'unused:')) requests.push(request.url()) })
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').filter({ hasText: 'T2 references' }).click()
      for (const version of [fixture.link, fixture.mixed]) {
        await page.getByLabel('Saved version').selectOption(version)
        await expect(page.getByRole('button', { name: 'Return to document' })).toBeVisible()
        await expect(page.locator('iframe')).toHaveAttribute('sandbox', '')
        const images = page.frameLocator('iframe').locator('img')
        await expect(images).toHaveCount(version === fixture.mixed ? 5 : 0)
        if (version === fixture.mixed) {
          await images.evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
          expect(await images.evaluateAll(items => items.map(item => [(item as HTMLImageElement).naturalWidth, (item as HTMLImageElement).naturalHeight])))
            .toEqual([...Array(4).fill([fixture.large_width, fixture.large_height]), [fixture.width, fixture.height]])
          expect(await page.getAttribute('body', 'data-source-script')).toBeNull()
          const frame = page.frames().find(f => f !== page.mainFrame())!
          expect(await frame.evaluate(() => { try { return Boolean(parent.document.body) } catch { return false } })).toBe(false)
          await nativeLink(page, 'External citation')
          // CSP may replace the attempted external navigation with its blocked
          // error frame before Electron emits a navigation event. Return still
          // restores the selected snapshot without allowing a network request.
          await returnDocument(page)
          await expect(page.frameLocator('iframe').getByText('Mixed fixture', { exact: false })).toBeVisible()
          await nativeLink(page, 'New window')
          expect(app.windows()).toHaveLength(1)
          await returnDocument(page)
        }
        const count = await reads(app)
        const address = await page.frameLocator('iframe').getByRole('link', { name: 'Open selected image', exact: true }).getAttribute('href')
        if (stage === 'reopened') expect(address).not.toBe(addresses.get(version))
        addresses.set(version, address!)
        await viewImage(page, fixture.width, fixture.height)
        await page.screenshot({ path: join(directory, `${stage}-${version === fixture.link ? 'link' : 'mixed'}-image.png`) })
        await returnDocument(page)
        await expect(page.frameLocator('iframe').getByRole('link', { name: 'Open selected image', exact: true })).toBeVisible()
        if (version === fixture.mixed) {
          await nativeLink(page, 'HTML image link')
          const image = page.frameLocator('iframe').locator('img')
          await expect(image).toHaveCount(1)
          await image.evaluate(async item => (item as HTMLImageElement).decode())
          expect(await image.evaluate(item => [(item as HTMLImageElement).naturalWidth, (item as HTMLImageElement).naturalHeight])).toEqual([fixture.width, fixture.height])
          await returnDocument(page)
          await expect(page.frameLocator('iframe').getByRole('link', { name: 'HTML image link', exact: true })).toBeVisible()
          await nativeLink(page, 'Linked thumbnail')
          const jpeg = page.frameLocator('iframe').locator('img')
          await jpeg.evaluate(async item => (item as HTMLImageElement).decode())
          expect(await jpeg.evaluate(item => [(item as HTMLImageElement).naturalWidth, (item as HTMLImageElement).naturalHeight])).toEqual([512, 512])
          await returnDocument(page)
        }
        expect(await reads(app)).toBe(count)
        observations.push({ stage, version, image_decoded: true, html_link_opened: version === fixture.mixed, return_without_version_read: true })
      }
      if (stage === 'opened') { await recordNetwork('opened-network.json'); await app.close(); app = await launch() }
    }
    page = await app.firstWindow()
    observations.push({ runtime: await app.evaluate(() => ({ electron: process.versions.electron, chromium: process.versions.chrome })) })
    // The preserved AR-T2-01 bytes now travel outside the navigation URL.
    await page.getByLabel('Saved version').selectOption(fixture.large_link)
    const largeImages = page.frameLocator('iframe').locator('img')
    await expect(largeImages).toHaveCount(4)
    await largeImages.evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
    const largeHref = await page.frameLocator('iframe').getByRole('link', { name: 'Large selected image' }).getAttribute('href')
    expect(largeHref!.length).toBeLessThan(200)
    await nativeLink(page, 'Large selected image')
    const largeImage = page.frameLocator('iframe').locator('img')
    await largeImage.evaluate(async item => (item as HTMLImageElement).decode())
    expect(await largeImage.evaluate(item => [(item as HTMLImageElement).naturalWidth, (item as HTMLImageElement).naturalHeight])).toEqual([fixture.large_width, fixture.large_height])
    await page.screenshot({ path: join(directory, 'large-link-opened.png') })
    await returnDocument(page)
    await expect(page.frameLocator('iframe').getByText('Large-link control', { exact: false })).toBeVisible()
    observations.push({ finding: 'AR-T2-01', image_bytes: fixture.large_bytes, protocol_url_characters: largeHref!.length, large_embeds_decoded: 4, large_link_opened: true })
    const served = await app.evaluate(() => (globalThis as any).referenceControl.responses)
    await fs.writeFile(join(directory, 'served-resources.json'), JSON.stringify(served, null, 2))
    const selected = await fs.readFile(join(directory, 'workspace', 'versions', fixture.large_link,
      Object.keys(fixture.versions[fixture.large_link]).find(n => n.startsWith('assets/') && fixture.versions[fixture.large_link][n] === '700c083b0861ab1dd9a952a154f66c815277a04a2edb0bb63a872238312744c6')!))
    expect(served.some((r: any) => r.url === largeHref && r.status === 200 && r.length === selected.length &&
      r.sha256 === createHash('sha256').update(selected).digest('hex'))).toBe(true)
    const jpegBytes = await fs.readFile(join(directory, 'workspace', 'versions', fixture.mixed, fixture.jpeg_asset))
    expect(served.some((r: any) => r.status === 200 && r.headers['content-type'] === 'image/jpeg' &&
      r.length === jpegBytes.length && r.sha256 === createHash('sha256').update(jpegBytes).digest('hex'))).toBe(true)
    // A main-process fetch lacks a requesting frame. Opaque origin is no grant.
    expect(await app.evaluate(async ({ net }, url) => {
      try { return (await net.fetch(url, { headers: { Origin: 'null' } })).status } catch { return 403 }
    }, largeHref!)).toBe(403)
    expect(await app.evaluate(async ({ BrowserWindow, session }, url) => {
      const other = new BrowserWindow({ show: false, webPreferences: { sandbox: true, contextIsolation: true, nodeIntegration: false } })
      try {
        await other.loadURL('about:blank')
        const denied = await other.webContents.executeJavaScript(`new Promise(resolve => {const i = new Image(); setTimeout(() => resolve('timeout'), 5000); i.onload = () => resolve(false); i.onerror = () => resolve(true); i.src = ${JSON.stringify(url)}; document.body.append(i)})`)
        let foreignDenied = false
        try { const response = await session.fromPartition('t2-foreign').fetch(url, { signal: AbortSignal.timeout(5000) }); foreignDenied = response.status !== 200 } catch { foreignDenied = true }
        return denied === true && foreignDenied
      } finally { other.destroy() }
    }, largeHref!)).toBe(true)
    const previewFrame = page.frames().find(f => f !== page.mainFrame())!
    await previewFrame.evaluate(url => {
      for (const [index, src] of [url + '?forged=1', url + '#forged', url.replace(/.$/, 'X'),
        url + '/extra', url.replace('/snapshot/', '/foreign/')].entries()) {
        const i = new Image(); i.dataset.forged = String(index); i.src = src; document.body.append(i)
      }
    }, largeHref!)
    await expect.poll(() => previewFrame.evaluate(() => Array.from(document.querySelectorAll<HTMLImageElement>('img[data-forged]')).map(i => [i.complete, i.naturalWidth])))
      .toEqual(Array(5).fill([true, 0]))
    await previewFrame.evaluate(() => document.querySelectorAll('img[data-forged]').forEach(i => i.remove()))
    // The trusted shell and an unrelated sandbox frame may know a URL, but
    // neither is the registered preview frame. Observe their native denials.
    await page.evaluate(async url => {
      await new Promise<void>(resolve => {
        setTimeout(resolve, 5000)
        const image = new Image(); image.onload = image.onerror = () => { image.remove(); resolve() }; image.src = url; document.body.append(image)
      })
      const frame = document.createElement('iframe'); frame.name = 'unrelated'; frame.sandbox.value = ''
      frame.srcdoc = `<img src="${url}">`; document.body.append(frame)
    }, largeHref!)
    await expect.poll(async () => (await app.evaluate(() => (globalThis as any).referenceControl.network)).filter((n: any) => n.url === largeHref && n.cancel).length).toBeGreaterThanOrEqual(3)
    await page.locator('iframe[name="unrelated"]').evaluate(frame => frame.remove())
    const beforeTabs = await reads(app)
    await page.getByRole('button', { name: 'Markdown', exact: true }).click()
    await expect(page.locator('iframe')).toHaveCount(0)
    await page.getByRole('button', { name: 'Preview', exact: true }).click()
    await page.frameLocator('iframe').locator('img').first().evaluate(async image => (image as HTMLImageElement).decode())
    expect(await reads(app)).toBe(beforeTabs)
    await page.getByLabel('Saved version').selectOption(fixture.link)
    await viewImage(page, fixture.width, fixture.height)
    const advanced = fixtureCommand('advance')
    await expect(page.getByLabel('Saved version').locator('option').first()).toHaveAttribute('value', advanced.version, { timeout: 10000 })
    await expect(page.getByLabel('Saved version')).toHaveValue(fixture.link)
    const destination = join(directory, 'link.zip')
    await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, destination)
    await page.getByRole('button', { name: 'Export ZIP' }).click()
    await expect(page.locator('.toast.success')).toContainText('ZIP bytes verified. Asset references: ok')
    expect((await calls(app)).filter((c: any) => c.action === 'export').at(-1)).toMatchObject({ job: fixture.job, version: fixture.link })
    await page.getByRole('button', { name: 'Export ZIP' }).click() // exact repeated export
    await returnDocument(page)

    // A transfer failure keeps raw inspection/export and the real assessment,
    // while publishing no partial preview or stale Return action.
    await app.evaluate(() => { (globalThis as any).referenceControl.transferFault = true })
    await page.getByLabel('Saved version').selectOption(fixture.mixed)
    await expect(page.getByRole('alert')).toContainText('Preview unavailable')
    await expect(page.getByRole('button', { name: 'Return to document' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Export ZIP' })).toBeEnabled()
    await expect(page.locator('.asset-reference-status')).toHaveCount(0) // Existing UI omits an ok diagnosis.
    await page.getByRole('button', { name: 'Markdown', exact: true }).click()
    await expect(page.locator('.markdown-view')).toContainText('Mixed fixture')
    await page.getByRole('button', { name: 'Preview', exact: true }).click()
    await app.evaluate(() => { (globalThis as any).referenceControl.transferFault = false })
    await page.getByRole('button', { name: 'Retry loading version' }).click()
    await expect(page.getByRole('button', { name: 'Return to document' })).toBeVisible()
    const retryHref = await page.frameLocator('iframe').getByRole('link', { name: 'Open selected image', exact: true }).getAttribute('href')
    expect(retryHref).not.toBe(largeHref)
    await page.getByLabel('Saved version').selectOption(fixture.link)
    await expect(page.frameLocator('iframe').getByText('Hyperlink fixture', { exact: false })).toBeVisible()
    await expect(page.locator('.toast.success')).toHaveCount(0)
    await page.frames().find(f => f !== page.mainFrame())!.evaluate(url => {
      const i = new Image(); i.dataset.revoked = 'true'; i.src = url; document.body.append(i)
    }, largeHref!)
    await expect.poll(() => page.frameLocator('iframe').locator('img[data-revoked]').evaluate(i => [(i as HTMLImageElement).complete, (i as HTMLImageElement).naturalWidth])).toEqual([true, 0])


    await hold(app, true)
    await page.getByLabel('Saved version').selectOption(fixture.mixed)
    await expect.poll(() => pending(app)).toBe(1)
    await expect(page.locator('iframe')).toHaveCount(0)
    await expect(page.locator('.toast.success')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Return to document' })).toHaveCount(0)
    await page.getByLabel('Saved version').selectOption(fixture.incomplete)
    await expect.poll(() => pending(app)).toBe(2)
    await settle(app, 1)
    await expect(page.locator('.asset-reference-status')).toContainText('Asset references: incomplete')
    await settle(app, 0)
    await expect(page.locator('.asset-reference-status')).toContainText('does not contain this asset')
    await expect(page.frameLocator('iframe').getByText('Missing source')).toBeVisible()
    await expect(page.frameLocator('iframe').locator('a[href]')).toHaveCount(0)
    await page.screenshot({ path: join(directory, 'historical-incomplete.png') })
    await hold(app, false)
    await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, join(directory, 'incomplete.zip'))
    await page.getByRole('button', { name: 'Export ZIP' }).click()
    await expect(page.locator('.toast.success')).toContainText('ZIP bytes verified. Asset references: incomplete')
    await page.getByRole('button', { name: 'Markdown', exact: true }).click()
    await expect(page.locator('.markdown-view')).toContainText(fixture.asset)
    await page.getByRole('button', { name: 'Preview', exact: true }).click()

    await hold(app, true)
    await page.getByLabel('Saved version').selectOption(fixture.link)
    await expect.poll(() => pending(app)).toBe(1)
    await page.getByLabel('Saved version').selectOption(fixture.mixed)
    await expect.poll(() => pending(app)).toBe(2)
    await settle(app, 1, true)
    await expect(page.getByRole('alert')).toContainText('Could not load the selected version')
    await settle(app, 0)
    await expect(page.locator('iframe')).toHaveCount(0)
    await expect(page.locator('.asset-reference-status')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Return to document' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Export ZIP' })).toBeDisabled()
    await hold(app, false)
    await page.getByRole('button', { name: 'Retry loading version' }).click()
    await expect(page.getByRole('button', { name: 'Return to document' })).toBeVisible()
    await viewImage(page, fixture.width, fixture.height)
    await page.getByRole('button', { name: 'Rebuild from this version' }).click()
    await expect(page.getByRole('button', { name: 'Export ZIP' })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'Return to document' })).toHaveCount(0)
    await expect(page.locator('iframe')).toHaveCount(0)
    await page.getByRole('button', { name: 'Discard edits' }).click()
    await expect(page.frameLocator('iframe').getByText('Mixed fixture', { exact: false })).toBeVisible()

    await page.getByLabel('Saved version').selectOption(fixture.unavailable)
    await expect(page.locator('.asset-reference-status')).toContainText('Asset references: unavailable')
    await expect(page.frameLocator('iframe').locator('a[href]')).toHaveCount(0)
    await expect(page.frameLocator('iframe').getByText('Unavailable source')).toBeVisible()
    await page.getByLabel('Saved version').selectOption(fixture.unsupported)
    await expect(page.locator('.asset-reference-status')).toContainText('Asset references: incomplete')
    await expect(page.frameLocator('iframe').getByText('remote alt (image unavailable)')).toBeVisible()

    await hold(app, true)
    await page.getByLabel('Saved version').selectOption(fixture.link)
    await expect.poll(() => pending(app)).toBe(1)
    await page.getByLabel('Saved version').selectOption(fixture.mixed)
    await expect.poll(() => pending(app)).toBe(2)
    await page.getByLabel('Saved version').selectOption(fixture.link)
    await expect.poll(() => pending(app)).toBe(3)
    await settle(app, 2)
    const latestHref = await page.frameLocator('iframe').getByRole('link', { name: 'Open selected image', exact: true }).getAttribute('href')
    await settle(app, 0, true) // Old same-pair failure must not hide a newer success.
    await settle(app, 0) // Old different-pair success cannot revive its lease.
    await expect(page.frameLocator('iframe').getByRole('link', { name: 'Open selected image', exact: true })).toHaveAttribute('href', latestHref!)
    await hold(app, false)

    await hold(app, true)
    await page.getByLabel('Saved version').selectOption(fixture.incomplete)
    await expect.poll(() => pending(app)).toBe(1)
    await page.locator('.document-item').filter({ hasText: 'T2 other task' }).click()
    await expect.poll(() => pending(app)).toBe(2)
    await expect(page.getByRole('button', { name: 'Return to document' })).toHaveCount(0)
    await settle(app, 1)
    await expect(page.frameLocator('iframe').getByText('Other task marker')).toBeVisible()
    await settle(app, 0)
    await expect(page.locator('.asset-reference-status')).toHaveCount(0)
    await hold(app, false)
    await page.locator('.document-item').filter({ hasText: 'T2 corrupt' }).click()
    await expect(page.getByRole('alert')).toContainText('integrity verification')
    await expect(page.getByRole('button', { name: 'Export ZIP' })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Return to document' })).toHaveCount(0)
    await page.screenshot({ path: join(directory, 'registered-corruption.png') })

    // A new renderer starts in the existing default-follow-head mode.
    await recordNetwork('checked-network.json')
    await app.close(); app = await launch()
    page = await app.firstWindow()
    await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
    await page.locator('.document-item').filter({ hasText: 'T2 references' }).click()
    await expect(page.frameLocator('iframe').getByText('Advanced head marker')).toBeVisible()
    const next = fixtureCommand('advance')
    await expect(page.getByLabel('Saved version')).toHaveValue(next.version, { timeout: 10000 })
    await expect(page.frameLocator('iframe').getByText('Advanced head marker')).toBeVisible()
    expect(requests.filter(url => url.includes('example.invalid'))).toEqual([])
    const finalCalls = await calls(app)
    expect(finalCalls.some((c: any) => ['start', 'continue'].includes(c.action))).toBe(false)
    observations.push({ actual_desktop: true, explicit_selection_retained: true, default_follow_head: true,
      late_success_and_failure_ignored: true, task_switch: true, editor_invalidates_return: true,
      external_requests: requests, integrity_failure_distinct: true, large_repeated_bytes: fixture.large_bytes })
  } finally { await page!.screenshot({ path: join(directory, 'final-observation.png') }).catch(() => {}); await fs.writeFile(join(directory, 'browser-messages.json'), JSON.stringify(browserMessages, null, 2)); await fs.writeFile(join(directory, 'network.json'), JSON.stringify(await app.evaluate(() => ({ network: (globalThis as any).referenceControl.network, responses: (globalThis as any).referenceControl.responses })), null, 2)); await app.close(); await server?.close() }
  const verification = fixtureCommand('verify')
  await fs.writeFile(join(directory, 'desktop-verification.json'), JSON.stringify({ shell, renderer_url: rendererURL, observations, verification }, null, 2))
})
