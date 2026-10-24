import { test, expect, _electron as electron } from '@playwright/test'
import { createServer } from 'node:http'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

test('Stop with new instructions, failed-request Continue, restart and export preserve the complete source', async () => {
  await fs.mkdir(resolve('.local'), { recursive: true })
  const directory = await fs.mkdtemp(resolve('.local/continuation-desktop-'))
  const workspace = join(directory, 'workspace')
  const source = join(directory, 'Continuation source.pdf')
  const destination = join(directory, 'delivery.zip')
  execFileSync(resolve('.venv/Scripts/python.exe'), ['tools/make-smoke-pdf.py', source], { windowsHide: true })
  const payloads: any[] = []
  let savedVersion = ''
  const functionCall = (name: string, args: unknown, id: string) => ({ id, type: 'function', function: { name, arguments: JSON.stringify(args) } })
  const server = createServer(async (req, res) => {
    const chunks: Buffer[] = []
    for await (const chunk of req) chunks.push(Buffer.from(chunk))
    const payload = JSON.parse(Buffer.concat(chunks).toString())
    payloads.push(payload)
    const outputs = payload.messages.filter((m: any) => m.role === 'tool').map((m: any) => JSON.parse(m.content))
    let calls: unknown[]
    if (payloads.length === 1) calls = [functionCall('inspect_pdf', { pages: [1, 2], mode: 'text' }, 'read')]
    else if (payloads.length === 2) calls = [functionCall('render_page', { page: 1, dpi: 144, region: [60, 310, 530, 490] }, 'image')]
    else if (payloads.length === 3) {
      calls = [functionCall('edit_document', { base_version: null, expected_head: null, title: 'Complete section',
        replace_blocks: [
          { id: 'p1', pages: [1], markdown: outputs[0].data.value.pages[0].content },
          { id: 'figure', pages: [1], markdown: `![Source figure](${outputs[1].data.asset_path})` },
          { id: 'p2', pages: [2], markdown: outputs[0].data.value.pages[1].content }
        ], page_updates: { '1': { printed: '1', disposition: 'included' }, '2': { printed: '2', disposition: 'included' } }, claim: 'complete' }, 'save')]
    } else if (payloads.length === 4) {
      savedVersion = outputs[2].data.version_id
      calls = [functionCall('context_update', { notes: 'pause-after-settlement-fixture' }, 'policy'),
        functionCall('edit_document', { base_version: savedVersion, expected_head: savedVersion, claim: 'partial',
          operations: [{ kind: 'delete', id: 'p2' }, { kind: 'delete', id: 'figure' }] }, 'obsolete-edit')]
    } else if (payloads.length === 5) {
      res.writeHead(502); res.end('Local failure fixture'); return
    } else {
      calls = [functionCall('report', { state: 'complete', version_id: savedVersion, message: 'Both source pages and the image are preserved.' }, 'done')]
    }
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({ id: `fixture-${payloads.length}`, choices: [{ finish_reason: 'tool_calls',
      message: { role: 'assistant', content: null, tool_calls: calls } }], usage: { prompt_tokens: 100, completion_tokens: 50 } }))
  })
  await new Promise<void>(done => server.listen(0, '127.0.0.1', done))
  const address = server.address() as { port: number }
  const launch = () => electron.launch({ args: [resolve('out/main/index.js')], env: { ...process.env,
    PDFMD_DATA: workspace, PDFMD_PYTHON: resolve('.venv/Scripts/python.exe'),
    PYTHONPATH: resolve('tests/desktop/boundary-hook'), PDFMD_TEST_BOUNDARY: join(directory, 'settled.txt') } })
  let app = await launch()
  try {
    let window = await app.firstWindow()
    await expect(window.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
    await app.evaluate(({ dialog }, source) => {
      dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [source] })
    }, source)
    await window.getByRole('button', { name: 'Nexus connection' }).click()
    await window.getByLabel('Full endpoint URL').fill(`http://127.0.0.1:${address.port}/v1/chat/completions`)
    await window.getByLabel('Model alias').fill('Local continuation fixture')
    await window.getByLabel('Nexus credential', { exact: true }).fill('fixture-only')
    await window.getByLabel('This route accepts image inputs').check()
    await window.getByRole('button', { name: 'Save connection' }).click()
    await window.getByRole('button', { name: 'Choose a PDF' }).click()
    await window.getByRole('button', { name: 'Open document', exact: true }).click()
    await window.getByRole('button', { name: 'Start conversion', exact: true }).click()
    // A test-only Python hook pauses after the real receipt, before the next tool.
    // This exercises UI Stop at a known boundary, not an unknown interrupted process.
    await expect.poll(() => fs.stat(join(directory, 'settled.txt')).then(() => true).catch(() => false),
      { timeout: 30000 }).toBe(true)
    await window.getByRole('button', { name: 'Stop', exact: true }).click()
    await expect(window.locator('.status')).toHaveText('Stopped', { timeout: 15000 })
    expect(payloads).toHaveLength(4)
    await window.getByLabel('Instructions or reply').fill('Preserve the second page and source image. Finish the complete requested scope.')
    await window.getByRole('button', { name: 'Continue', exact: true }).click()
    await expect(window.locator('.status')).toHaveText('Needs attention', { timeout: 15000 })
    expect(payloads).toHaveLength(5)
    const skipped = payloads[4].messages.find((m: any) => m.tool_call_id === 'obsolete-edit')
    expect(JSON.parse(skipped.content)).toMatchObject({ ok: false, data: { skipped: true, execution: 'not_started' } })
    expect(JSON.stringify(payloads[4])).toContain('Preserve the second page')
    await window.getByLabel('Instructions or reply').fill('Continue after the provider error; preserve all saved content.')
    await window.getByRole('button', { name: 'Continue', exact: true }).click()
    await expect(window.locator('.status')).toHaveText('Completed', { timeout: 15000 })
    expect(payloads).toHaveLength(6)
    expect(JSON.stringify(payloads[5])).toContain('Request continuation record')
    expect(JSON.stringify(payloads[5])).toContain('Continue after the provider error')
    const job = await window.evaluate(async () => {
      const jobs = await globalThis.window.workbench.invoke('jobs')
      return globalThis.window.workbench.invoke('job', { job: jobs[0].id })
    })
    expect(job.head).toBe(savedVersion)
    expect(job.versions).toHaveLength(1)
    expect(job.attempts).toBe(6)
    await app.close()
    app = await launch()
    window = await app.firstWindow()
    await expect(window.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
    await window.locator('.document-item').first().click()
    await expect(window.frameLocator('iframe').getByText('End of the synthetic section.', { exact: false })).toBeVisible()
    await app.evaluate(({ dialog }, destination) => {
      dialog.showSaveDialog = async () => ({ canceled: false, filePath: destination })
    }, destination)
    await window.getByRole('button', { name: 'Export ZIP' }).click()
    await expect(window.getByRole('status')).toContainText('Exported completed version')
    await window.screenshot({ path: join(directory, 'reopened.png') })
    const verification = JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'), ['tests/desktop/verify_delivery.py',
      workspace, source, destination, job.id, savedVersion], { windowsHide: true, encoding: 'utf-8' }))
    expect(verification).toMatchObject({ source_pages: 2, blocks: 3, assets: 1, claim: 'complete', verified: true })
    await fs.writeFile(join(directory, 'verification.json'), JSON.stringify({ ...verification, requests: payloads.length,
      skipped_call: JSON.parse(skipped.content), pipeline: 'save -> Stop -> amend -> skip obsolete edit -> HTTP 502 -> Continue -> complete -> restart -> export' }, null, 2))
    await fs.writeFile(join(directory, 'fixture-payloads.json'), JSON.stringify(payloads, null, 2))
    expect(payloads).toHaveLength(6)
  } finally {
    await app.close()
    await new Promise<void>(done => server.close(() => done()))
  }
})
