import { test, expect, _electron as electron } from '@playwright/test'
import type { Page } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { join, resolve } from 'node:path'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { testRunRoot } from '../support/artifacts'

// T3b: an enriched schema 2 save (readable non-ASCII names, embedded primary XMP,
// DCT JPEG original) produced by the production edit path survives close/relaunch,
// opens natively, Returns, and exports a ZIP whose relative links resolve after relocation.

async function nativeLink(page: Page, name: string) {
  const link = page.frameLocator('iframe').getByRole('link', { name, exact: true })
  await link.scrollIntoViewIfNeeded()
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

test('T3b enriched save reopens, opens readable-name images natively, returns and exports a relocatable ZIP', async () => {
  test.setTimeout(240000)
  const directory = await fs.mkdtemp(join(testRunRoot, 'enriched-save-'))
  const fixtureCommand = (command: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
    ['-X', 'utf8', '-m', 'tests.desktop.fixtures.enriched_save', command, directory], { windowsHide: true, encoding: 'utf-8' }))
  const fixture = fixtureCommand('prepare')
  const launch = () => electron.launch({ args: [resolve('tests/desktop/support/reference-workbench.cjs')], env: { ...process.env,
    PDFMD_UI_PROFILE: join(directory, 'profile'), PDFMD_DATA: join(directory, 'workspace'),
    PDFMD_PYTHON: resolve('.venv/Scripts/python.exe'), PDFMD_SKIP_CREDENTIAL_FILE: '1', ELECTRON_RENDERER_URL: '' } })
  let app = await launch()
  let page: Page
  const observations: unknown[] = []
  try {
    for (const stage of ['opened', 'relaunched']) {
      page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').filter({ hasText: 'T3b enriched save' }).click()
      await page.getByLabel('Saved version').selectOption(fixture.version)
      await expect(page.getByRole('button', { name: 'Return to document' })).toBeVisible()
      await expect(page.locator('.asset-reference-status')).toHaveCount(0)
      const inline = page.frameLocator('iframe').locator('img')
      await expect(inline).toHaveCount(1)
      await inline.evaluate(async item => (item as HTMLImageElement).decode())
      await viewImage(page, 'Open page 1', fixture.render_size)
      await page.screenshot({ path: join(directory, `${stage}-page.png`) })
      await returnDocument(page, '第四章')
      await viewImage(page, 'Open figure', fixture.figure_size)
      await page.screenshot({ path: join(directory, `${stage}-figure.png`) })
      await returnDocument(page, '第四章')
      if (stage === 'relaunched') {
        const destination = join(directory, 'enriched.zip')
        await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, destination)
        await page.getByRole('button', { name: 'Export ZIP' }).click()
        await expect(page.locator('.toast.success')).toContainText('ZIP bytes verified. Asset references: ok')
      }
      observations.push({ stage, inline_image_decoded: true, page_link_opened: true, figure_link_opened: true })
      if (stage === 'relaunched') {
        // A real UI save on the schema 2 version sends one keyed submission to the engine.
        await page.getByRole('button', { name: 'Edit content', exact: true }).click()
        await page.locator('.block-editor textarea').first().fill(`## 第四章 新聞（修訂）

Source pages: [Open page 1](${fixture.page_uri})`)
        await page.locator('.block-editor textarea').nth(1).fill('Figure moved to an appendix.')
        await page.getByRole('button', { name: 'Save new version' }).click()
        await expect(page.getByRole('status')).toContainText('Saved your edits')
        observations.push({ stage, ui_edit_saved: true })
      }
      if (stage === 'opened') { await app.close(); app = await launch() }
    }
    const served = await app.evaluate(() => (globalThis as any).referenceControl.responses)
    for (const path of [fixture.page, fixture.figure]) {
      const bytes = await fs.readFile(join(directory, 'workspace', 'versions', fixture.version, path))
      expect(served.some((r: any) => r.status === 200 && r.length === bytes.length &&
        r.sha256 === createHash('sha256').update(bytes).digest('hex'))).toBe(true)
    }
    const calls = await app.evaluate(() => (globalThis as any).referenceControl.calls)
    expect(calls.some((c: any) => ['start', 'continue'].includes(c.action))).toBe(false)
  } finally { await app.close() }
  const verification = fixtureCommand('verify')
  await fs.writeFile(join(directory, 'desktop-verification.json'), JSON.stringify({ observations, verification }, null, 2))
})
