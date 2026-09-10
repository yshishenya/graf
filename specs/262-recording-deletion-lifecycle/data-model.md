# Модель данных и переходов

## Идентичность

- Native `RecordingKey`: нормализованный server origin + workspace_id + creator_user_id + local_recording_id. server origin учитывает среду; секреты не входят.
- Server `RecordingOrigin`: workspace_id + creator_user_id + local_recording_id — существующий уникальный ключ Meeting. device_id задаёт полномочия и размещение копии, но не меняет идентичность записи.
- `meeting_id`: канонический серверный ID после установления связи. Web-only записи используют scope + meeting_id; нативный адаптер связывает alias по серверному подтверждению.
- `media_revision_id` и `local_media_revision_id`: версии материалов; удаление встречи распространяется на все её версии. Идентификаторы версий не должны создавать второй пользовательский объект.
- Название, дата, длина файла и положение в списке не являются identity.
- `ExecutionScope`: server origin + workspace + authenticated actor_user_id; отдельно от target creator. Pending операция возобновляется только прежним исполнителем с актуальными правами. Управляющий может удалить чужую разрешённую встречу по meeting_id, но не отменять чужой origin через owner-only маршрут.
- Новые пакеты без входа имеют `local_unbound`: известные installation/channel и локальный пользователь Mac, `serverCreationAttempted=false`. Им разрешены local play/delete. `legacy_unknown` — происхождение не доказано, доступно только восстановление; это другое состояние.

## Сохраняемые сущности

### Существующий DesktopUploadQueueDocument и его items

В документ добавляется одна коллекция deletionOperations по scoped RecordingKey, включая server-only записи без локального пакета. В ней единственное состояние intent/receipt; item не хранит дублирующую deletion machine. Переиспользуются id, directoryId, serverTruth, syncGeneration, syncConflictState, retentionDecision. Добавляются ограниченные поля (точные Swift имена определяются при реализации):

| Поле | Назначение |
|---|---|
| item.ownerScope | server origin, workspace, creator; для новой standalone local-only записи — доверенный локальный профиль Mac до явной привязки; nil только legacy/unknown и запрещает автоматические действия |
| serverCreationAttempted | Долговечно записан до первого create; различает никогда не отправлявшуюся запись и неизвестный ответ |
| document.deletionOperations | operation UUID, executionScope, отдельный target identity (origin или meeting_id), phase, requestedAt, nextAttemptAt, bounded reason, receipt ID; без аудио/транскрипта/токенов |
| operation.acceptedDeletion | Авторитетный receipt/request ID, identity, server deletion epoch при наличии; сохраняется монотонно и используется всеми items с этим identity |
| lifecycleGeneration | Локальное поколение для отказа от устаревших callback; желательно уточнить семантику существующего syncGeneration, а не вводить второй счётчик без необходимости |

Расширение формата декодируется явно. Unknown enum/schema не переводится молча в live; поддерживаемая миграция сохраняет исходный файл и все tombstones. Весь документ сохраняется атомарно существующим механизмом защиты. Файловый purge не считается успешно начатым, пока intent/tombstone не сохранён.

Bulk сначала атомарно сохраняет весь допущенный набор операций и immutable targets, затем отправляет запросы. При ошибке этого сохранения не начинает ни одну операцию. Удаление аудиопакета не удаляет operation/accepted tombstone. Pending operations сохраняются до определённого результата; accepted markers удерживаются для предотвращения rescan/restore resurrection.

### Существующие Meeting / DeletionRequest / PurgeJournal / LocalPurgeTask

Остаются источниками серверного удаления, физических попыток и результата по устройствам. `Meeting.deletion_epoch` остаётся барьером для late upload/finalize/processing. Не вводить второй статус серверного удаления в отдельном сервисе.

### Новый минимальный RecordingOriginCancellation

Только для origin, для которого Meeting ещё не создан: workspace_id, creator_user_id, local_recording_id, cancellation_id, accepted_at, actor/device audit identity. Unique по origin, RLS по workspace и owner; отсутствие Meeting допустимо. Нет названия, длительности, содержимого, media revision, upload status, тела create.

Это отрицательная запись «этот origin нельзя создавать», а не фиктивная встреча. Удаление существующей Meeting использует её tombstone без обязательного дубля cancellation. Marker не удаляется по короткому TTL: иначе поздний create или старый клиент воскресит запись. Срок хранения минимальных идентификаторов согласуется с действующей политикой lifecycle/audit перед выпуском; политика не должна разрешать повторное использование origin.

Receipt имеет тип `meeting_deletion` либо `origin_cancellation`. Для второго сервер подтверждает только запрет создания (`server_content=never_created`); local cleanup result хранится в native operation, без фиктивных LocalPurgeTask/DeletionRequest с отсутствующим meeting_id. Отчёт данного случая собирает server cancellation receipt и результат именно текущего Mac. Гарантия отчёта о произвольных копиях на других устройствах не заявляется. Обычные встречные удаления используют существующий многоприборный report/task/ACK.

## Независимые оси состояния

| Ось | Состояния |
|---|---|
| Размещение/передача | local_only, create_unresolved, uploading, linked_server, material_missing |
| Обработка | Существующие processing/summary статусы без переписывания |
| Доступ | allowed, unknown, denied |
| Запрос удаления | none, queued, sending, resolving, accepted, rejected |
| Физическая очистка | not_required, pending, running, failed_retryable, verified, unverified |

`accepted` и `verified` не объединяются. При accepted запись скрыта/заблокирована независимо от физических файлов. При queued/sending/resolving отображается недоступная строка ожидания до принятия, а не открываемая запись. После явного rejected можно снять только барьер этой непринятой операции; доступность пересчитывается по правам. Старый live ответ никогда не снимает acceptedDeletion.

## Приоритет правил

1. Неверный/неизвестный контекст исполнения: не раскрывать контент и не выполнять команды за другой аккаунт. Target creator не обязан совпадать с actor для разрешённого manager-delete по meeting_id. Local_unbound имеет свой доверенный локальный контекст; legacy_unknown — только восстановление.
2. acceptedDeletion либо authoritative deleting/deleted: исключить из обычной выдачи, остановить управляемый playback, запретить upload/retry/export/generation; оставить metadata-only результат очистки.
3. Незавершённое подтверждённое пользователем намерение: запретить новый upload/open, показать ожидающее удаление; выполнить только разрешение/повтор самой операции.
4. Явный denied: убрать доступный контент, показать/сохранить безопасный результат отказа без purge на основании 403/404.
5. Active capture/saving: сохранить Stop, запретить delete до завершения, не менять захват из операции списка.
6. Остальные состояния: вычислить единые canSelect/canDelete/canOpen/canSend и причину недоступности из подтверждённых фактов и наличия файла.

Представление передаёт capabilities, но при исполнении сервис повторно проверяет состояние. Приоритет удаления действует и если server conflict сообщает metadata/device mismatch, а deletion_state уже terminal.

## Сериализация

### На Mac

Одна последовательная область изменения существующей очереди. Сетевой вызов не держит блокировку. Каждая команда захватывает scope и generation. Intent сохраняется, generation увеличивается, callback старой generation может записать транспортный факт/identity, но не вернуть live статус или разрешённые действия. Любая команда open получает текущую разрешённую playback session, которую инвалидирует deletion/access/scope change. Удаление закрывает session до удаления файлов.

### На сервере

Create и cancel-origin берут одну PostgreSQL transaction-level advisory lock по namespace+origin, затем проверяют cancellation и Meeting. Стабильное хеширование только для lock key; сравнение записи всегда по полному identity. Коллизия хеша может сериализовать разные записи, но не смешать права или данные. Действующий unique constraint остаётся обязательным.

Порядок блокировок: origin lock → Meeting row → deletion/task/report rows. Все create-пути, включая старый API и fallback, проходят общий guard. Cancel существующего объекта вызывает существующий deletion service внутри того же контекста, не удерживая транзакцию во время внешнего I/O.

Если cancel первым зафиксировал marker — поздний create получает terminal conflict. Если create первым создал Meeting — cancel удаляет эту Meeting. Успешный cancel не может сосуществовать с живой Meeting того же origin после commit.

## Восстановление

- Restart: сначала загрузить pending/accepted state, закрыть действия, затем синхронизироваться и очистить; не начинать с processDueItems.
- Legacy: известные server aliases проверить; отсутствие подтверждённого scope не привязывать к текущему аккаунту по умолчанию.
- Повреждённый queue: карантин плюс recovery gate; scan не превращает неизвестный пакет в новую автоматически отправляемую запись.
- Восстановленный пакет с tombstone: остаётся заблокированным, purge повторяется по тому же identity. Намеренный новый импорт пользователем является новой записью и отдельным действием; дедупликация по содержимому не вводится.
- ACK потерян: повторить ACK; это не требует повторять сетевое удаление встречи или считать отсутствующий файл ошибкой.
- Истёкшая задача: разрешить проверенную очистку и поздний ACK по контракту; не заявлять verified по одному календарному сроку.


## Уточнение реализации 2026-09-09

Queue v3 содержит deletionOperations, lastAuthenticatedContext и старые items. ownerScope существует только для подтверждённого серверного аккаунта; isLocalUnbound=true означает новую запись текущего пользователя Mac без серверной привязки. Это отдельный признак доверенного локального происхождения, а не выдуманный серверный scope. Legacy nil/nil не даёт права открыть, отправить или удалить файл.

Для доказанно неотправленной записи (serverCreationAttempted=false, оба meetingId отсутствуют) повторно используется существующий terminalDeleted + retentionDecision: атомарный tombstone до файлового эффекта, localArtifactsRetained=true до проверенной очистки. Такой случай не требует серверной операции/receipt даже при известном ownerScope. Частичная очистка остаётся в разделе состояния; остальные пакеты обрабатываются независимо.

Accepted/verified operation нельзя получить через обычный переход без подходящего receipt; decoder отвергает сохранённый accepted без receipt. Отсутствие локального пакета не переводит origin cancellation в verified. Scope generation отменяет устаревшее согласование; подтверждённый receipt своего прежнего scope может безопасно сохраняться для последующего возвращения в него.

waitReason ограничен перечислением connection/authentication/rateLimit/serverUpdate/localCleanup. Чужие коды, токены и тела ошибок в операцию не записываются. Серверный Retry-After откладывает остальные запросы этого scope. Системный сетевой отказ не запускает 100 последовательных одинаковых таймаутов.
