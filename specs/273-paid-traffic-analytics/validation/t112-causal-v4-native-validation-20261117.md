# T112 — единственный адресный опыт V4 после повторного ревью

17.11.2026, автор `/root`. Существующая полоса F273 `high-risk-product`, T112/#7698 и T113/#7804. Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`, исходный HEAD `eef65dc7082d5fe40156829376b32e3e8af747e3` с узкой правкой диагностического observer.

## Допуск и исправление

[Первое независимое ревью](t112-causal-v4-review-20261117.md) нашло P2-V4-01: trace читал `response_bytes` до присваивания в guard:569. На историческом observer получен точный RED `KeyError: 'response_bytes'`; ранняя фильтрация событий и `local.get` для частичных locals дали GREEN8, без сети и БД. Новый [selfcheck](t112-causal-trace-selfcheck-20261117.py) покрывает сам trace, в отличие от прежних10 случаев adapter/post. Эти наборы не суммируются как HTTP/PG-приёмка.

[Повторное независимое ревью](t112-causal-v4-rereview-20261117.md), SHA-256 `27dbc1f22c692c150417aef6d7aedd890eccb8fa698db65db27736b65291bbfc`, получено FINAL и полностью прочитано **до запуска**: scoped PASS/P1=0/P2=0, P2-V4-01 CLOSED. Допущен ровно один опыт двух native-параметризаций с исправленным [observer](t112-causal-trace-v4-20261117.py), SHA-256 `0117e4001c7066931873233b3a480732885a91eafbfcde1b37660058afa66d40`. Историческая внешняя V4 `57f5b851…` не запускалась повторно.

## Исполнение и факты

Временная побайтовая копия принятого observer установлена как `apps/server/graf_t112_causal_trace_v4.py`; отсутствие прежнего файла проверено, SHA до запуска подтверждён. Штатный runner выполнялся с существующей shared venv, `UV_NO_SYNC=1`, `GRAF_TEST_WORKERS=1`:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -vv -s -p graf_t112_causal_trace_v4 tests/contract/test_result_view_http_integration.py::test_real_commit_acknowledgement_and_idle_return_keep_pair_and_foreign_generation
```

Реальный результат: **2 FAIL, EXIT1**, один warning; pytest15.85s, фаза runner21s, внешний процесс26.322s. Выборка ровно2, digest `0563dc20ccd9f4e252750b47a93930f1c7094796294ce65c7587a500e73ce64e`. Warning — уже импортированный `tests.fixtures.postgres_test_database`, для которого pytest не переписывает asserts; это не объяснение отказа.

Обе параметризации остановились на исходной integration:1159: GET detail вернул HTTP200, но извлечение подтверждений показа дало0 вместо2. Это предшествует созданию observer task, COMMIT-сценарию и обоим POST. В каждом диагностическом выводе только `native_exception AssertionError` на1159 и `scenario_before_finally`; post_enter, M1 и guard records отсутствуют. Normal snapshot7.239948s, fault3.791994s; entered=False, target/deadlines отсутствуют, watchdog=False. Буфер не переполнен: по2 записи, dropped отсутствует; tracer_restored=True в обоих случаях.

Следовательно, задуманные normal POST2 и fault POST1 **не достигнуты**. Этот опыт не объясняет исторический repeated unavailable, отсутствие завершённого ASGI-ответа или response_held timeout. Он не доказывает, что причиной стала стоимость tracing, нагрузка или рабочий дефект. Причина отсутствия proofs здесь не установлена. Нового повторного запуска, общего87 или изменения runtime по этому результату не выполнялось. Следующий диагностический проект должен объяснить раннюю предпосылку и уменьшать вмешательство; новый опыт потребует собственного точного допуска.

## Происхождение и очистка

- Исходный локальный журнал `/private/tmp/graf-t112-causal-v4-native-20261117.log`, SHA-256 `491c3a92b389ccba146e9a85552942807e22ea8fee753ad85eaf9a1c784e7ada`. Он содержит обычный развёрнутый pytest failure с синтетической страницей/сессией и **не включается в Git**; цитируются только числовые метаданные. Сам plugin не выводил тело/headers/proof/SQL.
- Receipt `/private/tmp/graf-t112-causal-v4-native-20261117.json` записан непосредственно wrapper после завершения subprocess, не транскрипция.
- Извлечённые два диагностических объекта `/private/tmp/graf-t112-causal-v4-native-metadata-20261117.json`, SHA-256 `52096a596702fe6846aa08d6360c516f00154d2d9ecf64287bd573630a7d7d33`; только metadata/counters.
- Штатный runner подтвердил `postgres_test_cleanup=isolated_container_removed`. Он создавал только собственный ephemeral PostgreSQL17-alpine в tmpfs/loopback; иных контейнеров не менял.
- Wrapper сверил SHA временного plugin и снял только эту копию в finally; `temporary_plugin_removed=true`. Сохранённый observer и все исходные отчёты остались.

Runtime `apps/server/src`, `changes`, native integration/budget и сроки2s/work1.5s/cleanup0.5s не менялись. Настоящий `ingest._result_period_context` остаётся `yield None`. Почта ГРАФ — Postal. Production, контент/вёрстка, настройки, внешние события, PR/merge/CD не затронуты.

**Unknown repeated HOLD, полная T112/T113/T098/restore/readiness/T0 и коммерческие критерии остаются открытыми.** Исправлен собственный дефект диагностики и закончена одна разрешённая попытка; работающий сбор или внешний трафик этим не приняты.
