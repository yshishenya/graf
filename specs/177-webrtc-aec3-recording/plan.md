# Implementation Plan: WebRTC AEC3 Recording

**Branch**: `177-webrtc-aec3-recording` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/177-webrtc-aec3-recording/spec.md`

## Summary

Remove the acoustic copy of system playback from the microphone before GRAF's
existing canonical mix. Integrate pinned `webrtc-audio-processing` v2.1
(`846fe90a289f58b7c9303a635142aa2c7caa93e5`) through one narrow C ABI and a
checked-in static universal XCFramework. `RecordingAudioTimeline` remains the
single timeline owner: after PTS alignment and 48 kHz mono conversion it feeds
each 480-sample system block to AEC3, then the matching microphone block, and
uses the cleaned microphone in the unchanged `0.5 * (microphone + system)` mix.
There is no raw-microphone fallback and no second recording path.

## Technical Context

**Language/Version**: Swift 6 package mode; C++17 bridge compiled with Apple Clang

**Primary Dependencies**: ScreenCaptureKit, AVFoundation, existing SwiftPM package; pinned `webrtc-audio-processing` v2.1/WebRTC M131 and its pinned Abseil `20240722.0` build fallback

**Storage**: Existing local recording package: optional backward-compatible manifest fields, one canonical WAV, one review M4A

**Testing**: Swift Testing/XCTest through `swift test`; C ABI smoke; deterministic synthetic audio harness; packaging/linkage validators; controlled hardware listening and level measurements

**Risk / Validation Lane**: `high-risk-feature` because the change owns microphone integrity, capture discontinuities, diagnostics, native packaging, and failure behavior

**Release Gate**: No deploy or public release in this slice. Local build/test and ad-hoc installer evidence only; Developer ID/notarization remains a separate authorized release action.

**Target Platform**: macOS 14.0+ Swift package and the existing universal arm64/x86_64 shipped app contract on macOS 14.5+

**Project Type**: Native macOS desktop application with a small statically linked C++ audio-processing component

**Performance Goals**: Serial real-time processing of every 10 ms frame without unbounded buffering; p95 AEC processing time below 10 ms on supported hardware; exact output sample count; 60-minute alignment within 100 ms

**Constraints**: 48 kHz mono float, exactly 480 samples per AEC call; system reference processed before the matching microphone frame; system component unchanged; AEC only with HPF, NS, AGC, transient suppression, VAD and gates disabled; no raw audio in diagnostics/evidence; no Homebrew runtime dependency

**Scale/Scope**: One production mic+system capture path, one canonical mix, one manifest extension, one vendored static artifact, historical v3/v4 package reading preserved

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- **Capture-first integrity — PASS**: the design reuses native producers and the
  existing PTS-aligned canonical timeline. AEC failure, missing reference,
  route change, non-finite input, overflow, or unacceptable discontinuity fails
  closed and cannot release raw microphone as cleaned audio.
- **Visible control — PASS**: Record, persistent recording indication,
  Pause/Resume, one-action Stop, target-scoped auto-record and its countdown are
  unchanged. A degraded recording remains stoppable.
- **Data and secret boundary — PASS**: processing is entirely local and adds no
  network egress or credentials. Diagnostics and committed evidence contain
  bounded metadata only; WebRTC AecDump is prohibited.
- **Deletion truth — PASS**: the feature adds no user-visible artifact or new
  retention destination. Optional health metadata follows the existing package
  lifecycle.
- **Distribution integrity — PASS**: the dependency is statically linked into
  the existing executable. No nested dylib, rpath, entitlement, or signing
  exception is introduced. Required notices are bundled and final release
  remains gated by the existing Developer ID/notarization flow.
- **Spec-driven delivery — PASS**: clarify, plan, capture checklist, tasks,
  analyze and implementation gates are required before code completion.
- **No removed routing revival — PASS**: Features 038/039/106 runtime is not
  restored. Their metadata-only validation lessons may be reused, while the
  current system-audio-first pipeline remains authoritative.

### Post-design re-check

The Phase 1 contracts explicitly define frame ordering, discontinuity, prefix
retention, optional manifest compatibility and metadata-only diagnostics. No
constitution exception or complexity waiver is required.

## Validation Plan

1. Run the checked-in artifact validator and C ABI smoke for both architecture
   slices; prove no WebRTC/Abseil dylib load command exists.
2. Run focused Swift tests for framing partitions, ordering, exact sample count,
   fail-closed states, pause/resume, route changes, package shape and legacy
   manifest decoding.
3. Run the deterministic synthetic matrix in [quickstart.md](quickstart.md):
   far-end only, near-end only, double-talk, jitter, gaps, saturation, delay
   drift/jumps and a 60-minute clock-drift case.
4. Build the local universal installer and inspect architecture, linkage,
   signature structure, bundled notices and package surface.
5. Run `infra/scripts/ci-local.sh --fast` as the repository gate.
6. Execute the controlled real-hardware matrix on built-in speakers,
   headphones and route changes. Keep raw measurement material outside the
   repository and user recording packages; commit only bounded metrics.
7. Full CI, Developer ID, notarization, stapling, Gatekeeper and live update
   checks are deferred until an explicitly authorized release candidate.

## Project Structure

### Documentation (this feature)

```text
specs/177-webrtc-aec3-recording/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── aec-processing.md
│   └── recording-integrity.md
├── checklists/
│   ├── requirements.md
│   └── audio-capture.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── Native/GrafAEC3/
│   ├── Sources/GrafAEC3.cpp
│   ├── include/GrafAEC3.h
│   ├── include/module.modulemap
│   └── upstream.lock
├── Vendor/GrafAEC3.xcframework/
├── Scripts/
│   ├── build-graf-aec3-xcframework.sh
│   └── validate-graf-aec3-artifact.sh
├── RecApp/Sources/Capture/
│   ├── RecordingAudioTimeline.swift
│   ├── RecordingSampleSources.swift
│   ├── SystemAudioCaptureService.swift
│   └── V5LocalRecordingWriter.swift
├── Shared/Sources/Models/
├── Shared/Tests/
└── Package.swift

docs/
qa/macos/
```

**Structure Decision**: Keep all runtime behavior in the existing macOS package
and integrate at the one point where microphone and system audio already share
a canonical PTS timeline. The C++ boundary owns only one AEC3 instance; Swift
owns framing, state, package integrity and UI truth. The vendored artifact is
reproducible from a pinned lock and build script, but end users receive only the
statically linked app.

## Complexity Tracking

No constitution violations require justification.
