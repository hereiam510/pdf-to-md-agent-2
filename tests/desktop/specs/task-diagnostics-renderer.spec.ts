import { testRunRoot } from '../support/artifacts'
import { test, expect, _electron as electron, type Page } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

declare global {
  interface Window {
    diagnosticRejectionFixture: {
      replies: unknown[];
      calls: { action: string; args: Record<string, unknown> }[];
      render: () => void;
    }
  }
}

let root: string
test.beforeAll(async () => {
  const parent = resolve(process.env.PDFMD_F01_F02_RENDERER || resolve(testRunRoot, 'task-diagnostics-renderer'))
  await fs.mkdir(parent, { recursive: true }); root = await fs.mkdtemp(join(parent, 'run-'))
  await fs.writeFile(join(root, 'index.html'), '<div id="root"></div><script type="module" src="/entry.tsx"></script>')
  await fs.writeFile(join(root, 'entry.tsx'), `
    import React from 'react'; import {createRoot} from 'react-dom/client';
    window.fixture={replies:[],calls:[]};
    window.workbench={invoke:async(action,args)=>{
      window.fixture.calls.push({action,args});
      if(action==='closeDiagnostics')return {closed:true};
      const next=window.fixture.replies.shift();
      if(!next)throw Error('No scripted reply');
      if(next.rejection)throw Error(next.rejection);
      if(next.deferred)return new Promise(resolve=>window.fixture.release=()=>resolve(next.value));
      return next;
    }};
    const {TaskDiagnostics}=await import(${JSON.stringify(resolve('src/renderer/features/diagnostics/TaskDiagnostics.tsx').replaceAll('\\', '/'))});
    const root=createRoot(document.getElementById('root'));
    window.renderFixture=(job='A',observation='initial')=>root.render(<TaskDiagnostics key={job} job={job} latest={null} observation={observation}/>);
    window.diagnosticRejectionFixture={...window.fixture,render:()=>window.renderFixture()};
  `)
  await fs.writeFile(join(root, 'vite.config.mjs'), `export default {root:${JSON.stringify(root)},base:'./',build:{outDir:'dist',emptyOutDir:true}}`)
  execFileSync(process.execPath, [resolve('node_modules/vite/bin/vite.js'), 'build', '--config', join(root, 'vite.config.mjs')], { windowsHide: true })
  await fs.writeFile(join(root, 'electron.cjs'), `const {app,BrowserWindow}=require('electron');app.setPath('userData',process.env.PDFMD_UI_PROFILE);app.whenReady().then(()=>new BrowserWindow({show:false}).loadFile(${JSON.stringify(join(root, 'dist/index.html'))}));app.on('window-all-closed',()=>app.quit());`)
})
const empty = (job = 'A') => ({ status: 'ok', job, view: job + '-view', captured_at: 1000, total: 0, boundary_seq: null, first: 0, last: 0, events: [], older: null, newer: null, oldest: 'oldest', recent: 'recent', consistency: 'captured catalog' })
async function run(name: string, check: (page: Page) => Promise<void>) {
  const app = await electron.launch({ args: [join(root, 'electron.cjs')], env: { ...process.env, PDFMD_UI_PROFILE: join(root, name) } })
  try { const page = await app.firstWindow(); await page.waitForFunction(() => Boolean((window as any).renderFixture)); await check(page) } finally { await app.close() }
}

test('failed link raw observations cannot supply ownership or evidence navigation', async () => {
  await run('failed-raw', async page => {
    await page.evaluate(value => { (window as any).fixture.replies.push(value); (window as any).renderFixture() }, empty())
    await expect(page.getByLabel('Diagnostic view')).toBeVisible()
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', total: 1, items: [{ id: 'op' }] }))
    await page.getByLabel('Diagnostic view').selectOption('operation')
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', kind: 'operation', id: 'op', record: {},
      version: 'independent', links: [{ ref: 'bad', status: 'unavailable', reason: 'Descriptor metadata/kind has an unsupported shape.',
        raw_descriptor: { kind: 'candidate', meta: null, attempt: 'untrusted-owner' } },
        { ref: 'good', status: 'available; integrity checked, acceptance not inferred', facts: { kind: 'candidate', bytes: 2, meta: {}, attempt: 'checked-owner' } }] }))
    await page.getByRole('button', { name: 'Inspect op', exact: true }).click()
    const bad = page.locator('.diagnostic-link').filter({ has: page.getByRole('button', { name: 'Open raw bad', exact: true }) })
    await expect(bad).toContainText('Artifact owner attempt: unconfirmed')
    await expect(bad.getByRole('button', { name: 'Open raw bad', exact: true })).toBeDisabled()
    const good = page.locator('.diagnostic-link').filter({ has: page.getByRole('button', { name: 'Open raw good', exact: true }) })
    await expect(good).toContainText('checked-owner')
    await expect(good.getByRole('button', { name: 'Open raw good', exact: true })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'Open committed version', exact: true })).toBeEnabled()
    await bad.getByText('Raw descriptor observation (not verified facts)', { exact: true }).click()
    await expect(bad.locator('pre')).toContainText('"meta": null')
  })
})

test('late old-task activity cannot replace the selected task and its temporary view is closed', async () => {
  await run('late-task', async page => {
    await page.evaluate(value => { (window as any).fixture.replies.push({ deferred: true, value }); (window as any).renderFixture() }, empty())
    await expect(page.getByRole('status')).toHaveText('Reading selected local facts…')
    await page.evaluate(value => { (window as any).fixture.replies.push(value); (window as any).renderFixture('B') }, empty('B'))
    await expect(page.getByRole('status')).toContainText('Showing 0–0 of 0')
    await page.evaluate(() => (window as any).fixture.release())
    await expect(page.locator('code').first()).toHaveText('B')
    await expect.poll(() => page.evaluate(() => (window as any).fixture.calls.filter((x: any) => x.action === 'closeDiagnostics' && x.args.view === 'A-view').length)).toBe(1)
  })
})

test('stale/unavailable detail preserves event coverage and refresh is explicit', async () => {
  await run('stale-detail', async page => {
    await page.evaluate(value => { (window as any).fixture.replies.push(value); (window as any).renderFixture() }, empty())
    await expect(page.getByRole('status')).toContainText('Showing 0–0 of 0')
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', view: 'A-view', total: 1, offset: 0, items: [{ id: 'request', status: 'prepared', attempts: 0 }] }))
    await page.getByLabel('Diagnostic view').selectOption('request')
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'stale', reason: 'Catalog changed' }))
    await page.getByRole('button', { name: 'Inspect request', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('stale: Catalog changed')
    await expect(page.getByText(/Event boundary empty/)).toBeVisible()
    await expect(page.getByRole('region', { name: 'Diagnostic record detail' })).toHaveCount(0)
    await page.evaluate(value => (window as any).fixture.replies.push(value), empty())
    await page.getByRole('button', { name: 'Refresh diagnostics and recent activity' }).click()
    await expect(page.getByRole('alert')).toHaveCount(0)
    await expect(page.getByRole('status').filter({ hasText: /^Showing/ })).toContainText('0–0 of 0')
  })
})

test('unconfirmed association shows its reason and retains independent commit navigation', async () => {
  await run('unconfirmed', async page => {
    await page.evaluate(value => { (window as any).fixture.replies.push(value); (window as any).renderFixture() }, empty())
    await expect(page.getByLabel('Diagnostic view')).toBeVisible()
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', total: 1, items: [{ id: 'A:0', tool: 'edit_document' }] }))
    await page.getByLabel('Diagnostic view').selectOption('operation')
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', kind: 'operation', id: 'A:0', record: { status: 'done' },
      origin: 'unattributed', request: null, request_association: { status: 'unconfirmed', candidate_request: 'A', reason: 'Artifact request/attempt ownership is unconfirmed.' },
      version: 'saved', effect: 'committed document version' }))
    await page.getByRole('button', { name: 'Inspect A:0', exact: true }).click()
    await expect(page.getByText(/Request association: unconfirmed/)).toContainText('Artifact request/attempt ownership is unconfirmed.')
    await expect(page.getByRole('button', { name: 'Open linked request', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Open committed version', exact: true })).toBeEnabled()
  })
})

test('malformed row remains visible and selecting it preserves good rows and continuation', async () => {
  await run('mixed-rows', async page => {
    await page.evaluate(value => { (window as any).fixture.replies.push(value); (window as any).renderFixture() }, empty())
    await expect(page.getByLabel('Diagnostic view')).toBeVisible()
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', total: 4, offset: 0, next: 'next', items: [
      { id: 'good-new', status: 'prepared', attempts: 0 },
      { id: 'bad', diagnostic_status: 'unavailable', reason: 'Record JSON root must be an object.' },
      { id: 'good-old', status: 'prepared', attempts: 0 }] }))
    await page.getByLabel('Diagnostic view').selectOption('request')
    await expect(page.getByRole('row').filter({ hasText: 'bad' })).toContainText('Diagnostic unavailable · Record JSON root must be an object.')
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'unavailable', reason: 'Record shape/ownership is inconsistent.' }))
    await page.getByRole('button', { name: 'Inspect bad', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('Record shape/ownership is inconsistent.')
    await expect(page.getByRole('button', { name: 'Inspect good-new', exact: true })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'Inspect good-old', exact: true })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'More records', exact: true })).toBeEnabled()
    await expect(page.getByRole('status').filter({ hasText: /^Showing/ })).toContainText('Showing 1–3 of 4')
  })
})

test('typed request detail retains raw attempts, local failures and observation invalidation', async () => {
  await run('typed-request', async page => {
    await page.evaluate(value => { (window as any).fixture.replies.push(value); (window as any).renderFixture() }, empty())
    await expect(page.getByLabel('Diagnostic view')).toBeVisible()
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', total: 1, items: [{ id: 'request' }] }))
    await page.getByLabel('Diagnostic view').selectOption('request')
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', kind: 'request', id: 'request', record: { status: 'prepared' },
      links: [], limitations: [], attempts: [
        { id: 'attempt', record: { status: 'unknown', transport: { received_body_bytes: 0 }, usage: null }, usage_state: 'unknown' },
        { id: 'bad-attempt', status: 'unavailable', reason: 'Attempt ownership mismatch.' },
        { id: 'raw-attempt', record: { status: { unexpected: true }, transport: 42, usage: [1, null] }, usage_state: 'reported' }
      ], publication: { pointer: null, staging_ref: null, meaning: 'not acceptance' }, origin: 'unattributed', result: { parent: ['raw-parent'] } }))
    await page.getByRole('button', { name: 'Inspect request', exact: true }).click()
    const detail = page.getByRole('region', { name: 'Diagnostic record detail', exact: true })
    const attemptRow = detail.getByRole('row').filter({ has: page.getByRole('cell', { name: 'attempt', exact: true }) })
    await expect(attemptRow.locator('td').nth(1)).toHaveText('unknown')
    await expect(attemptRow.locator('td').nth(2)).toHaveText('0')
    await expect(attemptRow.locator('td').nth(3)).toHaveText('unknown: null')
    await expect(detail.getByRole('row').filter({ hasText: 'bad-attempt' })).toContainText('unavailable')
    await expect(detail.getByRole('row').filter({ hasText: 'raw-attempt' })).toContainText('"unexpected": true')
    await expect(detail).toContainText('raw-parent')
    await detail.getByText('Attempts, receive boundaries and reported usage', { exact: true }).click()
    await expect(detail.locator('pre').filter({ hasText: 'Attempt ownership mismatch.' })).toBeVisible()
    await page.evaluate(() => (window as any).renderFixture('A', 'changed'))
    await expect(detail.getByRole('alert')).toContainText('Task observation changed')
    await detail.screenshot({ path: join(root, 'typed-request-detail.png') })
  })
})

test('late successful detail after a view switch cannot enter the current state', async () => {
  await run('late-detail', async page => {
    await page.evaluate(value => { (window as any).fixture.replies.push(value); (window as any).renderFixture() }, empty())
    await expect(page.getByLabel('Diagnostic view')).toBeVisible()
    await page.evaluate(() => (window as any).fixture.replies.push({ status: 'ok', total: 1, items: [{ id: 'old-request' }] }))
    await page.getByLabel('Diagnostic view').selectOption('request')
    await page.evaluate(() => (window as any).fixture.replies.push({ deferred: true, value: {
      status: 'ok', kind: 'request', id: 'old-request', record: {}, links: [], limitations: [] } }))
    await page.getByRole('button', { name: 'Inspect old-request', exact: true }).click()
    await page.evaluate(value => { (window as any).fixture.replies.push(value); (window as any).renderFixture('B') }, empty('B'))
    await expect(page.locator('code').first()).toHaveText('B')
    await page.evaluate(() => (window as any).fixture.release())
    await expect(page.getByRole('region', { name: 'Diagnostic record detail', exact: true })).toHaveCount(0)
  })
})

test('production diagnostic client rejection reaches the existing alert with one exact read and no retry', async () => {
  await run('client-rejection', async page => {
    await page.evaluate(value => {
      window.diagnosticRejectionFixture.replies.push(value)
      window.diagnosticRejectionFixture.render()
    }, empty())
    await expect(page.getByLabel('Diagnostic view')).toBeVisible()
    await page.evaluate(() => window.diagnosticRejectionFixture.replies.push({ status: 'ok', total: 1, items: [{ id: 'request' }] }))
    await page.getByLabel('Diagnostic view').selectOption('request')
    await page.evaluate(() => window.diagnosticRejectionFixture.replies.push({ rejection: 'Diagnostic transport unavailable' }))
    await page.getByRole('button', { name: 'Inspect request', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('Error: Diagnostic transport unavailable')
    await expect(page.getByRole('region', { name: 'Diagnostic record detail', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Inspect request', exact: true })).toBeEnabled()
    expect(await page.evaluate(() => window.diagnosticRejectionFixture.calls)).toEqual([
      { action: 'activity', args: { job: 'A' } },
      { action: 'diagnostics', args: { job: 'A', view: 'A-view', kind: 'request' } },
      { action: 'diagnosticRecord', args: { job: 'A', view: 'A-view', kind: 'request', key: 'request' } }
    ])
  })
})
