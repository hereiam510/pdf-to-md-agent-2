# Project work register

This register owns known work, selection and comparative priority, residual scope and reconsideration conditions. Issue descriptions retain why work was raised; linked task/evidence owners supply implementation and acceptance. A selected entry records its chosen scope, not an assertion that it is currently executing or unfinished. [INDEX](INDEX.md#start-by-task) locates owners; [PHASE_PLAN](PHASE_PLAN.md#delivery-route) owns phase outcomes and [CURRENT_STATE](CURRENT_STATE.md#focus-and-resume-route) owns interaction continuation. Inclusion is not execution authority.

## Selection now

Documentation organization was selected separately: [DOC-FLOW-01](#maintenance-and-coverage). This does not change the application comparison below or execute its selected batch. The application's [CRED-03-04 spec](batches/CRED-03-04/spec.md), [tickets](batches/CRED-03-04/tickets.md) and [verification](batches/CRED-03-04/verification.md) own agreement, execution and acceptance.

The credential preservation correction precedes the next source-delivery investigation because CRED-03/04 have deterministic P2 counterexamples, a small shared implementation surface and inexpensive offline acceptance. The successful state-owner design remains the baseline. [The review](reviews/RUNTIME_FINDINGS.md#credential-repair-follow-up-review-2026-11-06) and [acceptance owner](design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance) supply the evidence and completion conditions.

After that increment, reassess R01CAL-A01's complete-section/page-classification gap offline before proposing another provider interval. The investigation is not technically dependent on credentials; its position reflects the bounded correction's readiness and cost. R01/CTX-02 numerical calibration remains high-impact and needs candidate, threshold and independent-validation choices. Neither local repairs nor the Task A baseline resolves that question.

R03 is a substantial Stage C recovery gap that needs its own design; blind replay is unsafe. OBS-02/03 are measured costs whose optimization priority depends on a selected workload and threshold. UA-01-DEFAULTS concerns sparse helper routes; complete-route use does not establish sparse-route acceptance. R08/R14/R01-PACK/DIST-01 re-enter with declared Stage D destinations/distribution. Other findings retain their work-register triggers. Uncertain incidence does not dismiss a supported blocker.

Before proposing costly live work, identify the unresolved question, why cheaper checks are insufficient and how known defects affect interpretation. After each increment, reassess priorities and phase readiness. The phase title does not authorize conversion or require every unrelated bug to be cleared. Closed intervals, unselected trials and proposals grant no new execution authority.

## Development credential startup

The runtime review owns the [original findings](reviews/RUNTIME_FINDINGS.md#development-credential-startup-review-2026-11-06), [original execution evidence](reviews/RUNTIME_FINDINGS.md#credential-startup-repair-implementation-and-offline-acceptance-2026-11-06) and [follow-up counterexamples](reviews/RUNTIME_FINDINGS.md#credential-repair-follow-up-review-2026-11-06). The mechanism owner supplies [original acceptance](design/DEVELOPMENT_CREDENTIALS.md#credential-repair-acceptance) and [follow-up acceptance](design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). The entries below own selection/disposition; assigned tickets own execution progress. Actual desktop incidence and provider consequences remain unmeasured in the cited review.

| ID | Evidence / impact | Current disposition and next check |
| --- | --- | --- |
| CRED-01 | An early remembered-key decryption can replace the selected file key; see the original review and repair evidence above. | Reopen on a supported ordering/persistence regression. |
| CRED-02 | An early settings snapshot can misroute ordinary Start; see the original review and repair evidence above. | Reopen on a supported stale-settings or readiness regression. |
| CRED-03 | Default-file stat succeeds, then read ENOENT is treated as absence and selects remembered credentials. Reproduced at d370082; 66d779e blocks the same failure. P2 unintended-credential risk; incidence unmeasured. | Selected. [Task and progress](batches/CRED-03-04/tickets.md#cred-03); [scope and acceptance basis](batches/CRED-03-04/spec.md). |
| CRED-04 | Startup encryption unavailability is cached through explicit Remember saves after capability recovers; no ciphertext is saved. Reproduced at d370082; 66d779e rechecks and persists. P2 persistence/recovery failure. | Selected. [Task and progress](batches/CRED-03-04/tickets.md#cred-04); [scope and acceptance basis](batches/CRED-03-04/spec.md). |

The [comparison above](#selection-now) explains this correction's priority. The [batch spec](batches/CRED-03-04/spec.md) defines its execution boundary and authorizes no follow-on investigation.

## Runtime and engineering inventory

Evidence is inherited from linked review scopes and [current verification](INDEX.md#find-by-topic), not freshly reproduced here. R01 concrete residuals follow. R02 retains performance uncertainty and historical OS attribution after the later publication repair. R07 and H01 are not blanket open repair tasks. R03/R09 connect primarily to C, R08/R14 to D, R01/R02/R11 to B/E; other findings re-enter the phase whose selected outcome they affect.

| ID | Topic | Evidence / assessment | Current disposition and next check or revisit condition |
| --- | --- | --- | --- |
| [R01](reviews/RUNTIME_FINDINGS.md#r01--usable-context-may-be-substantially-narrower-than-the-route-can-support) | Usable context narrowed by estimation | Estimation restriction; see the linked review for the selected remedy and its tested scope. | Real limits/natural conversion benefit remain separate (CTX-01/02/03); compare residuals below. |
| [R02](reviews/RUNTIME_FINDINGS.md#r02--streaming-persistence-amplifies-work-with-chunk-count) | Per-chunk persistence and growing metadata | Persistence/metadata cost; comparisons, integrity and lifecycle evidence remain in the linked review. | Revisit production-route incidence, device writes or whole-task benefit when measured needs justify it; preserve adopted durability. |
| [R03](reviews/RUNTIME_FINDINGS.md#r03--local-process-stop-can-leave-no-supported-continuation) | Interrupted OCR/script continuation | Source-supported recovery gap; proposed “safe replay” inference rejected | Unscheduled scoped recovery design; revisit for required local-process use/interruption |
| [R04](reviews/RUNTIME_FINDINGS.md#r04--http-errors-lose-diagnostic-body-and-have-no-automatic-retry) | HTTP error diagnostics and retry | Error-body omission and terminal status handling confirmed in source | Separate diagnostic retention from replay policy; revisit for an observed error or selected receive follow-up |
| [R05](reviews/RUNTIME_FINDINGS.md#r05--raw-markdown-preservation-differs-from-safe-rendering) | Raw Markdown and active HTML | Raw preservation confirmed; downstream exploit not reproduced; proposed parser flag insufficient | Decide output/rendering threat boundary when unsafe downstream behavior is demonstrated or delivery requirements demand it |
| [R06](reviews/RUNTIME_FINDINGS.md#r06--resource-safeguards-are-incomplete) | Rendering/receive resource use | Source-supported missing resource safeguards; exhaustion not reproduced | Target resource management if source/stream size or measurements expose failure; no silent content truncation |
| [R07](reviews/RUNTIME_FINDINGS.md#r07--malformed-complete-replies-escape-intended-validation-settlement) | Malformed native reply parsing | Malformed native reply parsing; original failures and finite controls remain in the linked review. | Reopen on a supported new shape or settlement failure; broader/live-route incidence is not assumed. |
| [R08](reviews/RUNTIME_FINDINGS.md#r08--exclusive-zip-publication-depends-on-hard-link-support) | Hard-link export portability | Source-supported missing fallback; filesystem cases not executed | Unscheduled export capability work; revisit on target filesystem need/failure |
| [R09](reviews/RUNTIME_FINDINGS.md#r09--environment-inheritance-and-descendant-lifecycle-need-clearer-boundaries) | Environment inheritance and child lifecycle | Source-supported exposure/termination limits; no exfiltration or descendant test | Unscheduled least-privilege environment and process-tree analysis |
| [R10](reviews/RUNTIME_FINDINGS.md#r10--remembered-credentials-do-not-isolate-against-same-user-scripts) | Same-user access to remembered credentials | Threat-model clarification; not an established encryption flaw | Clarify expectations when reviewing trusted-script/security guidance |
| [R11](reviews/RUNTIME_FINDINGS.md#r11--verification-cost-and-long-term-storage-growth) | Integrity verification and storage growth | Repeated version verification supported; “every tool” claim too broad; no benchmark | Measure relevant workload before changing verification; retention/GC requires its own policy |
| [R12](reviews/RUNTIME_FINDINGS.md#r12--pdf-parsing-shares-the-engine-process) | In-process PDF parsing | Architectural exposure/isolation opportunity; no exploit reproduced | Revisit for crash/resource evidence or an explicit hostile-input isolation requirement |
| [R14](reviews/RUNTIME_FINDINGS.md#r14--deep-windows-file-url-assets-can-fail-to-display) | Deep Windows file-URL image paths | Identical exported package fails image decode at the tested 264-character URL pathname and works at 192 characters | Shorten newly introduced test-directory nesting; broader destination/viewer support remains a Stage D follow-up on a required long-path delivery case |
| H01 | SQLite connection lifecycle | SQLite connection lifecycle; [reconciliation evidence](reviews/RUNTIME_FINDINGS.md#observability-review-reconciliation-2026-10-29). | Do not schedule the superseded Store-close claim as another repair; revisit a new supported lifecycle defect. No general leak benchmark exists. |
| H02 | Mojibake error text | Source-confirmed string defect | Unscheduled small correction; not a Stage B prerequisite |
| H03 | Untyped local API input | Missing-key path supported by source; HTTP test not run | Unscheduled input/error-contract improvement |
| H04 | Free route parameters | Parameters can constrain tools; not all mentioned values break the loop | Decide controller-owned versus deliberately user-selected parameters |
| H05 | Long functions | Maintainability observation, not a defect by line count | Split only where responsibility/failure handling work justifies it |

## Production estimation residuals

Stable suffixes identify remaining questions under R01 without renumbering original findings. The linked R01-MOD/COUNT and R01-CAL evaluator records own execution and acceptance; numerical calibration and other residuals retain separate selection decisions. [November 1 evidence](reviews/RUNTIME_FINDINGS.md#r01-engineering-review-reconciliation-2026-11-01) and [November 4 evidence](reviews/RUNTIME_FINDINGS.md#r01-november-4-engineering-review) retain original reproductions and limits.

| ID | Evidence / impact | Next action and completion or revisit condition |
| --- | --- | --- |
| R01-MOD | Non-content metadata classification/text-preservation risk; [repair evidence](reviews/RUNTIME_FINDINGS.md#r01-mod-production-classification-increment-2026-11-06). | Reopen on a supported classification/text-preservation counterexample; calibration and upstream incidence remain separate. |
| R01-COUNT / OBS-06 | Bad-resource decoding and changed-byte/transient recovery; [repair evidence](reviews/RUNTIME_FINDINGS.md#r01-count-automatic-recovery-increment-2026-11-06). | Revisit on recovery/isolation regression or measured remaining reread/key-work impact. No latency saving is assumed. |
| R01-CAL | Numeric calibration and independently supported operating limits; [evaluator evidence](reviews/RUNTIME_FINDINGS.md#r01-cal-offline-evaluator-increment-2026-11-06), [Task A execution/acceptance/usage](verification/20261106_1408_R01CAL_TASK_A.md). | Numerical candidate/gates and independence remain open and unselected. Follow [R01CAL-A01](#context-capability-and-delivery-work) before proposing further live calibration; no further provider work, observer or trial enrollment is selected. Recorded intervals and operational preparation remain with their evidence owners. |
| R01-PACK | Frozen smoke test omits counter loading/BPE-mode assertion; no packaged failure demonstrated. | D: at next selected build verify actual frozen vocabulary/native loading, known vector and mode. |
| R01-FEEDBACK | Automatic feedback omits fallback method/reason exposed in metadata. | Unselected B/E visibility improvement; assess full payload/convergence and actual use. |
| R01-SURROGATE | Lone U+D800 fails UTF-8 serialization before either counter profile. | B input-validity investigation: trace reachable inputs and specify an honest error boundary without replacing source characters; actual user incidence unknown. |
| R01-RESERVE | Current-payload feedback and prospective admission differ; placeholder leaf counts do not bound full envelopes. | Deferred semantic/verification question: test reachable full status/reason/ID combinations when changing reservation; no demonstrated live admission failure. |

## Observer findings

OBS-01–08 alias findings #1–8 in the [observer review](verification/20261105_0220_USAGE_OBSERVATION.md#disposition-of-the-eight-pasted-findings); [later results](verification/20261105_0220_USAGE_OBSERVATION.md#source-identity-disposition-and-remaining-limits) qualify older measurements and dispositions. These concern B/E observation readiness, not dispatch authority.

| ID | Problem / evidence route | Next check or revisit condition |
| --- | --- | --- |
| OBS-01 | Comparator isolation, geometry and observer classification; evidence in the linked observer record. | Reopen on comparator loss or a supported classification counterexample. R01-MOD remains separate. |
| OBS-02 | Repeated reconstruction/preparation cost; measurements and differing claim scopes remain in the observer evidence. | Select workload/latency budget before reuse; preserve independent validations. |
| OBS-03 | Full-sink scan/linking cost; scale and measurements remain in the observer evidence. | Keyed lookup is unselected; compare at chosen scale and preserve row identity/accounting across reopen. |
| OBS-04 | Policy labels and object/byte inventories; see the observer evidence. | Reopen on extra-write evidence; no universal storage claim. |
| OBS-05 | Original cutoff and diagnostic-failure reason retained. | Reporting constraint: preserve all opportunities and distinguish diagnostic failures when selecting denominators. |
| OBS-06 | Alias of R01-COUNT; original repeated-decode measurements remain historical. | Use R01-COUNT for recovery/isolation scope and remaining I/O questions; no separate repair status. |
| OBS-07 | regex supplied transitively; no observed import failure. | Unselected direct-dependency declaration; verify when dependency maintenance is selected. |
| OBS-08 | Repair-tail layout correctly rejects with a general reason. | Unselected diagnostic-label improvement; revisit when breakdown needs a separate repair-tail category. |

## Context, capability and delivery work

[CTX agenda](discussions/REQUEST_CAPACITY.md#complete-agenda) preserves original questions. Later [contracts](INDEX.md#initial-contract-basis) and results qualify its old open-method/API wording.

| ID | Problem / phase | Next action or completion/revisit condition |
| --- | --- | --- |
| CTX-01 | B/E actual route capacity remains uncertain. | Establish supported profile or explicit unknowns from documentation/configuration/records first; no probes here. |
| CTX-02 | B/E estimation and numerical calibration; [mechanism and trial](design/CONTEXT_MANAGEMENT.md), [observer evidence](verification/20261105_0220_USAGE_OBSERVATION.md). | R01 residuals and production recalibration remain open; see UA-01/02. Current error is not endorsed. |
| CTX-03 | B/E operational compaction goals/thresholds remain open beyond trial rules. | Distinguish real pressure from avoidable compaction with saved payloads before policy changes. |
| CTX-04 | A/B explicit representations, whole-batch coordination and natural coavailability; [implementation evidence](history/IMPLEMENTATION_HISTORY.md#complete-context-update-coordination). | Revisit general benefit with a selected dependency/source case; preserve native pairings and agent choice. |
| CTX-05 | B exact-version/index/field/range access; [editing evidence](history/IMPLEMENTATION_HISTORY.md#document-editing-increment). | Real-use applicability is separate evidence work; reopen on supported selector/completeness/editing failure. |
| CTX-06 | B natural-compaction handoff quality/progress not broadly validated. | Selected source-led check must preserve originals, pending work and version identities; smaller summaries alone do not pass. |
| CTX-07 | A coordination and bounded accepted-evidence recovery; [coordination evidence](history/IMPLEMENTATION_HISTORY.md#complete-context-update-coordination), [recovery evidence](verification/20261031_1917_RECOVERY_ACCEPTANCE.md). | Preserve regressions on changed paths; reopen on supported first/reopen discrepancy; R03 is separate. |
| R01CAL-A01 | Complete-section delivery gap, P2; unfinished outside-scope classification can obstruct the requested complete edit despite remaining allowance. [Finding and observed outcome](verification/20261106_1408_R01CAL_TASK_A.md#finding-recommendation-and-deferrals). | Remedy unselected; recommend bounded offline diagnosis of large outside-scope classification and guidance before proposing B. Preserve a truthful whole-PDF map, autonomy and source scope; no manual A repair or Continue. |
| CTX-08 | B broader native/scanned/mixed source acceptance unverified. | Select a meaningful source class after relevant readiness assessment and live authority; no conversion now. |
| FD-01 | Independent figure delivery and source-grounded adjacent text; [local evidence](verification/20261101_0033_FD01_LOCAL.md), [two-page evidence](verification/20261101_0103_FD01_TWO_PAGE_LIVE.md). | Full fourteen-page/captionless validation deferred; revisit on separately selected scope. [Historical closeout](decisions/NURSING.md#historical-fourteen-page-task-closeout-2026-11-01) retains its original acceptance and limitation; it does not repair the old output. |
| UA-01 | B/E usage-anchoring trial; [repair scope/results](reviews/RUNTIME_FINDINGS.md#ua-01-repair-implementation-increment-2026-11-06). | Real enrollment, operational results and an excerpt-only blind-design exercise remain unselected; preserve default-off/mock-only rules. Original review/plan retain their history. |
| UA-01-R1 | P2 counted-score evidence defect; [repair evidence](reviews/RUNTIME_FINDINGS.md#ua-01-repair-implementation-increment-2026-11-06). | Reopen on a supported counted-score evidence counterexample; use the owner for revalidation/reduction and required-evidence conditions. |
| UA-01-R2 | P2 optional-counter faults affecting ordinary preparation; [repair evidence](reviews/RUNTIME_FINDINGS.md#ua-01-repair-implementation-increment-2026-11-06). | Reopen on a supported fallback/ordinary-guard regression; use the owner for payload, obstruction, accounting, recovery and reopen requirements. |
| UA-01-DEFAULTS | Sparse raw route and materialized defaults can hash differently (`180` versus `180.0`) and reject offline membership; complete job-route fixtures work. | [Observed boundary](reviews/RUNTIME_FINDINGS.md#ua-01-defaults--sparse-offline-route-identity-boundary), deferred outside R1/R2. Assess consistent default normalization when direct sparse-route construction is required; no ordinary default app enrollment path or live incidence is established. |
| UA-02 | Operational observation deferred; offline diagnostics prove neither real opportunity incidence nor savings. | Select workload, route/accounting/image profile, denominators, diagnostic-failure treatment, duration and latency/storage threshold; compare R01 and OBS-02/03 before separate execution authorization. |
| DIST-01 | D installed readiness unverified; old packages lack current source changes. | Select target/destination and check actual installed build with R08/R14/R01-PACK; packaging not selected here. |

## Diagnostics and retained options

[F evidence](reviews/RUNTIME_FINDINGS.md#observability-review-reconciliation-2026-10-29) and [option details](PROPOSED_CHANGES.md) retain mechanisms and rationale. Optional entries are not adopted requirements.

| ID | Current disposition / impact | Next check or revisit condition |
| --- | --- | --- |
| F03 | B/E supported timing instrumentation gap. | Select diagnostic question; cover fresh/reused/skipped/recovery paths and unknown crash tails. |
| F04 | B/E stopped-poll recovery copies: source-supported cost, magnitude unmeasured. | Measure responsiveness before optimization; preserve coherent no-write inspection and exact receipt/graph selection. |
| OPT-DIAG | Detail scans/reloads: source-supported, unmeasured impact. | Profile chosen slow detail before reuse/lazy access/bounds; preserve full access/integrity labels. |
| OPT-LANGFUSE | External telemetry/export unselected. | Revisit missing diagnostics; decide privacy, hosting, retention and lifecycle. |
| OPT-PREPARE | Dedicated prepare-only action unselected. | Revisit repeated previews/credential-free preparation need; define durable no-dispatch lifecycle. |
| OPT-PRETOOLS | Pre-tools execution stop unselected. | Revisit required operator boundary; define accepted evidence, continuation and no new effects. |
| OPT-FAILSTOP | Multi-dispatch fail-stop unselected. | Revisit bounded evaluation needs; preserve receipts/consumption without routine per-request approval. |
| OPT-PIN-READ | Reading without persistent pin is an available strategy. | Assess one-off retention if useful; ordinary reads can remain in history. |
| OPT-PIN-EXPIRY | Agent-selected lifetime/release unselected. | Revisit demonstrated unnecessary retention; define success/failure/replay/reopen semantics first. |

## Revisit conditions and aliases

| IDs | Basis / evidence route | Reopen condition |
| --- | --- | --- |
| R13 | [Settlement/recovery evidence](reviews/RUNTIME_FINDINGS.md#r13--accepted-result-settlement-consistency-selected-2026-10-28). | Supported eligibility/receipt/acceptance/first-reopen discrepancy; no general local-effect recovery claim. |
| SC01, SC02, SC03, SC04 | [Streaming review scopes and follow-up evidence](reviews/RUNTIME_FINDINGS.md#streaming-contract-review-reconciliation-2026-10-30). | New supported identity/semantic/usage/diagnostic failure. Historical incomplete raw remains unaccepted. |
| F01, F02, F02-D01, F02-D02, F02-D03, DT01 | Diagnostic access/provenance/isolation/typing [evidence](reviews/RUNTIME_FINDINGS.md). | New affected failure; preserve finite evidence and its broader unverified limits. |
| F05, F06 | F05 maps R07; F06 maps H01/H02/H03. | Follow those items without duplicate repairs. |
| DOC-01–13 | Earlier [reorganization](reviews/DOCUMENTATION_REORGANIZATION_2026-10.md) and [structure evidence](reviews/20261031_0157_DOCUMENTATION_STRUCTURE.md). | New preservation/navigation contradiction; historical checks are not rerun here. |
| DOC-14–19 | [Conformance evidence](reviews/20261031_1917_DOCUMENTATION_CONFORMANCE.md#disposition). | Lost basis/meaning, contradictory summary or wrong acceptance mapping. |
| DOC-ORG-20261106 | [Original organization evidence](verification/20261106_2300_PROJECT_ORGANIZATION.md), qualified by the [follow-up review](reviews/20261106_2307_ORGANIZATION_REVIEW.md#assessment). | Retain the original scope; route its remaining owner-duplication finding to [DOC-ORG-R1](#maintenance-and-coverage), without maintaining a second repair status. |
| ORG-01 | [Organization correction evidence](reviews/20261031_1907_PROJECT_ORGANIZATION.md#correction-checks-and-closeout). | Relevant ownership/path regression. |
| History-pressure coordination | [Adoption and evidence basis](decisions/CONTEXT_MANAGEMENT.md#history-pressure-admission-retained-option-and-adoption-basis). | Supported contract violation; expiry is separate. |

## Maintenance and coverage

**DOC-FLOW-01:** Selected by the current user request to apply progressive disclosure, separate planning from interaction continuation, consolidate redundant navigation and verify reading/update/resumption with GPT-6.1 Sol low agents. [Spec](batches/DOC-FLOW-01/spec.md), [tickets](batches/DOC-FLOW-01/tickets.md) and [verification](batches/DOC-FLOW-01/verification.md) own the detailed scope, progress and acceptance. Revisit on a demonstrated missing dependency, stale consumer, duplicate live fact or lost continuation question. This is separate from application implementation.

**DOC-ORG-R1:** Selected by the user on 2026-11-07 for document-owner reconciliation and daily-workflow entry maintenance. [Original review](reviews/20261106_2307_ORGANIZATION_REVIEW.md#doc-org-r1--remaining-mutable-status-and-result-mirrors), [adopted batch scope](batches/DOC-ORG-R1/spec.md), [execution](batches/DOC-ORG-R1/tickets.md) and [acceptance](batches/DOC-ORG-R1/verification.md) provide the detailed owners. Revisit on a supported stale current claim, duplicate owner or broken continuation route. Application item priorities remain in this register; phase outcomes stay in PHASE_PLAN. This selection does not execute the credential assignment.

Reassess affected items when discoveries, decisions or evidence change their selection, priority, residual scope or reconsideration. A task/verification change alone does not require another completion/status sentence here. Keep IDs stable; cross-reference duplicates and retain original aliases. Add unfinished adopted capabilities and new review families. Leave residual scope visible after bounded acceptance; reassess phase judgments and continuation only when their facts change. Original assessments retain their historical scope; the register owns current item dispositions. README and INDEX link here without copying the list.

Initial coverage reconciles maintained R/H/F/SC/CTX navigators, observer #1–8/latest results, current state/phase/handoff, retained options and named conformance/organization closeouts. This is recorded-evidence reconciliation, not a fresh code audit or discovery of all unknown defects. No private task stores or historical permissions were used as execution authority.

## Batch layout organization

DOC-LAYOUT-01 records the earlier layout migration: [spec](batches/DOC-LAYOUT-01/spec.md), [tickets](batches/DOC-LAYOUT-01/tickets.md), [verification](batches/DOC-LAYOUT-01/verification.md). Current maintenance selection is under [maintenance and coverage](#maintenance-and-coverage).
