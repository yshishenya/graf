# T112 — независимая проверка блокировок записи результата

Дата: 16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Основа: `46c989b959856c836ab0c2fc5ef0aeb255992a07`.
Полоса проверки: чтение существующих путей записи внутри действующего
`high-risk-product` F273. Изменён только настоящий отчёт. Незавершённые
изменения `product_analytics/ingest.py` и `test_result_view_admission.py`
при входе сохранены; их реализация здесь не оценивается.

## Вывод

**Для просмотренных существующих путей публикации общая блокировка строки
Meeting через `FOR UPDATE` достаточна как защита выбора источника и результата
от параллельной смены и появления новой подходящей строки.** Условие: новая
серверная проверка должна сначала получить эту блокировку, заново прочитать
проекцию и удерживать ту же транзакцию до единственного commit аналитики.
Конкретный действующий путь записи выбранного текста, принятой аудиоверсии
или текущего слота, обходящий Meeting, в указанной области не найден.
Для этого узкого инженерного вывода P1=0, P2=0.

Это свойство согласованных путей записи приложения. **Одни `FOR SHARE` на уже
существующих MediaRevision/ProcessingResult/MeetingOutcomeSet не закрывают
появление новой строки, смену выбора слота или изменение дочерних сегментов.**
Блокировка родительского результата сама по себе не запрещает удалять его
TranscriptSegment или заменять MeetingOutcomeItem. Нельзя обосновывать
защиту от таких изменений только существующими строками либо внешними ключами.
Общий Meeting является точкой упорядочивания реально найденных writers.

Проверка чтением не доказывает будущую реализацию verifier, соблюдение бюджета,
конкурентные тесты, готовность T113, T0 либо рабочий сбор событий. Настоящий
источник готовности до приёмки T113 по-прежнему должен отказывать в допуске.

## Проверенные пути записи

Пути в таблице относительно `apps/server/src/twobrain_rec_server/`.

| Что может изменить выбранную проекцию | Фактическая защита |
| --- | --- |
| Новая версия ProcessingResult, замена дочерних transcript/diarization при частичном повторе | `processing/store.py:2814` `persist_processing_result` получает Meeting на строке 2821 до проверки текущего workflow и принятой ревизии; затем блокирует/создаёт результат, заменяет сегменты и сохраняет статусы. Все выбранные данные записываются до завершения этой транзакции. `set_dependency_state` на строке 3212 сам делает commit; это фактическое снятие блокировки в конце успешного пути, после записи результата, не reusable fence для последующих операций. |
| Новая попытка обработки или смена текущего workflow | `create_processing_attempt` получает Meeting на строке 1226; `upsert_processing_workflow` — на 1950; `set_workflow_status` — на 2132. `prepare_closed_workflow_same_job_recovery:926` также получает Meeting до создания следующего ordinal и переноса job. `retire_unsupported_processing:1742` меняет статус через fenced `set_workflow_status`. Эти операции не могут незаметно поменять выбор текущей обработки, пока аналитика держит Meeting. |
| Создание/обновление исходной линии итогов, очистка AI-wait projection | `outcomes/service.py:137` `ensure_outcomes_for_processing_result` получает Meeting на 145 до проверки последней принятой ревизии и результата. Вызовы `create_outcome_set`, `_project_revision_scoped_ai_wait` и `replace_outcome_items` находятся внутри этой границы. Принятые/замещённые версии не переписываются этим путём как новый текст. |
| Создание кандидата итогов и нового summary slot | `outcomes/ai_service.py:300` `create_summary_candidate` получает Meeting на 313 перед `ensure_summary_slot`. `ensure_automatic_summary_candidate` сначала вызывает `mark_meeting_default_slot`, который получает Meeting, затем создаёт/находит слот и кандидата. Подавление `SummarySlotDefaultConflict` не откатывает транзакцию и не снимает уже полученную блокировку. |
| Установка слота по умолчанию | `outcomes/service.py:621` `mark_meeting_default_slot` получает Meeting через `FOR UPDATE` на 635 до проверки существующего default и создания/изменения слота. |
| Публикация model-generated outcome, смена текущего outcome в слоте | `outcomes/ai_service.py:143` `publish_model_generated_outcome` использует `_lock_candidate_meeting_and_attempt:2668`, сначала Meeting. `_cas_summary_slot:2417` повторяет Meeting fence на 2438, затем блокирует слот и прежний outcome; изменение `current_outcome_set_id`, binding, state_version и accepted/superseded выполняется под ним. |
| Сохранение нового текста кандидата после ответа модели | `_store_candidate_protocol:1842` вызывается только двумя путями `execute_candidate_generation`: повтор сохранённого ответа на 1326 под первоначальным Meeting lock и новый ответ на 1791 после повторного `_lock_candidate_meeting_and_attempt` на 1726–1728. Предшествующий commit retained GenerationCall явно сопровождается новым получением Meeting перед публикацией. |
| Создание новой аудиоревизии/сессии | `ingest/sessions.py:52` `create_media_revision_upload_session` получает Meeting через `FOR UPDATE` на 76 до INSERT MediaRevision; обычный `create_upload_session:210` получает ту же блокировку на 229. |
| Переход аудиоревизии в accepted, смена последней принятой ревизии | `ingest/finalize.py:660` повторно получает `_lock_finalize_lifecycle_fence` после работы с хранилищем. Вызов `mark_media_revision_accepted` на 741 использует `commit=False`; дальнейшие `persist_meeting`, tracks/session/audit также не делают commit. Функция возвращает управление владельцу транзакции, удерживая блокировку до её завершения. Единственный производственный вызов `mark_media_revision_accepted` найден здесь. |
| Восстановление/блокировка незавершённой ревизии при abort/expire | `ingest/lifecycle.py:33` получает Meeting до UploadSession; `lifecycle_guards.py:96` и `desktop_sync.py:647` используют тот же порядок перед восстановлением состояния и `persist_meeting`. Принятая immutable ревизия этими путями не переводится обратно в blocked. |
| Создание первой встречи и первой ревизии | `ingest/meetings.py:226` вызывает `persist_meeting` для новой встречи после блокировки recording origin. Повторный запрос к уже существующей встрече получает её `FOR UPDATE` на 143 и возвращает существующую запись после проверки; новую ревизию в обход блокировки существующей встречи этот путь не создаёт. |
| Имя участника, название встречи | `cabinet/web_routes/speakers.py:51` вызывает `lock_shareable_meeting` до записи имени; `cabinet/meeting_titles.py:38` использует `lock_meeting_fence` на 50. Эти отображаемые имена/название не входят в проверяемый T112 digest текста, но их writers также согласованы. |
| Удаление расшифровки, итогов и слотов | `deletion/service.py:145` получает Meeting перед tombstone/epoch. `_purge_server_controlled_content:1889` после отдельного commit tombstone заново получает Meeting на 1903–1910; удаление сегментов, очистка outcomes и удаление слотов происходят внутри этой транзакции. `_purge_meeting_outcomes:2495` вызывается только из неё на 2326. |
| Перенос графа встречи при объединении аккаунтов | `auth/account_merge.py:1493–1501` выбирает исходные Meeting через `FOR UPDATE` до смены workspace/owner и `_move_meeting_workspace_rows:1510`. Он не переносит выбранный source/result/outcome незаметно для удерживаемой блокировки Meeting. Это дополнительная узкая проверка смены области доступа, не полный аудит merge. |

## Функции без собственной блокировки Meeting

Поиск вызовов различает низкоуровневую функцию и фактический путь записи.
Следующие функции сами не берут Meeting, однако найденные производственные
вызовы находятся под вышеописанными блокировками:

- `outcomes/store.py:61` `create_outcome_set` и `:110` `replace_outcome_items`;
- `outcomes/service.py:548` `ensure_summary_slot`;
- `outcomes/ai_service.py:1842` `_store_candidate_protocol`;
- `ingest/media_revisions.py:207` `mark_media_revision_accepted`;
- `ingest/store.py:232` `persist_meeting`, `:576`
  `restore_meeting_after_upload_session_lifecycle`;
- `ingest/lifecycle.py:89` `mark_media_revision_blocked_for_lifecycle`;
- `deletion/service.py:2495` `_purge_meeting_outcomes`.

`persist_meeting` действительно умеет добавить отсутствующую первую ревизию
и обновить незавершённую ревизию. Поэтому нельзя объявлять его безопасным
лишь из-за неизменяемости принятого источника: важны проверенные вызывающие
пути. Его вызов `finalize.py:175` относится только к ветке `db is None`,
где записи PostgreSQL нет. В ветке с БД degraded finalize получает Meeting
через `FOR UPDATE` перед изменением статусов.

Найденный намеренный writer **без Meeting fence**:
`processing/store.py:2664` `persist_mediascribe_submission_fallback` блокирует
только MediaScribeJob, сохраняет opaque external ID и blocked/error metadata
после внешнего запроса. Он не создаёт/меняет ProcessingResult, сегменты,
принятую ревизию, текст итогов или summary slot. Это конкретное исключение
из общего утверждения «все writers берут Meeting», но не обход защиты
проверяемой выбранной проекции. Схожие записи run/export metadata не следует
ошибочно приравнивать к публикации текста.

`cabinet/egress.py` читает выбранные результаты и итоговые слоты; операции
выгрузки/прослушивания меняют разрешения выдачи, аудит и сведения об артефактах,
но не публикуют новый текст, accepted MediaRevision или current summary slot.
Начальный commit экспорта на 459 — причина не переиспользовать такую функцию
внутри analytics transaction в качестве чистого verifier.

## Условия применения вывода к серверной реализации

1. Отдельная свежая DB-сессия с актуальным контекстом доступа; Meeting сначала,
   затем source/result/outcome/slot locks. Недопустима проекция из старой
   identity map или заранее заполненного кабинетного read-prefetch. После
   получения Meeting нужен свежий выбор тем же review helper и теми же
   разрешёнными query-параметрами, что использует GET.
2. Сохранение Meeting до единственного commit обеих аналитических вех. Между
   проверкой proof/digest/lineage и записью пары не вызываются helpers, которые
   делают commit/rollback. Повторный вызов `lock_meeting_fence` внутри той же
   транзакции допустим; сохранённый ORM-объект после commit не сохраняет lock.
3. При блокировке, смене доступа/владельца/источника, ошибке или неизвестном
   исходе commit — закрытый отказ аналитики в уже принятом ограниченном
   бюджете, без повторной записи. Не превращать это исследование в основание
   отключить T113, доверять клиентскому флагу или старому proof.
4. После реализации нужны причинные проверки в независимых DB-сессиях:
   сначала mutation → verifier видит новое состояние/отказывает старому proof;
   сначала analytics → writer ждёт или получает ограниченный отказ, а до
   завершения analytics не меняет выбранную проекцию. Приоритет: новая accepted
   ревизия, новый результат/дочерние сегменты, смена слота, удаление. Результаты
   таких тестов в этом отчёте не заявлены.

Дополнительное наблюдение: `reconcile_closed_processing_workflow_result:1062`
сначала блокирует ProcessingWorkflow, затем вызывает `set_workflow_status`,
который получает Meeting. Это не обход fence, но обратный порядок относительно
Meeting → workflow требует ограниченного ожидания/закрытого отказа аналитики;
глобальное отсутствие взаимных ожиданий этим чтением не доказано.

## Срез и предел доказательств

Выполнены чтение исходников, поиск мест создания/изменения выбранных сущностей
и вызовов вспомогательных функций. Ни тесты, ни приложение, ни PostgreSQL,
ни браузер, ни внешние системы здесь не запускались. Code/spec/plan/tasks/
checklists, Git/GitHub, runtime и публикации не изменены. Рассмотрены текущие
пути приложения; прямой SQL администратора, миграции и будущие writers этот
вывод не покрывает. Само время и истечение сроков не замораживаются row lock;
они должны проверяться штатной свежей проверкой в ограниченной транзакции.

SHA-256 прочитанных ключевых источников:

| Путь относительно server package | SHA-256 |
| --- | --- |
| `processing/fences.py` | `1b4b8398d49212f5703a29e18460130d13d2c2bb39bcbc0b1d968804c63c4834` |
| `processing/store.py` | `de616c64a03c3a036ab09d532d84bdb9443089a6c8f85f53a332af0295ba4b42` |
| `outcomes/service.py` | `b10b0708564a809ec102f83d90f8030a3587dae28cbeae0781d9c5b1a3432377` |
| `outcomes/store.py` | `db2589b6b052052b718da3fe6ef950e49a0e90c052e80671b4c06c6360077704` |
| `outcomes/ai_service.py` | `d4948c8a117c68372041e9484b3b03f7224d5b2899b666697467c51833cf3d1c` |
| `ingest/sessions.py` | `39084236b666f9bc3e3c31e3c18f38b98c957b6f30396f39304c9d31b8b4ac78` |
| `ingest/meetings.py` | `d0af070ed6316bb43f65b7bfce543dcff9873efd2549a73006a95a7dfaa93ffa` |
| `ingest/store.py` | `5eabc08617cc89a078b97cc307902130f976be3266cc7907308eba85ac3a86e7` |
| `ingest/media_revisions.py` | `72e5e4a0d4ab6631762c84799b626f594dec7b8f3264b5b9f6f909c19f9e0391` |
| `ingest/finalize.py` | `e072170a260eaabde506c4d2be131821a2d64c0e8808ead6884364b9ee6a6f78` |
| `ingest/lifecycle.py` | `7fd08abf63d9b652aff9279a77eb171b91e5683e427b1a4514d43455bec98159` |
| `ingest/lifecycle_guards.py` | `f0b6e4bdaf975d350d104e9e5831f3adcf49aebca39de58656ecc39b38c33835` |
| `ingest/desktop_sync.py` | `ba2b9ffab87f7b19a8a3cd47dc7ab15b693a3b8bcbae0a6f720eedc06f43863d` |
| `cabinet/web_routes/speakers.py` | `90118be6b2cf3fbf9af247cc156c6a56046816dc1070fef0047c4ff3ea740b0c` |
| `cabinet/meeting_titles.py` | `c24301d65ea90fc3ffe47457516bdd8c8bf156a5991533fb29e3ff57be4b6446` |
| `cabinet/egress.py` | `4f31ab02b410938596a0fde2c4085ec31e0b4e6b1944db23607036f0fe380e40` |
| `deletion/service.py` | `4534012daa4f54dfe5fd58cc8bba5674c4771e9c108697c34820b4a3c5b3aa00` |
| `auth/account_merge.py` | `7840869e398b8f621d78c27119a7ecbba15f4f6058fac1d7f54e1dd4f598e205` |
