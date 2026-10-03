# F280 — браузерная проверка возврата оплаты

Дата: 2026-10-03. Владелец: независимый browser tests worker. Scope: новые `apps/server/tests/browser/billing-payment-return.test.cjs` и `apps/server/tests/contract/test_billing_payment_return_browser.py`; production не изменялся этим исполнителем.

## RED до изменения JS/шаблона

Команда:

```sh
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=chromium GRAF_NODE_MODULES=/tmp/airis-optout-native-deps/node_modules apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -k 'success and 320' -q --tb=short --show-capture=no
```

Результат: **1 FAILED / 1 deselected**, Chromium320. Настоящий HTTP→ASGI→PostgreSQL и синтетический transport ЮKassa; initial checkout создан существующим штатным тестовым helper, invoice/operation по одной, grant0 до возврата. Новый денежный POST запрещен мостом; browser expected automatic success, но locator «Оплачено» исчерпал5с (`automatic-success`, `TimeoutError`). Все24 записанных HTTP запросов были GET200; refresh POST0, bridge errors0. Это ожидаемый RED поведения отсутствующей автопроверки; production JS/template еще прежние. Root уже отдельно менял server routes после собственного server RED.

Локальный log: `/tmp/graf-f280-payment-browser-red.log` (только синтетический trace/stage/count; без session/cookie/payload). Duration23с с подготовкой; call9.72с включает запуск браузера и timeout5с.

Исходники перед RED:

- cabinet.js SHA256 `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34`.
- billing_operation_status_content.html SHA256 `9b428a4474355dc5357393773ad31fb382ecb90980f26c4e93d9f18c9737c0a9`.

Первый подготовительный запуск остановился на дублированном именованном cookie TestClient (`CookieConflict`) до браузера. Helper выбора корректного issued cookie исправлен; этот сбой не считается RED продукта. Еще один запуск с неверным префиксом пути не собрал тесты; runner требует `tests/...` из apps/server, исправленная команда указана выше.

CHK001 повторно подтвержден в reviewer-owned отчете: только связанный grant/исторический срок, без зависимости от current active subscription; requirements PASS17/0. Окончательный analyze и issue sync перед test GO подтвердил root. RED не является GREEN, выпуском либо финансовой приемкой.

## Промежуточная проверка контроллера и исправления стенда

Реальный Chromium320 → HTTP → ASGI → PostgreSQL: `-k '320 and (errors or guards or lifecycle or timeout)'` дал **4passed/24deselected** после серверного исправления local recovery. Лог `/tmp/graf-f280-payment-browser-controller-debug2.log`,55.37сpytest. HTTP401/403/429/500, network/unexpected HTML, incoming/current user/workspace/session/invoice/missing scope, busy/double trigger/reinit, hidden/visible, detached target, actual navigation и настоящий XHR timeout15с с исходным серверным POST, продолжающим жить до17с. Recovery GET не начинает второй POST. Cookie/timezone/CSRF и HTML настоящие; provider synthetic; новых create/operation/invoice/grants нет.

Предыдущие полные прогоны12failed/16passed не являются GREEN. Исправлены именно ошибки стенда: page-level route.continue пропускал нижний счётчик; глобальный locator видел меню «К встречам»; фокусируемый элемент — main, не h1; result provider error называется unavailable; Playwright routing не перехватывает следующий URL redirect, поэтому named faults теперь fetch настоящие POST303→GET до изменения ответа; timeout assertions ждут окончания исходного server thread перед проверкой SQL. Таймер0 может исполниться даже при paused clock, поэтому fault/hold устанавливаются до initial GET, а current-scope меняется после первого доказанного check. Нельзя трактовать preparatory failures как дефекты продукта или ослаблять финансовые assertions.

## Независимая находка и ее закрытие: вторичное продолжение pending

Первоначальный **HOLD**, подтверждено actual DOM RED3октября: `/tmp/graf-f280-payment-browser-continuation-red.log`; команда того же runner с `-k 'pending and 320'`,1FAILED/27deselected. Настоящий provider GET успешно оставляет этот же payment pending, локальные invoice/operation pending/provider_pending. В карточке отсутствует «Вернуться к оплате» (expected1, actual0). Новой денежной операции нет.

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
GRAF_PAYMENT_RETURN_BROWSER=1 GRAF_BROWSER=ENGINE GRAF_NODE_MODULES=/tmp/airis-optout-native-deps/node_modules apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_payment_return_browser.py -q --tb=short --show-capture=no
```

| Движок/прогон | Реальный результат | Доказательство |
| --- | --- | --- |
| Chromium, полная матрица320/1280 | 27PASS/1FAIL;250.71сpytest. Единственный FAIL — initial page.goto5с, bridge trace пустой; сценарий платежа не начался. Это не полный зеленый прогон. | `/tmp/graf-f280-payment-browser-chromium-final.log` |
| WebKit, полная матрица320/1280 | 28PASS;287.67сpytest | `/tmp/graf-f280-payment-browser-webkit-final.log` |
| Chromium, pending320/1280 после исправления root | 2PASS/26deselected;32.08сpytest. Прочитан итог выполненного root прогона, собственный дубликат не запускался. | `/tmp/graf-f280-pending-continuation-chromium-green.log` |
| WebKit, pending320/1280 после исправления root | 2PASS/26deselected;35.97сpytest. Прочитан итог выполненного root прогона, собственный дубликат не запускался. | `/tmp/graf-f280-pending-continuation-webkit-green.log` |
| Chromium, клавиатура/фокус/темы/200% после появления вторичной кнопки | 2PASS/26deselected;29.00сpytest | `/tmp/graf-f280-continuation-a11y-chromium.log` |
| WebKit, клавиатура/фокус/темы/200% после появления вторичной кнопки | 2PASS/26deselected;32.16сpytest | `/tmp/graf-f280-continuation-a11y-webkit.log` |

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
