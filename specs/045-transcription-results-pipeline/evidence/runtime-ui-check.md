# Runtime UI Check: Desktop App And Embedded Cabinet

**Feature**: `045-transcription-results-pipeline`
**Date**: 2026-06-24

## Metadata-Safe Rules

- No raw audio, transcript text, private meeting content, credentials, signed
  URLs, or private local recording paths are recorded here.
- Runtime paths are described by project-relative build artifacts or product
  surface names only.

## Worktree Build

- Command: `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
- Result: passed.
- Build artifact: `apps/macos/RecApp/.build/2brain Rec.app`
- Installer artifact: `apps/macos/.build/installer/2brain-rec-local.pkg`
- Signing mode: ad-hoc local development signing.

## Worktree Non-Recording Preflight

Rechecked on 2026-06-24 with the current branch bundle. This preflight did not
press Record/Stop, did not install the package, did not reset or change macOS
privacy/TCC state, did not inspect audio content, and did not run HAL probes.

- Command: `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --self-test`
- Result: `manual_gate_self_test=passed`.
- Command: `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
- Result: passed; product `TwoBrainRecApp` built, the local `.app` signature was
  replaced with ad-hoc development signing, and the local pkg was rebuilt.
- Command: `SYSTEM_AUDIO_MANUAL_GATE_ASSUME_CLEAN_BASELINE=1 apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --preflight`
- Result: `manual_gate_preflight=passed`.
- Package boundary: `system_audio_capture_pivot_validation=passed`; default
  local package remained app-only.
- Launch: packaged app launch was observed with `processCount=1`.
- Idle phase: passed with `maxCoreaudiodCpuPercent=0.00`,
  `maxAppHelperCpuPercent=0.20`, `maxAppHelperRssMB=113.64`,
  no helper process, no unexpected app process, and
  `halProbeObserved=false`.
- Quit phase: passed with the app process gone, no helper process, and
  `halProbeObserved=false`.
- Thermal/performance: no thermal warning level, performance warning level, or
  CPU power status warning was recorded.
- Remaining manual gates reported by the harness:
  `permission_matrix`, `controlled_artifact`, `activeRecording_cpu`,
  `stop_cpu`, `30_minute`, `75_minute`, and `final_review`.

This proves the current branch app bundle builds, launches, idles, and quits in
the safe non-recording harness. It does not prove current-branch Record/Stop,
permissioned system-audio capture, recording artifact creation, upload,
transcription, or review.

## Worktree App UI

Observed with the freshly built worktree `.app`:

- Main window launched.
- Local meeting list was visible.
- Embedded cabinet loaded the expected missing-auth login state.
- Login copy stated that meeting cabinet access requires sign-in.
- Control panel opened.
- Idle state showed `Запись не идет`.
- Record button was visible.
- Upload queue truth showed existing local recordings that need review.
- Meters showed the pre-recording waiting state.
- Diagnostics stated that the legacy driver is parked and not required for
  system-audio recording.

## Worktree Recording Smoke

Current branch recording start/stop is **not proven** from the
worktree-launched bundle because this ad-hoc app identity does not have the
same macOS system-audio permission as the installed product app:

- The worktree app bundle launched from
  `apps/macos/RecApp/.build/2brain Rec.app`.
- The control panel exposed `systemAudio.record.button`.
- Clicking the record button returned the UI to `Запись не началась`.
- The blocker banner said the app needs system-audio recording permission in
  macOS Settings before retrying.
- The app log recorded `recording.start_blocked` with
  `microphonePermission=granted systemAudioPermission=unknown` and
  `action=grant_system_audio`.
- No `recording.started` event was recorded for this worktree smoke.

This proves the current branch fails closed and explains the blocker to the
user when the local development app identity lacks system-audio permission. It
does not prove current-branch start/stop recording, because macOS TCC treats the
worktree app identity separately from the already-installed product app.

## Installed App Cross-Check

The already-installed `/Applications/2brain Rec.app` was checked only as a
product-runtime comparison, not as proof of current branch code:

- Idle state showed `Запись остановлена`.
- Record button was enabled.
- A short local recording smoke entered active state.
- The visible recording indicator appeared.
- Microphone and system-audio meters reported active recording.
- Stop returned the UI to `Запись остановлена`.
- The upload queue count increased by one local item requiring review.
- The app log recorded `recording.started` followed by `recording.stopped`.

This proves the installed product runtime can still start/stop local recording,
but it does not replace current-branch installed-app verification.

## Installed Current-Branch Permissioned Proof Attempt

After explicit owner approval on 2026-06-24, the current branch app-only
package was installed over `/Applications/2brain Rec.app` to reuse the
permissioned installed-app path:

- Build command:
  `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
- Package boundary: default local package remained app-only.
- Installed bundle: `/Applications/2brain Rec.app`.
- Bundle identifier: `pro.2brain.rec`.
- Signing mode: ad-hoc local development signing.
- Installed bundle CDHash matched the just-built current-branch bundle:
  `11e4ce8dd89d0e1df4a2bac05e86d5b3a393c96d`.

Rejected setup attempts:

- One attempt was rejected because the app was already running during baseline
  (`appProcessCount=1`, max `coreaudiod` CPU `9.20%`).
- One attempt was rejected because `Yandex.Telemost` was running before
  baseline. The harness correctly blocked the run with
  `meetingProcessRunningBeforeBaseline`.

Clean speakerphone/degraded attempt:

- Baseline before launch was clean: max `coreaudiod` CPU `0.00%`,
  `appProcessCount=0`, no helper process, no unexpected app process, and
  `halProbeObserved=false`.
- Fresh `recording.started` was observed at `2026-06-24T15:11:35Z` for
  session `16287729-FC91-4FAB-9EBA-C7DDA333199B`.
- Permission snapshot in the manifest was `microphone=granted` and
  `systemAudio=granted`.
- Active recording CPU passed: max `coreaudiod` CPU `11.40%`, max app/helper
  CPU `15.20%`, `appProcessCount=1`, no helper process, no unexpected app
  process, `halProbeObserved=false`, and `phaseEventObserved=true`.
- Fresh stop/local-recording event was observed at `2026-06-24T15:12:19Z` with
  `reason=user_requested` and `localRecordingStatus=degraded`.
- The immediate stop CPU gate failed with sustained `coreaudiod` over the
  threshold, but a later stop-recovery sample showed `coreaudiod` back at
  `0.00%`; the recovery sample itself was not accepted because the harness had
  already exited and the app was no longer running.
- The newest artifact directory was
  `20260624-151135-16287729-FC91-4FAB-9EBA-C7DDA333199B`.
- The feature-025 clean artifact validator rejected it, as expected for this
  speakerphone/degraded class: manifest schema was v3, status was `degraded`,
  transcription readiness was `degraded`, and failure reason was
  `leakage_unproven`.
- Both original media tracks were still present and saved:
  `local_mic` duration `44585 ms`, `remote_speaker` duration `44600 ms`,
  duration difference `0.015 s`, both WAV PCM mono 16 kHz.
- The app queued the package for upload with `upload.queued`.

Interpretation:

- This proves the installed current-branch bundle can pass macOS permissions,
  enter active recording, expose one-action Stop, create a dual-track local
  package, and queue the package for upload in a real speakerphone/high-leakage
  class.
- It does not prove a clean `saved` / `ready` artifact. That old clean-artifact
  gate is still useful for headphones/low-leakage acceptance, but it cannot be
  the only MVP criterion because users will record both through headphones and
  through speakers.
- For 045, the product-relevant next proofs are controlled system-audio capture
  for a known-audible speakerphone source and production upload-to-live-
  MediaScribe-to-review after merge/deploy approval. Feature 044 remains the
  separate track for improving speakerphone echo/noise quality.

## Local Server Full-Path Probe For Speakerphone/Degraded Package

The same installed-app speakerphone/degraded artifact was replayed through the
current branch server ingest API in a local TestClient harness with fake object
storage and fake Temporal. No production endpoint, external network, or live
MediaScribe dependency was used.

- Artifact class: speakerphone/high-leakage, manifest status `degraded`,
  failure reason `leakage_unproven`, transcription readiness `degraded`.
- Permission snapshot in the manifest remained `microphone=granted` and
  `systemAudio=granted`.
- Create meeting: `200`.
- Create upload session: `200`.
- Uploaded real artifact bytes for `manifest`, `microphone`, and `system`:
  `200`, `200`, `200`.
- Accepted bytes by track: manifest `7679`, microphone `1426774`, system
  `1427244`.
- Finalize: `200`, upload status `finalized`, meeting status
  `ingested_pending_processing`.
- Processing dispatch: `workflow_started=true`, processing state
  `workflow_started`, fake Temporal starts `1`, MediaScribe job created
  `false`.
- Transcript, diarization, and content availability stayed `false`, as expected
  for a local fake-Temporal proof without a running worker or live MediaScribe.

Audio/trancription probe for the same artifact:

- Microphone track level: mean `-37.3 dB`, max `-8.6 dB`.
- Incoming/system track level: mean `-91.0 dB`, max `-78.3 dB`.
- Local tiny-model Whisper transcripts were generated for microphone-only and
  microphone-plus-incoming mixed audio under `/tmp` for manual review; transcript
  text is intentionally not committed here.
- The mixed transcript was effectively the microphone transcript with only a
  small tail difference, matching the level analysis that the incoming/system
  track in this run was almost silent.

Interpretation:

- `leakage_unproven` is not an upload/finalize/processing-start blocker on the
  current branch.
- This run does not prove useful dual-track capture for speakerphone meetings,
  because the system/incoming channel did not contain meaningful incoming
  audio. The next speakerphone proof must verify that actual system audio lands
  in the system track, or the product must fall back to a single/microphone
  source path for that class.

## Live Production Probe For Fresh Failed/Leakage Package

After a fresh owner-created recording on 2026-06-24, the installed current-
branch desktop app created a new speakerphone/high-leakage package:

- Directory id: `20260624-153543-7254103C-B01F-4356-BB54-78130CF5D925`.
- Manifest: schema v3, status `failed`, failure reason `leakage_detected`,
  transcription readiness `failed`, source mode `dual`.
- Permissions in manifest: microphone `granted`, system audio `granted`.
- Track metadata: two 16 kHz mono WAV files, about `30.4 s` each.
- Audio levels: microphone mean `-31.7 dB` / max `-10.2 dB`; incoming/system
  mean `-22.6 dB` / max `-3.5 dB`.

The desktop app then uploaded that exact package to production:

- Local queue state became `uploaded` after one attempt.
- Production logs showed create meeting, create upload session, microphone/
  system/manifest part uploads, missing range checks, and finalize `200`.
- Production assigned meeting id `697a106a-4f3a-4f71-82c2-6ab4654a91f8` and
  upload session id `58401f08-f399-4dc9-a421-2a849bdb52a8`.
- The embedded desktop cabinet navigated to meeting detail after upload.

Production state caveat:

- Production was running `master` commit `e312d25`, not the 045 branch.
- Because 045 auto-start/reuse is not deployed there, processing initially
  stayed `not_submitted` after finalize.
- A targeted `POST /api/v1/internal/processing/pickup` for only this meeting
  returned `202`, `accepted=true`, and `started_count=1`.
- A follow-up processing status check returned `processed` with
  `content_available=true`, `transcript_available=true`,
  `diarization_available=true`, and workflow present.
- Cabinet API returned `200`, `processing_dependency=mediascribe`, both source
  roles, playback available, four transcript segments, and two speakers.

Result quality caveat:

- Transcript text is available for owner review but intentionally not committed
  to repository evidence.
- Segment-level `speaker_label` and `source_role` were not consistently aligned
  in the live result. This is a real review-quality issue: the UI can confuse
  local microphone vs incoming/system attribution even though both sources were
  captured and the pipeline reached processed state. The current branch now has
  a regression fix that matches transcript and diarization segments by
  normalized `(sequence, source_role)` instead of sequence alone; production is
  still on `e312d25`, so the fix needs post-deploy production proof.

## Desktop Post-Upload Processing Reconciliation Check

After the production probe above, the local desktop queue still showed the
uploaded recording as `processingStatus=not_submitted` even though production
had imported a processed result. This exposed a desktop follow-up gap for
terminal uploaded items.

Current-branch check on 2026-06-24:

- Built the current branch release bundle with local ad-hoc signing.
- Direct replacement of the system `/Applications` bundle was blocked by macOS
  filesystem ownership in this Codex session; no sudo/password path was used.
- Installed the same current-branch bundle into the user app location and
  launched it against the existing local queue state.
- Without manually editing the queue, the app reconciled the uploaded recording
  from `processingStatus=not_submitted` to `processingStatus=processed`,
  advanced `lastReconciledAt`, and kept `syncConflictState=none`.
- The app process launched with one standard `2brain Rec` window.

Interpretation:

- The current branch now proves a desktop post-upload follow-up path for
  already-uploaded recordings whose server processing state changes after the
  upload terminal state.
- This does not prove 045 production auto-start/reuse, because production was
  still running the older deployed branch and the processed result required the
  targeted pickup described above.
- This does not replace a system `/Applications` install proof; that install
  still needs an administrator-authenticated local install or packaged release
  path.

## Desktop Status For MVP Audit

- Desktop shell UI: partially proven on current branch.
- Embedded missing-auth cabinet: proven on current branch.
- Current-branch build/launch/idle/quit non-recording preflight: proven.
- Current-branch no-permission recording blocker: proven.
- Current-branch installed-app recording start/stop with granted system-audio
  permission: proven for the speakerphone/degraded class, not yet proven for a
  clean `saved` / `ready` low-leakage artifact.
- Installed-app recording start/stop: proven as comparison only.
- Local server upload/finalize/processing-start replay of the installed-app
  speakerphone/degraded artifact: proven without production or live MediaScribe.
- Upload-to-live-transcript-to-review from desktop: proven for one fresh
  failed/leakage package after targeted manual processing pickup on production
  `e312d25`; not yet proven for deployed 045 auto-start/reuse behavior.

## Required Follow-Up

- Prove the current-branch speaker/source-role alignment fix on production
  after 045 is reviewed, merged, and deployed.
- Complete a clean low-leakage/headphones artifact proof for the old
  `saved` / `ready` acceptance class.
- Complete production upload-to-live-MediaScribe-to-review proof after PR/merge
  and explicit deploy authorization, specifically proving 045 auto-start/reuse
  without manual pickup.

## Continuation Preflight

Rechecked again on 2026-06-24 after evidence/status synchronization:

- `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --self-test`:
  passed with `manual_gate_self_test=passed`.
- `SYSTEM_AUDIO_MANUAL_GATE_ASSUME_CLEAN_BASELINE=1
  apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --preflight`:
  passed with `manual_gate_preflight=passed`.
- Observed scope: packaged app launch, idle, quit, no helper process, no
  unexpected app process, no HAL probe, and no thermal/performance warning.
- This recheck remains `non_recording_only`; it does not prove permissioned
  Record/Stop, system-audio capture, metadata-valid recording artifact
  creation, upload, transcription, or review.

Rechecked again on 2026-06-24 after PR/privacy/apply preflight:

- `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --self-test`:
  passed with `manual_gate_self_test=passed`.
- `SYSTEM_AUDIO_MANUAL_GATE_ASSUME_CLEAN_BASELINE=1
  apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --preflight`:
  passed with `manual_gate_preflight=passed`.
- Observed scope: app-only package validation passed, baseline CPU was
  diagnostic-only/clean, packaged app launch was observed with one app process,
  idle CPU passed with no helper/HAL probe, quit CPU passed with app process
  count returning to 0, and no thermal/performance warning was recorded.
- This recheck remains `non_recording_only`; the remaining manual gates are
  `permission_matrix`, `controlled_artifact`, `activeRecording_cpu`,
  `stop_cpu`, `30_minute`, `75_minute`, and `final_review`.

Rechecked again on 2026-06-24 during MVP closeout continuation:

- `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --self-test`:
  passed with `manual_gate_self_test=passed`.
- First `--preflight` attempt stopped before app launch because the clean
  baseline CPU gate saw `coreaudiod` above threshold. This was treated as an
  environmental blocker, not an app failure.
- Repeat `SYSTEM_AUDIO_MANUAL_GATE_ASSUME_CLEAN_BASELINE=1
  apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --preflight`:
  passed with `manual_gate_preflight=passed`.
- Observed repeat-pass scope: clean baseline, packaged app launch observed,
  idle and quit CPU phases passed, no helper process, no unexpected app process,
  no HAL probe, and no thermal/performance warning.
- This recheck remains `non_recording_only`; it does not prove permissioned
  Record/Stop, system-audio capture, package creation, upload, transcription, or
  review.

Rechecked again on 2026-06-24 during goal continuation:

- `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --self-test`:
  passed with `manual_gate_self_test=passed`.
- Two repeat `--preflight` attempts stopped before app launch because baseline
  `coreaudiod` CPU was around 8-9%, above the pre-launch threshold `5`.
- Because the app was not launched, this is an environmental pre-launch blocker
  for this continuation rather than a current-branch app failure.
- This check does not prove launch, idle, quit, permissioned Record/Stop,
  package creation, upload, transcription, or review.

Rechecked again on 2026-06-24 during runtime continuation:

- `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --self-test`:
  passed with `manual_gate_self_test=passed`.
- `SYSTEM_AUDIO_MANUAL_GATE_ASSUME_CLEAN_BASELINE=1
  apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --preflight`:
  passed with `manual_gate_preflight=passed`.
- Observed scope: clean baseline, packaged app launch, idle and quit CPU phases
  passed, no helper process, no unexpected app process, no HAL probe, and no
  thermal/performance warning.
- This recheck remains `non_recording_only`; it does not prove permissioned
  Record/Stop, system-audio capture, package creation, upload, transcription, or
  review.

Metadata-only desktop app UI inspection on 2026-06-24:

- Installed `/Applications/2brain Rec.app` launched and exposed process
  `2brain Rec`.
- Accessibility metadata showed the app as frontmost, with one standard window
  named `2brain Rec` and one menu bar.
- The app quit cleanly and `pgrep -x "2brain Rec"` returned no running process
  after quit.
- Pixel screenshot capture was not retained as evidence because the available
  screen-coordinate path was not metadata-safe enough for committed evidence.
  This inspection records only process/window metadata and does not prove visual
  layout pixels.

Goal-continuation desktop recheck on 2026-06-24:

- `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --self-test`:
  passed with `manual_gate_self_test=passed`.
- `SYSTEM_AUDIO_MANUAL_GATE_ASSUME_CLEAN_BASELINE=1
  apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --preflight`:
  passed with `manual_gate_preflight=passed`, `preflight_scope=non_recording_only`,
  clean baseline, packaged app launch, idle and quit phases, no helper process,
  no unexpected app process, no HAL probe, and no thermal/performance warning.
- Installed `/Applications/2brain Rec.app` metadata-only UI inspection then
  launched the app, observed `process_exists=true`, `frontmost=true`,
  `window_count=1`, `window_names=2brain Rec`, `window_roles=AXWindow`, and
  `menu_bar_count=1`; quit stopped the process. No screenshot or raw audio was
  captured.
