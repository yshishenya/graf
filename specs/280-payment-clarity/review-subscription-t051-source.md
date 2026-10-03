# F280 T051 — независимая проверка исходников

2026-10-04. **PASS статической проверки исходников T051. Critical/high/medium/low findings: 0/0/0/0.** Это не окончательный PASS реализации, браузерных/DB проверок или выпуска: свежие результаты остаются отдельным условием.

Проверяющий не автор реализации. Прочитаны уточнённые FR-042/044, T051/plan/contract/quickstart и независимый requirements PASS14/0; фактический diff, полный GET/шаблон, общая денежная политика, её callers, renewal charge и snapshot. Применимые AGENTS/guidance ранее прочитаны. Записан только этот отчёт; код/тесты/spec/tasks/checklist/Git/GitHub/выпуск не изменялись. Проверки не запускались, финансовые действия не выполнялись.

## Соответствие общей политике

`billing_subscription_page` читает строго исходный `CHECKOUT_BLOCKING_STATES`, без локального добавления `provider_key_expired`. В запросе сохраняются workspace predicate, JOIN invoice→operation и поиск всех видов также без subscription. Сохранено исключение prepared scheduled renewal без provider_id: это подготовленный расчёт, а не блокирующий отправленный invoice.

Общий helper `_blocking_payment_operation_query` и его callers прочитаны: обзор оплаты, trial/выбор тарифа, хранение, GET оформления, POST запуска/продолжения оформления используют прежний набор и prepared исключение. Прямые ограничения early confirm и отмены будущего объёма также используют прежний набор. Все эти функции unchanged. `blocks_new_checkout` по-прежнему проверяет исходный set; T051 не добавляет новую денежную политику и не разрешает запрещённое состояние.

`provider_key_expired` удалён также из дополнительного resolution fence подготовки GET quote и из `payment_unresolved` шаблона. Это снимает самостоятельный view-only запрет. Существующие pending/unknown/unknown_pending resolution и обнаруженный blocking invoice всё ещё подавляют новые/manual/early/resume действия и подготовку quote. Современный manual_resolution входит в общий набор: истечение ключа не делает его доступным для новой оплаты. INITIAL_CHECKOUT_OBSERVATION_EXPIRED не добавлен; прежний доступный checkout после окончания наблюдения сохраняется без обещания отмены старого провайдерного платежа.

`_resume_renewal_snapshot` неизменён и проверен вместе с обоими callers: GET подготовки и POST resume validation. Он читает renewal текущего paid-through и требует допустимую `next_renewal_attempt`; любое состояние вне canceled/succeeded/scheduled считается unresolved и возвращает недоступный snapshot. Поэтому удаление одного expired resolution fence не отменяет существующую проверку реального незавершённого renewal. Resume POST по-прежнему проверяет сессию/owner/tenant, версию, карту, согласие и актуальный immutable quote/snapshot. При наличии другого blocking invoice GET до snapshot не доходит.

## Восстановление карты и правдивые слова

Причина `method_required` может быть сохранена как до dispatch, так и после него; T051 не выводит отправку из этой причины. Последняя проверенная редакция сообщает **«Результат платежа на [сумма] еще не подтвержден»**, либо такое же нейтральное сообщение без суммы. Нет утверждения, что платёж уже отправлен или не будет списан.

Внутри pending ветки сохранена основная ссылка проверки существующего invoice/поддержки. Одновременно при method_required показывается прежний `_renewal_notice` со штатным безопасным GET `/billing/payment-method`. Карта не получает нового денежного действия. Новый/manual/early/resume путь остаётся закрытым, поскольку pending conditions прежние. Other receipt-contact notice с checkout URL по-прежнему не становится доступным внутри pending ветки.

Отмена сохраняет прежнюю защищённую форму и область допустимости. Последствие при unresolved теперь нейтральное **«Этот платеж продолжит проверяться»**; его отправка не выводится из manual_resolution. Сохранение оплаченного доступа и отсутствие возврата правдивы и unchanged. Включение продления остаётся отдельным непринятым required согласием, точной суммой/попыткой/картой и hidden CSRF/version/quote. Early preview/error/receipt путь сохраняется.

Название native details — **«Способ оплаты, условия и история»**. Внутри прежние полные сроки/время/зона, период/цена/карта и история. Нет новой вложенности или UI/API/JS компонента; обычное краткое представление не меняется.

## Scope и fingerprints последней редакции

HEAD при проверке: `b3b3ac1c63f256c8d6b6d39710ed7406f6e90ecf`; diff незакоммичен, заключение привязано к байтам. Рабочий production diff относительно HEAD — только GET route и шаблон: route2+/2−, template5+/4−. CSS, финансовые модули/handlers, API/БД/миграции/JS/конфигурация/цены/зависимости не изменены.

Независимое сравнение AST и полного исходного текста `billing.py`: 85 функций в обеих версиях, изменена только `billing_subscription_page`; остальные84 совпадают, новых/удалённых функций нет. Это включает common blocking helper, snapshot и все денежные POST обработчики.

| Файл | SHA-256 | Git blob |
| --- | --- | --- |
| `cabinet/web_routes/billing.py` | `b2ea985f0eb6726d160d4fd211620aa1f94871e7d41e3676179b336ad3d7b048` | `451f0ecbc7b7f11355adc542742a26b3aebbbe2e` |
| `cabinet/pages/billing_subscription_content.html` | `3788ae2d22f8e414d5714b90c8c1bd4285cda38b44d5a04d8d28825d6f8c2541` | `55934f188ef6e08c338621e136418fbbb9e711e3` |
| `cabinet/static/cabinet/cabinet.css` | `24074ca3bc01545a1ab794c8df222e36622fa1cbe171a6a327dfe840fe200a64` | `bbcda962e18df9c8a2aa20092236569dadcf43c3` |
| `billing/operations.py` | `f121492003d242d148703b559692c201571aec18bd792dae87878c524a4a844a` | `889bdc29f284d68d77d2d217c27bf8904da7c3f6` |

## Оставшиеся условия

Оба ранее подтверждённых P2 устранены в проверенном исходном коде: самостоятельный expired fence убран, safe card recovery сохранён и отправка не приписывается method_required. Исправлений исходников по этому обзору не требуется.

Фактическая проверка исполнения T051 должна независимо подтвердить expired/observation разрешение, modern manual_resolution запрет, method_required до/после dispatch с/без provider_id, neutral pending/cancel wording, отсутствие новых operation/invoice/grant/quote/provider calls при блокере, полный затронутый DB файл и свежие оба браузера. Предыдущие source fingerprints/template обзоры теперь исторические; свежий браузерный review нужен для новой строки/ссылки/названия. Текущие незавершённые прогоны не названы успешными.

Следом обязательны convergence, новое exact-SHA PR evidence/common validator, обычное слияние, отдельный frozen release-full/GO/CD/runtime/tag/Release/publication и честный rollback status. Этот source PASS не снимает требования выпуска и не подтверждает реальную карту/банк/чек/возврат/автосписание, человеческую приёмку F278 либо рост конверсии. Новые реальные денежные действия не создавались.
