# Contract: Provider Smoke

**Feature**: `096-product-analytics-provider-rollout`

Provider smoke proves wiring and readiness without committing private payloads.

## Required Smoke Scripts

Implementation tasks should add or extend scripts for:

- `infra/scripts/run-product-analytics-provider-smoke.sh`
- `infra/scripts/validate-product-analytics-provider-pages.sh`
- `infra/scripts/rollback-product-analytics-providers.sh`

Existing 094 scripts may be reused or wrapped:

- `infra/scripts/run-product-analytics-smoke.sh`
- `infra/scripts/validate-product-analytics-pages.sh`

## PostHog Smoke Scenarios

| Scenario | Expected Evidence |
| --- | --- |
| Stack health | service status, separate domain reachability, redacted runtime mode |
| Secret wiring | secret file present, value redacted, no committed values |
| RBAC/access model | role/access model status, audit expectation status, no personal identifiers |
| Retention/deletion lifecycle | retention days, backup/export/offline caveat status, no content-bearing exports |
| Deploy dry-run handoff | separate PostHog stack included in dry-run validation without secret output |
| Server delivery | approved synthetic event accepted or dry-run validated |
| Web-direct delivery | rendered page config present, credential suppression present |
| Autocapture everywhere | current browser page classes report autocapture enabled or non-browser |
| Desktop-direct delivery | desktop route configured or blocked with explicit reason |
| Dashboard visibility | dashboard exists and owner/caveats recorded |
| Rollback | flags disable delivery/autocapture without product outage |

## Yandex Smoke Scenarios

| Scenario | Expected Evidence |
| --- | --- |
| Counter reuse | runtime counter presence redacted; no live ID committed |
| Public baseline | `/` and `/download` still approved |
| Blocked pages | blocked Yandex classes do not render Yandex collection |
| Offline upload auth | OAuth secret file present and redacted |
| Offline live upload | exactly two approved milestones can upload or live-safe smoke pass records provider status |
| Duplicate protection | retry does not create duplicate conversion evidence |
| Dashboard visibility | offline conversion/reporting surface visible without screenshot data |
| Rollback | offline upload and all-pages expansion disable cleanly |

## Smoke Output Shape

Smoke output must be line-oriented or JSON metadata that is safe to commit:

```text
provider_smoke_result=pass
posthog_stack=reachable
posthog_access_model=metadata_only_pass
provider_lifecycle=metadata_only_pass
posthog_deploy_dry_run=pass
posthog_autocapture=current_pages_enabled
yandex_counter=runtime_only_redacted
yandex_offline=live_safe_pass
private_payload_status=none_committed
rollback_status=pass
```

Forbidden smoke output:

- raw request/response payloads;
- provider tokens;
- PostHog project key;
- Yandex counter ID;
- Yandex ClientID/Yclid/cookies;
- screenshots with visitor/account/meeting data;
- transcript/audio/meeting content;
- signed URLs or local paths.

## Failure Handling

Provider smoke failure blocks provider rollout, not normal product use. Evidence records:

- provider;
- failed step;
- non-secret reason;
- rollback status;
- dashboard caveat.
