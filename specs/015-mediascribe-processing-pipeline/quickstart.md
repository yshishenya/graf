# Quickstart: MediaScribe Processing Pipeline

Use this guide to validate `015-mediascribe-processing-pipeline` after
implementation. Commands assume the repository root as the working directory.

## 1. Prerequisites

- `012-server-ingest-foundation` migrations and ingest tests pass.
- Local server dependencies are installed through `uv`.
- Real MediaScribe credentials are not required for default local validation;
  tests must use a fake client/server unless explicitly running an operator
  dependency smoke.
- Do not put real credentials, raw audio, transcript text, signed URLs, or live
  secret paths into evidence files.

## 2. Contract And Unit Tests

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_processing_status_contract.py \
  tests/contract/test_mediascribe_client_contract.py \
  tests/unit/test_processing_state_machine.py \
  tests/unit/test_mediascribe_result_import.py
```

Expected:

- processing status contract matches
  `specs/015-mediascribe-processing-pipeline/contracts/processing-status.openapi.yaml`;
- dual-track request mapping uses `mic_file` and `incoming_file`;
- duplicate pickup does not create duplicate workflow or job records;
- result import is idempotent.

## 3. Integration Happy Path With Fake MediaScribe

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_processing_pickup.py \
  tests/integration/test_mediascribe_processing_happy_path.py
```

Expected:

- finalized `ingested_pending_processing` meeting is picked up;
- one workflow id is recorded;
- one MediaScribe job id is persisted;
- transcript and diarization segments import with source roles and timestamps;
- ingest status remains truthful.

## 4. Failure And Retry Matrix

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_processing_failures.py \
  tests/integration/test_processing_worker_restart.py
```

Required scenarios:

- missing credentials -> `blocked_config` / safe reason;
- 401 -> terminal auth failure;
- 413 -> terminal payload-too-large failure;
- 429/5xx/timeout -> retryable until retry budget ends;
- crash after job creation -> resume polling existing job id;
- malformed result -> retryable or terminal with safe reason;
- duplicate pickup -> existing workflow reused.

## 5. Tenant And Content Boundary

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_processing_tenant_authorization.py \
  tests/contract/test_processing_no_secret_content_egress.py
```

Expected:

- cross-tenant status/pickup attempts are forbidden or hidden;
- processing status responses do not include transcript text;
- logs/audit/problem payloads do not include raw audio, transcript text,
  MediaScribe credentials, signed URLs, bearer tokens, passwords, or live secret
  paths.

## 6. Readiness And Compose

```sh
docker compose -f infra/docker-compose.dev.yml config
docker compose -f infra/docker-compose.yml config
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_processing_readiness.py
```

Expected:

- ingest readiness remains independent from processing readiness;
- processing readiness distinguishes Temporal configuration, MediaScribe base
  URL/credential configuration, and dependency reachability;
- production compose uses secret files/placeholders rather than literal live
  credentials.

## 7. Out-Of-Scope Regression

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_processing_out_of_scope_boundaries.py
```

Expected:

- no dashboard meeting detail UI;
- no share links or public pages;
- no transcript/audio/summary download endpoint;
- no deletion execution endpoint;
- no assisted recording behavior;
- no macOS capture/upload changes.

## 8. Full Local Gate

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q
PYTHONPATH=src uv run --extra dev ruff check .
cd ../..
python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts
```

Expected:

- all tests pass;
- Ruff passes;
- compileall passes;
- working tree contains no generated secrets, raw transcripts, raw audio, or
  unreviewed build output.

## 9. Evidence

Record implementation evidence in this quickstart or a dedicated evidence file
only after commands are run. Evidence must remain metadata-only and should list
command, result, date, and any blocked dependency reason.
