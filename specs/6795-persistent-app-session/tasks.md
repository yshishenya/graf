# Tasks: Сохранение входа GRAF

## Phase 1 — Requirements
- [X] T001 Проверить требования, security checklist и analyze в specs/6795-persistent-app-session/; синхронизировать GitHub задачи до кода.

## Phase 2 — US1 Сохранение входа
Independent test: переход через сутки/30 дней при активности, обе копии cookie.
- [X] T002 [US1] Добавить регрессии срока, отказа и доставки в apps/server/tests/unit/test_auth_session_renewal.py.
- [X] T003 [US1] Реализовать условное продление и доставку в apps/server/src/twobrain_rec_server/auth/{sessions.py,dependencies.py,session_renewal.py}, config.py и main.py.
- [X] T004 [P] [US1] Добавить проверку продления и позднего ответа в apps/macos/Shared/Tests/DesktopCabinetSessionBridgeTests.swift; обновить apps/macos/RecApp/Sources/Cabinet/DesktopCabinetSessionBridge.swift и Upload/DesktopUploadClient.swift.

## Phase 3 — US2 Контроль доступа и closeout
Independent test: expiry/logout/revoke, иной origin/token и отсутствие ложной смены аккаунта.
- [X] T005 [US2] Выполнить целевые серверные/Swift проверки, включая apps/server/tests/integration/test_rls_postgres_policies.py, и анализ diff; записать результаты в specs/6795-persistent-app-session/validation.md и changes/unreleased/F6795.yaml, выполнить converge.
- [ ] T006 [US2] После разрешённого коммита выполнить governance-fast на точном SHA и проверку установленного GRAF Dev через harness; записать evidence в specs/6795-persistent-app-session/validation.md.

## Dependencies and implementation strategy
T001 → T002 → T003; T004 после T001 может выполняться параллельно с серверными T002/T003 по согласованному contracts/session-renewal.md; T003 + T004 → T005 → T006. Сервер и native должны выйти совместно. Нативная и серверная части имеют разных владельцев файлов; общий runtime не менять. Реализация не отмечает reviewer-owned checklist. T006 — отдельный внешний gate и не объявляется выполненным по локальным тестам.

## Coverage
FR-001/002/003/004/006 → T002/T003; FR-003/004/005 → T004; FR-007, SC-001/002/003 → T005/T006; T001 покрывает обязательные planning gates.

## GitHub issues

- T001: https://github.com/yshishenya/graf/issues/6931
- T002: https://github.com/yshishenya/graf/issues/6932
- T003: https://github.com/yshishenya/graf/issues/6933
- T004: https://github.com/yshishenya/graf/issues/6934
- T005: https://github.com/yshishenya/graf/issues/6935
- T006: https://github.com/yshishenya/graf/issues/6936
