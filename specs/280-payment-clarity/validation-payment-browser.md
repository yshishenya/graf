# F280 — браузерная проверка возврата оплаты

Дата: 2026-10-03. Владелец: независимый browser tests worker. Scope: новые `apps/server/tests/browser/billing-payment-return.test.cjs` и `apps/server/tests/contract/test_billing_payment_return_browser.py`; production не изменялся этим исполнителем.

## RED до изменения JS/шаблона

Команда:

```sh
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=chromium GRAF_NODE_MODULES=airis-optout-native-deps/node_modules apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -k 'success and 320' -q --tb=short --show-capture=no
```

Результат: **1 FAILED / 1 deselected**, Chromium320. Настоящий HTTP→ASGI→PostgreSQL и синтетический transport ЮKassa; initial checkout создан существующим штатным тестовым helper, invoice/operation по одной, grant0 до возврата. Новый денежный POST запрещен мостом; browser expected automatic success, но locator «Оплачено» исчерпал5с (`automatic-success`, `TimeoutError`). Все24 записанных HTTP запросов были GET200; refresh POST0, bridge errors0. Это ожидаемый RED поведения отсутствующей автопроверки; production JS/template еще прежние. Root уже отдельно менял server routes после собственного server RED.

Локальный log: `graf-f280-payment-browser-red.log` (только синтетический trace/stage/count; без session/cookie/payload). Duration23с с подготовкой; call9.72с включает запуск браузера и timeout5с.

Исходники перед RED:

- cabinet.js SHA256 `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34`.
- billing_operation_status_content.html SHA256 `9b428a4474355dc5357393773ad31fb382ecb90980f26c4e93d9f18c9737c0a9`.

Первый подготовительный запуск остановился на дублированном именованном cookie TestClient (`CookieConflict`) до браузера. Helper выбора корректного issued cookie исправлен; этот сбой не считается RED продукта. Еще один запуск с неверным префиксом пути не собрал тесты; runner требует `tests/...` из apps/server, исправленная команда указана выше.

CHK001 повторно подтвержден в reviewer-owned отчете: только связанный grant/исторический срок, без зависимости от current active subscription; requirements PASS17/0. Окончательный analyze и issue sync перед test GO подтвердил root. RED не является GREEN, выпуском либо финансовой приемкой.

## Промежуточная проверка контроллера и исправления стенда

Реальный Chromium320 → HTTP → ASGI → PostgreSQL: `-k '320 and (errors or guards or lifecycle or timeout)'` дал **4passed/24deselected** после серверного исправления local recovery. Лог `graf-f280-payment-browser-controller-debug2.log`,55.37сpytest. HTTP401/403/429/500, network/unexpected HTML, incoming/current user/workspace/session/invoice/missing scope, busy/double trigger/reinit, hidden/visible, detached target, actual navigation и настоящий XHR timeout15с с исходным серверным POST, продолжающим жить до17с. Recovery GET не начинает второй POST. Cookie/timezone/CSRF и HTML настоящие; provider synthetic; новых create/operation/invoice/grants нет.

Предыдущие полные прогоны12failed/16passed не являются GREEN. Исправлены именно ошибки стенда: page-level route.continue пропускал нижний счётчик; глобальный locator видел меню «К встречам»; фокусируемый элемент — main, не h1; result provider error называется unavailable; Playwright routing не перехватывает следующий URL redirect, поэтому named faults теперь fetch настоящие POST303→GET до изменения ответа; timeout assertions ждут окончания исходного server thread перед проверкой SQL. Таймер0 может исполниться даже при paused clock, поэтому fault/hold устанавливаются до initial GET, а current-scope меняется после первого доказанного check. Нельзя трактовать preparatory failures как дефекты продукта или ослаблять финансовые assertions.

## Независимая находка и ее закрытие: вторичное продолжение pending

Первоначальный **HOLD**, подтверждено actual DOM RED3октября: `graf-f280-payment-browser-continuation-red.log`; команда того же runner с `-k 'pending and 320'`,1FAILED/27deselected. Настоящий provider GET успешно оставляет этот же payment pending, локальные invoice/operation pending/provider_pending. В карточке отсутствует «Вернуться к оплате» (expected1, actual0). Новой денежной операции нет.

Причина: `_status_refresh_result()` при processed1/pending1/failed0 возвращает `refreshed`; template открывает вторичный continue лишь для `status_result == "unchanged"`. Существующий can_continue_payment проверяет допустимый invoice.pending + operation.provider_pending + actor + trusted confirmation URL, но этот безопасный доступный путь скрыт после каждой успешной проверки. Это противоречит contracts/payment-journey.md:108 и FR-034/приёмке pending. Assertion добавлен; production этим reviewer не менялся.

## Независимая проверка причинного server/worker/CD изменения

Исходники автором браузерных тестов не изменялись. Прочитаны billing/database.py, workflows/maintenance_worker.py, workflows/worker.py, db/tenant_context.py, регистрационный contract, реальные RLS regression и bash rollout/recovery tests.

- Maintenance identity: фактические session_user/current_user, row_security=on, без superuser/BYPASSRLS, разрешенный точный operation/feature context. Startup READ ONLY probe закрывает session/engine; повторная проверка при Temporal connection и в activity до действий. Обход RLS/права app роли не расширялись. Transaction-local context штатно восстанавливается после commit через существующий after_begin hook.
- Старый processing consumer удалён; maintenance регистрирует прежние workflow/activity/queue. Renewal scope не расширялся. Неожиданный normal return и exception завершают generation, старые tasks cancel+await до client.close и нового подключения. Startup/reconnect mismatch прекращает работу до poller. Отключение Temporal не блокирует независимый calendar loop после успешного startup identity gate.
- CD требует stop API+processing+maintenance до runtime up; при неуспехе recovery сначала строго останавливает processing+maintenance и не восстанавливает runtime, если stop отказал. Прочитаны тесты, реально исполняющие эти bash branches при успешном stop и nonzero stop. Не выполнялся deploy этим reviewer.
- Status GET не обращается к provider и требует invoice+operation succeeded и linked entitlement grant для оплаченного срока; historical grant не зависит от current subscription.state. Storage требует существующий storage entitlement. Без grant — service-review. Ошибки/чужой HTML/смена scope не заменяют trusted DOM; status text suppression сериализуется в реальный serverResponse. После timeout ?view=local оставляет GET-only путь без billing POST forms.

Для этих причинных изменений новых препятствий не найдено. Первоначальный product HOLD из-за отсутствующего продолжения pending закрыт ниже по реальному доказательству, а не удалением assertion.

## Окончательная матрица и закрытие замечания

Среда: Playwright1.62.1, Chromium151.0.7922.34/revision1234, WebKit26.5/revision2336. Ширины320/1280 CSS px, UTC с cookie до initial GET. Это настоящие движки Playwright; WebKit не означает проверку установленного Safari. Изолированные PostgreSQL контейнеры каждого завершенного runner удалены; cookies/CSRF/config не публиковались.

Общая команда полного прогона (для каждого ENGINE отдельно):

```sh
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=ENGINE GRAF_NODE_MODULES=airis-optout-native-deps/node_modules apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -q --tb=short --show-capture=no
```

| Движок/прогон | Реальный результат | Доказательство |
| --- | --- | --- |
| Chromium, полная матрица320/1280 | 27PASS/1FAIL;250.71сpytest. Единственный FAIL — initial page.goto5с, bridge trace пустой; сценарий платежа не начался. Это не полный зеленый прогон. | `graf-f280-payment-browser-chromium-final.log` |
| WebKit, полная матрица320/1280 | 28PASS;287.67сpytest | `graf-f280-payment-browser-webkit-final.log` |
| Chromium, pending320/1280 после исправления root | 2PASS/26deselected;32.08сpytest. Прочитан итог выполненного root прогона, собственный дубликат не запускался. | `graf-f280-pending-continuation-chromium-green.log` |
| WebKit, pending320/1280 после исправления root | 2PASS/26deselected;35.97сpytest. Прочитан итог выполненного root прогона, собственный дубликат не запускался. | `graf-f280-pending-continuation-webkit-green.log` |
| Chromium, клавиатура/фокус/темы/200% после появления вторичной кнопки | 2PASS/26deselected;29.00сpytest | `graf-f280-continuation-a11y-chromium.log` |
| WebKit, клавиатура/фокус/темы/200% после появления вторичной кнопки | 2PASS/26deselected;32.16сpytest | `graf-f280-continuation-a11y-webkit.log` |

Дополнительные выборки используют тот же runner с `-k pending` либо `-k a11y`. Составное покрытие дает успешное доказательство всех28случаев каждого движка; это не переименование Chromium27/1 в полный28PASS. После минимального исправления root повторены именно затронутые pending/доступность. Полная матрица ранее запускалась параллельно; 5сinitial navigation timeout не повторился в обоих targeted pending ширинах.

14групп на каждой ширине: automatic success, historical paid/free current subscription, pending, canceled, cancel-on-check, succeeded_refused, succeeded без grant, HTTP401/403/429/500/network/unexpected, incoming/current user/workspace/session/invoice/missing scope, lifecycle busy/reinit/hidden/visible/detached/navigation, real15s timeout, JS-off native POST303→GET, keyboard/reflow/themes, provider-unavailable. Для каждой группы обязательны real SQL assertions: по одной operation/invoice/provider create из initial fixture; нет нового payment/create/amount mutation; успешная группа получает ровно один соответствующий grant и период, другие не получают grant; recurring_allowed остаетсяFalse. Native fallback и явные GET recovery/navigation допускают ожидаемую смену документа; автоматические/ручные XHR check сохраняют исходный document и независимый runner marker.

Pending проверяет ровно6auto starts, интервалы≥10с, starts внутри60с, отсутствие сброса при swap/reinit и отсутствие дальнейших auto запросов. Ручная седьмая проверка после исчерпания лимита разрешена без перезапуска sequence. Неизменный pending действительно вставляет aria-live=off; новый provider error с тем же operation state озвучивается. Timeout проверяет активный исходный server POST до17с и15сXHR timeout, затем GET-only ?view=local без POST forms/auto и без нового provider check; SQL assertions ждут окончания исходного POST.

Замечание missing continuation закрыто: actual template теперь принимает status_result in ["unchanged", "refreshed"] только внутри прежнего can_continue_payment. Actual billing.py продолжает требовать invoice.pending, совместимую незавершенную operation, billing actor, разрешенный checkout и trusted confirmation URL; service-gap/terminal/read-only recovery идут по отдельным веткам. Отмена убирает continue, success дает «К встречам», ошибки блокируют controls и не создают денежного запроса. Последующие targeted pending проходят сохраненный RED assertion expected1 и все лимиты/финансовые assertions. Новых обходов финансовой защиты не появилось.

## Третья независимая проверка текущего результата — T031

**PASS по текущему объему F280/US3; открытых применимых замечаний0.** Проверены actual root JS/template/routes и actual worker/database/CD, которые этот reviewer не реализовывал. Успех сообщает предоставленный оплаченный доступ/его срок; ожидание дает одно понятное главное действие и безопасное вторичное продолжение уже созданного платежа; service-review не обещает выданный доступ; отмена не продолжает terminal платеж. Одновременные запросы/поздний чужой ответ/обновление сеанса/скрытие страницы не запускают новый платеж и не заменяют доверенный результат. Переходы, фокус, обе темы и отсутствие горизонтального переполнения при200% подтверждены браузером. Перенос обработчика устраняет доказанную ошибку роли без расширения прав/RLS и без новой финансовой транзакции. Условия запуска/cleanup/выпуска прочитаны отдельно; deploy этим reviewer не выполнялся.

Reviewer-owned requirements checklist повторно прочитан:17[x]/0[ ], markers не менялись; они означают качество требований, не финансовую приемку. Tasks/GitHub/commits/release не менялись.

База обзора `6dbbe450876e7b7dbdacfc3ce542322eaaff6e3c` плюс незакоммиченные изменения. После последующего commit/rebase на изменившийся master (F285 CSS/native) root обязан привязать required CI и затронутую визуальную/native матрицу к итоговому SHA; это будущая release-проверка, данный отчет ее не подтверждает.

Границы: synthetic provider transport и контролируемые named faults, не банковское зачисление/чек/возврат/последующий recurring и не человеческая конверсия. Actual hidden/context guards проверены через DOM события/метаданные, не переключением системной учетной записи. Доступность проверена DOM/клавиатурой/reflow, без утверждения о ручной приемке реальным screen reader. T011/T012/F278 и реальное состояние оплаченного пользователем счета после выпуска имеют отдельное evidence. Нельзя обещать, что каждый пользователь обязательно оплатит, по технической матрице.

## SHA256 текущих проверенных файлов

- browser test: `4adfcda44a43b6788d000eb69deefc6351636e34b3dd5da421b8190c1bfb168d`.
- Python HTTP/SQL harness: `b4cb3e1e0cc137ab2654608a899ff2f2056fa5027eed52651c54c34a3dd7d097`.
- cabinet.js: `7946ccd9b6498808034f3ac2fd102e8e0ba046bb2f6dd6c4b36bb91cf6774a7f`.
- status template после pending fix: `10d2a66d6bb2d18e4c111acae91cf47cae4893548e4919b9965592b36ee240f3`.
- billing.py: `f924f09e633b82bb66b12dc08f0ffb3259a08670891c32377f4c7d0ad3d0a1c6`.
- billing/database.py: `b75f7a35952b8725ac1017e926ddea3449f480c71de0d6b3a7f83ae49fe6197f`.
- maintenance_worker.py: `f79ba3c4ebfbed53718883c523a87877fd7a0ab0071a5cd0b9da618890fc9a1b`.
- workflow worker.py: `c6a33d8f920ca5032e0b45cb0b433fcb85a398cde76c3f5fa043a35a43a599d6`.
- cd-remote-runtime.sh: `48428a85cb326de2f6a1ebb48992eff554978ab93a997693e47a66c81519b57c`.

Node syntax и Ruff owned Python проверены без ошибок. Текущий combined coverage и прочитанный код дают PASS текущего review, но не подтверждают будущий commit/rebase/deploy.


## Адресная проверка после commit/rebase — 2026-10-03

Проверен **HEAD `e478371a3d7b40d4a9d640194a42cd36fa023703`**, master-основа `f3ec4dd95c3aa68fc7246338bd7c58908d24aee2` с F285. Перед и после исполнения source был чистым; HEAD не менялся. Только этот evidence append изменён reviewer. Production/test/Native code не менялся; коммиты/PR/GitHub этим исполнителем не изменялись. Lane: адресная повторная validation текущего high-risk F280 после изменения CSS/native основы.

### Настоящая страница результата оплаты: ширины320/1280

Для каждого ENGINE = chromium / webkit выполнено:

```sh
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=ENGINE GRAF_NODE_MODULES=airis-optout-native-deps/node_modules apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -k a11y -q --tb=short --show-capture=no
```

- Chromium: **2PASS/26deselected**,14.87сpytest,22сphase; `graf-f280-rebased-a11y-chromium.log`.
- WebKit: **2PASS/26deselected**,16.14сpytest,23сphase; `graf-f280-rebased-a11y-webkit.log`.

Обе ширины читают настоящий HTTP→ASGI→PostgreSQL status и настоящие текущие cabinet.css/cabinet.js. Проверены focus restoration после HTMX замены, переход Tab/Option+Tab к следующему actionable control, unchanged status aria-live suppression, светлая/темная темы,200%zoom без горизонтального переполнения, hidden stop без возобновления auto, сохранение document/runner marker и отрицательные SQL/provider create/grant assertions. Изолированные PostgreSQL контейнеры удалены. Полная28-case матрица не повторялась, поскольку изменены CSS/native base, а не денежная логика; ее исходные/адресные доказательства остаются выше.

### Контракты CSS/настроек/фокуса F285

```sh
cd apps/server
NODE_PATH=airis-optout-native-deps/node_modules GRAF_BROWSER=chromium uv run --extra dev --extra evaluation pytest tests/contract/test_focus_indicators_browser.py tests/contract/test_cabinet_static_assets_contract.py tests/contract/test_settings_ui_contract.py -q --tb=short
```

**102PASS**,12.43с; `graf-f280-rebased-f285-web-contracts.log`. Существующие PytestAssertRewriteWarning и StarletteDeprecationWarning не являются отказами. F285 browser entrypoint действительно исполнился, не был skipped.

Из корня checkout дополнительно:

```sh
NODE_PATH=airis-optout-native-deps/node_modules GRAF_BROWSER=webkit node apps/server/tests/browser/focus-indicators.test.cjs
NODE_PATH=airis-optout-native-deps/node_modules node apps/server/tests/browser/local-recording-focus.test.cjs
node apps/server/tests/browser/meeting-delete-focus.test.cjs
```

Все exit0/PASS: `graf-f280-rebased-f285-focus-webkit.log`, `graf-f280-rebased-local-recording-focus.log`, `graf-f280-rebased-meeting-delete-focus.log`. Общий focus-indicators проверяет actual CSS на синтетических control fixtures: один контур поля, contrast≥3:1, неизменную геометрию, отсутствие активации от focus, кнопки/ссылки/summary/checkbox/radio/range/file, обе темы и increased contrast; Chromium также forced colors. Local recording проверяет stable keyed nodes, controls/checkbox handoff, time context и removal/restoration в браузере. Meeting delete — существующий JavaScript VM contract всех направлений Tab, не отдельный real-browser proof.

### Нативные относящиеся проверки: результат с явными пропусками

Прочитана local-development guidance: автоматические тесты без установки приложения допускаются в worktree. Исполнен package unit test executable; никакой отдельный GRAF Local/Preview/Test/GRAF Dev runtime, запись, реальное уведомление или изменение системной настройки/VoiceOver не запускались.

```sh
cd apps/macos
swift test --filter 'AppControlAccessibilityTests|NativeSettingsComboBoxTests|DesktopNotificationAccessibilityTests'
```

Лог `graf-f280-rebased-native-focus.log`, exit0; build21.41с, selected test execution16.107с:

- **AppControlAccessibilityTests:25PASS/0skip/0failure** — source bindings/контейнеры informational recording не создают обычных keyboard stops; assistive targets/navigation сохранены.
- **NativeSettingsComboBoxTests:28PASS/0skip/0failure** — рисунок контура и CALayer, обе темы/Increase Contrast, неизменные bounds, keyboard/edit/commit/popup contracts.
- **DesktopNotificationAccessibilityTests:14PASS/5SKIP/0failure** — всего19зарегистрировано. Общий результат72зарегистрированных/67выполненных успешно/5SKIP/0failure, а не72PASS.

Пять пропусков явно сохраняются как **неподтвержденные**: testEscapeRestoresPreviousWindowAndCallbackReplacementKeepsItsFocus, testExplicitFocusAndKeyLoopReachCloseCheckboxAndActions, testExplicitFocusFromInactiveAppDoesNotDependOnAnotherSuiteActivation, testFocusedKeyboardEventsToggleActAndCloseWithoutGlobalEscape, testKeyboardScrollSurvivesTickAndTabReachesAction. Каждый штатно пропущен после того, как тестовая среда не подтвердила фокус контрольного обычного AppKit-окна без карточки; причина требует проверки в GRAF Dev. Это не PASS и не выданное reviewer новое исключение. Notification production/tests не входят в diff F285 master commit; изменённые F285 AppControl/ComboBox suites прошли полностью. Установленный общий GRAF Dev не менялся. Полная фактическая keyboard-проверка этих пяти notification сценариев этим отчетом не закрывается; прежнее отдельно разрешенное VoiceOver ограничение не подменяет их.

### Итог текущего SHA

**Адресная browser/CSS и измененная native часть F285 на текущем F280 SHA: PASS; новых дефектов в этом объеме0.** Полное утверждение о прохождении всех notification native сценариев недопустимо из-за5SKIP выше. Обязательные GitHub checks/final evidence commit/реальная приёмка после production остаются у root; локальные результаты не подменяют эти gates.

Проверенные SHA256 после rebase:

- cabinet.css `a261058e23eff659b2ddb47e6d48e81a23940232631fbca2488f0ad2f761e169`.
- cabinet.js `7946ccd9b6498808034f3ac2fd102e8e0ba046bb2f6dd6c4b36bb91cf6774a7f`.
- status template `10d2a66d6bb2d18e4c111acae91cf47cae4893548e4919b9965592b36ee240f3`.
- browser test `4adfcda44a43b6788d000eb69deefc6351636e34b3dd5da421b8190c1bfb168d`.
- DesktopMeetingShellView.swift `95866ab0472e1009b78ea41b4b4008b1d2f0b9245e9abe628509b91018726f62`.
- NativeSettingsComboBox.swift `a535ac52f426beb00416c5850fa2d5d7d33e2912e971fa19165184a7206cd761`.


## T035 / UI-R7 — причинный RED границы начала проверок

GO root получен после T035/#7483, уточнения FR033/034/spec/plan/contract и canon sync. Изменены только owned browser/HTTP harness и этот evidence; production JS еще прежний, SHA256 `7946ccd9b6498808034f3ac2fd102e8e0ba046bb2f6dd6c4b36bb91cf6774a7f`.

Добавлены deadline-success/deadline-pending/deadline-timeout на320/1280: первые5ответов настоящего synthetic provider GET дают pending, шестой реальный transport блокируется до явного phase marker до применения ASGI/SQL. Браузер продвигает только window clock:6начал с интервалами≥10с, шестой около50с, граница пересекается до62с. HTML/POST303/GET/CSRF/SQL не подменяются; provider release static fixture marker не содержит данных платежа и не создаёт нового API/money path. Свой nativeXHR timeout15с остается настоящим. Будущий GREEN требует принять eligible sixth success после60с, дать понятное manual waiting после sixth pending, не принять поздний ответ после собственных15с и безопасно прочитать локальный success без второго POST. Financial assertions сохраняют1operation/1invoice/1provider create, ровно соответствующий grant/period, неизменные recurring consent и отсутствие7auto.

Команда RED:

```sh
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=chromium GRAF_NODE_MODULES=airis-optout-native-deps/node_modules apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -k 'deadline-success and 320' -q --tb=short --show-capture=no
```

**1FAILED/33deselected**: actual sixth HTTP POST дошел до provider после5завершённых check; при пересечении global60с прежний JS снял aria-busy и завершил запрос, вместо сохранения его собственного15с. Assertion `60s start window must not abort sixth in-flight XHR`: expected true, actual null. Bridge errors0;6real POST303. После отказа cleanup освободил исходный provider gate, дождался настоящей ASGI/SQL transaction и удалил PostgreSQL контейнер. Лог `graf-f280-deadline-causal-red.log`. Это product causal RED, не ошибка стенда.

Ранее подтвержденная14-group/28case матрица не покрывала этот новый deadline case. Новый состав17groups/34cases на движок; до исправления root и targeted GREEN новые случаи не считаются пройденными. Итог/текущие source SHA после исправления будут добавлены отдельно. Reviewer не меняет JS/GitHub/commits.


## T035 — адресный GREEN после исправления окна старта, 2026-10-03

Измененный cabinet.js SHA256 `26fb5eab58ff2983989001f59b16ab370ea42f2fa5b49726c28190b855020ed9`; browser test `18ec6a656b9809d6ee238689b75a7df3ab965bc455bc6ec0c2cdb4b119bbf3c6`; Python bridge test `2df5de24abcb80c0ecba3f399fe02c1b5dfd25a70736774ae5f038c4ab15868d`. HEAD `e478371a3d7b40d4a9d640194a42cd36fa023703` с незафиксированными T034/T035; это source-hash evidence, а не новый committed/exact-SHA CI.

Для каждого ENGINE=chromium/webkit исполнено:

```sh
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=ENGINE GRAF_NODE_MODULES=airis-optout-native-deps/node_modules apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -k deadline -q --tb=short --show-capture=no
```

- Chromium: **6PASS/28deselected**,56.96сpytest/61сphase; `graf-f280-deadline-chromium-green.log`.
- WebKit: **6PASS/28deselected**,60.55сpytest/65сphase; `graf-f280-deadline-webkit-green.log`.

Оба браузера и ширины320/1280 проверили каждый из трех новых сценариев. Шестой настоящий POST начинает provider GET около50с; пересечение60с сохраняет aria-busy и исходный запрос. `deadline-success` принимает настоящую серверную paid-проекцию после границы; `deadline-pending` сохраняет ожидание с честным объяснением и ручным следующим шагом. `deadline-timeout` подтверждает собственный нативный XHR timeout около15реальных секунд, не заменяя его управляемыми часами страницы; завершившийся после timeout серверный успех не меняет уже восстановленную DOM-проекцию, явный GET local recovery читает оплаченный результат без нового/перекрывающего POST. Во всех случаях отсутствуют седьмой автоматический старт и новый платеж; SQL подтверждает одну operation/invoice/provider create и ожидаемое число связанных grant/period. При обычной замене сохраняются document/независимый runner markers, контекст и интервалы≥10с. Изолированные PostgreSQL контейнеры удалены.

Автор тестов не считает собственные тесты независимо проверенными. Отдельный UI-R9 idle-before60s сценарий этим GREEN не закрыт; root сообщил о нем после запуска, он требует собственной задачи и причинного RED/GREEN.


### Независимый исходный review T034

`return_design` не автор Dev изменений и прочитал фактические `infra/docker-compose.dev.yml`, новый `bootstrap_dev_database_roles.py`, оба `test_dev_maintenance_database_role.py`, общий `bootstrap_runtime_database_roles.py`, billing database guard, `infra/server/Dockerfile`, связанный build/start путь dev-harness и отчет `validation-payment-dev-role.md`. Четыре SHA256 T034 совпадают с таблицей этого отчета. Applicable source findings: **0**. Compose использует существующий migration image, присутствующий в dev-harness build и содержащий `/app/scripts`; отдельный one-shot bootstrap завершает каноническую роль после миграций до rec-maintenance. Ограниченная роль получает прежнюю каноническую проверку attributes/memberships/привилегий, row_security=on; startup READ ONLY и отказ superuser/BYPASSRLS не изменены. Helper отказывает вне development до вызова канонического bootstrap, временные600 files удаляет и восстанавливает env в finally; общий production bootstrap не изменен. Интеграционные тесты подтверждают настоящий login и прежние maintenance contexts/SELECT, а не только строку URL. Отчет автора содержит causal RED и8PASS PostgreSQL/23PASS harness; reviewer прочитал результаты, но не объявляет их собственным повторным прогоном. Installed Dev cutover и полный Compose startup не выполнены и не считаются доказанными.

### Независимый source review T035

Изменение фактически снимает только60с abort/recovery и оставляет остановку новых стартов. beforeSwap допускает in-flight ответ после60с при прежнем unblocked ledger, сохраняя все проверки identity/context/target/request; native15с timeout, hidden/departure/context failure по-прежнему блокируют ответ и требуют GET local recovery. В пределах T035 новых findings нет. Общий source convergence **HOLD**: отдельно полученный UI-R9 сценарий с пятью завершенными проверками и idle на60с требует T036. Собственные browser tests не названы независимым тестовым review.


### T035 затронутые регрессии, те же исходные SHA256

- Chromium: `-k 'pending or errors or guards or lifecycle or timeout or cancel-on-check'`, **16PASS/18deselected**,139.84сpytest/145сphase, `graf-f280-deadline-chromium-regressions.log`. Выражение также выбрало четыре уже проверенных deadline-pending/deadline-timeout case; это повтор, а не четыре дополнительных уникальных сценария.
- WebKit: `-k 'not deadline and (pending or errors or guards or lifecycle or timeout or cancel-on-check)'`, **12PASS/22deselected**,99.98сpytest/104сphase, `graf-f280-deadline-webkit-regressions.log`.

В обоих браузерах/320/1280 прошли шесть затронутых прежних групп: pending, errors, guards, lifecycle, timeout, cancel-on-check. Это реальные loopback HTTP→ASGI→PostgreSQL сценарии с fake provider transport; сохраняются SQL/new-payment-negative/context/document assertions. Оба runner завершились status=pass и удалили изолированные контейнеры. Исходный JS/browser/Python hash повторно проверен после прогонов и не изменился. Scoped diff --check PASS. UI-R9/T036 остается отдельным незакрытым случаем до новых тестов/исправления.


### T036 первый preparatory runner failure

Первый `idle-five` запуск `graf-f280-idle-five-causal-red.log`1FAIL/35deselected после остановки зависшего Node не является causal RED продукта. Пятая проверка планировалась около52.03с из-за30мс после каждого завершения, а тест продвинул часы только до52.00с и бесконечно ждал gate. Harness исправлен: ожидается actual четвертый start+10000+1мс и все gate waits теперь bounded6с. Production hash до нового прогона по-прежнему `26fb5eab58ff2983989001f59b16ab370ea42f2fa5b49726c28190b855020ed9`.

Второй preparatory runner `graf-f280-idle-five-actual-red.log`1FAIL/35deselected15.23с завершился bounded ConditionTimeout и trace содержал только первыйPOST; intended idle message assertion не достигнут. Это также не product RED. Добавлен отдельный1мс controlled clock step после завершения ответа для немедленного следующего таймера; source не изменен.


### T036 диагностика задержанного первого ответа

Дополнительные bounded preparatory runners `idle-five-causal-red-final.log`13.58с и `idle-five-causal-red-ready.log`13.07с также не достигли idle deadline assertion: ответ2 не начался даже после clock step1/50мс. `idle-five-diagnostic.log`12.86с подтвердил, что afterSwap первого ответа произошел и фактическая pending-проекция permits checks. Последний `graf-f280-idle-five-diagnostic-phase.log` упал на отдельном phase assertion, а не на intended T036: после первого pending ответа14с и продвижения часов до14.080с observed={starts:[0],finished:1,swaps:1,timeouts:0,hidden:false,busy:null,auto:true,error:false,form:billing-status-refresh,visibleMessage:null}. Bridge errors=[] и ровно1POST303. Нельзя выдавать это за product RED idle-after60s. Требуется разобраться с immediate automatic trigger после задержанного ответа прежде, чем чинить T036; possible HTMX processing-before-settle timing пока только гипотеза, нового source изменения reviewer не делал.


### Новый причинный RED: немедленный сигнал до HTMX обработки новой формы

Read-only browser instrumentation использует события `billing-status-check`, `htmx:afterProcessNode`, `htmx:afterSettle` и признак initHash в фактической bundled HTMX2.0.10. `graf-f280-slow-reply-process-diagnostic.log`: **1FAIL/35deselected**,7.29сpytest/12сphase, bridge_errors=[],1realPOST303, cleanup=isolated_container_removed. Source hash остается `26fb5eab58ff2983989001f59b16ab370ea42f2fa5b49726c28190b855020ed9`, browser test hash `d13ce7a2d2a0d211a30161cf47e844265901046b0b5621079d1075b2a8b53971`.

Observed exact causal order: first automatic trigger at1мс processed=true; pending response released14.001с; next trigger at14.001с processed=false; new form actual afterProcessNode/afterSettle only at14.021с. At14.081с: starts=[1],finished=1,swaps=1,timeouts=0,hidden=false,busy=null,auto=true,error=false,visibleMessage=null. Assertion `next due check phase` expected2starts got1. This is a new real dropped-automatic-check defect, not intended idle-after60s RED. Bundled HTMX source schedules o.tasks (including form processing) in settle callback20мс after afterSwap; controller schedules0 delay before that processing. No manual reinit or injected successful payment hides the failure. Root must task-back this newly discovered source fix before returning to T036 idle-five causal RED/GREEN. Current source convergence HOLD.
