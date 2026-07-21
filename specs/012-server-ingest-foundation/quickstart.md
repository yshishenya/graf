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

Seed deterministic local identity/device records for smoke uploads:

```sh
cd apps/server
PYTHONPATH=src python scripts/seed_dev_identity.py --print-headers
```

Use the printed values as:

- `TEST_ORGANIZATION_ID`
- `TEST_WORKSPACE_ID`
- `TEST_USER_ID`
- `TEST_DEVICE_ID`

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
  --organization "$TEST_ORGANIZATION_ID" \
  --workspace "$TEST_WORKSPACE_ID" \
  --user "$TEST_USER_ID" \
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
  --organization "$TEST_ORGANIZATION_ID" \
  --workspace "$TEST_WORKSPACE_ID" \
  --user "$TEST_USER_ID" \
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
  --organization "$TEST_ORGANIZATION_ID" \
  --workspace "$TEST_WORKSPACE_ID" \
  --user "$TEST_USER_ID" \
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

- API returns `400` or `413` with one of:
  - `recording_duration_exceeded`
  - `track_bytes_exceeded`
  - `package_bytes_exceeded`
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

## 13. Implementation Evidence

Recorded on 2026-06-04:

- `cd apps/server && PYTHONPATH=src pytest -q` -> `27 passed`.
- `python -m compileall -q apps/server/src apps/server/tests apps/server/scripts` -> pass.
- `docker compose -f infra/docker-compose.dev.yml config` -> pass.
- `TWOBRAIN_POSTGRES_PASSWORD=dummy TWOBRAIN_MINIO_ACCESS_KEY=dummy TWOBRAIN_MINIO_SECRET_KEY=dummy docker compose -f infra/docker-compose.yml config` -> pass.
- `git diff -- apps/macos/Package.swift` -> no diff; 012 did not modify the macOS driver/uploader package.
- Secret/content scan found only local development placeholders and redaction test strings, not production credentials:
  - `infra/docker-compose.dev.yml` uses `twobrain_rec_dev_secret` for local-only MinIO/Postgres development.
  - `apps/server/tests/unit/test_redaction.py` intentionally includes a fake bearer value to verify redaction.
  - Redaction key names such as `mediascribe_api_key` and `signed_url` appear only as blocked field names.

Review remediation recorded on 2026-06-04:

- Final sanity review blockers were captured as Phase 10 tasks T106-T118 and GitHub issues #107-#111.
- `cd apps/server && PYTHONPATH=src pytest -q` -> `36 passed`.
- `cd apps/server && PYTHONPATH=src ruff check .` -> pass.
- `python -m compileall -q apps/server/src apps/server/tests apps/server/scripts` -> pass.
- `docker compose -f infra/docker-compose.dev.yml config` -> pass.
- `TWOBRAIN_POSTGRES_PASSWORD=dummy TWOBRAIN_MINIO_ACCESS_KEY=dummy TWOBRAIN_MINIO_SECRET_KEY=dummy docker compose -f infra/docker-compose.yml config` -> pass.
- Secret/content scan found only expected deployment placeholders, local development placeholders, and redaction test strings:
  - production compose uses required environment placeholders for Postgres and MinIO secrets;
  - `infra/docker-compose.dev.yml` and `apps/server/src/twobrain_rec_server/config.py` retain local-only development defaults;
  - `apps/server/tests/unit/test_redaction.py` intentionally includes a fake bearer value to verify redaction;
  - `mediascribe_api_key` and `signed_url` appear only as blocked field names.

Second review hackathon verdict recorded on 2026-06-04:

- Five read-only review agents completed five rounds: independent review, cross-check,
  new-finding search, devil's-advocate ranking, and final last-look vote.
- All five agents voted that the current 012 changes are not PR-ready until the
  Phase 11 tasks T119-T180 are completed.
- Confirmed blocker issue packages:
  - #112 finalize integrity and artifact provenance;
  - #113 session lifecycle, idempotency, and cold persistence;
  - #114 tenant auth, audit, and privacy hardening;
  - #115 resumable ranges, limits, and streaming upload;
  - #116 OpenAPI contract and readiness alignment;
  - #117 production runtime and compose hardening;
  - #118 quickstart, helper script, and status docs;
  - #119 Postgres/Alembic/MinIO proof gates and bootstrap.
- Confirmed additional issue packages:
  - #120 finalize/audit cleanup consistency;
  - #121 metadata model and placeholder completeness;
  - #122 API validation and Problem responses;
  - #123 readiness, docs exposure, logging, and async storage;
  - #124 test hygiene and production config coverage.
- Do not use the earlier `36 passed` evidence as PR readiness evidence; it is now
  known to miss true Postgres/Alembic, real MinIO, cold-start, OpenAPI contract,
  finalize integrity, and streaming-upload blockers.

Final sanity remediation evidence recorded on 2026-06-04:

- Final sanity review packages were captured as Phase 12 tasks T181-T195 and
  GitHub issues #127-#131.
- `cd apps/server && uv run --extra dev pytest -q` -> `115 passed`.
- `cd apps/server && uv run --extra dev ruff check .` -> pass.
- `cd apps/server && uv run python -m compileall -q src tests scripts` -> pass.
- `docker compose -f infra/docker-compose.dev.yml config` -> pass.
- `TWOBRAIN_POSTGRES_PASSWORD=dummy TWOBRAIN_MINIO_ROOT_USER=rootuser TWOBRAIN_MINIO_ROOT_PASSWORD=rootsecret TWOBRAIN_MINIO_API_ACCESS_KEY=twobrain_rec_api TWOBRAIN_MINIO_API_SECRET_KEY=apisecret docker compose -f infra/docker-compose.yml config` -> pass.
- Empty-schema readiness is covered by
  `apps/server/tests/integration/test_health_readiness.py::test_ready_reports_not_ready_when_database_schema_is_empty`.
- Alembic clean-database bootstrap is covered by
  `apps/server/tests/integration/test_postgres_migrations.py::test_clean_database_migrates_and_accepts_seeded_identity_request`.
- OpenAPI drift is covered by
  `apps/server/tests/contract/test_openapi_contract_drift.py::test_runtime_openapi_matches_committed_contract`
  plus `ValidationError.input` / `ValidationError.ctx` assertions.
- Secret/content scan found only expected local development placeholders and
  redaction test strings; no production credentials were committed.

Pre-merge polish evidence recorded on 2026-06-04:

- Residual warning cleanup was captured as Phase 13 tasks T196-T200 and GitHub
  issues #132-#133.
- `cd apps/server && uv run --extra dev pytest -q -W error` -> `115 passed`.
- `cd apps/server && uv run --extra dev ruff check .` -> pass.
- `cd apps/server && uv run python -m compileall -q src tests scripts` -> pass.
- `docker compose -f infra/docker-compose.dev.yml config` -> pass.
- `TWOBRAIN_POSTGRES_PASSWORD=dummy TWOBRAIN_MINIO_ROOT_USER=rootuser TWOBRAIN_MINIO_ROOT_PASSWORD=rootsecret TWOBRAIN_MINIO_API_ACCESS_KEY=twobrain_rec_api TWOBRAIN_MINIO_API_SECRET_KEY=apisecret docker compose -f infra/docker-compose.yml config` -> pass.
- `python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py`
  -> OK (2 Spec Kit issues checked).
- The previous Starlette TestClient and Alembic config warnings are gone. The
  warnings-as-errors run also proved upload spool and SQLite test engine
  resources are closed cleanly.

Phase 11 partial remediation evidence recorded on 2026-06-04:

- #112 finalize integrity and artifact provenance remediation completed for
  Spec Kit tasks T119, T125, T132, and T133.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_finalize_integrity.py apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/unit/test_manifest_validation.py` -> `10 passed`.
- `cd apps/server && PYTHONPATH=src ruff check src/twobrain_rec_server/api/ingest.py src/twobrain_rec_server/ingest/finalize.py src/twobrain_rec_server/ingest/store.py tests/integration/test_finalize_integrity.py tests/integration/test_persistent_ingest_storage.py` -> pass.
- At that point, remaining Phase 11 packages #113-#124 still blocked PR
  readiness and deployment-plan handoff until their associated tasks were
  completed.
- #113 partial remediation completed for Spec Kit task T131: ingest services now
  use the module-owned store reference so process-store reset tests exercise real
  cold-load behavior instead of stale imported store objects.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/integration/test_minio_upload_storage.py apps/server/tests/integration/test_finalize_integrity.py apps/server/tests/integration/test_processing_placeholder.py` -> `10 passed`.
- #113 partial remediation completed for Spec Kit task T138: upload session TTL,
  terminal-state mutation guards, `finalized_at` persistence, and one-active-session
  enforcement are covered by `apps/server/tests/integration/test_upload_session_lifecycle.py`.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_upload_session_lifecycle.py apps/server/tests/integration/test_finalize_integrity.py apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/integration/test_upload_resume.py apps/server/tests/unit/test_manifest_validation.py` -> `17 passed`.
- #113 partial remediation completed for Spec Kit task T123: process-store reset
  coverage now proves persisted session status, missing ranges, meeting reload, and
  finalize after reset.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/integration/test_upload_session_lifecycle.py` -> `9 passed`.
- #113 partial remediation completed for Spec Kit tasks T121 and T139: lifecycle
  tests now cover expired sessions, terminal mutation rejection, one active session
  per meeting, conflicting meeting creates, persisted meeting reload, and persisted
  meeting upload status after session creation.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_upload_session_lifecycle.py apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/integration/test_upload_resume.py apps/server/tests/unit/test_upload_idempotency.py` -> `15 passed`.
- #113 partial remediation completed for Spec Kit task T140: `started_at`,
  `ended_at`, processing placeholder status, upload session processing status, and
  `finalized_at` lifecycle timing are persisted and covered by integration tests.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_upload_session_lifecycle.py apps/server/tests/integration/test_finalize_integrity.py apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/integration/test_upload_resume.py apps/server/tests/unit/test_manifest_validation.py apps/server/tests/unit/test_upload_idempotency.py` -> `23 passed`.
- #115 partial remediation completed for Spec Kit tasks T120, T134, and T135:
  missing ranges now use accepted byte intervals; upload rejects negative offsets,
  invalid part numbers, overlapping ranges, offset-mismatched replay, expected-size
  overflow, and cumulative package limit overflow before accepted persistence.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_upload_resume.py apps/server/tests/integration/test_upload_session_lifecycle.py apps/server/tests/integration/test_finalize_integrity.py apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/unit/test_missing_ranges.py apps/server/tests/unit/test_upload_idempotency.py apps/server/tests/unit/test_manifest_validation.py` -> `29 passed`.
- #114 partial remediation completed for Spec Kit tasks T122, T124, T141, and
  T143: auth now fails closed without persistent DB context, upload-session
  creation enforces meeting owner/device binding, denial branches cover inactive
  membership and wrong device/user bindings, and audit rows persist actor user and
  device identifiers.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_tenant_authorization.py apps/server/tests/integration/test_audit_persistence.py apps/server/tests/integration/test_upload_resume.py apps/server/tests/integration/test_upload_session_lifecycle.py apps/server/tests/integration/test_finalize_integrity.py apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/unit/test_redaction.py apps/server/tests/unit/test_missing_ranges.py apps/server/tests/unit/test_upload_idempotency.py apps/server/tests/unit/test_manifest_validation.py` -> `38 passed`.
- #114 remediation completed for Spec Kit task T142: API boundary validation now
  bounds/sanitizes meeting identifiers, titles, abort reasons, request IDs, audit
  metadata keys/values, and request path logging templates resource UUIDs.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_api_boundary_validation.py apps/server/tests/unit/test_redaction.py apps/server/tests/integration/test_tenant_authorization.py apps/server/tests/integration/test_audit_persistence.py` -> `12 passed`.
- #116 partial remediation completed for Spec Kit tasks T126 and T150: public
  readiness now returns `200 {"status":"ready"}` or `503 {"status":"not_ready"}`
  without dependency detail; `/api/v1/health/ready/internal` exposes dependency
  checks for internal diagnostics.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_health_readiness.py apps/server/tests/integration/test_no_processing_side_effects.py` -> `4 passed`.
- #116 remediation completed for Spec Kit tasks T127 and T144: committed
  `contracts/openapi.yaml` is now generated from runtime `/openapi.json`, and
  contract tests fail on future drift for schemas, status codes, readiness shape,
  and Problem `request_id` naming.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_openapi_contract_drift.py apps/server/tests/integration/test_health_readiness.py apps/server/tests/unit/test_api_boundary_validation.py apps/server/tests/unit/test_redaction.py apps/server/tests/integration/test_tenant_authorization.py apps/server/tests/integration/test_audit_persistence.py` -> `18 passed`.
- #113 remediation completed for Spec Kit task T145: upload-session creation
  supports `Idempotency-Key` replay/conflict behavior, meeting creation keeps
  local-recording idempotency semantics, and upload part replay/conflict behavior
  remains covered by idempotency tests.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_openapi_contract_drift.py apps/server/tests/integration/test_upload_session_lifecycle.py apps/server/tests/unit/test_upload_idempotency.py` -> `13 passed`.
- #122 remediation completed for Spec Kit tasks T161, T162, T169, and T174:
  boundary validation, exact degraded assertions, upload limit/storage Problem
  responses, and OpenAPI Problem schema drift checks are covered.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_api_boundary_validation.py apps/server/tests/integration/test_degraded_ingest.py apps/server/tests/integration/test_upload_resume.py apps/server/tests/contract/test_openapi_contract_drift.py` -> `13 passed`.
- #115 remediation completed for Spec Kit tasks T130, T136, and T137: upload body
  reading now uses bounded request streaming before checksum/size acceptance,
  fake storage enforces stream length/failure hooks, and accepted object writes
  create temporary cleanup accounting rows.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_streaming_upload.py apps/server/tests/integration/test_upload_resume.py apps/server/tests/integration/test_minio_upload_storage.py apps/server/tests/integration/test_upload_session_lifecycle.py apps/server/tests/integration/test_finalize_integrity.py apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/contract/test_openapi_contract_drift.py apps/server/tests/unit/test_upload_idempotency.py apps/server/tests/unit/test_missing_ranges.py` -> `36 passed`.
- #119 remediation completed for Spec Kit tasks T128, T129, T146, T147, and
  T149: server image packages Alembic artifacts, deterministic identity/device
  bootstrap exists, compose separates MinIO root/API credentials, MinIO bucket/API
  user provisioning runs in an init service, and readiness no longer mutates MinIO.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_postgres_migrations.py apps/server/tests/integration/test_compose_bootstrap.py apps/server/tests/integration/test_upload_helper_contract.py apps/server/tests/integration/test_health_readiness.py apps/server/tests/integration/test_minio_upload_storage.py` -> `10 passed`.
- `/usr/local/bin/docker compose -f infra/docker-compose.dev.yml config` -> pass.
- `TWOBRAIN_POSTGRES_PASSWORD=dummy TWOBRAIN_MINIO_ROOT_USER=root TWOBRAIN_MINIO_ROOT_PASSWORD=rootsecret TWOBRAIN_MINIO_API_ACCESS_KEY=api TWOBRAIN_MINIO_API_SECRET_KEY=apisecret /usr/local/bin/docker compose -f infra/docker-compose.yml config` -> pass.
- #120 remediation completed for Spec Kit tasks T155, T156, T157, and T171:
  finalize validation failures now durably persist degraded meeting/session state
  plus operation-scoped audit events before returning, audit persistence no longer
  reads the global latest event, temporary/orphan object cleanup rows carry
  explicit role/reason/error accounting, and audit tests assert ordering, content,
  actor/device/tenant, and redaction.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_finalize_integrity.py apps/server/tests/integration/test_audit_persistence.py apps/server/tests/integration/test_minio_upload_storage.py` -> `11 passed`.
- `cd apps/server && PYTHONPATH=src ruff check src/twobrain_rec_server/ingest/audit.py src/twobrain_rec_server/ingest/finalize.py src/twobrain_rec_server/ingest/meetings.py src/twobrain_rec_server/ingest/sessions.py src/twobrain_rec_server/ingest/parts.py src/twobrain_rec_server/ingest/lifecycle.py src/twobrain_rec_server/ingest/lifecycle_guards.py src/twobrain_rec_server/ingest/store.py src/twobrain_rec_server/db/models/ingest.py tests/integration/test_finalize_integrity.py tests/integration/test_audit_persistence.py tests/integration/test_minio_upload_storage.py` -> pass.
- #121 remediation completed for Spec Kit tasks T158, T159, T160, T175, T176,
  and T177: processing placeholders can load from Postgres after process-store
  reset, placeholder snapshots include meeting lifecycle status, access policy
  placeholders represent admin/deletion/share/download/export denial branches,
  expected track roles and expected track sizes are split in runtime and DB
  models, meeting timestamps are returned and persisted, and ManifestSnapshot
  provenance is asserted for future processing/deletion use.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/integration/test_processing_placeholder.py apps/server/tests/integration/test_access_placeholders.py apps/server/tests/contract/test_openapi_contract_drift.py apps/server/tests/integration/test_postgres_migrations.py` -> `18 passed`.
- `cd apps/server && PYTHONPATH=src ruff check src/twobrain_rec_server/api/schemas.py src/twobrain_rec_server/api/ingest.py src/twobrain_rec_server/ingest/store.py src/twobrain_rec_server/ingest/sessions.py src/twobrain_rec_server/ingest/finalize.py src/twobrain_rec_server/ingest/processing_placeholder.py src/twobrain_rec_server/ingest/access_policy.py src/twobrain_rec_server/db/models/ingest.py src/twobrain_rec_server/db/models/meeting.py tests/integration/test_persistent_ingest_storage.py tests/integration/test_processing_placeholder.py tests/integration/test_access_placeholders.py` -> pass.
- #123 remediation completed for Spec Kit tasks T163, T164, T165, T166, T167,
  and T170: public readiness remains non-mutating and detail-free, internal
  readiness requires `X-Internal-Health-Check: true`, production disables
  `/docs`, `/redoc`, and `/openapi.json`, MinIO SDK operations are exposed through
  async threadpool wrappers for readiness/upload paths, and request logs emit
  structured JSON with request id, method, templated path, status, duration, and
  redacted safe headers.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_health_readiness.py apps/server/tests/integration/test_production_docs_exposure.py apps/server/tests/unit/test_structured_logging.py apps/server/tests/unit/test_redaction.py apps/server/tests/unit/test_minio_async_wrappers.py apps/server/tests/integration/test_minio_upload_storage.py` -> `11 passed`.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_openapi_contract_drift.py apps/server/tests/integration/test_health_readiness.py` -> `6 passed`.
- `cd apps/server && PYTHONPATH=src ruff check src/twobrain_rec_server/main.py src/twobrain_rec_server/api/health.py src/twobrain_rec_server/observability/logging.py src/twobrain_rec_server/storage/minio_client.py src/twobrain_rec_server/ingest/parts.py tests/integration/test_health_readiness.py tests/integration/test_production_docs_exposure.py tests/unit/test_structured_logging.py tests/unit/test_minio_async_wrappers.py` -> pass.
- #124 remediation completed for Spec Kit tasks T168, T172, T173, T178, T179,
  and T180: tenant auth tests now cover wrong organization, inactive membership,
  other-workspace device, other-user device, and revoked device branches; fake
  MinIO storage has exact stream-length and failure-injection tests; targeted
  integration tests use TestClient portal calls instead of ad-hoc `asyncio.run`;
  upload helper contract tests prove separate identity headers plus optional
  bearer token behavior; production config validation rejects localhost/default/root
  MinIO assumptions; and compose lint covers API healthcheck, localhost-only bind,
  log rotation, resource limits, runtime-only dependency install, and constraints.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_tenant_authorization.py apps/server/tests/integration/test_persistent_ingest_storage.py apps/server/tests/unit/test_fake_minio_storage.py apps/server/tests/integration/test_upload_helper_contract.py apps/server/tests/unit/test_config_validation.py apps/server/tests/integration/test_compose_hardening.py` -> `33 passed`.
- `TWOBRAIN_POSTGRES_PASSWORD=dummy TWOBRAIN_MINIO_ROOT_USER=rootuser TWOBRAIN_MINIO_ROOT_PASSWORD=rootsecret TWOBRAIN_MINIO_API_ACCESS_KEY=twobrain_rec_api TWOBRAIN_MINIO_API_SECRET_KEY=apisecret /usr/local/bin/docker compose -f infra/docker-compose.yml config` -> pass.
- `PYTHONPATH=apps/server/src python -m compileall -q apps/server/src apps/server/tests apps/server/scripts` -> pass.
- #117 remediation completed for Spec Kit tasks T151, T152, and T153: module
  import no longer constructs an app while the production Docker command uses
  uvicorn factory mode, FastAPI lifespan disposes the DB engine and closes runtime
  storage clients that expose `close`, the runtime image installs `.` with
  `constraints.txt` instead of `.[dev]`, and production compose has localhost-only
  API binding, API healthcheck, resource limits, log rotation, required secret
  placeholders, and production fail-closed config validation.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_app_lifecycle.py apps/server/tests/unit/test_config_validation.py apps/server/tests/integration/test_compose_hardening.py apps/server/tests/integration/test_production_docs_exposure.py apps/server/tests/integration/test_health_readiness.py` -> `20 passed`.
- `TWOBRAIN_POSTGRES_PASSWORD=dummy TWOBRAIN_MINIO_ROOT_USER=rootuser TWOBRAIN_MINIO_ROOT_PASSWORD=rootsecret TWOBRAIN_MINIO_API_ACCESS_KEY=twobrain_rec_api TWOBRAIN_MINIO_API_SECRET_KEY=apisecret /usr/local/bin/docker compose -f infra/docker-compose.yml config` -> pass.
- `cd apps/server && PYTHONPATH=src ruff check src/twobrain_rec_server/main.py tests/unit/test_app_lifecycle.py tests/integration/test_compose_hardening.py tests/integration/test_production_docs_exposure.py tests/unit/test_config_validation.py` -> pass.
- #118 remediation completed for Spec Kit tasks T148 and T154: the upload helper
  now requires separate organization, workspace, user, and device identifiers,
  keeps bearer token optional, creates upload sessions with explicit expected
  roles/sizes, uploads all three artifact parts, and finalizes the session;
  quickstart now documents deterministic local identity/device bootstrap and
  every helper invocation uses the finalized auth/header contract. Current status
  docs and PRD now say Phase 11 issues #112-#124 / tasks T119-T180 are remediated
  locally, with final full sanity, dirty-worktree review, and commit/PR decision
  still remaining before handoff.
- `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_upload_helper_contract.py apps/server/tests/integration/test_compose_bootstrap.py` -> `3 passed`.
- `cd apps/server && PYTHONPATH=src ruff check scripts/upload_test_artifact.py scripts/seed_dev_identity.py tests/integration/test_upload_helper_contract.py` -> pass.
- `PYTHONPATH=apps/server/src python -m compileall -q apps/server/scripts/upload_test_artifact.py apps/server/scripts/seed_dev_identity.py` -> pass.
