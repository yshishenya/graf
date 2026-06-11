# 2brain Rec Server

Backend ingest and processing foundation for finalized local recording artifacts.

The `012-server-ingest-foundation` slice is intentionally server-mediated:
desktop clients call the 2brain Rec API, and the server writes validated bytes
to owner-controlled MinIO. That slice does not expose direct object-storage
upload URLs, start Temporal workflows, call MediaScribe, or emit
content-bearing diagnostics.

The `015-mediascribe-processing-pipeline` slice adds the first server-side
processing path after ingest finalization. Eligible finalized meetings can be
picked up with an idempotent `processing/<meeting_id>` Temporal workflow id,
submitted to MediaScribe from server-controlled mic/system artifacts, polled,
and imported into durable transcript/diarization tables. Desktop clients still
never receive MediaScribe credentials, signed dependency URLs, or raw storage
paths.

## Observability Boundary

Logs, problem responses, and audit metadata may include request IDs, tenant-scoped IDs, lifecycle statuses, byte counts, checksum identifiers, error codes, and timing information. They must not include raw audio, transcript text, bearer tokens, MinIO credentials, MediaScribe credentials, signed URLs, passwords, or live secret paths.

Readiness checks cover API configuration, Postgres, MinIO, ingest limits, and
processing dependency configuration. Temporal and MediaScribe remain separate
processing dependency signals: accepted ingest readiness is not evidence that
transcription is available unless processing is explicitly enabled and its
dependency checks are configured.

## Local Processing Flow

Default local validation uses fake Temporal and fake MediaScribe adapters in
tests. Real dependency smoke requires operator-provisioned secret files and must
not be run with committed placeholders.

```sh
cd apps/server
uv run --extra dev pytest -q tests/contract/test_processing_status_contract.py \
  tests/contract/test_mediascribe_client_contract.py \
  tests/integration/test_processing_pickup.py \
  tests/integration/test_mediascribe_processing_happy_path.py
```

Processing config placeholders live in `.env.example` and production config
templates. Real MediaScribe API keys must be mounted through
`TWOBRAIN_MEDIASCRIBE_API_KEY_FILE`; do not put key values in `.env`, Compose,
docs, logs, or evidence files.

## Not Implemented In 012

The server does not expose transcript download, summary download, audio
download, public share links, login-required share pages, team-wide browsing,
privileged admin review, dashboard meeting detail, deletion execution, indexing,
or assisted auto-recording endpoints. Later slices may add those surfaces after
the required dashboard, access, retention, and deletion specs are complete.
