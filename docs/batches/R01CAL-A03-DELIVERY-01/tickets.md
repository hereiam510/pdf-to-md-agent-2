# R01CAL-A03-DELIVERY-01 local tickets

[Batch scope and acceptance](spec.md) · [Adopted design](../../design/ASSET_REFERENCES.md) · [Adoption and planning rationale](../../discussions/ASSET_REFERENCES.md#primary-xmp-and-portable-link-split-adopted) · [Evidence](verification.md)

## Planning basis and authority

**Plan identity: AR-T1, adopted on 2026-11-08, Asia/Singapore, against design/spec AR-S4.2.** The user explicitly accepts the five-ticket split and requests formal tickets, dependencies and acceptance correspondence, with discussion/design records updated. The preceding [ticket discussion](../../discussions/ASSET_REFERENCES.md#spec-readiness-and-ticket-sequence-discussion) retains the alternatives and reasoning. The writer qualification remains a concrete technical dependency; adopting this plan does not establish its result.

The planning instruction was tickets only; its [formal planning review](verification.md#formal-ticket-planning-review) remains documentation evidence. The subsequent 2026-11-08 instruction selects **T1 only**, including isolated acquisition/build, a qualification harness and its Windows controls, then stop. It excludes application integration, automatic dependency changes, provider calls, original-task mutation, global installation/settings changes, destructive cleanup, publication and subagents. The [local ticket policy](../../../AGENTS.md#batch-documents-and-ticket-mode) continues. Entry HEAD is `a88f1bab6687a2234c689b4589b1035d8f4b6618` with inherited modified/untracked documentation preserved; [T1 execution evidence](verification.md#t1-windows-helper-qualification) identifies the actual tested artifacts and changes.

The user's later agreement selected the [bounded comparative T1 follow-up](#t1-comparative-follow-up) for a continuation prompt, followed by the explicit instruction to execute that scope only and stop. This is a scoped amendment to AR-T1, not a sixth ticket or a product-version decision. The original prompt-preparation review remains document evidence; the [comparative execution record](verification.md#t1-comparative-execution-1355-and-1361) owns the subsequent run. The [selection rationale](../../discussions/ASSET_REFERENCES.md#comparative-qualification-selected) distinguishes qualification from adoption; all prior execution exclusions continue.

The preceding agreement selected [the AR-Q4 qualification scope](#t1-ar-q4-malformed-xmp-qualification) for T1 amendment and execution-prompt preparation only. The [adoption rationale](../../discussions/ASSET_REFERENCES.md#ar-q4-qualification-scope-agreed) retains that historical no-execution boundary. The subsequent user instruction authorizes **only that bounded qualification and its records**, then stop, with no product adoption/integration. The [execution evidence](verification.md#ar-q4-bounded-execution-and-packet-coverage-stop) records its actual stop and limits; the [design boundary](../../design/ASSET_REFERENCES.md#ar-q4-bounded-qualification-target), earlier results and five-ticket split remain intact.

The preceding agreement selected [the AR-Q4-C1 coverage-only study](#t1-ar-q4-c1-coverage-only-study) for amendment and execution-prompt preparation, expressly permitting instrumentation of a separate **read-only ExifTool copy** in that future study. [Adoption reasoning](../../discussions/ASSET_REFERENCES.md#ar-q4-c1-coverage-only-study-agreed) and [the agreed proof boundary](../../design/ASSET_REFERENCES.md#ar-q4-c1-coverage-proof-for-the-agreed-study) own the method choice. The subsequent user instruction authorizes **only this bounded coverage study and its records, then stop**; [the execution record](verification.md#ar-q4-c1-coverage-study-source-closure-stop) owns the new observations. The instrumentation permission remains a narrow exception for an observer copy; tested writers and prior runs remain unchanged. No product adoption or integration is selected.

The 2026-11-09 [AR-S4.3 adoption](../../discussions/ASSET_REFERENCES.md#scoped-resource-protocol-adopted-2026-11-09) amends the preview target and [T2 protocol acceptance checks](spec.md#t2-protocol-acceptance-checks) within the existing AR-T1 split. That adoption instruction was documentation-only. The subsequent [T2-only authority](#r01cal-a03-delivery-01-t2) selects its implementation and checks; T1 and T3–T5 boundaries remain separate.

The 2026-11-09 [AR-S4.4 adoption](../../discussions/ASSET_REFERENCES.md#primary-xmp-and-portable-link-split-adopted) revises AR-T1 by separating T3a and T3b and adding T1-F06 inside T1. The user approved documentation and tickets only, then stop. Earlier execution permissions apply only to their recorded work.

<a id="proposed-sequence-and-dependencies"></a>
## Sequence and dependencies

| Ticket | Verifiable contribution | Required dependency result | Execution state |
| --- | --- | --- | --- |
| [T1](#r01cal-a03-delivery-01-t1) / [T1-F06](#t1-f06-primary-xmp-writer-and-independent-reader-qualification) | Qualify the exact primary-XMP writer and independent reader | Independent of T3a. Use AR-S4.4 and prior source/qualification evidence | T1-F06 qualified for its bounded tested preparation; [evidence](verification.md#t1-f06-primary-xmp-qualification), with [B-lite requalification](verification.md#t1-f06-b-lite-legacy-xmp-requalification). Selected for product use on 2026-11-10. Prior investigations retain their scoped results |
| [T2](#r01cal-a03-delivery-01-t2) | Resolve references and view/diagnose the selected saved version | Use the adopted shared interpretation and selected-version interfaces | Scoped contribution completed. [Protocol evidence and limits](verification.md#final-t2-protocol-evidence-and-scoped-assessment) |
| [T3a](#r01cal-a03-delivery-01-t3a) | Save and export portable links under existing registered hash paths | T2's shared reference and preview contribution | Scoped contribution completed. [Implementation evidence and limits](verification.md#t3a-portable-link-save-implementation-and-verification) |
| [T3b](#r01cal-a03-delivery-01-t3b) | Create readable, independently informative source-image deliverables | T3a's shared save path, positive T1-F06 qualification and explicit product selection of the candidate | In progress: selected 2026-11-10; the [remaining scope](#r01cal-a03-delivery-01-t3b) is on the T5 route |
| [T4](#r01cal-a03-delivery-01-t4) | Correct source facts and synchronize assets and references atomically | T3b's enriched creation and publication path | Selected completion checks done in [T4-A to T4-C](#t4-follow-up-tickets); combined acceptance belongs to T5 |
| [T5](#r01cal-a03-delivery-01-t5) | Establish combined save/reopen/export and declared-platform acceptance | Integrated T2, T3a, T3b and T4, with matching qualified and selected T1-F06 artifacts and invocation | [Local execution and continuation](#t5-local-execution); [closing tickets](#t5-closing-tickets) selected 2026-11-13 |

T3a addresses P2 first when authorized. T1-F06 may be selected independently. One integrator owns the overlapping document publication path across T3a, T3b and T4. A scoped repair or qualification is distinct from the combined acceptance.

## Shared interfaces and completion records

| Handoff | Required result before dependent work |
| --- | --- |
| T2 -> T3a | Use the existing role-aware interpretation and resolver, guarded reference correspondence and selected-version preview. The [reference design](../../design/ASSET_REFERENCES.md#reference-interpretation-and-destination-policy) and [snapshot protocol](../../design/ASSET_REFERENCES.md#preview-binding-and-return-behavior) own the rules. |
| T3a -> T3b | Reuse the same dependency union and immutable publication path with schema 2 occurrence/representation bindings. |
| T1-F06 -> T3b | Exact positively qualified artifacts, invocation, allowed fields, pre/post checks, independent readback and applicability limits, followed by explicit product selection. |
| T3b -> T4 | Schema 2 occurrence/representation model, fact patches, durable reservations, creation receipt/mappings and joint visibility boundary. Corrections use the same lifecycle. |
| T2, T3a, T3b and T4 -> T5 | One integrated revision with actual saved-version and fixture identities and recorded criterion/platform gaps. |

For future execution, record implementation revision/diff, exact fixtures and environments, relevant check results, preserved failed work and any unresolved limitation in [verification](verification.md); each ticket links its own entry and records its resulting state here. T1-F06 qualification and each save/view contribution must identify their bounded coverage. T5 alone assembles the whole-batch verdict against all criteria. No automatic commit, push or PR permission follows from the need to identify a revision.

All tickets include affected documentation maintenance under the existing owner rules: design for changed contracts, guides for implemented mechanisms, discussion for consequential choices, verification for observations, and this file for execution progress. Reuse existing tests in `tests/engine/documents/` and `tests/desktop/` where applicable; use canonical fixture imports and fresh ignored run locations. Do not create a second execution ledger or test each implementation detail without a behavioral purpose.

## R01CAL-A03-DELIVERY-01-T1

For the effective AR-S4.4 writer gate, use [T1-F06](#t1-f06-primary-xmp-writer-and-independent-reader-qualification). The earlier T1 entries below retain their original scope and evidence.

**Purpose:** settle whether explicitly selected helper candidates can satisfy the exact supported image/metadata workflow before downstream implementation depends on them. This is bounded qualification with a usable disposition, not a general dependency replacement project or product-adoption decision.

**Initial execution disposition (2026-11-08): completed negative assessment**, main implementer. [Windows qualification evidence](verification.md#t1-windows-helper-qualification) owns AR-Q1–AR-Q3, exact artifacts/invocations, checks and limits. [Dependency alternatives](../../discussions/ASSET_REFERENCES.md#t1-qualification-and-dependency-decision) followed that result; no alternate candidate was adopted. The original investigation stopped after T1 while leaving T3's positive gate unsatisfied. The separately selected [comparative follow-up](#t1-comparative-follow-up) below preserves this original result.

**Responsible role:** main implementer, acting as dependency/metadata integrator. Own the isolated qualification harness, helper/reader acquisition evidence and any resulting dependency-selection proposal. Do not change the document API or weaken image fidelity to make a candidate pass.

**Inputs and shared contract:** [helper invocation and qualification gate](../../design/ASSET_REFERENCES.md#dependency-versions-and-helper-boundary), [XMP schema/mapping](../../design/ASSET_REFERENCES.md#exact-xmp-namespace-and-serialization), and [AR-D1–AR-D3 evidence](verification.md#ar-s42-release-and-security-applicability-review).

**Work and completion evidence:**

- Establish exact helper and independent-reader artifacts/build identities, licenses and hashes under the existing local artifact policy. Record resolved build-tool versions and whether inherited prerelease components participate in the actual path; do not override unrelated transitives solely to remove labels.
- Trace the intended write/readback calls and execute the relevant valid/malformed XMP, PNG chunk-order, extended-JPEG, encoded-payload and standalone-reader controls in [AR-8](spec.md#ar-8--source-grounded-naming-and-embedded-standalone-provenance) and [AR-12](spec.md#ar-12--enrichment-fidelity-and-complete-delivery-chain). Use bounded isolated controls for resource cases; no source-extension-only exclusion or after-the-fact warning claim.
- Return either a bounded qualified invocation/artifact set, a specific defect requiring a dependency decision, or an unavailable check with its missing condition. Record results at the existing verification owner. A metadata-reader open or a production label alone does not qualify the writer.

**Exit and dependency gate:** qualify the selected Windows writer and an independent reader on the development destination. Record one of three dispositions: qualified for the bounded intended use; not qualified with a reproduced/source-supported defect and concrete alternatives; or inconclusive because required evidence is unavailable. The first satisfies the writer qualification dependency, but T3 additionally requires explicit product selection of the candidate and T2 acceptance; it grants no execution authority by itself. The second can complete the qualification investigation while keeping T3 blocked on a dependency decision. The third leaves qualification pending. Do not wait for every T5 destination before recording a valid Windows writer result, or treat that result as cross-platform acceptance. Acquire artifacts only within the selected qualification scope; no host/global installation is implied.

If a supported valid image cannot be preserved, the ticket may establish that negative result but cannot unlock T3. Present the concrete alternatives under the adopted production-first policy; no automatic development upgrade, custom backport, metadata stripping or sidecar. T2 can continue independently if its execution has been selected. This plan does not claim the required build/platform facilities are already available.

### T1 comparative follow-up

**State:** bounded comparative execution completed; complete preparation qualification remains inconclusive under [the recorded disposition](verification.md#comparative-disposition-and-next-decision). [Comparative evidence](verification.md#t1-comparative-execution-1355-and-1361) owns AR-Q1–AR-Q4 observations and exact scope. **Owner:** the same main dependency/metadata integrator. Compare exact ExifTool **13.55** and **13.61** under the [staged comparison plan](../../discussions/ASSET_REFERENCES.md#development-release-comparison-after-t1), retaining the original negative assessment. The test-only 13.61 source pin is `9b8664dfcf2c609d3cc8925d380e98ad2a379f9b`; acquire and verify its exact official Windows 64-bit artifact in an isolated local location. Reuse verified 13.55 artifacts and the pinned independent Adobe reader where available. Missing baseline artifacts or a materially changed build must be reported, not silently treated as the original identity.

First compare the six decisive AR-Q1/AR-Q2 controls using identical fixture bytes/expected values and the final harness for both candidates. Use CSV for the intended write and preserve the rejected JSON path as a negative control. If 13.61 passes the focused controls, execute its full applicable final suite; otherwise record the decisive result without unnecessary broader execution. Only rerun other 13.55 controls where the comparison or changed harness requires it. Keep the existing process/resource limits, complete stdout/stderr, independent metadata comparison and separate encoded-payload checks. Any necessary harness correction must have an evidence-backed reason, retain its old version/results and recheck affected comparisons for both candidates; do not patch either writer or lower expectations to obtain a pass.

Preserve `.local/ar-t1-20261108-qualification/` and all earlier originals, derivatives, manifests, logs and harness snapshots. Use fresh ignored run directories; record exact artifact, harness, reader, fixture and environment identities. Append the candidate comparison, expected negative controls, limits and disposition to verification. Maintain discussion reasoning, design qualification implications and ticket progress without replacing historical observations or creating a second execution ledger.

**Stop:** report qualified, not qualified or inconclusive for this candidate/invocation, then stop. No product dependency/lockfile change, adoption exception, T2–T5 execution, application save/reopen/export integration, replacement-writer project, original-task mutation, provider call, global installation/settings change, destructive cleanup, publication or subagents. A positive test result alone leaves product adoption undecided and does not unlock T3. No whole-batch, installed-product, cross-platform or universal malformed-input acceptance follows from this Windows comparison.

### T1 AR-Q4 malformed-XMP qualification

**State:** bounded execution completed at the prescribed stage-one stop; qualification remains pending under [the recorded disposition and specific missing evidence](verification.md#ar-q4-bounded-disposition-and-remaining-evidence). Source tracing, identity freezing, outer inventory and read-only nested witnesses are complete; stages two through four were not entered. The separately agreed [coverage-only study](#t1-ar-q4-c1-coverage-only-study) below does not relabel that run or resume those stages. No strict guard or writer preparation is accepted. **Owner:** main dependency/metadata integrator, working directly without subagents. This is a bounded continuation of T1, not T6 or an application integration increment. The user authorized qualification only, including harness work and local runs, then stop.

**Purpose and basis:** establish whether the [agreed raw-XMP pre/post validation boundary](../../design/ASSET_REFERENCES.md#ar-q4-bounded-qualification-target), around the exact tested ExifTool 13.61 CSV path, can close [AR-Q4's missing rejection evidence](verification.md#comparative-preservation-and-negative-control-observations) while preserving supported valid metadata and image data. The [discussion](../../discussions/ASSET_REFERENCES.md#ar-q4-rejection-follow-up-recommendation) retains alternatives, source guidance, staged-control rationale and open compatibility questions. AR-S4.2, [AR-8](spec.md#ar-8--source-grounded-naming-and-embedded-standalone-provenance) and [AR-12](spec.md#ar-12--enrichment-fidelity-and-complete-delivery-chain) retain their acceptance scope; no whole-batch pass is implied.

**Preserved inputs and qualification constraints:** reuse verified copies of the exact 13.61 Windows helper/source, pinned Adobe v2025.03 reader, config/CSV/allowlist and existing fixture/expected-value identities from [comparative verification](verification.md#comparative-artifacts-and-reproducibility-basis). The original 13.55 assessment and comparative result remain distinct. Preserve **both** `.local/ar-t1-20261108-qualification/` and `.local/ar-t1-compare-20261108/` unchanged, including their raw results, sources, failed work, manifests and earlier harness snapshots. Use a new ignored root and verified runtime/reader copies; never relabel an earlier run as a revised-harness execution. Retain entry harness/source editions before corrections. No helper patch, automatic dependency change or new product package is authorized.

Qualification-only harness/validator work belongs under the existing `tools/qualification/` ownership, with generated inputs/results in the fresh ignored root. Use the existing Python 3.12.14 standard-library Expat as the first read-only candidate and establish the actual linked parser/build/settings. Resolve ordinary implementation details within the selected boundary; a new parser dependency, support reduction or general metadata-parser project is not silently substituted for missing coverage.

**Stages and completion correspondence:**

1. **Freeze and prove packet coverage first.** Reconcile actual checkout/artifacts and retrieve applicable official guidance for the exact APIs. Trace the intended write/full-readback paths and locate complete original XMP bytes, including source-backed treatment of reachable nested packets. Record actual type, spans, packet hashes and completeness. Missing/ambiguous/unhandled forms or bounded-resource failure cannot become an absent-XMP pass. Stop with the precise gap if it cannot be settled within this bounded locator.
2. **Prove precheck rejection and valid-input support.** Exercise the exact malformed UTF-8 PNG/JPEG cases, unterminated CDATA/comments and the agreed syntax/namespace controls; rejected normal preparations must show **zero writer invocations**. Genuine no-XMP creation and valid CDATA/comment/custom-namespace/entity/language/Unicode/BOM/wrapper/padding controls must remain usable without repair, normalization, reserialization or metadata stripping. Distinguish policy, syntax and unavailable/resource outcomes. No external/source-directed resolution is allowed.
3. **Prove container, postcheck and resource behavior.** Cover both PNG chunk orders and actual reachable compressed/legacy forms; for JPEG reconstruct/check StandardXMP and ExtendedXMP correctly, including valid fragment reordering and split multibyte characters plus missing/overlapping/mismatched controls. A separately corrupted output fixture must fail the postcheck and yield no accepted preparation. Put inventory, decompression and validation inside the existing pre-start Windows Job limits: **256 MiB aggregate memory, five seconds job CPU, 15 seconds wall**. No unchecked declared-length allocation, exploit execution or stress bomb is required.
4. **Expand only after those controls pass.** Run the complete applicable valid-input 13.61 suite through guard plus unchanged CSV writer/independent reader. Check full new-record recovery, unrelated useful metadata and encoded/container preservation separately from same-decoder properties. Retain standalone copied-image, extended-JPEG, color/profile/alpha/bit-depth/orientation and JSON-import/stripping/missing-extension negative controls. Reuse earlier evidence only where identities/coverage remain valid; a changed comparative premise requires affected paired reruns, not an automatic broad 13.55 rerun or version upgrade.
5. **Record the bounded disposition and stop.** Verification owns actual guard/extractor/parser/build/settings identities, exact fixtures/hashes, invocations, complete stdout/stderr, pre/post outcomes, writer counts, preserved failures and limits. Maintain affected design/discussion/guide records and continuation honestly. Return qualified for the bounded tested preparation, not qualified with a reproduced failure, or inconclusive with the precise remaining coverage/compatibility/validity evidence. A parse success, reader-open success, accepted tool call or passing valid-input count alone is insufficient.

**Exit/stop:** complete only this qualification contribution. A decisive malformed-input acceptance, supported-valid-input rejection/loss or unresolvable packet gap may stop unnecessary expansion. Preserve all original/candidate/failed work; do not obtain a pass by repair, stripping, sidecars, weakened expectations or source-extension-only exclusions. No application head/save/reopen/export/atomicity, installed-product, cross-platform or universal malformed/resource acceptance is claimed. Product adoption of 13.61, application dependency/lockfile change, T2–T5, replacement writer, original-task mutation, providers, global installation/settings changes, evidence deletion, publication and subagents remain excluded. Even a positive result leaves product selection, T2 acceptance and T3 execution authority separate; **T3 remains blocked**.

### T1 AR-Q4-C1 coverage-only study

**State:** bounded execution completed at the prescribed stage-one source-closure stop; [execution evidence](verification.md#ar-q4-c1-coverage-study-source-closure-stop) owns the coverage disposition and exact missing route. Identities/source review and four bounded read-only route witnesses are recorded; no observer or later matrix is built/run. The latest user instruction authorizes only this study and its records, then stop, without adoption or integration. **Owner:** main dependency/metadata qualification integrator, working directly without subagents. This remains inside T1 and the AR-T1 five-ticket plan, not a sixth ticket. The earlier [planning review](verification.md#ar-q4-c1-study-amendment-and-execution-prompt-review) retains its documentation-only meaning.

**Purpose and dependencies:** determine whether the [agreed proof obligations](../../design/ASSET_REFERENCES.md#ar-q4-c1-coverage-proof-for-the-agreed-study) can close [AR-Q4-C1's complete original-packet coverage gap](verification.md#ar-q4-c1-reachable-nested-bytes-exceed-the-bounded-outer-locator) using the existing pinned native traversal. The [method discussion](../../discussions/ASSET_REFERENCES.md#ar-q4-c1-native-traversal-observer-proposal) retains alternatives, API/source findings and why a packet dump/callback count alone is insufficient. No predecessor implementation ticket is required; any later strict-validation or writer-dependent work requires a separate selection and its existing gates.

**Frozen basis and preservation:** reuse verified copies of exact ExifTool 13.61 source commit `9b8664dfcf2c609d3cc8925d380e98ad2a379f9b` and Windows x64 archive SHA-256 `ab75b37515385a753aa60a58f68ffffe1ff81e43b319df9540978fb19e0580e5`, with the recorded bundled runtime, config/CSV/allowlist and fixture identities. The pinned Adobe v2025.03 reader and its recorded binary/build identities remain unchanged. Read [the comparative artifact basis](verification.md#comparative-artifacts-and-reproducibility-basis) and [the subsequent runtime/source/parser identities](verification.md#ar-q4-artifacts-parser-identity-and-invocations); the installed standard-library Expat is not qualified by its identity probe. Preserve `.local/ar-t1-20261108-qualification/`, `.local/ar-t1-compare-20261108/` and `.local/ar-q4-20261108-qualification/` unchanged, including all sources, failed work, manifests, raw results and harness snapshots. Use a new ignored root and verified fresh runtime/reader copies. Preserve entry and successive observer/harness editions; never relabel an earlier run.

**Allowed qualification changes when separately executed:** maintained observer/harness/fixture/provenance tooling belongs under `tools/qualification/`; generated inputs, raw packet evidence, copied native runtimes, instrumented source editions and logs belong in the fresh ignored root. The user permits source instrumentation of a separate **read-only ExifTool** runtime to expose original bytes, lossless source mappings, serialization/carrier events and completion. Enforce read-only native invocations and establish zero native write calls. Observation must preserve normal read-side dispatch, returns, namespaces, packet contents, decoded results and diagnostics. A documented API may be used if it satisfies the same proof; ordinary per-hook/capture choices within this agreed boundary need no further routine permission. The actual writer distribution, config/CSV/allowlist and Adobe reader are not patched. A new parser dependency, general metadata parser, altered writer/support contract or application integration is outside this amendment.

**Stages and acceptance correspondence:**

1. **Freeze and prove source closure before instrumentation.** Reconcile checkout/inherited changes, exact artifacts/environment and applicable official guidance. Audit serialization-entry routines, direct and indirect table/function dispatch, recursive transforms, skip/return and carrier-completion paths for the frozen PNG/JPEG preparation. Establish that read-only extraction exposes every original packet consumed by the fixed write path, including relevant carrier contents that could be skipped before a callback. Source recognition, conditions and raw/converted buffer origins must be explicit. A shared parser name, loaded-module list or file suffix does not establish closure. Stop with the precise gap if correspondence or pre-repair provenance requires a general metadata parser or cannot be closed within this instrument; do not run a writer to discover a write-only branch.
2. **If closure is feasible, build only the read-only observer.** Use a separately copied pinned ExifTool runtime, keeping the uninstrumented baseline and tested writer intact. Review the observation-only diff and preserve exact source/module/runtime hashes. Capture original bytes before repair/value normalization and verify each permitted transport/decoder edge without creating replacement XML. Associate parent/carrier spans, logical packet bytes, occurrence identities and completion events. Do not rely only on the current buffer at `ProcessXMP`, ordinary block output or `NoBlockSave` by name. Incomplete/ambiguous/transformed-only evidence cannot become absence or complete coverage.
3. **Check observation fidelity and independent byte inventories.** Pair the same read-only invocation/config/options against the unmodified 13.61 copy; review unchanged dispatch and compare complete results/diagnostics. Use independently constructed fixture inventories and exact source mappings, beginning with the eight AR-Q4-C1 witnesses and earlier AR-Q4 PNG/JPEG bytes. Cover additional reachable classes found by the audit: compressed/legacy PNG forms and chunk orders, TIFF/Photoshop/JUMBF, multi-level nesting, custom namespace aliases/opaque values, duplicate occurrences, and complete Standard/ExtendedXMP association/reconstruction before decoding. Preserve valid CDATA/comments/language/Unicode/literal escapes and genuine no-XMP controls. Drop an event, omit/truncate a dump and interrupt traversal only in separate trace-negative controls; each must prevent a completeness claim. Keep unrelated generic XML/opaque text and subranges distinct from independent XMP serializations. Agreement between two native traces or decoded leaves alone is insufficient.
4. **Keep all processing bounded.** Retain pre-start 256 MiB aggregate Windows Job memory, five seconds job CPU and 15 seconds wall for observer, inventory, decompression, transform/provenance and native processing. Count observation overhead; no unchecked declared-length allocation, per-fragment limit reset, hidden truncation, exploit execution or stress bomb. A missing final completion, unresolved carrier/transform, compatibility issue or resource failure remains unavailable/inconclusive, never no-XMP or permission to exclude supported valid metadata for a pass.
5. **Record the coverage disposition and stop.** Append source closure/locations, artifact and observer/harness diffs/hashes, exact fixtures/expected raw inventories, invocations and complete stdout/stderr, packet/source/transform/occurrence manifests, completion evidence, native write counts, controls, failures, preservation checks and limitations to verification. Maintain ticket progress and affected discussion/design/guidance/continuation records. Conclude coverage qualified for the exact tested read-only extraction boundary, not qualified with a reproduced required-property failure, or inconclusive with the precise missing route/provenance/compatibility evidence. Stop unnecessary expansion on a decisive unresolved gap or failure.

**Exit and explicit exclusions:** finish only this coverage study and its records, then stop. There are zero native writer invocations and no accepted image preparations. Even a positive coverage result does not close full AR-Q4, resume strict Expat input/output-validation work, run the guarded CSV/valid-image suite or satisfy T3's writer dependency. Product adoption of 13.61 or the observer, application dependencies/lockfiles, save/reopen/export/atomicity integration, T2–T5, replacement writers, metadata stripping/repair, sidecar delivery, original-task mutation, provider calls, global installations/settings, evidence deletion, remote publication and subagents remain excluded. Internal evidence files are qualification artifacts, not a deliverable companion fallback. Previous results retain their actual identities and scope.

### T1-F01 AR-Q4-C1-R1 offline feasibility note

**State:** offline feasibility note completed on 2026-11-09. [Source/API evidence](verification.md#t1-f01-ar-q4-c1-r1-feasibility-evidence) and the [writer recommendation](../../discussions/ASSET_REFERENCES.md#writer-reconsideration-after-t1-f01) own its result. **Owner:** main T1 integrator. This is a local follow-up under T1 within the five-ticket sequence.

**Basis and dependency:** use the frozen candidate and retained [source-closure study](verification.md#ar-q4-c1-coverage-study-source-closure-stop), [adopted coverage proof](../../design/ASSET_REFERENCES.md#ar-q4-c1-coverage-proof-for-the-agreed-study) and [post-T2 recommendation](../../discussions/ASSET_REFERENCES.md#next-step-advice-after-t2). T2 is a separate contribution. T3's writer gate still requires positive qualification and product selection.

**Work:** use local retained source, artifact identities and API guidance to resolve or bound (1) inclusion and compatibility of the recognized skipped PNG/JPEG carrier, (2) a supplemental read-only route with exact source spans and recursive occurrence accounting, and (3) an identified decoder interface with complete input-consumption and terminal-state evidence. Separate facts established by inspection, prior runtime observations and evidence that a later qualification would need. Preserve existing valid-input support and the original evidence.

**Exit:** record an inspectable source/API note and recommend a specific qualification-only amendment if justified, or reconsidering the writer with the missing proof named. The user authorizes the note and records only, with the ticket created first. Stop before implementation, dependency acquisition/build, qualification or provider runs, or product adoption.

### T1-F02 Production ExifTool release source check

**State:** source review completed on 2026-11-09. [Exact-release evidence](verification.md#t1-f02-production-exiftool-release-evidence) and the [writer recommendation](../../discussions/ASSET_REFERENCES.md#writer-recommendation-after-t1-f02) own the result. **Owner:** main T1 integrator. Local follow-up under T1, within the existing five-ticket sequence.

**Basis:** [production-release policy](../../design/ASSET_REFERENCES.md#dependency-versions-and-helper-boundary), [AR-Q1/AR-Q2 preservation controls](verification.md#comparative-preservation-and-negative-control-observations), [T1-F01 evidence](verification.md#t1-f01-ar-q4-c1-r1-feasibility-evidence) and the [writer reconsideration](../../discussions/ASSET_REFERENCES.md#writer-reconsideration-after-t1-f01).

**Work:** verify the official current production designation, exact source tag/commit and platform artifact identity as published. Inspect the pinned release against the valid XMP CDATA/comment and PNG EXIF/JUMBF failures and the recognized skipped Brotli carrier. Trace the actual read/write path and decoder evidence, distinguishing source changes, already observed runtime behavior and unverified qualification criteria. Preserve the [coverage proof](../../design/ASSET_REFERENCES.md#ar-q4-c1-coverage-proof-for-the-agreed-study) and existing valid-input support.

**Exit:** record exact source evidence and recommend whether the candidate merits qualification or the writer should be reconsidered. The user selected this source check and records with the local ticket created first. Stop before implementation, builds, qualification runs and adoption.

### T1-F03 Adobe XMP Toolkit writer source review

**State:** source/API review completed on 2026-11-09. [Source evidence](verification.md#t1-f03-adobe-sdk-writer-source-evidence) and the [method recommendation](../../discussions/ASSET_REFERENCES.md#writer-recommendation-after-t1-f03) own the result. **Owner:** main T1 integrator. Local follow-up within T1.

**Basis:** the [writer recommendation](../../discussions/ASSET_REFERENCES.md#writer-recommendation-after-t1-f02), [earlier SDK boundary assessment](verification.md#candidate-comparison-and-bounded-disposition), [helper contract](../../design/ASSET_REFERENCES.md#dependency-versions-and-helper-boundary), [coverage obligations](../../design/ASSET_REFERENCES.md#ar-q4-c1-coverage-proof-for-the-agreed-study) and [AR-8/AR-12 acceptance](spec.md#ar-8--source-grounded-naming-and-embedded-standalone-provenance).

**Work:** identify the pinned Adobe XMP Toolkit v2025.03 source and retained reader. Trace the documented update and close APIs, PNG and JPEG writer and reader branches, exact preservation risks, raw packet access and nested carrier coverage. Assess a separate implementation for standalone and preservation readback. Distinguish source-supported mechanisms, limits and future qualification controls.

**Exit:** record whether there is a credible qualification path under the existing contract, or the exact obstacle and recommended next decision. The user selected this source/API review and records with the ticket created first. Stop before implementation, builds, qualification runs and product adoption.

### T1-F04 XMP-only container method feasibility

**State:** source/API review completed on 2026-11-09. See the [feasibility evidence](verification.md#t1-f04-xmp-only-container-feasibility-evidence) and [method recommendation](../../discussions/ASSET_REFERENCES.md#writer-recommendation-after-t1-f04). **Owner:** main T1 integrator. Local follow-up within T1.

**Purpose and basis:** determine whether a PNG/JPEG XMP-only container update can preserve unrelated metadata and encoded image data under the adopted contract. Use the [method recommendation](../../discussions/ASSET_REFERENCES.md#writer-recommendation-after-t1-f03), [AR-SDK-01 source evidence](verification.md#writer-lifecycle-and-preservation), [skipped-carrier evidence](verification.md#t1-f01-ar-q4-c1-r1-feasibility-evidence), [helper contract](../../design/ASSET_REFERENCES.md#dependency-versions-and-helper-boundary) and [AR-Q4-C1 proof obligations](../../design/ASSET_REFERENCES.md#ar-q4-c1-coverage-proof-for-the-agreed-study).

**First gate:** identify a concrete candidate write/readback boundary and show how its pre/post inventory could account for every relevant original XMP serialization and recognized skipped carrier. Start with AR-Q4-C1-R1 in PNG caBX and JPEG APP11 JUMBF. Identify exact source/API and artifact boundaries, original spans and multipart/recursive occurrence mapping, applicable compatibility evidence, and decoder consumption/terminal state. Include separate Standard and ExtendedXMP inventories and reachable legacy, compressed and nested paths. An unexplained carrier keeps the gate open. A claimed exclusion needs an exact source condition within the adopted support and coverage rules.

**If the gate has a credible path:** describe the narrow container update and the packet generation boundary. Adobe XMPCore and PackageForJPEG are optional components to assess. Identify the bytes permitted to change, how unrelated JPEG APP1/APP13, PNG chunks, encoded image data and useful XMP would be preserved, how strict pre/post validation would work, and which independent reader could verify the complete standalone record. Specify later controls against the [AR-8](spec.md#ar-8--source-grounded-naming-and-embedded-standalone-provenance) and [AR-12](spec.md#ar-12--enrichment-fidelity-and-complete-delivery-chain) requirements. Distinguish source evidence from future qualification.

**Exit:** record a source/API feasibility assessment with a bounded qualification proposal if justified, or the exact blocking condition and the next decision if coverage or preservation remains unresolved. A favorable note leaves qualification and explicit product selection pending before T3. The subsequent 2026-11-09 instruction selects this source/API review and related records, with a stop before implementation, builds, qualification runs, provider calls or dependency/product adoption.

### T1-F05 Read-only packet coverage for the XMP-only candidate

**Disposition:** superseded for the AR-S4.4 delivery path by [T1-F06](#t1-f06-primary-xmp-writer-and-independent-reader-qualification). The historical stage-one review stopped at the [source and compatibility gate](verification.md#t1-f05-packet-coverage-source-gate) before implementation. The amended JUMBF compression rule and retained Brotli witnesses remain unresolved coverage evidence for the wider inventory. Revisit only if nested XMP must be read, compared, updated or removed. **Owner:** main T1 integrator. This is a local follow-up inside T1. The original 2026-11-09 request to write the ticket first and then implement selected the [read-only follow-up recommended after T1-F04](../../discussions/ASSET_REFERENCES.md#writer-recommendation-after-t1-f04).

**Outcome and dependencies.** Establish whether the candidate can produce a complete original-byte XMP inventory for supported PNG and JPEG. Start with [AR-Q4-C1-R1 and the exact decoder candidate](verification.md#ar-q4-c1-r1-original-bytes-fragments-and-decoder-state). Apply the [adopted coverage proof](../../design/ASSET_REFERENCES.md#ar-q4-c1-coverage-proof-for-the-agreed-study) to the [T1-F04 candidate's write and full readback boundary](verification.md#coverage-decision-and-exact-candidate-boundary). Keep the baseline ExifTool 13.61 runtime, prior studies and Adobe reader artifacts unchanged.

1. **Establish source closure first.** Obtain applicable JUMBF compression rules or equivalent independently authored conformance evidence. Distinguish the typed Brotli layout in the retained witnesses, amended JUMBF compression, and C2PA compressed manifests in PNG `caBX` and JPEG APP11. Bind each applicable layout to an exact recognition condition, payload range and recursive dispatch. Close the original packet set across PNG text/legacy profiles, TIFF, Photoshop, JUMBF, JPEG Standard/ExtendedXMP, reachable scan/trailer metadata and namespace-directed nesting. Identify any required path the narrow method cannot resolve before building it. A supported input or a recognized skip without a proven mapping remains unavailable.
2. **Implement only after the gate clears.** Use a separate read-only 13.61 observer with capture-only changes and an isolated supplemental traversal. The observer preserves normal dispatch, return behavior, namespace/group state, packet output and diagnostics. Freeze candidate Google Brotli v1.2.1 source and the separate native decoder helper's compiler, source, linked artifacts and executable hashes. Use its streaming completion and consumption API for exact spans, bounded output and recorded terminal state. Keep maintained qualification code under `tools/qualification/` and source copies, instrumented runtimes, results and logs under a fresh ignored root. No changes to app dependencies or helper distribution.
3. **Check the full inventory.** Compare unchanged and instrumented 13.61 reads under the same invocation. Use independent fixture inventories for exact file spans, same-type APP11 instances, reordered ExtendedXMP, compressed/nested packets, TIFF/Photoshop/Nikon edges, legacy forms, trailer cases and true absence. Check incomplete or conflicting fragments, truncated and trailing compressed input, and a dropped event/dump/completion record. Keep the pre-start 256 MiB aggregate Job memory, five-second Job CPU and 15-second wall limits across the whole qualification process. A timeout, decoder error, unexpected skip or unaccounted occurrence cannot become absence or a pass.
4. **Stop and record.** Record exact identities, observed checks, zero native writer calls and the coverage disposition in verification. If source closure is blocked, record the exact unresolved rule or path and stop before dependent implementation. Positive coverage would leave strict guards, image writing, independent standalone acceptance, T3 integration, product selection and provider execution outside this ticket.

### T1-F06 Primary-XMP writer and independent reader qualification

**State and responsibility.** Executed on 2026-11-09 after the user selected it. Disposition: qualified for the bounded tested preparation (31 of 31 controls), with `tools/qualification/primary_xmp.py` as writer, splicer and validator and production ExifTool 13.55 as independent reader. The [verification](verification.md#t1-f06-primary-xmp-qualification) owns identities and limits, and the [selection questions](../../discussions/ASSET_REFERENCES.md#t1-f06-qualification-result-and-selection-questions) await the user. On 2026-11-10 the user decided the legacy-XMP question as B-lite. The candidate was changed and requalified (38 of 38 controls); the [B-lite requalification](verification.md#t1-f06-b-lite-legacy-xmp-requalification) owns its identities. The user then [selected that candidate for product use](../../discussions/ASSET_REFERENCES.md#t1-f06-qualification-result-and-selection-questions) on 2026-11-10, with ExifTool 13.55 as acceptance reader. T1-F06 is complete; it hands off to T3b. Main metadata integrator owns a bounded local Windows development qualification. Use the [primary-XMP design](../../design/ASSET_REFERENCES.md#primary-xmp-enrichment-boundary), [AR-8 standalone readback](spec.md#ar-8--source-grounded-naming-and-embedded-standalone-provenance) and [AR-12 controls](spec.md#primary-xmp-qualification-controls). Start from [T1-F04's splice findings](verification.md#coverage-decision-and-exact-candidate-boundary) and the [Adobe preservation counterexamples](verification.md#t1-f03-adobe-sdk-writer-source-evidence). T3a and recursive packet inventory are outside the prerequisites.

1. Define one exact PNG/JPEG writer/splice, bounded strict pre/post validator and separate offline reader. Record artifacts, versions, source/build identities, licenses, hashes, settings and input/output contracts. Use an isolated harness, app-owned literal paths and separate preparation copies. Retain the existing pre-start Windows qualification limits of 256 MiB aggregate Job memory, five seconds Job CPU and 15 seconds wall time for the controlled processing.
2. Exercise every [primary-XMP qualification control](spec.md#primary-xmp-qualification-controls). Record primary packet and copied byte spans, property differences, full JPEG extension reconstruction, rejection stage and zero writer entries on invalid inputs. Verify that the independent reader obtains all expected source facts from the renamed image alone. Treat unavailable coverage, limit exhaustion, invalid output or preservation mismatch as a failed or inconclusive result with the exact condition.
3. Record the bounded qualified, negative or inconclusive disposition in [verification](verification.md). Positive qualification hands exact artifacts, settings and limits to T3b for a separate product-selection decision. No app integration, provider work, product dependency adoption or whole-batch acceptance belongs to this ticket.

## R01CAL-A03-DELIVERY-01-T2

**Current authority:** the subsequent 2026-11-09 instruction selects AR-S4.3 implementation for T2 only, including scoped fixes, tests, isolated desktop verification and records, preserving all four guarantees, then stop. No provider calls or T1/T3-T5 work. The [adoption record](../../discussions/ASSET_REFERENCES.md#scoped-resource-protocol-adopted-2026-11-09) retains the preceding documentation-only instruction.

**Execution:** initially selected on 2026-11-08, then selected for AR-S4.3 implementation on 2026-11-09; main implementer, T2 only including tests, scoped corrections, isolated desktop verification and records, then stop. T1 is not a prerequisite. Preserve inherited work; no provider calls, original-task mutation, global installation/settings, destructive cleanup, remote publication or subagents. New-save publication remains with the [T3a and T3b split](#r01cal-a03-delivery-01-t3).

**Disposition:** completed the selected AR-S4.3 T2 contribution. [Final protocol evidence](verification.md#final-t2-protocol-evidence-and-scoped-assessment) owns the four-guarantee observations, corrections, tested identities and limits; the [original T2 stop](verification.md#t2-reference-and-selected-version-implementation) remains historical evidence. The shared interface and scoped preview contribution are ready for [T3a](#r01cal-a03-delivery-01-t3a), and subsequently [T3b](#r01cal-a03-delivery-01-t3b), when separately selected. Writer qualification, new enriched-save integration and the whole-batch verdict remain outside this contribution. Stop here under the current instruction.

**Purpose:** make one shared interpretation connect precise source destinations to selected-version assets, preview and diagnostics, including historical incomplete output.

**Responsible role:** main implementer/integrator across the document core, server responses and document-session renderer. Shared files include `src/pdfmd/documents.py`, focused parser helpers, `src/pdfmd/server.py`, `src/desktop/main.ts` and the existing preload boundary, renderer document features/types and `src/renderer/index.html`. Retain the existing module responsibilities and canonical test imports.

**Prerequisite and interface:** the [whole-document and destination-span contracts](../../design/ASSET_REFERENCES.md#reference-interpretation-and-destination-policy) are already specified. Establish the shared collector and serializer interface for T3a, T3b and T4. Use the same interpretation across these contributions.

**Work and completion evidence:** implement guarded source correspondence, strict URI lookup, role-aware dependency analysis and input-handle recognition without publishing unresolved handles. Implement selected-version assessment and the [scoped protocol/lease lifecycle](../../design/ASSET_REFERENCES.md#preview-binding-and-return-behavior), reusing verified saved bytes and the existing document-session selection owner. Test cross-block definitions, tables/footnotes/raw HTML, literal exclusions, ambiguous markup and selection/load races. For historical controls, use isolated fixtures with known member inventories; preserve incomplete original bytes and distinguish integrity failure from reference incompleteness.

Use [AR-1](spec.md#ar-1--supported-references-and-presentation), [AR-2](spec.md#ar-2--rejection-and-candidate-preservation), [AR-5](spec.md#ar-5--actual-desktop-reopen-and-link-use), [AR-6](spec.md#ar-6--exact-export-and-relocation-without-inference) and [AR-7](spec.md#ar-7--historical-incomplete-inventory-and-diagnosis) for the relevant parser, historical-view and selection behavior. T2 covers selected-version behavior with the recorded fixtures. T3a owns new schema 1 saves, and T3b owns enriched publication and returned path mappings. T5 checks the complete desktop and export chain.

**Exit:** the shared interpretation/span interface is verified for its supported syntax and rejection cases; actual isolated desktop observations and host/resource checks satisfy all four [T2 protocol acceptance rows](spec.md#t2-protocol-acceptance-checks) against preserved synthetic saved fixtures, with their tested identity recorded in verification. The original data-URL negative observation remains preserved separately and cannot count as a protocol pass. Historical incomplete/corrupt controls retain their distinct outcomes. Hand off these observed results to T3a and T3b. New enriched-save and full relocation acceptance remain explicitly open until the appropriate later checks.

<a id="r01cal-a03-delivery-01-t3"></a>
## Original T3 route

The former T3 is now [T3a for portable image links](#r01cal-a03-delivery-01-t3a) and [T3b for readable, enriched source images](#r01cal-a03-delivery-01-t3b).

## R01CAL-A03-DELIVERY-01-T3a

**Purpose and state.** Fix P2 for new schema 1 saves using existing registered hash paths. **Disposition:** the 2026-11-09 instruction selected T3a implementation; the scoped contribution is completed. [Verification](verification.md#t3a-portable-link-save-implementation-and-verification) owns the tested identity, observations and limits. T3b, T1-F06 and the whole-batch verdict remain open. Main document integrator owns the save collector and its shared resolver integration. Use [T2](#r01cal-a03-delivery-01-t2) and the [portable-link save design](../../design/ASSET_REFERENCES.md#portable-link-save-increment).

**Work and exit.** Pass the current whole-document interpretation and task-owned paths to `dependencies(analysis, registered)`. Preserve exact hash-path and version rules and use the returned dependency union to collect display bytes and associated originals. Apply the [diagnostic registration guard](../../design/ASSET_REFERENCES.md#portable-link-save-increment) before publication. Update the save and resolver comments to reflect the T3a/T3b ownership split. Use the [T3a acceptance](spec.md#t3a-portable-link-acceptance) to verify new saves, failure preservation, desktop reopen/link/Return and the relocated ZIP. Hand the common save path to T3b. Scope ends at portable links and exact saved-version delivery.

**Review follow-up.** The [correction review](verification.md#t3a-correction-follow-up-review) confirms AR-T3A-01 and the improved corruption rejection. The AR-T3A-02 recovery residual was then corrected and tested in the [recovery correction](verification.md#t3a-corrupt-object-recovery-correction). The [storage review](verification.md#t3a-storage-recovery-review) confirms same-hash recovery and records open failure-path findings AR-T3A-03/04. T1-F06 qualification can be selected independently. The [store failure-path correction](verification.md#t3a-store-failure-path-correction) then fixed AR-T3A-03 and AR-T3A-04.

## R01CAL-A03-DELIVERY-01-T3b

**Purpose and state.** Create a source-grounded occurrence and its readable, independently informative deliverable through one accepted schema 2 save. Planned pending the [T3a save path](#r01cal-a03-delivery-01-t3a) and a positively qualified [T1-F06](#t1-f06-primary-xmp-writer-and-independent-reader-qualification) candidate explicitly selected for product use. Both prerequisites are met: T3a is complete, and the [B-lite candidate](verification.md#t1-f06-b-lite-legacy-xmp-requalification) was selected on 2026-11-10. Integrating it must recheck the qualified hash or reopen qualification if the artifact or invocation changes. The user selected T3b implementation on 2026-11-10; see the execution note below.

**Responsible role.** Main native-service/document integrator owns evidence registration, naming/Unicode comparison, metadata integration, schema/HTTP/tool responses and joint publication. Reuse the [versioned schema](../../design/ASSET_REFERENCES.md#versioned-data-and-embedded-schema), [edit API](../../design/ASSET_REFERENCES.md#document-edit-api-and-operation-semantics) and [enriched save flow](../../design/ASSET_REFERENCES.md#enriched-save-flow).

**Work and exit.** Preserve raw evidence before annotation. Create occurrence facts, reserve names, prepare the primary-XMP representation, resolve handles and publish the dependency union, originals, head and receipt together. Exercise explicit eligible legacy adoption, unknown labels, distinct occurrences with equal pixels, real collisions, unreferenced catalog entries, candidate reuse, stale head, interrupted preparation and replay. Reopen and export the identified save and independently read a renamed copy. Use the [criterion mapping](#coverage-and-integration-discipline), keeping source-led meaning checks distinct from byte/name validation. Hand off the coherent creation lifecycle to T4 and record any T5 gaps. Reopen affected qualification if the integrated artifact or invocation differs from T1-F06.

**Execution (2026-11-10).** The user selected T3b implementation. A recoverable baseline of `src`, `tests`, `tools` and `docs` was copied to `.local/t3b-baseline-20261110/` because Git was unavailable in the shell. Work paused for the user's Git question, then resumed after the user installed Git. The [first increment](verification.md#t3b-first-increment-enriched-creation) is implemented and has received a [standalone review](verification.md#t3b-first-increment-review). Follow the review for the correctness and recovery work recommended before handoff and the [discussion](../../discussions/ASSET_REFERENCES.md#t3b-review-and-open-integration-choices) for integration choices. On 2026-11-10 the user selected fixing all five review findings; the [review correction](verification.md#t3b-review-correction) owns their evidence. On 2026-11-11 the user chose the bounded child process for the writer; the [bounded writer evidence](verification.md#t3b-bounded-writer-process) owns its checks. Schema 1 retirement stays open.

On 2026-11-11 the user selected fixing the worker lifecycle findings AR-T3B-05 to 07 and then measuring and sizing writer memory (AR-T3B-08). The [lifecycle and budget correction](verification.md#t3b-writer-lifecycle-and-budget-correction) owns the evidence. The user then selected streaming the engine's image copies and adding a pooled, parallel writer. See [streaming and pool](verification.md#t3b-streaming-and-writer-pool).

On 2026-11-11 the user selected correction of AR-T3B-09 through 11 and a stop before T4. That increment is complete at the scope of the [correction and focused rerun](verification.md#t3b-streaming-and-writer-pool-correction).

On 2026-11-11 the user then selected the cross-process allocation control. Its [evidence](verification.md#t3b-cross-process-allocation) covers controlled concurrent allocation by two engine processes on one Windows store and the AR-T3B-12 correction. The [follow-up review](verification.md#t3b-cross-process-correction-review) establishes the scope of this evidence at the task-writer boundary.

On 2026-11-12 the user selected the AR-T3B-13 and AR-T3B-14 corrections with the per-task lock and a stop before T4. See the [correction and reruns](verification.md#t3b-receipt-and-preparation-correction) for this increment.

Remaining T3b scope:
- AR-9/AR-10 boundary controls on actual destinations (part of the T5 matrix). See the [focused published-suffix verification](verification.md#ar-10-published-suffix-verification) for the local reservation case;
- remaining real-source label and JPEG cases in the [T5 criterion evidence map](verification.md#t5-criterion-evidence-map);
- the agent-facing flow from evidence to `asset_changes` in an actual conversion. The [offline guidance rerun](verification.md#t5-offline-repair-and-same-revision-windows-verification) covers the scripted path and explicit legacy adoption;
- the open choice on retiring schema 1 saves;
- the T5 destination matrix.

Implementation notes for this increment:
- T3b introduced `create` asset changes. See [T4](#r01cal-a03-delivery-01-t4) for correction support;
- the selected `primary_xmp.py` copied byte-identically into `src/pdfmd/`, with a test pinning SHA-256 `74c30f2b…d6a2`. See the [engine guide](../../guides/DOCUMENT_ENGINE.md#enriched-creation-path-t3b) for child-process invocation and the [integration decision](../../discussions/ASSET_REFERENCES.md#t3b-review-and-open-integration-choices) for its basis;
- readable naming, portable comparison keys and task-local SQLite name reservations with the 180-byte check;
- a schema 2 save when an edit creates an occurrence, updates source facts or builds on a schema 2 base. A create can adopt a matching schema 1 asset via `legacy_path`. Schema 1 saves still use hash paths. This transitional rule is a proposal, not an adopted design change.

## R01CAL-A03-DELIVERY-01-T4

**Purpose:** correct an existing occurrence or shared source/page observation without leaving stale references, mismatched embedded facts or changed historical versions.

**Responsible role:** the same edit/publication integrator as T3b. Reuse its operation identities, reservations, prepared representations and atomic visibility boundary; use T2's guarded spans. Avoid separate rename/publication lifecycles.

**Prerequisite and interface:** T3b's complete creation path. Use [correction versus genuine occurrence](../../design/ASSET_REFERENCES.md#synchronized-corrections-and-distinct-occurrences) and [operation semantics](../../design/ASSET_REFERENCES.md#document-edit-api-and-operation-semantics).

**Execution (2026-11-12).** The user selected the first single-occurrence correction after the local T3b checkpoint. Implemented `asset_changes` with one `correct` item and complete replacement values for supplied facts on the selected schema 2 base. The [single-occurrence verification](verification.md#t4-single-occurrence-correction) owns observed reopen, export and retry results.

The user then selected a local single-occurrence checkpoint and a printed-page correction affecting two images, including an unreferenced occurrence. The [shared-page verification](verification.md#t4-shared-printed-page-correction) owns the checkpoint and observed checks for per-task locking, rollback, later linking, reopen, export and retry. See the [T4 follow-up tickets](#t4-follow-up-tickets) for the subsequent work.

**Work and completion evidence:** apply explicit occurrence/source/page patches across all affected catalog occurrences, including currently unreferenced registrations. Rebuild changed representations and operative destinations together; preserve unrelated text, valid independent occurrences, prior names' ownership and historical-base mappings. Exercise shared-page/title updates, metadata-only changes, corrected-name collision, exact retry, restart and failed/stale publication. Inspect corrected saved/reopened/exported output alongside the unchanged earlier version.

Use [AR-4](spec.md#ar-4--editing-identity-and-failed-publication), [AR-10](spec.md#ar-10--collision-allocation-retries-and-distinct-occurrences), [AR-11](spec.md#ar-11--synchronized-corrections-and-immutable-history) and affected [AR-12](spec.md#ar-12--enrichment-fidelity-and-complete-delivery-chain) controls. A fresh second occurrence uses the T3b creation path and preserves the independently valid first citation.

**Exit:** identified correction operations cover occurrence-only, shared-fact and non-filename changes; corresponding saved/reopened/exported output is coherent and earlier versions remain exact. Concurrent allocation, failure, restart and replay controls establish the same publication boundary as creation. Hand off the integrated create/correct revision and any remaining whole-matrix observations to T5.

<a id="proposed-t4-follow-up-tickets"></a>
### T4 follow-up tickets

One document-edit integrator owns the overlapping preparation/publication path and engine tests. See the [completion checks](spec.md#t4-completion-checks).

| Ticket | Contribution and dependency | Completion evidence |
| --- | --- | --- |
| [T4-A — Correct shared source facts](#t4-a--correct-shared-source-facts) | Refresh the catalog from validated `source_update` on the shared-page baseline, and update `edit_document` guidance. | [Shared source correction verification](verification.md#t4-a-shared-source-correction). |
| [T4-B — Apply corrections per occurrence](#t4-b--apply-corrections-per-occurrence) | Use the T4-A preparation path to apply distinct explicit corrections together with any shared page or source changes. | [Multiple occurrence correction verification](verification.md#t4-b-multiple-occurrence-corrections). |
| [T4-C — Verify the correction lifecycle](#t4-c--verify-the-correction-lifecycle) | Check the integrated T4-A and T4-B revision through the normal edit route, Windows development desktop and a matching frozen engine. | [Correction lifecycle verification](verification.md#t4-c-correction-lifecycle). |

#### T4-A — Correct shared source facts

Implemented and verified on 2026-11-12 for the selected [shared source metadata case](spec.md#t4-completion-checks). The catalog correction pass in `documents.py` reuses the existing preparation and publication path, and `edit_document` describes the supported patch. The [verification](verification.md#t4-a-shared-source-correction) owns the observed checks and tested identities. The [T4-A selection](../../discussions/ASSET_REFERENCES.md#t4-a-selected) stopped at this ticket before the subsequent T4-B instruction.

#### T4-B — Apply corrections per occurrence

Implemented and verified on 2026-11-12 for the selected [multiple explicit corrections case](spec.md#t4-completion-checks). The edit engine validates duplicate IDs before preparation and the tool guidance describes the per-occurrence rule. The [verification](verification.md#t4-b-multiple-occurrence-corrections) owns the local T4-A checkpoint and observed checks. The [T4-B selection](../../discussions/ASSET_REFERENCES.md#t4-b-selected) stopped at this ticket before the subsequent T4-C instruction.

#### T4-C — Verify the correction lifecycle

Completed on 2026-11-12 for the selected [collision, history and recovery case](spec.md#t4-completion-checks). The [verification](verification.md#t4-c-correction-lifecycle) owns the T4-B checkpoint, integrated checks and coverage limits. The shared-original diagnostic correction is part of this ticket's repeated-stream control. Execution stops here per the [T4-C selection](../../discussions/ASSET_REFERENCES.md#t4-c-selected).

## R01CAL-A03-DELIVERY-01-T5

**Purpose:** verify the combined user outcome from one identified saved version through actual desktop close/reopen/link/return/export and independent relocated use.

**Responsible role:** main integrator/reviewer. Own the combined criterion assessment, actual environment/artifact identities, supported fixes and documentation synchronization. This role does not imply a separate agent or broaden publication authority.

**Prerequisites:** integrated T2, T3a, T3b and T4, and the qualified and selected T1-F06 artifacts. Use the [declared destination/reader matrix](../../design/ASSET_REFERENCES.md#portable-comparison-and-destination-matrix), [preservation/export rules](../../design/ASSET_REFERENCES.md#export-and-existing-version-preservation), and all [AR-1 through AR-12 criteria](spec.md#acceptance-and-evidence-correspondence).

**Work and completion evidence:** reuse earlier meaningful checks and run the missing integration/desktop/platform observations. Verify actual member bytes, readable filenames, source facts recovered from an image alone, originals, selected-version identity, historical diagnosis, failure/replay and unchanged provider usage. Check the same portable package on the declared Windows destination with the selected external viewer and independent reader. The Linux and macOS rows are deferred by the [platform scope amendment](spec.md#status-and-authority) and remain unverified; this is not a Linux/macOS app-packaging ticket. Record unavailable targets explicitly and leave the associated acceptance open.

Resolve in-scope integration defects and recheck affected criteria when future execution authority includes implementation. Preserve failed evidence and source limitations. The [verification owner](verification.md) records criterion-level observations, residuals and the combined verdict; ticket completion alone is not that verdict. Broader live conversion, numerical tuning, original A03 repair, installer delivery and cleanup remain outside this batch.

**Exit:** every AR-1–AR-12 criterion has a source-linked observation or explicitly unresolved disposition, and the combined verdict accounts for all required destinations and source-preservation limits. Whole-batch acceptance requires the applicable conditions to pass; an unavailable required platform/check leaves acceptance incomplete. A completed review with unresolved criteria is recorded as such and does not become an accepted delivery. Keep software behavior, source-image fidelity, metadata interoperability and package consistency distinguishable in the verdict.

### T5 local execution

The user selected the [T4-C checkpoint and available local T5 checks](../../discussions/ASSET_REFERENCES.md#t5-local-verification-selected) on 2026-11-12. The local integration and [focused published-suffix check](verification.md#ar-10-published-suffix-verification) are complete under their selected scopes. The user then selected the [offline publisher-source check](../../discussions/ASSET_REFERENCES.md#t5-offline-publisher-source-check-selected), completed within the [recorded scope](verification.md#t5-offline-publisher-source-check). On 2026-11-12 the user [limited the platform scope to Windows](../../decisions/REBUILD.md#windows-only-platform-scope-2026-11-12), deferring the Ubuntu and macOS rows. Use the same canonical ZIP for the Windows row. The user then accepted Windows 10 for that row and selected the [Windows-row and scripted tool-path checks](verification.md#t5-windows-row-and-agent-tool-path-checks), which corrected AR-T5-01 and AR-T5-02 and recorded the open AR-T5-03 guidance conflict. The [criterion evidence map](verification.md#t5-criterion-evidence-map) identifies the remaining checks.

The user [selected the offline follow-up](../../discussions/ASSET_REFERENCES.md#t5-offline-repairs-and-same-revision-checks-selected) on 2026-11-12. Main integrator scope covers private export preparation and retry settlement (AR-T5-04), consistent system and tool guidance with explicit legacy adoption (AR-T5-03), and the desktop and frozen-engine rerun on one identified revision. Preserve the same-version package and compare its actual member bytes, relocated links and standalone records. Follow the [criterion evidence map](verification.md#t5-criterion-evidence-map) for remaining scope. The user subsequently selected the [AR-T5-05 to 07 cleanup](../../discussions/ASSET_REFERENCES.md#ar-t5-05-to-ar-t5-07-cleanup-selected) and a standalone review. See the [cleanup evidence](verification.md#ar-t5-05-to-ar-t5-07-cleanup) and [review findings](verification.md#standalone-review-of-the-t5-cleanup).

The selected offline follow-up has completed. The [same-revision Windows verification](verification.md#t5-offline-repair-and-same-revision-windows-verification) owns the results and the [criterion map](verification.md#t5-criterion-evidence-map) owns remaining acceptance.

### T5 follow-up for AR-T5-08 to AR-T5-10

On 2026-11-13 the user selected [AR-T5-08 to AR-T5-10](verification.md#standalone-review-of-the-t5-cleanup) for offline repair and regression checks. The main integrator starts with actionable handle rejection under AR-2, then checks verified ZIP retention after a publication conflict under AR-6 and restores the committed-veto premise in the guard tests. Live adoption and branch publication are deferred.

The selected offline work is complete. See the [regression evidence](verification.md#t5-offline-repair-for-ar-t5-08-to-ar-t5-10) and the [remaining T5 scope](verification.md#t5-criterion-evidence-map).

### T5 follow-up for AR-T5-11

The user selected the [corrupt competing ZIP repair](verification.md#ar-t5-11--a-corrupt-competing-zip-can-discard-the-verified-preparation) for offline implementation. Under AR-6, a DEFLATE read failure in the competing ZIP must leave it in place and preserve the verified preparation with a conflict diagnostic naming both paths. Check the same-destination retry and the identical-ZIP control. Live adoption and branch publication remain deferred.

The selected offline work is complete. See the [regression evidence](verification.md#t5-offline-repair-for-ar-t5-11).

### T5 closing tickets

The user [selected](../../discussions/ASSET_REFERENCES.md#t5-closing-route-selected) the T5 closing route on 2026-11-13, requested tickets before execution and then asked to start them. Each executor reads [AGENTS.md](../../../AGENTS.md), this section, the ticket's linked basis and the [T5 ticket](#r01cal-a03-delivery-01-t5). The [criterion map](verification.md#t5-criterion-evidence-map) owns remaining acceptance, and [verification](verification.md) receives each ticket's observations in a new section named in the ticket.

| Ticket | Contribution | Depends on | Execution |
| --- | --- | --- | --- |
| [T5-F12](#t5-f12--repair-ar-t5-12) | Keep the verified preparation for any unreadable competing ZIP | None | [Repair and document-engine checks complete](verification.md#t5-offline-repair-for-ar-t5-12). Full suite in T5-R |
| [T5-L1](#t5-l1--bounded-live-adoption-run) | Observe whether a real model takes the enriched save path | None | [Single authorized run and review complete](verification.md#t5-live-adoption-run) |
| [T5-G1](#t5-g1--clarify-enriched-save-guidance) | Clarify how to carry established source facts and evidence of absence into the first enriched save | T5-L1 | [Offline verification complete](verification.md#t5-enriched-save-guidance-verification) |
| [T5-R](#t5-r--final-windows-chain-on-the-verdict-revision) | Repeat the Windows desktop and frozen-engine chain once | T5-F12, T5-L1 and T5-G1 complete, with no unreviewed code change after them | After T5-G1 and T5-F12 |
| [T5-V](#t5-v--combined-t5-verdict) | Record the combined T5 and batch verdict | T5-R | After T5-R |
| [T5-P](#t5-p--publish-the-batch-branch) | Push the branch and open a PR to `master` | Push: none. PR: T5-V, or a draft PR earlier | Initial [push verified](verification.md#branch-publication) |

**Execution order:** T5-P initial push, T5-F12, T5-L1, the selected T5-G1 follow-up, T5-R, T5-V, then the PR. Coordinate shared edits to `verification.md`, this file, [WORK_ITEMS](../../WORK_ITEMS.md) and [CURRENT_STATE](../../CURRENT_STATE.md) through one writer.

**Rules for every ticket.** Commit locally when the ticket is complete, with the attribution the repository uses. Do not push except under T5-P. Do not merge, change global settings or install software globally. Do not read credentials from conversation or authentication logs. Keep runtime stores, logs and outputs in a new uniquely named ignored folder under `.local/`, `workspaces/` or `outputs/`, following [artifact storage](../../ARTIFACT_STORAGE.md#ownership-and-locations). Do not overwrite earlier runs. Preserve failed evidence and say what was not run. If a ticket finds a new defect, record it as the next `AR-T5-NN` finding with a reproduction, severity and impact. Add it to the [work register](../../WORK_ITEMS.md#context-capability-and-delivery-work) and stop for the user. Do not fix it in the same ticket unless it is inside that ticket's stated scope. Update [CURRENT_STATE](../../CURRENT_STATE.md#focus-and-resume-route) when the ticket finishes. Run `python tools/docs/check_docs.py` and `git diff --check` before committing.

#### T5-F12 — Repair AR-T5-12

**Basis:** [AR-T5-12](verification.md#ar-t5-12--other-unreadable-competing-zips-still-discard-the-verified-preparation), [AR-6](spec.md#ar-6--exact-export-and-relocation-without-inference), [export retention contract](../../design/RUNTIME_AND_DELIVERY.md#continuation-feedback-and-delivery-settlement). The method is settled. Offline only; no provider call.

**Change.** In `Documents.export` in `src/pdfmd/documents.py`, the local `verify(path)` returns `False` only for `zipfile.BadZipFile` and `zlib.error`. `zipfile` also raises `RuntimeError` (encrypted member), `NotImplementedError` (unsupported compression method), `EOFError` and other errors. Comparing a *competing destination* has one meaning: does it already hold this version's export? Any failure to read it means no.

- Add a helper, for example `holds_this_export(path)`, that returns `verify(path)` and returns `False` on any `Exception`. Use it at both destination comparisons: the pre-check `if self.store.maybe("export", intent) and verify(target)` and the comparison after `os.link` raises `FileExistsError`. The `except OSError` around the post-link comparison then becomes unnecessary.
- Keep `verify(temp)` and the post-publication `verify(target)` strict. Those check the attempt's own files, and a failure there must still be reported.
- Keep the outer `except OSError` mapping to `_destination_error` for the attempt's own folder, preparation and publication errors.
- Expected behavior: a competing destination that appears during publication and cannot be read returns 409. The message names the destination and the retained preparation. The preparation keeps the selected version's exact members, and the competing bytes are unchanged. An existing unreadable destination at the pre-check returns the existing-destination conflict, 409, "The destination exists". This includes an existing directory, which currently gives 400 through the `OSError` path. Record that response change in the verification section.

**Tests.** In `tests/engine/documents/test_documents.py`, extend the parameter list of `test_export_preserves_a_destination_that_appears_during_publication` with `encrypted_zip` and `unsupported_method_zip`. Build each from the source preparation's bytes, as `corrupt_zip` does:

- **Encrypted:** set bit 0 of the general-purpose flag at offset 6 of the first local header (`PK\x03\x04`) and at offset 8 of the first central directory header (`PK\x01\x02`).
- **Unsupported method:** set the 16-bit compression method to 93 at offset 8 of the first local header and at offset 10 of the first central directory header.

Assert inside the hook that the member names still match and that `archive.read` raises the expected exception, so the case cannot pass vacuously. Add a retry for each new case, as for `corrupt_zip`. The retry reaches the pre-check with the intent the first attempt recorded. Add the same retry to the `directory` case; it must return 409 with "destination exists" instead of the current 400. First run the new cases against the unchanged code and record that they fail with 500. The review's probe, which is not in the repository, saw `RuntimeError` and `NotImplementedError` with 500 and a deleted preparation.

**Checks.** `.venv\Scripts\python.exe -m pytest tests/engine/documents` must pass. On 2026-11-13 the group had 220 tests before these additions. Then run the full `.venv\Scripts\python.exe -m pytest` once and record the count and exit code. Record SHA-256 of `documents.py` and `test_documents.py`.

**Records.** Add verification section `## T5 offline repair for AR-T5-12`. Update the [execution guide](../../guides/EXECUTION_AND_DELIVERY.md#10-explicit-version-export-and-publication), which describes the decompression failure path, to say that any read failure of a competing destination is a conflict. Add the evidence link to the AR-6 row of the [criterion map](verification.md#t5-criterion-evidence-map), and update the AR-T5-12 row in WORK_ITEMS.

#### T5-L1 — Bounded live adoption run

**Question:** under ordinary guidance, does a real model deliver source images through `edit_document` with `asset_changes` creates on its first image save, producing schema 2 with readable names and standalone provenance? Or does it use a schema 1 hash-path link? The run answers this for one model, source and request. It is not a reliability rate and does not certify conversion fidelity in general. Basis: [AR-8](spec.md#ar-8--source-grounded-naming-and-embedded-standalone-provenance), [AR-T5-03](verification.md#ar-t5-03--system-instructions-also-steer-delivery-to-schema-1) and the [selection](../../discussions/ASSET_REFERENCES.md#t5-closing-route-selected).

**Authority.** One fresh task and one Start against the provider, within the limits below. No Continue, replay, second Start, extension or replacement run. Do not repair or coach mid-run. If preparation fails, stop before Start and report.

**Source and scope.** Use `references/news-writing/source.pdf` (ignored, local). Before anything else, check that it is 290 pages with SHA-256 `9d23a3c4a519a1c04357a6f2e64093afd1c001034e8e4576561883c13b1cad4e`. A missing or different file blocks the run; do not substitute another PDF. The requested scope is physical pages 1–3. Each is one full-page DCT JPEG with no printed page number: page 1, the front cover, is RGB, object 2137, with original stream SHA-256 `228660d981f8af0dc7415d84f8b4b1cb06b052a416e7129f2e9cdeb4f715088b`; page 2 is RGB and page 3 is gray. Use this exact task request, written in the A03 form with no coaching:

> Convert physical pages 1–3 (the front cover and front matter) of this 290-page PDF into faithful, readable, reusable Markdown with source images where needed. Account truthfully for the full physical-page inventory and deliver your selected saved version. Choose your own source reads and conversion methods.

Do not supply tool instructions, `asset_changes` examples, expected names, earlier outputs, reviewer renders or this ticket to the converter.

**Route and limits.** Use the A03 values recorded in [Task A's identities](../../verification/20261106_1408_R01CAL_TASK_A.md#identities-and-preserved-conditions) and [A03's configuration](../R01CAL-A03/spec.md#selected-configuration-and-finite-interval):

- **Route:** `cliproxy/gpt-6.1-sol`, `reasoning_effort: low`, Chat Completions through the existing Nexus gateway, vision on.
- **Allowances:** context 131,072, output 8,192, image 4,096.
- **Request limits:** at most 12 physical application sends, including compaction and response-correction sends; at most 1,200 known active seconds; Stop at 1,500 seconds of wall time after Start; one attempt per request; replay off.
- **Optional mechanisms:** trusted scripts, the observer and usage anchoring stay off.

If the current app cannot set a field identically, for example because waiting now defaults to streaming progress, record the effective value. A different waiting policy is acceptable. A different route, model or effort is not. Use the existing subscription route only, with no purchase, top-up or paid fallback. If metered billing exposure is unknown or has changed, stop before Start and ask the user.

**Preparation, offline.** Follow steps 1–2 of [A03's preparation](../R01CAL-A03/spec.md#preparation-execution-and-evidence-responsibilities):

- **Launch:** use the development launcher, `.\tools\dev\start.ps1 -Workspace <new workspace>`. It loads the credential from the ignored `private/api-key.txt` without printing it.
- **Task:** import the source and create the fresh task, then record the source, build, lockfile and task identities and the effective limits.
- **Readiness:** confirm Start, monitoring, Stop, reopen and export work, with zero requests.
- **Tooling:** drive the UI with the supported Electron and Playwright tooling. Native Windows capture is unreliable ([OPS-01](../../WORK_ITEMS.md#context-capability-and-delivery-work)). [A03 T3](../R01CAL-A03/verification.md#t3-single-finite-conversion-2026-11-08) shows the monitoring and settlement records to keep.

**Run.** Start once and monitor until the task reports complete, partial or waiting, or a limit stops it. Keep the frozen payloads, native responses, candidates, operation receipts, versions and usage the store records.

**Observations to record:**

1. **First image save.** Which `edit_document` call first carries an image, its schema version, and whether it uses `asset_changes` creates with `facts.image_ref` taken from `extract_image` or `render_page`. Quote any rejection message and the agent's next attempt; [AR-T5-08](verification.md#ar-t5-08--handle-guidance-can-prescribe-an-invalid-retry) changed those messages.
2. **Image path.** Whether the agent used `extract_image`, which preserves the DCT originals, or `render_page`. Compare each retained original with the PDF stream bytes. Record the delivered basenames and the printed-label state for each page. No printed label is visible on pages 1–3, so `none` with evidence is expected, and `unknown` must be explained.
3. **Selected version.** Close and relaunch the app, open the selected version explicitly, check that the images decode and Return works, then export it. Use a fresh short folder under `outputs/`, not a long path. Confirm that requests and attempts do not increase during reopen and export.
4. **Standalone provenance.** Copy each delivered image alone into an empty folder, rename it and read it with ExifTool 13.55 at `.local/ar-t1-20261108-qualification/dependencies/exiftool/exiftool-13.55_64/exiftool.exe`. Check the source title, physical page, printed-label state and source identity against the saved record.
5. **Content.** Compare the saved Markdown with the visible pages 1–3 and record discrepancies. Review the page map for all 290 pages.
6. **Usage.** Record native usage, active time, sends and anything unknown.

**Result.** Report one of the following:

- **Adopted:** the first image save is schema 2 through creates.
- **Adopted after correction:** a rejected attempt was followed by an autonomous schema 2 save.
- **Not adopted:** the selected version has schema 1 hash links or embeds.
- **Inconclusive:** no image was saved, or the run stopped first.

Keep this result separate from content fidelity, AR-8 naming and provenance on real pages, and package consistency. Do not change the guidance or code in this ticket. Any of these sends the decision on requiring enriched saves back to the user: not adopted, adopted only after correction, or a defect found in the run.

**Records.** Add verification section `## T5 live adoption run`. Update the AR-8 row, and AR-12 where the run applies, in the [criterion map](verification.md#t5-criterion-evidence-map). Add the result to the [selection discussion](../../discussions/ASSET_REFERENCES.md#t5-closing-route-selected) and update the AR-T5-03 row in WORK_ITEMS. Usage evidence follows the [cost rule](../../../AGENTS.md#verification-and-records): keep unknowns unknown.

#### T5-G1 — Clarify enriched save guidance

**Authority and scope.** The user [selected](../../discussions/ASSET_REFERENCES.md#enriched-save-guidance-clarification-selected) guidance and offline verification after T5-L1. Keep the save API, schema 1 transition and source-reading choices under the existing [enriched save contract](../../design/ASSET_REFERENCES.md#enriched-save-flow).

**Work and check.** In the ordinary request's system instructions and `edit_document` description, explain how to use `source_update` for facts already established from evidence, including a visible source title. Explain that an asserted absence of a printed label uses `printed_basis`, and an asserted absence of a caption or figure label uses that fact's `basis`. Keep unresolved facts unknown. Extend the existing scripted agent check to inspect actual wire guidance, make a first enriched save with a visible title and both printed-label states exercised by the script, then verify the exact saved and exported provenance. Preserve controls for unknown values and legacy saves. Recheck context admission tests affected by the guidance size.

#### T5-R — Final Windows chain on the verdict revision

**Purpose:** one Windows desktop and frozen-engine chain on the product revision that carries the T5 verdict, replacing the `2b8e2ef` run in the [same-revision record](verification.md#t5-offline-repair-and-same-revision-windows-verification). Offline. Start after the committed T5-F12, T5-L1 and T5-G1 work. Bind the result to the tested commit and show that the verdict commit carries the same product and test sources.

**Steps.** Repeat that record's chain on the current commit, using the harness scripts retained under ignored `.local/t5-final-c19a72/` and its `chain/` folder (`seed.py`, `desktop.cjs`, `verify-package.py`, `verify-browser.cjs`) as the starting point. Copy them to a new run folder and adjust paths.

1. **Builds.** Build the Electron app with `pnpm build` and freeze the engine with `.\tools\build\build-windows.ps1`, both from the same commit. Record the commit, the frozen engine SHA-256 and the tool versions.
2. **Smoke and regression checks.** Run the frozen startup and the writer smoke check (`tools/build/check-frozen-engine.py`) and `pnpm test:desktop`. Run the full `.venv\Scripts\python.exe -m pytest` once and record the count and exit code.
3. **One version through Windows delivery:**
   - Save a schema 2 version on the synthetic PDF through the frozen HTTP edit route, then advance the head in the desktop editor.
   - Close and relaunch the app, select the older version explicitly, decode its image links and Return.
   - Make two desktop exports and one frozen export, and compare all members byte for byte.
   - Extract to a short new folder, follow the links in Chrome for Testing 157.0.8103.38 (`.local/t5-971eccc/chrome/chrome-win64/chrome.exe`), and read each renamed standalone image with ExifTool 13.55.
   - Check that copied ranges outside primary XMP and the decoded pixels match the source evidence.
4. **Windows-row controls.** Repeat the following:
   - the collision package through Python `zipfile`, Windows `tar.exe` and PowerShell 7 `Expand-Archive`;
   - the long ZIP path and the overlong-component 400;
   - the deep-extraction limits;
   - the export conflict cases: file, directory, corrupt, encrypted and unsupported-method competitors, plus the concurrent identical-ZIP retry.

**Records.** Add verification section `## T5 final same-revision Windows verification` with all identities. Point the AR-5, AR-6 and AR-12 rows of the [criterion map](verification.md#t5-criterion-evidence-map) at it. If any check fails, record it as a finding and stop.

#### T5-V — Combined T5 verdict

**Purpose:** meet the [T5 exit](#r01cal-a03-delivery-01-t5). Every AR-1–AR-12 criterion gets a linked observation or an explicit unresolved disposition, and the batch receives one combined verdict. Documentation only.

**Work.**

- Add verification section `## T5 combined verdict`. Give one row per criterion with its evidence and verdict, built on the [criterion map](verification.md#t5-criterion-evidence-map) and the T5-F12, T5-L1 and T5-R sections.
- Report software behavior, source-image fidelity, metadata interoperability, package consistency and real-model adoption separately before the combined verdict.
- Apply the [verdict scope amendment](spec.md#status-and-authority): a publisher JPEG with competing or legacy XMP is a recorded AR-12 limitation, not a blocker.
- Record the Linux and macOS rows as deferred under [XPLAT-01](../../WORK_ITEMS.md#context-capability-and-delivery-work), unverified.
- An "inconclusive" or "not adopted" result from T5-L1 leaves AR-8's agent path open and must be stated in the verdict. It does not justify calling the batch fully accepted.

**Also update:**

- the T5 row of the [sequence table](#sequence-and-dependencies);
- the R01CAL-A03-DELIVERY-01 row in WORK_ITEMS, with residual items and their revisit conditions;
- [PHASE_PLAN readiness](../../PHASE_PLAN.md#readiness-and-evidence) only if a stage's completion basis changed: this batch does not by itself close Stage B or Stage D;
- CURRENT_STATE.

Recommend the next work from [WORK_ITEMS selection](../../WORK_ITEMS.md#selection-now) without selecting it.

#### T5-P — Publish the batch branch

**Authority:** the user [authorized](../../discussions/ASSET_REFERENCES.md#t5-closing-route-selected) pushing `codex/r01cal-a03-delivery-01` and opening a PR to `master`. Merging, force-pushing, rewriting history and deleting branches are not authorized.

**Work.**

1. **Push.** Check that the working tree is clean and that no ignored private data is tracked: `git ls-files` must not include `private/`, `references/`, `.local/`, `workspaces/` or `outputs/`. Then run `git push -u origin codex/r01cal-a03-delivery-01`. This can happen at any time and again after each ticket. If the push is rejected, stop and report; do not force.
2. **PR.** After T5-V, open a PR with base `master`. Opening a draft PR earlier is also allowed. The description gives:
   - the problem: P2 broken portable source-image links from A03;
   - the delivered behavior: portable links, enriched schema 2 images with readable names and standalone XMP provenance, corrections, export publication protection, and Windows-only scope;
   - the T5 verdict and its open limits;
   - the commands and evidence used, linking verification sections.

   Do not merge. Bind and monitor the PR only as the user directs.

**Records.** Note the remote branch and PR link in the T5-V verification section, or in a short `## Branch publication` note if T5-V has not run yet.

## Coverage and integration discipline

| Criterion owner | Primary contribution / dependencies | Final acceptance responsibility |
| --- | --- | --- |
| [AR-1 — references/presentation](spec.md#ar-1--supported-references-and-presentation) | T2 interpretation/spans/URI, T3a and T3b same-save integration, T4 rewritten destinations | T5 verifies saved and rendered correspondence |
| [AR-2 — rejection/candidates](spec.md#ar-2--rejection-and-candidate-preservation) | T2 classification, T3a and T3b rejection/candidate retention, T4 correction failures | T5 verifies integrated failure behavior |
| [AR-3 — display/original dependencies](spec.md#ar-3--display-and-original-dependency-preservation) | T3a and T3b inventories/bytes, T1-F06 qualifies enrichment | T5 verifies actual saved and packaged members |
| [AR-4 — editing/identity/publication](spec.md#ar-4--editing-identity-and-failed-publication) | T3a schema 1 save, T3b enriched create/rebuild/replay, T4 correction and failure integration | T5 verifies coherent selected-version lifecycle |
| [AR-5 — desktop reopen/link use](spec.md#ar-5--actual-desktop-reopen-and-link-use) | T2 selected-version UI/identity, T3a and T3b/T4 provide new saved outputs | T5 verifies actual close/reopen/link/return for the integrated target |
| [AR-6 — exact export/relocation](spec.md#ar-6--exact-export-and-relocation-without-inference) | T2 selected-version/diagnostic behavior, T3a and T3b/T4 finalized version contents | T5 verifies ZIP bytes, relocated links and no additional inference |
| [AR-7 — historical diagnosis](spec.md#ar-7--historical-incomplete-inventory-and-diagnosis) | T2 owns incomplete/unavailable/integrity controls | T5 checks integration did not heal or alter historical fixtures |
| [AR-8 — naming/standalone provenance](spec.md#ar-8--source-grounded-naming-and-embedded-standalone-provenance) | T3b source facts/names/records, T1-F06 independent-reader qualification, T4 changed facts | T5 performs source-led and copied-image checks |
| [AR-9 — portable spelling/shortening](spec.md#ar-9--portable-spelling-exact-180-byte-limit-and-semantic-shortening) | T3b naming/comparison/budget, T4 corrected/suffixed names | T5 verifies semantic fidelity and the declared destination matrix |
| [AR-10 — collision/retry/occurrence](spec.md#ar-10--collision-allocation-retries-and-distinct-occurrences) | T3b durable allocation and separate creation, T4 corrections/reservations/history | T5 verifies restart and delivered identity correspondence |
| [AR-11 — synchronized corrections](spec.md#ar-11--synchronized-corrections-and-immutable-history) | T4 owns correction; T2 and T3b supply spans and publication lifecycle | T5 verifies new/old saved, reopened and exported versions |
| [AR-12 — fidelity/complete chain](spec.md#ar-12--enrichment-fidelity-and-complete-delivery-chain) | T1-F06 primary-XMP controls, T3b/T4 integrated image preservation | T5 verifies one identified version through the complete chain and matrix |

This table assigns contribution and final checking responsibility; the linked spec remains the owner of conditions and expected results, and verification owns actual outcomes. It asserts no criterion pass. Reuse an earlier observation only when its exact code/artifact/input basis still supports the criterion; recheck when a relevant change or unresolved concern invalidates that basis.

The adopted split separates the original P2 repair from writer qualification, then joins both for enriched creation, correction and combined acceptance. It does not split every library/file into its own ticket or defer all integration until the end. Keep each ticket's implementation/evidence links here when work is selected; no commits, runs or completed statuses are invented during planning. Material discoveries update the affected dependency and design decision rather than silently weakening acceptance.
