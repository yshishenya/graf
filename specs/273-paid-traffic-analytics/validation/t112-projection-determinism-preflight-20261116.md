# T112 — независимый проект устранения H1 и ограничения исходного JSON

16.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
HEAD `eea992190c92e57b2cceaa199c2bcbd94ff71614`.
Полоса: TEST/RUNTIME DESIGN существующего high-risk-product F273/T112/T113.
Изменён только настоящий новый отчёт; прежний HOLD b3f534… сохранён.

## Решение

**SCOPED DESIGN PASS: три завершающих PK tie-break в общих readers,
ранний RR и числовой guard фактических SELECT с raw JSON bound. P1=0/P2=0
для этого уточнённого проекта.** Это минимальный разрешённый следующий путь;
не копия31 selectors, не изменение ORDER только в preflight и не новый reader.

PASS относится к проекту, не к ещё отсутствующему guard. Нужны причинные
испытания и независимое ревью точного кода. HTTP, настоящий T113, измерение/T0,
рабочий сбор и выпуск остаются закрытыми. `_result_period_context` не открывать.
294 проверки не запускались повторно; PostgreSQL/browser/runtime не читались.

Прочитаны полный новый request `graf-t112-projection-h1-followup-20261116.txt`,
main-owned determinism map, прежние собственные отчёты и применимые оригиналы
source/contract/PRD. 18 входных хешей совпали. Использовано прежнее собственное
полное чтение того же диалога; актуальные изменившиеся зависимости прочитаны
самостоятельно. Модельные constraints проверены по исходникам; рабочая schema
и production isolation здесь не наблюдались.

Reviewer-owned требования остаются requirements16/0, security27/0,
privacy-measurement52/0, infra29/0: **124/0**, отметки не менялись. Это не новый
перезапуск их приёмки и не implementation PASS.

## Необходимая правка общего reader — ровно три выбора

| Место | Сохранённый приоритет | Добавить последним |
| --- | --- | --- |
| queries.py:1482, workflow LATERAL LIMIT1 | attempt_ordinal DESC, created_at DESC | ProcessingWorkflow.id DESC |
| queries.py:1562, dependency LATERAL LIMIT1 | updated_at DESC | ProcessingDependencyState.id DESC |
| egress.py:2651, activity LIMIT50 | created_at DESC | MeetingEgressAuditEvent.id DESC |

PK непуст и уникален. Каждый такой ORDER после добавления задаёт полный
порядок при любых равных прежних ключах, в том числе NULL в более ранних
sort keys; прежнее направление/NULL ordering не переписывается.

Это меняет конкретно выбранную metadata-строку/границу истории при прежде
неопределённом равенстве. Нельзя называть этот случай побайтово неизменным.
Workflow status/dependency/activity могут получить иной определённый порядок
на таких данных; при разных ordinal/timestamps выбор сохраняется.

**Контракт result-visibility §3 допускает эту узкую правку.** Он сохраняет
единый get_cabinet_meeting_review и правила transcript/outcome, запрещая
отдельный аналитический latest reader. Три изменения делаются в самих общих
queries/egress, одинаковых для отображения и проверки. Transcript/effective
result order, source selection и default/pinned outcome pointers не меняются.
В PRD §23 нет обещания конкретного выбора между равными UUID metadata rows.
Нового продукта, изменения публичного лендинга или пересмотра принципов нет.

Обязательной четвёртой правки нет. У fallback _latest_workflow нет SQL LIMIT:
guard проверяет весь фактический результат, а не одну scalar строку. Добавлять
там tie-break ради отдельной согласованности возможно лишь отдельным осмысленным
изменением; для закрытия H1 его не следует незаметно включать в этот срез.

## Полнота ограниченных selectors

Самостоятельно сверены source, mapped constraints, достижимость из fresh
getter(storage=None) и source/binding. Статический инвентарь использован лишь
как указатель. Таблица ниже закрывает все найденные LIMIT в этой области.

| Выбор | Почему крупные выбранные поля одинаковы в одном RR snapshot |
| --- | --- |
| Prefetch latest/accepted MediaRevision | unique(workspace,meeting,revision_number), revision_number NOT NULL; первые два равны фильтру. Максимальная revision_number уникальна, updated_at не создаёт tie. accepted predicate при пустом default slot выбирает тот же уникальный максимум; при pointer — PK |
| Prefetch workflow/dependency | Именно две требуемые правки выше; активные partial unique workflow и dependency/revision индексы сами по себе не достаточны |
| Prefetch result | Полный order заканчивается ProcessingResult.id; join ProcessingWorkflow по PK |
| Prefetch effective result | Общий effective_processing_result_query заканчивается result.id; revision=None даёт false, а не произвольный legacy row |
| Default slot | unique(workspace,meeting) WHERE is_meeting_default IS TRUE совпадает с фильтром |
| Selected slot | unique(workspace,meeting,template_key), template_key NOT NULL. Выбранный None превращается в IS NULL и даёт пустое множество; не неоднозначные NULL строки |
| Outcome/outcome result/template/personal template/canonical artifact | Равенства по конкретным PK. Дополнительные workspace/meeting/template/status predicates лишь убирают строку |
| Artifact policy | unique(workspace,meeting) |
| Normalization | unique(workspace,media_revision_id,profile_version). accepted.id либо конкретный PK, либо SQL NULL. Сравнение column=accepted.id при NULL даёт UNKNOWN/нет строки, не IS NULL по всем legacy jobs |
| Finalized archive UploadSession | ORDER created_at DESC,id DESC |
| Current calendar link | unique(workspace,meeting) |
| Generation attempt | ORDER created_at DESC,id DESC |
| Previous recurring Meeting/link | ORDER matched_event_starts_at DESC,link.id DESC; Meeting join по PK. Затем revision/result без SQL LIMIT проверяются целиком |
| Candidate participants LIMIT100 | ORDER kind,name,id; последний PK уникален |
| Calendar audit LIMIT50 | ORDER created_at DESC,id DESC |
| Egress activity LIMIT50 | Третья обязательная правка; ORDER created_at DESC,id DESC |
| Optional correction source/event limits | source.id и event.starts_at/event.id; IDs полные. Текущий fresh вызов не включает correction; рабочие owner candidates/roster/previous не выключаются |
| Transcript/diarization presence LIMIT1 | Выбирается только UUID PK; любое выбранное значение имеет один доказанный фиксированный envelope. Счёт0/1 и presence не зависят от выбранного ID; это не разрешение так же обращаться с ORM Model/JSON |
| load_result_view_source LIMIT1 | Meeting.id, revision.id, result.id заданы; workflow.id=ProcessingResult.processing_workflow_id. Все четыре выбранные модели однозначны. Join нескольких UploadSession может дать несколько одинаковых выбранных tuple; UploadSession/audit fields не передаются этой выборкой. Следовательно envelope выбранного tuple одинаков независимо от дубликата |

Весь prefetch — Workspace по PK и LEFT JOIN LATERAL LIMIT1; после двух правок
каждая крупная ветвь выбрана однозначно, outer row0/1 с NULL optional fields.
Полная ORM projection всех aliases учитывается, включая повтор одного result
в нескольких aliases. Не считать identity-map dedup доказательством меньшего
транспорта: asyncpg декодирует всё пришедшее до такого объединения.

Нет достижимого OFFSET/DISTINCT ON/volatile/side-effect selector, создающего
ещё один неоднозначный крупный LIMIT в прочитанном пути. Batch DISTINCT ON
из статической карты не вызван fresh getter. Worker SKIP LOCKED не является
его чтением. Это source-scoped вывод, не разрешение будущих неизвестных форм.
Новая реально достигнутая форма/тип закрывает аналитику до model load.

Scalar без SQL LIMIT — полная фактическая SQL выборка. Нельзя добавлять LIMIT1
в аналитическую копию latest revision/result/workflow/attempt. UUID-only
presence допускает фиксированный numeric envelope; остальные поля нельзя
опускать, потому что они не входят в digest или безопасный view.

## Исходный JSON: обязательное уточнение прежнего проекта

Подтверждено: ProcessingResult.provenance_json/overlaps_json/acoustic_turns_json/
downloads_json — SQL JSON; миграция0078 добавляет sa.JSON. Установленный
SQLAlchemy2.0.51 asyncpg dialect.setup_asyncpg_json_codec передаёт binary JSON
как bin_value.decode() в json.loads. Non-server-side cursor сначала выполняет
prepared_stmt.fetch всех rows; ORM видит уже декодированные значения.
После ORM load или after_cursor_execute исправлять это поздно.

Поэтому `octet_length(to_jsonb(q)::text)` **не верхняя граница**: JSONB убирает
пробелы и duplicate keys. Предыдущий отчёт не переписан; эта его проектная
оценка заменяется следующим обязательным алгоритмом:

1. На стороне БД по каждой **реально выбранной expression** SQL JSON считать
   исходный `octet_length(convert_to(json_expression::text,'UTF8'))`, прежде
   любого jsonb cast/shape traversal. JSONB имеет отдельное правило с его
   textual encoding; консервативно учесть protocol version overhead. SQL NULL
   даёт0, JSON literal null —4 bytes и один JSON node. Повторные aliases
   считаются повторно. Не выбирать в Python сами expression/JSON для подсчёта.
2. String/Text: исходные UTF-8 bytes, binary: octet_length(bytea), числовые/
   UUID/date/bool — доказанные консервативные фиксированные envelopes. Тип
   берётся у selected expression, а не по догадке от имени всей модели.
   Неизвестный type/coercion/array/text-star закрывает аналитику. В текущей
   ORM model graph SQL ARRAY не найден; его поддержку нельзя выдумывать.
   Если он понадобится, требуется доказанный raw output/cardinality/depth
   envelope до выдачи driver; обычный Python list из SQL JSON — случай JSON.
3. Вернуть в Python одну строку чисел: bounded count, cumulative raw bytes,
   max row/max field, overflow. Row count покрывает Q целиком либо cap+1
   prefix с отказом при overflow. До этого нет выдачи частных fields/ORM rows.
4. Только после positive raw byte envelope проверить depth/node count на БД
   и только затем исполнить исходный SELECT. В одной RR транзакции Q после
   трёх tie-break выбирает тот же payload во всех фазах. Не полагаться на
   CASE/CTE как единственное доказательство, что optimizer сначала выполнит
   byte guard: две последовательные числовые фазы дают явную границу.
5. Для SQL JSON shape использовать сохраняющие повторные ключи json_each и
   json_array_elements/json_typeof либо доказанный эквивалент. **Одного jsonb
   traversal недостаточно даже после byte check.** Пример: раннее значение
   duplicate key содержит глубокий массив, последнее равно0; jsonb удаляет
   глубокое дерево, но Python JSON decoder всё равно его разбирает. Это
   дополнительное самостоятельно найденное условие проекта.
6. Raw shape traversal ограничен depth+1/node+1. Для object/array CASE
   подставляет пустой объект/массив неподходящему типу до вызова соответствующей
   функции; wrong-type error не должен обходить контроль. LIMIT node_cap+1
   и отказ при его достижении; если лимит не достигнут, разобраны все nodes.
   SQL timeout остаётся≤500ms и ограничен общим остатком. DB parse/codec error
   даёт generic unavailable, без частного error text/context в журнале/ответе.

Нормализованный row JSON допустим как дополнительная оценка; он больше не
является основным transport bound. SQL binary/text size не заявляется точной
оценкой Python heap: node/row/field caps отдельно ограничивают amplification.

## Минимальная реализация guard без переписывания ORM SQL

Допускается прежнее направление session-scoped do_orm_execute на **новой**
Session владельца; RR выбран через db.connection(execution_options=...) до
первого tenant/readiness SQL. Public APIs: SessionEvents.do_orm_execute,
ORMExecuteState.statement/parameters/invoke_statement, Select.selected_columns,
Select.subquery, FromClause.c, Connection.execute и локальные event.listen/remove.
Обёртка одного AsyncSession.execute не доказывает scalar/scalars/get охват.

Из исходного Select строится Core numeric Q с теми же bind parameters;
public subquery columns дают disambiguated aliases и selected expression types.
Дублированные имена не означают пропуск одноимённых fields. TextClause/raw star,
неоднозначное соответствие columns/типов, неподдержанное eager loading,
executemany SELECT/streaming/volatile/SKIP LOCKED — отказ до полного row.
Нельзя использовать context.compiled._result_columns или изменять ORM result-map.
После числовых фаз исходный ORM statement передаётся invoke_statement без
замены columns/ORDER/NULL/parameters/tuple shape; zero/empty остаётся zero/empty.

Cumulative budget — один Python state owner, числа возвращены до исходного
SELECT. Расход резервируется до материализации каждого Q, повторные реальные
чтения и aliases считаются повторно; неизвестный исход обрывает фазу, refund/
retry нет. Нет transaction-local GUC counters, дополнительной таблицы/записи
или set_config вне существующего tenant setup. Сессия не используется параллельно,
autoflush выключен и не содержит ранее загруженных чужих/unbounded objects.
Cached db.get безопасен только если объект создан в этой guarded fresh сессии.

Локальный connection before_cursor_execute допустим **как detector обхода**:
не переписывает SQL, а допускает только подготовленные owner control statements,
числовой preflight и исходный разрешённый read. Неизвестный direct connection/
raw SQL закрывает фазу. Control advisory/set_config не исполняются повторно
внутри aggregate. Listener снимается finally перед возвратом connection в pool;
нет глобального engine hook, consumer чтения cursor или доступа к driver._rows.

FOR UPDATE/SHARE исходного точечного SELECT сохраняется в numeric subquery;
он получает настоящую row lock до возврата полного объекта. PG lock semantics
outer aggregate/limit требуют причинного теста; helpers не создают DeletionFence.
Режим не ослабляется, порядок T113 прежний. Неподдержанный locking shape
закрывается, а не переписывается частными атрибутами SQLAlchemy.

Почему single MATERIALIZED Q сейчас не выбран: before_cursor_execute public
и позволяет менять SQL string, но не обещает соответствия новой projection
старому compiled ORM result-map. Q.* с duplicate labels/добавленным ordinal
требует отдельной схемы. Внешний SELECT без своего ORDER не получает гарантию
порядка только от ORDER внутри CTE; добавление window ordinal может конфликтовать
с DISTINCT/FOR UPDATE. При пустом Q вычисление side-effect GUC counter не
гарантировано одним MATERIALIZED SELECT. Это отдельный SQL rewriting framework,
который три shared tie-break не требуют. Его код/ошибки CASE/GUC не нужны для
закрытия H1; отсутствие такого framework не является новым blocker.

## Границы и обязательная причинная приёмка

Прежние caps не расширяются:4096 rows/query,16384 cumulative rows,8MiB raw
logical bytes,512KiB row,256KiB field,128 reads,depth32,nodes65536. Это прежние
немеренные кандидаты, не доказанный безопасный runtime envelope. Preflight
SQL тоже входит в один2s срок; lock≤250ms, statement≤500ms. Счётчик128
должен охватывать все управляющие/numeric/исходные SQL исполнения этой
аналитической проверки, а не скрывать дополнительные запросы внутри128
logical reads. Это тот же фиксированный предел, без бесконечной recursion.
Один timeout на каждый helper не заменяет общий срок. Проверка остатка до/после
синхронной materialization/canonical/JSON/digest, перед INSERT и commit обязательна.

Обязательная следующая последовательность, без повторения294:

1. RED H1:51 audit event одного created_at, включая большой JSON; tied workflow
   и dependency в допустимой schema. До правки — разные допустимые choices;
   после PK tie-break — один набор exact rows/fields при разных PG plans в RR.
   Отдельно разные ordinal/timestamps: старый приоритет полностью сохранён.
2. Prefetch/source boundaries: NULL selected key, absent accepted revision,
   duplicate eligible UploadSession с одинаковой выбранной source tuple,
   UUID-only presence с несколькими rows, previous-meeting scalar без LIMIT.
   Проверить реальный transport count, а не только Python scalar результат.
3. Raw JSON RED: много whitespace при маленьком jsonb; duplicate keys с
   большим/глубоким ранним значением и коротким последним; Unicode, SQL NULL/
   JSON null; cap-1/cap/cap+1 bytes/depth/nodes. До исправления пройдёт
   normalized-only envelope; после — отказ до asyncpg decoder и ORM instance.
4. Interception: execute/scalar/scalars/get/cache, aliases/duplicate labels,
   raw connection bypass, recursion, listener reuse/cleanup, unknown shape/type.
   Фактический renderer получает оригинальный ORM shape, порядок и empty rows.
5. Real PG preflight→reader races для current/previous/calendar/grants/source;
   сохранение locks,40001 без retry. Обычная30–60мин синтетическая встреча
   должна пройти со всеми обычными JSON/diarization и без выключения календаря;
   pinned/old-source/default/selected paths сохраняют exact digest. Не проходящий
   обычный fixture означает HOLD runtime; caps ради зелёного не поднимать.
6. Максимальный допустимый envelope и SQL count: весь2s бюджет включая JSON
   decode/canonical/model/digest;0 surviving tasks/sessions,0 partial new pair,
   generic отказ и отсутствие private fields/JSON/proof в log/provider.

RR не заменяет T113 freshness: identity/session/membership/device/status,
legal/withdrawal/readiness/mode/source/result/outcome/deletion writers должны
оставаться согласованы действующими fences до commit. Phantom insertion до
lock в RR отдельно проверяется;40001 не повторяется. Эти прежние обязательства
не объявлены выполненными тремя tie-break или isolated fixture.

**Точный следующий шаг:** в рамках существующего T112 сначала изменить три
общих ORDER и выполнить причинные tie/priority проверки; затем реализовать
числовые raw-byte/raw-shape фазы и scoped Session guard с новым RED/GREEN.
Для исходного закрытого T113 проверить safe absence; для guard — изолированный
внутренний synthetic context, без verifier=True/новой HTTP настройки. После
implementation review решать подключение HTTP; рабочее измерение этим PASS
не разрешено. От пользователя дополнительных разрешений для проекта не нужно.

## Версии и сохранность

Все18 прежних входов совпали; отдельно проверены SHA старого отчёта и main
map. Эти файлы не переписаны. Перечень входов:

| Путь | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/spec.md` | `a7f23904625df9b06aed1e09c05f2ffa75ec3e5ec9ac0eda0531cd88c949c645` |
| `specs/273-paid-traffic-analytics/plan.md` | `5207a988f666c47f65203718a1212cf352312009f1c3804163abd093318a8b3c` |
| `specs/273-paid-traffic-analytics/tasks.md` | `3870e4d091557e0c40dd5500aa8fb5932b933cfe877e684c930d7f7e4f93a7d5` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `4f2488aa98a3fba478eed042304279f408dc2530bd3f2b0449cedabaf39dd074` |
| `specs/273-paid-traffic-analytics/research.md` | `64caef3d9a78f0021c2b37ca86e0f388724bf117e899bd044f4ca557a1ba094f` |
| `specs/273-paid-traffic-analytics/data-model.md` | `478c18546d1240c4a1c15c5b07e76f7aeb551082273b75bc1fbf4cdd8d1ae8ab` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `d771fe1f54e69b297346bfde3ea52f82d484fc241f13576efc34e09feffe80f4` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `dbd65a5afb7829789d8b4aa48f8c0b32243cc039681d15a5b851b381ca3b8b92` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `5b4164d0ce3e11ea6bca8419f4f0d6f6d33de163e3745cbb4cbfccd90ce07840` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `a3319849bcd8be93803415495b42b4e50476cf1e08eb57ef898d34293f2be0cf` |
| `specs/273-paid-traffic-analytics/validation/t112-requirements-review-20261116.md` | `bb7c8592b302d6cb9ef21e0ecfc1045778afd39f07efed29787091ae3aaf91a5` |
| `specs/273-paid-traffic-analytics/validation/t112-analyze-20261116.md` | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `66ba7daa70519c8848a6daea51cd593220fccf75d4b5ea3a4a154e5ae139c3ca` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |

Точные source/report inputs этого среза:

| Путь | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/validation/t112-projection-budget-preflight-20261116.md` | `b3f5344650831ed104af19a108bbc870de0813659723f3ca44f644b5302f2356` |
| `specs/273-paid-traffic-analytics/validation/t112-projection-determinism-map-20261116.md` | `17b20aa6c5e078622013e715efbc2d0e574fe94dba3587bc4b68c32007f6d82e` |
| `apps/server/src/twobrain_rec_server/cabinet/queries.py` | `cf0e7b622c60e53513df78140ddf2d2ab74937a55a15ce7c719de56fa14f50da` |
| `apps/server/src/twobrain_rec_server/cabinet/egress.py` | `4f31ab02b410938596a0fde2c4085ec31e0b4e6b1944db23607036f0fe380e40` |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `b59aa36240282748ed88696e1cfee04710302364ce9df9f2b5fc3315fdedb5e7` |
| `apps/server/src/twobrain_rec_server/calendar/service.py` | `5c81afc11964c63314c1dcdafd381c594ed6f8081141117afb63ffd033c8fb84` |
| `apps/server/src/twobrain_rec_server/calendar/audit.py` | `cb5f8a219c147065c006e917ec8809f3f508e9b14a32fd2c25e2492f1ad61657` |
| `apps/server/src/twobrain_rec_server/processing/results.py` | `9a5044639b3902a4c4cd577dfc73a1d4b0a282f960b76a24f20ec39e41c8b009` |
| `apps/server/src/twobrain_rec_server/db/models/processing.py` | `fceefdfc9f1f0c8669a0bdedc744bf24877ef412af8f118f255d6bb0bec7296b` |
| `apps/server/src/twobrain_rec_server/db/models/ingest.py` | `46c814be586c78a69fa31f7bef1e6756dbec2a070f5c1bd9df5ce0714298809c` |
| `apps/server/src/twobrain_rec_server/db/models/normalization.py` | `1cd57e8b6e07165feb50717e40c382b4af13884ef31df6b272f7b12f8d9ec035` |
| `apps/server/src/twobrain_rec_server/db/models/outcomes.py` | `456b0c1cae8d6da7b6a4efe3cb90fe3c0e867ca93e83b15df61d8d6b008fbbaf` |
| `apps/server/src/twobrain_rec_server/db/models/calendar.py` | `0a2d82743331cfdade53fc4f781a5ed1cb31aaeee176d74463e01d278e1a419a` |
| `apps/server/src/twobrain_rec_server/db/models/meeting_access.py` | `37bc890cbafbe8f4b35f479ad42444790aa164707f69e3aa329794e3edfb3cad` |
| `apps/server/src/twobrain_rec_server/db/migrations/versions/0078_processing_recovery.py` | `be5f7ba61502a9507d795a055483d1be00ae110b376ee98c445e0eb516e9b008` |

Прочитаны установленные исходники SQLAlchemy2.0.51 (не новый запуск кода):

| Относительно site-packages/sqlalchemy | SHA-256 |
| --- | --- |
| `dialects/postgresql/asyncpg.py` | `c5784dd0e262892cbd0ba6cae2daf69b3152037152ada95619a9fb10f6f12bda` |
| `engine/events.py` | `d4c0098fe0f97711c18535d96276f163c015888b51b639be184c53ad737e9eb6` |
| `engine/interfaces.py` | `847decdb2c905353b58c7d7d7fdc56611930a1e744f9ecdc2bba3332d6d408eb` |
| `orm/session.py` | `b75a4e427f453c2eaf19f04d87f66c2da644698a14f3b11880f56a73e2a0760d` |
| `sql/selectable.py` | `93891d6d91c86304813c331ef17bef7291f392d709500bfa9989ba083b9ee515` |
| `sql/elements.py` | `2a85480d879f833e6df86d5630028e04c1b0e83b62a351490b6b3b6c322bab81` |

Проверяющий не менял code/tests/spec/plan/tasks/checklists/Git/GitHub,
runtime/данные, сайт/контент/вёрстку, почту Postal или соседние службы,
nginx/DNS/Compose, сбор/T0 и публичные сообщения. Не создавал новых агентов.
Полное новое чтение неприменимой неизменной истории не заявляется.
