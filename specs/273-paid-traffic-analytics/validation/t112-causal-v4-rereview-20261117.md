# T112 — независимое повторное ревью P2-V4-01

17.11.2026. Проверяющий `/root/public_counter_readiness_review`. F273/T112/#7698, T113/#7804; существующая полоса `high-risk-product`. Копия `/private/tmp/graf-f273-result-visibility-20261116`, HEAD `eef65dc7082d5fe40156829376b32e3e8af747e3` с узкой незакоммиченной правкой observer и новым selfcheck. Прочитано целиком поручение `/private/tmp/graf-t112-causal-v4-rereview-request-20261117.txt`. Написан только этот новый отчёт; код, прежние отчёты, требования/план/tasks, checklist, Git/GitHub, службы и чужие изменения не менялись. Observer, selfcheck, приложение и тесты проверяющим не исполнялись; новых агентов не создавалось.

## Вердикт и допуск

**SCOPED CAUSAL OBSERVER PASS, P1=0/P2=0. P2-V4-01 CLOSED** для точного observer SHA-256 `0117e4001c7066931873233b3a480732885a91eafbfcde1b37660058afa66d40`.

**Один адресный диагностический HTTP/PostgreSQL опыт обеих native-параметризаций допустим по этому reviewer gate**, с этой точной исправленной версией, прежними pinned sources, неизменными fixtures/assertions/F/B и сроками2s/work1.5s/cleanup0.5s. Это только точный test `test_real_commit_acknowledgement_and_idle_return_keep_pair_and_foreign_generation` с fault=False и fault=True, однократно. Новый общий87 не назначен. До исполнения сверить, что загружается исправленный сохранённый observer, а не историческая внешняя V4 с hash57f5b851…; при смене hashes/исходников данный допуск не переносится автоматически.

Допуск наблюдения не снимает unknown repeated HOLD и не является PASS реального HTTP/PG пути, runtime, полной T112/T113/T098, восстановления/T0 или коммерческих критериев. Предыдущие P2-D01/V3 и P2-01 checkout/checkin остаются отдельно CLOSED. Наблюдение в этом ревью не запускалось.

## Сверенные точные материалы

| Материал | SHA-256 |
| --- | --- |
| Исправленный `validation/t112-causal-trace-v4-20261117.py` | `0117e4001c7066931873233b3a480732885a91eafbfcde1b37660058afa66d40` |
| Новый `validation/t112-causal-trace-selfcheck-20261117.py` | `066a58ea03decbd775472f7ae7386c0c0fbfb5572c2490dba3d906ca7c7a98cf` |
| RED `/private/tmp/graf-t112-causal-trace-red-20261117.log` | `4ffccf3de42b9a908fc8b46608f38c9fb8640774e9a279bd55bf147d84f94d28` |
| GREEN `/private/tmp/graf-t112-causal-trace-green-20261117.log` | `63774d663fe650fcda184eb0c378232a17bdf2635979adfa4d226b00f8e46634` |
| Receipt `/private/tmp/graf-t112-causal-trace-selfcheck-20261117.json` | `93eadc4298b1b05dc3ad7e10341a9a1a054ebb6f5abb94cda70de78692e9e84d` |
| Исторический внешний `/private/tmp/graf-t112-causal-trace-v4-20261117.py` | `57f5b85170a858c8cea6890974d4073dd6fb494745a0122e149cf00d566ec846` |
| Неизменённый предыдущий `t112-causal-v4-review-20261117.md` | `76ba14605d54fb867018760986697f95e85ff41d08d1779ff0642c7c5781461d` |
| Guard `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `7f2887f19c69f218d8bd4d27e55d481b46f8769abe5a0a6d36a96c55a0a299d6` |
| Integration `apps/server/tests/contract/test_result_view_http_integration.py` | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| Budget/relay `apps/server/tests/contract/test_result_view_http_budget.py` | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |

## Почему P2-V4-01 закрывается

Точный Git diff содержит шесть добавленных строк ранних проверок и одну замену чтения поля. Перед построением data теперь отсекаются невыбранные line events, события кроме line/exception и StopIteration/StopAsyncIteration. Событие guard:569 с messages=[] проходит ранний выход и не читает ещё не присвоенную response_bytes. На допустимом exception event ранней инициализации `local.get("response_bytes")` даёт None; отсутствие значения не становится KeyError и не превращается в ноль.

Повторно прочитана вся затронутая ветвь trace с контекстом, новый selfcheck и оба журнала/receipt. Остальной observer сохраняет ранее целиком прочитанную реализацию; diff вне указанных строк отсутствует. Нет broad catch, скрывающего ошибки наблюдения, изменений рабочего guard, удаления его проверок, подмены ответов, изменения сроков, Context() или дополнительных запросов. Данные по-прежнему ограничены метаданными, и разбор тела ответа не возвращён.

RED-журнал показывает именно прежний `KeyError: 'response_bytes'` на исторической V4:167 при synthetic frame для guard:569. GREEN-журнал сообщает `causal_trace_selfcheck=PASS cases=8 network_calls=0 database_calls=0`. Receipt содержит совпадающие hashes, RED exit_code1 и GREEN exit_code0; по поручению журналы сохранены из subprocess capture_output. Проверяющий независимо прочитал файлы и сверил их суммы, но не повторял исполнение и не выдаёт чтение receipt за собственный запуск.

Новый скрипт действительно извлекает trace и append/task_state/snapshot из AST. Восемь случаев покрывают невыбранную line569 с messages без response_bytes; exception на той же неполной инициализации; выбранную line590 с отсутствующим счётчиком; выбранную line с полным synthetic body/counter без утечки body; call/return без записи; StopIteration; inactive marker. Он проверяет возврат trace/None, ожидаемые counts/records и отсутствие synthetic private body в записях. Это причинная синтетическая проверка найденного дефекта observer. Она не упражняет реальные guard frames, sys.settrace lifecycle, fixture, HTTP, PostgreSQL и не объясняет исторический отказ.

## Условия интерпретации единственного опыта

Стоимость global tracing/line events остаётся: ранний фильтр уменьшает работу построения metadata, но не отменяет доставку событий. Timeout под trace не устанавливает причину старого untraced timeout. Не расширять исходные сроки, locks/SQL caps, не убирать F/B/assertions и не менять изолированный Context() независимых задач.

Cap96, counts/dropped и relay_counts сохранены. **Отсутствие защищённого terminal snapshot вне96 records известно и не исправлялось этой узкой правкой.** При dropped>0 поздние branch/deadline/POST2 данные могут отсутствовать; такой журнал нельзя считать полной причинной цепочкой. Недостигнутая ветвь, невоспроизведённый симптом, неизвестная первичная причина или изменённый source pin не дают основания назначить причину, снять unknown HOLD либо повторять профиль до PASS. Завершённый результат/первичный журнал/точные hashes и факт очистки изолированного стенда нужно сохранить; диагностический observer после опыта снять. Полная исходная приёмка остаётся отдельной.

## Требования и сохранённые границы

Свежая самостоятельная сверка18 unchanged_inputs карты `/private/tmp/graf-t112-root-history-reading-20261116.json`: **18SAME**. Все124 вопроса checklist перечитаны в непосредственно предшествующем собственном V4 review; hashes сейчас неизменны, актуальный пересчёт подтверждает requirements16/0, security27/0, privacy-measurement52/0, infra29/0 — **124 checked/0 unchecked**. Отметки не менялись; это состояние требований, не приёмка работающего измерения.

Runtime `apps/server/src` и `changes` по-прежнему SAME checkpoint `237d368b94c61908f853262ec1be545504951dc8`. Настоящий `_result_period_context` сохраняет `yield None`; состояние всей публичной Метрики этим не определяется. Postal остаётся почтой ГРАФ. Release/runtime/provider, недельный отчёт Метрики, внешний трафик и продажи здесь не проверялись; публикаций/CD/внешних событий не было. Unknown repeated HOLD и T112/T113/T098/restore/readiness/T0/коммерческие критерии остаются открытыми.

**Итог: P2-V4-01 CLOSED, scoped PASS/P1=0/P2=0; один адресный диагностический опыт двух native-параметризаций допустим, общий87 не назначен и в этом ревью ничего не запускалось.**
