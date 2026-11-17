# T112 — один normal-опыт полного native HTTP/COMMIT

17.11.2026. F273/T112/#7698, T113/#7804, существующая полоса
`high-risk-product`. Копия `/private/tmp/graf-f273-result-visibility-20261116`,
ветка `codex/f273-result-visibility-20261116`, исходный HEAD
`1514803209d4d619d406219edf0c633f63652082`.

## Результат

**Один normal `[False]`: PASS, EXIT0, pytest1 passed/1 warning.**
Пройдена полная исходная последовательность GET/HTML→POST1/COMMIT→ранняя
очистка/F/B→POST2/неизменная пара данных, без global tracing. Это локальное
подтверждение обычной цепочки именно этого опыта; причина исторического
repeated HOLD, прежнего normal response_complete=false и fault response_held
не установлена. True/M1/V4/87 не запускались и автоматически не назначены.

Рабочий код, исходный integration-тест, сроки и проверки не менялись.
Настоящий `_result_period_context` сохраняет `yield None`; контент, вёрстка,
production, почта/очереди/службы, аналитические настройки/IP, резервные копии
и внешние события не менялись. Почта ГРАФ — Postal.

## Допуски до исполнения

Получены действительные FINAL, каждый целиком прочитан и независимо сверены
его хеш и точные входы:

| Допуск | SHA-256 |
| --- | --- |
| [Проект следующего опыта](t112-native-response-next-design-20261117.md) | `8f59e2eacbe72fb0dcf3a553869c001141eeeb4fac6032f4938e449f137c1e3d` |
| [Ревью реализации](t112-native-normal-implementation-review-20261117.md) | `65dbb8557d407953acef697d058b9be3f54771cf40283f6c6391a18c1e958bd0` |
| [Отдельное ревью запуска](t112-native-normal-invocation-review-20261117.md) | `dce7edb8aae7ec59a2ff25753fc8a56e784ff3a56fc520668dba69b9303714ec` |

Implementation и invocation оба SCOPED PASS/P1=0/P2=0. Старые one-GET/V4
допуски не переносились. Точный инертный рецепт
`/private/tmp/graf-t112-native-normal-invocation-20261117.py`, SHA-256
`bbe0e009f93ace302d1c01c212275ce97cff56b08da4d00ab9e0a87b82742f49`.
Probe20bf2ba1…/selfcheckdc1e6eda… — прежняя принятая реализация, без новых
правок после FINAL. Полные суммы всех9pins сохранены в квитанциях.

Перед обоими шагами совпали9 встроенных pins; отдельно совпали четыре
зависимости из invocation review: tests/conftest.py, test_resources.py,
postgres_test_database.py, pyproject.toml. Не заданы PYTEST_ADDOPTS,
PYTEST_PLUGINS, PYTEST_DISABLE_PLUGIN_AUTOLOAD, PYTHONOPTIMIZE,
GRAF_TEST_REPORT_DIR, GRAF_PERFORMANCE_GATE; optimize=0. Общая существующая
venv используется без sync; VIRTUAL_ENV удалён только в дочернем окружении.
Предварительно свободно97 103 630 336байт, рецепт непосредственно перед
native дополнительно проверил >=80 000 000 000. Тяжёлой сборки/архива нет.

## Фактически выполненный порядок

Оба шага исполнены отдельно из корня указанной копии:

```sh
env -u VIRTUAL_ENV PYTHONDONTWRITEBYTECODE=1 \
  /Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python \
  /private/tmp/graf-t112-native-normal-invocation-20261117.py collection
```

Collection wrapper EXIT0/4.721146s, pytest1 collected/0.23s, ровно один
полный node `[False]`, inventory_only=true/container_not_started=true,
observations пуст, временная копия удалена. Полная квитанция и весь
collection log проверены, хеш журнала совпал; только после этого выполнено:

```sh
env -u VIRTUAL_ENV PYTHONDONTWRITEBYTECODE=1 \
  /Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python \
  /private/tmp/graf-t112-native-normal-invocation-20261117.py native
```

В обоих шагах runner получил `--focused -p tests.conftest` и только:

```text
test_t112_native_normal_probe_20261117.py::test_real_commit_acknowledgement_and_idle_return_keep_pair_and_foreign_generation[False]
```

Выборка1, SHA-256 со следующим переводом строки
`08511b1a31e0a192e0df21cc6e8ee7a488d3b53fb4a4770d375e4bc83519d5ee`.
Никаких tests/, True, repeat, xdist и дополнительных GET/POST не добавлялось.
Native wrapper EXIT0/19.160003s; pytest1PASS1warning/8.06s,
setup4.04s/call3.71s/teardown0.03s, focused phase13s.
Это разные интервалы; время всего теста не является временем GET либо POST.
Единственный warning — известный PytestAssertRewriteWarning ранее
импортированного tests.fixtures.postgres_test_database, не отказ теста.

## Доказательство полной цепочки

Считан весь безопасный JSON наблюдателя, сводки runner/pytest и первичный
native print; весь закрытый raw log обработан для receipt/hash/ошибок,
но его содержимое целиком не печаталось и не помещалось в Git.
28 records, dropped0; ошибок app/post/snapshot/run нет.

| Граница | Фактическое доказательство |
| --- | --- |
| GET/HTML | HTTP200, исходный parser дважды вызван ровно как прежде, каждый раз2 proof; исходные pool0/empty pair assertions прошли |
| POST1 | entered1/returned1, completed start200=1, body attempted/completed2/2, terminal body completed1, app returned1; исходные accepted/private-no-store/writes2/commits1 прошли |
| COMMIT/ранняя очистка | commit1/after_commit1/reset1/checkin1 в исходном окне, invalidate0; все прежние owner/Session/task/keys/pool/backend idle/locks0 assertions прошли |
| F/B | borrower_before_gate/gate_opened/borrower_after_gate по1 после исходных проверок; тот же normal target generation, чужое соединение здорово до/после gate.set, safe reuse |
| POST2 | отдельный entered1/returned1, completed start200=1, body attempted/completed2/2, terminal completed1, app returned1; исходные JSON accepted и полное equality сохранённых2строк прошли |
| Конец | post2_json/post2_rows/scenario_complete по1, provider_calls0/pool0 assertions прошли, watchdogfalse |

Ранний исходный print сообщает elapsed0.764s, same_pool_foreign/safe_reuse=true,
old_generation_closed=false, m1=false, return offsets[0,1]. Он расположен
до POST2 и сам по себе полного PASS не доказывает. Полный результат выше
подтверждён отдельными POST2/terminal markers и исходными assertions.

В snapshot первым действием явного scenario finally:
last_stage=scenario_complete, enteredtrue, test_error/snapshot_error/target
snapshot_error=None; post/observer/db_task done=true/cancelling0; watchdogfalse.
Остатки actual work/hard POST1:0.058190/0.558190s,
POST2:0.822613/1.322613s. Сроки каждого POST различны, hard-work=.5s;
никакого продления/переноса срока от первого запроса ко второму нет.
Это остатки в конкретной финальной точке, не длительности запросов.

Normal target response_gate=true/held=false/stream done=false до явного
finally: здоровое сохранённое поколение в этот момент не обязано закрываться.
Это не fault/M1 и не доказательство утечки. Полная snapshot return_count5 и
checkout offsets[0,1,2,3,5] накоплены к концу POST2; их нельзя подменять
ранним точным checkout-window с markercheckin1. Исходная корреляция не менялась.

## Очистка и сохранённые первичные материалы

Runner подтвердил `postgres_test_cleanup=isolated_container_removed` и
`postgres_test_result=pass mode=focused partitioned=false shard=none`.
Обе временные root-level копии сняты finally после сверки SHA; фактическое
отсутствие проверено после native. Все9pins после опыта SAME;
`git diff` apps/server/changes к исходному HEAD пуст. Стендовые архивы,
дополнительные контейнеры или копии продукта не создавались.

| Материал вне Git | SHA-256 |
| --- | --- |
| `/private/tmp/graf-t112-native-normal-invocation-20261117-collection.log` | `dc71166a2b0e6f99e897ae0756b77cc6a207ab012307de1489c88c312087cf3a` |
| `/private/tmp/graf-t112-native-normal-invocation-20261117-collection.json` | `86a9923ea2663c3979b480ab3d2bcda3e68e19d595c310f4675d9e96750b285d` |
| `/private/tmp/graf-t112-native-normal-invocation-20261117-native.log` | `1b4fe28a50b536b4c3b79f4bcc7bd4cc340cee5aa484dcd58c6c0415d84bceb6` |
| `/private/tmp/graf-t112-native-normal-invocation-20261117-native.json` | `9596a6f698a9d4cb46bdaacabf06823dc7b4e8537324d83c768fce985aa671bf` |

## Предел и следующий вопрос

Нормальная цепочка в данном новом изолированном опыте принята автором по
первичным метаданным и неизменным native assertions. Нет причинного A/B,
поэтому global tracing/нагрузка причинами старых отказов не объявляются.
Положительный результат не исправляет задним числом V4/0proofs или прежний
normal POST2. Данный допуск использован; нового normal/True/M1/87 не назначать
автоматически. Следующий шаг — независимое чтение результата и отдельный
проект необходимого fault/M1 опыта либо иной конкретной проверки по evidence.

Это не проверка browser/native видимости результата, выпуска/эксплуатации,
T098/T113/restore/readiness/T0 или внешнего происхождения аккаунтов.
Рабочее измерение, новые визиты/регистрации и коммерческие критерии остаются
открытыми; неизвестные числа не становятся нулём. Публичная Метрика здесь
не читалась и не объявляется выключенной. Tasks/issue не закрывались.
