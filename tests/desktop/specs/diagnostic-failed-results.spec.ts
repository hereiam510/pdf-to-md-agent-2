import { testRunRoot } from '../support/artifacts'
import { test, expect, _electron as electron, type Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'

const root = resolve(process.env.PDFMD_D03_EVIDENCE || resolve(testRunRoot, 'diagnostic-failed-results'))
const build = resolve(process.env.PDFMD_DIAGNOSTIC_BUILD || 'out')
const env = { ...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: resolve('src') }
const reason = 'Descriptor metadata/kind has an unsupported shape.'
function fixture(action: string, directory: string) {
  return JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'), ['-B', '-X', 'utf8', '-m', 'tests.desktop.fixtures.diagnostic_failed_results', action, directory], { encoding: 'utf-8', windowsHide: true, env }))
}
function launch(directory: string) {
  return electron.launch({ args: [resolve(process.env.PDFMD_F01_F02_LAUNCH || 'tests/desktop/support/isolated-workbench.cjs')], env: {
    ...env, PDFMD_UI_PROFILE: join(directory, 'profile'), PDFMD_DATA: join(directory, 'workspace'),
    PDFMD_PYTHON: resolve('.venv/Scripts/python.exe'), PDFMD_DIAGNOSTIC_BUILD: build
  } })
}
async function open(page: Page) {
  await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
  await page.locator('.document-item').filter({ hasText: 'D03 synthetic' }).click()
  await expect(page.getByAltText('Source PDF physical page 1')).toHaveAttribute('src', /^data:/)
  await page.getByRole('button', { name: /^View activity and diagnostics/ }).click()
  const panel = page.getByRole('region', { name: 'Task activity and diagnostics', exact: true })
  await expect.poll(async () => await panel.getByLabel('Diagnostic view').count() + await panel.getByRole('alert').count()).toBeGreaterThan(0)
  if (await panel.getByRole('alert').count()) await panel.getByRole('button', { name: 'Refresh diagnostics and recent activity' }).click()
  await expect(panel.getByLabel('Diagnostic view')).toBeVisible()
  return panel
}

test('failed descriptors remain local in actual Electron HTTP and process reopen without task writes', async () => {
  test.setTimeout(240000)
  await fs.mkdir(root, { recursive: true })
  const directory = await fs.mkdtemp(join(root, 'flow-'))
  const input = join(directory, 'input')
  const value = fixture('prepare', input)
  await fs.writeFile(join(directory, 'fixture.json'), JSON.stringify(value, null, 2))
  for (const phase of ['fresh', 'reopened']) {
    const app = await launch(input)
    try {
      await app.evaluate(() => {
        const original = globalThis.fetch
        ;(globalThis as any).d03Http = []
        ;(globalThis as any).d03Pending = 0
        globalThis.fetch = async (url, init) => {
          ;(globalThis as any).d03Http.push({ path: new URL(String(url)).pathname, method: init?.method || 'GET' })
          ;(globalThis as any).d03Pending++
          try { return await original(url, init) }
          finally { (globalThis as any).d03Pending-- }
        }
      })
      const page = await app.firstWindow()
      if (process.env.PDFMD_DIAGNOSTIC_QUIESCENT === '1') {
        // main.ts starts the backend after its initial loadFile resolves.
        // Reloading an unfinished initial load can prevent that startup.
        await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
        // Run-local measurement control: the ordinary 1.5s job poll can open
        // source SQLite sidecars during a file map. Record the timer after
        // reload, then stop it only after startup/source reads have completed.
        // All diagnostic HTTP/IPC and exact sidecar comparisons remain real.
        await page.addInitScript(() => {
          const polls: number[] = []
          window.setInterval = new Proxy(window.setInterval, {
            apply(target, receiver, args) {
              const handle = Reflect.apply(target, receiver, args)
              if (args[1] === 1500) polls.push(handle)
              return handle
            }
          })
          Object.defineProperty(window, 'stopD03Poll', { value: () => polls.forEach(handle => window.clearInterval(handle)) })
        })
        await page.reload()
      }
      const panel = await open(page)
      // Source rendering/app initialization are outside the inspection interval.
      if (process.env.PDFMD_DIAGNOSTIC_QUIESCENT === '1') await page.evaluate(() => (window as any).stopD03Poll())
      await expect.poll(() => app.evaluate(() => (globalThis as any).d03Pending)).toBe(0)
      const before = fixture('hash', input), beforeFacts = fixture('facts', input)
      const api = await page.evaluate(async value => {
        const first = await window.workbench.invoke('activity', { job: value.job })
        const records = []
        for (const [kind, cases, field] of [['operation', value.cases, 'operation'], ['request', value.inputs, 'request']] as const) {
          for (const item of cases) records.push(await window.workbench.invoke('diagnosticRecord', { job: value.job, view: first.view, kind, key: item[field] }))
        }
        const ref = value.cases.at(-1).ref
        const exact = await window.workbench.invoke('diagnosticEvidence', { job: value.job, view: first.view, ref, mode: 'raw', start: 1, end: 6 })
        await window.workbench.invoke('closeDiagnostics', { job: value.job, view: first.view })
        return { first, records, exact }
      }, value)
      await fs.writeFile(join(directory, `${phase}-api.json`), JSON.stringify(api, null, 2))
      expect(api.records.every((item: any) => item.status === 'ok')).toBe(true)
      expect(api.exact.range).toEqual([1, 6])
      expect(api.exact.complete).toBe(false)
      for (const item of api.records) for (const link of item.links) if (link.status === 'unavailable') {
        expect(link.reason).toBe(reason); expect(link.facts).toBeUndefined()
      }
      for (const item of value.cases) {
        await panel.getByLabel('Diagnostic view').selectOption('operation')
        await panel.getByRole('button', { name: `Inspect ${item.operation}`, exact: true }).click()
        const detail = panel.getByRole('region', { name: 'Diagnostic record detail', exact: true })
        await expect(detail).toBeVisible()
        if (item.field) {
          const link = detail.locator('.diagnostic-link').filter({ has: page.getByRole('button', { name: `Open raw ${item.ref}`, exact: true }) })
          await expect(link).toContainText(reason)
          await expect(link.getByRole('button', { name: `Open raw ${item.ref}`, exact: true })).toBeDisabled()
          await link.getByText('Raw descriptor observation (not verified facts)', { exact: true }).click()
          await expect(link.locator('pre')).toContainText('"meta": ' + JSON.stringify(item.raw_meta))
        }
        await expect(detail).toContainText('Request association: confirmed')
        await expect(detail.getByRole('button', { name: 'Open linked request', exact: true })).toBeEnabled()
        if (item.label === 'invalid-commit' || item.label === 'invalid-files') {
          await expect(detail).toContainText('unknown: document lineage unavailable')
          await expect(detail.getByRole('button', { name: 'Open committed version', exact: true })).toHaveCount(0)
        } else {
          await expect(detail).toContainText('committed document version (atomic operation/version receipt and files checked)')
          await panel.screenshot({ path: join(directory, `${phase}-${item.label}-operation.png`) })
          await detail.getByRole('button', { name: 'Open committed version', exact: true }).click()
          await expect(detail).toContainText('version files checked; source fidelity not assessed')
        }
        await panel.screenshot({ path: join(directory, `${phase}-${item.label}.png`) })
      }
      for (const item of value.inputs) {
        await panel.getByLabel('Diagnostic view').selectOption('request')
        await panel.getByRole('button', { name: `Inspect ${item.request}`, exact: true }).click()
        const detail = panel.getByRole('region', { name: 'Diagnostic record detail', exact: true })
        await expect(detail).toContainText(item.attempt)
        await expect(detail).toContainText('no published pointer')
        await expect(detail).toContainText('"fits": true')
        await expect(detail).toContainText(reason)
        await expect(detail.getByRole('button', { name: `Open full ${item.ref}`, exact: true })).toBeDisabled()
        const inputLink = detail.locator('.diagnostic-link').filter({ has: page.getByRole('button', { name: `Open full ${item.ref}`, exact: true }) })
        await inputLink.scrollIntoViewIfNeeded()
        await expect(inputLink.getByText(new RegExp('unavailable.*' + reason.replaceAll('.', '\\.')))).toBeVisible()
        await inputLink.screenshot({ path: join(directory, `${phase}-${item.request.split(':').at(-1)}-link.png`) })
        await detail.locator('table').screenshot({ path: join(directory, `${phase}-${item.request.split(':').at(-1)}-attempt.png`) })
      }
      await panel.screenshot({ path: join(directory, `${phase}-input.png`) })
      const audit = fixture('verify', input)
      await fs.writeFile(join(directory, `${phase}-source-export.json`), JSON.stringify(audit, null, 2))
      const after = fixture('hash', input), afterFacts = fixture('facts', input)
      await fs.writeFile(join(directory, `${phase}-inspection-map.json`), JSON.stringify({ before, after, beforeFacts, afterFacts,
        recurringJobPollSuppressed: process.env.PDFMD_DIAGNOSTIC_QUIESCENT === '1' }, null, 2))
      expect(after).toEqual(before); expect(afterFacts).toEqual(beforeFacts)
      await fs.writeFile(join(directory, `${phase}-no-write.json`), JSON.stringify({ before, after, beforeFacts, afterFacts, unchanged: true }, null, 2))
      await fs.writeFile(join(directory, `${phase}-dom.html`), await page.content())
      const requests = await app.evaluate(() => (globalThis as any).d03Http)
      expect(requests.every((item: any) => ['GET', 'DELETE'].includes(item.method))).toBe(true)
      await fs.writeFile(join(directory, `${phase}-http.json`), JSON.stringify(requests, null, 2))
    } finally { await app.close() }
  }
  const final = fixture('hash', input)
  const last = JSON.parse(await fs.readFile(join(directory, 'reopened-no-write.json'), 'utf8'))
  expect(final).toEqual(last.after)
  await fs.writeFile(join(directory, 'final-retained-map.json'), JSON.stringify({ actual: final, matchesLastInterval: true }, null, 2))
})
