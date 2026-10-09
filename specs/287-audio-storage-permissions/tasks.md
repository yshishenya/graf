# Tasks: Надёжная подготовка аудио при платном хранении

## Phase 1: Requirements gates

- [X] T001 Проверить требования, независимые reviewer-owned checklists и анализ в specs/287-audio-storage-permissions/checklists/, specs/287-audio-storage-permissions/analysis.md; синхронизировать GitHub ownership. FR001–008. (Issue #7582)

## Phase 2: User Story 1 — платное хранение

- [X] T002 [US1] Добавить причинную проверку подготовки personal под настоящей медиаролью и матрицу существующего расчёта в apps/server/tests/integration/test_playback_normalization_postgres.py; воспроизвести RED до изменения кода. FR001/002/006/007, SC001/004. (Issue #7582)
- [X] T003 [US1] Сузить только форму чтения bonus/invoice в apps/server/src/twobrain_rec_server/billing/purchases.py и согласовать apps/server/tests/unit/test_storage_packages.py и существующие помощники test_billing_entitlements.py/test_renewal_charge.py; сохранить отсутствие строки/NULL и все финансовые ветки. FR002/003, SC001. (Issue #7582)

## Phase 3: User Story 2 — границы доступа

- [X] T004 [US2] Назначать, очищать и точно проверять минимальные права столбцов в apps/server/scripts/bootstrap_runtime_database_roles.py; согласовать apps/server/tests/fixtures/postgres_test_database.py, apps/server/tests/integration/test_playback_normalization_postgres.py и apps/server/tests/integration/test_rls_postgres_policies.py. Добавить проверки чужих строк/лишних полей/записи/повторного bootstrap. FR003–007, SC002/003/004. (Issue #7582)

## Phase 4: Validation and delivery

- [X] T005 Выполнить quickstart-профили, независимое ревью и convergence; сохранить результаты в specs/287-audio-storage-permissions/validation.md, changes/unreleased/F287.yaml. FR001–008, SC001–004. Commit/merge/CI/release/production ворота остаются отдельно до разрешения владельца. (Issue #7582)

## Dependencies

T001 → T002 (RED) → T003 → T004 → T005. Параллельных изменений одних файлов нет.

## GitHub

T001–T005: [#7582](https://github.com/yshishenya/graf/issues/7582). Reservation T000 преобразована в T001; дубликаты не создавались. before_taskstoissues canon ensure и after_taskstoissues canon validate выполнены: PASS, 300 issues. Analyze PASS перед реализацией.

## Локальное завершение реализации

T001–T005 проверены: validation.md, code-review.md, convergence.md. Выпуск и установка требуют отдельных ворот, issue #7582 остаётся открыт до PR/приёмки. Новых задач реализации не выявлено.
