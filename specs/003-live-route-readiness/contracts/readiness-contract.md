# Contract: Live Route Readiness

## Purpose

Define the user-visible readiness contract for moving from `not ready for calls
yet` to `ready`.

## Inputs

- selected physical microphone
- selected physical output
- current public virtual device state
- private app I/O heartbeat state
- microphone path evidence
- speaker path evidence
- latency and leakage measurements when available

## State Contract

| State | Meaning | Allowed User Claim |
|---|---|---|
| `not_started` | No live route check has run | Not ready |
| `checking` | User-triggered check is in progress | Not ready |
| `ready` | Mic and speaker path evidence both pass | Ready for calls |
| `stale` | Prior evidence invalidated by route/browser/device change | Recheck required |
| `degraded` | Route works but violates latency/leakage/profile policy | Not release-ready |
| `failed` | Required path is missing, self-routed, or unproven | Not ready |

## Invariants

- Publication-only evidence must never produce `ready`.
- `ready` requires both microphone and speaker path evidence.
- Readiness checks must not start recording.
- App I/O loss must invalidate ready within 5 seconds.
- Diagnostics must not include raw audio, transcript text, credentials, tokens,
  or signed URLs.
