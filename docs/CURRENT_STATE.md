# Current state

Updated 2026-10-23, Asia/Hong_Kong. Current human instructions authorize building this app, copying the old references/private configuration, and testing through Nexus. The old repository remains unchanged.

## Implemented application

The first increment implements an Electron/TypeScript/React workbench, one Python LangGraph controller, native Nexus requests, PDF/OCR/preview/script tools, transient context assembly, immutable documents and explicit-version ZIP export. [ARCHITECTURE](ARCHITECTURE.md#implementation-map-and-selected-dependencies) maps modules and pins. [CONTRACTS](CONTRACTS.md#implemented-first-version-contracts) specifies executable Q1–Q3 choices. [OPEN_QUESTIONS](OPEN_QUESTIONS.md) records design closure without claiming universal runtime or content acceptance.

The desktop imports an unchanged PDF and scope, shows source pixels and saved Markdown/HTML/evidence, runs or stops the agent, accepts later instructions, edits saved blocks locally, selects versions and exports partial or complete work. Reopening loads persisted state without starting inference. Nexus uses native non-streaming Chat Completions or Responses. Credentials stay outside task journals and can be remembered with Windows encryption. Trusted scripts are off by default and run with host-user permissions when enabled.

`Start Workbench.cmd` opens the local Windows folder app with `workspaces/default`. The PowerShell launcher provides the same default and an override. `tools/setup.ps1` installs locked dependencies; `tools/build-windows.ps1` bundles the engine and desktop. Direct executable/`pnpm dev` launch uses Electron's user-data directory unless `PDFMD_DATA` is set. [README](../README.md) gives commands.

No application changes have been pushed or published as a GitHub release during this task. Runtime data, copied references, private configuration, builds and review outputs are Git-ignored. The user's pre-existing `docs_bundle.txt` remains untouched and outside the implementation change.

## Copied inputs

The requested subagent copied 47 reference files (242,220,051 bytes, including the manifest) and two private files. There were no destination collisions. Every copy matched its source bytes, all 46 manifest entries matched, and all five PDFs contained real PDF bytes, including the large LFS-backed JRE source. Credentials were never displayed. Both directories are ignored. Receipt: `.local/reference-copy-report.json`.

`private/provider.json` selects the user's loopback Nexus Chat Completions route and `cliproxy/gpt-6.1-sol`. `private/api-key.txt` supplies the credential programmatically. The live exercise retained the configuration's 40-request/1,200-active-second limits and 180-second request timeout, with no replay. Its 131,072 context, 8,192 output and 4,096 per-image allowances are explicit local assumptions, not discovered provider specifications.

## Verification and observed corrections

### Offline and desktop checks

- Sixteen Python tests pass: exact candidate reuse, supplied-field metadata patches, insertion/stale-head checks, exact text patches, whole-document references/footnotes, source assets/ZIP bytes, persistent budgets, accepted-batch cancellation, native Responses reasoning/call pairing, rejected/truncated calls, accepted-reply/result-pointer gaps, commit-before-checkpoint resume, compaction boundaries, local authentication, HTML sanitation and opt-in script output retention.
- TypeScript checking and the production desktop build pass. A real Electron window and Python engine pass the desktop fixture workflow: source import, native image input, saved-output screenshot, local edit, version export and reopen without more inference. The Windows folder build passes this workflow too. It uses five local fixture responses and no provider calls.
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

The Windows folder app is verified locally. The unsigned NSIS installer is built at `release/PDF Markdown Workbench Setup 0.1.0.exe`. Clean-machine installation, signing and macOS/Linux distributions are unverified. No platform/provider matrix is queued. The requested build and scoped Nexus delivery exercise are complete; further development should follow an actual delivery need or observed blocker. Do not reopen the design or launch more provider tests merely from this status note.

## Preserved knowledge

The requirements, owner documents, four technical guides and terminology navigator remain self-contained. The optional local source bundle retains 207 visible messages, the inherited handoff, the original 30 attachments, recovered ATT-31, substantive forum figures and supporting excerpts. [PRESERVATION_AUDIT](reference/PRESERVATION_AUDIT.md) records earlier source-first, language, attachment and subsystem reviews and their limits. Historical examples and old permissions remain inert data, not current defaults or rebuild acceptance.
