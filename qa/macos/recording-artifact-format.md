# Recording Artifact Format Gate

This gate controls the dual-track local package consumed by the later upload
pipeline.

## Required Evidence

- [ ] Manual `Record`/`Stop` creates `mic.wav` and `incoming.wav`.
- [ ] Both WAV files are signed 16-bit little-endian PCM, mono, 16 kHz.
- [ ] `manifest.json` maps the microphone track to `local_mic`.
- [ ] `manifest.json` maps the system-audio track to `remote_speaker`.
- [ ] Manifest readiness and degraded/failed reasons reflect actual artifacts.
- [ ] Track timing discontinuities are preserved or truthfully degraded.
- [ ] Diagnostics remain metadata-only and redacted.
- [ ] The desktop app stores no MediaScribe credential and performs no
  MediaScribe request during local recording.
- [ ] A newly encoded current manifest contains no retired routing lifecycle
  fields.

## Automated Validation

```sh
swift test --package-path apps/macos --filter 'SystemAudioRecordingPackageTests|LocalRecordingManifestTests|LocalRecordingWriterSystemAudioTests'
swift run --package-path apps/macos ContractValidation
sh apps/macos/Scripts/validate-recording-artifact-format.sh
```

## Manual Smoke

Use `tests/macos/local-recording/recording-artifact-format-smoke.md`. Record
fresh evidence after the cleanup and inspect the package without uploading its
audio content.
