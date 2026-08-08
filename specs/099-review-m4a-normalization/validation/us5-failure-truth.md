# US5 Failure Truth Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Tasks**: T073-T080

## Outcome

GRAF now separates objectively unusable source media from recoverable server
failures without asking the user or a workspace administrator to repair the
recording. Empty, corrupt, encrypted, no-audio, ambiguous-audio, unsupported,
over-limit, missing and fingerprint-mismatched sources terminate with one
durable safe reason. Temporary storage, database, dependency, timeout, process
output, worker interruption, publish interruption and generated-output failures
remain in automatic recovery.

Only one validated canonical playback artifact can become ready. A failed,
partial, truncated, unpublished or invalidly receipted output is cleaned by the
server, never exposed as playback and never replaces the retained accepted
source. The browser receives bounded Russian copy; the same reason catalogue has
bounded English copy. Neither language tells the user to retry, re-upload,
contact an administrator or run a repair action.

## Red receipt

The first combined US5 run reported `8 failed, 119 passed`. Three failures were
the intended missing product behavior:

- an empty local source reached FFprobe and became `corrupt_source` instead of
  being rejected as `empty_source` before tool execution;
- an authoritative encrypted audio tag (`enca`) was not parsed and classified;
- the centralized bounded RU/EN playback-reason projection did not exist.

Five failures exposed retained test/setup/toolchain truth rather than missing
conversion behavior: a whole model was compared instead of its six public
playback fields, the deletion-precedence fixture omitted its required terminal
timestamp, a stale local Pydantic environment did not understand `exclude_if`,
the old browser-shell assertion rejected legitimate GET polling, and committed
OpenAPI truth needed to match the pinned Pydantic/FastAPI versions. Those were
corrected without weakening playback, privacy, deletion or no-user-work gates.

## Focused green receipt

From `apps/server`:

```text
uv run --extra dev pytest -q \
  tests/integration/test_playback_normalization_media_matrix.py \
  tests/integration/test_playback_normalization_failures.py \
  tests/integration/test_playback_normalization_retry.py \
  tests/integration/test_playback_normalization_incidents.py \
  tests/integration/test_playback_normalization_backfill.py \
  tests/contract/test_playback_status_contract.py \
  tests/contract/test_playback_normalization_no_secret_egress.py \
  tests/unit/test_playback_normalization_selection.py \
  tests/unit/test_playback_normalization_profile.py \
  tests/unit/test_playback_normalization_state.py \
  tests/unit/test_playback_normalization_audit.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py

uv run --extra dev ruff check .
git diff --check
```

Result:

- pytest: `191 passed`;
- exit code: `0`;
- elapsed time: `14.47s`;
- project-pinned Ruff `0.15.20`: all checks passed;
- diff whitespace check: passed;
- one non-blocking pre-existing Starlette/httpx test-client deprecation warning.

The manual-upload response and canonical OpenAPI projection were rerun after the
toolchain-compatible optional-field fix: `12 passed`, exit code `0`. Runtime
OpenAPI and `specs/012-server-ingest-foundation/contracts/openapi.yaml` are
byte-structure equivalent under pinned Pydantic `2.13.4` and FastAPI `0.138.1`.

## Media runtime and integration receipt

From the repository root:

```text
infra/scripts/test-playback-normalization-integration.sh
```

Result:

- media image built with FFmpeg `5.1.9-0+deb12u1`;
- container ran non-root with no network, read-only root filesystem, all Linux
  capabilities dropped, `no-new-privileges`, one CPU, 1 GiB memory, 128 PIDs and
  a private 512 MiB `noexec,nosuid,nodev` work tmpfs;
- 14 runtime cases passed: WAV, MP3, AAC, FLAC, Ogg/Vorbis, Ogg/Opus, M4A, MP4,
  MOV, M4V, WebM, MKV, canonical byte-copy and non-faststart lossless remux;
- every produced artifact passed full decode;
- non-file protocol input was refused;
- host integration: `56 passed` in `8.64s`;
- `playback_normalization_container_result=pass`;
- `playback_normalization_integration_result=pass`;
- container residue `0`, image residue `0`, synthetic file residue `0`.

The first two build attempts stopped while the base image tried to download
FFmpeg packages from the Debian HTTP mirror. The same mirror was reachable over
HTTPS. The Dockerfile now switches the signed Debian source definitions to
HTTPS before `apt-get`; the unchanged capability and integration scenario then
passed completely. This was build-transport recovery, not a conversion bypass.

## Permanent-source matrix

The following durable reasons are `permanent_source` and cannot create a public
retry or a ready artifact:

- `empty_source`, rejected before FFprobe;
- `corrupt_source`;
- `encrypted_media`, recognized from the authoritative audio stream tag without
  codec guessing;
- `no_audio`;
- `ambiguous_audio_tracks`;
- `unsupported_container` and `unsupported_codec`;
- `stream_limit_exceeded`, `duration_limit_exceeded` and
  `source_size_limit_exceeded`;
- `source_missing` and `source_mismatch`.

The real synthetic media matrix also proves that supported content is detected
by bytes rather than filename extension, a unique usable stream is selected, a
unique default stream wins deterministically, equal candidates terminate as
ambiguous, and a selected-stream decode failure never silently falls back to a
different track.

## Automatic-recovery and cleanup matrix

Runtime exceptions map safely as follows:

| Failure | Durable retry reason |
|---|---|
| worker cancellation | `worker_interrupted` |
| database exception | `database_unavailable` |
| process timeout | `normalization_timeout` |
| local filesystem failure | `temporary_storage_unavailable` |
| interrupted publication | `publish_interrupted` |
| unavailable media dependency or bounded process-output overflow | `dependency_unavailable` |
| invalid generated output or invalid validation receipt | `generated_output_invalid` |

For every exercised case the job ended in `retry_wait` with a future automatic
attempt, the attempt ended `cleaned`, local partial output was removed, no
canonical playback row was published, accepted-source objects were unchanged
and the private work directory was empty.

## Status, copy, precedence and privacy receipts

- List and detail project the same durable playback state. Playback readiness is
  independent of transcript/diarization/notes readiness.
- Deleting/deleted truth takes precedence over access and terminal media truth.
  An accepted revision with no job projects automatic reconciliation rather
  than a dead unavailable state.
- All public preparing, ready, access, terminal and deletion reasons have
  bounded RU/EN text plus a generic safe fallback. Public terminal categories
  intentionally coarsen container/codec and resource subreasons.
- HTML renders terminal truth as plain status. It contains no retry, reprocess,
  repair, re-upload or contact-admin control.
- Responses, incidents and evidence contain no filename, object key/URL,
  provider/process payload, raw audio, transcript, summary, credential or
  secret-path material.
- Impossible legacy missing/mismatched sources create one metadata-only incident
  per job/reason. Replays remain deduplicated. Exhausted automatic recovery uses
  the same metadata-only cooldown incident boundary.

## Requirement receipts

| Requirement | Receipt |
|---|---|
| FR-011 | Objective source failures become terminal; server/resource/output failures remain automatic retries with no user action. |
| FR-012 | Durable reason classes and public coarse categories distinguish unsupported source truth from infrastructure recovery. |
| FR-013 | Partial, truncated, failed, unpublished and invalidly receipted outputs never become ready and are server-cleaned. |
| FR-021 | Stream, duration, output and runtime resource bounds fail closed without exposing partial playback. |
| FR-031 | Storage, database, dependency, worker, timeout and publication failures have explicit automatic ownership. |
| FR-037 | Public copy, incidents, logs asserted by tests and this receipt remain metadata-only and contain no forbidden content. |
| FR-039 | Only one unique usable/default audio stream is selected; equal candidates terminate without guessing. |
| FR-040 | Every tested supported valid format converges automatically; only objectively unusable media terminates. |

## Success-criteria receipts

- SC-010: every tested response and incident remains inside the metadata-only
  allowlist.
- SC-015: zero partial, failed or unvalidated artifacts projected ready.
- SC-020: supported files require no user or administrator repair action.

## Limitations and scope truth

The encrypted-media rule is tested from the exact bounded FFprobe
`codec_tag_string=enca` fact. A copyrighted or access-controlled DRM sample is
not committed to the repository; therefore this receipt does not claim an
end-to-end decode attempt of third-party protected content. The correct product
behavior for such content is truthful terminal status, not decryption.

The successful format fixtures are locally generated deterministic synthetic
media. They exercise the real FFmpeg/FFprobe binaries and full-decode gate but
contain no private meeting content. Absolute success for arbitrary corrupt,
encrypted or future unknown formats is intentionally not promised; the product
guarantee is automatic convergence for the validated supported matrix and safe
terminal truth for objectively unusable input.

This receipt closes US5. Deletion/retention races, complete tenant/RLS checks,
worker readiness, rollout/rollback and deployment gates remain US6. No macOS
runtime source changed in US5, so this checkpoint requires no app rebuild or
installation. Feature 097 and its separate Codex Security scan were not touched.
No implementation commit was created.
