# Feature 099 Authorized Local E2E Receipt

**Date**: 2026-07-14
**Task**: T099
**Input policy**: authorized `test-rec` originals were read-only; evidence uses
safe aliases and media facts only.

## Command

```sh
cd apps/server
GRAF_TEST_REC_DIR=<authorized-test-rec> PYTHONPATH=src \
  uv run --extra dev pytest -q \
  tests/integration/test_playback_normalization_test_rec_e2e.py
```

Result: `1 passed, 1 warning in 3.43s`.

The warning is the existing Starlette `TestClient` deprecation notice. It does
not affect the media, storage, database, Range or cleanup assertions.

## Safe input preparation

- `source-a`: WAV, PCM signed 16-bit, mono, 16 kHz.
- `source-b`: WAV, PCM signed 16-bit, mono, 16 kHz.
- `source-c`: M4A, AAC-LC, mono, 48 kHz.
- Each selected original was streamed through SHA-256 before and after the run.
- Full originals were copied to a mode-`0700` feature temp directory under
  neutral aliases. Scenario inputs were bounded four-second working copies.
- FFmpeg `8.1.2` performed setup and runtime media operations without a shell.
- No original filename, audio content, transcript text, object key or FFmpeg
  diagnostic body was emitted into this receipt.

## Scenario receipts

| Safe alias | Accepted path | Durable result | Derivation | Decode | Range |
|---|---|---|---|---|---|
| `candidate-copy` | first-party manifest + two authoritative WAV sources + canonical candidate | finalized, queued, one published attempt, ready | `uploaded_candidate` | full pass | `206` and returned bytes equal stored canonical bytes |
| `candidate-remux` | first-party manifest + two authoritative WAV sources + non-faststart candidate | finalized, queued, one published attempt, ready | `lossless_faststart_remux` | full pass | `206` and returned bytes equal stored canonical bytes |
| `dual-source-fallback` | first-party manifest + two authoritative WAV sources, no candidate | finalized, queued, one published attempt, ready | `dual_source_mix_transcode` | full pass | `206` and returned bytes equal stored canonical bytes |
| `manual-m4a` | manual canonical M4A upload | accepted, queued, one published attempt, ready; source remains separately stored | `source_byte_copy` | full pass | `206` and returned bytes equal stored canonical bytes |
| `manual-wav` | manual WAV upload | accepted, queued, one published attempt, ready; source remains separately stored | `single_source_transcode` | full pass | `206` and returned bytes equal stored canonical bytes |

Every output had a positive byte length and duration, one AAC-LC audio stream,
48 kHz mono audio, faststart layout, no fragmentation and profile
`review_m4a_aac_lc_48k_mono_64k_v1` validated by
`playback_validator_v1`. First-party candidates were hidden from playback until
publication and were superseded by the canonical artifact.

## Cleanup and preservation

- Every per-job work directory was empty immediately after execution.
- Every independently re-downloaded canonical file was removed after its full
  decode and Range comparison.
- All isolated test object keys were deleted; remaining object count: `0`.
- The feature temp directory was removed; remaining temp path: absent.
- SHA-256 of all three selected originals matched the pre-run digest.
- The pytest fixture disposed its isolated SQLite database after the test.

This receipt proves local automatic conversion and server-mediated Range
playback for authorized working copies. Browser and embedded-media events are a
separate T100 gate; transient restart, corrupt input and deletion-race receipts
remain assigned to T101 and the already-focused recovery/failure suites.
