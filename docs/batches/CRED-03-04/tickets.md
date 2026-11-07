# CRED-03-04 tickets

[Spec and authority](spec.md) · [Verification](verification.md)

All work is owned by the main agent. The 2026-11-07 implementation request selects CRED-03 only under the spec's offline boundary and requires a stop before CRED-04. Shared credential state requires sequential integration.

## CRED-03

Contribution: implement the selected default-file failure correction. Basis and completion conditions: [mechanism](../../design/DEVELOPMENT_CREDENTIALS.md#selected-credential-follow-up-target-2026-11-06), [follow-up acceptance](../../design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). Dependencies: inspected actual baseline and preserved inherited work under the spec. State: complete at the scoped offline boundary, main agent, 2026-11-07. The discovery-only absence correction and production-path regressions are implemented; [verification](verification.md#cred-03-offline-execution-2026-11-07) owns the baseline failure, checks and limits. This does not complete CRED-04 or integration.

## CRED-04

Contribution: implement selected Remember capability recovery. Same [mechanism](../../design/DEVELOPMENT_CREDENTIALS.md#selected-credential-follow-up-target-2026-11-06) and [acceptance owner](../../design/DEVELOPMENT_CREDENTIALS.md#credential-follow-up-acceptance). Dependency: integrate CRED-03 before editing shared credential state. This is execution ordering, not a new product dependency. State: not started.

Continuation when selected: reconcile the CRED-03 checkpoint and inherited edits, then implement the second selected rule in `ConnectionState.save()` without altering file eligibility. Extend production-path capability-transition instrumentation and execute the capability-recovery/newer-intent rows plus the original regressions. Combined review/acceptance remains in the integration ticket after both repairs. The current turn stops before this work.

## CRED-03-04-INTEGRATION

Main agent reviews the combined changes, executes the linked follow-up and original regression checks under the spec's offline boundary, corrects scoped failures and records the combined verdict in verification. Dependencies: CRED-03 and CRED-04. State: not started. Existing historical results do not certify either new repair.
