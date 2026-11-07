# CRED-03-04 verification

[Spec](spec.md) · [Tickets](tickets.md)

## Migration observation

On 2026-11-07, Asia/Hong_Kong, existing planning/assignment material was separated into fixed batch files. [Organization evidence](../DOC-LAYOUT-01/verification.md) owns the preservation and navigation checks. Historical source evidence remains at its original location, linked from the spec.

## Combined acceptance

Not accepted: the current implementation request selects CRED-03 only. CRED-04 capability recovery and combined integration acceptance remain outstanding. The observations below apply to this increment, not the complete batch.

## CRED-03 offline execution (2026-11-07)

Entry HEAD was `5783d43` on `codex/docs-progressive-disclosure`. Work reuses this checkout on `codex/cred-03`; unrelated inherited CURRENT_STATE and DOC-FLOW-01 verification work is excluded from the scoped checkpoint. Ignored `.local/c3-ed68ca2f/` retains their entry copies/diff, entry source/build hashes and all five preceding `out` build members before replacement. The initial production development build passed before changing application code; `baseline-out/` retains that build, and `baseline-build.log` records the command. Its five members exactly match the preserved entry build. New cases exercise that production main/preload/renderer through the fixture-owned credential harness, not a copied loader.

Before implementation, current official Electron guidance and the pinned v45.0.0 [app lifecycle/packaged reference](https://github.com/electron/electron/blob/v45.0.0/docs/api/app.md) and [async safeStorage reference](https://github.com/electron/electron/blob/v45.0.0/docs/api/safe-storage.md) were checked against installed declarations. Initialization remains after readiness, development file access remains excluded when packaged, and async credential ownership/persistence is unchanged. No dependency upgrade is selected.

**Correction and discriminator.** `fileCandidate()` now grants default absence only in the initial stat rejection handler. Subsequent read/validation errors reach the existing fixed failure path, which prevents remembered decryption and engine/Start dispatch. No ownership, persistence queue, revision, renderer or dependency mechanism changed. Six new production-path cases use synthetic remembered ciphertext and fixture-only I/O; the read-error injection occurs after a real successful fixture stat. The failure cases assert repeated settled safe settings, visible fixed error, failed health/Start, zero decrypt/spawn/local Start calls, unchanged connection bytes, empty task workspace and secret/raw-error exclusion.

| Execution | Observed result | Retained local evidence |
| --- | --- | --- |
| `pnpm build` before the correction (includes `tsc --noEmit`) | Passed; preserved entry and freshly built baseline bytes agree. | `baseline-build.log`, `baseline-out/`, `entry-out/` |
| `pnpm exec playwright test credential-state.spec.ts --grep 'CRED-03'` on the baseline build | **1 failed, 5 passed**. Default post-discovery read ENOENT returned `credentialState=ready`, `hasKey=true` instead of fixed failure. Explicit read ENOENT, default read EACCES, default invalid UTF-8, discovery EACCES and explicit discovery ENOENT controls passed. | `red.log`, `red/results/` failure trace/context; fixture evidence is outside the runner-cleared results child. |
| `pnpm build` after correction | Passed, including TypeScript checking. Only `out/main/index.js` differs from baseline; preload and renderer members are byte-identical. | `fixed-build.log`, `out/`, `tested-manifest.json` |
| `pnpm exec playwright test credential-state.spec.ts credential-loader.spec.ts` | **37 passed** in one serial run, including all six new cases. No retries or changed expectations were needed. | `green.log`, unique `green/` fixture/profile/settings/store evidence |

**Coverage and limits.** Initial default stat ENOENT still restores the exact synthetic remembered key at local Start, with one stat, no discovered file/read, one decrypt and unchanged connection bytes after repeated settings calls. The manual-entry absence control and valid default/alternate controls also pass. Existing cases retain both file/settings readiness orders and their serial control (valid-file decrypt remains excluded), ordinary UI Start after delayed file/settings delivery, replacement/Clear against pending file/decrypt/encrypt, stale save replies, Start after accepted saves/job lookup, Remember/restart/uncheck/Clear, constant unavailability/decrypt/rotation/encryption-failure controls, connection/task-settings separation, secret exclusion and simulated packaged/launcher exclusion. The standalone loader test additionally exercises the actual local engine in an isolated empty synthetic workspace through load/reopen/opt-out/invalid phases, without conversion or provider calls. Credential-state Start capture ends before controller/model dispatch. This is CRED-03 offline acceptance; it does not test CRED-04 false/rejected-to-true capability recovery or the combined corrected batch, actual desktop incidence, provider behavior or installed readiness.

**Tested identity.** `tested-manifest.json` records 65 source/test/tool/config members (SHA-256 normalized to UTF-8 LF) and raw hashes for all three five-member build snapshots. Its SHA-256 is `d1852d2d8d6ad5f74bc9f96ceb938fb31315c1160972e81e1e70c9453447c56b`. The changed tested source identities are:

| Member | SHA-256 (UTF-8 LF) |
| --- | --- |
| `src/desktop/connection.ts` | `ff9aca1dd30e9d9ec312dc303a911be62136a42a0cb7a181be21db440d6991de` |
| `tests/desktop/specs/credential-state.spec.ts` | `c7c26fe1db8bf5d02c5f72a84beb2ca9bb4258bc8597bae199ef18226c929a70` |
| `tests/desktop/support/credential-host.cjs` | `8da7350a2212b286b919985f4601977dbcf2db018ede0c5901925af1250279bb` |

Built main SHA-256 changed from `6211922db5847cb9fe6696255f757f1a5a83a1e4127b44c18ecd5d99e3c4d6df` to `c45f668b97ec20c15310d109929dcbcbeeb2c72f09730745e325970faee0213c`. Retained logs/manifests are local evidence, not an external-review package; maintained results and regression sources do not depend on their availability. Earlier builds/results/private data were preserved. No private credential access, global settings change, real-task operation, provider call, conversion, packaging, publication, cleanup or subagent occurred.

**Documentation impact and scoped review.** The credential owner now states initial discovery versus selected-read failure explicitly; the integration guide explains the separated catches and reuses the existing readiness owner. The runtime review keeps the original d370082 counterexamples and routes later execution here instead of presenting its pending assessment as current. Spec/tickets record this turn's CRED-03-only boundary and the CRED-04 continuation. README setup/error links, DEVELOPMENT_GUIDE, technical-term consumers, launcher and package allowlists were inspected: the correction restores their promised policy without changing commands, flags, destinations or packaging inputs, so those consumers need no edits. CURRENT_STATE routes this interaction to the remaining ticket, preserving the inherited prior orientation/documentation return line unstaged. WORK_ITEMS priority/residual selection and PHASE_PLAN acceptance do not change: no new product-stage or follow-on work is selected.

The main agent reviewed the complete source/test delta and traced the policy through initialization, main-process startup/Start and renderer readiness. All 65 tested source identities still match; `save()`, `forStart()` and redaction are byte-identical to entry source after newline normalization. DOC-FLOW-01 verification retains its exact inherited bytes. `python tools/docs/check_docs.py` passed (116 Markdown files, zero errors), and `git diff --check` passed. The continuation, adoption-versus-evidence distinction and affected claims were checked directly; this is a main-agent review, not independent review or proof of all semantic coverage. The local checkpoint includes CRED-03 source/tests/owners and its CURRENT_STATE focus changes; the inherited orientation return line and DOC-FLOW-01 edits remain outside it. Stop here; resume [CRED-04](tickets.md#cred-04) only when selected.
