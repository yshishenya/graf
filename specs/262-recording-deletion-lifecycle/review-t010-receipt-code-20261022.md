# Независимое ревью исправления сетевых подтверждений T010

Дата: 2026-10-22. Проверяющий: `f262_requirements_reviewer`.
Фича/задача: F262/T010, [#6885](https://github.com/yshishenya/graf/issues/6885).
Ветка: `codex/262-validate-deletion-receipts`.
HEAD/основа: `eb929969fd9323b7b6489d1d25c245562f2d7e7c`.
Объект ревью — незакоммиченная дельта четырёх файлов на этой основе;
только HEAD не идентифицирует проверенные изменённые байты.
Применён навык `code-reviewer`, проведено чтение diff и всех найденных
production callers; исполняемые тесты проверяющий самостоятельно не запускал.
Разрешено изменение только этого отчёта; общие правки других участников
сохранены.

## Решение

**PASS в проверенной области: обязательных замечаний P0/P1/P2/P3 не найдено.**
Изменение закрывает ранее найденный пробел принятия сетевого receipt без
проверки phase; новый обязательный рефакторинг или расширение области не нужны.
Рекомендация — принимать этот код после обязательных проверок PR точного SHA
и основы. Этот отчёт не означает, что PR уже проверен/слит или #6885 закрыта.

Качество требований до реализации проверено отдельно:
[review-t010-receipt-checklists-20261022.md](review-t010-receipt-checklists-20261022.md),
20 подтверждённых пунктов / 0 неподтверждённых. Хеши обязательных документов
повторно сверены с его таблицей: содержание конституции, PRD, статуса,
применённых guidance и всех документов F262 совпало. Суждения этого ревью
относятся к текущей дельте, а прежний implementation FAIL сохранён как история.

## Проверка причины и исправления

| Проверенная граница | Наблюдение и вывод |
| --- | --- |
| Прямые origin/meeting POST | `DesktopUploadClient.swift:873–877` запрашивает private `AcceptedRecordingDeletionReceipt`; неправильный phase не преобразуется в domain receipt |
| Строгость phase | Обёртка на 1713–1723 требует именно строку `accepted`. Иной текст даёт invalidResponse, missing/null/nonstring даёт DecodingError; значение по умолчанию не подставляется |
| Вложенные lifecycle receipts | `DesktopRecordingLifecycleEntry.init(from:)` на 1734–1739 использует ту же обёртку. Невалидный имеющийся receipt прекращает декодирование ответа; nil receipt остаётся nil и сам по себе не разрешает accepted |
| Все сетевые входы | Поиск всех `RecordingDeletionReceipt`/`DesktopRecordingLifecycleEntry`/callers выявил прямой POST, `recordingLifecycle(origins:scope:)` и meeting lookup после 404. Последние два декодируют общий entry, обхода строгой проверки не найдено |
| Identity/scope/ошибки | capability/version и actor/workspace до запроса, scoped headers, target.matches, receipt kind/epoch и Retry-After сохранены. Неоднозначный ответ продолжает путь `.resolving`, не становится доказанным отказом или успехом |
| Очередь и очистка | Исполнитель сначала сохраняет намерение. До `operation.accepting` невалидный сетевой ответ не доходит; у origin нет accepted receipt, поэтому `finishAcceptedOriginDeletions` не получает разрешение очистки |
| Формат хранения | Shared `RecordingDeletionReceipt` Codable, `RecordingDeletionOperation` и queue v3 не изменены; сетевой тип не сохраняется. Старый receipt без вложенного phase продолжает читаться |
| Монотонность и неизвестная схема | Существующие guards accepted/verified, обязательность matching receipt и отказ unknown queue schema не затронуты |
| Сервер и дополнительные разрешения | Действующие `DeletionRequestResponse`/`OriginCancellationReceipt` уже выдают Literal accepted. API, политика очистки, авторизация, миграции и дополнительная серверная гарантия не меняются |
| Размер и сопровождение | Один небольшой private Decodable и явный decoder entry, без новой зависимости, общей машины состояний или форматной миграции. Существенного влияния на память/скорость нет |

В единственной иной реализации `requestRecordingDeletion` в тестовом fake
`RecordingDeletionPurgeAcceptanceTests.swift` domain receipt создаётся прямо;
это не сетевой production decoder. Отсутствие wire phase у таких domain
фикстур сохранено намеренно, аналогично сохраняемым fixtures.

При неправильном вложенном receipt весь bounded lifecycle ответ может быть
отклонён. Это безопасное сохранение неопределённости с последующей попыткой,
а не ложное принятие или очистка. Новое специальное восстановление части
недостоверного ответа не требуется для существующего контракта.

## Проверка тестов и доказательств

Новый `testNetworkReceiptPhaseControlsAcceptanceAndOriginCleanup` вызывает
настоящие `DesktopUploadClient` и queue service через синтетический
requestExecutor; использует временные собственные каталоги и настоящий
файловый эффект. Положительная ветвь каждого маршрута проверяет, что настройка
достигает принятия; отрицательная проверяет сохранённое состояние и неизменные
байты manifest после перезапуска queue service.

Матрица: **5 маршрутов × 7 вариантов phase = 35 сочетаний**, в том числе
5 положительных и 30 отрицательных. Это один XCTest, не35 отдельных XCTest.

| Маршрут | Что покрыто |
| --- | --- |
| direct-origin | origin_cancellation, accepted очищает manifest; шесть неправильных phase сохраняют файлы и resolving с исходным ID/target |
| direct-meeting | meeting_deletion для meeting target; неверный phase не принимает команду и не удаляет локальные байты |
| origin-as-meeting | own-origin POST возвращает meeting_deletion; допустимая связь origin→meeting сохранена, файлы не очищаются как never-created |
| origin-lookup | вложенный origin_cancellation/canceled_before_creation; неверный phase не создаёт accepted операцию и не очищает файлы |
| meeting-fallback | исходный404 meeting_not_found, затем вложенный meeting_deletion/deletion_accepted; строгая проверка сохраняется после разрешения исхода |

Варианты: accepted, rejected, неизвестная строка future, null, число1,
boolean true, отсутствующее поле. Нестроковые массив/объект отдельно не
перебираются, но обязательный `decode(String.self)` однозначно их отвергает;
обязательного пробела в этом ограниченном исправлении не найдено.

Новый `testPersistedAcceptedReceiptsWithoutWirePhaseSurviveRestart` проверяет
accepted и verified прежней meeting receipt: отсутствие вложенного phase в
JSON, запись документа, чтение реальным queue service, полное равенство операции
и невозможность понижения в rejected. Дополнительные2 варианта roundtrip входят
в один XCTest. Общий Codable receipt и его enum/kind не меняются, отдельной
миграции origin receipts не требуется.

Три прежние группы HTTP-фикстур в lifecycle/bulk/recovery получили поле
accepted, соответствующее действующей серверной схеме; domain/сохраняемые
фикстуры без phase не были массово переписаны. После первого GREEN основной
агент убрал из синтетического origin_cancellation несуществующие meeting
поля. Текущий исправленный fixture повторно прошёл расширенный профиль;
первый GREEN не выдаётся за единственную проверку окончательных байтов.

Журналы прочитаны и независимо разобраны по полным XCTest-именам:

| Журнал | Результат и предел |
| --- | --- |
| f262-t010-receipt-red-20261022.log | 2 XCTest: новый сетевой тест FAIL, сохранённая совместимость PASS;120 сообщений assertion failure, включая12 ошибок отсутствия manifest.30 сообщений Invalid network phase accepted подтверждают все отрицательные сочетания до исправления |
| f262-t010-receipt-green-20261022.log | Те же2 XCTest PASS,0FAIL/0SKIP, до последнего уточнения origin fixture |
| f262-t010-focused-20261022.log | 223 разных XCTest PASS,0FAIL/0SKIP, финальный Selected tests passed. Новые2 уже входят в223 |

Расширенный профиль: DesktopLocalPurge7, DesktopMeetingShellWebViewBoundary19,
DesktopUploadClient49, DesktopUploadCustodyProjection30, DesktopUploadQueue83,
RecordingDeletionBulkAcceptance1, RecordingDeletionLegacyAcceptance2,
RecordingDeletionLifecycle23, RecordingDeletionPurgeAcceptance5,
RecordingDeletionRecoveryAcceptance4. Сумма223, повторов имён нет.
Итоги вложенных XCTest suites и финальная строка Swift Testing с0 tests не
считаются дополнительными проверками. Старые165 и35 сочетаний к223 не прибавляются.

RED доказывает реальный файловый эффект только в синтетическом окружении:
12 отсутствующих manifest соответствуют двум origin-cancellation маршрутам
и шести неправильным phase. Это сильнее прежней decoder-only пробы, но не
свидетельство производственного ответа, удаления пользовательских данных
или проверки установленного GRAF Dev.

## Ограничения и следующий шаг

- Ревью не запускало приложение, сборку, тесты, производственные запросы,
  GitHub mutation, commit, release или deploy. Проверены исходники и журналы
  исполнения основного агента; `git diff --check` PASS.
- Дельта ещё не закоммичена. Привязка здесь — контрольные суммы файлов/diff;
  журнал локального профиля не заменяет GitHub CI точного будущего PR SHA/base.
- Полный повтор S01–S51, аппаратная приёмка, установленный клиент, release-full
  и production не заявляются выполненными. Исправление receipt не восстанавливает
  истёкший CI артефакт PR#6911 задним числом.
- После фиксации окончательного кандидата основной агент должен выполнить
  оставшиеся проектные ворота, сверить владение T010 и допустимое closeout
  evidence; лишь затем решать закрытие #6885 с подробным комментарием.
  Найденных оснований для дополнительной правки кода в текущем объёме нет.

## Контрольные суммы

SHA-256 diff по четырём файлам изменения и трём неизменённым queue/model
consumers относительно основы: `dbda7b2af2c05260ccbc7d5c781cccf74b4c1c0d4b5067d68a57a3727245a270`.

| Источник относительно корня репозитория | SHA-256 |
| --- | --- |
| `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` | `aa208b0d7fdaf62b94976a8741ed8b228eaaec5f0e89c0aa65a70a018d50812f` |
| `apps/macos/Shared/Tests/RecordingDeletionLifecycleTests.swift` | `88616cfc359b2f2a8038a48f41e7fa4c2667c78a2ac2568a3471db08901d47dd` |
| `apps/macos/Shared/Tests/RecordingDeletionBulkAcceptanceTests.swift` | `5753fc12481fd93d52f7f4dc78ddbf8c34aeba6731f0e3e9bff49e89aa3dba51` |
| `apps/macos/Shared/Tests/RecordingDeletionRecoveryAcceptanceTests.swift` | `58e935dc8a729e18903167cbf7525ef8e510077e637f62d8eaf636f4caf29b5f` |
| `apps/macos/Shared/Sources/Models/RecordingDeletionLifecycle.swift` | `8ce68fc8c7b999a2ef3266a0b1217cc249f32fdc3fc830852aafcf7112ee39ad` |
| `apps/macos/Shared/Sources/Models/AudioModelCore.swift` | `1a6f994d2ce1844f00d9989a4b1cb94c3c0b21d462e2e64cd90a249e1802e748` |
| `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` | `8b08fb8031a592d9dc8499c0cbb4244fefa9175c491fbab74c78f8ac6463c535` |
| `apps/server/src/twobrain_rec_server/api/schemas.py` | `572e9df589572edc382005d512f65037e082d2a080b0ed9f4da4437f0a34f539` |
| `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py` | `ba2b9ffab87f7b19a8a3cd47dc7ab15b693a3b8bcbae0a6f720eedc06f43863d` |
| `specs/262-recording-deletion-lifecycle/review-t010-receipt-checklists-20261022.md` | `32a827307c3421eaecb2a30fa3bdd171a599d89f269c150245aaefdb8d20e75c` |
| `docs/agent-guidance/development-process.md` | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |

| Внешний журнал | SHA-256 |
| --- | --- |
| `f262-t010-receipt-red-20261022.log` | `d5b04de64d3f3813dd9e234dfc5ef5a67bae87c1270e5102b48ce607da21ebf9` |
| `f262-t010-receipt-green-20261022.log` | `4fd0e5512b1d14ff83b8e092aba709727360db81af450223ffcc2571aef4efce` |
| `f262-t010-focused-20261022.log` | `5062741bbbd960d144bffcc62deb436a373daeb4ba598adaa7008966a4ffbcd2` |

Применённый `code-reviewer/SKILL.md` SHA-256: `d2bd763e7cfa424845c54639d4a97cdb0aa03b5eedeabb1d171a16086584cec9`.
