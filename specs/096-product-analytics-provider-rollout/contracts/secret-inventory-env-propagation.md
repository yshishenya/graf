# Contract: Secret Inventory And Env Propagation

**Feature**: `096-product-analytics-provider-rollout`

Do not place live values in this file.

## Secret And Runtime Inventory

| Logical Name | Source | Target | Owner Role | Rotation Note | Committed Default | Required Test |
| --- | --- | --- | --- | --- | --- | --- |
| `POSTHOG_PROJECT_KEY` | runtime secret file | `rec-api`, web/direct config where required | product analytics operator | Rotate by creating/replacing the PostHog project key outside git, swapping the runtime secret file, and rerunning provider smoke. | empty/placeholder | file exists, value redacted, route can read without logging |
| `POSTHOG_SECRET_KEY` | runtime secret file | PostHog stack | infrastructure operator | Rotate by replacing the stack secret file, restarting the PostHog stack, and verifying health without printing the value. | empty/placeholder | stack starts and no value appears in logs/evidence |
| `POSTHOG_DB_PASSWORD` | runtime secret file | PostHog stack DB | infrastructure operator | Rotate with database credential update, stack restart, and backup/restore redaction check. | empty/placeholder | stack starts; backup/restore redacts value |
| `POSTHOG_REDIS_PASSWORD` | runtime secret file if used | PostHog stack Redis | infrastructure operator | Rotate with Redis credential update, stack restart, and smoke confirmation that no value enters evidence. | empty/placeholder | stack starts; no value in evidence |
| `POSTHOG_OBJECT_STORAGE_SECRET` | runtime secret file if used | PostHog recording/blob storage | infrastructure operator | Rotate with object-storage credential replacement, storage health check, and replay-disabled/default state verification. | empty/placeholder | storage health check passes |
| `YANDEX_COUNTER_ID` | runtime environment/provider dashboard | `rec-api`, page renderer, smoke runner | growth analytics operator | Change only through a counter migration/update record, runtime config swap, page-scope smoke, and redacted evidence. | empty | numeric presence check only |
| `YANDEX_OAUTH_TOKEN` | runtime secret file | offline conversion uploader | growth analytics operator | Rotate by issuing a new token outside git, swapping the runtime secret file, and rerunning upload auth smoke. | empty/placeholder | upload auth check without printing token |
| `PRODUCT_ANALYTICS_FLAGS` | runtime environment | `rec-api`, rendered pages, desktop config | release operator | Change through reviewed runtime config deploy or rollback, with smoke proving expected enabled/disabled states. | disabled defaults | compose config and runtime env check |

`rec-api` mounts the PostHog project key and Yandex OAuth Docker secret slots so
runtime enablement can use `/run/secrets/...` paths only. Disabled deployments
must not require live provider files to exist. The base Compose file therefore
defaults both optional provider secret sources to the committed empty
`infra/secret-placeholders/disabled_optional_provider_secret` placeholder. When
PostHog or Yandex upload is enabled, the release operator must set the matching
host-side `*_SECRET_FILE` variable to an out-of-git file under `infra/secrets/`
and keep the in-container `*_FILE` path at `/run/secrets/...`.

## Existing 094 Env Keys

These keys already exist as disabled defaults and must be carried forward or extended:

- `TWOBRAIN_PRODUCT_ANALYTICS_ENABLED`
- `TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE`
- `TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_HOST`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_PROJECT_KEY_FILE`
- `TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED`
- `TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED`
- `TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_COUNTER_ID`
- `TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OAUTH_TOKEN_FILE`
- `TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED`
- `TWOBRAIN_PRODUCT_ANALYTICS_RETENTION_MIN_DAYS`
- `TWOBRAIN_PRODUCT_ANALYTICS_CONSENT_COPY_VERSION`
- `TWOBRAIN_PRODUCT_ANALYTICS_DIRECT_DESKTOP_EGRESS_ENABLED`
- `TWOBRAIN_PRODUCT_ANALYTICS_DIRECT_DESKTOP_EGRESS_APPROVED`
- `TWOBRAIN_PRODUCT_ANALYTICS_LEGAL_APPROVED`
- `TWOBRAIN_PRODUCT_ANALYTICS_DASHBOARD_READY`
- `TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_SMOKE_APPROVED`
- `TWOBRAIN_PRODUCT_ANALYTICS_CAMPAIGN_READINESS_APPROVED`

## New Or Updated 096 Flags

Implementation tasks should add or map equivalent flags for:

- PostHog autocapture everywhere enabled;
- PostHog credential suppression enabled;
- PostHog web-direct route enabled;
- PostHog desktop-direct route enabled;
- PostHog replay enabled separately from autocapture;
- Yandex offline live upload enabled;
- Yandex all-pages inventory version;
- rollback-disabled provider modes.

## Propagation Tests

Minimum tests:

1. Host env/secret source contains only redacted or runtime values and each logical secret/runtime ID has an owner role and rotation note.
2. `docker compose -f infra/docker-compose.yml config` shows provider config only in intended services.
3. `infra/scripts/cd-remote.sh --dry-run` includes the separate PostHog stack handoff without printing secret values or private host paths.
4. Live `rec-api` runtime sees product analytics flags and secret-file paths.
5. `rec-processing-worker` does not receive PostHog/Yandex product provider secrets unless a later task proves need.
6. Rendered browser pages contain PostHog autocapture configuration after enablement and no live Yandex config on blocked Yandex page classes.
7. Smoke runner can read secret files without printing values.
8. No-secret scan finds no live keys, OAuth tokens, counter IDs, client IDs, cookies, signed URLs, raw payloads, private host paths, or content-bearing exports.
