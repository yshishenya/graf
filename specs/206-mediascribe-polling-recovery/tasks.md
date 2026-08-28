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
- T014–T015 дополняют media-recovery после T001–T009.
- T025 → T026 → T027 после backend/status semantics.
- T010–T012 после T001–T009, T013–T015 и T025–T027.

## Implementation Strategy

Сначала минимально разделить polling budget и recovery limit, затем покрыть
Temporal/status projection. Не менять MediaScribe и не создавать новые
provider jobs. Коммиты, PR, merge, release и deploy остаются отдельным шагом
после проверки и явного одобрения.

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
- T025: #5890
- T026: #5892

## Дополнение: tolerant media recovery

- [X] T014 [P] [US1] Выполнить tolerant first-pass recovery и строгую проверку результата в `apps/server/src/twobrain_rec_server/normalization/media.py` и `apps/server/src/twobrain_rec_server/normalization/service.py`.
- [X] T015 [P] [US1] Добавить audit/readiness guards и regression matrix для повреждённых, усечённых и валидных media-файлов в `apps/server/src/twobrain_rec_server/normalization/audit.py`, `apps/server/src/twobrain_rec_server/normalization/worker.py` и `apps/server/tests/`.

## Дополнение: terminal input-audio recovery

- [X] T025 [P] [US2] Зафиксировать contract/integration checks для `invalid_audio_payload/input_audio`, единого terminal-статуса и остановки frontend polling. (#5890)
- [X] T026 [US2] Терминализировать новый provider input-audio failure, согласовать legacy `processed` projection, сделать новую попытку текущей во всех проекциях и защитить её canonical no-archive source от purge старой попыткой. (#5892)
- [X] T027 [US2] Удалить эвристический fallback выбора исторического результата: определять текущую попытку через обязательную цепочку `processing_result → mediascribe_job → processing_workflow`, сохранить принятый outcome по current pointer и не допускать migration hash в новую генерацию.
