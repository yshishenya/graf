# Backup retention and disable/rollback

Feature: `297-launch-capture-retention`.

## What runs

- `graf-rec-backup-prune.timer` runs daily at 04:20 UTC.
- It calls `infra/scripts/prune-rec-backups.sh --execute --older-than-days 30`.
- The script removes only direct child directories of `TWOBRAIN_BACKUP_ROOT`
  whose name is exactly `YYYYMMDDTHHMMSSZ` and whose age is greater than 30
  days. It never removes the newest backup, symlinks, foreign directories or
  files outside the root.

## Install (operator)

```sh
install -m 0755 infra/scripts/prune-rec-backups.sh /usr/local/libexec/prune-rec-backups.sh
install -m 0644 infra/systemd/graf-rec-backup-prune.service /etc/systemd/system/
install -m 0644 infra/systemd/graf-rec-backup-prune.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now graf-rec-backup-prune.timer
```

Before enabling, run a dry run:

```sh
TWOBRAIN_BACKUP_ROOT=/opt/projects/2brain-rec/backups \
  /usr/local/libexec/prune-rec-backups.sh --dry-run --older-than-days 30
```

If you use a different root, update both `Environment=TWOBRAIN_BACKUP_ROOT=` and
`ReadWritePaths=` in the service before enabling it.

## Disable

```sh
systemctl disable --now graf-rec-backup-prune.timer
```

Retention scanning can be stopped independently with
`TWOBRAIN_RETENTION_SCHEDULER_ENABLED=false` on all API/worker roles.

## Rollback

1. Stop the timer.
2. Restore the newest verified full backup using the normal restore runbook.
3. Verify PostgreSQL, object storage, health and a synthetic meeting.
4. Record the incident and the recovery point.
5. Do not claim that already-pruned data was restored.

## Evidence

Keep only metadata: command, exit code, counts, backup reference, timestamps.
Never commit database dumps, object lists, credentials, audio or transcript
content.
