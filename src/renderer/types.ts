export type Route = {
  endpoint: string; model: string; protocol: 'chat_completions' | 'responses';
  context_tokens: number; output_tokens: number; image_tokens: number | null; vision: boolean;
  timeout_seconds: number; parameters: Record<string, unknown>
}
export type Limits = { max_requests: number; max_active_seconds: number; replay_unknown: boolean; max_attempts_per_request: number }
export type Settings = { route?: Route; limits?: Limits; hasKey?: boolean; encryptionAvailable?: boolean; remember?: boolean }
export type Job = {
  id: string; name: string; scope: string; status: string; page_count: number; head: string | null; delivery: string | null;
  last_message: string; attempts: number; active_seconds: number; limits: Limits; route: Route | null; running?: boolean;
  cancel_requested: boolean; stop_reason: string | null; content_claim: string;
  versions?: { id: string; title: string; claim: string }[];
  requests?: { id: string; kind: string; status: string; capacity?: { input_estimate: number; capacity: number; output_reserve: number } }[];
  events?: { seq: number; type: string; data: Record<string, unknown>; created: number }[];
  evidence?: { ref: string; kind: string; bytes: number; meta: Record<string, unknown> }[]
}
export type Block = { id: string; markdown: string; pages: number[]; source_note: string }
export type Saved = { version: string; markdown: string; preview: string; content: { title: string; scope: string; blocks: Block[]; claim: string; known_gaps: string[] } }

declare global {
  interface Window { workbench: { invoke<T = any>(action: string, args?: Record<string, unknown>): Promise<T> } }
}
