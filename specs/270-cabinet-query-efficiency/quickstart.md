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
| `/meetings/{id}` | — | 84 | не более 25 (ещё не подтверждено) |

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

Ожидаемо: всё проходит без правки ожиданий. Ограничение только итогами и недоступная встреча отдают 404
на загрузку аудио; полный доступ без разрешения загрузки отдаёт 409. Отозванный доступ исчезает из списка, недоступная встреча даёт 404,
деталь не показывает аудио при ограниченном доступе.

## Сценарий 5. Обязательные проверки на точном SHA

Перед слиянием обязательны `governance-fast`, `macos-pr` и `pr-metadata` на точном
SHA пул-реквеста. Полный прогон `release-full` выполняется на замороженном кандидате
выпуска и служит доказательством для выкатки.

## Откат

Правка не меняет схему и не оставляет следов в данных, поэтому откат — возврат
коммита. Миграции откатывать не требуется.

## Повторная проверка общих встреч (#7142)

Сценарий 1 включает отдельно `/shared-with-me` и `/desktop/shared-with-me`:
получателю выдаются 5, затем 50 действующих доступов к 50 разным встречам.
Одна доступная встреча на фоне 50 собственных не проверяет этот дефект.
Исходный замер master `2c7f93e6bb4c7264e6b0e131879abe30ed1f326d`:
73 SQL при 5 и 253 SQL при 50 встречах на обеих страницах. Цель: рост <=25%,
не более 80 SQL; время сохраняется как наблюдение, а не нестабильный предохранитель.
Проверки доступа из сценария 4 обязательны без ослабления ожиданий. Полная приёмка
также требует отдельного бюджета детали <=25 SQL (SC-003); прежнее исключение в
плане не отменяло это требование.

Дополнительно сравнить SQL пустого списка и одиночной общей встречи до/после:
рост не допускается. Существующий guard owner API сохраняется; веб-страницы
`/meetings`, `/desktop/meetings` и обе shared страницы проверяются отдельно.
Отрицательная проверка временно добавляет SQL в каждый соответствующий цикл,
должна назвать проверяемую страницу и упасть; нарушение затем удаляется.
Для полного прогона 2214s — исходная длительность серверной части (не всего workflow), 7583s — сумма тел параллельных
случаев; они не взаимозаменяемы. SC-005 требует <=1881,9s длительности серверной части в
сопоставимом исходному окружении. Без такого доказательства критерий остаётся открыт.

В сравнении5→50shared число исходных рабочих пространств фиксировано: один владелец.
Это доказательство отсутствия чтений на встречу, а не постоянной стоимости для
50 разных рабочих пространств. Изоляция нескольких владельцев проверяется отдельно;
для сравнения бюджета количество групп должно оставаться тем же.

## Сценарий 6. Служебный контекст (#7142/T029–T031)

Использовать существующее окружение и одноразовую PostgreSQL, без сборки приложения:

```sh
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
  bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_tenant_context_query_budget.py \
  tests/unit/test_rls_tenant_context.py \
  tests/integration/test_rls_postgres_policies.py \
  tests/integration/test_rls_identity_policies.py \
  tests/integration/test_rls_meeting_content_policies.py \
  tests/integration/test_rls_maintenance_context.py \
  tests/integration/test_rls_worker_context.py \
  tests/integration/test_rls_application_boundaries.py \
  tests/integration/test_rls_stale_session_device_context.py -q
```

Дополнительно повторить сценарий 4 и предохранитель
`tests/integration/test_cabinet_meeting_list_query_budget.py`. Ожидания старых
проверок не менять. До исправления новый предохранитель обязан падать на числе
SQL. После — все значения current_setting совпадают, один непустой проход
выполняет 1 SQL, первый session apply сохраняет 2 прохода/2 SQL, пустой контекст
не выполняет SQL. Проверить commit/rollback, замену и восстановление контекста,
повторное использование физического соединения, параллельные сессии и отказ SQL.
Ошибочная транзакция не допускает защищённого чтения до rollback; после rollback
восстановление использует прежний сохранённый контекст.

Сохранить замер той же детали, что дала 84 SQL, и число обращений списков.
Снижение промежуточного результата не закрывает SC-003 (<=25 SQL); полный
серверный прогон и сопоставимый эталон SC-005 остаются отдельной T026.
