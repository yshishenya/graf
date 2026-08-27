# Tasks: Надёжное ожидание результата MediaScribe

**Input**: Design documents from `/specs/206-mediascribe-polling-recovery/`

## Phase 1: Backend recovery (P1)

- [X] T001 [P] [US1] Добавить в `apps/server/src/twobrain_rec_server/processing/recovery.py` явное основание остановки scheduler и режим без generic max-attempt limit для provider polling.
- [X] T002 [P] [US1] Добавить unit checks в `apps/server/tests/unit/test_processing_recovery.py` для pending polling дольше 12 проверок, deadline и max-attempt distinction.
- [X] T003 [US1] Изменить `apps/server/src/twobrain_rec_server/workflows/worker.py`, чтобы provider polling использовал watchdog deadline и не маскировал pending как terminal failure.
- [X] T004 [US1] Проверить/дополнить `apps/server/tests/integration/test_mediascribe_processing_happy_path.py` для pending → ready на том же provider job.

## Phase 2: Temporal durability (P1)

- [X] T005 [US2] Проверить durable wait/manual wake в `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py` и сохранить deterministic replay contract.
- [X] T006 [P] [US2] Добавить сценарии в `apps/server/tests/unit/test_processing_temporal_workflow.py` для pending loop, watchdog result и manual check.

## Phase 3: Status projection and UX (P1/P2)

- [X] T007 [US2] Исправить единую terminal/pending projection в `apps/server/src/twobrain_rec_server/processing/status.py` и связанных view models, если stale workflow/meeting status расходятся.
- [X] T008 [P] [US2] Добавить contract checks для detail/list status и recovery controls в `apps/server/tests/contract/test_recording_workflow_accessibility.py` и cabinet tests.
- [X] T009 [P] [US3] Обновить user-facing копирайт/статус watchdog в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и reason labels только если это требуется итоговой статусной моделью.

## Phase 4: Validation and closeout

- [X] T010 [P] [US1] Обновить `CHANGELOG.md` в `[Unreleased]`.
- [X] T011 [US1] Выполнить quickstart, focused tests, `git diff --check` и `infra/scripts/ci-local.sh --fast`; зафиксировать evidence.
- [X] T012 [US1] Проверить UX/infra checklists и выполнить Spec Kit analyze без unresolved critical findings.
- [X] T013 [US1] Исправить `apps/server/scripts/cleanup_smoke_artifacts.py`, чтобы удаление smoke-артефактов учитывало зависимости по `processing_result_id` и не оставляло production cleanup в блокирующем состоянии.

## Dependencies & Execution Order

- T001–T002 → T003 → T004.
- T005–T006 независимы от T001–T004 по write scope, но интегрируются до closeout.
- T007–T009 после backend semantics.
- T010–T012 после всех изменений.
- T014–T015 → T019–T024.
- T016–T018 выполняются до соответствующих implementation tasks T019–T024.
- T020 → T021; T022 независим по write scope, но обязателен до integration validation.
- T025 → T026 → T027.
- T028–T030 после T014–T027; T031 после scoped/current-SHA validation.

## Implementation Strategy

Сначала минимально разделить polling budget и recovery limit, затем покрыть
Temporal/status projection. Не менять MediaScribe и не создавать новые
provider jobs. Пользователь уже одобрил commit, PR, merge, release, deploy и
production smoke; повторный Full CI не выполняется, scoped/current-SHA и deploy
gates остаются обязательными.

Canonical slice выполняется test-first: pass-count/source/MIME, Temporal
crash/replay, no-archive и terminal UI contracts добавляются до реализации.
Новые таблицы, workers и artifacts не добавляются без повторного plan/analyze.

## GitHub issue mapping

- T001: #5856
- T002: #5859
- T003: #5858
- T004: #5857
- T005: #5860
- T006: #5861
- T007: #5867
- T008: #5862
- T009: #5863
- T010: #5864
- T011: #5866
- T012: #5865
- T013: #5870
- T014: #5879
- T015: #5881
- T016: #5880
- T017: #5884
- T018: #5883
- T019: #5882
- T020: #5885
- T021: #5886
- T022: #5887
- T023: #5888
- T024: #5889
- T025: #5890
- T026: #5892
- T027: #5891
- T028: #5894
- T029: #5893
- T030: #5895
- T031: #5896

## Дополнение: tolerant media recovery

- [X] T014 [US4] Только для `manual_upload` выполнить exact bounded source probe → tolerant transcode с `-t 14401` → output probe → strict output validation без preliminary full source decode; сохранить прежние pass counts остальных путей в `apps/server/src/twobrain_rec_server/normalization/media.py`, `apps/server/src/twobrain_rec_server/normalization/service.py` и command/regression tests.
- [X] T015 [P] [US4] Исправить normalization audit semantics и regression matrix для corrupt/truncated/valid media в `apps/server/src/twobrain_rec_server/normalization/audit.py` и `apps/server/tests/integration/test_playback_normalization_media_matrix.py`.

## Phase 6: Canonical manual-upload handoff (P1)

- [X] T016 [P] [US4] Сначала добавить failing tests exact canonical source, zero original submit, one provider POST и MIME/filename в `apps/server/tests/integration/test_mediascribe_processing_happy_path.py` и `apps/server/tests/contract/test_mediascribe_client_contract.py`.
- [X] T017 [P] [US4] Сначала добавить Temporal pending/manual/replay и crash-start tests в `apps/server/tests/unit/test_processing_temporal_workflow.py` и `apps/server/tests/integration/test_processing_worker_restart.py`.
- [X] T018 [P] [US4] Сначала добавить no-archive storage/playback/purge tests в `apps/server/tests/integration/test_manual_media_upload.py` и `apps/server/tests/integration/test_finalize_processing_autostart.py`.
- [X] T019 [US4] Создавать normalization job для всех manual uploads и сохранять transient custody в `apps/server/src/twobrain_rec_server/ingest/finalize.py` и `apps/server/src/twobrain_rec_server/ingest/manual_media_upload.py`.
- [X] T020 [US4] Добавить pre-submit normalization gate и exact canonical source selection в `apps/server/src/twobrain_rec_server/workflows/worker.py`, `apps/server/src/twobrain_rec_server/processing/store.py` и `apps/server/src/twobrain_rec_server/processing/submit.py`.
- [X] T021 [US4] Добавить bounded Temporal wait/manual wake, отдельный от provider watchdog, с `continue_as_new` и replay current-history без нового workflow type в `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py` и replay tests.
- [X] T022 [US4] Reconcile persisted `starting`/`workflow_started` processing intent с deterministic Temporal start, `REJECT_DUPLICATE`, ambiguous-start recovery и tenant reconstruction в `apps/server/src/twobrain_rec_server/processing/pickup.py`, `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`, `apps/server/src/twobrain_rec_server/workflows/worker.py`, `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py`, `apps/server/src/twobrain_rec_server/processing/lifecycle.py` и start-policy tests.
- [X] T023 [US4] Реализовать единый revision no-archive policy, transient canonical без playback/storage reserve/commit, processing-safe selector и двухфазный race-safe purge через существующий journal в `apps/server/src/twobrain_rec_server/normalization/service.py`, `apps/server/src/twobrain_rec_server/billing/storage.py`, `apps/server/src/twobrain_rec_server/cabinet/egress.py`, `apps/server/src/twobrain_rec_server/deletion/service.py` и `apps/server/src/twobrain_rec_server/processing/store.py`.
- [X] T024 [US4] Ограничить multipart MIME и canonical filename в `apps/server/src/twobrain_rec_server/mediascribe/client.py` и `apps/server/src/twobrain_rec_server/processing/submit.py`.

## Phase 7: Terminal projection and recovery UX (P1/P2)

- [X] T025 [P] [US2] Сначала заменить ошибочный `invalid_audio_payload → processed` контракт terminal expectations в `apps/server/tests/integration/test_processing_failures.py`, `apps/server/tests/contract/test_processing_status_contract.py` и `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.
- [X] T026 [US2] Terminalize provider input-audio failure и добавить legacy projection fallback в `apps/server/src/twobrain_rec_server/processing/submit.py`, `apps/server/src/twobrain_rec_server/processing/status.py` и `apps/server/src/twobrain_rec_server/processing/store.py`.
- [X] T027 [US4] Добавить normalization countdown, «Повторить подготовку», idempotent due-now под revision/job fencing, dispatch и wake processing workflow, а также terminal no-poll UX в `apps/server/src/twobrain_rec_server/api/processing.py`, `apps/server/src/twobrain_rec_server/normalization/service.py`, `apps/server/src/twobrain_rec_server/normalization/pickup.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и связанных routes/templates.

## Phase 8: Validation and release readiness

- [X] T028 [P] Обновить `[Unreleased]`, operational metrics и runbook в `CHANGELOG.md`, `apps/server/src/twobrain_rec_server/admin/metrics.py` и `specs/206-mediascribe-polling-recovery/quickstart.md`.
- [X] T029 Выполнить updated checklists, `$speckit-analyze`, quickstart, focused tests, replay evidence, `git diff --check` и `infra/scripts/ci-local.sh --fast`.
- [ ] T030 Провести Product Design audit web/embedded flow на pending, retry countdown, terminal failure и success; сохранить текущие screenshots/evidence вне git.
- [ ] T031 Выполнить scoped/current-SHA gate без повторного Full CI, PR/review/merge/release/deploy и production E2E на real ready, recoverable corrupt, no-archive и terminal recordings.
