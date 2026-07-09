# Self-Hosted PostHog Infra Notes

Feature: `096-product-analytics-provider-rollout`

Status: `implementation_validated_review_remediated`

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

## Runtime Placement

The first rollout runs on the same production server as GRAF but uses a separate
analytics domain and separate Compose project. It must be portable to a later
separate analytics server.

Production execution must use the official PostHog self-hosted/hobby Docker
Compose runtime generated on the target server, with a reviewed DockerHub image
tag or commit. The GRAF file records the boundaries that must be applied and
validated: secret files, resource limits, health checks, backups, rollback, and
metadata-only evidence.

## Required Boundaries

- separate domain/TLS route;
- separate Docker project based on the official generated PostHog runtime;
- pinned PostHog image tag supplied through `POSTHOG_IMAGE` before production
  execute;
- separate secrets;
- separate volumes;
- explicit resource limits;
- health checks;
- bounded logs;
- backup/restore procedure;
- rollback path.

## Validation

Before any production execution, run:

```sh
docker compose -f infra/posthog/docker-compose.posthog.yml config
infra/scripts/cd-remote.sh --dry-run
infra/scripts/run-product-analytics-provider-smoke.sh
```

Production execute requires separate approval.

Before production execute, replace
`posthog/posthog:REPLACE_WITH_PINNED_RELEASE_TAG` with an explicitly reviewed
PostHog DockerHub release tag or reviewed commit-derived image reference in the
runtime env outside git. Do not deploy the mutable `latest` tag.
