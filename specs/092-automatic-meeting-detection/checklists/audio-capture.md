# Audio Capture Checklist: 092 Automatic Meeting Detection

**Date**: 2026-07-08

## Capture Safety

- [x] Detector-assisted recording still uses existing local prerequisite gates.
- [x] Manual Record/Stop remains available whenever workspace policy permits.
- [x] Active detector-assisted recording requires persistent local visible state.
- [x] One-action Stop remains mandatory.
- [x] Unknown apps and diagnostic-only targets cannot prompt or auto-record.

## Native Detector

- [x] Native detector uses `AudioHAL` app ownership rather than process launch.
- [x] Start debounce is 5 seconds of stable `AudioHAL bundle ownership`.
- [x] End grace is 15 seconds after ownership removal.
- [x] Sub-5-second audio ownership observations become telemetry short tests rather than
  prompt triggers.
- [x] Parser/log stream failure degrades to manual recording with health evidence.

## Browser Detector

- [x] Browser audio ownership alone is weak and cannot prompt.
- [x] Browser detection requires browser metadata plus calendar/join intent or
  equivalent service-specific evidence.
- [x] Browser extensions are future optional adapters, not first-release
  requirements.

## Implementation Validation Requirements

- [x] Requirements specify synthetic parser fixtures for start, update, end,
  malformed, unknown, browser, and non-target events.
- [x] Requirements specify measured CPU, memory, disk, and network evidence for
  detector gates.
- [x] Requirements specify prompt/auto-record validation for visible indicator
  and one-action Stop before accepted capture.
