# Preserved pre-migration WORK_ITEMS

Captured 2026-11-07, Asia/Hong_Kong, from the working tree at f1929b7 with inherited document edits. Historical scope and permissions only; current owners are in [the catalogue](../INDEX.md#batch-documents).

# Project work register

Updated 2026-11-06, Asia/Singapore. This is the central view of known outstanding work and current item dispositions. [INDEX](../INDEX.md#start-development) is the entrance; [PHASE_PLAN](../PHASE_PLAN.md#next-increment-selection) owns outcomes and sequencing; [CURRENT_STATE](../CURRENT_STATE.md#find-current-work) owns readiness and active work. Detailed linked owners retain explanations, original observations and verification. Inclusion is not implementation authority or a requirement to fix everything before delivery.

## Selection now

[Task A evidence](../verification/20261106_1408_R01CAL_TASK_A.md) owns the closed interval and partial-delivery result. [Credential execution evidence](../reviews/RUNTIME_FINDINGS.md#credential-startup-repair-implementation-and-offline-acceptance-2026-11-06) owns the original repair results; the individual dispositions follow below.

**Selected next increment: CRED-03/04 fixes, offline regressions and records.** The [d370082 review](../reviews/RUNTIME_FINDINGS.md#credential-repair-follow-up-review-2026-11-06) supports the core CRED-01/02 fixes but reproduces two P2 preservation regressions. Both corrections are selected and pending under the [active implementation handoff](../REVIEW_HANDOFF.md#credential-follow-up-implementation-handoff-2026-11-06). After this bounded repair, reassess the recommended, separately unselected offline R01CAL-A01 diagnosis before proposing B. B stays ready with zero attempts and unselected. Numerical calibration, certified holdout provenance and candidate/gates remain open. Production calibration/full source access are unchanged; observer and usage-anchoring enrollment remain off. Provider calls, conversions, packaging, publication, cleanup and subagents remain excluded. R03, OBS-02/03, UA-01-DEFAULTS and distribution retain their triggers.

R03 remains a separate substantial recovery candidate. OBS-02/03 are measured costs but no operational threshold/workload is selected. R08/R14/R01-PACK connect to declared distribution/destination needs. Important alternatives and revisit conditions remain below. A Stage B title does not direct immediate conversion; Task A's specifically approved interval is now closed, and further live work needs its own selection.

## Development credential startup

CRED-01/02 are repaired at their recorded offline scope. The later CRED-03/04 P2 regressions are reproduced and selected, with implementation pending. The runtime review owns the [original evidence](../reviews/RUNTIME_FINDINGS.md#development-credential-startup-review-2026-11-06) and [follow-up counterexamples](../reviews/RUNTIME_FINDINGS.md#credential-repair-follow-up-review-2026-11-06); the mechanism owner supplies [original](../guides/INTEGRATION_AND_MODEL_BOUNDARY.md#credential-repair-acceptance) and [follow-up acceptance](../guides/INTEGRATION_AND_MODEL_BOUNDARY.md#credential-follow-up-acceptance). Actual desktop incidence and provider consequences remain unmeasured. Task A remains valid at its closed scope.

| ID | Evidence / impact | Current disposition and next check |
| --- | --- | --- |
| CRED-01 | An early remembered-key decryption can finish after file loading and replace the selected file key; a later Start can use stale credentials. | Locally complete at the [recorded offline scope](../reviews/RUNTIME_FINDINGS.md#credential-startup-repair-implementation-and-offline-acceptance-2026-11-06). Both candidate-read readiness orders preserve file identity; valid-file remembered decryption is excluded. Replacement/Clear, persistence and current-key Start checks pass. Reopen on a supported ordering/persistence regression. |
| CRED-02 | The renderer retains an early `hasKey=false` snapshot after loading succeeds, so the Start guard unnecessarily opens Connection settings. | Locally complete in the same increment. Actual delayed-file and delayed-settings-response renderer cases reach ordinary local Start without a settings detour; loading controls, stale replies and manual/error paths pass. Reopen on a supported stale-settings or readiness regression. |
| CRED-03 | Default-file stat succeeds, then read ENOENT is treated as absence and selects remembered credentials. Reproduced at d370082; 66d779e blocks the same failure. P2 unintended-credential risk; incidence unmeasured. | Selected, implementation pending. Narrow benign absence to initial discovery; prove discovered-file failure blocks engine/Start with zero fallback while missing-default/manual and explicit-path controls remain correct. |
| CRED-04 | Startup encryption unavailability is cached through explicit Remember saves after capability recovers; no ciphertext is saved. Reproduced at d370082; 66d779e rechecks and persists. P2 persistence/recovery failure. | Selected, implementation pending. Refresh capability within the existing save owner/queue; prove recovery plus encrypted restart and newer Clear/replacement/Remember-off protection across delayed capability/encryption. |

The [phase selection rationale](../PHASE_PLAN.md#next-increment-selection) compares this correction with R01CAL-A01, calibration, recovery and distribution. The [handoff](../REVIEW_HANDOFF.md#credential-follow-up-implementation-handoff-2026-11-06) defines its execution boundary; it authorizes no follow-on work.

## Runtime and engineering inventory

Evidence is inherited from linked review scopes and [current verification](../CURRENT_STATE.md#verification-basis), not freshly reproduced here. R01 concrete residuals follow. R02 retains performance uncertainty and historical OS attribution after the later publication repair. R07 and H01 are not blanket open repair tasks. R03/R09 connect primarily to C, R08/R14 to D, R01/R02/R11 to B/E; other findings re-enter the phase whose selected outcome they affect.

| ID | Topic | Evidence / assessment | Current disposition and next check or revisit condition |
| --- | --- | --- | --- |
| [R01](../reviews/RUNTIME_FINDINGS.md#r01--usable-context-may-be-substantially-narrower-than-the-route-can-support) | Usable context narrowed by estimation | Archived restriction measured; selected estimator and compressed-resource fallback repair locally verified; route-wide/causal scope open | Selected local remedy complete; real limits/natural conversion benefit remain separate (CTX-01/02/03) |
| [R02](../reviews/RUNTIME_FINDINGS.md#r02--streaming-persistence-amplifies-work-with-chunk-count) | Per-chunk persistence and growing metadata | Fixed cursor plus scoped FULL SQLite handle has reproducible same-byte local receive/settlement benefit; final integrity/Stop/process-kill/legacy/563-case/delivery checks pass | Production switch adopted and locally verified; actual route incidence/device writes/whole-task benefit unknown |
| [R03](../reviews/RUNTIME_FINDINGS.md#r03--local-process-stop-can-leave-no-supported-continuation) | Interrupted OCR/script continuation | Source-supported recovery gap; proposed “safe replay” inference rejected | Unscheduled scoped recovery design; revisit for required local-process use/interruption |
| [R04](../reviews/RUNTIME_FINDINGS.md#r04--http-errors-lose-diagnostic-body-and-have-no-automatic-retry) | HTTP error diagnostics and retry | Error-body omission and terminal status handling confirmed in source | Separate diagnostic retention from replay policy; revisit for an observed error or selected receive follow-up |
| [R05](../reviews/RUNTIME_FINDINGS.md#r05--raw-markdown-preservation-differs-from-safe-rendering) | Raw Markdown and active HTML | Raw preservation confirmed; downstream exploit not reproduced; proposed parser flag insufficient | Decide output/rendering threat boundary when unsafe downstream behavior is demonstrated or delivery requirements demand it |
| [R06](../reviews/RUNTIME_FINDINGS.md#r06--resource-safeguards-are-incomplete) | Rendering/receive resource use | Source-supported missing resource safeguards; exhaustion not reproduced | Target resource management if source/stream size or measurements expose failure; no silent content truncation |
| [R07](../reviews/RUNTIME_FINDINGS.md#r07--malformed-complete-replies-escape-intended-validation-settlement) | Malformed native reply parsing | Historical parser failures superseded by current safeguards; 38 finite Runtime/Nexus/persist/reopen controls pass on 2026-10-31 | Selected malformed-container settlement gap locally verified; broader shapes and live-route incidence remain unverified |
| [R08](../reviews/RUNTIME_FINDINGS.md#r08--exclusive-zip-publication-depends-on-hard-link-support) | Hard-link export portability | Source-supported missing fallback; filesystem cases not executed | Unscheduled export capability work; revisit on target filesystem need/failure |
| [R09](../reviews/RUNTIME_FINDINGS.md#r09--environment-inheritance-and-descendant-lifecycle-need-clearer-boundaries) | Environment inheritance and child lifecycle | Source-supported exposure/termination limits; no exfiltration or descendant test | Unscheduled least-privilege environment and process-tree analysis |
| [R10](../reviews/RUNTIME_FINDINGS.md#r10--remembered-credentials-do-not-isolate-against-same-user-scripts) | Same-user access to remembered credentials | Threat-model clarification; not an established encryption flaw | Clarify expectations when reviewing trusted-script/security guidance |
| [R11](../reviews/RUNTIME_FINDINGS.md#r11--verification-cost-and-long-term-storage-growth) | Integrity verification and storage growth | Repeated version verification supported; “every tool” claim too broad; no benchmark | Measure relevant workload before changing verification; retention/GC requires its own policy |
| [R12](../reviews/RUNTIME_FINDINGS.md#r12--pdf-parsing-shares-the-engine-process) | In-process PDF parsing | Architectural exposure/isolation opportunity; no exploit reproduced | Revisit for crash/resource evidence or an explicit hostile-input isolation requirement |
| [R14](../reviews/RUNTIME_FINDINGS.md#r14--deep-windows-file-url-assets-can-fail-to-display) | Deep Windows file-URL image paths | Identical exported package fails image decode at the tested 264-character URL pathname and works at 192 characters | Shorten newly introduced test-directory nesting; broader destination/viewer support remains a Stage D follow-up on a required long-path delivery case |
| H01 | SQLite connection lifecycle | Cited unclosed Store paths superseded by R02 owned-close semantics | Specific claim retired by source/history review; no new general leak benchmark; see [observability reconciliation](../reviews/RUNTIME_FINDINGS.md#observability-review-reconciliation-2026-10-29) |
| H02 | Mojibake error text | Source-confirmed string defect | Unscheduled small correction; not a Stage B prerequisite |
| H03 | Untyped local API input | Missing-key path supported by source; HTTP test not run | Unscheduled input/error-contract improvement |
| H04 | Free route parameters | Parameters can constrain tools; not all mentioned values break the loop | Decide controller-owned versus deliberately user-selected parameters |
| H05 | Long functions | Maintainability observation, not a defect by line count | Split only where responsibility/failure handling work justifies it |

## Production estimation residuals

Stable suffixes identify remaining questions under R01 without renumbering original findings. R01-MOD/COUNT and the R01-CAL offline evaluator are locally complete at their recorded scopes; numeric calibration and other residuals remain open/unselected. [November 1 evidence](../reviews/RUNTIME_FINDINGS.md#r01-engineering-review-reconciliation-2026-11-01) and [November 4 evidence](../reviews/RUNTIME_FINDINGS.md#r01-november-4-engineering-review) retain original reproductions and limits.

| ID | Evidence / impact | Next action and completion or revisit condition |
| --- | --- | --- |
| R01-MOD | Historical non-content metadata false-image/rejection defect corrected in production F; both protocols/profiles and native/error controls verified offline. | Locally complete at [recorded scope/source](../reviews/RUNTIME_FINDINGS.md#r01-mod-production-classification-increment-2026-11-06). Reopen on a supported classification/text-preservation counterexample; calibration and upstream incidence remain separate. |
| R01-COUNT / OBS-06 | Deterministic bad-resource decoding is reused independently by production/shadow loaders; changed bytes and transient faults recover automatically. | Locally complete at [recorded source/acceptance](../reviews/RUNTIME_FINDINGS.md#r01-count-automatic-recovery-increment-2026-11-06). Resource rereads/key work remain; revisit on recovery/isolation regression or measured remaining I/O impact. No latency saving is claimed. |
| R01-CAL | Offline evaluator verified; production numeric profile unchanged. Task A baseline interval closed with source-checked transcription and consistent **partial** delivery; B is ready with zero exposure and unselected. | [Execution/acceptance/usage](../verification/20261106_1408_R01CAL_TASK_A.md); nine normal sends, 233.188 active seconds, all nine native usage/acceptance checks, no candidate fitting or holdout claim. Follow R01CAL-A01 before proposing B; numerical candidate/gates and independence remain open. No further provider work, observer or trial enrollment is selected. |
| R01-PACK | Frozen smoke test omits counter loading/BPE-mode assertion; no packaged failure demonstrated. | D: at next selected build verify actual frozen vocabulary/native loading, known vector and mode. |
| R01-FEEDBACK | Automatic feedback omits fallback method/reason exposed in metadata. | Unselected B/E visibility improvement; assess full payload/convergence and actual use. |
| R01-SURROGATE | Lone U+D800 fails UTF-8 serialization before either counter profile. | B input-validity investigation: trace reachable inputs and specify an honest error boundary without replacing source characters; actual user incidence unknown. |
| R01-RESERVE | Current-payload feedback and prospective admission differ; placeholder leaf counts do not bound full envelopes. | Deferred semantic/verification question: test reachable full status/reason/ID combinations when changing reservation; no demonstrated live admission failure. |

## Observer findings

OBS-01–08 alias findings #1–8 in the [observer review](../verification/20261105_0220_USAGE_OBSERVATION.md#disposition-of-the-eight-pasted-findings); [later results](../verification/20261105_0220_USAGE_OBSERVATION.md#source-identity-disposition-and-remaining-limits) qualify older measurements and dispositions. These concern B/E observation readiness, not dispatch authority.

| ID | Current disposition / evidence | Next check or revisit condition |
| --- | --- | --- |
| OBS-01 | Comparator isolation, unreadable geometry and additional observer false-image classification corrected/offline verified. | Closed within scope; reopen on comparator loss or a supported classification counterexample. R01-MOD remains separate. |
| OBS-02 | Repeated reconstruction remains; complete warm preparation overhead about 0.62–0.95 s. Some assemblies check different claims. | Select workload/latency budget before reuse; preserve independent validations. |
| OBS-03 | Full-sink scan remains; median linking 1.04–1.25 s with 5,000 unrelated rows/two matches. | Keyed lookup is an unselected optimization; compare at chosen scale and preserve row identity/accounting across reopen. |
| OBS-04 | Policy-byte label corrected; actual object/byte inventories supplied. | Closed for measured fixtures; reopen on extra-write evidence, not a universal storage claim. |
| OBS-05 | Original cutoff and diagnostic-failure reason retained. | Reporting constraint: preserve all opportunities and distinguish diagnostic failures when selecting denominators. |
| OBS-06 | Same locally completed decoding/recovery repair as R01-COUNT; original three-decode evidence remains historical. | Preserve automatic changed-byte/transient recovery and independent caches. Remaining reads are explicit, without a measured latency claim. |
| OBS-07 | regex supplied transitively; no observed import failure. | Unselected direct-dependency declaration; verify when dependency maintenance is selected. |
| OBS-08 | Repair-tail layout correctly rejects with a general reason. | Unselected diagnostic-label improvement; revisit when breakdown needs a separate repair-tail category. |

## Context, capability and delivery work

[CTX agenda](../discussions/REQUEST_CAPACITY.md#complete-agenda) preserves original questions. Later [contracts](../CONTRACTS.md) and results qualify its old open-method/API wording.

| ID | Current disposition / phase | Next action or completion/revisit condition |
| --- | --- | --- |
| CTX-01 | B/E actual route capacity remains uncertain. | Establish supported profile or explicit unknowns from documentation/configuration/records first; no probes here. |
| CTX-02 | Local estimator implemented; calibration inaccurate; usage-anchoring v1 adopted and observer offline increment complete. | R01 residuals and production recalibration remain open; see UA-01/02. Current error is not endorsed. |
| CTX-03 | B/E operational compaction goals/thresholds remain open beyond trial rules. | Distinguish real pressure from avoidable compaction with saved payloads before policy changes. |
| CTX-04 | A/B explicit representations and whole-batch coordination implemented; general natural coavailability benefit unverified. | Revisit with a selected dependency/source case; preserve native pairings and agent choice. |
| CTX-05 | B exact-version/index/field/range access implemented with local checks. | Remaining real-use applicability is evidence work; reopen on supported selector/completeness/editing failure. |
| CTX-06 | B natural-compaction handoff quality/progress not broadly validated. | Selected source-led check must preserve originals, pending work and version identities; smaller summaries alone do not pass. |
| CTX-07 | A coordination and bounded accepted-evidence recovery locally verified. | Preserve regressions on changed paths; reopen on supported first/reopen discrepancy; R03 is separate. |
| R01CAL-A01 | B complete-section completion gap, P2; the first complete edit failed on unprocessed scope, then the agent ended partial with 274 pages unclassified despite remaining allowance. | [Finding/evidence](../verification/20261106_1408_R01CAL_TASK_A.md#finding-recommendation-and-deferrals). Remedy unselected; recommend bounded offline diagnosis of large outside-scope classification and guidance before proposing B. Preserve a truthful whole-PDF map, autonomy and source scope; no manual A repair or Continue. |
| CTX-08 | B broader native/scanned/mixed source acceptance unverified. | Select a meaningful source class after relevant readiness assessment and live authority; no conversion now. |
| FD-01 | Guidance implemented; bounded two-page source-led acceptance complete; full fourteen-page/captionless validation deferred. | Revisit on separately selected scope; [accepted historical closeout](../decisions/NURSING.md#historical-fourteen-page-task-closeout-2026-11-01) does not repair the old output. |
| UA-01 | B/E adopted trial implemented offline against current F; the two independent-review P2 gaps are locally repaired/verified. | [Repair scope/results](../reviews/RUNTIME_FINDINGS.md#ua-01-repair-implementation-increment-2026-11-06); original review and plan remain historical. Default off/mock-only and normative rules unchanged. No real enrollment/operational result or excerpt-only blind-design exercise. |
| UA-01-R1 | P2 at review: orphan/native score evidence could still qualify reporting. | Locally corrected in [the selected repair](../reviews/RUNTIME_FINDINGS.md#ua-01-repair-implementation-increment-2026-11-06). Every candidate score is revalidated before reduction; unavailable required evidence independently bars clean review. Both-protocol settled cohorts, unchained loss, contradictory usage/margins, redundant minima, late attribution and reopen preserve exposures. Reopen on a supported counted-score evidence counterexample. |
| UA-01-R2 | P2 at review: expected optional counter faults interrupted ordinary preparation; now reproduced offline and corrected. | [Repair/results](../reviews/RUNTIME_FINDINGS.md#ua-01-repair-implementation-increment-2026-11-06): Pf/Pa faults preserve exact ordinary payload/disposition or legitimate obstruction, durable reason and zero trial debit/veto/slot; actual warm-F/cold-anchor loader, recovery and reopen controls pass. Reopen on a supported fallback/ordinary-guard regression. |
| UA-01-DEFAULTS | Sparse raw route and materialized defaults can hash differently (`180` versus `180.0`) and reject offline membership; complete job-route fixtures work. | [Observed boundary](../reviews/RUNTIME_FINDINGS.md#ua-01-defaults--sparse-offline-route-identity-boundary), deferred outside R1/R2. Assess consistent default normalization when direct sparse-route construction is required; no ordinary default app enrollment path or live incidence is established. |
| UA-02 | Operational observation deferred; offline diagnostics prove neither real opportunity incidence nor savings. | Select workload, route/accounting/image profile, denominators, diagnostic-failure treatment, duration and latency/storage threshold; compare R01 and OBS-02/03 before separate execution authorization. |
| DIST-01 | D installed readiness unverified; old packages lack current source changes. | Select target/destination and check actual installed build with R08/R14/R01-PACK; packaging not selected here. |

## Diagnostics and retained options

[F evidence](../reviews/RUNTIME_FINDINGS.md#observability-review-reconciliation-2026-10-29) and [option details](../PROPOSED_CHANGES.md) retain mechanisms and rationale. Optional entries are not adopted requirements.

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

## Closed scopes and aliases

| IDs | Current disposition / basis | Reopen condition |
| --- | --- | --- |
| R13 | Bounded settlement/recovery locally verified; [evidence](../reviews/RUNTIME_FINDINGS.md#r13--accepted-result-settlement-consistency-selected-2026-10-28). | Supported eligibility/receipt/acceptance/first-reopen discrepancy; no general local-effect recovery claim. |
| SC01, SC02, SC03, SC04 | Locally corrected within [streaming review scopes](../reviews/RUNTIME_FINDINGS.md#streaming-contract-review-reconciliation-2026-10-30), including SC02 follow-up. | New supported identity/semantic/usage/diagnostic failure. Historical incomplete raw remains unaccepted. |
| F01, F02, F02-D01, F02-D02, F02-D03, DT01 | Finite diagnostic access/provenance/isolation/typing scopes locally complete; [evidence](../reviews/RUNTIME_FINDINGS.md). | New affected failure; broader unverified scope does not erase finite results. |
| F05, F06 | F05 maps R07; F06 maps H01/H02/H03. | Follow those items without duplicate repairs. |
| DOC-01–13 | Earlier [reorganization](../reviews/DOCUMENTATION_REORGANIZATION_2026-10.md) and [structure](../reviews/20261031_0157_DOCUMENTATION_STRUCTURE.md) corrections closed within their recorded scopes. | New preservation/navigation contradiction; historical checks are not rerun here. |
| DOC-14–19 | [Conformance increment closed](../reviews/20261031_1917_DOCUMENTATION_CONFORMANCE.md#disposition). | Lost basis/meaning, contradictory summary or wrong acceptance mapping. |
| DOC-ORG-20261106 | [Updated-skill organization](../verification/20261106_2300_PROJECT_ORGANIZATION.md) owns the original preservation and navigation checks; [follow-up review](../reviews/20261106_2307_ORGANIZATION_REVIEW.md#assessment) qualifies completion. | Preservation/navigation scope passed; full one-owner conformance remains open through DOC-ORG-R1 below. |
| ORG-01 | [Organization correction closed](../reviews/20261031_1907_PROJECT_ORGANIZATION.md#correction-checks-and-closeout). | Relevant ownership/path regression. |
| History-pressure coordination | Adopted and implemented; [decision](../decisions/CONTEXT_MANAGEMENT.md#history-pressure-admission-retained-option-and-adoption-basis). | Supported contract violation; expiry is separate. |

## Maintenance and coverage

**DOC-ORG-R1:** Open; specification and local ticket plan prepared at the user's request. Implementation has not started. [Review evidence](../reviews/20261106_2307_ORGANIZATION_REVIEW.md#doc-org-r1--remaining-mutable-status-and-result-mirrors) establishes the defect; the [batch specification](../WORK_ITEMS.md#doc-org-r1-specification) and [tickets](../WORK_ITEMS.md#doc-org-r1-tickets) below own the proposed correction and execution plan. This documentation follow-up does not change application priorities or authorize the credential repair.

Update affected items with discoveries, decisions and evidence in the same authorized increment. Keep IDs stable; cross-reference duplicates and retain original aliases. Add unfinished adopted capabilities and new review families. Leave partial scope visible after bounded closure and reconcile phase/current-state summaries. Original assessments retain their historical scope; the register owns current item dispositions. README and INDEX link here without copying the list.

Initial coverage reconciles maintained R/H/F/SC/CTX navigators, observer #1–8/latest results, current state/phase/handoff, retained options and named conformance/organization closeouts. This is recorded-evidence reconciliation, not a fresh code audit or discovery of all unknown defects. No private task stores or historical permissions were used as execution authority.

### DOC-ORG-R1 specification

Prepared 2026-11-06, UTC+08:00. Scope is inferred from the current reorganization discussion and the user's request for specs/tickets. This is a ready planning proposal under the existing [ownership decision](../decisions/DOCUMENTATION.md#updated-skill-organization-2026-11-06), not permission to execute the repair. No unresolved material method choice is identified. Baseline: `f1929b7` plus the uncommitted organization review and its CURRENT_STATE/INDEX/WORK_ITEMS links; preserve the unrelated DEVELOPMENT_GUIDE change. Recheck actual working state before implementation.

**Outcome:** a maintainer can change a current item disposition, correct an execution observation or select a different validation scope without updating redundant prose copies of that same fact. Readers can still find the substantive reasons, requirements, results and historical limits from the project entrance.

**Scope and method:** correct the reviewed WORK_ITEMS credential/Task A passages and INDEX figure-delivery row, then inspect their directly connected active restatements in CURRENT_STATE, REVIEW_HANDOFF and the credential/evidence owners. Resolve only redundant representations of these same facts, preserving independently necessary design/implementation distinctions. The individual work-item entries own current dispositions and next/revisit actions; original execution records own run observations; PHASE_PLAN owns comparative sequencing; INDEX owns navigation. Selection summaries may link items and explain distinct selection facts, but must not duplicate their pending/completed states. A copied result list becomes an exact evidence link, not a shorter copied result list.

Historical snapshots, source collections, dated reviews and original execution observations remain intact. Preserve unique impact, rationale, caveats, known failures, uncertainty, identifiers and explicit unimplemented-target labels. Do not turn historical evidence into an active status owner or leave link chains with no substantive answer. No application, skill, dependency, private-data, retention or remote change is included. This batch neither implements CRED-03/04 nor starts a conversion. It requires no new tracker, document hierarchy or subagent.

**Acceptance criteria — planned, not executed:**

| ID | Condition and expected outcome | Discriminating check |
| --- | --- | --- |
| A1 | A hypothetical CRED-03 completion changes its disposition in one item owner; other active destinations remain truthful through links. | Trace the credential selection/introduction/rows, catalogue, handoff and mechanism labels. Distinguish an independently necessary mechanism change from a copied status sentence. Record every surviving occurrence and its role. |
| A2 | A hypothetical correction to Task A's send/time/acceptance observation has one execution-evidence owner; the register retains its independent disposition, impact and next action. | Follow the Task A evidence-to-register route and search affected active owners for copied measurements/results. Do not change real measured values during the exercise. |
| A3 | A hypothetical selection of broader FD-01 validation changes its disposition once; catalogue links and historical two-page evidence remain valid. | Trace INDEX → work item → decision/execution evidence. Neither rewrite the closed historical interval nor falsely imply that a newly selected scope has passed. |
| A4 | Every removed active passage retains any unique meaning in an appropriate substantive owner. Existing historical evidence and unrelated files remain unchanged. | Compare actual entry and final content; account for reasons, qualifications and counterexamples, not only matching words. Check protected file identities and required old anchors. |
| A5 | The corrected records work together and the batch verdict matches evidence. | Follow README/AGENTS → INDEX → register/phase/state and each A1–A3 route; run `python tools/docs/check_docs.py` and whitespace checks. Record remaining limitations and actual reviewed state. Link success alone does not satisfy A1–A4. |

Use review-only hypothetical changes or disposable local copies for A1–A3; do not publish fabricated statuses or measurements. Detailed execution evidence belongs in a new dated verification record when the repair is actually run, with related reruns grouped there. This specification section owns the combined batch acceptance verdict; the verification record supplies observations and links back here. Do not copy that verdict into README/INDEX or the historical review. All A1–A5 must be satisfied before this item can close; ticket completion alone is insufficient. No acceptance verdict is asserted by this plan.

### DOC-ORG-R1 tickets

All tickets are assigned to the main agent for future execution. Assignment denotes responsibility, not a running task or delegation. The order is sequential because the tickets edit shared documentation and depend on settled owner locations. Ticket progress lives only in this table; criteria are referenced rather than copied.

| Ticket | Work and deliverable | Dependency | Acceptance | Execution state |
| --- | --- | --- | --- | --- |
| DOC-ORG-R1-T1 | Identify the reviewed facts' current owners and correct WORK_ITEMS status/result duplication. Account for unique material before replacing passages with links. Produce a concise before/after ownership mapping with the eventual verification evidence. | Implementation selection; preserve entry working changes first | A1, A2, A4 | Not started |
| DOC-ORG-R1-T2 | Correct INDEX and directly connected active references using T1's ownership mapping. Preserve necessary target/implementation labels and stable historical routes; keep unrelated topics out of the batch. | T1 | A1, A2, A3, A4 | Not started |
| DOC-ORG-R1-T3 | Check the integrated result with the change simulations, semantic comparison and navigation checks; correct scoped failures, record evidence and assess combined acceptance here. Reassess distinct readiness/phase implications through owner links. | T2 | A1–A5 | Not started |

When implementation is selected, the main agent owns all three tickets through integrated acceptance, without routine handoffs between them. Unexpected loss, an ambiguous fact owner or a requirement change must be resolved before claiming closure; ordinary link and prose repairs remain within the method. Applicable local checkpoint policy is handled at delivery, preserving unrelated work; this planning request performs no Git mutation or remote issue creation.
