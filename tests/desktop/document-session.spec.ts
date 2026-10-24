import { test, expect, _electron as electron } from '@playwright/test'
import type { ElectronApplication } from '@playwright/test'
import { resolve } from 'node:path'

const pending = (app: ElectronApplication) => app.evaluate(() => (globalThis as any).sessionHarness.pending.length)
const captures = (app: ElectronApplication) => app.evaluate(() => (globalThis as any).sessionHarness.captures)
const hold = (app: ElectronApplication, value: boolean) => app.evaluate((_electron, value) => { (globalThis as any).sessionHarness.hold = value }, value)
const settle = (app: ElectronApplication, index: number, fail = false) => app.evaluate((_electron, { index, fail }) => {
  (globalThis as any).sessionHarness.settle(index, fail)
}, { index, fail })

async function open() {
  const app = await electron.launch({ args: [resolve('tests/desktop/session-harness.cjs')] })
  const window = await app.firstWindow()
  await window.getByRole('button', { name: 'Session fixture' }).click()
  await expect(window.frameLocator('iframe').getByText('Retained second page.')).toBeVisible()
  return { app, window }
}

test('loading blocks editing/export and the draft binds to the loaded version', async () => {
  const { app, window } = await open()
  try {
    await window.getByLabel('Saved version').selectOption('v1')
    await expect(window.getByRole('button', { name: 'Rebuild from this version' })).toBeEnabled()
    await hold(app, true)
    await window.getByLabel('Saved version').selectOption('v2')
    await expect.poll(() => pending(app)).toBe(1)
    await expect(window.getByText('Loading selected version…')).toBeVisible()
    await expect(window.locator('iframe')).toHaveCount(0)
    await expect(window.getByRole('button', { name: 'Edit content', exact: true })).toBeDisabled()
    await expect(window.getByRole('button', { name: 'Export ZIP' })).toBeDisabled()
    await hold(app, false); await settle(app, 0)
    await expect(window.frameLocator('iframe').getByText('Retained second page.')).toBeVisible()
    await window.getByRole('button', { name: 'Export ZIP' }).click()
    await window.getByRole('button', { name: 'Edit content', exact: true }).click()
    await expect(window.locator('.block-editor textarea')).toHaveCount(2)
    await expect(window.getByLabel('Saved version')).toBeDisabled()
    await window.locator('.block-editor textarea').first().fill('Edited first page.')
    await window.getByRole('button', { name: 'Save new version' }).click()
    await expect(window.getByRole('status')).toContainText('Saved your edits')
    const recorded = await captures(app)
    expect(recorded[0]).toMatchObject({ action: 'export', job: 'job1', version: 'v2' })
    expect(recorded[1]).toMatchObject({ action: 'edit', job: 'job1', edit: {
      base_version: 'v2', expected_head: 'v2', mode: 'edit',
      replace_blocks: [{ markdown: 'Edited first page.' }, { markdown: 'Retained second page.' }]
    } })
  } finally { await app.close() }
})

test('failed and out-of-order reads cannot enable a stale version; retry is local', async () => {
  const { app, window } = await open()
  try {
    await hold(app, true)
    await window.getByLabel('Saved version').selectOption('v1')
    await expect.poll(() => pending(app)).toBe(1)
    await window.getByLabel('Saved version').selectOption('v2')
    await expect.poll(() => pending(app)).toBe(2)
    await settle(app, 1, true)
    await expect(window.getByRole('alert')).toContainText('Could not load the selected version')
    await settle(app, 0) // A late successful V1 must not replace the failed V2 selection.
    await expect(window.getByRole('button', { name: 'Export ZIP' })).toBeDisabled()
    await expect(window.getByRole('button', { name: 'Edit content', exact: true })).toBeDisabled()
    await expect(window.locator('iframe')).toHaveCount(0)
    await hold(app, false)
    await window.getByRole('button', { name: 'Retry loading version' }).click()
    await expect(window.frameLocator('iframe').getByText('Retained second page.')).toBeVisible()
    expect(await captures(app)).toEqual([])
  } finally { await app.close() }
})

test('head advancement retains the original edit session and conflict keeps the draft', async () => {
  const { app, window } = await open()
  try {
    await window.getByRole('button', { name: 'Edit content', exact: true }).click()
    await window.locator('.block-editor textarea').first().fill('Keep this unsaved work.')
    await app.evaluate(() => (globalThis as any).sessionHarness.advance())
    await expect(window.getByText('A newer version was saved while you were editing.', { exact: false })).toBeVisible({ timeout: 10000 })
    await expect(window.getByLabel('Saved version')).toHaveValue('v2')
    await window.getByRole('button', { name: 'Save new version' }).click()
    await expect(window.getByRole('alert')).toContainText('Head changed')
    await expect(window.locator('.block-editor textarea').first()).toHaveValue('Keep this unsaved work.')
    expect((await captures(app))[0].edit).toMatchObject({ base_version: 'v2', expected_head: 'v2', mode: 'edit' })
    await window.getByRole('button', { name: 'Discard edits' }).click()
    await window.getByRole('button', { name: 'Rebuild from this version' }).click()
    await window.getByRole('button', { name: 'Save new version' }).click()
    await expect(window.getByRole('status')).toContainText('Saved your edits')
    expect((await captures(app))[1].edit).toMatchObject({ base_version: 'v2', expected_head: 'v3', mode: 'rebuild' })
  } finally { await app.close() }
})
