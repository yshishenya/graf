# Quickstart: Local Recording Persistence

## Automated Validation

Run:

```sh
sh apps/macos/Scripts/validate-local-recording-persistence.sh
```

Expected result:

```text
local_recording_persistence_validation=passed
```

The script must run:

- `swift test --package-path apps/macos --disable-swift-testing`
- `swift run --package-path apps/macos ContractValidation`
- `sh tests/macos/static/audio-rt-safety-check.sh`
- a local recording artifact contract check

## Manual Smoke

1. Launch the freshly built app from the current branch.
2. Ensure the route is valid and `Record` is enabled.
3. Press `Record`.
4. Speak briefly into the local mic.
5. Play a short remote/speaker stimulus through `2brain Rec Speaker` if
   available.
6. Press `Stop`.
7. Confirm the app shows a saved local recording location.
8. Open the location and confirm:
   - `manifest.json` exists;
   - local mic track file exists and is non-empty;
   - remote speaker track file exists and is non-empty when speaker frames were
     present;
   - manifest status is `saved` only if both required tracks are saved.

## Forbidden Content Scan

Run a scan across implementation, fixtures, QA, and this spec:

```sh
rg -n "BEGIN PRIVATE KEY|Authorization: Bearer|X-API-Key:|rawAudio|transcriptText|meetingContent|signedUrl|signedUrls|password|apiKey|mediaScribeCredentials|langfuseContentTrace" apps/macos tests/macos qa/macos specs/008-local-recording-persistence -g '!apps/macos/.build/**'
```

Expected result: matches are only policy, fixture, or redaction-test forbidden
field strings, not live secrets, raw audio, transcript text, or meeting content.

## Out Of Scope Checks

During this feature, validation must confirm:

- no upload starts;
- no MediaScribe request starts;
- no Langfuse content trace starts;
- no dashboard meeting record is published;
- no retention or deletion promise is shown;
- non-recording passthrough remains usable after stop.
