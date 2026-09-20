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
passed on 2026-07-18 for all twelve generated-runtime volume classes. A
90-day session-recording policy and session-replay object-lifecycle rule were
configured on 2026-07-21, but full PostHog operational readiness remains
blocked until independent RBAC/audit, future deletion-enforcement,
dashboard-freshness, and persistent alert/restore reviews pass. Normal GRAF
product workflows and provider live-safe delivery remain unchanged.

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

## What A Restore Recreates And What Is Lost

Feature `273-paid-traffic-analytics` requires the restore path to state which
data comes back completely and which data is gone for good (FR-053). This
section is the contract for that split. The 2026-07 receipts above stay valid
for the manual rehearsal path; the scheduled automation that produces the
archives is described in `docs/analytics/product-analytics-posthog-runbook.md`.

Fully recoverable from the analytics backup set:

- the PostHog relational database: projects, dashboards, insights, feature
  flags, and organisation/user configuration;
- ClickHouse event data that was durably persisted at backup time;
- session-recording objects that were present in the backed-up object/blob
  storage volumes;
- queue, cache, and broker state that is part of the archive.

Permanently lost without a fresh backup:

- events captured after the newest archive;
- in-flight ingestion that was never persisted to ClickHouse;
- session-replay objects that were not yet uploaded to object storage;
- every class the backup inventory excludes — `infra/posthog/backup-volumes.txt`
  marks optional classes with a `?` suffix, so a `?` class is recoverable only
  when the reviewed runtime actually included it;
- provider-side data GRAF does not control, such as Yandex.Metrica aggregates,
  which are never restored from this backup set;
- data already removed by the enforced retention terms: measurement events at
  365 days, anonymous aggregate at 1095 days, visit attribution at 90 days, and
  client acquisition attribute at 1095 days.

A restore recreates the analytics node only. GRAF product workflows are never
restored from this backup set, are never stopped by it, and must keep running
while the analytics node is rebuilt. The expected product impact of a restore is
a measurement gap, not a product outage.

### Copy Count And Placement (FR-052)

A copy that lives only on the same disk as the original is not a backup. At
least two copies of the analytics backup set are kept at all times, and at least
one of them is offsite — outside the measured server. When either condition
fails, analytics readiness stays blocked (`backup_copy_count_below_minimum` or
`backup_offsite_copy_missing`) and the copy does not count as disaster
recovery. An offsite copy that no run has refreshed is a stale copy, not a
second copy.

### Retention And Recovery Objectives

| Objective | Value | Source |
| --- | --- | --- |
| Backup artifact retention | Keep at least two stored copies per FR-052; keep enough history to support the enforced analytics retention categories unless a later approved category is shorter | `## Backup Rules` |
| Recovery-point objective | Newest archive not older than `26` hours (`GRAF_POSTHOG_BACKUP_MAX_AGE_HOURS`) | FR-033, FR-034 |
| Recovery-verification objective | Successful restore verification not older than `30` days (`GRAF_POSTHOG_RESTORE_MAX_AGE_DAYS`), recorded as metadata-only evidence | FR-035, SC-010 |
| Minimum stored copies | `2` (`GRAF_POSTHOG_BACKUP_MIN_COPIES`) | FR-052 |
| Minimum offsite copies | `1` (`GRAF_POSTHOG_BACKUP_MIN_OFFSITE_COPIES`) | FR-052 |

Backup artifact receipts and the newest archive age are recorded as metadata
only. Production receipts for the scheduled backup, the restore verification,
and the first offsite upload are `pending operator receipt`.

### Scheduled Automation

Three tasks keep the rules above true without an operator in the loop. Each one
writes a metadata-only state file that the readiness report
(`providers.analytics_operations`) and the external alert read, and each one
alerts on failure instead of stopping the product.

| Task | Unit and timer | State file |
| --- | --- | --- |
| Archive every inventory volume class and upload one offsite copy | `infra/posthog/graf-posthog-backup.{service,timer}`, daily 02:30 | `/var/lib/graf-posthog-backup/backup-state` |
| Restore one stored copy into isolated rehearsal volumes and read it back | `infra/posthog/graf-posthog-restore-verify.{service,timer}`, days 1 and 15 at 04:30 | `/var/lib/graf-posthog-backup/restore-state` |
| Enforce the events, aggregate and attribution retention terms | `infra/posthog/graf-posthog-retention-enforce.{service,timer}`, daily 03:15 | `/var/lib/graf-posthog-retention/retention-state` |

Commands:

```sh
infra/scripts/backup-posthog.sh --dry-run
infra/scripts/backup-posthog.sh --execute
infra/scripts/verify-posthog-restore.sh --execute
infra/scripts/verify-posthog-restore.sh --status
```

The restore verification never touches the live analytics stack: it verifies
every archive against the SHA-256 manifest, unpacks into
`graf-posthog-rehearsal-*` volumes, counts the restored files, and removes the
rehearsal volumes afterwards. The volume class list is
`infra/posthog/backup-volumes.txt`; a class marked with `?` is optional, and a
required class that resolves to no volume fails the run.

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
