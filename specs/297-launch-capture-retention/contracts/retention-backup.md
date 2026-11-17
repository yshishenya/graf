# Contract: Retention and backup prune

## Daily meeting retention

- Trigger: maintenance worker loop, at most once per 24 hours; immediate first pass is allowed.
- Scope: every active workspace with meeting retention configured.
- Operation: existing `run_retention_scan(db, settings, workspace_id, limit=100, dry_run=False)`.
- Context: `MaintenanceTenantContext(operation_name="retention_scan", feature_area="deletion", ...)`; add `retention_scan` to the allowed maintenance operations.
- Safety: use existing snapshot, row locks, processing/deleting/policy-blocked fences, deletion request and audit. Legal hold is not part of F297.
- Disable: `TWOBRAIN_RETENTION_SCHEDULER_ENABLED=false` stops the loop; re-enable requires a deploy/config change and a fresh dry-run.
- Failure: one workspace failure must not stop the loop; log metadata-only counts and safe reason.
- Idempotence: repeated runs must not create duplicate deletion requests for the same meeting.

## Backup prune

- Script: `infra/scripts/prune-rec-backups.sh`.
- Default: `--dry-run`; no file changes.
- Execute: `--execute` required.
- Root: `TWOBRAIN_BACKUP_ROOT` or `/opt/projects/2brain-rec/backups`. `TWOBRAIN_BACKUP_DIR` keeps its existing meaning of one full dated backup path and is not used as the prune root.
- Age: `--older-than-days 30` default; use directory name date, not ambiguous mtime alone.
- Eligibility: exact `YYYYMMDDTHHMMSSZ`, direct child of root, directory (not symlink), not the newest directory, not the current release backup.
- Forbidden: `..`, absolute names, symlinks, files outside root, wildcard expansion, deleting non-GRAF directories.
- Output: metadata-only `prune_result`, `candidate_count`, `deleted_count`, `skipped_count`, `reason`.
- Exit codes: `0` success/no candidates; `2` invalid root/arguments; `3` partial deletion failure.
- Timer: `infra/systemd/graf-rec-backup-prune.timer` daily; service uses the script with `--execute` only after operator installation. Disable by stopping the timer; rollback restores from the newest verified backup and records that already-deleted data is not claimed restored.

## Public policy

- Privacy policy must say: meeting materials are deleted by the daily retention job after the configured period; backups are pruned by the operator job within the configured period; external/observability copies follow their own disclosed limits.
- If the scheduler is disabled or misconfigured, the policy must not claim the automated behavior.
