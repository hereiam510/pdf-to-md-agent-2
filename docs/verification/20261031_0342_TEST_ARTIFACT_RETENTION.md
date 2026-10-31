# Development test-artifact retention cleanup

## Decision and authority

The user explicitly approved deletion of the previously enumerated approximately 3.80 GiB of development test products. This is a one-time cleanup, not a general retention policy or authorization for additional deletion. Ordinary successful synthetic test workspaces were removed while aggregate reports, source identity, important failed reproductions, representative final deliveries and uncommitted modifications were preserved. No backward-compatibility requirement justified retaining every historical workspace.

Nursing tasks, their snapshots/packages, conversation exports, user-provided source PDFs/reference inputs, application code, tests, configuration, model calls, Git commits and remote publication were outside this operation. Synthetic PDFs inside the approved temporary test cases were removable test products. The 139.67 MiB duplicate/cache cleanup was not part of this first operation; it was separately authorized and completed in the [follow-up below](#duplicate-and-cache-follow-up).

## Verified result

- Completed and verified on 2026-10-31 (UTC+08:00); exact operation times are in the local journal.
- Deleted 4,410 explicitly selected directories, including 86,503 files: **4,078,645,443 logical bytes (3.7985 GiB)**.
- C: available space immediately before/after deletion: 13,121,544,192 -> 17,382,998,016 bytes. Observed increase: **4,261,453,824 bytes (3.9688 GiB)**. This is a whole-volume observation during deletion, not an attribution of every concurrent system write.
- No selected directory/file remained. Every pre-existing non-target `.local` file retained its path, byte size and nanosecond modification time.
- All 155,057 retained files in the affected batches also retained their SHA-256 hashes, including source snapshots, reports, original manifests, failed-run evidence and the explicit retained cases.
- All 752 existing tracked/untracked nonignored repository files retained their SHA-256 hashes; Git status was unchanged before these record updates. No source/test changes were made by this cleanup.
- Nursing and conversation preservation was checked by the complete non-target file metadata inventory. This is not a fresh conversion, recovery, application acceptance run or full content-hash audit of those untouched trees.

## What historical evidence now means

Original manifests, logs, JUnit records and source identities are preserved verbatim. They describe the original runs. Their full retained-file inventories are no longer claims that every historical file is still present: the specific disposable products below have been intentionally removed. Do not rewrite an original manifest to manufacture a full-tree match. Use this record and the deletion receipt to explain expected absence. Removed per-case databases and temporary outputs cannot be opened again; rerunning a test creates a new observation, not the deleted historical state.

Representative final delivery/restore/export cases listed below remain complete. The later follow-up removes only the specified redundant source copies and regenerable profile/interpreter caches; retained source content and actual delivery evidence remain. Other retained final workflow directories include `phase2-settings/final-tests`, `context-review/acceptance-tests`, `context-progress/acceptance-tests`, `handoff-replay/acceptance-tests`, `context-retry/delivery-final`, `context-capacity-wait/delivery-tmp`, the R01 `delivery-runtime-final` and the accepted-evidence-recovery `desktop-delivery` workflows. Important failed/interrupted batches, R02 benchmarks/hardkill/controls, all source snapshots and unrelated verification batches remain.

## Exact scope

Paths in the tables are relative to `.local/`. In whole-directory rows, the named directory was removed. In selected-children rows, only its immediate `test_*` directories outside the literal retained list were removed; parent files and all other entries were kept. The JSON plan freezes every expanded target, rather than leaving a wildcard for future deletion.

| Root | Operation | Removed directories | Removed logical MiB | Retained direct case directories |
| --- | --- | ---: | ---: | --- |
| `phase2-settings/acceptance-tests/` | Whole directory | 1 | 200.22 | Not applicable; later final workflow retained separately. |
| `phase2-settings/focused-tests/` | Whole directory | 1 | 76.81 | Not applicable; later final workflow retained separately. |
| `phase2-settings/settings-tests-fixed/` | Whole directory | 1 | 36.05 | Not applicable; later final workflow retained separately. |
| `context-review/full-tests/` | Whole directory | 1 | 49.36 | Not applicable; later final workflow retained separately. |
| `context-review/final-tests/` | Whole directory | 1 | 50.90 | Not applicable; later final workflow retained separately. |
| `context-progress/first-tests/` | Whole directory | 1 | 45.26 | Not applicable; later final workflow retained separately. |
| `handoff-replay/focused-tests/` | Whole directory | 1 | 114.44 | Not applicable; later final workflow retained separately. |
| `context-retry/expanded-tests/` | Whole directory | 1 | 4.57 | Not applicable; later final workflow retained separately. |
| `context-retry/retry-tests/` | Whole directory | 1 | 3.92 | Not applicable; later final workflow retained separately. |
| `context-capacity-wait/focused-tmp/` | Whole directory | 1 | 9.39 | Not applicable; later final workflow retained separately. |
| `phase3-closeout/focused-tests/` | Whole directory | 1 | 16.45 | Not applicable; later final workflow retained separately. |
| `phase3-pdf/first-tests/` | Whole directory | 1 | 2.19 | Not applicable; later final workflow retained separately. |
| `phase3-pdf/focused-tests/` | Whole directory | 1 | 2.49 | Not applicable; later final workflow retained separately. |
| `context-retry/all-tests/` | Selected test children only | 200 | 256.18 | `test_deferred_update_survives_0`, `test_deferred_update_survives_1`, `test_rejected_stream_pin_can_b0`, `test_rejected_stream_pin_can_b1` |
| `context-capacity-wait/full-tmp/` | Selected test children only | 240 | 243.21 | `test_capacity_repair_reopens_a0`, `test_capacity_repair_reopens_a1`, `test_capacity_repair_reopens_a2`, `test_capacity_repair_reopens_a3`, `test_large_source_to_saved_reo0`, `test_large_source_to_saved_reo1` |
| `context-coordination/final-tmp/` | Selected test children only | 290 | 283.26 | `test_deferred_update_survives_0`, `test_deferred_update_survives_1`, `test_needs_revision_explicit_r0`, `test_needs_revision_explicit_r1` |
| `r01-estimator-2026-10-28/pytest-tail/` | Selected test children only | 229 | 173.17 | `test_precise_read_old_full_pre0`, `test_precise_read_old_full_pre1`, `test_streamed_handoff_then_edi0`, `test_streamed_handoff_then_edi1` |
| `r01-estimator-2026-10-28/pytest-settings-final/` | Selected test children only | 22 | 1.52 | `test_settings_continue_to_save0`, `test_settings_continue_to_save1`, `test_settings_continue_to_save2`, `test_settings_continue_to_save3`, `test_settings_continue_to_save4`, `test_settings_continue_to_save5` |
| `r02-storage-2026-10-28-run1/full-temp/` | Selected test children only | 468 | 311.58 | `test_streamed_handoff_then_edi0`, `test_streamed_handoff_then_edi1` |
| `r13-acceptance-2026-10-28-run1/full-final2/temp/` | Selected test children only | 509 | 313.57 | `test_runtime_repairs_old_point0`, `test_runtime_repairs_old_point1`, `test_streamed_handoff_then_edi0`, `test_streamed_handoff_then_edi1` |
| `r13-terminal-2026-10-28-run1/full-store/` | Selected test children only | 633 | 318.14 | `test_runtime_repairs_old_point0`, `test_runtime_repairs_old_point1`, `test_streamed_handoff_then_edi0`, `test_streamed_handoff_then_edi1`, `test_suffix_rule_covers_real_c0`, `test_suffix_rule_covers_real_c1`, `test_task_deadline_change_then0`, `test_task_deadline_change_then1` |
| `accepted-evidence-recovery-2026-10-29-run1/full-delivery-tmp/` | Selected test children only | 716 | 329.56 | `test_document_commit_report_re0`, `test_document_commit_report_re1`, `test_runtime_repairs_old_point0`, `test_runtime_repairs_old_point1`, `test_streamed_handoff_then_edi0`, `test_streamed_handoff_then_edi1` |
| `request-deadline-evidence/full-tmp/` | Selected test children only | 369 | 246.57 | `test_settings_continue_to_save0`, `test_settings_continue_to_save1`, `test_settings_continue_to_save2`, `test_settings_continue_to_save3`, `test_settings_continue_to_save4`, `test_settings_continue_to_save5`, `test_task_deadline_change_then0`, `test_task_deadline_change_then1` |
| `stream-progress-evidence/full-tmp/` | Selected test children only | 418 | 307.38 | `test_streamed_handoff_then_edi0`, `test_streamed_handoff_then_edi1` |
| `phase3-closeout/all-tests/` | Selected test children only | 167 | 251.75 | `test_rejected_stream_pin_can_b0`, `test_rejected_stream_pin_can_b1`, `test_image_originals_display_a0`, `test_image_originals_display_a1`, `test_image_originals_display_a2`, `test_image_originals_display_a3`, `test_image_originals_display_a4`, `test_image_originals_display_a5`, `test_image_originals_display_a6` |
| `phase3-pdf/all-tests/` | Selected test children only | 136 | 241.76 | `test_image_originals_display_a0`, `test_image_originals_display_a1`, `test_image_originals_display_a2`, `test_image_originals_display_a3`, `test_image_originals_display_a4`, `test_image_originals_display_a5`, `test_image_originals_display_a6`, `test_extracted_boxes_crop_actu0`, `test_extracted_boxes_crop_actu1`, `test_extracted_boxes_crop_actu2`, `test_extracted_boxes_crop_actu3`, `test_extracted_boxes_crop_actu4`, `test_extracted_boxes_crop_actu5`, `test_extracted_boxes_crop_actu6`, `test_extracted_boxes_crop_actu7` |

## Local receipts and reproducibility limits

These ignored receipts contain local paths and are not automatically included in an external review package:

- `.local/test-artifact-cleanup-20261031_0342-plan.json`: exact absolute targets, original per-target file counts/bytes, group definitions and all retained exceptions.
- `.local/test-artifact-cleanup-20261031_0342-before.json`: complete pre-cleanup local file metadata, exact removed-file inventory, retained-file hashes, repository hashes, HEAD and entry Git status.
- `.local/test-artifact-cleanup-20261031_0342-deleted.jsonl`: flushed per-directory deletion events, original plan SHA-256 and measured free space.
- `.local/test-artifact-cleanup-20261031_0342-result.json`: completed removal and preservation checks; no mismatches.
- `.local/cleanup-test-artifacts-20261031_0342.py`, `.local/delete-test-artifacts-20261031_0342.ps1` and `.local/verify-test-cleanup-20261031_0342.py`: operation/verification sources. They are historical helpers, not instructions to rerun deletion.
- Each of the 16 affected batch roots now contains `EVIDENCE_RETENTION.md`, pointing to this record. Existing README/manifests were not rewritten.

Before deletion, absolute targets and every ancestor/descendant were checked against the named workspace; reparse points and active project processes would have stopped the operation. The exact reviewed 4,078,645,443-byte total and 4,410-target count were checked again. Deletion used native PowerShell `Remove-Item -LiteralPath`; no shell-built path expression or recursive delete outside `.local` was used.

No product tests or model calls were run. Repository-only documentation checks passed for 70 Markdown files and 3,913 local links/destinations, including the source-integrity and coverage checks at their existing scope. `git diff --check` passed. These checks do not establish semantic completeness or product readiness. CURRENT_STATE and INDEX link this record; the 16 local retention notices also resolve to it.

## Duplicate and cache follow-up

The user separately authorized the exact previously confirmed 139.67 MiB duplicate/cache list. This does not authorize other `.local` cleanup, task changes or new model calls. Source/reference inputs, Nursing, conversation exports, reports, important failed-run evidence and unique modifications remain protected.

- Completed on 2026-10-31 (UTC+08:00): **88 exact targets** (80 directories and eight individual JSON files), containing **2,900 files**, totaling **146,455,877 bytes (139.67 MiB)**.
- C: available bytes immediately before/after deletion: 17,389,060,096 -> 17,540,325,376; observed increase **151,265,280 bytes (144.26 MiB)**. As above, this is a whole-volume observation during deletion.
- Before deletion, all four duplicate directory pairs and eight duplicate JSON pairs were checked for matching file sets and SHA-256 contents. After deletion, **22,417 retained files** in the directly affected sibling trees and **753 existing repository files** matched their pre-cleanup SHA-256 hashes.
- All other pre-existing `.local` files retained their path, byte size and modification time. This includes Nursing, conversation exports and the preceding cleanup receipts. No target remains. Git status was unchanged before the follow-up record updates.
- Original historical manifests were not rewritten. Their expected missing-file lists now include this follow-up; duplicate content remains at the retained paths below. Original scripts referring to removed paths may require an explicit path substitution for a future reproduction. Do not claim the original full inventory still exists.

### Duplicate-to-retained mapping

Paths are relative to `.local/`. Each removal has a byte-identical retained counterpart.

| Removed path | Retained counterpart | Removed MiB |
| --- | --- | ---: |
| `context-coordination/package-checks-final/reconstructed-a484b9b` | `context-coordination/package-checks-final/reconstructed-c1e6fcc` | 9.57 |
| `context-retry/package-verification/patch-check-4ke3ffi8` | `context-retry/package-verification/patch-check-ipeyip0g` | 9.05 |
| `context-lifecycle/package-verification/patch-check-81tlssw6` | `context-lifecycle/package-verification/patch-check-qb4yw14n` | 9.10 |
| `context-capacity-wait/package-verification/patch-check-nvyk5o9z` | `context-capacity-wait/package-verification/patch-check-pc6jjpce` | 9.15 |
| `r01-estimator-2026-10-28/comparison/post-canonical-current-future_streaming-42-54.json` | `r01-estimator-2026-10-28/comparison/final-chunked-current-future_streaming-42-54.json` | 7.41 |
| `r01-estimator-2026-10-28/comparison/post-canonical-current-future_streaming-44-57.json` | `r01-estimator-2026-10-28/comparison/final-chunked-current-future_streaming-44-57.json` | 10.00 |
| `r01-estimator-2026-10-28/comparison/post-canonical-current-legacy_nonstreaming-42-54.json` | `r01-estimator-2026-10-28/comparison/final-chunked-current-legacy_nonstreaming-42-54.json` | 7.41 |
| `r01-estimator-2026-10-28/comparison/post-canonical-current-legacy_nonstreaming-44-57.json` | `r01-estimator-2026-10-28/comparison/final-chunked-current-legacy_nonstreaming-44-57.json` | 10.00 |
| `r01-estimator-2026-10-28/comparison/post-canonical-v2-current-future_streaming-42-54.json` | `r01-estimator-2026-10-28/comparison/final-chunked-current-future_streaming-42-54.json` | 7.41 |
| `r01-estimator-2026-10-28/comparison/post-canonical-v2-current-future_streaming-44-57.json` | `r01-estimator-2026-10-28/comparison/final-chunked-current-future_streaming-44-57.json` | 10.00 |
| `r01-estimator-2026-10-28/comparison/post-canonical-v2-current-legacy_nonstreaming-42-54.json` | `r01-estimator-2026-10-28/comparison/final-chunked-current-legacy_nonstreaming-42-54.json` | 7.41 |
| `r01-estimator-2026-10-28/comparison/post-canonical-v2-current-legacy_nonstreaming-44-57.json` | `r01-estimator-2026-10-28/comparison/final-chunked-current-legacy_nonstreaming-44-57.json` | 10.00 |

### Cache scope

Only the following six child directories were removed from each listed Electron profile: `Code Cache`, `DawnGraphiteCache`, `DawnWebGPUCache`, `GPUCache`, `GrShaderCache`, `ShaderCache`. Profile state outside those directories, screenshots, task databases and delivered content remain. Paths below are relative to `.local/accepted-evidence-recovery-2026-10-29-run1/`.

```text
desktop-delivered-cc2/chat_completions-P6DBUB/electron-profile
desktop-delivered-resp2/responses-RYnPEU/electron-profile
desktop-delivered/responses-HPZEXh/electron-profile
desktop-delivery/chat_completions-4bBm59/electron-profile
desktop-delivery/responses-4g1e2X/electron-profile
desktop-final2/chat_completions-AUq6A6/electron-profile
desktop-final2/responses-sK2ILR/electron-profile
desktop-stable/chat_completions-DNMsvn/electron-profile
desktop-stable/responses-W8xbfg/electron-profile
desktop-validation/chat_completions-dkYriJ/electron-profile
desktop-validation/responses-rWJ7mg/electron-profile
ui-preparation-negative/chat_completions-J57WZr/electron-profile
```

The following Python bytecode-only directories were also removed; their source files remain. Paths are relative to `.local/`.

```text
accepted-evidence-recovery-2026-10-29-run1/tested-source/src/pdfmd/__pycache__
accepted-evidence-recovery-2026-10-29-run1/tested-source-closure/src/pdfmd/__pycache__
accepted-evidence-recovery-2026-10-29-run1/tested-source-final/src/pdfmd/__pycache__
r01-fallback-r02-2026-10-28-run1/r02/__pycache__
```

### Follow-up receipts and checks

- `.local/duplicate-cleanup-20261031_0411-plan.json`: all 88 exact paths, byte/file counts and duplicate-to-retained mapping.
- `.local/duplicate-cleanup-20261031_0411-before.json.gz`: compressed pre-cleanup metadata inventory, removed-file list and protected content hashes.
- `.local/duplicate-cleanup-20261031_0411-deleted.jsonl`: flushed deletion journal and measured volume free space.
- `.local/duplicate-cleanup-20261031_0411-result.json`: successful removal/preservation verification, with no mismatches.
- `.local/duplicate-cleanup-20261031_0411-verifier-correction.txt`: the first read-only verifier stopped at journal parsing because `utf8-sig` is not a valid encoding name. The original helper was preserved; the `-verified.py` copy changes only that spelling to `utf-8-sig`. Verification was rerun successfully. Deletion was not rerun.
- Seven affected batch roots now identify this follow-up in `EVIDENCE_RETENTION.md`; two are new notices and five extend the first cleanup notices.
- Follow-up documentation checks passed for 70 Markdown files and 3,914 local links/destinations, with no errors; `git diff --check` passed. `.local/duplicate-cleanup-20261031_0411-closeout.json` records the final source/notice checks after record updates.
- This follow-up did not delete the separately discussed session-ui caches, OCR cache or old deliverables package. No tests, application execution, commits, model calls or Nursing continuation were performed.

## Failure batches and Nursing archive disposal

The user approved the previously enumerated A+B reduction, totaling 1,271,381,513 bytes, and explicitly requested deletion of the four named Nursing all-products ZIPs. Agreement that the implemented R01 batch is finished does not authorize blanket removal of R01: only the exact reviewed test-case paths below were selected. Remaining route-calibration questions do not require retaining every historical workspace.

### Diagnostic selection and correction

Mixed-result batches retain their concrete failed cases and relevant parameter controls. Removed cases do not add a separately identified diagnosis beyond the retained reports, source identities and final workflows. Six interrupted recovery runs retain one listed representative snapshot each, all interruption reasons, source snapshots and the separate ownership/process/poll/projection negative reproductions. Those snapshots are not asserted to reproduce the exact instant of interruption, and partial runs are not classified as complete passes.

Correction to the preceding discussion: `context-coordination/full-tmp` was not established to belong to the 94-failure initial run. Its creation time and case names align more closely with a later 295-pass run, but a direct execution mapping was not established. It was excluded and remains intact. R01 partial runs whose progress logs lack sufficient failure-to-workspace mapping also remain.

The four ZIPs are historical archive packages, not the active Nursing task store. Their deletion was explicitly chosen by the user; it is not a finding that every archive member has a verified independent copy. The receipt retains archive SHA-256, member names/sizes/CRC values and available top-level README/MANIFEST/source-export notes. Those metadata and reports cannot reconstruct the deleted archive payloads. Nursing task directories, other snapshots, conversation exports and user-provided reference/source inputs were not deletion targets.

### Verified result

- Removed **1,743 selected test directories** and **four ZIP files**, containing 32,744 files. Test products: 1,271,381,513 bytes (1.1841 GiB); archives: 1,489,888,983 bytes (1.3876 GiB); total: **2,761,270,496 bytes (2.5716 GiB)**.
- C: available space before/after deletion: 12,672,352,256 -> 14,372,339,712 bytes; observed increase **1,699,987,456 bytes (1.5832 GiB)**. Logical file bytes and whole-volume free-space change are different measurements; this run did not establish the cause of their difference.
- All 1,747 targets are absent. All pre-existing non-target `.local` files retained their path, size and modification time. **3,468 selected retained evidence/source/report files** and **753 existing repository files** retained their SHA-256 hashes. No mismatch was found; Git status was unchanged before record updates.
- All 27 explicitly retained failure/control cases and representative interrupted-run snapshots remain. Original historical manifests and reports were not rewritten; the removed-file inventories are retained separately. No code/test/configuration edits, application/model execution, commits or publication were performed.

### Exact test-workspace scope

Paths are relative to `.local/`. Only immediate `test_*` case directories outside the literal keep list were removed. Parent files and all other entries remain.

| Root | Removed directories | Removed MiB | Retained case directories |
| --- | ---: | ---: | --- |
| `context-lifecycle/python-tmp/` | 224 | 263.68 | `test_rejected_pin_preserves_po0`, `test_rejected_pin_preserves_po1` |
| `context-lifecycle/focused-tmp/` | 48 | 90.47 | `test_unknown_frozen_compaction0`, `test_unknown_frozen_compaction1` |
| `context-retry/focused-tests/` | 59 | 140.75 | `test_retry_rejects_when_policy0`, `test_retry_rejects_when_policy1` |
| `context-progress/integration-tests-fixed/` | 10 | 37.33 | `test_partial_reduction_can_rep0`, `test_partial_reduction_can_rep1` |
| `r01-estimator-2026-10-28/pytest-final3/` | 194 | 133.65 | `test_continue_after_failed_com0` |
| `r01-estimator-2026-10-28/remaining-regressions/initial-workspaces/` | 14 | 85.21 | `test_receipt_distinguishes_app0`, `test_receipt_distinguishes_app1`, `test_receipt_distinguishes_app2`, `test_receipt_distinguishes_app3`, `test_retained_results_cannot_d0`, `test_retained_results_cannot_d1`, `test_retained_target_uses_spec0`, `test_retained_target_uses_spec1`, `test_unfit_suffix_keeps_rollin0`, `test_unfit_suffix_keeps_rollin1` |
| `r01-estimator-2026-10-28/capacity-tests/fifth/` | 68 | 30.29 | `test_explicit_release_can_redu0` |
| `r01-estimator-2026-10-28/capacity-tests/sixth/` | 40 | 48.37 | `test_reference_only_prefix_inc0` |
| `accepted-evidence-recovery-2026-10-29-run1/full-closure-tmp/` | 334 | 147.04 | `test_unfit_suffix_keeps_rollin0` |
| `accepted-evidence-recovery-2026-10-29-run1/full-stable-tmp/` | 306 | 145.19 | `test_accepted_bytes_win_over_c0` |
| `accepted-evidence-recovery-2026-10-29-run1/full-verified-tmp/` | 153 | 71.09 | `test_unusable_fallback_commits0` |
| `accepted-evidence-recovery-2026-10-29-run1/full-complete-tmp/` | 77 | 4.16 | `test_own_child_abrupt_exit_pre2` |
| `accepted-evidence-recovery-2026-10-29-run1/full-final-tmp/` | 107 | 7.05 | `test_task_deadline_change_then0` |
| `accepted-evidence-recovery-2026-10-29-run1/full-tmp/` | 109 | 8.22 | `test_explicit_choice_recovers_0` |

### Explicitly deleted Nursing archives

| File under `.local/` | Bytes |
| --- | ---: |
| `stage-b-2026-10-26-nursing-all-products-initial-crlf-source.zip` | 409,969,831 |
| `stage-b-2026-10-26-nursing-all-products.zip` | 409,972,880 |
| `stage-b-2026-10-27-nursing-segment06-all-products.initial-verifier.zip` | 334,972,707 |
| `stage-b-2026-10-27-nursing-segment06-all-products.zip` | 334,973,565 |

### Receipts

- `.local/failed-batch-cleanup-20261031_0441-plan.json`: all 1,747 exact target paths and retained-case lists.
- `.local/failed-batch-cleanup-20261031_0441-before.json.gz`: pre-cleanup file metadata, exact removed-file inventory and preservation hashes.
- `.local/failed-batch-cleanup-20261031_0441-archive-inventory.json`: archive hashes, member inventory and available top-level reports; not archive-content backups.
- `.local/failed-batch-cleanup-20261031_0441-deleted.jsonl`: per-target deletion events and free-space measurements.
- `.local/failed-batch-cleanup-20261031_0441-result.json`: successful removal/preservation checks.
- Five affected development-batch roots identify this operation in `EVIDENCE_RETENTION.md`; CURRENT_STATE links this maintained record.

Closeout: repository-only documentation checks passed for 70 Markdown files and 3,914 local links/destinations; `git diff --check` passed. All 27 retained cases and five notice links were checked. `.local/failed-batch-cleanup-20261031_0441-closeout.json` records the final checks; code/tests/configuration remained unchanged.
