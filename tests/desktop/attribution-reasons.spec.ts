import { test, expect, _electron as electron } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

const root = resolve(process.env.PDFMD_ATTRIBUTION_EVIDENCE || '.local/attribution-reasons-desktop')
function fixture(mode: string, dir: string, ...args: string[]) {
  return JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'), ['-X', 'utf8',
    'tests/desktop/attribution-reasons-fixture.py', mode, dir, ...args], { windowsHide: true, encoding: 'utf-8' }))
}
async function launch(dir: string) {
  const app = await electron.launch({ args: [resolve('tests/desktop/isolated-workbench.cjs')], env: { ...process.env,
    PDFMD_UI_PROFILE: join(dir, 'profile'), PDFMD_DATA: join(dir, 'workspace'), PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
  const page = await app.firstWindow()
  await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
  await page.locator('.document-item').first().click()
  await expect(page.getByAltText('Source PDF physical page 1')).toHaveAttribute('src', /^data:/)
  return { app, page }
}

for (const protocol of ['chat_completions', 'responses']) {
  test(`current B and explicitly earlier raw A survive fresh API/UI and process reopen: ${protocol}`, async () => {
    await fs.mkdir(root, { recursive: true })
    const dir = await fs.mkdtemp(join(root, `attribution-${protocol}-`))
    const value = fixture('prepare', dir, protocol, 'attribution')
    for (const phase of ['fresh', 'reopened']) {
      const { app, page } = await launch(dir)
      try {
        const panel = page.getByRole('region', { name: 'Saved acceptance recovery' })
        const before = fixture('hash', dir)
        await panel.getByRole('button', { name: 'Inspect saved acceptance' }).click()
        await expect(panel.locator('p').filter({ hasText: /^Request:/ })).toContainText(`Attempt: ${value.b}`)
        await panel.getByText('Evidence references and usage', { exact: true }).click()
        const rawLine = panel.locator('p').filter({ hasText: /^Raw stream:/ })
        await expect(rawLine).toContainText(`Attempt: ${value.a}`)
        await expect(rawLine).toContainText('earlier attempt evidence; partial evidence')
        await expect(rawLine).not.toContainText(value.b)
        await expect(panel).toContainText('0 success-body bytes observed')
        await expect(panel).toContainText('Selected attempt raw stream evidence: No corresponding retained evidence established.')
        await expect(panel.getByRole('button', { name: 'Preserve work and prepare to re-plan' })).toBeHidden()
        const diagnosis = await page.evaluate(async job => window.workbench.invoke('diagnoseConflict', { job }), value.job)
        expect(diagnosis.attempt).toBe(value.b)
        expect(diagnosis.evidence_provenance.stream_ref.attempt).toBe(value.a)
        expect(diagnosis.evidence_provenance.stream_ref.relation).toBe('earlier_attempt')
        await panel.getByRole('button', { name: 'Open complete raw bytes', exact: true }).click()
        await expect(page.locator('.evidence-detail')).toContainText('base64_original_bytes')
        const opened = JSON.parse(await page.locator('.evidence-detail pre').innerText())
        expect(Buffer.from(opened.data, 'base64').toString('hex')).toBe(value.raw_hex)
        expect(opened.ref).toBe(value.stream_ref)
        const after = fixture('hash', dir)
        expect(after).toEqual(before)
        await fs.writeFile(join(dir, `${phase}-no-write.json`), JSON.stringify({ before, after, unchanged: true }, null, 2))
        await fs.writeFile(join(dir, `${phase}-diagnosis.json`), JSON.stringify(diagnosis, null, 2))
        await panel.screenshot({ path: join(dir, `${phase}.png`) })
        if (phase === 'reopened') {
          // Export is a subsequent, separately recorded write interval.
          await page.getByLabel('Saved version').selectOption(value.version)
          await page.getByRole('button', { name: 'Preview', exact: true }).click()
          const preview = page.frameLocator('iframe').locator('body')
          await expect(preview).toContainText('First page. Preserve 25 mg.')
          await expect(preview).toContainText('Second page. Do not omit this paragraph.')
          await expect(preview).not.toContainText('Manual retained note.')
          await preview.locator('img').evaluateAll(async images => Promise.all(images.map(el => (el as HTMLImageElement).decode())))
          await page.locator('.output-panel').screenshot({ path: join(dir, 'explicit-version-preview.png') })
          await app.evaluate(({ dialog }, destination) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath: destination }) }, join(dir, 'delivery.zip'))
          await page.getByRole('button', { name: 'Export ZIP' }).click()
          await expect(page.locator('.toast.success')).toContainText('Exported completed version')
          await fs.writeFile(join(dir, 'post-export-hashes.json'), JSON.stringify(fixture('hash', dir), null, 2))
        }
      } finally { await app.close() }
    }
    expect(fixture('verify', dir).verified).toBe(true)
  })
}

test('supported finish with unreadable head displays its actual fact refusal after reopen', async () => {
  await fs.mkdir(root, { recursive: true })
  const dir = await fs.mkdtemp(join(root, 'reason-'))
  const value = fixture('prepare', dir, 'responses', 'reason')
  for (const phase of ['fresh', 'reopened']) {
    const { app, page } = await launch(dir)
    try {
      const panel = page.getByRole('region', { name: 'Saved acceptance recovery' })
      const before = fixture('hash', dir)
      await panel.getByRole('button', { name: 'Inspect saved acceptance' }).click()
      await expect(panel).toContainText('Saved terminal response has an unfinished received tail')
      await expect(panel).toContainText('All effects established')
      await expect(panel).toContainText('Current head is unavailable/inconsistent')
      await expect(panel).not.toContainText('outside the supported finish-boundary class')
      await expect(panel.getByRole('button', { name: 'Preserve work and prepare to re-plan' })).toBeHidden()
      const diagnosis = await page.evaluate(async job => window.workbench.invoke('diagnoseConflict', { job }), value.job)
      expect(diagnosis.reasons).toEqual(diagnosis.fact_errors)
      expect(diagnosis.eligible).toBe(false)
      expect(diagnosis.effects.operations[0].certainty).toBe('completed')
      expect(fixture('hash', dir)).toEqual(before)
      await fs.writeFile(join(dir, `${phase}-diagnosis.json`), JSON.stringify(diagnosis, null, 2))
      await fs.writeFile(join(dir, `${phase}-no-write.json`), JSON.stringify({ before, after: fixture('hash', dir), unchanged: true }, null, 2))
      await panel.screenshot({ path: join(dir, `${phase}.png`) })
    } finally { await app.close() }
  }
})
