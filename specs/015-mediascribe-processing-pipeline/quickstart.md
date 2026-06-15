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

### 2026-06-11 Implementation Evidence

- `uv run --extra dev pytest -q tests/unit/test_processing_state_machine.py tests/unit/test_processing_workflow_identity.py tests/unit/test_mediascribe_request_mapping.py tests/unit/test_mediascribe_result_import.py tests/contract/test_processing_status_contract.py tests/contract/test_mediascribe_client_contract.py tests/contract/test_processing_no_secret_content_egress.py tests/integration/test_processing_migrations.py tests/integration/test_processing_pickup.py tests/integration/test_processing_pickup_blockers.py tests/integration/test_mediascribe_submit.py tests/integration/test_mediascribe_processing_happy_path.py tests/integration/test_processing_result_idempotency.py tests/integration/test_processing_failures.py tests/integration/test_processing_worker_restart.py tests/integration/test_processing_readiness.py tests/integration/test_processing_audit.py tests/integration/test_processing_deletion_dependency.py tests/integration/test_processing_tenant_authorization.py tests/integration/test_processing_out_of_scope_boundaries.py` -> `30 passed`.
- `uv run --extra dev pytest -q` from `apps/server` -> first pass found OpenAPI contract drift after adding processing endpoints; committed contract was regenerated from runtime OpenAPI and rerun -> `230 passed`.
- `uv run --extra dev ruff check .` from `apps/server` -> first pass found import-order/style cleanup; safe Ruff fix plus one manual `contextlib.suppress` cleanup; rerun -> `All checks passed!`.
- `uv run --extra dev python -m compileall -q src tests scripts` from `apps/server` -> passed.
- `docker compose -f infra/docker-compose.dev.yml config` -> passed, rendered 286 lines to `/tmp/twobrain-rec-dev-compose.yml`.
- `docker compose -f infra/docker-compose.yml config` -> passed, rendered 410 lines to `/tmp/twobrain-rec-prod-compose.yml`.
- `uv run --extra dev pytest -q tests/contract/test_processing_no_secret_content_egress.py tests/unit/test_deployment_evidence_scan.py tests/unit/test_redaction.py` -> `8 passed`.
- Targeted changed-file secret scan over 47 implementation/doc/config files, excluding pre-existing `.specify/*` worktree changes -> `findings 0`.
- GitHub issue sync completed for T001-T087 as issues #550-#636. After implementation validation, all 87 GitHub issues were closed with an evidence comment; `gh issue list --repo yshishenya/crisp --label feature:015 --state open --limit 100 --json number,title` returned `[]`.
- Linear sync created YSH-274 through YSH-352 for T001-T079, then stopped at
  T080-T087 because the Linear workspace active issue limit was exceeded. This
  is now historical only: Linear has been excluded from the required repository
  workflow, so missing Linear issues are not a `015` blocker.

### 2026-06-11 Final Audit Notes

- Spec scope upheld: no dashboard, share, download, delete, notes, assisted-recording, or macOS capture/upload behavior was added.
- Privacy boundary upheld: desktop receives no MediaScribe credentials or signed dependency URLs; processing status is content-safe; audit metadata uses safe counters/status/reason codes only.
- Lifecycle truth upheld: processing failures update processing state, not ingest status; dependency state records future deletion truth without claiming external deletion execution.
- Design review: no user-facing UI was introduced in `015`, so Product Design did not require a visual design pass for this backend-only slice.

### 2026-06-11 E2E Processing Audit

- Added strict fake-MediaScribe e2e proof for accepted upload artifacts:
  finalized ingest is picked up through `/api/v1/internal/processing/pickup`,
  uploaded microphone/system track hashes are compared to hashes received at
  the MediaScribe boundary, then persisted workflow/job/result/transcript/
  diarization/dependency rows are asserted.
- Found a worker-activity gap: missing MediaScribe configuration returned an
  activity failure status but did not persist the processing workflow blocker.
  Added a regression test and fixed the activity to persist `blocked` with
  `blocked_config`.
- `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_mediascribe_processing_happy_path.py -vv`
  -> `2 passed`.
- Red/green defect proof:
  `tests/integration/test_processing_failures.py::test_worker_activity_persists_blocked_config_when_mediascribe_is_unconfigured`
  failed before the fix with persisted `workflow_started` / no reason, then
  passed after the fix with `blocked_config`.
- Processing-focused suite after the fix -> `32 passed`.
- Full server gate after the fix:
  `PYTHONPATH=src uv run --extra dev pytest -q` -> `232 passed`;
  `PYTHONPATH=src uv run --extra dev ruff check .` -> `All checks passed!`;
  `PYTHONPATH=src uv run --extra dev python -m compileall -q src tests scripts`
  -> passed.

### 2026-06-11 Live MediaScribe Audit With Real App Recording

- Located real local app recordings under
  `~/Library/Application Support/2brain Rec/Recordings/` and selected
  `20260610-093247-F2645A5B-6479-4E7F-AE32-34870B5AFAAE` because both
  microphone and incoming WAV tracks were short and had non-zero signal.
- Live external MediaScribe smoke using the real app recording succeeded:
  submit returned `uploaded`, polling reached `ready`, fetch returned transcript
  and diarization rows with both `mic` and `incoming` roles and speakers `MIC`
  and `REMOTE_00`. No transcript text was recorded in evidence.
- Found and fixed a live-contract mismatch: production MediaScribe polls and
  returns results through `/jobs/{job_id}` and `/jobs/{job_id}/result`, while
  the initial client used `/v1/audio/transcriptions/jobs/{job_id}`. The live
  result payload also uses `start`/`end`/`speaker`, so the client now normalizes
  that shape into internal `start_seconds`/`end_seconds`/`speaker_label`.
- End-to-end backend storage/import proof using the real app recording and live
  MediaScribe succeeded through finalized ingest, internal pickup, storage
  artifact submission, poll/fetch, result import, and DB assertions:
  workflow `processed`, MediaScribe job `ready`, processing result `imported`,
  transcript rows `2`, diarization rows `2`, roles `incoming` and `mic`,
  dependency state `mediascribe:imported`.
- Historical pre-deploy Production Rec host check:
  `2brain.dev:/opt/projects/2brain-rec` was on `master` at `311c25b` with
  services `rec-api`, `rec-migrate`, `rec-minio`, `rec-minio-init`, and
  `rec-postgres`; the `015` processing worker was not yet deployed there. This
  finding is superseded by the production deployment and real-recording e2e
  evidence below.
- Full server gate after live-contract fixes:
  `PYTHONPATH=src uv run --extra dev pytest -q` -> `233 passed`;
  `PYTHONPATH=src uv run --extra dev ruff check .` -> `All checks passed!`;
  `PYTHONPATH=src uv run --extra dev python -m compileall -q src tests scripts`
  -> passed.

### 2026-06-11 Current Master Completion Re-audit

- Audited `origin/master` at `965b775` after merged `015` PR #637 and
  post-merge fixes #638-#642 and #713. Spec Kit prerequisite resolution passes
  with `SPECIFY_FEATURE_DIRECTORY=specs/015-mediascribe-processing-pipeline`;
  all 5 checklists pass; `tasks.md` has 87 checked tasks and 0 open tasks.
- GitHub tracking is complete for `015`: open issues with `feature:015` -> 0;
  closed issues with `feature:015` -> 87. Linear validation still reports the
  historical T080-T087 gaps, but Linear is no longer part of the required
  workflow and is not a closure blocker.
- Current-master local gates before the new fix:
  `PYTHONPATH=src uv run --extra dev pytest -q` -> `243 passed`;
  `PYTHONPATH=src uv run --extra dev ruff check .` -> `All checks passed!`;
  `PYTHONPATH=src uv run --extra dev python -m compileall -q src tests scripts`
  -> passed;
  `docker compose -f infra/docker-compose.dev.yml config` and
  `docker compose -f infra/docker-compose.yml config` -> passed.
- Review found an uncovered failure-path gap: malformed successful MediaScribe
  submit/result payloads could escape as unmanaged validation exceptions instead
  of safe processing failure state. Red proof:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mediascribe_client_contract.py tests/integration/test_processing_failures.py`
  failed before the fix with `ValidationError` / unpersisted safe reason.
- A second audit check found that missing/unreadable MediaScribe API key files
  could escape as unmanaged file-system exceptions instead of safe
  `blocked_config`. Added regression coverage and mapped that path to
  `MediaScribeClientError("blocked_config")`.
- A production hardening review found `rec-api` still mounted the
  `twobrain_mediascribe_api_key` Docker secret even though only the processing
  worker needs it. Removed that mount and added compose hardening coverage so
  only `rec-processing-worker` receives the MediaScribe API key secret.
- Added regression coverage for missing MediaScribe job id, invalid result
  payload validation, import-time result validation failure, and unreadable
  secret-file configuration. After the fix:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mediascribe_client_contract.py tests/integration/test_processing_failures.py`
  -> `9 passed`;
  `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mediascribe_client_contract.py tests/integration/test_processing_failures.py tests/contract/test_processing_no_secret_content_egress.py`
  -> `11 passed`.
- Full local gate after the completion-audit fixes:
  `PYTHONPATH=src uv run --extra dev pytest -q` -> `247 passed`;
  `PYTHONPATH=src uv run --extra dev ruff check .` -> `All checks passed!`;
  `PYTHONPATH=src uv run --extra dev python -m compileall -q src tests scripts`
  -> passed;
  dev/prod Compose config render -> passed.

### 2026-06-11 Production Deployment And Real Recording E2E

- Deployed `master` at
  `4cda38c02eec88da3bf02ba8a78abe4e7d24ccbf` to
  `2brain.dev:/opt/projects/2brain-rec` with
  `infra/scripts/cd-remote.sh --execute --branch master`.
- CD evidence:
  local server tests -> `247 passed`; Ruff -> `All checks passed!`; compileall
  -> passed; deployment evidence scan -> passed; remote backup -> pass
  (`/opt/projects/2brain-rec/backups/20260611T143559Z`); restore rehearsal ->
  pass; production migration verification -> `0004_mediascribe_processing`
  head; production smoke -> pass; public `/api/v1/health/live` -> `ok`;
  public `/api/v1/health/ready` -> `ready`.
- Production service state after deployment:
  `rec-api` running and healthy; `rec-processing-worker` running; `rec-temporal`
  running; `rec-postgres` and `rec-minio` healthy.
- Full production e2e used the real local app recording
  `20260610-093247-F2645A5B-6479-4E7F-AE32-34870B5AFAAE` with `mic.wav` and
  `incoming.wav` copied into the production `rec-api` container as a temporary
  smoke artifact. The e2e run id was `e2e-015-20260611-144103`.
- The production e2e flow succeeded through public upload/finalize, internal
  processing pickup, Temporal worker processing, live MediaScribe submit/poll,
  result import, content-safe status, and cleanup:
  upload result `ingested_pending_processing`; pickup `started_count=1`;
  workflow `processed`; MediaScribe job `ready`; processing result `imported`;
  transcript status `available`; diarization status `available`; transcript
  rows `2`; diarization rows `2`; source roles `mic` and `incoming`;
  dependency state `mediascribe:imported`.
- The content-safe processing status endpoint returned `state=processed`,
  `content_available=true`, `transcript_available=true`,
  `diarization_available=true`, `mediascribe_job_id_present=true`, and did not
  expose transcript text.
- Cleanup after the e2e pass succeeded:
  `auth_rows_removed=2`, `database_records_removed=34`,
  `object_keys_removed=3`, and `residue_records=[]`.
- Transcript text was inspected in command output for manual verification only.
  It was not written into tracked evidence documents, logs, or issue comments.
