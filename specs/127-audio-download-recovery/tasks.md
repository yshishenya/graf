# Tasks: Восстановление скачивания аудио

## Phase 1: User Story 1 — доступный audio artifact (P1)

- [X] T001 [US1] Добавить регрессионный contract test для menu link в `apps/server/tests/contract/test_recording_governance_ui_contract.py`: ссылка сохраняет default action, её закрытие меню отложено, а не-link menu items по-прежнему закрывают меню синхронно.
- [X] T002 [US1] Изменить общий menu click-handler в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, чтобы для `a[href]` сначала выполнялся default navigation/download, затем через `window.setTimeout(..., 0)` закрывалось меню.

## Phase 2: User Story 2 — отказ и повтор (P1)

- [X] T003 [P] [US2] Обновить `CHANGELOG.md` в секции `[Unreleased]`, зафиксировав восстановление скачивания аудио без изменения server-mediated egress, auth и fail-closed policy.
- [X] T004 [US2] Выполнить сценарии из `specs/127-audio-download-recovery/quickstart.md`, включая focused server contracts, существующие artifact egress tests при доступной БД, `swift test --filter DesktopCabinetConfigurationTests`, `swift test --filter DesktopCabinetRoutePolicyTests` и `infra/scripts/ci-local.sh`; записать metadata-only evidence в `specs/127-audio-download-recovery/quickstart.md` и отметить завершённые задачи только после проверки.
