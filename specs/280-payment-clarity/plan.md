# Implementation Plan: Понятная оплата

**Branch**: `codex/280-payment-clarity` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)
**Input**: `specs/280-payment-clarity/spec.md`

## Summary

Упростить существующий кабинет: один главный шаг, полная сумма и условия на виду, второстепенные расчеты по раскрытию. Исправить обнаруженные препятствия и недостоверные состояния. Сохранить финансовую модель F278, существующие шаблоны и компоненты, цены, отдельную оферту и запрет повторных платежей; режим разовой оплаты расширяется только по FR-019/020.

## Technical Context

- Language/Version: существующие Python 3.13+ и Swift 6; Jinja2/HTML/CSS и небольшой существующий JavaScript.
- Primary Dependencies: FastAPI, SQLAlchemy, Jinja2, WKWebView; новых зависимостей нет.
- Storage: существующий PostgreSQL; без миграций и изменения денежных вычислений.
- Testing: существующие pytest, Playwright (Node), Swift Testing/XCTest.
- Risk / Validation Lane: `high-risk-product`, поскольку денежные решения, состояния и защищенная навигация macOS.
- Release Gate: коммит реализации только после локальной проверки и одобрения владельца; затем точные SHA checks `governance-fast`, `macos-pr`, `pr-metadata`. Выпуск отдельно: frozen `release-full`, dry-run, разрешение; F278 financial gates сохраняются.
- Target Platform: веб 320/360/768/1280 px, light/dark, 200%; macOS embedded, только GRAF Dev через harness.
- Performance Goals: не добавлять внешних запросов/тяжелых библиотек/новых polling loops; локальные раскрытия мгновенны, путь не длиннее исходного.
- Constraints: не менять provider, idempotency, версии authority, catalog, receipt/refund, privacy, analytics; сохраняемый выбор и False→no-save меняются только по FR-019/020; синтетические данные в проверках.
- Scale/Scope: 12 платежных шаблонов и приглашения, связанные модели представления, узкая native route policy, тексты JS storage и целевые проверки.

## Constitution Check

До исследования: PASS — цель соответствует §II (явное согласие), §III (ограничение данных), §VI (полный Spec Kit), §VII (существующий стиль/собственный код). Capture и AI не меняются.
После проектирования: PASS по тем же основаниям. Никаких новых сторонних ресурсов/шрифтов/изображений, источники — исследование поведения. Проверка reviewer-owned checklist до кода обязательна. Успешные локальные тесты не заменяют внешнее финансовое подтверждение, людей или установленный Dev.

## Phase 0 — Research

Исследование: [research.md](research.md), исходная карта и замечания [audit.md](audit.md), независимая оценка [ux-audit.md](ux-audit.md). Источники прочитаны и сохраняются с применимостью/ограничениями; выводы проверены по реальным исходникам. Гипотеза опровергается, если скрытие текста лишает человека важных условий: такие сведения остаются на виду.

## Phase 1 — Design

[contracts/payment-journey.md](contracts/payment-journey.md) определяет экраны и состояния. [data-model.md](data-model.md) фиксирует только представление существующих данных. Новую машину платежей и слой компонентов не создавать.

Исправления recovery принадлежат существующему `cabinet/web_routes/billing.py`: ссылка invoice→status, сохранение cycle, ранняя понятная проверка verified receipt contact с существующим путем account. Выявленная потеря контекста требует переноса узко проверенного `next` через существующие settings/email/merge формы и переходы: `auth/redirects.py`, `cabinet/web_routes/settings.py`, `auth_email_flow.py`, `account_merge.py`, `cabinet/rendering.py`, `cabinet/auth_rendering.py`, два account templates и auth `email_code.html`/`login.html` для явного возврата на каждом шаге. Это только навигация; правила доказательства владения почтой, сессий, CSRF и объединения не меняются, состояния refused/service_gap/renewal blockers. Новые backend fields только там, где шаблон не может правдиво использовать существующие данные. Финансовые обработчики не переписывать.

Нативная политика разрешает ровно четыре существующих POST: storage preview, cancel-selection, subscription early-preview и purchases confirm; остальные неизвестные пути запрещены. Контроль method/origin и внешний provider handoff сохраняются.

## Validation Plan

[quickstart.md](quickstart.md): целевые серверные/браузерные/native тесты; синтетическая визуальная матрица и подсчет видимых пояснений до/после. Три независимых reviewer-прохода после кода; исправления запускают повторный узкий набор. Реальные пользователи SC-005 и наблюдение SC-006 остаются отдельными задачами. Без нового коммита нельзя продвигать dirty checkout в GRAF Dev; сначала все возможные локальные проверки.

## Project Structure

- `specs/280-payment-clarity/`: spec, plan, research, audits, contracts, checklists, tasks, quickstart, validation.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_*_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/{cabinet.css,cabinet.js}`
- `apps/server/tests/{contract,integration,unit,browser}/` — существующие billing tests + один focused regression suite.
- `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`
- `changes/unreleased/F280.yaml`

## Complexity Tracking

Нарушений конституции нет; миграции, новые пакеты, framework, экспериментальная аналитика и изменение тарифов не требуются.


## Дополнение: T014/T015 после проверки промокода

Продолжение существующего high-risk-product среза F280, без нового стека и миграций. Модель представления истории читает цикл сохранённого счёта в текущем пространстве; отсутствующий/неизвестный цикл даёт пустую подпись. Общий запрос кампаний и список непроверенных предложений удаляются целиком: доступность конкретного известного кода уже проверяет существующее оформление. Текущие цены, snapshot/quote, eligibility, provider, idempotency, receipt, cookie path/TTL и lifetime не изменяются.

Целевая проверка: синтетическая универсальная кампания + годовой счёт и изменение текущей кампании; неизвестный период; ограниченная/исчерпанная кампания не обещается как доступная; HTTP-путь валидного кода месяц→год→очистка. Сохраняется существующий более широкий набор promo/storage/early и защита запроса/роли/пространства. Независимый requirements reviewer до кода, затем независимые обзоры результата; новая реализация и выпуск имеют свои точные SHA gates.


## Дополнение 2026-10-01: сохранение промокода после обновления

Продолжение F280, lane `high-risk-product`: меняется жизненный цикл пользовательского выбора и его граница сессии. Текущий замороженный выпуск не изменять; новый срез проходит отдельные exact-SHA PR проверки и последующий серверный выпуск. Разрешение владельца на публичную оплату и технический выпуск уже есть, поэтому новый запрос разрешения не нужен. Финансовая и человеческая приёмка остаются отдельными.

### Уточнение и исследование причины

Текущая ветка среза: `codex/280-payment-promo-refresh`. `$speckit-clarify` использует полученный конкретный ответ пользователя; FR-017/018 и SC-007 задают цель и ограничения, новых продуктовых вопросов нет. Независимый source reviewer подтвердил в `cabinet/web_routes/billing.py` чтение общего cookie при GET оформления и его удаление в этом же ответе; helper `_checkout_result_redirect` ставит состояние на 300 секунд. POST preview передаёт выбранный cycle в URL, но следующий GET уже лишён кода. Ошибочный формат очищается ещё в helper. Наличие этих путей не доказывает конкретную последовательность неизвестного пользовательского кода.

Решение: обычную отправку формы с переходом 303 сохранить. Меняется только безопасное кратковременное представление выбора. Готового универсального helper для подписанного выбора здесь нет: переиспользовать существующий стандартный образец из `auth/dependencies.py` (base64 JSON + HMAC + constant-time comparison + expiry) и уже настроенный `app.state.web_csrf_secret`, с отдельным purpose/version для промокода. Частный CSRF helper не использовать как общий сериализатор и новый общий механизм хранения не создавать. Без новой зависимости, ключа, таблицы или миграции. Подпись/целостность и связь с проверенными `principal.user_id`, `tenant_scope.workspace_id`, `principal.session_id` обязательны; отсутствие проверенной сессии или ключа не разрешает неподписанный запасной путь. Имя cookie само по себе не доказывает связь содержимого: переименование/перенос также должны отвергаться. Старый общий `graf_checkout_promo` не читать и не наследовать.

### Модель и договор состояния

Кратковременное состояние содержит только введённый код длиной не более 48 символов, cycle `month|year`, expiry и границы пользователя/пространства/сессии; формат и назначение подписи имеют отдельный префикс версии. Код с ошибочным форматом сохраняется как закодированный ограниченный ввод, проверка корректности остаётся серверной. Существующие `HttpOnly`, `SameSite=Lax`, `Secure` на HTTPS и путь `/billing/checkout` сохраняются. Срок — ровно 300 секунд с явной отправки/замены; Обычный GET не переписывает состояние; явный допустимый GET меняет только период без продления срока и не продлевает срок. Целостность, срок и все три границы проверяются сервером до использования. Код не переносится в URL, localStorage, JavaScript, журналы, снимки или evidence. Синтетические тесты могут читать выдуманное значение; реальный код в документы не включать.

Состояния: absent → applied/rejected при явном вводе; applied/rejected → повторное чтение без нового срока; replacement → новое состояние по явному действию; explicit remove/empty input → absent; expired/corrupt/foreign/session changed → absent; авторитетно созданная операция → absent, дальнейшее продолжение по существующим operation/invoice. Смена month/year не означает удаления кода: каждый GET заново проверяет его применимость к текущему периоду и получает свежий расчёт. Если акция изменилась/закончилась, введённый код остаётся с понятной ошибкой и заблокированной оплатой, обычная сумма не подставляется молча. Ошибочный формат до 48 символов также сохраняется до expiry с ошибкой и безопасно экранируется в форме; сырых байтов в response headers нет, поскольку payload кодируется до подписи. Значения больше существующего MAX48 не сохраняются как новый допустимый ввод. Валидный query cycle при явном переключении приоритетен; без него берётся сохранённый cycle, после отсутствия состояния — действующий обычный выбор. Явная смена периода может обновить cycle с прежним expiry, но не продлить срок кода. Ошибки start/recovery также не продлевают expiry существующего выбора: новую пятиминутку получают только явное применение/замена кода.

Все читатели/писатели `_checkout_result_redirect` получают границы явно из уже проверенных зависимостей. Preview, `/billing/discounts/apply`, checkout GET, `/billing/discounts/remove`, ошибки checkout start и переходы к созданной/продолжаемой операции рассматриваются совместно. Не расширять cookie path ради флага discounts page. Скрытые quote/idempotency/offer поля и согласия не превращаются в сохраняемый выбор: оферта всегда непринята, выбор автопродления соответствует FR-019/020, перед денежным действием остаются прежние проверки цены/оферты/прав/свежести/idempotency. POST preview не создаёт operation/invoice/reservation и не вызывает провайдера.

### Последовательность работ и приёмка

Перед генерацией задач и реализацией независимый reviewer читает новый `checklists/promo-refresh.md` и актуальность действующих requirements/ux-payment/promo-presentation; сам автор отметок не выставляет. После полного PASS добавляются T016–T019: воспроизведение и отрицательные проверки → исправление existing routes/helpers → регрессии, три независимых обзора и convergence → новый exact-SHA выпуск и evidence. T011/T012 не дублировать, чужой замороженный кандидат не менять. Браузерная приёмка требует настоящую синтетическую DOM submit→303→reload/back цепочку Chromium/WebKit; fixture-only матрица остаётся дополнительной проверкой вида. Native handoff выдаёт обычную браузерную сессию, уже внутри неё работает новый выбор; переход к новой сессии не наследует старый draft, native policy не меняется. Точный перечень сценариев и команды — дополнение [quickstart.md](quickstart.md).

Конституция до исследования: PASS по §II/III/VI/VII — согласия явны, данные ограничены, полный существующий Spec Kit, стиль/активы без изменения. После проектирования: PASS — временный выбор не становится финансовым источником правды, подпись и проверенные границы обязательны, ни деньги, ни сессии авторизации не создаются, capture/AI/native/public macOS artifacts не меняются. Открытая человеческая/финансовая приёмка не объявляется выполненной.

Native preview form: кнопки периода связаны с одним редактируемым полем через HTML form. Ограниченное скрытое `previous_promo_code` передает последнее показанное значение только как подсказку о правке: новый ввод при смене периода — явная замена с новым сроком; тот же код сохраняет прежний срок или прекращается после expiry. Это недоверенный ввод, не разрешение скидки/платежа; применимость, границы сессии, цена и согласия по-прежнему проверяются сервером. Подсказка позволяет не терять впервые введенный код и не оживлять прежний истекший код стандартными средствами формы.

Отказ промокоду при входе со страницы скидок также использует 303 к оформлению с подписанным вводом и ошибкой; это закрывает тот же сброс при refresh, не расширяя cookie path. Прежний локальный same-page 409 обновляется в соответствующем тесте возврата.

При финальном визуальном обзоре подтвержден дефект WebKit320: вложенная grid-разметка растягивает согласия до769px. Узкая правка existing cabinet.css использует flex для checkbox/text; финансовые формы и текст сохраняются. Приемка проверяет фактическую компактную высоту и расстояние до кнопки обоими браузерами; это FR-012/T018, не новый дизайн.

### Пограничные случаи после автоматического обзора PR #7403

T017 сохраняет период подписки в обоих результатах discounts apply. При смене периода сравнивает недоверенный предыдущий ввод с текущим подписанным выбором; старая неизмененная форма использует более новый проверенный выбор без продления срока. Явные apply/правка и remove сохраняют определенную семантику. Promo editor не зависит от подтверждения почты, тогда как payment form и start guards остаются зависимыми. Прежние обзоры до этих исправлений не подтверждают новый SHA.

### Точная семантика двух вкладок

При переключении периода неизмененный ввод старой формы A (promo_code == previous_promo_code) и текущий действующий подписанный выбор B используют B, сохраняя исходный expiry B. Неподписанная подсказка не разрешает скидку; новые условия B проверяются сервером. Если B уже истек/поврежден/чужой, A не возрождается и показано прежнее объяснение promo_expired. Явное Apply или действительно измененный непустой ввод — намеренная замена и новый срок; явное пустое Apply и remove — удаление. Пустая старая форма при смене периода не является командой удаления нового B.

При входе со страницы скидок без выбранного периода источник — текущий действительный цикл подписки, иначе month; оба исхода valid/invalid сохраняют его. Редактор промокода доступен до подтверждения почты, форма start и денежное действие недоступны. Проверочная матрица: year discounts valid/invalid; tabs A→B→stale A period; empty stale period; explicit A replacement; explicit empty Apply; expired B stale A; no receipt invalid→edit→clear при отсутствии start.

### PR7403: статус истории и прямые HTTP409

В существующем status GET удалить безусловную очистку черновика; общий operation redirect сохраняет очистку после авторитетной операции. Общая отрисовка checkout для прямых offer_changed/quote_changed должна брать проверенный подписанный код и период вместо старого request.state; точные причины отказа и финансовые проверки сохранить. Регрессии добавить в существующий HTTP/SQL файл T016, затем независимая сверка и convergence до выпуска T019. Новых моделей/зависимостей/сервисов нет.

Смежный303 start исправить в общем result helper с учётом происхождения start; все callers наследуют сохранение B/code/cycle/expiry. Preview-переключение периода и explicit replace сохранить. Разрешённые redirects продолжения существующей операции используют существующий operation helper, чтение/отказ не очищают выбор.

Последняя409 поправка: signedB период приоритетен; без B сохраняется допустимый Form cycle из двух прежних request.state присваиваний. Promo renderer остаётся только signedB; ни старый код, ни принятие оферты не восстанавливаются; явный выбор автопродления соответствует FR-019/020. Отдельная регрессия year без saved draft для offer_changed/quote_changed; прежний money-path тест переводится на реальное Apply перед start с сохранением всех проверок цены/оферты/непринятой оферты/provider0 и сохранённого выбора FR-020.


### Явный ввод при временной недоступности preview

Если checkout выключен или dependency db отсутствует после открытия формы, явное Apply/изменённый непустой ввод сохраняет новый bounded подписанный код и допустимый период на исходных условиях TTL300/binding. Пустое Apply очищает выбор. Неизменённая старая форма при смене периода сохраняет действующий B с прежним сроком; истёкший B не возрождается. Причина unavailable остаётся видимой, расчет/денежное действие не выполняются. После восстановления доступности каждый GET проверяет свежую цену и применимость. Это FR017/018, существующие T016–T019, без нового права на оплату.


### Явный период из ссылки выбора тарифа

Действующий подписанный промокод и переход GET /billing/checkout?cycle=month|year считаются явным выбором периода. При отличающемся периоде подписанный draft сохраняет этот период с исходным expiry, не начиная новый TTL; последующие GET без query и ошибки start сохраняют его. Обычный GET/невалидный query не переписывает выбор. Истёкший/чужой/повреждённый draft не возрождается; денежные проверки и согласия прежние. Прямой старый POST по-прежнему предпочитает текущий B, а не период A. Это уточнение FR017/018/SC007 и существующих T016–T019.


## Дополнение: необязательное продление, T020–T022

Ветка `codex/280-payment-optional-renewal`, существующая F280, lane `high-risk-product` + выпуск `release-deploy`. Specify/clarify выполнены по прямому решению пользователя; новых продуктовых вопросов нет. Constitution before/after design: PASS — отдельная оферта явно отправляется перед оплатой, снимаемое разрешение показано на виду и фиксируется в финансовом снимке при явном денежном действии; capture/privacy неизменны, новые зависимости/таблицы/миграции не нужны. Исключение к старому UX-требованию непредвыбранных обеих галочек — явное решение владельца, а не скрытый обход.

Сначала RED-регрессии. Затем минимально обновить `cabinet/web_routes/billing.py`: False не отклоняется, request/invoice snapshot содержит фактический bool, общий `_create_initial_checkout_payment` требует именно bool и передаёт его в YooKassa `save_payment_method`. Recovery всех callers продолжает исходный immutable snapshot/key. В `billing/entitlements.py` новое сохранение карты разрешено только с consent is True; выдача оплаченного периода не зависит от recurring consent. Существующие проверки версии authority, актуального владельца, duplicate grant и сохранение оплаченного остатка не ослабляются.

Шаблон `billing_checkout_content.html`: required только у оферты; recurring checked по умолчанию, выбор False доступен с клавиатуры; сводка показывает отсутствие автоматического списания при False; базовый HTML без JS обозначает будущую цену условно («При автопродлении»), а JS отображает явное OFF и скрывает дату списания. Использовать существующие meta graf-time-user/graf-workspace/graf-time-session (UUID идентичности, не session token) и sessionStorage только для bool визуального выбора: ключ graf-checkout-renewal:<user>:<workspace>:<session>. API/cookie/promo draft не расширять; новый финансовый источник правды не создаётся. В новой вкладке без перенесённого состояния True, в текущей False переносится до окончания браузерной сессии; code не появляется в URL или JS storage. Сохранять False через preview/cycle/remove/reload/ошибки, при этом новая оферта всегда выключена. Каждая обычная новая вкладка без opener начинает с True; стандартное клонирование sessionStorage браузером при opener не обходить новыми tab IDs. JS init/HTMX/pageshow синхронизирует checkbox и summary. При отсутствующих meta или отказе storage checkbox/summary работают в документе, перенос после полной навигации best effort; безопасный fallback не наследует чужой контекст. Без JS обычный POST сохраняет выбранное значение, межстраничное сохранение недоступно. Конечный режим денежной формы фиксируется в авторитетной операции; повтор продолжает первоначальный режим независимо от визуального выбора.

Независимый requirements gate: `checklists/optional-renewal.md` и `review-optional-renewal-requirements.md`, отметки только рецензенту. После него analyze → issue sync → T020 RED/код → T021 browser/security/flow и convergence → T022 exact-SHA PR/Full/CD/runtime/release. Новое доказательство обязательно, прошлый Full/DOM не переиспользуется для изменённого кода. Серверная публикация не пересобирает публичный macOS пакет; T011/T012/F278 сохраняются.

## Дополнение: отказ создания платежа, FR-021–023 / SC-009

Существующая F280, lane `high-risk-product` в active Spec Kit slice, затем `release-deploy`. Specify/clarify опираются на полученные решения и подтверждённую причину. Constitution before/after design: требования приватности, явного согласия, изоляции пространств, отсутствия повторного списания и достоверного статуса сохраняются; новых таблиц, миграций, API, зависимостей и перехода True→False без пользователя нет. Исторические T020–T022 и их выпуск не переобозначаются как проверка нового кода.

Минимальный код находится в `apps/server/src/twobrain_rec_server/billing/yookassa.py`, существующем `cabinet/web_routes/billing.py` и `cabinet/templates/cabinet/pages/billing_operation_status_content.html`. В `_request` только для HTTP403 + JSON error/forbidden + точного известного отказа магазина в recurring вычисляется фиксированный `recurring_not_available`; полное тело/description/provider request id не сохраняются. Ошибка содержит прежний HTTP status и необязательный фиксированный признак. Незнакомый JSON, текст и malformed body остаются прежней общей ошибкой. При сохранении `provider_failure` разрешается исключительно этот известный признак; произвольные значения не переносятся.

Страница статуса выводит отказ создания из авторитетной операции: purchase_schema == 2, operation.state == canceled, provider_id is None, provider_failure.class == provider_rejected и сохранённый целочисленный HTTP в {400, 401, 403, 404, 405, 415, 429}. Bool, строка, другой статус или незнакомая class не подтверждают этот UI-признак; прежние schema1/предотправочные ошибки без такого доказательства остаются с прежним безопасным представлением. Общий старый403 также даёт «Не удалось начать оплату»; уточнение автопродления допустимо только с сохранённым fixed reason, HTTP403 и snapshot recurring_consent is True. Источник — сохранённое состояние, а не query result. `_bind_initial_checkout_payment`, dispatch/state rules, promo release, acceptance budget и GET/list recovery сохраняют финансовую семантику. Подтверждённая provider cancellation сохраняет прежний самостоятельный путь повторной оплаты; manual_resolution, unknown и известная ссылка на провайдера не получают этот новый creation-rejection путь. В UI новое действие использует существующий retry URL и checkout, показывает способ вручную выбрать False; не создаёт новую форму, POST, автоматическое переключение или обход оферты. Отказ не обещает, что False обязательно будет принят внешним провайдером.

Сначала independent reviewer-owned gate `checklists/provider-rejection.md`; затем окончательные задачи T023–T025, read-only consistency analyze, deduplicated canon issue sync и RED. Матрица на существующих adapter/recovery/status/return тестах проверяет точный и соседние ответы, безопасные поля, старый403, retry/cycle, один POST и прежние неопределённые состояния. Настоящие Chromium/WebKit и независимые flow/security/browser reviews завершают срез до нового exact-SHA PR/Full/CD/runtime/publication. Финансовая и человеческая приёмка отдельны; подпись/байты публичного macOS пакета не меняются серверным выпуском.


## Продолжение F280: промокод на месте, FR-024–030 / SC-010–012

Ветка `codex/280-promo-inline`; lane `high-risk-product` в active Spec Kit slice, выпуск `release-deploy`. Specify/clarify завершены2026-10-02 без неотвеченных решений. Constitution before/after design: PASS — применяются §III приватность, §VI проверяемый Spec Kit, §VII доступность/собственный код; capture/AI/удаление и распределение macOS неизменны. Контекст данных остается описан существующим `data-model.md`; нет новых таблиц/миграций, API, платежной машины или формата cookies. Локальные состояния нового представления и уточнение поведения без storage описаны в `contracts/payment-journey.md`, не расширяют финансовую модель.

### Архитектура и границы

1. Использовать загруженный HTMX2.0.10 как улучшение `#billing-promo-preview`: hx-post текущего preview, hx-target/hx-select checkout main, outerHTML и без push history. Обычные action/method/внешние form-associated input/buttons сохраняются; native JS-off получает прежний303. Сохранить POST303→GET200: XHR следует тому же redirect/Set-Cookie, а hx-select извлекает main из обычного full shell. `templates.py` задает private/no-store, DENY/no-referrer и не является автоматическим fragment renderer; общий `_page_shell` не переписывать. Если исследование докажет необходимость явного HX response, узкое изменение только billing.py должно использовать общий расчет/context и прежние guards, не создавать второй расчет.
2. В существующем `cabinet.js` добавить небольшой scoped preview lifecycle: beforeRequest фиксирует scope и bool текущего выбора, снимает прежнюю оферту, ставит busy; связанные Apply/cycle и native start не могут конкурировать. Ограничить preview ожидание15с. afterSwap использует существующий глобальный initCabinet; временный bool текущего документа восстанавливается в той же scope и после повторных ошибок даже без sessionStorage. Метаданные user/workspace/session не являются auth token. При смене scope временная память очищается; дефолт True в новом контексте. Междокументное сохранение без storage остается best effort, promo/сумма/оферта в JS storage не добавляются.
3. BeforeSwap допускает только ожидаемый checkout main с соответствующим контекстом и результатом текущего запроса. Другие login/owner/error HTML, detached/stale ответы не считаются свежим расчетом. Network/timeout/500/429/swapError снимают busy, показывают inline ручной повтор, блокируют start и оставляют оферту пустой. Успешная новая проверка снимает этот временный запрет только если сервер вернул валидную form с quote/receipt/нет pending blocker. Никакого автоматического start, provider POST или обхода серверных условий.
4. При успешном смененном периоде привести текущий URL к `/billing/checkout?cycle=month|year` через replace, без нового history entry и без кода/quote/result/consents. Иначе прежний query year после inline month переопределит cookie при следующем reload. Серверные правила signed draft сохраняют выбранный cycle/исходный expiry; устаревшие вкладки/409 продолжают предпочитать текущий signedB. Session/cookie не реконструировать в JS.
5. Публичные тексты `purchases.py`: `validate_acceptance_campaign` сообщает о недоступном промокоде и исправлении, `reserve_acceptance_budget` о недоступной оплате аккаунта/поддержке. Все условия budget/workspace/expiry/reservation сохранены. Общий loader применяется в GET/start/initial preview/storage preview/early renewal; `_reserve_purchase_promo` проверяет кампанию напрямую перед окончательным резервом. Нельзя исправить только шаблон и оставить внутреннюю фразу в другом caller; нельзя обещать обход dedicated budget удалением промокода. Denial ответа не вводит новый provider reason или финансовый переход.
6. Перед/после замены сохранить логичный focus в promo input/Apply/selected cycle либо связанной ошибке, объявить состояние один раз через role=status/alert. Обычный initBillingFocus не должен переводить preview в h1. Использовать существующие стили кабинета; при необходимости только существующий cabinet CSS без новой библиотеки/шрифта/asset.

### Сроки и совместимость

Draft max48/code/cycle/expiry/user/workspace/session, HMAC/HttpOnly/SameSite/Lax/Secure/path и TTL300с прежние. GET/cycle/start error не продлевают TTL; explicit apply/replace может начать новые300с. Quote остается10мин с прежним переиспользованием равного снимка. Start перепроверяет свежие цены/offer/quote/authority и принимает фактический bool; карты/доступ/recurring после success прежние. Receipt не подтвержден → только promo editor/account, без monetary form. Авторитетная pending/unknown operation блокирует новую оплату. Ошибки/исторические snapshots не переписываются; старые финансовые403 не переотправляются.

### Проверки и порядок допуска

Переиспользовать `tests/integration/test_billing_promo_refresh.py`, `tests/unit/test_billing_purchases.py`, `tests/contract/test_billing_ui.py`, `tests/contract/test_billing_clarity.py`, `tests/browser/billing-promo-refresh.test.cjs` и `tests/contract/test_billing_promo_refresh_browser.py`. Сначала regressions/RED нового поведения, затем минимальные изменения; настоящий bridge ASGI→PostgreSQL, synthetic provider и оба браузера. Existing start остается native navigation; preview harness больше не ждет navigation, проверяет unchanged document marker/history и новый DOM. Network/delay/auth/context/blocked-storage случаи входят в ту же инфраструктуру; JS-off separately реальными HTTP303/GET, без fixture claims. Старые return/authority/receipt/cookie regressions сохранить. Три независимых flow/security/browser заключения, исправления и convergence обязательны.

Предварительное разделение T026–T028: T026 server RED/GREEN и понятные public errors в общем purchases.py; T027 inline template/lifecycle и существующие regression/browser cases; T028 настоящий browser, независимые reviews/converge, exact-SHA PR/Full/CD/runtime/publication. Окончательные executable tasks генерируются только после независимого reviewer PASS `checklists/promo-inline.md`, согласно `$speckit-tasks` prerequisite. Новый checklist генерируется unchecked; прежние checklist marks не выдаются за новый review. Root владеет production template/cabinet.js/purchases.py; tests worker владеет существующими наборами server/browser проверки. Billing.py/общий renderer меняются лишь при конкретном необходимом дефекте текущего минимального пути; для HX-select полного GET ответа это не нужно. Владение конкретными файлами root согласует до изменения, чужие правки не откатываются. До gates реализации нет. Issue sync принадлежит root после нового read-only analyze; новый issue/закрытие прежнего не предполагается до проверки дублей.

Новые evidence: `validation-promo-inline.md`, `review-promo-inline-final.md`, `converge-promo-inline.md`, `release-promo-inline-closeout.md` плюс metadata-only запись по выбранному кандидату. Выпуск требует свежих exact-SHA checks/frozen Full и CD dry-run/execute по действующему разрешению владельца; source/runtime/publication отдельны, публичные macOS байты сохраняются. Установленный Dev/люди/F278/T011/T012 остаются собственными незакрытыми доказательствами.

После конкретного GitHub FAIL область тестов расширена только на три существующих runtime сценария в `tests/contract/test_cabinet_static_assets_contract.py`: их модель dispatch должна вызывать всех зарегистрированных обработчиков, как настоящий браузер. Root отвечает за эту узкую коррекцию, независимый read-only reviewer проверяет сохранение assertions. Production touchpoints остаются прежними.
