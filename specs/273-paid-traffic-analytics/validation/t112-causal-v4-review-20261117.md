# T112 — независимое статическое ревью причинного observer V4

17.11.2026. Проверяющий `/root/public_counter_readiness_review`. F273/T112/#7698, T113/#7804; существующая полоса `high-risk-product`. Копия `/private/tmp/graf-f273-result-visibility-20261116`, HEAD `eef65dc7082d5fe40156829376b32e3e8af747e3`. Область записи — только этот новый отчёт. Код, прежние отчёты, требования/план/задачи, reviewer-owned checklist, Git/GitHub, службы и чужие изменения не менялись. Observer, selfcheck и приложение не исполнялись; HTTP/PG, тесты и новые агенты не запускались.

## Решение

**V4 DIAGNOSTIC HOLD, P1=0/P2=1 — P2-V4-01.** В текущем trace есть детерминированно достижимое чтение ещё не присвоенной локальной переменной guard. Наблюдатель может сам выбросить KeyError и изменить исход приложения. До узкого исправления и статического повторного чтения конкретной версии адресный опыт двух native параметризаций не допущен. Новый общий87 не назначен.

Прежние **P2-D01/V3 CLOSED и P2-01 checkout/checkin CLOSED** не пересматриваются этим замечанием. Unknown repeated HOLD, полная приёмка T112/T113/T098, восстановление, T0 и коммерческие критерии остаются открытыми. Этот статический дефект новой V4 не является установленной причиной исторических HTTP-отказов: V4 с HTTP/PG ещё не исполнялась.

## Точные входы и происхождение доказательств

| Материал | SHA-256 |
| --- | --- |
| V4 `/private/tmp/graf-t112-causal-trace-v4-20261117.py` и побайтово равный сохранённый `validation/t112-causal-trace-v4-20261117.py` | `57f5b85170a858c8cea6890974d4073dd6fb494745a0122e149cf00d566ec846` |
| Selfcheck `/private/tmp/graf-t112-causal-adapter-selfcheck-20261117.py` и побайтово равный сохранённый `validation/t112-causal-adapter-selfcheck-20261117.py` | `3cc53c8f8463c9475ce57b4124bbcd1d37d1bb48568512bbfc998c0720d09732` |
| Receipt `/private/tmp/graf-t112-causal-adapter-selfcheck-20261117.json` | `15bf89eea62dd1698af0e20836fcd1b9013f16f714501e8a5775a74c2b26d129` |
| Авторский `validation/t112-causal-v4-draft-validation-20261117.md` | `4af745a06be24c8f1d4bd92d5d9153a26d86950743e349a0e4cc01bfdd6d4569` |
| Integration `apps/server/tests/contract/test_result_view_http_integration.py` | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| Budget/relay `apps/server/tests/contract/test_result_view_http_budget.py` | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |
| Guard `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |
| Ingest `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `69a930d6b63465c774ff4452e9d289b5937313641dd50d236d8820a5ed7f1795` |

Поручение, V4, selfcheck, receipt и авторский draft-report прочитаны целиком. Три source pins самостоятельно сверены с текущими файлами. Прочитаны применимые строки guard/relay/native observer/finally; исходные требования и предыдущий проект доступны из собственного чтения в том же диалоге. Runtime под `apps/server/src` и `changes` не отличаются от checkpoint `237d368b94c61908f853262ec1be545504951dc8` по Git diff.

Receipt открыто называет себя транскрипцией завершённого вывода инструмента, не перенаправленным исходным журналом. Он сообщает EXIT0 и `causal_adapter_selfcheck=PASS cases=10 network_calls=0 database_calls=0`, с совпавшими hashes. Проверяющий не присутствовал при исходном исполнении и не повторял его. Самостоятельно прочитанный скрипт подтверждает границы проверки: из AST извлекаются только append/task_state/snapshot/transport_init/post; fixture и trace вообще не исполняются. Десять случаев относятся к делегированию/исключениям/ContextVar/cap, не к trace lines или реальному guard.

## P2-V4-01 — trace читает response_bytes до присваивания

V4:148 включает line events выбранного guard-frame. Затем V4:150–172 строит data **для каждого события этого frame**, и только V4:173 проверяет, выбран ли конкретный номер строки. В V4:165 достаточно наличия messages, после чего V4:167 безусловно читает `local["response_bytes"]`.

Закреплённый рабочий guard выполняет две отдельные строки:

```python
568: messages = []
569: response_bytes = 0
```

Line event для569 происходит до выполнения присваивания569. К этому моменту messages уже существует, а response_bytes ещё не присвоена. Поэтому trace входит в ветвь V4:165 и получает KeyError в V4:167. То, что569 не входит в guard_lines, не защищает: фильтр применяется после опасного чтения. Отклонение затрагивает выбранный fault POST1 либо normal POST2, если они доходят до этого места. Оно может повредить наблюдаемый запрос и отключить tracing вследствие ошибки trace callback.

Это прямое статическое следствие порядка строк, без исполнения отрицательного опыта. Selfcheck10 не может его опровергнуть: функция trace не извлечена и не проверяется. Ошибка принадлежит наблюдателю V4, а не принятому рабочему коду. Нет оснований исправлять guard или менять его сроки/порядок присваиваний ради диагностики.

Минимальная допустимая правка V4: **до построения metadata** отсеивать неиспользуемые события/строки; читать зависимые локальные значения только после проверки их наличия. Exception events также могут возникнуть до полной инициализации locals, поэтому для них отсутствие response_bytes должно означать неизвестное значение/отсутствующее поле, а не собственное исключение. Не использовать широкий catch с сокрытием дефекта и не подменять response приложения. Сохранять точные branch markers, срок, исходные исключения и делегирование. После исправления нужен точный статический rereview. Исполнитель может отдельно проверить synthetic trace-frame с messages без response_bytes без HTTP/PG; это не поручение проверяющему запускать код и не разрешение общего профиля.

## Что соответствует проекту вне находки

- Fixture ограничена точным native test и обеими параметризациями; подробный HTTP trace выбирает normal POST2 и fault POST1/достигнутый POST2. Wrapper вызывает исходный post один раз, сохраняет response/исключение/отмену и сбрасывает ContextVar. Дополнительных HTTP/SQL вызовов нет.
- Source pins проверяются до установки tracer. Выбраны исходные code objects guard/operation/unavailable/join и test-only сценария/observer/commit/relay/watchdog. Coroutine return не выдаётся за окончательное завершение. Не меняются методы приложения, native driver, DB/Session/Pool или условия теста.
- Внешний ASGI adapter сохраняет исходные scope/receive и объекты сообщений, различает send attempted/completed и app return/raise. Ошибка/отмена send либо app распространяется. Body, headers, URL, proof, SQL payload и тексты исключений не выводятся; HTTP-ответ не декодируется. Подтверждённый узкий принцип V3 сохранён.
- Независимый observer/relay не требуют HTTP ContextVar и сохраняют исходный пустой Context(). Сопоставление target stream выполняется по identity в существующем списке сценария; в записи идут ordinal и примитивные снимки. Фактический аргумент when настоящего timeout_at фиксируется только при caller observer, без замены timeout и без повторного расчёта min.
- Snapshot scenario:1271 расположен перед `armed=False`, отменой watchdog, открытием gates и отменой задач. Exception event observer также снимается до этой finally. Порядок подтверждён текущими исходными строками. Снимок содержит task done/cancelling, но не сами task/frame/owner/exception объекты в records.
- Буфер ограничен96; counts/dropped и relay_counts сохраняются отдельно. Relay ordinals1–4 различимы; ordinal5 в relay_counts объединяет все последующие, тогда как подробные записи используют настоящий ordinal. Это предел агрегата, не доказательство тождества поздних поколений.

## Ограничения будущей интерпретации

Расположение меток в relay имеет смысл **до выполнения соответствующей строки**: например142 означает вход перед response_held.set, а143 с snapshot response_held=True подтверждает последующий этап. Строка138 следует за фактическим upstream read, но не доказывает COMMIT acknowledgement; прежний независимый M1-снимок по-прежнему необходим. Внешний adapter, напротив, явно фиксирует attempted до await send и completed после его возврата.

Даже после исправления P2-V4-01 global sys.settrace получает вызовы и выбранные frames получают line events на всех своих строках; фильтрация ограничивает запись, но не убирает стоимость доставки этих событий. Сейчас scenario также обновляет state на всех line events. Диагностический timeout не доказывает причину исторического untraced отказа. Не увеличивать2s/work1.5s/cleanup0.5s, lock/SQL caps, не удалять F/B/assertions и не менять Context() ради наблюдения.

Отдельного защищённого terminal snapshot вне96 records текущий вывод не содержит: counters сохраняют частоты, но не последние deadline/branch данные. При dropped>0 существенная поздняя запись, включая POST2/снимок до finally, может отсутствовать; такой результат нельзя считать полной причинной цепочкой. Не объявлять неизвестную причину установленной и не повторять профиль до PASS. При недостигнутой ветви, невоспроизведённом симптоме или изменившемся source pin вывод также остаётся ограниченным. Текущий HOLD уже достаточен для запрета запуска; этих ограничений нельзя лишиться при узком исправлении.

## Требования и границы завершения

Самостоятельно сверены все18 unchanged_inputs карты `/private/tmp/graf-t112-root-history-reading-20261116.json`: **18SAME**. Повторно прочитаны все текущие вопросы четырёх reviewer-owned checklist: requirements16/0, security27/0, privacy-measurement52/0, infra29/0, итого **124 checked/0 unchecked**. Отметки и предыдущие review-records не менялись. Эти totals подтверждают состояние требований, не HTTP/PG или выпускную приёмку.

Настоящий ingest._result_period_context:181–188 по-прежнему `yield None`; это не утверждение об отключении всей публичной Метрики. Postal остаётся почтой ГРАФ. Опубликованный выпуск/runtime/provider и отчёт Метрики здесь не проверялись; публикаций/внешних событий/CD не было. Unknown repeated HOLD, полные T112/T113/T098/restore/T0 и коммерческие критерии сохраняются открытыми. Новый87 не назначен; адресный опыт двух native параметризаций — только после устранения находки и конкретного PASS будущей точной версии.

**Итог: V4 DIAGNOSTIC HOLD/P1=0/P2=1 (P2-V4-01), без исполнения.**
