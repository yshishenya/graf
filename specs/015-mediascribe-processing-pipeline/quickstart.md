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
- Linear sync created YSH-274 through YSH-352 for T001-T079, then stopped at T080-T087 because the Linear workspace active issue limit was exceeded; see `linear-sync.md`.
- Follow-up Linear pass on 2026-06-11 moved YSH-274 through YSH-352 to `Done`, added evidence comments, and recorded their mapping in `.specify/linear.yml`.
- `python3 .specify/extensions/linear-sync/scripts/linear_sync.py sync --feature 015 --apply` still could not create T080-T087 because Linear returned `USAGE_LIMIT_EXCEEDED` for `activeIssueCount`.
- `python3 .specify/extensions/linear-sync/scripts/linear_sync.py validate --feature 015 --apply` now reports exactly 8 remaining Linear gaps: T080-T087.

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
- Production Rec host check: `2brain.dev:/opt/projects/2brain-rec` is currently
  on `master` at `311c25b` with services `rec-api`, `rec-migrate`, `rec-minio`,
  `rec-minio-init`, and `rec-postgres`; the `015` processing worker is not yet
  deployed there. Full Rec-production pipeline validation therefore requires
  rolling out the `015` branch and applying production secrets/migrations first.
- Full server gate after live-contract fixes:
  `PYTHONPATH=src uv run --extra dev pytest -q` -> `233 passed`;
  `PYTHONPATH=src uv run --extra dev ruff check .` -> `All checks passed!`;
  `PYTHONPATH=src uv run --extra dev python -m compileall -q src tests scripts`
  -> passed.
