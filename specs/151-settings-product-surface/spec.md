# Feature Specification: Продуктовый раздел настроек

**Feature Branch**: `151-settings-product-surface`

**Created**: 2026-08-16

**Status**: Implemented locally; PR and production rollout pending

**Input**: User description: «Перенести спроектированный в Open Design раздел настроек в настоящий продукт GRAF».

## User Scenarios & Testing

### User Story 1 - Открыть обзор настроек (Priority: P1)

Пользователь открывает «Настройки» в GRAF и видит единый обзор разделов с понятной областью действия каждого: этот Mac, текущее пространство или личная настройка.

**Why this priority**: Без общего обзора пользователь не понимает, где меняется запись, где — аккаунт, а где — выбранное пространство.

**Independent Test**: Авторизованный пользователь открывает `/settings` и получает обзор из семи карточек, каждая ведёт на существующий серверный раздел.

**Acceptance Scenarios**:

1. **Given** авторизованный пользователь в кабинете, **When** он открывает «Настройки», **Then** видит заголовок, описание, группированную навигацию и карточки «Запись», «Итоги», «Календари», «Пространства», «Аккаунт и безопасность», «Уведомления», «Тариф и оплата».
2. **Given** карточка раздела отображается, **When** пользователь читает её, **Then** область действия и назначение раздела видны до перехода.
3. **Given** пользователь находится в подразделе, **When** он смотрит навигацию, **Then** текущий пункт обозначен семантически и визуально.

### User Story 2 - Изменить существующую настройку в правильной области (Priority: P1)

Пользователь переходит из обзора в нужный раздел и меняет уже поддерживаемую настройку через существующую серверную форму.

**Why this priority**: Визуальный слой не должен превращать реальные account, workspace, calendar, notification и billing операции в демо-состояния.

**Independent Test**: По одному разу открыть каждый раздел и подтвердить, что его форма, результат, CSRF и текущая область действия сохраняются.

**Acceptance Scenarios**:

1. **Given** пользователь открывает «Запись», **When** он читает страницу, **Then** видит, что запись и разрешения управляются приложением GRAF на этом Mac, а веб-кабинет не обещает невозможное.
2. **Given** пользователь открывает «Аккаунт и безопасность» или «Уведомления», **When** он сохраняет изменение, **Then** результат отображается в кабинете и не требует клиентского фальшивого состояния.
3. **Given** пользователь открывает «Тариф и оплата», **When** актуальные финансовые данные недоступны или checkout закрыт gate-ами, **Then** продукт показывает truthful unavailable/gated state без демо-цифр.

### User Story 3 - Использовать настройки на малом экране и с клавиатурой (Priority: P2)

Пользователь может прочитать навигацию и выполнить основные действия на узком окне без горизонтального overflow и с видимым focus state.

**Why this priority**: Кабинет открыт внутри desktop web view и браузера с разными размерами, а настройки затрагивают доступ и безопасность.

**Independent Test**: Проверить `/settings` и все новые/изменённые интерактивные элементы на `390×844`, клавиатурой и в forced-colors mode.

**Acceptance Scenarios**:

1. **Given** ширина viewport 390px, **When** пользователь открывает обзор и подразделы, **Then** контент не выходит за пределы viewport, а навигация остаётся достижимой.
2. **Given** пользователь перемещается Tab, **When** фокус достигает ссылки, формы или destructive action, **Then** focus ring виден и порядок соответствует визуальной иерархии.
3. **Given** пользователь отключил motion, **When** открывает настройки, **Then** переходы не мешают чтению и действию.

### Edge Cases

- Сессия истекла до перехода: существующий login/re-auth flow остаётся источником истины.
- Workspace недоступен или приглашение устарело: показывается существующее безопасное empty/unavailable состояние.
- Финансовое состояние не подтверждено: не показывать придуманные тариф, лимиты, storage или payment status.
- В браузере отключён JavaScript: серверные формы настроек продолжают работать обычной отправкой.
- Роль пользователя не позволяет выполнить действие: существующие owner/CSRF/reauth ограничения сохраняются.

## Requirements

### Functional Requirements

- **FR-001**: Product MUST expose one settings overview using the existing settings category source, with exactly the supported seven categories and their existing server routes.
- **FR-002**: Each overview category MUST show a truthful scope label and a concise description before navigation.
- **FR-003**: Product MUST preserve existing server-backed forms, CSRF tokens, tenant scope, owner checks, re-auth checks, result notices, and no-JavaScript fallbacks.
- **FR-004**: Recording settings MUST state that microphone/system-audio capture and local automatic-recording controls belong to the macOS app, without adding web controls that can hide or stop active capture.
- **FR-005**: Account, notification, workspace, calendar and billing pages MUST continue to use their current persisted data and actions; this feature MUST NOT add a parallel browser-local settings store.
- **FR-006**: Active settings navigation MUST be exposed with `aria-current="page"` and retain a visible selected state.
- **FR-007**: The settings surface MUST remain usable at 390px wide, with no document-level horizontal overflow and with keyboard-visible focus states.
- **FR-008**: All unavailable, gated, empty, destructive and failure states MUST use truthful existing copy and MUST NOT introduce demo values or promises outside GRAF control.
- **FR-009**: Product MUST not add a schema migration, new external dependency, new provider, new billing activation, or change to capture policy as part of this feature.

### Key Entities

- **Settings category**: Existing navigation definition containing id, label, scope, description, group, icon and server route.
- **Account settings surface**: Existing server projection for profile, providers, devices, sessions and account closure state.
- **Workspace settings surface**: Existing server projection for active workspace and join offers.
- **Billing state**: Existing gated server-owned projection; not replaced by fixture data.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The settings overview renders all seven supported categories and every card resolves to an existing product route.
- **SC-002**: Focused route/template checks cover overview, recording, summaries, calendar, workspace, account, notifications and billing navigation without introducing a second settings source.
- **SC-003**: Browser checks at 1280×720 and 390×844 observe zero document-level horizontal overflow on the settings overview and at least one form-backed subsection.
- **SC-004**: Accessibility checks find one and only one active settings navigation item with `aria-current="page"` on every settings page.
- **SC-005**: Existing account/notification/workspace/calendar/billing focused tests remain green, and no capture, auth, CSRF or payment boundary test regresses.

## Assumptions

- The current server-rendered Jinja/HTMX cabinet remains the implementation surface.
- Existing settings routes and server projections are the source of truth; the Open Design HTML is a visual/IA reference only.
- Billing checkout and production payment activation remain controlled by existing launch gates.
- This feature may refine settings-only CSS and templates but does not change the product shell outside settings.

## Out of Scope

- New account providers, calendar providers, billing providers or payment activation.
- New capture behavior, target registry semantics, automatic-recording policy or macOS permission flow.
- Replacing server forms with a SPA or localStorage-backed settings implementation.
- Changing deletion, retention, observability or auth/session contracts.
