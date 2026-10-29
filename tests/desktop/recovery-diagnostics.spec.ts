import { test, expect, _electron as electron } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

const root = resolve(process.env.PDFMD_DIAGNOSTICS_EVIDENCE || '.local/recovery-diagnostics-desktop')
const fixtureScript = 'tests/desktop/recovery-diagnostics-fixture.py'
const baseline = process.env.PDFMD_DIAGNOSTICS_BASELINE
const env = { ...process.env, ...(baseline ? { PYTHONPATH: resolve(baseline) } : {}) }

function fixture(mode: string, directory: string, protocol?: string) {
  return JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
    ['-X', 'utf8', fixtureScript, mode, directory, ...(protocol ? [protocol] : [])],
    { windowsHide: true, encoding: 'utf-8', env }))
}
async function directory(prefix: string) {
  await fs.mkdir(root, { recursive: true })
  return fs.mkdtemp(join(root, prefix))
}
function launch(directory: string) {
  return electron.launch({ args: [resolve('tests/desktop/isolated-workbench.cjs')], env: { ...env,
    PDFMD_UI_PROFILE: join(directory, 'electron-profile'), PDFMD_DATA: join(directory, 'workspace'),
    PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
}
async function open(app: Awaited<ReturnType<typeof launch>>) {
  const page = await app.firstWindow()
  await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
  await page.locator('.document-item').first().click()
  await expect(page.getByAltText('Source PDF physical page 1')).toHaveAttribute('src', /^data:/)
  await expect(page.getByLabel('Saved version')).toHaveValue(/.+/)
  return page
}

for (const protocol of ['chat_completions', 'responses']) {
  test(`fresh recovery diagnosis retains usage and exact native/raw links after reopen: ${protocol}`, async () => {
    const dir = await directory(`reopen-${protocol}-`)
    const value = fixture('prepare', dir, protocol)
    let app: Awaited<ReturnType<typeof launch>> | undefined
    try {
      app = await launch(dir)
      let page = await open(app)
      let panel = page.getByRole('region', { name: 'Saved acceptance recovery' })
      await panel.getByRole('button', { name: 'Inspect saved acceptance' }).click()
      await expect(panel.getByText('Local recovery is available', { exact: true })).toBeVisible()
      await panel.getByRole('button', { name: 'Preserve work and prepare to re-plan' }).click()
      await expect(panel.getByRole('status')).toContainText('Local recovery is ready')
      const first = await page.evaluate(async job => window.workbench.invoke('diagnoseConflict', { job }), value.job)
      await fs.writeFile(join(dir, 'immediate-authoritative-diagnosis.json'), JSON.stringify(first, null, 2))
      await app.close(); app = await launch(dir); page = await open(app)
      panel = page.getByRole('region', { name: 'Saved acceptance recovery' })
      const before = fixture('hash', dir)
      await panel.getByRole('button', { name: 'Inspect saved acceptance' }).click()
      await expect(panel.getByRole('status')).toContainText('Local recovery is ready')
      await panel.getByText('Evidence references and usage', { exact: true }).click()
      const diagnosis = await page.evaluate(async job => window.workbench.invoke('diagnoseConflict', { job }), value.job)
      expect(diagnosis.request).toBe(value.request)
      expect(diagnosis.resolution_ref).toBe(`conflict-resolution:${value.request}`)
      expect(diagnosis.original_usage).toEqual(value.original_usage)
      expect(diagnosis.saved_usage).toEqual(value.saved_usage)
      expect(diagnosis.native_ref).toBe(value.native_ref)
      expect(diagnosis.stream_ref).toBe(value.stream_ref)
      expect(diagnosis.effects.operations).toHaveLength(2)
      const usageLine = panel.getByText(/^Original recorded usage:/)
      await expect(usageLine).toContainText(`Original recorded usage: ${diagnosis.original_usage === null ? 'unknown' : JSON.stringify(diagnosis.original_usage)}.`)
      await expect(usageLine).toContainText(`Saved reply usage: ${JSON.stringify(diagnosis.saved_usage)}.`)
      await expect(panel).toContainText(value.version)
      const operation = diagnosis.effects.operations[1]
      await panel.getByRole('button', { name: `Open candidate ${operation.operation}`, exact: true }).click()
      await expect(page.locator('.evidence-detail')).toContainText(operation.candidate_ref)
      await panel.getByRole('button', { name: `Open result ${operation.operation}`, exact: true }).click()
      await expect(page.locator('.evidence-detail')).toContainText(operation.result_ref)
      await expect(page.locator('.evidence-detail')).toContainText('not_started')
      await panel.getByRole('button', { name: 'Open native response', exact: true }).click()
      await expect(page.locator('.evidence-detail')).toContainText(value.native_ref)
      let opened = JSON.parse(await page.locator('.evidence-detail pre').innerText())
      expect(opened.value).toEqual(value.native)
      await panel.getByRole('button', { name: 'Open complete raw bytes', exact: true }).click()
      await expect(page.locator('.evidence-detail')).toContainText('base64_original_bytes')
      opened = JSON.parse(await page.locator('.evidence-detail pre').innerText())
      expect(opened.ref).toBe(value.stream_ref)
      expect(Buffer.from(opened.data, 'base64').toString('hex')).toBe(value.raw_hex)
      expect(Buffer.from(opened.data, 'base64').at(-1)).toBe(0xe4)
      expect(opened.complete).toBe(true)
      await panel.getByRole('button', { name: 'Open saved resolution', exact: true }).click()
      await expect(page.locator('.evidence-detail')).toContainText('preserve_and_replan')
      const after = fixture('hash', dir)
      expect(after).toEqual(before)
      await fs.writeFile(join(dir, 'read-only-hashes.json'), JSON.stringify({ before, after, unchanged: true }, null, 2))
      await fs.writeFile(join(dir, 'reopened-authoritative-diagnosis.json'), JSON.stringify(diagnosis, null, 2))
      await panel.screenshot({ path: join(dir, 'reopened-diagnosis.png') })
      await page.getByRole('button', { name: 'Preview', exact: true }).click()
      const preview = page.frameLocator('iframe').locator('body')
      await expect(preview).toContainText('First page. Preserve 25 mg.')
      await expect(preview).toContainText('Second page. Do not omit this paragraph.')
      await preview.locator('img').evaluateAll(async images => Promise.all(images.map(el => (el as HTMLImageElement).decode())))
      await page.locator('.output-panel').screenshot({ path: join(dir, 'saved-preview.png') })
      await page.getByLabel('Saved version').selectOption(value.seed_version)
      await expect(preview).toContainText('First page. Preserve 25 mg.')
      await expect(preview).toContainText('Second page. Do not omit this paragraph.')
      await page.getByLabel('Saved version').selectOption(value.version)
      await expect(preview).toContainText('Second page. Do not omit this paragraph.')
      await app.evaluate(({ dialog }, destination) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath: destination }) }, join(dir, 'delivery.zip'))
      await page.getByRole('button', { name: 'Export ZIP' }).click()
      await expect(page.locator('.toast.success')).toContainText('Exported completed version')
      await app.close(); app = undefined
      expect(fixture('verify', dir).verified).toBe(true)
    } finally { if (app) await app.close() }
  })

  test(`newer frozen unknown request remains primary after earlier recovery: ${protocol}`, async () => {
    const dir = await directory(`newer-${protocol}-`)
    const initial = fixture('prepare', dir, protocol)
    let app: Awaited<ReturnType<typeof launch>> | undefined
    try {
      app = await launch(dir)
      const page = await open(app)
      const panel = page.getByRole('region', { name: 'Saved acceptance recovery' })
      await panel.getByRole('button', { name: 'Inspect saved acceptance' }).click()
      await expect(panel.getByText('Local recovery is available', { exact: true })).toBeVisible()
      await panel.getByRole('button', { name: 'Preserve work and prepare to re-plan' }).click()
      await expect(panel.getByRole('status')).toContainText('Local recovery is ready')
      await expect(panel.locator('p').filter({ hasText: /^Request:/ }).first()).toContainText(initial.request)
      // An idle app must invalidate its old ready view when regular job polling
      // observes a genuinely frozen and failed newer request. No user Inspect
      // click is required to stop the old ready claim.
      const value = fixture('advance', dir)
      await expect(panel.getByText(/Stale diagnosis:/)).toBeVisible({ timeout: 15000 })
      await expect(panel.getByText(/Local recovery is ready/)).toBeHidden()
      await expect(panel.getByRole('button', { name: 'Preserve work and prepare to re-plan' })).toBeHidden()
      const before = fixture('hash', dir)
      await panel.getByRole('button', { name: 'Inspect saved acceptance' }).click()
      const primary = panel.locator('p').filter({ hasText: /^Request:/ }).first()
      await expect(primary).toContainText(value.request)
      await expect(primary).not.toContainText(value.old_request)
      await expect(panel).toContainText('Complete acceptance staging is unavailable')
      await expect(panel).toContainText('No complete accepted staging')
      await expect(panel.getByText(/Local recovery is ready/)).toBeHidden()
      await expect(panel.getByRole('button', { name: 'Preserve work and prepare to re-plan' })).toBeHidden()
      const diagnosis = await page.evaluate(async job => window.workbench.invoke('diagnoseConflict', { job }), value.job)
      expect(diagnosis.request).toBe(value.request)
      expect(diagnosis.status).toBe('missing_staging')
      expect(diagnosis.eligible).toBe(false)
      expect(diagnosis.publication.request_status).toBe(value.request_status)
      expect(fixture('hash', dir)).toEqual(before)
      await fs.writeFile(join(dir, 'newer-primary-diagnosis.json'), JSON.stringify(diagnosis, null, 2))
      await panel.screenshot({ path: join(dir, 'newer-primary.png') })
    } finally { if (app) await app.close() }
  })
}
