# Quickstart: повторная обработка записи пользователем

Run commands from the repository root. The PostgreSQL wrapper creates and
removes an isolated test database, so the checks do not depend on a developer's
local `TWOBRAIN_DATABASE_URL`.

## 1. Admission and authorization

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_processing_attempts.py \
  tests/contract/test_processing_status_contract.py
```

Required scenarios:

- owner request creates one replacement workflow;
- the same predecessor returns the same immediate successor;
- two tabs create no parallel workflow;
- an older predecessor conflicts without creating work;
- non-owner/shared recipient cannot launch;
- the same media revision is not charged twice.

## 2. Complete-result retention and owner visibility

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/unit/test_processing_results.py \
  tests/unit/test_cabinet_view_models.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_artifact_egress_policy.py \
  tests/integration/test_desktop_sync.py
```

Required matrix:

| Previous result | New attempt | Owner detail | Stored/shared result |
|---|---|---|---|
| complete A | active/no result | one neutral indicator | A |
| complete A | transcript-only B | one neutral indicator | A |
| complete A | terminal B | restored A plus retry | A |
| complete A | complete B | B in transcript and player together | B |
| complete A version 2 | complete B version 1, newer attempt | B | B |

Detail, full share, transcript export, transcript egress and desktop sync must agree on the same result ID.

## 3. Temporal identity and retry

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/unit/test_processing_workflow_identity.py \
  tests/unit/test_processing_temporal_workflow.py \
  tests/unit/test_processing_recovery.py \
  tests/contract/test_processing_status_contract.py
```

Required scenarios:

- new payload contains `processing_workflow_id`;
- old history without the field replays;
- delayed old activity cannot load the new attempt;
- automatic retry reuses the workflow/job and advances schedule generation;
- stale manual command creates no work.

## 4. Cabinet UI and accessibility

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_recording_workflow_accessibility.py \
  tests/integration/test_cabinet_meeting_detail.py
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
```

Manual synthetic-data acceptance:

1. Owner finds the action in `Ещё`; shared recipient does not.
2. The dialog contains only the manual-name warning plus `Отмена` and `Подготовить`; Cancel/Escape restores focus.
3. Active, `result_not_ready`, retryable, unknown-outcome and temporary status-fetch-failure states show only `Готовим новую версию`; prior owner content and player are hidden.
4. Terminal failure restores the prior transcript, manual speaker names, outcomes and player and offers `Попробовать снова`.
5. Successful publication swaps transcript and player together; both show labels from the new result.
6. Browser and embedded macOS surfaces have the same flow; shared recipients continue to receive the last complete result while replacement is active.

## 5. Feature gate

From repository root:

```sh
git diff --check
infra/scripts/ci-local.sh --fast
```

Do not run release/deploy or production smoke without separate approval. Full CI is reserved for the frozen release candidate or approved deployment.

## Validation evidence (2026-09-01)

- Isolated-PostgreSQL run of the 12 core Feature 213 files after synchronizing
  `origin/master` at `bef6ef5ced604d475eab43bfd1c9bbddc8faff05`:
  `349 passed`.
- The remaining quickstart egress, recovery and accessibility files passed in
  one isolated-PostgreSQL run: `36 passed`.
- Targeted access, transcript continuity, web/embedded replacement and UI refresh
  regressions are rerun after the final `origin/master` synchronization.
- Owner/non-owner, lost-response replay, stale predecessor/revision, missing
  source, CSRF, fresh terminal successor, one provider job, unchanged initial
  recovery and schedule-generation scenarios are covered with synthetic IDs
  and no meeting content in evidence.
- Web and embedded HTML acceptance confirms that complete result B replaces A
  only after transcript and matching diarization are complete.
- `node --check`, Ruff, Python compile and `git diff --check`: PASS.
- `infra/scripts/ci-local.sh --fast`: PASS (`1362` unit tests and `153` changed
  server tests); coverage is intentionally partial and the next release gate is
  full CI on the exact release candidate.
- Release, deployment and production smoke were not performed.

## UX simplification evidence (2026-09-02)

- Branch synchronized with `origin/master` at
  `10008b6c8f236be151672e37773f706053656c06` before final validation.
- The combined isolated-PostgreSQL Feature 213 matrix passed: `300 passed`.
  It covers admission/idempotency, complete-result selection, Temporal identity,
  web and embedded detail, terminal restoration, accessibility, artifact egress,
  desktop sync and result-scoped speaker names.
- The browser harness verifies that replacement publication pauses the old audio
  and replaces the main detail plus adjacent player from the same fragment in
  one JavaScript turn.
- Ruff, `node --check`, development-process preflight and `git diff --check`:
  PASS.
- GitHub Actions `governance-fast` passed on implementation SHA
  `c26d56abbe98b12aeb92e3cbdc034d8c6f5dafdf`: run
  [33639708179](https://github.com/yshishenya/graf/actions/runs/33639708179).
  The remote fast lane passed `1362` server tests, `117` changed-server tests,
  `169` governance tests and `60` CI-contract tests with
  `coverage=partial` and `next_gate=full_before_release`.
- Full CI remains the frozen release-candidate gate; release, deployment and
  production smoke were not performed.
