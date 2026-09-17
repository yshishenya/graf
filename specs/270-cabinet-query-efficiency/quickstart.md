# Quickstart: Предсказуемая скорость страниц кабинета

**Фича**: 270-cabinet-query-efficiency
**Назначение**: проверяемые сценарии и точные команды для подтверждения результата.

## Предварительные условия

- Docker Engine запущен (прогон поднимает одноразовый контейнер PostgreSQL).
- Все команды выполняются из корня репозитория.
- Замеры сравниваются с эталоном `/tmp/graf-baseline/parallel.jsonl`, снятым до правок.

## Сценарий 1. Число обращений к базе не растёт от числа встреч (SC-001, SC-006)

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_cabinet_meeting_list_query_budget.py -q -s
```

Ожидаемо: проверка проходит; в выводе видно число обращений при 5 и при 50 встречах
и оно отличается не более чем на 25 процентов.

Проверка обязана упасть, если в список вернуть обращение к базе внутри цикла по
встречам. Это подтверждается отдельным прогоном с намеренно внесённым нарушением
(см. tasks.md, задача проверки предохранителя).

## Сценарий 2. Замер страницы списка и детали (SC-001, SC-002, SC-003)

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_cabinet_meeting_list.py -q -s
```

Ожидаемо по замерам:

| Страница | Встреч | До правок | После правок |
|---|---|---|---|
| `/meetings` | 5 | 144 | не более ~30 |
| `/meetings` | 10 | 299 | не более ~30 |
| `/meetings` | 20 | 609 | не более ~30 |
| `/meetings` | 50 | ~1500 (расчёт) | не более ~30 |
| `/meetings/{id}` | — | 84 | без роста |

## Сценарий 3. Полный серверный прогон (SC-004, SC-005)

```sh
GRAF_TEST_WORKERS=4 GRAF_PERFORMANCE_GATE=required GRAF_TEST_REPORT_DIR=/tmp/graf-after \
  bash apps/server/scripts/run_local_postgres_tests.sh --full -q
```

Ожидаемо:
- прогон завершается успешно, ни одна существующая проверка не изменена;
- число случаев совпадает с эталоном (4454 в параллельной фазе);
- суммарное время тел меньше эталонных 7583 с;
- результат фиксируется в отчёте о реализации.

Сравнение с эталоном:

```sh
python3 - <<'PY'
import json, collections
def total(path):
    call = setup = 0
    for line in open(path):
        row = json.loads(line)
        if row["when"] == "call": call += row["duration"]
        elif row["when"] == "setup": setup += row["duration"]
    return call, setup
before = total("/tmp/graf-baseline/parallel.jsonl")
after = total("/tmp/graf-after/parallel.jsonl")
print(f"до:    тела {before[0]:.0f}s подготовка {before[1]:.0f}s")
print(f"после: тела {after[0]:.0f}s подготовка {after[1]:.0f}s")
PY
```

## Сценарий 4. Проверки доступа не изменились (SC-004)

```sh
GRAF_TEST_WORKERS=4 bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_shared_with_me.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_web_owner_session_context.py \
  tests/contract/test_cabinet_no_secret_content_egress.py -q
```

Ожидаемо: всё проходит без правки ожиданий. Ограничение только итогами отдаёт 409
на загрузку аудио, отозванный доступ исчезает из списка, недоступная встреча даёт 404,
деталь не показывает аудио при ограниченном доступе.

## Сценарий 5. Обязательные проверки на точном SHA

Перед слиянием обязательны `governance-fast`, `macos-pr` и `pr-metadata` на точном
SHA пул-реквеста. Полный прогон `release-full` выполняется на замороженном кандидате
выпуска и служит доказательством для выкатки.

## Откат

Правка не меняет схему и не оставляет следов в данных, поэтому откат — возврат
коммита. Миграции откатывать не требуется.
