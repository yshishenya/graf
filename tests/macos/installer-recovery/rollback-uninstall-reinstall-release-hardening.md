# Rollback, Uninstall, And Reinstall Release-Hardening Check

## Purpose

Record metadata-only evidence that rollback, uninstall, and reinstall leave Core
Audio in a truthful state and do not require undocumented cleanup.

## Steps

- [ ] Record pre-state and current runtime probe output.
- [ ] Run rollback or record `not_accepted` when no backup exists.
- [ ] Run uninstall or record `not_accepted` when destructive cleanup is not safe
  in the current environment.
- [ ] Refresh `coreaudiod`.
- [ ] Confirm 2brain Rec virtual devices disappear after uninstall or record
  blocked evidence with manual cleanup details.
- [ ] Reinstall and run runtime probe again.
- [ ] Record operation, pre-state, post-state, Core Audio refresh requirement,
  runtime probe result, and final result.

## Evidence Rules

- Results are `passed`, `blocked`, or `not_accepted`.
- Stale HAL bundle state after uninstall is blocked.
- Any manual cleanup requirement must be explicit in the lifecycle report.
- Evidence must not contain raw audio, transcript text, credentials, tokens,
  signed URLs, passwords, or meeting content.
