# Contract: Driver/App Handoff

## Purpose

Define the realtime-safe handoff between the HAL driver and the desktop app
bridge for low-resource non-recording passthrough.

## Ownership

| Component | Owns | Must Not Own |
|-----------|------|--------------|
| HAL driver | virtual device publication, explicit client IO state, shared-buffer reads/writes, fail-closed zero/drop behavior | recording, transcription, physical device orchestration, UI, network, diagnostics formatting |
| App route engine | physical working device selection, bounded startup, heartbeat, recovery, diagnostics, fallback | HAL callback execution, driver-owned recording |
| Future recording layer | recording/transcription trigger and visible capture state | driver publication or Core Audio callback safety |

## Shared State

The app/driver boundary may use existing POSIX shared memory and atomically
readable fields:

- microphone buffer and indices;
- speaker buffer and indices;
- capture mirror buffer and indices;
- app bridge state;
- app heartbeat or precomputed freshness state;
- drop/zero counters;
- client running counters exposed through Core Audio properties.

## Realtime Safety

HAL callback-sensitive paths must not perform:

- file IO or trace writes;
- string formatting/logging;
- heap allocation;
- lock waits;
- blocking IPC;
- wall-clock/timezone/date calls;
- process launches;
- network calls;
- UI work;
- synchronous app/process health checks.

Allowed callback-path behavior:

- atomic loads/stores;
- bounded ring-buffer reads/writes;
- `memset` zero-fill/drop fail-closed behavior;
- fixed-size arithmetic and counters;
- host-time calculations required by Core Audio timestamp contracts.

## Fail-Closed Rules

- If app bridge health is missing, stale, or unavailable, microphone reads must
  zero-fill and speaker writes may drop without blocking.
- Fail-closed behavior must never imply that recording has started.
- Fail-closed behavior must preserve Core Audio client responsiveness.

## Startup Boundary

- Physical AudioUnit setup, Core Audio enumeration, and physical device binding
  happen outside HAL callbacks.
- Startup orchestration must be bounded to 3000 ms and may return
  `blocked`/`failed`/`fallback` instead of waiting.
- Startup must not run through an unbounded UI/main-thread path.

## Diagnostics Boundary

- Diagnostics may read metadata-only counters and state snapshots outside
  realtime callback paths.
- Diagnostics must not contain raw audio, transcript text, meeting content,
  credentials, tokens, signed URLs, passwords, or live secret paths.

## Fallback Boundary

- If low-resource startup or realtime-safety gates fail, the app must be able to
  restore the accepted 005 app-launch route lifecycle without reinstalling the
  HAL driver.
