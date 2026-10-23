import { test, expect, _electron as electron } from '@playwright/test'
import { createServer } from 'node:http'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

test('desktop imports, converts through a local fixture, previews, edits, exports, and reopens', async () => {
  const local = resolve('.local')
  await fs.mkdir(local, { recursive: true })
  const directory = await fs.mkdtemp(join(local, 'desktop-'))
  const source = join(directory, 'Field notes.pdf')
  const destination = join(directory, 'delivery.zip')
  execFileSync(resolve('.venv/Scripts/python.exe'), ['tools/make-smoke-pdf.py', source], { windowsHide: true })
  let requests = 0
  const payloads: any[] = []
  const server = createServer(async (req, res) => {
    const parts: Buffer[] = []
    for await (const part of req) parts.push(Buffer.from(part))
    const payload = JSON.parse(Buffer.concat(parts).toString())
    payloads.push(payload); requests++
    if (requests === 1) {
      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify({ id: 'fixture-narration', choices: [{ finish_reason: 'stop', message: {
        role: 'assistant', content: 'I will read the two source pages next.' } }] }))
      return
    }
    const step = requests - 1
    const outputs = payload.messages.filter((m: any) => m.role === 'tool').map((m: any) => JSON.parse(m.content))
    let name: string, args: unknown
    if (step === 1) { name = 'inspect_pdf'; args = { pages: [1, 2], mode: 'text' } }
    else if (step === 2) { name = 'render_page'; args = { page: 1, dpi: 144, region: [60, 310, 530, 490] } }
    else if (step === 3) {
      const pages = outputs[0].data.value.pages
      name = 'edit_document'; args = { base_version: null, expected_head: null, title: 'A small, complete section',
        replace_blocks: [
          { id: 'section', pages: [1], markdown: '# A small, complete section\n\n' + pages[0].content },
          { id: 'figure', pages: [1], markdown: `![Figure 1. Unchanged source region.](${outputs[1].data.asset_path})` },
          { id: 'continuation', pages: [2], markdown: '## The section continues\n\n' + pages[1].content }
        ], page_updates: { '1': { printed: '1', disposition: 'included' }, '2': { printed: '2', disposition: 'included' } }, claim: 'complete' }
    } else if (step === 4) { name = 'preview_document'; args = { version_id: outputs[2].data.version_id, width: 1024, height: 900 } }
    else { name = 'report'; args = { state: 'complete', message: 'Saved both pages and the unchanged source figure. This run used a local fixture, not a live model.', version_id: outputs[2].data.version_id } }
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({ id: `fixture-${requests}`, choices: [{ finish_reason: 'tool_calls', message: { role: 'assistant', content: null,
      tool_calls: [{ id: `call-${requests}`, type: 'function', function: { name, arguments: JSON.stringify(args) } }] } }], usage: { prompt_tokens: 100, completion_tokens: 100 } }))
  })
  await new Promise<void>(done => server.listen(0, '127.0.0.1', done))
  const address = server.address() as { port: number }
  const env = { ...process.env, PDFMD_DATA: join(directory, 'workspace'), PDFMD_PYTHON: resolve('.venv/Scripts/python.exe') }
  const launch = () => electron.launch({ executablePath: process.env.PDFMD_PACKAGED_EXE,
    args: process.env.PDFMD_PACKAGED_EXE ? [] : [resolve('out/main/index.js')], env })
  let app = await launch()
  try {
    let window = await app.firstWindow()
    await expect(window.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
    await fs.mkdir(resolve('.local/qa'), { recursive: true })
    await window.screenshot({ path: '.local/qa/welcome.png' })
    await app.evaluate(({ dialog }, files) => {
      dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [files.source] })
      dialog.showSaveDialog = async () => ({ canceled: false, filePath: files.destination })
    }, { source, destination })
    await window.getByRole('button', { name: 'Nexus connection' }).click()
    await window.getByLabel('Full endpoint URL').fill(`http://127.0.0.1:${address.port}/v1/chat/completions`)
    await window.getByLabel('Model alias').fill('Local software fixture')
    await window.getByLabel('Nexus credential', { exact: true }).fill('fixture-only-credential')
    await window.getByLabel('This route accepts image inputs').check()
    await window.getByText('Optional recovery and model parameters', { exact: true }).click()
    await expect(window.getByLabel('Automatic response corrections', { exact: true })).toHaveValue('2')
    await window.screenshot({ path: '.local/qa/connection.png' })
    await window.getByRole('button', { name: 'Save connection' }).click()
    await window.getByRole('button', { name: 'Choose a PDF' }).click()
    await window.getByRole('button', { name: 'Open document', exact: true }).click()
    await expect(window.getByRole('heading', { name: 'Field notes', exact: true })).toBeVisible()
    await window.getByRole('button', { name: 'Start conversion', exact: true }).click()
    await expect(window.locator('.status')).toHaveText('Completed', { timeout: 60000 })
    expect(requests).toBe(6)
    expect(JSON.stringify(payloads[1])).toContain('Application continuation feedback')
    const job = await window.evaluate(async () => {
      const jobs = await globalThis.window.workbench.invoke('jobs')
      return globalThis.window.workbench.invoke('job', { job: jobs[0].id })
    })
    const saved = await window.evaluate(async ({ job, version }) => globalThis.window.workbench.invoke('version', { job, version }),
      { job: job.id, version: job.delivery })
    const sourcePages = JSON.parse(payloads[2].messages.find((m: any) => m.role === 'tool').content).data.value.pages
    expect(saved.content.blocks[0].markdown).toBe('# A small, complete section\n\n' + sourcePages[0].content)
    expect(saved.content.blocks[2].markdown).toBe('## The section continues\n\n' + sourcePages[1].content)
    expect(saved.content.claim).toBe('complete')
    const previewOperation = job.events.find((e: any) => e.type === 'tool_settled' && e.data.tool === 'preview_document')
    expect(previewOperation?.data.ok).toBe(true)
    const previewResult = await window.evaluate(async ({ job, ref }) => globalThis.window.workbench.invoke('evidence', { job, ref }),
      { job: job.id, ref: previewOperation.data.result_ref })
    expect(previewResult.value.top).toBeGreaterThanOrEqual(0)
    expect(previewResult.value.viewport_height).toBeGreaterThan(0)
    expect(previewResult.value.width).toBeGreaterThan(0)
    expect(previewResult.value.document_height).toBeGreaterThanOrEqual(previewResult.value.viewport_height)
    expect(payloads[3].messages.some((m: any) => Array.isArray(m.content) && m.content.some((p: any) => p.type === 'image_url'))).toBe(true)
    await expect(window.frameLocator('iframe').getByText('End of the synthetic section.', { exact: false })).toBeVisible()
    await window.screenshot({ path: '.local/qa/workspace.png' })
    await window.getByRole('button', { name: 'Export ZIP' }).click()
    await expect(window.getByRole('status')).toContainText('Exported completed version')
    expect((await fs.stat(destination)).size).toBeGreaterThan(1000)
    await window.getByRole('button', { name: 'Edit content', exact: true }).click()
    await window.locator('.block-editor textarea').first().fill('# Manual local correction\n\nUnchanged source remains available.')
    await window.getByRole('button', { name: 'Save new version' }).click()
    await expect(window.getByRole('status')).toContainText('Saved your edits')
    expect(requests).toBe(6)
    await app.close()
    app = await launch()
    window = await app.firstWindow()
    await expect(window.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
    await window.locator('.document-item').first().click()
    await expect(window.frameLocator('iframe').getByRole('heading', { name: 'Manual local correction' })).toBeVisible()
    expect(requests).toBe(6)
  } finally {
    await app.close()
    await new Promise<void>(done => server.close(() => done()))
  }
})
