# US3 Compatibility and Rollback Receipt

**Scope**: metadata-safe compatibility tests and release-boundary review only.
No release, install, rollback action, audio, transcript or credential was used.

## 2026-07-17

- The current focused macOS command passed: `215` tests, `0` failures,
  including v3/v4 read-only compatibility and v5 rejection of historical write
  behavior.
- The focused server and release-integration group passed: `117` tests,
  `11` expected skips, `0` failures. It includes additive v5 source-kind
  migration coverage and v5 deletion truth for the exact `manifest`, `media`
  and `playback` role set.
- Release-checklist assertions passed: `11` installer lifecycle tests,
  including the rule that rollback is a release action for a subsequent
  recording, not a runtime toggle or hidden dual fallback.
- Read-only GitHub tag lookup verified the pre-v5 baseline
  `v2026.07.17.6` at `4be444e82ec449a3bb5312920fb0cd6008072c56`. The
  user-confirmed, still-in-progress parallel `v2026.07.16.7` work is not an
  interchangeable baseline.

**Open release gate**: verify the exact baseline SHA, use the separately
approved local install procedure, make one controlled v5 recording, and
reinstall that baseline for one subsequent controlled recording. No accepted
v5 record may be rewritten or resubmitted during that rehearsal.

## 2026-07-18

- Re-ran the compatibility/rollback-focused macOS group from `quickstart.md`:
  `219` tests passed, `0` failures.
- Re-ran the matching server ingest, processing, deletion and playback group:
  `97` tests passed, `0` failures. One pre-existing Starlette TestClient
  deprecation warning remains.
- The result validates the v3/v4 read-only compatibility boundary, v5-only
  creation/rejection rules, deletion coverage and the no-live-toggle rollback
  contract. It does not claim the separate installed-app baseline rehearsal.

## 2026-07-18 — exact baseline rehearsal outcome

- `baseline_ref=v2026.07.17.6`, `baseline_sha=4be444e82ec449a3bb5312920fb0cd6008072c56`.
- `baseline_artifact_and_signature=pass`; `installed_app_replaced=no`.
- `rollback_scope=isolated_future_capture_rehearsal`; `baseline_subsequent_recording=fail`.
  The baseline manual Start surface was exercised, but ScreenCaptureKit timed
  out (`runtime_start_failed`) before a recording package was published.
- `candidate_v5_integrity_pre_post=unchanged`; `candidate_v5_resubmit_or_rewrite=no`.
- `synthetic_e2e_and_deletion=pass`; `rollback=fail/open`.
- Limitation: this receipt makes no installer, updater, TCC or deployment
  rollback claim and does not mark T064 complete.
