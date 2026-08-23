# Implementation Evidence: Feature 193

Date: 2026-08-23

## Scope and lane

- Lane: significant/high-risk capture, auth and diagnostics change; full Spec
  Kit flow with mandatory clarify, product gates and local full CI.
- Branch: `193-automatic-recording-reliability`.
- Working-tree base after synchronizing both local branches with `origin/master`:
  `42791b3865633b254b69ec628b90d0523a3e324f`. The implementation is not committed; a future
  release still requires an approved exact-SHA gate.
- Evidence is metadata-only. No audio, transcript, cookie value, credential,
  signed URL, private meeting content or raw system-log line is retained.
- Production policy, deployment, signing, release and installed app contents
  were not changed.

## Confirmed root causes and fixes

- AudioHAL and Sensor Indicator events previously overwrote one shared active
  state. They are now independent sources; candidate end requires all sources
  to be inactive through the grace period.
- Emitting a detector trigger previously closed the candidate before the
  consumer outcome was known. Accepted, retryable and terminal outcomes now
  control closure, with a bounded two-second retry for transient blockers.
- Prompt countdown and detector-assisted capture could outlive policy,
  acknowledgement or readiness changes. Every route now requires current
  authorization before the promise and rechecks immediately before capture.
- The one-shot log child had no bounded startup reconciliation or recovery.
  One supervisor now owns bounded final-state snapshot, live observation,
  restart and wake generations without parallel children.
- WebKit login replacement/logout did not authoritatively remove stale native
  copies. Same-origin reconciliation now deletes old scope copies and native
  selection is deterministic across expiry, domain, path, scheme and host-only
  constraints.
- Final review found a stop-before-observation race: `observations()` cleared a
  prior stop request and could start a generation after deliberate stop. The
  reset was removed and a regression test was added.

## Focused and repository validation

- Focused reliability suites on `42791b38`: `135 tests`, `0 failures`. They cover source
  permutations, all-source end/grace, consumer outcomes, current start gates,
  snapshot/live recovery, cookie reconciliation and capture controls.
- The stop-before-observation regression first reproduced the defect as `1
  failure`; after the root fix it passed, and it is included in the `131/131`
  result.
- `infra/scripts/ci-local.sh --fast` on the pre-sync base `f0916254`: `1170
  passed`; server lint, Python compile and retired-audio guard passed. It is
  retained as historical evidence and is not an exact-SHA gate for `42791b38`.
- `infra/scripts/ci-local.sh --full` was intentionally stopped by the user
  (`exit 130`) during the server suite at about 26%. It is not a passing full
  CI result. Before the stop, the macOS build, `747/747` macOS tests and
  `ContractValidation: PASS` completed on the pre-sync base `f0916254`.
- Full server tests, strict PostgreSQL/RLS, deployment evidence and the exact-SHA
  full gate for `42791b38` remain intentionally unrun after the requested stop.

## Runtime evidence

- A fresh ad-hoc `GRAF Local.app` was built from the pre-sync working tree and
  opened without installing or replacing the public app; this is historical
  runtime evidence, not an exact-`42791b38` smoke result.
- Terminating only the dev `/usr/bin/log stream` child produced one replacement
  child in `2.773 s`; the child count remained exactly one (historical
  pre-sync run).
- Deliberate observer stop and stop-before-start are covered by
  `testLogStreamDeliberateStopDoesNotRespawn` and
  `testLogStreamStopBeforeObservationNeverStartsGeneration`.
- Desktop UI automation could not reliably deliver Quit while a permission
  onboarding sheet and two GRAF app identities were present, so no GUI quit is
  counted as pass evidence. During that attempt the already-running installed
  process exited; its bundle, configuration and policy were not modified. It
  was relaunched unchanged and finished with exactly one observer child while
  the dev app was absent.

## Review and privacy checks

- Correctness review of parser, candidate state machine, observer supervisor,
  start gates and cookie reconciliation found no remaining actionable defect.
- `git diff --check`: PASS.
- Modified/untracked secret, forbidden-content and added-live-path scans: PASS.
- Ponytail review: `Lean already. Ship.` No dependency, endpoint, database
  schema, global cookie cleanup or replacement observer abstraction was added.

## Explicit limitations

- No private meeting, real audio, transcript or raw provider/system-log content
  was used.
- Sleep/wake and deliberate stop are exercised through deterministic test seams;
  only child failure recovery was repeated against the live dev process.
- This evidence does not authorize production policy enablement, deployment,
  installation, signing, notarization, tag or release.

## Verdict

Focused implementation validation is complete on synchronized base
`42791b38`; the repository full gate is incomplete by explicit user request.
The working tree is ready for review and an approved commit/PR, not for
automatic production rollout.
