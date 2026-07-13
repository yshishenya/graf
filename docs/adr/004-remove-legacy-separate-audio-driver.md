# ADR 004: Remove The Legacy Separate Audio-Routing Implementation

**Status**: Accepted

**Date**: 2026-07-13

## Context

ADR 002 moved MVP recording to native macOS system-audio capture after the
earlier separate routing experiment showed unsafe CPU, enumeration, and
recording-truth failure modes. The experimental source, shared-memory bridge,
packaging branches, lifecycle scripts, runtime state, QA, and UI remained in
the repository as parked code.

Keeping two architectures created an ongoing risk: an obsolete path could be
rebuilt, packaged, or reintroduced as a fallback even though accepted recording
already uses ScreenCaptureKit plus app-owned microphone capture.

## Decision

Remove the former separate audio-routing implementation from active source,
SwiftPM dependencies, application composition, installer/uninstaller behavior,
tests, validators, QA, and active product documentation.

The supported recording graph is:

```text
SystemAudioCaptureService -> BufferedLocalRecordingSampleSource
MicrophoneCaptureService -> app-owned microphone sample source
both explicit sources -> LocalRecordingWriter
LocalRecordingWriter -> mic.wav + incoming.wav + manifest.json
```

The following invariants remain mandatory:

- manual start/stop;
- persistent local capture indication and one-action stop;
- microphone and Screen & System Audio Recording permission truth;
- two original tracks with truthful finalization/degradation state;
- metadata-only diagnostics;
- generic fail-closed microphone-input eligibility;
- backward reads for existing recording roots and historical manifest fields.

Generic Core Audio use for physical microphone discovery and metadata-only
meeting-app ownership remains part of the current product. It is not the
removed implementation.

## Consequences

- SwiftPM and packaging produce no separate audio component.
- Normal build, test, install, and uninstall paths perform no privileged audio
  mutation or Core Audio service restart.
- Historical proof/failure material remains audit evidence under
  `docs/evidence/legacy-audio-driver/` and completed feature specs.
- An already installed proof component is host state, not repository state. Its
  removal is a deliberate operator action governed by
  `docs/agent-guidance/legacy-audio-driver-cleanup.md`.
- Any future advanced routing starts from a new approved Spec Kit slice,
  architecture, safety case, packaging design, and rollback plan. The removed
  implementation is not a dormant feature flag or fallback.

## Validation

- Current capture/writer/permission/package tests must pass before and after
  removal.
- A repository guard rejects retired paths, symbols, payloads, lifecycle
  commands, and active documentation claims.
- Installer expansion must show exactly one application component.
- Full local CI remains required.
