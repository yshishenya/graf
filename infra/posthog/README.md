# Self-Hosted PostHog Infra Notes

Feature: `096-product-analytics-provider-rollout`

Status: `production_runtime_live_safe_validated_with_hardening_followups`

This directory holds the GRAF-owned PostHog deployment handoff contract and
operations notes for GRAF product analytics. The live PostHog runtime must be
created from the official PostHog self-hosted Docker Compose deployment on the
production server. The committed Compose file here is a metadata-only contract
for GRAF secret/resource/rollback expectations; it is not a replacement for the
full upstream PostHog runtime stack.

It intentionally contains placeholders only. Do not commit live PostHog project
keys, provider secrets, database passwords, object storage credentials, cookies,
visitor/account identifiers, raw payloads, or provider exports.

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.posthog.yml` | GRAF handoff/preflight contract for the separate self-hosted PostHog runtime; not the full upstream stack. |
| `posthog.production.env.example` | Redacted runtime environment example to copy outside git. |
| `backup-restore.md` | Backup, restore, and restore rehearsal procedure. |
| `graf-posthog-runtime-guard.*` | One-minute aggregate health/resource guard and fail-closed provider rollback contract. |
| `runtime-guard.env.example` | Out-of-git systemd guard settings; no secrets. |

## Runtime Placement

The first rollout runs on the same production server as GRAF but uses a separate
analytics domain and separate Compose project. It must be portable to a later
separate analytics server.

The 2026-07-09 production runtime uses the official PostHog self-hosted/hobby
Docker Compose runtime generated on the target server. The GRAF file records
the boundaries that must be applied and validated: secret files, resource
limits, health checks, backups, rollback, and metadata-only evidence.

## Required Boundaries

- separate domain/TLS route;
- separate Docker project based on the official generated PostHog runtime;
- generated runtime images pinned by reviewed tag or digest;
- separate secrets;
- separate volumes;
- explicit resource limits;
- health checks;
- bounded logs;
- backup/restore procedure;
- rollback path.

## Validation

Before future production provider changes, run:

```sh
docker compose -f infra/posthog/docker-compose.posthog.yml config
infra/scripts/cd-remote.sh --dry-run
infra/scripts/run-product-analytics-provider-smoke.sh
```

Future production deploy or PostHog stack changes require separate approval.

Install the guard script as a root-owned copy under `/usr/local/libexec`; the
systemd unit must never execute the mutable checkout. The checked-in env example
is observe-only and must be copied to `/etc` with mode `0600`; automatic
rollback/stack-stop require a separately reviewed production override.

Runtime hardening recorded on 2026-07-09: mutable generated-runtime references
were pinned by digest in the out-of-git production runtime, Compose config
validation passed, and analytics health returned `ok` after restart. Future
PostHog stack updates must repeat the mutable-tag scan and pinning check.

Production guard receipt recorded on 2026-07-20: the script is installed as a
root-owned copy, the systemd timer is `enabled` and `active`, and a metadata-only
one-shot returned `posthog_guard_result=pass` (`containers=33`, `oom=0`,
`health_failures=0`). The only host-level repair was creating the missing empty
`/opt/projects/2brain-rec/.env.lock` as `root:root` mode `0600`, required by the
systemd namespace. On 2026-07-21 the separately reviewed production override
enabled automatic analytics rollback (`AUTO_ROLLBACK=1`, `DRY_RUN=0`) while
keeping full-stack stop disabled (`STOP_STACK=0`). The follow-up one-shot passed
and both GRAF and analytics health checks returned HTTP 200. Provider delivery
remains fail-closed; this receipt does not approve product analytics rollout.
