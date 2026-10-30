> Entry snapshot captured 2026-10-31 01:57 UTC+08:00 (Asia/Singapore), before topic reorganization. Original owner: `docs/design/EXECUTION_AND_DELIVERY.md`. The filename is capture time, not adoption or execution time. Original text and source times are retained; relative links are adjusted and applicable shared-owner links target this captured edition. Earlier task permissions are historical. Earlier design identities not recorded by the source remain unknown. [Current catalogue](../../INDEX.md).

# Execution, recovery, and delivery engineering handoff

This guide explains durable execution responsibilities, failure reasoning and considered Q3 options without requiring the original chat export. [The implemented contracts](../contracts/20261031_0157_CONTRACTS.md#implemented-first-version-contracts) now select the exact first-version schemas and transitions; they supersede statements below that these choices remain open. Other example IDs, nodes and state labels remain explanatory notation. [CURRENT_STATE](../../CURRENT_STATE.md) records verification and its limits.

[CONTRACTS](../contracts/20261031_0157_CONTRACTS.md) owns the effective boundaries and [OPEN_QUESTIONS](../../decisions/INITIAL_CONTRACTS.md) states their closure conditions. [Document engine](../../guides/DOCUMENT_ENGINE.md) explains content, editing, validation, and file/metadata commits. [Context and evidence](../../guides/CONTEXT_AND_EVIDENCE.md) explains context policy, input selection, capacity, and compaction. [Integration](20261031_0157_INTEGRATION_AND_MODEL_BOUNDARY.md) explains native protocols and framework wiring. The [detailed reference](../discussions/20261031_0157_REBUILD_DELIVERY.md) retains the proposal/correction chain. [Bundled source material](../../sources/rebuild/INDEX.md) is optional audit evidence.

The preferred design uses a small Python LangGraph StateGraph, one shared Nexus request service, and a shared tool dispatcher. It also uses compact graph state, SQLite metadata, and immutable external content. These responsibilities may share one process. The graph provides control and checkpoint primitives. It does not atomically commit remote generation, filesystem results, SQLite changes, and its own checkpoint. The first-version recommendation uses one active writer per task rather than a general multi-writer branch system.

<a id="streaming-contract-candidate-after-review-2026-10-30"></a>
## Read by execution question

Use [current contracts](../contracts/20261031_0157_CONTRACTS.md#reading-this-contract) for governing rules and [current evidence](../../CURRENT_STATE.md#verification-basis) for actual verification. This guide retains mechanism, rationale, examples and historical alternatives; titles containing "historical" do not select implementation.

- Streaming acceptance: [A/SC02 rules](#streaming-contract-a-and-sc02-adopted-rules-and-implementation), [rule basis](#rule-basis-and-field-semantics), [finite acceptance](#finite-acceptance-and-stopping-conditions), [implemented mechanism](#a-implementation-mechanism-2026-10-30).
- Original/accepted evidence and effects: [settlement](#accepted-result-settlement), [local conflict recovery](#historical-conflict-recovery-implementation), [request/attempt identity](#request-and-attempt-identity).
- Persistence and continuation: [receive storage](#implemented-streaming-receive-persistence), [Continue boundary](#implemented-continuation-boundaries), [operation replay](#operation-replay), [recovery transitions](#recovery-transitions).
- Consumption, stop and delivery: [settings/active time](#implemented-task-settings-and-active-time), [budgets and cancellation](#budgets-cancellation-and-stop), [completion](#completion-and-waiting), [export](#explicit-version-export).

<details>
<summary>All sections in this owner</summary>

- [Streaming contract A and SC02: adopted rules and implementation](#streaming-contract-a-and-sc02-adopted-rules-and-implementation)
- [Accepted-result settlement](#accepted-result-settlement)
- [Historical conflict recovery implementation](#historical-conflict-recovery-implementation)
- [Implemented task settings and active time](#implemented-task-settings-and-active-time)
- [Implemented streaming receive persistence](#implemented-streaming-receive-persistence)
- [Implemented continuation boundaries](#implemented-continuation-boundaries)
- [1. Ownership and entry points](#1-ownership-and-entry-points)
- [2. Request, attempt, accepted response, and operation identities](#2-request-attempt-accepted-response-and-operation-identities)
- [3. Accepted batch execution and ordering](#3-accepted-batch-execution-and-ordering)
- [4. Operation replay and resolved defaults](#4-operation-replay-and-resolved-defaults)
- [5. Recovery transitions and durability gaps](#5-recovery-transitions-and-durability-gaps)
- [6. Persistent budgets, cancellation, and stop reasons](#6-persistent-budgets-cancellation-and-stop-reasons)
- [7. Context work uses the same durable execution boundary](#7-context-work-uses-the-same-durable-execution-boundary)
- [8. Execution stop, content completion, and package consistency](#8-execution-stop-content-completion-and-package-consistency)
- [9. Local processes, progress, and desktop IPC](#9-local-processes-progress-and-desktop-ipc)
- [10. Explicit-version export and publication](#10-explicit-version-export-and-publication)
- [11. Worked recovery sequence](#11-worked-recovery-sequence)
- [12. Q3 closure and implementation order](#12-q3-closure-and-implementation-order)

</details>

## Streaming contract A and SC02: adopted rules and implementation

The former heading called this a candidate. A was subsequently selected and implemented, followed by the bounded SC02 correction. The sections below retain the alternatives and review-time evidence alongside the implemented mechanism; [current disposition](../../reviews/RUNTIME_FINDINGS.md#streaming-contract-review-reconciliation-2026-10-30) and [recorded validation](../IMPLEMENTATION_HISTORY.md#sc02-item-state-and-role-correction-locally-verified-2026-10-30) distinguish those stages. No new model call follows from this design.

**A adopted and local implementation/isolated acceptance authorized (2026-10-30).** The human selected the reviewed scope below; real continuation and all retained prohibitions remain outside it. [CONTRACTS](../contracts/20261031_0157_CONTRACTS.md#streaming-progress-waiting) records the selected policy. Implementation and verification are reported separately in CURRENT_STATE. [The findings](../../reviews/RUNTIME_FINDINGS.md#streaming-contract-review-reconciliation-2026-10-30) own defects/evidence; [Stage B](../discussions/20261031_0157_STAGE_B_CONVERSION.md#streaming-contract-discussion-and-review-2026-10-30) owns review chronology and historical execution. This section remains the single detailed mechanism/acceptance owner; the heading is retained for existing links.

### Purpose, alternatives and scope

The receiver should accommodate supported transport variation without turning service metadata into response identity, losing semantic contradictions or executing incomplete tools. Model-generated content, API framing, Nexus translation, SDK behavior and app acceptance policy are distinct. Scope is existing Chat Completions (CC) and Responses, their directly relevant fields, completion, publication and diagnostic consumers. No model-name exceptions, new protocols or universal route compatibility are proposed.

| Option | Appropriate responsibility | Tradeoff and current recommendation |
| --- | --- | --- |
| A: semantic protocol decoder correction | Classify identity, content, service observations, usage and completion by meaning; retain originals and validate the complete reply. | Recommended for the demonstrated problem. Removes unjustified rejection without accepting contradictory content. Requires shared fresh/reopen rules and finite negative controls, not merely deleting `service_tier` from a tuple. |
| B: scoped route adapter | Translate an evidenced route/version-specific representation with an explicit, loss-accounted mapping. | Use only when A cannot interpret a supported difference directly, such as an evidenced finish mapping or cumulative usage contract. Requires native/translated controls. No speculative adapter framework or model-name branch is selected. |
| C: retain rejection and require route correction | Preserve the boundary when identity, content or terminal claims conflict, or a faithful mapping cannot be established. | Appropriate for unresolved semantic contradictions, not the default for any service metadata update. One observed tier transition proves neither deterministic routing nor permanent incompatibility. |

These responsibilities can coexist. A does not remove C's protection, and B cannot manufacture missing termination or erase a refusal. The user requires no backward compatibility, legacy decoder or migration. Nursing and all local PDFs are test inputs; preserve useful originals and historical facts without turning old execution formats into support obligations. This does not lower fidelity or complete-before-tools requirements.

### Rule basis and field semantics

For each rule, identify whether its basis is an official protocol requirement, necessary app attribution/completeness policy, evidenced route mapping, or a remaining local assumption. The following selected rules define supported behavior; they do not prove that every route emits these forms.

| Field or event class | Selected interpretation and preserved boundary |
| --- | --- |
| Response, item, choice and call attribution | Retain single-choice support and attempt/request isolation. Bind observed identity consistently; a conflicting ID, created value, model or item/call association cannot be treated as a metadata refresh. Optional per-event omission is not a conflict or an invented identity. Define required final identity and types explicitly; retain current protections unless an evidenced equivalent is selected. CC documents stable ID/created; model consistency is also an app attribution policy, not permission to guess a replacement. |
| `service_tier`, `system_fingerprint` | Service observations, not tool/completion/billing authority. Absence leaves the observation unchanged; explicit null records unknown; supported non-null values update the final explicit observation with event provenance. Malformed/uninterpretable observations stay in raw evidence and become unavailable in the derived projection, never a guessed default. Preserve the transition history through raw event references, without duplicating it on every chunk. This proposed tolerance is an app policy; request/response tier differences in official documentation do not prove arbitrary changes within a stream are protocol-conforming. |
| CC additional properties | Preserve original bytes. Known competing content containers at choice level (`message`, `text`, `content`, `refusal`, `tool_calls`) must not hide semantic content beside `delta`. Define absence, null, empty and content-bearing cases explicitly: do not reject an absent/neutral field solely by its name, or ignore a populated refusal/container. Other additions require a documented semantic disposition; neither a fixed allowlist of all keys nor treating every other key as harmless is sufficient. |
| Responses supported content events | Validate observed text, reasoning, summary, refusal and supported function-call event families, including `content_part` and applicable summary-part announcements/completions, against item/part identities, deltas and terminal snapshot. A missing optional intermediate announcement is not itself corruption. If present, a completed part cannot contradict the rest of the stream. Preserve opaque encrypted reasoning according to its supported representation; do not require plaintext that the protocol need not supply. |
| Refusal and unsupported content | An observed refusal cannot disappear from tool eligibility because a later snapshot omits it. Unknown message/reasoning part types and unclassified events that might affect content, attribution, error or termination cannot silently authorize a batch. Return an explicit unsupported/rejected result with originals retained. Rejecting a semantic unknown is different from rejecting a harmless added metadata property. |
| Observation-only events | Use a finite named classification justified by applicable official documentation and app semantics, with synthetic controls. Route observations can supplement that basis; a paid/live example is not mandatory before supporting an official event. Object shape, an `output_index` field, an event-name prefix or lack of live Responses evidence does not establish harmlessness or a low rejection cost. |
| Error, finish and terminal | CC requires a successful finished choice plus blank-line-dispatched `[DONE]`; a permitted usage-only event can follow finish. Responses uses its own consistent `response.completed` snapshot, never a CC `[DONE]` requirement. Failed/incomplete terminals, refusal, invalid tools and contradictory completion claims remain ineligible. Keep the received-prefix/UTF-8/trailing-data rule below. No arbitrary event reorder is classified as legal delta segmentation. |

The finite event table below records the supported forms. Documented supported events need positive controls, and unsupported semantic events need negative controls. Text-only part contradictions remain part of this batch's two-protocol completeness claim alongside refusal/control cases.

### Usage interpretation and derived observations

Keep four facts separate: original reported usage, validated usage, accepted publication and billable cost. Usage never proves completeness. Missing, null, malformed or contradictory usage can coexist with valid accepted content; it must not become zero, a guessed sum or a false known total.

Use one pure interpretation of applicable accounting fields across CC streaming assembly, Responses completed snapshots and non-streaming native parsing. Do not fix only a ledger or UI while `parse_reply` still produces another projection. CC uses prompt/completion/total field meanings; Responses uses input/output/total. Existing cross-protocol test aliases are not protocol authority. Correct fixtures while preserving their original behavioral test purpose.

Recognized token counts must be non-negative integers excluding booleans. When input, output and total are all present, check their additive relationship. Check recognized cached/reasoning subsets against the applicable parent when present; do not add them again. Do not impose these numeric rules on arbitrary extra metadata. Missing counts remain missing: a supported partial report must be explicitly partial, with no zero filling or invented total. An unusable or contradictory report yields unavailable validated usage and a local reason, while retaining the original. Finalize the precise partial-report representation and local reason codes during implementation; this is not a reason for a new general assessment.

For CC, allow usage on finish or a permitted usage-only event. Repeated equal aggregate reports do not accumulate. Compare defined accounting fields, not arbitrary provider metadata; differing aggregates without an evidenced cumulative contract yield unknown validated usage rather than silently choosing the last. Absence/null supplies no new count. For Responses, the completed snapshot owns the final report; earlier observations remain separately attributable. Non-mapping usage is a usage-quality failure, not by itself a reason to reject otherwise valid content.

Raw SSE and native response bytes remain immutable. `assembled_response` is derived and linked to its source stream. A final metadata/usage summary may be recomputed on demand or persisted once with provenance/rule identity; it is not a second authority. Reopen recomputes it from original evidence under the applicable rules. No mandatory legacy interpreter follows from a rule/version marker. Keep helper names, compact serialization and small function boundaries with the implementer rather than prescribing a framework.

### Shared acceptance, history and diagnostics

Inspect `streaming.py`, `nexus.py`, `acceptance.py`, `history.py`, relevant `recovery.py` consumers, `server.py`, `diagnostics.py` and directly affected UI/types/tests together. `AcceptanceInspector` reparses native evidence and compares the accepted projection. `history.batch_reply` also reparses resolved-historical native evidence and compares the entire saved projection. Ordinary accepted history has a different read path; do not claim all historical reads reparse.

An unconditional new projection key can invalidate every old exact comparison; a value-only normalization affects records whose values actually change. Neither forces backward compatibility. Preserve incompatible old bytes, usage, pointers and tool facts and report an explicit conflict/unsupported state. Never rewrite old acceptance to make a new comparison pass, clear consumption or auto-resend. New-format first acceptance, publication reconciliation, saved replay and relevant resolved-history consumers must agree. Retain R13's atomic request/attempt settlement, provenance and complete-before-tools gate, and R02's per-chunk durability. Do not splice tool arguments across attempts or bypass tool-schema/handoff validation.

Diagnostic summaries use fixed local categories, known fields/stages and bounded ordinals. Filter values as well as keys. Current `terminal_event` can contain an arbitrary upstream CC finish string; map unsupported values to a local classification rather than echoing them in a supposedly bounded summary. This is distinct from deliberate full raw-evidence access, which remains available. Do not expose arbitrary upstream errors, event names, parameters or credentials in compact reasons. Label usage by artifact kind: usage from `assembled_response` is derived, not an original upstream full response. A raw-report view must identify actual raw observations and avoid implying settlement/billing or hiding their originals behind a derived null. Reuse existing diagnostics; no Langfuse or broad UI redesign is necessary.

### Finite acceptance and stopping conditions

Tests distinguish semantic correction from broad permissiveness. This authorized batch reuses existing streaming-parser, terminal, acceptance-settlement, continuation and delivery mechanisms with new isolated synthetic stores and fixture transports. It uses no real Nursing Store/Runtime or historical live driver.

| Group | Observable acceptance |
| --- | --- |
| Original failure | Original raw hash remains `a7d4423c15da7efc43e11f75fae5f486d298a860d51140be4015970849634d11`; without `[DONE]` it remains ineligible. Any completed derivative is visibly synthetic with distinct identity, never a repaired original or acceptance of the failed attempt. |
| Metadata and attribution | Absence/null/late/repeated/updated service observations and harmless additions follow the stated rules; ID/model/created, item/call and request/attempt conflicts cannot pass. Check final explicit metadata and its raw provenance, not just absence of exceptions. |
| Content and tools | Positive documented content-part events, opaque reasoning and legal interleaved tool deltas assemble correctly. Contradictory parts, observed refusals, unsupported semantic parts/events, hidden CC choice content, incomplete argument JSON, duplicate call IDs and missing observed items cannot execute. |
| Usage | Both protocols cover absent/null, repeated/conflicting reports, malformed container, negative/bool/string counts, total/subset contradictions and supported partial fields. Known counts are accurate, unknown stays unknown, originals remain accessible, and no content failure is invented solely for usage quality. |
| Completion and segmentation | CC finish/DONE and Responses completed semantics are distinct. Missing/failed/incomplete terminal, conflicting received suffixes and invalid UTF-8 fail appropriately. Same actually received bytes split at UTF-8/JSON/SSE boundaries yield equal results. Protocol-permitted delta segmentation is a separate equivalence test; semantic reordering is not assumed valid. |
| Publication and reopen | For each protocol exercise accepted-with-known-usage, accepted-with-unknown-usage and rejected-content-contradiction through first processing, save and reopen. Verify exact raw/assembled/staging/ledger linkage and zero effects before complete acceptance. Publication interruption reconciles without another send, duplicate effects or consumption reset. Include relevant resolved-history equality and explicit old-format conflict controls without a legacy compatibility matrix. |
| Shared flows and delivery | Representative normal/compaction/non-streaming affected paths retain independent handoff validation and failed-Continue successor semantics. Inspect actual saved/reopened/exported text and source-image bytes for bounded synthetic delivery fixtures; passing parser tests alone is insufficient. If UI presentation changes, check the actual focused display/reopen behavior. |
| Diagnosis | Local field/stage/category/ordinal locates the failure without copying synthetic upstream secrets or arbitrary finish/error strings into summaries. Full raw access and raw-versus-derived-versus-settled usage labels remain truthful. |

Same-byte equivalence is conditional on the same received prefix: terminal-driven local close may prevent later chunks from ever being received. Do not claim equality for unseen suffixes. Report parser, Runtime/ledger, actual UI/reopen, synthetic delivery and real-route evidence as separate levels.

Stop and preserve evidence if identity/preservation fails, fresh/reopen judgments differ, tools run early, or supporting a route requires weakening attribution/completeness. Fix routine defects within an authorized implementation batch, but return a material safety/requirement change for decision. A touched path exposing R07 warrants a bounded shared-path correction/decision, not wholesale parser reconstruction. R01/CTX calibration, R02 performance comparisons, R03 subprocess recovery, SDK/dependency replacement, installation, live calls and historical-task migration stay outside this batch. Revisit each on its own evidence or separate selection.

Offline completion does not authorize Nursing. A future ordinary `continue_failed` path preserves rejected `:45:62`, records a continuation receipt and prepares a successor; it does not resend its old attempt, rewrite the frozen request or reuse unknown compaction `:45:61` recovery. This raw has no accepted evidence to recover. Any real continuation needs a later scope/allowance decision and actual-state preflight. Full fourteen-page fidelity, source images, autonomy and save/reopen/export remain product acceptance beyond this batch.

### Primary guidance and evidence limits

The assessment/review consulted [CC streaming events](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events), [Responses streaming events](https://developers.openai.com/api/reference/resources/responses/streaming-events) and [API compatibility guidance](https://developers.openai.com/api/reference/overview). Additive API evolution does not prove every unknown event is harmless. The [pinned CLIProxyAPI translator](https://github.com/router-for-me/CLIProxyAPI/blob/911f49cbd49f4fe2516979754a7488a3fd14fe64/internal/translator/codex/openai/chat-completions/codex_openai_response.go) reads/caches response tier observations and translates finish/usage; it is not byte certification of the installed modified build, a request-echo proof or evidence of permanent route behavior. [OpenAI SDK assembly](https://github.com/openai/openai-python/blob/main/src/openai/lib/streaming/chat/_completions.py) is an implementation comparison only; this app uses HTTPX and its own decoder. Consult relevant official guidance for the installed/selected versions when implementing uncertain features, without automatic upgrades or provider probes.

### SC02 item-state and role follow-up (2026-10-30)

**Implemented within A; local verification is recorded in the closeout below.** The preceding recording turn saved the finding, human decision and finite scope without code changes. The submitted implementation task authorized completion of the correction, isolated acceptance and affected records together. [SC02](../../reviews/RUNTIME_FINDINGS.md#sc02-item-state-and-role-follow-up-2026-10-30) owns evidence strength and disposition; [DECISIONS](../decisions/20261031_0157_DECISIONS.md#sc02-item-state-and-role-follow-up-authorized-2026-10-30) owns authority. No real continuation follows this work.

#### Protocol basis and app policy

The public official references were retrieved again on 2026-10-30 before implementation: [Responses events](https://developers.openai.com/api/reference/resources/responses/streaming-events), [Responses output item schemas](https://developers.openai.com/api/reference/resources/responses/methods/retrieve), [CC events](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events) and [CC create/stream options](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create). Responses distinguishes added/progress observations from an item-done boundary; message, function-call and reasoning statuses have the `in_progress`, `completed`, `incomplete` vocabulary. Function-call and reasoning status are optional. Message role is `assistant`. Added encrypted reasoning can be partial; its completed representation belongs to item done.

The app's supported acceptance policy is separate from the public schema: retain its existing tolerance for absent item status and absent message role, without inventing fields in the native projection. Reject an explicit unsuccessful, malformed or contradictory observation. A final snapshot has no authority to erase one. The three supported types do not document null status, and messages do not document null role; explicit null is therefore a rejected value, not absence or a service-field unknown. This rule is not a route mapping or a claim that every officially documented output item is supported. No Nexus route was sampled. There is no SDK substitution: the existing native decoder remains in use, with installed pinned HTTPX 0.28.1, LangGraph 1.2.16 and SQLite checkpointer 3.1.2 unchanged; graph/framework structure was not modified.

#### Effective mechanism and examples

`streaming.validate_response_item_state` supplies one pure rule for stream observations and `nexus.parse_reply`'s final native items. It dispatches by supported item type and boundary. `_responses` invokes it through `_check_item` for item-added/done events, outputs carried by supported created/in-progress/queued lifecycle snapshots, and the final completed snapshot. Native parsing invokes the same rule with a final boundary, including reasoning. The existing unsupported-type/content gates remain independent.

| Observation | Effective interpretation |
| --- | --- |
| Status absent | Preserve optional-field tolerance. It does not reset a previously observed completion or require an intermediate announcement. |
| Explicit `in_progress` in an added/lifecycle item | Valid before completion; it can become `completed`. It cannot follow an observed completed state for the same item. |
| Explicit `completed` | A successful item state. `_item_statuses` retains completion across later absent fields. An item-done boundary also records completion when status is absent. |
| Explicit `in_progress` at item done or final native output | Reject: the claimed completed item remains in progress. |
| Explicit `incomplete` at any supported observation | Reject immediately; terminal replacement with `completed` or omission cannot recover eligibility. |
| Null, non-string or unsupported status | Reject as unsupported item content. `failed` and `cancelled` are not alternate successful values for these types. |
| Explicit message role | Require `assistant` wherever a supported message item is carried. Reject null, wrong types, non-assistant and unsupported roles at observation, before assembly can drop them. Absence stays optional. |
| Function/reasoning role or function-only fields on reasoning | Do not impose message/function requirements on reasoning. Preserve its opaque encrypted string; added partial encrypted content may become the done representation. Done-to-terminal encrypted content consistency remains required. |

For example, an added function with `in_progress`, done function with `completed`, and completed response remains valid. A done function with `incomplete` or `in_progress` rejects even if the terminal function has `completed` or omits status. A done message with role `user` rejects even when the terminal replaces it with `assistant` or omits role, including a reply that also contains valid function arguments. Supported opaque reasoning without plaintext remains valid when accompanied by otherwise acceptable text/tools. A reasoning-only reply with neither calls nor output text still fails the existing empty-reply gate; the new tests do not weaken it.

The state map remembers only lifecycle completion, separately from identity/content evidence. It does not compare every snapshot status for equality, merge arguments between attempts, require item announcements or fabricate a complete item from deltas. Identity, item/call/request/attempt ownership, complete JSON-object arguments, refusal/content consistency and received-prefix termination retain their existing gates. CC still requires finish plus dispatched `[DONE]`; Responses still uses its own completed semantics. No new usage interpretation, waiting policy, autonomous method restriction or diagnostic value is introduced. Errors use existing bounded categories and `item` fields without upstream values in compact diagnostics.

#### First acceptance, reopened evidence and resolved history

Nexus retains immutable received chunks/raw stream separately from the assembled native artifact and links request/attempt/source stream. Complete validation precedes accepted staging and R13's atomic request/attempt publication. Fresh settlement may reuse only its already validated archive; reopened inspection reconstructs the original bytes under the same decoder. Rejected early events can stop reception before later fixture chunks: preservation checks compare the exact received prefix, without claiming unread bytes were received. Attempt spending, active time and unknown usage are not reset.

A directly related new control exposed a resolved-history bypass: the old receipt reader validated recorded identity, while `batch_reply` reparsed only terminal native content. In a newly created old-semantics fixture, a previously resolved item-status contradiction still entered history. `history.resolution_receipt` now also calls the shared no-write `inspect_acceptance` and requires successful reconstruction with exactly the already supported `finish_conflict` boundary. A prior resolution cannot authorize a new feed/item/native conflict. This one reader defaults to full compatibility for resolved history and graph projection. Read-only diagnostic selection and fact extraction use `verify_stream=False` only to retain the structurally owned receipt, request/attempt and exact refs when bytes are missing or incompatible. `resolved_diagnosis` then performs the default full check separately and blocks its ready projection on failure. Structural identity is not execution authority; the flag is not exposed through a public recovery/Continue action. Ordinary acceptance keeps `accepted_evidence_conflict`; incompatible resolved history raises `Conflict`, keeps the known request/attempt and readable facts in a blocked diagnosis, and cannot repeat the old resolution action. No original acceptance, receipt, operation, consumption or frozen payload is rewritten, and no resend follows.

This current compatibility guard qualifies the earlier decision to avoid repeated full stream checks during resolved inspection. It is required for the newly evidenced semantic change and reuses the existing checker rather than adding a legacy decoder or recovery class. Existing diagnostic fact labels retain their resolution-time meaning; reading bytes for current compatibility does not relabel every saved fact as newly accepted or billed. Repeated resolved reads may cost more; no performance measurement or caching change belongs to this batch. Revisit that cost only with evidence of material impact under separately selected R02/diagnostic work.

#### Local verification closeout

Evidence entry: `.local/sc02-item-state-2026-10-30-run1/README.md`. Only newly generated synthetic Store/Runtime workspaces and fixture transports are used. `run_pytest.py` blocks real HTTP transports and general socket connects while permitting Windows asyncio's own loopback socketpair construction. There is no Electron profile or real task launcher. Python runs with `-B` / `PYTHONDONTWRITEBYTECODE=1`; caches, outputs and test databases are new children of this ignored evidence directory. Existing release and installed artifacts are untouched.

The original Nursing raw is only a read-only negative control. Its exact SHA-256 remains `a7d4423c15da7efc43e11f75fae5f486d298a860d51140be4015970849634d11`; whole and 4096-byte cuts observe 6204 events and reject missing `[DONE]`. No terminator was appended and no real database/WAL was opened. Final identity is HEAD `ba8bad3867c82373da008bccf716be7df413a417` / `master` plus cumulative work and this scoped increment, not a new commit. All 146 previous implementation entries matched at entry. This increment changes four production files (`streaming.py`, `nexus.py`, `history.py`, `recovery.py`) and adds `test_stream_item_semantics.py` / `test_stream_item_persistence.py`. The final 148-file manifest `implementation-source-final.json` has SHA-256 `dddd8f3d8aa96ca7cc539b8426726bcd1ffa71df8778f5cbdacea86fac9bfa2d`; entry/final source copies and a diff against this batch's entry separate inherited changes from this work. Source hashes remained stable during the final affected verification.

The final affected selection (`correction.xml`) passes **344 cases**, zero failures/errors/skips: all 236 new cases, all 77 accepted-evidence-recovery cases, all 29 recovery-diagnostic cases and both unknown-outcome Continue controls. The earlier larger selection (`final.xml`, before the diagnostic identity repair) is **779 passes, three failures and one setup error across 783 cases**. Its passing controls include both protocols' parser/termination, R13 transaction rollback/own-child exit, provenance/corruption, R02 immutable chunk/durable suffix, normal/compaction, failed-Continue, separate handoff/domain gates and synthetic source-led delivery. Those results remain separate; the final correction reruns every changed history/diagnostic consumer and new case, rather than claiming one final 783-pass run.

Meaningful failures remain available:

- `red.xml`: all 22 selected status/role counterexamples fail before the fix, including terminal replacement/omission and message-carrying lifecycle snapshots. The later cases distinguish same received bytes at whole/one-byte/17-byte UTF-8/JSON/SSE cuts from independently permitted delta segmentation and interleaved calls; arbitrary event reordering is not a positive case.
- `green.xml`: 208 pass/four failures. The new positive reasoning-only fixture violated the existing no-text/no-tool gate. Adding a valid companion function retained opaque reasoning and preserved that gate.
- `history-red.xml`: one pass/one failure confirms the previously resolved-history bypass. `focused.xml` then passes 219 with one diagnostic expectation failure. The new assertion incorrectly expected a blocked primary projection while that implementation only retained an unavailable historical entry; the existing missing-evidence regressions later demonstrated the identity loss, which was repaired in code.
- `regression.txt` is an interrupted run under the first overly broad local network guard. `diagnostic.xml` (38 pass/one failure) identifies Windows asyncio's internal `socketpair` as the blocked call. The repaired runner permits only that internal loopback construction; ordinary sockets and real HTTP transports still fail. This is isolation-harness evidence, not parser or route evidence. `repaired-runner.xml` retains 235 passes/one new diagnostic-expectation failure before the proper identity repair.
- `final.xml` preserves three existing diagnostic failures for missing native/raw/staging evidence; existing tests were not changed. The final fix reads structural diagnostic identity separately and checks current compatibility before ready/reuse. The setup error was `WinError 5` while renaming a seed version's `.prepared` directory before the stream test, not a model-triggered edit. `setup-error-result.json` and the original workspace retain its failure, candidate and prepared files. Both affected Continue cases pass in the final selection. OS cause is unconfirmed; no unrelated automatic storage retry was introduced. Revisit under R02 if it repeats or affects delivery.

New integration cases verify initial/save/reopen results in normal and compaction requests, zero accepted publication or domain effects for rejected streams, and exact received bytes/raw/assembled/staging/request/attempt linkage. Reopened reconciliation cannot obtain credentials or dispatch. Valid Runtime replies contain domain-schema-correct `edit_document` and `report` arguments: settlement failure after the request UPDATE rolls back both records, accepted publication before graph checkpoint is reused, and a committed edit before tool checkpoint is not repeated. Each yields one mock dispatch, one new immutable version, stable prior receipts/frozen input and retained attempts/time/unknown usage. Contradictory Runtime replies cannot delete source content; a separate synthetic ordinary Continue records one receipt and creates one accepted successor without replaying or changing the rejected request.

The actual saved/reopened/exported artifacts are compared against generated source PDFs: complete paragraphs and 25 mg survive Markdown/JSON/HTML/ZIP, every package member matches the selected saved version, source-image bytes match their evidence and decoded page pixels match an independent source render. The saved Markdown and representative PNG were manually viewed in `artifact-review/`. These are scripted synthetic deliveries, not natural agent evidence selection or fourteen-page Nursing fidelity.

Earlier A evidence is reused only for unchanged desktop/build presentation and its historical exercised scope: the prior final 180-case selection and desktop results do not validate these new counterexamples. The earlier 622-case run remains 618 pass/four assertion failures with a separate 143-case correction, as recorded in its own entry. No UI/type/build boundary changed here, so no additional UI build or installation was performed. R01/CTX calibration, R02 controlled performance, R03 arbitrary local effects and broader R07 remain deferred with their existing conditions. No true route, model usage/fees, installed readiness or arbitrary OS/power-loss guarantee is established. Stop after this finite local closeout; the next product decision is a separately authorized bounded real-route/fourteen-page interval with fresh actual-state/request/allowance preflight and explicit exits.

### A implementation mechanism (2026-10-30)

The selected implementation keeps the existing HTTPX 0.28.1 transport, attempt-local decoder, native parser and StateGraph lifecycle. No SDK or dependency changed. Official CC/Responses event references above and [HTTPX asynchronous streaming/closing](https://www.python-httpx.org/async/#streaming-responses) were retrieved during implementation. Protocol meanings inform the rules; finite supported output forms, single-choice attribution, service-update tolerance and complete-before-tools are app policies. No route mapping or model-specific branch is introduced.

`StreamDecoder._chat` binds observed `id`, `model` and `created` separately from service observations. Non-null identity strings must be nonempty; created values must be nonnegative integers excluding bool. Responses also checks observed response ID, model/created_at and item/call attribution. Omitted per-event identity does not invent a replacement. Existing request/attempt ownership and archive provenance remain authoritative even when a provider field is absent. Tool IDs are unique within the complete native batch; arguments must be a complete finite JSON object, never a prefix or cross-attempt concatenation.

For `service_tier` and `system_fingerprint`, absence leaves state unchanged. Explicit null publishes an unknown observation. Fingerprints are nonempty strings; the supported tier vocabulary is `auto/default/flex/scale/priority/fast`. Other types or unknown tier values yield derived null with an unavailable observation, not a default. A later interpretable observation can update that state. The decoder records field/status/event ordinal; exact values and transitions remain in raw SSE, and assembled artifacts link that source. Responses applies these service rules across response snapshots and carries the last explicit state into its derived completion. This is app tolerance, not proof of route conformance.

The event classification is finite:

| Family | Current treatment |
| --- | --- |
| `response.created`, `response.in_progress`, `response.queued` | Observation-only lifecycle; any supplied output content/identity and error/control state still undergo validation. No generation progress merely from status. |
| `response.output_item.added/done` | Bind item identity/type/call attribution; retain observed text/arguments and verify completed items against completion. Opaque reasoning remains native. |
| `response.content_part.added/done`, `response.reasoning_summary_part.added/done` | Validate the applicable part type, index and observed prefix/full value. A done part, including its observed annotations, cannot change or disappear. Optional announcements are not required. |
| `response.output_text`, `response.reasoning_text`, `response.reasoning_summary_text`, `response.function_call_arguments` delta/done pairs | Preserve additions, bind part/item ownership and verify full values. A done suffix can establish previously unseen progress; repeated snapshots cannot. Custom-tool input can be reconstructed but remains unsupported for native execution. |
| `response.refusal.delta/done` or refusal parts | Reject immediately; omission by a later snapshot cannot erase the observation. Unsupported message/reasoning/summary parts also reject. |
| `response.output_text.annotation.added` | Bind annotation index and check its exact value against the terminal part. It does not reset generation waiting. |
| `response.compaction.compacting` | Documented observation-only signal, bound to its compaction item. It neither resets waiting nor authorizes the unsupported provider-native compaction output form. |
| Error and failed/incomplete/cancelled state; `response.completed` | Error/control state cannot disappear. Only consistent completed native output is terminal success; CC separately requires finish plus dispatched `[DONE]`. |
| Other event types | Explicit unsupported-semantic rejection, with raw retained. No name-prefix, object-shape or live-sample admission heuristic. |

CC distinguishes known competing choice containers (`message`, `text`, `content`, `refusal`, `tool_calls`) from `delta`. Absent/null/empty containers and a neutral assistant role carry no competing payload; populated containers reject. Unknown non-null delta fields remain unsupported. Additive envelope metadata does not replace required semantics; raw bytes preserve additions. This is more specific than accepting or rejecting every unknown property.

`usage.py:interpret_usage` returns `Usage(value, status, reason)`. Status is complete, partial or unknown; reasons are fixed local codes such as count, total, subset, container and missing. The nullable accepted `usage` mapping contains only recognized native accounting fields; unknown metadata remains in raw evidence. Present recognized count fields may stay null; missing counts remain absent, with no synthesized zero or total. A complete main triple must add up. The same helper serves streaming and non-streaming `parse_reply`.

Accounting detail recognition is protocol-scoped. The [CC usage schema](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events) defines input cached/cache-write/audio/image/text counts and output reasoning/audio/text/accepted-prediction/rejected-prediction counts. The [Responses usage schema](https://developers.openai.com/api/reference/resources/responses/methods/cancel) defines input cached/cache-write counts and output reasoning counts. Each recognized count is checked against a present parent without adding overlapping subsets. A field from another protocol's vocabulary remains additional raw metadata rather than receiving an unsupported numeric rule. These finite sets were checked against current official guidance during the final contract cross-check, with dedicated positive/negative and persisted controls.

For Responses, [the documented cache-write breakdown](https://developers.openai.com/api/docs/guides/prompt-caching) additionally defines `cache_write_tokens_details.ttl_30m_tokens/ttl_12h_tokens`. These are nonnegative integers excluding bool, individually bounded by a present write count; when both lifetimes and their parent exist, their sum must match. Documented read/write counts are non-overlapping and cannot together exceed present input tokens. A partial breakdown stays partial rather than inventing its parent or missing lifetime. These checks validate relationships, not a second summation or bill calculation. Unknown additional detail fields are excluded from numeric rules and remain accessible in originals.

CC compares recognized accounting fields across aggregate reports. Equal reports do not accumulate; unrelated metadata is not a conflicting aggregate. An unusable report or conflicting aggregate makes validated usage unknown for that stream, even if a subsequent report looks valid. Absence/null does not supply new counts. Responses uses its completed snapshot; earlier reports remain original SSE evidence rather than settlement. No unconditional accepted-projection key was added: diagnostics recompute helper status/reason on demand. Thus exact comparisons change only when actual derived values change.

`acceptance.py` and resolved `history.batch_reply` already reparse native bytes through the common parser and compare the whole saved projection. They now consume this interpretation without rewriting stored projections. `Nexus._settle_accepted` maps unsupported/inconsistent saved inspection to `accepted_evidence_conflict`; transaction-race validation and atomic R13 publication remain intact. Synthetic old unvalidated usage stops with originals/counters/tool facts unchanged. Ordinary historical reads remain distinct from resolved-history revalidation. No legacy decoder or migration was added. The touched stream/native container boundary translates malformed structures into a safe rejection; it is a bounded R07 treatment, not general R07 closure.

`receive_diagnostics.safe_receive` restricts enum values, finite nonnegative numeric facts and known HTTP status shapes, as well as keys. Unsupported CC finish strings become the local `unsupported_finish` terminal classification; native parsing still refuses them. `StreamError` supplies local category/field/stage/ordinal; the UI displays these bounded validation coordinates. Native parse failures use a local native-stage diagnosis. Deliberate raw evidence keeps arbitrary upstream strings. Diagnostic usage entries label native raw JSON, observed raw SSE and derived assembly separately, with on-demand validated status/reason; attempt publication remains a different fact and no entry asserts billing. Unknown usage does not hide the raw report.

Local checks and their exact source identity belong in CURRENT_STATE and the handoff. This implementation does not accept the original missing-DONE raw, establish live-route compatibility, perform real Continue, explain the old non-streaming 180-second stop, rebuild an installed distribution or complete fourteen-page product delivery.

## Accepted-result settlement

The [R13 follow-up](../../reviews/RUNTIME_FINDINGS.md#r13-follow-up-terminal-acceptance-and-reopened-validation-differ) corrects a reproduced first-send/reopen mismatch. Both now use `StreamDecoder.finish_received()` after feeding all actually received bytes. Natural EOF is a separate transport observation. The review owner retains the pre-fix trigger, failed file Stores, implementation evidence and limits; the rule below explains the effective behavior.

### Received-prefix completion rule (2026-10-28)

First reception and saved replay use one decoder receive-boundary operation. This boundary describes all bytes actually delivered by HTTPX, not natural HTTP EOF. Before terminal, existing strict framing, identity, JSON, content and native/tool checks remain. CC still needs the finished choice plus a blank-line-dispatched `[DONE]`; Responses still needs its consistent `response.completed` snapshot. EOF cannot complete an unfinished terminal frame. After feeding the **entire received chunk**, a complete terminal permits local close only after checking the decoder's remaining state:

- Blank lines and fully consumed SSE comments are harmless. A remaining line starting with `:` is also harmless **if every received UTF-8 character is complete**: no possible continuation of that line can turn it into data. Retain its exact bytes, without adding a newline or claiming a complete frame.
- Preserve existing SSE handling of complete non-data fields (`event`, `id`, `retry`, unknown fields): without data they dispatch no native content and do not reconnect. An unfinished non-comment line is rejected; it may still become a data field. Pending `data` is rejected even when the JSON or field value is complete or empty. A blank-line-dispatched extra data event, including another terminal, is already rejected by the decoder. A comment following pending data cannot conceal it.
- UTF-8 characters may span chunks before the stopping boundary. Invalid UTF-8 or an incomplete character at the boundary is rejected, including within comments. The client does not read another chunk to complete a suffix after terminal. Complete non-comment Unicode in an unfinished line remains an unvalidated field and is rejected. No raw bytes are dropped, replaced or normalized.

Both natural EOF and deliberate terminal stop use this same received-prefix rule. Natural EOF without terminal remains unknown; malformed framed data remains rejected. Never infer that later transport chunks were received, persisted or validated. Chunk cuts can change the actually delivered prefix when the client stops; equal stored prefixes must have equal conclusions. Protocol completion alone is not native acceptance: save raw/candidate evidence on rejection, validate the full native reply before staging acceptance/tools, and apply the independent compaction handoff gate afterward.

Reopen verifies ordered immutable chunk identity/hash/provenance and the aggregate, then runs the same semantic operation and compares native bytes. Normal send uses the already fed decoder and existing strict archive verification, without an additional constituent-file pass. R13's short atomic/idempotent request/attempt transaction and R02's chunk durability/cursor/handle are unchanged. This separates disk verification reuse from semantic validation; it requires neither a storage migration nor journal/segment/cache redesign.

Historical staged or published acceptance with an unfinished **valid comment** can be reused after full linkage/native validation, repairing a missing pointer/attempt through the existing transaction. Previously accepted pending data, unfinished non-comment lines or incomplete UTF-8 report `accepted_evidence_conflict` and retain all raw/native/staging/pointer/attempt/usage/time/tool facts. Runtime uses its normal controlled-stop path to expose that reason and retain committed tools; it does not advance the pending batch. Neither clearing acceptance, undoing tools, inventing an attempt nor automatic resend is permitted. No raw-only terminal is promoted. Other corruption/provenance checks remain strict; an invalid historical result requires a separate explicit recovery decision. Actual verification and its limits belong to the review owner and CURRENT_STATE.

Rationale and official scope: [WHATWG SSE parsing](https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream) and [interpretation](https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation) define UTF-8, colon comments, literal fields and blank-line dispatch. Browser EOF discards pending data; this executable-response validator deliberately rejects such unresolved received content instead of discarding it. Accepting a recognized comment prefix is the narrow application extension for deliberate close. [HTTPX async streaming](https://www.python-httpx.org/async/#streaming-responses) and [the installed 0.28.1 source](https://github.com/encode/httpx/blob/0.28.1/httpx/_models.py) distinguish decoded `aiter_bytes` from raw transport bytes and require eventual `aclose` for manual streaming. These sources were retrieved on 2026-10-28; they justify framing/receive lifecycle, not any Nexus route's actual suffix behavior. Existing protocol terminals remain project contracts, with no new provider capability claim or call.

`Nexus._settle_accepted` owns publication for normal send and local reconcile. It repairs both a missing request pointer and an already published pointer whose attempt was left unfinished by the earlier two-commit implementation. Changing only write order would move the partial-publication window. Independent send/reconcile patches would duplicate ownership, diagnostics and replay rules. One short catalog transaction now settles both metadata records, after immutable acceptance evidence has been saved. This is the bounded R13 correction, not an event journal or a transaction spanning files and graph checkpoints.

Evidence preparation precedes `BEGIN IMMEDIATE`. The deterministic `accepted:<request>` blob must have the right kind, task, request, unique member attempt and finite original `received_at`. The frozen-input descriptor/bytes, native descriptor/bytes and exact parsed accepted projection must agree. Legacy acceptance requires a complete `native_response`. Streaming requires a complete `raw_stream` linked to a complete `assembled_response` of the frozen protocol, both owned by the same request/attempt. `registration_only` partial preservation is ineligible. Reopen strictly verifies chunk order/files/checkpoint/aggregate through `read_stream`, replays the attempt-local decoder, compares the assembled native bytes and validates the parsed accepted projection. It never manufactures acceptance from terminal SSE or raw bytes alone. Normal send reuses only its freshly archived, strictly reconstructed stream descriptor to avoid a second constituent-file pass; descriptor equality and native/staging validation still apply. No file reads or decoder reconstruction occur inside the write transaction.

Inside the transaction, task-scoped row reads recheck current request/attempt IDs, member identity, eligible states, frozen route/input/replay fields and validated evidence/observation descriptors. A change between validation and publication is an explicit conflict, with no metadata writes. Publication merges only acceptance fields into current records so newer unrelated fields survive. Before publication, request diagnostic pointers may legitimately refer to an earlier failed attempt on this request; their field-specific kind and ownership are checked even when their descriptors were already loaded. Acceptance replaces these earlier diagnostic pointers while retaining their original blobs. A different pointer on the accepted attempt is a conflict; once the accepted pointer exists, conflicting native/stream pointers are also rejected. A different attempt's usage or a known contradictory usage/status/stream reference is never silently overwritten.

| Field | Authority and re-entry rule |
| --- | --- |
| Request `status`, `accepted_ref`, `response_ref`, applicable `stream_ref` | Validated accepted/native/stream identities, published together with the selected attempt. Frozen payload, replay policy, attempts and other current fields are preserved. |
| Attempt `status`, `usage` | Accepted staging must equal a fresh complete-native parse. Only its actual member attempt becomes accepted. Known prior usage must agree; missing known usage is filled; native unknown remains null. No budget or usage total is incremented during settlement. |
| Attempt `finished` | Fill a missing/null value from staging's original `received_at`. Preserve an existing finite historical finish time, including the older send-time value after staging. Never use reopen time. |
| `http_status`, `transport` | New staging retains the settled receive observation, including legacy non-streaming cleanup/deadline diagnostics. Older staging can use its same-attempt `stream_receive` observation. Existing settled diagnostics must agree with the available authority. Absent legacy diagnostics stay absent/unknown; acceptance does not invent HTTP 200 or cleanup success. |
| `started`, `remote_cancelled`, unrelated fields | Preserve current values. A missing cancellation value is recorded as unknown, never inferred from local completion. Other attempts and their unknown usage/cancellation remain untouched. |

Staging captures `received_at` with the sender's wall clock after complete native validation. It records the original acceptance-staging moment. Transport observations separately retain body/protocol elapsed timings. Recovery reads these saved facts; it makes no new measurement of the original reply's arrival or remote completion.

| Saved state | Recovery outcome |
| --- | --- |
| Complete valid staging, no pointer | Validate and atomically publish request plus its attempt. |
| Complete valid staging and pointer, attempt still `in_flight`/unknown or missing known usage/finish | Validate the same chain and repair that attempt, even though the pointer already exists. |
| Fully settled matching records | Return the same accepted result; do not write either record again or refresh time/usage. |
| Conflicting pointer, staging, member attempt, native/stream chain or known usage | Refuse explicitly; preserve files and current metadata for diagnosis. |
| No accepted staging/pointer, only complete-looking raw or terminal SSE | No acceptance is synthesized; the original frozen replay/unknown-outcome gate remains effective. |

The historical counterexample is staging → request-pointer commit → interruption before attempt commit. The old reconcile skipped this state forever because its repair gate required a missing pointer. The new common responsibility does not use that gate. An exception or abrupt own-process exit after the first metadata UPDATE now leaves both metadata records unpublished; independently committed staging remains available for later repair. A separate Runtime handoff validation is still necessary for compaction; native acceptance alone neither adopts context nor dispatches compaction tools.

This uses existing Python 3.12.14 / SQLite 3.53.1 and `Store.transaction`, without dependency or framework changes. Consulted official [Python 3.12 transaction control](https://docs.python.org/3.12/library/sqlite3.html#transaction-control) and [SQLite transaction semantics](https://www.sqlite.org/lang_transaction.html) support explicit transaction/rollback and current reads under `BEGIN IMMEDIATE`. Catalog atomicity does not imply file/graph atomicity or power-loss safety. [R13](../../reviews/RUNTIME_FINDINGS.md#r13--accepted-result-settlement-consistency-selected-2026-10-28) owns evidence and limits.

## Historical conflict recovery implementation

The [selected recovery design](../../design/ACCEPTED_EVIDENCE_RECOVERY.md) owns semantics; [CONTRACTS](../contracts/20261031_0157_CONTRACTS.md#historical-accepted-evidence-local-recovery) owns the public boundary. `acceptance.inspect_acceptance()` performs the shared no-write immutable/metadata check used by Nexus settlement and recovery diagnosis. Publication remains in Nexus; classification and human selection remain in `recovery.py`. The checker returns the parsed staged projection, attempt, evidence descriptors, receive-boundary status and reconstruction facts. A saved reply rejected only by `finish_received()` can be eligible historical evidence without becoming newly accepted. A feed-time failure or a known metadata disagreement cannot use that action. Fresh sends pass their already validated archive to avoid repeating full constituent-file reconstruction; reopen still verifies all durable bytes.

### Read-only observation and evidence identity

D01/D02 separate subject selection from factual projection inside that same read-only snapshot. `select_subject` gives an explicit pending or actually frozen current request precedence over historical decisions, including when it has no staging. With no newer request, `recovery_boundary` requires the exact committed successor and coordinate scheduling plus the existing parent-lineage proof; later progress/completion leaves only labeled historical summaries. The projection routine still recognizes later descendants for idempotent mutation reentry. This stricter diagnostic readiness rule changes no graph projection or Continue/replay authority. Multiple decisions are matched by identity and relationship, never the last row in catalog order.

`diagnostic_facts` supplies original publication/status/usage/finish, saved usage, exact evidence and operation refs, current head/versions and the separate historical `resolution_head`. Original recorded facts are checked now; committed saved/native/raw/operation semantic validation is qualified as verified at resolution. The existing receipt/history readers verify authority and pairing and direct byte checks establish present availability without claiming another complete constituent-stream audit. Known missing references and inconsistent scope remain explicit; required failures prevent a fresh ready claim. A failed snapshot interval discards its apparent ready result. The [design owner](../../design/ACCEPTED_EVIDENCE_RECOVERY.md#d01d02-implementation-and-rationale-2026-10-29) owns the complete algorithm, alternatives and acceptance matrix; the API/UI guide names actual response fields.

Each native/raw reference now additionally validates its own descriptor task/ref, applicable kind, request, uniquely retained attempt membership, matching attempt record and present bytes. Receipt-linked descriptors must still match the committed descriptor exactly. An inherited request pointer, including one copied into a newer attempt, establishes no ownership by itself. The projection keeps the selected attempt separate from each reference's confirmed actual owner and relative retained-attempt relationship. An earlier partial raw remains partial and accessible; it cannot supply the newer attempt's receive observation or accepted reply. An unconfirmed reference disables its own link and contributes a required fact error without erasing independent facts. The selected attempt's recorded transport byte count is displayed separately from corresponding retained-evidence availability; absent observation is never synthesized as zero. The response schema and rendering are explained in the [API guide](20261031_0157_INTEGRATION_AND_MODEL_BOUNDARY.md#local-saved-acceptance-diagnosis-and-recovery-api).

The explanatory reason list evaluates the same three predicates independently: supported finish boundary, no unknown effects and no required fact errors. It does not infer unsupported receive evidence merely because a head check failed, or hide one failure behind another. This changes diagnostics only; selection, acceptance, Nexus send/replay, effects and A/B/C publication/projection remain as before.

The on-demand diagnostic opens no original database through SQLite. A real file-backed negative showed that `mode=ro` may create original `-wal`/`-shm` sidecars. The reader instead copies `catalog.sqlite`, `graph.sqlite` and present WAL files to a private temporary directory, keeping the source bytes and mtime identities. It rejects unsupported rollback-journal state, uses read-only SQLite connections to those copies, and compares original identities across the inspection interval. SQLite interprets the copied WAL; the app does not implement a WAL parser or ignore it with `immutable=1`. A changing interval exposes no executable choice. Immutable evidence bodies remain read from their verified source object paths. Temporary files are isolated and removed by their own lifecycle, never by deleting source evidence.

An existing executor lock can be probed/held through a read-only file descriptor without creating a task lock. A missing lock is checked again after observation; Engine also rejects its own active future. The consistency guard compares every main-database byte and every nonempty WAL byte. Mtime-only changes and creation/removal of an empty WAL contain no changed SQLite page/commit, so normal polling housekeeping does not invalidate identical durable bytes. Timestamp metadata is captured but is not transition authority. Changed durable bytes still make the view unavailable; actual mutable facts are rechecked at commit. The installed SQLite saver normally performs setup even during reads, so the narrow `ReadSaver` overrides that setup with SELECT-only checks of supported columns. It uses LangGraph `get_state` with the same compiled topology and nonexecuting node stubs. Missing graph, unsupported schema, busy task and stale snapshot have named outcomes. Neither Store/Runtime initialization nor Nexus/Dispatcher reconciliation, events, credentials or transport are part of diagnosis.

The first selection's `basis` hashes the current job catalog descriptors/facts and exact graph checkpoint/values/scheduled successor. Inert recovery-candidate rows are excluded because they have no authority. This is a stale-selection guard, not execution permission. `ReadView` binds both required and optional catalog reads to the task, including context and handoff receipts. Matching JSON fields do not excuse a foreign catalog row. Pending context must have a readable supported proposal relationship, and request kind must agree with the scheduled graph phase. `history.resolution_receipt` separately checks the committed authority's task/request/ref/choice, receipt descriptor kind and identity, basis linkage and original request/attempt equality. That one reader serves diagnosis, history and graph replay. The UI separately reports original publication, saved usage versus original unknown/known usage, native reconstruction, receive-rule conflict and effect certainty. A metadata disagreement does not erase already established byte/reconstruction observations, while an unknown operation/context association is not labeled verified provenance. Parser limitations are not reported as physical disk corruption.

### Prepare, catalog commit, graph projection

For K, **A** writes unique `recovery_candidate` objects. None has the authoritative `result:<op>`, context-outcome or `conflict-resolution:<K>` identity. Even when a previous A exited, old candidates neither settle a skipping operation nor block a changed-basis retry. Diagnosis can identify relevant uncommitted candidates and explains that no decision exists yet.

Before **B**, the caller holds the task mutation lock, rejects a live executor, rechecks the graph and validates every required operation. Call identity includes ordered index, name, exact authored argument bytes/hash and candidate/result ownership. A done flag or nominal blob alone is insufficient. Recognizable saved results must match their retained effects; document edits require the original atomic operation receipt, registered version, candidate/parent/source relation and package hashes. A verified staged result can repair only operation metadata. Started-but-unconfirmed effects remain unknown, including nominal done records without a proven result. A generic script/OCR/preview process error without retained completion/effect evidence cannot establish a completed process; the first version blocks that case rather than guessing from the error string. No tool executes to discover its outcome. Prior skipping keeps its amendment reason; genuinely unstarted calls receive `ok=false`, `skipped=true`, `execution=not_started` with the recovery reason.

B is one short catalog transaction. It rechecks current job/operation/context/request/attempt rows and evidence descriptors, publishes all final aliases and paired operation metadata, linked context dispositions and the single `conflict_resolution[K]` authority together, or publishes none. Every publication target also receives a SQL-row task-ownership check: the per-task basis cannot detect a foreign task's colliding primary key, even if its JSON happens to agree. Such a collision aborts the entire transaction. Disk replay, network and graph updates occur outside it. It does not nest `event_once`; no event grants recovery authority. The immutable receipt records original acceptance/usage/time facts, all disposition refs, the exact graph basis and a successor computed once. Original request/attempt records are never rewritten, including staging-only acceptance gaps. Known completed effects are retained without another execution.

For **C**, supported `graph.update_state(..., as_node="tools")` schedules coordination without executing a tool node. `State.resolutions[K]` carries the authority ref. Projection accepts the exact saved source checkpoint, or proves a marked successor with that source parent, exact expected state and coordinate scheduling on the current lineage. Later descendants retain the same marker; counters alone are insufficient proof. An unexpected branch stops explicitly. Reentry uses the recorded patch, never recalculates increments/appends, and never rolls back newer history, head, instructions or settings. After B, the canonical receipt is read in one catalog transaction and graph lineage in a pinned read-only SQLite snapshot. This explicit mutation path may permit SQLite sidecar bookkeeping; it still checks existing graph/schema before Runtime initialization and cannot create a missing graph. It does not copy the polling catalog or compare newer mutable job facts with the old first-choice basis. An already-projected duplicate returns its original outcome without Runtime construction. Temporary storage-view failures report a conflict with any committed choice retained. A duplicate POST after later progress still locates K's original authority. Runtime finishes committed projections before `resume_pending` can reconcile K. An unresolved projection can be finished locally without a model credential; ordinary Continue is a separate action.

Normal N appends K once and increments normal sequence/revision once. C1 verifies the historical handoff receipt/archive, covered prefix, original refs and resolution refs against the frozen revision, then restores that transition without another capacity judgment or normal sequence increment. C2 retains old history/handoff and uncommitted candidates, advances revision only and executes no unexpected compaction calls. Context restores only proven committed policy effects and exact settlements; uncommitted K intent requires explicit reselection, preserving complete/incomplete candidates and prior settled dispositions. Related superseded ancestors do not revive; unrelated pending intent remains for normal coordination. Old report receipts/claims/versions remain, while report/terminal control is cleared for re-planning. Only the repair episode consumed by the transition is removed. Stop, total budgets, consumption, active time and unrelated repairs are preserved.

The [context guide](../../guides/CONTEXT_AND_EVIDENCE.md#resolved-historical-batches) explains paired model history, full source access and cost accounting after recovery. Official [LangGraph checkpointer/state update guidance](https://docs.langchain.com/oss/python/langgraph/checkpointers), the installed LangGraph 1.2.16 / SQLite saver 3.1.2 implementation and [SQLite WAL guidance](https://www.sqlite.org/wal.html) informed these boundaries. No dependency upgrade, generalized R03 effect recovery, R07 parser repair, journal/cache migration, telemetry framework or real Nursing action is included. CURRENT_STATE owns actual local acceptance and remaining limits.

## Implemented task settings and active time

Phase 2 addresses two observed failures: an existing task ignored explicit allowance/capacity changes, and a stale execution timestamp charged all offline time as active work. [The Q3 contract](../contracts/20261031_0157_CONTRACTS.md#existing-task-settings-and-active-time-accounting) owns exact fields and semantics. The implementation retains the single-writer graph, frozen requests, exact originals and autonomous tool selection.

`Engine.configure` and Start/Continue share `_configure` under the cross-process task lock. A short catalog transaction validates the full merged settings, restricts changes after a request is frozen, records the before/after values, and writes the job. A failed validation changes nothing. The task's consumed attempts/time and saved work are not part of the settings patch. The Electron **Task limits** form submits explicit task values; Start uses global connection defaults only when that task has no route. This avoids silently reverting a saved per-task increase on the next Continue.

The later option-A increment adds an explicit request deadline to this same path. Its effect lasts for subsequent newly frozen requests in the task, including normal and compaction requests; no one-off override or global default update is involved. For example, saving 600 seconds leaves an old 180-second unknown request unchanged. Ordinary Continue still respects that old replay gate. A separately authorized exact-request recovery records its existing continuation choice, then prepares a new request with 600 seconds. Saving settings alone performs no inference and does not reset consumed time, attempts or correction episodes.

Nexus retains header status and bounded receive observations even when a later body wait fails. This distinguishes local total-deadline expiry, HTTP errors, client timeout classes, Stop and budget exhaustion without inferring upstream causation. Full HTTP-body receipt, valid native output, valid handoff application and correct saved conversion remain separate stages. [Q3](../contracts/20261031_0157_CONTRACTS.md#existing-task-settings-and-active-time-accounting) owns the fields, partial-body privacy boundary and hard-termination limits. Existing automatic handoff corrections are unchanged: a future one-request diagnostic experiment must explicitly stop at its agreed boundary rather than assume invalid handoffs already stop automatically.

Three values must remain distinct: the task's latest capacity for future input, a pending request's original frozen route/input, and total task allowances. For example, raising context capacity from 65,536 to 131,072 changes the next newly prepared request, while an already prepared request keeps its original 65,536 configuration and exact payload. Raising total requests from 1 to 10 preserves the first consumed attempt and does not expand that request's original replay ceiling. `Nexus.freeze` snapshots replay policy; `send` reads that snapshot for replay eligibility and current job totals for whole-task admission. Existing pre-snapshot records retain the now-immutable task recovery policy. Supported settings changes cannot reopen an exhausted correction episode or unknown local effect.

`ActiveTime` measures a running invocation with `time.monotonic()`. It saves known elapsed deltas and a wall observation together at request/preparation/tool boundaries and at one-second intervals during network/child-process polling. Each budget gate also includes the current unsaved monotonic delta. A clean exit saves the remainder. There is no background scheduler or separate heartbeat thread. Wall times identify observations; they do not measure current execution duration. The wall marker is sampled alongside the monotonic reading before persistence, so time spent waiting for that transaction remains in the next measured delta or unknown crash tail rather than falling between the two observations.

Suppose a task has 17 recorded active seconds and restarts 10,000 wall seconds after its last durable observation. It keeps the 17 seconds and records an unknown interval between those observations, with `active_seconds=null`. It does not charge 10,000 seconds or label the interval zero. The next run adds its own measured time. Its budget is explicitly **known-active-only**, and UI/API show the unknown interval separately. This keeps normal continuation usable while acknowledging that a hard kill during an uncheckpointed operation may lose the exact active portion of that tail. It does not guarantee a strict all-time work limit, zero remote cost, or remote cancellation. Backward wall-clock adjustments remain visible as a signed wall span, without reducing known consumption.

Checkpointing time and replacing an interrupted marker use catalog transactions, independently of graph checkpoints. An interrupted transaction cannot both increment a total and leave its old accounting cursor committed. Likewise, recording an unknown interval and replacing its marker is atomic. The existing task lock supplies ownership; no new cross-store atomicity claim is made.

Official guidance consulted before this implementation: [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) distinguishes graph checkpoints from application data; [Python 3.12 monotonic time](https://docs.python.org/3.12/library/time.html#time.monotonic) defines the in-run elapsed clock; [React state](https://react.dev/reference/react/useState) supplies the dialog's local form state. Dependency pins and the supported graph lifecycle are unchanged. [CURRENT_STATE](../../CURRENT_STATE.md) owns verification results and unresolved scope.

## Implemented streaming receive persistence

The R02 integration selected on 2026-10-28 retains `Store.blob` and its content-addressed immutable files. Every nonempty decoded HTTP-body chunk is registered as `stream:<attempt>:<index>` with request, attempt, zero-based index and receipt elapsed time before interpretation or progress advancement. New files are flushed/fsynced before the FULL SQLite registration commit; identical content can reuse a physical object while keeping separate chunk identities. Stop/budget control still queries current job data after persistence. Decoder/progress observation follows. No timed flush, memory-only durability or batch of uncommitted chunks is introduced.

`stream_receive` replaces its growing reference list with a fixed-field `cursor`: format `ordered_chunks_v1`, durable `chunk_count`, `bytes`, incremental prefix `sha256` and `last_chunk_ref` (null for zero chunks). Field count and digest size are constant; numeric encodings grow with their value, rather than with a reference list. Transport fields still describe observed receive/protocol/progress facts. The cursor records the durable prefix known to that checkpoint; it is neither an accepted-response marker nor an instruction to discard any later durable records. Received, registered, checkpointed, native-validated, handoff-validated and published are separate facts.

The cursor-only prototype removed cumulative list serialization but retained essentially all elapsed cost. The selected second variable is `Store.connection_scope` around the synchronous Nexus exchange, including HTTP cleanup. It owns one thread-confined SQLite handle with `synchronous=FULL`. `transaction` still issues BEGIN IMMEDIATE and commits each blob registration and each observation separately. Fresh SELECT statements read current Stop/budget state; neither job data nor read transactions are cached. Nested scopes reuse the owner; only it closes the handle on every exit. Nested write transactions are rejected before they can roll back their caller. Other threads and Store instances use their own handles. Final archive, native validation and acceptance staging remain outside the receive scope. Reusing the handle avoids repeated connection/PRAGMA/open/close work without making a transaction span chunks. No graph lifecycle or dependency change is selected.

`Store.read_stream(job, request, attempt)` takes a consistent catalog snapshot, checks request/attempt ownership and discovers all deterministic per-attempt chunk records. It orders by numeric identity, requires contiguous indexes starting at zero and matching reference/metadata/job identities, then checks every object's length and SHA-256. It validates the checkpoint prefix's count, byte count, digest and last reference. Legacy `stream_receive.chunks` is read as an exact prefix list; no migration or rewrite is needed. A missing object, index gap/duplicate/wrong identity, bad digest or checkpoint ahead of the durable sequence raises an integrity error. A valid suffix beyond an older observation is retained and returned in full with a separate `checkpoint_count`; it does not acquire decoded/protocol/acceptance status. Absence of a record cannot prove that upstream sent no additional data.

For complete protocol settlement, `archive_stream` reconstructs and verifies this durable sequence against the in-process received bytes before archiving `raw_stream` with `chunk_validation="reconstructed"`. Its final `meta.chunks` manifest is written once. An unaccepted incomplete protocol has a separate preservation path: if cursor count/bytes/digest/last reference match the received prefix, archive those exact bytes and deterministic already committed references with `chunk_validation="registration_only"`. It does not reread every file during Stop/disconnect settlement, and makes no reconstruction/acceptance claim. A cursor mismatch still falls back to strict reconstruction, discovering any registered suffix beyond the observation. This avoids a measured multi-second fresh-file verification tail after the body was already closed; it does not delay chunk fsync/registration. The reader always verifies files/order/checkpoint and published aggregate, regardless of the archive's validation label. A later missing/corrupt constituent is an integrity failure even when the partial raw aggregate is still usable evidence.

The separately saved `assembled_response` links its source stream and attempt. Native validation precedes `accepted:<request>` staging; request/attempt pointer publication follows. Reconcile verifies acceptance blob request/attempt/kind/reference as well as stream/assembled evidence relationships before recovering or returning accepted streaming output. A mismatched stage must not copy a later attempt's usage into an older unknown attempt. Terminal bytes found by `read_stream` alone never cause parsing, acceptance, sending or tool execution. Complete native validation remains necessary for tools; compaction's handoff validation remains an additional later gate.

The reader's `data`, ordered `chunks`, `chunk_count`, `received_bytes` and `sha256` describe its verified durable sequence. In particular, `received_bytes` here means reconstructed durable length, not a claim that the last transport observation caught up. `checkpoint_count` describes the observed prefix and `checkpoint_present` distinguishes an absent observation from an observed zero. Neither missing observations nor missing usage become known zero. Chunk fragments may split UTF-8; exact `raw` evidence reads retain the bytes even when a fragment cannot be decoded alone as text.

Received bytes, immutable chunk registration, the latest observation and complete accepted output are separate facts. An interruption between chunk registration and observation can leave durable chunk evidence beyond the checkpoint; inspect per-attempt indexed records rather than treating the checkpoint as proof that nothing else arrived. Ordinary completion archives the exact aggregate as `raw_stream`, derives a separately identified `assembled_response`, validates the complete native reply and stages acceptance before tool dispatch. Reopen recovers staged acceptance without sending; unaccepted interrupted data remains subject to the frozen unknown-outcome gate. Local Stop says nothing about remote cancellation or final cost. [The streaming contract](../contracts/20261031_0157_CONTRACTS.md#streaming-progress-waiting) owns these boundaries.

[R02's current result](../../reviews/RUNTIME_FINDINGS.md#r02-storage-increment-authorized--2026-10-28) owns prototype/final comparisons, selected disposition, remaining linear costs and evidence limits. Journals, segmented storage, data caches and timed flush remain unselected. File lengths, logical encoded sizes and sampled WAL peaks are not actual device writes. Official references consulted for the installed Python3.12/SQLite3.53.1 behavior are [Python transaction and connection control](https://docs.python.org/3.12/library/sqlite3.html), [SQLite FULL synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous) and [WAL lifecycle](https://www.sqlite.org/wal.html). A Python connection context manager does not close its handle; owned handles are explicitly closed. FULL asks SQLite/VFS to synchronize commits; file fsync and SQLite cannot prove the operating system/device honored every persistence request. Process termination checks do not establish OS-crash or power-loss safety, and the catalog/files/graph remain separate commit domains.

## Implemented continuation boundaries

The 2026-10-24 increment resolves two practical failures: resuming an accepted batch could run an obsolete edit before the model saw the user's new instructions, and Continue after an HTTP/rejected reply could reopen the same permanently rejected request. [Q3](../contracts/20261031_0157_CONTRACTS.md#q3-execution-recovery-and-delivery) owns the exact contract. The implementation keeps the existing graph and separates these cases at entry and tool boundaries:

| Observed durable state | Action and rationale |
| --- | --- |
| Tool has a receipt, including a document committed before graph completion | Recover the same result and any context intent. Preserve useful effects without duplicate commits or rollback. |
| Accepted tool has not started, and amendments changed | Preserve its candidate; settle an explicit unexecuted result under the original call identity. Then let the model decide using the new instructions. |
| Tool started but has no recoverable receipt | Keep the unknown local outcome and files. Do not claim it was skipped or assume no effect. General reconciliation remains separate work. |
| Request was prepared but never attempted, and amendments changed | Retain it and record a new-input transition. Sending known-obsolete unsent input adds no recovery value. |
| HTTP error or complete transport with rejected/truncated native reply; user presses Continue | Retain failure evidence, record the Continue decision and assemble a new request from current state. Never execute a partial call from the old reply. |
| Attempt is unknown/in flight during ordinary Continue or re-entry | Keep the same request and original replay gate. New instructions do not prove the earlier generation never happened. |
| Current compaction is unknown; user explicitly selects Resume context organization | Validate the exact current request under the task lock, preserve it and its unknown cost, then durably authorize one successor transition. This does not change its replay gate or permit automatic repeated replacements. |
| Handoff application receipt committed, but graph completion did not | Recover the original validated transition after matching its prefix/revision and immutable archive. Preserve historical capacity diagnostics; then prepare current input with new amendments/head. An archived candidate alone is not an application receipt. |

`Nexus.reconcile` and `Dispatcher.reconcile` read durable acceptance/result facts before any replacement decision. `instruction_basis` hashes only the ordered human amendments. A normal document save by the agent cannot accidentally invalidate the remaining calls in its own batch. On amendment, all genuinely unstarted old calls receive paired unexecuted results, not just writes. This avoids maintaining a speculative tool-category filter and returns method selection to the model. The app does not reject future equivalent actions that the model chooses under the new instructions.

Skipping itself has a durable intermediate `skipping` marker. A crash after that marker, after its result object, or before graph completion resumes the same skip; it cannot later execute the superseded call. Settled context intents still apply at the pending batch boundary. A historical completion report is preserved but cannot close the new instruction.

Explicit failed-request continuation first saves `continuation:<request>`, including the next revision and diagnostic/reference. Only then does the runtime use LangGraph's supported state update and return through `coordinate` and `prepare`. The stable record covers the gap between the catalog and graph stores without pretending they share a transaction. Feedback reaches both normal and compaction requests. Original attempts/time, correction counts, retained history, saved versions and unknown fees remain intact. New input can still encounter capacity or budget limits.

`Engine.start` conveys the user's Start/Continue action. Merely opening the desktop reads state. Plain runtime re-entry can recover a previously persisted Continue decision but cannot create that decision for an HTTP/rejected reply. This separates deliberate continuation from transparent recovery without requiring routine approvals for normal agent tools.

Stage B exposed a different entry need: a user pause during a compaction with frozen replay disabled. After explicit human adoption, `recover_compaction_request` names that exact pending request. Validation precedes configuration so a stale click cannot add an amendment, clear Stop or recover a later request. Locally saved accepted bytes take precedence. Otherwise the existing `continuation:<request>` identity records `explicit_compaction_recovery`, original payload/attempt references and the next revision before graph advancement. A receipt/checkpoint interruption resumes that same choice; a later unknown successor requires a new explicit choice. Current state is replanned and capacity-checked, so a fitting normal continuation does not force another compaction. Saved documents, active policy, previous unknown records, correction counts and consumption remain intact. [Q3](../contracts/20261031_0157_CONTRACTS.md#q3-execution-recovery-and-delivery) owns the narrow exception, and `tests/test_compaction_recovery.py` plus its desktop fixture verify these boundaries. General normal-request and local-tool unknown recovery are not inferred from it.

Tests in `tests/test_continuation.py` inject the relevant persistence gaps, exercise both native protocols and byte-check preserved delivery. `tests/desktop/continuation-workflow.spec.ts` drives the real Electron/Python path with loopback scripted replies. Its test-only `boundary-hook/sitecustomize.py` delays return from a genuinely settled context tool so the UI can press Stop at a deterministic boundary. The hook is absent from normal app startup. An earlier test interrupted a running script instead: that correctly produced `local_outcome_unknown`, and is not evidence of safe script cancellation/replay. No real model judgment, source-quality benchmark or arbitrary crash guarantee follows from these tests.

<a id="ownership-and-entry-points"></a>
## 1. Ownership and entry points

| Responsibility | Authoritative facts | What another layer may retain |
|---|---|---|
| Nexus request service | Prepared request, actual send attempts, consumed limits, accepted complete native reply | The graph can retain stable references and purpose/status. |
| Accepted-batch executor / dispatcher | Accepted tool-call list, per-operation identity/input, progress, outcomes and necessary completion effects | Graph continuation can project that progress. One receipt cannot represent the whole batch. |
| Document/evidence services | Registered versions, fixed evidence/assets, committed operation results and promised pointers | A checkpoint can reference them, without undoing later committed facts. |
| Graph/context owner | Compact policy projection, proposal/settlement references, processed batches and work continuation | Catalog commits establish context effects; graph checkpoints recover them. Hydrated images/OCR remain transient request content. |
| Export responsibility | Task-scoped chosen version/scope, destination intent, actual publication/results | A model completion statement is one content claim, not proof of package consistency. Another task using the same document must not silently replace this selection. |
| Process/task lifecycle | Cancellation, waiting/stop reason, supervised local attempt state and relevant limits | UI events notify the user. Durable records remain available after reconnect. |

This is an ownership map, not six required modules or tables. One physical database can store several authorities. Two databases did not cause the historical policy-regression bug. Interpreting an old receipt as current state caused it. Co-location alone cannot fix that logic.

The discussion preferred the small graph because a batch-owning node can directly order tools, reconcile progress, and prepare the next input. An illustrative loop is `prepare -> model -> tool_batch -> prepare`, with a delivery/stop assessment after a no-tool response. The implemented graph adds a separate `coordinate` checkpoint before `prepare` so outcome projection does not depend on input preparation succeeding. `prepare` can be deterministic without adding a model call. Semantic compaction is a separate accounted model decision even if preparation invokes it.

Do not assume every invocation, restart, or branch enters through prepare. Framework checkpoint successors or `update_state(as_node=...)` can continue later in the graph. The model-service entry and actual-send boundary must therefore enforce their own identity, budget, cancellation, and accepted-reply checks. There is no hidden second scheduler merely to keep a framework's prebuilt-agent shape.

**Source basis:** EVT-0878, EVT-0942, EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166.

<a id="request-and-attempt-identity"></a>
## 2. Request, attempt, accepted response, and operation identities

One ID cannot safely represent all of the following:

| Identity | Meaning and continuity rule |
|---|---|
| Task / execution context | The authorized work and its durable original allowances. Reopening it does not replenish them. |
| Logical model step | One intended model judgment. Persist a fresh identity for new input or deliberate regeneration. Recovery of the same prepared judgment retains it. |
| Input view / frozen request | The exact selected input plus route/model settings, generation parameters, and tool schemas for that judgment. The view may be resent as several attempts. |
| Attempt | One actual request send and its observed outcome. Consume/record its allowance before sending. |
| Accepted native response | The complete response accepted for that request. Its tool-call list supplies executable intent. |
| Tool batch | The full accepted call list from that response, including ordering/dependencies and progress. |
| Application operation | One accepted effect with stable scoped identity and complete effective input. Recovery reuses it. A different input cannot overwrite it. |
| Framework message/checkpoint | Runtime representation/progress. It relates to the above records but is not a substitute for their causal identities. |

The review rejected `parent_model_request_id == input_view_id` as a universal equivalence. A service can resend one view. A task turn can prepare different views. Accepted replies generate the calls to execute.

A provider `tool_call_id` alone can collide across parent responses. A tuple such as `(thread_id, checkpoint_ns, tool_call_id)` remains insufficient unless uniqueness across its full scope is established. Preserve the accepted parent response relationship and app operation identity. Record the input fingerprint for inconsistency detection.

Likewise `(job_id, checkpoint_ns, model_turn_seq)` describes a straight-line proposal, not all new judgments. A checkpoint namespace is not necessarily a branch identity. A no-tool answer can reach END without incrementing the proposed counter. Later user input can then collide.

Deliberate regeneration can use byte-identical prompts but still be a new decision. A hash of the input identifies content equality, not intent or operation identity. Exact app entry rules must decide when to continue the existing prepared step and when to create a new one.

<a id="request-record-names-and-entry-rules"></a>
### Request records and explicit entry intentions

The source sketches named the durable intended decision `model_step_id`. They used `request_ref` for an immutable request location. They used `request_fingerprint` or `request_sha256` to check its fixed content. A proposed `requests/<model_step_id>.json` layout illustrated external payload storage while Graph State kept compact references. Those spellings and paths are examples.

The fingerprint boundary must include the selected route/protocol/model, generation settings, tool schemas, and actual selected content. Hashing text alone or mutable filenames does not satisfy that boundary. `input_view_id` identifies the assembled view. It relates to step, attempt, and accepted-reply identities but is not interchangeable with them.

ATT-27 made the entry intentions explicit through names such as `resume_interrupted_job()`, `branch_or_regenerate()`, and `append_user_input()`. A resume finds the same prepared step. It reuses an accepted complete reply if present. Otherwise, it reconciles attempts and remaining allowance before any permitted resend.

New user input or deliberate regeneration requires a new judgment and durable step identity, even when the fingerprint is unchanged. The proposed `step_intent="new_judgment_required"` expresses that decision. It does not prove a resumed graph will pass through `prepare_step`. A display `branch_seq`, UUID choice, or counter cannot replace the entry rule. Generalized branching remains deferred.

The prepared request fixes more than text messages. It includes the selected route/model/protocol configuration, generation parameters, tool definitions, required native items, selected content and exact image/artifact versions. Large request content can live in immutable files while graph state retains small references, fingerprints, and compact policy. Re-resolving `latest`, swapping a newer crop, or applying a fresh policy after preparation changes the request. The input assembler selects evidence. Encoding obeys that selection instead of scanning all old artifacts and restoring released images.

Before sending, retrieve any complete accepted reply for the same logical step/request. If present, reuse it and continue its batch instead of generating again. Storing `accepted_reply_id` only in graph message metadata misses the interval where the service saved the reply but the graph did not checkpoint. The lookup needs a durable app step identity that survives that gap.

If no complete accepted reply exists, inspect attempt records. Absence of a reply is not proof the request was never sent. Unknown remote outcome remains possible. Same-ID/different-input recovery is an error to reconcile. It must not silently overwrite the original prepared request.

<a id="hashes-and-identity"></a>
### What a hash proves, and what the operation identity adds

| Check | What equality establishes | What it does not establish |
|---|---|---|
| Raw candidate/reply payload hash | The preserved bytes being inspected are the same retained payload. | Valid syntax, a complete call, or correct PDF content. A parsed dictionary is a separate representation and cannot stand in for original wire bytes. |
| Prepared request fingerprint | The frozen content/configuration/schema being reused agrees with that prepared decision's specified fingerprint boundary. | That two byte-identical prompts are the same intended judgment, or that the earlier attempt was never sent. |
| Effective operation input fingerprint | The tool, target/base, resolved references/defaults, and submitted changes match that operation's fixed input boundary. | That the operation is still eligible to commit against today's head, or that a different accepted call with identical content is a duplicate. |
| Saved asset/package member hash | The checked bytes agree with the expected bytes. | Which source/region/settings produced them, semantic correctness, complete publication, or absence of extra/missing package members. |

The app identity supplies task/accepted-parent/operation scope. Fingerprints detect inconsistent reuse of that identity. Their canonical serialization and exact covered fields remain contract work. Preserve native/raw and resolved representations without pretending one hash identifies all of them. Resolving a candidate reference expands an input for execution. Rewriting its pointer to a different candidate under the same operation ID changes meaning, not merely formatting.

**Source basis:** EVT-0855, EVT-0878, EVT-0942, EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107. ATT-21–ATT-29.

<a id="accepted-batch-execution"></a>
## 3. Accepted batch execution and ordering

Persist the complete accepted call list before relying on execution progress. Calls execute from their original complete arguments, not a shortened model-facing history projection. Incomplete JSON or concatenated fragments from separate attempts must never become an executable call. Domain validation can reject an individual call with a precise result, while preserving its received candidate arguments.

A batch-owning executor is responsible for all declared calls and the point at which the next model input becomes valid. Finding a committed receipt for A does not settle B. Before the next new request:

1. Restore completed results and necessary intents/effects.
2. Execute or reconcile outstanding calls according to their contracts.
3. Account for any stop. A stopped unfinished batch does not become a completed batch merely because one call succeeded.

“Settled” includes an accurately recorded validation/error outcome. It does not mean every tool succeeded. If A saved a version and B's arguments were rejected, preserve A's success and B's candidate/error. Once the executor accounts for the accepted batch's actual outcomes, a later model decision can propose a new valid B operation.

Do not rewrite the accepted B arguments under its old identity. Do not silently omit B. Do not resend A to make the batch appear uniformly successful. Malformed or incomplete native calls take the preservation/error path. That path does not authorize execution merely because the app saved a raw candidate.

Do not assume that adopting `create_agent` preserves the old controller's sequential execution. The reviewed implementation dispatched tools through separate `Send("tools", ...)` paths. Two distinct orderings matter:

- **Context intent order:** settle intents according to the trusted accepted-parent declaration order, not the order concurrent I/O finishes. Persist policy and processed-batch state coherently at the defined sequential boundary.
- **Actual effect order:** a deterministic intent list does not order edits, file writes, or previews. If B depends on A's version, the executor must express that dependency or use explicit versions and service preconditions.

A small sequential tool-batch node is a valid first-version choice and does not impose a PDF extraction recipe. Independent reads may later parallelize under their actual resource/side-effect contract. A fixed-version reopen is not unsafe merely because it is called a document tool. Conversely, OCR/render can create files, assets, and child processes. Leaving the PDF unchanged does not make these operations universally pure.

The review rejected an in-memory declaration-order lock as recovery machinery. A may complete, and the framework may restore its pending write without rerunning A. B can then wait forever for A to signal a new in-memory event. Durable progress and the executor's complete batch ownership must determine what remains. A read of `latest` can also race a later writer even if each writer waits for earlier writers. Bind the read/export/preview to its intended version or define its dependency at acceptance.

### Completion includes effects beyond display text

Some tools produce a `ToolMessage` plus a graph `Command` or context intent. Replaying only the visible message can leave a necessary current-batch state update absent. Preserve the domain result and supported completion semantics. If the implementation supports only `Command.update`, it cannot silently discard other forms such as `goto` or `graph`. Concentrating state writes may simplify the final implementation, but does not remove required effects.

At the same time, an old completion must not force a newer state backward. Suppose batch X settled policy 7 to 8 and a later batch settled 9. Replay of X reports its completed processing and retains 9. An incomplete original transition can use its receipt only under compatible parent state. Incompatible modification needs an explicit conflict, not `max(policy_rev)` or unconditional activation of the old result.

Stable message IDs are useful but limited. A reducer can replace an existing same-ID message. After compaction removes it, replay may append it again. Do not scan every successful receipt and inject historical ToolMessages into current input. Reconcile the accepted pending batch/runtime work, not an unbounded global journal. Protocol pair validity must survive projection and recovery.

Progress also needs a defined causal boundary. An operation created with sequence 10 can finish after sequence 11. Neither `max(event_seq)` nor the latest timestamp safely substitutes for per-call completion and processed-effect identity. Record which accepted calls/effects remain outstanding. Under sequential execution, a small batch cursor plus explicit records can track this information. It does not require a general event-sourcing system.

The earlier controller's `next_call` and pending-operation identity illustrated this cursor responsibility. It means “which declaration still needs an accounted outcome,” not “the first absent display message.” Recovery needs the accepted call list and each call's durable result, error, unfinished state, or stop reason. A cursor alone cannot prove that an externally committed operation did not happen. Conversely, a framework pending write may already contain a result that need not be executed again.

**Source basis:** EVT-0878, EVT-0914, EVT-0942, EVT-1005, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-21–ATT-30.

<a id="operation-replay"></a>
## 4. Operation replay and resolved defaults

Persist resolved defaults at the operation's declared start boundary, after any required earlier batch dependency. These values stay bound to that operation on recovery:

- An omitted version that resolved to V10.
- Selected source, region, and render parameters.
- The output location and attempt directory. A later new operation may resolve defaults again. This prevents a retry of “preview current” from quietly previewing a different version.

For `save(...)` followed by `preview(version omitted)`, resolving both calls at batch acceptance could bind preview to the pre-save version. Under the discussed sequential-start option, preview resolves the current version once, after the preceding save settles. It records that exact version before doing its own work. Explicit version arguments remain preferable when already known.

The final contract must state the resolution point. “remove the word latest” does not remove a dynamic default. It must also distinguish the originally accepted arguments from the effective arguments with recorded defaults, so recovery can check both without resolving them anew.

The proposed record names `resolved_version_id`, `output_dir`, and `attempt_dir` make this binding concrete: they record the values actually chosen for execution, not defaults to evaluate again after restart. The suggested operation tuple `(task_id, model_step_id, call_index, tool_call_id)` also tried to give a provider call task/parent/order context. It is an illustrative key, not a finalized uniqueness rule. The accepted parent reply and fixed effective input still need an unambiguous relationship. Declaration index does not itself serialize effects.

Same operation identity with the same complete effective input reuses its original result. The service rejects the same identity with changed parameters, tool, target, or fixed references. A new accepted operation with similar content is not automatically the old operation. Optional content deduplication needs the full scope/base/target/content, and does not infer semantic intention.

| Operation | Recovery facts and boundary |
|---|---|
| Fixed-version read/reopen | Resolve the original exact version/evidence. Do not substitute today's head. |
| Save/edit | Find its committed registration/receipt. If only a prepared result exists, finish only under the original expected base/target. Otherwise, retain it and return conflict. |
| Select delivery | Return the original selection receipt. Do not overwrite a later legitimate selection. Target/scope validity is separate from requiring a fully completed document. |
| Source render | Check PDF identity, physical page/region, DPI/engine settings, attempt state, and output completeness. It needs no saved document version. |
| Output preview | Check selected document version and view parameters, including whether this is ordinary reading or an expanded diagnostic view. |
| Export | Reconcile the specified immutable version, destination identity, intended members and actual bytes, separately from working head. |
| OCR / child process | Inspect its recorded attempt and files/process state. Safe parallelism, safe reuse, and safe rerun are separate questions. Preserve useful output. Uncertain local effects require reconciliation or stop. |
| Host-user script | Retain complete arguments/logs and known effects. Do not blindly rerun an outcome-unknown script merely because no success receipt exists. |

Suppose A produced V12 and B later produced V13. Replay A returns “A produced V12” and leaves head V13. Suppose C selected V10 and D later selected V11. Replay C returns C's historical result without selecting V10 again. A historical receipt is a fact at commit time, not a fresh command to establish the same pointer today.

Successful version metadata does not replace started/outcome-unknown records. No receipt may mean the effect never happened, the process is still running, or the effect completed before its receipt was saved. File/hash equality alone cannot establish whether a render used the requested source/region/DPI. Use the operation's complete fixed inputs and actual result/attempt facts.

**Source basis:** EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-25–ATT-30.

<a id="recovery-transitions"></a>
## 5. Recovery transitions and durability gaps

Q3 must assign an owner and finite re-entry behavior at each boundary below. These are scenarios to specify, not claims that all such failures occurred in the old app or that every hard crash will be recoverable.

| Durable facts on re-entry | Required next decision/action | Invalid shortcut |
|---|---|---|
| Prepared request exists, but no accepted reply exists | Reconcile attempts, consumed limits, cancellation and configured replay eligibility before another send of that frozen request. | Assume no reply means no remote work/cost. |
| Attempt may have been sent, and remote outcome is unknown | Apply enabled bounded model replay under original limits, preserving uncertainty and potential overlap. | Claim local timeout canceled the upstream generation. |
| Service accepted a complete reply, but graph lacks it | Retrieve by durable logical request/step identity and recover its accepted batch. | Send another model request because graph metadata lacks an ID. |
| Executor accepted the reply, but only some calls are complete | Reuse completed results/effects and reconcile all remaining calls in that same batch. | Advance after the first receipt found. |
| Immutable version payload is ready, but metadata is absent | Verify identity/completeness and original expected base/target before finishing the defined commit. Preserve conflict output. | Delete it as abandoned or advance head over a newer version. |
| Tool committed, but result projection/checkpoint is absent | Return/reconstruct its historical receipt and necessary current-batch completion effects. | Repeat the local commit or treat projection error as write failure. |
| Whole batch settled, but graph continuation is absent | Restore supported deterministic continuation effects, then assemble the next request at a safe boundary. | Re-inject all historical receipts or regress compact policy. |
| External local effect remains unknown | Inspect/reconcile within the operation contract. If the effect cannot be established, preserve work and stop with a specific unknown outcome. | Blindly repeat OCR/script/process work. |
| Stop, waiting, or cancellation is recorded | Respect that state and original limits. A defined explicit continuation may alter cancellation, but not replenish allowances by itself. | Restart as a fresh unlimited run or add a reminder to every stop. |
| Export partly published | Check original output identity, selected version, directory and archive contents, then finish/reconcile the declared effects without overwriting unrelated output. | Assume one rename atomically published directory and ZIP. |

Graph checkpoints, metadata transactions, and external files are separate durability boundaries. A runtime checkpointer is not a transaction manager for outside effects. Modes described as `sync`, `async`, and `exit` have different persistence timing. Select and verify the actual supported behavior of the pinned framework version. The historical `durability="sync"` argument concerned writing a prior checkpoint before the next step, not exactly-once remote generation or universal power-loss safety.

Use supported framework state/history/resume and pending-write facilities rather than treating diagnostic task descriptions as an executable tool-call array. `StateSnapshot.tasks` describes runtime tasks. The app should not invent a competing scheduler from those descriptions. A batch-owning node can retain durable app progress because the framework does not automatically checkpoint each nested call. Reuse framework-recorded completion where available and app receipts across the remaining effect/checkpoint gap.

Restoring an old graph snapshot cannot erase later committed document versions, request attempts, consumed budgets, or external effects. An old request still reuses its own frozen input. Once its accepted batch is settled, a new decision can assemble a current view. These two rules coexist: historical input consistency and preservation of later facts protect different responsibilities.

An exception that runs `finally` and flushes data is not a hard process-kill test. Broken IPC can leave a child working. The old R1/R2 exercises injected bounded network/stream failures. They did not establish arbitrary crash recovery, natural prolonged-outage behavior, or migration of old job formats. No backward compatibility is required for the rebuild.

<a id="historical-fault-relay"></a>
### Historical fault injection and its exact scope

The old `tools/experiment_fault_relay.py` was a closed experiment helper, not a product API or production transport. Its CLI bound a loopback listener and a fixed Nexus upstream, path and model. It armed faults after matching the controller's request, published draft and receipt, with requested positions still unprocessed. Those structural checks did not establish source usefulness, which required independent review.

| Mode | Historical injected condition |
| --- | --- |
| R1 | After the partial-work gate matched, a 90-second monotonic timer controlled local HTTP 503 rejection before any upstream connection. Timer expiry and later forwarding were separate events. |
| R2 | One cut followed at least 64 accumulated alphanumeric characters from content or tool-argument deltas in complete, nonterminal Chat SSE frames. |

The R2 counter used Python `str.isalnum()`, including qualifying Unicode characters. It did not count bytes, tokens, punctuation, heartbeat comments or mere frame arrivals. The observer disabled further cuts after a finish reason or `[DONE]`. The relay forwarded through the triggering complete frame, then closed both connection handles. Complete frames could still contain incomplete tool arguments, which never authorized execution.

If no qualifying interval appeared, the helper recorded `fault_unexercised`. It forwarded ordinary bytes incrementally without reconstructing or joining attempts. Its records contained safe timestamps, hashes, stages and forwarding facts, not provider bodies, arbitrary headers or credentials. A stop file closed the listener, active handles and timer.

These mechanics explain what the old trials exercised. They do not establish a natural outage, a new application dependency or permission for another trial. [SUP-25](../../sources/rebuild/support/SUP-25.txt) preserves the selected helper logic. [SUP-26](../../sources/rebuild/support/SUP-26.txt) preserves its historical scope description.

**Source basis:** EVT-0942, EVT-0968, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166. Earlier recovery qualifications appear in [reference 02](../discussions/20261031_0157_REBUILD_CONTEXT.md#persistence-and-replay).

<a id="budgets-cancellation-and-stop"></a>
## 6. Persistent budgets, cancellation, and stop reasons

All actual model sends pass the shared service's final gate, including ordinary reasoning, semantic compaction, configured overflow re-preparation, and an optional reminder. A gate only at the graph's starting node can be bypassed by a restored successor or alternate edge. Persist consumption/attempt identity before dispatch, then preserve observed outcome, known usage, unknown cost, and remaining allowance. Do not hide nested SDK/proxy retries that multiply the configured policy.

Keep the following quantities distinct and define their accounting in the open contract:

| Quantity | What needs an explicit rule |
|---|---|
| Logical decisions / model rounds | When a new intended step consumes the original task allowance. |
| Physical attempts | Every actual send, including enabled retry or capacity-recovery send. |
| Request inactivity or transport timeout | Which connection/header/body/idle boundary is observed and what outcome is actually known. |
| Whole-job active time / elapsed time | Whether waiting, backoff, local preflight, tools, and user waiting count. Restart must not reset accumulated facts. |
| Context/input and output reserve | The actual assembled request and selected route, separate from request bytes and nominal provider window. |
| Cost/usage | Known observed usage and unknown/possibly duplicated inference. A local failure or later success does not erase uncertainty. |

The historical examples select no new retry count, 60–120-second backoff, 180-second timeout, 100-round cap, or universal context threshold. Old zero-retry defaults and finite trials do not become new-repository defaults. Exact eligibility/limits need configuration within the authorized task.

Unknown remote generation and unknown local effects have different handling. When bounded unknown-outcome model replay is enabled and allowance remains, it does not require routine human proof that the original generation stopped. Record possible duplicate inference, remote overlap, and unknown fee/usage. Local abort, timeout, or a successful later attempt does not prove cancellation, continuation of the first generation, or zero cost. A script/OCR operation with an unreconciled local outcome stops under its own effect contract rather than being blindly replayed.

The app can read already durable accepted results when the model allowance is exhausted. Reading them does not send a request. This does not grant authority for every unfinished tool to run past another applicable limit. Preserve the pending batch/stop reason and useful work. Host-callable export of a specified saved version remains possible without further model tokens, subject to its own execution time, storage, cancellation, and publication rules.

<a id="historical-retry-hierarchy"></a>
### Historical retry hierarchy and manual resume

The old controller distinguished three modes. These names and limits explain its policy. They do not select rebuild defaults.

| Historical configuration | Automatic eligibility | Ceiling per preserved model round |
|---|---|---|
| `automatic_retries > 0` | Eligible transient replay, including recognized queue failures. | `1 + automatic_retries` app HTTP attempts, including the original. Queue attempts consume this allowance even when `queue_retries` is larger. |
| `automatic_retries = 0`, `queue_retries > 0` | Only recognized pre-generation queue failures. | `1 + queue_retries` app HTTP attempts, including the original. |
| Both options equal zero | No automatic replay. | The original attempt plus at most two explicit resumptions retains a three-attempt ceiling. |

Thus, `automatic_retries: 2` allowed three app HTTP attempts for that preserved round. The queue option did not add another retry allowance. The controller persisted attempts and consumed budget before dispatch. Resume and restart retained the original turn, active-time and per-round attempt budgets. Two permitted explicit resumptions did not replenish those budgets.

All attempts and waits shared the original cumulative active deadline and maximum turns. A retry was not a new model round. Successful recovery preserved earlier unknown attempts and their unresolved usage. A later local-only continuation did not charge the same accepted historical ambiguity again.

The old policy specified one accountable app retry owner to prevent configurable SDK or proxy layers from silently multiplying its allowance. Opaque upstream retries remained a limitation. Three app attempts did not guarantee three upstream generations or a monetary ceiling.

This hierarchy covered the historical transport and recognized-queue policy. It did not settle every future admission or capacity-recovery policy. The rebuild retains durable accounting and explicit bounded eligibility. [Capacity re-preparation](#capacity-rejection-is-not-ordinary-same-input-retry) still needs its separate rules while sharing task totals.

**Source basis:** SUP-09, historical TOOLS retry-budget and retry-owner passages.

<a id="historical-retry-delay"></a>
### Historical backoff values and calculation

The old `RunConfig` supplied these defaults and bounds:

| Field | Historical default | Accepted range |
| --- | --- | --- |
| `retry_initial_delay` | 2 seconds | 0–60 seconds, inclusive. |
| `retry_max_delay` | 30 seconds | 0–300 seconds, inclusive. |
| `retry_jitter` | 0.25 | 0–1, inclusive, as a dimensionless proportion. |
| `queue_retry_delay` | 15 seconds | 0–60 seconds, inclusive. |

For an eligible automatic retry, `attempt` meant the failed attempt's one-based number, including the original send as 1. The controller calculated:

```text
local = min(retry_max_delay, retry_initial_delay * 2**(attempt - 1))
local = min(retry_max_delay, local * (1 + uniform(0, retry_jitter)))
delay = max(local, retry_after_seconds)
```

Thus, jitter only added a nonnegative proportion before the second cap. With the defaults, the first local delay ranged from 2 to 2.5 seconds. A valid `Retry-After` of 59 seconds could exceed the 30-second local cap. An absent accepted header contributed zero, not an extra delay.

For recognized queue-only recovery with `automatic_retries=0`, `queue_retry_delay` replaced `local` before the final maximum. It did not add another exponential wait or retry allowance. Positive `automatic_retries` retained the automatic calculation even for eligible queue failures.

The controller persisted `retry_wait_seconds` and `retry_not_before` before its cancellable wait. Resume used the remaining wait against that timestamp instead of drawing fresh jitter. Attempts and waits still shared the original active deadline, cancellation state and attempt allowance. A larger header delay did not extend the task deadline.

[SUP-24](../../sources/rebuild/support/SUP-24.txt) preserves the historical configuration, formula and wait code. These numbers do not choose rebuild defaults or settle the open capacity-recovery policy.

<a id="send-boundary-sequence"></a>
### Same-request recovery at the service boundary

The service follows this sequence:

1. Locate the prepared logical decision and check its fixed input identity.
2. Recover any complete accepted result.
3. Only if a fresh send is needed, assess original attempt state, remaining limits, cancellation, and actual request capacity.
4. For that fresh send, persist attempt consumption before dispatch. Save the received native result and its acceptance outcome before graph continuation depends on it. Exact record/state names and timeout accounting remain Q3 choices.

This order avoids two opposite errors. A zero model allowance does not discard an answer already obtained and saved. Conversely, missing graph state does not permit another send without examining attempts already charged to the task. If a compaction used the last allowed attempt, the app can still inspect and validly apply its stored result. A subsequent ordinary request is not free.

The prepared request may be too large, or its route may no longer apply. A later authorized re-preparation must receive its own identity and preserve the earlier attempt's history. Silently changing the frozen payload is not same-request replay.

Cancellation takes precedence at the actual work boundary, including after successful compaction and before the next request. Do not require a final model handoff before honoring pause/cancel. A defined explicit continuation can clear cancellation but does not itself reset attempts/turns/time. A genuine question waits for user input. A technical blocker, exhausted allowance, or generic no-tool stall is not automatically a question for the user.

### Capacity rejection is not ordinary same-input retry

A deterministic local projection consumes no HTTP attempt but uses time. An actual reduced resend does consume an attempt and shared totals. With retries zero, defining every send as `1 + automatic_retries` would leave no separate capacity-recovery send. Therefore, the policies need separate explicit eligibility and bounds while sharing total accounting. “One immediate overflow resend” remained a proposal.

Only a supported capacity diagnosis and a changed view that improves the relevant limit justify re-preparation. Generic HTTP 500/502 is not overflow evidence. HTTP 413 concerns request bytes and may include `Retry-After`. It does not reveal token capacity or justify always resending immediately.

Rejection of a locally estimated 80k input does not prove an 80k model window. Record route/model/protocol, upstream error/count/limit where available, and local estimate/method separately. A provisional safety budget can be adjusted deliberately without rewriting a provider specification or changing unrelated routes.

Streaming and non-streaming use the same complete-response acceptance, operation, persistence, and stop semantics. Partial fragments remain evidence. Never splice them across attempts into executable JSON. Retain useful received native content with appropriate handling of sensitive/error fragments. Preserve distinctions between protocol completion, schema validity, and content correctness.

**Source basis:** EVT-0855, EVT-0878, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-22/26–ATT-30.

<a id="context-work-and-frozen-input"></a>
## 7. Context work uses the same durable execution boundary

R01 changes new unfrozen capacity observations, not execution identity. [The context guide](../../guides/CONTEXT_AND_EVIDENCE.md#capacity-accounting) owns the shared BPE proxy, offline data, explicit fallback and uncertainty semantics. Recover historical handoff/settlement effects and existing frozen requests before any current estimate; never rewrite receipt/usage or revive committed needs-revision content. Prospective app-authored outcome metadata uses the same canonical ordering and latest-candidate anchor as the eventual saved settlement, so embedded JSON strings produce the same native payload and BPE reservation. An old equal-byte-length assumption is insufficient for that boundary. Original model/tool content is unaffected.

The single built-in executor keeps a compact policy projection in graph state: selections, pin/release choices, notes or references, compaction boundary and processed batches. Context calls save intents; the coordinator admits the complete revision. Its catalog transaction commits disposition and any active-policy effect, which the graph then recovers. The historical graph-only simplification rejected a competing policy scheduler; the current commit/current-policy records provide checkpoint-gap authority without adding another decision writer. Request budgets, committed documents and external-operation receipts likewise remain service facts because graph rollback cannot undo them. [Q2/Q3](../contracts/20261031_0157_CONTRACTS.md#q2-context-transitions) owns this current boundary.

Transient hydration belongs to request assembly. Returning giant OCR/images as persistent state updates refills every checkpoint. The input service follows the settled selection and resolves the corresponding immutable evidence. It does not make a second independent relevance decision.

A save that omits a context delta does not silently release everything unpinned. Pin/release conflicts need an explicit merged outcome. Reducers do not determine semantic importance by themselves.

Semantic compaction is real model work with a purpose, frozen input, identity, attempt records, accepted output, budgets, and cancellation. It cannot be an untracked call inside a supposedly free prepare function. It can share the same service in the same Python backend without another communications stack. A successful compaction edge must return through the same checks before further work.

Each compaction records the history actually supplied, prior handoff/coverage, uncovered history, and base revision. Apply only the covered range and preserve unprocessed messages and complete protocol pairs. The app should supply program-known message IDs and revision anchors. The summarizer should not reconstruct them. Check format/nonblank/refusal, exact replacement scope, current revision, and resulting capacity. These checks do not prove semantic losslessness or require a second review-model call.

Distinguish progress from readiness for normal inference. Reducing 140k to 100k toward an 80k target can be useful even though another compaction is needed. Check the complete resulting view including summary/anchor overhead. A normal request must fit the final input/output allowance. Intermediate compaction need not already reach it.

Preserve originals on invalid/stale/no-progress output and use bounded original allowances to stop if no fitting request can be assembled. Do not automatically resend the same oversized normal request after failure.

The recommended handoff is self-sufficient for continuation: effective requirements, current scope/version, unfinished work, exact useful references, decisions, cautions, and cross-page dependencies. A delta-only note can lose meaning when its anchor changes.

For example, a handoff omits “next-page rows use the prior header” because it is already in an anchor. That information disappears if a later anchor only says “processing page 18.” An anchor stored on disk does not prove that future input assembly includes it. That alternative would need exact anchor inclusion or reconsolidation. It is not the V1 prerequisite.

Authoring arguments can be as large as tool results. Keep original calls for pending execution/replay. A later model-input projection may replace completed historical body text with exact references. Latest drafts and unresolved candidates can partly leave input when irrelevant portions are safely retrievable. There is no fixed recent-K or superseded-only retention rule.

A just-generated call was not in the prior model input, so projecting it before first return does not necessarily invalidate that prior prefix. Rewriting earlier sent history differs. Neither a permanent verbatim window nor a claimed 90% saving is established. Frozen snapshots protect replay independently of cache policy.

The [context guide](../../guides/CONTEXT_AND_EVIDENCE.md) contains the detailed policy/capacity algorithms and examples. This section states what their execution boundary must preserve.

**Source basis:** EVT-0878, EVT-0914, EVT-0942, EVT-1005, EVT-1040, EVT-1068, EVT-1107, EVT-1147, EVT-1166.

<a id="completion-and-waiting"></a>
## 8. Execution stop, content completion, and package consistency

Use separate dimensions rather than one terminal label that mixes them:

| Dimension | Examples of information it records |
|---|---|
| Execution | Running, waiting on a real question, canceled, limited by budget/time, blocked by a specific technical/unknown-effect outcome, stopped without complete delivery. |
| Content claim | Which scope/version the agent considers complete, known gaps/errors, draft/partial status, and source-review observations where performed. |
| Package consistency | Which version/scope was selected, which output files/archive were built, actual consistency checks, and publication outcome. |

<a id="stop-label-meanings"></a>
### Why the historical terminal labels were split

ATT-28 proposed `completed_verified_delivery`, `exported_honest_draft`, `waiting_for_user_clarification`, `stopped_operational_limit`, and `stopped_unreconciled_effect` as five mutually exclusive terminal states. They mix facts that can coexist: a canceled or budget-limited execution may have exported an honest draft. The later `execution_status`, `content_status`, and `delivery_status` names express separate dimensions, not a frozen three-field schema. In particular, `completed_verified_delivery` must not imply source acceptance merely because package bytes match a version. A label such as `exported_package_verified_against_version` describes that narrower consistency check.

The waiting aliases `awaiting_user`, `waiting_for_user_input`, and `waiting_for_user_clarification` are meaningful only with a concrete question to answer. `clarification_prompt` was a suggested place to retain it. A generic technical fault or repeated no-tool reply can instead be `stopped_incomplete` with its actual reason. `stopped_unreconciled_effect` also needs to distinguish local effect uncertainty from an unknown remote model outcome, because the latter can permit configured bounded replay. Exact state names remain Q3 work. The distinctions prevent a UI from asking the user to resolve a question that was never posed.

A canceled run can contain a useful exported draft. A consistent ZIP can contain incomplete content. A valid schema or no-tool final answer cannot establish source fidelity. A selected good V10 can coexist with experimental V11 and an unused candidate. Those do not automatically block delivery. Only known necessary unfinished work affects the completion claim.

A no-tool answer may ask a real question, explain a blocker, merely narrate a planned tool action, prematurely claim completion, or actually finish. The implemented agent protocol uses `report` to declare complete, partial or waiting intent. For text without that declaration, the response-correction increment gives bounded feedback to continue useful work or formalize the intended report. It explicitly states that no user answer has arrived. A question becomes waiting through `report(waiting)`; the controller does not infer semantic completion or classify question marks. Whether a real model reliably follows this instruction remains a model-quality question.

The historical one-shot reminder proposal required persisted identity, finite counts, normal accounting and stop precedence. The implemented policy now permits `max_response_repairs` corrections (default 2, configurable for new tasks), with independent normal-response and compaction episodes. Feedback lives at `repair:<request>`; the graph carries only its reference, count and current-head/amendment basis. Re-entry reuses accepted replies and saved feedback rather than sending the same request again. Plain Continue does not replenish the allowance. New user instructions or an edited head establish a new episode while consumed task attempts/time remain unchanged. Explicit reports, cancellation and budgets retain precedence. This is not a general semantic-progress detector or a guarantee that the model will act correctly.

Invalid handoff JSON, schema, reduction or unexpected tool calls follow the same feedback mechanism. A new compaction request keeps the covered history and diagnostic; the rejected candidate text is included only when the complete input fits. Previous context remains active until a valid replacement applies. State mismatches and local storage faults do not become model repair prompts. `handoff:<request>` and transactional event receipts cover replay after archive/feedback persistence and before checkpoint completion. This does not make the graph checkpoint and catalog one transaction.

The no-tool decision can therefore be expressed without inventing a completion detector:

| Known condition | Retained behavior |
|---|---|
| User canceled, a limit is exhausted, or a local effect cannot be reconciled | Record that stop reason and preserve available work. No reminder overrides it. |
| Agent declares a specific necessary question with `report(waiting)` | Store the question and wait for its answer. Do not run a continuation reminder after this explicit report. |
| A saved version/scope is already selected and only packaging is missing | Use the host-callable export path under its applicable limits. A new model judgment is unnecessary for known packaging intent. |
| Agent reports completion | Bind the content claim to its actual version/scope and retain known gaps/review evidence. A statement alone does not certify fidelity. |
| Text-only reply without a report, with execution still permitted | Use the configured bounded correction to request the next action or an explicit report. If the text asked a necessary question, request `report(waiting)` without assuming an answer. Do not pretend completion or fabricate a user question. |
| The same stall persists after its allowed reminder | Preserve results and report incomplete stopping. Restart does not create a fresh reminder allowance. |

**Source basis:** EVT-0968, EVT-1005, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-25–ATT-30.

<a id="process-and-progress"></a>
## 9. Local processes, progress, and desktop IPC

Process isolation and side-effect tracking serve different purposes. Trusted scripts are process-opt-in/off by default and run with host-user permissions. They are not an OS sandbox. Enabling them permits autonomous own-task use under the agreed task scope. Source text and recorded commands remain inert data. Separate attempt/output directories can avoid collisions, but do not isolate model context, privileges, or unknown external effects.

Read-only inspection, explicit termination, and salvage must be separate actions. Historical names `inspect_attempt`, `terminate_attempt`, and `salvage_attempt` express that distinction without requiring those exact APIs. Inspecting or copying useful output must not silently kill a running child. A proposed `terminate_running_process=True` made termination explicit.

Windows Job Objects and `FILE_SHARE_READ` snapshots were possible mechanics. A real implementation must determine whether reading a live file is stable/allowed and report conflicts/incompleteness. These options do not create a required general process-salvage subsystem.

Preserve useful complete images, logs, and partial outputs in an interrupted attempt. Do not clear `attempt_dir` as a routine prelude to rerunning. Check source/settings/completeness before reuse, and create a distinct new attempt for necessary reruns. Complete decoding of saved output and bounds on inspection matter. Rescued output is not proof that the whole operation or task completed. Original full logs/files remain available despite tool response-size limits.

For the eventual desktop, structured progress can describe preparation/capacity, request/attempt/backoff, streamed character count, OCR page progress, candidate retention, and committed versions. These are notifications about work, not the source of truth. “OCR page completed” means evidence extraction, not conversion/source acceptance. Version diffs read explicit saved versions rather than reconstructing prose from progress events.

The historical direction was asynchronous JSON over standard input/output, with exact framing open. IPC is communication between the desktop and Python processes. Protocol messages and diagnostics require distinct deliberate channels. A library printing text into the protocol stream can corrupt framing. The proposed universal first-line `os.dup2` remedy was withdrawn because native callbacks, libraries, threads, Windows behavior, and packaging need the actual implementation context. The retained requirement is correct channel separation, not a mandated redirection recipe.

A bounded queue cannot guarantee unlimited non-droppable replies, producers that never wait, and indefinite receiver failure simultaneously. If the UI stops reading, a pipe eventually fills. Keep ordinary progress off the conversion core's critical path.

- Coalesce outdated progress.
- Persist important results for request-ID lookup.
- Use a snapshot/sequence or revision on reconnect.

Declare queue/storage limits and how new work is limited or rejected. Both protocol and diagnostics pipes need appropriate consumption. Dropping obsolete “page 5” progress after “page 6” is different from dropping the only receipt for a committed version.

The proposed `state_seq` / `state_watermark` event would tell the UI that newer committed state is available. `dropped_intermediate_events` would report coalesced notifications. It would not reconstruct lost authoritative results. Similarly, `evidence_extracted` and `version_committed` distinguish OCR evidence from a saved draft. A proposed `diff(V11, V12)` reads those two actual versions.

A ring buffer, watermark, or separate async sender can support this notification design. None removes finite pipe/storage limits. None permits an unbounded stream of lossless control replies while the receiver is absent. These names are explanatory event sketches. Final IPC framing and schema remain open.

The [integration guide](20261031_0157_INTEGRATION_AND_MODEL_BOUNDARY.md#desktop-process-boundary) covers the desktop/native protocol ownership. This guide supplies the durability and finite-failure limits.

**Source basis:** EVT-0855, EVT-0878, EVT-1040, EVT-1068, EVT-1107, EVT-1147. ATT-21/22/27–ATT-30.

<a id="explicit-version-export"></a>
## 10. Explicit-version export and publication

Export operates on a specified saved version and effective scope. The conceptual delivery intent is `(version_id, scope_rev)` plus the defined destination/output choices. It must not silently become “whatever head is latest when packaging finishes.” If V10 is good and V11 is an experimental table edit, selecting V10 means exporting V10 even while work on V11 continues.

Delivery intent belongs to the current task, rather than one unqualified global selection on the source document. The document core owns committed versions and their provenance. The task owns which version and scope it chooses to deliver. Choosing an existing V10 must be expressible without creating a dummy edited V12. Selecting the just-created version can remain a convenience of a commit, but it does not replace direct existing-version selection. General branch UI or merge support is unnecessary to preserve this ownership distinction.

The host/CLI/UI can export existing saved content without another model call. The old `Workspace.export(document, version)` and CLI dispatch already demonstrated that responsibility. The rebuild should preserve the capability, not their exact API. Exhausted model tokens do not make saved content inaccessible. Export still consumes time/disk and has its own cancellation/publication behavior.

The proposed `export_package(version_id, destination, delivery_label)` named the same host-callable responsibility more explicitly. It chooses immutable content, an output destination, and an honest label without asking a model to regenerate or approve it. `finalize_run_node` named a possible caller inside the graph, not the sole owner or a guarantee that a finalizer always runs. Persisted intent and results let a host action perform or reconcile export after the inference loop stops.

The selected version determines Markdown, JSON, HTML, source-derived images/assets, and ZIP. Keep the relevant body/maps/assets consistent across representations. A draft remains labeled draft/partial with known gaps. Selecting/exporting it must not gain a hidden “full task complete” precondition. Likewise export success must not upgrade the content claim.

### Historical package members

The earlier implementation used the following layout for one saved snapshot. These names illustrate member roles rather than fix the rebuild's filenames.

| Historical member | Role for the selected saved version |
| --- | --- |
| `document.md` | The saved Markdown reading content, with relative links to its required assets. |
| `document.json` | The structured document, version/source identity, page mapping, content status, Markdown, and asset metadata. |
| `preview.html` | The safe HTML reading preview generated from that saved Markdown and version. |
| `manifest.json` | The version identity and file-hash map for `document.md`, `document.json`, `preview.html`, and the referenced asset files. |
| `assets/<referenced-file>` | Zero or more referenced asset files from that saved version. The package excludes unrelated workspace assets. |

The ZIP contained `manifest.json` plus the files listed in its member map. An empty `assets/` directory was not a required ZIP entry. Final member names and layout remain open under Q3. The retained requirement is consistent artifacts and resolvable relative links for the explicitly selected version.

A proportionate consistency check compares intended members and actual bytes against the selected version. A manifest identity alone does not prove that files were written correctly or that the ZIP contains those same members. Source fidelity is a further content question. Package consistency cannot certify that every figure label or paragraph is correct.

Directory publication and ZIP publication are two effects. A rename of one cannot atomically publish both. Persist enough identity/intent/outcome to reconcile re-entry: which version/scope, destination, artifacts, and known completed publication belong to this operation. Preserve unrelated files and do not overwrite a different existing output merely because the original desired name is occupied. Exact output naming, idempotence/replacement behavior, and crash visibility remain Q3 choices.

<a id="export-publication-sequence"></a>
### Build, check, publish, and re-enter

The discussed requirements imply the following finite responsibilities. Their exact filesystem layout and transaction representation remain open:

1. Resolve and retain the export's specified immutable version, task/scope, content label, destination, and operation identity. If a later task selects another version, this export still refers to its original version.
2. Obtain the canonical document and its required assets. Build portable Markdown, document JSON, safe HTML, and the intended image set. Do not copy unrelated workspace files, credentials, requests, or logs into the package. Relative links must resolve within the delivered package.
3. Prepare the output directory and archive from that same selection. Keep draft/gap metadata consistent with the selected scope/version. Packaging does not regenerate missing source content or upgrade the completion claim.
4. Compare the intended member set and actual written files/ZIP member bytes with the selected result. Detect missing, extra, or differing members under the declared package contract. Checking only the manifest file's hash cannot detect a changed image or absent Markdown member.
5. Publish each declared output and retain its actual outcome/identity. The point at which the directory becomes visible and the point at which the ZIP becomes visible may differ. A single completed publication is not evidence that both finished.
6. On re-entry, first reconcile known publications and useful prepared files. If the directory is complete but the ZIP is unpublished, preserve the matching directory.

   Finish or rebuild only the unresolved archive work as the export contract permits. The destination may instead contain another operation's output. In that case, report the conflict or use an explicitly defined separate destination. Do not replace that output as if it belonged to this export.
7. Return the original export outcome when that same operation already completed. Replaying the export receipt neither moves the working head nor restores an old delivery selection over a newer one. A fresh export to another destination is a separate operation even when it contains the same version bytes.

This is separate from the immutable-version commit. A failed export can leave a valid saved version available for a later host action. A committed export receipt can outlive the currently selected delivery. The implementation must define what to report if an already-published file is subsequently removed or changed. Its historical receipt cannot honestly certify the present bytes without checking them.

An all-exit finalizer cannot promise packaging after hard termination, shutdown, cancellation, or every graph failure. Cancellation first stops new model/tool work. Whether a large already-running package operation may continue depends on the task's defined policy. A later host action can export saved work. Automatically producing the newest draft must not replace the explicitly selected delivery. All-exit packaging is not a V1 prerequisite.

**Source basis:** EVT-0914, EVT-0942, EVT-0968, EVT-1005, EVT-1068, EVT-1107, EVT-1147, EVT-1166. ATT-23–ATT-30. SUP-05, SUP-06.

<a id="worked-recovery-sequence"></a>
## 11. Worked recovery sequence

This sequence combines the discussed boundaries to make their interaction explicit. It is an explanatory scenario, not a prescribed conversion workflow or claim of implementation.

1. Prepare logical decision Q using V10, chosen OCR evidence, route/settings, and tool schemas. Save that exact request. Before send attempt 1, record the consumed allowance.
2. Save a complete accepted response with a batch containing A and B. A edits V10 to produce V11. B previews the resulting intended version. The batch owner resolves their defined dependency. It does not let B read an unrelated future `latest`.
3. A stages/validates immutable content and commits V11's registration, promised head change, and operation receipt. The process stops before B and before the graph records full continuation.
4. Re-entry locates Q and its accepted response, so it sends no replacement model call. It returns A's original result and restores necessary current-batch effects. It determines that B remains unfinished.
5. If B has a complete suitable saved artifact, reuse it. If its local process outcome is uncertain, inspect/reconcile within the contract and stop if unresolved. Do not delete useful attempt output or blindly duplicate a process.
6. Once the entire batch is settled and applicable limits/cancellation permit, prepare the next model decision from current facts. If another legitimate later commit already made V12 current, neither A's receipt nor the old graph snapshot sets head back to V11.
7. The agent may select the older good V10 for delivery rather than the experimental V11/V12. Export uses that explicit version/scope. If inference is stopped, a host action can still package saved V10 under the export contract and honestly report its content state.

An unknown remote attempt before step 2 uses bounded model replay only when enabled and within original limits. An unknown local effect after step 3 uses effect-specific reconciliation. Their uncertainty and recovery permissions are different. Neither resets the job's accumulated budget.

<a id="q3-closure-and-implementation-order"></a>
## 12. Q3 closure and implementation order

The original Q3 discussion required authoritative records and supported transitions for the boundaries below. [Implemented Q3](../contracts/20261031_0157_CONTRACTS.md#q3-execution-recovery-and-delivery) and its later scoped recovery refinements now select them. The list preserves the design/verification rationale; it is not an unresolved first-implementation queue:

- Prepared request, attempt, and accepted reply.
- Complete batch progress, operation effect/receipt, and graph/context completion.
- Stop/waiting/cancel and export publication. It must specify:

- How new intended judgments obtain identities, how recovery finds old ones, and which entry paths may continue a prepared request.
- Which input/configuration/defaults are frozen and how same-ID/different-input inconsistencies are rejected.
- How the whole accepted batch resumes, which graph completion forms are supported, and how stale effects avoid regressing later state.
- What save/selection/export commits promise, which prepared files can finish conditionally, and how local unknown outcomes stop with useful work preserved.
- How original attempts/turn/time/cancellation state persists, including wait/backoff accounting and configured unknown-outcome replay eligibility.
- How execution stop, content claim, and actual package outcome remain distinct and how explicit continuation is interpreted.

The retained design principle is finite behavior at these boundaries. It does not require universal migration, exactly-once remote generation, generalized branch coordination, mandatory process salvage, or all-crash recovery. The four-module/six-table sketch was incomplete because it did not assign all these responsibilities. That is not an instruction to build more tables. Existing checkpointer/journal/record facilities may supply them.

The original first-increment rationale was to connect a real bounded source/scope through shared Nexus/tools, candidate preservation, save/reopen, basic capacity behavior, and specified-version export. That historical proposal is not current execution authority; [CURRENT_STATE](../../CURRENT_STATE.md#find-current-work) routes actual implementation and product verification. It should not postpone candidate retention until after the first validation failure. Nor should it postpone capacity until a document exceeds 40 pages. One inspect already reached 191,662 characters historically. Advanced DOM comparison conveniences, generalized concurrency, malformed-call extraction, cache tuning, reminders, and automatic exit packaging need not block that increment.

Later verification should inspect the actual contract boundaries and source-led saved/reopened/exported reading proportionately. Scripted mocks can exercise crash gaps and identity rules. They cannot establish model understanding, source fidelity, natural adoption, equal-quality savings, or installed desktop readiness. The old 228 checks and R1/R2 completed trials do not certify new integration. These suggested verification boundaries are not standing permission for live provider experiments.

**Historical scope consolidation:** EVT-1148 and EVT-1166 limited the then-unresolved first-version design to Q1 document/reference semantics, Q2 capacity/handoff, and Q3 persistence/recovery/stop. Those choices were subsequently closed in [CONTRACTS](../contracts/20261031_0157_CONTRACTS.md#implemented-first-version-contracts). A material new contract violation or changed human requirement can reopen the relevant boundary; its historical presence here cannot do so by itself.
