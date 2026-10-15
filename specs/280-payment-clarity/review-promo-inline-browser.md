# Независимая браузерная проверка промокода F280

Дата: 2026-10-02. Срез T026–T028, FR024–030/SC010–012. Режим: независимое чтение и синтетический браузер/HTTP/SQL. Применён навык code-reviewer. В репозитории изменён только этот отчёт.

## Итог: PASS независимого браузерного ревью; выпускная приёмка открыта

H1 обнаружено независимым браузерным запуском, исправлено основным исполнителем и повторно проверено. Последующий разбор matrix-2 выявил M2; оно исправлено и закрыто новым независимым настоящим браузерным запуском ниже. Применимых незакрытых critical/high/medium замечаний нет. Прежние узкие Chromium/WebKit доказательства хранения False остаются достоверными в своём срезе. Это заключение не заменяет окончательную полную матрицу, проверки GitHub, выпуск и установленный production.

## H1 — закрыто после исправления

Первый независимый Chromium запуск на320px с хранилищем blocked и выбором автопродления False дал1 FAIL,27 deselected: после первого Apply новый DOM показывал True, `data-renewal-ready` отсутствовало. Настоящий ASGI путь: GET checkout200 → POST preview303 → GET checkout200; bridge errors0. Повторное временное наблюдение и просмотр изображения подтвердили дефект.

Причина: чтение `sessionStorage.getItem` в `initCabinetRail` без обработки исключения прекращало общую инициализацию до обработчиков автопродления и afterSwap. Основной исполнитель ограничил чтение/запись try/catch, сохранив адаптивный исходный вид и управление навигацией. Проверено непосредственно в [cabinet.js](../../apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js).

Повторная исходная команда прошла1/1,27 deselected; новый независимый WebKit запуск того же пути с дополнительным визуальным наблюдением также прошёл1/1. Исключение хранилища теперь не прекращает инициализацию. Автопродление False остаётся False через7 inline обновлений. H1 закрыто; исходный FAIL сохранён в доказательствах и не выдан за PASS.

## Собственные выполненные проверки

- Chromium, настоящий существующий runner с одноразовым PostgreSQL/ASGI: `GRAF_PROMO_BROWSER=1 GRAF_BROWSER=chromium apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -k inline-basic-off-blocked-verified-320 -q --tb=short --show-capture=no` —1 PASS,27 deselected,36.69с; runner46с, isolated cleanup PASS.
- WebKit: та же исходная параметризованная проверка, движок `webkit`. Временная копия существующего браузерного скрипта добавляет только наблюдение/снимки/визуальные и клавиатурные assertions. Сервер, HTML и SQL остаются настоящими; нет setContent/макета страницы. Результат1 PASS,27 deselected,34.39с; runner43с, isolated cleanup PASS.
- Apply валидного синтетического кода; month по Enter; два ошибочных кода подряд; исправление по Enter; year; очистка +Apply. Проверены7 обновлений, неизменность window/document,0 запросов навигации основного документа,0 новых записей истории. Два обычных reload сохраняют month; final reload сохраняет year. Адрес содержит только cycle.
- Новый проверенный итог/период/кнопка оплаты согласованы; оферта после каждого обновления снята. False сохраняется даже через ответы без checkbox. При настоящем полном reload с заблокированным storage ожидается исходное True: это ранее оговорённая граница, а не перенос False в тот же документ.
- Ошибка синтетического неизвестного кода показывает «Промокод не распознан», field `aria-invalid=true`, `aria-describedby=billing-checkout-error`, role alert. Доступны исправление/очистка; ошибочный код не показывает форму денежного действия. Недоступный acceptance campaign по коду сохраняет понятную формулировку «Промокод сейчас недоступен. Уберите его или введите другой»; отдельный тип запрета аккаунта и result `account_unavailable` не подсказывают обходить запрет удалением кода.
- Фокус после обновления остаётся на связанном input/Apply/cycle. В WebKit Option-Tab из ошибочного поля достигает Apply. После clearing details раскрыт, поле и Apply видимы. Успешный status показывает новую сумму, ошибка не выдается за успешную скидку.
- WebKit320px: обе темы,100%/200% для двух ошибок и очистки. Проверены отсутствие горизонтального переполнения документа, размещение input/Apply/денежного действия в видимой ширине и достижимость прокруткой.12 изображений сохранены; независимо просмотрены неизвестный код в обеих темах, cleared light100%, cleared dark200%.
- Существующий fixture подтверждает0 POST start,0 invoice/operation/redemption/reservation/grant и0 вызовов провайдера в этих предварительных действиях. Одноразовая среда удалена.
- `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и `git diff --check` —PASS.

## Проверка обработчиков и ошибок чтением

BeforeRequest отключает controls и снимает оферту после формирования параметров HTMX. BeforeSwap проверяет200, текущий живой target, identity user/workspace/session и ожидаемый checkout main. Несоответствующий ответ не заменяет расчёт. AfterSwap возвращает логичный фокус, replaceState изменяет только cycle, а общая повторная инициализация восстанавливает выбор. AfterRequest/sendError/timeout/swapError снимают busy, сообщают причину и оставляют денежное действие закрытым до нового успешного расчёта. Перед submit денежной формы действует дополнительная проверка checking/recovery. Таймаут запроса15000ms, двойное действие dropped.

Проверен установленный HTMX2.0.10 и официальные первичные материалы `htmx.org/events/`, `w3.org/WAI/WCAG22/Understanding/status-messages.html`. Готовность состояния проверяется после afterSettle; содержимое status/alert доступно через программные роли. Реальный диктор отдельно не запускался.

## Дополнительные доказательства другого исполнителя

Прочитаны результаты accessibility16 PASS Chromium и16 PASS WebKit (`graf-f280-inline-accessibility-chromium-tests-final.log`, `graf-f280-inline-accessibility-webkit-tests-final.log`) и205 PASS HTTP/domain (`graf-f280-inline-http-domain2-tests-final.log`). Их не считаю своими независимыми запусками. Ранние broad логи содержали6 FAIL на устаревшем ожидании числа обычных redirect после перевода preview вXHR; актуальные tests теперь различают1 обычный redirect и1 preview update. Окончательная полная матрица ещё должна быть получена основным исполнителем; ранний FAIL не засчитывается как успешный полный прогон.

## Привязка к источникам

- `apps/server/src/twobrain_rec_server/billing/purchases.py` SHA256 `d03b4743c9ef29d12025e149b130260d3b2fd335a6eb4557cd063bccc9cfc66c`
- `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` SHA256 `ba7db4c90ec19f85e114a276e3983619cf8e6321e45f1e992ab831532c5b75b8`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` SHA256 `ea894567e3a61b17917b5668297db539cb930d2277cb911c4a4bdc8ec1022a15`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html` SHA256 `4b17d26ee11577eeb30a6d7788d4a8eafabfa1649a4dcef2613d34ebd10db3b0`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/htmx-2.0.10.min.js` SHA256 `71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de`

## Артефакты

- `graf-f280-independent-browser-chromium.log` SHA256 `258587b8c437da61e3da26e378d424395cde828e660b6761917a004223808e24`
- `graf-f280-independent-browser-debug.log` SHA256 `08750283f4e4271ecbe60d2115c0f16a1a0e0f30d65d4d582d296380f238cf84`
- `graf-f280-independent-browser-false-failure.png` SHA256 `e3f54f4e0bc9e3ce7810f6369c45178a196f1569e107d6b7183afa67d4cd4b83`
- `graf-f280-independent-browser-chromium-green.log` SHA256 `b1957f3d23a30f0faceffedf2b78cb254e6539131ae288c8d8d406f85f90906e`
- `graf-f280-independent-browser-webkit-visual.log` SHA256 `f21bb13f2490f8533d3720ac64aedaa438e6dffd7db6ca321af88777534aa291`
- `graf-f280-independent-browser-debug.cjs` SHA256 `5dccb9c653bb77a42970ae7cf938764ecdfdd6f30dd4c68c5a8aef609c7d43fa`
- `graf-f280-independent-browser-webkit-cleared-dark-1.png` SHA256 `464106354d88885e8f18ac5352e884d8cc8de6a2b256c5096ce386108191d1b0`
- `graf-f280-independent-browser-webkit-cleared-dark-2.png` SHA256 `5d2528a2b7221e61aa76f845e7506b573e90c9e2edb97a0cbfaa7b210cca353a`
- `graf-f280-independent-browser-webkit-cleared-light-1.png` SHA256 `f5a5bb75660bfae523fa93fb5c1807f039a261e0a8cc994afe5302c6b37983bb`
- `graf-f280-independent-browser-webkit-cleared-light-2.png` SHA256 `49723e6956190d617413b9a615c10a0df12e628978f25fe9514fc14a576108c7`
- `graf-f280-independent-browser-webkit-error-AB-dark-1.png` SHA256 `ec5ed1988c0ac02c71c2992bd801783b11783fb55a2061af735ee26a1f6b32e2`
- `graf-f280-independent-browser-webkit-error-AB-dark-2.png` SHA256 `ce8f13cf191212fbfcce6aff7b6810af2c7fbfeaf0ed43dbd8e66d1e837fd8fa`
- `graf-f280-independent-browser-webkit-error-AB-light-1.png` SHA256 `293f4c7a7dd2768a6713e436aca20a61efacfb150f28250d7b2701107c624f69`
- `graf-f280-independent-browser-webkit-error-AB-light-2.png` SHA256 `e56a3ef0de7972445b1139ca37977405a804c37e2efde5b2135da7d01f47af15`
- `graf-f280-independent-browser-webkit-error-SYNTH-UNKNOWN-dark-1.png` SHA256 `5354522d024f28ebf85628866346adc669df263811316662375a98c2809eefb3`
- `graf-f280-independent-browser-webkit-error-SYNTH-UNKNOWN-dark-2.png` SHA256 `fa1f0a3cbb47e3d8fc00a3bf5e15bfae1e221aaa79b4df65a109281885d50ed6`
- `graf-f280-independent-browser-webkit-error-SYNTH-UNKNOWN-light-1.png` SHA256 `5acdfc3dc15a72d6045e8abd2249fddd3239102a943ac8d7ad00b7dcdcc8e3cf`
- `graf-f280-independent-browser-webkit-error-SYNTH-UNKNOWN-light-2.png` SHA256 `8f72b1cd2c16c5cc2971d6c212b332633dea28bfa48d2db8e31e7408296573a5`

## Границы заключения

Настоящие промокоды, карта и деньги не использованы. Production, провайдер, GitHub, код, тесты, tasks и checklists этим reviewer не изменены. Сетевые/timeout/context failure матрица и native fallback проверены чтением, но не повторены этим reviewer в браузере: они остаются частью полной проверки другого исполнителя. Это не реальная привязка карты, списание, чек, банк, возврат, человеческая приёмка, испытание диктором или доказательство конверсии. Обещание, что каждый пользователь обязательно оплатит, не следует из этих результатов.

## Исторический дополнительный разбор matrix-2: M2 до исправления

Прочитаны `graf-f280-inline-chromium-2-tests-final.log` (detached late FAIL в обеих ширинах) и `graf-f280-inline-webkit-2-tests-final.log` (также timeout FAIL в обеих ширинах). Эти результаты не являются полным PASS.

### M2 — detached запрос может оставить общую защёлку запроса

Текущий продукт слушает завершение на body через события HTMX. Установленный HTMX2.0.10 собирает предков исходного элемента в onload (`const t=In(r)`), когда элемент уже может быть удалён. При detached source события beforeSwap/afterRequest происходят на удалённом элементе; подключённого предка для переотправки может не быть. В таком случае `billingPreviewRequest` остаётся прежним, и следующий beforeRequest отменяется глобальной проверкой. Даже если точная причина зависания тестового маркера loadend ещё не установлена, этот путь неполной очистки следует непосредственно из продукта/HTMX.

Рекомендация основному исполнителю: при beforeRequest добавить однократный прямой `xhr.addEventListener('loadend', ...)`, вызывающий существующий `finishBillingPreview(state, true)` только пока текущий pointer равен этому state. Нормальный afterSwap уже очистит pointer до loadend, поэтому новый достоверный расчёт не получит ложный recovery. Если исходный page detached, существующая finish-функция сначала очистит pointer и затем выйдет, не изменяя новый DOM/согласия/контекст. Не перезаписывать onload/ontimeout HTMX и не вставлять late HTML через прямой listener.

Тестовая наблюдательная beforeRequest подписка имеет `{once:true}` без фильтра формы; её стоит ограничить `elt.id==='billing-promo-preview'`, иначе посторонний запрос может забрать наблюдение. Маркер loadend сам по себе не доказывает очистку продуктового pointer; после завершения полезно проверить принятие следующего корректного запроса в новом допустимом контексте. Исходный FAIL требует повторной проверки и не объявлен исправленным.

### WebKit timeout: пока не доказан отдельный дефект продукта

Текущие test файлы изменены уже после matrix-2: cjs23:34:13, Python bridge23:34:53, log23:32:40 Europe/Istanbul. Сейчас bridge задерживает третий POST preview17с, а Playwright пропускает настоящий сетевой запрос через continue. Значит, matrix-2 не проверяла этот актуальный путь; старый timeout мог относиться к остановленной interception, при которой WebKit иначе запускает часы XHR. Не следует добавлять новый общий JS таймер только по этому старому результату. Сначала нужен свежий WebKit узкий timeout на реальной медленной loopback сети, с `xhr.timeout`/фактической продолжительностью/событиями и recovery. Продукт задаёт15000ms, installed HTMX присваивает `g.timeout=C.timeout` и публикует afterRequest/timeout. Прямой loadend cleanup усиливает освобождение состояния, но сам по себе не исправляет отсутствие native timeout.

В этом дополнительном разборе не изменены source/tests, новые браузерные матрицы не запускались.

## Закрытие M2 после исправления

Основной исполнитель добавил прямой однократный native `xhr.loadend` с вызовом существующей guard-функции. Source `cabinet.js` SHA256 `95f5d619f7cab0d70e1b604f0c6fccaba5ce47b91c756ae4fc9073ac75baeb34` проверен чтением, синтаксисом и настоящим Chromium. Он очищает только совпавший state; disconnected page не изменяется. При обычном успешном afterSwap pointer уже пуст, поэтому loadend не создаёт ложную ошибку. Новый таймер не добавлен.

Независимая исходная команда: `GRAF_PROMO_BROWSER=1 GRAF_BROWSER=chromium apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -k inline-guards-320 -q --tb=short --show-capture=no` —1 PASS,27 deselected,13.69с; runner18с, isolated cleanup PASS.

Проверка удерживает настоящий ответ preview, заменяет прежний main свежим наблюдённым серверным HTML в том же документе и включает установленный HTMX через process. После завершения late XHR проверяет неизменность quote/replacement и запускает **следующую успешную проверку**. Inline helper подтверждает прежние document/window markers,0 запросов навигации основного документа,0 новых записей истории, достоверную сумму/период, снятую оферту. Fixture подтверждает0 денежных действий и финансовых записей. Это проверка освобождения pointer без reload, а не сброс всего состояния полной навигацией.

Test worker отдельно имеет RED этого точного fresh-retry критерия: `graf-f280-inline-detached-retry-red-tests-final.log` показал TimeoutError при попытке следующего запроса на прежнем коде. После исправления прочитаны `graf-f280-inline-chromium-boundary4-tests-final.log` и `graf-f280-inline-webkit-boundary4-tests-final.log`: по4 PASS (timeout/guards на320/1280),0 FAIL. Их не считаю своими независимыми запусками. Наблюдательная beforeRequest подписка теперь фильтрует billing-promo-preview. Обе конкретные причины прежней matrix-2 перепроверены; полный финальный28-case прогон остаётся ответственностью основного исполнителя.

Текущие SHA256 тестов при независимом M2 GREEN:

- `apps/server/tests/browser/billing-promo-refresh.test.cjs`: `e180e2c4fe54748e9ed20cf70849d2883b470af3ac4a5f65f50a054298ee82e5`
- `apps/server/tests/contract/test_billing_promo_refresh_browser.py`: `5ab899f007db8023b7d51906484cb04b79e757138ce20c0e572a7a8dcf22442b`

- Artifact `graf-f280-independent-browser-detached-green.log` SHA256 `8327cbbba50ba6fe4df930509f83ed570fcba50cc24912d0b7078d0a135ca767`
- Artifact `graf-f280-inline-detached-retry-red-tests-final.log` SHA256 `4cbb4bc4042dff43abe7fbe6f1068a5464f98b542fd201086268755f7610054e`
- Artifact `graf-f280-inline-chromium-boundary4-tests-final.log` SHA256 `5b31676093fc2fcef5a7d51f75bfe0aaff6a5a21d461fa313cbc8f2826995418`
- Artifact `graf-f280-inline-webkit-boundary4-tests-final.log` SHA256 `4f9b2cd79e6a866bb136989f29ee6aa4bb3febc512031192d7e5f45e59cee34a`
