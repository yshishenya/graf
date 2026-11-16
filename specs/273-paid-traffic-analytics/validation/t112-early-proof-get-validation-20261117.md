# T112 — один GET с редкими наблюдениями: серверная предпосылка проходит

17.11.2026. Автор `/root`; F273/T112/#7698, T113/#7804,
полоса `high-risk-product`. Источник
`33aedbaaa4d79ff8c4f2305b211cf81e99a22177`. Runtime, native tests, probe,
selfcheck, сроки и лимиты не менялись. Это диагностическое свидетельство,
не приёмка T112/T113, нового клиента или внешнего трафика.

## Допуск и исполненный объём

Получен FINAL и полностью прочитан новый
[invocation review](t112-early-proof-invocation-review-20261117.md),
SHA-256 `072eacd95ad69e8a05f7c56945e669675239edc7debf4600873933bef9b516df`:
SCOPED INVOCATION PASS/P1=0/P2=0. Он дополнил прежний
[implementation PASS](t112-early-proof-implementation-review-20261117.md)
для точного probe SHA-256
`e3c5f0d5dcec7c2f66d86ad9ec189b6689a233f12bdf27884b214316fa5030d8`.
Разрешены предварительная collection и один GET; этот допуск теперь использован.

Перед копированием проверены HEAD, SHA обоих применимых файлов, шесть PINS,
существующие зависимости загрузки по таблице ревью и18 unchanged_inputs:
18SAME. Наследуемых PYTEST_ADDOPTS/PYTEST_PLUGINS нет. Доступное место Mac
101206503424байта, выше80ГБ. Временная копия создана эксклюзивно в
`apps/server/test_t112_early_proof_probe_20261117.py`, её SHA совпал.
Из дочернего окружения убран только VIRTUAL_ENV; shared venv не менялся.

```sh
env -u VIRTUAL_ENV \
  UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
  UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
  /opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused -p tests.conftest \
  test_t112_early_proof_probe_20261117.py::test_early_proof_single_get \
  -q -s --tb=short
```

Сначала та же команда с `--collect-only`: EXIT0/4.864376s, ровно1тест,
inventory_only и container_not_started. Digest выбранного единственного node:
`1f961a21fd0facf78b86bded04594885ebf5ae066d61ec553e9bbd46e8b455cf`.
Затем один запуск без collect-only: **1 passed,1 warning / EXIT0**, pytest6.79s,
focused phase11s, внешняя длительность18.33111s. Выбран тот же digest.
PASS pytest означает исполнение пробника; смысл результата определён ниже
по его отдельным метаданным, а не по одной зелёной строке.

## Полученные метаданные

Один HTTP GET: **status200**, elapsed1.458918s. В records16строк,
все7стадий присутствуют, dropped0/incomplete=false, exception records0.
До получения actual work/cleanup параметров остатки сроков были None.

| Стадия | Наблюдение |
| --- | --- |
| optional | Все четыре access bool true; исходный результат dict/count2 |
| eligible | Один исходный вызов, allowed=true |
| operation | Штатно завершилась, dict/count2 |
| issue | Штатно завершилась, dict/count2 |
| inspect | Все шесть precondition bool true; dict/count2 |
| account | Yield не None, точный inspection owner; exit_finished без исключения |
| bindings | Исходный loader вернул dict/count2 |

Длительность optional от её enter до leave: **0.843491s**;
длительность loader bindings: **0.786548s**. Это измерения функциональных
границ данного GET, в отличие от whole-case elapsed прежнего V4.
На выходе optional оставалось work0.656518s/hard1.156518s.
Вход issue наблюдал work1.499884s/hard1.999884s.
Ни сроки, ни проверки ради результата не увеличивались.

Этот отдельный GET без global tracing сформировал на сервере два
подтверждения и прошёл operation cleanup. Тело/headers ответа, ключи/значения
proof и bindings, SQL payload не читались. Поэтому размещение подтверждений
в HTML этим опытом не проверено; положительное серверное число не заменяет
доказательство клиентской выдачи или видимого показа результата.

## Очистка и источники вне Git

Runner сообщил `postgres_test_cleanup=isolated_container_removed` и
`postgres_test_result=pass mode=focused partitioned=false shard=none`.
Временная копия снята в finally после повторной сверки SHA.
Второго GET, POST/M1, native commit-сценария, V4 или87 не было.

| Источник | SHA-256 |
| --- | --- |
| `/private/tmp/graf-t112-early-proof-invocation-20261117-collection.log` | `30638fa4cd96b707944a44368d5b0d98c83c13ae61f556f5b3feefe99f9f1f87` |
| `/private/tmp/graf-t112-early-proof-invocation-20261117-get.log` | `b23fc17d90cc4fc15714a13e34a39bfbd7d16fafdf5550baa4049fb30790da7f` |
| `/private/tmp/graf-t112-early-proof-invocation-20261117.json` | `49e6e818d9e9c7a3bab0aae8c35d5203fafd6920f3e6cea7e869dde288e5d662` |

Квитанция содержит source pins, допуск, командные результаты, только разрешённые
метаданные7стадий и очистку. Из raw log прочитаны безопасные test/result markers;
полное содержимое лога не публиковалось и в Git не включено.

## Что изменилось в следующем вопросе

Ранняя серверная предпосылка воспроизведена положительно без глобальной
трассировки. Это **не доказывает**, что прежние0proofs вызвала трассировка:
нет причинного A/B, изменились состав отдельного case и наблюдение.
Положительный новый опыт не исправляет прежний V4 задним числом.

Неизвестные прежние repeated HOLD, normal POST2 response_complete=false
и fault response_held timeout остаются необъяснёнными. Нельзя менять runtime
по догадке либо автоматически повторять POST/V4/87. Следующий полезный шаг —
независимо выбрать минимальный опыт для исходного незавершённого native
COMMIT/response, опираясь на этот положительный серверный GET. До его
нового точного дизайна и приёмки исполнения не назначено.

Настоящий period сохраняет `yield None`; почта ГРАФ — Postal. T112/T113/T098,
restore/readiness/T0, внешние аккаунты и коммерческие критерии открыты.
Контент/вёрстка, production, службы, аналитические настройки/IP, публикации
и внешние события не менялись. Метрика здесь не читалась.
