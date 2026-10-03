# F280 US4 — независимая проверка T050

2026-10-04 · PR [#7506](https://github.com/yshishenya/graf/pull/7506) · lane `high-risk-product`, активный Spec Kit срез. Проверка только чтением; единственная запись проверяющего — этот отчёт.

**PASS в пределах T050.** Замечаний P0/P1/P2/P3: 0. Изменение одного assertion соответствует FR-039/040/042; остальные проверки и код продукта сохранены. Это не разрешение слияния или выпуска.

## Исходники и причина

Текущая ветка `codex/280-subscription-clarity`, HEAD `8b5e447f8161781e4297567e6c629073bc6edad7`. Проверен фактический незакоммиченный diff относительно HEAD, а не только описание задачи. Прочитаны применимые AGENTS/guidance, требования, plan/tasks/quickstart, реальный шаблон, GET обработчик и журналы.

- `apps/server/tests/integration/test_billing_return.py:334–350`: прежние данные active subscription + unknown renewal и отключение `recurring_allowed` сохранены. На строке 347 заменено только ожидание повторяющейся фразы на точное `<dt>Автопродление</dt><dd>Отключено</dd>`. Побайтовое сравнение всего файла подтверждает ровно эту замену; остальные 23 из 24 функций идентичны, добавленных/удалённых функций нет.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html:31–36`: поле находится в основном видимом `dl`, вне раскрытий и скрытых сообщений; `False` даёт «Отключено». Проверка соответствует FR-039, а не требует возвращать лишний текст.
- Строки теста 348–350 неизменны: отправленный платёж «еще может завершиться», отсутствует ложное «Автоматического списания не будет», сохранён точный `href="/billing/checkout/status/INV-CLARITY"`. Шаблон на строках 23–25 показывает неопределённость и проверку существующего платежа; GET `cabinet/web_routes/billing.py:2820–2837,2904–2905` получает его invoice и использует существующий путь результата. Это сохраняет FR-040/042 и не обещает отменить уже отправленный платёж.

SHA-256 проверенных байтов:

| Файл | SHA-256 |
| --- | --- |
| `apps/server/tests/integration/test_billing_return.py` | `ef277f0b725a6a66bfbf61655c3e32896dce93c871ce1fb96acf11c70fe5b033` |
| `cabinet/pages/billing_subscription_content.html` | `3fa4aa82bbe3362e3f3688a44c19fda0467656cf72eed11b3f1f868dd33c2d13` |
| `cabinet/web_routes/billing.py` | `b199d977373883be3a94c5d395387c219beed1eebbdd3931921188bfdcced666` |
| `cabinet/static/cabinet/cabinet.css` | `24074ca3bc01545a1ab794c8df222e36622fa1cbe171a6a327dfe840fe200a64` |

Три файла продукта побайтово равны HEAD; diff HEAD для `apps/server/src`, `apps/macos`, `infra` пуст. Шаблон/маршрут совпадают с ранее проверенными UX/security байтами, CSS — с итоговым browser review после интеграции F285 (blob `bbcda962e18df9c8a2aa20092236569dadcf43c3`). Сверка с [предыдущим отчётом](review-subscription-release-readiness.md) и первичными UX/security/browser отчётами подтверждает сохранение проверенной реализации. Старый CSS до интеграции не назван текущим; изменённый тест рассмотрен отдельно здесь.

## Завершённые журналы

Фактические журналы прочитаны независимо, тесты повторно не запускались. Основной агент указал команду полного файла в [validation](validation-subscription-clarity.md): `apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_return.py -q --tb=short --show-capture=no`.

| Журнал | Наблюдаемый результат | SHA-256 |
| --- | --- | --- |
| `graf-f280-subscription-return-red.log` | Причинный отказ строки 347 на старой фразе; HTTP 200; `1 failed, 81 deselected`; `postgres_test_phase=focused status=fail`; `postgres_test_cleanup=isolated_container_removed`. | `cadc65abb404450f8734a893a121534508acb5ac97d23062a05844c1da8d0083` |
| `graf-f280-subscription-return-green.log` | `collection_count=82`; **82 passed / 0 failed / 0 skipped**, без deselected; 110.57 с pytest, 118 с runner; `postgres_test_phase=focused status=pass`, `postgres_test_result=pass mode=focused partitioned=false shard=none`, `postgres_test_cleanup=isolated_container_removed`. | `75b3a438b20ae8cffd739d6619eca80ce09ee18edf886acc29f848033c083ac2` |

GREEN завершён, а не принят по имени файла или промежуточным точкам. Collection digest `355468009a2a415ee678c6b52e5aaf6aca2ecc32382c033337be12cf75e5ebba`. В обоих запусках две предупреждающие записи pytest/Starlette; отказов либо пропусков в GREEN нет.

## Границы заключения

Журналы получены запуском основного агента: проверяющий подтвердил их содержимое и конечные маркеры, но не запускал тесты самостоятельно. Сам журнал GREEN не содержит fingerprint исходников и списка всех node IDs; привязка к текущему файлу опирается на проверенный diff/hash и запись команды в validation, не является exact-SHA CI аттестацией. Production здесь означает неизменность исходников, а не проверку живого сервера. Браузерная видимость и остальные финансовые сценарии заново не проверялись; тест подготавливает отключение через БД, не доказывает действие POST отмены или настоящий ответ провайдера.

Актуальные `governance-fast`, `macos-pr`, `pr-metadata`, слияние и отдельные release/deploy/publication gates остаются обязательными и этим отчётом не подтверждены. Новые реальные платежи, списания, возвраты или grants не выполнялись. Код, тесты, spec/plan/tasks/checklist, Git/GitHub и выпуск проверяющий не изменял.
