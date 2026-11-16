# T112 — минимальный кандидат устранения неоднозначного LIMIT

16.11.2026. Основной исполнитель `/root`; основа
`eea992190c92e57b2cceaa199c2bcbd94ff71614`.
Полоса текущей работы: исследование исходников / документация.
Будущая реализация остаётся high-risk-product существующих F273/T112/T113.
Этот документ — новый проектный кандидат, **не независимый PASS**.

## Основание следующего действия

Окончательный независимый отчёт `t112-projection-budget-preflight-20261116.md`,
SHA-256 `b3f5344650831ed104af19a108bbc870de0813659723f3ca44f644b5302f2356`,
завершён: HOLD, P1=0/P2=1, H1. Его промежуточное заключение не применяется.
Повторять два одинаковых SELECT с неоднозначным LIMIT недостаточно даже
в REPEATABLE READ. Это пробел будущего проекта, не рабочий сбой сайта.

Вместо нового reader или большой копии графа зависимостей проверяется
возможность устранить неоднозначность в самом общем reader. Приоритетные
ключи остаются прежними; существующий UUID PK разрешает только равные ключи.
Numeric guard затем проверяет тот же исходный SQL с теми же параметрами и
всеми реально выбираемыми полями, после чего исполняется общий reader.
Добавление tie-break только в preflight запрещено: оно не устраняет H1.

Нужны независимая проверка полноты карты и оценка воздействия до кода.
Три изменения ниже не объявляются достаточным охватом по одному поиску.

## Конкретные найденные изменения общего reader

| Место | Существующий выбор | Предложение | Почему нынешняя схема не доказывает уникальный выбор |
| --- | --- | --- | --- |
| `cabinet/queries.py:1482`, workflow LATERAL | attempt_ordinal DESC, created_at DESC, LIMIT1 | Последним ProcessingWorkflow.id DESC | Частичные unique индексы активных workflow не делают эти две сортировки уникальными для всех статусов и source/purpose |
| `cabinet/queries.py:1562`, dependency LATERAL | updated_at DESC, LIMIT1 | Последним ProcessingDependencyState.id DESC | Индексы по revision/dependency допускают несколько dependencies и revisions одного meeting с одинаковым updated_at |
| `cabinet/egress.py:2651`, activity_response | created_at DESC, LIMIT50 | Последним MeetingEgressAuditEvent.id DESC | created_at не уникален; одна из 51 tied строк может иметь большой metadata_json |

Это изменение общего порядка при ранее неопределённом tie; нельзя объявлять
его побайтово неизменным отображением всех исторических случаев. Необходимо
подтвердить, что контракт общего выбора допускает такое разрешение равенства.
Публичные страницы, их контент и вёрстка этими предложениями не затрагиваются.

## Источниковая карта остальных ограниченных выборов

Пути относительно `apps/server/src/twobrain_rec_server/`. Проверены названные
функции/ограничения; статический инвентарь193 не заменяет проверку достижимости.

| Выбор | Основание устойчивого набора или обязательная дополнительная проверка |
| --- | --- |
| Prefetch revision и accepted revision | `MediaRevision` unique(workspace_id, meeting_id, revision_number); фиксированный workspace/meeting. Nullable/predicate оригинала сверяется при ревью |
| Prefetch result | Порядок завершается ProcessingResult.id DESC; workflow join по PK |
| Prefetch effective | `processing/results.py:48`, общий effective_processing_result_query завершается result.id DESC; media_revision_id=None возвращает false |
| Default summary slot | Partial unique(workspace_id, meeting_id) WHERE is_meeting_default IS TRUE совпадает с фильтром |
| Selected slot | Unique(workspace_id, meeting_id, template_key) и равенство выбранному ключу; NULL key требует проверки фактической ветви |
| Outcome, outcome source result, template, canonical artifact, personal default template | WHERE по PK; дополнительная проверка всех joins не должна добавлять иные выбранные payload |
| Artifact policy | Unique(workspace_id, meeting_id) |
| Normalization | Unique(workspace_id, media_revision_id, profile_version); accepted.id при отсутствии revision NULL проверяется отдельно |
| Finalized upload archive | Порядок created_at DESC / UploadSession.id DESC |
| Current calendar link | Unique(workspace_id, meeting_id) |
| Generation attempt LATERAL | Порядок created_at DESC / MeetingOutcomeGenerationAttempt.id DESC |
| Previous recurring pair | Порядок matched_event_starts_at DESC / link.id DESC; Meeting join по PK |
| Candidate participants LIMIT100 | Порядок participant_kind, display_name, CalendarParticipant.id |
| Calendar activity LIMIT50 | Порядок created_at DESC / CalendarAuditEvent.id DESC |
| Calendar correction source/event limits | Порядки source.id и event.starts_at/event.id. Текущий fresh caller оставляет include_calendar_correction_candidates=False; это не основание менять работающие ветви |
| Transcript/diarization presence LIMIT1 | Передаётся только UUID, поэтому допустим доказанный фиксированный byte envelope любой выбранной строки. Нельзя обобщать это на Model с JSON |
| load_result_view_source LIMIT1 | Выбирает Meeting/revision/result/workflow по конкретным PK. Несколько UploadSession могут дублировать только одинаковые выбранные поля; это требует самостоятельного доказательства join projection |
| batch_latest_summary_attempts DISTINCT ON | Порядок group keys, created_at DESC, id DESC. Из fresh detail пути прямой вызов не найден; нельзя объявлять эту batch функцию причиной недетерминированности |
| scalar() без SQL LIMIT | Numeric guard охватывает весь фактический Q, а не одну возвращаемую Python scalar строку. Капы до materialization, без переписывания общего запроса в LIMIT1 |

Существующие `SKIP LOCKED` в worker claim processing/store — отдельные writers;
их присутствие в модуле не доказывает достижимость из fresh getter. Неизвестная
действительно достигнутая форма должна закрывать аналитику до ORM load.

## Отдельная исправляемая граница JSON

`ProcessingResult.provenance_json`, overlaps_json, acoustic_turns_json и
downloads_json имеют SQLAlchemy JSON. Нормализация `json` в `jsonb` может
удалить незначащие пробелы и повторные ключи до передачи числовой оценки.
Поэтому один `octet_length(to_jsonb(q)::text)` не является верхним пределом
исходного транспорта PostgreSQL json. Установленный asyncpg codec передаёт
исходную строку в json.loads; это расход до ORM.

Будущий preflight обязан ограничивать исходный `json::text` byte размер
каждого реально выбранного JSON expression до нормализации, а также общие
bytes/row/field и depth/nodes. Для JSONB/string/array/bytea нужны отдельные
типовые правила; неизвестный тип нельзя молча пропустить. Нормализованный
row envelope остаётся дополнительной оценкой, не заменой raw JSON bound.
Причинный PG пример большого whitespace JSON и repeated keys ещё не исполнен.

## Причинное подтверждение предложенного устранения

До кода: независимый вывод по полному покрытию selectors и допустимости
изменения ties в общих readers. Затем в изолированной PostgreSQL:

1. H1: 51 audit event одного created_at; один большой metadata_json. До
   исправления показать разные допустимые subsets с разными SQL планами в
   одном RR snapshot, после — ровно тот же набор по полному общему order.
   Также tied workflow и dependency в реальной допустимой schema.
2. Сохранить существующий приоритет разных времён/ordinal; ровно равные
   значения выбираются по PK. Getter и будущий aggregate используют один
   запрос, включая вложенные LATERAL, а не две похожие сборки SQL.
3. JSON: raw cap+1 при малом jsonb; oversized и deep/node-heavy JSON
   отказывают до driver decoder/ORM. Граничные UTF-8/NULL/arrays/bytea отдельно.
4. Проверить точный interception execute/scalar/scalars/get, неизвестные
   формы, ещё пустую identity map, locks/cleanup и суммарный расход повторов.
5. Прежний полный профиль guard: обычная 30–60мин synthetic встреча,
   pinned/old-source/default/selected, foreign calendar/grantee/previous,
   реальные concurrent writers, до/после истечения общего2s. Не trim.

RR выбирается до первого SQL; не заменяет legal/readiness/session/source
свежесть и участие действующих writers в fences. Истинный T113 по-прежнему
закрыт. Этот проект не меняет `_result_period_context`, не разрешает HTTP
hookup, рабочий сбор, T0 или внешнюю передачу. Значения caps из предыдущего
отчёта остаются немеренными кандидатами, не принятыми безопасными пределами.

## Состояние исполнения

Код, тесты, Canonical Spec Kit документы, checklist и GitHub не изменены.
18 прежних требований совпали по SHA-256; итоговый reviewer HOLD принят,
его отчёт не переписан. Прежний294 не запускался повторно. Нового кода,
RED/GREEN, независимого PASS этого кандидата, PR/CI/выпуска нет. Почта Postal,
соседние службы, nginx/DNS/Compose, сайт и рабочие данные не затрагивались.
Неудачные wait без выданного running cell ID не являются ни review delivery,
ни проверкой среды, ни verified wait; они не дают оснований повторять тесты.

Новый запрос независимой проверки подготовлен:
`/private/tmp/graf-t112-projection-h1-followup-20261116.txt`.
Доставка именно этого запроса и живое выполнение нового ревью не подтверждены.
Ожидание завершённого предыдущего reviewer не заявляется.

## Контроль исходников текущего исследования

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/queries.py` | `cf0e7b622c60e53513df78140ddf2d2ab74937a55a15ce7c719de56fa14f50da` |
| `apps/server/src/twobrain_rec_server/cabinet/egress.py` | `4f31ab02b410938596a0fde2c4085ec31e0b4e6b1944db23607036f0fe380e40` |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `b59aa36240282748ed88696e1cfee04710302364ce9df9f2b5fc3315fdedb5e7` |
| `apps/server/src/twobrain_rec_server/processing/results.py` | `9a5044639b3902a4c4cd577dfc73a1d4b0a282f960b76a24f20ec39e41c8b009` |
| `apps/server/src/twobrain_rec_server/outcomes/progress.py` | `e84d89e8ee8e949a25339a1b8275daa6d5de174e892fa2f640209a8484977773` |
| `apps/server/src/twobrain_rec_server/calendar/service.py` | `5c81afc11964c63314c1dcdafd381c594ed6f8081141117afb63ffd033c8fb84` |
| `apps/server/src/twobrain_rec_server/db/models/processing.py` | `fceefdfc9f1f0c8669a0bdedc744bf24877ef412af8f118f255d6bb0bec7296b` |
| `apps/server/src/twobrain_rec_server/db/models/ingest.py` | `46c814be586c78a69fa31f7bef1e6756dbec2a070f5c1bd9df5ce0714298809c` |
| `apps/server/src/twobrain_rec_server/db/models/normalization.py` | `1cd57e8b6e07165feb50717e40c382b4af13884ef31df6b272f7b12f8d9ec035` |
| `apps/server/src/twobrain_rec_server/db/models/outcomes.py` | `456b0c1cae8d6da7b6a4efe3cb90fe3c0e867ca93e83b15df61d8d6b008fbbaf` |
| `apps/server/src/twobrain_rec_server/db/models/calendar.py` | `0a2d82743331cfdade53fc4f781a5ed1cb31aaeee176d74463e01d278e1a419a` |
| `apps/server/src/twobrain_rec_server/db/models/meeting_access.py` | `37bc890cbafbe8f4b35f479ad42444790aa164707f69e3aa329794e3edfb3cad` |
