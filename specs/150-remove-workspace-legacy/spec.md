# Feature Specification: Remove Workspace Legacy

**Feature Branch**: `codex/150-remove-workspace-legacy`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "До запуска удалить из кода поддержку legacy bootstrap/workspace-сценариев; не сохранять совместимость с ошибочно созданными пользовательскими пространствами."

## Clarifications

### Session 2026-08-15

- Q: Нужно ли сохранять legacy-совместимость для существующих пользователей? → A: Нет; продукт ещё не запущен, production-пользователей и пользовательских данных нет.
- Q: Что считать корректным состоянием нового личного аккаунта? → A: Ровно одно видимое личное пространство, которым пользователь владеет.
- Q: Может ли технический bootstrap-контекст оставаться пользовательским пространством? → A: Нет; технический auth-контекст не получает пользовательских membership, данных, выбора или биллинга.
- Q: Как появляется командное пространство? → A: Только после явного приглашения или другого отдельно утверждённого корпоративного enrollment-flow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Один понятный личный контекст (Priority: P1)

Как новый пользователь GRAF, я хочу после регистрации сразу попасть в одно личное пространство, чтобы не выбирать между непонятными дубликатами и не сомневаться, где будут храниться мои встречи и оплата.

**Why this priority**: Два пространства у пользователя без команды создают риск записи или оплаты не в тот tenant и разрушают доверие ещё до первой встречи.

**Independent Test**: Новый аккаунт проходит регистрацию и повторный вход; в обоих случаях список доступных пространств содержит ровно одно личное пространство с ролью владельца, а встречи и биллинг относятся к нему.

**Acceptance Scenarios**:

1. **Given** новый подтверждённый аккаунт, **When** регистрация завершается, **Then** пользователь получает ровно одно активное личное пространство и является его владельцем.
2. **Given** пользователь повторяет callback, вход или подтверждение после сетевого сбоя, **When** сессия создаётся повторно, **Then** второе личное или техническое пространство не появляется.
3. **Given** пользователь открывает настройки пространства или биллинг, **When** интерфейс показывает текущий контекст, **Then** он использует понятное имя личного пространства и не показывает внутренние идентификаторы или английское `Personal`.

---

### User Story 2 - Команда только после явного присоединения (Priority: P1)

Как пользователь без команды, я хочу не видеть и не получать командное пространство автоматически, чтобы система не приписывала мне несуществующую организацию.

**Why this priority**: Неявное membership меняет границы доступа, владельца биллинга и место хранения встреч без осознанного действия пользователя.

**Independent Test**: У аккаунта без принятого приглашения доступно только личное пространство; после принятия валидного приглашения появляется отдельное рабочее пространство с реальным именем и ролью.

**Acceptance Scenarios**:

1. **Given** у пользователя нет принятого корпоративного приглашения, **When** он входит в GRAF, **Then** никакое рабочее пространство не создаётся и не отображается автоматически.
2. **Given** у пользователя есть pending invitation, **When** он только входит или регистрируется, **Then** membership не возникает до явного принятия.
3. **Given** пользователь явно принял валидное приглашение, **When** он открывает переключатель пространств, **Then** он видит личное и настоящее рабочее пространство, каждое с корректной ролью.

---

### User Story 3 - Clean cut до запуска (Priority: P2)

Как владелец продукта, я хочу удалить неиспользуемые legacy-ветки до запуска, чтобы новая модель аккаунта была единственной поддерживаемой моделью и не требовала постоянных fallback, отчётов и специальных тестов.

**Why this priority**: До появления реальных данных удаление совместимости дешевле и безопаснее, чем поддержка двух моделей tenancy после запуска.

**Independent Test**: Проверка исходного кода, служебных команд и тестов не находит активных путей, которые классифицируют, показывают, активируют или мигрируют legacy bootstrap memberships.

**Acceptance Scenarios**:

1. **Given** чистая pre-launch база, **When** применяется актуальная схема и создаётся тестовый аккаунт, **Then** legacy migration/report step не требуется.
2. **Given** технический auth bootstrap существует как внутренний policy anchor, **When** выполняются регистрация, вход, приглашение или восстановление сессии, **Then** он не становится пользовательским workspace и не получает customer membership.
3. **Given** код развёртывается до публичного запуска, **When** выполняется metadata-only inventory, **Then** любые ошибочные bootstrap memberships можно удалить как тестовый residue без переноса встреч, платежей или пользовательских данных.

### Edge Cases

- Повторный signup/callback приходит конкурентно в двух запросах.
- Сессия ссылается на несуществующее, отозванное или внутреннее bootstrap-пространство.
- Pending corporate invitation существует до первой регистрации.
- У пользователя есть валидное корпоративное membership, но нет активного personal membership из-за повреждённого тестового состояния.
- Технический bootstrap anchor временно недоступен или ошибочно попал в выборку доступных пространств.
- Биллинг открывается сразу после первой регистрации до повторного запроса контекста.
- Pre-launch cleanup обнаруживает встречи, платежи, uploads или иные customer-owned rows в удаляемом пространстве: удаление должно остановиться, а не продолжиться автоматически.
- Старый тестовый клиент присылает workspace identifier, который больше не является доступным membership пользователя.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Новый подтверждённый аккаунт MUST получать ровно одно personal workspace и owner membership в нём.
- **FR-002**: Повторные signup, callback, login и session-recovery MUST переиспользовать personal workspace аккаунта и MUST NOT создавать дубликаты.
- **FR-003**: Внутренний auth bootstrap context MUST NOT иметь customer memberships, становиться active workspace пользователя или попадать в список доступных пространств.
- **FR-004**: Внутренний auth bootstrap context MUST NOT быть субъектом встреч, uploads, devices, invitations, usage или billing.
- **FR-005**: Corporate workspace membership MUST возникать только после явного, identity-verified enrollment, принятого пользователем; первичный owner может быть создан только отдельным operator provisioning flow, а не публичным signup/login.
- **FR-006**: Система MUST reject activation и session continuation для workspace, к которому у пользователя нет действующего membership, без fallback на bootstrap workspace.
- **FR-007**: При недоступном ранее активном corporate workspace система MUST возвращать пользователя в personal workspace; если personal workspace отсутствует, система MUST атомарно создать или восстановить его и MUST fail closed, если однозначное восстановление не удалось.
- **FR-008**: Переключатель пространств MUST показывать только действующие customer workspaces и MUST использовать названия `Моё пространство` для личного контекста и реальное имя для рабочего пространства.
- **FR-009**: Подпись личного пространства MUST быть `Личное · Владелец`; подпись рабочего пространства MUST отражать тип `Рабочее пространство` и фактическую роль пользователя.
- **FR-010**: Self-serve billing MUST быть доступен только owner активного personal workspace; internal bootstrap и corporate workspace MUST быть отклонены для каталога, checkout, trial, referral, payment method и entitlement mutations.
- **FR-011**: Runtime MUST NOT содержать классификацию, report-only migration или fallback, предназначенные только для поддержки legacy bootstrap memberships.
- **FR-012**: Pre-launch cleanup MUST сначала доказать отсутствие customer-owned meetings, uploads, recordings, payment operations и subscriptions в удаляемых test memberships/workspaces и MUST остановиться при ненулевом результате.
- **FR-013**: Auth, tenant and billing audit/log output MUST оставаться metadata-only и MUST NOT содержать email, токены, cookies, коды входа или содержимое встреч.
- **FR-014**: Удаление workspace legacy MUST NOT удалять и не ослаблять отдельные действующие compatibility boundaries за пределами auth/workspace onboarding.
- **FR-015**: Invitation, join offer и public auth response MUST NOT принимать internal bootstrap как customer target или раскрывать его identifier/name пользователю.

### Key Entities

- **Canonical user**: подтверждённая учётная запись, которой принадлежит один personal workspace.
- **Personal workspace**: пользовательский tenant для личных встреч, использования и биллинга; уникален для canonical user и имеет owner membership.
- **Corporate workspace**: отдельный customer tenant с реальным названием и membership, полученным через явный enrollment.
- **Internal auth bootstrap context**: технический policy/organization anchor, не являющийся customer workspace и не доступный пользователю.
- **Workspace membership**: явная связь пользователя с customer workspace, ролью и состоянием доступа.
- **Active workspace session context**: server-verified current customer workspace, используемый для авторизации операций.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: В 100% регистраций и повторных входов чистого аккаунта доступно ровно одно personal workspace с owner role.
- **SC-002**: В 100% списков и переключателей bootstrap context отсутствует, включая signup, login, revoked-session recovery и billing entry.
- **SC-003**: Ни один auth/workspace runtime path, CLI или scheduled job не классифицирует и не мигрирует legacy bootstrap memberships после изменения.
- **SC-004**: Все негативные сценарии activation/session/billing для bootstrap или чужого workspace завершаются отказом без выдачи tenant data.
- **SC-005**: Focused auth/workspace/billing matrix и canonical fast repository gate проходят без legacy fixtures для bootstrap memberships.
- **SC-006**: Pre-launch cleanup dry-run сообщает точные metadata-only counts и выполняет destructive cleanup только при нулевом customer-data inventory.

## Assumptions

- Публичного запуска ещё не было; реальных production-пользователей, встреч и платежных данных нет.
- Существующие ошибочные пространства и memberships относятся только к внутреннему тестированию и могут быть удалены после backup и zero-data inventory.
- Внутренний auth bootstrap anchor может остаться как техническая деталь, только если текущая auth policy/RLS действительно требует его; это не считается legacy-поддержкой, пока он не видим и не связан с customer data.
- Удаление `legacy_header_auth_enabled`, historical meeting/media compatibility и macOS release migration не входит в этот feature: они не являются причиной второго workspace и требуют отдельных решений.
- Provisioning первого owner нового corporate workspace остаётся отдельной operator/admin операцией и не выполняется self-serve signup.
- Read-only cleanup inventory является одноразовым release evidence и не остаётся постоянным runtime/CLI compatibility layer.
- Коммит, merge и production cleanup/deploy выполняются только после проверок и отдельного подтверждения пользователя.
