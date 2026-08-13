# Запуск биллинга GRAF

Этот runbook описывает только контролируемое включение биллинга Feature 140.
Он не разрешает production rollout сам по себе: до всех обязательных подписей
checkout, сохранение способа оплаты и автоматическое продление остаются
`default-off`. Возврат выполняется оператором только во внешнем кабинете
YooKassa; GRAF не создаёт refund mutation и не показывает клиенту результат
возврата.

## 0. Неизменяемые границы

- Merchant/site для production: `https://rec.2brain.pro`, YooKassa shopId
  `1430118`, API protocol — YooKassa HTTP API. ShopId не является секретом;
  API/webhook/referral secrets никогда не записываются в Git, логи или evidence.
- Production return URL — `https://rec.2brain.pro`; production webhook endpoint —
  `https://rec.2brain.pro:8443/api/v1/billing/providers/yookassa/webhook/production`;
  test window uses the bounded `/webhook/test` route on the same listener.
  Test shop `1436758` проверяется на той же установке, но только в отдельном
  последовательном окне: explicit `TWOBRAIN_BILLING_YOOKASSA_ENVIRONMENT=test`,
  test `SHOP_ID` и test API/webhook secret files задаются одновременно, а
  checkout и provider observation останавливаются перед возвратом к
  `production`/`1430118`. Два магазина не работают одновременно на одном
  runtime. Перед переключением оператор убеждается, что нет pending webhook или
  provider operations от test окна; тестовые платежи и receipts не считаются
  production evidence.
- YooKassa API/webhook и referral secrets монтируются server-side через Docker
  secrets в `rec-api`, `rec-processing-worker` и `rec-maintenance`, потому что
  последние два запускают reconciliation/renewal/notification workflows.
  `rec-web`, desktop и браузер credentials не получают. Перед canary
  проверяются owner, permissions `0600`, rotation date и отсутствие
  placeholder/default values; deploy script fail-closed проверяет rendered
  Compose paths, чтобы enabled checkout не получил пустой placeholder.
- Evidence содержит только local `evidence_ref`, exact release SHA, bounded
  outcome, timestamp, role, severity/owner/deadline и hash evidence-файла. В нём
  не должно быть provider/payment/refund/invoice ID, card data, email клиента,
  webhook/CSV body, secret, audio или transcript.
- Manual full/partial refund, receipt composition and provider-side accounting
  остаются merchant-cabinet/back-office процессом. GRAF только читает
  webhook/GET/list/registry и создаёт metadata-only reconciliation gap при
  несовпадении.

### Обязательная edge-защита webhook

До canary reverse proxy должен иметь отдельный bounded location только для
`/api/v1/billing/providers/yookassa/webhook/test` и
`/api/v1/billing/providers/yookassa/webhook/production`: только TLS, лимит
тела `256k`, rate limit, `proxy_request_buffering off`, CIDR allowlist YooKassa
(`185.71.76.0/27`, `185.71.77.0/27`, `77.75.153.0/25`, `77.75.156.11`,
`77.75.156.35`, `77.75.154.128/25`, `2a02:5180::/32`) и overwrite заголовка
`X-Billing-Webhook-Secret` из защищённого operator-managed include. Клиентский
заголовок нельзя проксировать. Общий webhook location должен быть закрыт или
защищён тем же allowlist. Нужны `nginx -t`, отрицательный synthetic probe с
неразрешённого адреса и подтверждённая доставка YooKassa; отсутствие любого
доказательства оставляет T080/T078 blocked.

### Текущая topology-проверка production

На `2brain.dev` внешний `443` сейчас принимает общий Nginx `stream` SNI-router
и передаёт HTTPS virtual hosts на `127.0.0.1:10444`. Установленный Nginx
`1.24.0` не разрешает `server_name` внутри `stream`-server, поэтому нельзя
безопасно включить `proxy_protocol` только для `rec.2brain.pro`: глобальное
включение затронет остальные SNI-сервисы и Xray upstream. Попытка добавить
такую конфигурацию должна завершаться `nginx -t` с автоматическим rollback;
нельзя оставлять частичную allowlist или прокидывать секрет через общий
location.

Выбран безопасный вариант без нового сервера/IP: YooKassa официально принимает
HTTPS callback на `8443`, поэтому `rec.2brain.pro:8443` терминирует TLS напрямую
в отдельном Nginx listener. Он сохраняет реальный source IP, применяет provider
CIDR allowlist и server-side overwrite `X-Billing-Webhook-Secret`, не меняя
общий SNI-router сайта на `443`. Репозиторный installer
`infra/scripts/install-billing-webhook-edge.sh` обязан сделать backup,
`nginx -t`, reload, negative probe и automatic rollback. До успешного
controlled provider delivery checkout остаётся fail-closed.

## 1. Перед canary: checklist

### Окружение и release

- [ ] Проверены target hostname, environment label, migration head и exact
  `release_sha`; checkout пока disabled.
- [ ] Test и production YooKassa shop/credentials разделены; rotation и
  access log зафиксированы metadata-only.
- [ ] Backup/restore reference и migration rollback rehearsal существуют;
  reverse proxy принимает webhook только по TLS и опубликованному YooKassa
  source-network allowlist. Приложение требует `X-Billing-Webhook-Secret`.
- [ ] В production secret mounts присутствуют только у server-side ролей
  `rec-api`, `rec-processing-worker`, `rec-maintenance`; прямой публичный
  доступ к backend webhook закрыт.
- [ ] Есть on-call owner, incident owner, deadline, emergency-stop operator и
  независимый approver (four-eyes); canary cohort allowlisted и ограничен.

### Product, finance/legal and safety

- [ ] `product`: утверждены `Free`/Trial/`Личный`, unlimited paid core,
  storage ladder, fair-use и cohort copy.
- [ ] `finance/accounting`: подтверждены COGS, gross-margin floor, 54-ФЗ/VAT,
  receipt lines, ledger retention и source-retention policy.
- [ ] `legal`: опубликованы offer, recurring consent, immediate-Free/no-grace
  wording и email-only external refund boundary.
- [ ] `security/qa`: пройдены RLS, CSRF, redaction, provider boundary,
  accessibility, no-refund-mutation scan и test-shop matrix.
- [ ] YooKassa capability evidence имеет отдельные rows для initial payment,
  saved method, recurring, authoritative GET, webhook, receipt, full/partial
  refund observation и renewal failure→Free. Zero-amount binding — `pass`
  только при явном подтверждении shop; иначе остаётся `blocked`.
- [ ] Продуктовые и внешние gates (JTBD/WTP/COGS, landing/usability, live
  security/privacy) закрыты или явно помечены как blocking; отсутствие gate
  возвращает readiness в fail-closed.

## 2. Capability evidence packet

Создайте одну metadata-only запись на capability. Шаблон нельзя заполнять
реальными идентификаторами или payload:

```text
evidence_ref: <local-random-ref>
release_sha: <40-char-git-sha>
environment: test-shop | controlled-real-shop
shop_ref: test-shop-<ticket> | production-shop-1430118
observed_at_utc: <RFC3339>
operator_role: <role>
approver_role: <independent role>
capability: <allowlisted capability name>
result: pass | fail | blocked | not_tested
source: contract | provider_test_shop | controlled_real_shop | registry_poll
safe_observation: <bounded outcome, no IDs/payload>
revalidation_due_utc: <RFC3339>
incident_ref: <empty or metadata-only ref>
```

Capability row становится `stale` при смене SHA, shop, secret, схемы,
receipt/VAT/price, provider contract, cohort или при незакрытом incident.
Истёкшая/отсутствующая row блокирует checkout. `zero_amount_binding=blocked`
не является ошибкой: self-service replacement должен оставаться выключенным.

## 3. Test-shop procedure

1. На той же production-системе создать synthetic owner/workspace для
   последовательного test-shop окна. Это не отдельный параллельный runtime:
   перед переключением остановить checkout/observation, убедиться, что нет
   незавершённых provider-операций, заменить explicit environment/shop/secret
   configuration согласованным набором и проверить config snapshot. Не смешивать
   test payment data с production customer cohort; после теста удалить synthetic
   данные по runbook и вернуть production configuration до любого публичного
   smoke.
2. На exact SHA выполнить:

   ```sh
   .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
   cd apps/server
   uv run pytest tests/contract/test_billing_launch_gates.py -q
   uv run pytest tests/e2e/test_billing_test_shop.py -q
   cd ../..
   infra/scripts/ci-local.sh --fast
   ```

   Для реального provider окна оператор заранее кладёт test API и webhook
   secrets в отдельные защищённые файлы (например,
   `secrets/twobrain_yookassa_test_secret` и
   `secrets/twobrain_yookassa_test_webhook_secret`) и временно указывает их
   через `TWOBRAIN_BILLING_YOOKASSA_SECRET_FILE` и
   `TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE`. Значения не передаются в
   чат и не попадают в Git.

3. Включить checkout только на короткое окно test shop и проверить monthly,
   annual, saved-method, decline, timeout/unknown, duplicate/out-of-order
   webhook, authoritative GET и exact receipt. Return URL/webhook без
   authenticated GET не даёт entitlement.
4. Проверить one-attempt renewal success, confirmed failure→immediate Free,
   unknown→blocked pay-again, late-success/refusal precedence, storage
   admission, unlimited paid core и no-grace/no-retry.
5. В merchant cabinet test shop (не в GRAF) выполнить full и partial refund,
   если capability поддерживает это. В GRAF проверить только read-only
   webhook/GET/list/registry convergence и отсутствие refund API mutation.
6. Заполнить capability rows, metrics snapshot, stop rehearsal и независимую
   review. После окна вернуть checkout disabled, восстановить
   `TWOBRAIN_BILLING_YOOKASSA_ENVIRONMENT=production`, shop `1430118` и
   production secret files, перезапустить сервисы, проверить health/readiness и
   только затем считать систему готовой к production canary.

Любой mismatch amount/currency/shop/environment, duplicate grant, missing
receipt, unexpected refund call, leaked secret или customer content — `fail`,
немедленный stop и incident metadata-only. Нельзя продолжать по принципу
"почти прошло".

## 4. Controlled real-shop canary

Real shop запускается только после раздела 5. Один allowlisted synthetic или
consented canary identity, один base plan и один add-on; расширение cohort
запрещено до отдельного решения. Перед включением:

```sh
infra/scripts/cd-remote.sh --dry-run
```

`--execute` допустим только после независимой release authorization. В окне
canary оператор:

1. сверяет exact SHA, backup/migration evidence, secret mounts, webhook TLS,
   read-only reconciliation и emergency-stop;
2. проводит base + one add-on payment и подтверждает authenticated GET,
   webhook, exact receipt, entitlement и storage projection;
3. выполняет заранее одобренный renewal failure→immediate Free без retry/grace,
   затем проверяет late-outcome precedence и отсутствие второй charge key;
4. выполняет manual full и partial refund во внешнем merchant cabinet;
5. подтверждает в GRAF только observed refund receipt/list/registry convergence,
   gap ownership, отсутствие customer-facing refund status/notification и ноль
   refund mutation calls;
6. сохраняет metadata-only packet, metrics snapshot и двухличное решение.

Любая незакрытая gap, неподтверждённая capability, нарушение redaction или
расхождение ledger останавливает rollout и оставляет checkout disabled.

## 5. Four-eyes sign-off

Подпись относится только к указанному SHA, shop, cohort и сроку. Исполнитель и
approver должны быть разными людьми; запись без `evidence_ref` не считается
подписанной.

| Gate | Approver role | Status | Evidence ref | Valid until / revalidation trigger | Date + initials |
| --- | --- | --- | --- | --- | --- |
| Product, plan/storage/fair-use/cohort | `product` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Finance/accounting, COGS/VAT/54-ФЗ/receipt/retention | `finance/accounting` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Legal, offer/recurring/immediate-Free/refund boundary | `legal` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Security/QA, RLS/CSRF/redaction/accessibility/rollback | `security/qa` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Infrastructure/on-call, backup/TLS/secrets/stop path | `infrastructure/on-call` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Release decision, executor ≠ independent approver | `release owner + independent approver` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |

Все `pending`/`fail`/`stale` записи блокируют enablement. Изменение цены,
receipt/VAT, schema, provider capability, secret, cohort, deployment SHA или
unresolved incident требует нового цикла sign-off.

## 6. Emergency stop and rollback

### Немедленная остановка

В защищённой deployment-конфигурации выставить:

```text
TWOBRAIN_BILLING_CHECKOUT_ENABLED=false
TWOBRAIN_BILLING_EMERGENCY_STOP=true
```

Затем прогнать `infra/scripts/cd-remote.sh --dry-run`; execute — только с
отдельной authorization. Stop обязан блокировать checkout, zero-binding и
automatic renewal mutations, но сохранять cancel/refusal, payment history,
support email, Record/Stop, deletion и export. Не удалять ledger, не отзывать
историческое entitlement задним числом и не запускать refund из GRAF.

### Причины обязательного stop

- двойное списание или duplicate entitlement;
- mismatch amount/currency/shop/environment или missing receipt;
- unknown outcome, который не восстанавливается bounded GET/list/poll;
- RLS/CSRF/redaction/secret-boundary нарушение;
- storage over-admission, потеря deletion gate или registry gap без owner/deadline;
- неожиданный provider refund mutation или customer-facing refund state;
- любой security/privacy/accessibility gate, ставший stale.

### Rollback и восстановление

1. Заморозить cohort и создать metadata-only incident с `incident_ref`,
   severity, owner, deadline и exact SHA.
2. Сохранить backup и registry/reconciliation snapshot; не изменять исходный
   ledger вручную.
3. Выполнить проверку совместимости миграций и restore rehearsal. Для отката
   приложения использовать [общий rollback runbook](../deployments/2brain-rec/rollback-runbook.md);
   downgrade схемы без утверждённого backup запрещён.
4. После исправления повторить test-shop stop/recovery, capability evidence и
   все обязательные sign-offs. Только затем можно вернуть
   `TWOBRAIN_BILLING_EMERGENCY_STOP=false` и открыть новый короткий rollout.

## 7. После canary и revalidation

- Сохранить exact SHA, capability packet, test/real scope, backup/migration
  refs, metrics snapshot, incident list и решение о расширении cohort.
- Закрывать только подтверждённые gaps; unresolved gaps остаются owned
  metadata-only records с owner/deadline и не маскируются как `pass`.
- Повторно проверить stop path после любой ротации secret, deploy, миграции,
  изменения цены/receipt/VAT или YooKassa capability.
- При отсутствии любой подписи checkout и automatic renewal остаются выключены.
