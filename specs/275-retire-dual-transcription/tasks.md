# Tasks: Единый источник расшифровки — F275

Input: spec.md, plan.md, research.md, data-model.md, contracts/transcription.md. Lane: high-risk-feature.

## Phase 1: Setup

- [X] T001 Подготовить инвентаризацию границ в specs/275-retire-dual-transcription/research.md и прочитать независимый review-report.md. Отчёт и пользовательские checklists изменяет только независимый рецензент, не исполнитель (FR-006, FR-008).

## Phase 2: Foundations

- [X] T002 Перевести положительные server fixtures на единый источник и сохранить отдельные historical negative fixtures в apps/server/tests/fixtures/artifacts.py, processing.py, recording_sync.py (FR-008).

## Phase 3: US1 — Единый файл

Independent test: WAV/manual M4A → один POST → result; прежний fingerprint выдерживает retry.

- [X] T003 [P] [US1] Сначала обновить contract/integration проверки MediaScribe, затем удалить paired submit/source selection и лишние параметры в apps/server/src/twobrain_rec_server/mediascribe/client.py, processing/submit.py, processing/store.py, workflows/worker.py; сохранить fingerprint, known-ID poll/delete, завершить unsupported pending/unknown без отправки; default нового job single_track в db/models/processing.py и при необходимости новой migration (FR-001, FR-003, FR-005, FR-006).

## Phase 4: US2 — Запрет возобновления старого пути

Independent test: новое и продолжаемое старое upload получают отказ; очередь сохраняет read/delete без отправки.

- [X] T004 [P] [US2] Сначала добавить negative admission/restart тесты, затем удалить старые write defaults и legacy role acceptance в apps/server/src/twobrain_rec_server/api/schemas.py, ingest/meetings.py, sessions.py, parts.py, finalize.py, manifest.py, store.py, media_revisions.py; сохранить историческое чтение и manual-upload; актуализировать положительные ingest tests (FR-004, FR-006, FR-008).
- [X] T005 [P] [US2] Сначала добавить legacy-queue/no-network regressions, затем удалить старые payload/descriptors, блокировать старые persisted items и retries в apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift, DesktopUploadQueueService.swift, DesktopUploadCustodyProjection.swift и apps/macos/Shared/Sources/Models/AudioModelCore.swift; обновить apps/macos/Shared/Tests и README с сохранением удаления и v5 capture (FR-002, FR-004, FR-006, FR-008).

## Phase 5: US3 — Проверяемая очистка

Independent test: synthetic smoke package корректен, active docs и residue inventory согласованы.

- [X] T006 [P] [US3] Добавить проверку валидного пакета и перевести apps/server/scripts/create_test_artifact.py, upload_test_artifact.py, seed_smoke_outcome.py и infra/scripts/run-production-smoke.sh на canonical single-source; сохранить безопасные target/auth/cleanup проверки (FR-007, FR-008).
- [X] T007 [P] [US3] Заменить docs/integrations/mediascribe-dual-track-api.md на mediascribe-api.md, обновить текущие ссылки, PRD/status/readiness и активный specs/012-server-ingest-foundation/contracts/openapi.yaml; записать changes/unreleased/F275.yaml и specs/275-retire-dual-transcription/residue-inventory.md (FR-007, SC-003).

## Phase 6: Validation and closeout

- [X] T008 Выполнить quickstart.md high-risk-feature проверки server/native/scripts, независимый review и converge; записать точные результаты, ограничения и PR checks в specs/275-retire-dual-transcription/quickstart.md (FR-008, SC-001–SC-004).

## Dependencies And Parallel Execution

T001 → T002 → T003/T004/T005/T006/T007 → T008. T002 завершается до начала изменений T003–T007. T002 единолично владеет общими fixtures; после его завершения владение ими переходит T004. T003 владеет processing/mediascribe tests; T004 — ingest tests и fixtures; T005 — macOS; T006 — scripts/smoke tests; T007 — docs/readiness/OpenAPI. После T002 задачи T003–T007 работают только с непересекающимися файлами. Независимое review в T008 выполняет отдельный рецензент; исполнитель не меняет его отчёт или checklist-маркеры.

## Implementation Strategy

Сначала negative regressions и поддерживаемые fixtures, затем удаление целых веток, затем регрессия сохранённой функциональности. Ни одна задача не включает production deployment, удаление данных или переписывание applied migrations.

## GitHub

Umbrella: https://github.com/yshishenya/graf/issues/7258.

- T001 (Issue #7259): https://github.com/yshishenya/graf/issues/7259
- T002 (Issue #7260): https://github.com/yshishenya/graf/issues/7260
- T003 (Issue #7261): https://github.com/yshishenya/graf/issues/7261
- T004 (Issue #7262): https://github.com/yshishenya/graf/issues/7262
- T005 (Issue #7263): https://github.com/yshishenya/graf/issues/7263
- T006 (Issue #7264): https://github.com/yshishenya/graf/issues/7264
- T007 (Issue #7265): https://github.com/yshishenya/graf/issues/7265
- T008 (Issue #7266): https://github.com/yshishenya/graf/issues/7266
