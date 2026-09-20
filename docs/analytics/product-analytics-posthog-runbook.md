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

## Invitation SMTP Through Postal

GRAF already sends transactional mail through the owner-controlled Postal
installation. PostHog invitation mail follows the same contour, but uses SMTP
because PostHog owns the email task: configure its dynamic instance settings
to use the internal `postal-smtp:25` service, a dedicated Postal SMTP
credential, and a sender in the Postal-owned `tutor.2brain.pro` domain. Do not
reuse the GRAF Postal HTTP API key as an SMTP password, and do not use a sender
domain that Postal does not own.

The current production hop is inside the private Docker network, so
`EMAIL_USE_TLS=false` and `EMAIL_USE_SSL=false` are intentional. This does not
make the public Postal SMTP endpoint an unauthenticated relay. Keep the
credential only in PostHog's instance settings database and never print it or
commit it. After changing settings, restart the PostHog worker so its cached
email configuration is refreshed, then resend the existing invitation rather
than creating another one.

Verify all of the following without recording recipient data or message
content:

- PostHog reports email available and its web/worker health endpoints return
  HTTP `200`;
- the worker records a sent timestamp for the invitation message;
- Postal logs show accepted SMTP authentication, sender/recipient acceptance,
  and `250` message-data acceptance.

The production Postal Compose handoff now declares `graf-posthog_default` as
an external shared network and attaches `postal-smtp` to it alongside the
Postal network. After a Postal update or recreation, rerun the Compose config
check and verify that PostHog resolves `postal-smtp:25` before relying on
invitation delivery. If the worker cannot connect, keep product analytics
fail-closed; this mail path must never block normal GRAF workflows.

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
| Retention | Product event retention is `84` months; the self-hosted session-recording policy is now `90d` while recording is opted out; the session-replay bucket has an enabled 90-day object-lifecycle rule. | Review any policy/category without a documented owner and deletion behavior; do not claim lifecycle readiness from an empty table alone. The 90-day project value is a reversible self-hosted database override because the supported API rejected the entitlement. |

The 2026-07-20 production receipt verified the 35-service Compose configuration,
35 CPU entries, 35 memory entries, 33 running containers with non-zero runtime
CPU/memory limits, zero OOM-killed containers, analytics health `200`, GRAF
readiness `200`, and `29%` disk used. The production compose change is kept
outside git with rollback copies. The repository guard contract now exists, but
the production systemd installation and automatic-rollback override are recorded
in the T101 production receipts.

The 2026-07-21 operations receipt configured the session-recording policy at
`90d` and an enabled 90-day lifecycle on the session-replay object-storage
bucket. The bucket was empty, session replay remains disabled, and no general
GRAF/PostHog object-storage lifecycle was changed. The approved-goal dashboard
now contains aggregate-only insights, but its refresh timestamp remains unset
while provider delivery is disabled. See
`specs/096-product-analytics-provider-rollout/validation/t101-posthog-operations-receipt-20260721.md`.

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

## Threshold Scopes: Analytics First, Host Second

Feature `273-paid-traffic-analytics` splits the guard thresholds into two
independent scopes (FR-031, FR-032, SC-012). The split lives in
`infra/scripts/posthog-runtime-guard.sh` and is configured through
`infra/posthog/runtime-guard.env.example`. Every value below defaults to the
previously hard-coded threshold, so removing a line keeps production behaviour.
The analytics scope is evaluated first and may disable measurement only. The
host scope alerts only and never disables measurement automatically, so a
traffic spike on the public site cannot stop measurement by itself.

Analytics scope — these reasons may disable measurement:

| Reason code | Condition | Threshold variable | Default |
| --- | --- | --- | --- |
| `analytics_node_unavailable` | Node availability: failed analytics probes | `GRAF_POSTHOG_GUARD_ANALYTICS_HEALTH_FAILURES` | `1` (one failed analytics probe) |
| `analytics_storage` | Analytics storage free space below the review floor | `GRAF_POSTHOG_GUARD_ANALYTICS_DISK_FREE_PERCENT` | `20` (`<20 %` free) |
| `analytics_delivery_lag` | Delivery lag at or above the limit | `GRAF_POSTHOG_GUARD_ANALYTICS_LAG_SECONDS` | `900` (`>=900 s`) |
| `analytics_queue_depth` | Ingest queue backlog at or above the limit | `GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_DEPTH` | `100000` (`>=100000`) |
| `analytics_queue_growth` | Ingest queue growth at or above the limit | `GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_GROWTH_PER_MIN` | `5000` (`>=5000` per minute) |
| `container_limits_missing` | Analytics container CPU/memory limits missing | — | any missing limit |
| `container_oom` | Container OOM-killed | — | more than `0` |
| `container_restarts` | Container restarts in the last 10 minutes | — | more than `2` |

Host scope — these reasons alert only and never disable measurement:

| Reason code | Condition | Threshold variable | Default |
| --- | --- | --- | --- |
| `host_load` | Host 1-minute load average at or above the limit | `GRAF_POSTHOG_GUARD_HOST_LOAD` | `11` (`>=11`) |
| `host_memory` | Host available memory below the limit | `GRAF_POSTHOG_GUARD_HOST_MEMORY_MIB` | `16384` (`<16384 MiB`) |
| `host_disk` | Host disk free space below the limit | `GRAF_POSTHOG_GUARD_HOST_DISK_FREE_PERCENT` | `10` (`<10 %`) |
| `host_product_probe_unavailable` | GRAF product readiness probe failing | `GRAF_POSTHOG_GUARD_HOST_HEALTH_FAILURES` | `2` (2 consecutive minutes) |

`GRAF_POSTHOG_GUARD_AUTO_ROLLBACK=1` with `GRAF_POSTHOG_GUARD_DRY_RUN=0` may now
disable measurement only for analytics-scope reasons. Host-scope reasons never
disable measurement, never edit the provider switches, and only raise an alert.
This is the rule that keeps SC-012 true: a fivefold traffic spike does not turn
measurement off and does not affect product availability.

Unreadable analytics probes are reported as an analytics alert, not as a silent
pass: `analytics_delivery_lag_unavailable` when the delivery-lag probe cannot be
read and `analytics_queue_metric_unavailable` when the queue metric cannot be
read. Both are alert-only while `GRAF_POSTHOG_GUARD_ANALYTICS_STRICT_METRICS=0`.
Set `GRAF_POSTHOG_GUARD_ANALYTICS_STRICT_METRICS=1` only after the first
production receipt proves the probes are readable; from then on a broken probe
disables measurement instead of passing silently.

The same `*_unavailable` shape covers every other unreadable probe, and none of
them disables measurement by itself: `docker_unavailable` and
`docker_inspect_unavailable` when the container runtime cannot be queried,
`posthog_containers_missing` when no analytics container is running,
`restart_metric_unavailable`, `restart_history_unavailable` and
`restart_state_unavailable` for the restart counters, and
`host_load_unavailable`, `host_memory_unavailable`, `host_disk_unavailable` and
`host_clock_unavailable` for the host sensors. A report that lists an
`*_unavailable` code means the guard could not verify that probe, so the
threshold behind it is unproven for that minute rather than satisfied.

The alert path adds its own codes when the notification itself is the problem:
`alert_channel_unavailable` when the channel probe fails, `guard_state_missing`
and `guard_state_stale` when the guard state file is absent or older than
`GRAF_ANALYTICS_ALERT_STATE_MAX_AGE_MINUTES`, `alert_delivery_failed` when
delivery fails on every transport, and `alert_owner_unnamed` when the fired rule
resolves to a role that the environment does not name. The complete machine-
readable inventory of every code, its scope, severity, owner role and escalation
window is `infra/posthog/alert-rules.txt`.

The analytics thresholds are justified by a measured baseline, not by a guess:
the absolute volume per storage class, the growth per day, and the growth per
1000 events are recorded in `docs/analytics/product-analytics-capacity-baseline.md`.
Until that measurement is executed and filed, every baseline row stays
`pending operator receipt`.

Each run writes a metadata-only state file to
`$GRAF_POSTHOG_GUARD_STATE_DIR/alert-state`, default
`/var/lib/graf-posthog-runtime-guard/alert-state`. It carries no visitor or user
data and no secrets:

| State key | Meaning |
| --- | --- |
| `alert_state_version` | State schema version |
| `recorded_at`, `recorded_at_epoch` | When the sample was written |
| `result` | `pass` or `alert` |
| `breach_scope` | `analytics`, `host`, or `analytics+host` |
| `analytics_scope`, `host_scope` | Per-scope `pass`/`alert` verdict |
| `analytics_breaches`, `host_breaches` | Breach codes observed in each scope |
| `analytics_disable_reasons` | Analytics breach codes that may disable measurement |
| `measurement_action` | `not_requested`, `blocked_dry_run`, `disabled`, or `failed` |
| `load_1m`, `memory_mib`, `disk_free_percent` | Host metrics |
| `delivery_lag_seconds`, `queue_depth`, `queue_growth_per_min` | Analytics metrics |
| `container_count`, `oom_count`, `restart_count` | Container metrics |
| `health_failures`, `analytics_health_failures` | Consecutive probe failures per scope |
| `product_impact` | `measurement_gap_only` |

The external alert path is `infra/scripts/alert-analytics-degradation.sh`
(Telegram), with a delivery deadline of at most 15 minutes from the start of a
degradation (SC-009). The systemd timers are
`infra/posthog/graf-analytics-degradation-alert.timer` (every 5 minutes) and
`infra/posthog/graf-analytics-alert-channel-check.timer` (every 15 minutes,
independent channel-outage detection, FR-056). Like the guard, these units are
installed and enabled as a release/deploy step, not by a local smoke run. The
training alert that proves the deadline is
`infra/scripts/alert-analytics-degradation.sh --drill`. No production drill
exists yet, so the SC-009 delivery receipt is `pending operator receipt`.

## Alert Rules And Named Owners

FR-055 requires a named owner for every alert rule, and FR-054 forbids visitor
and user data in the alert body. The machine-readable rule inventory is
`infra/posthog/alert-rules.txt`. It is line-oriented, with one `rule` line per
rule, and its header states the format:

```text
rule code=<code> scope=<analytics|host|backup|restore|retention|alerting> \
     owner_role=<role> severity=<critical|warning> escalate_after_minutes=<n> \
     requirement=<FR-030|FR-031|FR-032|FR-033|FR-035|FR-036|FR-051|FR-056>
```

Field meaning:

| Field | Meaning |
| --- | --- |
| `code` | The exact rule code the guard, the backup task, the restore verification task, the retention task, or the alert channel check emits |
| `scope` | `analytics` or `host` for the guard rules; `backup`, `restore`, `retention`, or `alerting` for the scheduled tasks and the alert path itself |
| `owner_role` | The responsible role, for example `analytics_operator`, `infra_operator`, or `product_owner` |
| `severity` | `critical` or `warning` |
| `escalate_after_minutes` | How long the rule may stay unacknowledged before escalation |
| `requirement` | The requirement the rule implements |

The file groups rules by scope: analytics rules that may disable measurement,
host rules that never disable measurement, backup and restore rules, retention
rules, and the alert-path rules used for independent channel-outage detection.
A rule without an owner role is a configuration error.

The committed file is installed as a root-owned configuration file on the
analytics server (`/etc/graf-analytics-alert-rules.txt`, overridable through
`GRAF_ANALYTICS_ALERT_RULES_FILE`). The alert script reads the owner role for a
fired rule code from it, resolves the role to a named owner from the
environment, and reports `alert_owner_unnamed` when the role has no name. A
checkout whose alert script cannot read the rules file treats every rule as
`unassigned`, which is why the file must be installed and kept in sync with the
repository before readiness is claimed.

The concrete named owner is never committed. This repository records roles and
statuses only, so the operator names the responsible person in the out-of-git
environment file (`GRAF_ANALYTICS_ALERT_OWNER_INFRA_OPERATOR`,
`GRAF_ANALYTICS_ALERT_OWNER_ANALYTICS_OPERATOR`,
`GRAF_ANALYTICS_ALERT_OWNER_PRODUCT_OWNER`). When the environment does not name
the owner, the alert still goes out and carries `alert_owner_unnamed`, so the
gap is visible in the channel and in journald instead of passing silently. No
owner assignment receipt exists yet: it is `pending operator receipt`.

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

Access review receipt (initial state, 2026-07-21): a pending `ADMIN`
invitation exists for a second trusted operator, but the active membership
count is still one because the invitation had not been accepted. The initial
receipt was recorded before the SMTP follow-up below.
The invitee must set their own password and enable MFA. Until then, the
owner-only access boundary remains open and provider delivery stays fail-closed.

SMTP follow-up (2026-07-21): the existing invitation was resent through the
shared Postal contour and PostHog recorded successful message delivery. The
invite remains pending until the invitee accepts it and enables MFA; this does
not by itself close the independent RBAC/audit gate.

### Two Operators And Mandatory Second Factor

FR-037 requires at least two analytics operators and a mandatory second factor.

- Access requires at least two analytics operators holding an accepted
  membership. One accepted operator plus one pending invitation is one operator,
  not two.
- The second factor (TOTP) is mandatory. It must be enrolled before any provider
  access is used, not after: an account that has not enrolled TOTP may not read
  dashboards, change project settings, create exports, or review audit events.
- An invitation that is not accepted does not count as a second operator, does
  not close the RBAC/audit gate, and does not allow provider delivery to be
  turned on.
- Until two accepted operators with enrolled TOTP exist, the owner-only access
  boundary stays open, analytics readiness stays blocked, and GRAF provider
  delivery stays fail-closed. The 2026-07-21 receipt above records exactly that
  state, and this rule keeps it in force.

### Operator Change And Access Revocation Procedure

FR-060 requires access to be revocable, not only grantable. An access change
follows this order and is recorded before provider delivery resumes:

1. Revoke the membership on the same day as the role change. Do not leave an
   unused privileged account for a later cleanup.
2. Rotate every provider credential the removed operator could read, so the old
   credential cannot be reused after the membership is gone.
3. Review the provider audit log for the removal window and confirm that no
   action after the revocation belongs to the removed operator.
4. Keep GRAF provider delivery fail-closed until the review is recorded. A
   revocation that has not been reviewed is not a finished revocation.
5. Record a metadata-only receipt: roles, statuses, and dates only. Never record
   personal names, emails, account identifiers, credential values, or provider
   payloads here or in any other committed evidence.

A periodic access review is required even when nothing changed. The review
confirms the accepted operator count, TOTP enrollment status, that removed
access is actually revoked and not merely intended, and that the installed guard
copy on the server still matches the reviewed repository revision (FR-038). The
review interval is an owner decision recorded with the receipt; access review
and operator-change receipts remain `pending operator receipt` until then.

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

### Scheduled Backup, Restore Verification, And Retention

Feature `273-paid-traffic-analytics` adds the automation that turns the manual
procedure above into a scheduled, evidence-producing path (FR-033, FR-035,
FR-036, FR-051, FR-052).

| Artifact | Schedule | State file | Contract |
| --- | --- | --- | --- |
| `infra/scripts/backup-posthog.sh` | daily systemd timer `graf-posthog-backup.timer`, `OnCalendar=*-*-* 02:30:00` | `/var/lib/graf-posthog-backup/backup-state` | At least two retained copies; exactly one offsite copy is required per run through `GRAF_POSTHOG_OFFSITE_COMMAND`; a run without the offsite copy is a failure, not a partial success |
| `infra/scripts/verify-posthog-restore.sh` | systemd timer `graf-posthog-restore-verify.timer`, days 1 and 15, `OnCalendar=*-*-01,15 04:30:00` | `/var/lib/graf-posthog-backup/restore-state` | Restores into an isolated target and records metadata-only evidence: command names, pass/fail status, duration class, blocker codes |
| `infra/scripts/enforce-product-analytics-retention.sh` | daily systemd timer `graf-posthog-retention-enforce.timer`, `OnCalendar=*-*-* 03:15:00` | `/var/lib/graf-posthog-retention/retention-state` | Enforces every approved local retention category and records the outcome per category |
| `infra/scripts/apply-posthog-event-ttl.sh` | operator step whenever the term changes | — | Applies and verifies `infra/posthog/clickhouse-retention.sql`; the term is `POSTHOG_EVENT_RETENTION_DAYS`, default `365` |

The retention task has a deliberately narrow deletion boundary. Its PostgreSQL
statements target only the tables declared by the product-analytics SQLAlchemy
models and Alembic migrations: `anonymous_page_aggregate_buckets` by
`bucket_date`, `public_visit_attributions` by `expires_at`, and
`client_acquisition_attributes` by `captured_at`. It verifies every table and
age column before issuing any `DELETE`; if any mapping, table, column, or
retention state is missing, the run fails closed and deletes nothing. The
ClickHouse path reads system metadata to verify the `sharded_events` TTL but does
not delete provider-held rows. Billing provider-event metadata in
`billing_webhook_events.metadata_json` is outside this product-analytics purge
scope; no provider-held data is claimed deleted by this task.

The committed units run the installed copies in `/usr/local/libexec` and read
root-owned environment files (`/etc/graf-posthog-backup.env`,
`/etc/graf-posthog-retention.env`). The installed names differ from the
repository names, so the two cannot be confused by accident:

| Unit | Installed script | Repository source | Environment file |
| --- | --- | --- | --- |
| `graf-posthog-backup.{service,timer}` | `/usr/local/libexec/graf-posthog-backup.sh` | `infra/scripts/backup-posthog.sh` | `/etc/graf-posthog-backup.env` |
| `graf-posthog-restore-verify.{service,timer}` | `/usr/local/libexec/graf-posthog-restore-verify.sh` | `infra/scripts/verify-posthog-restore.sh` | `/etc/graf-posthog-backup.env` |
| `graf-posthog-retention-enforce.{service,timer}` | `/usr/local/libexec/graf-posthog-retention-enforce.sh` | `infra/scripts/enforce-product-analytics-retention.sh` | `/etc/graf-posthog-retention.env` |
| `graf-analytics-degradation-alert.{service,timer}` | `/usr/local/libexec/graf-analytics-degradation-alert.sh` | `infra/scripts/alert-analytics-degradation.sh` | `/etc/graf-analytics-alert.env`, `/etc/graf-posthog-runtime-guard.env`, `/etc/graf-posthog-backup.env` |
| `graf-analytics-alert-channel-check.{service,timer}` | `/usr/local/libexec/graf-analytics-degradation-alert.sh --check-channel` | `infra/scripts/alert-analytics-degradation.sh` | `/etc/graf-analytics-alert.env`, `/etc/graf-posthog-runtime-guard.env` |
| `graf-posthog-runtime-guard.{service,timer}` | `/usr/local/libexec/graf-posthog-runtime-guard.sh` | `infra/scripts/posthog-runtime-guard.sh` | `/etc/graf-posthog-runtime-guard.env` |

Install each source with `install -o root -g root -m 0755`, install the unit
files with mode `0644`, install the environment files with mode `0600`, then run
`systemctl daemon-reload`. The alert channel check is the same installed script
with `--check-channel`, which is why the two alert units share one file. The
alert units also read the guard and backup environment files because they need
the same state-file paths the guard and the backup task write.

systemd evaluates `OnCalendar` in the
server timezone: keep the analytics server on UTC so `02:30`, `04:30`, and
`03:15` are UTC times, and record the timezone with each receipt.

Retention categories enforced by the scheduled task:

| Category | Term | Storage | Mechanism |
| --- | --- | --- | --- |
| `measurement_events` | `365` days | ClickHouse | Row TTL |
| `anonymous_aggregate` | `1095` days | PostgreSQL | Scheduled task |
| `visit_attribution` | `90` days | PostgreSQL | Scheduled task |
| `acquisition_attribute` | `1095` days | PostgreSQL | Scheduled task |

Every deletion is logged with a row count and nothing else: no visitor data, no
user data, no event content, no account identifiers. A category with no
retention term is a configuration error, never "keep indefinitely" (FR-050), and
the task must fail loudly rather than delete by guesswork.

The ClickHouse category is enforced as a row TTL rather than a delete loop, so
it has its own step:

```sh
infra/scripts/apply-posthog-event-ttl.sh --dry-run
infra/scripts/apply-posthog-event-ttl.sh --execute
```

The statement in `infra/posthog/clickhouse-retention.sql` targets
`sharded_events`, the MergeTree table every insert path reaches; `events` and
`writable_events` are distributed tables and cannot carry a TTL. The committed
Compose file is a metadata-only handoff for the generated PostHog runtime, so it
declares the required term in its `x-graf-clickhouse-retention` block instead of
enforcing it as a service setting; the DDL above is the enforcement. The daily
retention task reads the enforced TTL back and fails with
`clickhouse_ttl_not_enforced` when it is missing or shorter than the approved
term, and the readiness claim stays blocked in that case.

A failed backup raises an alert (FR-051); a failed restore verification blocks
the analytics readiness claim (FR-035, FR-051). These timers are installed and
enabled as a release/deploy step, not by a local smoke run. Scheduled backup,
restore-verification, retention-enforcement, TTL application, and
first-offsite-upload receipts are all `pending operator receipt` until they run
on the analytics server.

## Analytics Readiness Blockers

Analytics readiness is blocked by the blockers reported in the
`analytics_operations` block of `GET /api/v1/product-analytics/catalog`, under
`providers.analytics_operations.blockers` (FR-034, FR-050, FR-051, FR-053). A
blocker list is part of the readiness claim: it cannot be overridden by a
technical flag, it blocks the claim itself once live provider delivery is
claimed, and a readiness verdict that ignores a reported blocker is a
configuration error rather than a ready state.

| Blocker code | Meaning |
| --- | --- |
| `backup_state_unavailable` | The backup state file is missing or unreadable |
| `backup_missing` | No stored analytics backup copy exists |
| `backup_stale` | The newest copy is older than the recovery-point objective |
| `backup_offsite_copy_missing` | Fewer than the minimum number of copies live outside the measured server |
| `backup_copy_count_below_minimum` | Fewer than the minimum number of stored copies are present |
| `restore_verification_missing` | No successful restore verification is recorded |
| `restore_verification_stale` | The last successful verification is older than the verification objective |
| `restore_verification_failed` | The last verification attempt failed |
| `retention_state_unavailable` | The retention state file is missing or unreadable |
| `retention_category_missing:<category>` | A required retention category is absent from configuration |
| `retention_term_missing:<category>` | A configured category has no retention term (FR-050) |
| `retention_term_below_required:<category>` | A configured term is shorter than the required term for the category |
| `retention_enforcement_unverified:<category>` | The category has a term but no recorded enforcement |

Defaults for every threshold above:

| Setting | Default | Meaning |
| --- | --- | --- |
| `GRAF_POSTHOG_BACKUP_MAX_AGE_HOURS` | `26` | Newest backup copy not older than 26 hours |
| `GRAF_POSTHOG_RESTORE_MAX_AGE_DAYS` | `30` | Successful restore verification not older than 30 days (SC-010) |
| `GRAF_POSTHOG_BACKUP_MIN_COPIES` | `2` | At least two stored copies |
| `GRAF_POSTHOG_BACKUP_MIN_OFFSITE_COPIES` | `1` | At least one offsite copy |

The blocker list carries codes and counts only. It must never expose payload
data, provider secrets, private host paths, or personal data, and the readiness
state remains `blocked` until the underlying condition is fixed and verified.

## Storage Capacity And Growth Measurement

The analytics scope thresholds in this runbook (queue growth, storage fill) are
only defensible against a measured baseline, so the load check required by
FR-039 and the growth rate required by SC-012 are recorded in
`docs/analytics/product-analytics-capacity-baseline.md`.

```sh
infra/scripts/measure-posthog-storage-growth.sh --window-hours 24
infra/scripts/measure-posthog-storage-growth.sh --status
```

| What | Where |
| --- | --- |
| Measurement script | `infra/scripts/measure-posthog-storage-growth.sh` |
| Committed result table | `docs/analytics/product-analytics-capacity-baseline.md` |
| Stored sample for the next comparison | `/var/lib/graf-posthog-storage/storage-growth-state` |
| Analytics storage guardrail | `GRAF_POSTHOG_GUARD_ANALYTICS_DISK_FREE_PERCENT`, default `20` |

The script reports storage sizes and event counts only; it never reads event
content, and it does not change retention, configuration, or the running stack.
Run it twice with at least 24 hours of ordinary traffic between the runs: the
second run then records `growth_basis=previous_sample`, which is the only
measured baseline. A results table whose cells still read
`pending operator receipt` means the load check has not been performed and the
baseline may not be quoted as evidence.

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
