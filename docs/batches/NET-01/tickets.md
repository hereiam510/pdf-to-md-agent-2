# NET-01 tickets

[Spec](spec.md) · [Verification](verification.md) · [Register](../../WORK_ITEMS.md#runtime-and-engineering-inventory)

## Planning basis and authority

Planned 2026-11-14 (Asia/Singapore) after the user's "Confirm and plan tickets", which adopted the [NET-01 spec](spec.md) with C1 and C2. Local ticket mode applies. This file owns ticket content, dependencies and progress. The spec owns behavior and acceptance; a `verification.md` will own observed checks and the combined verdict once evidence exists.

Revised the same day after a review of the plan: T5 now includes the Electron bridge, T2's scope is narrowed to classification and reporting, the defect rule follows the authorized work, and shared interfaces have one owner. C1 and C2 are unchanged.

The user authorized implementation of T1–T6 on 2026-11-14, with offline checks only. T7 and live Nexus testing are deferred. Preserve unrelated changes and commit the NET-01 records before implementation.

On 2026-11-14 the user agreed with every finding of the [implementation review](verification.md#review-of-the-implementation-at-28cd1df) and asked to "Confirm and plan tickets". That added the closeout tickets T6a–T6c. RV2 and RV3 stay recorded in verification and get no ticket.

The subsequent request to "review and implement" selected T6a and T6b under the same offline scope. On 2026-11-14 the user selected T6c and requested the push of `codex/net-01` and a draft PR against `master`. T7 awaits a user-selected Windows sleep test window. Live Nexus testing remains deferred.

On 2026-11-14 the user agreed with the [closeout review](verification.md#review-of-the-closeout-at-b3eed35) recommendation: prepare T7 before merging, run the real sleep check, then mark PR #2 ready and merge it. The user then asked to create the tickets and implementation prompts. T7 is now split into T7a (harness and dry run, no sleep) and T7b (the real sleep runs), and T8 covers readiness and merge. Planning authorizes none of them. Each needs its own request: T7b also needs the user's sleep window, and T8 needs an explicit merge request.

**Rules for every ticket.**

- Start from `master` at `e60fa00` or a later commit that contains the earlier tickets, on a batch branch (for example `codex/net-01`), never on `master` itself.
- Use offline fixtures only: httpx `MockTransport`, local fault servers and controllable clocks. No Nexus or provider call.
- Keep the [preserved guarantees](spec.md#preserved-guarantees). If one cannot be kept, stop and report it rather than weakening it.
- Engine tests go under `tests/engine/<concern>/` with canonical imports, as described in the [project layout](../../guides/PROJECT_LAYOUT.md#tests-and-fixtures). Desktop specs go under `tests/desktop/specs/`.
- Update the governing owners named in each ticket in the same change. The spec's [document list](spec.md#documents-to-update-during-implementation) is the full set.
- Record what was run and observed in `verification.md` under the ticket's heading.
- A new defect found during the work becomes `NET-01-Fnn` in verification. Defects are judged against the work the user's request authorized, not one ticket's boundary:
  - a defect that belongs to authorized work, including a later authorized ticket, is fixed within that scope;
  - an independent finding is recorded with its evidence and deferred to the register;
  - the work stops for the user only when a finding blocks acceptance of the authorized work or needs a decision beyond its authority.

## Sequence and dependencies

| Ticket | Contribution | Depends on | State |
| --- | --- | --- | --- |
| [T1](#t1--windows-clocks-and-active-time) | Windows clock pair, boot identity, suspension detection, sleep-free active time | None | Implemented |
| [T2](#t2--failure-classes-send-evidence-and-diagnostics) | Failure classes, send evidence and bounded diagnostics | None | Implemented |
| [T3](#t3--retry-policy-cooldowns-scheduling-and-response-waits) | Frozen retry policy, cooldowns, durable scheduling, retry loop, C1 response waits | T1, T2 | Implemented |
| [T4](#t4--pauses-and-the-retry-action) | Pause reasons, the `retry_request` transition and cooldown carry-over | T3 | Implemented |
| [T5](#t5--desktop-activity-recovery-and-settings) | Desktop activity, Retry or Continue, settings, and forwarding `retry_request` through the Electron bridge | T4 | Implemented |
| [T6](#t6--integration-and-offline-acceptance) | Whole-batch offline acceptance, local-server desktop check, contract consolidation | T1–T5 | Complete |
| [T6a](#t6a--carry-the-retry-cooldown-only-into-the-first-successor) | Fix NET-01-F09: only the first successor after Retry inherits the cooldown | T6 | Complete |
| [T6b](#t6b--final-revision-suite-run) | Close NET-01-RV1: one complete Python suite run on the final revision | T6a | Complete |
| [T6c](#t6c--draft-pull-request) | Draft PR for the offline-accepted batch | T6b, plus the user's publication request | Complete. [Draft PR #2](https://github.com/hereiam510/pdf-to-md-agent-2/pull/2) |
| [T7a](#t7a--sleep-test-harness-and-dry-run) | Local scripted-server harness for the two sleep cases, validated by a no-sleep dry run | T6b | Ready; needs an implementation request |
| [T7b](#t7b--real-sleep-and-wake-runs) | Real Windows sleep during a server-requested wait and during an in-flight request | T7a, plus a sleep window chosen by the user | Blocked on T7a and the user |
| [T8](#t8--mark-pr-2-ready-and-merge) | Mark PR #2 ready, merge it and record the merge | T7b, plus the user's merge request | Blocked; needs the user |

**Order and writers.** T1 and T2 touch different files and can run in either order or side by side. T2, T3 and T4 all edit `nexus.py` and must run one at a time with one writer. T3 also edits `waiting.py`. T4 edits `runtime.py` and `server.py`. T5 edits the renderer and the Electron bridge (`src/desktop/main.ts`). T6 integrates the whole batch. T6a edits `runtime.py`, its tests and the affected contract. T6b changes no code. A defect exposed by the run reopens T6a. T7 can run before or after T6c. T7a adds a harness and changes no application code. T7b changes no code. T8 changes only records and GitHub state.

## Shared interfaces

Each interface is defined by the ticket named below, which owns it. A later ticket that needs a change makes it in coordination with that owner's records and tests, rather than redefining it. Frozen request records keep their promised immutability regardless.

- **Clock service (T1).** Working-state time, sleep-inclusive interrupt time, boot identity and detected suspensions, behind an injectable interface so tests can control both clocks. T3 and the request waits use it; nothing calls the Windows APIs directly.
- **Attempt record fields (T2).** Failure class, `send_evidence` (`may_have_been_sent`, `not_sent`, `response_observed`), HTTP status, validated upstream code and parsed `Retry-After` delay.
- **Request records (T3).** The frozen retry policy, the `not_before` cooldown and `retry_schedule`, each with an interrupt-time deadline, boot identity and `due_wall`.
- **Stop reasons and API (T4).** `network_retry_exhausted`, `network_retry_disabled`, `retry_wait_exceeds_limit`, `provider_configuration_error`, and the `retry_request` start parameter, with the job fields the desktop reads.

## T1 — Windows clocks and active time

**Contribution.** Measure active time without sleep, and detect and record suspensions. Basis: [N2 clock meanings](spec.md#n2--retry-policy-delays-and-clocks) and [N5](spec.md#n5--sleep-and-wake-windows).

**Work.**

1. Add a clock module (for example `src/pdfmd/clocks.py`). It reads `QueryInterruptTime` and `QueryUnbiasedInterruptTime` through `ctypes`, provides a boot identity from a documented OS source, and has a portable fallback that keeps `time.monotonic()` and reports no suspension detection.
2. Choose the boot identity source and record the choice with its documentation link in the engineering guide. If no documented source is reliable, use the spec's conservative fallback everywhere and record why.
3. Switch `ActiveTime` to working-state time on Windows. Detect suspensions at checkpoints and wait polls, exclude every suspension from active time, and record a `suspended_interval` with an activity event when one lasts 2 seconds or more. Keep `active_time_gap` for unmeasured crash tails only.

**Files.** The new clock module, `active_time.py`, and their tests under `tests/engine/execution/`.

**Checks.**

- The active-time and clock parts of A17, with a controllable clock pair: a 1-second and a 10-second suspension during work are both excluded, and only the 10-second one is recorded.
- Existing active-time, crash-tail and settings tests still pass.
- On this Windows machine, read both real clocks and the boot identity once, and record the values and APIs used. This check involves no sleep.

**Owners to update.** The [active-time section](../../design/RUNTIME_AND_DELIVERY.md#active-time-measurement-and-unmeasured-intervals) of the runtime contract.

## T2 — Failure classes, send evidence and diagnostics

**Contribution.** Classify every failed attempt truthfully, record what is known about sending, and capture safe diagnostics. This ticket includes no retries yet. Basis: [N1](spec.md#n1--failure-classes), [N3 send evidence](spec.md#n3--attempt-states-and-durable-scheduling) and [N6](spec.md#n6--diagnostics-r04).

**Work.**

1. In `Nexus.send` and `exchange`, map exceptions and statuses to the five N1 classes, including the TLS-cause check and the explicit transient status list.
2. Record `send_evidence` at admission (`may_have_been_sent`) and update it only on evidence.
3. Add the loopback proxy wording.
4. Read the headers' `Retry-After` and `Date` into a parsed delay without keeping the raw headers.
5. Add the bounded, isolated diagnostic body read (16 KiB, 5 s, Stop-aware) with the fixed upstream code set.
6. Route `transient_status` and `unsent` failures to a pause for now, so behavior stays safe until T3 adds retries. A proven unsent attempt pauses with a truthful message (no request reached the provider, no usage) and must not use `unknown_outcome`. Other classes keep accurate interim messages.

This ticket fixes classification and reporting only. It does not yet make a stranded task recoverable: automatic recovery arrives in T3 and the Retry transition in T4.

**Files.** `nexus.py` and tests under `tests/engine/transport/`.

**Checks.** The classification and record parts of A1–A5, plus A13, A18, A18b and A20. Existing transport, streaming and settlement tests still pass.

**Owners to update.** The R04 entry and the [integration guide's failure section](../../guides/INTEGRATION_AND_MODEL_BOUNDARY.md#11-concrete-integration-failures-and-the-retained-response).

## T3 — Retry policy, cooldowns, scheduling and response waits

**Contribution.** Retry automatically within the frozen limit, with durable waits that survive restarts and never retry early. Apply C1 to the response-wait timers. Basis: [N2](spec.md#n2--retry-policy-delays-and-clocks), [N3](spec.md#n3--attempt-states-and-durable-scheduling), [C1 and C2](spec.md#decisions-to-confirm) and [N5 wake rules](spec.md#n5--sleep-and-wake-windows).

**Work.**

1. Extend `Limits` and the frozen `replay_policy` with the retry fields and C2 defaults for new tasks. Requests frozen earlier keep their recorded policy.
2. Write the `not_before` cooldown for every parsed `Retry-After`. Write `retry_schedule` when a retry remains and is enabled.
3. Run the wait loop inside `Nexus.send`, polling Stop and the allowances at least once a second.
4. Implement the restart rules: an interrupt-time deadline in the same boot, and one persisted replacement deadline otherwise.
5. Pause with `retry_wait_exceeds_limit` without shortening a long server delay.
6. Move the `RequestWait` timers to working-state time, keeping their start at exchange start. Set the httpx read timeout to none in both the streaming and legacy paths, and leave connect, pool and write as they are.
7. Apply the same behavior to compaction requests.

**Files.** `nexus.py`, `waiting.py`, `schema.py`, and tests under `tests/engine/transport/` and `tests/engine/execution/`.

**Checks.** The retry parts of A1–A4, plus A6, A7, A10, A11, A12, A14, A16, A19, and the wait and in-flight parts of A17. Existing deadline and streaming-wait tests still pass, or any changed expectation is justified by C1 in verification.

**Owners to update.** The runtime contract's [transport behavior](../../design/RUNTIME_AND_DELIVERY.md#shared-limits-and-transport-behavior) and [Q3 recovery](../../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery) sections, and the [streaming design](../../design/STREAMING_RECEIVE.md) where its timer statements change.

## T4 — Pauses and the Retry action

**Contribution.** Pause with an accurate reason, and let one Retry click create exactly one replacement request that respects any server cooldown. Basis: [N4](spec.md#n4--pause-and-the-retry-action).

**Work.**

1. Replace the interim T2 pause with the four N4 stop reasons and messages.
2. Add `retry_request` to the start API. Validate it under the task lock, write `continuation:<request>` with `explicit_network_retry` before the graph advances, and prepare the successor from current state with the current retry policy.
3. Refuse the action before `not_before`, and carry the cooldown into the receipt and the successor's first attempt.
4. Keep explicit Continue for configuration errors and rejected replies.
5. Expose what the desktop needs on the job: the pause class, attempts used, `not_before`, and whether Retry or Continue applies.

**Files.** `runtime.py`, `server.py`, `nexus.py` (only the cooldown check at admission), and tests under `tests/engine/execution/`.

**Checks.** A8, A9, A15 and A15b; existing compaction-recovery and continuation tests still pass.

**Owners to update.** The runtime contract's Q3 section for the new transition.

## T5 — Desktop activity, recovery and settings

**Contribution.** Show retries, sleep and pauses in plain words, and give the user Retry or Continue plus the retry settings. Basis: [N7](spec.md#n7--desktop).

**Work.**

1. Activity shows "Attempt *n* of *m*", the class, the next retry time and "Resumed after sleep".
2. The task view shows the pause reason, attempts used and the duplicate-work note, plus a Retry button (disabled with "Retry available at *time*" before `not_before`) or a Continue button for configuration errors.
3. Connection settings get the "Retry automatically after network problems" checkbox (default on) and the attempts per request, replacing the current replay checkbox.
4. The Electron `start` handler in `src/desktop/main.ts` builds the engine payload itself and currently forwards only `recover_compaction_request`. It must also forward `retry_request`, or the Retry button cannot reach the engine.

**Files.** `src/renderer/` (`main.tsx`, the settings and recovery features, `types.ts`), `src/desktop/main.ts` (and the preload if its typing changes), the diagnostic client types, and specs under `tests/desktop/specs/`.

**Checks.**

- Focused desktop specs for each display state against a local scripted engine fixture.
- One check through the actual Electron path: a Retry click in the renderer reaches the engine as `retry_request`, and a second click creates no second successor.
- Typecheck and the development build.

**Owners to update.** User-facing wording wherever settings and recovery are described.

## T6 — Integration and offline acceptance

**Contribution.** Show that the whole batch meets the spec's offline acceptance and leaves earlier behavior intact. Basis: [Acceptance](spec.md#acceptance).

**Work.**

1. Run A1–A20 together on one revision, through the real `Nexus.send` and graph path, checking saved, reopened and exported output after each recovery.
2. Run the full Python and desktop suites, typecheck, and the development and frozen-engine builds.
3. Run the desktop against a local scripted server: stop and restart the server during a send, delay a reply, and kill the engine during a wait. Check the activity wording, Retry, Continue, settings and the exported result.
4. Reconcile the runtime contract, the streaming design, the guides and the R04 and NET-01 register rows into one consistent description.
5. Record the combined offline verdict in verification. It is offline only; real sleep stays with T7.

**Checks.** As listed; every A-case is linked to its observed result.

## T6a — Carry the retry cooldown only into the first successor

**Contribution.** Fix [NET-01-F09](verification.md#review-of-the-implementation-at-28cd1df). The first successor after Retry honors the cooldown under the [Q3 contract](../../design/RUNTIME_AND_DELIVERY.md#q3-execution-recovery-and-delivery), [N4](spec.md#n4--pause-and-the-retry-action) and the N2 restart rules.

**Work.**

1. Pass the receipt's `not_before` only when freezing the first successor of that Retry. Later requests in the same continuation, such as a response correction or a compaction, freeze without it. The implementer chooses how to tell them apart, for example by the successor already having an admitted attempt, or by recording the cooldown's consumer in the request. Do not change the frozen original, the receipt or the existing repair-count rule.
2. Add a sentence to the runtime contract's Q3 section saying that later requests do not inherit the cooldown, if the current wording leaves that open.

**Files.** `src/pdfmd/runtime.py`, `tests/engine/execution/test_network_recovery.py`, and the runtime contract if step 2 applies.

**Checks.**

- New regression case: after a Retry whose cooldown has passed, the successor reply has no tool call, so a correction request is frozen. Simulate a boot-marker change, and separately a missing marker, before the correction freezes. The correction request has no `not_before` and is admitted without waiting.
- The first successor still respects an unexpired cooldown. A15 and A15b still pass, as does the rest of the 61-case NET-01 matrix.
- Existing compaction-recovery and continuation tests still pass.

**Evidence.** [T6a repair and regression results](verification.md#t6a--retry-cooldown-inheritance).

## T6b — Final-revision suite run

**Contribution.** Close [NET-01-RV1](verification.md#review-of-the-implementation-at-28cd1df). Give the batch one complete all-green Python suite run on the revision that will be proposed for merge.

**Work.**

1. On a clean tree at T6a's final commit, run `.venv\Scripts\python.exe -m pytest tests/engine` with a JUnit report.
2. Run the desktop [network-retry spec](../../../tests/desktop/specs/network-retry.spec.ts) once on the same revision, because T6a changes the Retry successor path. Run typecheck and `tools/docs/check_docs.py`.
3. If a case fails, record it as `NET-01-Fnn` and handle it under the defect rule. A fix in engine code reopens T6a's checks, and the suite run is repeated on the new revision.

**Evidence.** [T6b suite run, tested revision and reports](verification.md#t6b--final-revision-suite-run) and the [combined verdict](verification.md#combined-verdict).

**Checks.** All engine tests pass on one named commit; the network-retry spec, typecheck and the docs check pass on the same commit.

## T6c — Draft pull request

**Contribution.** Put the offline-accepted batch up for review on GitHub, under the project's [delivery setting](../../../AGENTS.md#batch-documents-and-ticket-mode).

**Preconditions.** T6b has passed, and the user has asked for the push and the PR. This ticket grants neither.

**Work.**

1. Push `codex/net-01` and open a draft PR against `master`. The description states the problem (NET-01 with R04), what now works, the offline evidence with links to verification, and what remains open: T7, live route behavior, RV2 and RV3.
2. Keep the PR in draft until T7 passes, unless the user decides to merge the offline-accepted work before it. Readiness and merge each need their own request.

**Records.** The PR link and state in this ticket's row and in CURRENT_STATE.

## T7 — Real Windows sleep and wake check

**Contribution.** Observe real Windows suspend and resume against a local scripted server, with no provider calls. Basis: the real sleep case in [Acceptance](spec.md#acceptance) and the [N5 wake rules](spec.md#n5--sleep-and-wake-windows). T7a prepares and validates the harness without sleep. T7b performs the two real runs.

**Result.** Passing T7b completes NET-01's Windows acceptance. A live Nexus check of route-specific behavior is a separate, later selection.

**Limit.** The scripted server runs on the same machine and sleeps with it. The runs therefore test the engine's clocks, its waits, and a loopback connection across sleep. They do not test a remote network that drops or changes during sleep. That remains part of the later live selection.

### T7a — Sleep-test harness and dry run

**Contribution.** A repeatable driver that runs each sleep case through the real engine path and produces a report. It is validated by a dry run without sleep.

**Work.**

1. Add a driver that the user can launch from the repository root. Choose its location under the [project layout](../../guides/PROJECT_LAYOUT.md#tests-and-fixtures), for example a module launched with `python -m tests.desktop.fixtures.sleep_wake`. If no existing location fits, add a row to the layout guide. It uses the real clocks (`SYSTEM_CLOCKS`), a real `Store`, `Runtime`, `Nexus` with httpx on a real loopback socket, and a synthetic PDF fixture. It makes no provider call and needs no credential beyond a fixed local test value.
2. Script two cases on a local HTTP server:
   - **Wait case:** the first response is HTTP 503 with `Retry-After` set to a configurable delay (default 120 seconds, below the 300-second default limit). The retry then succeeds and the task saves a version.
   - **In-flight case:** the server accepts the request and holds the reply for a configurable delay (default 180 seconds) before a complete success reply. Cover the default streaming mode. A legacy non-streaming variant is optional.
3. Each case prints when to put the machine to sleep and how long to sleep (at least 60 seconds). It waits until the scripted delay and the run finish, then writes a JSON report under a unique ignored run directory (`.local/test-runs/<run>/`, as in [artifact storage](../../ARTIFACT_STORAGE.md#test-executions)). The report includes:
   - the revision, the tested case and its parameters;
   - the `powercfg /a` output, which records whether the machine uses S3 sleep or Modern Standby;
   - both clock readings and the boot marker at start and end;
   - wall-clock span, `active_seconds` before and after, and every `suspended_interval` and `resumed_after_sleep` event;
   - the attempts, with their failure classes, send evidence and `not_before` / `retry_schedule` records;
   - the job's final status and stop reason;
   - a reopened saved version and an exported ZIP verified against the source text and image.
4. Add a `--dry-run` option that shortens the delays and expects no suspension. Add pass/fail evaluation in the report, so T7b does not depend on manual interpretation. Expected results for the real runs:
   - one `suspended_interval` close to the sleep length;
   - active-time growth close to wall span minus suspension, never including the suspension;
   - no failed attempt caused by sleep;
   - in the wait case, the retry is admitted on wake once the delay has passed, so the run has two attempts;
   - in the in-flight case, the reply is accepted on the same attempt with no response-wait timeout;
   - a verified export.

**Checks.** Both dry-run cases pass on this machine and their reports are recorded. The existing engine and NET-01 tests are unaffected; run the NET-01 matrix once. `tools/docs/check_docs.py` passes.

**Records.** A T7a section in verification with the commit, the commands, the dry-run report locations and their key values, and the `powercfg /a` result. Commit the harness and records on `codex/net-01`. Pushing updates draft PR #2, so it needs the user's request.

### T7b — Real sleep and wake runs

**Preconditions.** T7a has passed, and the user has said they are ready to sleep the machine now. Only the user puts the machine to sleep and wakes it.

**Work.**

1. Start the wait case. When the driver says so, the user sleeps the machine for at least 60 seconds and wakes it. Collect the report.
2. Repeat with the in-flight case.
3. Compare each report with the T7a expectations. If a result differs, record it as `NET-01-Fnn` with the report and stop for the user. A code fix is new implementation and needs its own request.

**Records.** A T7b section in verification with both reports' key values, the sleep type, and the verdict for Windows acceptance. Update the [combined verdict](verification.md#combined-verdict) and CURRENT_STATE. Commit on `codex/net-01`. Pushing needs the user's request.

## T8 — Mark PR #2 ready and merge

**Preconditions.** T7b has passed, its records are committed and pushed, and the user has explicitly asked to merge. This ticket does not grant that request.

**Work.**

1. Confirm that the PR head equals the local commit with the T7b records, that the PR is mergeable, and that the description's open items are current: replace the T7 item with its result and keep live route behavior, RV2 and RV3.
2. Mark [PR #2](https://github.com/hereiam510/pdf-to-md-agent-2/pull/2) ready and merge it with the repository's merge-commit method, as PR #1 was.
3. After the merge, record the merge commit. Following PR #1's pattern, the record goes in the next working branch from the updated `master`. Record it in this ticket's row, the NET-01 and R04 rows in [WORK_ITEMS](../../WORK_ITEMS.md#runtime-and-engineering-inventory), and CURRENT_STATE, which then returns to next-work selection among the Stage B candidates.

**Records.** The merge commit and date. NET-01's disposition becomes closed, with live route behavior, RV2 and RV3 kept as recorded residuals with their revisit conditions.
