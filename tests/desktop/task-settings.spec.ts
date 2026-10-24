import { test, expect, _electron as electron } from '@playwright/test'
import { createServer } from 'node:http'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

for (const protocol of ['chat_completions', 'responses']) {
  test(`task settings restore ${protocol} conversion after capacity and allowance blocks`, async () => {
    const directory = await fs.mkdtemp(resolve('.local/settings-desktop-'))
    const workspace = join(directory, 'workspace'), source = join(directory, 'Settings source.pdf'), destination = join(directory, 'delivery.zip')
    execFileSync(resolve('.venv/Scripts/python.exe'), ['tools/make-smoke-pdf.py', source], { windowsHide: true })
    const payloads: any[] = []
    const server = createServer(async (req, res) => {
      const chunks: Buffer[] = []
      for await (const chunk of req) chunks.push(Buffer.from(chunk))
      const payload = JSON.parse(Buffer.concat(chunks).toString())
      payloads.push(payload)
      const outputs = (payload.messages || payload.input).filter((m: any) => m.role === 'tool' || m.type === 'function_call_output')
        .map((m: any) => JSON.parse(m.content || m.output))
      let name: string, args: unknown
      if (payloads.length === 1) { name = 'inspect_pdf'; args = { pages: [1, 2], mode: 'text' } }
      else if (payloads.length === 2) { name = 'render_page'; args = { page: 1, dpi: 144, region: [60, 310, 530, 490] } }
      else if (payloads.length === 3) {
        name = 'edit_document'; args = { base_version: null, expected_head: null, title: 'Complete settings fixture', replace_blocks: [
          { id: 'p1', pages: [1], markdown: outputs[0].data.value.pages[0].content },
          { id: 'figure', pages: [1], markdown: `![Source figure](${outputs[1].data.asset_path})` },
          { id: 'p2', pages: [2], markdown: outputs[0].data.value.pages[1].content }
        ], page_updates: { '1': { printed: '1', disposition: 'included' }, '2': { printed: '2', disposition: 'included' } }, claim: 'complete' }
      } else { name = 'report'; args = { state: 'complete', version_id: outputs[2].data.version_id, message: 'Both complete pages and the source figure are saved.' } }
      const id = `call-${payloads.length}`, argumentsText = JSON.stringify(args)
      const value = protocol === 'responses' ? { status: 'completed', output: [
        { type: 'function_call', call_id: id, name, arguments: argumentsText, status: 'completed' }
      ] } : { choices: [{ finish_reason: 'tool_calls', message: { role: 'assistant', content: null, tool_calls: [
        { id, type: 'function', function: { name, arguments: argumentsText } }
      ] } }] }
      res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(value))
    })
    await new Promise<void>(done => server.listen(0, '127.0.0.1', done))
    const address = server.address() as { port: number }
    const launch = () => electron.launch({ args: [resolve('out/main/index.js')], env: { ...process.env,
      PDFMD_DATA: workspace, PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
    let app = await launch()
    try {
      let window = await app.firstWindow()
      await expect(window.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await app.evaluate(({ dialog }, source) => { dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [source] }) }, source)
      await window.getByRole('button', { name: 'Nexus connection' }).click()
      await window.getByLabel('Protocol').selectOption(protocol)
      await window.getByLabel('Full endpoint URL').fill(`http://127.0.0.1:${address.port}/v1/${protocol === 'responses' ? 'responses' : 'chat/completions'}`)
      await window.getByLabel('Model alias').fill('Local settings fixture')
      await window.getByLabel('Nexus credential', { exact: true }).fill('fixture-only')
      await window.getByLabel('Context capacity', { exact: true }).fill('2048')
      await window.getByLabel('Output reserve', { exact: true }).fill('256')
      await window.getByLabel('Maximum model requests', { exact: true }).fill('1')
      await window.getByLabel('This route accepts image inputs').check()
      await window.getByRole('button', { name: 'Save connection' }).click()
      await window.getByRole('button', { name: 'Choose a PDF' }).click()
      await window.getByRole('button', { name: 'Open document', exact: true }).click()
      await window.getByRole('button', { name: 'Start conversion', exact: true }).click()
      await expect(window.locator('.status')).toHaveText('Needs attention', { timeout: 15000 })
      expect(payloads).toHaveLength(0)
      await window.getByRole('button', { name: 'Task limits', exact: true }).click()
      await window.getByLabel('Task context capacity', { exact: true }).fill('65536')
      await window.getByLabel('Task output reserve', { exact: true }).fill('2048')
      await window.getByRole('button', { name: 'Save task limits' }).click()
      await expect(window.getByTestId('effective-task-limits')).toContainText('65,536')
      await window.getByRole('button', { name: 'Start conversion', exact: true }).click()
      await expect.poll(() => payloads.length).toBe(1)
      // The previous capacity-block label can remain visible until the next UI poll.
      await expect.poll(async () => window.evaluate(async () => {
        const jobs = await window.workbench.invoke('jobs')
        const value = await window.workbench.invoke('job', { job: jobs[0].id })
        return value.running ? 'running' : value.stop_reason
      }), { timeout: 15000 }).toBe('budget_exhausted')
      await expect(window.locator('.status')).toHaveText('Needs attention', { timeout: 15000 })
      const before = await window.evaluate(async () => {
        const jobs = await window.workbench.invoke('jobs')
        return window.workbench.invoke('job', { job: jobs[0].id })
      })
      expect(before.stop_reason).toBe('budget_exhausted')
      // Inject only persisted clock state while the task is stopped.
      execFileSync(resolve('.venv/Scripts/python.exe'), ['-c',
        'import sys,time; from pdfmd.storage import Store; s=Store(sys.argv[1]); s.update_job(sys.argv[2],active_seconds=17,active_since=time.time()-10000,active_session="offline-clock-fixture")',
        workspace, before.id], { windowsHide: true })
      await window.getByRole('button', { name: 'Task limits', exact: true }).click()
      await window.getByLabel('Task context capacity', { exact: true }).fill('131072')
      await window.getByLabel('Task output reserve', { exact: true }).fill('4096')
      await window.getByLabel('Task total model requests', { exact: true }).fill('10')
      await window.getByLabel('Task active time limit (seconds)', { exact: true }).fill('1800')
      await window.screenshot({ path: join(directory, 'settings-before-save.png') })
      await window.getByRole('button', { name: 'Save task limits' }).click()
      await expect(window.getByTestId('effective-task-limits')).toContainText('131,072')
      // Connection defaults still contain the original 2048/1; Continue must use the task's saved values.
      await window.getByRole('button', { name: 'Continue', exact: true }).click()
      await expect(window.locator('.status')).toHaveText('Completed', { timeout: 30000 })
      expect(payloads).toHaveLength(4)
      const current = await window.evaluate(job => window.workbench.invoke('job', { job }), before.id)
      expect(current.attempts).toBe(4)
      expect(current.limits.max_requests).toBe(10)
      expect(current.active_seconds).toBeGreaterThanOrEqual(17)
      expect(current.active_seconds).toBeLessThan(100)
      expect(current.active_time_gaps).toHaveLength(1)
      expect(current.requests[1].route.context_tokens).toBe(65536)
      expect(current.requests[2].route.context_tokens).toBe(131072)
      await expect(window.getByText('interrupted interval(s) have unknown active time.', { exact: false })).toBeVisible()
      await app.close(); app = await launch(); window = await app.firstWindow()
      await expect(window.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await window.locator('.document-item').first().click()
      await expect(window.getByTestId('effective-task-limits')).toContainText('131,072')
      await expect(window.frameLocator('iframe').getByText('End of the synthetic section.', { exact: false })).toBeVisible()
      await window.frameLocator('iframe').locator('img').evaluateAll(async images => Promise.all(images.map(i => (i as HTMLImageElement).decode())))
      await app.evaluate(({ dialog }, destination) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath: destination }) }, destination)
      await window.getByRole('button', { name: 'Export ZIP' }).click()
      await expect(window.locator('.toast.success')).toContainText('Exported completed version')
      await window.screenshot({ path: join(directory, 'reopened.png') })
      const verification = JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'), ['tests/desktop/verify_delivery.py',
        workspace, source, destination, current.id, current.delivery], { windowsHide: true, encoding: 'utf-8' }))
      expect(verification).toMatchObject({ verified: true, source_pages: 2, blocks: 3, assets: 1, claim: 'complete' })
      await fs.writeFile(join(directory, 'verification.json'), JSON.stringify({ ...verification, protocol, before, current, live_model_calls: 0 }, null, 2))
      await fs.writeFile(join(directory, 'fixture-payloads.json'), JSON.stringify(payloads, null, 2))
    } finally {
      await app.close()
      await new Promise<void>(done => server.close(() => done()))
    }
  })
}
