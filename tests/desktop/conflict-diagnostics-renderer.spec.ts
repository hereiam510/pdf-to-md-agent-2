import { test, expect, _electron as electron, type Page } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

// Isolate the actual component from API timing so failed refreshes and
// timeout-after-commit can be exercised without a provider or live task.
let root: string
test.beforeAll(async () => {
  const parent = resolve(process.env.PDFMD_DIAGNOSTICS_RENDERER_EVIDENCE || '.local/conflict-diagnostics-renderer')
  await fs.mkdir(parent, { recursive: true })
  root = await fs.mkdtemp(join(parent, 'run-'))
  await fs.writeFile(join(root, 'index.html'), '<div id="root"></div><script type="module" src="/entry.tsx"></script>')
  const component = resolve('src/renderer/ConflictRecovery.tsx').replaceAll('\\', '/')
  await fs.writeFile(join(root, 'entry.tsx'), `
    import React from 'react'; import { createRoot } from 'react-dom/client';
    import { ConflictRecovery } from ${JSON.stringify(component)};
    window.fixture = { responses: [], calls: [], evidence: [], resolveError: null, refreshError: null };
    window.workbench = { invoke: async (action, args) => {
      const f = window.fixture; f.calls.push({action, args});
      if (action === 'resolveConflict') {
        if (f.resolveError) throw Error(f.resolveError);
        return {request: 'job:0:0', resolution_ref: 'conflict-resolution:job:0:0', projection: 'ready'};
      }
      const next = f.responses.shift();
      if (!next || next.error) throw Error(next?.error || 'No scripted diagnosis');
      if (next.deferred) return new Promise(resolve => { f.release = () => resolve(next.value) });
      return next;
    }};
    const root = createRoot(document.getElementById('root'));
    window.renderFixture = ({job = 'job', running = false, observation = 'initial'} = {}) => root.render(<ConflictRecovery job={job} running={running} observation={observation}
      refresh={async () => { if (window.fixture.refreshError) throw Error(window.fixture.refreshError) }}
      viewEvidence={(ref, raw) => window.fixture.evidence.push({ref, raw: Boolean(raw)})} />);
    window.renderFixture();
  `)
  await fs.writeFile(join(root, 'vite.config.mjs'), `export default {root: ${JSON.stringify(root)}, base: './', build: {outDir: 'dist', emptyOutDir: true}}`)
  execFileSync(process.execPath, [resolve('node_modules/vite/bin/vite.js'), 'build', '--config', join(root, 'vite.config.mjs')],
    { windowsHide: true, encoding: 'utf-8' })
  await fs.writeFile(join(root, 'electron.cjs'), `const {app, BrowserWindow} = require('electron');
    app.setPath('userData', process.env.PDFMD_UI_PROFILE);
    app.whenReady().then(() => { const w = new BrowserWindow({show:false}); w.loadFile(${JSON.stringify(join(root, 'dist/index.html'))}); });
    app.on('window-all-closed', () => app.quit());`)
})

const eligible = { status: 'eligible', eligible: true, reasons: [], job: 'job', request: 'job:0:0', attempt: 'attempt', basis: 'basis',
  accepted_staging_ref: 'accepted:job:0:0', native_ref: 'native:attempt', stream_ref: 'stream:attempt',
  original_usage: { prompt_tokens: 10 }, saved_usage: { prompt_tokens: 12 },
  evidence_provenance: { native_ref: { ref: 'native:attempt', status: 'verified', request: 'job:0:0', attempt: 'attempt', relation: 'selected_attempt', completeness: 'complete' },
    stream_ref: { ref: 'stream:attempt', status: 'verified', request: 'job:0:0', attempt: 'attempt', relation: 'selected_attempt', completeness: 'complete' } },
  verification: { original: 'checked_now', saved: 'checked_now', raw: 'checked_now', operations: 'checked_now' } }
const ready = { ...eligible, status: 'resolved', eligible: false, projection: 'ready', resolution_ref: 'conflict-resolution:job:0:0',
  original_usage: 0, saved_usage: { prompt_tokens: 25 },
  verification: { original: 'checked_now', saved: 'checked_now', raw: 'verified_at_resolution', operations: 'verified_at_resolution' } }

async function withRenderer(name: string, run: (page: Page) => Promise<void>) {
  const app = await electron.launch({ args: [join(root, 'electron.cjs')], env: { ...process.env, PDFMD_UI_PROFILE: join(root, name) } })
  try {
    const page = await app.firstWindow()
    await expect(page.getByRole('button', { name: 'Inspect saved acceptance' })).toBeVisible()
    await run(page)
  } finally { await app.close() }
}

test('resolution replaces the entire diagnosis with authoritative facts', async () => {
  await withRenderer('authoritative', async page => {
    await page.evaluate(values => { (window as any).fixture.responses = values }, [eligible, ready])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.getByRole('button', { name: 'Preserve work and prepare to re-plan' }).click()
    await expect(page.getByRole('status')).toContainText('Local recovery is ready')
    await page.getByText('Evidence references and usage').click()
    await expect(page.getByText(/Original recorded usage:/)).toContainText('Original recorded usage: 0')
    await expect(page.getByText(/Saved reply usage:/)).toContainText('25')
    expect(await page.evaluate(() => (window as any).fixture.calls.map((x: any) => x.action))).toEqual(['diagnoseConflict', 'resolveConflict', 'diagnoseConflict'])
  })
})

test('a refresh failure after commit retains a stale guarded view', async () => {
  await withRenderer('refresh-failed', async page => {
    await page.evaluate(values => { (window as any).fixture.responses = values }, [eligible, { error: 'Synthetic diagnosis unavailable' }])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.getByRole('button', { name: 'Preserve work and prepare to re-plan' }).click()
    await expect(page.getByText(/Stale diagnosis/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Preserve work and prepare to re-plan' })).toBeDisabled()
    await expect(page.getByText(/Local recovery is ready/)).toHaveCount(0)
  })
})

test('timeout after commit is reconciled through the same authoritative inspection', async () => {
  await withRenderer('timeout', async page => {
    await page.evaluate(values => { const f = (window as any).fixture; f.responses = values; f.resolveError = 'Synthetic timeout after commit' }, [eligible, ready])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.getByRole('button', { name: 'Preserve work and prepare to re-plan' }).click()
    await expect(page.getByRole('status')).toContainText('Local recovery is ready')
    await page.getByText('Evidence references and usage').click()
    await expect(page.getByText(/Original recorded usage:/)).toContainText('Original recorded usage: 0')
  })
})

test('unavailable evidence and omitted usage remain distinct from original unknown facts', async () => {
  await withRenderer('unavailable', async page => {
    const { original_usage: _original, ...partial } = ready
    await page.evaluate(values => { (window as any).fixture.responses = values }, [{ ...partial, projection: 'blocked', saved_usage: null,
      verification: { original: 'unavailable', saved: 'checked_now', raw: 'unavailable', operations: 'verified_at_resolution' },
      evidence_availability: { 'native:attempt': { status: 'unavailable', reason: 'Saved file is missing' } } }])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.getByText('Evidence references and usage').click()
    await expect(page.getByText(/Original recorded usage:/)).toContainText('unavailable')
    await expect(page.getByText(/Saved reply usage:/)).toContainText('unknown')
    await expect(page.getByRole('button', { name: 'Open native response', exact: true })).toBeDisabled()
    await expect(page.getByText(/Saved file is missing/)).toBeVisible()
    await expect(page.getByText(/Raw stream verification:/)).toContainText('Unavailable')
  })
})

test('unavailable historical receipt stays labeled and cannot open another reference', async () => {
  await withRenderer('historical-unavailable', async page => {
    await page.evaluate(values => { (window as any).fixture.responses = values }, [{ ...ready,
      historical_resolutions: [{ request: 'job:old', resolution_ref: 'conflict-resolution:job:old', verification: 'unavailable', reason: 'Historical receipt is missing' }] }])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.getByText('Historical local recovery decisions').click()
    await expect(page.getByText(/Historical receipt is missing/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Open historical resolution job:old', exact: true })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Open saved resolution', exact: true })).toBeEnabled()
  })
})

test('observed execution invalidates old ready until another inspection', async () => {
  await withRenderer('execution-stale', async page => {
    await page.evaluate(values => { (window as any).fixture.responses = values }, [ready,
      { status: 'missing_staging', eligible: false, reasons: ['Current request has no staging'], request: 'job:1:1' }])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await expect(page.getByRole('status')).toContainText('Local recovery is ready')
    await page.evaluate(() => (window as any).renderFixture({ running: true, observation: 'running' }))
    await expect(page.getByText(/Stale diagnosis/)).toBeVisible()
    await expect(page.getByText(/Local recovery is ready/)).toHaveCount(0)
    await page.evaluate(() => (window as any).renderFixture({ running: false, observation: 'new-request' }))
    await expect(page.getByText(/Stale diagnosis/)).toBeVisible()
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await expect(page.getByText(/Request:.*job:1:1/)).toBeVisible()
    await expect(page.getByText(/Stale diagnosis/)).toHaveCount(0)
  })
})

test('a changed stopped-task observation guards old actions and discards in-flight inspection', async () => {
  await withRenderer('observation-stale', async page => {
    await page.evaluate(values => { (window as any).fixture.responses = values }, [eligible, { deferred: true, value: ready }])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.waitForFunction(() => Boolean((window as any).fixture.release))
    await page.evaluate(() => (window as any).renderFixture({ observation: 'head-or-request-changed' }))
    await expect(page.getByText(/Stale diagnosis/)).toBeVisible()
    await page.evaluate(() => (window as any).fixture.release())
    await expect(page.getByRole('button', { name: 'Preserve work and prepare to re-plan' })).toBeDisabled()
    await expect(page.getByText(/Local recovery is ready/)).toHaveCount(0)
  })
})

test('unavailable current head is explicitly labeled', async () => {
  await withRenderer('head-unavailable', async page => {
    await page.evaluate(values => { (window as any).fixture.responses = values }, [{ ...ready, head: 'missing-head', versions: ['missing-head'], head_verification: 'unavailable' }])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await expect(page.getByText(/Current head verification:/)).toContainText('Unavailable')
    await expect(page.getByText(/Current head:/)).toContainText('missing-head')
  })
})

test('each link displays its own attempt and partial evidence; missing observation stays missing', async () => {
  await withRenderer('attribution', async page => {
    await page.evaluate(values => { (window as any).fixture.responses = values }, [{ ...eligible,
      eligible: false, status: 'missing_staging', attempt: 'B', current_attempt_evidence: { native_ref: 'established', stream_ref: 'not_established' },
      attempt_observation: { status: 'missing' }, evidence_provenance: {
        native_ref: { ref: 'native:attempt', status: 'verified', request: 'job:0:0', attempt: 'B', relation: 'selected_attempt', completeness: 'partial' },
        stream_ref: { ref: 'stream:attempt', status: 'verified', request: 'job:0:0', attempt: 'A', relation: 'earlier_attempt', completeness: 'partial' } } }])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.getByText('Evidence references and usage').click()
    await expect(page.locator('p').filter({ hasText: /^Native:/ })).toContainText('Attempt: B (selected attempt evidence; partial evidence)')
    await expect(page.locator('p').filter({ hasText: /^Raw stream:/ })).toContainText('Attempt: A (earlier attempt evidence; partial evidence)')
    await expect(page.getByText(/Selected attempt receive observation:/)).toContainText('Missing; received byte count is not established.')
    await expect(page.getByText(/Selected attempt raw stream evidence:/)).toContainText('No corresponding retained evidence established.')
    await page.getByRole('button', { name: 'Open complete raw bytes', exact: true }).click()
    expect(await page.evaluate(() => (window as any).fixture.evidence)).toEqual([{ ref: 'stream:attempt', raw: true }])
  })
})

test('an unconfirmed evidence owner disables only its own link without guessing', async () => {
  await withRenderer('unconfirmed-owner', async page => {
    await page.evaluate(values => { (window as any).fixture.responses = values }, [{ ...eligible, eligible: false,
      evidence_provenance: { ...eligible.evidence_provenance, stream_ref: { ref: 'stream:attempt', status: 'unconfirmed', reason: 'Wrong request membership.' } } }])
    await page.getByRole('button', { name: 'Inspect saved acceptance' }).click()
    await page.getByText('Evidence references and usage').click()
    await expect(page.getByRole('button', { name: 'Open complete raw bytes', exact: true })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Open native response', exact: true })).toBeEnabled()
    await expect(page.locator('p').filter({ hasText: /^Raw stream:/ })).toContainText('Wrong request membership.')
    await expect(page.locator('p').filter({ hasText: /^Raw stream:/ })).not.toContainText('Attempt:')
  })
})
