# Rollback and Partial Cleanup Matrix (US4)

## Purpose

Validate rollback behavior and truthful reporting when partial cleanup cannot be completed automatically.

## Scenarios

1. **Rollback with prior signed backup available**
   - Simulate a bad installer state.
   - Run rollback operation.
   - Confirm rollback restores a valid prior HAL bundle state and writes a successful rollback report.

2. **Rollback without backup**
   - Remove known backup path to force no-source restore.
   - Run rollback.
   - Confirm `partial`/`manual` outcome and explicit remediation items are returned.
   - Confirm diagnostics include both attempted source and destination paths.

3. **Rollback and update deferral interplay**
   - Attempt rollback while call/capture is active and confirm no forced stop occurs as part of this operation.
   - If operation pauses, result includes exact state and why.

4. **Partial cleanup validation**
   - Force HAL removal permission failure for one path.
   - Confirm uninstall report includes per-path manual remediation list, not only generic failure copy.
   - Confirm report file can be consumed by support tooling (valid JSON).

## Expected Outcome

- Rollback and partial cleanup produce deterministic machine-readable reports.
- Manual remediation steps are explicit, actionable, and localized to affected component paths.
