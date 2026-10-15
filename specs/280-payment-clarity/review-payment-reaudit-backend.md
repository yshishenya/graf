# Независимая проверка восстановления оплаты и достоверности чека

Дата: 2026-10-16, Europe/Istanbul. Область: FR-053/FR-054 повторной проверки
F280. Lane: `high-risk-product`, существующий Spec Kit срез. Проверяющий
реализовал тесты в двух перечисленных ниже файлах, но не изменял продуктовую
реализацию. После исправления проведена отдельная проверка продуктового diff.

## Вердикт

**PASS для проверенного backend-среза.** Новых применимых замечаний
CRITICAL/HIGH/MEDIUM в итоговом diff не найдено. Это заключение о коде и
синтетических HTTP/PostgreSQL проверках; выпуск, производство, реальные деньги,
чек провайдера и установленное приложение требуют собственного evidence.

База рабочей ветки: `0a235f175bed306324064b68a7c1e38bffa322b0`. Проверен
незакоммиченный diff; результат не выдается за CI или evidence будущего SHA.

## Проверенные свойства

- `_hosted_checkout_url` разрешает сохраненный адрес только связанным
  invoice/operation текущего пространства с `pending/provider_pending`,
  поддерживаемым видом операции и допустимым HTTPS адресом провайдера.
  Initial checkout требует `provider_id`; историческое отсутствие actor
  разрешено только для initial checkout. Storage требует точного actor.
- `_recover_checkout_operation` читает счет с явными ограничениями пространства
  и operation ID. Неподходящее состояние ведет на локальный статус; отсутствующий,
  чужой или отвязанный счет не возвращает пользователя к провайдеру.
- Один предикат применяется в трех POST start ветках: повтор существующего
  ключа, незавершенный блокер и winner после `IntegrityError`. GET checkout,
  GET status и hosted ветки POST continue согласованы с ним.
- Проверки владельца, пространства, CSRF, разрешенного оформления и actor
  остаются на вызывающих маршрутах. Восстановление same-key остается раньше
  изменяемых promo/quote проверок и не переписывает исходное согласие.
- Новый помощник не делает commit, не создает платеж, не меняет финансовые
  записи и не добавляет блокировки строк. Порядок существующих блокировок
  не изменен; новая выборка счета не использует `FOR UPDATE`.
- `_initial_checkout_can_continue` и `_checkout_invoice_can_continue` сохраняют
  прежний отдельный legacy no-provider dispatch с тем же ключом, ограничением
  срока, суммы/валюты и новой схемы. Восстановление hosted URL не вводит
  дополнительную проверку истечения ключа и не меняет
  `CHECKOUT_BLOCKING_STATES`/политику observation expiry.
- Утверждение «Оплата остается подтвержденной» теперь требует
  `invoice.status == "succeeded"`. Paid service-gap сохраняет достоверное
  сообщение о деньгах и видимое предупреждение об услуге. Проверки receipt-only
  полномочий, CSRF и частоты запросов не менялись.

## Причинный RED и полные GREEN проверки

Новые тесты добавлены только в
`apps/server/tests/integration/test_billing_clarity.py` и
`apps/server/tests/contract/test_billing_ui.py` с использованием прежних fixtures
и финансового snapshot helper. После получения RED продукт исправил другой
исполнитель. После GREEN тесты не ослаблялись.

| Прогон | Результат | Содержание |
|---|---|---|
| Причинный targeted RED | 50 failed, 21 passed, 0 skipped; 48.97 с | 40 неправильных start redirect, пять ложных paid notice и пять неправильных GET continuation |
| Два полных измененных файла | 289 passed, 0 skipped; 142.30 с | Вся прежняя матрица и новые регрессии |
| Три полных соседних файла | 250 passed, 0 skipped; 391.72 с | Return, purchase journey, promo refresh |

В новых 55 start случаях проверены все три ветки, pending reuse, terminal и
несовместимые состояния, истекший ключ, отсутствующий/чужой/отвязанный счет,
actor и отсутствие provider ID. Снимки всех billing таблиц и подписки остаются
неизменными; owner fixture запрещает provider create. Winner проверяется через
один внедренный `IntegrityError` в первый lookup существующего ключа, затем
второй lookup читает настоящий сохраненный объект PostgreSQL после rollback.
Отдельные семь receipt-query случаев проверяют пять неоплаченных состояний и
два paid состояния, включая service-gap.

Команды из корня репозитория:

```sh
GRAF_TEST_WORKERS=2 apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_billing_clarity.py tests/contract/test_billing_ui.py \
  -q --tb=short --show-capture=no

GRAF_TEST_WORKERS=2 apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_billing_return.py \
  tests/integration/test_billing_purchase_journey.py \
  tests/integration/test_billing_promo_refresh.py \
  -q --tb=short --show-capture=no
```

Оба прогона использовали штатную одноразовую PostgreSQL; оба контейнера удалены
штатно. Непосредственно перед проверками на Mac было более 100 ГБ свободно.
`ruff check` двух измененных тестовых файлов и `git diff --check` прошли.
В каждом прогоне два существующих предупреждения инфраструктуры тестирования:
pytest assert rewriting и deprecated Starlette/httpx adapter.

## Отпечатки итоговых файлов

Отпечатки сверены после обоих полных прогонов, совпадение подтверждено.

| Файл | SHA256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `30530765973b9f2073a2a08dcc005943d9b2ae21d613f297667ebc57902b5623` |
| `apps/server/tests/integration/test_billing_clarity.py` | `de7729f3a775501e64b48baf5f1239a6f11b9d0b4c7fa7c807f7987c5a10aaa7` |
| `apps/server/tests/contract/test_billing_ui.py` | `b3eeea724d36c56657ef0d67892111c15e84a22c62158c02506a382684501358` |

На causal RED `billing.py` имел SHA256
`5a9b6356db31644fb3bbfd1c523d64f3c1ccac10c25e9d80cf981c093b9d254e`.
Отпечатки тестов между RED и GREEN не менялись.

## Локальные журналы

Журналы находятся в игнорируемом `.dev/`, зависимости и промежуточные сборки
в evidence не копировались. Для переноса результатов достаточно этого отчета,
текстовых журналов и контрольных сумм:

| Журнал | SHA256 |
|---|---|
| `.dev/payment-reaudit-targeted-red.log` | `a3424a8bd7a43c5f2cb56900b35d814a13aa548e275972eaf3ec86083c8cb8e8` |
| `.dev/payment-reaudit-full-green.log` | `fa862f1ccbd2c12faec9267e9c111b2bf3adcd041642703d2c1d22aae6f87f45` |
| `.dev/payment-reaudit-preserved-guards-green.log` | `6426d3b117fab8162421561807d776716df6de935e5dbf1d02628fc9dfdfddcc` |

Сумма двух полных непересекающихся наборов этого исполнителя: **539 passed**.
Повторенный соседним оператором набор не добавлен к этому числу. Browser,
другие unit/security наборы и release evidence выполняют соответствующие
исполнители отдельно.
