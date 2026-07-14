# US2 Manual Media Normalization Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Tasks**: T038-T046

## Outcome

Every supported valid manual audio/video upload is now accepted once as the
authoritative `media` source, committed with its normalization job, and
dispatched to the independent playback workflow before transcript processing.
The worker verifies that exact retained source, selects audio by inspected
container bytes, fully decodes it, then byte-copies, losslessly remuxes or
transcodes into one validated profile-v1 M4A. The original source remains
unchanged and separate.

The user performs no conversion, format selection, retry, reprocess or backfill
action. A unique usable stream or unique default is selected deterministically;
ambiguous media and a corrupt selected stream fail without guessing or falling
through to another stream.

## Red receipt

Before implementation, the focused US2 run reported `22 failed`:

- manual dispatch never started the playback workflow and could not prove a
  committed job;
- the manual worker path rejected the accepted `media` role as
  `source_missing`;
- `FFmpegNormalizationPipeline` had no single-source conversion capability;
- copy/remux/transcode and stream-selection cases therefore could not run.

The initial test generator also exposed two portability details before the
green receipt: Opus requires a supported sample rate, and the Homebrew FFmpeg
build provides its native experimental Vorbis encoder rather than `libvorbis`.
The generated-fixture code now chooses valid explicit encoder arguments without
changing the accepted format contract.

## Container capability receipt

From the repository root:

```text
infra/scripts/test-playback-normalization-container.sh
```

Final result:

- media runtime: Debian Bookworm FFmpeg `5.1.9-0+deb12u1`;
- non-root, read-only root filesystem, all capabilities dropped,
  `no-new-privileges`, no network and private `0700` work tmpfs;
- 12 source matrix cases reached canonical playback by full transcode:
  WAV, MP3, raw AAC, FLAC, Ogg/Vorbis, Ogg/Opus, M4A, MP4, MOV, M4V, WebM and
  MKV;
- fully canonical fast-start M4A used `source_byte_copy` and remained byte
  identical;
- canonical-audio/non-fast-start M4A used
  `lossless_faststart_remux`;
- every output passed the pipeline's strict probe, BMFF/profile/digest gate and
  an additional complete decode;
- a non-file protocol probe was refused;
- `synthetic_residue_count=0`, `container_residue_count=0`, and
  `image_residue_count=0`;
- result: `playback_normalization_container_result=pass`.

Synthetic tones existed only inside the disposable work directory/container.
No raw media fixture was added to git.

## Integration receipt

The disposable integration runner invokes the container capability gate and
then the manual/finalize/workflow/format/reuse suite with an isolated temporary
root:

```text
infra/scripts/test-playback-normalization-integration.sh
```

Final result:

- `38 passed`;
- one pre-existing Starlette/httpx test-client deprecation warning;
- `full_decode_gate=pass`;
- `synthetic_residue_count=0`;
- exit code `0`.

The green tests prove committed-before-dispatch ordering, playback dispatch
with processing disabled, zero ProcessingWorkflow/MediaScribeJob/ProcessingResult
side effects, retained manual-source custody, wrong-extension byte detection,
the complete format matrix, canonical copy, fast-start remux, profile
transcode, unique-stream/default selection, ambiguity rejection, selected
stream decode failure without fallback, stable title precedence and durable
calendar exclusion.

Ruff for all touched US2 Python files, shell syntax checks for both runners and
`git diff --check` also passed.

## Requirement receipts

| Requirement | Receipt |
|---|---|
| FR-003 | Manual finalize creates the durable job and automatic playback dispatch; every supported real matrix case reaches a full-decoded canonical M4A. |
| FR-008 | User title remains authoritative; filename fallback remains unchanged; normalization publication does not mutate either title or title source. |
| FR-009 | The durable `skipped_manual_upload` calendar state and null event snapshot remain unchanged after normalization. |
| FR-038 | Strict canonical M4A is copied byte-for-byte, layout-only mismatch is remuxed, audio/profile mismatch is transcoded, and source/canonical artifacts remain separate. |
| FR-039 | Selection uses the only usable track or the unique default; ambiguous media and selected-stream corruption never guess, mix or fall through. |
| FR-040 | All supported valid synthetic audio/video sources converge automatically; the API exposes no conversion or repair action. |

## Success-criteria receipts

- SC-002, SC-009 and SC-020: every supported matrix input reaches ready with
  stable title behavior and no user/admin action.
- SC-004 and SC-005: accepted-source/job identity remains deterministic and
  publication retains one canonical artifact.
- SC-010: receipts contain only synthetic aliases, versions, states and counts;
  no raw media, transcript, key, URL, credential or provider content.
- SC-013 and SC-014: the worker consumes the existing accepted `media` artifact
  and no competing upload/finalize path exists.
- SC-015: only a complete validated output is published; ambiguity and decode
  failure produce no partial playback artifact.
- SC-022: scheduling is proved with processing disabled and zero processing
  rows.

## Scope truth

This receipt closes the US2 manual-media checkpoint. Automatic retry cycles,
restart reconciliation, legacy backfill, the full failure/lifecycle matrix,
Chrome playback proof, release and production closeout remain later tasks.
Feature 097 and its separate security scan were not touched. No implementation
commit was created.
