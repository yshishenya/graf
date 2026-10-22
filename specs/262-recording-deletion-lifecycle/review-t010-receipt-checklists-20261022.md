# Независимая проверка требований перед исправлением T010

Дата: 2026-10-22. Проверяющий: `f262_requirements_reviewer`.
Исходная ветка: `codex/262-origin-cancellation-audit`.
Исходный HEAD: `40670c6bc44084b85b23576681082f3cabdec137`.
Задача: [#6885](https://github.com/yshishenya/graf/issues/6885), F262/T010.
Режим: независимая проверка требований существующего high-risk-feature.
Разрешены изменения только двух reviewer-owned чеклистов и этого отчёта.

## Решение

**Качество требований: PASS.** requirements — 10 отмечено / 0 не отмечено;
security-ux — 10 отмечено / 0 не отмечено. Все 20 пунктов рассмотрены отдельно.
Неоднозначности, требующей нового продуктового решения владельца, не найдено.
Проверка серверного принятия уже обязательна по FR-002/004/007/008 и контракту.

**Приёмка текущей реализации T010: FAIL в проверяемой границе receipt.**
Issue #6885 остаётся открытой: найден обязательный пробел проверки сетевого
ответа. Отметки качества требований не означают завершённую реализацию,
прохождение CI, установленную приёмку или выпуск.

## Проверенное замечание

1. В `apps/macos/Shared/Sources/Models/RecordingDeletionLifecycle.swift:193`
   `RecordingDeletionReceipt` декодирует тип, request/target identity и epoch,
   но не содержит `phase` в свойствах или CodingKeys. Поле ответа игнорируется.
   `matches` проверяет identity и неотрицательный epoch, а не принятие.
2. `DesktopUploadClient.swift:1445` принимает любой 2xx и декодирует выбранный
   тип. В `requestRecordingDeletion` (840–903) прямой ответ декодируется в этот
   receipt; последний guard проверяет только `matches`. Предварительная
   capability/version и actor/workspace проверка не валидирует тело ответа.
3. В `DesktopUploadQueueService.swift:310` возвращённый receipt передаётся в
   `RecordingDeletionOperation.accepting`; этот метод проверяет только identity
   и совместимость с прежним receipt, затем сохраняет `.accepted`.
4. Для `origin_cancellation` путь `finishAcceptedOriginDeletions` (379–405)
   использует `.accepted` как разрешение удалить собственные локальные файлы.
   Поэтому ответ с подходящим identity, но `phase: rejected` или неизвестным
   phase может ошибочно стать локальным подтверждением принятия. Для
   `meeting_deletion` существуют дополнительные task/reconcile проверки перед
   физической очисткой; немедленная очистка встречи одним таким ответом здесь
   не заявляется.
5. Уязвима также граница вложенного receipt: `DesktopRecordingLifecycleEntry`
   (`DesktopUploadClient.swift:1710`) декодирует общий тип без phase, а
   `synchronizeRecordingLifecycle` (265–307) превращает receipt при
   deletion_accepted/canceled_before_creation в accepted operation.
   Fallback после meeting_not_found в `requestRecordingDeletion` использует
   те же lifecycle entries; исправить только прямой POST недостаточно.

Существующие серверные схемы `DeletionRequestResponse` и
`OriginCancellationReceipt` в `api/schemas.py:1254,2497` задают
`phase: Literal["accepted"]`; lifecycle lookup создаёт эти схемы.
Следовательно, нормальные ответы действующего сервера совместимы со строгой
проверкой. Неправильного производственного ответа и реальной потери данных
этим обзором не установлено: обнаружен клиентский приём ответа, нарушающего
действующий контракт.

Прочитан журнал `f262-t010-receipt-probe-red-20261022.log`, предоставленный
основным агентом: `source_receipt_matches_target_with_rejected_phase=true`.
Проба извлекает исходную структуру receipt и проверяет decoder/matches;
**это не полный HTTP/queue/purge запуск**. Собственных исполняемых тестов,
приложения и производственных действий проверяющий не запускал.

## Граница совместимости сохранённой очереди

`RecordingDeletionReceipt` одновременно служит сохраняемой моделью:
`RecordingDeletionOperation` Codable содержит receipt, а queue v3 содержит
массив таких операций (`AudioModelCore.swift:1892–1940`). Нынешний encoder
не сохраняет вложенный phase. Поэтому существующие accepted/verified операции
нормально имеют receipt без этого поля. Операционный phase хранится отдельно.

Нельзя просто сделать phase обязательным в общем Codable receipt: это сломает
чтение законных прежних подтверждений и восстановление запрета повторной
отправки/возвращения записи. Нельзя удалять старую очередь, сбрасывать операции
или подменять ошибку декодирования новым пустым состоянием.

Минимальный рекомендуемый путь — отдельная **сетевая** Decodable-обёртка или
небольшой тип ответа, который строго требует строку `phase == "accepted"`,
декодирует существующие поля и лишь затем возвращает прежний domain receipt.
Такая же проверка нужна для каждого вложенного сетевого lifecycle receipt.
Точный способ остаётся решением исполнителя; новый формат очереди, миграция,
изменение server API, новая машина состояний или зависимости не требуются.

Отсутствующий, null, нестроковый, неизвестный или rejected phase в сетевом
подтверждении не разрешает accepted/verified и файловую очистку. Не следует
превращать неверный receipt в доказанный серверный отказ: результат сохраняет
путь разрешения неизвестного исхода. Законный ранее сохранённый accepted
остаётся монотонным при ошибке нового ответа. Существующие scope, target,
receipt kind, epoch, атомарность и отказ неизвестной schema сохраняются.

## Основания всех пунктов requirements

| Пункт | Основание | Итог |
| --- | --- | --- |
| Пользовательское поведение | US1–US5 и FR-002/004/007 задают результат и основания удаления; сетевой DTO — способ реализации существующего требования | PASS |
| Ценность, приоритеты, границы | Все пять US имеют P1, Why и Independent Test; T010 принадлежит US3, без расширения capture/server политики | PASS |
| Обязательные секции | В spec имеются истории, сценарии, FR, сущности, SC, предположения и Clarifications | PASS |
| Нет обязательных уточнений | Clarifications определяют неизвестный исход и долговечность; contract прямо требует phase=accepted | PASS |
| Проверяемость и однозначность | FR-002/004/007 и контракт позволяют проверить accepted против неизвестного/отказа, отдельно сеть и сохранённую очередь | PASS |
| Измеримые результаты | SC-001–007 задают отсутствие возврата/новой встречи, сроки и индивидуальные результаты; неверный phase не является успехом | PASS |
| Положительные/отрицательные/конкурентные сценарии | S05/S08/S19/S27/S28/S36–S40/S50 плюс create/cancel покрывают потерю ответа, контекст, восстановление и границы очистки | PASS |
| Предположения и пределы | FR-018/022, Assumptions, contract/Purge различают принятие, текущий Mac, недоступные устройства, retained observability и rollback | PASS |
| Требование/код/доказательство | Проектные требования и исторические результаты различаются; настоящий отчёт явно фиксирует текущий FAIL и предел decoder-пробы | PASS |
| Конституция/MVP | Constitution II/IV/VI, product-gates/Deletion Truth; ручной Stop сохранён, универсальное стирание и удаление observability не вводятся | PASS |

## Основания всех пунктов security-ux

| Пункт | Основание | Итог |
| --- | --- | --- |
| CHK001 | data-model/Идентичность, FR-009/019: actor/execution scope отдельно от target creator, local_unbound отдельно от legacy_unknown | PASS |
| CHK002 | FR-002/004–008; оси intent/accepted/rejected/unknown/purge и явный phase=accepted в contract | PASS |
| CHK003 | FR-008/021; contract/origin, S10–S14 задают cancellation до create и запрет позднего результата | PASS |
| CHK004 | FR-007/013/014, data-model/Восстановление, contract/Purge, S25/S32–S38: строгое основание, реальные файлы и late ACK | PASS |
| CHK005 | FR-010–012/017, US4, S18–S23/S41: замороженный выбор, отдельные результаты и фокус | PASS |
| CHK006 | SC-003, contract/Состояние origins, S24/S28/S46/S51: origin и meeting lookup, denied/offline не дают purge | PASS |
| CHK007 | FR-015/018, contract/Плеер, S30/S31/S42: управляемая сессия и честные внешние пределы | PASS |
| CHK008 | FR-019/020/022, data-model/Сериализация и Восстановление, S27/S37–S40/S47: неизвестная schema, старые receipts, scope и rollback | PASS |
| CHK009 | SC-002/003/006 отделяют получение авторитетного разрешения, сеть/сон и измеряемую очистку | PASS |
| CHK010 | FR-016, S15/S16, Constitution II: active/saving исключены из delete, ручной Stop доступен | PASS |

## Обязательная будущая проверка исправления

- Сетевые положительные ответы обоих receipt kinds с accepted проходят все
  прежние identity/scope проверки. Origin, преобразованный сервером в
  meeting_deletion, остаётся поддержан.
- На прямых POST проверить rejected/unknown/missing/null/nonstring phase;
  сохранённая операция не становится accepted/verified, файлы остаются,
  исходный ID/target и возможность выяснения результата сохраняются.
- То же для lifecycle own_origin и meeting fallback после 404. Одного
  отрицательного decoder-теста для HTTP/purge границы недостаточно.
- Настоящий queue/filesystem тест на синтетическом origin с неверным сетевым
  phase доказывает отсутствие очистки, не только thrown error.
- Прежний queue v3 с accepted и verified receipt без вложенного phase читается,
  сериализуется и переживает restart без потери target/receipt/tombstone.
  Сохраняются монотонность, отказ missing receipt у accepted и unknown schema.
- Подтвердить исходный отказ до исправления и прохождение после него; обновить
  только сетевые фикстуры, которым теперь требуется accepted. Сохранённые
  domain/queue фикстуры без phase не переписывать для маскировки несовместимости.
- После реализации требуется отдельное независимое ревью кода и доказательств;
  обязательные exact-SHA/base PR проверки и live closeout issue остаются
  обязанностью основного агента. Старые 11 T010 случаев из набора165 не
  доказывают эту ранее отсутствующую проверку phase.

## Прочитанные источники и SHA-256

Полное повторное чтение обязательных документов выполнено после сжатия
контекста; совпадение хеша само по себе не использовалось как приёмка продукта.
Пути в таблице относятся к корню репозитория. Внешний журнал указан только
без приватного содержимого и без пути к пользовательским данным.

| Источник | SHA-256 |
| --- | --- |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `specs/262-recording-deletion-lifecycle/spec.md` | `f64766bd86981a52c7d18019cd418a8d227756de02e234af1e1d28cf762e063d` |
| `specs/262-recording-deletion-lifecycle/plan.md` | `25d14d4fd41cbc9a7364805722a92173f8e3b93debdd9f30efbfae21e3542cb3` |
| `specs/262-recording-deletion-lifecycle/tasks.md` | `f4ed5a207676dfa3fe7f2803c6fbcd447f2bc5faa49e812ba5617fa4c26175ce` |
| `specs/262-recording-deletion-lifecycle/data-model.md` | `0d3514d73303dd20c4e991b89ba6778de54a88cee5007a5b1684359f44a2367e` |
| `specs/262-recording-deletion-lifecycle/contracts/lifecycle.md` | `f0652db20a6369046802a78320c44f0fa7da1df506aed106d0790a724abc66ef` |
| `specs/262-recording-deletion-lifecycle/research.md` | `696aeff0f6dfe2da78cbd5a702eb5f57a32fd187011a114083b1cc2b9d7a636b` |
| `specs/262-recording-deletion-lifecycle/analysis.md` | `3c2ead5b0cfbf492d8c95c8a26b59b8dcd6d11accc872a9e997512d0077af4da` |
| `specs/262-recording-deletion-lifecycle/scenarios.md` | `29df91c40b00227e6f682394e4a1f5b0fdc8a426b7c734591a934fab72cb434b` |
| `specs/262-recording-deletion-lifecycle/quickstart.md` | `a728d664177055ad0544c3a2f1b72eee209805ce2612472ca4b2795bdedb2bb0` |
| `apps/macos/Shared/Sources/Models/RecordingDeletionLifecycle.swift` | `8ce68fc8c7b999a2ef3266a0b1217cc249f32fdc3fc830852aafcf7112ee39ad` |
| `apps/macos/Shared/Sources/Models/AudioModelCore.swift` | `1a6f994d2ce1844f00d9989a4b1cb94c3c0b21d462e2e64cd90a249e1802e748` |
| `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` | `9403fc45728c531076ce3e886059fca0080dd485110d14b02580244e716660fc` |
| `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` | `8b08fb8031a592d9dc8499c0cbb4244fefa9175c491fbab74c78f8ac6463c535` |
| `apps/server/src/twobrain_rec_server/api/schemas.py` | `572e9df589572edc382005d512f65037e082d2a080b0ed9f4da4437f0a34f539` |
| `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py` | `ba2b9ffab87f7b19a8a3cd47dc7ab15b693a3b8bcbae0a6f720eedc06f43863d` |
| `apps/macos/Shared/Tests/RecordingDeletionLifecycleTests.swift` | `7b1ccc44daec46755f7cc3948284e8404d471ead503d8c9c7b4e7df1dc8657ec` |
| Внешний `f262-t010-receipt-probe-red-20261022.log` | `2055fcbe47c3da5a5599400edfe5c6a62142ba5162a8a53a9e45d473e0b07656` |

Прочитана live issue #6885 с критериями и обоими комментариями 2026-10-22:
OPEN. Состояние GitHub не менялось. Исходный рабочий каталог был чистым.
После записи оба чеклиста перечитаны: **10/0 + 10/0 = 20/0**.
Код, spec, plan, tasks, governance, Git, приложение, данные, release/deploy
проверяющий не изменял. Проверка `git diff --check` фиксируется при передаче;
эта проверка форматирования не является исполняемой приёмкой T010.
