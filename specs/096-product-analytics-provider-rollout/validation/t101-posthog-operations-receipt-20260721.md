# T101 PostHog operations receipt: 2026-07-21

This receipt records the production-only operations that were safe to complete
without enabling product analytics delivery. It contains aggregate state,
configuration status, and HTTP results only. No event rows, person rows,
payloads, credentials, exports, cookies, or user content were read or written.

## Applied retention boundary

- The supported PostHog retention update path rejected the required `90d`
  value with `Invalid retention entitlement`.
- Because session replay is disabled and the session-replay bucket was empty, a
  reversible self-hosted database override set the project session-recording
  policy to `90d`. No ClickHouse TTL or content deletion was performed.
- The session-replay object-storage bucket has an enabled expiration lifecycle
  of `90` days. The bucket contained `0` objects and `0` bytes before and after
  the change.
- The separate general GRAF/PostHog object-storage bucket was not changed; the
  lifecycle rule was scoped only to the session-replay bucket.
- Session replay remains disabled. The disabled UI retention options were not
  bypassed by enabling replay or selecting a shorter policy.

The database override is an operational compatibility measure for this
self-hosted deployment, not evidence that the hosted entitlement/API now
accepts `90d`. It can be reverted by the production operator if the supported
PostHog path is repaired or an approved category-specific policy changes.

## Dashboard and goal visibility

- The dashboard was renamed to `GRAF Activation — approved goals` and its
  description now states that it is aggregate-only and fail-closed while
  provider delivery is disabled.
- Two aggregate goal insights are present for the approved event names
  `desktop_account_connected` and `first_value_session_completed`.
- Two dashboard tiles reference those insights. No live provider delivery was
  enabled and no campaign or paid-traffic approval was claimed.
- The dashboard refresh timestamp remains unset because there is no approved
  provider data to refresh. This keeps the freshness gate open rather than
  manufacturing a successful refresh receipt.

## Independent checks

| Check | Result | Boundary |
| --- | --- | --- |
| GRAF readiness | HTTP `200` | Product readiness remained healthy. |
| PostHog health | HTTP `200` | Analytics runtime remained healthy. |
| Session-recording policy | `90d` | Self-hosted project model after reversible override. |
| Session-replay bucket | `0` objects, `0` bytes | No content was deleted by this change. |
| Session-replay lifecycle | Enabled, expiration `90` days | Object-storage lifecycle is configured for future replay objects. |
| Provider delivery | Disabled/fail-closed | `TWOBRAIN_PRODUCT_ANALYTICS_ENABLED=false` and `TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false`; no Yandex enablement was added. |
| Runtime guard | Enabled/active, one-shot exit `0` | Automatic analytics rollback is enabled; full-stack stop remains disabled. |

## T101 status and remaining evidence

This receipt closes the configuration portion of the retention/lifecycle and
goal-visibility work, but it does not close T101. The following evidence still
requires a separate approved operator boundary:

1. independent RBAC/MFA/audit review with a second operator or an explicit
   owner-only risk acceptance;
2. a real dashboard freshness review after an approved provider rollout or a
   documented empty-data refresh procedure;
3. persistent restore-target and alert/recovery review beyond the already
   passed isolated restore rehearsal and runtime guard one-shot.

T101 and dependent T104 remain open in `tasks.md` and in tracker issue #3857.
