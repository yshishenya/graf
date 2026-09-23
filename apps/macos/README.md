# GRAF macOS Architecture

> Проверки разработки выполняются только в `/Applications/GRAF Dev.app` через
> `infra/scripts/dev-harness.sh`: [инструкция](/docs/agent-guidance/local-development.md).
> Команды Installer ниже предназначены для подготовки и проверки релизных
> артефактов; они не заменяют Dev-стенд и не разрешают устанавливать ещё одну
> тестовую копию приложения.

This directory contains the macOS system-audio-first product. The retired
separate audio-routing implementation is not a build target, runtime option, or
installer component.

## Supported Recording Flow

```text
SystemAudioCaptureService (ScreenCaptureKit)
  -> PTS-bearing RecordingAudioBatch

MicrophoneCaptureService (app-owned microphone capture)
  -> PTS-bearing RecordingAudioBatch

LocalRecordingWriter (v5 implementation) + RecordingAudioTimeline
  -> GrafAEC3 (system reference, then matching microphone frame)
  -> CanonicalRecordingWriter
  -> meeting-transcription.wav (PCM s16le, mono, 16 kHz, ASR only)
  -> meeting-review.m4a (AAC-LC, mono, 48 kHz, playback only)
  -> manifest.json
```

Both sources are created by the app and explicitly injected as timestamped
batches. The timeline, rather than FIFO position or wall-clock padding, aligns
them, processes exact 10 ms pairs through mandatory WebRTC AEC3, and fails
closed on a missing reference, untrustworthy clock, route change, processor
failure or overflow. New recording has no raw-microphone fallback, dual WAV
output or text merge.

Recording readiness requires:

- workspace recording policy;
- microphone permission;
- Screen & System Audio Recording permission;
- available storage;
- a persistent visible capture indicator;
- an eligible microphone input and available system-audio source.

Manual Record/Stop, persistent visible capture state, one-action stop, one
shared canonical timeline, truthful degraded/failure state, and metadata-only
diagnostics are release-critical.

Generic Core Audio APIs remain where the current product needs physical
microphone discovery or metadata-only meeting-app ownership signals. The
`AudioHAL` unified-log name used by meeting detection is an operating-system
log category, not a packaged plug-in. Metadata-only `coreaudiod` CPU sampling
is an observation gate and must not restart or mutate the service.

## Package Layout

`Package.swift` builds Swift libraries, the desktop app, validation tools,
tests, and the vendored static universal `GrafAEC3.xcframework`. The app ships
no WebRTC/Abseil dylib and requires no runtime package manager.

The local installer builds one application component:

```sh
GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
  apps/macos/Installer/Scripts/build-local-installer.sh
```

The resulting `graf.pkg` is one universal installer. The app binary contains
both `arm64` and `x86_64` slices and supports macOS 14.5 or newer on Apple
Silicon and Intel Macs. The public download page offers this same package via
one link.

The default build, test, packaging, and uninstall paths do not install or
remove privileged audio components and do not restart Core Audio services.

## Recording Compatibility

- New recordings use the current GRAF application-support directory.
- Existing recordings under the former application-support directory remain
  readable.
- Historical v3/v4 manifests and queue documents v1/v2/v3 remain readable
  for local playback, existing server status and deletion. Their original
  paths, identities and deletion operations are retained; no automatic
  conversion or file removal occurs.
- Only a complete v5 package can be uploaded: manifest, canonical transcription
  WAV and review M4A. Old mic/incoming packages are blocked before meeting or
  upload-session creation and cannot be retried manually. Queue loading, scans,
  scheduling and in-flight callbacks enforce the same restriction, including
  entries with a previously saved uploadable flag or server identity.
- Historical role values remain in decoding and byte accounting only. They
  do not create upload descriptors or change the current capture/AEC pipeline.

## Validation

```sh
swift build --package-path apps/macos -j 4
swift test --package-path apps/macos -j 4 --disable-swift-testing
swift build --package-path apps/macos -j 4 --product ContractValidation
MACOS_VALIDATION_BIN="$(swift build --package-path apps/macos -j 4 --show-bin-path)"
"$MACOS_VALIDATION_BIN/ContractValidation"
sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh
sh apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata
sh apps/macos/Scripts/validate-foundation.sh
```

These automated commands do not launch the desktop app. Manual/runtime checks
require the local-development guide and the single GRAF Dev installation.

Current release QA is in `qa/macos/release-candidate-checklist.md`.

## Historical Evidence And Existing Local Proof Installs

Historical failure/proof evidence is retained under
`docs/evidence/legacy-audio-driver/` for audit only. It is not executable
guidance.

Removing repository source does not remove a component previously installed on
a developer Mac. Read
`docs/agent-guidance/legacy-audio-driver-cleanup.md` before any deliberate
host cleanup. Normal build and validation commands never perform that cleanup.
