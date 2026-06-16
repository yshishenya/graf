# Desktop Native Shell Contract

## Purpose

Define what remains native and authoritative while the web-owned cabinet is
embedded.

## Native-Owned Surfaces

The macOS shell owns:

- active recording indicator;
- one-action Stop;
- manual Record;
- local permission recovery;
- local recording package truth;
- local upload queue truth;
- local diagnostics and logs;
- driver/system-audio recovery;
- app-level offline/unavailable state.

The embedded cabinet may be visible next to or below these surfaces, but it
must never replace them or require them to load.

## Required Layout Invariants

- During active recording, Stop remains visible outside the embedded content.
- When idle, manual Record remains native and available according to existing
  prerequisite gates.
- Upload queue truth remains native and visible when there are active,
  failed, blocked, or uploaded items.
- The embedded surface may scroll internally, but it cannot create a focus trap
  that prevents keyboard access to native Stop.
- Native shell copy uses user-facing product terms, not implementation labels
  such as WebView, API, route, or server-owned.

## Unavailable State Behavior

When the embedded cabinet is not configured, offline, denied, expired,
malformed, or timed out:

- local recording controls remain unchanged;
- upload truth remains unchanged;
- no foreign meeting content is confirmed;
- the unavailable message is bounded and recoverable;
- no local paths, tokens, signed URLs, raw audio, or transcript text are shown.

## Acceptance

- Tests prove active capture keeps native Stop outside embedded content.
- Tests prove route policy cannot execute native/capture controls through the
  embedded cabinet.
- Screenshots prove the default workspace is meetings-first while keeping
  native capture/upload status visible.
