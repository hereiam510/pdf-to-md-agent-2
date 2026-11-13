import { test, expect, _electron as electron } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { createServer } from 'node:http'
import { promises as fs } from 'node:fs'
import { join, resolve } from 'node:path'
import { testRunRoot } from '../support/artifacts'

test('activity reports a recorded wake and a paused request shows its cooldown', async () => {
  const root = await fs.mkdtemp(join(testRunRoot, 'network-ui-'))
  const launcher = join(root, 'launcher.cjs')
  const html = resolve('out/renderer/index.html')
  const preload = resolve('out/preload/index.js')
  await fs.writeFile(launcher, `
    const {app,BrowserWindow,ipcMain}=require('electron');
    app.setPath('userData',${JSON.stringify(join(root, 'profile'))});
    const job={id:'fixture',name:'Network fixture',scope:'Complete source',status:'blocked',page_count:1,
      attempts:1,active_seconds:0,limits:{max_requests:80},requests:[],event_summary:{count:1,latest_seq:1},
      network_recovery:{request:'fixture:0:0',class:'transient_status',action:'retry',
        retry_available_at:'03:00:00',retry_remaining_seconds:20}};
    const calls=globalThis.calls=[];
    app.whenReady().then(()=>{
      ipcMain.handle('workbench',(_event,action,args)=>{
        if(action==='start'){calls.push(args);return {started:true};}
        if(action==='jobs') return [job];
        if(action==='job') return job;
        if(action==='settings') return {hasKey:true,route:{model:'local'}};
        if(action==='health') return {ready:true};
        if(action==='page') return {url:''};
        if(action==='activity') return {status:'ok',view:'fixture',job:job.id,captured_at:0,consistency:'fixture',
          total:1,first:1,last:1,boundary_seq:1,events:[{id:'one',seq:1,type:'resumed_after_sleep',created:0,data:{duration_seconds:10}}]};
        if(action==='closeDiagnostics') return {closed:true};
        throw Error(action);
      });
      const window=new BrowserWindow({show:false,webPreferences:{preload:${JSON.stringify(preload)}}});
      window.loadFile(${JSON.stringify(html)});
    });
    globalThis.finishCooldown=()=>{job.network_recovery.retry_available_at=null;};
    app.on('window-all-closed',()=>app.quit());`)
  const app = await electron.launch({ args: [launcher] })
  try {
    const page = await app.firstWindow()
    await page.getByRole('button', { name: /Network fixture/ }).click()
    const retry = page.getByRole('button', { name: 'Retry', exact: true })
    await expect(retry).toBeDisabled()
    await expect(page.getByText('Retry available at 03:00:00')).toBeVisible()
    await page.getByRole('button', { name: /View activity and diagnostics/ }).click()
    await expect(page.getByText(/Resumed after sleep \(10.0 seconds\)/)).toBeVisible()
    await app.evaluate(() => (globalThis as any).finishCooldown())
    await expect(retry).toBeEnabled()
    await retry.click()
    expect(await app.evaluate(() => (globalThis as any).calls)).toMatchObject([{ retry_request: 'fixture:0:0' }])
  } finally { await app.close() }
})

test('network retry survives server restart and engine termination and exports the saved source', async () => {
  const directory = await fs.mkdtemp(join(testRunRoot, 'network-'))
  const workspace = join(directory, 'workspace')
  const destination = join(directory, 'delivery.zip')
  const python = resolve('.venv/Scripts/python.exe')
  const launcher = join(directory, 'launcher.cjs')
  const pidFile = join(directory, 'engine.pid')
  await fs.writeFile(launcher, `const {app}=require('electron'); app.setPath('userData', ${JSON.stringify(join(directory, 'profile'))});
    const cp=require('node:child_process'), spawn=cp.spawn;
    cp.spawn=(exe,args,...rest)=>{const child=spawn(exe,args,...rest);
      if(args.includes('pdfmd.server')) require('node:fs').writeFileSync(${JSON.stringify(pidFile)},String(child.pid));
      return child;}; require(${JSON.stringify(resolve('out/main/index.js'))});`)
  let phase = 'disconnect'
  const payloads: Buffer[] = []
  let savedVersion = ''
  const server = createServer(async (request, response) => {
    const chunks: Buffer[] = []
    for await (const chunk of request) chunks.push(Buffer.from(chunk))
    payloads.push(Buffer.concat(chunks))
    if (phase === 'disconnect') {
      request.socket.destroy()
      return
    }
    if (phase === 'wait') {
      response.writeHead(503, { 'Retry-After': '20' })
      response.end()
      return
    }
    if (phase === 'configuration') {
      response.writeHead(401)
      response.end()
      return
    }
    await new Promise(done => setTimeout(done, 250))
    response.setHeader('Content-Type', 'application/json')
    response.end(JSON.stringify({ id: 'local-delayed-reply', choices: [{ finish_reason: 'tool_calls', message: {
      role: 'assistant', content: null, tool_calls: [{ id: 'report', type: 'function', function: {
        name: 'report', arguments: JSON.stringify({ state: 'complete', version_id: savedVersion, message: 'Saved source is complete.' })
      } }] } }] }))
  })
  const listen = (port: number) => new Promise<void>(done => server.listen(port, '127.0.0.1', done))
  const close = () => new Promise<void>(done => server.close(() => done()))
  await listen(0)
  const port = (server.address() as { port: number }).port
  const endpoint = `http://127.0.0.1:${port}/v1/chat/completions`
  const source = join(directory, 'Synthetic.pdf')
  const fixture = JSON.parse(execFileSync(python, ['-c', `
import json
import sys
import pymupdf
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
workspace, source, endpoint = sys.argv[1:]
text = 'Preserve the complete synthetic source. Keep 25 mg.'
with pymupdf.open() as pdf:
    pdf.new_page().insert_text((72, 72), text)
    pdf.save(source)
store = Store(workspace)
dispatcher = Dispatcher(store)
job = dispatcher.evidence.create_job(source, 'Convert the complete source.',
    {'endpoint': endpoint, 'model': 'local-network', 'context_tokens': 65536, 'output_tokens': 2048},
    {'automatic_retry': False})
saved = dispatcher.execute(job['id'], 'seed', 'edit_document', json.dumps({
    'base_version': None, 'expected_head': None, 'replace_blocks': [{'id': 'text', 'pages': [1], 'markdown': text}],
    'page_updates': {'1': {'printed': 'none', 'disposition': 'included'}}, 'claim': 'complete'}))
assert saved['ok'], saved
print(json.dumps({'job': job['id'], 'version': saved['data']['version_id']}))
`, workspace, source, endpoint], { encoding: 'utf-8', windowsHide: true }))
  savedVersion = fixture.version
  const launch = () => electron.launch({ args: [launcher], env: { ...process.env, PDFMD_DATA: workspace, PDFMD_PYTHON: python } })
  let app = await launch()
  try {
    let page = await app.firstWindow()
    const open = async () => {
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').first().click()
      await page.getByRole('button', { name: 'Nexus connection' }).click()
      await page.getByLabel('Full endpoint URL').fill(endpoint)
      await page.getByLabel('Model alias').fill('local-network')
      await page.getByLabel('Nexus credential', { exact: true }).fill('offline-fixture')
      await page.getByLabel('Remember with operating-system encryption').uncheck()
      await page.getByRole('button', { name: 'Save connection' }).click()
    }
    const getJob = () => page.evaluate(job => window.workbench.invoke('job', { job }), fixture.job)
    await open()
    await page.getByRole('button', { name: 'Start conversion', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Retry', exact: true })).toBeVisible()
    const pending = (await getJob()).network_recovery
    expect(pending).toMatchObject({ class: 'lost_after_send', attempts_used: 1, action: 'retry' })
    await close()
    phase = 'wait'
    await listen(port)
    await page.getByRole('button', { name: 'Task limits', exact: true }).click()
    await page.getByLabel('Retry automatically after network problems').check()
    await expect(page.getByLabel('Maximum attempts per request')).toHaveValue('3')
    await page.getByRole('button', { name: 'Save task limits' }).click()
    await page.getByRole('button', { name: 'Retry', exact: true }).click()
    await expect.poll(() => payloads.length).toBe(2)
    await page.getByRole('button', { name: /View activity and diagnostics/ }).click()
    await expect(page.getByText(/Temporary HTTP failure.*Next retry at/).first()).toBeVisible()
    await expect(page.getByText(/Attempt 1 of 3/).first()).toBeVisible()
    execFileSync('taskkill.exe', ['/PID', await fs.readFile(pidFile, 'utf-8'), '/T', '/F'], { windowsHide: true })
    await expect(page.getByText(/The local engine exited/)).toBeVisible()
    await app.close()
    phase = 'configuration'
    app = await launch()
    page = await app.firstWindow()
    await open()
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    await expect.poll(async () => (await getJob()).stop_reason, { timeout: 45000 }).toBe('provider_configuration_error')
    expect(payloads[1].equals(payloads[2])).toBe(true)
    const duplicate = await page.evaluate(({ job, request }) => window.workbench.invoke('start', { job, retry_request: request }),
      { job: fixture.job, request: pending.request })
    expect(duplicate.started).toBe(false)
    expect(payloads).toHaveLength(3)
    phase = 'complete'
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    await expect(page.locator('.status')).toHaveText('Completed', { timeout: 20000 })
    const job = await getJob()
    expect(job.head).toBe(savedVersion)
    expect(job.attempts).toBe(4)
    expect(job.requests).toHaveLength(3)
    await expect(page.frameLocator('iframe').getByText(/Keep 25 mg/)).toBeVisible()
    await app.evaluate(({ dialog }, path) => {
      dialog.showSaveDialog = async () => ({ canceled: false, filePath: path })
    }, destination)
    await page.getByRole('button', { name: 'Export ZIP' }).click()
    await expect(page.locator('.toast.success')).toContainText('ZIP bytes verified')
    const report = execFileSync(python, ['tests/desktop/support/verify_delivery.py',
      workspace, source, destination, fixture.job, savedVersion], { encoding: 'utf-8', windowsHide: true })
    expect(JSON.parse(report)).toMatchObject({ claim: 'complete', verified: true, source_pages: 1 })
    await fs.writeFile(join(directory, 'verification.json'), report)
  } finally {
    await app.close()
    if (server.listening) await close()
  }
})
