# PostHog Backup And Restore Procedure

Feature: `096-product-analytics-provider-rollout`

Status: `implementation_validated_review_remediated`

This document is safe to commit. It contains no live provider secrets, database
passwords, backup object URLs, signed URLs, account identifiers, raw payloads,
screenshots, meeting content, transcript text, audio, or private local paths.

## Backup Scope

Minimum volumes to account for:

| Volume | Purpose | Backup Required |
| --- | --- | --- |
| `graf-posthog-db-data` | PostHog relational data | yes |
| `graf-posthog-redis-data` | queue/cache durability where configured | yes if persistence is used |
| `graf-posthog-media` | media/blob files for provider runtime | yes |

If later implementation adds ClickHouse, object storage, or replay/blob storage,
this table must be updated before readiness can pass.

## Volume Inventory Command

Metadata-only inventory command:

```sh
docker volume ls --format '{{.Name}}' | grep '^graf-posthog-'
```

Evidence may record volume names only. Do not record dump contents or private
host paths.

## Backup Rules

- Backups are separate from GRAF app database and MinIO backups.
- Backup evidence is metadata-only.
- Backup names in evidence must not expose private host paths.
- Backup retention must support at least 90 days of analytics retention unless
  a later approved category has a shorter retention.
- Backup failures block PostHog readiness, not normal GRAF product use.

## Restore Rehearsal

Record only:

- command names;
- pass/fail status;
- volume names;
- redacted environment label;
- restore duration class;
- blocker codes.

Do not record:

- dump contents;
- secret contents;
- visitor/account data;
- raw events;
- screenshots with provider data;
- private filesystem paths.

## Rehearsal Sequence

1. Stop PostHog delivery or put provider mode into rollback/dry-run.
2. Confirm GRAF app health is unaffected.
3. Create a metadata-only backup inventory.
4. Restore into an isolated rehearsal target.
5. Run PostHog stack health check.
6. Run provider smoke in dry-run or live-safe mode.
7. Confirm secrets were not printed.
8. Record pass/fail summary in implementation evidence.

## Restore Checklist

Before restore:

- PostHog delivery is disabled or in dry-run/rollback mode;
- GRAF health is checked separately;
- target environment is isolated from production users;
- runtime secrets are mounted from secret files;
- no provider payload exports are copied into git.

After restore:

- PostHog health check passes or blocker is recorded;
- provider smoke passes in dry-run/live-safe mode or blocker is recorded;
- no secret values appear in logs/evidence;
- dashboard caveats remain visible;
- GRAF product flows remain unaffected.

## Failure Handling

If backup or restore rehearsal fails:

- keep GRAF product runtime online;
- keep PostHog provider readiness blocked;
- disable PostHog delivery if needed;
- add a dashboard caveat;
- record the blocker code without payload data.
