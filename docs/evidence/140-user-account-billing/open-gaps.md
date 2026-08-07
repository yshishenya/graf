# Открытые launch-gates Feature 140

Статус на 2026-08-07: public launch **BLOCKED**. Это не продуктовый refund
case и не обещание пользователю; документ служит только внутренним
metadata-only реестром незакрытых доказательств.

Автономная реализация account-close/source lifecycle, add-on/payment-method
transitions и billing primitives закрыта задачами T038, T039, T042, T043,
T051 и частью T053/T075–T078. Refund webhook backstop теперь проходит
bounded cursor pagination YooKassa (до 20 страниц, с защитой от повторного
cursor), но полный registry import и monitoring для этих задач ещё не доказаны.
Агрегированные admin metrics и отдельный readiness diagnostic уже доступны,
но live dashboard/alert routing и stop-all-charges drill остаются открытыми.
Остаются
evidence/gates: moderated
accessibility/usability and landing review, live security/RLS review, product-
market segment/JTBD, WTP/COGS, upgrade-copy and final cross-artifact closeout
(T079–T085, T087).

Checkout, binding и renewal mutation нельзя включать, пока владельцы Product,
Finance/Accounting, Legal, Security и QA не внесут версии решений и exact-SHA
evidence в launch runbook.

## Повторный runtime-аудит 2026-08-07

После повторной проверки выявлены дополнительные блокеры, которые нельзя
заменять contract/unit evidence:

- initial checkout теперь имеет bounded provider-GET backstop для сохранённого
  `provider_id`; если POST в YooKassa завершился таймаутом до сохранения этого
  ID, операция всё ещё остаётся `unknown` и требует ручного gap resolution;
- reconciler создаёт и обслуживает только заранее существующие `renewal`
  operations: автоматическое создание и списание renewal до публичного запуска
  не доказано;
- receipt payload/contact snapshot не подключены к YooKassa payment request;
  нужен merchant test-shop canary с проверкой 54-ФЗ и чека;
- processing free-cap и paid-unlimited helpers ещё не подключены к admission
  путям ingest/processing, поэтому публичный checkout должен оставаться
  выключенным до runtime evidence;
- storage admission подключён к публикации canonical playback, но нужен
  PostgreSQL/RLS прогон с истёкшим trial/paid cutoff и replacement/deletion
  сценариями;
- proxy-level allowlist для webhook описан в runbook, но его фактическая
  конфигурация и live RLS не предъявлены.
