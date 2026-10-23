# Current state

Updated 2026-10-23, Asia/Hong_Kong. Current human instructions authorize focused implementation increments toward autonomous, faithful PDF conversion: fix evidenced defects, add necessary capabilities and verify complete delivery without reducing scope or agent autonomy. The old repository remains unchanged. Reviews and historical proposals supply evidence to assess, not an automatic implementation queue.

## Implemented application

The first increment implements an Electron/TypeScript/React workbench, one Python LangGraph controller, native Nexus requests, PDF/OCR/preview/script tools, transient context assembly, immutable documents and explicit-version ZIP export. [ARCHITECTURE](ARCHITECTURE.md#implementation-map-and-selected-dependencies) maps modules and pins. [CONTRACTS](CONTRACTS.md#implemented-first-version-contracts) specifies executable Q1–Q3 choices. [OPEN_QUESTIONS](OPEN_QUESTIONS.md) records design closure without claiming universal runtime or content acceptance.

The desktop imports an unchanged PDF and scope, shows source pixels and saved Markdown/HTML/evidence, runs or stops the agent, accepts later instructions, edits saved blocks locally, selects versions and exports partial or complete work. Reopening loads persisted state without starting inference. Nexus uses native non-streaming Chat Completions or Responses. Credentials stay outside task journals and can be remembered with Windows encryption. Trusted scripts are off by default and run with host-user permissions when enabled.

`Start Workbench.cmd` opens the local Windows folder app with `workspaces/default`. The PowerShell launcher provides the same default and an override. `tools/setup.ps1` installs locked dependencies; `tools/build-windows.ps1` bundles the engine and desktop. Direct executable/`pnpm dev` launch uses Electron's user-data directory unless `PDFMD_DATA` is set. [README](../README.md) gives commands.

No application changes have been pushed or published as a GitHub release during this task. Runtime data, copied references, private configuration, builds and review outputs are Git-ignored. The user's pre-existing `review-code.txt`, `review-docs.txt` and `review-src.txt` remain untouched and outside this increment.

## Response-correction increment

Purpose: remove two evidenced barriers to autonomous continuation in baseline `7bba197`: text-only model narration immediately paused the job, and rejected handoff re-entry reused the same accepted candidate without a repair route. This increment changes those execution paths, rather than attempting to certify overall conversion quality or reopen every review proposal.

- Text-only normal replies now retain their original history and schedule application feedback asking for a useful tool action or explicit `report`. Necessary questions and partial delivery can be formalized without assuming a user answer. `report(waiting)`, partial reports, cancellation and budgets still stop execution.
- Invalid handoff JSON/schema, failure to reduce input and unexpected compaction tool calls now retain separate correction feedback. A new fitting request carries the error and covered history, optionally the rejected candidate text when capacity permits. Old context remains active until a valid handoff applies. Native acceptance records remain unchanged; compaction tool calls are not executed.
- `max_response_repairs` is configurable for new tasks in the desktop connection dialog, default 2, zero disables. Separate normal and compaction counts persist across restart and ordinary Continue. A new user amendment or document head starts a new episode; consumed task attempts/time remain intact. This is a tunable starting policy, not a demonstrated optimum or a semantic-progress detector for arbitrary tool loops.
- Feedback and handoff identities are stable. Transactional event receipts prevent duplicate correction/application events at the tested persistence-before-checkpoint gaps. Full model replies, evidence, useful candidates and saved versions remain available.

Implementation: `runtime.py`, `context.py`, `storage.py`, `schema.py`, and the desktop limit control. No dependency/framework replacement or upgrade was needed: explicit graph transitions and immutable receipts fit this problem. [CONTRACTS Q2/Q3](CONTRACTS.md#implemented-first-version-contracts) owns the effective behavior; the execution/context guides explain it.

Verification:

- All 30 Python tests pass. New regression coverage adds text-only continuation through source read, image delivery, exact document save, reopen and byte-checked ZIP export for Chat Completions and Responses. It also covers correction exhaustion across restart, new-instruction recovery, cancellation, original request budgets, waiting/partial reports, invalid and oversized handoff repair, non-execution of compaction calls, and feedback/handoff checkpoint gaps. Tests live in `tests/test_response_repairs.py` alongside the retained baseline checks.
- TypeScript checking and desktop production build pass. The development Electron workflow deliberately begins with text-only narration, then completes a two-page synthetic PDF in six local fixture responses without Continue. Saved source text, source-image delivery, actual saved-output preview, export, local edit and reopen are checked. No live provider calls are part of these checks.
- Windows engine, folder app and NSIS installer are rebuilt with the correction code. Packaging log: `.local/response-repair-build.log`. The rebuilt folder app passes the desktop workflow with six local fixture responses, the default correction setting of 2, and exact saved text matching both source pages. Retained workspace: `.local/desktop-duh0Ch`; screenshots: `.local/qa/`. Installer execution and clean-machine installation are not tested.
- These are scripted-response software and artifact checks. They do not establish real-model compliance with correction instructions, source-led quality on unseen PDFs, summary fidelity, or any reduction in actual Nexus fees. This increment makes no new live Nexus call; the older Nursing exercise retains its limitations below.

Related known work remains separate: stale-base/candidate edits can overwrite newer document content; large-result projection can still force unnecessary compaction or block progress; existing-job limit changes are ignored; crash downtime is charged as active time; prepared requests can retain stale inputs after user amendments; queued cancellation has cleanup gaps; truncated native responses and unknown local effects still stop. The next recommended focused batch is stale-base and candidate-reuse protection with actionable local repair, because it directly protects already-correct saved work. Large-evidence admission and resume/budget corrections follow; this is not a requirement to solve every risk before another deliverable increment.

## Copied inputs

The requested subagent copied 47 reference files (242,220,051 bytes, including the manifest) and two private files. There were no destination collisions. Every copy matched its source bytes, all 46 manifest entries matched, and all five PDFs contained real PDF bytes, including the large LFS-backed JRE source. Credentials were never displayed. Both directories are ignored. Receipt: `.local/reference-copy-report.json`.

`private/provider.json` selects the user's loopback Nexus Chat Completions route and `cliproxy/gpt-6.1-sol`. `private/api-key.txt` supplies the credential programmatically. The live exercise retained the configuration's 40-request/1,200-active-second limits and 180-second request timeout, with no replay. Its 131,072 context, 8,192 output and 4,096 per-image allowances are explicit local assumptions, not discovered provider specifications.

## Verification and observed corrections

### Offline and desktop checks

- The original increment passed sixteen Python tests: exact candidate reuse, supplied-field metadata patches, insertion/stale-head checks, exact text patches, whole-document references/footnotes, source assets/ZIP bytes, persistent budgets, accepted-batch cancellation, native Responses reasoning/call pairing, rejected/truncated calls, accepted-reply/result-pointer gaps, commit-before-checkpoint resume, compaction boundaries, local authentication, HTML sanitation and opt-in script output retention. Current response-correction verification is recorded above.
- The original development and Windows folder builds passed a desktop fixture workflow: source import, native image input, saved-output screenshot, local edit, version export and reopen without more inference. That baseline used five local fixture responses. The current six-response correction workflow and build verification are recorded above; neither fixture makes provider calls.
- Development and packaged OCR workers read `LOCAL OCR TEST 25 mg` from a synthetic image and retain text, blocks, hOCR and TSV. Language data is cached. This is not multilingual or scanned-book quality validation.
- The frozen-engine check initializes verified TLS, HTTPX, PDF resources and the script entry point without a model call. Packaging initially omitted required PyMuPDF data and a certificate distrust resource used by this machine's managed Python. The build now preserves both; TLS verification remains enabled.
- Documentation checks pass for local links, 356 preserved point/detail mappings and 503 bundled source files. Exact discussion-source bytes remain unchanged. Counts do not prove semantic completeness or runtime correctness.

### Live Nexus exercise

The packaged desktop converts the complete Breasts section on Nursing physical page 12 / printed page 68, including Figure 4-13 and its caption. The agent receives only the source PDF and scope. Example answers and development transcripts are not conversion input. This is a known reference scope, not an unseen benchmark or framework comparison.

The first version completed in 12 real Nexus requests. Resuming the same persistent job for a metadata correction reached 16 requests. Saving, reopening and explicit-version ZIP export succeeded. Correct candidate blocks were reused exactly despite validation failures. The correction preserved prose, caption and image bytes.

The failures exposed an incomplete model-facing page-update schema. The model guessed label fields/dispositions and eventually left `printed` as `unknown`. The schema now exposes `printed`, `disposition` and `note`, merges only supplied fields, and explains complete-claim classification. The continued agent used this contract to save printed label `68`.

Source review also found that diagram labels remained image-only. The product requires searchable substantive labels. The agent instruction now states that requirement. A further continuation added all 18 figure labels as searchable text from source evidence. The task completed with 19 total model requests and three saved versions. These review-directed corrections are part of this exercise; this is not evidence of unaided first-pass acceptance.

Evidence is local in `workspaces/default` and `.local/nexus-reference/`: native requests/replies/tools, scope, source/UI images, exported versions and reopen/byte receipts. Job: `b26da7e6e1db4cd3949438a2b40f59d5`. First version: `002ca12c117b490e8a955aaad3a56912`. Metadata-corrected version: `a14348fa5a1d41db80f26fe4e7f01f61`. Final version: `bfd67d56d2824dacaa2e1c163359256d`. Final package: `outputs/nursing-breasts.zip`. The complete section prose, caption, figure, 18 labels and printed metadata were checked against source page 12. Existing prose/caption and figure bytes remain unchanged; the new labels are a separate block. Source-render crop bytes and actual ZIP names/bytes match the final saved version. Reopen/export did not consume model requests.

The ledger reports 409,926 cumulative input tokens and 2,849 output tokens across 19 successful requests, including validation repair and the two review continuations. These are provider-reported usage, not per-request context size or a bill. All attempts have reported usage; actual Nexus fees and cache pricing remain unknown. The figure-label review and final source/byte verification receipts are under `.local/nexus-reference/`.

## Limits and remaining work

One live route/section does not certify other models, full books, multilingual OCR or universal fidelity. Responses has offline protocol coverage, not live validation. This live section did not require history compaction. Compaction transitions pass offline checks; summary quality remains model-dependent. The byte estimator is a heuristic, not a tokenizer or proven bound for every route. Native background retrieval, remote cancellation and provider compaction are not dependencies. Streaming is not implemented.

Single-writer recovery covers specific durable gaps, not arbitrary branching or every hard crash. An abruptly interrupted active interval is conservatively charged through restart. Unknown OCR/script outcomes stop with files retained. ZIP publication currently uses an exclusive local hard link; other destination filesystem behavior is unverified. External MCP/CLI product surfaces are not implemented.

The Windows folder app is verified locally. The NSIS installer is built at `release/PDF Markdown Workbench Setup 0.1.0.exe`; this task does not claim code-signing or clean-machine installation verification. macOS/Linux distributions remain unverified. No platform/provider matrix is queued. The earlier scoped Nexus exercise is complete. Development now follows the user's focused-increment instruction and the evidenced priorities above; this status note alone authorizes no additional provider test.

## Preserved knowledge

The requirements, owner documents, four technical guides and terminology navigator remain self-contained. The optional local source bundle retains 207 visible messages, the inherited handoff, the original 30 attachments, recovered ATT-31, substantive forum figures and supporting excerpts. [PRESERVATION_AUDIT](reference/PRESERVATION_AUDIT.md) records earlier source-first, language, attachment and subsystem reviews and their limits. Historical examples and old permissions remain inert data, not current defaults or rebuild acceptance.
