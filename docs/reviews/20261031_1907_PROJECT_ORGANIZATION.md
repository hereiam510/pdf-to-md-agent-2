# Project organization review and correction

Recorded 2026-10-31 at 19:07, Asia/Singapore (UTC+08:00); the timestamp identifies this review's evidence batch. Reviewed `eae596a` and its inherited worktree against the [organization decision](../decisions/PROJECT_ORGANIZATION.md), [layout](../guides/PROJECT_LAYOUT.md), [storage policy](../ARTIFACT_STORAGE.md) and [original verification](../verification/20261031_1646_PROJECT_ORGANIZATION.md). The human initially requested checking the linked organization chat, then explicitly authorized direct project changes. This round covers organization corrections and local verification, not a new conversion, release or product design.

## Finding and selected correction

**ORG-01 (low priority): two shared fixtures bypass canonical package imports.** `tests/engine/transport/test_streaming_delivery.py` loads the compaction fixture as `stream_delivery_legacy_fixture`; `tests/desktop/fixtures/diagnostic_failed_results.py` loads the diagnostics fixture as `existing_fixture`. Both use `spec_from_file_location` and `exec_module`. A pre-change in-process comparison with normal package imports returns different module objects in both cases. The loaders retain filename coupling and duplicate module identity despite the adopted canonical-import rule. This is a test-maintenance defect, not evidence of incorrect conversion or a failed delivery.

Replace the two loaders with `tests.desktop.fixtures` imports, retaining the local aliases and all fixture behavior. No new package hierarchy or dependency is needed. [Official pytest guidance](https://docs.pytest.org/en/stable/explanation/goodpractices.html#choosing-an-import-mode), checked during this review, supports the existing importlib mode and explains why canonical module identities avoid double imports. Installed pytest remains 9.1.1. Acceptance: both consumers share the canonical module object; discovery is unchanged; existing streamed recovery/save/reopen/export and failed-descriptor desktop checks pass.

## Review evidence and limits

Before correction, all 163 members of the organization implementation manifest match their recorded hashes. Applying the 100-file relocation map leaves no missing entry member. All engine files, source-collection members and PDF fixtures remain byte-identical to the organization entry. This checks preservation of that round, not semantic completeness of every historical source discussion.

The repository documentation checker passes (503 source hashes and 356 point/detail mappings); Python discovers 1,290 cases; TypeScript checking exits 0. Code inspection follows moved renderer imports, Python package/fixture consumers, tool root calculations, launchers and OCR packaging paths. Current guidance contains no remaining exact old path from the relocation map outside explicitly historical/evidence records. Topic routes from INDEX retain separate layout/storage ownership, current contracts and historical evidence. The linked chat and retained run records distinguish the earlier composite regressions from a single clean whole-suite run.

Local reproduction, before-edit copies and execution logs belong to `.local/org-review-20261031_1907/`. The original source manifests and earlier failed/successful runs remain unchanged. Correction results are recorded below; pre-change checks alone do not establish post-change acceptance.

## Existing findings and product boundary

DOC-09–13's topic ownership and preserved basis remain in place. H05 does not justify an unrelated function rewrite. R03's unknown local effects, broader R07 reply-shape validation, R01/CTX route calibration and residual R02 cost/performance work retain their recorded impact and revisit conditions. R14's observed long Windows preview-path limitation remains real; this review does not generalize shorter synthetic paths to arbitrary user destinations. Revisit these under selected work or evidence that they directly prevent delivery; numerical uncertainty does not dismiss the concerns. Stage B's complete fourteen-page Nursing result and installed-product readiness remain unverified.

## Correction checks and closeout

ORG-01 is corrected and locally verified. No further organization defect was established within the reviewed paths and preservation boundary.

| Check | Actual result and scope |
| --- | --- |
| Canonical identity | Both consuming modules now hold the same module objects as normal `tests.desktop.fixtures` imports. No remaining `spec_from_file_location` / `exec_module` fixture loader or `sys.path` insertion exists under `tests/`. |
| Engine delivery | `.venv/Scripts/python.exe -B -m pytest tests/engine/transport/test_streaming_delivery.py -p no:cacheprovider --basetemp=.local/org-review-20261031_1907/python-temp --junitxml=.local/org-review-20261031_1907/python.xml`: two passes in 35.32 seconds. Both protocols preserve unknown-request facts, source/image pixels, saved/reopened versions and every exported ZIP member. Their retained `verification.json` files confirm zero live model calls. |
| Desktop diagnostics | `pnpm exec playwright test diagnostic-failed-results.spec.ts`, with `PDFMD_TEST_RUN_ROOT` set to this round's `desktop/`: one pass in 2.3 minutes. The existing generated desktop build was reused; no UI code changed. Fresh/reopened checks retain unavailable-descriptor reasons, exact source/export members and unchanged task-file/fact maps. |
| Discovery | After correction, 1,290 Python identities exactly match the previous round's node list; zero added/missing. Playwright lists 58 tests in 20 files. These are discovery results, not 1,348 fresh test passes. |
| Documentation navigation | The existing CommonMark/HTML audit was inspected and copied into this round before execution. The final check reaches all 77 documents from README and INDEX, with 3,286 parsed local links and zero path, fragment, duplicate-ID, filename-case or catalogue errors. The normal documentation/source checker also passes. No heading or renderer behavior changed; no new browser navigation certification is claimed. |
| Preservation and prior evidence | Zero missing relocated entry members; 26 engine files, 534 source-collection members and seven PDFs remain exact. The original Python XML's eight failed identities equal the eight passing focused rerun identities. Desktop logs retain the six initial failures and the later five-/two-case results. This supports the original composite description, not a new full-suite execution. |

The checked implementation is the [original 163-file manifest](../verification/20261031_1646_PROJECT_SOURCE.json) with exactly these two replacements (SHA-256 of current file bytes):

| File | SHA-256 |
| --- | --- |
| `tests/engine/transport/test_streaming_delivery.py` | `0bbe00add28a9cf22463858fad2957dd27f5b6cdfbe1937afc49e531afe83e14` |
| `tests/desktop/fixtures/diagnostic_failed_results.py` | `ecdbb1f48d3f986e6879d0407131fe6780082ec5ad995ce158a14932453395cf` |

The local round retains `correction.patch`, before-edit copies, source hashes, discovery output, Python XML/log, desktop trace/results and synthetic saved/exported products. It also retains the copied audit and rendered reading artifacts. These local products are not part of Git or automatically available to a remote reader. Early console inspection encountered a default-codepage decode error; subsequent comparisons explicitly used UTF-8. This was an inspection-script failure, not a failing product check.

The scoped local checkpoint covers the tracked streaming-test correction and review/navigation/layout/current-state records on `codex/project-organization`. The existing 37 modified/untracked source/test members remain outside that checkpoint. The diagnostic fixture is one of those untracked members: its import correction remains in the working tree with its inherited content and is separately recoverable from the local before-copy and patch. Thus the checkpoint alone is not the complete corrected or tested implementation. No application source, dependency, private task store, original repository, release or remote publication changes are included. The next product decision remains the separately authorized bounded fourteen-page interval; this review does not select it.
