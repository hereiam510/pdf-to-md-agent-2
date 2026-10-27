import { test, expect, _electron as electron, chromium } from '@playwright/test'
import { createServer } from 'node:http'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { execFileSync } from 'node:child_process'

function frames(protocol: string, name: string | undefined, args: unknown, text: string | undefined, ordinal: number): string[] {
  const event = (data: unknown, type?: string) => `${type ? `event: ${type}\n` : ''}data: ${JSON.stringify(data)}\n\n`
  if (protocol === 'chat_completions') {
    const base = { id: `stream-${ordinal}`, object: 'chat.completion.chunk', model: 'local-streaming-fixture' }
    const chunk = (delta: unknown, finish_reason: string | null = null) => event({ ...base, choices: [{ index: 0, delta, finish_reason }] })
    const result = [': transport heartbeat\n\n', chunk({ role: 'assistant' })]
    if (name) result.push(chunk({ tool_calls: [{ index: 0, id: `call-${ordinal}`, type: 'function', function: { name, arguments: '' } }] }))
    const body = name ? JSON.stringify(args) : text!
    for (let offset = 0; offset < body.length; offset += 35) result.push(chunk(name
      ? { tool_calls: [{ index: 0, function: { arguments: body.slice(offset, offset + 35) } }] }
      : { content: body.slice(offset, offset + 35) }))
    result.push(chunk({}, name ? 'tool_calls' : 'stop'), event({ ...base, choices: [], usage: { prompt_tokens: 100, completion_tokens: 50 } }), 'data: [DONE]\n\n')
    return result
  }
  const item = name
    ? { id: `item-${ordinal}`, type: 'function_call', call_id: `call-${ordinal}`, name, arguments: JSON.stringify(args), status: 'completed' }
    : { id: `item-${ordinal}`, type: 'message', role: 'assistant', content: [{ type: 'output_text', text }], status: 'completed' }
  let sequence_number = 0
  const result = [': transport heartbeat\n\n', event({ type: 'response.created', sequence_number: sequence_number++, response: { id: `stream-${ordinal}`, status: 'in_progress', output: [] } }, 'response.created')]
  result.push(event({ type: 'response.output_item.added', sequence_number: sequence_number++, output_index: 0,
    item: name ? { ...item, arguments: '', status: 'in_progress' } : { ...item, content: [], status: 'in_progress' } }, 'response.output_item.added'))
  const body = name ? JSON.stringify(args) : text!
  const type = name ? 'response.function_call_arguments.delta' : 'response.output_text.delta'
  for (let offset = 0; offset < body.length; offset += 35) result.push(event({ type, sequence_number: sequence_number++,
    output_index: 0, item_id: item.id, content_index: 0, delta: body.slice(offset, offset + 35) }, type))
  result.push(event({ type: 'response.output_item.done', sequence_number: sequence_number++, output_index: 0, item }, 'response.output_item.done'),
    event({ type: 'response.completed', sequence_number: sequence_number++, response: { id: `stream-${ordinal}`, object: 'response',
      status: 'completed', output: [item], usage: { input_tokens: 100, output_tokens: 50 } } }, 'response.completed'))
  return result
}

for (const protocol of ['chat_completions', 'responses']) {
  test(`streamed compaction recovery, save, reopen and exported renderer: ${protocol}`, async () => {
    const root = resolve(process.env.PDFMD_STREAM_EVIDENCE || '.local/stream-progress-evidence/delivery/desktop')
    await fs.mkdir(root, { recursive: true })
    const directory = await fs.mkdtemp(join(root, `${protocol}-`))
    const payloads: any[] = [], errors: string[] = [], observations: unknown[] = [], rawStreams: string[] = []
    let fixture: any
    let releaseFirst: (() => void) | undefined
    const server = createServer(async (request, response) => {
      try {
        const parts: Buffer[] = []
        for await (const part of request) parts.push(Buffer.from(part))
        const payload = JSON.parse(Buffer.concat(parts).toString())
        payloads.push(payload)
        expect(payload.stream).toBe(true)
        let stream: string[]
        if (payloads.length === 1) {
          expect(payload.tools).toBeUndefined()
          stream = frames(protocol, undefined, undefined, JSON.stringify({ task: 'Convert the complete one-page synthetic source.',
            current_state: `Version ${fixture.version} preserves opening text and source figure.`,
            unfinished_work: ['Append the final source sentence, then save and report.'], dependencies: [],
            references: [fixture.source_ref, fixture.image.ref], cautions: ['Retain the existing draft and source image.'] }), 1)
        } else if (payloads.length === 2) {
          expect(payload.tools.length).toBeGreaterThan(0)
          stream = frames(protocol, 'edit_document', { base_version: fixture.version, expected_head: fixture.version,
            operations: [{ kind: 'insert', after_id: 'image', blocks: [{ id: 'closing', pages: [1], markdown: fixture.closing }] }],
            claim: 'complete', known_gaps: [] }, undefined, 2)
        } else {
          expect(payloads).toHaveLength(3)
          const outputs = (payload.messages || payload.input).filter((m: any) => m.role === 'tool' || m.type === 'function_call_output')
            .map((m: any) => JSON.parse(m.content ?? m.output))
          const saved = outputs.find((out: any) => out.ok && out.data?.version_id)
          expect(saved).toBeTruthy()
          stream = frames(protocol, 'report', { state: 'complete', version_id: saved.data.version_id,
            message: 'The complete synthetic source and figure are saved.' }, undefined, 3)
        }
        rawStreams.push(stream.join(''))
        response.setHeader('Content-Type', 'text/event-stream')
        response.setHeader('Cache-Control', 'no-cache')
        response.flushHeaders()
        for (const [index, frame] of stream.entries()) {
          // Deliberately split JSON fields across socket writes, with real asynchronous delivery.
          const split = Math.min(19, frame.length)
          response.write(frame.slice(0, split))
          await new Promise(done => setTimeout(done, 2))
          response.write(frame.slice(split))
          if (payloads.length === 1 && index === 3) {
            await new Promise<void>(done => { releaseFirst = done })
          }
        }
        response.end()
      } catch (error) {
        errors.push(String(error))
        if (!response.headersSent) response.writeHead(500)
        response.end()
      }
    })
    await new Promise<void>(done => server.listen(0, '127.0.0.1', done))
    const port = (server.address() as { port: number }).port
    const endpoint = `http://127.0.0.1:${port}/v1/${protocol === 'responses' ? 'responses' : 'chat/completions'}`
    const runFixture = (mode: string) => JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'),
      ['-X', 'utf8', 'tests/desktop/streaming-delivery-fixture.py', mode, directory, protocol, endpoint],
      { windowsHide: true, encoding: 'utf-8' }))
    const launch = () => electron.launch({ args: [resolve('out/main/index.js')], env: { ...process.env,
      PDFMD_DATA: join(directory, 'workspace'), PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') } })
    let app: Awaited<ReturnType<typeof launch>> | undefined
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
      await page.getByRole('button', { name: 'Task limits', exact: true }).click()
      await page.getByLabel('Response waiting', { exact: true }).selectOption('streaming')
      await expect(page.getByLabel('First progress wait (seconds)', { exact: true })).toHaveValue('600')
      await expect(page.getByLabel('Progress idle wait (seconds)', { exact: true })).toHaveValue('300')
      await expect(page.getByLabel('Set a total request deadline', { exact: true })).not.toBeChecked()
      await page.screenshot({ path: join(directory, 'stream-wait-settings.png') })
      await page.getByRole('button', { name: 'Save task limits' }).click()
      await expect(page.getByRole('form', { name: 'Task limits', exact: true })).toBeHidden()
      const configured = await getJob()
      expect(configured.route.wait_policy).toEqual(fixture.wait_policy)
      expect(configured.attempts).toBe(fixture.attempts_before)
      expect(configured.active_seconds).toBe(fixture.active_seconds_before)
      expect(configured.requests.find((r: any) => r.id === fixture.unknown_request.id).route).toEqual(fixture.route)
      expect(payloads).toHaveLength(0)
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await expect.poll(async () => (await getJob()).events.filter((e: any) => e.type === 'stopped').length,
        { timeout: 15000 }).toBe(fixture.unknown_stop_events_before + 1)
      expect(payloads).toHaveLength(0)
      await page.getByRole('button', { name: 'Resume context organization', exact: true }).click()
      await expect(page.getByTestId('receive-progress')).toContainText('Receiving generation progress', { timeout: 15000 })
      const partial = await getJob()
      expect(partial.head).toBe(fixture.version)
      expect(partial.versions).toHaveLength(1)
      expect(payloads).toHaveLength(1)
      await page.screenshot({ path: join(directory, 'receiving-progress.png') })
      observations.push({ stage: 'incomplete_compaction', previous_draft_unchanged: true, requests: payloads.length })
      releaseFirst!()
      await expect(page.locator('.status')).toHaveText('Completed', { timeout: 30000 })
      await expect(page.getByTestId('receive-progress')).toContainText('Complete response accepted')
      await expect(page.getByTestId('receive-progress')).toContainText('HTTP 200')
      expect(errors).toEqual([])
      expect(payloads).toHaveLength(3)
      const completed = await getJob()
      expect(completed.attempts).toBe(fixture.attempts_before + 3)
      expect(completed.versions).toHaveLength(2)
      expect(completed.compaction_recovery).toBeNull()
      const duplicate = await page.evaluate(async args => {
        try { await globalThis.window.workbench.invoke('start', args); return false } catch { return true }
      }, { job: fixture.job, recover_compaction_request: fixture.unknown_request.id })
      expect(duplicate).toBe(true)
      expect(payloads).toHaveLength(3)
      for (const stage of ['saved', 'reopened']) {
        const body = page.frameLocator('iframe').locator('body')
        await expect(body).toContainText(fixture.opening)
        await expect(body).toContainText(fixture.closing)
        const images = body.locator('img')
        await expect(images).toHaveCount(1)
        await images.first().evaluate((el: HTMLImageElement) => el.decode())
        const size = await images.first().evaluate((el: HTMLImageElement) => ({ width: el.naturalWidth, height: el.naturalHeight }))
        expect(size).toEqual({ width: fixture.image.width, height: fixture.image.height })
        await body.screenshot({ path: join(directory, `${stage}-preview.png`) })
        observations.push({ stage, size, text: [fixture.opening, fixture.closing] })
        if (stage === 'saved') {
          await app.close(); app = await launch(); page = await app.firstWindow()
          await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
          await page.locator('.document-item').first().click()
          expect((await getJob()).attempts).toBe(completed.attempts)
          expect((await getJob()).route).toEqual(configured.route)
          expect(payloads).toHaveLength(3)
        }
      }
      await app.evaluate(({ dialog }, filePath) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath }) }, join(directory, 'delivery.zip'))
      await page.getByRole('button', { name: 'Export ZIP' }).click()
      await expect(page.locator('.toast.success')).toContainText('Exported completed version')
      expect(runFixture('verify').verified).toBe(true)
      await app.close(); app = undefined
      const browser = await chromium.launch({ channel: 'msedge', headless: true })
      try {
        const exported = await browser.newPage()
        await exported.route(/^https?:/, route => route.abort())
        await exported.goto(pathToFileURL(join(directory, 'exported/preview.html')).href)
        await expect(exported.locator('body')).toContainText(fixture.opening)
        await expect(exported.locator('body')).toContainText(fixture.closing)
        await expect(exported.locator('img')).toHaveCount(1)
        await exported.locator('img').evaluate((el: HTMLImageElement) => el.decode())
        await exported.screenshot({ path: join(directory, 'export-preview.png'), fullPage: true })
        observations.push({ stage: 'exported', browser: browser.version() })
      } finally { await browser.close() }
      expect(payloads).toHaveLength(3)
      await fs.writeFile(join(directory, 'renderer-verification.json'), JSON.stringify({ observations,
        settings_and_plain_continue_requests: 0, streamed_recovery_and_followup_requests: 3,
        duplicate_recovery_rejected: true, wait_policy: fixture.wait_policy, live_model_calls: 0 }, null, 2))
    } finally {
      releaseFirst?.()
      if (app) await app.close()
      await fs.writeFile(join(directory, 'fixture-payloads.json'), JSON.stringify({ payloads, rawStreams, errors }, null, 2))
      await new Promise<void>(done => server.close(() => done()))
    }
  })
}
