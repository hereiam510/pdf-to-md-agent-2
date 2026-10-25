# Rebuild architecture

Status: responsibility boundaries implemented in the first application increment on 2026-10-23. EVT-1068, EVT-1107 and EVT-1166 consolidate this direction. The earlier Pi-first and LangChain `create_agent` recommendations remain documented in the reference discussion with their corrections. [CURRENT_STATE](CURRENT_STATE.md) separates implementation from verified scope.

For shared terms, an end-to-end example and the module-specific engineering explanations, read [DEVELOPMENT_GUIDE](DEVELOPMENT_GUIDE.md). It links to detailed local guides. Source IDs provide optional provenance. They are not prerequisites for understanding this architecture.

## Responsibilities

| Component | Owns | Boundary |
| --- | --- | --- |
| Desktop shell | Task configuration, source/scope selection, progress, saved-document reading, intervention and export access | Electron/TypeScript/React. Reconstruct the UI from durable state after reconnect. |
| Python controller | Agent loop, finite execution policy, task lifecycle and accepted tool-batch sequencing | One controller and shared tools. The agent chooses conversion methods. |
| Small LangGraph StateGraph | Explicit model/tool/context/recovery transitions and checkpoints of compact orchestration state, including small context policy | Framework is a preferred substrate, not an external-effect transaction manager |
| Nexus request service | Native encoding of the context-selected frozen input, request identity, attempts, complete accepted replies, budgets and cancellation checks | Normal reasoning and compaction share this service. It does not independently reselect evidence. |
| Shared tool dispatcher | Tool discovery, raw argument retention, validation, dispatch and durable original receipts | App-internal and external MCP/CLI surfaces use the same core contracts |
| Document/evidence core | Immutable source/evidence/candidate/version content, exact reads, editing, rendering and explicit-version exports | Assess content fidelity against the source. Storage integrity is a separate guarantee. |
| SQLite metadata | Version registration, current pointers, operation uniqueness/receipts and defined execution metadata | Short transactions cover durable metadata. Large immutable files remain external. |

There is no required module count or table count. Boundaries may share a file or be factored into packages as implementation warrants. Do not create a second agent loop merely to adopt a framework.

## Agent loop and autonomy

Deferred context coordination is part of that same loop. `Context` validates and projects proposed selections; `ContextUpdates` records final settlement at an unfrozen request boundary; Runtime remains the sole graph-state writer. Checkpoints keep the active compact policy plus pending/outcome references. Immutable proposal chains retain exact intended changes outside checkpoints. Complete-input admission activates the proposal, with compaction first when needed. A transient release view can help compaction but cannot establish that the original policy will work after rejecting that proposal. Capacity rejection instead previews the actual active fallback and rejected-outcome envelope through the same normal/compaction assembler before committing. Settlement receipts reconcile the catalog/checkpoint gap without a second scheduler or cross-store atomicity claim. [Q2](CONTRACTS.md#q2-context-transitions) owns ordering and replay semantics.

A graph can express a dynamic model/tool loop. Graph-based execution does not require a fixed business workflow, and autonomy does not remove the need to manage state, budgets, side effects and recovery. The graph represents execution responsibilities. The model still selects methods, tools and continuation based on results.

The model selects source access, OCR, scripts and reconstruction scope. The app checks capacity, maintains identities and accepts complete native replies. The dispatcher executes only validated calls. Before the assembler builds the next model input, the dispatcher records each accepted batch member's success, rejection or failure. A complete accepted reply does not imply that every proposed operation passes domain validation. Context work occurs at a defined safe boundary with the same durable request and budget handling as other model calls.

The implemented graph has `coordinate`, `prepare`, `model`, `tools`, and `compact` nodes. `coordinate` restores/settles a pending context proposal or checkpoints its explicit waiting observation. Only after that checkpoint does `prepare` assemble/freeze a fitting normal or compaction request through the shared Nexus service. This separates a durable decision from the ability to deliver its outcome in the next input. `tools` settles the accepted batch sequentially. A text-only reply returns through coordination with durable continuation feedback; invalid handoffs return with bounded correction while old context remains active. Reports, cancellation and exhausted limits end the invocation. [The contracts](CONTRACTS.md#implemented-first-version-contracts) own exact state and recovery behavior.

Continuation has an explicit entry boundary. The server conveys the user's Continue action; the runtime reconciles durable records before deciding whether to resume the existing request or record a distinct request transition. Nexus owns accepted-reply/attempt facts, the dispatcher owns completed or unexecuted tool receipts, and graph state owns the next step and feedback references. New amendments supersede only unstarted accepted calls; completed effects and unknown outcomes are not relabeled. This fits the existing single-writer graph without adding a second scheduler or changing the agent's choice of conversion methods.

Task settings and time accounting remain application-service facts outside graph rollback. The server validates allowed changes under the task lock and records before/after settings with the job update. Nexus separates current total allowances from frozen request input/replay policy. `ActiveTime` owns monotonic in-run measurements, short transactional progress checkpoints and explicitly unknown crash tails; Runtime, Nexus and the child-process poller share that one meter per invocation. The desktop edits task limits separately from connection defaults and displays effective values and uncertainty. [CONTRACTS Q3](CONTRACTS.md#existing-task-settings-and-active-time-accounting) defines the policy and limits. No new scheduler, framework or conversion recipe is involved.

## Content and context are separate

PDF geometry and image derivation belong to the evidence core. The public region frame matches extraction's unrotated page points; the renderer alone converts to display coordinates and records the actual raster transform. Image extraction retains encoded image/mask streams separately from a display asset, including original/derivative identity and color/encoding provenance. The document core follows only the selected assets' original-stream references into an immutable version and export. This keeps originals portable without exposing JPX/encoded streams as preview images or adding a model-side conversion recipe. [The PDF contract](CONTRACTS.md#pdf-coordinates-and-image-delivery) owns exact fields and limits.

Keep complete immutable originals outside the model context. Distinguish:

1. Source PDF and derived evidence with source identity and provenance.
2. Received native messages and tool arguments, including rejected or incomplete candidates.
3. Accepted executable messages, tool-batch progress and original receipts.
4. Immutable document versions and explicit delivery versions.
5. The temporary model-input projection and compact continuation state.

Correction feedback is an immutable application result linked to the accepted response. It does not change that response's native acceptance status. Graph state holds only the current feedback references, counts and episode basis. Re-entry reconstructs the same transition from those records. Stable handoff identities and transactional event receipts prevent duplicate handoff references and correction/application events at the tested checkpoint gaps.

Model-facing projections can release or replace large content with accurate references without rewriting the original journal. Replay always uses the original executable call/receipt, never a shortened display of it. Saving data does not automatically decide its relevance or release timing.

Evidence hydration belongs in transient request assembly. Returning large hydrated messages as persistent graph-state updates can refill every checkpoint. The retained simplification keeps small context policy (selections, pin/release choices, notes/references, compaction boundary and settled-batch identity) in graph state, with one settlement writer. An additional external policy-version/activation subsystem is not selected for the single executor (EVT-0872/0878). Transient assembled content stays outside that persistent policy. If a framework hook is used, its actual return/persistence semantics must be verified for the selected version.

Pin admission uses that same boundary. The runtime provides its current ordered policy to the dispatcher for `context_update`; `Context` resolves explicit index/image/full/raw selections and preflights the proposed input before a successful tool receipt exists. Rejection retains the prior policy. A successful receipt contains only the resulting references/selections and notes, allowing checkpoint-gap replay without recalculating historical admission. Temporary envelopes account for the pending call and identify later unsettled tools; the next actual request still has its normal capacity gate. No second mutable policy store or provider request is needed.

Stencil components remain inspectable evidence without a deliverable asset registration. An agent-selected page occurrence uses the existing renderer, carrying graphics-state appearance and original-stream provenance into the ordinary immutable document/export path. This preserves method choice and avoids falsely presenting decoded mask coverage as the source figure's colors.

## Authority and recovery

Immutable version files are the recommended body authority. SQLite registers their identities and commits metadata/pointers/receipts. Avoid a second independently mutable body in `blocks_json`. A staged file plus SQLite commit needs an explicit visibility/reconciliation contract. A database transaction does not also commit the external files or graph checkpoint.

Each request, accepted reply, pending batch, document version and operation receipt has one authoritative record. The graph may keep references and deterministic projections of those facts. A checkpoint timestamp proves neither committed external effects nor model exposure to those effects. Preserve local effects when replaying graph work. Do not roll back external budgets or publication with a graph branch.

First-version recovery assumes one active writer per task. Multiple independent task workspaces may exist. Do not confuse directory isolation with model-context isolation or an OS sandbox. General multi-writer/fork/merge coordination is not a first-version prerequisite.

## Provider portability

Nexus is the intended configurable access layer, including the user's subscription route. Provider-native compaction, response retrieval and remote cancellation may be optional future route capabilities, but the baseline must work without them. Compatibility must cover actual native messages, tool-call IDs/pairs, reasoning items, streaming completion and image content, not only a `base_url` setting.

Do not force every native interaction into a lossy common message shape. Keep a native journal and an explicit, validated projection/adapter where framework messages are needed. Normal inference and history compaction share the same request service, persistent limits and cancellation gate. Framework/SDK/proxy retries must not multiply independently.

## Framework tradeoff retained

Pi offers a lightweight extensible loop and compaction/context hooks, but moving the controller toward TypeScript and integrating the Python source/document core has real coordination costs. LangChain `create_agent` offers a maintained loop and middleware but still needs domain storage/protocol contracts. Deep Agents supplies useful offloading/filesystem/summary mechanisms with stronger built-in assumptions. LangMem supplies memory/summary mechanisms rather than the complete document runtime. OpenAI Agents SDK, Claude Agent SDK and other runtimes require provider/authentication/product-fit checks. SDK maturity alone does not prove Nexus subscription compatibility.

The preferred small StateGraph keeps the Python core and native Nexus service explicit while reusing graph persistence/control primitives. This is a fit judgment, not a benchmark proving lower cost, fewer edits or greater reliability. No new framework bake-off is queued by this choice.

## Implementation boundary

No backward compatibility or old-run migration is required. Useful old code can be reviewed for selective reuse, with the original repository preserved. Dependency versions, exact API/schema names and desktop packaging details are not silently copied from an old environment. Network transport expansion remains deferred. CONTRACTS retains the discussed execution boundaries necessary for context and durable work.

## Implementation map and selected dependencies

| Source | Effective responsibility |
| --- | --- |
| `src/desktop/main.ts`, `preload.ts` | Sandboxed renderer, explicit IPC actions, native file dialogs, encrypted connection settings, authenticated loopback engine, isolated preview worker |
| `src/renderer/` | Source/scope selection, source-page display, agent activity, saved preview/Markdown/evidence, local block edits, version selection and ZIP export |
| `src/pdfmd/server.py`, `runtime.py` | Task lifecycle, one executor per job, `StateGraph` and SQLite checkpointer |
| `nexus.py`, `context.py` | Complete native replies, frozen attempts, shared limits, actual-envelope object admission with exact deferred receipts, independent pins, reference-only prefix handling and rolling handoffs with bounded final-capacity correction |
| `storage.py`, `schema.py`, `documents.py` | Immutable objects, metadata transactions, typed document edits, candidates, version integrity and export |
| `evidence.py`, `tools.py`, `tools/ocr-worker.cjs` | PDF text/layout/raw/pixel access, shared dispatch, local Tesseract OCR, saved-output screenshots and opt-in host scripts |

The engine prints a bounded startup announcement and serves only an ephemeral loopback port with a random per-launch bearer token. Electron's renderer has no Node or generic filesystem/network IPC access. Its main process holds the credential and sends it only to the local engine for the configured model request. Important results survive in storage rather than relying on UI event delivery. Closing the app terminates the local child; reopening reads saved state and requires an explicit continuation.

Saved-output previews record the actual scroll position and CSS viewport/document dimensions, the display scale and actual PNG dimensions, as well as the requested viewport. This distinguishes a clamped scroll/window request from the pixels that were captured. The screenshot covers that viewport; it is not a claim to have reviewed the complete document.

`uv.lock` and `pnpm-lock.yaml` record full dependency resolutions. The selected main versions are Python 3.12, LangGraph 1.2.16, SQLite checkpointer 3.1.2, HTTPX 0.28.1, Pydantic 2.14.1, PyMuPDF 2.0, FastAPI 0.161.1, Electron 45.0.0, React 19.3.1, TypeScript 7.0.2, electron-vite 6.0.0 and Tesseract.js 7.0.0. PyInstaller 6.22.3 bundles the engine. These pins are implementation choices, not inherited old-environment requirements.

Official guidance consulted for this implementation:

- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [PyMuPDF TextPage](https://pymupdf.readthedocs.io/en/latest/textpage.html#TextPage.extractDICT): the capacity increment retains the existing checkpoint/reference boundary and preserves dictionary image bytes in saved originals. Request projection is transient; native vision input is separate from Base64 inside a text result. No dependency changes were made.
- [React state structure](https://react.dev/learn/choosing-the-state-structure) and [effect lifecycle](https://react.dev/reference/react/useEffect): the 2026-10-24 document session groups related edit state, derives readiness from task/version identity and ignores obsolete asynchronous reads. [Pydantic model validators](https://docs.pydantic.dev/latest/concepts/validators/) govern edit-mode and content-source validation. Installed dependency pins remain unchanged.
- [LangGraph checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers): checkpoint lifecycle, synchronous durability and supported `update_state(as_node=...)` continuation. The 2026-10-24 change records its continuation intent before updating the checkpoint, so a cross-store gap can be reconciled. Installed SQLite saver signatures were also inspected.
- [HTTPX exceptions](https://www.python-httpx.org/exceptions/): HTTP status failures and transport failures are distinct observations. Explicit failed-response Continue is kept separate from unknown-outcome replay; neither establishes remote cancellation or a known bill.
- [Electron security](https://www.electronjs.org/docs/latest/tutorial/security) and [safeStorage](https://www.electronjs.org/docs/latest/api/safe-storage): process isolation, narrow IPC and the asynchronous encryption API.
- [electron-vite](https://electron-vite.org/guide/) and [pnpm settings](https://pnpm.io/settings): supported desktop build structure and explicit dependency build-script policy.
- [Native function calls](https://developers.openai.com/api/docs/guides/function-calling) and [Responses](https://developers.openai.com/api/reference/resources/responses/methods/create): protocol field/call identity guidance. Actual Nexus route support remains separately verified.
- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/tutorial.html), [image recipes](https://pymupdf.readthedocs.io/en/latest/recipes-images.html), [Tesseract.js API](https://github.com/naptha/tesseract.js/blob/master/docs/api.md), and [PyInstaller usage](https://pyinstaller.org/en/stable/usage.html): request lifecycle, source access, OCR worker and packaged-resource handling.

The Windows build preserves PyMuPDF's required resource data. When the selected Python distribution has an SSL distrust resource beside `ssl.py`, the build also preserves it. A frozen-engine check initializes verified TLS and the HTTP client before desktop packaging. It does not disable certificate verification or send a model request.
