# Quickstart: Dual Audio Formats

Run from repository root:

```sh
cd /Users/yshishenya/.codex/worktrees/fd8e/crisp
```

## 1. Verify macOS recording artifacts

```sh
swift test --package-path apps/macos --filter SystemAudioRecordingPackageTests
```

Expected:

- `mic.wav` and `incoming.wav` are still created and accepted as transcription
  tracks.
- `meeting-review.m4a` is written from the capture-rate path when both sources
  are present.
- The M4A derivative does not change manifest transcription roles.

## 2. Verify desktop upload descriptors and queue safety

```sh
swift test --package-path apps/macos --filter DesktopUploadClientTests
swift test --package-path apps/macos --filter DesktopUploadQueueTests
```

Expected:

- Required upload descriptors remain `microphone`, `system`, and `manifest`.
- A validated M4A adds optional `playback`.
- Random bytes or WAV content renamed to `meeting-review.m4a` do not add
  `playback`.
- Existing upload session truth is preserved when optional playback appears
  later; retry uses the server session's expected roles and skips unexpected
  local playback descriptors.

## 3. Verify server playback contract

```sh
(cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_cabinet_playback_contract.py)
(cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_playback_route.py)
```

Expected:

- Meeting review state can report `stored_review_m4a`.
- Playback route prefers stored M4A and returns `audio/mp4`.
- Playback route keeps byte-range support.
- Playback route falls back to generated WAV when stored M4A bytes are missing
  but both retained WAV sources exist.
- Access denied, deleting/deleted, malformed range, and unavailable states fail
  closed without storage details.

## 4. Verify download/export policy separation

```sh
(cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_artifact_egress_policy.py)
```

Expected:

- Allowed audio download returns `meeting-review.m4a` when stored playback audio
  exists.
- Disabled export/download does not block in-page playback but blocks direct
  download/export.
- Export manifests and activity endpoints stay metadata-only.

## 5. Verify storage missing-object normalization

```sh
(cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_minio_async_wrappers.py)
```

Expected:

- Missing stored playback object is normalized to `KeyError` and can trigger
  safe fallback.
- Non-missing storage errors are preserved.

## 6. Run repository gate

```sh
infra/scripts/ci-local.sh
```

Expected:

- Canonical local CI passes before PR or release closeout.

## Evidence Rules

Record only command names, pass/fail status, and metadata-safe summaries. Do not
commit raw audio, transcript text, credentials, signed URLs, storage object keys,
private local paths, or private meeting content.
