import { test, expect, _electron as electron, chromium } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'

test('PDF coordinates and native image originals survive saved preview, restart and portable export', async () => {
  const directory = await fs.mkdtemp(resolve('.local/pdf-delivery-desktop-'))
  const runFixture = (mode: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
    ['tests/desktop/pdf-delivery-fixture.py', mode, directory], { windowsHide: true, encoding: 'utf-8' }))
  const fixture = runFixture('prepare')
  const launch = () => electron.launch({ args: [resolve('out/main/index.js')], env: { ...process.env,
    PDFMD_DATA: join(directory, 'workspace'), PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
  let app = await launch()
  const observed: unknown[] = []
  try {
    for (const stage of ['saved', 'reopened']) {
      const page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').first().click()
      const images = page.frameLocator('iframe').locator('img')
      await expect(images).toHaveCount(fixture.images.length)
      await images.evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
      const sizes = await images.evaluateAll(items => items.map(item => {
        const image = item as HTMLImageElement
        return { label: image.alt, width: image.naturalWidth, height: image.naturalHeight }
      }))
      expect(sizes).toEqual(fixture.images.map(({ label, width, height }: any) => ({ label, width, height })))
      await page.frameLocator('iframe').locator('body').screenshot({ path: join(directory, `${stage}-preview.png`) })
      observed.push({ stage, sizes })
      if (stage === 'saved') { await app.close(); app = await launch() }
    }
    const page = await app.firstWindow()
    const destination = join(directory, 'delivery.zip')
    await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, destination)
    await page.getByRole('button', { name: 'Export ZIP' }).click()
    await expect(page.locator('.toast.success')).toContainText('Exported completed version')
    const verification = runFixture('verify')
    expect(verification.attempts).toBe(0)
    expect(verification.originals).toBeGreaterThanOrEqual(11)
    expect(verification.visible_images).toBe(15)
  } finally { await app.close() }
  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1000, height: 900 } })
    await page.route(/^https?:/, route => route.abort())
    await page.goto(pathToFileURL(join(directory, 'exported/preview.html')).href)
    await expect(page.locator('img')).toHaveCount(fixture.images.length)
    await page.locator('img').evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
    const sizes = await page.locator('img').evaluateAll(items => items.map(item => {
      const image = item as HTMLImageElement
      return { label: image.alt, width: image.naturalWidth, height: image.naturalHeight }
    }))
    expect(sizes).toEqual(fixture.images.map(({ label, width, height }: any) => ({ label, width, height })))
    await page.screenshot({ path: join(directory, 'export-preview.png'), fullPage: true })
    observed.push({ stage: 'exported', sizes })
  } finally { await browser.close() }
  await fs.writeFile(join(directory, 'renderer-verification.json'), JSON.stringify({ observed, live_model_calls: 0 }, null, 2))
})
