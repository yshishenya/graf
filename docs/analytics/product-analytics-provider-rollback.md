# Product Analytics Provider Rollback

Feature: `096-product-analytics-provider-rollout`

Status: `metadata_only_not_executed`

This rollback runbook is safe to commit. It contains no live provider IDs,
tokens, cookies, visitor identifiers, payload rows, screenshots, meeting
content, transcript text, audio, signed URLs, or private local paths.

## Product Impact Rule

Rollback reduces measurement. It must not break normal GRAF product workflows.

The order is fixed by FR-032: measurement is switched off first, the product
keeps serving. The guard may only disable the measurement scope, and only
analytics-scope reasons may trigger an automatic rollback, so a site traffic
spike cannot switch measurement off by itself.

Rollback must preserve:

- login/signup;
- cabinet navigation;
- recording/upload/review flows;
- deletion/export/account/legal flows;
- telemetry gate truth.

A rehearsed rollback is the evidence FR-045 asks for; what counts as rehearsal
evidence, and which steps still need an operator, is in
`product-analytics-launch-approval.md`.

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

Metadata-only command (the only mode used by smoke and tests):

```sh
infra/scripts/rollback-product-analytics-providers.sh --metadata-only --target all
```

The script is safe by default and fail-closed:

- default mode is `rollback_execution=metadata_only_no_state_change`;
- `--dry-run` remains a compatibility alias for `--metadata-only`;
- output is metadata-only and never changes provider state;
- secret values are never printed;
- product impact is always `measurement_gap_only`;
- normal product workflows must remain available.

`--execute` does not itself implement a provider rollback. It is an explicit
operator boundary and exits nonzero unless both
`TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE=1` and an absolute executable
`TWOBRAIN_PROVIDER_ROLLBACK_EXECUTOR_HOOK` are configured. Only that operator
hook may perform live provider mutation; the script passes `--target <target>`
to it, suppresses hook output, and blocks on a missing or failed hook. Tests and
smoke never configure or invoke this hook, so they cannot mutate a live provider.

The script records these switches for operators:

- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE=disabled`


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
2. Run the metadata-only command and record its output:
   `infra/scripts/rollback-product-analytics-providers.sh --metadata-only --target all`.
3. Obtain the separate operator approval and configure the operator-owned
   executor hook; never treat metadata-only output as live evidence.
4. If a live rollback is approved, run `--execute` with both explicit approval
   and the absolute executable hook. A missing or failed hook is a blocker.
5. Stop or detach the PostHog stack only when the operator hook's target includes
   the stack/domain path.
6. Run `infra/scripts/cd-remote.sh --dry-run` after runtime switch changes.
7. Run provider smoke in rollback mode.
8. Run page validation for browser surfaces when web-direct/Yandex/replay is
   involved.
9. Confirm GRAF health.
10. Record a metadata-only delivery gap and dashboard caveat.
11. Leave provider secrets out of logs and evidence.

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

Restoration does not approve paid campaign launch. The launch gate is computed
from the approval records, not from the rollback state
(`product-analytics-launch-approval.md`).
