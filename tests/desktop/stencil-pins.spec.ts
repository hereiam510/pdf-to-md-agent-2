import { test, expect, _electron as electron, chromium } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'

for (const protocol of ['chat_completions', 'responses']) {
  test(`stencil appearance and rejected pin repair survive desktop reopen/export: ${protocol}`, async () => {
    const directory = await fs.mkdtemp(resolve(`.local/stencil-pins-${protocol}-`))
    const runFixture = (mode: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
      ['-X', 'utf8', 'tests/desktop/stencil-pins-fixture.py', mode, directory, protocol],
      { windowsHide: true, encoding: 'utf-8' }))
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
        await expect(images).toHaveCount(3)
        await images.evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
        const sizes = await images.evaluateAll(items => items.map(item => {
          const image = item as HTMLImageElement
          return { label: image.alt, width: image.naturalWidth, height: image.naturalHeight }
        }))
        expect(sizes).toEqual(fixture.images.map(({ label, width, height }: any) => ({ label, width, height })))
        await expect(page.frameLocator('iframe').locator('body')).toContainText('Stencil source: red and blue. Keep 25 mg.')
        await page.frameLocator('iframe').locator('body').screenshot({ path: join(directory, `${stage}-preview.png`) })
        for (const [i, name] of ['red', 'blue'].entries()) {
          await images.nth(i).screenshot({ path: join(directory, `${stage}-${name}.png`) })
        }
        observed.push({ stage, sizes })
        if (stage === 'saved') { await app.close(); app = await launch() }
      }
      const page = await app.firstWindow()
      await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, join(directory, 'delivery.zip'))
      await page.getByRole('button', { name: 'Export ZIP' }).click()
      await expect(page.locator('.toast.success')).toContainText('Exported completed version')
      const result = runFixture('verify')
      expect(result.mock_attempts).toBe(5)
      expect(result.originals).toBe(2)
      expect(result.stencil_occurrence_pixels_equal).toBe(true)
    } finally { await app.close() }
    const browser = await chromium.launch({ channel: 'msedge', headless: true })
    try {
      const page = await browser.newPage({ viewport: { width: 1000, height: 900 } })
      await page.route(/^https?:/, route => route.abort())
      await page.goto(pathToFileURL(join(directory, 'exported/preview.html')).href)
      const images = page.locator('img')
      await expect(images).toHaveCount(3)
      await images.evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
      await expect(page.locator('body')).toContainText('Stencil source: red and blue. Keep 25 mg.')
      for (const [i, name] of ['red', 'blue'].entries()) {
        await images.nth(i).screenshot({ path: join(directory, `exported-${name}.png`) })
      }
      await page.screenshot({ path: join(directory, 'export-preview.png'), fullPage: true })
      observed.push({ stage: 'exported', browser: browser.version() })
    } finally { await browser.close() }
    expect(runFixture('colors').all_expected_colors_present).toBe(true)
    await fs.writeFile(join(directory, 'renderer-verification.json'), JSON.stringify({ observed, live_model_calls: 0 }, null, 2))
  })
}
