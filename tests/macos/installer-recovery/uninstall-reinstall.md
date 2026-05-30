# Uninstall + Reinstall Recovery (US4)

## Purpose

Validate uninstall truthfulness, manual-remediation handoff, and reinstall behavior after partial or successful cleanup.

## Preconditions

- Install has completed and app-managed virtual devices are visible.
- At least one physical input and output selection has been made.
- Capture stop action has been used or is available.

## Scenarios

1. **Clean uninstall**
   - Run uninstall from interactive flow.
   - Confirm uninstall report explicitly reports `succeeded` when both app bundle and HAL bundle are removed.
   - Confirm if restart is required, the user-facing requirement is shown and persisted in report.
   - Confirm virtual devices disappear from Core Audio after reboot/restart where applicable.

2. **Reinstall after uninstall**
   - Re-run installer install flow immediately after uninstall.
   - Confirm app can re-install from scratch without duplicate HAL registration.
   - Confirm route setup must be re-run and no stale route-copying assumptions are applied automatically.

3. **Physical output/input restoration**
   - During uninstall while device selections are known, confirm restoration attempt is recorded.
   - If auto-restore succeeds, report is explicit `restored`.
   - If restore fails partially, report contains specific manual remediation entries.

4. **Reinstall under partial uninstall state**
   - Simulate uninstall partial path (manual cleanup needed).
   - Reinstall anyway.
   - Confirm manual cleanup report does not block installer from running when operator confirms cleanup status.
   - Confirm all failure paths remain truthful and do not auto-suppress manual cleanup warnings.

## Expected Outcome

- Uninstall result is machine-readable and truthful.
- Reinstall path is deterministic and idempotent.
- Restore attempts and manual cleanup requirements are never hidden.
