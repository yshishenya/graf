# Tasks: Безопасное восстановление авторизации и навигации

**Input**: Design documents from `/specs/136-auth-navigation-recovery/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/cabinet-navigation-lifecycle.md`, `quickstart.md`
**Risk / Validation Lane**: High-risk feature — auth, sessions, WebKit history
and user-visible native navigation.

## Статус восстановления 2026-10-17

Исторические IDs и завершённые отметки сохранены из архива; `[X]` ниже, кроме
новой текущей evidence, отражают прежний учёт, а не новую приёмку на master.
Открытые issues перепроверены: T004 #4731, T005 #4732, T006 #4733,
T010 #4737, T011 #4738, T012 #4739, T016 #4743. Их отметки восстановлены в `[ ]`.
Текущий срез выполняет T005/T006/T010 и T017; остальные открытые задачи не
закрываются автоматически. Закрытые исторические issues повторно не закрывать.

## Phase 1: Setup

**Purpose**: Зафиксировать регрессионную матрицу до изменения shared policy.

- [X] T001 [P] Add replay-safe auth-action and stable-login route policy tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`.
- [X] T002 [P] Add navigation-policy tests for POST, callback, provider link, Back/Forward/Reload and prior-session history in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.

## Phase 2: Foundational session/navigation lifecycle

**Purpose**: Сделать один общий replay-safe predicate и отложенную границу
сессии, от которых зависят все пользовательские сценарии.

- [X] T003 Implement stable-document and transient-request predicates, including root-only login/signup replay safety, in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [ ] T004 Implement a minimal primary-sign-in versus authenticated-provider-link continuation state and keep external origins blocked outside those continuations in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [X] T005 Replace per-POST history fencing with a deferred, committed session-boundary transition in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [X] T006 Update the shared regression matrix for the predicates and session transition ordering in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.

**Checkpoint**: No action, OAuth leg or callback can become the declarative route;
session history is cleared only after a stable target has been committed.

## Phase 3: User Story 1 — Завершить вход без повторного запуска (Priority: P1)

**Goal**: Email, VK ID and Яндекс flows perform one explicit action and reach a
safe terminal document without a SwiftUI-generated replay.

**Independent Test**: Focused XCTest matrix proves auth actions are transient,
root login is stable, primary OAuth is allowed only after an allowed start, and
a protected final page commits the new session boundary.

- [X] T007 [US1] Commit `currentRoute` and `lastLoadedRequestIdentity` only for stable final documents, preserving the last stable page during auth actions, provider pages and callbacks, in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [X] T008 [US1] Extend auth-flow regression assertions for email start/verify, VK/Yandex start, provider callback and restart-safe recovery in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.

**Checkpoint**: Primary sign-in can be completed or safely abandoned without
replaying POST or provider start.

## Phase 4: User Story 2 — Предсказуемо пользоваться навигацией (Priority: P1)

**Goal**: Native controls and WebKit gestures share one safe history policy
without restricting ordinary meetings/settings navigation.

**Independent Test**: Focused XCTest matrix proves transient entries are skipped
or disabled, normal pages remain navigable, and prior protected history remains
unavailable after logout/login or expiry.

- [X] T009 [US2] Route native Back, Forward, Reload and back/forward gesture decisions through the stable-document predicate and preserve existing accessibility identifiers in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [X] T010 [US2] Add normal-history and post-session-boundary control-state assertions in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.

**Checkpoint**: Native navigation is useful on normal documents and cannot
replay an action or expose a prior session.

## Phase 5: User Story 3 — Не повторять действия в настройках (Priority: P2)

**Goal**: Settings form actions and authenticated provider linking preserve the
current session and only commit their stable result page.

**Independent Test**: Focused XCTest matrix proves an approved provider-link
continuation can use OAuth without a session reset, while arbitrary external
links remain blocked and Settings POST never becomes a declarative GET.

- [ ] T011 [US3] Apply the continuation and transient-route rules to provider-link and Settings action paths in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [ ] T012 [US3] Add provider-link and Settings POST regression coverage in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift` and `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.

**Checkpoint**: Authenticated provider linking works inside the allowed boundary
without opening arbitrary external content or losing the active session.

## Phase 6: Validation and closeout

**Purpose**: Prove the high-risk behavior, update the user-facing change record
and preserve metadata-only evidence.

- [X] T013 Update the Unreleased fix entry for Feature 136 in `CHANGELOG.md`.
- [X] T014 Run the focused tests listed in `specs/136-auth-navigation-recovery/quickstart.md` and record only command/result evidence in `specs/136-auth-navigation-recovery/tasks.md`.
- [X] T015 Run `infra/scripts/ci-local.sh` and record the result in `specs/136-auth-navigation-recovery/tasks.md`.
- [ ] T016 Perform the metadata-only manual smoke matrix from `specs/136-auth-navigation-recovery/quickstart.md` and record pass/fail and any bounded limitation in `specs/136-auth-navigation-recovery/tasks.md`.

## Dependencies & Execution Order

1. T001–T002 define the expected policy and may proceed in parallel.
2. T003–T006 establish shared replay/session behavior; complete before story
   implementation.
3. T007–T008 deliver primary login recovery.
4. T009–T010 add safe native controls after the shared predicate exists.
5. T011–T012 extend the same design to authenticated provider links/settings.
6. T013–T016 close out only after all story checkpoints pass.

## Parallel Opportunities

- T001 and T002 touch different test concerns and can run in parallel.
- After T003–T005 are complete, T008 and T010 can be prepared in parallel with
  careful merge of `DesktopCabinetWorkspaceTests.swift`.
- T013 is independent of code mechanics but must describe the final verified
  user-visible outcome.

## Implementation Strategy

1. Deliver the foundational replay/session predicates first and make their
   tests pass.
2. Complete US1 to restore login before expanding the shared behavior.
3. Complete US2 and US3 using the same predicate; do not add route-specific
   server fallbacks or parallel navigation mechanisms.
4. Run all focused and repository validation before asking for an implementation
   commit or release decision.

## Текущая проверка и сопровождение

- [ ] T017 Подготовить `changes/unreleased/F136.yaml`, текущую RED/GREEN матрицу и `specs/136-auth-navigation-recovery/validation.md`, независимое итоговое ревью и converge для T005/T006/T010; перед коммитом получить согласие, а проверки PR на точном SHA подтвердить отдельно.

T017 зависит от T005/T006/T010. T004/T011/T012 зависят от отдельного
исправления OAuth continuation. T016 требует единственного доступного GRAF Dev
и разрешённого тестового входа; автоматические тесты не заменяют эту приёмку.
Старые T013–T015 относятся к архивному срезу; текущий fragment/checks принадлежат T017.

## Историческая validation evidence (не текущая приёмка)

- `swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests` — PASS (15 tests).
- `swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests` — PASS (43 tests).
- `swift test --package-path apps/macos` — PASS (645 tests).
- `infra/scripts/ci-local.sh` — PASS: macOS build/tests/contracts, server tests
  (2456 passed, 1 skipped), strict RLS tests (42 passed, 1 skipped), lint,
  Python compile, deployment-evidence scan.
- T016 remains open: an OAuth/email manual smoke needs an approved test account
  and one-time code. No credentials, URLs, cookies or meeting content were
  accessed or recorded.

## Phase 7: Convergence

- [X] T018 Ограничить безопасные auth-документы корневыми `/login` и `/sign-up` в общей политике истории и сохранении маршрута SwiftUI; вложенные email/OAuth actions остаются разрешёнными живому WebKit, но не становятся повторно открываемыми документами. Дополнить `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`, исправить `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` и записать RED/GREEN в `specs/136-auth-navigation-recovery/validation.md` по FR-002, FR-003, FR-005, SC-002, SC-003 (partial, HIGH).


Текущий итог implement 18.10.2026: T005/T006/T010/T018 реализованы и
проверены локально; 83 профильных PASS и полный повтор1245:1243 PASS,
2 SKIP,0 FAIL. Первый полный отказ одного notification focus test сохранён
в validation.md; отдельный и полный повтор без правок прошли, причина
нестабильности не установлена. Отметки [X] относятся к реализации, не к
принятию GitHub. #4732/#4733/#4737/#7652 остаются OPEN до принятого PR и
своих критериев закрытия. T017 остаётся [ ]: коммит и PR пока отсутствуют.
T004/T011/T012/T016 остаются [ ]; вся F136 не завершена.
