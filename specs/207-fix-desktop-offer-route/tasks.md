# Tasks: Safe Desktop Offer Route

**Input**: Design documents from `specs/207-fix-desktop-offer-route/`

**Validation lane**: Significant feature / shared security boundary

## Phase 1: User Story 1 — Прочитать оферту перед оплатой (P1)

**Goal**: Точный `/offer` безопасно открывается во внешнем браузере, checkout остаётся доступным, а неизвестные sibling routes по-прежнему блокируются.

**Independent Test**: Выполнить сценарий из `specs/207-fix-desktop-offer-route/quickstart.md`; focused suite должна доказать exact allow, sanitization и negative sibling behavior.

- [X] T001 [US1] Добавить regression checks для `/offer`, sanitization и `/offer/extra` в `apps/macos/Shared/Tests/DesktopCabinetBillingHandoffTests.swift`
- [X] T002 [US1] Разрешить точный browser-owned `/offer` через существующую policy без новой абстракции в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`

## Phase 2: Closeout and PR evidence

- [X] T003 Обновить пользовательский changelog в `CHANGELOG.md` и implementation evidence в `specs/207-fix-desktop-offer-route/tasks.md` после focused test, Swift build и `infra/scripts/ci-local.sh --fast`
- [ ] T004 После merge подготовить отдельный exact-SHA macOS release candidate, пройти full/signing/notarization/Sparkle gate и записать installed production smoke в `specs/207-fix-desktop-offer-route/validation/implementation-evidence.md`

## Dependencies

- T001 → T002: regression contract first.
- T002 → T003: closeout only after behavior is implemented.
- T003 → T004: release candidate only after validated PR merge and explicit release approval.

## Parallel Opportunities

Нет безопасной параллели: patch состоит из одного общего policy case и одного связанного regression suite.

## Implementation Strategy

1. Зафиксировать fail-closed contract тестом.
2. Внести минимальный exact-path policy change.
3. Запустить focused checks и fast lane, затем подготовить PR evidence.
4. Full exact-SHA validation, signing, notarization and Sparkle publication выполнить только для отдельно утверждённого release candidate и закрыть installed-app smoke.

## Implementation Evidence — 2026-08-28

- RED: `swift test --package-path apps/macos --filter DesktopCabinetBillingHandoffTests` — expected FAIL только нового `/offer` contract (4 failures); negative sibling assertion и 8 прежних тестов PASS.
- GREEN: тот же focused suite — 9/9 PASS.
- Sibling policy: `swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests` — 16/16 PASS.
- Compile: `swift build --package-path apps/macos` — PASS.
- Repository fast lane: `infra/scripts/ci-local.sh --fast` — PASS; 1248 server unit tests, Ruff и Python compile.
- Full CI: не запускался; обязателен для T004 на exact release-candidate SHA.
- Production release/appcast/installed-app smoke: pending T004.
- Tracker canon: Feature 207 issues #5901–#5904 соответствуют project canon; глобальный validator PASS — 300/300 открытых Spec Kit issues.
