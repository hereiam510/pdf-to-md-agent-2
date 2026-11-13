import { test, expect } from '@playwright/test'
import { readDiagnosticRecord } from '../../../src/renderer/features/diagnostics/diagnosticClient'
import type { DiagnosticRecordArgs, DiagnosticRecordResult } from '../../../src/renderer/types'

async function withBridge(
  invoke: (action: string, args?: Record<string, unknown>) => Promise<DiagnosticRecordResult>,
  check: () => Promise<void>
) {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'window')
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { workbench: { invoke } } })
  try { await check() }
  finally {
    if (previous) Object.defineProperty(globalThis, 'window', previous)
    else Reflect.deleteProperty(globalThis, 'window')
  }
}

const args: DiagnosticRecordArgs = { job: 'task', view: 'captured-view', kind: 'request', key: 'exact-request' }

test('diagnostic client delegates once with identical payload, promise and result for each status', async () => {
  const results: DiagnosticRecordResult[] = [
    { status: 'ok', view: args.view, job: args.job, captured_at: 1000, graph: 'unchecked', consistency: 'captured catalog',
      event_boundary_is_change_cursor: false, kind: args.kind, id: args.key, record: {}, links: [], limitations: [] },
    { status: 'unavailable', job: args.job, reason: 'Record unavailable', refreshable: true },
    { status: 'stale', job: args.job, reason: 'View expired', refreshable: true }
  ]
  for (const result of results) {
    const calls: { action: string; args?: Record<string, unknown> }[] = []
    const pending = Promise.resolve(result)
    await withBridge((action, payload) => { calls.push({ action, args: payload }); return pending }, async () => {
      const returned = readDiagnosticRecord(args)
      expect(returned).toBe(pending)
      expect(await returned).toBe(result)
      expect(calls).toEqual([{ action: 'diagnosticRecord', args }])
      expect(calls[0].args).toBe(args)
    })
  }
})

test('diagnostic client propagates the original rejection without a retry', async () => {
  const failure = new Error('Diagnostic transport unavailable')
  const calls: string[] = []
  const pending = Promise.reject<DiagnosticRecordResult>(failure)
  await withBridge(action => { calls.push(action); return pending }, async () => {
    const returned = readDiagnosticRecord(args)
    expect(returned).toBe(pending)
    await expect(returned).rejects.toBe(failure)
    expect(calls).toEqual(['diagnosticRecord'])
  })
})
