# Contract: Cabinet Runtime State

## Purpose

Define the boundary between static cabinet configuration, embedded WebKit
navigation truth, native shell presentation, and web/desktop cabinet parity.

## State Inputs

The desktop shell may receive:

- a configured cabinet origin;
- an embedded navigation start;
- an HTTP main-frame response;
- a WebKit navigation failure;
- a finished allowed route;
- a blocked embedded route.

The shell must not treat configuration alone as a healthy state.

## HTTP And Navigation Mapping

Existing response mapping remains authoritative:

- `2xx` and `3xx`: allow navigation to continue, then classify by route kind at
  finish.
- `401`: `expiredSession`.
- `403`: `accessDenied`.
- `404`: `notFound`.
- `408` or `504`: `timeout`.
- `5xx`: `offline`.
- other unexpected main-frame responses: `malformedResponse`.

Navigation errors:

- timeout: `timeout`;
- other network errors: `offline`;
- expected app-driven navigation cancellations preserve the current state.

## Finished Route Mapping

When an allowed route finishes loading:

- meeting list route: `ready`;
- meeting detail route: `ready`;
- login route: `expiredSession`;
- sign-up route: `expiredSession`;
- unsupported/external/forbidden route: `blockedRoute`.

## Native Shell Presentation

The presentation must derive from `Cabinet Runtime State`:

- `ready`: success tone and "cabinet available" copy.
- `loading`: neutral tone and "checking" copy.
- `offline` or `timeout`: error tone and "server unavailable" copy.
- `expiredSession`: warning tone and "login required" copy.
- not configured: local-mode copy.

The native shell must preserve local recording and upload truth separately from
cabinet status.

## Web And Desktop Parity

The web cabinet and desktop embedded cabinet use the same server-owned review
routes. Runtime checks must cover:

- ready processed meeting;
- processing state;
- failed state;
- unavailable/no-audio/policy-blocked states;
- auth-required or missing session state.

Evidence may record state names, booleans, route classes, command outcomes, and
overflow counts. Evidence must not record raw audio, transcript text,
credentials, signed URLs, private local paths, or private meeting content.
