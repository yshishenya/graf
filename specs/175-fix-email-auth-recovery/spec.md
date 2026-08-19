# Feature Specification: Надёжный вход по email и восстановление аккаунта

**Feature Branch**: `codex/175-fix-email-auth-recovery`

**Created**: 2026-08-19

**Status**: Ready for implementation

**Input**: User description: "Исправить все выявленные проблемы входа по email отдельной задачей и отдельной веткой; раньше вход работал"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Завершить вход по email без серверной ошибки (Priority: P0)

Пользователь получает одноразовый код, вводит его и попадает в свой существующий аккаунт без общей серверной ошибки, потери данных или повторного запроса кода.

**Why this priority**: Production-вход по email сейчас завершается HTTP 500 после уже выполненного подтверждения адреса и блокирует доступ к аккаунту.

**Independent Test**: На одноразовых PostgreSQL-данных с принудительным RLS пройти вход существующего пользователя от выдачи кода до redirect и убедиться, что создана ровно одна действующая сессия, callback-state завершён один раз и повтор кода отклоняется.

**Acceptance Scenarios**:

1. **Given** существующий пользователь с одним email-аккаунтом получил действующий код, **When** он вводит код, **Then** сервер атомарно завершает callback, выдаёт сессию и перенаправляет его в личное пространство без HTTP 500.
2. **Given** вход завершён успешно, **When** тот же код отправлен повторно, **Then** повтор отклоняется без новой сессии и без изменения данных аккаунта.
3. **Given** завершение callback невозможно, **When** транзакция откатывается, **Then** не остаётся действующей orphan-сессии, частично использованного callback-state или частично изменённого аккаунта.
4. **Given** код неверен или истёк, **When** сервер фиксирует безопасный audit outcome, **Then** callback завершается без HTTP 500 и без сессии даже при принудительном RLS.

---

### User Story 2 - Получить понятный путь при нескольких аккаунтах (Priority: P0)

Пользователь, чей подтверждённый адрес относится к нескольким GRAF-аккаунтам, видит не тупиковое сообщение, а доступные действия для безопасного подтверждения второго способа входа.

**Why this priority**: Текущий экран сообщает о необходимости второго подтверждения, но скрывает работающие способы входа и не объясняет следующий шаг.

**Independent Test**: Создать два аккаунта с одним нормализованным адресом и разными способами входа, открыть recovery-экран в web и embedded-поверхности и пройти доступный OAuth-путь до безопасного preview без автоматического объединения.

**Acceptance Scenarios**:

1. **Given** email относится к нескольким активным аккаунтам, **When** пользователь начинает вход, **Then** экран объясняет конфликт простым языком и показывает реально доступные способы подтверждения.
2. **Given** поддерживаемый OAuth-провайдер доступен, **When** пользователь выбирает его, **Then** начинается существующий защищённый linking/recovery flow с сохранением исходного безопасного destination.
3. **Given** пользователь не завершает второе подтверждение, **When** recovery истекает, отменяется или завершается ошибкой, **Then** аккаунты, встречи и сессии остаются без изменений, а повторный путь остаётся понятным.
4. **Given** неоднозначность обнаружена только после ввода кода, **When** код уже нельзя использовать повторно, **Then** пользователь получает provider recovery actions, а не тупиковую форму использованного кода.

---

### User Story 3 - Корректно связать или предложить объединение аккаунтов (Priority: P1)

Уже вошедший пользователь подтверждает email и получает правильный результат: новый способ входа связывается с текущим аккаунтом, либо показывается preview ровно одного другого аккаунта, либо неоднозначность блокирует продолжение.

**Why this priority**: Текущая классификация считает сам текущий аккаунт дополнительным кандидатом и ошибочно блокирует безопасный сценарий; последующее создание merge intent также может потерять callback-state из-за RLS-контекста.

**Independent Test**: На принудительном PostgreSQL RLS проверить три набора кандидатов после исключения текущего пользователя: 0, 1 и больше 1; доказать link, preview и fail-closed результаты, одноразовость callback и полный rollback при ошибке.

**Acceptance Scenarios**:

1. **Given** после исключения текущего пользователя других владельцев email нет, **When** код подтверждён, **Then** email identity идемпотентно связывается с текущим аккаунтом.
2. **Given** после исключения текущего пользователя остаётся ровно один другой аккаунт, включая аккаунт без встреч, **When** код подтверждён, **Then** создаётся одноразовый merge intent и показывается явный preview; данные не объединяются до отдельного подтверждения.
3. **Given** после исключения текущего пользователя остаётся больше одного аккаунта, **When** код подтверждён, **Then** система блокирует автоматический выбор и показывает безопасное состояние неоднозначности.
4. **Given** merge intent создан, **When** callback завершается после смены tenant-контекста, **Then** callback-state обновляется в разрешённой области и транзакция не падает из-за RLS.
5. **Given** linking открыт во встроенном macOS-кабинете, **When** пользователь вводит неверный код, повторяет отправку, возвращается или открывает preview, **Then** все действия остаются на `/desktop/...` маршрутах.
6. **Given** preview открыт, **When** пользователь оценивает последствия, **Then** он понимает, какой аккаунт останется основным, что произойдёт со способами входа, встречами, пространствами, сессиями и блокирующими конфликтами до подтверждения.

### Edge Cases

- Код неверен, истёк, уже использован или превышен лимит попыток.
- Callback-state исчез, принадлежит другому flow или не виден в текущем tenant-контексте.
- Пользователь или identity деактивированы между выдачей и вводом кода.
- Два запроса одновременно пытаются использовать один код или создать один merge intent.
- OAuth-провайдер отключён, недоступен или не вернул подтверждённый адрес.
- Redirect ведёт только на разрешённый first-party web/embedded destination; внешний destination не принимается.
- Ошибка возникает после подготовки сессии или merge intent, но до фиксации callback-state.
- Один и тот же адрес связан с текущим пользователем, одним другим пользователем или несколькими другими пользователями.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST complete successful email-code login as one atomic operation that leaves a valid session and a consumed single-use callback-state.
- **FR-002**: System MUST update callback-state within an authorization context that can access the state's original login workspace even after the flow selects a personal workspace or account-merge context.
- **FR-003**: System MUST preserve forced PostgreSQL RLS and MUST NOT bypass tenant isolation with an unscoped maintenance role, disabled RLS or broad cross-tenant session.
- **FR-004**: If any completion step fails, the system MUST roll back session creation, callback consumption, identity changes and merge-intent creation together.
- **FR-005**: Login and linking routes MUST own the single transaction commit and MUST prepare the safe response before committing, so response preparation failure cannot leave an orphan session or consumed callback.
- **FR-006**: A consumed, missing, expired or replayed code MUST NOT create an additional session or mutate account data.
- **FR-007**: Failure and expiry audit events MUST be written under an authorized workspace context before the exact callback terminal transition, without widening callback or audit RLS policies.
- **FR-008**: Ambiguous-email login MUST fail closed without selecting an arbitrary account and MUST render a localized, actionable recovery surface instead of an HTTP 500 or dead end.
- **FR-009**: The recovery surface MUST retain the currently configured, supported OAuth providers and explain that the user should confirm another existing sign-in method.
- **FR-010**: Provider actions MUST preserve the existing CSRF, state, nonce, rate-limit, verified-email and first-party destination protections.
- **FR-011**: Authenticated email linking MUST exclude the current user before classifying other candidate accounts.
- **FR-012**: With zero other candidates, the system MUST link the verified email identity idempotently to the current user.
- **FR-013**: With exactly one other candidate, the system MUST create a single-use merge intent and show explicit preview/confirmation without moving data automatically.
- **FR-014**: The system MUST NOT auto-confirm a cross-account merge merely because the other account currently has no counted meetings or artifacts.
- **FR-015**: With more than one other candidate, the system MUST report ambiguity and MUST NOT select, merge or expose account-specific private data.
- **FR-016**: Callback completion after creating a merge intent MUST remain RLS-safe and atomic under the same rollback and replay guarantees as ordinary login.
- **FR-017**: OAuth provider-link completion MUST restore an allowed link-state context after account-merge work before finalizing its terminal state.
- **FR-018**: Browser and embedded macOS surfaces MUST use the same server-owned recovery semantics and user-facing reasons, and embedded email-link verify, resend, back, preview, confirm and cancel actions MUST stay on allowed `/desktop/...` routes.
- **FR-019**: Merge preview MUST state the survivor, preserved sign-in methods and data classes, separate workspace behavior, session/device revocation and blocker reasons using bounded metadata only.
- **FR-020**: Auth logs, audit and committed evidence MUST remain metadata-only and MUST NOT contain real email addresses, codes, tokens, account IDs or meeting content.
- **FR-021**: The hotfix MUST preserve existing successful Yandex ID and VK login behavior.

### Key Entities

- **Email Login Callback State**: Single-use, time-bounded state that binds an email-code flow to its original workspace, safe destination and completion status.
- **User Session**: Authenticated session created only after successful atomic completion.
- **Linked Sign-in Identity**: Verified email or OAuth identity attached to one canonical user.
- **Merge Intent**: Single-use preview/confirmation record created only when exactly one other account is eligible for explicit recovery.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All supported existing-user email-login scenarios finish with redirect and usable session, with zero HTTP 500 responses in the forced-RLS regression matrix.
- **SC-002**: Every injected failure point in callback completion leaves zero orphan sessions, zero partially consumed callback states and zero unintended identity or merge changes.
- **SC-003**: The 0/1/>1 other-candidate matrix produces respectively link, explicit preview and fail-closed ambiguity in 100% of regression cases.
- **SC-004**: A user on the ambiguous recovery screen can start a supported second-provider confirmation in one action on both web and embedded surfaces.
- **SC-005**: Existing Yandex ID and VK success-path regression checks remain green.
- **SC-006**: Focused auth/RLS tests, feature quickstart and repository fast validation complete successfully before PR.

## Assumptions

- Feature 157 remains the authority for the entity-by-entity merge policy; Feature 175 supersedes only its optional empty-account auto-confirm behavior so every cross-account operation receives explicit preview and confirmation.
- No schema migration or new dependency is expected unless root-cause analysis proves it unavoidable.
- Real production accounts are not merged, deleted or edited automatically by this implementation or its validation.
- Supported OAuth provider availability continues to come from the existing configuration and rendering contract.
- Production deployment is a separate release gate after code review and explicit approval.

## Out of Scope

- Automatic merge or manual repair of any real production account.
- New authentication providers, passwords or password-reset flow.
- Changes to the entity-by-entity merge policy defined by Feature 157.
- Weakening RLS, CSRF, OAuth state/nonce, rate limits or destination allowlists.
- Broad redesign of the login page outside the blocked recovery journey.
