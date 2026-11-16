# T112 — инертная диагностическая копия normal-цепочки

17.11.2026, F273/T112/#7698; существующая полоса `high-risk-product`.
Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`,
ветка `codex/f273-result-visibility-20261116`, исходный HEAD
`d33d9cfc49253bea4a3f207c1000ec56a5d55c85`.

## Сделано

По принятому независимому проекту
[t112-native-response-next-design-20261117.md](t112-native-response-next-design-20261117.md)
подготовлены полная инертная копия integration-модуля
[t112-native-normal-probe-20261117.py](t112-native-normal-probe-20261117.py)
и [самопроверка без HTTP/БД](t112-native-normal-selfcheck-20261117.py).
Меняется только тело одного native-теста и добавляются его диагностические
помощники в конце копии. Исходный integration-модуль, runtime, imports/globals
исходника и остальные тесты не менялись. Копия находится вне обычного набора
pytest; конструктор наблюдателя отказывает для любого fault кроме точного False.

В native-теле ровно14 уникальных текстовых преобразований: создание
наблюдателя; обёртка app; статус GET и прозрачное получение count из двух
существующих вызовов `_proofs`; два прежних POST; ранняя очистка/F/B/gate;
исходные JSON/строки второго POST; конец сценария; первый синхронный snapshot
в исходном finally; вывод после полного `_run` и его очистки. Все14
преобразований явно перечислены в selfcheck, обратимы ровно по одному разу.
После их удаления весь исходный модуль побайтово и по AST равен основе.
Самопроверка отвергает изменение исходного assertion, await и удаление
обязательной диагностической вставки. Произвольные statements не удаляются.

POST вызывает прежний bound method один раз, передаёт те же args/kwargs,
возвращает тот же response и распространяет то же исключение/отмену;
ContextVar сбрасывается finally. ASGI app получает прежние scope/receive;
каждое исходное message передаётся send ровно один раз. Диагностика читает
только type/status/more_body и числовые сроки scope.state, без body, headers,
path/query, response.json/text и значений proof. Исходные обращения к
response/json/HTML и SQL assertions остаются в самом native-тесте.

48 подробных records ограничены независимо от фиксированных сводок запросов
и стадий. Попытка и завершение start/body/terminal body различаются. Сроки
POST1/POST2 не смешиваются: snapshot POST1 использует факты target либо
фактический наблюдённый scope, POST2 — только собственный scope. Отсутствующий
срок остаётся None; нового дедлайна нет. Snapshot первым действием исходного
scenario finally сохраняет только bool/числа/типы исключений и checkout
смещения. Это точка до явной спасательной очистки, а не до всех автоматических
context-manager cleanup. JSON печатается после исходного `_run` cleanup.

## Фактические проверки

Самопроверка выполнена штатным уже существующим Python3.13 окружением,
без uv sync/новых зависимостей и без выполнения тестовых функций модуля:

```sh
env -u VIRTUAL_ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=apps/server/src:apps/server \
  /Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python \
  specs/273-paid-traffic-analytics/validation/t112-native-normal-selfcheck-20261117.py \
  apps/server/tests/contract/test_result_view_http_integration.py \
  specs/273-paid-traffic-analytics/validation/t112-native-normal-probe-20261117.py
```

EXIT0: exact source/AST restoration,3 отвергнутые мутации, original call/return
identity, args/kwargs, то же исключение и CancelledError, настоящая отмена
искусственной task, ContextVar reset, ASGI attempted/completed send и app
return/raise, запрет доступа к payload искусственных объектов, один вызов
proof parser/та же коллекция, исходный short-circuit, независимые deadlines,
сводки после заполнения cap, snapshot partial target/None/error.
Это импорт инертного модуля и вызовы помощников с искусственными объектами;
HTTP/SQL/PostgreSQL/приложение/контейнер не запускались. Первый PASS был
проверкой черновика; итоговый PASS относится к хешам ниже.

| Материал | SHA-256 |
| --- | --- |
| diagnostic probe | `20bf2ba1455156bf6863f2eac6123c1fae25b897e7260aa94793afc1de94a83b` |
| selfcheck | `dc1e6edabc1f8d98dd43911106ed71d9c6698ebcc63f55d290c25152f1ad00d2` |
| `/private/tmp/graf-t112-native-normal-selfcheck-20261117.log` | `2fafadd84fa42033034c09bad2da8d8219f8a98b64103621aa0ebbd7e05df5e7` |
| исходный integration | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| принятый проект следующего опыта | `8f59e2eacbe72fb0dcf3a553869c001141eeeb4fac6032f4938e449f137c1e3d` |

Независимый reviewer отдельно подтвердил18/18 неизменных требований и
checklist124/0 перед кодом; основные маркеры не менялись. Собственная сверка
18inputs SAME, prerequisite PASS, agent-context PASS. Ruff selfcheck PASS;
у полной копии нет новых замечаний относительно исходника:4 прежних I001
совпадают при одинаковом stdin-filename. Исходные imports не переставлялись;
два новых поздних импорта имеют адресный noqa E402 для сохранности основы. Применимые оригиналы и
зависимости восстановлены в этом же диалоге по document-reading; research
T112 прочитан целиком. `speckit-implement` используется внутри существующего
среза; before/after_implement auto-commit hooks disabled. Tasks T112/T113
остаются открытыми; code selfcheck не равен исполнению или завершению задачи.

## Следующая граница

Отдельное независимое implementation review точных хешей обязательно до
collect-only и одного native `[False]` опыта. Старые early-proof/V4 результаты
на эту копию не переносятся. Только после нового PASS допустим узкий адресный
сбор с явным `-p tests.conftest`, inventory одного False и container_not_started,
затем ровно один normal GET→POST1→F/B→POST2. Без True/M1/87, повторов,
дополнительных запросов или изменения runtime по догадке. Любой отказ
сохраняется; новый опыт не назначается автоматически.

Настоящий `_result_period_context` сохраняет `yield None`; Postal — почта
ГРАФ. Рабочая инфраструктура, службы/почта, сбор/IP, резервные копии,
контент/вёрстка сайта и внешние публикации не менялись. T098/T113/restore,
готовность измерения/T0 и коммерческие критерии остаются открытыми.
Неизвестные прежние normal POST2/fault response_held/repeated HOLD не объяснены.
