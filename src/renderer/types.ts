export type WaitPolicy = { first_progress_seconds: number; idle_progress_seconds: number; total_seconds: number | null }
export type Route = {
  endpoint: string; model: string; protocol: 'chat_completions' | 'responses';
  context_tokens: number; output_tokens: number; image_tokens: number | null; vision: boolean;
  timeout_seconds: number; wait_policy?: WaitPolicy | null; parameters: Record<string, unknown>
}
export type Limits = { max_requests: number; max_active_seconds: number; replay_unknown: boolean; max_attempts_per_request: number; max_response_repairs: number }
export type Settings = { route?: Route; limits?: Limits; hasKey?: boolean; encryptionAvailable?: boolean; remember?: boolean;
  revision?: number; credentialState?: 'ready' | 'failed'; error?: string }
export type ReceiveObservation = {
  mode?: string; settled?: boolean; stop_cause?: string | null; http_status?: number | null;
  headers_elapsed_seconds?: number | null; first_body_elapsed_seconds?: number | null; last_body_elapsed_seconds?: number | null;
  received_body_bytes?: number; first_progress_elapsed_seconds?: number | null; last_progress_elapsed_seconds?: number | null;
  event_count?: number; progress_count?: number; protocol_complete?: boolean; terminal_event?: string | null;
  diagnostic?: { category: string; field: string; stage: string; ordinal: number | null }
}
export type Job = {
  id: string; name: string; scope: string; status: string; page_count: number; head: string | null; delivery: string | null;
  last_message: string; attempts: number; active_seconds: number; limits: Limits; route: Route | null; running?: boolean;
  active_since?: number; active_time_budget_policy?: 'known_active_only';
  active_time_gaps?: { id: string; from_wall: number; observed_wall: number; wall_span_seconds: number; active_seconds: null }[];
  cancel_requested: boolean; stop_reason: string | null; content_claim: string;
  compaction_recovery?: { request: string } | null;
  diagnostic_limitations?: string[];
  versions?: { id: string; title: string; claim: string }[];
  requests?: { id: string; kind: string; status: string; diagnostic_status?: string; reason?: string; attempts?: number; receive?: ReceiveObservation | null; capacity?: { input_estimate: number; capacity: number; output_reserve: number } }[];
  event_summary?: { count: number; latest_seq: number | null };
  evidence?: { ref: string; kind: string; bytes: number; meta: Record<string, unknown> }[]
}
export type Block = { id: string; markdown: string; pages: number[]; source_note: string }
export type Saved = { job: string; version: string; markdown: string; preview: string; content: { title: string; scope: string; blocks: Block[]; claim: string; known_gaps: string[] } }
export type EditSession = { job: string; baseVersion: string; expectedHead: string | null; mode: 'edit' | 'rebuild'; blocks: Block[] }

export type DiagnosticPage = {
  status: string; reason?: string; view: string; job: string; captured_at: number; graph: string; consistency: string;
  total: number; first: number; last: number; boundary_seq: number | null; older: string | null; newer: string | null; oldest: string; recent: string;
  events: { id: string; seq: number; created: number; type: string; data: Record<string, unknown> }[];
  kind?: string; items?: { id: string; created?: number; diagnostic_status?: string; status?: string; tool?: string; claim?: string; attempts?: number; reason?: string; parent?: string }[];
  offset?: number; next?: string | null;
}

export type DiagnosticLink = {
  ref: string;
  // Observations retain rejected shapes. They cannot supply labels or navigation.
  raw_descriptor?: unknown;
  association?: string;
} & ({ status: 'unavailable'; reason: string; facts?: never } | {
  status: 'available; integrity checked, acceptance not inferred';
  facts: { kind: string; bytes: number; meta: Record<string, unknown>; attempt?: string; relation?: string };
  reason?: never;
})

// The diagnostic JSON contract, not a runtime validator for HTTP/IPC payloads.
// Only fields used structurally by this renderer are described; original raw
// objects are retained in full and do not acquire validated-fact semantics.
export type DiagnosticDetail = {
  status: 'ok'; view: string; job: string; captured_at: number; graph: string; consistency: string;
  event_boundary_is_change_cursor: false;
  kind: string; id: string;
  // record_summary checks these display fields, not the whole original record.
  record: { status?: string | null; parent?: string | null };
  links: DiagnosticLink[]; limitations: string[];
  boundary?: string;
  publication?: { pointer: unknown; staging_ref: string | null; meaning: string };
  frozen_preparation?: { kind: unknown; payload_ref: unknown; route: unknown; meta: unknown; instruction_basis: unknown; replay_policy: unknown };
  attempts?: ({ id: string; record: unknown; receive_record: unknown; usage_state: 'unknown' | 'reported'; time_meaning: string; status?: never; reason?: never }
    | { id: string; status: 'unavailable'; reason: string; record?: never; usage_state?: never })[];
  raw_usage?: { ref: string; attempt: string; usage: unknown; meaning: string; ordinal?: number;
    validation?: { status: 'unknown' | 'partial' | 'complete'; reason: string | null; usage: unknown } }[];
  saved_acceptance_facts?: object; usage_comparison?: string;
  result?: unknown; effect?: string; execution_history?: string; origin?: string;
  request_association?: { status: 'confirmed'; request: string; publication: string; meaning: string; reason?: never }
    | { status: 'unconfirmed'; candidate_request?: string; reason: string; publication?: never; meaning?: never };
  request?: string | null; version?: string;
  operations?: { id: string; origin: string; publication?: string; candidate_ref?: unknown }[];
  unconfirmed_operations?: { id: string; status: 'unconfirmed'; candidate_request?: string; reason: string }[];
  related?: { kind: string; id: string; record: unknown }[];
  events?: { seq: number; job: string; type: string; data: unknown; created: number }[];
  candidate_ref?: unknown; verification?: string; projection?: string; limitation?: string;
}

// diagnostic_read returns exactly these two failure statuses. HTTP/auth/query
// errors reject the invoke promise instead of inventing another JSON status.
export type DiagnosticRecordResult = DiagnosticDetail | {
  status: 'unavailable' | 'stale'; job: string; reason: string; refreshable: true
}
export type DiagnosticRecordArgs = { job: string; view: string; kind: string; key: string }

declare global {
  interface Window { workbench: {
    invoke(action: 'diagnosticRecord', args: DiagnosticRecordArgs): Promise<DiagnosticRecordResult>;
    invoke<T = any>(action: string, args?: Record<string, unknown>): Promise<T>
  } }
}
