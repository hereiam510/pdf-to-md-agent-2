import { testRunRoot } from '../support/artifacts'
import { test, expect, _electron as electron, type Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { createHash } from 'node:crypto'

const root = resolve(process.env.PDFMD_F01_F02_EVIDENCE || resolve(testRunRoot, 'f01-f02-desktop'))
const build = resolve(process.env.PDFMD_DIAGNOSTIC_BUILD || 'out')
const env = { ...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: resolve('src') }
function fixture(action: string, directory: string) {
  return JSON.parse(execFileSync(resolve('.venv/Scripts/python.exe'), ['-B', '-X', 'utf8', '-m', 'tests.desktop.fixtures.task_diagnostics', action, directory], { encoding: 'utf-8', windowsHide: true, env }))
}
function launch(directory: string) {
  return electron.launch({ args: [resolve(process.env.PDFMD_F01_F02_LAUNCH || 'tests/desktop/support/isolated-workbench.cjs')], env: {
    ...env, PDFMD_UI_PROFILE: join(directory, 'electron-profile'), PDFMD_DATA: join(directory, 'workspace'),
    PDFMD_PYTHON: resolve('.venv/Scripts/python.exe'), PDFMD_DIAGNOSTIC_BUILD: build
  } })
}
async function select(page: Page, name: string) {
  await page.locator('.document-item').filter({ hasText: name }).click()
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  await expect(page.getByAltText('Source PDF physical page 1')).toHaveAttribute('src', /^data:/)
  const panel = page.getByRole('region', { name: 'Task activity and diagnostics', exact: true })
  if (!(await panel.count())) await page.getByRole('button', { name: /^View activity and diagnostics/ }).click()
  // Source-page rendering is an intentional app write. If it overlaps the
  // initial catalog copy, the read must refuse and allow explicit refresh.
  await expect.poll(async () => (await panel.getByLabel('Diagnostic view').count()) + (await panel.getByRole('alert').count())).toBeGreaterThan(0)
  if (await panel.getByRole('alert').count()) await panel.getByRole('button', { name: 'Refresh diagnostics and recent activity' }).click()
  await expect(panel.getByLabel('Diagnostic view')).toBeVisible()
  return panel
}
async function record(panel: ReturnType<Page['getByRole']>, kind: string, key: string) {
  await panel.getByLabel('Diagnostic view').selectOption(kind)
  await panel.getByRole('button', { name: `Inspect ${key}`, exact: true }).click()
  await expect.poll(async () => (await panel.getByRole('region', { name: 'Diagnostic record detail', exact: true }).count()) + (await panel.getByRole('alert').count())).toBeGreaterThan(0)
  if (await panel.getByRole('alert').count()) {
    await expect(panel.getByRole('alert')).toContainText('stale')
    await panel.getByRole('button', { name: 'Refresh diagnostics and recent activity' }).click()
    await panel.getByLabel('Diagnostic view').selectOption(kind)
    await panel.getByRole('button', { name: `Inspect ${key}`, exact: true }).click()
  }
  await expect(panel.getByRole('region', { name: 'Diagnostic record detail', exact: true })).toBeVisible()
}

test('complete task activity, three diagnostic questions, preservation and reopened Electron/API flow', async () => {
  test.setTimeout(240000)
  await fs.mkdir(root, { recursive: true })
  const directory = await fs.mkdtemp(join(root, 'flow-'))
  const fixtureDir = join(directory, 'input')
  const value = fixture('prepare', fixtureDir)
  await fs.writeFile(join(directory, 'fixture-observations.json'), JSON.stringify(value, null, 2))
  let app: Awaited<ReturnType<typeof launch>> | undefined
  try {
    app = await launch(fixtureDir)
    await app.evaluate(() => {
      const original = globalThis.fetch
      ;(globalThis as any).diagnosticHttp = []
      globalThis.fetch = async (url, init) => {
        const u = new URL(String(url))
        ;(globalThis as any).diagnosticHttp.push({ path: u.pathname, query: u.search, method: init?.method || 'GET' })
        return original(url, init)
      }
    })
    let page = await app.firstWindow()
    await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
    let panel = await select(page, 'Diagnostics synthetic')
    // Page setup/rendering intentionally precedes the inspection-only hash interval.
    const before = fixture('hash', fixtureDir)
    await fs.writeFile(join(directory, 'initial-dom.html'), await page.content())
    await panel.screenshot({ path: join(directory, 'initial-ui.png') })
    await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText('of 1103 events')
    let seen: number[] = []
    for (;;) {
      const current = await panel.locator('[data-event-seq]').evaluateAll(rows => rows.map(row => Number(row.getAttribute('data-event-seq'))))
      seen = [...current, ...seen]
      if (await panel.getByRole('button', { name: 'Older events', exact: true }).isDisabled()) break
      await panel.getByRole('button', { name: 'Older events', exact: true }).click()
      await expect(panel.getByRole('button', { name: 'Recent events', exact: true })).toBeEnabled()
    }
    expect(seen).toEqual(value.events)
    expect(new Set(seen).size).toBe(1103)
    const apiPages = await page.evaluate(async job => {
      let current = await window.workbench.invoke('activity', { job })
      const view = current.view, pages = [current]
      while (current.older) { current = await window.workbench.invoke('activity', { job, cursor: current.older }); pages.unshift(current) }
      await window.workbench.invoke('closeDiagnostics', { job, view })
      return pages
    }, value.job)
    expect(apiPages.flatMap((p: any) => p.events.map((event: any) => event.seq))).toEqual(value.events)
    await fs.writeFile(join(directory, 'api-full-traversal.json'), JSON.stringify(apiPages, null, 2))
    await fs.writeFile(join(directory, 'ui-full-traversal.json'), JSON.stringify({ actual: seen, expected: value.events, exact: true }))
    await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText('Showing 1–3')
    await panel.getByRole('button', { name: 'Recent events', exact: true }).click()
    await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText('Showing 1004–1103')
    await record(panel, 'request', value.prepared)
    await expect(panel).toContainText('prepared; no dispatch attempt recorded')
    await expect(panel).toContainText('65000')
    await panel.getByRole('button', { name: `Open full ${value.earlier_proposal_ref}`, exact: true }).click()
    await expect(panel.getByRole('region', { name: 'Diagnostic evidence', exact: true })).toContainText('Explicit earlier-revision fixture')
    await panel.screenshot({ path: join(directory, 'prepared-capacity.png') })
    await record(panel, 'request', value.request)
    await expect(panel).toContainText('inconsistent recorded reports')
    await panel.getByRole('button', { name: `Open full ${value.context_ref}`, exact: true }).click()
    await expect(panel).toContainText('history_pressure')
    await panel.screenshot({ path: join(directory, 'request-context-boundaries.png') })
    await panel.getByRole('button', { name: `Open operation ${value.request}:0 (matched saved call and operation arguments)`, exact: true }).click()
    await expect(panel).toContainText('committed document version (atomic operation/version receipt and files checked)')
    await expect(panel).toContainText('individual fresh executions and receipt-reuse returns are not durably logged')
    await panel.getByRole('button', { name: 'Open committed version', exact: true }).click()
    await expect(panel).toContainText(value.head)
    await panel.screenshot({ path: join(directory, 'atomic-version-lineage.png') })
    await record(panel, 'operation', value.request + ':1')
    await expect(panel).toContainText('not_started (recorded skip)')
    await record(panel, 'operation', value.request + ':2')
    await expect(panel).toContainText('pending/unknown effects')
    const callsBefore = await app.evaluate(() => (globalThis as any).diagnosticHttp.length)
    await page.waitForTimeout(3300)
    const polls = await app.evaluate((_, start) => (globalThis as any).diagnosticHttp.slice(start), callsBefore)
    await fs.writeFile(join(directory, 'poll-requests.json'), JSON.stringify(polls, null, 2))
    expect(polls.some((r: any) => r.path === `/jobs/${value.job}`)).toBe(true)
    expect(polls.some((r: any) => /activity|diagnostics|evidence/.test(r.path))).toBe(false)
    expect(fixture('hash', fixtureDir)).toEqual(before)
    await fs.writeFile(join(directory, 'inspection-no-write.json'), JSON.stringify({ before, after: fixture('hash', fixtureDir), unchanged: true }, null, 2))
    // Intentional fixture writer is outside the no-write interval.
    await record(panel, 'request', value.prepared)
    fixture('stale', fixtureDir)
    await expect(panel.getByRole('alert')).toContainText('Task observation changed', { timeout: 10000 })
    await panel.getByRole('button', { name: 'Refresh diagnostics and recent activity' }).click()
    fixture('arrive', fixtureDir)
    await expect(panel.getByRole('status').filter({ hasText: 'New activity' })).toBeVisible({ timeout: 10000 })
    await panel.getByRole('button', { name: 'Oldest events', exact: true }).click()
    await expect(panel.getByRole('status').filter({ hasText: 'Showing' })).toContainText('of 1103 events')
    await panel.getByRole('button', { name: 'Refresh diagnostics and recent activity' }).click()
    await expect(panel.getByRole('status').filter({ hasText: 'Showing' })).toContainText('of 1104 events')
    await expect(panel.locator('[data-event-seq]').last()).toContainText('new after boundary')
    panel = await select(page, 'Empty synthetic')
    await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText('Showing 0–0 of 0')
    panel = await select(page, 'Exact boundary synthetic')
    await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText('Showing 1–100 of 100')
    await expect(panel.getByRole('button', { name: 'Older events', exact: true })).toBeDisabled()
    await expect(panel.getByRole('button', { name: 'Newer events', exact: true })).toBeDisabled()
    panel = await select(page, 'Attribution synthetic')
    const attribution = value.tasks['Attribution synthetic']
    const attributionBefore = fixture('hash', fixtureDir)
    await record(panel, 'request', attribution.request)
    const link = panel.locator('.diagnostic-link').filter({ has: page.getByRole('button', { name: `Open raw ${attribution.stream_ref}`, exact: true }) })
    await expect(link).toContainText(attribution.a)
    await expect(link).toContainText('earlier_attempt')
    await expect(link).not.toContainText(attribution.b)
    await link.getByRole('button', { name: `Open raw ${attribution.stream_ref}`, exact: true }).click()
    const opened = JSON.parse(await panel.getByRole('region', { name: 'Diagnostic evidence', exact: true }).locator('pre').innerText())
    expect(Buffer.from(opened.data, 'base64').toString('hex')).toBe(attribution.raw_hex)
    expect(opened.complete).toBe(true)
    await panel.screenshot({ path: join(directory, 'attribution-exact-raw.png') })
    expect(fixture('hash', fixtureDir)).toEqual(attributionBefore)
    for (const name of ['Published resolution synthetic', 'Staging resolution synthetic', 'Handoff rejection synthetic', 'Rejected raw synthetic']) {
      panel = await select(page, name)
      const subject = value.tasks[name]
      await record(panel, 'request', subject.request)
      if (name.includes('resolution')) {
        await expect(panel).toContainText(subject.published ? `pointer accepted:${subject.request}` : 'no published pointer')
        await panel.getByRole('button', { name: `Open conflict_resolution ${subject.request}`, exact: true }).click()
        await expect(panel).toContainText('receipt alone does not prove graph readiness')
      } else if (name.startsWith('Handoff')) {
        await expect(panel).toContainText('invalid_handoff')
        await expect(panel).toContainText('accepted')
      } else {
        await panel.getByText('Reported and derived usage (separate from settlement)', { exact: true }).click()
        await expect(panel).toContainText('not a settlement')
        await expect(panel).toContainText('unknown')
      }
      await panel.screenshot({ path: join(directory, name.split(' ')[0].toLowerCase() + '.png') })
    }
    await app.close(); app = undefined
    app = await launch(fixtureDir); page = await app.firstWindow()
    await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
    panel = await select(page, 'Diagnostics synthetic')
    const reopenBefore = fixture('hash', fixtureDir)
    await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText('of 1104 events')
    await panel.getByRole('button', { name: 'Oldest events', exact: true }).click()
    await expect(panel.locator('[data-event-seq]').first()).toHaveAttribute('data-event-seq', String(value.events[0]))
    await record(panel, 'operation', value.request + ':0')
    await expect(panel).toContainText('committed document version')
    const api = await page.evaluate(async ({ job, request, version }) => {
      const activity = await window.workbench.invoke('activity', { job })
      const detail = await window.workbench.invoke('diagnosticRecord', { job, view: activity.view, kind: 'request', key: request })
      const versionDetail = await window.workbench.invoke('diagnosticRecord', { job, view: activity.view, kind: 'version', key: version })
      await window.workbench.invoke('closeDiagnostics', { job, view: activity.view })
      return { activity, detail, versionDetail }
    }, { job: value.job, request: value.request, version: value.head })
    await fs.writeFile(join(directory, 'reopened-api.json'), JSON.stringify(api, null, 2))
    expect(fixture('hash', fixtureDir)).toEqual(reopenBefore)
    await fs.writeFile(join(directory, 'reopened-no-write.json'), JSON.stringify({ before: reopenBefore, after: fixture('hash', fixtureDir), unchanged: true }, null, 2))
    const audit = fixture('verify', fixtureDir)
    await fs.writeFile(join(directory, 'source-image-version-export-audit.json'), JSON.stringify(audit, null, 2))
    await panel.screenshot({ path: join(directory, 'reopened-lineage.png') })
  } finally { await app?.close() }
})

test('corrupt evidence keeps independent facts and exact native-pixel evidence usable', async () => {
  await fs.mkdir(root, { recursive: true })
  const directory = await fs.mkdtemp(join(root, 'corrupt-'))
  const input = join(directory, 'input')
  const value = fixture('prepare', input)
  await fs.writeFile(join(directory, 'intentional-damage.json'), JSON.stringify(fixture('damage', input), null, 2))
  const app = await launch(input)
  try {
    const page = await app.firstWindow()
    await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
    const panel = await select(page, 'Diagnostics synthetic')
    const before = fixture('hash', input)
    await record(panel, 'request', value.request)
    const native = panel.locator('.diagnostic-link').filter({ has: page.getByRole('button', { name: `Open full ${value.native_ref}`, exact: true }) })
    await expect(native).toContainText('unavailable')
    await expect(native.getByRole('button', { name: `Open full ${value.native_ref}`, exact: true })).toBeDisabled()
    await expect(panel).toContainText('inconsistent recorded reports')
    await expect(panel).toContainText('recorded attempt(s)')
    await panel.screenshot({ path: join(directory, 'corrupt-scoped-facts.png') })
    await record(panel, 'blob', value.image.ref)
    await panel.getByRole('button', { name: `Open full ${value.image.ref}`, exact: true }).click()
    const image = panel.getByAltText('Exact saved diagnostic image')
    await image.evaluate((el: HTMLImageElement) => el.decode())
    expect(await image.evaluate((el: HTMLImageElement) => [el.naturalWidth, el.naturalHeight])).toEqual([value.image.width, value.image.height])
    const opened = JSON.parse(await panel.getByRole('region', { name: 'Diagnostic evidence', exact: true }).locator('pre').innerText())
    expect(opened.complete).toBe(true)
    expect(opened.access.representation).toBe('native_image_reference')
    const after = fixture('hash', input)
    expect(after).toEqual(before)
    await fs.writeFile(join(directory, 'no-write.json'), JSON.stringify({ before, after, unchanged: true }, null, 2))
    await fs.writeFile(join(directory, 'source-export-audit.json'), JSON.stringify(fixture('verify', input), null, 2))
    await panel.screenshot({ path: join(directory, 'native-pixel-evidence.png') })
  } finally { await app.close() }
})

test('F02 correction: consistent provenance, mixed rows and independent commits survive API/UI process reopen', async () => {
  test.setTimeout(240000)
  await fs.mkdir(root, { recursive: true })
  const directory = await fs.mkdtemp(join(root, 'consistency-'))
  const input = join(directory, 'input')
  fixture('prepare', input)
  const value = fixture('consistency', input)
  await fs.writeFile(join(directory, 'fixture-setup.json'), JSON.stringify(value, null, 2))
  for (const phase of ['fresh', 'reopened']) {
    const app = await launch(input)
    try {
      const page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      const panel = await select(page, 'Diagnostics synthetic')
      // Backend/app setup and source render finish before the measured reads.
      const before = fixture('hash', input)
      const factsBefore = fixture('facts', input)
      await fs.writeFile(join(directory, `${phase}-inspection-before.json`), JSON.stringify({ before, factsBefore }, null, 2))
      const api = await page.evaluate(async value => {
        const activity = await window.workbench.invoke('activity', { job: value.job })
        const args = { job: value.job, view: activity.view }
        let current = await window.workbench.invoke('diagnostics', { ...args, kind: 'request' })
        const pages = [current]
        while (current.next) {
          current = await window.workbench.invoke('diagnostics', { ...args, kind: 'request', cursor: current.next })
          pages.push(current)
        }
        const request = await window.workbench.invoke('diagnosticRecord', { ...args, kind: 'request', key: value.request })
        const operation = await window.workbench.invoke('diagnosticRecord', { ...args, kind: 'operation', key: value.request + ':0' })
        const version = await window.workbench.invoke('diagnosticRecord', { ...args, kind: 'version', key: value.head })
        const normal = await window.workbench.invoke('diagnosticRecord', { ...args, kind: 'operation', key: value.equal_b + ':0' })
        const bad = await window.workbench.invoke('diagnosticRecord', { ...args, kind: 'request', key: 'bad-array' })
        const context = await window.workbench.invoke('diagnostics', { ...args, kind: 'context_commit' })
        const raw = await window.workbench.invoke('diagnosticEvidence', { ...args, ref: 'accepted:' + value.equal_b, mode: 'raw' })
        const foreign = await window.workbench.invoke('diagnostics', { ...args, job: value.tasks['Empty synthetic'].job, kind: 'request' })
        await window.workbench.invoke('closeDiagnostics', args)
        return { activity, pages, request, operation, version, normal, bad, context, raw, foreign }
      }, value)
      await fs.writeFile(join(directory, `${phase}-api.json`), JSON.stringify(api, null, 2))
      expect(api.pages.flatMap(p => p.items.map((item: any) => item.id))).toEqual(value.request_order)
      expect(api.pages.map(p => p.offset)).toEqual([0, 50])
      expect(api.pages.every(p => p.status === 'ok' && p.total === value.request_order.length)).toBe(true)
      expect(api.pages.flatMap(p => p.items).filter((i: any) => i.id.startsWith('bad-')).every((i: any) => i.diagnostic_status === 'unavailable' && i.reason && i.attempts === undefined)).toBe(true)
      const link = api.request.links.find((x: any) => x.ref === 'accepted:' + value.equal_b)
      expect(link.reason).toBe('Artifact request/attempt ownership is unconfirmed.')
      expect(api.operation.request).toBeNull()
      expect(api.operation.request_association.reason).toBe(link.reason)
      expect(api.request.operations).toEqual([])
      expect(api.request.unconfirmed_operations.find((x: any) => x.id === value.request + ':0').reason).toBe(link.reason)
      expect(api.operation.version).toBe(value.head)
      expect(api.version.verification).toContain('version files checked')
      expect(api.normal.request).toBe(value.equal_b)
      expect(api.normal.request_association.publication).toBe('published')
      expect(api.bad.status).toBe('unavailable')
      expect(api.context.items.find((i: any) => i.id === 'bad-context-json').reason).toBe('Malformed record JSON.')
      expect(api.context.items.some((i: any) => i.id === value.context_ref)).toBe(true)
      expect(api.raw.complete).toBe(true)
      expect(createHash('sha256').update(Buffer.from(api.raw.data, 'base64')).digest('hex')).toBe(value.equal_b_raw_sha256)
      expect(api.foreign.status).toBe('unavailable')

      await record(panel, 'request', value.request)
      await expect(panel).toContainText('Unconfirmed operation association:')
      await expect(panel).toContainText(link.reason)
      await expect(panel.getByRole('button', { name: new RegExp(`^Open operation ${value.request}:`) })).toHaveCount(0)
      const badLink = panel.locator('.diagnostic-link').filter({ has: page.getByRole('button', { name: `Open full accepted:${value.equal_b}`, exact: true }) })
      await expect(badLink).toContainText(link.reason)
      await expect(badLink.getByRole('button').first()).toBeDisabled()
      await record(panel, 'operation', value.request + ':0')
      await expect(panel).toContainText(`Request association: unconfirmed · ${link.reason}`)
      await expect(panel.getByRole('button', { name: 'Open linked request', exact: true })).toHaveCount(0)
      await expect(panel).toContainText('committed document version (atomic operation/version receipt and files checked)')
      await page.getByRole('region', { name: 'Diagnostic record detail', exact: true }).scrollIntoViewIfNeeded()
      await page.screenshot({ path: join(directory, `${phase}-unconfirmed-commit.png`) })
      await panel.getByRole('button', { name: 'Open committed version', exact: true }).click()
      await expect(panel).toContainText('version files checked; source fidelity not assessed')

      await panel.getByLabel('Diagnostic view').selectOption('request')
      await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText(`Showing 1–50 of ${value.request_order.length}`)
      const badRow = panel.getByRole('row').filter({ has: page.getByRole('button', { name: 'Inspect bad-array', exact: true }) })
      await expect(badRow).toContainText('Diagnostic unavailable · Record JSON root must be an object.')
      await panel.getByRole('button', { name: 'Inspect bad-array', exact: true }).click()
      await expect(panel.getByRole('alert')).toContainText('Record shape/ownership is inconsistent.')
      await expect(panel.getByRole('button', { name: `Inspect ${value.equal_b}`, exact: true })).toBeVisible()
      await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText(`of ${value.request_order.length}`)
      await badRow.scrollIntoViewIfNeeded()
      await page.screenshot({ path: join(directory, `${phase}-mixed-row.png`) })
      await panel.getByRole('button', { name: 'More records', exact: true }).click()
      await expect(panel.getByRole('button', { name: 'Inspect bad-null', exact: true })).toBeVisible()
      await expect(panel.getByRole('status').filter({ hasText: /^Showing/ })).toContainText(`Showing 51–${value.request_order.length}`)
      await panel.getByRole('button', { name: 'First records', exact: true }).click()
      await panel.getByRole('button', { name: `Inspect ${value.equal_b}`, exact: true }).click()
      await panel.getByRole('button', { name: `Open operation ${value.equal_b}:0 (matched saved call and operation arguments)`, exact: true }).click()
      await expect(panel).toContainText('Origin: request-linked')
      await expect(panel).toContainText('Request association: confirmed · published')
      await panel.getByRole('button', { name: 'Open linked request', exact: true }).click()
      await panel.getByRole('button', { name: `Open raw accepted:${value.equal_b}`, exact: true }).click()
      await expect(panel.getByRole('region', { name: 'Diagnostic evidence', exact: true })).toContainText('"complete": true')
      await panel.getByLabel('Diagnostic view').selectOption('context_commit')
      await expect(panel.getByRole('row').filter({ has: page.getByRole('button', { name: 'Inspect bad-context-json', exact: true }) })).toContainText('Malformed record JSON.')
      await panel.getByRole('button', { name: `Inspect ${value.context_ref}`, exact: true }).click()
      await panel.getByRole('button', { name: `Open full ${value.context_ref}`, exact: true }).click()
      await expect(panel.getByRole('region', { name: 'Diagnostic evidence', exact: true })).toContainText('history_pressure')
      const after = fixture('hash', input)
      expect(after).toEqual(before)
      expect(fixture('facts', input)).toEqual(factsBefore)
      await fs.writeFile(join(directory, `${phase}-no-write.json`), JSON.stringify({ before, after, unchanged: true, factsBefore, factsAfter: fixture('facts', input) }, null, 2))

      // Switching task triggers source render: start a separate quiescent interval.
      const staging = value.tasks['Staging resolution synthetic']
      const stagedPanel = await select(page, 'Staging resolution synthetic')
      const stageBefore = fixture('hash', input)
      await record(stagedPanel, 'request', staging.request)
      await expect(stagedPanel).toContainText('no published pointer')
      await expect(stagedPanel).toContainText('unpublished · recorded call relationship')
      await stagedPanel.getByRole('button', { name: `Open operation ${staging.request}:0 (matched saved call and operation arguments)`, exact: true }).click()
      await expect(stagedPanel).toContainText('Request association: confirmed · unpublished')
      await expect(stagedPanel).toContainText('not_started (recorded skip)')
      await expect(stagedPanel).toContainText('graph readiness not inferred')
      await page.getByRole('region', { name: 'Diagnostic record detail', exact: true }).scrollIntoViewIfNeeded()
      await page.screenshot({ path: join(directory, `${phase}-staging-unpublished.png`) })
      expect(fixture('hash', input)).toEqual(stageBefore)
      await fs.writeFile(join(directory, `${phase}-staging-no-write.json`), JSON.stringify({ before: stageBefore, after: fixture('hash', input), unchanged: true }, null, 2))
      await fs.writeFile(join(directory, `${phase}-source-export-audit.json`), JSON.stringify(fixture('verify', input), null, 2))
    } finally { await app.close() }
  }
})
