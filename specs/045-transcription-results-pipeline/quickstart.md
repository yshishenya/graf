# Quickstart: Transcription Results Pipeline

## Goal

Validate that structurally valid recordings are uploaded and processed even
when local audio quality readiness is imperfect, and that transcription results
become visible in both web and desktop review through the server-owned path.

## Prerequisites

- Local macOS package tests can run.
- Server test dependencies are installed.
- MediaScribe integration tests use fakes unless an explicit live validation
  run is approved.
- Evidence must be metadata-only.

## Focused Local Validation

Run macOS upload eligibility and manifest tests:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter DesktopUploadQueueTests
swift test --package-path apps/macos --disable-swift-testing --filter LocalRecordingLeakageFinalizationTests
swift test --package-path apps/macos --disable-swift-testing --filter LocalRecordingManifestTests
```

Expected outcomes:

- Structurally valid packages with leakage, echo, silence, timing, or
  transcription-readiness warnings are upload eligible.
- Missing files, unreadable files, consent failure, and permission failure stay
  blocked.
- Diagnostic bundles remain content-safe.

## Focused Server Validation

Run server ingest, processing, and review tests:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_finalize_integrity.py \
  tests/integration/test_processing_pickup.py \
  tests/integration/test_processing_pickup_blockers.py \
  tests/integration/test_mediascribe_processing_happy_path.py \
  tests/contract/test_processing_status_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py
```

Expected outcomes:

- Finalization still rejects role, size, checksum, and immutable fingerprint
  mismatches.
- Accepted packages start or reuse processing when processing is enabled.
- Dependency unavailable states remain visible and content-safe.
- Imported transcript and diarization availability reaches cabinet review.
- Status and evidence payloads do not contain raw audio or transcript text.

## End-To-End Smoke

Use a synthetic or explicitly approved private-safe recording package:

1. Record or prepare a dual-track package with valid manifest, microphone, and
   incoming/system audio files.
2. Mark local quality/leakage readiness as imperfect in a controlled fixture.
3. Upload and finalize through the desktop/server path.
4. Confirm upload accepted and processing state becomes visible without manual
   operator pickup when processing is enabled.
5. Let fake or approved MediaScribe processing import a result.
6. Open web review and desktop embedded review for the same meeting.
7. Confirm both surfaces show matching upload, processing, transcript, and
   diarization availability.

Evidence to record:

- package eligibility state;
- upload finalization status;
- processing status progression;
- transcript and diarization availability booleans;
- web/desktop review state match;
- validation commands and pass/fail result.

Evidence not allowed:

- raw audio;
- transcript text;
- participant names or private meeting content;
- credentials;
- signed URLs;
- private local paths.

## One-Hour Orchestration Benchmark

Use a one-hour synthetic or explicitly approved private-safe recording package.
If the transcription dependency is faked, configure the fake to return a ready
result without transcript text in logs or evidence.

Measure and record:

- time from upload finalization to visible processing state;
- product-owned orchestration time before transcription submission;
- product-owned orchestration time after result availability;
- duplicate job/result count for retries during the benchmark;
- metadata-safe command names and pass/fail result.

Expected outcomes:

- visible processing state appears within 60 seconds in a healthy processing
  environment;
- product-owned orchestration before submission and after ready result
  availability completes in under 3 minutes total;
- no raw audio, transcript text, private meeting content, credentials, signed
  URLs, secret paths, or private local paths are recorded in evidence.

## Full Regression Gate

Run the repository gate before implementation closeout:

```sh
infra/scripts/ci-local.sh
```

If release or production proof is requested, follow
`docs/agent-guidance/release-and-validation.md`.
