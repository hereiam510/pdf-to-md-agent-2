# Project organization decisions

## Responsibility-based repository layout (2026-10-31)

Recorded at 16:46, Asia/Singapore (UTC+08:00); this is the recording time for the current round. The human requested reorganizing the whole `pdf-to-md-agent-2` project with vibe-coding. This authorizes repository organization, reference repairs, local verification and a scoped Git checkpoint. It does not select new product behavior, dependency upgrades, live provider calls, task-data migration or remote publication. Earlier documentation-only permissions describe their original batches.

The entry is HEAD `15393228205bca350f51decc16eddc9842ac49b1` on `master` plus accumulated source, test and documentation changes. A 750-file, 14,860,948-byte entry copy, original Git diff/status and SHA-256 inventory are retained at `.local/project-organization-20261031_1646/`. Private inputs, task stores, installed dependencies and generated application builds are outside that copy and remain in place. The copy is local recovery evidence, not a new product baseline.

### Selected structure and reasons

Keep `src/pdfmd/`, `src/desktop/` and the renderer entry as the existing application boundaries. The engine has named modules for context, execution, transport, storage, documents and evidence; the architecture already permits this small structure. Splitting those modules or adding a service layer would change more than retrieval needs justify. Keep runtime imports, graph nodes, durable schemas and package entry points intact.

Group renderer components by feature: document session, task settings, receive progress, accepted-evidence recovery and diagnostics. Keep shared types, global styling and the application entry at the renderer root. Move files with their imports; do not rewrite state or IPC behavior. Group Python tests under `tests/engine/` by context, documents, execution, transport and diagnostics. Use canonical test-package imports and pytest's supported importlib mode rather than relying on a flat directory being inserted into `sys.path`. Keep common fixtures in the root conftest and source PDF fixtures under `tests/fixtures/pdf/`.

Separate desktop specs, fixture builders, harness/support scripts and compile-time type checks. Launch Python fixture builders as modules from the repository root. Group tools into development, build, documentation and runtime roles; update callers and root discovery together. Root manifests and lockfiles stay where their tools discover them. Preserve the topic-based documentation layout and original source bytes and historical prose. Only affected historical/review link targets are repaired; their exact prior locator spelling remains in the preceding Git edition and the entry snapshot. Old commands and evidence identities retain their original spelling. The layout guide and artifact-storage policy explain ownership; INDEX remains the only complete document catalogue.

This is preferable to an additional backend package hierarchy or framework replacement because it improves navigation without introducing new dependency boundaries. Keeping everything flat would leave fixture builders, runnable specs and support utilities mixed. New directories must contain an actual maintained responsibility; no empty future architecture is selected.

### Findings and product boundary

- **H05:** long functions remain a maintainability observation, not a proven defect. This round organizes files and explains module ownership; splitting functions is deferred until a responsibility or failure-handling change justifies it.
- **DOC-09–13:** the existing topic catalogue, separated owners and preserved historical basis remain effective. They are extended for the new layout/storage owners, not replaced or audited anew as a full preservation exercise.
- **R03:** interrupted local-process effects still have the documented recovery gap. Moving files cannot resolve it; revisit on selected interruption work or an actual delivery blocker.
- **R07 / SC02:** preserve the finite locally checked stream corrections and the separately open broader reply-shape validation concern. Reopen on new semantic/reopen counterexamples; organization is not a validation-policy repair.
- **R01 / CTX-01–03 and R02:** route calibration and whole-task/performance benefit retain their evidence limits. Revisit under a separately selected measurement or evidenced delivery need. No cost claim follows from this reorganization.

The [finding owner](../reviews/RUNTIME_FINDINGS.md#finding-index), [current state](../CURRENT_STATE.md) and [Stage B acceptance](../PHASE_PLAN.md#b-establish-complete-autonomous-conversion-on-actual-sources) retain product impact and selection boundaries. Full fourteen-page Nursing delivery and installed-product readiness remain unverified. Numerical uncertainty does not dismiss supported risks, and this batch does not make every finding a prerequisite.

### Acceptance and work sequence

1. Preserve the entry state and record a relocation map before moving maintained files. Keep inherited edits distinguishable from the organization delta.
2. Move feature/test/tool files, repair imports, root calculations, launchers, fixture paths and build resource references, and preserve test cases and assets.
3. Establish the layout/storage owners and reconcile active guidance, navigation and current-state summaries. Historical event commands and originals keep their original spelling and status.
4. Compare test discovery before/after; run engine regressions, TypeScript/desktop build, desktop fixtures and documentation/source checks. Inspect preservation against the entry, including inherited edits and exact source/PDF assets. Check development and packaging path selection without overwriting an existing Windows distribution.
5. Save the scoped organization checkpoint while retaining unrelated implementation changes. Record actual outcomes, failures, source identity and limits in [this round's verification](../verification/20261031_1646_PROJECT_ORGANIZATION.md).

Completion means a repository-only reader can find the responsible code, tests, tools and records, and affected operations resolve their relocated inputs. Passing these checks does not establish live Nexus compatibility, source fidelity for Nursing or a newly installed build.

### Verification-driven fixture corrections

The desktop continuation check exposed both a missed scheduling-hook directory reference and an inherited protocol mismatch: its local server serves complete JSON, while the current new-connection default requests SSE streaming. Read-only inspection of both failed synthetic task stores showed the first request ending `unknown_outcome`, without a document head or tool operation; the Stop boundary had not been reached. Select complete-response waiting explicitly in the continuation and ordinary workbench JSON fixtures, as the existing task-settings JSON scenario already does. Preserve the streaming default and dedicated SSE cases. This corrects fixture conditions against the adopted waiting contract; it does not relax native acceptance or reinterpret the failed raw reply.

The first focused desktop rerun overlapped the full suite. A PDF case then reported a closed initial window. Shared default Electron-profile concurrency is a candidate cause, not yet a proven application defect; rerun affected cases serially before disposition. Keep both failed runs and their original stores/traces. Do not add a runtime retry, change product timeouts or rewrite old attempts to make a fixture pass.

The streamed export check subsequently demonstrated a location-dependent Windows image-preview failure: an identical copied package fails Edge image decoding at a 264-character URL pathname and succeeds at 192 characters. [R14](../reviews/RUNTIME_FINDINGS.md#r14--deep-windows-file-url-assets-can-fail-to-display) records the product impact and broader Stage D revisit condition. Shorten the new default run identifier and the streaming case subdirectory to avoid nesting introduced by this round. Preserve all asset bytes, decode assertions and the original failed control. This is a test-storage correction, not a promise of arbitrary-length output support.

The retained compaction desktop scenario also reads the removed `job.events` field and fails before its recovery assertion. Use the existing `activity`/`closeDiagnostics` API, as the streaming scenario already does. An unavailable or malformed activity view remains a polling failure (`-1`), not zero stopped events; close successful captures after reading. Preserve the same expected additional stopped event, request/budget invariants and recovery/export assertions. Its default case directory is also shortened to `compaction/`. These are test-consumer/storage corrections against the current API, not a new product event projection or recovery policy.

The corrected continuation then reaches export but its page-wide `role=status` assertion matches both receive progress and the successful export toast. Scope export/edit notification assertions in continuation and ordinary workbench to the existing `.toast.success` element. Retain the exact expected messages and product accessibility roles. Do not remove progress facts or weaken successful-export verification to satisfy an ambiguous locator.

### Official guidance checked before changes

The installed pins remain pytest 9.1.1, electron-vite 6.0.0 and Playwright 1.64.1. [pytest integration guidance](https://docs.pytest.org/en/stable/explanation/goodpractices.html) recommends a source layout and importlib mode and explains canonical test-package names. [electron-vite's project structure guidance](https://electron-vite.org/guide/dev) permits configured entry locations; the current explicit main/preload/renderer inputs remain selected. Its public guide currently labels itself v5, so installed v6 configuration/types and the actual build are the version-specific check. [Playwright configuration](https://playwright.dev/docs/api/class-testconfig#test-config-test-dir) supports an explicit spec directory and separate result destination. No framework upgrade or new lifecycle is introduced.
