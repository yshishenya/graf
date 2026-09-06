# Tasks: Достоверные устройства и сеансы

## Phase 1 — Foundation
- [X] T001 Проверить требования, RLS-контракт и reviewer checklists в specs/248-trustworthy-account-sessions/{spec.md,plan.md,checklists/}; выполнить analyze и issue sync до кода. [FR-001–012] (Issue #6616)

## Phase 2 — US1: Отдельные клиенты
Independent test: app/email/OAuth/browser получают разные регистрации; workspace continuation сохраняет тип.
- [X] T002 [US1] Добавить failing регрессии client metadata и независимых входов в apps/server/tests/unit/test_auth_session_clients.py и существующие tests/contract/test_auth_contracts.py, tests/unit/test_workspace_onboarding.py. [FR-001–003] (Issue #6617)
- [X] T003 [US1] Реализовать уникальные клиенты/связи во всех login callers в apps/server/src/twobrain_rec_server/auth/{sessions,callbacks,workspace_onboarding}.py, api/auth.py, cabinet/web_routes/{auth_email_flow,browser}.py; сохранить срок/тип при continuation. [FR-001–003] (Issue #6618)
- [X] T004 [P] [US1] Добавить устойчивый GRAFDesktop UA и реальную проверку POST/redirect в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift и apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift. [FR-002,012] (Issue #6619)

## Phase 3 — US2: Достоверный отзыв
Independent test: single/bulk/device revoke блокирует чужой токен и сохраняет текущий; browser handoff независим.
- [X] T005 [US2] Добавить failing проверки principal-only/device/binding-only revoke, unbound bootstrap против missing/blocked binding, current/foreign/CSRF/replay и независимого billing handoff в apps/server/tests/contract/test_auth_contracts.py, tests/contract/test_account_routes.py, tests/integration/test_web_owner_session_context.py. [FR-007–010] (Issue #6620)
- [X] T006 [US2] Реализовать общий revoke, principal device gate/last_seen и отдельную handoff session в apps/server/src/twobrain_rec_server/auth/{sessions,dependencies}.py, api/auth.py, cabinet/web_routes/{settings,billing}.py; проверить RLS в tests/integration/test_rls_stale_session_device_context.py. [FR-005–009] (Issue #6621)

## Phase 4 — US3: Понятный раздел
Independent test: current/other/expired/revoked/unknown UI, timezone, no-JS подтверждение и responsive.
- [X] T007 [US3] Добавить регрессии effective state (включая законно unbound и повреждённую binding), sorting, time zone, privacy и подтверждения в apps/server/tests/unit/test_settings_view_models.py и tests/contract/test_account_routes.py. [FR-004–006,010–012] (Issue #6622)
- [X] T008 [US3] Реализовать единый список и историю, подтверждение/отмену, тексты результатов в apps/server/src/twobrain_rec_server/cabinet/{view_models,queries,rendering}.py, web_routes/settings.py и templates/cabinet/pages/settings_account_content.html. [FR-004–006,010–012] (Issue #6623)

## Phase 5 — Validation / PR
- [X] T009 Проверить полный auth/UI путь в изолированном PostgreSQL, browser и WKWebView; пройти converge/Ponytail review, добавить changes/unreleased/F248.yaml и specs/248-trustworthy-account-sessions/evidence/implementation.md; создать PR и дождаться exact-SHA governance-fast. [FR-001–012,SC-001–004] (Issue #6624)

## Dependencies
T001 → T002 → T003; T004 после T001 (отдельные Swift файлы). T005 → T006 после T003; T007 → T008 после T006; T009 после всех реализаций. Сначала тесты, затем соответствующий код. Checklist state принадлежит рецензенту, не реализации. Tasks отмечать только после evidence.
