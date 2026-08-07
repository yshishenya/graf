# Открытые launch-gates Feature 140

Статус на 2026-08-08: public launch **BLOCKED**. Это не продуктовый refund
case и не обещание пользователю; документ служит только внутренним
metadata-only реестром незакрытых доказательств.

Автономная реализация account-close/source lifecycle, playback quota admission,
add-on/payment-method transitions и billing primitives закрыта задачами T029,
T036, T038, T039, T042, T043, T047, T051, T053 и T075–T077. Refund webhook
backstop проходит bounded cursor pagination YooKassa (до 20 страниц, с защитой
от повторного cursor); payments/refunds registry теперь импортируется только
раздельными metadata-only наборами с completeness hash и gap ownership.
Агрегированные admin metrics, maintenance workflows и отдельный readiness
diagnostic доступны, но live dashboard/alert routing и stop-all-charges drill
остаются операционными launch-gates T078.
Операционный canary runbook и quickstart теперь описывают разделение test/prod,
capability evidence, four-eyes sign-off, emergency stop и rollback; фактический
canary/sign-off остаётся T078. Автоматическая часть T079 усилилась
recoverable promo error, keyboard-safe copy и focus/reflow checks; T080 получил
provider-boundary forbidden-field guard для browser PostHog, provider-ID
path validation и bounded analytics ingress. Остаются
evidence/gates: moderated accessibility/usability и landing review, live
security/RLS review, product-market segment/JTBD, WTP/COGS, upgrade-copy и
финальный cross-artifact closeout (T078–T085, T087).

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
- receipt registration truth теперь сохраняется монотонно и metadata-only,
  а receipt contact snapshot/54-ФЗ поведение всё ещё требует merchant
  test-shop canary;
- processing free-cap и paid-unlimited helpers подключены к admission и
  проходят focused regression; public checkout всё равно остаётся выключенным
  до controlled canary и finance/legal/security/QA sign-off;
- storage admission подключён к публикации canonical playback, но нужен
  PostgreSQL/RLS прогон с истёкшим trial/paid cutoff и replacement/deletion
  сценариями;
- proxy-level allowlist для webhook описан в runbook, но его фактическая
  конфигурация и live RLS не предъявлены.

## Ремедиация 2026-08-08

- Исправлены локальные P1 hardening gaps: chunked webhook body bounded до
  `256 KiB`, startup-проверка непустых provider/webhook/referral secrets и
  support email, write-RLS для глобального billing catalog, явные промо/карта
  действия и безопасные reconciliation labels.
- Не закрыты без внешнего доступа: live proxy/firewall/TLS и PostgreSQL RLS
  probe, test-shop/real-shop canary, merchant/finance/legal/security/QA
  sign-offs, moderated usability/landing, интервью/WTP/usage/COGS и финальный
  Spec Kit closeout. Поэтому public launch остаётся **BLOCKED**.
