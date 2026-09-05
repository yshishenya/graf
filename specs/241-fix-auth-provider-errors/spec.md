# Feature Specification: Непрерывность способов входа при ошибках

**Feature Branch**: `241-fix-auth-provider-errors`

**Created**: 2026-09-04

**Status**: Ready for planning

**Input**: User description: "После ввода тестового пользователя экран входа показывает ошибку, а включённые способы авторизации исчезают. Найти причину, исправить аналогичные проблемы во всём приложении, устранить связанный устаревший, нелогичный или неиспользуемый код и довести работу до PR."

## Clarifications

### Session 2026-09-04

- Q: Нужно ли сообщать, что email не связан с аккаунтом, если вход нельзя начать? → A: Нет. Сообщение должно быть правдивым, но нейтральным и не позволять проверять существование чужих аккаунтов.
- Q: Как трактовать дополнительную просьбу исправить legacy и нелогичные пути? → A: Проверить все соседние ветки ошибок login, sign-up и provider-start; менять только доказанно связанный дублирующий, недостижимый или сбрасывающий безопасное состояние код.
- Q: Что должно происходить, если политика провайдеров действительно недоступна? → A: Сохранять fail-closed поведение: не показывать непроверенные способы как активные и явно оставлять состояние недоступности.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Сохранить доступные способы входа после ошибки (Priority: P0)

Пользователь, который получил безопасную ошибку при входе или регистрации, продолжает видеть те же реально включённые способы входа, что были доступны до отправки формы, и может сразу выбрать один из них.

**Why this priority**: Исчезновение рабочих способов входа превращает восстановимую ошибку одного пути в тупик всего экрана авторизации.

**Independent Test**: Для каждого восстановимого ответа входа и регистрации открыть исходный экран с включёнными Яндекс ID и VK, вызвать ошибку и убедиться, что оба действия остаются видимыми, активными и ведут на тот же безопасный first-party путь.

**Acceptance Scenarios**:

1. **Given** в политике пространства включены Яндекс ID и VK, **When** вход по email не может начаться, **Then** экран показывает безопасное объяснение и сохраняет действия Яндекс ID, VK, Mail.ru и Одноклассники в том же порядке и с тем же назначением.
2. **Given** один из способов входа выключен политикой, **When** любой другой путь входа возвращает восстановимую ошибку, **Then** выключенный способ не появляется, а остальные включённые способы не исчезают.
3. **Given** пользователь находится во встроенном кабинете macOS, **When** вход завершается восстановимой ошибкой, **Then** доступные способы входа и допустимый встроенный адрес возврата сохраняются без перехода на внешний или неподдерживаемый путь.
4. **Given** политика способов входа сама недоступна, **When** сервер строит страницу ошибки, **Then** он показывает правдивое состояние недоступности и не изображает непроверенный способ как включённый.

---

### User Story 2 - Понять ошибку и продолжить без повторного ввода (Priority: P1)

Пользователь получает правдивое, не раскрывающее существование чужого аккаунта сообщение, видит ранее введённый им корректный адрес и может исправить его, выбрать другой способ входа либо перейти к регистрации.

**Why this priority**: Текущее сообщение утверждает, что код не отправлен, даже когда доставка не начиналась, а очищенное поле заставляет повторять ввод и затрудняет исправление опечатки.

**Independent Test**: Отправить корректно сформированный, но неподходящий для обычного входа адрес и ошибку доставки; в обоих случаях проверить сообщение, сохранённое значение поля, доступные альтернативы и отсутствие признаков, позволяющих определить наличие чужой учётной записи.

**Acceptance Scenarios**:

1. **Given** обычный вход не может безопасно выбрать единственный аккаунт, **When** пользователь отправляет корректный email, **Then** сообщение не утверждает, что письмо отправлялось, не подтверждает наличие или отсутствие аккаунта и предлагает проверить адрес, выбрать другой доступный способ или зарегистрироваться.
2. **Given** пользователь отправил корректный нормализованный email, **When** форма возвращается с восстановимой ошибкой, **Then** его собственный адрес остаётся в поле и экранируется как обычный текст.
3. **Given** введённый email синтаксически неверен, **When** форма отклоняет его, **Then** непроверенное значение не отражается как доверенное, а пользователь получает понятную просьбу исправить адрес.
4. **Given** почтовая доставка действительно недоступна после подготовки одноразового кода, **When** сервер откатывает попытку, **Then** сообщение отличает сбой доставки от невозможности начать вход и сохраняет другие работающие способы входа.

---

### User Story 3 - Устранить аналогичные разрывы и связанный устаревший код (Priority: P1)

Владелец продукта получает единое поведение всех серверных экранов входа и регистрации: восстановимые ошибки не сбрасывают уже известную безопасную конфигурацию, а подтверждённо недостижимые или дублирующие ветки в этом потоке удалены либо сведены к общему пути.

**Why this priority**: Точечное исправление одного сообщения оставит те же дефекты в соседних ветках ограничения частоты, доставки, регистрации и старта внешнего провайдера.

**Independent Test**: Выполнить статический аудит всех вызовов экранов входа/регистрации и автоматическую матрицу ошибок; доказать, что каждый пустой список способов входа обусловлен отсутствием проверяемого пространства или базы, а не локальным сбросом состояния.

**Acceptance Scenarios**:

1. **Given** приложение возвращает ошибки неверного email, ограничения частоты, отсутствующей входной identity, сбоя почтовой доставки, регистрации или старта провайдера, **When** пространство и политика доступны, **Then** экран использует один общий источник фактических способов входа.
2. **Given** путь не может загрузить базу или определить безопасное пространство, **When** строится ошибка, **Then** пустой список не заменяется выдуманными активными способами и причина остаётся видимой.
3. **Given** в связанном маршруте найден дублирующий, нелогичный или недостижимый код, **When** его удаление не меняет защищённый контракт, **Then** используется существующий общий помощник или минимальная общая ветка с проверкой против повторного появления дефекта.
4. **Given** код относится к несвязанной части приложения или его устаревание нельзя доказать, **When** проводится аудит, **Then** он не изменяется в этой фиче и фиксируется только как возможная отдельная работа.

### Edge Cases

- Пространство входа не настроено, база авторизации недоступна либо политика провайдеров не читается.
- Приглашение истекло, не соответствует адресу или больше не существует.
- Ограничение частоты срабатывает до чтения пользователя либо провайдера.
- Яндекс ID включён, VK выключен; оба выключены; оба включены.
- Запрошен будущий, неизвестный или отключённый провайдер.
- Пользователь пришёл из браузера либо из разрешённого `/desktop/...` маршрута.
- Корректный email содержит регистр или пробелы и нормализуется перед безопасным повторным показом.
- Введённое значение содержит HTML; шаблон обязан вывести его как текст, а не разметку.
- Повторный запрос после ошибки не создаёт дополнительный код, callback-state, сессию или audit-событие успешного входа.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every recoverable login or registration error MUST retain the currently configured and enabled supported provider actions when the workspace, database and provider policy remain available.
- **FR-002**: Error responses MUST apply the same provider policy filtering and ordering as the initial login or registration page; disabled providers MUST remain hidden and unverified providers MUST NOT become active.
- **FR-003**: Browser and embedded macOS auth surfaces MUST share the same error-state provider semantics and preserve only allowlisted first-party return destinations.
- **FR-004**: When the workspace, auth database or provider policy cannot be safely resolved, the response MUST fail closed, explain the unavailable state, and MUST NOT claim an unverified provider is usable.
- **FR-005**: The email-start unavailable message MUST describe failure to begin authentication without claiming that delivery was attempted and without revealing whether an arbitrary email belongs to an account.
- **FR-006**: A syntactically valid normalized email submitted by the current user SHOULD remain in the returned login or registration field after a recoverable error; invalid or unnormalized input MUST NOT be reflected as trusted markup.
- **FR-007**: A real delivery failure MUST remain distinguishable from pre-delivery rejection and MUST preserve all other currently usable sign-in actions.
- **FR-008**: The feature MUST NOT automatically create, select, link or merge an account during ordinary login and MUST preserve existing ambiguity, callback, CSRF, nonce, rate-limit, verified-email, RLS and session protections.
- **FR-009**: The implementation MUST audit every call site that renders login or registration error state and eliminate state-resetting empty-provider arguments wherever a verified provider snapshot can be loaded.
- **FR-010**: Confirmed duplicate, illogical or unreachable code in the scoped auth error-rendering path MUST be removed or consolidated into an existing shared path without adding a new dependency or parallel provider registry.
- **FR-011**: Empty provider state MUST remain explicit only for cases where no safe workspace/database/policy context exists or for a recovery mode that intentionally exposes no available provider.
- **FR-012**: Error rendering MUST preserve the submitted safe next path, invitation classification, browser/embedded presentation, status code, retry headers and product-analytics placement already required by the originating route.
- **FR-013**: Regression coverage MUST exercise login, registration and provider-start error classes with enabled, partially disabled and unavailable provider policies, including the exact failure class shown in the user report.
- **FR-014**: Logs, audit, tests, screenshots, specs and evidence MUST NOT contain real email addresses, codes, tokens, private account identifiers or meeting content.
- **FR-015**: The change MUST add no schema migration, new authentication provider, external dependency or production configuration flag unless root-cause evidence proves it unavoidable and the plan is re-reviewed.
- **FR-016**: Existing accessibility semantics MUST remain intact: errors remain announced as alerts, active methods remain keyboard-operable links, unavailable methods remain non-interactive with `aria-disabled`, and every email input retains its visible label and editable state.

### Key Entities

- **Auth provider snapshot**: The current workspace-scoped set of supported provider policies, including enabled state and display identity, used consistently by initial and error pages.
- **Auth error presentation**: A server-rendered login or registration response containing a safe reason, preserved first-party continuation, available provider actions and, where allowed, the current user's normalized submitted email.
- **Email authentication attempt**: A pre-authentication request that may be rejected before delivery, fail during delivery or proceed to a single-use code without changing account-linking rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of covered login, registration and provider-start recoverable error scenarios with two enabled providers, both enabled provider actions remain visible and actionable after the error.
- **SC-002**: In 100% of covered partially disabled policy scenarios, no disabled provider appears and every remaining enabled provider keeps the same destination as on the initial page.
- **SC-003**: The user-reported unknown-or-unselectable email scenario shows a truthful non-enumerating message, retains safe alternatives and does not create an email code or session.
- **SC-004**: All syntactically valid test emails used in the error matrix remain editable in the returned form; all HTML-like input is escaped and never executes or changes document structure.
- **SC-005**: A repository-wide scoped audit leaves zero error-rendering call sites that pass an empty provider list while a safe provider snapshot is available.
- **SC-006**: Existing successful email, Yandex ID, VK, Mail.ru, Odnoklassniki, invitation and ambiguous-account recovery tests continue to pass with no weakened security assertion.
- **SC-007**: Focused auth tests, feature quickstart, repository fast validation and PR exact-SHA checks pass before the PR is declared ready.

## Assumptions

- The screenshot corresponds to the existing `email_start_unavailable` response: the server could not safely select a unique active email identity before attempting delivery.
- Яндекс ID and VK availability remains owned by the existing workspace policy and provider registry; this feature changes presentation continuity, not provider enablement.
- Mail.ru and Одноклассники remain approved VK ID authorization hints, while T-Банк ID, Sber ID, Госуслуги and Alfa ID remain non-active planned entries.
- The current server-rendered browser and embedded macOS WebView surfaces are both in scope; native capture controls and unrelated cabinet pages are not.
- Production data inspection, deployment, account mutation and real email delivery are separate release/operations actions and are not required to prepare the PR.

## Out of Scope

- Creating or auto-linking an account from an unknown email during ordinary login.
- Enabling new providers, SSO, passwords or password reset.
- Changing account merge policy, invitation ownership or provider credentials.
- Reading or mutating a real production user's account to make the test pass.
- Broad cleanup outside the login, registration and provider-start rendering paths.
- Production deployment, release publication or live email sending.
