import { testRunRoot } from '../support/artifacts'
import { test, expect, _electron as electron, chromium, type Page, type FrameLocator } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'

test('FD-01 fixture crops and associated copyable text survive correction, restart and explicit export', async () => {
  const directory = await fs.mkdtemp(resolve(testRunRoot, 'figures-'))
  const fixtureCall = (mode: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
    ['-m', 'tests.desktop.fixtures.figure_delivery', mode, directory], { windowsHide: true, encoding: 'utf-8' }))
  const fixture = fixtureCall('prepare')
  const observed: unknown[] = []
  const check = async (surface: Page | FrameLocator, stage: string) => {
    const body = surface.locator('body')
    await expect(surface.locator('img')).toHaveCount(4)
    await surface.locator('img').evaluateAll(async items => Promise.all(items.map(item => (item as HTMLImageElement).decode())))
    const sections = await body.evaluate(element => [...element.querySelectorAll('h3')].map(heading => {
      const nodes: Element[] = []
      for (let item = heading.nextElementSibling; item && item.tagName !== 'H3'; item = item.nextElementSibling) nodes.push(item)
      const text = nodes.map(item => (item as HTMLElement).innerText).join('\n')
      const image = nodes.flatMap(item => [...item.querySelectorAll('img')])[0] as HTMLImageElement
      const paragraph = nodes.find(item => item.textContent?.includes(heading.textContent === 'panels' ? 'Original caption:' :
        heading.textContent === 'curve' ? 'Original caption:' : 'Agent description (not a source caption)'))!
      const range = document.createRange(); range.selectNodeContents(paragraph)
      const selection = window.getSelection()!; selection.removeAllRanges(); selection.addRange(range)
      const copyable = selection.toString(); selection.removeAllRanges()
      return { key: heading.textContent, text, copyable, width: image.naturalWidth, height: image.naturalHeight }
    }))
    expect(sections.map(item => item.key)).toEqual(Object.keys(fixture.images))
    for (const section of sections) {
      const image = fixture.images[section.key!]
      expect([section.width, section.height]).toEqual([image.width, image.height])
      expect(section.copyable).toContain(section.key === 'panels' || section.key === 'curve' ? 'Original caption:' : 'Agent description (not a source caption)')
    }
    expect(sections[0].text).toContain('Panel A: IN; 10 mg. Panel B: OUT; 0 mg.')
    expect(sections[0].text).toContain('only if enabled')
    expect(sections[0].text).toContain('no transfer')
    expect(sections[1].text).toContain('Time (s): 0, 5. Level (mg): 0, 10.')
    expect(sections[2].text).toContain('does not specify')
    expect(sections[3].text).toContain('No source caption, labels or numerical values')
    await body.screenshot({ path: join(directory, `${stage}.png`) })
    observed.push({ stage, sections })
  }
  const launch = () => electron.launch({ args: [resolve('tests/desktop/support/isolated-workbench.cjs')], env: { ...process.env,
    PDFMD_UI_PROFILE: join(directory, 'profile'), PDFMD_DATA: join(directory, 'workspace'),
    PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
  let app = await launch()
  try {
    for (const stage of ['saved', 'reopened']) {
      const page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').first().click()
      await check(page.frameLocator('iframe'), stage)
      if (stage === 'saved') { await app.close(); app = await launch() }
    }
    const page = await app.firstWindow()
    await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, join(directory, 'delivery.zip'))
    await page.getByRole('button', { name: 'Export ZIP' }).click()
    await expect(page.locator('.toast.success')).toContainText('Exported completed version')
    expect(fixtureCall('verify').attempts).toBe(0)
  } finally { await app.close() }
  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  try {
    const page = await browser.newPage()
    await page.route(/^https?:/, route => route.abort())
    await page.goto(pathToFileURL(join(directory, 'exported/preview.html')).href)
    await check(page, 'exported')
  } finally { await browser.close() }
  await fs.writeFile(join(directory, 'renderer-verification.json'), JSON.stringify({ observed, live_model_calls: 0 }, null, 2))
})
