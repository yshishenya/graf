# GRAF macOS Architecture

This directory contains the macOS system-audio-first product. The retired
separate audio-routing implementation is not a build target, runtime option, or
installer component.

## Supported Recording Flow

```text
SystemAudioCaptureService (ScreenCaptureKit)
  -> BufferedLocalRecordingSampleSource
  -> LocalRecordingWriter incoming source

MicrophoneCaptureService (app-owned microphone capture)
  -> LocalRecordingWriter microphone source

LocalRecordingWriter
  -> mic.wav
  -> incoming.wav
  -> manifest.json
```

Both sources are created by the app and explicitly injected into
`LocalRecordingWriter`. There is no implicit incoming-audio fallback.

Recording readiness requires:

- workspace recording policy;
- microphone permission;
- Screen & System Audio Recording permission;
- available storage;
- a persistent visible capture indicator;
- an eligible microphone input and available system-audio source.

Manual `Record`/`Stop`, persistent visible capture state, one-action stop,
dual original tracks, truthful degraded/failure state, and metadata-only
diagnostics are release-critical.

Generic Core Audio APIs remain where the current product needs physical
microphone discovery or metadata-only meeting-app ownership signals. The
`AudioHAL` unified-log name used by meeting detection is an operating-system
log category, not a packaged plug-in. Metadata-only `coreaudiod` CPU sampling
is an observation gate and must not restart or mutate the service.

## Package Layout

`Package.swift` builds Swift libraries, the desktop app, validation tools, and
tests. It has no C shared-memory target and no separate audio component.

The local installer builds one application component:

```sh
GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
  apps/macos/Installer/Scripts/build-local-installer.sh
```

The default build, test, packaging, and uninstall paths do not install or
remove privileged audio components and do not restart Core Audio services.

## Recording Compatibility

- New recordings use the current GRAF application-support directory.
- Existing recordings under the former application-support directory remain
  readable.
- Historical manifest fields that are unknown to the current decoder are
  ignored.
- The retired `hal_probe_observed` failure value maps to the current
  fail-closed `legacy_not_ready` state and cannot become uploadable.
- The persisted `legacy_recorder_fallback` source-mode raw value remains
  decodable for existing artifacts; current recordings do not emit it.

## Validation

```sh
swift build --package-path apps/macos
swift test --package-path apps/macos
swift run --package-path apps/macos ContractValidation
sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh
sh apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata
sh apps/macos/Scripts/validate-foundation.sh
```

Current release QA is in `qa/macos/release-candidate-checklist.md`.

## Historical Evidence And Existing Local Proof Installs

Historical failure/proof evidence is retained under
`docs/evidence/legacy-audio-driver/` for audit only. It is not executable
guidance.

Removing repository source does not remove a component previously installed on
a developer Mac. Read
`docs/agent-guidance/legacy-audio-driver-cleanup.md` before any deliberate
host cleanup. Normal build and validation commands never perform that cleanup.
