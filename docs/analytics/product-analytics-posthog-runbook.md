# Product Analytics PostHog Runbook

Feature: `096-product-analytics-provider-rollout`

Status: `production_runtime_live_safe_validated_with_hardening_followups`

This runbook is safe to commit. It contains no live PostHog project key,
provider secret, token, cookie, visitor identifier, raw event payload, screenshot,
meeting content, transcript, audio, signed URL, or private local path.

## Purpose

Self-hosted PostHog is the primary GRAF product analytics workspace for feature
096. It is first-party and owner-controlled, so it may receive broad product
analytics and browser autocapture. That wider PostHog scope does not apply to
Yandex, paid advertising surfaces, committed evidence, logs, screenshots, or raw
payload dumps.

PostHog Cloud is out of scope for this rollout.

## Hosting Decision

- First placement: same production server as GRAF.
- Public route: separate analytics domain, `analytics.2brain.pro`.
- Runtime boundary: separate Docker Compose project from the GRAF app stack.
- Portability: must be movable later to a separate analytics server without
  changing event names, identity rules, dashboard definitions, or disclosure
  copy.

## DNS And TLS

Domain: `analytics.2brain.pro`.

Production runtime metadata recorded on 2026-07-09:

- internal analytics `_health` check returned `ok`;
- external HTTPS analytics `_health` check returned `ok`;
- the GRAF app health check stayed `ready` after runtime provider enablement.

DNS evidence may record only:

- domain label;
- record type;
- status: pending/pass/blocked;
- non-secret blocker code.

TLS evidence may record only:

- certificate issuance status;
- renewal status;
- route status;
- non-secret blocker code.

Do not commit provider screenshots, account details, private IP inventories, or
secret material as DNS/TLS evidence.

## Compose And Deploy Handoff

The production PostHog runtime comes from the official PostHog self-hosted
Docker Compose deployment generated on the target server for a reviewed
DockerHub image tag or commit. The committed
`infra/posthog/docker-compose.posthog.yml` file is the GRAF handoff/preflight
contract for secret, resource, backup, rollback, and evidence expectations. It
is not the complete upstream PostHog runtime stack.

`infra/scripts/cd-remote.sh --dry-run` must report the separate PostHog handoff
as metadata only:

```text
posthog_stack_handoff=dry_run_metadata_only
posthog_stack_contract=infra/posthog/docker-compose.posthog.yml
posthog_stack_runtime_source=official_posthog_hobby_generated_compose_required
posthog_stack_execute=requires_explicit_release_approval
```

The dry-run handoff is not production execution. Starting or updating the
PostHog stack in production requires separate explicit release approval.

The official runtime normally includes more than web, worker, Postgres, and
Redis. The release operator must preserve the upstream-required services such
as ingestion/capture workers, ClickHouse, Kafka-compatible broker, object
storage, proxy/TLS, and any additional services required by the reviewed
PostHog release. Do not deploy a simplified GRAF-only Compose file as if it were
the full PostHog stack.

Runtime fix recorded on 2026-07-09:

- the generated node services needed explicit internal Redis settings for
  logs/traces and the combined plugins service;
- `LOGS_REDIS_HOST`, `LOGS_REDIS_PORT`, `LOGS_REDIS_TLS=false`,
  `TRACES_REDIS_HOST`, `TRACES_REDIS_PORT`, and `TRACES_REDIS_TLS=false` must
  be present where the generated runtime starts logs/traces consumers;
- without these values, the services can try localhost or Redis TLS and exit
  even while the main web health check is green.

## Required Runtime Boundaries

PostHog must stay separate from the GRAF application stack in these areas:

- domain and TLS route;
- Compose project name;
- services and networks;
- runtime secret files;
- volumes and backup targets;
- resource limits;
- log retention;
- health checks;
- RBAC/access review;
- dashboard/export permissions;
- rollback switches.

## Secret Handling

Live values are never committed. Runtime secrets are supplied through secret
files or equivalent out-of-git mounts.

Required logical secrets:

| Logical Secret | Runtime Target | Evidence Allowed |
| --- | --- | --- |
| `POSTHOG_PROJECT_KEY` | `rec-api`, browser/direct config where required | present/redacted status only |
| `POSTHOG_SECRET_KEY` | PostHog stack | present/redacted status only |
| `POSTHOG_DB_PASSWORD` | PostHog database | present/redacted status only |
| `POSTHOG_REDIS_PASSWORD` | Redis if enabled | present/redacted status only |
| `POSTHOG_OBJECT_STORAGE_SECRET` | object/blob storage if enabled | present/redacted status only |

Runtime note for non-swarm Docker Compose: `uid`, `gid`, and `mode` on Compose
secrets may be ignored and host files may be bind-mounted as-is. If `rec-api`
fails closed on an unreadable provider secret, correct only the runtime file
permissions/ownership outside git and rerun health plus provider smoke. Do not
print the secret value.

Forbidden evidence:

- key values;
- secret file contents;
- raw request/response payloads;
- screenshots with account or visitor data;
- event/autocapture/replay exports.

## Image Pinning

Committed Compose files must not default to the mutable `latest` PostHog image.
Generated runtime images must be pinned to explicitly reviewed release tags or
image digests outside git and recorded only as redacted/pinned-status evidence.

The operator may use an out-of-git env file for the GRAF handoff contract:

```sh
POSTHOG_RUNTIME_ENV_FILE=/opt/graf/posthog/posthog.production.env \
POSTHOG_IMAGE=posthog/posthog:<reviewed-release-tag> \
docker compose -f infra/posthog/docker-compose.posthog.yml config
```

This command validates the GRAF handoff contract only. Live PostHog startup
still requires the official generated PostHog Compose runtime and explicit
release approval.

Runtime hardening recorded on 2026-07-09: generated runtime references that
previously used mutable `latest`/`master` tags were pinned by digest in the
out-of-git production runtime, Compose config validation passed, the analytics
domain returned `_health=ok` after restart, and post-pinning web/desktop
live-safe smoke events were ingested. Keep this pinning check in every future
PostHog stack update.

For the GRAF app stack, the base Compose file mounts optional PostHog/Yandex
provider secret slots from `infra/secret-placeholders/disabled_optional_provider_secret`
while product analytics is disabled. That placeholder is intentionally empty:
it lets Docker start without live provider files, and the app treats it as
missing if someone points a runtime `*_FILE` setting at it. When enabling
PostHog delivery, set the host-side `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_PROJECT_KEY_SECRET_FILE`
to an out-of-git `infra/secrets/...` file and keep
`TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_PROJECT_KEY_FILE=/run/secrets/graf_posthog_project_key`.

## Data Scope

Allowed inside self-hosted PostHog:

- approved 094 activation events;
- approved public acquisition events from 093;
- server-mediated product events;
- web-direct page/event/autocapture data;
- desktop-direct product analytics data;
- broad browser autocapture for current browser-rendered GRAF pages;
- future browser page autocapture after global credential suppression exists;
- product-visible identity/context that GRAF can already display to authorized
  operators, such as role/category labels and owner-controlled user/account
  context, when retained inside the self-hosted PostHog workspace only.

Forbidden everywhere, including first-party PostHog:

- passwords and passcodes;
- OAuth codes;
- access, refresh, and ID tokens;
- API keys;
- provider/client secrets;
- signed URLs;
- cookies;
- private keys;
- raw audio files;
- raw transcript/meeting-content dumps;
- raw payload dumps in logs or evidence.

## Autocapture

096 enables PostHog autocapture for every current browser-rendered page class.
The page inventory records sensitivity, expected product-visible data,
credential suppression, retention/deletion truth, owner role, dashboard purpose,
and rollback behavior.

Autocapture is not session replay.

Rendered-page wiring is validated, not only helper-level configuration:

- public pages such as `/`, `/download`, and `/privacy` render anonymous
  first-party PostHog provider config;
- auth pages such as `/login` and `/sign-up` render anonymous first-party
  PostHog provider config;
- authenticated cabinet, settings, calendar, meeting detail, deletion report,
  and embedded desktop webview pages render pseudonymous `graf_pseudo_*`
  `distinct_id` values;
- the browser sends autocapture through the first-party
  `/api/v1/product-analytics/posthog-web-capture` proxy;
- provider smoke rejects credential material such as token-like actions before
  returning dry-run success.

## Session Replay

Default state: disabled.

Replay may be enabled later only after page-class proof covers:

- masking by default;
- URL/title/referrer sanitization;
- form/input suppression;
- private DOM hiding;
- storage and retention;
- QA evidence;
- legal approval;
- dashboard caveat;
- rollback.

## Initial Same-Server Resource Thresholds

These are the concrete first-pass limits for the same-server deployment. The
thresholds are review and rollback contracts; they do not claim that an alerting
service exists. A future monitor must emit only the status, threshold and
blocker code described here.

| Area | Initial Threshold | Rollback/Review Trigger |
| --- | --- | --- |
| CPU | Per-service Compose caps: `worker=4`, `web=3`, `clickhouse=3`, `elasticsearch=2`, `db=2`, `kafka=2`, `plugins=2`, `temporal-django-worker=2`; all other services are capped at `0.5–1` CPU. | Review at host 1-minute load `>=9` for 5 minutes; the guard alerts on a sample at `>=11`. |
| Memory | Per-service Compose caps: `worker=12g`, `web/clickhouse/elasticsearch=8g`, `db/kafka/plugins/temporal-django-worker=4g`, `zookeeper/temporal/ingestion/object-storage/recording-api=2g`, small services `1g`. | Roll back on any PostHog `OOMKilled=true`, more than 2 new restarts in 10 minutes, or host available memory `<16 GiB`. |
| Disk | Keep analytics volumes separate; review below `20%` free and block/rollback before `<10%` free on the configured analytics filesystem. | Mark PostHog not ready, disable provider delivery, preserve GRAF workflows, and restore only after backup and free-space checks pass. |
| Network | Analytics traffic remains on `analytics.2brain.pro`; probe analytics health every 60 seconds. | The guard alerts after 2 consecutive failed analytics/GRAF probes; latency and 3-of-5 probe review remain operator checks. |
| Logs | `json-file` rotation `max-size=50m`, `max-file=3` for every generated-stack service. | Review if rotation is missing or forbidden fields appear; stop provider delivery before unbounded growth can affect GRAF. |
| Backups | Daily metadata-only backup; latest backup age must be `<26h`; retain at least 90 days and rehearse isolated restore at least monthly. | Block readiness if backup is missing/stale or restore rehearsal fails; use the last known-good compose/volume state. |
| Retention | Product event retention is `84` months; session recording policy is `5y` while recording is opted out; the 90-day baseline remains the minimum for new categories. | Review any policy/category without a documented owner and deletion behavior; do not claim lifecycle readiness from an empty table alone. |

The 2026-07-20 production receipt verified the 35-service Compose configuration,
35 CPU entries, 35 memory entries, 33 running containers with non-zero runtime
CPU/memory limits, zero OOM-killed containers, analytics health `200`, GRAF
readiness `200`, and `29%` disk used. The production compose change is kept
outside git with rollback copies. The repository guard contract now exists, but
the production systemd installation remains a separate T101 deploy receipt.

Analytics must degrade first. Normal GRAF workflows must not be starved by the
PostHog stack.

Disk-full behavior:

1. Mark PostHog readiness blocked.
2. Disable PostHog server/web/desktop delivery or set rollback mode.
3. Keep GRAF application workflows running.
4. Preserve metadata-only evidence of the blocker.
5. Restore PostHog only after backup/restore and free-space checks pass.

Resource-pressure behavior:

1. Stop provider delivery before product workflows are affected.
2. Keep dashboard caveats visible.
3. Run provider smoke after resource changes.
4. Record only status, threshold, and blocker code.

## Automated Runtime Guard

The repository includes a deliberately narrow guard at
`infra/scripts/posthog-runtime-guard.sh`. Production must run a reviewed,
root-owned copy from `/usr/local/libexec`, not the mutable application
checkout, through the systemd oneshot/timer pair
(`graf-posthog-runtime-guard.service` and `graf-posthog-runtime-guard.timer`)
once per minute.
The guard emits only aggregate metrics and threshold/blocker codes to stdout
and journald. It fails closed when host, Docker, or health metrics are
unavailable, validates that running analytics containers retain non-zero CPU
and memory limits, and never reads, prints, or copies provider secrets or event
payloads.

On a breach it logs an alert and, when the out-of-git environment sets
`GRAF_POSTHOG_GUARD_AUTO_ROLLBACK=1` with `GRAF_POSTHOG_GUARD_DRY_RUN=0`,
sets all product-analytics provider switches to their fail-closed values and
restarts only `rec-api`. Set `GRAF_POSTHOG_GUARD_STOP_STACK=1` in the reviewed
production override when the analytics containers must also be stopped to
remove resource pressure. The expected impact is a measurement gap; GRAF
readiness and normal product workflows remain the guarded health checks. A
rollback or stack-stop failure returns a non-zero status for systemd/alerting.
The runtime environment example is `infra/posthog/runtime-guard.env.example`.

Installation is a release/deploy step, not a local smoke side effect:

```sh
install -d -o root -g root -m 0755 /usr/local/libexec
install -o root -g root -m 0755 infra/scripts/posthog-runtime-guard.sh /usr/local/libexec/graf-posthog-runtime-guard.sh
install -o root -g root -m 0644 infra/posthog/graf-posthog-runtime-guard.service /etc/systemd/system/
install -o root -g root -m 0644 infra/posthog/graf-posthog-runtime-guard.timer /etc/systemd/system/
install -o root -g root -m 0600 infra/posthog/runtime-guard.env.example /etc/graf-posthog-runtime-guard.env
systemctl daemon-reload
stat -c '%U:%G %a %n' /usr/local/libexec/graf-posthog-runtime-guard.sh /etc/graf-posthog-runtime-guard.env
GRAF_POSTHOG_GUARD_DRY_RUN=1 systemctl start graf-posthog-runtime-guard.service
systemctl enable --now graf-posthog-runtime-guard.timer
```

The checked-in environment example is observe-only (`AUTO_ROLLBACK=0`,
`DRY_RUN=1`, `STOP_STACK=0`). Before enabling automatic rollback, create a
separate root-owned production override, verify the dry-run receipt, and record
the operator approval. The contract test checks the thresholds, metadata-only
logging, fail-closed switches, secure install path, zero-restart execution, and
one-minute timer; it does not constitute a production timer receipt.

## RBAC And Audit Model

Committed evidence may use roles and statuses only, not personal names or
emails.

Minimum roles:

- infrastructure operator: manages stack, secrets, TLS, backups, restore;
- product analytics operator: manages project settings and event/dashboard
  configuration;
- dashboard viewer: reads aggregate dashboards;
- campaign reviewer: may inspect campaign-facing reports only after campaign
  readiness is separately approved.

Audit expectations:

- access changes are reviewed;
- export creation is reviewed;
- replay flag changes are reviewed;
- retention changes are reviewed;
- provider configuration changes are reviewed.

## Backup And Restore

The detailed procedure lives in `infra/posthog/backup-restore.md`.

The runbook must always identify:

- volumes included in backups;
- volumes excluded from backups;
- retention for backup artifacts;
- restore rehearsal command sequence;
- evidence format;
- failure and rollback behavior.

Evidence remains metadata-only.

Current backup/restore receipt: on 2026-07-18 the generated runtime volume set
(relational data, ClickHouse, Kafka/Redpanda, Redis, object/blob storage, Caddy,
and coordination volumes) passed a metadata-only archive integrity check and
an isolated restore rehearsal. The restored web health endpoint returned `200`,
the rehearsal volumes were removed, and GRAF stayed ready. Full PostHog
operational readiness is still gated by the separate resource, RBAC/audit,
retention/lifecycle, and dashboard-freshness reviews.

Backup retention:

- maintain enough backups to support at least the 90-day analytics retention
  baseline unless a later legal/security rule requires a shorter category;
- never commit backup archives or content-bearing exports;
- record restore rehearsal status before live readiness claims.

## Move-Out Procedure

When moving PostHog to a separate analytics server:

1. Keep event names, approved field contracts, identity rules, disclosure copy,
   and dashboard definitions stable.
2. Prepare the new analytics host with equivalent secrets, volumes, resource
   limits, TLS, and backups.
3. Restore or migrate PostHog data using the backup/restore procedure.
4. Update DNS and runtime PostHog host configuration.
5. Run provider smoke.
6. Confirm GRAF health.
7. Record only metadata-only evidence.

If move-out fails, restore the previous endpoint or disable PostHog delivery.
The expected product impact is a measurement gap only.

## Rollback

Rollback must be able to disable:

- server-mediated PostHog delivery;
- web-direct PostHog delivery;
- desktop-direct PostHog delivery;
- autocapture;
- session replay;
- analytics domain exposure when required.

Normal product workflows must continue.

## Validation Commands

Implementation evidence should record pass/fail summaries for:

```sh
docker compose -f infra/posthog/docker-compose.posthog.yml config
infra/scripts/run-product-analytics-provider-smoke.sh
infra/scripts/validate-product-analytics-provider-pages.sh
infra/scripts/rollback-product-analytics-providers.sh
infra/scripts/cd-remote.sh --dry-run
```

Do not run future production deploys or PostHog stack changes from this runbook
without explicit release approval.
