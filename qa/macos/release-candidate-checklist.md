# macOS Release Candidate Checklist

This checklist describes the current app-owned system-audio-first recording
release surface.

## Automated Gates

- [ ] `swift build --package-path apps/macos` passes.
- [ ] `swift test --package-path apps/macos` passes.
- [ ] `swift run --package-path apps/macos ContractValidation` passes.
- [ ] `sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh` passes.
- [ ] `sh apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata` passes.
- [ ] `infra/scripts/ci-local.sh` passes.

## Recording Regression Gates

- [ ] `SystemAudioCaptureService` still produces the app-owned incoming
  sample source.
- [ ] `MicrophoneCaptureService` still produces the app-owned microphone
  sample source.
- [ ] Both sources are explicitly injected into `LocalRecordingWriter`.
- [ ] `Record`/`Stop` creates two non-empty original WAV tracks and a
  finalized manifest.
- [ ] Microphone and system-audio permissions are both enforced.
- [ ] The persistent local capture indicator and one-action `Stop` pass.
- [ ] Existing recording-directory and manifest compatibility tests pass.

## Packaging Gates

- [ ] The distribution package contains exactly one app component.
- [ ] The package contains no privileged audio component, lifecycle sidecar, or
  host-service mutation script.
- [ ] Package expansion/inspection passes without installing it.
- [ ] Signing/notarization evidence matches the intended release lane.

## Manual Gates

- [ ] Current-build short recording smoke passes on the required browser target.
- [ ] Claimed microphone device classes pass the device matrix.
- [ ] Indicator visibility and stop behavior are observed directly.
- [ ] Long-duration acceptance is either passed with evidence or called out as
  a known limitation.

## Release Hygiene

- [ ] Russian changelog/release notes describe the architecture removal,
  compatibility impact, validation evidence, known limitations, and linked
  PR/issues.
- [ ] No secrets, raw audio, transcript text, signed URLs, or private meeting
  content are committed as evidence.
