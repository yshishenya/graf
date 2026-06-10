# Contract: Recording Timeline Evidence

## Purpose

Connect live route stability to final local recording artifact truth. This
contract makes route interruptions distinguishable from generic
`timeline_misaligned` failures.

## Required Manifest Evidence

```json
{
  "recordingSessionId": "uuid",
  "routeSessionId": "uuid",
  "micDurationSeconds": 4393.07,
  "incomingDurationSeconds": 4240.88,
  "durationDifferenceSeconds": 152.19,
  "alignmentBand": "failed",
  "routeInterruptionCategory": "incoming_route_stopped",
  "autorepairAttemptIds": ["uuid"],
  "countsAsCleanAcceptance": false,
  "diagnosticSafe": true
}
```

## Alignment Bands

- `accepted`: `durationDifferenceSeconds <= 3`
- `degraded_warning`: `durationDifferenceSeconds > 3` and `<= 10`
- `failed`: `durationDifferenceSeconds > 10`

## Route Interruption Categories

- `none`
- `incoming_route_stopped`
- `microphone_route_stopped`
- `both_routes_stopped`
- `coreaudiod_restart`
- `sleep_wake`
- `physical_device_change`
- `default_route_change`
- `browser_stream_recreated`
- `app_route_engine_restart`
- `unknown_route_gap`

## Acceptance Rules

- Stable accepted long-duration recording runs require `accepted` alignment.
- `degraded_warning` evidence is useful diagnostics but does not count as clean
  acceptance.
- `failed` evidence fails the feature timeline gate.
- Differences measured in tens of seconds or minutes are route-stability bugs
  unless a future accepted spec explicitly supersedes the cause.

## Privacy Rules

Evidence must not contain raw audio, transcript text, meeting content, or full
local user paths. It may contain directory id, manifest filename, session ids,
track role names, durations, and alignment bands.
