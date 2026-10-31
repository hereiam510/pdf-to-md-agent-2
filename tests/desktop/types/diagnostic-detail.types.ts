// Compile-only controls, included by the repository's tsc --noEmit check.
import type { Dispatch, SetStateAction } from 'react'
import type { DiagnosticDetail, DiagnosticLink, DiagnosticRecordResult } from '../../../src/renderer/types'
import { readDiagnosticRecord } from '../../../src/renderer/features/diagnostics/diagnosticClient'

type IsAny<T> = 0 extends (1 & T) ? true : false
type ExpectFalse<T extends false> = T
type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false
type ExpectTrue<T extends true> = T

// Deliberate low-level discriminator: the transport still has the old escape.
// Production detail consumers must import readDiagnosticRecord instead.
export function lowLevelBridgeDiscriminator(invoke: typeof window.workbench.invoke) {
  const missingKey = invoke('diagnosticRecord', { job: 'task', view: 'view', kind: 'request' })
  const retainedEscape: ExpectTrue<IsAny<Awaited<typeof missingKey>>> = true
  void retainedEscape
}

export function diagnosticArgumentControls() {
  // @ts-expect-error Arguments are required at the actual production entry point.
  readDiagnosticRecord()
  // @ts-expect-error job is required.
  readDiagnosticRecord({ view: 'view', kind: 'request', key: 'request' })
  // @ts-expect-error view is required.
  readDiagnosticRecord({ job: 'task', kind: 'request', key: 'request' })
  // @ts-expect-error kind is required.
  readDiagnosticRecord({ job: 'task', view: 'view', key: 'request' })
  // @ts-expect-error DT01 discriminator: missing key cannot select a fallback.
  readDiagnosticRecord({ job: 'task', view: 'view', kind: 'request' })
  // @ts-expect-error job must be a string.
  readDiagnosticRecord({ job: 1, view: 'view', kind: 'request', key: 'request' })
  // @ts-expect-error view must be a string.
  readDiagnosticRecord({ job: 'task', view: 1, kind: 'request', key: 'request' })
  // @ts-expect-error kind must be a string.
  readDiagnosticRecord({ job: 'task', view: 'view', kind: 1, key: 'request' })
  // @ts-expect-error key must be a string.
  readDiagnosticRecord({ job: 'task', view: 'view', kind: 'request', key: 1 })
  // @ts-expect-error Callers cannot select their own result type.
  readDiagnosticRecord<string>({ job: 'task', view: 'view', kind: 'request', key: 'request' })
}

export async function diagnosticDetailContract(
  save: Dispatch<SetStateAction<DiagnosticDetail | null>>,
  link: DiagnosticLink,
  raw: unknown
) {
  const promise = readDiagnosticRecord({ job: 'task', view: 'view', kind: 'request', key: 'request' })
  const exact: ExpectTrue<Equal<typeof promise, Promise<DiagnosticRecordResult>>> = true
  const result = await promise
  const typed: DiagnosticRecordResult = result
  const checked: ExpectFalse<IsAny<typeof result>> = false
  const checkedLinks: ExpectFalse<IsAny<DiagnosticDetail['links'][number]>> = checked
  // @ts-expect-error A failed response cannot enter successful detail state.
  save(result)
  // @ts-expect-error Failure responses do not expose detail links before narrowing.
  result.links.map(item => item.ref)
  if (typed.status === 'ok') {
    save(typed)
    typed.links.map(item => {
      const inferred: ExpectFalse<IsAny<typeof item>> = checkedLinks
      if (item.status === 'unavailable') {
        // @ts-expect-error Failed links have no success facts.
        return item.facts.attempt
      }
      const bytes: number = item.facts.bytes
      void inferred
      return `${item.ref}:${bytes}`
    })
  } else {
    const status: 'unavailable' | 'stale' = typed.status
    const refreshable: true = typed.refreshable
    // @ts-expect-error Even a refreshable failure is not successful detail.
    save(typed)
    void [status, refreshable]
  }
  if (link.status === 'unavailable') {
    // @ts-expect-error Raw observations cannot become verified ownership.
    const owner: string = link.raw_descriptor.meta.job
    void owner
  }
  // @ts-expect-error Arbitrary JSON cannot be assigned to detail state.
  save(raw)
  // @ts-expect-error Raw operation results have no checked parent field.
  const parent: string = typed.status === 'ok' ? typed.result.parent : ''
  void [parent, exact]
}
