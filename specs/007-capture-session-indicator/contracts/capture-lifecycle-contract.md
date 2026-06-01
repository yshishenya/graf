# Contract: Capture Lifecycle

## Purpose

Define the allowed manual recording lifecycle for feature
`007-capture-session-indicator`.

## Start Contract

Input:

- explicit user action: `manual_record_start`;
- current route evidence;
- recording prerequisite snapshot;
- visible indicator availability;
- local storage/buffer risk;
- source app eligibility.

Allowed start result:

- `started`: recording entered `active` with visible indicator and one-action
  stop;
- `blocked`: recording did not start and a concrete blocker/recovery action is
  available;
- `failed`: recording did not start or immediately failed closed.

Start MUST NOT:

- start from publication-only route evidence;
- start upload, transcription, MediaScribe, Langfuse, dashboard publication, or
  external egress;
- start if no visible local indicator can be shown.

## Stop Contract

Input:

- explicit user action from a visible local surface, or system fail-closed
  trigger when safety is lost.

Allowed stop result:

- `stopping` within one interaction;
- `stopped` within 1 second in local validation when no finalization blocker is
  present;
- `failed` with failure evidence if stop cannot complete normally.

Stop MUST:

- make active recording cease or fail closed;
- record metadata-only stop evidence;
- leave non-recording passthrough allowed when the route remains valid.

## Fail-Closed Triggers

Recording MUST stop or fail closed when:

- all visible indicator surfaces are unavailable;
- app bridge/heartbeat loss makes the active route unsafe;
- `coreaudiod` restart invalidates route evidence;
- storage reserve becomes unsafe;
- route becomes stale, blocked, failed, or unknown.
