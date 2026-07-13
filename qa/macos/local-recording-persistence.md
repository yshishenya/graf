# Local Recording Persistence Gate

This gate controls local recording artifacts after manual `Record`/`Stop`.
The current writer receives an app-owned microphone sample source and an
app-owned system-audio sample source explicitly.

## Required Evidence

- [ ] Recording starts only after current prerequisites pass.
- [ ] `Stop` finalizes `mic.wav`, `incoming.wav`, and `manifest.json`.
- [ ] Missing or empty required tracks are degraded or failed, never complete.
- [ ] The app exposes the local recording location after finalization.
- [ ] Current recordings use the GRAF application-support root.
- [ ] Existing recordings under the former application-support directory
  remain readable without becoming the preferred write location.
- [ ] Unknown historical manifest keys remain safely ignorable.
- [ ] No upload, transcription, dashboard publication, or external egress is
  triggered by local finalization.

## Automated Validation

```sh
swift test --package-path apps/macos --filter 'LocalRecordingStoreTests|LocalRecordingManifestTests|LocalRecordingWriterTests|LocalRecordingWriterSystemAudioTests|SystemAudioRecordingPackageTests'
swift run --package-path apps/macos ContractValidation
sh apps/macos/Scripts/validate-local-recording-persistence.sh
```

## Manual Smoke

Use `tests/macos/browser-meetings/manual-recording-smoke.md` and verify the
three finalized package files directly. Historical smokes are useful context,
but the cleanup slice requires fresh evidence from the current build.
