import { test, expect, _electron as electron, chromium } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'

for (const protocol of ['chat_completions', 'responses']) {
  test(`exact document reads and explicit context choice preserve delivery: ${protocol}`, async () => {
    const directory = await fs.mkdtemp(resolve(`.local/working-evidence-${protocol}-`))
    const run = (mode: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
      ['-B', '-X', 'utf8', 'tests/desktop/working-evidence-fixture.py', mode, directory, protocol],
      { windowsHide: true, encoding: 'utf-8' }))
    const fixture = run('prepare')
    const launch = () => electron.launch({ args: [resolve('out/main/index.js')], env: { ...process.env,
      PDFMD_DATA: join(directory, 'workspace'), PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
    let app = await launch()
    const observed: unknown[] = []
    try {
      for (const stage of ['saved', 'reopened']) {
        const page = await app.firstWindow()
        await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
        await page.locator('.document-item').first().click()
        const body = page.frameLocator('iframe').locator('body')
        await expect(body).toContainText('Stencil source: red and blue. Keep 25 mg.')
        await expect(body).toContainText('Section 11: exact source text.')
        await expect(body).toContainText('Item 16: retain this wording, 25 mg, and source order for section 11.')
        const images = page.frameLocator('iframe').locator('img')
        await expect(images).toHaveCount(3)
        await images.evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
        const sizes = await images.evaluateAll(items => items.map(item => {
          const image = item as HTMLImageElement
          return { width: image.naturalWidth, height: image.naturalHeight }
        }))
        expect(sizes).toEqual(fixture.images.map(({ width, height }: any) => ({ width, height })))
        // An iframe body can be much taller than its painted viewport. Capture
        // visible app views and each source figure instead of a mostly blank
        // full-body screenshot extending beyond that viewport.
        await page.screenshot({ path: join(directory, `${stage}-preview.png`) })
        for (let index = 0; index < fixture.images.length; index++) {
          const image = images.nth(index)
          await image.scrollIntoViewIfNeeded()
          await expect(image).toBeVisible()
          await image.screenshot({ path: join(directory, `${stage}-figure-${index}-${fixture.images[index].label}.png`) })
        }
        const lastSection = page.frameLocator('iframe').locator('p').filter({ hasText: 'Section 11: exact source text.' }).first()
        await lastSection.scrollIntoViewIfNeeded()
        await expect(lastSection).toBeVisible()
        await page.screenshot({ path: join(directory, `${stage}-last-section.png`) })
        observed.push({ stage, sizes, first_and_last_page_text: true,
          screenshots: ['app_viewport', 'three_individual_figures', 'last_section_viewport'] })
        if (stage === 'saved') { await app.close(); app = await launch() }
      }
      const page = await app.firstWindow()
      await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, join(directory, 'delivery.zip'))
      await page.getByRole('button', { name: 'Export ZIP' }).click()
      await expect(page.locator('.toast.success')).toContainText('Exported completed version')
      const result = run('verify')
      expect(result.mock_attempts).toBe(fixture.attempts)
      expect(result.source_and_originals_preserved).toBe(true)
      expect(result.all_twelve_pages_preserved).toBe(true)
      expect(result.original_draft_unchanged).toBe(true)
    } finally { await app.close() }
    const browser = await chromium.launch({ channel: 'msedge', headless: true })
    try {
      const page = await browser.newPage()
      await page.route(/^https?:/, route => route.abort())
      await page.goto(pathToFileURL(join(directory, 'exported/preview.html')).href)
      await expect(page.locator('body')).toContainText('Stencil source: red and blue. Keep 25 mg.')
      await expect(page.locator('body')).toContainText('Section 11: exact source text.')
      const images = page.locator('img')
      await expect(images).toHaveCount(3)
      await images.evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
      await page.screenshot({ path: join(directory, 'export-preview.png') })
      for (let index = 0; index < fixture.images.length; index++) {
        const image = images.nth(index)
        await image.scrollIntoViewIfNeeded()
        await expect(image).toBeVisible()
        await image.screenshot({ path: join(directory, `exported-figure-${index}-${fixture.images[index].label}.png`) })
      }
      const lastSection = page.locator('p').filter({ hasText: 'Section 11: exact source text.' }).first()
      await lastSection.scrollIntoViewIfNeeded()
      await expect(lastSection).toBeVisible()
      await page.screenshot({ path: join(directory, 'export-last-section.png') })
      observed.push({ stage: 'exported', browser: browser.version(), first_and_last_page_text: true,
        screenshots: ['browser_viewport', 'three_individual_figures', 'last_section_viewport'] })
    } finally { await browser.close() }
    await fs.writeFile(join(directory, 'renderer-verification.json'), JSON.stringify({ observed, live_model_calls: 0 }, null, 2))
  })
}
