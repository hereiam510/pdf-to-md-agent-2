import { test, expect, _electron as electron } from '@playwright/test'
import type { Page } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { join, resolve } from 'node:path'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { testRunRoot } from '../support/artifacts'

// T3a: new saves produced by the production edit path (not snapshots) carry
// their hyperlinked images, survive close/relaunch, open natively, Return, and
// export a ZIP whose relative links resolve after relocation.

async function nativeLink(page: Page, name: string) {
  const link = page.frameLocator('iframe').getByRole('link', { name, exact: true })
  await link.scrollIntoViewIfNeeded()
  // Wait for stable frame/target geometry; never synthesize a DOM click.
  let previous = '', stableSince = Date.now()
  await expect.poll(async () => {
    const state = JSON.stringify([await page.locator('iframe').getAttribute('name'),
      await page.locator('iframe').boundingBox(), await link.boundingBox()])
    if (state !== previous) { previous = state; stableSince = Date.now() }
    return Date.now() - stableSince >= 1000
  }, { timeout: 10000, intervals: [100] }).toBe(true)
  await link.click()
}

async function viewImage(page: Page, name: string, size: number[]) {
  await nativeLink(page, name)
  await expect.poll(() => page.frames().some(f => f.url().startsWith('pdfmd-preview://snapshot/'))).toBe(true)
  const image = page.frameLocator('iframe').locator('img')
  await image.evaluate(async item => (item as HTMLImageElement).decode())
  expect(await image.evaluate(item => [(item as HTMLImageElement).naturalWidth, (item as HTMLImageElement).naturalHeight])).toEqual(size)
}

async function returnDocument(page: Page, text: string) {
  const previous = await page.locator('iframe').getAttribute('name').catch(() => null)
  await page.getByRole('button', { name: 'Return to document' }).click()
  await expect.poll(() => page.locator('iframe').getAttribute('name')).not.toBe(previous)
  await expect(page.frameLocator('iframe').getByText(text, { exact: false })).toBeVisible()
}

test('T3a new hyperlink and mixed saves reopen, open natively, return and export relocatable ZIPs', async () => {
  test.setTimeout(240000)
  const directory = await fs.mkdtemp(join(testRunRoot, 'portable-link-'))
  const fixtureCommand = (command: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
    ['-X', 'utf8', '-m', 'tests.desktop.fixtures.portable_link_save', command, directory], { windowsHide: true, encoding: 'utf-8' }))
  const fixture = fixtureCommand('prepare')
  const launch = () => electron.launch({ args: [resolve('tests/desktop/support/reference-workbench.cjs')], env: { ...process.env,
    PDFMD_UI_PROFILE: join(directory, 'profile'), PDFMD_DATA: join(directory, 'workspace'),
    PDFMD_PYTHON: resolve('.venv/Scripts/python.exe'), PDFMD_SKIP_CREDENTIAL_FILE: '1', ELECTRON_RENDERER_URL: '' } })
  const reads = async () => (await app.evaluate(() => (globalThis as any).referenceControl.calls)).filter((c: any) => c.action === 'version').length
  let app = await launch()
  let page: Page
  const requests: string[] = []
  const observations: unknown[] = []
  const versions = [[fixture.link, 'link', 'Source pages'], [fixture.mixed, 'mixed', 'Mixed section']] as const
  try {
    for (const stage of ['opened', 'relaunched']) {
      page = await app.firstWindow()
      page.on('request', request => { if (request.url().startsWith('http')) requests.push(request.url()) })
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').filter({ hasText: 'T3a portable links' }).click()
      for (const [version, label, text] of versions) {
        await page.getByLabel('Saved version').selectOption(version)
        await expect(page.getByRole('button', { name: 'Return to document' })).toBeVisible()
        await expect(page.locator('.asset-reference-status')).toHaveCount(0) // ok diagnosis is not shown
        if (label === 'mixed') {
          const inline = page.frameLocator('iframe').locator('img')
          await expect(inline).toHaveCount(1)
          await inline.evaluate(async item => (item as HTMLImageElement).decode())
        }
        const count = await reads()
        await viewImage(page, 'Open page 1', fixture.render_size)
        await page.screenshot({ path: join(directory, `${stage}-${label}-page.png`) })
        await returnDocument(page, text)
        await viewImage(page, 'Open figure', fixture.figure_size)
        await returnDocument(page, text)
        expect(await reads()).toBe(count)
        if (stage === 'relaunched') {
          const destination = join(directory, `${label}.zip`)
          await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, destination)
          await page.getByRole('button', { name: 'Export ZIP' }).click()
          await expect(page.locator('.toast.success')).toContainText('ZIP bytes verified. Asset references: ok')
          await page.locator('.toast.success').waitFor({ state: 'detached', timeout: 15000 }).catch(() => {})
        }
        observations.push({ stage, version, label, page_link_opened: true, figure_link_opened: true, return_without_version_read: true })
      }
      if (stage === 'opened') { await app.close(); app = await launch() }
    }
    const served = await app.evaluate(() => (globalThis as any).referenceControl.responses)
    for (const path of [fixture.render, fixture.figure]) {
      const bytes = await fs.readFile(join(directory, 'workspace', 'versions', fixture.link, path))
      expect(served.some((r: any) => r.status === 200 && r.length === bytes.length &&
        r.sha256 === createHash('sha256').update(bytes).digest('hex'))).toBe(true)
    }
    expect(requests.filter(url => url.includes('example.invalid'))).toEqual([])
    const calls = await app.evaluate(() => (globalThis as any).referenceControl.calls)
    expect(calls.some((c: any) => ['start', 'continue'].includes(c.action))).toBe(false)
  } finally { await app.close() }
  const verification = fixtureCommand('verify')
  await fs.writeFile(join(directory, 'desktop-verification.json'), JSON.stringify({ observations, verification }, null, 2))
})
