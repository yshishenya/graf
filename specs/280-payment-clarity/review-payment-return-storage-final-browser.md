# F280 — независимый итоговый обзор хранения и браузера

Дата: 2026-10-03. Проверяющий: release_prepare_readonly. Lane: high-risk-product. Объект: окончательные T042/T043 и регрессия общего пути после оплаты, до нового коммита и production. Навык code-reviewer применён к локальным изменениям. Исходники, задачи, checklist, Git и GitHub не изменялись; записан только этот отчёт.

## Замечания и результат

**SOURCE/TEST PASS. Critical: 0; high: 0; исправимых medium: 0.** Достаточных оснований для нового изменения реализации в проверенных границах не найдено. Это допуск по исходникам и автоматизированным проверкам; не подтверждение выпуска или личной приёмки.

Два исходных дефекта T042/T043 были действительными: новая покупка хранилища не показывала оплаченные интервалы, а штатное историческое succeeded_projected не распознавалось как применение. Независимо прочитаны их исправления, реальные отрицательные проверки и причинный результат: 13 failed / 19 passed до исправления → 32 passed после него. История отказа сохранена в `graf-f280-storage-red.log`, результат — в `graf-f280-storage-green.log`.

В первом общем прогоне было 155 passed / 2 failed. Проверен весь дополнительный diff [test_billing_return.py](../../apps/server/tests/integration/test_billing_return.py#L289): проверка теперь требует две области role=status, ровно одну видимую и обязательно скрытое сообщение контроллера. Она не убирает доступность, финансовые проверки или сценарии failed/canceled. Финальный набор: **157 passed, failed 0, skipped 0**, 94.51с, изолированный контейнер удалён. Старый отказ `graf-f280-storage-regression.log` сохранён; новый результат — `graf-f280-storage-regression-final.log`. Контрольная сумма файла этого теста: `8cbc3adc32069cdb0eb32732ac996beb991032f666e627f22d29640f41b4c046`.

## Прочитанные доказательства применения

[Маршрут результата](../../apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py#L2050) выбирает invoice и operation одновременно по workspace и их связи. Новый payment_applied требует успешного invoice, подходящего завершённого состояния и отсутствия service_resolution/reconciliation_detail. Заголовок, сообщение и основное действие в [шаблоне](../../apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html) используют одно вычисленное доказательство. Действительный data-billing-state сохраняется.

T042: все права хранилища фильтруются одновременно по invoice и workspace, упорядочены по starts_at/ends_at/id. Отдельные интервалы разделены `; `; промежуток между ними не объявлен оплаченным. Исторический срок не зависит от нынешних capacity/state/paid_through. Отсутствующие и чужие права успехом не считаются.

T043: прочитан [штатный projector](../../apps/server/src/twobrain_rec_server/billing/maintenance.py#L57), который применяет объём и меняет конкретную связанную операцию на succeeded_projected в существующей транзакции. Маршрут принимает этот признак только для storage_upgrade, старой схемы и допустимого snapshot: известный целочисленный объём, месяц/год, обе даты с часовым поясом и start < end. Просто succeeded или общий текущий объём не доказывают покупку. Схема2 с projected и другой вид операции не принимаются. Reconciler, его финансовые переходы и миграции этим исправлением не изменены.

[32 проверки маршрута и PostgreSQL](../../apps/server/tests/integration/test_billing_clarity.py#L397) включают web, desktop, local и desktop_local; один и раздельные исторические интервалы; отсутствие/чужой invoice/чужой tenant; pending invoice; неприменённую старую операцию; malformed, missing, naive, zero и reversed dates; неверные cycle/capacity; reconciliation/service markers. Отдельный сценарий действительно запускает прежний projector, затем меняет/истекает текущую подписку и проверяет исторический успех. Провайдер на GET запрещён проверкой, сравниваются значения всех billing-таблиц и workspace_subscriptions до/после. Новых списаний, invoice, operation, grants или перепроекции от GET нет.

## Браузер, согласие и обработка

Независимо прочитаны [контроллер](../../apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js#L1930), [настоящий bridge браузер→ASGI→PostgreSQL](../../apps/server/tests/contract/test_billing_payment_return_browser.py) и существующие сценарии. Свежий результат: Chromium **56 passed / 233.93с**, WebKit **56 passed / 254.07с**, ширины320/1280, failed0/skipped0; оба контейнера удалены. SHA256 журналов сверены с машинным результатом. В проверках успех означает ровно один связанный grant; recurring_consent=False при оформлении сохраняет recurring_allowed=False. Сам browser56 не является отдельной браузерной проверкой интервалов хранилища: их доказательство — 32 route/PG сценария выше.

Лимиты по-прежнему ограничивают начала шестью попытками за60с, интервал между началами минимум10с, каждый запрос имеет собственные15с. После ожидания остаются честная ручная проверка и защищённый GET; успех не показывает продолжение оплаты. Поздний ответ, смена user/workspace/session/invoice и заменённая страница не дают старому HTML изменить чужой контекст. Фокус и раскрытые сведения сохраняются перед swap, сообщение после последней шестой попытки не скрывается из-за отдельной паузы ручной кнопки.

Проверены прежние [maintenance worker](../../apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py), [проверка ограниченной DB role](../../apps/server/src/twobrain_rec_server/billing/database.py), [cadence300с](../../apps/server/src/twobrain_rec_server/workflows/worker.py#L604) и [штатный CD](../../infra/scripts/cd-remote-runtime.sh#L1163). Обработчик той же billing reconciliation queue остаётся в maintenance; processing больше не создаёт её consumer. Реальные login/current role, row_security, запрет superuser/BYPASSRLS и допустимый контекст проверяются до обработки и при reconnect. CD останавливает старые API/processing/maintenance перед запуском новых. T042/T043 эти ограничения не меняют.

## Привязка к исходникам и границы

Независимо пересчитаны все шесть SHA256; они совпали с freeze, началом и концом обоих браузерных прогонов и текущими файлами:

| Файл | SHA256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `1444c3ac7cda96d8f5468236f172fc89a0e961b752104afc3faf4e1f34e13a05` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` | `a33426dee1cb1ea7d12d94d1752a46ebac91dd073e37dd9754f773dbfc4b27c1` |
| `apps/server/tests/browser/billing-payment-return.test.cjs` | `129b83a264f1c35b4f7a0fc1a9602eb4bc4231e1d7f8baa8717946ef8b01bf64` |
| `apps/server/tests/contract/test_billing_payment_return_browser.py` | `6718e667e9a831e98471b5186f31a54c036603fa306352f69406a08f66d62716` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `0af48ddb2d628815dc0626d4cbd7e7a84328b3b2e37512ac2daaff09fdb787d5` |
| `apps/server/tests/integration/test_billing_clarity.py` | `0d34024119097888e56b81370d6c6acd8b93783d6aaffffb4c0e160501cf3a45` |

Сопутствующие доказательства: [storage](validation-payment-return-storage.md), [browser](validation-payment-return-storage-browser.md). Указанные имена журналов и `graf-f280-storage-final-result.json` обозначают локальные временные артефакты, не публичные ссылки. В этом отчёте нет абсолютных локальных путей, идентификаторов реального платежа или персональных данных.

Новые exact-SHA CI, обычное слияние, frozen release-full, решение GO, CD и чтение существующего платежа в production остаются обязательными следующими действиями оператора. Личная сессия пользователя, реальные автосписания, банковское зачисление, возврат, человеческая понятность и конверсия этим обзором не доказаны. Для подтверждения оплаченного существующего invoice требуется отдельное production доказательство штатного grant и сохранённого false согласия. T011/T012 и F278 не закрываются данным PASS.
