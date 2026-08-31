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

## 2. Complete-result continuity

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/unit/test_processing_results.py \
  tests/unit/test_cabinet_view_models.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_artifact_egress_policy.py \
  tests/integration/test_desktop_sync.py
```

Required matrix:

| Previous result | New attempt | Expected visible result |
|---|---|---|
| complete A | active/no result | A |
| complete A | transcript-only B | A |
| complete A | terminal B | A |
| complete A | complete B | B |
| complete A version 2 | complete B version 1, newer attempt | B |

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
- `Повторить сейчас` reuses the workflow/job and advances schedule generation;
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
2. Cancel/Escape restores focus; confirm enters one busy state.
3. Active and retryable states keep transcript, player and transcript export usable.
4. Countdown is not announced every second.
5. Terminal failure offers a fresh reprocess action.

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
