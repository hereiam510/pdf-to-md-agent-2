# GYN-01 local tickets

## Authority and ownership

Updated 2026-11-15 (Asia/Hong_Kong) under the [T2/T3 instruction](../../discussions/SOURCE_CONVERSION.md#t2-and-t3-selected-2026-11-15). T2/T3 and draft-PR updates are authorized within the spec's single-interval limits.

The [spec](spec.md) owns requirements and limits, this file owns tasks/progress, and [verification](verification.md) owns actual evidence and the combined verdict. The main agent is the operator, source reviewer and single document integrator; the app's converter produces content during T2. No auxiliary-agent assignment is made. Use the project's [local ticket policy](../../../AGENTS.md#batch-documents-and-ticket-mode).

## Dependency and execution overview

| Ticket | Contribution and criteria | Dependency / execution gate | Progress |
| --- | --- | --- | --- |
| [GYN-01-T1](#gyn-01-t1--prepare-and-bind-the-fresh-task) | Prepare an attributable task and controls: [A1](spec.md#a1), [A6](spec.md#a6), [A7](spec.md#a7), [A8](spec.md#a8) | Preparation authorization | Complete; [readiness and handoff](verification.md#t1-preparation-and-publication) |
| [GYN-01-T2](#gyn-01-t2--execute-the-single-bounded-interval) | Conduct the finite interval and preserve evidence: [A1](spec.md#a1), [A5](spec.md#a5), [A6](spec.md#a6), [A8](spec.md#a8) | Current T1 readiness and live-run authorization | Complete; [interval evidence](verification.md#interval-accounting-and-context) |
| [GYN-01-T3](#gyn-01-t3--verify-the-source-and-delivery-and-assess-the-batch) | Source/delivery review and whole-spec assessment: [A1–A8](spec.md#planned-acceptance) | Settled T2 evidence and review/reopen/export authorization | Complete; [source/delivery assessment](verification.md#a1a8-assessment) |

T1 → T2 → T3 is the normal sequence. T3 follows partial/failed as well as successful intervals. If preparation blocks Start or no interval occurs, assess available evidence and mark live/content/delivery checks unperformed. A completed review ticket need not mean accepted conversion. No ticket implies product repairs, another interval or an extension.

## Shared interfaces and evidence handoff

Use the spec's [scope/instruction](spec.md#converter-facing-instruction), [fresh-task conditions](spec.md#fresh-task-and-independence-conditions), [route/limits](spec.md#agreed-route-and-finite-interval) and [OCR condition](spec.md#english-ocr-prewarming) directly; do not copy their values into another checklist.

| Handoff | Required record |
| --- | --- |
| T1 → T2 | Source/import hash and inventory; task/workspace/profile; revision, lockfiles and executed build; exact instruction identity; applied/read-back non-secret settings and mapping/billing basis; fresh counters/history; OCR warm-cache/resource and synthetic-only evidence with setup time; destinations, monitoring/Stop checks; readiness/blockers and execution instruction. |
| T2 → T3 | Same preparation/task identity; actual frozen inputs/settings; attempts, retries/repairs, receipts and usage; monitoring/Stop/settlement/tails; report and selected version if present; other versions/candidates; interventions and retained artifacts, including any in-run OCR loading. |

Keep actual evidence in [verification](verification.md) and link it from the progress table when execution occurs. Preserve private originals, complete logs and unsuccessful attempts under [artifact storage](../../ARTIFACT_STORAGE.md#ownership-and-locations). Reviewer material and synthetic preparation outputs stay outside converter history/inputs. Missing evidence remains explicit; neither a summary nor another ticket file replaces originals.

## GYN-01-T1 — Prepare and bind the fresh task

**Operator checklist** — complete the [preparation gate](spec.md#preparation-before-an-authorized-start), then stop before Start:

1. **Bind the basis.** Pin the integrated build and relevant checks; preserve older useful builds. Recheck source identity/inventory and the exact scope instruction. Reuse unchanged evidence; run only missing or change-justified zero-inference controls.
2. **Create the isolated task.** Establish the new workspace/profile and short Windows destination. Verify immutable import equality, zero counters/history and absent requests/versions/delivery. Preserve Task B and exclude reviewer answers, reference outputs and old conversion content.
3. **Configure, then verify.** Bind current non-secret route/model/subscription facts and ordinary credential loading. Apply every selected route/limit/switch value to the stopped fresh task, including explicit streaming and retry policies; read back and compare. Do not inherit an absent waiting policy, change global defaults or probe the provider. Reconcile mismatches before proceeding.
4. **Prewarm English OCR.** Follow the [synthetic-only procedure](spec.md#english-ocr-prewarming), including cache reuse without a second download and retained resource/log/timing evidence. Confirm conversion-task counters/history remain untouched. Failed warmup blocks readiness; no silent cold-cache substitution.
5. **Check controls.** Establish readable activity, durable logging, supported Stop, monitor cadence/gap recording and destination usability. Record the timing basis and how Stop will be issued at the specified threshold.
6. **Record readiness.** Save the T1 handoff with evidence for every gate or the precise blocker. Identify necessary remedy/checks without silently expanding the task. Recheck affected claims if the build, source, settings, cache or controls change.

**Done:** all preparation gates have attributable evidence and a readiness conclusion. Missing bindings or controls remain blocked. T1 creates no model request: T2 captures the first actual frozen payload.

## GYN-01-T2 — Execute the single bounded interval

**Operator checklist** — use the [finite interval and exit rules](spec.md#agreed-route-and-finite-interval):

1. **Start once.** Recheck T1's identity/readiness and the execution instruction. Start monitoring first; record Start and the wall-time Stop threshold. Supply only the selected source/scope and ordinary product guidance.
2. **Observe and retain.** Capture actual frozen input/settings and every attempt, retry, repair, usage record and context event. Stop dependent dispatch on an unexplained settings mismatch. Automatic retries share the aggregate budget. Let the converter choose methods; give no reviewer answers, coaching, manual assembly or mid-run question response.
3. **Enforce exits.** Apply Stop/terminal/pause/limit/conflict rules, retain unknown upstream/local outcomes and keep the selected streaming mode. No manual Retry/Continue, fallback, replacement run, counter reset or allowance transfer. Do not force context pressure or optional-tool use.
4. **Preserve settlement.** Record terminal reason/report, selected version if any, timing/tails, interventions, useful versions/candidates and native evidence. If settlement is uncertain, record that uncertainty and stop dispatch. Pass available evidence to T3 even after a failed/partial interval.

**Done:** an attributable interval/outcome record, or a precise unperformed/uncertain-outcome record. This is execution evidence, not content acceptance. Classify transport/runtime observations separately from content discrepancies under the spec.

## GYN-01-T3 — Verify the source and delivery and assess the batch

**Review checklist** — assess the complete [A1–A8 matrix](spec.md#planned-acceptance):

1. Bind source/task/build and the agent-selected immutable version. If none was selected/saved, state that; do not silently substitute a version or assemble candidates. Preserve earlier and partial work.
2. Check every included text region and all page-map entries under A2/A3. Use the degraded-extraction interpretation and logical page-8 boundary; A3 tests supplied-scope compliance, not independent discovery. Record discrepancies by source location and saved block.
3. Check every figure under A4/FD-01: complete units/panels/edges, source composition, applicable native pixels/originals, complete captions/credits and searchable associated labels/relationships. Faithful images do not excuse wrong text; retain uncertainty and separate agent explanations.
4. Actually reopen/select and export the same version without inference. Compare inventories/bytes, applicable originals, all relative links and rendered Markdown/HTML/images at the declared destination. Verify attempts and active time remain unchanged. Record blocked operations rather than inferring acceptance from receipts.
5. Audit validity, assistance, finite controls, actual context coverage and all usage/setup costs under A1/A5/A6/A8. A transport failure can leave content unassessed; distinguish cause uncertainty from the overall incomplete result. Preserve the historical comparison limits.
6. Record every criterion's result or explicit missing/unperformed/inapplicable coverage and the combined verdict. Identify concrete findings, impact, uncertainty and the bounded next action. Update distinct work-selection/phase/continuation facts only when changed; content/code repair and another interval require their applicable scope.

**Done:** a source-led, whole-spec assessment supported by identities and evidence. A failed/partial verdict may complete this ticket, but cannot be called accepted conversion.

## Planning closeout and resume

The existing three tickets include the supported corrections and selected OCR preparation condition; no separate software-repair ticket was needed. [Documentation correction verification](verification.md#documentation-correction-review) preserves the planning result. The authorized interval and review are recorded in [T2/T3 verification](verification.md#t2-and-t3-execution). Resume from the [completion-gap assessment](verification.md#gyn-t3-01--unfinished-final-self-check), not Start or Continue. [PR #4](https://github.com/hereiam510/pdf-to-md-agent-2/pull/4) delivered these records: at the user's request ("Merge PR #4") it was marked ready and merged at head `9cc9ee3` as merge commit `d34a896` on 2026-11-15 (13:16 UTC); the branch was kept. The GYN-01 post-run review (`5fc3a5e`) follows in [PR #5](https://github.com/hereiam510/pdf-to-md-agent-2/pull/5). No follow-up implementation or live ticket is selected.
