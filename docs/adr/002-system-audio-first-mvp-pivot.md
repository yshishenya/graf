# ADR 002: System-Audio-First MVP Capture Pivot

**Status**: Accepted

**Date**: 2026-06-08

## Context

`2brain Rec` started as a driver-first macOS MVP: meeting apps selected
`2brain Rec Microphone` and `2brain Rec Speaker`, while the desktop app owned a
Core Audio HAL route for local microphone and incoming speaker tracks.

Runtime validation of feature `019-live-route-stability` showed that this path
is not safe enough for MVP:

- live HAL publication attempts repeatedly drove `coreaudiod` into high CPU;
- runtime probes could hang CoreAudio enumeration;
- Telemost and the desktop UI could freeze while the audio route was being
  debugged;
- same-version local installer behavior made it easy to run stale app bundles;
- recording truth depended on the meeting app selecting the virtual speaker,
  so users could hear audio through physical speakers while `incoming.wav`
  stayed empty.

The product goal is reliable botless meeting capture, not proving a virtual
driver architecture at all costs. A meeting recorder that overheats or freezes
the Mac cannot be accepted as an MVP trust surface.

## Decision

Pivot the MVP capture strategy to system-audio-first:

1. Capture incoming/remote audio through native macOS Screen/System Audio
   capture APIs.
2. Capture the local microphone through explicit microphone capture APIs.
3. Persist separate `mic.wav` and `incoming.wav` tracks with truthful
   alignment/degraded metadata.
4. Keep visible local recording state and one-action stop as non-negotiable.
5. Keep the HAL virtual driver out of the MVP acceptance path.
6. Treat virtual-device routing as a future advanced routing slice that must
   pass separate CoreAudio safety, installer, rollback, and long-duration
   validation before it can become product behavior.

## Consequences

### Positive

- No meeting app needs to select `2brain Rec Speaker` for incoming recording.
- The app no longer needs to publish virtual CoreAudio devices for the MVP.
- The MVP avoids the current CoreAudio CPU runaway and HAL enumeration hang
  class of failures.
- Recording acceptance can focus on actual saved dual-track artifacts,
  permissions, visible capture state, and track alignment.
- The installer becomes simpler because the driver is not required for MVP
  operation.

### Tradeoffs

- `2brain Rec` no longer behaves like a Krisp-style virtual microphone/speaker
  in the MVP.
- Live passthrough/routing and in-meeting audio processing move out of scope.
- Meeting mute truth must be handled carefully because system audio and
  microphone capture do not automatically mean "what the meeting app sent".
- Screen/System Audio permission becomes part of onboarding and validation.
- Some conferencing apps or DRM-protected content may block, mute, or degrade
  system audio capture; this must be represented truthfully.

## MVP Acceptance Rule

The MVP is accepted only if a normal user can:

- grant microphone and screen/system-audio permissions;
- press Record;
- see an always-visible local recording indicator and Stop control;
- record a controlled meeting without selecting virtual devices;
- get `mic.wav`, `incoming.wav`, and `manifest.json`;
- see truthful degraded/blocked states when permissions or audio sources are
  unavailable;
- stop recording in one action;
- leave the Mac in a low-CPU state after recording and after app quit.

## Non-Goals

- Do not remove driver code as part of the pivot decision itself.
- Do not claim driver-based live routing is fixed.
- Do not start upload, MediaScribe, Langfuse, backend ingest, or external
  egress as part of this pivot.
- Do not auto-record arbitrary system audio without an explicit user-visible
  capture state and policy gate.

## Required Follow-Up

- Create feature spec `022-system-audio-capture-pivot`.
- Update PRD/current status to stop presenting driver-first as the MVP path.
- Add contracts for permission truth, system-audio capture sessions, local
  dual-track writer behavior, and degraded recording manifests.
- Add validation gates for CPU, app responsiveness, permission prompts,
  recording artifacts, and no driver/HAL dependency.
- Keep GitHub issue #234 open as driver advanced-routing work, not an MVP
  blocker after the pivot is accepted.
