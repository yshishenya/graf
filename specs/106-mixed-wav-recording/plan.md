# Implementation Plan: Единый синхронный WAV и playback M4A

**Branch**: `106-mixed-wav-recording` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/106-mixed-wav-recording/spec.md`

## Summary

Replace the active first-party dual-track recording path with one timestamped, continuous conversation timeline. The macOS client will fan that one canonical mixed PCM stream out to exactly two final artifacts:

- `meeting-transcription.wav`: PCM signed 16-bit little-endian, mono, 16 kHz; the sole source for a new recording's transcription.
- `meeting-review.m4a`: AAC-LC, mono, 48 kHz; playback only, never an ASR input.

The server will register the immutable v5 package as a distinct `initial_mixed_recording` revision and submit only its `media` WAV artifact to the existing single-track MediaScribe endpoint. This removes active dual ASR, transcript merge, AEC/echo-cleanup and per-track leakage gating from the new recording path. Old v3/v4 packages remain readable and processable only for their ordinary retention lifecycle; new packages never create their files.

## Technical Context

**Language/Version**: Swift 6 / SwiftPM on macOS; Python 3.12 server services and tests; POSIX shell only for existing validation scripts

**Primary Dependencies**: Native ScreenCaptureKit, AVFoundation, `AVAudioConverter`, Foundation and existing SwiftPM targets; FastAPI, SQLAlchemy, Temporal, MinIO-compatible storage and the existing MediaScribe client. No new runtime dependency.

**Storage**: Protected local recording package; existing Postgres media revision/workflow records; existing object storage; existing deletion and local purge lifecycle. No raw intermediate audio is retained after finalization.

**Testing**: XCTest and ContractValidation in `apps/macos`; pytest and Ruff in `apps/server`; shell syntax/format contracts; deterministic non-private synthetic audio fixtures; installed-app controlled hardware and full pipeline acceptance; canonical `infra/scripts/ci-local.sh` at closeout.

**Risk / Validation Lane**: High-risk feature. It changes macOS capture timing, private audio artifacts, upload contracts, MediaScribe egress, transcript generation, playback, deletion and an installed-app workflow.

**Release Gate**: No deploy, public rollout, installer distribution, release tag or production data action during this implementation lane. A separately approved release gate will use the v5 canary evidence; rollback rehearsal is a contingency action, not a prerequisite while v5 passes its quality gates.

**Target Platform**: Apple Silicon macOS 14.5+ desktop client; existing Linux containerized GRAF server and MediaScribe integration.

**Project Type**: Native desktop capture client plus server-mediated ingest, processing and playback service.

**Performance Goals**:

- no capture callback waits on network, disk finalization or an unbounded lock;
- bounded queue overflow is an explicit integrity failure, never silent frame loss;
- maximum unexplained WAV/playback timeline divergence is 100 ms in the 60-minute controlled run; AAC priming is recorded separately;
- active capture changes the selected playback route by 0 and incoming perceived level by no more than 1 dB in required hardware scenarios;
- one accepted v5 revision creates at most one external MediaScribe job.

**Constraints**:

- manual Start/Stop, persistent visible capture and one-action Stop remain;
- desktop sends audio only to GRAF and never has MediaScribe credentials;
- no AEC, Apple voice processing, WebRTC AEC, VAD trimming, amplitude presence gate, raw dual capture retention, dual ASR/merge or hidden text dedupe in the v5 path;
- diagnostics/evidence contain metadata, hashes, counts, durations and safe reason codes only—never audio, transcript text, credentials or local paths;
- historical v3/v4 reading is compatibility-only; the implementation must not create a parallel new recorder, new playback subsystem, database migration or runtime feature flag.

**Scale/Scope**: One first-party macOS recording format, one common PCM timeline, two final artifacts and one server submission per accepted revision. Manual media upload, new platforms, virtual audio routing and MediaScribe API redesign are out of scope.

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- **Capture-first MVP integrity — PASS**: the design stays native to macOS and preserves visible start/stop and route safety. A timestamped in-memory timeline replaces sample-count FIFO alignment; it does not introduce a virtual driver or a second recorder.
- **Visible consent and user control — PASS**: no new hidden capture mode, user setting, automatic start, or removal of the one-action Stop path.
- **Data boundary and secret discipline — PASS**: only GRAF backend stages the canonical WAV and calls MediaScribe. Audio, transcript text, credentials and live paths are excluded from fixtures and evidence.
- **Deletion truth and lifecycle accounting — PASS**: both final artifacts, temporary files and processing state use the existing revision-bound deletion/purge lifecycle. The plan does not promise deletion outside GRAF control.
- **Spec-driven delivery — PASS**: full clarify, plan, checklists, tasks, analysis, issue sync, implementation, focused checks, hardware acceptance and canonical local CI are required.
- **Platform and clean-room constraints — PASS**: AVFoundation and ScreenCaptureKit remain authoritative. No third-party AEC, routing driver, audio engine or copied product UI is introduced.
- **Post-design re-check — PASS**: version v5 makes the source mode immutable; a source-kind-aware server validator prevents a package that can be accepted but cannot be processed. There is no constitution exception.

## Architecture And Execution Approach

### 1. One timestamped capture timeline

Replace the current `LocalRecordingSampleSource` sample-count-only handoff with bounded source batches containing actual source PTS, duration, real sample rate, channel count, discontinuity and route generation. The writer fixes one recording epoch from the two first valid batches. It normalizes each source to mono 48 kHz through stateful `AVAudioConverter`, then writes gap silence and trims overlap against one monotonically increasing output frame index.

The implementation must prove that the source timestamps are comparable on one host-time basis before accepting an aligned recording. If a route transition, unsupported rate, queue overflow, missing timing basis or discontinuity cannot be reconciled, the recording receives a typed integrity outcome rather than a sample-count fallback. Stop freezes both sources, drains to a known PTS limit, flushes converters and finalizes once; it must not pad independently against `Date()`.

Existing feature-103 timeline work is a read-only design reference only. It may be selectively reimplemented after source-level review, but this branch must not merge that dirty worktree or import its experimental/legacy surfaces.

### 2. One canonical PCM fan-out

Create a small native `CanonicalRecordingWriter` boundary that receives the already-aligned 48 kHz mono mixed frames once. It writes two protected partial artifacts from those exact frames:

1. a statefully converted 16 kHz PCM s16le WAV via `AVAudioConverter`, with explicit end-of-stream flush and RIFF/header validation;
2. a 48 kHz mono AAC-LC M4A through `AVAudioFile`, with complete close and actual-container validation.

The mix profile is `canonical-mix.v1`: each finite normalized mono sample contributes exactly `0.5` from microphone plus `0.5` from system audio. The fixed average cannot clip valid `[-1, 1]` inputs, preserves both sources and avoids any adaptive gain, ducking, mute, speech inference or silence removal. M4A uses AAC-LC mono 48 kHz with a 96 kbit/s writer target. The profile and all timing metadata are part of v5 package truth. Both files are atomically renamed only after validation. Any partial artifact is deleted and cannot enter the queue.

### 3. Immutable package v5 and truthful upload progress

New desktop packages contain exactly `manifest.json`, `meeting-transcription.wav` and `meeting-review.m4a`. The manifest uses `local-recording-manifest.v5` and `mediaScribeSourceMode=single_wav_v1`. Its immutable artifact descriptors express file identity, actual codec/rate, duration, SHA-256, shared timeline version and safe finalization status.

The upload model adds the existing transport role `media` for the canonical WAV and makes `playback` required for v5. It computes progress from uploaded bytes across all three selected artifacts, not by completed artifact count. The UI must have monotonic intermediate progress; it may never claim 50% merely because one of two audio files completed.

Historic v3 and v4 decoders/upload states remain isolated compatibility cases. They do not change the v5 writer, its artifact profile or the new UI copy.

### 4. Server-side single source and playback reuse

Add `MediaRevisionSourceKind.INITIAL_MIXED_RECORDING`. Its only authoritative source role is `media`; `playback` is a candidate derivative and intentionally does not change the source fingerprint. Do not reuse `manual_upload`, which has different provenance and product semantics. No database migration is required: the existing source-kind/request-mode fields and immutable fingerprint support the new value.

Validate source kind, role set and descriptors together when an upload session is created and finalized:

| Source kind | Exact accepted role set |
| --- | --- |
| `initial_recording` (historic) | `manifest,microphone,system` with optional `playback` |
| `initial_mixed_recording` (v5) | `manifest,media,playback` |
| `manual_upload` | `manifest,media` |

For v5, `media` is only valid as WAV PCM s16le/16 kHz/mono and `playback` only as AAC M4A/48 kHz/mono. Processing stages exactly the accepted WAV, gives the multipart file a `.wav` name and `audio/wav` content type, and calls only `submit_single_track`. M4A never enters the processing temp directory or ASR request. The existing playback-normalization lifecycle validates/reuses the candidate M4A; no new playback table, worker or retention path is created.

### 5. Rollback and cleanup boundary

The server is additive-first: it reads v3/v4/v5 while the v5 path is evaluated. No old baseline is installed or rehearsed while v5 passes its quality gates. If a controlled v5 gate actually fails, the operator selects and verifies a pre-v5 baseline, then rolls back only future capture; the server keeps v5 reading/processing support for every accepted v5 revision. There is no per-user toggle, silent dual fallback, second ASR job, rewrite of accepted data or rollback below a server that has v5 data.

After v5 passes its agreed control period and all historical dual processing is drained or explicitly terminal, remove the active dual capture/upload/submission and merge/echo-cleanup paths. Compatibility decoding/read/display remains only for records within retention. The cleanup is verified by source scans and negative package tests, not by deleting unknown user data.

## Validation Plan

1. Start with deterministic XCTest tests before implementation for timing, discontinuities, converter flush, artifact identity, v3/v4 compatibility, byte-weighted progress and no silent queue loss.
2. Run focused Swift tests after each capture, package or upload change, then `ContractValidation` and the rewritten recording artifact script. Test one single WAV/M4A fan-out, no v5 `mic.wav`/`incoming.wav`, source markers at start/middle/end, partial finalization and all descriptor failures.
3. Run focused server pytest contracts after each server change: source-kind role validation at session and finalize, immutable fingerprint, single-track multipart filename/type, idempotency/unknown POST handling, M4A candidate reuse, transcript import and v5 deletion.
4. Exercise a synthetic, non-private complete path locally: desktop package → upload → server finalize → fake MediaScribe single WAV result → ordered transcript status and playback status. No fixture stores spoken words or raw audio.
5. Before closeout, build/install only under the normal local test procedure and perform the controlled owner hardware run: 60 minutes with safe generated markers, local/incoming speech, overlap, silence and music; verify route unchanged, volume delta ≤1 dB, no unexplained drift >100 ms, one submit and user-visible transcript. Record metadata-only evidence.
6. Rehearse deletion using test data. Keep rollback as a documented contingency and run its install/recording rehearsal only if the v5 quality gate fails.
7. Run `bash -n` for modified scripts, `docker compose -f infra/docker-compose.yml config`, relevant companion single-WAV contract tests when available, and `infra/scripts/ci-local.sh`. Do not deploy or publish without separate approval.

## Project Structure

### Documentation (this feature)

```text
specs/106-mixed-wav-recording/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── recording-package-v5.md
│   ├── timeline-and-artifact-contract.md
│   └── processing-lifecycle-and-rollback.md
├── checklists/
│   ├── requirements.md
│   ├── audio-capture.md
│   ├── security-lifecycle.md
│   ├── ux-and-progress.md
│   └── infrastructure.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/App/TwoBrainRecApp.swift
├── RecApp/Sources/Capture/
│   ├── V5LocalRecordingWriter.swift
│   ├── RecordingAudioTimeline.swift
│   ├── CanonicalRecordingWriter.swift
│   ├── RecordingSampleSources.swift
│   ├── SystemAudioCaptureService.swift
│   ├── MicrophoneCaptureService.swift
│   ├── LocalRecordingManifestService.swift
│   └── LocalRecordingStore.swift
├── RecApp/Sources/Upload/
│   ├── DesktopUploadQueueService.swift
│   └── DesktopUploadClient.swift
├── Shared/Sources/Models/
│   ├── AudioModelCore.swift
│   ├── AudioStates.swift
│   └── SystemAudioCaptureCoreModels.swift
├── Shared/Tests/
│   ├── LocalRecordingWriterTests.swift
│   ├── LocalRecordingWriterSystemAudioTests.swift
│   ├── SystemAudioRecordingPackageTests.swift
│   ├── CanonicalRecordingManifestTests.swift
│   ├── DesktopUploadQueueV5Tests.swift
│   ├── CaptureControlV5Tests.swift
│   └── DesktopUploadClientTests.swift
├── Shared/Tools/ContractValidation/ContractValidationV5.swift
└── Scripts/validate-recording-artifact-format.sh

apps/server/
├── src/twobrain_rec_server/
│   ├── domain/statuses.py
│   ├── api/{schemas.py,ingest.py}
│   ├── ingest/{meetings.py,sessions.py,finalize.py,manifest.py,media_revisions.py}
│   ├── processing/{store.py,submit.py}
│   ├── mediascribe/client.py
│   └── normalization/service.py
└── tests/{unit,integration,contract}/

docs/integrations/mediascribe-dual-track-api.md
docs/current-product-status.md
CHANGELOG.md
```

**Structure Decision**: Reuse the native capture services, one existing upload queue/client, immutable revision model, single-track MediaScribe client, and playback normalization/deletion lifecycle. Introduce only the timestamp timeline and canonical fan-out boundaries necessary to eliminate the current two-FIFO recorder. Do not add a second recorder, audio service, database table, audio library, playback pipeline or runtime configuration layer.

## Complexity Tracking

No constitution violations or justified exceptions.
