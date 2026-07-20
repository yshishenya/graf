# Contract: Rollback Plan

**Feature**: `096-product-analytics-provider-rollout`

Rollback must reduce measurement, not product availability.

## Rollback Targets

| Target | Disable Method | Verification |
| --- | --- | --- |
| PostHog server delivery | runtime provider mode/enable flag | provider smoke shows disabled or measurement gap |
| PostHog web-direct delivery | rendered config flag or snippet removal | page validation shows no delivery route |
| PostHog desktop-direct delivery | desktop runtime flag | Swift/config smoke shows route disabled |
| PostHog autocapture | runtime autocapture flag | page validation shows autocapture disabled |
| PostHog session replay | replay flag/provider setting | page validation shows replay disabled |
| PostHog stack | stop analytics stack or remove routing | GRAF health remains ready |
| PostHog deploy handoff | remove PostHog stack from deploy dry-run or mark blocked | `cd-remote.sh --dry-run` reports no PostHog execution path |
| Yandex all-pages expansion | runtime all-pages flag | blocked pages render no Yandex collection |
| Yandex offline upload | runtime offline flag or secret removal | uploader reports disabled |
| Yandex Webvisor/maps/forms | provider/page-class setting | inventory/evidence records unavailable |
| Provider validation mode | runtime validation mode | smoke reports disabled |

## Rollback Evidence

Allowed evidence:

- command names;
- pass/fail status;
- redacted environment name;
- provider mode after rollback;
- product health status;
- dashboard caveat added.

Forbidden evidence:

- secret values;
- raw event rows;
- live counter/project keys;
- private screenshots;
- content-bearing provider exports.

## Product Impact Rule

Rollback must preserve:

- login/signup;
- cabinet navigation;
- recording/upload/review flows;
- deletion/export/account/legal flows;
- telemetry gate truth.

Allowed product-facing impact:

- analytics measurement gap;
- dashboard caveat;
- provider delivery gap.

Rollback must not claim deletion of provider-held aggregates, provider backups,
dashboard exports, or already uploaded offline conversions unless the specific
provider operation was verified and recorded as metadata-only evidence.

## Move-Out Rollback

If moving PostHog to a separate analytics server fails:

1. Keep GRAF product runtime on the existing production server.
2. Restore previous PostHog DNS/runtime endpoint or disable PostHog delivery.
3. Verify GRAF health and product flows.
4. Verify no provider secret or token entered logs/evidence.
5. Record measurement gap and move-out blocker.
