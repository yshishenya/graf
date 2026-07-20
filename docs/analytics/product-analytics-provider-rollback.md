# Product Analytics Provider Rollback

Feature: `096-product-analytics-provider-rollout`

Status: `ready_not_executed`

This rollback runbook is safe to commit. It contains no live provider IDs,
tokens, cookies, visitor identifiers, payload rows, screenshots, meeting
content, transcript text, audio, signed URLs, or private local paths.

## Product Impact Rule

Rollback reduces measurement. It must not break normal GRAF product workflows.

Expected allowed impact:

- analytics measurement gap;
- dashboard caveat;
- provider delivery gap.

Rollback must preserve:

- login/signup;
- cabinet navigation;
- recording/upload/review flows;
- deletion/export/account/legal flows;
- telemetry gate truth.

## Rollback Targets

| Target | Disable Method | Verification |
| --- | --- | --- |
| PostHog server delivery | runtime provider mode or enable flag | provider smoke reports disabled or measurement gap |
| PostHog web-direct delivery | rendered config flag or snippet removal | page validation shows no delivery route |
| PostHog desktop-direct delivery | desktop runtime flag | macOS/config smoke reports route disabled |
| PostHog autocapture | runtime autocapture flag | page validation shows autocapture disabled |
| PostHog session replay | replay flag/provider setting | page validation shows replay disabled |
| PostHog stack | stop analytics stack or remove routing | GRAF health remains ready |
| PostHog deploy handoff | disable separate stack handoff | dry-run reports no PostHog execution path |
| Yandex all-pages expansion | runtime all-pages flag | blocked pages render no Yandex collection |
| Yandex offline upload | runtime offline flag or secret removal | uploader reports disabled |
| Yandex Webvisor/maps/forms | provider/page-class setting | inventory records unavailable |
| Provider validation mode | runtime validation mode | smoke reports disabled |

## Rollback Script

Dry-run command:

```sh
infra/scripts/rollback-product-analytics-providers.sh --target all
```

The script is safe by default:

- default mode is `rollback_execution=dry_run_no_state_change`;
- output is metadata-only;
- secret values are never printed;
- product impact is always `measurement_gap_only`;
- normal product workflows must remain available.

The script records these switches for operators:

- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE=disabled`

`--execute` is intentionally guarded by
`TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE=1` so an operator cannot mutate
provider state by accidentally running the script from a local review shell.

## Metadata-Only Evidence

Allowed:

- command names;
- pass/fail status;
- redacted environment label;
- provider mode after rollback;
- product health status;
- dashboard caveat status.

Forbidden:

- secret values;
- raw event rows;
- live counter IDs or project keys;
- screenshots with account/visitor data;
- content-bearing provider exports.

## Operator Sequence

1. Confirm the rollback target and reason.
2. Run the rollback script in dry-run mode and record the metadata output.
3. Disable the relevant runtime flag or provider route only after operator
   approval.
4. Stop or detach the PostHog stack only when the rollback target includes the
   stack/domain path.
5. Run `infra/scripts/cd-remote.sh --dry-run` after runtime switch changes.
6. Run provider smoke in rollback mode.
7. Run page validation for browser surfaces when web-direct/Yandex/replay is
   involved.
8. Confirm GRAF health.
9. Record a metadata-only delivery gap and dashboard caveat.
10. Leave provider secrets out of logs and evidence.

## Move-Out Failure

If moving PostHog to a separate analytics server fails:

1. Keep GRAF product runtime on the current production server.
2. Restore the previous PostHog DNS/runtime endpoint or disable PostHog delivery.
3. Verify GRAF health and product flows.
4. Verify no provider secret or token entered logs/evidence.
5. Record measurement gap and move-out blocker.

## Restoration

Restoration after rollback requires:

- non-secret reason the blocker is closed;
- runtime config review;
- provider smoke pass;
- page validation pass when page providers are affected;
- dashboard caveat update;
- implementation evidence update.

Restoration does not approve paid campaign launch.
