# Независимая повторная проверка требований F262/T001

Дата: 2026-10-22. Проверяющий: `f262_requirements_reviewer`, отдельный агент,
не автор текущего `analysis.md` или продуктового кода.
Ветка: `codex/262-requirements-recheck`.
Проверенный исходный SHA: `e20fa6a9001cceac327358f61462e7a461f80e57`.
Задача: [#6876](https://github.com/yshishenya/graf/issues/6876), T001.
Область проверки: качество требований и согласованность исходных проектных
документов с действующими правилами; дорожка проверки — существующий срез
Spec Kit, документальная проверка без изменения поведения удаления.

**Требования: PASS, CRITICAL 0 / HIGH 0.** После повторного чтения:
`requirements.md` — 10 отмечено / 0 не отмечено;
`security-ux.md` — 10 отмечено / 0 не отмечено. Исходные формулировки и
строгость критериев сохранены. Свежие профильные журналы и ключевые проверки
кода дополнительно перепроверены: **160 различных Swift-тестов, 33 PostgreSQL-теста
и один сценарный запуск Chromium — PASS**. Содержательная проверка T001 пройдена.
Закрытие #6876 допускается после обязательных проверок нового PR на точном SHA
и основе, слияния и live-проверки закрытия; эти этапы reviewer не выполнял.

## Основания проверки качества спецификации

Нумерация соответствует исходному порядку десяти пунктов
`checklists/requirements.md`; новые требования не добавлены.

| № | Результат и прямое основание |
|---|---|
| 1 | PASS. `spec.md`, пять историй и FR-001–022 описывают доступность записи, выбор, результат удаления и ошибки. Способы хранения/блокировок вынесены в `plan.md`, `data-model.md`, контракт. |
| 2 | PASS. У каждой истории есть Priority P1, Why this priority, Independent Test и Given/When/Then; история 5 явно ограничивает управляемые устройства, доступ и неизвестное удаление. |
| 3 | PASS. Заполнены User Scenarios, Edge Cases, Requirements, Key Entities, Success Criteria, Assumptions и Clarifications. Нумерация FR-001–022, SC-001–007 и S01–S51 непрерывна. |
| 4 | PASS. Clarifications от 09.09 различает рекомендации и ответы владельца; scope удаления, offline, identity, права, неизвестные ответы и восстановление определены. Обязательного незаполненного продуктового решения не найдено. Выпуск остаётся отдельной проверкой. |
| 5 | PASS. FR-002/004/007 не позволяют выводить удаление по отсутствию строки, 403/404 или таймауту; FR-003/014/021 придают принятому удалению приоритет. Контракт разделяет receipt отмены origin и удаления существующей встречи, S10–S14 требуют оба порядка гонки. Противоречащих допустимых исходов не найдено. |
| 6 | PASS. SC-001/004/005 задают наблюдаемые результаты, SC-002 — 1 с, SC-003 — 60 с/5 с в доступной активной среде, SC-006 — 100 пакетов до 100 МБ/60 с и действующий серверный предел 24 ч; SC-007 — клавиатура/экранный диктор. Технология реализации не является условием успеха. |
| 7 | PASS. S01–S51 включают обычный успех, отказ/таймаут/429, сохранение до сети, оба порядка create/cancel, позднюю публикацию, восстановление, смену контекста, безопасные пути и внешний экспорт. |
| 8 | PASS. Assumptions, FR-015/018, S31/S42 и контракт явно различают сервер, локальную очистку, резервные копии, MediaScribe, скачанные копии и retained Generation Call/Langfuse/Temporal. Корзина и отзыв чужой внешней программы не обещаны. |
| 9 | PASS в области требований. План/исследование фиксируют проект от 09.09; более поздние разделы `evidence.md`, `scenario-evidence.md`, `implementation-review.md` отдельно описывают реализацию, измерения и ограничения. Ни 51 безусловный GUI PASS, ни p95 там не заявлены. Исторические шапки о «проекте»/«PR перед review» сами по себе не являются текущим статусом GitHub; см. замечания ниже. |
| 10 | PASS. Конституция 7.1.0 §II/IV/VI, действующие Product Gates и PRD §18/23/25/29 сохранены: ручной Stop; native capture truth; whole-meeting deletion; принятый факт отдельно от очистки; lifecycle accounting; retention наблюдений; права/границы файлов; доступность интерфейса. Автозапись, обработка моделью и публичная поставка не переопределяются этой фичей. |

## Основания CHK001–CHK010

| Пункт | Результат и прямое основание |
|---|---|
| CHK001 | PASS. `data-model.md`, «Идентичность»: server origin/workspace/creator/local ID, отдельный ExecutionScope с actor; local_unbound отдельно от legacy_unknown. S46/S47/S49 требуют server-only, запись без входа и manager-delete. |
| CHK002 | PASS. FR-002/004–008, оси состояния модели и «Существующее удаление по meeting_id» контракта различают intent, accepted, verified, rejected и resolving. HTTP 202 означает принятие; 401/403/404 не являются доказательством. |
| CHK003 | PASS. FR-008/021, «Новая отмена по origin», сериализация модели и S10–S14 определяют отмену до create, общий lock, запрет создания/повторной публикации; сохранены epoch и существующий purge. |
| CHK004 | PASS. FR-007/013/014; «Восстановление» модели; Purge контракта; S25/S32–S38 определяют безопасные пути, сохранение намерения до эффекта, проверку пакета, потерянный ACK, поздний проверенный ACK и отсутствие purge при неизвестном состоянии. |
| CHK005 | PASS. FR-010–012/017, «Команды приложения и WebView» и тексты контракта, S18–S23/S41 определяют один подтверждённый набор до 100, aliases, частичный результат, повтор незавершённого, пустой список и фокус. |
| CHK006 | PASS. SC-003; lookup по собственному origin отдельно от meeting_id доступной чужой/server-only записи; S24/S28/S46/S51. Native хранит offline intent, обычный браузер не обещает очередь после закрытия вкладки. |
| CHK007 | PASS. FR-015/018, «Плеер и уже переданные данные», S30/S31/S42: отзыв управляемой сессии GRAF, никакого обещания отзыва скачанного внешнего файла; Generation Call/Langfuse/Temporal сохраняются по политике оператора. |
| CHK008 | PASS. FR-019/020/022; модель: scope/generation, legacy/recovery/quarantine; план: сервер до клиента, capability, запрет передачи v3 несовместимому бинарнику; S27/S37–S40/S47. Подмена rollback старой очередью поверх новых tombstones не разрешена. |
| CHK009 | PASS. SC-002/003/006 и quickstart «Нагрузка и время» задают начало отсчёта, объём, доступную среду и различают время получения факта/очистки/недоступную сеть. Единичный результат не называется p95. |
| CHK010 | PASS. FR-016, S15/S16, приоритеты модели и план сохраняют Stop, запрещают скрытое удаление active/saving и отделяют WebView от контроля захвата. |

## Свежая независимая сверка анализа и тематических проверок

Историческая часть `analysis.md` перечитана полностью, её таблица независимо
сверена с FR-001–022, SC-001–007 и существующими описаниями T001–T023:

| Требования | Проверенное соответствие задачам |
|---|---|
| FR-001,010–012,017 | T014–T018: единая выдача, выбор, подтверждение и результат |
| FR-002–009,014,019 | T002–T012: состояния, сохранение команды, права, удаление и доступ |
| FR-013,020 | T004,T011–T013,T019: восстановление очистки и старых записей |
| FR-015 | T005,T017,T019: управляемое воспроизведение и проверка удаления |
| FR-016 | T004,T015,T016,T019: активная запись и сохранение ручного Stop |
| FR-018 | T006,T011,T018,T019: пределы очистки и отчёт |
| FR-021 | T007–T010,T019: гонки обработки и запрет поздней публикации |
| FR-022 | T003,T012,T013,T019,T021: совместимость состояния и выпуска |
| SC-001–007 | T019–T021 вместе с тематическими проверками предшествующих задач |

Не найдено требования без задачи, отсутствующего номера или противоречия
описанию задачи. Исторические ранние FAIL, последующий post-hook PASS,
добавление T022/T023 и результат установленной приёмки 0e19 сохранены.
Новая датированная сверка `analysis.md` отдельно и честно описывает нынешние
результаты. Дополнение Legacy Impact в `spec.md` соответствует прежним
FR-014/015/019/020/022 и не меняет критерии, данные или миграцию.

Reviewer самостоятельно прочитал журналы и сопоставил важные проверки с кодом;
запуски выполнил основной исполнитель на исходном продуктовом коде
`e20fa6a9001cceac327358f61462e7a461f80e57`. Текущие изменения документальные.
Файлы журналов сохранены вне Git в каталоге проверки `issues-334-audit`.

| Журнал от 22.10.2026 | Фактический результат | SHA-256 |
|---|---|---|
| `f262-swift-recheck-20261022.log` | 49 разных PASS: LocalPurge 7, WebViewBoundary 19, CustodyProjection 23 | `5c12cbd1e491a850179d345fa83d160ceb3c9f27dca7e75b040a5362a7fba12b` |
| `f262-swift-queue-recheck-20261022.log` | 78 разных PASS, DesktopUploadQueueTests | `dc5f4a6c28322419f90636799cdaa68630938bce997d1274b28d5180cca1e4d3` |
| `f262-swift-deletion-recheck-20261022.log` | 33 разных PASS: lifecycle 21, purge 5, recovery 4, legacy 2, bulk 1 | `5a53fe6eb8962fbd29ae4d4c178fef693fecd8fefbd04d35256254bb53b17e5f` |
| `f262-postgres-recheck-20261022.log` | 18 PASS: origin cancellation 9, local purge 8, deletion access 1 | `41f72d20716528702091e3b541653c69021f42d52a76565eabd0dc0fb234a19c` |
| `f262-postgres-additional-20261022.log` | 15 PASS: HX feedback 7, sync conflicts 6, workflow deletion races 2 | `5709a1edeebad982cb63297fda5261e398c207e4771241161b9d063c14e6ecd4` |
| `f262-browser-recheck-20261022.log` | Один успешно завершённый Chromium script mixed-meeting-list | `91cd7e45e767a84628f4c30ce45395082efec43ac694339f4128f26f38e83d71` |

Полные имена успешно завершённых Swift-тестов разобраны независимо: 49 + 78 + 33
дают 160 уникальных имён без пересечения. Повторяющиеся строки общих итогов
не суммировались. Первоначальный фильтр с именем `DesktopUploadQueueV5Tests`
не выбрал очередь: это имя файла, фактический класс — `DesktopUploadQueueTests`
в `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift:10`. Отдельный
правильный фильтр дал 78 PASS; текущий quickstart исправлен ровно в этом месте
и перечитан целиком. Во всех трёх наборах Swift нет отказов или пропусков.
Имеющиеся предупреждения компилятора не препятствовали сборке.

PostgreSQL: два набора состоят из непересекающихся файлов и дают 33 случая.
Все пять файлов quickstart покрыты; origin cancellation — шестой дополнительный.
Оба запуска завершились `postgres_test_result=pass` и
`postgres_test_cleanup=isolated_container_removed`. Два предупреждения каждого
запуска относятся к pytest rewrite и устаревающему Starlette/httpx;
отказов/пропусков нет. Digests собранных наборов:
`c77a26c45a8d2953d15240f2dfaceb6cd04cf19123264aaf86eac71e81b95777`
и `d5c150eec91605a972423985904c16eb4d45f6b5758425107793ccda6a3185ac`.

Проверены существенные утверждения, а не только строки успешного итога:

- `testAcceptedOperationNeverRegressesOnLateResponse`,
  `testLateUploadTransitionCannotEraseTombstone` и
  `testServerDeletionWinsOverStaleUploadedAndFinalizedFlags` проверяют приоритет
  принятого удаления над поздним ответом. `RecordingDeletionOperation.applying`
  запрещает обратный переход accepted/verified, проверяет время и receipt цели.
- `testUnavailableAccessBlocksContentButDoesNotProveDeletion`,
  `testLocalPurgeUnknownSyncStateDoesNotDeleteRecordingBuffers` и
  `testLocalPurgeReconciledMeetingMismatchDoesNotDeleteRecordingBuffers`
  различают блокировку доступа и основание физического удаления.
- `testPersistedIntentBlocksEveryLocalActionAndSurvivesRestart`,
  `testUserDeletionSaveFailureLeavesFilesAndMemoryUntouchedBeforeAnyNetwork`,
  `testLocalPurgeAckFailureDoesNotFinalizeLocalQueueState` и
  `testLostAcknowledgementRestartsAndRetriesExpiredTaskWithoutAnotherDelete`
  проверяют долговечность, порядок сохранения/очистки/подтверждения и повтор.
- `test_origin_lock_orders_both_interleavings[create/cancel]` и
  `test_concurrent_cancel_and_create_never_leave_live_recording` исполняют
  серверную конкуренцию на PostgreSQL; проверки sync/access скрывают удалённую
  встречу и запрещают загрузку. Повторный delete возвращает тот же receipt.
- `test_deletion_wins_pending_egress_and_preserves_completed_observability_delivery`
  исполняет удаление и проверяет сохранённые наблюдения/отзыв управляемых
  производных. Temporal здесь заменён тестовым адаптером; это не live-проверка
  Temporal или Langfuse.
- Chromium запускает настоящий cabinet.js и DOM с подставленными HTTP-ответами:
  удалённая серверная строка не возрождает local alias, поздняя принятая HTML-строка
  убирается, pending отличим, выбор/счётчики/фокус сохраняют смысл. Это один script,
  не семь отдельных тестов и не полная проверка настоящего backend через GUI.

Эта совокупность достаточна для профильной проверки кода и тематических тестов
T001. Она не превращает исторические частичные S01–S51 в 51 новый сквозной PASS,
не повторяет установленную приёмку GRAF Dev, не измеряет p95 и не выпускает продукт.

## Точные исходные критерии #6876 и возможность закрытия

Issue прочитана live 22.10; body не изменялось. Она всё ещё OPEN.
PR #6911 действительно MERGED, head
`2279f8137688cde88e8fc0906feef44a81bf55cf`, merge
`977310d1a7c32de8a36da0ac13f89b198b388378`, mergedAt 10.09.2026
02:53:47 UTC. Старый комментарий «ожидает слияния» устарел.

| Исходный критерий | Что подтверждено этой проверкой / что требуется отдельно |
|---|---|
| «Результат T001 реализован согласно spec.md, plan.md и contracts/lifecycle.md» | Качество двух checklist и соответствие FR/SC задачам независимо перепроверены заново; датированная новая сверка в analysis.md перечитана. CRITICAL 0/HIGH 0 относится к новой проверке, история сохранена. |
| «Применимые сценарии S01–S51 … проверены, ошибки и незавершённые проверки указаны честно» | Все 51 сценарий перечитаны как требования, сопоставление и его ограничения изучены. Для T001 это проверка полноты/согласованности, а не новое исполнение 51 runtime-сценария. `scenario-evidence.md` сохраняет частичные/контрактные границы S10/S11/S14/S17/S21/S22/S26/S28/S29/S31/S36/S42/S44/S46 и установленной приёмки. Нельзя стирать их или объявлять все 51 сквозно пройденными. |
| «Подтверждённое удаление не отменяется устаревшим ответом; неизвестное состояние не выдаётся за удаление» | Требование полно и однозначно: FR-002/003/014, S03/S05/S28/S29; `RecordingDeletionOperation.applying` хранит монотонный accepted/verified и требует receipt, `lifecycleBlocksContent` блокирует неизвестный доступ без выдачи purge authority. Текущие журналы 160 Swift и 33 PostgreSQL проверок независимо прочитаны и сопоставлены с ключевыми утверждениями кода; доказательства перечислены выше. Сам reviewer их не запускал. |
| «Проверить соответствующий код и результаты focused tests из quickstart.md» | Прочитаны все шесть свежих журналов: все пять PostgreSQL-файлов quickstart плюс origin cancellation, четыре Swift baseline класса плюс lifecycle acceptance, один Chromium script. 160 Swift/33 PostgreSQL PASS без пересечений; механическая ошибка имени Swift-класса в quickstart исправлена и независимо проверена. Локальные результаты не являются обязательным CI. |
| «Сверить tasks.md, PR и точный исходный SHA; обязательные governance/release gates не заменены локальной проверкой» | T001 уже [X] в tasks и связан с #6876/#6911. Сохранённый текущий общий validator #6911 сообщает `governance-fast: missing/expired artifact`. Новый PR оформляет повторно выполненную проверку T001 на нынешнем источнике; обязательные governance-fast/macos-pr/pr-metadata точного нового SHA и основы, слияние и live closeout ещё ожидаются. Они не восстанавливают утраченную квитанцию исполнения старого продуктового SHA #6911. Release-full нужен там, где closeout заявляет выпуск; новый документальный обзор не выпускает продукт. |
| «Добавить понятный русский комментарий с доказательствами и границами» | Делает основной исполнитель после содержательной и live-проверки; reviewer GitHub не менял и issue не закрывал. У всех остальных 22 issues собственные критерии; этот отчёт их не принимает. |

**Вывод о закрытии:** содержательные критерии T001 подтверждены свежей
независимой сверкой требований/анализа и нынешними профильными проверками кода.
Допускается новый PR для документирования повторно выполненной T001 с
`Fixes #6876`, при обязательной проверке governance-fast/macos-pr/pr-metadata
его точного SHA и актуальной основы до слияния. Окончательное закрытие — после
слияния и успешного live closeout с подробным русским комментарием. Потерянный
артефакт #6911 честно остаётся историческим ограничением, а не заявляется
восстановленным новым CI. Этот вывод не принимает остальные 22 issues F262,
не заменяет их отдельные критерии и не подтверждает выпуск продукта.

## Замечания, не изменяющие требований

- Низкий приоритет: исторические шапки `spec.md`/`quickstart.md` говорят о
  готовящемся PR, `plan.md` — о проекте без реализации; нынешний #6911 слит.
  Датированные записи реализации сохраняют историю; новая сверка в
  `analysis.md` явно отделяет её от текущего состояния. Нельзя писать,
  что реализации/установленной приёмки никогда не было.
- Низкий приоритет: `plan.md` и `quickstart.md` исторически называют только
  governance-fast/metadata; текущая политика требует три проверки
  governance-fast/macos-pr/pr-metadata на точном SHA и основе. Действует
  нынешняя политика, старый текст не является исключением из неё.
- Не обнаружено нового дефекта требований, требующего изменения spec/plan,
  ослабления критериев или нового согласования с владельцем. Это не аудит
  всей современной реализации и не утверждение об отсутствии дефектов кода.

## Прочитанные источники и SHA-256

Обязательные документы прочитаны полностью, длинные — последовательными
частями. Хеши сняты после чтения; они подтверждают содержимое источника, а не
готовность продукта. Текущие `analysis.md`, `spec.md` и `quickstart.md` после
документальных правок основного исполнителя перечитаны полностью; их нынешние
хеши указаны ниже. Остальные источники перепроверены на неизменность.

```text
24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958  AGENTS.md
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8  .specify/memory/constitution.md
0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2  docs/prd-voice-layer-final.md
25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16  docs/current-product-status.md
2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb  docs/agent-guidance/README.md
5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411  docs/agent-guidance/document-reading.md
afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e  docs/agent-guidance/spec-kit-flow.md
9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5  docs/agent-guidance/product-gates.md
ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f  docs/agent-guidance/release-and-validation.md
06450200cabdef48000af51241564e9ee9e8d36b50c71e06a88f8c50b7365466  docs/agent-guidance/tracker-policy.md
7cd5c1cde2bb51e3842cae9e3717b094fea9f6fbb33fb1a408e6d243f9d68bf3  docs/agent-guidance/github-issue-canon.md
f64766bd86981a52c7d18019cd418a8d227756de02e234af1e1d28cf762e063d  specs/262-recording-deletion-lifecycle/spec.md
25d14d4fd41cbc9a7364805722a92173f8e3b93debdd9f30efbfae21e3542cb3  specs/262-recording-deletion-lifecycle/plan.md
f4ed5a207676dfa3fe7f2803c6fbcd447f2bc5faa49e812ba5617fa4c26175ce  specs/262-recording-deletion-lifecycle/tasks.md
a728d664177055ad0544c3a2f1b72eee209805ce2612472ca4b2795bdedb2bb0  specs/262-recording-deletion-lifecycle/quickstart.md
3c2ead5b0cfbf492d8c95c8a26b59b8dcd6d11accc872a9e997512d0077af4da  specs/262-recording-deletion-lifecycle/analysis.md
696aeff0f6dfe2da78cbd5a702eb5f57a32fd187011a114083b1cc2b9d7a636b  specs/262-recording-deletion-lifecycle/research.md
0d3514d73303dd20c4e991b89ba6778de54a88cee5007a5b1684359f44a2367e  specs/262-recording-deletion-lifecycle/data-model.md
29df91c40b00227e6f682394e4a1f5b0fdc8a426b7c734591a934fab72cb434b  specs/262-recording-deletion-lifecycle/scenarios.md
c486f269e0bba66aea55c71ef659b5a010c7682dc3e64d05dfee042745db4f9f  specs/262-recording-deletion-lifecycle/scenario-evidence.md
033c607ec02a32061b2cc422a948f590096bcf69b862a64f0163d79fb534d8b6  specs/262-recording-deletion-lifecycle/evidence.md
8fa48526ac9bf8b0347fa49ebda24370f236257dda40f2c1f388d8a182df1441  specs/262-recording-deletion-lifecycle/review-findings.md
35a6b395a973ea2ffa3a020b08457075f3d3d103b723b0be8179b3536eccd495  specs/262-recording-deletion-lifecycle/implementation-review.md
62feb7074399520b222f231f3ed56b76de53a7dcb59f845ca28c450729dbe5dc  specs/262-recording-deletion-lifecycle/design-review.md
531303eca5340b6baf8ae83999d04187121ee31018b5b8547de95fded352279a  specs/262-recording-deletion-lifecycle/issues.md
f0652db20a6369046802a78320c44f0fa7da1df506aed106d0790a724abc66ef  specs/262-recording-deletion-lifecycle/contracts/lifecycle.md
```

Точные команды для основного исполнителя, без исполнения reviewer:

```sh
git diff --check
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr 6911
# Профильные запуски выполнены основным исполнителем; проверены шесть журналов.
# Новый PR: три обязательные проверки точного SHA и актуальной основы.
# Перед любым закрытием — proposed comment JSON и существующий validator:
python3 scripts/validate-issue-closeout.py --issue-json /path/to/issue-6876.json \
  --tasks specs/262-recording-deletion-lifecycle/tasks.md \
  --expected-sha <точный-SHA-проверенного-PR> \
  --repo yshishenya/graf --verify-live
```

Reviewer изменил только два принадлежащих проверяющему checklist и этот отчёт.
Продуктовые тесты, сборка, установленное приложение, Git/GitHub, сервер,
пользовательские данные, платежи и выпуск им не изменялись.
