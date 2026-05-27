# 2brain Rec macOS Audio Component

This directory owns the thin macOS audio component for the driver-first MVP.

## Scope

- Publish `2brain Rec Microphone` and `2brain Rec Speaker`.
- Preserve physical microphone passthrough to meeting targets.
- Receive virtual speaker output, pass it to the selected physical output, and mirror it for desktop capture.
- Emit timing, drift, dropout, route, and passthrough health signals.
- Avoid policy, upload, retention, purge, diagnostics packaging, or MediaScribe responsibilities.

## Phase 0 Proof Gate

Before user-story implementation, the proof harness must demonstrate that the selected macOS audio technology can:

- publish both MVP virtual devices on Apple Silicon macOS 14.5 and latest stable macOS at release-candidate time;
- block or reject self-routing;
- keep remote speaker audio out of the virtual microphone path;
- sustain live passthrough while the desktop app simulates backend/network unavailability;
- surface continuity signals for dropout and clock drift accounting.

The current planning decision favors a Core Audio virtual-device approach. AudioDriverKit remains a researched fallback only if the proof shows it better satisfies the MVP virtual-device shape and distribution constraints.

## Current Proof Status

Status: scaffolded, not yet proven against macOS Core Audio runtime.

Created proof harnesses:

- `Sources/Proof/VirtualDeviceProof.cpp`
- `Sources/Proof/PassthroughTimingProof.cpp`

The selected implementation path remains Core Audio virtual-device proof first.
No user-story driver implementation should proceed until this proof is replaced
with a working Apple Silicon validation result and this section records the
observed outcome.

## Signing And Distribution Prerequisites

- Apple Developer Program membership with Developer ID Application and Developer ID Installer certificates.
- Notarization access for the installer package and any signed helper/component artifacts.
- Local signing identities must stay outside the repository.
- Entitlements, provisioning profiles, generated packages, notarization tickets, logs, and credentials must not be committed.

## Real-Time Boundary

Code in this directory must stay small and predictable. It should not perform network calls, server upload, transcription, LLM calls, retention deletion, or diagnostic bundle packaging.
