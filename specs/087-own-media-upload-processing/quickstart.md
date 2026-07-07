# Quickstart: Own Media Upload Processing

## Prerequisites

- Run from repository root.
- Server dev/test dependencies installed.
- No production credentials are required; tests use fakes.

## Focused Validation

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_manifest_validation.py \
  tests/unit/test_mediascribe_request_mapping.py \
  tests/integration/test_manual_media_upload.py \
  tests/integration/test_mediascribe_submit.py \
  tests/integration/test_mediascribe_processing_happy_path.py \
  tests/integration/test_recording_sync_processing.py
```

Expected:

- One-track manual upload finalizes with `manifest + media`.
- One-track MediaScribe request uses `POST /v1/audio/transcriptions` with one
  `file` field.
- Dual-track MediaScribe request still uses `mic_file` and `incoming_file`.
- Duplicate one-track retry reuses stored dependency job id.
- Imported one-track transcript produces review-visible outcomes.

## Contract Drift Check

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_ingest_openapi_contract.py
```

Expected:

- Existing ingest contract remains server-mediated.
- Manual media upload contract is visible without leaking dependency secrets.

## Repository Gate

```sh
infra/scripts/ci-local.sh
```

Expected:

- Full local gate passes before closeout.

## Out Of Scope

- Production deploy.
- Browser upload UI polish.
- New ffmpeg/transcoding dependency.
- Transcript editing or speaker correction.
- MediaScribe deletion confirmation beyond existing dependency state.
