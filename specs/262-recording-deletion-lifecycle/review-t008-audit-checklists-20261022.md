# Независимая проверка требований перед исправлением T008 / #6883

Дата: 2026-10-22. Проверяющий: `f262_requirements_reviewer`, отдельный агент,
не автор исправления. Область: требования и пригодность минимального
сохранения исполнителя/устройства отмены до создания Meeting. Это
reviewer-owned gate активного высокорискового среза F262, а не новая
приёмка реализации.

**Результат: PASS качества требований в указанной области. CRITICAL 0,
HIGH 0. requirements.md: 10 отмечено / 0 не отмечено;
security-ux.md: 10 отмечено / 0 не отмечено. Все 20 пунктов перечитаны
после записи примечаний. Неподтверждённых пунктов качества требований нет.**

Исходный HEAD при начале нового назначения уже переведён владельцем на
`9b286f6d9df01f4b948d7db1673aff99c78635ff`, ветка
`codex/262-origin-cancellation-audit`. `git diff --name-only
 ee33a177846bc89146cec2ad8aaece02035b17ed HEAD` пуст: дерево совпадает
с исходным ee33, на котором найден пробел. Игнорируемый feature.json
указывает F262/T008 и ee33; старое имя branch внутри него не использовано
как источник фактической ветки и проверяющим не исправлялось.

Изменены только два reviewer-owned checklist и этот отчёт. Проверяющий
не менял продуктовый код, spec, plan, tasks, governance, Git, GitHub,
приложение, данные, release или deploy и не запускал тесты. Предыдущий
внешний отчёт `f262-t008-independent-review-20261022.md` с выводом FAIL
приёмки текущего кода остаётся действительным; текущий PASS его не отменяет.

## Почему предложенный способ подходит

`data-model.md`, раздел «Новый минимальный RecordingOriginCancellation»,
требует actor/device audit identity. Это существующее требование, а не
расширение цели фичи. `contracts/lifecycle.md`, «Новая отмена по origin»,
определяет доверенный server/workspace/user/device из аутентифицированной
сессии, owner-only доступ и повтор с тем же receipt. FR-008/009/014/019/021
не позволяют менять identity/полномочия, отменять принятое удаление или
создавать объект ради отмены.

Прочитаны модель `MeetingLifecycleAuditEvent`, миграция0007, действующий
builder metadata и запись обычного deletion audit в service.py.
`meeting_id` и `deletion_request_id` уже допускают NULL; workspace,
actor_user_id, device_id, event_type, outcome, safe_reason, created_at и
metadata_json уже существуют. В миграции0007 journal имеет FORCE RLS,
request/worker workspace policy и служебный maintenance gate. Новая колонка,
таблица, фиктивная Meeting/DeletionRequest и ослабление RLS для этого
способа не требуются. Это статическая оценка пригодности; новое исполнение
INSERT под RLS остаётся обязательной проверкой реализации.

Существующий `build_lifecycle_audit_metadata` сейчас отвергает ключ
`cancellation_id`. Добавить только его в допустимые ключи и проверять
именно объект UUID до общих скалярных правил — пригодный минимальный путь.
Простое добавление ключа с разрешением произвольной строки было бы
недостаточным: обычный идентификатор origin задаётся клиентом и может
содержать произвольный текст. Указанный владельцем строгий UUID устраняет
это расширение данных. Не требуется ослаблять действующие проверки
приватных ключей/значений для остальных metadata.

Событие должно использовать фактический серверный cancellation.id,
полученный после flush marker; тело HTTP и operation_id не являются
источником audit identity. Прямые actor/device поля берутся из уже
проверенного TenantScope, а не из payload. UUID события отдельный от UUID
подтверждения: связь определяется безопасным cancellation_id.

Существующий admin/audit.py умеет включать события с NULL meeting_id,
использует event_type и workspace. Его общая проекция пока маркирует все
lifecycle entries как object_kind=meeting и не выводит metadata cancellation
ID или device. Эта проверка не объявляет новый интерфейс поиска/просмотра
origin audit реализованным и не требует расширять его в T008: требование
данного среза — долговечная проверяемая серверная привязка. Нельзя
создавать вымышленный meeting_id ради drill-down. Изменение пользовательской
проекции/контракта потребует отдельной проверки.

## Обязательный профиль минимального исправления

Ниже зафиксирована проверенная детализация предложения исполнителя в рамках
существующих требований; это критерии будущей реализации и тестов.

1. Только первое создание нового marker в уже удерживаемой origin lock
   области добавляет `MeetingLifecycleAuditEvent` с событием
   `recording_origin_canceled`, исходными workspace/actor/device,
   `meeting_id=None`, `deletion_request_id=None`, принятым outcome и
   безопасной фиксированной причиной. `created_at=marker.accepted_at`.
2. Единственная новая metadata — `cancellation_id`: принимается только
   объект UUID, возвращается его каноническая строка. Произвольные строки,
   включая строку похожую на UUID, None, bool/числа, массивы, словари и
   пользовательский origin не допускаются как cancellation_id. Остальные
   существующие metadata правила продолжают действовать.
3. Marker и audit вставляются/flush в одной транзакции и фиксируются только
   существующим endpoint commit. Ошибка INSERT/flush аудита не оставляет
   нового marker и не выдаёт успешный receipt. Нет отдельного commit,
   фоновой доставки или вызова внешнего сервиса ради обязательного аудита.
4. Повтор, включая другое реально зарегистрированное допустимое устройство
   того же владельца, возвращает прежний receipt и не создаёт новое событие,
   не переписывает первоначальные actor/device/accepted_at и не снимает guard.
   По-прежнему каждый HTTP запрос независимо проходит аутентификацию,
   workspace/device checks и ограничения частоты.
5. Существующий marker без исторического аудита остаётся в силе и повторно
   возвращает receipt. Исправление не приписывает ему текущее устройство,
   не фабрикует время/исполнителя, не удаляет marker и не запускает повторный
   create ради восполнения истории. Отсутствие старого аудита остаётся
   известным историческим ограничением.
6. Поведение existing-Meeting ветки, общий guard обоих create callers,
   namespace, transaction lock, RLS, receipt schema, ограничения удаления и
   retained observability сохраняются. Нет новых публичных маршрутов,
   возврата содержимого, файловой очистки или физической миграции схемы.

Конституция III/IV/VI и product-gates требуют metadata-only audit,
правдивого удаления, сохранения истории и отдельной последующей проверки.
PRD §26 прямо задаёт actor, workspace, device where applicable и object ID.
Предложение им соответствует и не меняет принцип продукта.

## Основания всех пунктов requirements.md

| Пункт | Результат и конкретное основание |
|---|---|
| Пользовательское поведение | PASS. Пять историй spec задают отсутствие возврата, понятный результат и пределы; устройство реализации вынесено в plan/data-model/contracts. Сохранение device закрывает существующее требование аудита. |
| Ценность, приоритеты, границы | PASS. US1–US5 P1 и Why/Independent Test; профиль выше ограничен T008 и не расширяет deletion policy, UI, capture или выпуск. |
| Обязательные секции | PASS. В spec есть stories, edge cases,22 FR,7 SC,entities,assumptions,clarifications,legacy impact. Plan содержит риск,границы,хранение и проверки. |
| Неразрешённые уточнения | PASS. Existing owner-only contract определяет источники actor/device; конкретизированы строгий UUID, одна транзакция, первоначальное устройство и старые markers без вымышленного восстановления. Нового решения пользователя не требуется. |
| Проверяемость и непротиворечивость | PASS. FR-008/009/014/021, S10–S12/S27/S50 и профиль первого события/повтора/ошибки имеют однозначные наблюдаемые исходы. Требование аудита не противоречит отсутствию фиктивной Meeting. |
| Измеримый успех | PASS. SC-001–007 разделяют реакцию/согласование/очистку и условия среды; аудит проверяется фактом commit/rollback и identity, без новых вымышленных метрик. |
| Положительные, отрицательные, конкурентные переходы | PASS. Матрица S01–S51, quickstart PostgreSQL обоих порядков; профиль добавляет ошибку аудита, повтор с другим устройством и чужой scope. |
| Предположения и пределы удаления | PASS. Assumptions, FR-018, contract S50 и data-model receipt: запрет создания отделён от локальной физической очистки и retained external copies. |
| Предложение/код/доказательство различены | PASS. Этот gate до реализации; текущий device gap остаётся открытым. analysis/quickstart/evidence сохраняют датированные пределы прежних тестов, installed/runtime и release. |
| Конституция и MVP | PASS. Конституция II/III/IV/VI, product-gates и PRD §18/23/25/26; manual Stop и system-audio-first не затрагиваются, журнал только metadata. |

## Основания CHK001–CHK010 security-ux.md

| ID | Результат и конкретное основание |
|---|---|
| CHK001 | PASS. Data-model «Идентичность»/ExecutionScope; contract session-derived actor/device и owner-only origin; actor не меняется на target creator для manager meeting-delete. |
| CHK002 | PASS. FR-002/004–008, оси data-model и типы receipt. Audit accepted не утверждает verified purge; при ошибке нет успешного receipt. |
| CHK003 | PASS. Plan §3, общий lock, FR-008/021, S10–S14; новая запись аудита не переносит guard после побочных эффектов. |
| CHK004 | PASS. FR-007/013/014, recovery и S25/S32–S38. Нет нового основания физического purge и нет изменения позднего ACK. |
| CHK005 | PASS. FR-010–012/017, contract frozen selection и S18–S23/S41; серверная metadata-доработка не меняет выбор/фокус/частичный результат. |
| CHK006 | PASS. Contract origin vs meeting lookup, SC-003 и S24/S28/S46/S51; audit не раскрывает недоступный контент и не делает offline равным успеху. |
| CHK007 | PASS. FR-015/018, AVFoundation scope и внешние копии, S30/S31/S42. Сохраняется metadata-only journal, retained Generation Call/Langfuse/Temporal не меняются. |
| CHK008 | PASS. FR-019/020/022 и S27/S37–S40/S47; схема reuse, старый marker не подменяется и не заполняется текущим устройством. |
| CHK009 | PASS. SC-002/003/006 явно отделяют контрольную среду от offline/sleep/unreachable; этот gate не выдаёт замер за результат. |
| CHK010 | PASS. FR-016 и S15/S16 сохраняют ручной Stop и запрет удаления capture/saving; предлагаемый audit путь не меняет захват. |

## Необходимые доказательства после реализации

Это открытая будущая проверка, а не невыполненные пункты качества требований:

- Отрицательная проверка на исходном коде: отсутствующий связанный device
  audit; после исправления — точные workspace/actor/device/cancellation_id,
  timestamp и NULL FK после commit/повторного чтения.
- Повтор с исходного и другого зарегистрированного устройства: тот же receipt,
  ровно одно принятое событие, первоначальная identity неизменна; конкуренция
  не дублирует событие и не возвращает live Meeting.
- Настоящий отказ INSERT аудита: транзакция rollback обоих новых объектов;
  следующий самостоятельный корректный запрос может принять отмену.
- Старый marker без audit: receipt/guard сохраняются, audit не выдуман.
- RLS с неповышенной ролью: допустимый owner, другой user/workspace и
  недопустимый device; отсутствие audit/marker при отказе. События и marker
  другого workspace не доступны через обычный scope.
- UUID-builder позитив/негатив плюс неизменные запреты приватных metadata;
  оба create callers по-прежнему останавливаются до persistent effects.
- Независимое ревью кода, профиль quickstart, новые три exact-SHA/base PR
  проверки, слияние и live issue closeout. Вся F262, installed app и release
  не принимаются этим отчётом.

## Прочитанные источники и пределы

Полностью перечитаны конституция; guidance README, document-reading,
spec-kit-flow, product-gates; оба checklist; spec, plan, tasks, data-model,
contracts/lifecycle, research, analysis, scenarios и quickstart F262.
Для неизменных общепродуктовых зависимостей дополнительно прочитаны целиком
применимые разделы PRD §18,§23,§25,§26 и вводная часть до§4; текущий статус
продукта — вводная часть, deletion feedback и implementation018; guidance
release-and-validation — Validation Lanes, Development/PR, Closeout/Full CI,
Git/Evidence Safety. Новая полная приёмка всего PRD/всей истории продукта не
заявляется. Прочитаны действующие model/migrations0007+0092/audit builder,
origin handler/endpoint, обычный deletion audit и применимые части admin
journal. Запуск runtime/CI/GitHub этим gate не производился.

Исторические документы содержат датированные фразы о готовности/статусе
PR6911; они не использованы как текущее подтверждение T008. Контрольные
суммы фиксируют прочитанные байты, а не выполнение продукта.

## Контрольные суммы SHA-256

```text
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8  .specify/memory/constitution.md
2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb  docs/agent-guidance/README.md
5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411  docs/agent-guidance/document-reading.md
afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e  docs/agent-guidance/spec-kit-flow.md
9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5  docs/agent-guidance/product-gates.md
ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f  docs/agent-guidance/release-and-validation.md
0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2  docs/prd-voice-layer-final.md
25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16  docs/current-product-status.md
f64766bd86981a52c7d18019cd418a8d227756de02e234af1e1d28cf762e063d  specs/262-recording-deletion-lifecycle/spec.md
25d14d4fd41cbc9a7364805722a92173f8e3b93debdd9f30efbfae21e3542cb3  specs/262-recording-deletion-lifecycle/plan.md
f4ed5a207676dfa3fe7f2803c6fbcd447f2bc5faa49e812ba5617fa4c26175ce  specs/262-recording-deletion-lifecycle/tasks.md
0d3514d73303dd20c4e991b89ba6778de54a88cee5007a5b1684359f44a2367e  specs/262-recording-deletion-lifecycle/data-model.md
f0652db20a6369046802a78320c44f0fa7da1df506aed106d0790a724abc66ef  specs/262-recording-deletion-lifecycle/contracts/lifecycle.md
696aeff0f6dfe2da78cbd5a702eb5f57a32fd187011a114083b1cc2b9d7a636b  specs/262-recording-deletion-lifecycle/research.md
3c2ead5b0cfbf492d8c95c8a26b59b8dcd6d11accc872a9e997512d0077af4da  specs/262-recording-deletion-lifecycle/analysis.md
29df91c40b00227e6f682394e4a1f5b0fdc8a426b7c734591a934fab72cb434b  specs/262-recording-deletion-lifecycle/scenarios.md
a728d664177055ad0544c3a2f1b72eee209805ce2612472ca4b2795bdedb2bb0  specs/262-recording-deletion-lifecycle/quickstart.md
e476727406492721e80b22530e86e3730561b38095eff2cfcc9b71d6b95bd224  specs/262-recording-deletion-lifecycle/checklists/requirements.md
22d032ef5d2cd165ca4a2b84e5b3169ce4b4bd474c7237388aa72cfa57bbcb78  specs/262-recording-deletion-lifecycle/checklists/security-ux.md
fc535eaefb2eb265cae174508dcb06b548a3df3dc1f4bd54fb68a50d79ff4d27  apps/server/src/twobrain_rec_server/db/models/deletion.py
6ade5be83afcd81c29b944651c3a08ac1916e1f0a6b037277f4a744e23da886c  apps/server/src/twobrain_rec_server/db/migrations/versions/0007_retention_deletion_execution.py
52df617bd877cd5877aaab074633a2617d469fb06f5462106ca0416b2d4e9ceb  apps/server/src/twobrain_rec_server/db/migrations/versions/0092_recording_origin_cancellation.py
eb1d62aaa300b6a2eb2e54561a383678e6be3c66887745951c14f2a87876677b  apps/server/src/twobrain_rec_server/deletion/audit.py
28c77b81e076dd37dde7474fe14c580fdd1b5a765fcd4b383ab76d414e417d85  apps/server/src/twobrain_rec_server/deletion/origin_cancellation.py
7c02907ed64464f4baffe2f87b2a9d48f8a65b250140d48222b9f1ea33a14aaa  apps/server/src/twobrain_rec_server/api/ingest.py
4534012daa4f54dfe5fd58cc8bba5674c4771e9c108697c34820b4a3c5b3aa00  apps/server/src/twobrain_rec_server/deletion/service.py
79d81885bc6af41c503d233b3224abd4f1d775c0e84bbadae11c5dd4e0b972b2  apps/server/src/twobrain_rec_server/admin/audit.py
```

Дополнительно полностью прочитан внешний план исполнителя
`/Users/yshishenya/Documents/Codex/2026-10-21/issues-334-audit/f262-t008-correction-plan-20261022.md`. Его область, scoped analyze CRITICAL0/HIGH0,
минимальное решение и восемь групп будущих проверок согласованы
с профилем этого отчёта. SHA-256 плана: `7681818803d017632fb70804f287bcdcfe20b1a351746e853e2300b24947ef03`.
