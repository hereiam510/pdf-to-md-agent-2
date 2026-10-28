import { test, expect, _electron as electron } from '@playwright/test'
import { createServer } from 'node:http'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

for (const protocol of ['chat_completions', 'responses']) {
  test(`diagnose, recover locally, reopen, separately Continue and export: ${protocol}`, async () => {
    const root = resolve(process.env.PDFMD_ACCEPTED_RECOVERY_EVIDENCE || '.local/accepted-recovery-desktop')
    await fs.mkdir(root, { recursive: true })
    const directory = await fs.mkdtemp(join(root, `${protocol}-`))
    const payloads: unknown[] = []
    const server = createServer(async (req, res) => {
      const chunks: Buffer[] = []
      for await (const chunk of req) chunks.push(Buffer.from(chunk))
      payloads.push(JSON.parse(Buffer.concat(chunks).toString()))
      if (payloads.length > 1) { res.writeHead(500); res.end(); return }
      res.writeHead(200, { 'Content-Type': 'text/event-stream' })
      res.end(await fs.readFile(join(directory, 'scripted-response.sse')))
    })
    await new Promise<void>(done => server.listen(0, '127.0.0.1', done))
    const port = (server.address() as { port: number }).port
    const endpoint = `http://127.0.0.1:${port}/v1/${protocol === 'responses' ? 'responses' : 'chat/completions'}`
    const runFixture = (mode: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
      ['-X', 'utf8', 'tests/desktop/accepted-recovery-fixture.py', mode, directory, protocol, endpoint],
      { windowsHide: true, encoding: 'utf-8' }))
    const fixture = runFixture('prepare')
    const launch = () => electron.launch({ args: [resolve('tests/desktop/isolated-workbench.cjs')], env: { ...process.env,
      PDFMD_UI_PROFILE: join(directory, 'electron-profile'),
      PDFMD_DATA: join(directory, 'workspace'), PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
    let app: Awaited<ReturnType<typeof launch>> | undefined
    try {
      app = await launch()
      expect(await app.evaluate(({ app }) => app.getPath('userData'))).toBe(join(directory, 'electron-profile'))
      let page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').first().click()
      const panel = page.getByRole('region', { name: 'Saved acceptance recovery' })
      const getJob = () => page.evaluate(async job => window.workbench.invoke('job', { job }), fixture.job)
      const before = await getJob()
      expect(before.attempts).toBe(1)
      // No connection/credential is configured for diagnosis or local resolution.
      await panel.getByRole('button', { name: 'Inspect saved acceptance' }).click()
      await expect(panel.getByText('Local recovery is available', { exact: true })).toBeVisible()
      await expect(panel.getByText(/no recovery decision was committed/)).toBeVisible()
      await expect(panel.getByText(/Completed and retained/).first()).toBeVisible()
      expect(payloads).toHaveLength(0)
      expect((await getJob()).attempts).toBe(before.attempts)
      await panel.screenshot({ path: join(directory, 'diagnosis.png') })
      await panel.getByRole('button', { name: 'Preserve work and prepare to re-plan' }).click()
      await expect(panel.getByRole('status')).toContainText('Local recovery is ready')
      await expect(panel.getByText(/no recovery decision was committed/)).toBeHidden()
      const resolved = await getJob()
      expect(resolved.stop_reason).toBe(before.stop_reason)
      expect(resolved.cancel_requested).toBe(true)
      expect(resolved.attempts).toBe(before.attempts)
      expect(resolved.head).toBe(before.head)
      expect(resolved.status).toBe('blocked')
      expect(payloads).toHaveLength(0)
      await panel.screenshot({ path: join(directory, 'locally-ready.png') })
      await panel.getByRole('button', { name: 'Open saved resolution', exact: true }).click()
      await expect(page.locator('.evidence-detail')).toContainText('preserve_and_replan')
      expect(payloads).toHaveLength(0)
      // Duplicate action after projection is idempotent through the real IPC/API.
      const duplicate = await page.evaluate(async args => window.workbench.invoke('resolveConflict', args),
        { job: fixture.job, request: fixture.request, basis: 'old-click' })
      expect(duplicate.projection).toBe('ready')
      await app.close(); app = await launch(); page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').first().click()
      const reopened = page.getByRole('region', { name: 'Saved acceptance recovery' })
      await reopened.getByRole('button', { name: 'Inspect saved acceptance' }).click()
      await expect(reopened.getByRole('status')).toContainText('Local recovery is ready')
      expect(payloads).toHaveLength(0)
      const preview = page.frameLocator('iframe').locator('body')
      await expect(preview).toContainText('First page. Preserve 25 mg.')
      await expect(preview).toContainText('Second page. Do not omit this paragraph.')
      await preview.locator('img').evaluateAll(async images => Promise.all(images.map(el => (el as HTMLImageElement).decode())))
      await preview.screenshot({ path: join(directory, 'reopened-preview.png') })
      await page.getByRole('button', { name: 'Nexus connection' }).click()
      await page.getByLabel('Full endpoint URL').fill(endpoint)
      await page.getByLabel('Protocol').selectOption(protocol)
      await page.getByLabel('Model alias').fill(fixture.route.model)
      await page.getByLabel('Nexus credential', { exact: true }).fill('scripted-local-only')
      await page.getByLabel('Remember with operating-system encryption').uncheck()
      await page.getByRole('button', { name: 'Save connection' }).click()
      expect(payloads).toHaveLength(0)
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await expect(page.locator('.status')).toHaveText('Completed', { timeout: 30000 })
      expect(payloads).toHaveLength(1)
      expect(JSON.stringify(payloads[0])).toContain(`conflict-resolution:${fixture.request}`)
      expect(JSON.stringify(payloads[0])).toContain('Historical completion claim')
      await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, join(directory, 'delivery.zip'))
      await page.getByRole('button', { name: 'Export ZIP' }).click()
      await expect(page.locator('.toast.success')).toContainText('Exported completed version')
      await app.close(); app = undefined
      const verified = runFixture('verify')
      expect(verified.verified).toBe(true)
      await fs.writeFile(join(directory, 'observed-payloads.json'), JSON.stringify(payloads, null, 2))
    } finally {
      if (app) await app.close()
      await new Promise<void>(done => server.close(() => done()))
    }
  })
}
