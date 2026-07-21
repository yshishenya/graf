# T101 production runtime guard receipt

Date: 2026-07-21 (Europe/Moscow)

This receipt is metadata-only. It contains no provider keys, OAuth material,
passwords, cookies, visitor identifiers, account details, raw events, exports,
screenshots, or content-bearing data.

## Applied production configuration

- The existing root-owned guard environment was updated atomically.
- `GRAF_POSTHOG_GUARD_AUTO_ROLLBACK=1`.
- `GRAF_POSTHOG_GUARD_DRY_RUN=0`.
- `GRAF_POSTHOG_GUARD_STOP_STACK=0`.
- The guard remains a measurement-only fail-closed path: a confirmed breach
  disables analytics delivery through the GRAF environment and does not stop
  the PostHog stack or GRAF services.
- The timer remains root-owned, mode `0600` protects its environment, and the
  timer is enabled and active.

## Verification

| Check | Result | Metadata-only result |
| --- | --- | --- |
| Guard environment | pass | The three reviewed values are `1`, `0`, and `0` respectively; file mode is `0600`, owner is `root:root`. |
| One-shot guard run | pass | `Result=success`, `ExecMainStatus=0`; `result=pass`, `containers=33`, `oom=0`, `restarts=0`, `health_failures=0`. |
| Timer | pass | `enabled` and `active`. |
| GRAF readiness | pass | `https://rec.2brain.pro/api/v1/health/ready` returned HTTP 200. |
| PostHog health | pass | `https://analytics.2brain.pro/_health/` returned HTTP 200. |
| Provider safety boundary | pass | Product analytics and PostHog delivery remain disabled; no provider rollout or campaign approval was made. |

No breach was simulated, no provider stack was stopped, and no user or
analytics data was changed.

## Remaining T101 blockers

This receipt closes the guard configuration subtask, not T101 as a whole.

- Self-hosted PostHog event retention is not enforced by the installed
  upstream code path; the current session-recording setting is `5y`, and the
  supported API rejected a narrower setting because this organization has no
  retention entitlement. No direct database override or custom ClickHouse TTL
  was applied.
- The live workspace still needs an independent RBAC/audit review. The current
  self-hosted UI exposes one owner/admin membership and does not expose the
  Cloud-only enforced-2FA control; no second operator or recovery path was
  invented.
- The existing dashboard is a generic starter dashboard. Freshness and
  approved activation-goal visibility still require an owner-approved goal
  definition and a real aggregate-only dashboard review.
- Full lifecycle/restore and persistent alert review remain separate T101
  gates; production provider flags stay fail-closed until those gates are
  complete.
