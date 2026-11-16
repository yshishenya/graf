# T112 — что public Pool.close доказывает до checkout

16.11.2026. Основной исполнитель, исходник
`c420927a7633596ca392799b61e46022ae7234d2`.
Полоса: read-only investigation с сохранением отчёта, существующая F273/T112.
Это уточнение доказательств для независимого baseline review и будущего
проекта, не самостоятельный допуск runtime исправления.

## Подтверждённый порядок

В установленном SQLAlchemy2.0.51 прочитаны `pool/base.py:708–896`, публичные
интерфейсы `base.py:475–631`, `pool/events.py:262–363`,
`pool/impl.py:143–180,220–229` и `connectors/asyncio.py:397–425`.

1. Checkout сначала извлекает entry из очереди, затем вызывает
   `entry.get_connection()`. Proxy и его weakref создаются только после
   успешного возврата. Поэтому `in_use=False` при замене поколения означает
   отсутствие выданного proxy; это не публичный признак наличия entry в очереди
   и не самостоятельное доказательство владения текущего запроса.
2. При устаревшем поколении `get_connection()` вызывает закрытие старого
   DBAPI с terminate=True. Public Pool.close передаёт exact DBAPI и entry
   **до** native закрытия; после него библиотека очищает DBAPI, info и
   создаёт новое поколение. В callback старые DBAPI/native driver ещё доступны.
3. Однако тот же public Pool.close вызывается обычным `entry.close()`.
   Например, QueuePool.dispose извлекает свободные entries и закрывает их;
   overflow return также закрывает entry. Событие не передаёт причину закрытия,
   признак reservation или checkout proxy. Нельзя объявлять каждый close с
   `in_use=False` заменой поколения для текущего auth.
4. Public `info` относится к физическому DBAPI поколению и очищается при
   замене; `record_info` сохраняется на протяжении жизни slot. Одна identity
   entry или запись в record_info не доказывает identity старого driver.
5. Вызов adapter.terminate внутри greenlet сначала ждёт shielded graceful
   close. Это объясняет достижимую стадию исходного опыта, но не доказывает,
   что новый terminate после начала native close закончит оставшуюся задачу.
   Предотвращение ожидания до close и отмена уже начатого close — разные пути.

## Что доказано опытом, а не одним callback

В [законченной паре normal/fault](t112-pool-return-validation-20261116.md)
точный slot T выбран причинной подготовкой пула: два других slot удержаны,
настоящее pre-ping invalidation уже случилось, старый T остаётся единственным
свободным entry. Наблюдатели знают exact DBAPI/driver/PID/stream, auth root,
task и Context. Эта информация доказывает причинность конкретного стенда.
Она не возникает автоматически в runtime от установки обработчика Pool.close.

В guard сейчас нет Pool.close listener: он получает обычный lease только при
connect/checkout; до замены старого поколения такого lease ещё нет. Существующие
C1 hard invalidate(None), initialization и CancelledError ветви нельзя просто
перенести на новый callback, убрав проверку in_use. Их область доказательства
иная. Ни C1, ни итоговый233 этим чтением не пересматриваются.

## Следствие для независимого проекта

Проект должен назвать достаточное публичное основание для действия над exact
старым поколением в текущем auth root/task/Context и объяснить сохранность
чужих, initialization и уже привязанных к transaction ресурсов. Отсутствие
ключей в entry.info и in_use=False по отдельности такого основания не дают.
Если проект использует намерение библиотеки закрыть idle поколение как
основание, он должен назвать этот смысл прямо, а не объявлять отсутствующий
request lease существующим. Необходимость изменения требований определяется
ревью; этот отчёт её не предрешает.

Нельзя добавлять private timestamps, frame inspection, подмену library methods,
retry или глобальное завершение owner children. SQLAlchemy должна закончить
собственный checkin/DBAPI bookkeeping. Runtime patch остаётся за отдельным
независимым допуском. Новый набор dispose/overflow опытов без реального HTTP
caller не требуется только из-за этой source-сверки: они приведены для
разграничения смысла public события, не как новые продуктовые сценарии.

Повторный поиск `.dispose(` / `.invalidate(` / `invalidate_pool_on_disconnect`
в auth, db и текущем guard нашёл dispose только в migrations/env.py, не в
исследованном auth/renewal HTTP пути. Это ограниченный поиск исходников,
не доказательство отсутствия произвольного caller во всём приложении.

## Контроль исходников

| Исходник | SHA-256 |
| --- | --- |
| SQLAlchemy pool/base.py | `5dbe91e32ec424f1e4cfee5db84896b96cfb23c601020e291d0a6644ff50883f` |
| SQLAlchemy pool/events.py | `1666b612f525f177db9cf118b116266ab46dba66099a9153131c6f3b86e63a69` |
| SQLAlchemy pool/impl.py | `ed1388cb028150edad2a85542d99808f819d1e7e8033bb19bf60e22ecbbb320a` |
| SQLAlchemy connectors/asyncio.py | `44d173217bfaf38174149b84d396bed502bf769a98ad41f022269408edf69f9b` |
| GRAF api/product_analytics_guard.py | `eda3d18801b09b742ac3c21ac7bae6f68665dee7252f7074e100baa06e94ef14` |

После этой source-сверки получен отдельный reviewer addendum в
[preflight](t112-pool-return-preflight-20261116.md), SHA-256
`b3d65ee4365f506fd66da3ad0a35aae0e20eba3abcee3657606273acd83afd96`.
Он независимо принял baseline как P1-R1 и отдельно допустил минимальный
проект, опирающийся именно на решение пула физически закрыть idle поколение.
Recycle-specific reservation через этот public callback оставлен HOLD.
Основной исполнитель прочитал весь addendum до runtime изменения. Настоящий
отчёт сохраняет исходные ограничения; результаты реализации записываются
отдельно. Само source-чтение не запускало тестов/контейнеров и не меняло
runtime или рабочие настройки. T112/T113/измерение/T0 и вся цель открыты.
