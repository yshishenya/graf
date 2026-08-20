# Tasks: Подключение email без тупиков

**Input**: Design documents from `specs/178-account-linking-journey/`

**Tests**: Обязательны test-first: auth/data mutation и high-risk UX требуют regression checks до реализации.

## Phase 1: Schema and policy inventory

**Purpose**: добавить закрытый workspace kind и точные proof bindings, не предполагая несуществующий production constraint.

- [X] T001 Добавить failing migration contract для фактического отсутствующего/существующего `ck_workspaces_kind`, нового `linked` kind, proof foreign keys и неизменного partial personal-owner index в `apps/server/tests/integration/test_postgres_migrations.py`
- [X] T002 Добавить migration `0074_linked_workspace_and_merge_proofs.py`, которая безопасно создаёт/заменяет workspace-kind check и добавляет nullable proof foreign keys, в `apps/server/src/twobrain_rec_server/db/migrations/versions/0074_linked_workspace_and_merge_proofs.py`
- [X] T003 Обновить ORM constraints и `AccountMergeIntent` proof fields в `apps/server/src/twobrain_rec_server/db/models/identity.py` и `apps/server/src/twobrain_rec_server/db/models/federated_auth.py`
- [X] T004 Добавить полный failing disposition inventory contract для каждого model FK на `user_identities` в `apps/server/tests/unit/test_account_merge_policy.py`

**Checkpoint**: новые schema values доступны, personal uniqueness и существующие RLS policies не ослаблены, новый FK нельзя добавить без explicit disposition.

## Phase 2: Foundational auth and capability boundaries

**Purpose**: общий fail-closed contract для всех user stories.

- [X] T005 [P] Добавить failing tests для exact session/source-identity/callback/link proof binding, workspace/provider fingerprint и same/different idempotency keys в `apps/server/tests/unit/test_account_merge_policy.py`
- [X] T006 [P] Добавить failing tests: linked доступен active member, но исключён из personal/corporate capability classes, в `apps/server/tests/unit/test_workspace_onboarding.py`, `apps/server/tests/unit/test_admin_permissions.py` и `apps/server/tests/unit/test_admin_invitations.py`
- [X] T007 [P] Добавить failing billing/trial/referral/fair-use lineage и comprehensive mutable-billing blocker tests в `apps/server/tests/unit/test_billing_entitlements.py`, `apps/server/tests/unit/test_billing_trust_boundaries.py` и `apps/server/tests/unit/test_referrals.py`
- [X] T008 [P] Добавить failing whole-account-close-from-linked и public-referral-link-after-conversion tests в `apps/server/tests/unit/test_account_closure.py` и `apps/server/tests/unit/test_referrals.py`
- [X] T009 Расширить `MergePreview` verified provider/workspace/domain state, policy version, locks и fingerprint, а также exact proof recheck в `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [X] T010 Разрешить active linked membership в list/activation, сохранив corporate-only join paths, в `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py`
- [X] T011 Ограничить whole-account close personal owner scope и public referral binding personal scope в `apps/server/src/twobrain_rec_server/auth/account_closure.py` и `apps/server/src/twobrain_rec_server/billing/referral_binding.py`
- [X] T012 Сделать trial/referral/fair-use eligibility lineage-aware без переписывания historical rows в `apps/server/src/twobrain_rec_server/billing/trial.py`, `apps/server/src/twobrain_rec_server/billing/referral_binding.py` и `apps/server/src/twobrain_rec_server/billing/fair_use.py`

**Checkpoint**: linked — доступное пространство, но не второй personal и не corporate team; proof/eligibility boundaries исполнимы до merge mutation.

## Phase 3: User Story 1 — Подключить email и сохранить оба пространства (Priority: P0) 🎯 MVP

**Goal**: два полноценных personal профиля объединяются без потери boundaries и без второго набора privileges.

**Independent Test**: synthetic merge сохраняет IDs/content/access, source personal становится linked, sessions/devices revoked, proof/replay/rollback/domain blockers fail closed.

### Tests for User Story 1

- [X] T013 [P] [US1] Добавить failing PostgreSQL integration cases для personal+personal success, default/custom name, stable workspace/meeting IDs, identities/memberships, sessions/devices, rollback, stale, expired и same/different-key replay в `apps/server/tests/integration/test_account_merge.py`
- [X] T014 [P] [US1] Добавить failing app-role/forced-RLS personal+personal case с workspace/domain row locks и post-merge access в `apps/server/tests/integration/test_rls_postgres_policies.py`
- [X] T015 [P] [US1] Добавить failing end-to-end email-link preview/confirm/cancel/re-login flow с двумя реальными personal profiles для browser и desktop в `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T016 [P] [US1] Добавить failing domain disposition cases для pending join offers, active user share grants, trial/referral/fair-use lineage, notification/calendar preferences, active summary templates и их collisions, а также billing/calendar/deletion и unfinished upload/requested export blockers в `apps/server/tests/integration/test_account_merge.py`

### Implementation for User Story 1

- [X] T017 [US1] Считать ровно одну safe personal root каждой стороны confirmable, блокировать сложные ownership/domain shapes и под locks преобразовать source personal в linked до owner transfer в `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [X] T018 [US1] Заполнить exact proof bindings из email-link и provider-link callers в `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py` и `apps/server/src/twobrain_rec_server/auth/provider_links.py`
- [X] T019 [US1] Перенести/deduplicate active access rows, включая memberships, pending join offers и active user share grants, сохранив historical actors, в `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [X] T020 [US1] Расширить billing/calendar/deletion/referral preflight до всех mutable authority states и сохранить lineage/history в `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [X] T021 [US1] Исправить expired confirm и different-key completed replay без ложного success в `apps/server/src/twobrain_rec_server/auth/account_merge.py` и `apps/server/src/twobrain_rec_server/cabinet/web_routes/account_merge.py`
- [X] T022 [US1] Выполнить focused backend suite US1 и зафиксировать только metadata-only результаты в `specs/178-account-linking-journey/evidence.md`

**Checkpoint**: root-cause и связанные security/data defects закрыты независимо от нового UI.

## Phase 4: User Story 2 — Понять решение и безопасно отказаться (Priority: P1)

**Goal**: task-led экран объясняет «сейчас → после», сохранность данных и safe cancel без внутренних терминов.

**Independent Test**: contract markup содержит фактические способы входа, три IA уровня, точные CTA, zero-mutation cancel и понятный post-success re-login result.

### Tests for User Story 2

- [X] T023 [P] [US2] Добавить failing markup/copy/compact-heading-flow/disclosure/provider/CTA/internal-term tests в `apps/server/tests/contract/test_account_merge_contract.py`
- [X] T024 [P] [US2] Добавить failing cancel, expired, success-login-message и browser/desktop return-route tests в `apps/server/tests/contract/test_account_routes.py` и `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 2

- [X] T025 [US2] Подготовить bounded presentation model из provider registry и merge preview без raw identifiers в `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T026 [US2] Перестроить template в компактную IA «итог → Сейчас/После → пространства/встречи → повторный вход → details → действия» без numbered wizard в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/account_merge_content.html`
- [X] T027 [US2] Добавить минимальный feature-scoped responsive CSS и warning/error tones на существующих tokens в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T028 [US2] Заменить cancel и post-success login copy на пользовательские результаты без `auth_session_invalid` в `apps/server/src/twobrain_rec_server/cabinet/rendering.py` и `apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py`

**Checkpoint**: confirm и decline понятны без технических деталей и не заканчиваются ложной ошибкой сессии.

## Phase 5: User Story 3 — Получить конкретный выход из редкого конфликта (Priority: P1)

**Goal**: настоящий blocker остаётся fail closed, но всегда даёт существующее доступное действие.

**Independent Test**: billing/calendar/deletion/role/meeting/referral states имеют truthful copy и route/support fallback; ни один не заканчивается только отменой.

### Tests for User Story 3

- [X] T029 [P] [US3] Добавить failing blocker-action matrix, safe reference и no-support fallback contracts в `apps/server/tests/contract/test_account_merge_contract.py`
- [X] T030 [P] [US3] Добавить failing browser/desktop route parity cases для blocker actions в `apps/server/tests/contract/test_account_routes.py`

### Implementation for User Story 3

- [X] T031 [US3] Сформировать bounded blocker presentation с billing/calendar/account routes и configured support fallback в `apps/server/src/twobrain_rec_server/cabinet/web_routes/account_merge.py`
- [X] T032 [US3] Отобразить для каждого blocker причину, неизменность данных и доступное действие без обещания несуществующей заявки в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/account_merge_content.html`

**Checkpoint**: все seeded blockers имеют concrete safe exit.

## Phase 6: User Story 4 — Одинаковый доступный опыт в web и macOS (Priority: P2)

**Goal**: один server-rendered flow и provider linking доступны на wide, 390px и embedded macOS surface.

**Independent Test**: same IA/copy/outcomes, strict nonce, existing allowlist, external-auth continuation, logical focus/heading order и no-overflow evidence.

### Tests for User Story 4

- [X] T033 [P] [US4] Добавить failing settings provider callback cases с correct/missing/wrong browser-state cookie в `apps/server/tests/contract/test_auth_contracts.py`
- [X] T034 [P] [US4] Добавить failing provider-link-start auth-continuation и unchanged merge/email allowlist cases в `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`
- [X] T035 [P] [US4] Добавить 390px scrollWidth, focus и disclosure runtime case в `apps/macos/Shared/Tests/CabinetSidebarRuntimeTests.swift`

### Implementation and validation for User Story 4

- [X] T036 [US4] Передать existing browser-state cookie в provider-link callback verifier в `apps/server/src/twobrain_rec_server/api/auth.py`
- [X] T037 [US4] Классифицировать desktop provider-link start как existing external-auth continuation без расширения unknown-route allowlist в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T038 [US4] Пройти wide/390px web flow через in-app Browser и embedded flow через GRAF Dev; хранить synthetic captures вне git и записать metadata-only conclusions в `specs/178-account-linking-journey/evidence.md`

**Checkpoint**: web и приложение дают один завершённый путь без overflow, nonce gap и dead ends.

## Phase 7: Polish, review and release readiness

- [X] T039 [P] Обновить понятный `[Unreleased]` changelog в `CHANGELOG.md`
- [X] T040 Провести correctness/root-cause и security/privacy review, исправить findings и повторить focused tests в `apps/server/tests/`
- [X] T041 Провести UX/UI/IA/CX, accessibility и Product Design visual QA против выбранного mockup; исправить P0–P2, хранить captures вне git и записать report в `design-qa.md`
- [X] T042 Провести Ponytail review, удалить дублирование/лишние механизмы и повторить затронутые regression checks в `apps/server/`
- [X] T043 Выполнить `infra/scripts/ci-local.sh --fast` на финальном committed diff после review fixes и записать immutable tested SHA, retained artifact reference/digest и результат в `specs/178-account-linking-journey/evidence.md`
- [X] T045 [P] Добавить runtime regression для legacy `AccountMergeIntent` без обязательных proof bindings: `proof_required`, без account/data mutation, в `apps/server/tests/integration/test_account_merge.py`
- [X] T046 [P] Расширить downgrade regression проверкой восстановленного workspace-kind constraint, неизменного partial personal-owner index и точных legacy RLS policy predicates в `apps/server/tests/integration/test_postgres_migrations.py`
- [X] T047 Закрепить доказуемый вне-git capture bundle ID и synthetic fixture digest без живых локальных путей в `specs/178-account-linking-journey/design-qa.md`; если прежний bundle недоступен, повторить synthetic captures перед closeout
- [ ] T044 После T043, T045–T047 синхронизировать `tasks.md` и GitHub issues, подготовить русский PR/review/merge и production release evidence по `docs/agent-guidance/release-and-validation.md`

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 выполняются последовательно.
- US2 и US3 зависят от bounded preview Phase 2 и стабильного US1 backend.
- US4 зависит от окончательных routes и markup US2/US3.
- Review/release начинается только после всех user stories.

## Parallel Opportunities

- T005–T008; T013–T016; T023–T024; T029–T030; T033–T035.
- CHANGELOG T039 можно готовить параллельно с первыми review-проходами после стабилизации behavior.

## Implementation Strategy

Минимальный безопасный increment — Phase 1–3. UI и blocker actions используют
существующий server-rendered flow; отдельный wizard, SPA state, support service,
provider icons и новые зависимости не создаются. Unknown user-reference rows
fail the disposition contract instead of silently inheriting a default policy.
