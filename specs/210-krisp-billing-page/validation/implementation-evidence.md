# Feature 210: implementation evidence

Дата: 2026-09-01.

## Scope и границы

- Validation lane: high-risk product area / payment UX and reference fidelity.
- Проверен установленный KRISP 3.15.6: billing overview, coupon disclosure,
  monthly/yearly comparison, Core/Advanced checkout, payment method и invoice
  history. Финальная оплата не запускалась.
- Исходники, ASAR и assets KRISP не извлекались. Реализация GRAF независимая и
  использует только наблюдаемую IA/UX-модель.
- Сохранены существующие YooKassa, promo preview, CSRF, owner/RLS, consent,
  idempotency и reconciliation boundaries. Новых routes, зависимостей,
  JavaScript framework или Swift production-кода нет.

## Automated evidence

- Focused server billing/security/authority/renewal: `106 passed`.
- PostgreSQL regression для one-trial-per-identity после owner/pending guards:
  `1 passed` в disposable container.
- Ruff для изменённых Python/tests: PASS.
- Focused macOS route/workspace/zoom/accessibility/runtime: `95 passed`.
- `CabinetBillingRuntimeTests` проверил WKWebView widths 390, 768, 1024, 1280 и
  1440 px, embedded widths 731–1387 px и 200% page zoom: horizontal overflow
  отсутствует, critical CTA не меньше 40 px.
- Spec Kit analyze: CRITICAL 0, HIGH 0.
- GitHub issue canon: PASS, 300 Spec Kit issues checked; Feature 210 tasks
  связаны с #5945–#5962.
- `git diff --check`: PASS.
- Exact reviewed SHA: `97c1489bf14280fc2f76fe515a8212a72f1baaf7`.
- На exact reviewed SHA `infra/scripts/ci-local.sh --fast` выполнен: сборка
  прошла, 781 macOS-тест запущен; 5 падений ограничены baseline
  `InstallerLifecycleEvidenceTests` с причиной `remote workflow files remain in
  the active repository`. Billing-код и связанные тесты в этих падениях не
  участвуют; full CI/release gate остаётся обязательным перед релизом.
- `infra/scripts/ci-local.sh --fast` штатно эскалировал в full из-за high-risk
  billing paths и завершился PASS: macOS `770 passed`, server parallel
  `3779 passed, 1 skipped`, performance `1 passed`, strict-RLS `52 passed,
  1 skipped`; Ruff, Python compile, ContractValidation, legacy-audio guard,
  compose и deployment-evidence scan — PASS.
- После review удалён дублирующий список blocking states из Jinja; route
  передаёт единый boolean из общей blocking-query. Focused billing regression:
  `80 passed`, Ruff/format и `git diff --check` — PASS.

## Browser QA

- Browser plugin: available; локальный origin `http://127.0.0.1:8081` на
  отдельной БД `twobrain_rec_210`.
- Overview проверен на 390×844, 768×1024, 1024×768, 1280×720 и 1440×900;
  horizontal overflow: 0.
- Plans: три равные карточки, selected annual state и server-link month/year;
  horizontal overflow: 0.
- Checkout при выключенном магазине показывает truthful unavailable state и не
  показывает guessed price; console warn/error: пусто.
- No-JS plans route работает. Light/dark, reduced motion и 200% scale проверены;
  при `visualScale: 2` horizontal overflow: 0.
- Page identity, non-blank DOM, отсутствие framework overlay и рабочий
  overview → plans → checkout preview interaction подтверждены. Provider start
  и финальная оплата не вызывались.

## Exact local desktop / Computer Use

- Собран exact local `GRAF Dev.app` из ветки `210-krisp-billing-page`.
  Developer ID local signing дошёл до собранного продукта, но Keychain вернул
  `errSecInternalComponent`; для локального smoke bundle был подписан ad-hoc.
  Это не distribution/notarization evidence.
- Через Computer Use exact bundle открыл loopback `/billing` внутри реального
  WKWebView shell. AX tree содержит heading «Тариф и оплата», Free-state,
  trial action, usage/storage, payment method и invoice history.
- В том же AX tree остаются доступными native capture region и кнопка
  «Начать запись системного звука»; billing zoom не масштабирует native shell.
- Workspace zoom повышен штатными командами до подтверждённого значения `2.0`;
  страница осталась читаемой и прокручиваемой без горизонтального выпадения.
  После проверки dev preference возвращён к `1.0`.
- Computer Use click-channel стабильно прерывался на WKWebView link/window
  actions. Поэтому ручная матрица 1280/fullscreen и inspector collapsed не
  считается закрытой; её геометрия покрыта runtime matrix, но task T017 остаётся
  открытым до полного повторного interactive smoke.
- Временный local-only initial-route seam использовался только для открытия
  `/billing` после сбоя click-channel и полностью удалён из исходников.

## Fidelity ledger

| Категория | Наблюдаемая модель KRISP | Реализация GRAF | Статус |
|---|---|---|---|
| IA и порядок | Plan summary → upgrade → account/payment → invoices | Current plan → GRAF options → workspace/usage → payment method → history | PASS; truthful GRAF naming |
| Composition | Compact plan card, period switch, comparison cards, order summary | Те же уровни и визуальная иерархия на реальных GRAF данных | PASS |
| Typography/color | Neutral dark surfaces, restrained accent, prominent amounts/actions | Существующие GRAF tokens, compact controls, light/dark/contrast states | PASS |
| Interaction | Month/year, coupon disclosure, selected plan, checkout summary | Server links, native `details`, preserved forms/CSRF/no-JS | PASS |
| Responsive/embed | Narrow web and desktop cabinet remain usable | 390–1440 px, 200%, embedded inspector widths; native capture remains visible | PASS automated; desktop interactive matrix partial |

Разрешённые отклонения: GRAF показывает workspace owner/role вместо KRISP seat
management, реальные GRAF plans/limits вместо KRISP catalog, YooKassa вместо
чужого provider и не отображает цену, если магазин выключен. Эти отклонения
сохраняют правдивость продукта и payment trust boundaries.

## Closeout boundary

- Реальная оплата и изменение подписки не выполнялись.
- Изменения закоммичены и отправлены в PR #5963; merge, release и deploy на
  момент этой записи не выполнялись.
- Production/test-shop configuration не менялась.
- Evidence содержит только synthetic/local metadata; credentials, payment
  identifiers, transcript/meeting content и reference screenshots в git не
  записывались.
