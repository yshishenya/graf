# T112 — независимое ревью загрузки фикстур one-GET пробника

17.11.2026. Проверяющий `/root/public_counter_readiness_review`. F273/T112/#7698, существующая полоса `high-risk-product`; текущая работа — узкое статическое ревью диагностического запуска. Копия `/private/tmp/graf-f273-result-visibility-20261116`. Текущий HEAD по последнему сообщению исполнителя: `33aedbaaa4d79ff8c4f2305b211cf81e99a22177`. В запросе и квитанции первой попытки указан прежний `ef9f5047ac5ac6c3ba2381e05b985b5071f3875c`; это историческая привязка. Git проверяющим не вызывался, свежая привязка HEAD получена от исполнителя, содержимое указанных ниже файлов проверено независимо по SHA-256.

Прочитан целиком `/private/tmp/graf-t112-early-proof-invocation-review-request-20261117.txt`. Изменён только этот новый отчёт. Тесты, collect-only, пробник, PostgreSQL, приложение и службы проверяющим не запускались; новые агенты не создавались. Код, требования, план, tasks, checklist, прежние отчёты, Git/GitHub и чужие изменения не менялись.

## Вердикт

**SCOPED INVOCATION PASS, P1=0/P2=0** именно для `-p tests.conftest` в приведённой ниже узкой команде при неизменных проверенных файлах. Один предварительный collect-only без PostgreSQL, затем один диагностический GET с изолированной PostgreSQL допустимы по этому reviewer gate. Предварительный сбор обязателен перед GET: он проверяет исправленный путь загрузки, не расходуя диагностический GET. Это не фактический результат запуска и не приёмка T112/T113.

Прежний implementation PASS `55cda55ea23f3266365aed7d12541b356be096425d13909c58ac09c74064c4c5` сохраняет границы самого пробника. Этот отчёт проверяет только новый способ загрузки, обнаруженный после EXIT4. Допуск не распространяется на изменение пробника/фикстур/исходников, расширение выбора, повторный автоматический опыт или перенос файла под `tests/`.

## Первая попытка завершилась до GET

Полностью прочитаны журнал и квитанция первой попытки. За `0.423881` секунды runner завершился с `exit_code=4`: `pytest: error: unrecognized arguments: --graf-collection-file`. В журнале есть `postgres_test_cleanup=container_not_started`; квитанция содержит пустые `observations`, `temporary_copy_removed=true`, `isolated_container_removed=false`.

В исходнике runner первичный `pytest --collect-only --graf-collection-file ...` расположен раньше `start_postgres` и исполнения `run_phase`. При неуспехе он печатает журнал и выходит с кодом первичного сбора. Поэтому этот EXIT4 является ошибкой запуска до сбора/выделения PostgreSQL/выполнения GET, а не отрицательным результатом диагностического HTTP-опыта. `isolated_container_removed=false` здесь не означает неудачную очистку запущенного контейнера: контейнер не стартовал. Сейчас временного `apps/server/test_t112_early_proof_probe_20261117.py` также нет.

| Материал первой попытки | SHA-256 |
| --- | --- |
| `/private/tmp/graf-t112-early-proof-native-20261117.log` | `3918cccb3072b4394a9387c33450b394e8ca8c0076f471c16245c5ee619d1d4c` |
| `/private/tmp/graf-t112-early-proof-native-20261117.json` | `79331f0a236f802e3e420ed3fdf7c79f3bb02cd7585ab4da9bdc166533d837af` |

## Путь регистрации и отсутствие конфликта

1. Пробник временно размещается непосредственно в `apps/server/`; `apps/server/conftest.py` отсутствует. Выбран конкретный существующий файл с `::test_early_proof_single_get`, поэтому начальная загрузка conftest ищет его каталог и предков, а не соседний `tests/`. Обычный Python-импорт `tests.contract...` сам по себе не регистрирует `tests/conftest.py` в pytest. Это согласуется с фактическим EXIT4.
2. `tests/conftest.py:49` объявляет `pytest_plugins`, включая `tests.fixtures.test_resources`. В `test_resources.py:18` функция `pytest_addoption` регистрирует `--graf-collection-file`. Тот же conftest содержит `postgres_seeded_database_url` и его зависимость `postgres_schema_database_url`; отдельная загрузка только resource-плагина не предоставила бы эти фикстуры.
3. В непартиционированном focused-режиме runner не добавляет resource-плагин к первичному сбору сам, но сохраняет пользовательские аргументы в `selection`. Поэтому `-p tests.conftest` попадёт и в первичный сбор, и в исполняющую фазу. `PYTHONPATH` перед этими процессами устанавливается на текущие `apps/server` и `apps/server/src`; `tests/__init__.py` существует.
4. Проверены исходники pytest и pluggy из указанного общего окружения. `consider_pluginarg` вызывает `import_plugin`, а `register` затем обрабатывает `pytest_plugins` модуля через `consider_module`. `import_plugin` возвращается без повторной регистрации, если плагин с тем же модульным именем уже зарегистрирован. В `run_phase` `-p tests.fixtures.test_resources` идёт до сохранённого `-p tests.conftest`; позднейшая запись того же имени из `pytest_plugins` безопасно пропускается. Одинаковые параметры повторно не добавляются.
5. При прямом имени `tests.conftest` FixtureManager рассматривает его как глобальный плагин: специальная обработка обычного conftest с локальной областью включается только для имени, оканчивающегося на `conftest.py`. Поэтому его фикстуры видны пробнику в `apps/server/`. Это намеренное расширение видимости в единственном отдельном процессе, а не изменение проекта.
6. Ограничение расположения существенно: если одновременно добавить `tests/` к выбору, pytest сможет обнаружить тот же модуль как conftest под именем пути, отличным от `tests.conftest`; pluggy отвергает один объект под двумя именами. Этот отчёт такого расширения не допускает. Импортированные вспомогательные контрактные модули не становятся отдельно выбранными тестами; `tests/contract/conftest.py` отсутствует.

## Эффекты фикстур и предварительного сбора

Явная загрузка conftest регистрирует три автоматические фикстуры: сброс `InMemoryIngestStore`, контекстных переменных запроса и process-local milestone guard. Их тела выполняются при setup/teardown выбранного теста, как при штатном запуске исходного контрактного теста. Они не добавляют HTTP-вызовы, не снимают ограничения аналитики и не открывают рабочий период. `client`, `_session_application`, медиа-роль и advisory-lock не являются автоматическими фикстурами и не исполняются только из-за импорта. БД создаётся через явную цепочку `postgres_seeded_database_url → postgres_schema_database_url → postgres_worker_database_url`; её проверки ограничивают адреса disposable loopback БД текущего runner.

Collect-only импортирует модули и собирает описание фикстур, но не выполняет их setup/teardown и тело пробника. Он не устанавливает семь диагностических обёрток: `install(monkeypatch)` находится внутри тела теста. Resource-плагин регистрирует маркеры, может заполнить `GRAF_NODE_MODULES` при наличии локального Playwright и пишет временный inventory. Это не обещание полного отсутствия файловых/процессных эффектов: runner создаёт и удаляет свой каталог метаданных, pytest может использовать штатный кэш. Однако после успешной проверки inventory ветка `collect_only` выходит до `start_postgres`, с `inventory_only` и `container_not_started`.

## Допустимый порядок запуска исполнителем

Сначала побайтово скопировать уже принятый пробник в `apps/server/test_t112_early_proof_probe_20261117.py` и сверить SHA-256 `e3c5f0d5dcec7c2f66d86ad9ec189b6689a233f12bdf27884b214316fa5030d8`. Читать сохранённый пробник непосредственно как тест из `validation/` нельзя: его корень source pins рассчитан на временную копию в `apps/server/`.

Из корня этой копии, без наследуемого `VIRTUAL_ENV` только в дочернем окружении:

```sh
env -u VIRTUAL_ENV \
  UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
  UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
  /opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused -p tests.conftest \
  test_t112_early_proof_probe_20261117.py::test_early_proof_single_get \
  --collect-only -q -s --tb=short
```

Ожидается EXIT0, `collection_count=1`, единственный указанный node ID, `postgres_test_result=inventory_only mode=focused collection_only=true` и `postgres_test_cleanup=container_not_started`. Сохранить журнал и хеш. Наличие лишнего выбора, параметров повторения/xdist из наследуемых pytest-настроек, иной загрузки плагинов или любой ошибки означает остановку до GET и разбор причины; это не разрешение менять окружение вслепую. В проверенном `pyproject.toml` нет `addopts`; непартиционированный focused-режим сам не добавляет `-n`, а `GRAF_TEST_WORKERS=1` сам по себе не является принудительным флагом xdist в этой ветке.

После такого предварительного успеха — один запуск той же команды без `--collect-only`:

```sh
env -u VIRTUAL_ENV \
  UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
  UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
  /opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused -p tests.conftest \
  test_t112_early_proof_probe_20261117.py::test_early_proof_single_get \
  -q -s --tb=short
```

Runner сначала снова собирает тот же единственный тест, затем выделяет свою изолированную PostgreSQL и выполняет одну focused-фазу. Сохранить исходный журнал, квитанцию, хеши и очистку. Удалить только эту временную копию в finally. Любой исход GET не назначает следующий опыт автоматически. Никаких POST/M1/native commit-теста/V4/87, расширения времени, лимитов или рабочего включения.

## Контрольные суммы новых зависимостей запуска

Все суммы ниже вычислены в этом проходе; для pytest/pluggy изучены применимые функции регистрации, начального поиска conftest и видимости фикстур статически, без их исполнения.

| Файл относительно корня копии | SHA-256 |
| --- | --- |
| `apps/server/scripts/run_local_postgres_tests.sh` | `b5858c56db899be16cdf842c42ecd87aa1984cac94f56015051eeb4e96240d07` |
| `apps/server/tests/conftest.py` | `0a8a2cb767b2f74e777fcb0c79616e68c65b0bf5a9ad5418838a4a0693389793` |
| `apps/server/tests/fixtures/test_resources.py` | `27b6994b848eddd4e2f95dcc827cb5a78946b27fba3e7972e5cfad7580a4a578` |
| `apps/server/tests/fixtures/postgres_test_database.py` | `9975596c2901035e2f58fe16481a19d1bc4d3924e8b3a00b1da69cfe80df505b` |
| `apps/server/tests/fixtures/postgres_rls.py` | `0bb6e2f46ce7b35530785ac4f8e8fcde39843b48f6d501ce30d9e009552beaad` |
| `apps/server/tests/fixtures/cabinet_exports.py` | `c6abde4f216dec32936a94277a944a17601ae60b6a8eacd33183066835753575` |
| `apps/server/pyproject.toml` | `711b51675fa997a2bbb509d641da36b2771566f6ad3088644cec2ba781d73ce7` |
| `specs/273-paid-traffic-analytics/validation/t112-early-proof-probe-20261117.py` | `e3c5f0d5dcec7c2f66d86ad9ec189b6689a233f12bdf27884b214316fa5030d8` |
| `specs/273-paid-traffic-analytics/validation/t112-early-proof-selfcheck-20261117.py` | `c73fa8b646f0d028e9f64d3b027018e4d8e0dee2203ac5c146b0211e4ddf8608` |

В `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/`:

| Файл окружения | SHA-256 |
| --- | --- |
| `_pytest/config/__init__.py` | `98b05c2c37d09e1d5c05975efc2d9af98d4aff6ea47de410a8e93956420873c1` |
| `_pytest/fixtures.py` | `f5d4d3f848d97411e456d50400d3aaecc19a9b0c90def9151e395ee8952042b7` |
| `pluggy/_manager.py` | `2b8229fe99048ef4f6a0e21f40fa7c0b0016a1756710d81045ccbdb651a28b4a` |

Все шесть PINS извлечены из AST пробника без его импорта и свежим вычислением совпали:

| Источник внутри `apps/server` | SHA-256 |
| --- | --- |
| `tests/contract/test_result_view_http_integration.py` | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| `tests/contract/test_result_view_http_budget.py` | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |
| `src/twobrain_rec_server/cabinet/web_routes/result_views.py` | `232d6c1f2bd36e7537b0e611aa1fd42fe13c6f3b874ca838aeca2c9c1f7b567e` |
| `src/twobrain_rec_server/product_analytics/ingest.py` | `69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795` |
| `src/twobrain_rec_server/cabinet/result_visibility.py` | `ecaac3c0e2a842802900352fc3a6a39b1a26e610bb78fb71eca723e5f6c8ce04` |
| `src/twobrain_rec_server/api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |

## Требования и пределы вывода

Свежее сравнение всех 18 `unchanged_inputs` в `/private/tmp/graf-t112-root-history-reading-20261116.json`: **18 SAME**. Это контроль неизменности собственных ранее прочитанных оригиналов в том же диалоге, а не замена чтения чужой записью. После сжатия повторно прочитаны оригиналы README/document-reading, применимые разделы: constitution VI и Development Workflow/Governance; result-visibility §3/7; весь T112-раздел plan и весь T112-профиль quickstart; product-gates Audio/Artifacts/Diagnostics и Server/Storage/AI. Они ограничивают синтетическую проверку, закрытый рабочий gate и журнал без содержимого/proof; эта узкая загрузка их не меняет. Дополнительные зависимости запуска описаны выше. По четырём исходным reviewer-owned checklist свежий подсчёт: requirements **16/0**, security **27/0**, privacy-measurement **52/0**, infra **29/0**; всего **124 отмечено / 0 не отмечено**. Маркеры не менялись; это не новая полная приёмка реализации и не подсчёт иных public-* checklist.

Настоящий `ProductAnalyticsIngestService._result_period_context` в текущем исходнике по-прежнему заканчивается `yield None`; тестовая `http_period` подменяет его только через monkeypatch. Postal остаётся почтой GRAF. Этот отчёт не утверждает, что вся публичная Метрика выключена.

Pytest PASS будущего пробника означает только завершившийся диагностический код: сам пробник не требует HTTP200 или наличия proof. `incomplete=false` отдельно не доказывает прохождение всех семи этапов. Краткая metadata-наблюдаемость не устанавливает причину прежнего POST2 `unavailable`; whole-case elapsed не является длительностью optional helper. Рабочие T112/T113/T098/restore/readiness, фиксированный T0, приёмка внешних пользователей, трафик и продажи этим допуском не закрываются. Внешних событий, публикации, выпуска или выкладки проверяющим не было.
