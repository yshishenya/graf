# Tasks: Desktop Billing Actions

**Input**: Design documents from `specs/208-desktop-billing-actions/`

**Validation lane**: High-risk product area / shared billing navigation boundary

## Phase 1: User Story 1 — Завершить действие биллинга в приложении (P1)

**Goal**: Все текущие user-visible billing actions проходят desktop route policy, а неизвестные siblings остаются blocked.

**Independent Test**: Выполнить focused сценарий из `quickstart.md`; тест должен покрыть весь contract без отправки form request и без нового платежа.

- [X] T001 [US1] Добавить полный positive/negative contract текущих billing action paths в `apps/macos/Shared/Tests/DesktopCabinetBillingHandoffTests.swift`
- [X] T002 [US1] Разрешить точные static и safe dynamic billing actions в общем `isBillingRoute` в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`

## Phase 2: Validation and closeout

- [X] T003 Запустить focused tests, Swift build и `infra/scripts/ci-local.sh --fast`, затем обновить `CHANGELOG.md` и `specs/208-desktop-billing-actions/tasks.md` фактическим evidence
- [X] T004 После merge и освобождения release/deploy lock подготовить отдельный exact-SHA macOS release, пройти full/signing/notarization/Sparkle gate и записать installed-app smoke в `specs/208-desktop-billing-actions/validation/implementation-evidence.md`

## Dependencies

- T001 → T002: regression contract first.
- T002 → T003: closeout only after implementation.
- T003 → T004: release only after validated PR merge and no concurrent release.

## Parallel Opportunities

Нет безопасной параллели: тест и общий policy helper образуют один security-sensitive diff.

## Implementation Strategy

1. Получить RED на полном action contract.
2. Исправить единственный shared helper минимальным exact allowlist.
3. Пройти focused/build/fast gates и подготовить PR.
4. Не пересекаться с текущим `.10` release; выпустить следующий exact-SHA клиент отдельным штатным циклом.

## Validation Evidence

- `DesktopCabinetBillingHandoffTests`: 10 tests, 0 failures.
- `DesktopCabinetRoutePolicyTests`: 16 tests, 0 failures.
- `swift build --package-path apps/macos`: PASS.
- `infra/scripts/ci-local.sh --fast`: PASS; server unit `1250 passed`, Ruff и
  Python compile — PASS.
- Full exact-SHA CI, Developer ID/notarization/Sparkle release и installed-app
  smoke прошли на `c428f7990843cc39c141b25c3d8dfdc8de3d66f2`; подробности — в
  `specs/208-desktop-billing-actions/validation/implementation-evidence.md` и
  `docs/deployments/2brain-rec/release-v2026.08.28.11.md`.
