# T112: независимое ревью реализации инертного fault/M1-прибора

2026-11-17. F273/T112/#7698, T113/#7804. Полоса `high-risk-product`.
Существующий проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`.
Ветка/HEAD из поручения: `codex/f273-result-visibility-20261116`,
`734ffb1509e88e7ea0f2f59bc19b4f3e48e23cde`; Git не вызывался и эти сведения
не выдаются за независимо проверенную Git-публикацию.

## Итог

**SCOPED IMPLEMENTATION PASS. P1: 0. P2: 0.**

Конкретная инертная реализация соответствует принятому проекту одного `[True]`
и сохраняет исходный native-сценарий. Допустимо готовить отдельную команду
запуска и представлять её на независимое invocation review. **Настоящий FINAL
не разрешает запуск True, collection, native, дополнительный normal или 87.**

Принятые ранее normal validation/design/implementation/invocation не
пересматривались. Сам normal повторно не запускался. Следующий runtime-результат
остаётся неизвестным; совпадение кода с проектом и чистый selfcheck не являются
доказательством causal M1.

## Точные входы

| Файл | SHA-256 |
| --- | --- |
| `validation/t112-native-fault-probe-20261117.py` | `a2f7477e7e69753377bb740887cb87cb7cbb66f53aedffbf756bebb353d6aea5` |
| `validation/t112-native-fault-selfcheck-20261117.py` | `74fe6beaa7f60a1368f832866365cce1371c889db22c3bc8385047219b4d595a` |
| `validation/t112-native-normal-review-next-design-20261117.md` | `8d9d703f64bd4600b2c5f768cadb4e23715463e8149e082492767c65289e7ce6` |
| `apps/server/tests/contract/test_result_view_http_integration.py` | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| `apps/server/tests/contract/test_result_view_http_budget.py` | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |

Оба новых файла прочитаны полностью: probe1599 строк, selfcheck665 строк.
Суммы совпали с поручением. Основа и проект проверены в фактических байтах,
не только по сообщённому HEAD. Запусков/импортов probe и selfcheck в этом
ревью не было: использовались чтение, AST, буквальные преобразования строк
и SHA-256. Код функций selfcheck не исполнялся.

## Независимое статическое доказательство сохранения исходника

Из AST selfcheck безопасно извлечён только буквальный список `EDITS`.
Независимым статическим преобразованием, без вызова `restore()` selfcheck,
проверены все **26** вставок/замен в обратном порядке. Каждая точная вставка
найдена один раз; восстановленный исходник совпал с integration **побайтно**,
а его AST совпало с AST исходного модуля.

Префикс перед выбранным последним native-тестом не изменён. Все остальные
тесты/фикстуры/imports/globals в копии буквальны исходнику. В целевом тесте
осталось **45 исходных awaits**. Просмотрены все 26 пары before/after,
включая большую последнюю замену observer: это прежний observer с перечисленными
синхронными метками и прозрачным try/except, а не произвольное удаление тела.
Таким образом сохранены native assertions, SQL, порядок операций и await,
callback conditions, routes/_real_app/http_period, gate.set, budgets, warmup,
пул и cleanup. Доказательство опирается и на полный просмотр diff, поэтому
обратный список не принимается как самодостаточный доверенный нормализатор.

После footer на уровне модуля имеются только две imports, две assignments
(ContextVar и фиксированный набор стадий), одна class definition. Нет main,
HTTP/DB/asyncio.run, автоматического test execution или подмены функций
исходного модуля на уровне импортирования. Исходные pytest decorators остаются
параметризованными False/True; поэтому адресная выборка будущего запуска
обязательна. Другие неизменные тесты из полной копии не разрешены к исполнению.

## Проверка соответствия проекту

| Область | Что подтверждено статически |
| --- | --- |
| True-only | `_FaultObservation.__init__` принимает только `fault is True`; False, None, 0, 1 и строка отвергаются; выборка/фикстуры до конструктора остаются отдельным gate |
| POST | Два исходных bound client.post передаются с прежними args/kwargs ровно в один await; возвращается тот же response; исключение/CancelledError передаются bare raise; ContextVar reset в finally |
| ASGI | Обёрнут только app конкретного ASGITransport; scope/receive/message передаются по идентичности; исходный send вызывается один раз; attempted до await/completed после; app return/raise отдельно |
| Содержимое | Нет чтения response.json/text/body для диагностики; ASGI читаются только type/status/more_body и state deadline; parser вызывается ровно как исходный, его результат возвращается по идентичности |
| Окно M1 | Исходный Timeout создаётся один раз в прежней точке; `window()` читает `.when()` и возвращает тот же объект; min(work_deadline-.1, loop.time()+.9) не пересчитывается и не расширяется |
| Relay | Используется импортированный исходный `_postgres_response_gate`; новой копии/обёртки, callbacks или новых Events для relay нет |
| Observer | Прежний create_task с пустым Context(); метки вызываются явно локальным diag, независимо от request ContextVar; нет новых Task/factory/listeners/trace/stack polling |
| DB | Нет новых SQL или диагностических await/сна; исходный bounded while и запросы pair/activity/locks сохранены; счётчик итераций и последняя завершённая граница обновляются синхронно |
| Очистка | Прежние invalidate/checkin(None), закрытое старое поколение/relay/backend до gate.set, новый B/здоровый F до/после gate и POST2 reconciliation сохранены |
| Вывод | До48 подробных records; счётчики/stages/requests/M1/cleanup/snapshot независимы от cap; один JSON после исходной `_run` cleanup; внешняя runner cleanup принимается отдельно |

### Полнота M1 и сроки

Точные места в probe: observer с1110, `window()` с1458,
`phase()` с1471, формула `valid` с1495, `durable()` с1525.

commit_enter ставится после исходных markers.append/entered.set.
held_observed — после исходного response_held.wait при неизменной семантике
relay: настоящий непустой server→client chunk устанавливает held только при
закрытом target gate перед ожиданием этого gate. Прибор не читает байты
протокола и не объявляет каждый chunk распознанным ответом COMMIT. Серверное
принятие доказывают исходные независимые durable/idle/locks наблюдения.

`durable()` вызывается только внутри исходного успешного условия перед break:
rows2, backend существует idle/no xact, locks0. Сохраняются только числовые и
логические признаки; строки, account/meeting IDs, PID, соединения, owner,
задачи, SQL и private payload в структуры прибора не помещаются.

Метки F окружают только прежний foreign_healthy в observer. m1_complete
снимается после прежних m1_pair/m1_at внутри исходного Timeout. `valid`
требует все обязательные стадии по одному разу и по времени, m1_window1,
успешный исходный commit correlation, commit1/after_commit0, закрытый gate,
held=true, POST pending, task donefalse/cancelling0, watchdogfalse,
положительные исходные M1/work remaining на held/durable/F/completion,
точную durable-сводку и отсутствие observer error. Требование intact
проверяется также после возвращения F и в m1_complete. m1_at<=now<тот же
M1 deadline, m1_at<work_deadline. Пропущенная стадия, неизвестное состояние,
дубликат, поздний срок, открытый gate или отмена не дают valid=true.

Начальные commit_enter/hold_wait_enter не требуют held=true: до прихода
настоящего ответа этот признак ещё не обязан существовать. Их исходный
порядок/целевой stream и неизменная точка закрытия gate проверены по исходнику;
отсутствие held позднее не скрывается и не компенсируется cleanup.

`boundary()` фиксирует последнюю completed query boundary, а не стек/текущий SQL. При
зависании следующего исходного запроса последняя завершённая граница может
оставаться предыдущей; это не следует выдавать за новое DB-доказательство.

### Ошибки, снимок и продолжение

Observer перехватывает BaseException только для type/module и `valid=False`,
затем выполняет bare raise. Первоначальная ошибка, TimeoutError или отмена
не подавляются. Нет ожидания следующего успеха после истечения окна.

Snapshot вызван первым statement исходного явного scenario finally
(probe1299), до armed=False/watchdog.cancel/gate.set/task.cancel/close/dispose.
M1 phases и durable копируются отдельно; поздние observer_error/изменение
текущей M1-сводки после rescue не переписывают сохранённый снимок. cleanup
сводка содержит новый список offsets, который далее исходником не изменяется.
Снимок неполного target/None deadline хранит неизвестность как None либо
snapshot_error type. Он может быть после естественного выхода из внутренних
context managers и не доказывает состояние до всей автоматической очистки.

cleanup_summary снимается после исходных fault assertions: invalidate1 перед
checkin1, returned_none, driver closed и завершённые root/pumps/wait_closed/
writers при закрытом gate. old_backend_checked стоит после прежних DB-проверок
отсутствия backend/locks и равенства saved rows M1-паре. F и новый B получают
прежние native проверки до/после исходного gate.set. Ранний native print всё
ещё до POST2 и не заменяет конец сценария. Второй исходный POST имеет свои
scope deadlines, исходный JSON accepted и полное rows equality; нет третьего
POST, нового GET/proof или повторного исполнения first request.

Guard2s/work1.5s/cleanup0.5s на запрос, SQL<=128, lock<=250ms,
statement<=500ms, body/proof/response caps, pool2/max_overflow0/pre_ping,
два sequential warm connect и watchdog3s сохранены. Watchdog — только исходный
спасательный выход неуспешного теста; его срабатывание исключает приёмку.

## Selfcheck: проверенный код и предел доказательства

Автор сообщил выполненный pure selfcheck EXIT0. В этом ревью он не повторялся;
не заявляется независимый новый executable PASS. Полностью проверены его
665 строк, включая отсутствие запуска тестов/HTTP/DB в main и явную границу
`if __name__ == '__main__'`. Импорт probe из selfcheck создаёт определения,
но не исполняет fixture/native scenario.

Статически подтверждено содержание проверок: hash исходника, точное обратное
восстановление/AST и45 awaits; три отвергаемые мутации assert/await/метки;
True-only; identity args/kwargs/response/ошибки/отмены; ContextVar reset;
ASGI attempted/completed и exception path, отдельные POST deadlines; parser
без чтения proof значений; cap/частичный snapshot/None; тот же Timeout/when
с одним вычислением; полная M1 и пропуски/late/cancelled/done/gate/after_commit/
commit count/durable/backend/locks/observer-error/watchdog/duplicate-F;
сохранение frozen M1-snapshot при позднем rescue изменении текущей сводки.

Selfcheck проверяет логические метаданные на двойниках. Он не доказывает
реально удержанный PostgreSQL chunk, серверный COMMIT, полный native ответ,
реальный request budget, отсутствие утечки или causal M1.

## Обязательные границы следующего шага

Отдельный invocation review должен закрепить новые точные файлы/хеши,
неизменные runtime/runner/dependencies, эксклюзивную временную копию и новые
журналы/квитанции, безопасную среду без pytest additions/Python optimization,
существующую общую venv без sync, reserve>=80GB. Сначала один отдельный
collect-only с ровно одним новым полным `[True]`, expected digest и
container_not_started, явным `-p tests.conftest`, без дополнительного `tests/`.
Только после принятой полной квитанции и отдельного invocation FINAL может
быть назначен один native. Ни команды, ни повторов этот implementation FINAL
не утверждает.

При будущей приёмке **exit0 недостаточно**: `phase()` вычисляет и сохраняет
`m1.valid`, не заменяя исходные native assertions диагностическим assert.
Нужно отдельно принять `m1.valid=true` вместе с полными стадиями и исходными
проверками, complete unavailable ASGI/app/POST1, invalidate→checkin(None),
завершением старого поколения/backend/relay до открытия gate, здоровыми B/F,
POST2 accepted/full saved equality, watchdogfalse и runner cleanup. Частичный
или поздний M1 остаётся HOLD даже если исходный тест когда-либо выйдет с0.
Данные snapshot до rescue и текущая сводка после cleanup различаются по точке
наблюдения; rescue не должен задним числом создавать M1 PASS.

## Требования и неизменённые границы

По document-reading переиспользовано собственное чтение того же диалога:
принятый normal-result/next-design и восстановленные там оригиналы
result-visibility §5, activation-milestones §«Одно решение в PostgreSQL»,
T112 plan/tasks/quickstart, constitution/diagnostic product-gates и
spec-kit-flow. Новых требований/зависимостей продукта не добавлено. Все18
unchanged_inputs карты `/private/tmp/graf-t112-root-history-reading-20261116.json`
свежим hash-сравнением SAME; карта автора подтверждает только байты и не
подменяет собственное чтение проверяющего.

Четыре checklist свежим подсчётом: requirements16/0, security27/0,
privacy-measurement52/0, infra29/0 — **124 отмечено / 0 не отмечено**.
Маркеры не менялись; это не новая приёмка эксплуатационных/коммерческих AC.

Новые probe/selfcheck и все чужие изменения сохранены без правок проверяющего.
Создан только настоящий implementation report. Никаких tests/selfcheck/
collection/HTTP/SQL/PostgreSQL/контейнеров/приложений/Git/GitHub/коммитов/
сети/служб, новых агентов или внешних сообщений в ревью не выполнялось.

Настоящий `_result_period_context` остаётся `yield None`, Postal остаётся
почтой ГРАФ; вся публичная Метрика не объявляется выключенной. Исторический
unknown repeated HOLD, T112/T113/T098, restore/readiness/T0, ручная/native
видимость, внешний трафик/аккаунты и продажи остаются открытыми. Данный PASS
не является release/production/рабочей или коммерческой приёмкой.
