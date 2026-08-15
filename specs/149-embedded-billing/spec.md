# Feature Specification: Встроенные тарифы и оплата

**Feature Branch**: `codex/149-settings-auth-handoff`

**Created**: 2026-08-15

**Status**: Ready for implementation

**Input**: Пользователь должен открывать раздел «Тарифы и оплата» внутри приложения GRAF, а не в системном браузере.

## User Scenarios & Testing

### User Story 1 - Открыть тарифы внутри приложения (Priority: P1)

Пользователь нажимает «Тарифы и оплата» в настройках GRAF и видит страницу тарифов в том же окне приложения.

**Why this priority**: Браузерный переход ломает контекст приложения и сейчас приводит к странице legacy auth с сырым JSON/401.

**Independent Test**: В установленном приложении открыть раздел настроек, нажать «Тарифы и оплата» и убедиться, что системный браузер не запускается, а URL остаётся в embedded web view.

**Acceptance Scenarios**:

1. **Given** активная desktop-сессия, **When** пользователь открывает `/billing`, **Then** маршрут разрешается embedded web view и получает desktop session headers.
2. **Given** пользователь переходит между `/billing`, `/billing/plans`, `/billing/usage`, `/billing/history` и `/billing/checkout/status/...`, **Then** все страницы остаются внутри приложения и не теряют auth context.
3. **Given** сессия истекла, **When** billing-маршрут возвращает login, **Then** login отображается внутри приложения, без открытия системного браузера и без сырого JSON.

### User Story 2 - Безопасно пройти оплату (Priority: P2)

Пользователь может перейти к разрешённой странице YooKassa из embedded billing checkout и вернуться на статус платежа внутри GRAF.

**Why this priority**: Внешний платёжный provider является частью оплаты, но не должен превращать весь billing flow в неконтролируемый внешний переход.

**Independent Test**: На test-shop checkout открыть разрешённый YooKassa URL, проверить возврат на `/billing/checkout/return` и отсутствие передачи секретов или финансовых параметров в URL приложения.

**Acceptance Scenarios**:

1. **Given** сервер вернул HTTPS confirmation URL разрешённого YooKassa host, **When** WebKit переходит по нему, **Then** переход разрешён только для payment flow.
2. **Given** внешний URL не входит в allowlist YooKassa, **When** он запрошен из billing, **Then** переход блокируется.
3. **Given** платёж вернулся в GRAF, **Then** отображается локальный статус операции, а повторная проверка использует существующий CSRF и session contract.

### Edge Cases

- Истёкшая или отсутствующая desktop-сессия показывает встроенный login/re-auth state.
- Query и fragment с amount, provider id, token или promo code не используются для внешнего handoff.
- Недоступный или неразрешённый payment provider оставляет пользователя на локальном billing error state.
- Admin, account и referral маршруты сохраняют существующие browser-owned решения.

## Requirements

### Functional Requirements

- **FR-001**: Desktop route policy MUST classify all supported `/billing` document routes as embedded and allowed.
- **FR-002**: Embedded billing GET navigation MUST preserve the validated desktop session header contract.
- **FR-003**: Billing navigation MUST NOT call the system browser opener or the desktop browser handoff endpoint.
- **FR-004**: Only HTTPS YooKassa confirmation hosts already approved by the server contract MAY load as external payment-provider pages during checkout.
- **FR-005**: Auth, tenant scope, CSRF, owner-only billing checks, and no-secret URL boundaries MUST remain unchanged.
- **FR-006**: Existing admin, account, referral, help, and unknown external route policies MUST remain unchanged.

### Key Entities

- **Billing document route**: A same-origin billing path and its safe route kind.
- **Payment-provider navigation**: A short-lived external HTTPS checkout page allowlisted by the existing YooKassa contract.
- **Desktop session**: The validated session header/cookie context used by the embedded cabinet.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of supported billing document routes remain in the app web view during navigation tests.
- **SC-002**: Billing navigation tests observe zero system-browser open calls.
- **SC-003**: Authenticated billing GET requests retain the desktop session context and render HTML, not legacy-header JSON 401 responses.
- **SC-004**: Unallowlisted external hosts remain blocked, while approved YooKassa test URLs complete the checkout-return flow.

## Assumptions

- Existing billing HTML, session, CSRF, YooKassa allowlist, and production launch gates are reused.
- Checkout remains disabled in production until its existing finance/legal/security gates are approved.
- Account/admin/referral ownership is intentionally unchanged in this slice.
