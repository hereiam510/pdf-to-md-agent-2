import type { DiagnosticRecordArgs, DiagnosticRecordResult } from '../../types'

// Supported detail entry point. The generic transport overload is intentionally
// hidden from callers here; backend checks still establish runtime JSON facts.
export function readDiagnosticRecord(args: DiagnosticRecordArgs): Promise<DiagnosticRecordResult> {
  return window.workbench.invoke('diagnosticRecord', args)
}
