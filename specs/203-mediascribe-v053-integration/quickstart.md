# Quickstart: MediaScribe v0.5.3 integration fidelity

This implementation slice is high-risk. Run from the repository root after the
implementation tasks are complete. Use synthetic/content-free fixtures only;
production verification is a separate release gate.

## 1. Contract boundary

```sh
cd /Users/yshishenya/.codex/worktrees/dc3d/crisp/apps/server
PYTHONPATH=src pytest -q tests/contract/test_mediascribe_client_contract.py \
  tests/contract/test_mediascribe_v1_client.py \
  tests/unit/test_mediascribe_result_import.py
```

Expected evidence:

- v0.5.3 WordItem forms are accepted/rejected safely;
- omitted single-track role becomes `mixed`;
- valid provider blocks retain their boundaries;
- summary/null/running/failed responses do not break result import;
- source/result hash includes words and unknown response fields do not crash the adapter.

## 2. Persistence and lineage

```sh
bash scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_mediascribe_processing_happy_path.py \
  tests/integration/test_postgres_migrations.py
```

Expected evidence:

- words survive import into the same result lineage;
- duplicate delivery does not append duplicate rows;
- stale revision/deletion fences still block late provider results;
- old rows with null words remain readable.

## 3. Temporal recovery

```sh
bash scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_processing_temporal_workflow.py \
  tests/unit/test_processing_recovery_contracts.py \
  tests/unit/test_processing_worker_readiness.py
```

Expected evidence:

- `Retry-After` and provider `next_retry_at` feed the existing durable timer;
- replay/restart remains deterministic;
- manual check is idempotent and does not create a new provider job;
- terminal provider states stop polling.

## 4. User-visible parity

```sh
bash scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_cabinet_view_models.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_transcript_export_egress.py \
  tests/contract/test_processing_status_contract.py
```

Expected evidence:

- transcript remains hidden before matching diarization;
- provider block count and boundaries are preserved;
- summary failure does not hide the transcript;
- browser and embedded cabinet projections share the same safe role/recovery state.

## 5. Required closeout gate

```sh
git diff --check
infra/scripts/ci-local.sh --fast
```

Do not claim a live provider or production proof from synthetic contract tests;
the release/deploy and live smoke are separate evidence gates.

## 6. Recorded evidence

- 224 focused contract/import/view-model/web-shell tests passed.
- 85 focused PostgreSQL status/cabinet/export/MediaScribe/migration tests
  passed after the terminal projection fix.
- 26 migration and worker-head tests passed after rebasing the additive
  migration onto master `0080` as `0081_mediascribe_words`.
- `git diff --check` passed.
- `infra/scripts/ci-local.sh --fast` passed: 1229 unit tests, lint and Python
  compile.
- No production/provider claim is made by this file; it requires the exact-SHA
  release and smoke evidence described in the release guidance.
