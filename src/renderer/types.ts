export type WaitPolicy = { first_progress_seconds: number; idle_progress_seconds: number; total_seconds: number | null }
export type Route = {
  endpoint: string; model: string; protocol: 'chat_completions' | 'responses';
  context_tokens: number; output_tokens: number; image_tokens: number | null; vision: boolean;
  timeout_seconds: number; wait_policy?: WaitPolicy | null; parameters: Record<string, unknown>
}
export type Limits = { max_requests: number; max_active_seconds: number; replay_unknown: boolean; max_attempts_per_request: number; max_response_repairs: number }
export type Settings = { route?: Route; limits?: Limits; hasKey?: boolean; encryptionAvailable?: boolean; remember?: boolean }
export type ReceiveObservation = {
  mode?: string; settled?: boolean; stop_cause?: string | null; http_status?: number | null;
  headers_elapsed_seconds?: number | null; first_body_elapsed_seconds?: number | null; last_body_elapsed_seconds?: number | null;
  received_body_bytes?: number; first_progress_elapsed_seconds?: number | null; last_progress_elapsed_seconds?: number | null;
  event_count?: number; progress_count?: number; protocol_complete?: boolean; terminal_event?: string | null
}
export type Job = {
  id: string; name: string; scope: string; status: string; page_count: number; head: string | null; delivery: string | null;
  last_message: string; attempts: number; active_seconds: number; limits: Limits; route: Route | null; running?: boolean;
  active_since?: number; active_time_budget_policy?: 'known_active_only';
  active_time_gaps?: { id: string; from_wall: number; observed_wall: number; wall_span_seconds: number; active_seconds: null }[];
  cancel_requested: boolean; stop_reason: string | null; content_claim: string;
  compaction_recovery?: { request: string } | null;
  versions?: { id: string; title: string; claim: string }[];
  requests?: { id: string; kind: string; status: string; attempts?: number; receive?: ReceiveObservation | null; capacity?: { input_estimate: number; capacity: number; output_reserve: number } }[];
  events?: { seq: number; type: string; data: Record<string, unknown>; created: number }[];
  evidence?: { ref: string; kind: string; bytes: number; meta: Record<string, unknown> }[]
}
export type Block = { id: string; markdown: string; pages: number[]; source_note: string }
export type Saved = { job: string; version: string; markdown: string; preview: string; content: { title: string; scope: string; blocks: Block[]; claim: string; known_gaps: string[] } }
export type EditSession = { job: string; baseVersion: string; expectedHead: string | null; mode: 'edit' | 'rebuild'; blocks: Block[] }

declare global {
  interface Window { workbench: { invoke<T = any>(action: string, args?: Record<string, unknown>): Promise<T> } }
}
