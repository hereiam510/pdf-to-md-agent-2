import { test, expect, _electron as electron, chromium } from '@playwright/test'
import { createServer } from 'node:http'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'

for (const protocol of ['chat_completions', 'responses']) {
  test(`explicit compaction recovery preserves frozen work and delivery: ${protocol}`, async () => {
    const evidenceRoot = resolve(process.env.PDFMD_RECOVERY_EVIDENCE || '.local/compaction-recovery-desktop')
    await fs.mkdir(evidenceRoot, { recursive: true })
    const directory = await fs.mkdtemp(join(evidenceRoot, `${protocol}-`))
    const payloads: any[] = []
    const errors: string[] = []
    let fixture: any
    const reply = (name?: string, args?: unknown, text?: string) => protocol === 'chat_completions'
      ? { choices: [{ finish_reason: name ? 'tool_calls' : 'stop', message: { role: 'assistant', content: text ?? null,
        tool_calls: name ? [{ id: `call-${payloads.length}`, type: 'function', function: { name, arguments: JSON.stringify(args) } }] : null } }],
        usage: { prompt_tokens: 100, completion_tokens: 20 } }
      : { status: 'completed', output: name
        ? [{ type: 'function_call', call_id: `call-${payloads.length}`, name, arguments: JSON.stringify(args), status: 'completed' }]
        : [{ type: 'message', role: 'assistant', status: 'completed', content: [{ type: 'output_text', text }] }],
        usage: { input_tokens: 100, output_tokens: 20 } }
    const server = createServer(async (req, res) => {
      try {
        const chunks: Buffer[] = []
        for await (const chunk of req) chunks.push(Buffer.from(chunk))
        const payload = JSON.parse(Buffer.concat(chunks).toString())
        payloads.push(payload)
        let response: unknown
        if (payloads.length === 1) {
          expect(payload.tools).toBeUndefined()
          response = reply(undefined, undefined, JSON.stringify({ task: 'Convert the complete one-page synthetic source.',
            current_state: `Existing version ${fixture.version} preserves opening text and source figure.`,
            unfinished_work: ['Append the final source sentence, then save and report.'], dependencies: [],
            references: [fixture.source_ref, fixture.image.ref], cautions: ['Retain the existing draft and image.'] }))
        } else if (payloads.length === 2) {
          expect(payload.tools.length).toBeGreaterThan(0)
          response = reply('edit_document', { base_version: fixture.version, expected_head: fixture.version,
            operations: [{ kind: 'insert', after_id: 'image', blocks: [{ id: 'closing', pages: [1], markdown: fixture.closing }] }],
            claim: 'complete', known_gaps: [] })
        } else if (payloads.length === 3) {
          const outputs = (payload.messages || payload.input).filter((m: any) => m.role === 'tool' || m.type === 'function_call_output')
            .map((m: any) => JSON.parse(m.content ?? m.output))
          const edit = outputs.find((out: any) => out.ok && out.data?.version_id)
          expect(edit).toBeTruthy()
          response = reply('report', { state: 'complete', version_id: edit.data.version_id,
            message: 'The local scripted recovery preserved the existing document and source figure.' })
        } else throw new Error('Unexpected additional request; this fixture authorizes one compaction successor and edit/report.')
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(response))
      } catch (error) {
        errors.push(String(error))
        res.writeHead(500); res.end('Local fixture assertion failed.')
      }
    })
    await new Promise<void>(done => server.listen(0, '127.0.0.1', done))
    const port = (server.address() as { port: number }).port
    const endpoint = `http://127.0.0.1:${port}/v1/${protocol === 'responses' ? 'responses' : 'chat/completions'}`
    const runFixture = (mode: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
      ['-X', 'utf8', 'tests/desktop/compaction-recovery-fixture.py', mode, directory, protocol, endpoint],
      { windowsHide: true, encoding: 'utf-8' }))
    const launch = () => electron.launch({ args: [resolve('out/main/index.js')], env: { ...process.env,
      PDFMD_DATA: join(directory, 'workspace'), PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
    let app: Awaited<ReturnType<typeof launch>> | undefined
    const observed: unknown[] = []
    try {
      fixture = runFixture('prepare')
      app = await launch()
      let page = await app.firstWindow()
      const getJob = () => page.evaluate(async job => globalThis.window.workbench.invoke('job', { job }), fixture.job)
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').first().click()
      await page.getByRole('button', { name: 'Nexus connection' }).click()
      await page.getByLabel('Nexus credential', { exact: true }).fill('fixture-only-in-memory')
      await page.getByLabel('Remember with operating-system encryption').uncheck()
      await page.getByRole('button', { name: 'Save connection' }).click()
      await expect(page.getByRole('button', { name: 'Resume context organization', exact: true })).toBeVisible()
      expect((await getJob()).compaction_recovery.request).toBe(fixture.unknown_request.id)
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await expect.poll(async () => (await getJob()).events.filter((e: any) => e.type === 'stopped').length,
        { timeout: 15000 }).toBe(fixture.unknown_stop_events_before + 1)
      expect(payloads).toHaveLength(0)
      expect((await getJob()).attempts).toBe(fixture.attempts_before)
      await page.getByRole('button', { name: 'Resume context organization', exact: true }).click()
      await expect(page.locator('.status')).toHaveText('Completed', { timeout: 30000 })
      expect(errors).toEqual([])
      expect(payloads).toHaveLength(3)
      const completed = await getJob()
      expect(completed.attempts).toBe(fixture.attempts_before + 3)
      expect(completed.compaction_recovery).toBeNull()
      expect(completed.versions).toHaveLength(2)
      for (const stage of ['saved', 'reopened']) {
        const body = page.frameLocator('iframe').locator('body')
        await expect(body).toContainText(fixture.opening)
        await expect(body).toContainText(fixture.closing)
        const images = body.locator('img')
        await expect(images).toHaveCount(1)
        await images.evaluateAll(async elements => Promise.all(elements.map(el => (el as HTMLImageElement).decode())))
        const size = await images.first().evaluate(el => ({ width: (el as HTMLImageElement).naturalWidth, height: (el as HTMLImageElement).naturalHeight }))
        expect(size).toEqual({ width: fixture.image.width, height: fixture.image.height })
        await body.screenshot({ path: join(directory, `${stage}-preview.png`) })
        observed.push({ stage, size })
        if (stage === 'saved') {
          await app.close(); app = await launch(); page = await app.firstWindow()
          await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
          await page.locator('.document-item').first().click()
          expect((await getJob()).attempts).toBe(completed.attempts)
          expect((await getJob()).compaction_recovery).toBeNull()
          expect(payloads).toHaveLength(3)
        }
      }
      await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, join(directory, 'delivery.zip'))
      await page.getByRole('button', { name: 'Export ZIP' }).click()
      await expect(page.locator('.toast.success')).toContainText('Exported completed version')
      const result = runFixture('verify')
      expect(result.verified).toBe(true)
      expect(payloads).toHaveLength(3)
      await app.close(); app = undefined
      const browser = await chromium.launch({ channel: 'msedge', headless: true })
      try {
        const exported = await browser.newPage()
        await exported.route(/^https?:/, route => route.abort())
        await exported.goto(pathToFileURL(join(directory, 'exported/preview.html')).href)
        await expect(exported.locator('body')).toContainText(fixture.opening)
        await expect(exported.locator('body')).toContainText(fixture.closing)
        const image = exported.locator('img')
        await expect(image).toHaveCount(1)
        await image.evaluate((el: HTMLImageElement) => el.decode())
        await exported.screenshot({ path: join(directory, 'export-preview.png'), fullPage: true })
        observed.push({ stage: 'exported', browser: browser.version() })
      } finally { await browser.close() }
      await fs.writeFile(join(directory, 'renderer-verification.json'), JSON.stringify({ observed,
        ordinary_continue_requests: 0, explicit_recovery_requests: 3, live_model_calls: 0 }, null, 2))
    } finally {
      if (app) await app.close()
      await fs.writeFile(join(directory, 'fixture-payloads.json'), JSON.stringify({ payloads, errors }, null, 2))
      await new Promise<void>(done => server.close(() => done()))
    }
  })
}
