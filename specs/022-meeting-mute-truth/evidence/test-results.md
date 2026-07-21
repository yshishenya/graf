# Test Results: Meeting-App Mute Truth

Date: 2026-06-16

## Summary

Feature 022 passes the automated Spec Kit implementation gates for models, UI copy,
manifest metadata, diagnostics, upload queue regression behavior, fixture
validation, and preserved local capture scripts.

Self-review found and fixed a privacy-truth metadata issue before closeout:
sample-source microphone pauses are recorded as `silenced`, while fallback or
non-suppressing microphone paths are recorded as `redacted`; Stop during Pause
now finalizes the active pause segment with the same truthful treatment instead
of `ended`.

A default latest-artifact check initially found an older pre-feature local
recording from 2026-06-10 and correctly failed because that manifest did not
contain `meetingMuteTruth`. A synthetic runtime proof now creates a fresh local
artifact through `LocalRecordingWriter`, and latest-artifact validation passes
against that new artifact.

The permissioned `/Applications/2brain Rec.app` bundle was launched and driven
through a manual Record/Pause/Resume/Stop pass from the desktop UI. The latest
local artifact from that pass validates with `validate-meeting-mute-truth.sh`
and contains one Pause privacy segment. This closes the previous manual runtime
gate for desktop interaction; the tested `/Applications` bundle is the
permissioned installed copy and may lag the latest UI-polish bundle that was
also inspected separately.

After the manual runtime pass, the latest staged app bundle was mirrored into
`/Applications/2brain Rec.app` and relaunched from `/Applications`. The current
system app now shows the UI-polished meeting list (`Запись 18:03`, `Сегодня`)
and upload card copy without the duplicated progress prefix.

## Static Scans

Command: stale-marker scan from `specs/022-meeting-mute-truth/quickstart.md`.

Result: PASS. No matches.

Command: forbidden-content scan from `specs/022-meeting-mute-truth/quickstart.md`.

Result: PASS with allowed matches only.

Allowed matches:

- Spec, plan, research, contract, and checklist wording that enumerates forbidden
  content classes.
- `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift` forbidden-key
  definitions.
- `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift` secret
  path detector wording.

No payload data, credentials, signed URLs, raw audio, transcript text, or meeting
content were found.

## SwiftPM

Command:

```sh
cd apps/macos
swift build
```

Result: PASS. Build complete.

Command:

```sh
cd apps/macos
swift test --filter 'MeetingMuteTruth|LocalRecordingWriterTests/testPrivacy|LocalRecordingWriterTests/testWriterPersistsPrivacy|CaptureControlTests/testPause|CaptureControlTests/testCaptureControlsCanShowMuteTruthWarning|CaptureIndicatorTests/testPaused|SystemAudioLocalizationTests/testMuteTruth|DesktopUploadQueueTests/testMuteTruth|LocalRecordingManifestTests/testManifestRoundTripsMuteTruth|DiagnosticRedactionTests/testMuteTruth'
```

Result: PASS. 18 selected tests, 0 failures.

Command:

```sh
cd apps/macos
swift test
```

Result: PASS. 422 tests, 0 failures.

Command:

```sh
cd apps/macos
swift run ContractValidation
```

Result: PASS. `ContractValidation: PASS`.

## Validation Scripts

Command:

```sh
apps/macos/Scripts/validate-meeting-mute-truth.sh --fixtures
```

Result: PASS. `meeting-mute-truth fixtures: OK`.

Command:

```sh
apps/macos/Scripts/validate-capture-session-indicator.sh
```

Result: PASS. `capture_session_indicator_validation=passed`.

Command:

```sh
apps/macos/Scripts/validate-local-recording-persistence.sh
```

Result: PASS. `local_recording_persistence_validation=passed`.

Command:

```sh
apps/macos/Scripts/validate-recording-artifact-format.sh
```

Result: PASS. `recording_artifact_format_validation=passed`.

Command:

```sh
apps/macos/Scripts/validate-meeting-mute-truth.sh --runtime-proof
```

Result: PASS. Fresh synthetic local artifact created and validated:

```text
meeting-mute-truth runtime proof: OK
directory=<local-recordings-dir>/<session-id>
decision=meeting_mute_unproven
privacySegments=1
meeting-mute-truth latest artifact: OK <local-recordings-dir>/<session-id>
```

Manifest spot-check:

- both `local_mic` and `remote_speaker` tracks are saved, timeline aligned, and
  3 seconds long;
- `meetingMuteTruth.decision` is `meeting_mute_unproven`;
- `meetingMuteTruth.reason` is `product_pause_segments_present`;
- one privacy segment is present, 1 second long, with
  `localMicTreatment=silenced`;
- forbidden content scan of the manifest returned no raw audio, transcript,
  meeting content, credential, token, or signed URL fields.

Interpretation: this proves the runtime writer/manifest/validator path with
synthetic samples. A separate manual UI pass through `/Applications/2brain
Rec.app` is recorded below.

## Runtime App Bundle

Command:

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
open -n "apps/macos/RecApp/.build/2brain Rec.app"
```

Result: PASS for build and launch. The repo-built app bundle launched as:

```text
<repo-root>/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec
```

Saved runtime screenshots:

- `specs/022-meeting-mute-truth/evidence/runtime-screens/2026-06-16-dev-app-window.png`
- `specs/022-meeting-mute-truth/evidence/runtime-screens/2026-06-16-repo-bundle-window.png`

Observed UI state: `Recording idle`, `Record System Audio`, upload queue
blocked by local package uploadability, and recorder input meters are visible.

Earlier automation limitation: `screencapture -l` and CoreGraphics window
discovery could see the repo-built window, but shell-posted mouse events did
not activate the SwiftUI button in that local environment. This limitation was
resolved for the installed `/Applications` runtime by using the app's
accessibility tree plus targeted button clicks after the user granted the
system-audio permission to that installed copy.

## Manual Desktop Runtime

Command:

```sh
open -n "/Applications/2brain Rec.app"
```

Result: PASS. The launched process was:

```text
/Applications/2brain Rec.app/Contents/MacOS/2brain Rec
```

Manual runtime flow:

1. Clicked `Начать` from the desktop UI.
2. Confirmed `Идет запись`, visible Stop, visible Pause, and active microphone
   and meeting-audio meters.
3. Clicked `Пауза`.
4. Confirmed `Запись на паузе` and visible Stop remained available.
5. Clicked `Продолжить`.
6. Confirmed recording resumed and meters remained visible.
7. Clicked `Остановить`.
8. Confirmed the new local recording appeared in the list and upload queue moved
   from 7 to 8 items requiring review.

Saved screenshots:

- `specs/022-meeting-mute-truth/evidence/runtime-screens/2026-06-16-applications-active-recording.png`
- `specs/022-meeting-mute-truth/evidence/runtime-screens/2026-06-16-applications-paused-recording.png`
- `specs/022-meeting-mute-truth/evidence/runtime-screens/2026-06-16-applications-resumed-recording.png`
- `specs/022-meeting-mute-truth/evidence/runtime-screens/2026-06-16-applications-stopped-recording.png`
- `specs/022-meeting-mute-truth/evidence/runtime-screens/2026-06-16-applications-current-ui-idle.png`

Artifact:

```text
<local-recordings-dir>/<session-id>
```

Manifest spot-check:

- `meetingMuteTruth.decision` is `unsupported`;
- `meetingMuteTruth.reason` is `unsupported_target`;
- one privacy segment is present with `control=pause`;
- the privacy segment is user initiated and has `localMicTreatment=redacted`;
- `local_mic` track is saved;
- `remote_speaker` track is degraded with `silent_input`, which is expected for
  this local QA pass without an active meeting audio source;
- validation passed without raw transcript, meeting content, credentials, or
  signed URLs in manifest metadata.

## Latest Local Artifact

Command:

```sh
apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory
```

Result: PASS after manual `/Applications` desktop runtime.

Observed output:

```text
meeting-mute-truth latest artifact: OK <local-recordings-dir>/<session-id>
```

Interpretation: the default latest artifact is now a real desktop UI recording
created from `/Applications/2brain Rec.app` with Record/Pause/Resume/Stop. The
older pre-feature artifact failure remains useful because it proved the
validator does not silently accept artifacts missing `meetingMuteTruth`.

## Closeout Validation

Command:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/unit/test_mvp_loop_readiness_matrix.py
```

Result: PASS. 14 readiness tests passed after the readiness matrix was updated
to treat `022-meeting-mute-truth` as accepted evidence and recommend
validation-only `035-mvp-loop-live-evidence`.

Command:

```sh
infra/scripts/ci-local.sh
```

Result: PASS. Server tests passed (`440 passed, 4 skipped`), server lint
passed, Python compile passed, the RLS boundary helper remained blocked from
production truth without a disposable database as expected, production Compose
config rendered, and deployment evidence scan passed.

Command:

```sh
swift build --package-path apps/macos
```

Result: PASS. Build complete.

Command:

```sh
swift test --package-path apps/macos --filter 'SystemAudioLocalization|SystemAudioPermission|CaptureControl|DesktopUploadQueue|SystemAudioDriverParked|AppControlAccessibility|MeetingMuteTruth'
```

Result: PASS. 53 selected XCTest tests passed.

Command:

```sh
apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory
```

Result: PASS. The latest artifact remained the manual `/Applications` desktop
recording listed above.

Command:

```sh
gh issue list --repo yshishenya/crisp --state open --label feature:022 --limit 120 --json number,title --jq 'length'
```

Result: PASS. Output: `0`.
