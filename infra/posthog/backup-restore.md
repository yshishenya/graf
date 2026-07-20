# PostHog Backup And Restore Procedure

Feature: `096-product-analytics-provider-rollout`

Status: `runtime_inventory_updated_restore_rehearsal_passed_followups_open`

This document is safe to commit. It contains no live provider secrets, database
passwords, backup object URLs, signed URLs, account identifiers, raw payloads,
screenshots, meeting content, transcript text, audio, or private local paths.

## Backup Scope

Minimum generated-runtime volumes to account for after the 2026-07-09
production setup:

| Volume | Purpose | Backup Required |
| --- | --- | --- |
| `graf-posthog_postgres-data` | PostHog relational data | yes |
| `graf-posthog_clickhouse-data` | event analytics storage | yes |
| `graf-posthog_redis7-data` | queue/cache durability where configured | yes if persistence is used |
| `graf-posthog_objectstorage` | object/blob storage used by the generated runtime | yes |
| `graf-posthog_seaweedfs` | object/blob storage used by the generated runtime | yes |
| `graf-posthog_kafka-data` | broker state when present | yes if required by reviewed runtime |
| `graf-posthog_redpanda-data` | broker state when present | yes if required by reviewed runtime |
| `graf-posthog_zookeeper-data` | coordination state | yes if required by reviewed runtime |
| `graf-posthog_zookeeper-datalog` | coordination transaction log | yes if required by reviewed runtime |
| `graf-posthog_zookeeper-logs` | coordination logs | yes if required by reviewed runtime |
| `graf-posthog_caddy-data` | Caddy runtime data/cert storage when used | yes if Caddy is the certificate owner |
| `graf-posthog_caddy-config` | Caddy runtime config storage when used | yes if Caddy owns runtime config |

If the official PostHog generator adds, removes, or renames services/volumes,
update this table before readiness can pass. Do not rely on the older minimal
web/worker/Postgres/Redis placeholder inventory for the generated runtime.

## Volume Inventory Command

Metadata-only inventory command:

```sh
docker volume ls --format '{{.Name}}' | grep '^graf-posthog-'
```

Evidence may record volume names only. Do not record dump contents or private
host paths.

Current evidence status: the metadata-only backup and isolated restore subgate
passed on 2026-07-18 for all twelve generated-runtime volume classes. Full
PostHog operational readiness remains blocked until the separate RBAC/audit,
retention/lifecycle, dashboard-freshness, and resource-threshold reviews pass.
Normal GRAF product workflows and provider live-safe delivery remain unchanged.

## Latest Rehearsal Receipt

Receipt label: `20260718T011751Z`.

- All twelve generated-runtime volume archives passed SHA-256 and tar-listing
  integrity checks.
- The production PostHog stack recovered to external analytics health `200`
  after its expected delayed migrations/startup.
- The archives were restored into twelve isolated rehearsal volumes. Core
  services became healthy and the restored web service returned HTTP `200` for
  `/_health/` with the approved analytics host header.
- The isolated containers, network, and all twelve rehearsal volumes were
  removed after the check; the live GRAF readiness probe remained `ready`.
- No provider flags, secrets, dashboard data, GRAF services, or user content
  were changed by the rehearsal.

This receipt proves backup/restore recoverability only. It does not prove
access/RBAC or audit review, retention/deletion lifecycle enforcement,
dashboard freshness/goal visibility, or concrete resource-alert thresholds.

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
