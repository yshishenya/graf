# Quickstart: verify the v5 recording pipeline

## Safety Preconditions

- Work only in `106-mixed-wav-recording`; preserve the canonical checkout and feature-103/other worktrees.
- Use deterministic non-private signals and metadata-only evidence. Do not add audio files, spoken text, transcripts, credentials, signed URLs or private paths to git, fixtures or reports.
- Do not deploy, publish, tag or install a release without its separate approval gate.

## Focused macOS checks

Run these after changes to the indicated boundary. Test filters may be narrowed to the changed test class while developing; run the listed group before its story is marked complete.

```sh
swift test --package-path apps/macos --filter 'LocalRecordingWriterTests|LocalRecordingWriterSystemAudioTests|SystemAudioRecordingPackageTests|LocalRecordingManifestTests|DesktopUploadClientTests|DesktopUploadQueueTests'

swift run --package-path apps/macos ContractValidation

sh apps/macos/Scripts/validate-recording-artifact-format.sh
```

Expected v5 assertions:

- exactly `manifest.json`, `meeting-transcription.wav` and `meeting-review.m4a` are final members;
- WAV is PCM s16le, mono, 16 kHz; M4A is AAC-LC, mono, 48 kHz;
- no v5 package contains `mic.wav`, `incoming.wav`, raw source or `.partial`;
- deterministic markers at beginning/middle/end maintain ≤100 ms WAV/M4A divergence across the 60-minute synthetic timeline;
- no overflow/drop/flush/partial artifact reaches `ready`;
- upload progress is byte-weighted, monotonic and has an observed intermediate value between 0 and 100 percent.

## Focused server checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_manifest_validation.py \
  tests/unit/test_media_revision_state_machine.py \
  tests/integration/test_ingest_happy_path.py \
  tests/integration/test_media_revision_identity.py \
  tests/integration/test_finalize_integrity.py \
  tests/integration/test_mediascribe_processing_happy_path.py \
  tests/integration/test_processing_result_idempotency.py \
  tests/integration/test_processing_worker_restart.py \
  tests/integration/test_processing_failures.py \
  tests/integration/test_processing_deletion_dependency.py \
  tests/integration/test_playback_normalization_finalize.py \
  tests/integration/test_playback_normalization_reuse.py

PYTHONPATH=src uv run --extra dev ruff check .
```

Expected v5 assertions:

- source-kind-aware accept/reject at upload session and finalization;
- immutable `initial_mixed_recording` revision with one authoritative `media` digest and playback excluded from source fingerprint;
- exactly one `.wav` / `audio/wav` single-track multipart submission and no M4A/microphone/system field;
- unknown POST/restart creates no second submission;
- playback candidate reuse and deletion cover both v5 audio artifacts;
- historical v3/v4 packages continue through their compatibility path.

## Synthetic end-to-end path

1. Generate deterministic non-private marker fixtures in a temporary ignored directory; do not commit them.
2. Use the native writer tests and fake MediaScribe client to create v5 package → upload → finalize → one single-track result import.
3. Verify the server stores one revision-bound result and independent playback state, with no dual merge output.
4. Delete the synthetic meeting and verify source/playback/temp/processing lifecycle truth and local purge acknowledgement behavior.

## Installed-app hardware acceptance

This is mandatory before closeout because unit tests cannot prove real device clock correlation or actual audible volume.

1. Build/install the candidate using the approved normal local test procedure.
2. Record 60 minutes with a safe generated fixture: markers near 0/30/60 minutes, local speech, incoming speech, overlap, silence and music.
3. Before/during/after recording verify selected playback route is unchanged and incoming level delta is ≤1 dB.
4. Inspect only metadata: exact package members/formats, durations, hashes, marker timing, gap/drop counts and status codes. WAV/decoded M4A/transcript timelines must differ by ≤100 ms beyond separately recorded AAC priming.
5. Upload through the desktop app. Confirm real progress moves before the final artifact, server accepts `media` + `playback`, and only `media` is sent to one ASR job.
6. Confirm playback and one chronological user-visible transcript result. The transcript check records pass/fail/count/timestamps only, never content.
7. Repeat with deletion and a rollback rehearsal on test data. Rollback affects a subsequent recording only.

## Closeout

```sh
bash -n apps/macos/Scripts/validate-recording-artifact-format.sh
docker compose -f infra/docker-compose.yml config
infra/scripts/ci-local.sh
git diff --check
```

Run companion MediaScribe single-WAV tests only against a clean, explicitly scoped companion worktree; do not merge its unrelated uncommitted WIP. Do not claim deployed/provider proof until a separately authorized deployment test has completed.
