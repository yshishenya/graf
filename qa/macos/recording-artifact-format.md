# Recording Artifact Format Gate

This gate controls the v5 local package consumed by the upload pipeline.

## Required Evidence

- [ ] Manual Record/Stop creates exactly manifest.json,
  meeting-transcription.wav and meeting-review.m4a.
- [ ] The WAV is signed 16-bit little-endian PCM, mono, 16 kHz and is the
  only ASR input.
- [ ] The M4A is AAC-LC, mono, 48 kHz, shares the canonical timeline within
  the recorded AAC presentation allowance, and is playback only.
- [ ] manifest.json maps the WAV to mixed_meeting_audio/media and the M4A to
  review_playback/playback.
- [ ] Manifest readiness and degraded/failed reasons reflect actual artifacts.
- [ ] Track timing discontinuities are preserved or truthfully degraded.
- [ ] Diagnostics remain metadata-only and redacted.
- [ ] The desktop app stores no MediaScribe credential and performs no
  MediaScribe request during local recording.
- [ ] A newly encoded current manifest contains no retired routing lifecycle
  fields, dual source files, AEC or echo-cleanup state.

## Automated Validation

```sh
swift test --package-path apps/macos --filter 'SystemAudioRecordingPackageTests|CanonicalRecordingManifestTests|LocalRecordingWriterSystemAudioTests'
swift run --package-path apps/macos ContractValidation
sh apps/macos/Scripts/validate-recording-artifact-format.sh
```

## Manual Smoke

Use `tests/macos/local-recording/recording-artifact-format-smoke.md`. Record
fresh evidence after the cleanup and inspect the package without uploading its
audio content.
