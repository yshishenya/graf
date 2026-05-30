# Local Buffer Pressure Recovery Scenarios (US3)

## Purpose

Validate local buffer warning/critical behavior and truthful stop/degrade reporting.

## Scenarios

1. Fill local cache to warning threshold.
   - Verify copy changes to warning state before data loss.
   - Verify capture remains usable and visible state is updated.
2. Raise pressure to critical threshold.
   - Verify visible state indicates degraded.
   - Verify capture finalization requires user decision to continue or stop.
3. Raise pressure to must-degrade-or-stop threshold.
   - Verify capture cannot continue without explicit stop/recovery flow.
   - Verify local artifacts remain and deletion state stays truthful.
4. Verify disk-reserve logic with low free-space condition.
   - Verify capture stops or degrades before silent data loss.

## Expected Outcome

- Buffer pressure is visible and recoverable in explicit states.
- No silent loss without user-visible degraded/stop path.
