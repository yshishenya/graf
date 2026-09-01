# Implementation Plan: KRISP-паритет страницы биллинга

**Branch**: `210-krisp-billing-page` | **Date**: 2026-08-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/210-krisp-billing-page/spec.md`

## Summary

Перестроить существующий server-rendered billing flow GRAF по наблюдаемой
иерархии KRISP: ясный первый экран текущего тарифа, компактная история и способ
оплаты, заметное сравнение периода, промокод внутри checkout и согласованные
pending/error/empty состояния. Одна Jinja/CSS-поверхность остаётся общей для web
и встроенного macOS кабинета. Backend-модели, платежные операции, маршруты,
YooKassa, каталог и desktop handoff не меняются; допускаются только безопасные
presentation-поля в GET context.

## Technical Context

**Language/Version**: Python 3.13+, Jinja2 templates, CSS; Swift 6.0 только для проверок существующей desktop integration

**Primary Dependencies**: FastAPI, Jinja2, SQLAlchemy; существующий WKWebView cabinet shell

**Storage**: PostgreSQL billing models только читаются существующими запросами; миграции и новые persisted fields не требуются

**Testing**: pytest contract/integration suites, Swift package tests, Playwright/browser viewport QA, Computer Use для установленного приложения

**Risk / Validation Lane**: high-risk-feature — user-facing payment UX, accessibility и approved reference-fidelity требуют полного Spec Kit, UX/financial-safety checklist, analyze, quickstart и repository gate

**Release Gate**: no deploy — реализация и локальная проверка разрешены; commit/PR/merge/release/deploy и реальная оплата не входят без отдельного разрешения

**Target Platform**: современный web browser и macOS embedded cabinet в поддерживаемом окне

**Project Type**: FastAPI web service с server-rendered cabinet и native macOS host

**Performance Goals**: первый meaningful billing render не добавляет сетевых round trips; все видимые значения приходят в одном GET; interaction feedback не зависит от тяжелого client runtime

**Constraints**: реальные GRAF цены/возможности; без horizontal overflow на 390/768/1024/1280/1440 px; keyboard, 200% zoom, WCAG 2.2 AA; без JS остаётся полный базовый flow; никакого извлечения KRISP code/assets

**Scale/Scope**: 1 shared billing surface, существующие billing templates и handlers, synthetic matrix owner/non-owner и free/trial/personal/pending/unavailable состояний

## Constitution Check

*GATE: PASS перед research; повторная проверка после design — PASS.*

- **Spec-driven delivery**: Feature 210 имеет spec, research, data model,
  contracts, quickstart, checklists, tasks и analyze до implementation.
- **Reference fidelity**: наблюдаемая KRISP IA/геометрия/состояния разрешены;
  код пишется независимо, third-party assets не копируются, private screenshots
  не попадают в git.
- **Truthful product and payment boundaries**: отображаются только утверждённые
  GRAF цены, реальные возможности, безопасные masks и существующие состояния;
  нет обещаний seat purchase, card replacement или storage add-on pricing.
- **Security and ownership**: существующие owner, CSRF, consent, catalog,
  idempotency, YooKassa URL, RLS, promo and reconciliation boundaries остаются
  неизменными.
- **Visible user control and accessibility**: destructive/financial actions
  остаются явными, keyboard/focus/live-region/200% zoom включены в acceptance.
- **Minimal implementation**: переиспользуются shared shell, route contexts,
  templates и CSS; новые зависимости, отдельный desktop UI и speculative
  abstraction запрещены.
- **No release mutation**: deploy, real payment, subscription mutation,
  commit и publication исключены текущим gate.

## Validation Plan

1. До кода сохранить synthetic reference ledger без private screenshots.
2. TDD: contract/accessibility/usability tests для hierarchy, safe context,
   selected cycle, no-JS forms, pending блокировки и допустимых URL.
3. Focused server suite:

   ```sh
   cd apps/server
   PYTHONPATH=src uv run pytest \
     tests/contract/test_billing_ui.py \
     tests/contract/test_billing_accessibility.py \
     tests/contract/test_payment_history_support.py \
     tests/integration/test_billing_usability.py \
     tests/integration/test_web_owner_session_context.py -q
   ```

4. Desktop boundary:

   ```sh
   swift test --package-path apps/macos \
     --filter 'DesktopCabinetBillingHandoffTests|DesktopCabinetRoutePolicyTests|CabinetSidebarRuntimeTests|CabinetBillingRuntimeTests'
   swift build --package-path apps/macos
   ```

5. Browser QA на 390x844, 768x1024, 1024x768, 1280x720, 1440x900:
   free, personal, non-owner, empty history/method, promo preview,
   pending/reconciliation, store/catalog unavailable; keyboard, 200% zoom,
   reduced motion, light/dark и no-JS fallback.
6. Installed desktop GRAF QA на минимальном, стандартном и fullscreen окне,
   включая раскрытую/скрытую правую панель. Проверить тот же visible state,
   встроенные billing routes и external `/offer` handoff.
7. Проверить fidelity ledger: IA, geometry, typography/color, interaction
   states, responsive/desktop embedding; каждое допустимое отличие объяснено.
8. Выполнить `infra/scripts/ci-local.sh --fast` перед closeout/PR. Full CI и
   deployment gate не запускаются: release не запрошен.

## Project Structure

### Documentation (this feature)

```text
specs/210-krisp-billing-page/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── desktop-web-parity.md
│   └── ui-contract.md
├── checklists/
│   ├── requirements.md
│   ├── ux.md
│   └── security.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/cabinet/
│   ├── web_routes/billing.py
│   ├── templates/cabinet/pages/billing_*_content.html
│   └── static/cabinet/cabinet.css
└── tests/
    ├── contract/test_billing_ui.py
    ├── contract/test_billing_accessibility.py
    ├── contract/test_payment_history_support.py
    ├── integration/test_billing_usability.py
    └── integration/test_web_owner_session_context.py

apps/macos/
├── RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift
└── RecApp/Tests/

CHANGELOG.md
```

**Structure Decision**: Реализация остаётся в существующем server cabinet.
`billing.py` может получить один небольшой private presentation mapper для
invoice, если он устраняет повторение между overview/history/detail. Production
Swift-файлы не меняются, пока route set остаётся прежним; macOS участвует в
runtime validation как host общей страницы.

## Complexity Tracking

Нет нарушений constitution и новых архитектурных сущностей. Отдельная desktop
разметка, client state store, новые API/routes, JavaScript framework, billing
service layer и migrations намеренно не создаются.
