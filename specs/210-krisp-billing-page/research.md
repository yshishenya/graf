# Research: billing page по наблюдаемой модели KRISP

## Reference baseline

Black-box проверка выполнена 2026-08-29 в установленном KRISP 3.15.6
(`ai.krisp.krispMac`) и авторизованном web/embedded кабинете. Проверены overview,
coupon disclosure, plan comparison с month/year, Core/Advanced checkout и empty
payment/invoice states. Финальное действие оплаты не выполнялось.

Наблюдаемая иерархия overview: текущий план и цена → компактные действия → один
выделенный upgrade offer → управление командой/владением → способ оплаты →
история. Comparison использует равные plan cards, явный selected border и ниже
— подробное сравнение. Checkout — узкая центрированная карточка: период, seats,
coupon, subtotal, final action. В GRAF seats заменяются правдивой workspace/owner
информацией и не влияют на цену.

Зафиксированы metadata-only параметры для fidelity: sidebar 200 px, content
padding 24 px, small controls 32 px, radius 8 px, plan cards radius 16 px,
heading 16/700, price 24/700, offer title 32/700, selected border 2 px purple.
Приватные screenshots, account content, KRISP assets и extracted application
contents не входят в evidence.

## Existing GRAF flow

- `billing.py` уже владеет overview, plans, discounts, checkout/preview/start,
  subscription, payment method, usage/storage, history, invoice и operation
  status routes.
- Feature 199 уже разделяет немутирующий promo preview и мутирующий checkout
  start. Preview — POST/Redirect/GET, не создает invoice, operation, reservation
  или provider request.
- Каталог правдиво содержит Free, trial Personal и Personal; конкурентный KRISP
  набор из трех коммерческих tiers копировать нельзя.
- Owner, CSRF, catalog version, emergency stop, offer/recurring consent,
  idempotency, YooKassa host validation, RLS, promo reservation и reconciliation
  уже реализованы и остаются authority.
- Текущий overview состоит из множества одинаково тяжелых `cabinet-card`; это
  скрывает тариф, цену, следующее действие и статус последней операции.
- Существующие CSS tokens уже близки к reference и поддерживают dark/light,
  focus-visible, reduced-motion, forced-colors и prefers-contrast. Новый theme
  layer или dependency не нужен.

## Desktop research

- Существующая `DesktopCabinetRoutePolicy.isBillingRoute` exact-allows весь
  текущий billing flow. Unknown sibling routes fail closed.
- `/offer` намеренно открывается во внешнем браузере с origin + canonical path;
  query/fragment удаляются. YooKassa navigation допускается только из checkout
  и только на allowlisted HTTPS hosts.
- `DesktopCabinetBillingHandoff` не имеет production call site; Feature 210 не
  должна его подключать.
- NSWindow: default 1280×760, minimum 1040×680. Native inspector занимает 52 px
  collapsed или 308 px expanded. Практические WebView widths: около 987/731 на
  minimum, 1227/971 на standard, 1387/1131 на 1440 fullscreen.
- WebView поддерживает page zoom 0.8–2.0 и использует общие templates/CSS без
  отдельного desktop billing layout.
- Baseline research tests: 98 focused Swift tests и 33 billing UI/accessibility
  pytest tests passed. Это baseline, а не closeout evidence после реализации.

## Decisions

1. Сохранить существующие routes, forms и backend projections; поменять
   визуальную иерархию в трех ключевых templates и billing-scoped CSS.
2. Не добавлять JS там, где server links/forms, `<details>`, fieldset/radios и
   CSS selected state покрывают поведение.
3. Не добавлять seat pricing, Enterprise, новые tiers или конкурентные claims.
   Workspace owner/members — документированное truthful deviation.
4. Overview показывает summary и короткий latest-invoice state; полная история
   остается отдельным route, чтобы первый экран не превращался в таблицу.
5. Plans и checkout получают один согласованный period choice через существующий
   `?cycle=month|year`; server remains pricing authority.
6. Pending/unknown/reconciliation/manual-resolution suppress competing checkout.
   Видимый safe continuation важнее reference fidelity.
7. Runtime geometry проверяется computed metrics в browser/WKWebView. Строковые
   CSS assertions недостаточны из-за поздних cascade overrides.

## Rejected alternatives

- SPA/component library: лишняя state-модель и no-JS regression.
- Новый billing API: дублирует уже безопасную server projection.
- Отдельный Swift billing screen: создает web/desktop drift.
- ASAR extraction или asset copy: нарушает независимую реализацию/provenance.
- Literal three-tier/seat UI: сообщает несуществующие условия GRAF.

## Open external gates

Real payment, provider mutation, production deploy, moderated usability and
public release remain outside this slice. Installed-app QA may validate only
non-mutating navigation and preview until a separately authorized exact build
exists.
