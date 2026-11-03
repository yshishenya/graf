# Независимая проверка реализации F140/T074 — 31.10.2026

**SCOPED PASS: P1=0, P2=0, HIGH=0, CRITICAL=0 для текущих байтов.**
Ранее найденное P2 с обходом проверок Settings устранено и подтверждено
отдельным отказом до исправления. Прежний незаписанный результат другого
процесса не использован как PASS и не заменяет эту проверку.

Основа `c9a85917307a4388d534c61bc98e036a18d1245e`, ветка
`codex/140-renewal-decline-validation`, плюс текущий diff. Полоса —
`active Spec Kit slice`, test-only; T074/#4928. Проверен окончательный source
SHA-256 `10d881940882f02122add9daf840c7cc6a8d84d79b946bd0a8d6ad55d5d231ca`.

Изменён только этот отчёт. Контрольные списки, код, требования, задачи,
Git/GitHub, CI, приложение и данные рецензент не менял. Тесты и сборки не
запускал; новых агентов не запускал. Чужие изменения сохранены.

## Прочитанные источники и область

Прочитан весь `test_billing_renewal_planner_postgres.py`, текущий diff и
дополнения spec/plan/quickstart/tasks, validation, прежний requirements report
с уточнением сеанса. Повторно сверены настоящие planner/charge, определение
трёх окон, ключи операций, `record_renewal_decline`, enqueue уведомления и
сохранение очереди, binding ответа провайдера, создание YooKassaClient и его
реальный HTTP-путь. Проверены billing-валидаторы Settings, BaseSettings
configuration, конструктор sessionmaker и ограниченный транспорт fixture.
Применён порядок code-reviewer; результат ограничен этим тестовым изменением.

## Почему проверки содержательны

| Критерий | Реализация и проверенный смысл |
| --- | --- |
| Три отказа и окна | Новый случай проходит `attempt=1,2,3` в `paid_through−72/48/24h` через настоящие `plan_due_renewals` и `charge_renewal_operation`. Подтверждаются сохранённый номер попытки, canceled у operation/invoice и отсутствие планирования через 23h после каждого отказа. После третьего это `paid_through−1h`, четвёртая попытка не создаётся. |
| Сохранение результата | Планирование явно commit; последующие handler, повтор и чтение идут в отдельных `_session(factory)`/AsyncSession. Charge сам commit сохраняемый canceled. Снимок не берётся из прежней карты ORM. Новый физический socket не заявляется. |
| Повтор без второго POST | Для каждой сохранённой operation handler вызывается повторно; результат равен первому. Суммарное число HTTP POST и число уникальных Idempotence-Key после каждого шага равны 1/2/3. Это одновременно проверяет отсутствие повторной отправки и разные ключи трёх разрешённых попыток. |
| Оплаченный доступ и согласие | После каждого отказа paid_through точно равен исходному, plan_code/state остаются personal, полные снимки grants и payment methods неизменны. После первых двух consent=true и версия authority прежняя; после третьего consent=false, версия возрастает ровно на1. |
| Уведомление | Из нового сеанса читается 1/2/3 записей renewal_attempt_failed с уникальными event_id, pending и attempts=0. Повтор handler уже выполнен до проверки числа записей. Настоящий enqueue записывает очередь, отправитель почты не запускается. |
| Настоящие переходы | Подменён только внешний HTTP-транспорт. Planner, charge, проверка binding и record_renewal_decline не заменены; canceled не устанавливается тестом напрямую. Начальная синтетическая успешная покупка остаётся предусловием прежней fixture, а не доказательством реального платежа. |

Production charge ставит schema-2 shop/environment в снимок перед POST,
получает synthetic canceled и проверяет provider ID, сумму/валюту, shop,
environment, workspace/operation/invoice metadata до принятия отказа.
Транспорт проверяет реальный POST `/v3/payments`, сумму и сохранённый метод;
ответ переносит фактическую metadata запроса. Отсутствующая или неправильная
привязка не превращается в принятый отказ: действующий валидатор её отклоняет.
Это положительный сценарий валидного ответа, не полная отрицательная матрица
провайдера. Старые unknown/sent случаи сохранены и вошли в профиль.

## P2 Settings: исправление подтверждено

В текущем новом тесте **нет `Settings.model_copy(update=...)`**. Выполняется
обычный `Settings(_env_file=None, **{**case.settings.model_dump(), ...})`:
копируются значения, затем весь набор заново проходит конструктор и
валидаторы Pydantic. Исходная fixture задаёт env=test и одноразовую БД;
платёжные значения явно заменены синтетическими, включая отдельные файлы
provider/webhook/referral, режим0600, HTTPS URL и безопасный support email.

`config.py:640–733` требует HTTPS, shop/секрет, webhook, а при checkout ещё
public URL/referral/support/receipt параметры. Отдельный RED-журнал и XML
`settings-red` показывают **1 FAIL / 0 SKIP,3.39s** при обычном конструкторе
без webhook secret: `ValidationError`, `enabled billing observation requires a
webhook secret file`. Таким образом обход был реальным недостатком подготовки,
а не косметической заменой метода. В окончательном source нужные синтетические
параметры заданы, валидаторы не monkeypatch и не отключены; итоговый профиль
после этого исправления успешен. Открытого P2 по Settings больше нет.

## Запрет внешних действий

Прежняя fixture до любых операций запрещает обе httpx.send. Новое разрешение
async send проверяет **и** host `api.yookassa.test`, **и** тождество фактического
transport существующему MockTransport, затем вызывает исходный send только
на нём. Синхронный send остаётся запрещён. Настоящий YooKassaClient получает
этот transport; фиксированные тестовые URL и секреты не относятся к магазину.
Внутренние результаты не подставляются. Нет реального provider HTTP, почтовой
отправки, Dev, миграций или изменений производственных функций.

Fixture проверяет maintenance-role без superuser/bypass RLS/владения таблицей
и row_security=on. Это сохраняет существующий уровень проверки, но один
сценарий не доказывает всю матрицу изоляции и гонок полномочий F140.

## Проверка журналов и XML

Результаты прочитаны, не перезапущены. XML разобраны по паре
`classname/name`, включая параметры; ошибок/пропусков и повторяющихся ID нет,
кроме намеренного отказа в settings-red.

| Набор | PASS | FAIL | SKIP | Граница |
| --- | ---: | ---: | ---: | --- |
| baseline | 116 | 0 | 0 | До нового случая, 5.04s |
| new | 1 | 0 | 0 | Прежний вариант до исправления Settings; не финальная приёмка байтов |
| profile | 117 | 0 | 0 | Прежний вариант до исправления Settings; не финальная приёмка байтов |
| settings-red | 0 | 1 | 0 | Причинная проверка обычного конструктора без обязательного значения |
| settings-profile | **117** | **0** | **0** | Окончательное исправление, **4.93s** |

Множество финальных ID содержит **все116 исходных**, утраченных0,
дублированных0; дополнительный ровно1:
`tests.integration.test_billing_renewal_planner_postgres.test_three_confirmed_declines_persist_without_duplicate_charges_or_lost_paid_term`.
Прежний profile и settings-profile имеют одинаковые117 ID. Финальный журнал
содержит collection_count=117, result=pass и штатное удаление одноразового
контейнера. Один прежний PytestAssertRewriteWarning сохранён и не выдан за FAIL.

## Оставшиеся границы

Весь reviewer-owned `renewal-decline.md` перечитан после проверки:
**6 отмечены / 0 открыты**, не менялся. Это не закрывает58 общих открытых
пунктов F140. Полная T074/#4928 по-прежнему `[ ]`: настоящий test shop,
остальная FR-090/T078/F278 T019/T026 и денежная/ручная/выпускная приёмка
не подтверждаются MockTransport. Окончание paid period, неизвестные исходы,
сбои/гонки и остальные финансовые сценарии требуют своих доказательств;
проверка этого diff не объявляет их новой полной приёмкой.

Следующие ворота — scoped converge и обязательные проверки нового точного
PR SHA и текущей основы с общим валидатором. Этот локальный результат не
принимает слияние, публичный запуск продаж, выпуск или production. Дефект
продукта в прочитанном пути не обнаружен; при его обнаружении зависимая
приёмка должна останавливаться, а не ослаблять проверку.

## SHA-256 проверенных источников

Хеши относятся к рабочим файлам и сохранённым журналам, а не к новому коммиту:

```text
10d881940882f02122add9daf840c7cc6a8d84d79b946bd0a8d6ad55d5d231ca  apps/server/tests/integration/test_billing_renewal_planner_postgres.py
1a3aee3233509b1737f55f505852799eb992a21d3901c27912616042011b77f7  apps/server/src/twobrain_rec_server/billing/renewal_charge.py
85d3b6964d29a3ff8106bfdbc45841060bf91ea18dd96414e78f548d42601531  apps/server/src/twobrain_rec_server/config.py
767eb4265eb4760575b43bfea7d61c77773c4309140b2070b8bccd768461295a  apps/server/src/twobrain_rec_server/billing/notifications.py
c4d8b6cdc72c31aa19d0d3a58ce72e6dae28551f8b2784974facc638c75512cf  apps/server/src/twobrain_rec_server/billing/events.py
e4d0203d9aa7e2d8dea3aa35a43c76f5a0199722a191fc46ccec791c4c1de64c  apps/server/src/twobrain_rec_server/billing/reconciliation.py
48f91e9bb74f6867d4adc256ae818ad2e16a29a9a81a74337af6420f94e8ed34  apps/server/src/twobrain_rec_server/billing/yookassa.py
cc4161572a468e7a0b3b0fec2dcf4ee516e55f969d4ab6ba8c8d54deb9caffd1  specs/140-user-account-billing/checklists/renewal-decline.md
545f9789a365422b6de55a0deed3d8af97a1ba7678bd5944f790847daacb8aac  specs/140-user-account-billing/review-renewal-decline-requirements-20261031.md
ac1882906cc2cbeb9b384363339bb76375c0ffd9400bd2b0608f710bb29e03da  specs/140-user-account-billing/validation-renewal-decline-20261031.md
2bf038224d2e8a950075cae2daaaf6b5fa9d8c2ea593ebe51bb0af20f83ee2f0  specs/140-user-account-billing/spec.md
3e9fd7f4355bf24386f48f9a71d020a02c78015e60c59bf31c9ec485ff91338f  specs/140-user-account-billing/plan.md
2bd034a0556b9a3a880d8712cd537a5158ffd22e2a35ebbdc70c51f4a05ddc60  specs/140-user-account-billing/quickstart.md
f38e71f839283bdb95c370de9183c541c8710be0f3f69eee29b2ac4fd13b19a3  specs/140-user-account-billing/tasks.md
b5a22010d8b22fb2081eed8aa988970525ef5e971fd399e6e3e60d4578e60e8f  /tmp/f140-t074-baseline.log
14fdb57737db9d51ea32225deeae0d2c6c5b03d4434399fd20b9889a0719257e  /tmp/f140-t074-baseline.xml
56d78c50689c58e5caa48e9785f25f79c68404971761c23ebcab9d5dadd26c20  /tmp/f140-t074-settings-red.log
076836382bae483bfd5dd07618d436ea5aa5b3fed58f883f25f6b27a2f021246  /tmp/f140-t074-settings-red.xml
cc199adc9f27a19db11af063aafe43db7345c2f9b2fba0fd084decb62f2fb741  /tmp/f140-t074-settings-profile.log
b7a2ec4e691ec57fb5bd145d992de471ebe6fc1c0485ad7f4c8715f5f602fc81  /tmp/f140-t074-settings-profile.xml
```
