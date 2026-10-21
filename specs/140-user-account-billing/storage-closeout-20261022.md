# F140 / T042 — сверка покупки места, 22.10.2026

Полоса: docs-only, сверка принятой реализации и issue #4897. Этот отчёт
не меняет продукт, цены, согласия, доступность оплаты или статус всей F140.
Исходная задача T042 уже отмечена `[X]` в [tasks.md](tasks.md).

## Реализация и прежнее замечание

Прежний аудит обнаружил только расчёты в `billing/storage_addons.py` без
пользовательского пути оплаты. Этот пробел устранён принятой F278:
[PR #7349](https://github.com/yshishenya/graf/pull/7349), head
`3e0a0b953c1a1df8de390094022d638a2a4d4977`, merge
`66bc074c5b39fc2ef7955a28a920785e0775f24f`, checked base
`f5cca687a06dc57ad6ccbef840a0be897eaa6336`.

- `/billing/storage/preview` создаёт неизменяемый расчёт, привязанный к
  владельцу, пространству, версии подписки, каталогу и границам услуги.
- `/billing/purchases/confirm` проверяет роль, CSRF, согласие и актуальность,
  блокирует подписку и сохраняет операцию/счёт до запроса провайдеру.
- `billing/purchases.py` рассчитывает доплату за оставшиеся оплаченные
  интервалы и сохраняет единственные неизменяемые права. Возврат браузера
  не выдаёт услугу; подтверждённый результат провайдера поступает через
  `billing/webhook_reconciliation.py` в `grant_confirmed_storage`.
- `effective_paid_storage` и `billing/maintenance.py` проецируют оплаченные
  интервалы в действующую ёмкость. Повтор не выдаёт права дважды; больший
  будущий объём сохраняется. Уменьшение, бонус и сумма ниже минимума
  откладываются; истёкшая оплаченная услуга требует финансовой сверки.

Старый каталог F140 заменён принятой F278: 5 ГБ включено, 0–99 дополнительных
пакетов по 5 ГБ. Это одна итоговая ёмкость на общей подписке. Новая цена требует
нового явного согласия плательщика, если его сохранённая цена отличается от
уже утверждённого владельцем каталога F278; прежние финансовые условия
сохраняются. Исходное описание T042 и история раннего аудита не переписываются под новый каталог.

## Проверка

На `8432f732ea2e2baeeb337e228d63f9b1e9b64d51` выполнена точная команда:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_billing_purchases.py \
  tests/unit/test_storage_packages.py \
  tests/contract/test_storage_addon.py \
  tests/integration/test_billing_purchase_storage.py \
  tests/integration/test_billing_purchase_journey.py -q
```

```text
176 passed, 0 failed, 0 skipped; 64.61 s
collection_digest=98d1c480e754d8bd0cc3bd1a7739b4fcdd09ab1b3f1c7a4add4069e7badba528
postgres_test_cleanup=isolated_container_removed
```

Проверены покупка через HTTP, конкурентные формы/бюджет, RLS, неизменность
снимков SQL, 20→100→20, границы срока, неизвестный ответ, повторы и позднее
подтверждение. Два предупреждения тестового окружения не являются отказами.

Повторный `validate-pr-checks.py` подтвердил точные SHA/base/attempt 1 #7349:
[governance-fast](https://github.com/yshishenya/graf/actions/runs/36369300302),
[macos-pr](https://github.com/yshishenya/graf/actions/runs/36369300280),
[pr-metadata](https://github.com/yshishenya/graf/actions/runs/36371745633) — PASS.

Исторический source `f9ed447e878581f7ec49003d5ab10864426071db`,
v2026.10.17.1, включает merge #7349. Его
[release-full 39020099599](https://github.com/yshishenya/graf/actions/runs/39020099599)
повторно получен: full/passed, `skipped_gates=[]`, исходные/наблюдаемые SHA
совпадают. SHA256 JSON:
`337e893757e84af97c99435d406f0ecd554933355f4577fdc3bf89715a75858f`.
Он подтверждает историческую покупку и выдачу места, но не поздние изменения
планировщика продления. Первый неуспешный Full раннего кандидата #7349
не используется как допуск.

### Поздняя правка продления и окончательный опубликованный источник

После v2026.10.17.1 [PR #7667](https://github.com/yshishenya/graf/pull/7667),
head `214ec2e327ac5a953df687dd537f0eb780651141`, merge
`945c47ce2b1b684bf78a513407667c83de50432b`, добавил `await db.flush()`
перед сохранением счёта в `billing/renewal_charge.py`. Это исправление
порядка записи финансовой операции; его нельзя считать только изменением
показа даты. Исходный отказ PostgreSQL и независимое ревью зафиксированы
в [отчёте T034](../278-production-billing/validation-renewal-order.md).

Повторная проверка 22.10 на `07a0df39a847ee184ee9f1b1b27c014d23e8dc04`:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_billing_renewal_planner_postgres.py \
  tests/unit/test_renewal_charge.py \
  tests/unit/test_billing_renewal_workflow.py -q
```

Результат: **120 passed, 0 failed, 0 skipped**, 12.11 s; два предупреждения
окружения, одноразовый контейнер удалён. Collection digest:
`808768f81c9848bf02db8f75b021d77cb7d880652bc7a01815edd0002d71a0cf`.
Настоящий PostgreSQL подтверждает сохранение operation/invoice/audit одной
транзакцией, отсутствие видимости до commit, rollback и идемпотентный повтор;
unit-набор проверяет расписание, согласие, снимки цен и неизвестный ответ.
Это не настоящие календарные платежи T026, которые остаются открытыми.

Окончательная ссылка на опубликованный продукт — **v2026.10.19.2**, source
`bfa7d71839171afd3043768ea736ce76ffa29808`, включающий merge #7667.
Повторно получен действительный артефакт `12186371339` полного
[release-full 39250886863](https://github.com/yshishenya/graf/actions/runs/39250886863):
attempt 1, full/passed, `skipped_gates=[]`, все requested/observed/component
SHA совпадают. SHA256 authoritative JSON:
`a75356f4b373020c577417d8514a75f1afde8eb01f9f88e68bae3877cb6c1453`.
Пять модулей `purchases.py`, `storage_addons.py`, `maintenance.py`,
`webhook_reconciliation.py`, **`renewal_charge.py`** и все три файла новой
проверки побайтно совпадают с этим source. Общий файл маршрутов имеет поздние
изменения и не выдаётся за побайтно неизменный. Публикация draft=false,
prerelease=false; развёртывание/допуски —
[отчёт выпуска](../../docs/deployments/2brain-rec/release-v2026.10.19.2.md).

Живые покупки и права уже подтверждены в
[отчёте F278/T031](../278-production-billing/receipt-production-closeout.md):
доплата за место 4,95 ₽, год с дополнительным пакетом 125 ₽, успешные платежи
и чеки, действующие 10 ГБ, автопродление отключено. Более поздняя сверка —
[отчёт F278/T032](../278-production-billing/notification-production-closeout.md).
Новых списаний, выпуска, развёртывания или запуска GRAF Dev этот аудит не делал.

## Граница закрытия

Подтверждён только результат F140/T042/#4897. Полная матрица уведомлений,
календарные попытки 72/48/24 часа, сопоставление банковских удержаний,
установленный GRAF Dev/VoiceOver и человеческая приёмка всей оплаты остаются
отдельными задачами. Общие F140/F278 не закрываются. Закрытие #4897 допустимо
после принятия документальной сверки, трёх обязательных проверок её точного SHA
и повторной live-проверки фактического комментария issue.
