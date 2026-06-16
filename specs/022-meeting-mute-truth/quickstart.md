# Quickstart: Meeting-App Mute Truth

## Prerequisites

- macOS 14+ on Apple Silicon.
- Current branch: `022-meeting-mute-truth`.
- Microphone and Screen/System Audio permissions available for manual toggling.
- Controlled non-sensitive meeting/audio sources for Zoom native,
  Chrome/Telemost, and Opera/Telemost.
- For local desktop QA, install the staged app into the permissioned
  `/Applications/2brain Rec.app` bundle before launch so macOS privacy
  permissions remain attached to the same bundle path across repeated checks.
  If a developer cannot write to `/Applications`, the helper can still be run
  without `TWO_BRAIN_REC_USER_APP_DEST` to use `~/Applications`, but acceptance
  evidence for this slice uses `/Applications`:

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
TWO_BRAIN_REC_USER_APP_DEST="/Applications/2brain Rec.app" sh apps/macos/Installer/Scripts/install-user-app.sh
open -n "/Applications/2brain Rec.app"
```

## 1. Static Spec And Secret/Content Scan

```sh
rg -n "NEEDS CLARIFICATION|Backlog Draft|no implementation authorized|not ready" \
  specs/022-meeting-mute-truth AGENTS.md \
  --glob '!specs/022-meeting-mute-truth/quickstart.md'

rg -n "rawAudio|transcriptText|meetingContent|signedUrl|password|apiKey|token" \
  specs/022-meeting-mute-truth apps/macos/Shared/Sources apps/macos/RecApp/Sources \
  --glob '!specs/022-meeting-mute-truth/quickstart.md'
```

Expected:

- no unresolved backlog/clarification blockers;
- forbidden-content matches, if any, are policy wording or
  `DiagnosticRedactor` forbidden-key tests, not payload data.

## 2. Swift Build And Tests

```sh
cd apps/macos
swift build
swift test
swift run ContractValidation
```

Expected:

- build succeeds;
- all existing tests pass;
- new meeting-mute-truth tests pass after implementation;
- contract validation accepts the local manifest extensions.

## 3. Focused Local Validation Script

After implementation, run:

```sh
apps/macos/Scripts/validate-meeting-mute-truth.sh --fixtures
apps/macos/Scripts/validate-meeting-mute-truth.sh --runtime-proof
apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory
```

Expected:

- fixture manifests pass the contract rules;
- runtime proof creates a fresh synthetic local artifact through
  `LocalRecordingWriter` with product Pause/Resume/Stop metadata;
- latest local artifact reports product pause segments and mute-truth decision
  metadata without raw audio or meeting content.

Note: `--runtime-proof` uses synthetic samples and metadata-safe modeled
permissions. It proves the writer/manifest/validator path, not a human UI click
through the desktop app.

## 4. Product Pause Manual Artifact Check

For each `pause_validated` target row:

1. Start a controlled meeting or meeting-like session with non-sensitive audio.
2. Start recording in 2brain Rec.
3. Confirm the limitation copy is visible if meeting-app mute truth is
   unproven.
4. Speak a short non-sensitive phrase while recording normally.
5. Activate `2brain Pause`.
6. Speak locally during pause.
7. Resume.
8. Speak a short non-sensitive phrase after resume.
9. Stop recording.
10. Validate the latest artifact metadata:

```sh
apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory
```

Expected:

- `privacySegments` includes the pause interval;
- local mic treatment for the pause interval is `silenced` or `redacted`;
- `meetingMuteTruth.decision` does not claim third-party meeting-app mute
  support;
- Stop remained available while paused;
- diagnostics remain metadata-only.

## 5. Unsupported Target Claim Check

Run or fixture-validate Yandex Browser/Telemost and unknown target rows.

Expected:

- limitation copy is visible;
- target status is `deferred` or `unsupported`;
- artifact uses `meeting_mute_unproven`, `unsupported`, or `degraded`;
- release validation does not pass the row as meeting-app-mute-respecting.

## 6. Existing Gate Regression

Re-run the local gates that this feature must preserve:

```sh
apps/macos/Scripts/validate-capture-session-indicator.sh
apps/macos/Scripts/validate-local-recording-persistence.sh
apps/macos/Scripts/validate-recording-artifact-format.sh
```

Expected:

- visible capture indicator and one-action Stop still pass;
- local artifact persistence still passes;
- artifact format remains compatible with dual-track local recording.
