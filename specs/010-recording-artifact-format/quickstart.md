# Quickstart: Recording Artifact Format

## Automated Validation

Run:

```sh
sh apps/macos/Scripts/validate-recording-artifact-format.sh
```

Expected result:

```text
recording_artifact_format_validation=passed
```

The script must run:

- `swift test --package-path apps/macos --disable-swift-testing`
- `swift run --package-path apps/macos ContractValidation`
- `sh tests/macos/static/audio-rt-safety-check.sh`
- a fixture/header validation that proves the required WAV contract is encoded
  in tests

## Manual Smoke

1. Launch the freshly built app from the current branch.
2. Ensure the route is valid and `Record` is enabled.
3. Select `2brain Rec Microphone` and `2brain Rec Speaker` in a supported
   meeting target.
4. Press `Record`.
5. Speak briefly into the local mic.
6. Play or receive a short remote/incoming audio stimulus.
7. Press `Stop`.
8. Confirm the app shows a saved local recording location.
9. Open the location and confirm:
   - `manifest.json` exists;
   - `mic.wav` exists;
   - `incoming.wav` exists;
   - both track files are WAV PCM signed 16-bit little-endian, mono, 16000 Hz;
   - manifest maps `local_mic` to `mic_file`;
   - manifest maps `remote_speaker` to `incoming_file`;
   - manifest status is ready/saved only if both tracks satisfy the contract.

## Forbidden Content Scan

Run:

```sh
rg -n "BEGIN PRIVATE KEY|Authorization: Bearer|X-API-Key:|rawAudio|transcriptText|meetingContent|signedUrl|signedUrls|password|apiKey|mediaScribeCredentials|langfuseContentTrace|MEDIASCRIBE_API_KEY=.*msk_|X-API-Key: msk_" apps/macos tests/macos qa/macos specs/010-recording-artifact-format docs/integrations -g '!apps/macos/.build/**'
```

Expected result: matches are only policy, fixture, or redaction-test forbidden
field strings, not live secrets, raw audio, transcript text, or meeting content.

## Out Of Scope Checks

During this feature, validation must confirm:

- no upload starts;
- no MediaScribe request starts;
- the desktop app does not read `MEDIASCRIBE_API_KEY`;
- no Langfuse content trace starts;
- no dashboard meeting record is published;
- no retention or deletion promise is shown;
- non-recording passthrough remains usable after stop.
