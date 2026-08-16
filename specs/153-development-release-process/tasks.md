# Tasks: Процесс от разработки до релиза

**Input**: Design documents from `/specs/153-development-release-process/`

## Phase 1: Documentation

- [X] T001 [US1] Проверить текущие validation lanes и production gate в `docs/agent-guidance/release-and-validation.md`, `infra/scripts/ci-local.sh` и `infra/scripts/cd-remote.sh`.
- [X] T002 [US1] Добавить единый development-to-release workflow и full-CI decision rule в `docs/agent-guidance/release-and-validation.md`.
- [X] T003 [US2] Добавить русскую запись о процессе в `CHANGELOG.md`.
- [X] T004 [US2] Зафиксировать contract и quickstart в `specs/153-development-release-process/contracts/development-release-process.md` и `specs/153-development-release-process/quickstart.md`.

## Phase 2: Validation

- [X] T005 [US1] Сверить команды, exact-SHA правило, approval gate и incident-only исключение с текущими скриптами.
- [X] T006 [US2] Выполнить `git diff --check` и markdown review; подтвердить отсутствие runtime-изменений.

## Dependencies & Execution Order

- T001 блокирует T002.
- T002 и T003 должны быть завершены до T005.
- T004 и T005 должны быть завершены до T006.
