# US7 Accepted Ingest Boundary Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Tasks**: T057-T062

## Outcome

Playback normalization remains an internal consumer of the existing accepted
recording lineage. Raw parts, in-flight or unfinalized upload sessions, unknown
revisions and source-digest mismatches cannot create or execute a normalization
job. The optional playback candidate and canonical derivative do not participate
in the accepted-source fingerprint.

MediaScribe source selection now requires the exact immutable `accepted` media
revision, the source-kind-specific authoritative roles, and artifact SHA-256
values matching that revision. First-party revisions can use only microphone and
system artifacts; manual revisions can use only the single media artifact. A
competing `media` row, playback candidate, canonical playback derivative,
duplicate role, pending revision or mismatched source is rejected or ignored as
appropriate. Staged source bytes are re-hashed outside the async event loop
before any MediaScribe request.

No normalization, retry, reprocess or backfill mutation endpoint was added.
The only source-creation surfaces remain the existing server-mediated manual
upload and upload-session/finalize routes. Desktop clients still send source
audio only to GRAF and never call MediaScribe or hold its credential.

## Red receipt

Before the accepted-source selector was tightened, the focused server run
reported:

- `2 failed, 13 passed`;
- a revision changed back to `pending_upload` was still selectable for
  MediaScribe;
- an injected stored `media` artifact on a first-party revision incorrectly
  switched the request from authoritative dual-track to single-track.

The failing expectations were retained. The implementation now selects roles
from the immutable revision source kind and verifies revision/artifact digests.

## Server green receipt

From `apps/server`:

```text
uv run ruff check \
  src/twobrain_rec_server/ingest/media_revisions.py \
  src/twobrain_rec_server/processing/store.py \
  src/twobrain_rec_server/processing/submit.py \
  tests/contract/test_playback_normalization_contract.py \
  tests/integration/test_playback_normalization_finalize.py \
  tests/integration/test_mediascribe_submit.py \
  tests/unit/test_mediascribe_request_mapping.py \
  tests/contract/test_ingest_openapi_contract.py

uv run pytest -q \
  tests/contract/test_playback_normalization_contract.py \
  tests/integration/test_playback_normalization_finalize.py \
  tests/integration/test_mediascribe_submit.py \
  tests/unit/test_mediascribe_request_mapping.py \
  tests/contract/test_ingest_openapi_contract.py \
  tests/contract/test_openapi_contract_drift.py \
  tests/integration/test_processing_pickup.py \
  tests/integration/test_processing_pickup_blockers.py \
  tests/integration/test_mediascribe_processing_happy_path.py \
  tests/integration/test_processing_out_of_scope_boundaries.py \
  tests/integration/test_finalize_processing_autostart.py
```

Result:

- Ruff: all checks passed;
- pytest: `49 passed`;
- exit code: `0`;
- elapsed time: `27.53s`;
- one pre-existing Starlette/httpx test-client deprecation warning.

An additional accepted-revision/manifest/finalize/manual/no-processing/
idempotency regression run reported `32 passed`. After moving staged SHA-256
verification off the event loop, the MediaScribe/pickup subset reported
`20 passed` and explicitly proved both storage download and file hashing run off
the async loop.

## macOS SwiftPM receipt

The package declares `TwoBrainRecShared` and `TwoBrainRecAppCore` libraries,
the `TwoBrainRecApp` executable, validation executables, and the
`TwoBrainRecSharedTests` target. From `apps/macos`:

```text
swift test --filter \
  'SystemAudioRecordingPackageTests|LocalRecordingManifestTests|DesktopUploadClientTests|DesktopUploadQueueTests'
```

Result:

- debug package build: pass;
- selected tests: `121`;
- failures: `0`;
- exit code: `0`;
- test execution: `4.482s` after the build.

The receipt proves `mic.wav` and `incoming.wav` remain the required dual source
and manifest lineage; `meeting-review.m4a` is optional and absent from manifest
source tracks. When playback appears after an upload session already exists,
the session, media revision, expected source roles and idempotency key remain
unchanged. Invalid or missing optional playback never blocks the source upload.
No macOS runtime source changed in US7, so this checkpoint requires no app
rebuild or installation; the final feature-wide macOS impact gate remains T098.

## Boundary receipts

- An in-flight raw part leaves the media revision `pending_upload`, creates no
  normalization job and cannot be adopted by the internal job service.
- An unmanaged revision identifier is rejected without creating a job.
- A changed authoritative artifact digest reaches terminal `source_mismatch`
  before conversion and produces no canonical output.
- Playback candidate digest changes do not change the accepted-source
  fingerprint.
- First-party MediaScribe submission retains microphone/system mode even when
  competing media and playback derivative rows exist.
- Manual MediaScribe submission retains its accepted single media artifact and
  never uses playback as transcription input.
- Same-size object-content replacement is caught by staged SHA-256 verification
  before MediaScribe receives any bytes.
- Runtime and committed OpenAPI remain aligned and expose no competing
  normalization source or repair mutation.

## Requirement receipts

| Requirement | Receipt |
|---|---|
| FR-026 | Normalization and MediaScribe require an immutable accepted revision and exact stored authoritative artifacts; pending/raw/unmanaged inputs are rejected. |
| FR-027 | First-party, manual, retry and derivative paths keep the same meeting and media-revision identity; accepted-role hashes remain authoritative. |
| FR-028 | No new public upload/finalize/source-of-truth route exists; normalization is dispatched only after existing finalize/manual acceptance. |
| FR-033 | Missing or mismatched accepted source is not fabricated from a playback derivative or competing role; complete legacy-backfill classification remains US4. |

## Success-criteria receipts

- SC-013: every tested normalization and MediaScribe attempt uses source roles
  whose artifact digests match the existing accepted revision.
- SC-014: runtime OpenAPI, committed OpenAPI and macOS upload contracts show
  zero competing source-of-truth paths.
- SC-015: candidate/derivative objects cannot be promoted into transcription
  source truth or normalization source custody.
- SC-022: accepted-source dispatch remains attached to existing finalize and
  independent from transcript completion.

## Scope truth

This receipt closes the US7 accepted-ingest checkpoint. Legacy backfill and its
full FR-033 behavior, the impossible-media matrix, deletion/retention races,
production worker/deploy readiness, Chrome evidence, release and production
closeout remain later tasks. Feature 097 and its separate Codex Security scan
were not touched. No implementation commit was created.
