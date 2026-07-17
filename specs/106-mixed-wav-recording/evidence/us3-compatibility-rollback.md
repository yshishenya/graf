# US3 Compatibility and Rollback Receipt

**Scope**: metadata-safe compatibility tests and release-boundary review only.
No release, install, rollback action, audio, transcript or credential was used.

## 2026-07-17

- The current focused macOS command passed: `212` tests, `0` failures,
  including v3/v4 read-only compatibility and v5 rejection of historical write
  behavior.
- The focused server group passed: `79` tests, `0` failures. It includes
  additive v5 source-kind migration coverage and v5 deletion truth for the
  exact `manifest`, `media` and `playback` role set.
- Release-checklist assertions passed: `11` installer lifecycle tests,
  including the rule that rollback is a release action for a subsequent
  recording, not a runtime toggle or hidden dual fallback.
- Read-only GitHub tag lookup verified the pre-v5 baseline
  `v2026.07.17.6` at `4be444e82ec449a3bb5312920fb0cd6008072c56`. The similarly
  numbered parallel `v2026.07.17.7` work is not an interchangeable baseline.

**Open release gate**: verify the exact baseline SHA, use the separately
approved local install procedure, make one controlled v5 recording, and
reinstall that baseline for one subsequent controlled recording. No accepted
v5 record may be rewritten or resubmitted during that rehearsal.
