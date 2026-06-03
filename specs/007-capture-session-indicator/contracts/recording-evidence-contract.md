# Contract: Recording Evidence

## Purpose

Define metadata-only evidence required for manual recording lifecycle QA.

## Required Event Families

- `recording.start_requested`
- `recording.start_blocked`
- `recording.started`
- `recording.stop_requested`
- `recording.stopped`
- `recording.failed`
- `recording.indicator_lost`
- `recording.route_invalidated`
- `recording.storage_blocked`

## Required Safe Fields

- `sessionId`
- `eventType`
- `occurredAt`
- `initiator`
- `routeState`
- `indicatorState`
- `stopActionAvailable`
- `blockedReason`
- `recoveryAction`
- `durationMs` where applicable
- `diagnosticSafe`

## Forbidden Fields

Evidence and diagnostics MUST NOT include:

- raw audio;
- transcript text;
- meeting content;
- credentials;
- API keys;
- passwords;
- tokens;
- signed URLs;
- live secret paths;
- MediaScribe credentials or job payloads;
- Langfuse content traces.

## Acceptance

A closed recording session is evidence-complete only when:

- every `recording.started` event has `recording.stopped` or
  `recording.failed`;
- active recording evidence includes visible indicator state;
- stop evidence includes stop initiator and stop reason;
- redaction status is `redacted` or equivalent safe result;
- no upload/transcription/external egress field is present.
