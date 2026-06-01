# Contract: Low-Resource Validation Evidence

## Purpose

Define the metadata-only evidence required before low-resource mode may become
the local default.

## Evidence Bundle

Each validation run records:

```json
{
  "run_id": "local-2026-06-01-001",
  "feature": "006-low-resource-audio",
  "baseline": "005-macos-passthrough-release-hardening",
  "result": "passed|blocked|not_accepted",
  "route_truth": [],
  "startup_attempts": [],
  "realtime_safety": {},
  "runtime_probe": {},
  "no_hang": [],
  "cpu": {},
  "browser_meeting_smoke": [],
  "recovery": [],
  "fallback": {}
}
```

Evidence values must be metadata-only. Raw audio, transcripts, meeting content,
credentials, tokens, signed URLs, passwords, and live secret paths are forbidden.

## Required Gates

| Gate | Pass Condition |
|------|----------------|
| Runtime publication | `2brain Rec Microphone` and `2brain Rec Speaker` visible/alive; hidden=0; idle running state is safe. |
| Automatic activation | Browser/meeting client can activate passthrough without `Run Check`. |
| Recording boundary | Driver creates no recordings, transcripts, uploads, jobs, MediaScribe requests, or Langfuse traces. |
| Startup timeout | Every startup attempt resolves within 3000 ms. |
| No-hang surfaces | macOS Sound settings, Chrome, Opera, Zoom, and Telemost surfaces open within 5 seconds or record blocked failure. |
| CPU | `coreaudiod` idle/no-call CPU does not sustain above 10% for more than 30 consecutive seconds. |
| Silent stream | Silent-but-open stream remains active until explicit IO closes. |
| Self-routing | 2brain virtual devices are rejected as physical working devices. |
| Chained device policy | Other virtual/aggregate/multi-output devices are unsupported/not release-ready unless accepted later. |
| Realtime safety | Static/manual validation finds no forbidden operations in HAL callback paths. |
| Recovery | `coreaudiod` restart, sleep/wake, and physical device changes clear ready state within 5 seconds and recover only with valid evidence. |
| Fallback | Accepted 005 lifecycle can be restored without reinstalling the HAL driver. |

## Promotion Rule

Low-resource mode becomes the local default only when every P1 gate passes in the
same validation run or in a documented equivalent run set with no open P1
regressions.

If any P1 gate fails:

- low-resource mode remains blocked/not accepted;
- the accepted 005 app-launch lifecycle remains or is restored as default;
- the failure is recorded with metadata-only reason and remediation target.

## Redaction Rule

Validation artifacts must pass diagnostics redaction and secret-pattern scans.
Deliberate policy/fixture strings may remain only when clearly marked as policy
or fixture text.
