# R01CAL-A02 metadata-only agent exercise specification

## Status and authority

Specified 2026-11-07, Asia/Hong_Kong, following the user's request to "Proceed to write the specs" for the discussed two-stage sequence. The user previously selected Task A's recorded model/settings baseline, the per-case ceilings below, and no added semantic no-progress heuristic. [The discussion](../../discussions/REQUEST_CAPACITY.md#metadata-only-agent-exercise-specification-discussion-2026-11-07) preserves those choices; [specification selection](../../discussions/REQUEST_CAPACITY.md#two-stage-specifications-selected-2026-11-07) records the later instruction. This file defines the first stage; [R01CAL-A03](../R01CAL-A03/spec.md) defines the conditional fresh-conversion stage.

The subsequent instruction, "Proceed to create the tickets," selected the [local task plan](tickets.md), following the [planning discussion](../../discussions/REQUEST_CAPACITY.md#two-stage-local-tickets-selected-2026-11-07). That planning instruction started no preparation helpers, synthetic application tasks or model calls. R01CAL-A01 remains the completed diagnosis batch; this is a distinct behavioral exercise for the same original finding.

The preceding 2026-11-07 instruction selected **R01CAL-A02-T1 only** in the current checkout: prepare, offline-validate and freeze both cases, verify supported controls/evidence paths without provider calls, maintain progress/evidence/continuation, then stop. It superseded the earlier preparation prohibition only for that ticket. [T1 verification](verification.md#t1-offline-preparation-and-freeze-2026-11-07) owns its operational evidence and limits.

The preceding instruction separately selected **R01CAL-A02-T2 only** and authorized the two frozen model-backed cases, small then large, under the unchanged baseline and finite ceilings below. It required reconciliation of T1/prior attempts, no repetition, complete evidence and the specified blocker/Stop rules without coaching, tuning, automatic reruns or resets. [T2 verification](verification.md#t2-finite-paired-execution-2026-11-07) owns those execution observations and their original stopping boundary.

The latest instruction selects **R01CAL-A02-T3 only**: account for both retained cases and all A1–A7 criteria, inspect exact maps/content/assets/selected versions, make fresh named reads and actual synthetic exports, preserve originals, and update progress/continuation. No model call or production repair is permitted. [T3's integrated review](verification.md#t3-integrated-review-and-combined-outcome-2026-11-07) owns the assessment. Stop before A03's separate transition review.

## Outcome and evidence basis

Determine whether the app's agent can autonomously finish truthful page classification through the unchanged interface when requested content is already saved, comparing small and large excluded complements. The [diagnosis](../R01CAL-A01/verification.md#diagnosis-acceptance) and its [follow-up acceptance](../R01CAL-A01/verification.md#recommendation-and-follow-up-acceptance) motivate this design: executable metadata saves and historical visibility are established at their recorded scope, but autonomous use and the cause of Task A's partial stop remain unresolved.

This is a finite behavioral check, not a new conversion, reliability benchmark, historical replay or calibration study. Fresh short histories deliberately remove transcription work and accumulated Task A context. Success cannot prove that the same behavior would occur under historical context pressure or explain the earlier stopping decision. The original Task A artifact remains partial and untouched. [Stage B](../../PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources) retains its full source-delivery acceptance.

The governing owners are [Q1 and complete claims](../../design/DOCUMENT_MODEL.md#q1-document-schema-and-commit), [merge/validation](../../design/DOCUMENT_MODEL.md#edits-and-validation), [commit and replay](../../design/DOCUMENT_MODEL.md#commit-and-replay), [exact access](../../design/DOCUMENT_MODEL.md#exact-saved-document-and-evidence-access), and [runtime limits/settlement](../../design/RUNTIME_AND_DELIVERY.md#shared-limits-and-transport-behavior). A missing update never means exclusion. Physical disposition, printed label, content claim, run stop reason and package consistency remain distinct.

## Paired cases

| Case | Source inventory | Requested physical scope | Initial saved map | Expected final map |
| --- | --- | --- | --- | --- |
| Small control | 20 synthetic pages | 11–15 | Five included; every other page unprocessed; partial claim | Five included; 1–10 and 16–20 outside scope with meaningful notes |
| Large case | 290 synthetic pages | 11–15 | Five included; every other page unprocessed; partial claim | Five included; 1–10 and 16–290 outside scope with meaningful notes |

Prepare fresh isolated sources, stores and seed versions. Both cases use identical included synthetic page content, blocks, source provenance, distinct printed labels, registered image bytes and retained original bytes; the extra excluded inventory is the intended scale difference. Keep `none` and `unknown` printed labels distinguishable. The seed has no known content gap and has valid provenance for all included pages, but its unprocessed complement prevents a complete claim. It is fixture input, not an agent-produced conversion or a reference answer for the missing classifications.

Use ordinary application tools and the ordinary system/tool guidance. A short task instruction identifies the existing partial version, the physical scope, the requirement to preserve saved content/labels/assets, and the desired complete selected version. Do not supply a per-page answer, exclusion-note template, successful T2 arguments, developer script, prescribed sequence or matching historical transcription. The agent may read originals or saved data, use full/index/field/range access, save in one or several edits, and choose its reconstruction scope. Acceptance checks the preserved result rather than mandating a particular call form. Trusted host scripts stay off with the selected baseline.

Run the small control first, then the large case, each once, if execution of both is later selected. Freeze both source manifests, initial instructions, settings and acceptance before the first Start. The second case receives no first-case history, solution, feedback or revised prompt. An ordinary behavioral partial/failure is retained and does not itself cancel the second control; an evidence-integrity, shared setup, preservation or unresolved-outcome problem stops further dispatch for assessment. Do not tune between cases or replace an unsuccessful case.

## Selected baseline and finite ceilings

The user's choices reuse the [recorded Task A configuration](../../verification/20261106_1408_R01CAL_TASK_A.md#identities-and-preserved-conditions) as a comparison target, not its closed permission or unused allowance. Before a later authorized execution, verify the actual mapping/settings without silent substitution. A historical alias is not proof of the present upstream model identity.

| Setting | Selected requirement |
| --- | --- |
| Model / protocol / effort | `cliproxy/gpt-6.1-sol`, Chat Completions through the existing Nexus route, `reasoning_effort: low` |
| Context / output / image allowance | 131,072 / 8,192 / 4,096; vision on; `bpe_proxy_v1`; production calibration and compaction policy unchanged |
| Request waiting | Task A's non-streaming 180-second complete-response deadline |
| Physical app sends | At most 12 per case; at most 24 across the pair. Normal, compaction and response-correction sends share these limits. |
| Known active time | At most 1,200 seconds per case; at most 2,400 across the pair |
| Wall-time Stop threshold | 1,500 seconds from each Start; at most two Start-to-Stop intervals, excluding intervening offline review |
| Starts / replay | One Start per case; one attempt per request; unknown-outcome replay off; no automatic Continue, replacement, extension or transfer of unused allowance |
| Existing response repair | Preserve Task A's two-response-repair setting and its ordinary episode semantics; repairs share total sends/time |
| No-progress policy | No added semantic heuristic or repeated-tool quota. Repetition can use only the remaining agreed sends/time; it receives no assistance, reset or extension. |
| Optional mechanisms | Trusted scripts, observer and usage-anchoring trial remain off |

The current payload builder sends the output setting as `max_completion_tokens` for Chat Completions. Record the actual frozen field and native finish/usage observations; local reservation, requested output cap, serialized bytes and provider behavior are not interchangeable. A large one-call map need not fit a single reply for multi-save completion to remain possible. Do not raise output allowance or require one-call completion to obtain a pass.

The [existing response-repair mechanism](../../design/RUNTIME_AND_DELIVERY.md#continuation-feedback-and-delivery-settlement) handles defined text-only/handoff cases; it is not semantic tool-loop detection. The user selected relying on that mechanism plus the finite ceilings rather than introducing observer judgment about three unchanged turns. No-progress outcomes can therefore be budget-limited and remain useful results. Do not Stop merely because a legitimate read or optional tool choice differs from the developer's expected strategy.

Stop on a terminal report (complete, partial or waiting), user Stop, a limit, terminal provider/runtime failure, acceptance/storage conflict, or unresolved remote/local outcome. Do not answer a model question mid-case or supply repair steps; record it and close the case at its actual boundary. Ordinary recoverable domain-validation errors remain available for autonomous correction inside the same interval. Operator monitoring enforces the wall threshold with the supported Stop path; record observation gaps, actual Stop latency and any in-flight tail. Thresholds are not claims of instantaneous cancellation or exact upstream spending limits.

No new purchase, top-up or paid fallback is proposed. Before live selection, verify the existing subscription/metering basis from authorized configuration/user facts; any changed monetary exposure needs an explicit ceiling. Preserve unknown upstream retries, completion, usage and fee attribution. Request counts are not a monetary estimate.

## Preparation and verification flow

1. Reconcile Git/source/schema/lockfile identities and inherited work. Use the existing pinned environment. Resolve the current supported task-seeding, execution, observation, Stop and named read/export paths; no direct database patching of originals or bypass of ordinary document validation. If the fixture cannot be prepared through existing supported interfaces, report that specific prerequisite before changing production code.
2. Create fresh synthetic inputs and valid partial seed versions only within a later selected preparation scope. Store them and full logs in a new short ignored `.local/` run under [artifact storage](../../ARTIFACT_STORAGE.md#ownership-and-locations). Retain expected-map/preservation oracles outside agent-visible task material. Keep prior T2 evidence and real Task A/B stores separate and unchanged. Preparation makes no provider call, and seeded content is labeled developer preparation.
3. Verify both seeds, mappings, output field, limits and input-access boundaries offline. Bind the finite future interval to actual task/source/settings identities, confirm applicable provider authority and ensure monitoring/Stop is available. Preparation readiness does not dispatch automatically.
4. If later selected, execute each case through the ordinary agent path without guidance changes, fault injection or routine prompting. Retain frozen inputs, complete native responses, rejected candidates, accepted calls, operation receipts, versions, reports and observed usage/time. Record all interventions and partial/failed boundaries.
5. After settlement, compare the selected immutable version with its seed and source inventory, open it through a fresh supported named reader, and inspect its synthetic export. These checks require no additional model call. Where execution leaves no deliverable, report unavailable downstream checks rather than manufacture a final version. No actual GUI reopen or installed-product claim follows from an API reader check.

## Acceptance and interpretation

These criteria separate validity of the experiment from success of the agent. A preserved partial/failure can complete the selected evidence exercise; it cannot pass metadata completion. The eventual verification owner records per-case outcomes and any missing required evidence.

| ID | Condition and expected observation | Discriminating check |
| --- | --- | --- |
| <a id="a1"></a>A1 | Both cases start with attributable comparable inputs and no successful answer/history leakage. | Freeze source/seed/instruction/settings hashes before either Start; inspect actual model-input/access boundaries and label all developer preparation. |
| <a id="a2"></a>A2 | Autonomous success covers every physical page truthfully. | Inspect exact keys/dispositions/notes against the declared scope, including 10/11, 15/16/17 and the final page; check zero unprocessed entries, valid included provenance, no invented omission and no known gap. Counts or a successful receipt alone do not pass. |
| <a id="a3"></a>A3 | Existing useful content and metadata survive. | Compare ordered block IDs/text/provenance, Markdown, title/scope, printed labels, unrelated page fields, image/original bytes and retained seed/candidates. Deliberate reconstruction remains permitted but must preserve this exercise's requested result. |
| <a id="a4"></a>A4 | Claimed completion selects the actual durable output. | Require a complete saved version and matching terminal report; compare its fresh named read and actual ZIP members/bytes/relative asset links. Separate any package/check failure from agent behavior. A saved complete map followed by partial/waiting reporting is not full autonomous success. |
| <a id="a5"></a>A5 | The interval remains finite and unaided. | Audit sends, request kinds, attempts, active/wall time, stop/report boundaries, intervention log, unchanged limits and no automatic restarts. Optional reads/method choices alone are not failures. |
| <a id="a6"></a>A6 | Failure explanations follow attributable evidence. | Retain original arguments, native finish/usage, exact returned and subsequent frozen feedback, accepted/rejected identities and final maps. Distinguish output truncation, admission rejection, domain-validation repair, waiting/partial stopping and infrastructure/evidence failure; preserve unknowns. |
| <a id="a7"></a>A7 | Comparison does not overstate its scope. | Account for both predefined cases without selective reruns or tuning. Report success, partial/failure and unperformed coverage separately, with historical-causality, reliability, source-fidelity, route-capacity and cost limits. |

If both cases complete, this finding alone supplies no reason for a production repair. If small succeeds and large fails, scale becomes a candidate contributor, not a demonstrated cause: inspect actual output/admission/feedback evidence before selecting a change. Specific repeated difficulty locating remaining work can motivate feedback work; an identified expression/output obstacle can motivate compact scope expression or existing multi-save use. If both fail, one waits, or the pattern differs, retain the supported observations without forcing a single explanation. One attempt per case cannot establish frequency or general reliability. No branch automatically authorizes a remedy, full conversion, numerical calibration or another run.

## Readiness and continuation

This specification defines the unchanged agreement. [T1's preparation evidence](verification.md#t1-offline-preparation-and-freeze-2026-11-07), [T2's execution evidence](verification.md#t2-finite-paired-execution-2026-11-07) and [T3's integrated assessment](verification.md#t3-integrated-review-and-combined-outcome-2026-11-07) own their operational observations and limits; do not use this specification as a second readiness ledger. If preparation reveals a material conflict, retain the evidence and resolve the affected agreement before dependent execution; do not silently change cases, settings, preservation or acceptance.

The [transition contract](../R01CAL-A03/spec.md#transition-from-r01cal-a02) owns the review needed before the fresh Task A-like conversion. It distinguishes autonomous correction, an invalidating defect and an unexplained behavioral failure; an error-free first stage is not required. A03 has its own scope and allowance, outside this batch's two cases. If a later instruction authorizes both stages and the transition conditions are met, continue within that authority without a routine extra approval round. An instruction selecting A02 alone does not start A03.

The [local tickets](tickets.md#dependency-and-execution-overview) define progress and dependencies. The current instruction ends after [T3](tickets.md#r01cal-a02-t3) and its records, before A03's transition review. Earlier T2 authority is closed; T3 permits no model call, Start/Continue/replay, replacement case or result repair. No real-task operation, calibration/observer work, dependency installation, packaging, cleanup, publication or production repair follows. Preserve the earlier diagnosis, original attempts, historical allowances and existing checkout work.
