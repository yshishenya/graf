# Quickstart: Server Ingest Foundation

This quickstart defines the validation scenarios for 012. The commands reference paths that the implementation tasks will create.

## 1. Start Local Ingest Stack

Local development runs the full Rec stack through `infra/docker-compose.dev.yml`: API, Postgres, and MinIO.

```sh
docker compose -f infra/docker-compose.dev.yml up --build
```

Expected:

- API listens on `http://localhost:8080`.
- Postgres is reachable by the API.
- MinIO bucket exists and is server-owned.
- `GET http://localhost:8080/api/v1/health/live` returns `200`.
- `GET http://localhost:8080/api/v1/health/ready` returns `200` when Postgres, MinIO, and ingest config are valid.
- Readiness does not require Temporal or MediaScribe.

## 2. Validate Production Compose Configuration

Production on `2brain.pro` runs a separate Rec-owned Docker Compose project through `infra/docker-compose.yml`: API, Postgres, MinIO, dedicated volumes, dedicated network, and secret placeholders.

```sh
docker compose -f infra/docker-compose.yml config
```

Expected:

- Compose defines Rec-owned API, Postgres, and MinIO services.
- Compose defines dedicated Rec volumes for Postgres and MinIO data.
- Compose uses secret placeholders or external secret references, not literal credentials.
- API environment points at the Rec Postgres and Rec MinIO service names inside the compose network.
- Production 012 runtime configuration does not point at a shared platform MinIO/Postgres instance.
- Readiness depends on Rec Postgres and Rec MinIO only; Temporal and MediaScribe are not required in 012.

## 3. Run Server Test Suite

```sh
cd apps/server
pytest
```

Expected:

- Unit tests cover limit validation, tenant authorization checks, idempotency, checksum conflicts, and status transitions.
- Contract tests validate `contracts/openapi.yaml`.
- Integration tests use the Docker Compose Postgres/MinIO stack or deterministic test doubles where explicitly scoped.

## 4. Happy Path Upload

```sh
python apps/server/scripts/create_test_artifact.py \
  --duration-seconds 1800 \
  --out /tmp/2brain-rec-fixtures/meeting-30m

python apps/server/scripts/upload_test_artifact.py \
  --api http://localhost:8080 \
  --workspace "$TEST_WORKSPACE_ID" \
  --device "$TEST_DEVICE_ID" \
  --token "$TEST_BEARER_TOKEN" \
  --artifact /tmp/2brain-rec-fixtures/meeting-30m
```

Expected:

- Meeting is created or idempotently resolved.
- Upload strategy is `server_mediated`.
- Microphone, system, and manifest parts are accepted.
- Finalize returns `meeting.status=ingested_pending_processing`.
- `workflow_started=false` and `mediascribe_job_created=false`.
- MinIO contains tenant-scoped stored objects.
- Postgres contains meeting, upload session, track artifact, processing placeholder, and audit metadata.

## 5. 60-Minute Fixture

```sh
python apps/server/scripts/create_test_artifact.py \
  --duration-seconds 3600 \
  --out /tmp/2brain-rec-fixtures/meeting-60m

python apps/server/scripts/upload_test_artifact.py \
  --api http://localhost:8080 \
  --workspace "$TEST_WORKSPACE_ID" \
  --device "$TEST_DEVICE_ID" \
  --token "$TEST_BEARER_TOKEN" \
  --artifact /tmp/2brain-rec-fixtures/meeting-60m
```

Expected:

- The 60-minute dual-track package finalizes within configured limits.
- The API never loads whole tracks into memory at once.

## 6. Retry And Resume

Run the upload helper with an intentional interruption after at least one accepted part:

```sh
python apps/server/scripts/upload_test_artifact.py \
  --api http://localhost:8080 \
  --workspace "$TEST_WORKSPACE_ID" \
  --device "$TEST_DEVICE_ID" \
  --token "$TEST_BEARER_TOKEN" \
  --artifact /tmp/2brain-rec-fixtures/meeting-30m \
  --stop-after-parts 2
```

Then rerun without interruption.

Expected:

- Previously accepted parts are returned as accepted/idempotent.
- `GET /api/v1/upload-sessions/{session_id}/missing-ranges` returns only missing ranges.
- Finalize succeeds once all required bytes and checksums match.

## 7. Idempotency Conflict

Replay an accepted part number with a different checksum.

Expected:

- API returns `409 checksum_conflict`.
- Existing accepted bytes and object metadata are not replaced.
- Audit event records safe metadata only.

## 8. Cross-Tenant And Revoked Device Denial

Use a valid token from workspace A with a workspace B session, then revoke a device and retry status/upload requests.

Expected:

- Cross-tenant requests return `403` or `404` according to the endpoint contract without revealing foreign resource details.
- Revoked devices cannot create, upload, finalize, abort, or read sessions.
- No audio/object details are leaked in errors.

## 9. Over-Limit Rejection

Generate artifacts that exceed duration, track bytes, and package bytes.

Expected:

- API returns `413` with one of:
  - `recording_duration_limit_exceeded`
  - `track_size_limit_exceeded`
  - `package_size_limit_exceeded`
- Meeting/session status is `failed` or `degraded` according to how far the upload progressed.
- No finalized meeting is produced.
- Response includes the exceeded limit name/value but not internal storage paths or secrets.

## 10. No Workflow Or MediaScribe Side Effects

After successful finalize, inspect configured processing placeholders and runtime dependencies.

Expected:

- `processing_status` is `not_submitted` or `pending_processing`.
- `workflow_id` is null.
- `mediascribe_job_id` is null.
- No Temporal workflow execution is created.
- No MediaScribe request is sent.

## 11. Log And Secret Leak Check

```sh
docker compose -f infra/docker-compose.dev.yml logs api > /tmp/2brain-rec-api.log
```

Expected:

- Logs contain safe metadata: IDs, statuses, byte counts, checksums, error codes, trace IDs.
- Logs do not contain raw audio bytes, transcript text, bearer tokens, MinIO credentials, MediaScribe credentials, signed URLs, or secret values.

## 12. RLS Hardening Register

Before moving beyond internal MVP, confirm the follow-up is still visible:

```sh
rg "RLS-hardening|Row Level Security" docs specs/012-server-ingest-foundation
```

Expected:

- Application-level tenant tests pass in 012.
- PostgreSQL RLS remains tracked as `RLS-hardening` until implemented or explicitly risk-accepted.
