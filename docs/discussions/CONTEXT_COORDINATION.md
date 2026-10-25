# Context management: discussion and design convergence

Last synthesis: 2026-10-26, Asia/Hong_Kong (UTC+08:00), including the four selected policies, integrated-design adoption through D20 and subsequent authorized implementation in D21. Exact timestamps for the earlier inline exchanges and supplied reviewer texts are unavailable; the sequence below preserves their relative order. Recording them today does not date their original statements or rerun their evidence.

## Current view and authority

The user wants the app to support its own agent in completing faithful PDF conversion, with little routine human intervention. The context capability must let the agent keep useful evidence and work, organize growing history, understand an update's outcome, and revise a non-admitted choice. Keeping bytes safe while leaving every continuation path blocked is not sufficient product functionality.

The user has selected **whole-batch context commitment, no automatic partial application after structural failure, explicit agent reselection of uncommitted intent after new instructions, and B for confirmed necessary-content excess**. Under B, a still-valid complete candidate becomes `needs_agent_revision` at the applicable unfrozen decision boundary once current settings confirm that its necessary content is too large. Prior feasibility and the active policy's ability to deliver the diagnosis do not change that disposition; later capacity increases do not restore automatic eligibility. The user has also adopted the [integrated target design](../design/CONTEXT_UPDATE_COORDINATION.md) for separated decision responsibilities, request plans, disposition/delivery, explicit reuse and recovery. These policies are implemented in the subsequently authorized D21 increment. Executable CONTRACTS and CURRENT_STATE separate effective behavior, local evidence and unverified real-model outcomes.

| Status | What is established |
| --- | --- |
| Explicit user requirements | Fidelity, full original access, agent autonomy, admission before policy effect, preservation on failure, immutable receipts, consumption and frozen-request boundaries; no need for backward compatibility. |
| Implementation | Baseline `a484b9b` is preserved; design checkpoint `c1e6fcc` precedes the complete coordination implementation. CURRENT_STATE owns final checks and source identity. |
| Confirmed remaining findings | CC-R1/2/3 below, supported by retained local reproductions and controls. They do not establish original-data damage or general conversion-quality failure. |
| Selected target policies | D15 selected whole-batch admission, no automatic partial context revision or older pending fallback after structural failure, and explicit reselection after new instructions. D18 selects B for confirmed necessary-content excess. D20 adopts the integrated design; content retention is distinct from continued execution eligibility. |
| Adopted target and remaining authority | One coordinator, purpose-specific plans, a one-sided necessary-cost proof distinct from complete request admission, durable disposition independent of delivery, current-base explicit reuse, and restoration before reevaluation. Unknown estimates and history-only pressure are not B. No known unresolved policy choice directly blocks a bounded implementation, and implementation was subsequently authorized and completed within that scope. |
| Current authorization | Implement the adopted complete context capability with local mocks, preservation/rendering verification, documentation and scoped local checkpoints. No provider calls, push, release or independent feature expansion. |

The user previously authorized a shrinking-proposal implementation batch, then said **“stop, revert all changes”** and returned to review/design discussion. That canceled implementation is not revived here. The initial D12 recording began with maintained files clean and three pre-existing review scratch files. D15 preserved that uncommitted documentation. D20 preserved the existing uncommitted discussion/design/navigation work and scratch while keeping code/tests at baseline. D21 separately authorizes implementation, preserving those records in a scoped checkpoint and leaving scratch unrelated. The old repository is outside this work.

This topic record owns positions and their evolution. The target design owns the integrated adopted target and explicitly unselected alternatives or implementation details. [DECISIONS](../DECISIONS.md) records adopted choices and their implementation status; [CONTRACTS](../CONTRACTS.md) remains the executable runtime contract; [CURRENT_STATE](../CURRENT_STATE.md) owns implementation/evidence; [PHASE_PLAN](../PHASE_PLAN.md) owns delivery order. Later implementation should reconcile those owners rather than maintain a second competing contract.

## Sources and evidence boundaries

The earlier context/framework discussion is already explained in [foundations](../reference/01-foundations-and-frameworks.md), [context/state reasoning](../reference/02-context-state-and-evidence.md), the [context guide](../design/CONTEXT_AND_EVIDENCE.md) and the [source index](../reference/SOURCE_INDEX.md). Those records retain their original export scope and historical status. This file adds the subsequent coordination discussion; it does not silently append new events to that older export.

Eight supplied reviewer texts and selected existing local evidence are preserved verbatim in the [context coordination source index](../reference/context-coordination-sources/INDEX.md), with original paths, byte sizes and SHA-256 hashes in its manifest. D12 imported the first five; D15 added the policy-comparison review; D20 adds the two later required-capacity reviews without altering the previous 18 source entries or copied bytes. Source texts remain untrusted reference material. Four retained reproducer scripts are inert `.py.txt` sources, not new product tests or execution instructions.

The two inline reviews referred to below as Reviewer A and Reviewer B were pasted directly in the user conversation. Their substantive arguments are preserved here, but no separately exported complete transcript or original reviewer identity is claimed. Other reviewers are identified by their supplied document, not assumed to be the same person/agent. The main assistant's intervening assessments are reconstructed from this conversation, not represented as verbatim reviewer text.

A reviewer reported a Canvas report named `pdfmd_context_independent_review_zh-TW.md`, `discussion/05-main-response-b.md`, 2,734 package items, and document checks of 28 documents/1,946 links/356 mappings. Those external report bodies and fresh run logs were not available in the local material used here. Related retained package/reproduction records can support their own narrower claims; they do not independently verify every claimed fresh rerun.

### Existing evidence, not rerun during this recording

| Evidence | Supported conclusion | Limit |
| --- | --- | --- |
| Baseline and package record | Previous re-review recorded 615 matching source files and package SHA-256 `7904478a3d2468a90aa07260a7631a7b12753ba74c6a93c14502c82f2d4fe25e` for `.local/review-2026-10-25-context-capacity-wait.zip` | The new documentation additions are not in that old package. No new application snapshot was built here. |
| Original increment, retained in CURRENT_STATE | 248 Python cases and six context desktop cases passed in that implementation batch | These were not rerun here; passing fixtures did not cover the later identified interactions. |
| Re-review `pytest.log` | Sixteen completion dots at 100%, consistent with the prior report of sixteen related tests | The compact log has no duration/count summary. Do not invent one. |
| `findings.json` | Six shrinking-update blocks and two final-handoff reserve discrepancies across both protocols | The R2 same-candidate control is expressly hypothetical and not graph committed. |
| `guard-control.json` | Four controls: unchanged old full pin or notes remain in a fitting actual compaction request, and a handoff is accepted | Index and notes modes were controlled; do not claim this particular control ran range mode too. |
| `savings.json` | Two protocol-specific positive-savings counterexamples, with narrower control coverage | Shows unnecessary deferral, not measured final quality loss or live model rereading. |
| `existing-tests.log` and `adjacent-results.json` | 52 selected tests passed in 81.22 seconds; eight additional ordered notes/release-repin Runtime controls passed with reopen and durable consumption | Local scripted responses. The eight controls do not independently repeat renderer or complete PDF export acceptance. |
| `package.log` | Historical verification reports 1,003 file hashes, 615 source/613 before-source files, both patch reconstructions and twelve saved/reopened/exported deliveries | Reusing this log does not re-render the app or re-verify all artifacts now. Synthetic delivery preservation is not natural model autonomy. |

All recent evidence above was available as existing 2026-10-25 review material. The import does not establish precise original execution timestamps. Documentation work checks source-copy integrity, links/structure and diffs; it does not rerun application tests, renderers, Nexus or fault injection. D14's code/test inspection is separate from these inherited execution records. D15 and D20 add no new application-behavior evidence. The later review discussions qualify existing tests: the capacity-wait fixture ultimately raises capacity to 500000, rather than demonstrating restoration to the original capacity; raw-pin correction/delivery uses scripted model responses and does not establish a real agent's autonomous success rate. New policy acceptance remains to be executed after implementation authorization.

## Chronology of material positions

### D01. Product direction and the two context responsibilities

**User:** focus context management first, leaving network management for later; Nexus is used for monthly subscription access, and routes may include other model providers. Do not base portability on direct pay-as-you-go API features. Treat native compaction/background retrieval/cancellation as unavailable baseline dependencies across these routes, rather than claiming every upstream implementation lacks them.

**User and main assistant:** distinguish ordinary history compaction from retrieving and selecting file/evidence content. The user agreed to a hybrid: the agent chooses what matters and methods to obtain it; the app asks for organization under capacity pressure. Preserve traceable originals. Releasable exact evidence can leave transient input; active instructions, unresolved dependencies and unsaved useful work require protection, including first saving exact content and keeping retrieval references.

**Effect:** fidelity and autonomy are outcomes; compaction and memory mechanisms serve them. Forum comments, papers and library claims are evidence to cross-check, not authority. This discussion did not select a fixed OCR/text/script sequence or let summaries become the only originals.

### D02. Framework fit and persistence responsibilities

**User:** consider Pi, LangChain/LangGraph/LangMem, Deep Agents, SDKs and self-built code; maturity may improve reliability, but actual fit and needed modifications matter. Full reconstruction is allowed.

**Main assistant, after successive critiques:** Pi-first and `create_agent`-first rankings were provisional and sometimes used asymmetric comparisons. Frameworks do not supply the app's source fidelity, document editing, candidate reuse, evidence provenance and context policy semantics automatically. The later implementation baseline became a small direct LangGraph StateGraph, shared native Nexus service and tool dispatcher, SQLite metadata and immutable large files.

**Effect:** reuse proven execution/storage responsibilities without making a framework, hook name, table count or short loop an immutable product requirement. Provider-specific compaction is not required. The detailed alternatives remain in the existing historical owners; no framework/API capability was freshly researched for this record.

### D03. Source preservation, explicit representations and admission before effect

**User:** capacity feedback must occur before a pin formally takes effect; failure must preserve the previously usable context. Explicit choices include an index/reference, visible image, exact selected range/fields, and complete text or explicitly requested raw bytes. Full content cannot silently become an index.

**User/main recommendation:** combine explicit representation with preflight of actual input, including tools, images and output allowance. Keep ordinary one-time reading available; reads can remain in history. Do not yet add automatic pin expiry or a complex pin manager. An already oversized active context is a separate obstruction, not something rejected-pin feedback magically solves.

**Effect:** explicit representations and pre-admission were implemented in the earlier Phase 3 closeout. [DESIGN_OPTIONS](../DESIGN_OPTIONS.md) separately records available read strategies and unselected lifetime ideas. Later historical-pressure coordination preserves otherwise feasible intent across compaction.

### D04. Repeated coordination increments and the capability-level review

**Mainline implementation:** context progress/replay, existing-task settings/time, PDF coordinates/stencil/provenance, pending context proposals, independent settlements and bounded result feedback were added in authorized increments. The capacity-wait/projection batch is recorded at `a484b9b`.

**Reviewer and main re-review:** ordinary fitting paths and many recovery/artifact cases pass, yet related supported operations still fail. The user asked for review of the complete capability, not another sequence of isolated line fixes. Findings should separate reproduced defects, code-supported risks, product policy choices and untested assumptions; AI agreement is not proof.

**Effect:** retain the existing evidence but reassess shared decision rules. After canceling an implementation attempt, the user explicitly requested review-only architecture/policy discussion and then a concrete design comparison before implementation. No canceled development authority remains current.

### D05. Three reproduced findings and the limits of their controls

These are **CC-R1/2/3 of the a484b9b context-capacity review**, not the unrelated R1/R2 identifiers in the old network reference archive.

| Finding | Mechanism and observed effect | Revised inference |
| --- | --- | --- |
| CC-R1: shrinking intent cannot reach feasible compaction | `Context.compact_request` uses old policy's stripped **normal** input plus unknown outcome reserve as an early compaction gate. At unchanged capacity, full-to-index/range and shorter notes remain pending but `coordinate`/`prepare` stop. | Actual compaction can fit while that unrelated normal template does not. Old-policy controls preserve the full 10.5 KB content and accept a handoff. General temporary shorter pending views/notes are not established as necessary. |
| CC-R2: final handoff judged against a different outcome | `apply_handoff` includes a reserved future outcome while `resolve` tests specific applied feedback. One synthetic handoff fits the latter and fails the former. | Share the target snapshot and specific presentation. The 60-unit difference is local estimation, not provider tokens; no general budget-exhaustion claim follows. |
| CC-R3: negative reference substitution masks a positive saving | Normal `admit_group` filters growing substitutions; compaction `has_body_savings` compares an all-reference form. Short argument growth hides result-only savings. | The baseline projection unnecessarily covers the next batch and defers a 22 KB result; the independent result-only control stops at the first batch. Share the positive-savings principle for actual native projections; no original damage is shown. |

Representative Chat Completions CC-R1 values are old core 27,010, allowance 27,110 and reserve-inflated guard 27,322. CC-R2's actual estimate 26,050 fits allowance 26,080, while reserved estimate 26,110 does not. CC-R3's first projection is 2,148; all-reference form 2,211; result-only form 2,035. These are fixtures, not universal constants or calibrated model token counts. Responses reproduces the corresponding decisions with its own envelope.

Relevant current source is [context.py](../../src/pdfmd/context.py), especially `preflight`, `admit_group`, `compact_request` and `apply_handoff`, and [context_updates.py](../../src/pdfmd/context_updates.py), especially `resolve`/`recover`. Historical line references such as 517, 570-572 and 625-640 apply to this baseline, not a future refactor.

Passing adjacent controls preserve note omission/clear/replacement and release-then-repin, including the current policy of retaining earlier pending work after invalid follow-ups. Each uses two mock requests including one compaction after reopen, retains seven seeded attempts before new work and at least 17 seconds, and does not rewrite receipts. Those controls establish existing capabilities to preserve or consciously change; they do not validate the proposed whole-revision failure semantics.

### D06. Initial responsibility separation and Reviewer A

**Main assistant:** separate policy composition, request projection/cost, continuation decisions and durable effects/recovery; compare keeping immediate/deferred behavior with complete admission at batch end.

**Reviewer A, inline user-pasted review:** capacity should be tested on the final candidate. `pin(Y)` followed by `release(X)` can fit even if intermediate `X+Y` does not. Do not automatically apply a fitting prefix: notes about Y may depend on a later pin. A single coordinating entry should use normal, actual compaction and post-handoff plans; proposal lifecycle and result delivery must be separate.

**Main assessment/revision:** accept these distinctions. Withdraw per-update necessary-capacity rejection as a universal final-batch rule and automatic fitting-prefix application. Also identify a gap in A's suggestion to skip structurally invalid operations: a valid notes operation can still depend on the invalid pin. Recommend whole context-revision non-application while preserving unrelated successful tool work. The X/Y and notes examples are design counterexamples/code-supported risks, not newly claimed full Runtime reproductions.

**Additional correction:** freezing proves a prepared input, not a sent request. A revision tool/base selector alone cannot help if no normal request under active policy can ever deliver the diagnostic to the agent.

### D07. Reviewer B's objection and what it establishes

**Reviewer B, inline user-pasted review:** retain immediate application without pressure and deferred proposals under pressure. It cites (1) half-batch Stop plus amendment preserving an already applied pin, (2) `report` currently routing directly from tools to END, (3) added outcome/storage overhead, and (4) many changed assertions without automatically fixing CC-R1/2/3. It suggests deferral only while later operations remain unsettled.

**Main assessment:** these are real integration points and costs, not evidence that final-candidate admission is unsuitable. The atomic unit, decision time, persistent effect authority and message presentation are separate choices. Existing completed effects must recover; a future saved-only operation is a different promise. Routing through local coordination need not cause another model call. One batch outcome need not imply one added user message per operation or a fixed overhead.

**Corrections to the objection:** `test_context_lifecycle.py:155` is not an invalid-middle-operation example; the relevant `test_context_retry.py:198` control has an invalid last update. Restricting immediate admission to no unsettled later calls also changes the cited half-cancel test, whose next edit is unstarted. The final `prepare` guard protects against sending the locally estimated excess; it does not prove a feasible correction path and does not calibrate the upstream provider limit.

**Effect:** preserve B's valid tradeoff, reject test-count/minimal-change arguments as the deciding metric, and keep whole-batch admission as the main recommendation. Neither approach alone fixes the three projection/planning defects.

### D08. Two further comments and the first reconciliation

The supplied [batch-tradeoffs review](../reference/context-coordination-sources/review-02-batch-tradeoffs.txt) and another inline independent report favor final composition. The inline report proposes settlement at the end of `Runtime.tools`, allowing immediate presentation of applied results without forcing a later extra message; it asks for choices on batch commitment, invalid-operation grouping and Stop/amendment behavior.

**Main assessment:** a batch-end decision service is a meaningful alternative, but its crash boundary must be specified. Prefer a complete-candidate checkpoint followed by one coordinator for recovery clarity. That node does not itself create cross-store atomicity. Do not promise zero overhead or modify raw saved receipts.

**Disputed claims:** calling the current capacity-dependent commitment a logical contradiction overstates it; it is a chosen dual-path contract. Rebinding an old candidate's `instruction_basis` to new instructions would falsify its origin. Generic temporary use of shorter pending notes/views is not justified by CC-R1, whose controls already compact with old content. Preserved older candidate bytes do not establish continuing automatic eligibility.

### D09. Design reconciliation: alternatives narrow

The supplied [design-reconciliation review](../reference/context-coordination-sources/review-03-design-reconciliation.txt) retracts the “dual-track contradiction,” rejects fabricated instruction bases and generic cheaper temporary pins/notes, introduces explicit `base="active" | "pending"`, and distinguishes whole-revision presentation from individual intermediate policy effects.

**Main assessment:** retain those corrections, but withdraw “permanent deadlock,” “only correct policy,” zero-discrepancy-across-all-purposes and guaranteed-recovery claims. A candidate may fit normal input directly; an active-policy size alone does not prove compaction impossible. Same-estimate consistency applies to the same snapshot/presentation, not all request kinds. The reviewer is recommending conservative supersession, not proving every other explicit validity policy impossible.

The review's projection rules still overlap when the latest batch remains after partial compaction, and its rejection decision still depends on feedback feasibility. Both need an explicit responsibility boundary.

### D10. Actual projection and previous-candidate eligibility

The [continuation-boundaries review](../reference/context-coordination-sources/review-04-continuation-boundaries.txt) requires an actually fitting compaction plan, not only a fitting candidate core. It replaces “history versus cross-wait” message placement with checking whether the actual emitted payload already contains the specified settlement result. It also distinguishes retaining `Q_prev` for reuse from allowing it to auto-commit after a failed new revision.

**Main assessment:** this is a usable design direction. Three remaining clarifications are required: persist candidate disposition before testing feedback feasibility; distinguish useful rolling compaction from exhausted correction/task budgets; and preserve a valid same-batch report in every branch, including unavailable capacity/configuration. A waiting label alone cannot supply an executable path.

### D11. Latest reviewer closeout and main synthesis

The [disposition-closeout review](../reference/context-coordination-sources/review-05-disposition-closeout.txt) incorporates those three points. A candidate needing revision stays ineligible after capacity repair, while an eligible pending one may be reassessed. Positive rolling reduction has no arbitrary count limit; request/time budgets differ from response-correction episodes. Local coordination precedes report completion without preparing a request that will never run.

**Main assistant's final clarification:** `auto_admit=False` is insufficient to distinguish needs-revision, terminal rejection/withdrawal/supersession and already applied effects. Preserve disposition, reason and originating revision. Prefer `eligible_pending` over a state name that assumes compaction is always the next action. Distinguish measured capacity excess, missing configuration/estimate, no-progress and exhausted repair. A new capacity setting is not automatic reconfirmation of an ineligible intent.

The source's first report table is visibly truncated. Its later complete report rules are retained as the source of the synthesis; no missing words are reconstructed. Claims that all issues are solved or no new table could be necessary remain reviewer confidence, not established facts or implementation constraints.

**Effect:** the integrated design is ready for explicit policy selection and an authorized bounded implementation, without another framework debate. It is not a claim of final application correctness or Stage A completion.

### D12. User authorizes durable recording

**User:** “use the updated ... vibe-coding ... skill to recording our discussion about context management and the final design”; then “use sub-agents if needed.”

**Action in this documentation task:** reread the updated skill; check the target repository baseline; use two read-only subagents to verify source chronology and retained evidence/ownership; preserve selected original reports and local results; write this chronology and the integrated target design; update navigation and current/phase status without changing effective code or contracts. No implementation choice is silently selected by a reviewer quote, and no application checks are described as newly executed.

### D13. User reopens three policy choices for discussion

**User:** continue from this record, the target design and CURRENT_STATE; discussion only, no writes, Git changes or provider calls. Compare commitment units, structural-failure grouping and new-instruction handling as separate choices. Use X-to-Y replacement, notes plus failed pin, Stop/Continue and capacity repair to explain effective policy, candidate, commitments, agent feedback and reopen behavior.

**Main assistant:** retain the whole-batch/non-partial/reselection recommendation, but compare fairly. An improved immediate/deferred path can save intermediate X+Y and then compose release X; it is not inherently unable to perform replacement. The stronger reason for whole-batch commitment is that early fitting notes can otherwise commit before a dependent pin fails. A note referring to Y without a pin is not necessarily false because Y may be read separately; the app lacks grounds to assume independence. Newly saved versus already committed effects are different promises, not a logical contradiction. New instructions stop automatic admission of old uncommitted intent, but its content can be explicitly selected under a new basis without routine user approval. Explicit retention authority could be recorded without falsifying the old instruction basis; it was not selected as a new UI feature.

**Effect:** recommendations remained open at that point. Batch admission, receipt presentation, outcome overhead and model calls were not coupled into one choice. No application tests or document changes occurred in that discussion turn.

### D14. Latest policy comparison and main reconciliation

The supplied [policy-comparison review](../reference/context-coordination-sources/review-06-policy-comparison.txt), attachment `5e243f22-9e71-4da4-8517-3810a3cde11f`, favors whole-batch commitment, whole-revision non-application and supersession with reuse. It separates actual payload outcome placement and discusses four concrete scenarios, reusing earlier evidence rather than presenting newly implemented policy tests.

**Main assessment:** support the direction with material corrections:

- The current per-call capacity rejection is not proof that every immediate/deferred design must reject X+Y. Y failing to become pinned is not deletion of Y's original.
- The review's blanket capacity-failure cancellation of automatic eligibility conflicts with its later eligible-history-wait scenario. Structural invalidity, historical pressure, missing estimates and an already recorded needs-revision outcome must stay distinct.
- At `a484b9b`, `context_updates.py:84-100` tests fallback feasibility before committing rejection. If fallback stops, it records waiting; a later fit does not overwrite an already committed rejection. Separating disposition from delivery is a policy/responsibility change, not just a missing-Boolean repair. Current CONTRACTS Q2 explicitly describes that behavior, and `resolve()` restores existing settlements first.
- The current Stop test preserves an already admitted effect; it does not require every completed context tool to apply unconditionally. Preserving that historical effect does not prevent a subsequent change under new instructions. Commitment timing and amendment policy remain separate decisions.
- Saved-proposal reuse requires a new revision, explicit current base/basis and revalidation. Replaying selected operations and importing a whole old policy are different operations. Ordinary `base="pending"` cannot silently revive an ineligible candidate. Reuse is not zero-cost, and outcome placement depends on actual payload coverage.

**Evidence boundary:** the main review reread the current skill, relevant source, contracts, target design and cancellation tests. It did not rerun tests, renderers or model calls, and made no file/Git changes. The three prior local controls remain evidence of their own mechanisms, not proof that the new policy is implemented or best under live model behavior. The review's remaining issues were not automatically authorized for coding.

### D15. Human selects the three policies and authorizes design recording

**Human decision, 2026-10-25, Asia/Hong_Kong:** the user says “同意the following” and endorses the explanation separating saved from applied, then asks to update the discussion/design and clarify capacity waiting, needs-revision, terminal outcomes and reuse/reopen, with no implementation or Nexus calls. The quoted explanation's prior “not yet decided” wording describes its earlier status; the current explicit agreement selects its three recommendations.

**Selected:** (1) compose one accepted response's context operations in order and admit the complete candidate at batch end; (2) no automatic partial context application after a structural failure and no automatic fallback to an earlier pending proposal; (3) after new instructions, preserve committed effects but stop automatic admission of old uncommitted intent, retaining content for explicit agent selection in a new revision. Obsolete unstarted tools are skipped. Plain Continue resumes the accepted work. Non-context document/evidence effects are preserved.

**Selected clarification:** legal historical-pressure waiting is different from invalid parameters; a previously recorded needs-revision or terminal result does not regain automatic eligibility merely through more capacity. Saving content is not maintaining execution authority. The current waiting-before-rejection path must not be mislabeled as resurrection of an existing rejection.

**Costs accepted:** early fitting context changes wait until batch completion; a structurally bad operation can hold other independently useful context changes; even a minor amendment requires reselection of uncommitted intent. The agent performs that selection without routine human approval. No adoption of reduced fidelity, hidden pin downgrades or narrower source scope follows.

**Remaining boundary:** the three choices do not alone determine when measured necessary-content excess should request an agent revision rather than await changed settings. The target preserves that classifier as an explicit recommendation/open decision instead of quietly adopting every earlier reviewer rule. Reuse mechanics are made concrete as design recommendations, with current-base operation/field reuse distinct from unselected old-policy snapshot replacement.

**Documentation action:** update this record, the target design, decision/status/phase/navigation owners and the inert latest-review source. Application code, tests, effective CONTRACTS, settings and Git refs/index are unchanged. D12's subagent and verification results remain historical; none are relabeled as D15 execution. No implementation authorization is inferred from policy adoption.

### D16. Necessary-content capacity options and the conditional C proposal

**User:** retain the three D15 decisions and compare waiting with automatic eligibility against durable needs-revision followed by diagnostic delivery. Examine history-only pressure, a newly oversized raw pin, a formerly feasible candidate after reduced capacity, already decided outcomes after increased capacity, and an active policy unable to deliver the diagnosis. No implementation or record update was authorized in that discussion.

**Reviewer, [required-capacity options](../reference/context-coordination-sources/review-07-required-capacity-options.txt):** proposes C. A newly oversized candidate should request agent revision. A formerly feasible candidate whose capacity is reduced should retain eligibility if the active policy cannot continue, but request revision if that policy can run or compact. Missing estimate/configuration data should remain eligible while waiting. The reviewer separates content, eligibility, disposition and delivery; it also proposes whole-old-policy reuse and claims strong autonomous-completion and capacity-restoration support from existing tests.

**Main assessment:** support explicit eligibility and independent delivery, but qualify the reasoning:

- Unknown cost is not confirmed excess. B need not reject a missing image estimate, and removing automatic eligibility does not delete the original intent or content. The agent cannot invent route capacity, but may choose another representation if a usable request can return control to it.
- C is a coherent possible policy when its conditions are explicit. It is not intrinsically contradictory merely because delivery feasibility participates in selecting the initial disposition. Once a disposition is committed, later delivery must not revise it. C trades simpler uniform decisions for automatic restoration in its stated blocked-capacity case.
- A fitting actual compaction request does not prove that the subsequent normal request under the active policy plus diagnosis can fit. Evaluate the target normal request and its necessary costs; do not spend repeated compactions on an already proven irreducible obstruction.
- Reuse should select old notes, fields or ordered operations against an explicit current base. A generic proposal reference must not silently replace current policy with an old snapshot. Frozen means prepared, not necessarily sent; outcome visibility depends on the actual emitted payload, not simply whether the old batch remains in stored history.
- Existing capacity-wait tests ultimately use 500000 and do not demonstrate exact original-capacity restoration. Raw-pin correction is scripted, not a measured real-agent self-repair rate. Local estimate units are not provider token capacity. Claims of complete correctness or guaranteed autonomous success exceed that evidence.

**Effect:** the policy choice remained open at this point. The main recommendation favored B's uniform durable disposition, while preserving C's actual rationale and costs rather than dismissing it as an impossible state machine. No source report was adopted verbatim.

### D17. Reconciliation of B and C and the committed-decision boundary

**Reviewer, [required-capacity reconciliation](../reference/context-coordination-sources/review-08-required-capacity-reconciliation.txt):** supports B, explicit current-base reuse, and acknowledging that fallback-first waiting in existing CONTRACTS/tests would change. The report distinguishes a capacity adjustment from a later coordination decision, but calls C self-contradictory and also compares B with a pure formerly-feasible-always-waits policy.

**Main assessment:** agree with the recommendation and its explicit policy-change status, with these corrections:

- The original C proposal is not pure waiting: it also hands revision control to the agent when the active policy is usable. Its distinctive restoration benefit applies to its blocked-active-policy branch. Comparing B only with unconditional waiting overstates the difference.
- C can intentionally use delivery feasibility in selecting a disposition without later rewriting a committed fact. B is selected for clearer uniform authority and fewer history-sensitive conditions, not because C has been proved logically impossible.
- The durable disposition is the boundary. Pressing Continue does not prove that coordination reached or committed that decision: an existing frozen request, interruption or failure may intervene. Restoring capacity before a new disposition preserves eligibility, not a promise of immediate fit despite remaining history.
- Explicit agent reselection need not require a dedicated confirmation-only model call. It can occur with ordinary conversion work; real model efficiency remains unverified. A compaction request fitting still does not guarantee reachable active-policy diagnostic delivery.

**Effect:** no further whole-project review was needed to present the remaining choice. The existing implementation and tests remained unchanged; the human still needed to choose the capacity policy and separately authorize implementation.

### D18. Human selects B for confirmed necessary-content excess

**Human decision:** the user explicitly selects B: for a still-valid, fully composed candidate, at an applicable unfrozen decision boundary, confirmed necessary-content excess under current settings is durably recorded as `needs_agent_revision`, with no remaining automatic admission eligibility. This applies whether the candidate previously fit and whether the active policy can currently deliver the diagnosis. Preserve the complete candidate, active policy and useful work; plan delivery separately. Increasing capacity later does not revoke this committed disposition.

**Limits selected with B:** missing estimates are not confirmed excess; history-only pressure retains the organize-and-readmit path. Existing committed effects are restored before fresh decisions. The setting observed at a decision boundary matters; the fact that the user pressed Continue does not substitute for a committed result. The three D15 choices remain in force.

**Accepted tradeoff:** after a real low-capacity decision, restoring capacity may permit diagnosis and agent reselection instead of automatically applying a formerly feasible candidate. This preserves a single explanation of authority independent of notification availability. It does not require human approval of each revised pin, a dedicated extra model call, or loss of saved work.

**Authority:** the user asks for an integrated, implementable and testable design, expressly forbidding files, implementation, tests and model calls during that design turn. This choice supersedes D15's open classifier and the later C recommendation. Original message time is not separately established here; this entry is recorded on 2026-10-25, Asia/Hong_Kong (UTC+08:00).

### D19. Integrated design and evidence bounds

**Main design response:** combine all four choices as one complete context-update capability. Preserve the small StateGraph/native Nexus/SQLite-and-immutable-file baseline where it already has a useful responsibility; reorganize decisions and request planning rather than assume either a few line edits or a framework replacement. The [target design](../design/CONTEXT_UPDATE_COORDINATION.md) owns the detailed flow; its essential rationale is:

- **One commitment unit, explicit lifecycle:** save and structurally validate ordered operations from a complete model-response batch, compose without intermediate capacity rejection, then admit the whole candidate. Saved collecting work, an eligible candidate, a committed needs-revision disposition, an applied policy and a terminal candidate are different facts. A structurally invalid context revision neither applies its valid prefix nor falls back to an older pending candidate. Other completed document/evidence effects remain. New instructions stop automatic eligibility of uncommitted intent without rewriting its instruction basis.
- **Different questions need different plans:** the candidate's complete normal input, actual active-policy compaction, specific diagnostic input and post-handoff continuation target share protocol assembly and cost principles but retain their own snapshots and contents. Unsettled outcomes may need a bounded reserve; a specific result uses its actual presentation. A justified necessary-cost lower bound can prove excess in one direction under the local estimator. A bound that fits does not prove a complete request fits. Emptying history/handoff is not proof that all indispensable state has been included: active work, dependencies and warnings still need a semantic home, while a verbose handoff can itself be reorganized. Outcome placement overhead is not blindly treated as universal irreducible cost.
- **Disposition precedes delivery:** B records needs-revision before trying to return control under the active policy. No ineligible candidate release is borrowed to shrink that policy. If history is the obstruction, assess actual compaction and progress toward the specific active-policy diagnostic target. If that target's necessary content is proven oversized, a fitting compaction alone does not justify futile retries. Unknown estimates remain a separate observation; if the coordinator explicitly hands revision control back to the agent, it first records the loss of old automatic eligibility rather than letting a stale candidate race the agent's new choices.
- **Reuse selects content, not old authority:** choose the current active or explicitly eligible pending base, import selected old fields or ordered context operations, add new changes, and revalidate the whole new revision under current instructions. Preserve provenance and order; omitted notes retain, supplied notes replace, and an explicit empty string clears. A generic old proposal reference is not a whole-policy replacement, and invalid source parameters remain recoverable without guessed repairs. New fields/API spellings are target examples, not existing capabilities.
- **One formal effect authority:** a durable settlement records the disposition and, only when applied, the policy transition. Restore that fact before deciding again; graph checkpoints retain position/references and reconstruct the committed projection. Neither a graph copy nor a candidate blob independently selects the active policy. Preserve raw tool receipts and consumed budgets. Determine which outcomes need a separate message from their visibility in the actual planned payload, not stored-history membership. Frozen requests preserve their bytes, route and replay boundary; prepared, attempted and understood are not synonymous.
- **Bounded continuation and end paths:** compare actual native projection savings, retaining short arguments when references would grow them. Accept useful partial compaction only with observable target progress and preserved semantic state; test the final continuation against the actual specific outcome. Preserve useful rejected handoffs and old history, and honor persistent repair/run budgets. A valid current report receives local coordination before ending, without a compulsory extra model request; an obsolete report cannot end work under new instructions. Plain Continue restores existing effects/work, while amended Continue follows the chosen new-instruction policy.

**Implementation route proposed:** first make purpose-specific plans and common cost/projection decisions coherent; then connect whole-batch composition, eligibility and the single decision commit; then integrate explicit reuse, delivery, recovery and the saved/reopened/exported workflow. These are dependency-ordered outcomes, not separate authorization or an arbitrary module-count target. No known remaining policy conflict directly prevents bounded implementation after authorization.

**Acceptance proposed, not run:** both protocols must cover the three known counterexamples plus ordered dependent updates, structural invalidity, history-only pressure, B before/after an actual durable decision, unknown estimates, reachable versus unreachable diagnostic targets, report endings and interrupted settlement/checkpoint/frozen-request boundaries. Include a real local Runtime/persistence flow with scripted responses through waiting or needs-revision, compaction/diagnosis, an explicit new revision, admission, continued editing, save/reopen/export; compare original PDF/data, prior Markdown/images, selected version and ZIP. Distinguish any real-renderer check from raw-byte/artifact checks. Verify no-progress stops and unchanged consumption. Existing tests do not prove these new policies; Stage B can later observe natural agent choices and actual conversion quality within separately authorized source/range/route/call limits.

### D20. Human adopts the integrated design and authorizes recording

**Human agreement:** after the integrated-design response, the user says “i agree. recording the discussion” and invokes the latest vibe-coding skill. In context this adopts the integrated design and authorizes recording it with the four selected policies. It does not authorize implementation, test changes, live calls, a Git checkpoint or Stage B.

**Recording action, 2026-10-25, Asia/Hong_Kong (UTC+08:00):** extend this topic history and its current summary, synchronize the existing target design and decision/status/phase/navigation owners, and preserve reviews 07/08 verbatim with hashes. Keep D01-D15 and all earlier source-copy contents/identities intact. Original times of the intervening reports and conversations are unknown; D16-D20 express relative order, not invented timestamps. Prior test results remain historical, and current uncommitted documentation/scratch is preserved.

**Continuation:** the target is sufficiently specified for a bounded implementation request, not yet a completed context capability. Effective runtime contracts and tests must be reconciled with B and whole-batch semantics during that separately authorized implementation. No additional policy debate or general review cycle is a prerequisite unless implementation reveals a concrete conflict with an explicit requirement.

### D21. Human authorizes implementation of the adopted capability

After D20, the user says "please proceed to 實作" and supplies a detailed implementation reference. This authorizes the integrated four-policy capability, necessary responsibility refactoring, local mock verification, preservation/renderer checks, owner updates and scoped local checkpoints. It excludes live model calls, installs/upgrades, push, old-repository changes and unrelated recovery/export/Alpha/packaging work.

Implementation and final local validation ran across 2026-10-25/26, Asia/Hong_Kong. The implementation keeps the small graph and storage foundation while assigning composition/reuse, request projections, disposition/commitment and execution recovery explicit owners. It addresses CC-R1/2/3 together with whole-batch invalidity, B, explicit content reuse and committed-effect recovery. The design documents were preserved first in `c1e6fcc`. The original three review scratch files remain unchanged. An unfrozen preparation restart discovered in regression now reenters coordination to apply valid new instructions without changing frozen input or consumption.

[CURRENT_STATE](../CURRENT_STATE.md#complete-context-update-coordination) records actual test and artifact results; [REVIEW_HANDOFF](../REVIEW_HANDOFF.md) identifies the exact package and limitations. The earlier 248/six-case results and reviewer reproductions are historical controls, not relabeled new evidence. Stage B remains the next separately authorized product-learning step; scripted choices do not establish model autonomy or general PDF fidelity.

## Alternatives and current disposition

| Alternative or earlier claim | Main recommendation and reason | Reconsideration/remaining cost |
| --- | --- | --- |
| Keep immediate/deferred commitment; fix only CC-R1/2/3 | Not selected for this target. A better deferred path could compose X+Y then release X, but early fitting dependent changes could still commit separately | Useful if independent early effect becomes a stronger requirement; would change the selected whole-revision promise |
| Whole candidate at batch end, with one coordinator | Whole-batch policy selected in D15; integrated responsibility/plan design adopted in D20 | Requires changed cancellation/receipt semantics and recovery/report tests, not merely a helper extraction |
| Automatically apply fitting/structurally valid prefix | Not selected; syntax or capacity does not establish independence of notes/pins | Agent can explicitly propose a new independent revision; no automatic dependency inference is selected |
| Use every smaller pending pin/note in temporary compaction | Not selected; smaller is not equivalent, and CC-R1 controls do not need it | Reconsider only with a concrete unsupported path and explicit semantics for the whole interdependent revision |
| Preserve old pending candidate's bytes and auto-admit it after replacement failure | Excluded by D15's selected non-partial policy; content retention is not continued intent | Keep bytes, identity and diagnostic; explicit new choice establishes a new revision's eligibility |
| Rebind old instruction basis after amendment | Rejected by the main assessment; destroys provenance and misstates authority | Explicit re-selection under new instructions is different and can be supported |
| Conditional C: preserve a formerly feasible candidate if reduced capacity also blocks the active policy | Not selected after D18. C is a possible deliberate policy, not a proved contradiction; B avoids prior-feasibility/delivery-sensitive eligibility | B costs explicit reselection after an actual low-capacity disposition, even when capacity later returns |
| Make disposition depend on whether feedback fits | B selects durable needs-revision for confirmed necessary-content excess independently of delivery. Existing fallback-first waiting had no committed rejection to revive; the target is an explicit policy change | Preserve content and active policy, then plan delivery or record a specific external blocker |
| One reserve or one numeric estimate for all request purposes | Excluded from the adopted target; actual compaction, known settlement and unknown future outcomes answer different questions | Common assembly/cost principles with named purpose and snapshot; a one-sided necessary-cost proof is not full admission |
| Reuse an old proposal as an implicit whole-policy replacement | Not selected. It can overwrite later valid choices and confuses retained content with continued authority | Explicit current-base selected field/operation reuse; whole-snapshot replacement would need its own explicit semantics |
| Determine inline outcome by stored-history membership or whether waiting occurred | Not recommended; these tests overlap and do not describe emitted content | Inspect settlement coverage in the actual planned native payload; frozen input remains immutable |
| Replace the framework/storage foundation | No current evidence justifies it | Reassign local responsibilities first; no promise that exact existing module/table boundaries must survive |
| Add a pin lifetime manager or compulsory evidence workflow | Unselected and outside this coordination design | Existing explicit views, read/release choices and exact retrieval remain available |

## Decision and continuation boundary

Four policies are selected: D15's three commitments and D18's B. D20 adopts the integrated design and D21 separately authorizes its implementation. The implemented contracts preserve an explicit current base for reuse and distinguish committed disposition from policy activation. Routine API/storage choices are explained in effective owners; no new policy vote is required by their spelling.

The [design's acceptance matrix](../design/CONTEXT_UPDATE_COORDINATION.md#observable-acceptance-and-limits) defines the bounded exit. Executed checks and artifact identities are recorded in CURRENT_STATE; documentation consistency and source-copy hashing alone do not establish product outcomes.

Stage B remains the next useful product-learning direction after a bounded mechanism closeout. Source/range, Nexus route and finite live-call authorization remain user decisions. Do not force compaction in a real conversion merely to demonstrate a feature. Do not make unrelated OCR/network/packaging hypotheses prerequisites. This record does not authorize that experiment. The current implementation results and their limits are recorded in CURRENT_STATE rather than inferred from reviewer agreement.
