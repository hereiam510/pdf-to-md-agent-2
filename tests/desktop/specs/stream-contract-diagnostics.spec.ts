import { testRunRoot } from '../support/artifacts'
import { test, expect, _electron as electron } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'

test('bounded validation display, intentional raw access and process reopen', async () => {
  const root = resolve(process.env.PDFMD_STREAM_EVIDENCE || resolve(testRunRoot, 'stream-contract-desktop'))
  await fs.mkdir(root, { recursive: true })
  const directory = await fs.mkdtemp(join(root, 'diagnostic-'))
  const env = { ...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: resolve('src'),
    PDFMD_PYTHON: resolve('.venv/Scripts/python.exe'), PDFMD_DATA: join(directory, 'workspace') }
  const fixture = (action: string) => JSON.parse(execFileSync(env.PDFMD_PYTHON,
    ['-B', '-X', 'utf8', '-m', 'tests.desktop.fixtures.stream_contract_diagnostics', action, directory],
    { encoding: 'utf-8', windowsHide: true, env }))
  const info = fixture('prepare')
  const launcher = join(directory, 'launch.cjs')
  await fs.writeFile(launcher, `const {app}=require('electron');app.setPath('userData',${JSON.stringify(join(directory, 'profile'))});require(${JSON.stringify(resolve(process.env.PDFMD_STREAM_BUILD || 'out', 'main/index.js'))});`)
  for (const stage of ['first', 'reopened']) {
    const app = await electron.launch({ args: [launcher], env })
    try {
      const page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').first().click()
      const compact = page.getByTestId('receive-progress')
      await expect(compact).toContainText('Response not accepted')
      await expect(compact).toContainText('Local validation: invalid_stream · response · native · event 2')
      expect(await compact.textContent()).not.toContain(info.secret)
      const value = await page.evaluate(async job => window.workbench.invoke('job', { job }), info.job)
      expect(JSON.stringify(value.requests.map((r: any) => r.receive))).not.toContain(info.secret)
      expect(value.attempts).toBe(1)
      await page.screenshot({ path: join(directory, `${stage}-summary.png`) })
      await page.getByRole('button', { name: /^View activity and diagnostics/ }).click()
      const panel = page.getByRole('region', { name: 'Task activity and diagnostics' })
      await expect.poll(async () => (await panel.getByLabel('Diagnostic view').count()) + (await panel.getByRole('alert').count())).toBeGreaterThan(0)
      if (await panel.getByRole('alert').count()) await panel.getByRole('button', { name: 'Refresh diagnostics and recent activity' }).click()
      await panel.getByLabel('Diagnostic view').selectOption('request')
      await panel.getByRole('button', { name: `Inspect ${info.request}`, exact: true }).click()
      await panel.getByText('Reported and derived usage (separate from settlement)', { exact: true }).click()
      await expect(panel).toContainText('native raw SSE report')
      await expect(panel).toContainText('assembled derived usage')
      await expect(panel).toContainText('"reason": "count"')
      await panel.screenshot({ path: join(directory, `${stage}-usage.png`) })
    } finally { await app.close() }
    expect(fixture('verify')).toEqual(info)
  }
})
