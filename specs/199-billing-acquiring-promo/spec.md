# Feature Specification: Доразвитие биллинга, эквайринга и промокодов

**Feature Branch**: `codex/199-billing-acquiring-promo`

**Created**: 2026-08-23

**Status**: Implementation in progress; production checkout remains controlled by explicit billing settings and provider safety checks.

**Input**: Пользователь просит повторно проверить реализованный Feature 140, довести денежный контур до запуска эквайринга и завершить поддержку промокодов.

## Context and Scope

Feature 140 уже содержит server-owned каталог, hosted YooKassa checkout,
идемпотентный invoice/operation ledger, provider reconciliation и безопасную
модель `PromotionCampaign`/`PromotionRedemption`. Этот срез закрывает только
расхождения, мешающие пользователю понять сумму до оплаты и оператору безопасно
создать кампанию. Реальный provider canary, merchant/legal/finance/security/QA
review и production enablement остаются внешними операционными решениями Feature
140; они больше не хранятся в обязательном runtime-реестре.

## Clarifications

### Session 2026-08-25

- Удаляем `billing_launch_gates` из active runtime path, ORM и схемы следующей
  миграцией. Историческая миграция `0072` остаётся в цепочке Alembic.
- Checkout и renewal сохраняют server-owned catalog validation, explicit
  YooKassa environment/shop, checkout flag, emergency stop, owner/CSRF/consent,
  idempotency, invoice/operation ledger, receipt, webhook and reconciliation
  checks.
- Provider canary and independent review remain operational evidence, but
  отсутствие записи в бывшем internal registry больше не блокирует оплату.
- Если YooKassa отклоняет или обрывает первый create до сохранения `provider_id`,
  GRAF сохраняет только безопасный класс ошибки и продолжает ту же immutable
  операцию с тем же provider idempotency key. Новая invoice/operation не создаётся.
- Продолжение доступно только до `provider_key_expires_at`; после истечения окна
  операция остаётся заблокированной для ручной сверки. Production-магазин не
  включается: canary выполняется production-приложением только в test shop.

## User Scenarios & Testing

### User Story 1 - Увидеть честную сумму с промокодом (Priority: P1)

Owner вводит код на странице checkout, выбирает месяц или год и получает
server-side рассчитанные список, скидку и сумму к оплате. Проверка не создаёт
invoice, не резервирует код и не вызывает YooKassa; финальный POST повторно
проверяет все условия перед денежной мутацией.

**Why this priority**: Без итоговой суммы до оплаты checkout непрозрачен, даже
если backend уже умеет безопасно применить скидку.

**Independent Test**: Рендер checkout с действующим, просроченным, исчерпанным,
неподходящим и ниже-floor кодом; убедиться, что видимые суммы и ошибки безопасны,
а БД и provider не меняются до submit.

**Acceptance Scenarios**:

1. **Given** утверждённый month/year catalog и действующий код, **When** Owner
   запрашивает preview, **Then** показываются цена списка, размер скидки,
   итог сегодня и полная сумма следующего периода.
2. **Given** код неизвестен, истёк, уже использован, не подходит по cycle или
   опускает сумму ниже provider floor, **When** Owner проверяет его, **Then**
   показывается recoverable безопасная ошибка без raw provider/campaign details.
3. **Given** preview устарел или после него изменился catalog/campaign, **When**
   Owner отправляет checkout, **Then** POST revalidates and either uses a fresh
   immutable snapshot or fails closed without a second charge.

### User Story 2 - Оператор может выпустить кампанию без утечки кода (Priority: P1)

Уполномоченный оператор создаёт или отключает кампанию через существующий
maintenance boundary. Raw code принимается только интерактивно/stdin, в БД
сохраняется только hash, а dry-run и execute выводят только metadata-safe
результат. Публичного admin UI и общего API для выпуска кодов нет.

**Why this priority**: Без controlled provisioning нельзя реально запустить ни
один промокод, а public admin endpoint расширил бы денежную trust boundary.

**Independent Test**: Прогнать CLI в dry-run и unit-test его validation/output;
проверить, что raw code отсутствует в JSON/output и campaign создаётся только
с явным `--execute` в maintenance context.

**Acceptance Scenarios**:

1. **Given** валидные даты, cycle, discount и cap, **When** оператор запускает
   dry-run, **Then** команда показывает hash и будущие параметры без записи.
2. **Given** duplicate code hash или invalid floor-unaware campaign parameters,
   **When** оператор запускает create, **Then** операция fail-closed и не
   изменяет существующую кампанию.
3. **Given** действующая кампания, **When** оператор отключает её, **Then** новые
   preview/checkout не принимают код, а уже созданные immutable invoices не
   пересчитываются.

### User Story 3 - Подготовить controlled acquiring launch (Priority: P1)

Оператор видит в quickstart и runbook один последовательный путь: test-shop
canary, receipt/VAT mapping, webhook delivery, renewal/unknown/refund
observation, затем отдельное production decision. До этого checkout остаётся
default-off.

**Why this priority**: Provider mutation без evidence создаёт риск двойного
списания, неверного чека и невозможного rollback.

**Independent Test**: Прочитать quickstart/runbook и проверить, что каждый
provider capability имеет owner, evidence reference, stop condition и explicit
no-go state.

**Acceptance Scenarios**:

1. **Given** checkout disabled, emergency stop или невалидны catalog/shop/
   provider settings, **When** оператор пытается открыть checkout, **Then**
   billing safety checks block it.
2. **Given** test canary passed and operational review is recorded, **When**
   release owner proceeds, **Then** production enablement remains a separate
   explicit approval and dry-run precedes execute.

### User Story 4 - Продолжить незавершённую оплату без двойного списания (Priority: P1)

Если первый запрос к YooKassa завершился до получения `provider_id`, Owner сразу
видит фактическое локальное состояние операции. Пока исходный idempotency key
действует, Owner может явно продолжить эту же операцию; GRAF повторяет тот же
immutable checkout request с тем же ключом и не создаёт вторую invoice.

**Independent Test**: Смоделировать provider reject/timeout до `provider_id`,
повтор с тем же ключом, истёкший ключ и status refresh с `processed=0`.

**Acceptance Scenarios**:

1. **Given** create payment завершился без `provider_id`, **When** Owner открывает
   статус, **Then** он видит локальный failure state и действие «Продолжить
   оплату», а не ложное сообщение об обычном provider pending.
2. **Given** исходный provider key ещё действует, **When** Owner продолжает
   оплату, **Then** GRAF использует те же operation, invoice, amount, receipt
   snapshot и idempotency key и сохраняет единственный provider id.
3. **Given** provider key истёк, **When** Owner пытается продолжить, **Then**
   provider mutation не выполняется и операция остаётся manual-resolution.
4. **Given** операция не подходит для provider polling, **When** Owner запрашивает
   refresh, **Then** UI не утверждает, что проверка обновила состояние.

## Edge Cases

- Unicode confusable, whitespace and unsupported characters never become a
  different accepted code.
- Preview never reserves a campaign slot; reservation is created only with the
  invoice and is released only after authoritative cancellation/expiry.
- Referral and entered promo never stack; the lower payable amount wins and the
  final invoice snapshot is authoritative.
- A malformed or expired short-lived browser cookie is ignored without exposing
  its contents in URL, analytics or logs.
- A missing catalog, disabled billing flag, emergency stop or invalid provider
  environment/shop keeps amounts/provider actions unavailable rather than
  inventing a price.
- Provider/configuration/transport failure metadata contains only a bounded
  class, optional HTTP status and timestamp; exception text and provider payload
  are not persisted or rendered.

## Requirements

### Functional Requirements

- **FR-001**: Checkout preview MUST calculate prices only from the effective
  approved database catalog and the existing promotion eligibility policy.
- **FR-002**: Preview MUST expose list amount, discount amount/percent, payable
  amount and next-period amount without creating an invoice, reservation or
  provider request.
- **FR-003**: Checkout POST MUST remain the only path that creates a money
  operation and MUST revalidate promo, catalog, consent, floor and provider
  environment/shop settings.
- **FR-004**: Campaign provisioning MUST accept raw code only through stdin or an
  interactive hidden prompt, persist only its normalized SHA-256 hash, and never
  print the raw value.
- **FR-005**: Campaign create/disable MUST run through the existing trusted
  maintenance/RLS boundary, default to dry-run, and require explicit execute.
- **FR-006**: Duplicate campaign hashes, invalid dates, invalid caps and invalid
  discounts MUST fail closed without changing existing rows.
- **FR-007**: No public admin UI, refund workflow, stacking rule or zero-total
  checkout may be introduced by this feature.
- **FR-008**: Launch documentation MUST preserve test/prod separation, provider
  observation, operational review, emergency stop and exact-SHA evidence.
- **FR-009**: A checkout failure before `provider_id` MUST preserve the existing
  operation/invoice and MUST NOT authorize a second checkout operation.
- **FR-010**: Explicit continuation MUST reuse the immutable checkout snapshot
  and original provider idempotency key, and MUST fail closed after
  `provider_key_expires_at`.
- **FR-011**: Checkout/status UI MUST render the current local state immediately;
  a reconciliation no-op MUST NOT be reported as a successful refresh.
- **FR-012**: Persisted checkout failure diagnostics MUST be metadata-safe and
  MUST NOT include provider payload, exception text, credentials or receipt
  contact.

### Key Entities

- **PromotionCampaign**: Global versioned campaign with hashed code, scope,
  percentage, dates, cap and enabled state.
- **PromotionRedemption**: Workspace/invoice-bound reservation or redemption;
  stores only code hash and immutable price snapshot.
- **CheckoutPreview**: Ephemeral server-calculated view of one catalog cycle;
  it has no persistence or provider side effect.

## Success Criteria

- **SC-001**: Every enabled catalog cycle renders a truthful promo preview and
  the focused preview/promo suite passes with no provider call.
- **SC-002**: 100% of provisioning command outputs and persisted campaign rows
  contain no raw promo code.
- **SC-003**: Duplicate, expired, ineligible, exhausted, confusable and
  below-floor cases fail closed in automated tests.
- **SC-004**: Checkout remains controlled by explicit settings, provider/shop
  separation and emergency stop; no code change silently enables production
  money mutations.
- **SC-005**: Focused tests prove that reject/timeout recovery makes at most one
  logical provider request identity and that expired keys perform zero provider
  mutations.

## Assumptions

- Feature 140's existing YooKassa client, catalog, RLS, CSRF, rate limits and
  promotion tables are reused; the obsolete launch-gate registry is removed by
  a cleanup migration.
- Campaign creation is an operations action, not an end-user or workspace-admin
  action.
- Production provider credentials and merchant decisions are supplied outside
  Git and are not written to evidence.
