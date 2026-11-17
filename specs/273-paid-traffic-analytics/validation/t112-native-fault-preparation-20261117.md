# T112: подготовка одного fault/M1-опыта

17.11.2026. F273/T112/#7698, T113/#7804, `high-risk-product`.
Основа: `734ffb1509e88e7ea0f2f59bc19b4f3e48e23cde`, отдельная ветка
`codex/f273-result-visibility-20261116`.

## Выполнено

Получен действительный независимый FINAL по уже завершённому normal и проекту
одного следующего `[True]`. Отчёт полностью прочитан, SHA-256 сверена:
`t112-native-normal-review-next-design-20261117.md`,
`8d9d703f64bd4600b2c5f768cadb4e23715463e8149e082492767c65289e7ce6`.
Normal принят как один законченный опыт, P1/P2=0. Не выполнялся повтор normal;
исторический repeated HOLD этим не объяснён.

Созданы два инертных файла вне обычного набора тестов:

| Файл | Текущий SHA-256 |
| --- | --- |
| `t112-native-fault-probe-20261117.py` | `a2f7477e7e69753377bb740887cb87cb7cbb66f53aedffbf756bebb353d6aea5` |
| `t112-native-fault-selfcheck-20261117.py` | `32ce83875d8deb45eca94a1c6380a39321523df6d6367fe27122d091189304e5` |

Probe — полный неизменный префикс исходного integration и 26 перечисленных
обратимых преобразований только последнего native-теста. Сохраняются все
45 исходных await, SQL, callbacks/assertions/порядок, два POST, настоящий
импортированный relay, pool2/overflow0, warmup, original Timeout и cleanup.
True-only helper не исполняется при импорте. Наблюдение не читает proof/body/
строки БД/ID/PID/частный текст и не меняет code/runtime.

Сводка M1 фиксирует исходный COMMIT, закрытый target gate/настоящий held chunk,
pending/non-cancelling target, две durable строки/backend idle/noTX/locks0 и
здоровый F того же pool. Полная точка требуется до отмены и строго внутри
первоначального `min(work_deadline-.1, entry_now+.9)`. Имеющийся Timeout
возвращается по идентичности после чтения `.when()`. Нет новых SQL/await/
задач/listeners/глобальной трассировки/сна/повтора/нового GET/proof.

После M1 сохраняются исходные unavailable/полный ASGI response,
invalidate→checkin(None), завершение старого поколения до gate.set,
здоровые B/F и POST2 reconciliation без переписывания пары. До48 подробных
записей; фиксированные сводки независимы от cap. Snapshot — первое действие
явного finally до rescue, с копией накопленной M1. Он не называется снимком
до всех внутренних context-manager cleanup.

## Проверки и независимый разбор

Pure selfcheck завершился EXIT0 без HTTP/SQL/PG. Команда из корня:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/server/src:apps/server \
/Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python \
specs/273-paid-traffic-analytics/validation/t112-native-fault-selfcheck-20261117.py \
apps/server/tests/contract/test_result_view_http_integration.py \
specs/273-paid-traffic-analytics/validation/t112-native-fault-probe-20261117.py
```

Подтверждены побайтовое/AST восстановление исходника и45 await, отбрасывание
трёх исходных мутаций, identity/args/error/cancel/ContextVar/ASGI/parser,
cap/partial/frozen snapshots, тот же Timeout/when с одним вычислением,
полная/неполная/поздняя M1, отсутствие target/backend, отмена, занятые locks,
поздний observer error и прочие отрицательные условия. Это проверка логики
наблюдения на искусственных объектах, не causal PostgreSQL PASS.

Получен и полностью прочитан действительный независимый implementation FINAL
`t112-native-fault-implementation-review-20261117.md`, SHA-256
`8d30108aeba81f5af022523959cc38e6066b8f9bab57085a76b78b834d848384`:
SCOPED IMPLEMENTATION PASS, P1/P2=0. Независимо восстановлены26 преобразований,
45 await,18 SAME и четыре checklist124/0; метки reviewer не менялись.
**Этот FINAL привязан к первоначальному selfcheck74fe6bea…**, не к32ce8387….

После FINAL Ruff обнаружил21 E701 только в однострочных ветвях selfcheck.
Они разбиты на две строки без изменения AST; буквальное AST-сравнение до/после
PASS. Probe не менялся. Итоговый Ruff selfcheck PASS, итоговый pure selfcheck
повторён из-за этой правки и снова EXIT0. Новое заключение по окончательному
хешу selfcheck ещё не получено. Предыдущее ревью не переименовывается в новое.

## Следующий отдельный допуск

Подготовлен, но НЕ исполнен инертный рецепт:
`/private/tmp/graf-t112-native-fault-invocation-20261117.py`, SHA-256
`60af34b12a06eae3020e86fad0bb5ff77867737adbe261bfb580d22005ab4312`.
В нём13 pins (два новых файла, семь source/runner, четыре зависимости), один
новый полный `[True]`, `-p tests.conftest`, раздельные collection/native,
новые exclusive logs/receipts/TEMP и запрет перезаписи. Общая venv без sync,
assertions включены, нет pytest additions; native заново требует>=80GB.
Последнее чтение места93330620416байт, это не будущая проверка перед запуском.

Нужны по порядку: независимая точная повторная приёмка только форматирования
selfcheck32ce8387… с неизменным probe; затем отдельный invocation FINAL
рецепта60af34b1…; затем один collect-only и полная приёмка его квитанции;
только затем отдельно один native. Команда требует m1.valid=true и полный
scenario_complete сверх exit0; основной агент разбирает все первичные границы.
Ни одного из этих новых PostgreSQL/collection шагов пока не было.

Запрос на следующий независимый разбор подготовлен в закрытом временном файле
`/private/tmp/graf-t112-native-fault-next-review-request-20261117.txt`.
Наличие файла не является подтверждением доставки или живого ожидания.
Новое фактическое поручение и FINAL надо получить; не выдавать прежний
implementation PASS за окончательный допуск новой команды.

Настоящий ingest `_result_period_context` сохраняет `yield None`.
Postal — почта ГРАФ; настроек Stalwart/почты не меняли. Код сервера,
исходные integration/budget, требования, checklist, `changes/` и рабочие
службы/аналитика не менялись. Контент/вёрстка, Full/CD, T0, публикации,
внешний трафик/регистрации/продажи этим результатом не подтверждаются.
T112/T113/T098/restore/readiness/исторический repeated HOLD остаются открытыми.
