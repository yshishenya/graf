# Независимая проверка кандидата T115: protected local custody

Дата: 2026-10-02. **Вердикт: REQUEST CHANGES — кандидат T115 пока не принят.**
Область — проект протокола, не реализация и не повторная приёмка T114.
Четыре замечания ниже относятся к требованиям literal T115; для их исправления
нужны решения в документации, а не полная приёмка T118 до проектирования.

## Область, процесс и точная версия

Каноническая рабочая копия:
`/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`;
branch `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`.
Кандидат находится в незакоммиченных bytes; один HEAD не идентифицирует проект.

Лично прочитан `code-reviewer/SKILL.md`. Его проверка correctness/security,
ошибок, границ ресурсов и проверяемости применена к проекту и реальным местам
внедрения. Проверочные запуски навыка не выполнялись по явному ограничению
области. Полностью прочитан свежий contract, включая последние уточнения §2/§4;
прочитаны data-model §12, quickstart §12, последние две секции plan и literal
T115/T116/T117/T118. Использованы применимые Constitution I/IV/VI, platform
constraints, FR-012/013/014/022, SC-001/003/005/006/008, PRD local buffer policy,
project guidance и затронутые критерии reviewer-owned checklists.

Режим — ограниченная read-only проверка документации внутри high-risk-feature.
Прочитаны существующие queue/recovery APIs и связанные места AppMain,
AtomicFileStore, writer и package inspector. Код, задачи, отметки, прежние отчёты
не менялись; VM, устройства, сборки, тесты, GitHub, commit/push не запускались.
Единственная запись рецензента — этот новый файл. T114 `[X]` не переоценивался;
T115–T118 остаются `[ ]`.

SHA-256 проверенных bytes; значения повторно совпали перед записью отчёта:

| Файл в `specs/200-windows-desktop-app/` | SHA-256 |
| --- | --- |
| `contracts/windows-protected-local-custody.md` (324 строки) | `27a0ac77a49bed71a3183a83bfaca73d3bf23aa4169788b8d055205785554b76` |
| `data-model.md` | `7fb236e24be17a8f1734925394d83013c831e26ffb1dd36eef6efbf1204b540a` |
| `quickstart.md` | `89f39e1aa6ae9ede8899dd504c2928128a7b2bd1a0134b95b8c1745fe84a1089` |
| `plan.md` | `25957aafcd47eb3955d964bbbb873a94553841510cd322e4a1db0ab63ad90b10` |
| `tasks.md` | `0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19` |

Основные исходники, на которых основаны контрпримеры, SHA-256:

- `apps/windows/RecApp/Upload/DesktopUploadQueueService.cpp`:
  `08ea8aac504d6f31d03cfed53b65ff4caed05522e57871a0a34ab376a4c12e5b`.
- `apps/windows/RecApp/Upload/DesktopUploadQueueService.h`:
  `1e28fc4caef5ba5b5f8417be30bbf93ed30f0422231f14fdde395561becb794d`.
- `apps/windows/RecApp/Upload/DesktopUploadRecoveryScheduler.cpp`:
  `e4fdac0709bf03c7b3f18d2629651ebded4f895d24fd3f026cc8bee066d6bf3c`.
- `apps/windows/RecApp/Upload/DesktopUploadRecoveryScheduler.h`:
  `fd27723045442bf0d0b8ba8359db1da76faa3d4254e695defd61efe6f2886862`.
- `apps/windows/RecApp/AppMain.cpp`:
  `f534c2ef8944120ed535a9a09fbc681b49f391ee6cb68a06fab8d83935391dbd`.

## Блокирующие замечания к проекту

### F1 [P1] Единственный valid generation1 не доказывает первую публикацию metadata

Место: `contracts/windows-protected-local-custody.md:142–145`, рядом с запретом
metadata rollback в строках135–139; `data-model.md:428–430`.

Условие «единственный valid generation1/slot0» проверяет оставшийся индекс,
но не историю объекта. Контрпример: очередь g1/slot0 ещё допускает отправку;
g2/slot1 durable содержит подтверждённый delete intent/запрет отправки. При
следующем запуске `index.1` отсутствует вследствие потери именно этого файла.
Остаются валидные g1/slot0 и его DATA blocks. Это буквально удовлетворяет
указанному исключению, хотя объект уже имел generation2. Выбор g1 отменяет
durable intent. Bootstrap содержит reader mode/queue object, но кандидат не
определяет независимое подтверждение последней queue generation или genuine
first publication. Правило «при generation≥2 blocked» не помогает, когда
единственный surviving index сообщает generation1.

Это не откат всего диска и не требование защиты от вошедшего пользователя.
Достаточно отсутствия одного последнего metadata index; такой отказ входит
в заявленные missing/corruption и no-old-ledger semantics. Существование более
новых orphan blocks может позволить отказ, но сейчас кандидат не требует
использовать это как отрицательное доказательство первой публикации.

Минимальная правка проекта: определить проверяемое отличие genuine first
publication от surviving g1 после потери g2. При отсутствии такого доказательства
singleton metadata не даёт authority/mutations/upload/GC. Можно выбрать более
строгий отказ на singleton после restart либо конкретный durable birth/commit
протокол; одной проверки decoded generation недостаточно. Не требуется новый
сервис или общая anti-rollback инфраструктура.

Будущая регрессия T116: g1 без intent → acknowledged g2 с intent → отсутствие
slot1 → restart. Ожидается recovery-required, сохранение файлов, отсутствие
отправки/отката intent; отдельно проверяется действительно первая публикация.

### F2 [P1] Bootstrap fence не закрывает окно отсутствующего ledger для старого reader

Место: `contracts/windows-protected-local-custody.md:279–286,300–302`.
Реальный старый reader: `Upload/DesktopUploadQueueService.cpp:135–147`.

Кандидат требует сохранить original в `legacy.originals`, поставить sentinel
на старое имя и при прерывании полагается на protected bootstrap fence. Но не
задаёт порядок/атомарный способ, исключающий отсутствие старого имени между
переносом original и публикацией sentinel. Старый клиент bootstrap не читает:
если прежний ledger и `<ledger>.quarantine` отсутствуют, его `load()` успешно
возвращает пустую незаблокированную очередь. `enqueue():375–383` и
`persist():1220–1228` затем могут создать новый v3 по старому имени.

Контрпример: original ledger с accepted ranges/delete operations уже перенесён;
процесс прерван до sentinel; после освобождения AppInstance запускается прежний
клиент. Новый fence существует, но этот клиент его не распознаёт. Original
физически сохранён, однако активный ledger стал пустым/новым, а прежние intents
и ranges перестали участвовать в lifecycle. Требование «updater не разрешает
downgrade» без указанного действующего условия до этой границы не исключает
такой restart старого writer.

Минимальная правка проекта: до утраты старого имени установить durable барьер,
который реально распознаёт прежний reader, либо описать замену, при которой
старое имя никогда не отсутствует и original заранее сохранён и проверен.
Если выбран запрет запуска старой версии, определить его предшествование
переносу, сохранность после crash и область действия. Например, существующий
old-reader `.quarantine` gate — возможная точка решения, не предложение менять
код в этом review. Подтвердить original exact bytes и согласовать такой барьер
с новым recovery; запрет auto-deletion из FR-012 сохраняется.

Будущая регрессия T117: cut после каждого действия над old name, включая
rename до sentinel, и запуск прежнего reader: отказ без создания пустого v3
или отправки legacy. Installed/update доказательство остаётся T118; сейчас
нужен определённый безопасный порядок, а не выполненная installed матрица.

### F3 [P2] Async candidate не определяет acknowledgment существующих bool/void callers

Место: `contracts/windows-protected-local-custody.md:177–185`; entity
`PendingLedgerMutation` в `data-model.md:426`.

Правильно запрещён synchronous UI persist и projection до durable ack. Однако
не определено, чем становятся результаты действующих APIs, какие continuation
ожидают ack и кто сохраняет завершённый flight до этого ack. Это нельзя решить
одной заменой `LedgerWriter` на worker:

- `DesktopUploadQueueService.h:145,151–177,200–205` — synchronous bool APIs;
  `DeletionPlan.saved` в строках260–264 означает уже durable requests.
- `DesktopUploadQueueService.cpp:382–383,389–391,1220–1230` изменяет projection
  до bool persist; false означает failure/quarantine, не pending.
- `DesktopUploadRecoveryScheduler.cpp:51–68` использует эти результаты до
  выбора snapshot и начала network work. `drain():115–137` забирает flight,
  вызывает void `apply`, увеличивает handled и освобождает lease. В
  `apply():167–170` reconcile и terminal mark — отдельные mutations, bool
  results игнорируются. Header32–38 связывает busy с ещё не drained flight.
- `AppMain.cpp:677–692` может стартовать следующий flight после drain;
  строки2206–2218 используют durable deletion plan до network dispatch;
  строки2427–2452 строят reply и снимают in-flight guard после применения ответа.

Контрпример для наивной async адаптации: вернуть true при постановке candidate
в worker — старый caller уже считает intent saved, разрешает эффект либо
освобождает flight до Flush/reopen. Вернуть false как pending — существующий
persist/caller трактует его как failure, а drain всё равно завершает обработку.
Ожидать worker внутри bool — нарушить UI/readiness ограничение. Декларация
«переводятся через границу» пока не выбирает безопасный четвёртый вариант.

Минимальная правка проекта: задать pending/committed/not-committed/ambiguous
completion и привязку к epoch/base generation; перечислить continuations для
prepare, completed-flight drain, enqueue/finalizer handoff и deletion plan/
answer/local purge. Указать, когда допускаются network/effect/reply, кто держит
busy/lease/result, и как обрабатывается cancel после физического commit, но
до owner callback. Связанные truth/status изменения должны иметь определённый
порядок и исход, а не зависеть от двух сразу возвращённых bool. Ни новые классы,
ни новая очередь сверх выбранных bounded32 команд этим замечанием не требуются.

Будущие T116 регрессии: delayed/failing/ambiguous persistence, отмена/смена
аккаунта между commit и callback, completed network flight при pending ledger
ack, delete saved/removed/accepted replies. До ack нет преждевременного эффекта,
успеха или lease release; UI не ждёт IO.

### F4 [P2] Новые authority payloads ещё не имеют однозначного schema/byte codec

Место: `contracts/windows-protected-local-custody.md:54–68,148–155,265–277`;
`data-model.md:423–425`. Literal T115 требует schema/version и explicit encoding.

Envelope16B, block104B, index112B и entries действительно заданы побайтно. Но
для нового logical payload bootstrap/package-state/migration-intent заданы
только смысловые поля/состояния и cap64KiB. Не выбран сам формат records:
ширины/порядок/encoding полей, значения reader mode/phase/stage, структура и
число references, формат owner/deletion/range stamp, схема проверки конфликтов
и отказа на duplicate/unknown/отсутствующие обязательные поля. Существующий
v5 manifest/v3 ledger этого не определяет — это новые служебные entities.

Контрпример совместимости: schema1 и перечисленные intent fields можно
поместить как bounded UTF-8 JSON либо как LE поля разных unsigned widths.
Обе записи могут иметь корректные описанные DPAPI envelope/index/block и
одинаковые смысловые значения, но после restart reader не имеет нормативного
способа разобрать payload. Сам DPAPI/role/hash не выбирает формат и не доказывает
корректность sealed state или migration stage. Общий cap решает размер, не схему.

Минимальная правка проекта: компактно выбрать один versioned payload codec
для трёх новых records, точные типы/enum/required поля и bounded references;
связать проверку store/object/role/generation/hash и отказ на конфликт с
authority правилами. Допустим строгий описанный JSON codec, если явно отделён
от LE storage headers. Не требуется менять logical v5/v3, писать serializers
сейчас или до design выполнять T118.

## Что рассмотрено и не является отдельным blocker

- Учтены **свежие**, а не прежние bytes: fixed confined bootstrap/queue/intent/
  package role locations, отказ от JSON redirects, исключение root `.custody-v1`
  из package scan; initial slot0/parity; сравнение decoded index bytes, не
  nondeterministic DPAPI ciphertext. F1 касается оставшейся истории singleton,
  не отменяет эти уточнения.
- Wire arithmetic headers104/112 и entry16 согласована; max count262144,
  length64GiB, explicit ZERO, exact short tail, раздельные preallocation
  block/index bounds и context entropy имеют конкретные правила. Это оценка
  проекта storage codec, не подтверждение реализации этих правил.
- Immutable finalized artifacts плюс exact sealed object/generation/length/SHA
  отличают изменяемый MF output до seal от upload/playback authority после seal.
  Два slots не объявлены неограниченной историей; pin/Clone cache и process
  budget заданы, GC сохраняет оба index refs/pins/candidate/package-state.
  Отдельного воспроизведённого design counterexample против этой схемы не
  установлено; F1 metadata history остаётся исключением к положительной оценке.
- Canonical fallback — лишь degraded trusted prefix; invalid authority metadata
  не должно откатывать очередь. Native key/context refusal не выдан за actual
  profile loss; per-recording cryptographic erasure не обещана.
- §8 теперь требует отдельного явного owner cleanup confirmation либо уже
  действующего confirmed delete/purge intent. Migration сама не даёт deletion
  right; original сохраняется и encrypted inventory claim запрещён до cleanup.
  Это исправление принято по качеству требования, не по runtime доказательству.
- quickstart§12 правильно ссылается на solution/CTest§2 и MSIX§8. Plan/data-model/
  quickstart сохраняют статус draft/T115 open и разделение T116–T118.
- Logical WAV RIFF/u32 и AAC параметры не заменяются research defaults.
  Сверены существующие manifest cap4096, queue cap4MiB, AAC48kHz/mono/96kbps
  (`V5LocalRecordingWriter.cpp:77–82`), playback duration tolerance100ms
  (`LocalRecordingPackage.cpp:78–86`). Физические quotas не приравнены к64GiB.
- Нет основания требовать actual profile loss,100cycles, installed Home/Pro/N,
  physical60min/AEC/SC003 acceptance до принятия проекта. Их условия оставлены
  открытыми для T116–T118/отдельных hardware gates. SC-003 и5s drain не ослаблены.

## Затронутые checklist criteria и оставшаяся проверка

Существующие `[X]` — историческая достаточность требований, не новая приёмка
этого candidate и не Windows runtime PASS. Отметки в чужих файлах не менялись.

| Reviewer-owned checklist | Требуемый вывод для этого среза |
| --- | --- |
| security CHK012/013 | Уточнить F1/F4: genuine first publication, отсутствие отката metadata/delete intent, строгий codec новых records и encrypted quarantine/temp accounting. F3: durable ack не равен queued worker. |
| security CHK009/010/015 | Уточнить F3: saved/accepted/removed/purge truth после надлежащего durable/OS/server proof; no web/decrypt acknowledgment как новое право. Owner-only cleanup уточнение FR012 сохранено. |
| security CHK016 | Уточнить F2 и F4: old reader gate до переноса имени, recovery по однозначным records, сохранность original/intent/ranges при всех migration cuts; owner/expiry/removal trigger есть, retirement ещё T117. |
| security CHK021; requirements CHK018 | Standard-user/offline/native DPAPI и Home/Pro/N readiness ограничения в проекте сохранены; installed/runtime доказательство отложено правильно, не выдаётся этим review. |
| audio-capture CHK002/008/013/015/020/024 | Storage readiness, no callback/UI IO, trusted prefix vs normal, immutable sealed WAV/AAC, budgets и EOS/finalizer lease должны включить F3 handoff. Clock/AEC и 5s не меняются; отдельно требуется реализация и измерение. |
| requirements CHK005/009/012/016/019/021 | Перед положительным повторным review устранить F1–F4 и согласовать новые entities/limits/ошибки со связанными docs; текущий analyze после изменений ещё обязателен. |
| ux CHK004/009/019/021 | Дать однозначное отображение pending durability/recovery-required/migration cleanup pending без ложных saved/uploaded/removed; quit/update admission держит jobs до фактического окончания. Это требования к существующей native поверхности, не новая Windows UI. |

При повторной сверке inherited limits явно привязать reserve к PRD policy:
минимум свободного места **10GB или10% capacity, меньшее из двух**
(`docs/prd-voice-layer-final.md:745–750`), включая физический peak группы, orphan/
pins/legacy/temp; 7days/5GB/80%/95% не заменяют этот порог. В §5 слово reserve
уже есть, но численная ссылка и capture admission consequence заслуживают
явной проверки checklist. Это не предложение нового порога. Аналогично закрыть
реестр всех существующих content-bearing temporary/quarantine путей: WAV/AAC
temps writer298–300, AtomicFileStore `.tmp-*`, ledger `.quarantine`, recovery,
short marker и migration originals; каждому соответствует protected role/
ciphertext temporary либо явно сохраняемый legacy exception без encrypted claim.

## Итог и граница разрешения

**REQUEST CHANGES для данного T115 candidate.** F1/F2 могут отменить действующую
authority/intent при одиночном file-loss либо migration interruption; F3/F4
оставляют неназначенные обязательные API/payload переходы до T116. Минимальное
продолжение — уточнить эти четыре решения в проекте, затем независимая повторная
проверка затронутых criteria и текущий analyze перед taskstoissues/implementation.

Это не отмена APPROVED исследования T114, не требование полной T118 раньше
design, не разрешение product implementation/migration и не задача рецензенту
поставить отметки. T115 и последующие задачи остаются открытыми; выпуска/общей
готовности F200 отчёт не подтверждает.

## Повторная независимая проверка T115 — 2026-10-02

**Актуальный вердикт: REQUEST CHANGES.** Исходные F1–F4 проработаны на уровне
проекта; остаются два конкретных противоречия миграционного протокола F5/F6.
Это не требование реализации T116/T117 или полной приёмки T118 до T115.
Предыдущий текст и прежние SHA сохранены целиком; дополнение начинается после
первоначальных267 строк. SHA-256 этого неизменённого префикса:
`8ff1d0a9ab1ba9d86fa68b9070a34f9b81b0181dd48593a5a30e1c1b2249ac01`.

### Точная версия и границы повторной проверки

Canonical HEAD остаётся `99b00a579c24b50e320465b69d9a296038bc544d`.
Лично перечитан `code-reviewer/SKILL.md`; полностью прочитаны свежие bytes
всех пяти документов ниже и первоначальный собственный отчёт. Проверены
актуальные затронутые security/audio-capture/requirements/ux criteria,
реальный старый `DesktopUploadQueueService::load`, queue/recovery APIs и
места вызова из AppMain. Использованы те же применимые constitution/spec/PRD
ограничения, без нового требования к продукту. Повторная проверка относится
к документации high-risk feature: проверки схем и последовательностей
проведены чтением, не запуском. VM/устройства/сборки/тесты/GitHub не запускались.
Единственная запись — это дополнение; чужие изменения сохранены.

| Документ в `specs/200-windows-desktop-app/` | Свежий SHA-256 |
| --- | --- |
| `contracts/windows-protected-local-custody.md` (496 строк) | `ad62f9046c2e9017955559d504ab7cdd51d75e2dc668200913a6b4b0837204f3` |
| `data-model.md` | `486f031e819531e9168ec24a9e56d1933efda29ced85c60d81de0a877e9d9405` |
| `quickstart.md` | `009af8e065cd9b30838dac74ef7f64049ce8be5b57a43f42a3f7b788288e6f93` |
| `plan.md` | `f943598d8065e58dff7452348e4b4c0848d7d38eb5579911fafd1de749f65278` |
| `tasks.md` | `0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19` |

`tasks.md` совпадает с первоначально проверенной версией: literal T115 остаётся
открытым, T114 принят, T116–T118 не разрешены. HEAD без этих SHA не фиксирует
незакоммиченный кандидат. Повторное хеширование перед записью совпало.

### Решение по первоначальным замечаниям

| Замечание | Повторная проверка свежего проекта |
| --- | --- |
| F1: surviving g1 ошибочно принимался за first birth | Закрыто для design scope: contract142–151 требует независимо защищённую пару с одинаковыми decoded g1 bytes до первого ACK; любой singleton после restart blocked. Потерянный g2 теперь не разрешает старый ledger. Это сознательный безопасный отказ, не доказательство восстановления interrupted birth. |
| F2: rename до sentinel открывал old-reader empty window | Первоначальное окно закрыто: contract320–333 требует CREATE_NEW/flush `.quarantine` до rename. Реальный `DesktopUploadQueueService.cpp:135–147` при missing ledger и этом имени возвращает false, а не новую пустую очередь. Bootstrap не выдаётся за old-reader barrier. Остаточный новый вопрос долгоживущей проверки barrier — F6 ниже. |
| F3: bool/void не определяли async ACK и владение | Закрыто как проект API: contract187–222 задаёт value-copy candidate, typed outcomes, ID/generation/epoch, retained result/lease до adoption, storage adoption даже при stale UI и запрет effects до ACK. Таблица212–217 покрывает prepare/drain, finalizer, deletion, purge/short и account/shutdown. Это обязательная будущая замена существующих callers, не утверждение, что нынешний синхронный код уже её реализует. |
| F4: новые authority payloads не имели строгого codec | Первоначальный пробел закрыт: contract364–452 определяет точные UTF-8 schemas, поля/типы/null/enums, decoded duplicate keys, unsigned numeric bounds, роли/ID/generation/refs/stages и cleanup authorization. Неопределённости межобъектного birth и отдельного исторического barrier выявлены отдельно как F5/F6, а не скрыты положительной оценкой codec. |

Отдельно сверены finalizer enqueue/discard (`AppMain.cpp:1023–1060`), ручные
retry/owner assignment (`832–841,873–879`), scheduler prepare/drain/apply,
deletion plan/reply и purge acknowledgment (`2206–2218,2360–2395,2427–2452`).
Правило contract190 охватывает **все** persistence-facing bool/void, включая
не поимённо перечисленные helper calls; table212–217 назначает продолжения и
владение результатов. При реализации нельзя оставить прежние ранние `handled`,
`saved`, освобождение flight/lease или HTTP ack до committed/adoption.
Текущий source не принят за доказательство будущего async поведения.

### F5 [P1] Первый migration fence требует intent/queue, которые по порядку ещё не созданы

Место: contract303–305,385–392; связанные425–426 и127–129.

Контрпример без crash: имеется исправный legacy ledger, но protected bootstrap,
intent и queue ещё не родились. Взят exclusive recovery lease, writers/flight
остановлены. Порядок303–305 требует сначала protected bootstrap migration fence,
**затем** durable intent. Однако migrating bootstrap по385 уже требует matching
durable intent, а queue reference по391 — fixed queue ID и два valid index slots.
До prepared copy такой protected queue не существует. Prepared destination
triple по425 весь null; пустую queue в непустом legacy root создавать нельзя343.
Следовательно, первый fence не может пройти собственную semantic validation
и validated reopen/ACK129. Если worker для старта игнорирует эти проверки, он
сам выбирает не описанное контрактом исключение из authority codec.

Это не требование protected queue для **чтения legacy stamp**:410–416 правильно
разрешает legacy anchor с null object/generation и whole logical source hash.
Цикл возникает именно от prerequisites bootstrap при первоначальном создании
intent/queue, а не от самой проверки original. Background recovery имеет ту же
проблему при interrupted birth: обещанное318 reconciliation не различает
допустимое промежуточное состояние от отсутствующих обязательных cross-refs.

Минимальное решение до T116/T117: явно назначить порядок создания intent/fence/
queue и stage-aware правила. Отделить структурно проверяемый **закрывающий** fence
от разрешающей обычные effects authority; определить, когда reserved queue ID
ещё не обязан иметь index pair, когда matching intent обязателен и какие пары
bootstrap/intent/destination допустимы после interruption. Либо изменить порядок
так, чтобы все требуемые ссылки действительно существовали до проверки fence.
При любом варианте сохранить no-effects, запрет empty legacy queue/downgrade и
проверку whole source stamp перед switch. Новая служба/третий индекс не нужны.

Будущая проверка T117: первое создание в verified legacy root и cuts между
intent birth, fence birth, destination birth и switch. Проект должен заранее
различать допустимое продолжение/явный retained recovery-required и corruption;
не требуется автоматически достраивать singleton metadata вопреки142–151.

### F6 [P2] Исторический barrier не имеет согласованного standalone validator и restart GC roots

Место: contract330–333,375–377,430–438; GC237–240.

Конкретная последовательность для нового intent: g1 prepared содержит
`barrier=null`, block position0/version1; g2 prepared ссылается на этот первый
immutable envelope, после чего он записан в `.quarantine`. g3 copied_verified
заменяет index slot0, g4 switched заменяет slot1. После restart оба current
индекса корректны, но ни один больше не представляет payload generation1 или
ссылку на version1. Текущий barrier ref при этом всё ещё указывает на первый
prepared envelope, что само по себе правильно и не требует третьего индекса.

Native context с store/object/role/position/version, точный размер/hash envelope
и authenticated payload schema/transaction позволяют проверить **точный
самостоятельный старый блок**. Но общее правило375 требует, чтобы generation
payload всегда совпадала с pinned own index. Для старого g1 нет соответствующего
индекса на диске; при применении этого правила к `.quarantine` нормальная
последовательность g1→g4 отказывается после restart. Применить только текущие
g3/g4 также нельзя: старый payload им не соответствует. Не определено отдельное
исключение/правило historical snapshot validation, которое согласовало бы эти
два требования, а не просто пропускало generation check.

Второй аспект того же lifetime:332 обещает pins до terminal migration, но237–240
перечисляет current index refs, pinned snapshots, dirty candidate и package-state,
не persistent transitive barrier refs intent. После restart прежних in-memory
pins нет. Нужно определить восстановление этих keep-roots **до разрешения GC**.
Иначе общий сборщик может счесть первый original intent block orphan. Сохранённая
`.quarantine` — отдельная ciphertext copy; её существование не доказывает потерю
самих bytes при GC блока, но проект пока не назначает эту copy достаточным
standalone источником вместо missing historical index/block pin.

Минимальное решение: описать прямую проверку immutable prepared barrier вне
обычного mutable-object index opener: exact ref/hash/length; native context и
header position/version/role/IDs; authenticated historical generation и допустимое
отношение к текущему transaction; schema/stage prepared и признаки именно birth
snapshot. Назначить источник retained bytes — original block либо проверенный
barrier envelope — и persistent transitive roots из intent/barrier, включая
нужные ссылки обоих metadata slots, восстанавливаемые до GC. Указать момент
освобождения исторического pin и отдельную сохранность fail-closed tombstones333.
Не требуется сохранять все прежние индексы, бесконечные версии или вводить сервис.

Будущая проверка T117: подготовить barrier, выполнить достаточное число commits
для ухода birth generation из обоих slots, restart → validation → bounded GC
→ тот же transaction recovery. Подмена ref/context/transaction/generation или
несовпадение envelope должны отказывать; исправный historical barrier — проходить
назначенный standalone путь без ослабления current metadata authority.

### Затронутые reviewer-owned criteria: оценка без изменения отметок

| Checklist / критерии | Конкретное evidence и оставшаяся граница |
| --- | --- |
| security CHK012/021 | Fixed confined roles и ACL до write (§2), размер до allocation (§3), native user scope без elevation/service; callback не делает IO. Достаточно определено для этого design scope, runtime acceptance не заявляется. |
| security CHK009/010/015 | Typed pending/ACK и current-context replies (§5), intent→quiesce→actual absence→ACK (§7), cleanup authorization440–451; replies/DPAPI/key loss не дают полномочий или cryptographic-erasure claims. Достаточно на уровне проекта. |
| security CHK013/016 | Два metadata birth slots и no rollback142–151, `.quarantine`320–333, explicit original preservation/old-reader retirement295–301. Migration recovery пока **не принято** из-за F5/F6; прежние checklist отметки не означают одобрение нового кандидата. |
| audio-capture CHK002/008/013/015/016/020/024 | Background readiness185–187; no callback IO и прежний5s drain; live canonical/sealed artifacts155–178; MF adapter §6; trusted prefix не normal; ticket удерживает finalizer214. SC-003/codec/N/resource gates остаются прежними и требуют будущей приёмки, не нового опыта T114. |
| requirements CHK009/012/018/020 | Explicit encoding/bounds §3, process budget §5, reserve=min(10GB,10%capacity)226–231, прежние logical v5/v3/v2/hash/ranges/UUID, supported editions/metadata-only evidence. Нет противоречия в проверенном уточнении. |
| requirements CHK005/019/021 | Normal/degraded/blocked и API ownership описаны, но допустимый migration birth и historical barrier restart недоопределены: F5/F6 блокируют принятие нового протокола. |
| ux CHK004/009/019/021 | pending/recovery-required не выдаётся за saved/accepted219–222; lease живёт после UI close, orphan/stale effects запрещены. Для migration relaunch корректный переход пока требует F5/F6; видимое поведение установленного UI здесь не проверялось. |

Закрытый temp registry454–466 включает canonical/WAV/AAC/manifest/recovery/queue,
atomic ciphertext temporary, sentinel/quarantine и явно незащищённые существующие
legacy originals/temps без права новой plaintext copy. Numeric reserve и peak
учитывают ciphertext, обе slots, pinned/orphan/candidate/legacy bytes226–231;
64GiB/64MiB исследовательского стенда не стали quota/SLA. Эти уточнения принимаются
в narrow design scope, не заменяют полный T116 producer inventory и T118 tests.

**Итог: REQUEST CHANGES до согласования F5/F6 в документации.** T114 не открыт
повторно; T115 остаётся открытым. После устранения этих двух противоречий нужны
повторный независимый review затронутых criteria и текущий analyze по literal
T115 перед taskstoissues/реализацией. Actual profile loss, installed standard-user
matrix, power loss,100 cycles и продуктовая SC-003 приёмка остаются T118, а не
новыми предварительными требованиями к этому проекту. Задачи/checklist отметки,
чужие документы и code не изменены; implementation/migration не разрешены.

## Отдельная повторная проверка исправлений F5/F6 — 2026-10-02

**Актуальный вердикт: APPROVED — только замороженный кандидат T115 в области
проектирования protected custody.** F5/F6 закрыты в этом design scope; новых
блокирующих замечаний к проверенным изменениям нет. Это заключение заменяет
прежний REQUEST CHANGES для свежих bytes ниже, но не удаляет историю замечаний.
Не означает принятия реализации, T118, установленного приложения или выпуска.

### Зафиксированные bytes и проведённая проверка

Canonical: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`;
HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, активная Feature200/high-risk
по `.specify/feature.json`. Полностью прочитаны четыре свежих candidate docs,
перечитаны собственные F5/F6; `tasks.md` проверен по SHA и literal T115–T118,
без повторной оценки принятого T114. SHA совпали с frozen manifest запроса и
повторно перед записью дополнения:

| Файл в `specs/200-windows-desktop-app/` | SHA-256 |
| --- | --- |
| `contracts/windows-protected-local-custody.md` (577 строк) | `48704f413e132f2b643206649a6422f6e6f6ea118cc63c86d5b675e9d4be9d54` |
| `data-model.md` (450 строк) | `c35201de8245e081bd1e0464cf2e6a1e6762a5d8362126892b17d139e34a58bf` |
| `quickstart.md` (425 строк) | `ddd1c7fbb01546a50f184872555cc2b1562deca337a5d3114b6c614005388208` |
| `plan.md` (941 строк) | `2fae246c22801ef49bff29f57873ee5e1d894b7fba1899c6b20a5b7333d74bea` |
| `tasks.md` (без изменения) | `0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19` |

Лично заново прочитан `code-reviewer/SKILL.md`. Проверены correctness/security,
error handling, ownership, границы ресурсов и проверяемость протокола чтением.
Процесс — ограниченная проверка документации внутри high-risk-feature, не новая
реализация. Применены актуальные AGENTS/guidance, FR-012/013/014/022,
SC-003/005/006/008, Constitution IV/VI и прежняя PRD local buffer policy.
Навык не вызвал проверочных запусков: они явно исключены областью запроса.

Сверены актуальные затронутые критерии четырёх reviewer-owned checklists.
Повторно прочитан actual old queue load135–173; SHA всех пяти ранее проверенных
queue/scheduler/AppMain source files совпали с первоначальным отчётом. Это
подтверждение неизменности мест внедрения, не product proof async API.
Другие отчёты, code/tasks/checklist отметки, VM/devices/builds/tests/GitHub/
commit не менялись и не запускались. Единственная запись — это дополнение.

Первые429 строк отчёта сохранены. SHA-256 старого префикса перед дополнением:
`e969d4d20f56fe84a290c12d9f19cb8b6549571c2a75a18098714e1607008583`.

### F5 закрыто: достижимый birth и отдельная closing authority

Contract309–325 задаёт обязательный порядок: exclusive lease/quiesce/закрытый
admission и source stamp → prepared intent pair → prepared barrier ref →
closing bootstrap → destination → switch. Reserved fixed queue ID не означает
создание пустого logical ledger. Исключение430–438 разрешает отсутствие готовой
queue только initial migrating/queue/prepared; для copied_verified нужны exact
copy и две valid slots, для protected — current validated queue pair. Package
migration требует уже protected queue и свой fixed package intent до fence.
Цикла «готовая queue нужна прежде copy» больше нет. Legacy anchor455–462
по-прежнему читается migration worker без выдуманной protected authority.

Bootstrap417–424 теперь содержит точные subject/directory/transaction поля:
queue → root intent, package → проверенный directory/fixed package intent;
protected → три null. Эти поля не позволяют JSON redirects вне locations §2.
Структурно валидный closing fence **запрещает** эффекты, а не допускает upload.

Таблица327–343 различает reserved IDs без envelopes, valid prepared intent до
fence, partial/singleton birth, provisional destination, copied_verified,
actual switch до receipt и reconciliation. Singleton metadata остаётся retained
recovery-required, не автоматически достраивается: это согласовано с142–151,
а не новый rollback/empty-queue путь. Продолжение использует те же transaction/
IDs и снова проверяет source/owner/stamp; чужое/несогласованное состояние blocked.

Отдельно проверен cut334: protected bootstrap либо sealed package-state уже
published, intent ещё copied_verified. Recovery проверяет exact destination,
source/original и old-reader barrier, пишет switched ACK, не открывает effects
до reconciliation и не возвращается к legacy. Для package именно sealed state
есть authority switch; последующее снятие root fence не второй выбор reader.
Для ledger actual switch — protected bootstrap; receipt не заменяет его.

### F6 закрыто: standalone birth block и persistent GC roots

Contract409–413 отделяет current mutable record validator от historical пути.
Barrier483–492 содержит explicit generation, exact block version/size/cipher
hash; queue quarantine и package manifest sentinel используют такой же direct
ref. Historical generation=1, но block version лишь >0 и exact по ref, **не**
приравнивается к generation: orphan collision не позволяет overwrite/reset.

Validator494–506 проверяет bounded exact envelope/hash, native context/header,
strict authenticated payload, own generation по direct ref=1 вместо current
g3/g4 index. Проверяются prepared/barrier-null/authorization-null/destination-
triple-null и matching transaction/subject/directory/ledger anchor/source stamps/
destination IDs. Birth payload≤64KiB целиком в одном block. Старый индекс не
требуется, но current mutable metadata сохраняет правило двух valid slots;
historical validator не даёт queue/package reader authority.

Retained-source правила508–519 разрешают exact immutable block либо verified
quarantine/manifest sentinel. При двух copies требуется совпадение bytes/hash;
malformed/conflicting copy не обходится выбором «хорошей». До old-name barrier
immutable block обязателен. После его создания проверенный tombstone может
быть самостоятельным источником; третьего индекса/сервиса нет.

GC239–246/514–519 теперь явно восстанавливает transitive keep-roots обоих valid
metadata slots **до** первого GC; старый in-memory pin не считается persistent
root. Пока roots не validated — GC scope закрыт. Historical pin удерживается
до durable complete и actual job exit, затем memory pin освобождается, но
persistent ref/tombstone сохраняются. Root ledger gate/sentinel остаются для
old-reader refusal; whole-scope deletion требует отдельного разрешения.
Прежний контрпример g1→g2→g3/g4→restart больше не требует отсутствующий индекс
и не позволяет счесть исторический barrier обычным неподтверждённым orphan.

### Проверка связанных уточнений без расширения задачи

Mutable queue434–437/471–479: после switch migration destination triple —
authenticated historical copy receipt, не frozen reader snapshot. Новые owner/
range/delete generations читаются из current queue pair; вечное сохранение g1
queue index и rollback к copied ledger не требуются. До switch остаются exact
destination validation и source stamp; после switch cleanup требует fresh queue/
owner/receipt527–533. Исторические GC destination/source refs читаются с этим
stage-specific правилом, не как приказ удерживать все queue поколения навсегда.

Old-reader порядок354–367 сохранил durable `.quarantine` **до** rename и sentinel
до switch. Реальный old load при missing ledger/существующей quarantine отвечает
false. Originals не удаляются автоматически379–389; без отдельной authorization
нет full encrypted-inventory claim. Legacy reader301–307 имеет owner T117,
expiry/removal trigger и запрет regular fallback; исправления этого не ослабили.

Data-model §12 согласует closing fence/historical validator/roots и mutable copy
receipt. Quickstart §12 добавляет first inter-object cuts и historical barrier/
restart GC regressions. Plan911–941 сохраняет статус кандидатной документации,
review/analyze/issue gates и открытые clock/product acceptance области.
Exact layouts/bounds §3, budget/quota/reserve §5, typed ACK/leases §5,
sealed refs/live recovery §4/8.1 и закрытый temp registry §8.2 не регрессировали.

### Затронутые reviewer-owned criteria — narrow PASS, без записи отметок

| Checklist / критерии | Прочитанное evidence / вывод о качестве требований |
| --- | --- |
| security CHK009/010/015 | Typed pending/ACK190–222; intent→quiesce→actual absence→ACK283–290; authorization521–533. Bootstrap/barrier/receipt не дают account/delete authority и не подменяют server truth. PASS. |
| security CHK012/013/016/021 | Confined handles/ACL38–71, bounds80–118, two-slot/no rollback127–153; birth/interruption309–343, old quarantine354–367, roots239–246/494–519; no elevation/service и retirement301–307. Новые F5/F6 препятствия для migration recovery устранены. PASS. |
| audio-capture CHK002/008/013/015/016/020/024 | Closing fence не открывает capture; background validation185–187, preserved dispatcher5s180–183, trusted prefix/sealed artifacts155–165, MF no-temp259–272, retained finalizer ACK214. SC-003/codec/N/Stop не ослаблены. PASS требований; не runtime acceptance. |
| requirements CHK005/009/012/018/019/020/021 | Exact wire/context/limits §§2–3, stage/subject/authority/roots §§8–8.1; data-model §12, quickstart §12, plan/T115–118. Explicit recovery-required и receipt cut, прежние logical identity/ranges, reserve=min(10GB,10%capacity), editions и metadata-only evidence. PASS. |
| ux CHK004/009/019/021 | Pending/ambiguous не saved219–222; interruption327–343 имеет no-effects/recovery-required и определённое продолжение; shutdown ownership217/295–297, originals/unprotected-leftover379–389/427–429. Migration relaunch больше не требует недостижимых prerequisites. PASS качества требований, не установленного UI. |

Итог выбранного затронутого набора: **25 критериев достаточны, 0 неподтверждённых
по качеству требований в этой области**. Это не новая полная проверка всех
112 пунктов Feature200, не приёмка реализации и не изменение старых отметок.
Изменения F5/F6 особенно закрывают security013/016, requirements005/019/021 и
ux019/021; остальные перечисленные критерии проверены на отсутствие регрессии.

### Итог и следующие обязательные ворота

**APPROVED для замороженного T115 design candidate с SHA выше.** F1–F4 сохраняют
предыдущее scoped closure; F5/F6 также закрыты в документации. Дальнейших
исправлений кандидата по этой независимой проверке не требуется. Текущий
read-only analyze и taskstoissues по literal T115 остаются отдельными воротами;
этот review их не исполняет и не отмечает T115/checkboxes выполненными.

T116/T117 должны реализовать и проверить именно этот протокол: inter-object
cuts включая switch-before-receipt; historical validator с negative context/
generation/stamp/cipher cases; restart before GC; async result/adoption fences;
whole logical identity/temp registry. Это проверки реализации уже описанных
решений, не дополнительные исследования T114 и не причины удерживать design
в REQUEST CHANGES до product code. T118 сохраняет actual profile/key loss,
installed standard-user/offline/editions/update/rollback, power-loss/disk-full,
100 cycles и SC-003 acceptance. Ни T114, ни F200 в целом повторно не закрывались;
VM/devices/build/test/GitHub/commit/code/checkbox changes не выполнялись.

## Свежая независимая проверка 112 критериев в области T115 — 2026-10-02

**REQUIREMENTS GATE: PASS / APPROVED, только проект защищённого хранения T115.**
Препятствие stale-review для этого среза снято настоящей проверкой текущих
документов и всех 112 формулировок, а не перенесением прежних `[X]` или результата
стенда. Новых блокирующих замечаний к требованиям T115 не найдено. Это **не
разрешение реализации**, не общий PASS Feature200/Phase0/Phase1/analyze и не
подтверждение T116/T117/T118. Общие HIGH-замечания по причинной модели часов,
F279 и политике оплаты, о которых сообщил основной агент, остаются вне этого
обзора и не снимаются им. Новый T119/календарный переход не принят этим отчётом.

### Метод, владение проверкой и границы записи

Режим: независимая проверка качества требований внутри действующего
`high-risk` среза; единственная разрешённая запись — append-only отчёт.
Лично прочитаны `code-reviewer/SKILL.md` и проектный `speckit-analyze/SKILL.md`.
Проверены ясность, полнота, измеримость, согласованность, отказы и связь с
задачами; достоинства/ошибки нынешнего product code и Windows runtime здесь
не оценивались. Навыки не дали права на сборку, VM, частное аудио или исправления.

Полностью прочитаны Constitution7.1.0, текущие spec/plan/data-model/quickstart,
проверенный снимок tasks с T001–T118, кандидат577строк, прежние разделы этого
отчёта и все112 checklist формулировок. Прочитаны routing/guidance index,
codex-worktrees/spec-kit-flow/product-gates/tracker-policy/release-and-validation,
действующие desktop/bridge contracts. Сверены относящиеся к этому срезу PRD
local buffer/security требования, current-product-status, research решения
RQ30-H1/round141, F277 contract и исходная матрица паритета. Наличие принятого
T114 установлено по его текущему exit report и tasks, без повторной аттестации
сохранённых исследовательских запусков. Часы и новый календарный срез не
рассматривались для отдельного одобрения.

Prerequisites: установленный скрипт не поддерживает `--require-spec` из текста
навыка (явный отказ на неизвестный аргумент). Поддерживаемый запуск
`.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
завершился успешно и вернул именно canonical Feature200; наличие spec отдельно
проверено чтением. `.specify/extensions.yml` прочитан и разобран как YAML:
before_analyze/after_analyze auto-commit hooks выключены, записи hooks нет.
Подсчёт checklist выполнен по actual checkbox lines/CHK IDs, с проверкой
уникальности IDs внутри каждого файла; это не запуск product tests.

Все прежние590строк этого отчёта сохранены. SHA-256 префикса до дополнения:
`2ccf8aafb233b2882e5794060cee8c40ce1e97e287e141d185f4fc3b4774c788`.
Код, пять checklist files, tasks/contract/spec/plan, GitHub, Git state, CI,
VM/devices/builds/private audio не изменялись и не запускались рецензентом.
Результат read-only analyze основного агента не выдаётся за runtime evidence;
содержательная сверка T115 выполнена независимо чтением.

### Точная версия и конкурентное добавление T119

Canonical: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`;
branch `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Feature pointer совпадает с этим HEAD.
Проект находится поверх коммита в изменённых/неотслеживаемых файлах, поэтому
HEAD не подменяет их SHA-256. Хеши ниже повторно проверяются при завершении.

| Документ | SHA-256 проверенных bytes |
| --- | --- |
| `.specify/memory/constitution.md` | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| `.specify/feature.json` | `ac8b95121137914458f0d254f7e0056ae4651f624989a1d35b65b770d7b6ef8f` |
| `spec.md` | `9f7e0d9ca96c6be1209af723e5fad0745a9b78cf8314f2b2996d6697de5c20b2` |
| `contracts/windows-protected-local-custody.md` | `48704f413e132f2b643206649a6422f6e6f6ea118cc63c86d5b675e9d4be9d54` |
| `data-model.md` | `c35201de8245e081bd1e0464cf2e6a1e6762a5d8362126892b17d139e34a58bf` |
| `plan.md` (1155строк) | `9f380ebb1052e2b8d1d0bc29dcae47d4b570c0a1d5b2cfa7d5f36f93f825f53b` |
| `quickstart.md` | `ddd1c7fbb01546a50f184872555cc2b1562deca337a5d3114b6c614005388208` |
| `tasks.md`: проверенный снимок548строк/T001–T118 | `0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19` |
| `tasks.md`: наблюдаемый файл561строка после append T119 | `45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50` |
| `research.md`: только перечисленные storage решения оценены | `b8158ab4bb5e9588bbb0dc00b81e914f47b0497b793f995eac9e71007c8f39da` |
| `contracts/windows-desktop-contract.md` | `8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135` |
| `contracts/windows-native-web-bridge.md` | `b8425859dc3a2d034a7be8767880bb6c86ada639431eccd9403d9c1910c55b95` |
| `contracts/f277-notifications-parity.md` | `e6e4e3048ad53d078cb80dccd3a34c9fe967a04ac65558141a834dc11fb6b7ca` |
| `parity-matrix.md`: границы требований, не runtime результаты | `659b04a1dbd5653888b775b34f8b83cbb94af0bde3e075185ef64136b410d8f9` |
| `checklists/review-2026-10-02-phase0-exit.md`: прежнее принятие literal T114 | `fc80e5285589455b8fcc726ea81f716b716fcde48e94b48895b17f61fc5d38d4` |

Во время обзора основной агент уведомил о добавлении Phase19/T119. Независимо
вычисленный SHA **первых548строк** нового tasks совпал с `0d10022f…`; literal
T115 и T114–T118 не изменились. Приложенные строки549–561 прочитаны только для
определения границы изменения, не для review календарных требований. Полнота,
безопасность и принятие всех119задач этим отчётом не подтверждаются. Изменение
полного task SHA не скрыто и не выдано за повторный анализ нового среза.

### Все пять чек-листов: actual checked/unchecked

`[X]`/`[x]` означает достаточность требований; не реализацию или успешный тест.
Таблица фиксирует фактическую текущую разметку, личное перечитывание всех пунктов
и проверку влияния T115. Ни один checkbox не переписан: выявленного основания
снимать отметки из-за требований именно T115 нет. Это не автоматическое принятие
нового T119 или другой будущей поправки к указанным требованиям.

| Checklist / лично перечитанные IDs | Всего | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| [requirements.md](requirements.md), CHK001–CHK022 | 22 | 22 | 0 | `ed65406d9f400a5ccb6510f40630462206e7afe86d9c9743e75f0d027b2d826a` |
| [audio-capture.md](audio-capture.md), CHK001–CHK024 | 24 | 24 | 0 | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| [advanced-routing.md](advanced-routing.md), CHK001–CHK014 | 14 | 14 | 0 | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| [security.md](security.md), CHK001–CHK027 | 27 | 27 | 0 | `e7aeddb5c3469a46063d3897dd6f77969c8e1fd07b3fc43b2d37936b92195612` |
| [ux.md](ux.md), CHK001–CHK025 (порядок IDs в файле иной) | 25 | 25 | 0 | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| **Итого** | **112** | **112** | **0** | Уникальность проверена отдельно в каждом checklist |

Ниже перечислены **все112 IDs**, сгруппированные по прочитанному основанию.
«Сохранено» — T115 не меняет соответствующее требование и не вводит противоречия;
это не новое одобрение незавершённого clock/F279/billing/calendar проекта.
«PASS T115» — достаточность описанного правила хранения, не принятие его кода.

| Checklist / IDs | Прочитанное основание и вывод в области T115 |
| --- | --- |
| requirements001–004 | Spec FR/SC, пять US с независимыми сценариями; историческая task traceability + Phase18 связывают требования, native/server owners разделены. Storage coverage уточнено ниже, не требует нового backend. Сохранено. |
| requirements005/012/016/019/021 | Custody §§1–4,7–8.2; data-model §§6–8,12; spec FR012–014/022 и assumptions: exact v5/v3/read-v2, normal/degraded/blocked, recovery действия, единственная authority, original preservation и versioned отказ. PASS T115. |
| requirements006/015/022 | Spec цель/Out of Scope/assumptions, plan ownership, parity mapping; отдельный Windows web UI, routing/service и скрытая серверная правка не вводятся. T119 — отдельный непроверенный срез. Сохранено. |
| requirements007/013 | Bridge §§1–9, desktop §§1,7: exact origin/route, document/nonce, отсутствие web capture/file/save authority. Custody §5 ACK не расширяет bridge. Сохранено. |
| requirements008/010/011/014/017/018 | Spec FR004/007–010/016–018 и edge cases, desktop §§2–6: gates/limited/trusted/degraded, технический Record, defaults/таймер, source failure; AAC/N prerequisites не обходятся plaintext fallback. PASS T115 для влияния storage, остальное сохранено. |
| requirements009 | Desktop §§3,5, bridge §3, spec SC001/003; custody §§3,5: явные размеры/overflow, 256dispatcher/2EOS/5s неизменны, 64GiB не quota, reserve и process budgets измеримы. PASS T115, clock candidate не принят. |
| requirements020 | Constitution III/IV, spec hygiene/FR021, desktop §9 и custody §§1–3,6–9: content/key/path не идут в diagnostics/evidence, ошибки safe codes. PASS T115. |
| audio001/003 | Spec FR007/008/Out of Scope и desktop §4: shared render + physical microphone, никаких новых routing/elevated paths. Сохранено. |
| audio002 | Spec FR004/008, custody §§2–5: technical/storage admission, ACL до первого write, budget/disk refusal и background readiness. PASS T115. |
| audio004/017 | Spec edge cases/FR017, desktop §§3,6 и custody §§4–5,7: interruption trusted prefix/retained jobs, no normal failure и idempotent Stop. Сохранено; runtime не проверялся. |
| audio005/006/007/009/010/011/012/014/018/019/021/023 | Spec FR009/010/017/018, SC003, data-model §§3–5, desktop §§3–6, plan validation и quickstart §§3–4: действующий QPC/count/AEC/framing/failure/DRM/pause/матрица. T115 не меняет clocks, допустимую коррекцию, источник или quality thresholds. Сохранено, не принято новое clock решение. |
| audio008/013/015/016/020/024 | Custody §§4–7,8.1–9 и quickstart §12: no callback/UI crypto/IO; degraded checkpoint отдельно от normal seal; exact WAV/AAC/hash/length и N/codec gates, shared buffers/cache/pins/bounded GC, EOS/timeline до finalizer и queue ACK. PASS T115. |
| audio022 | Spec FR021/desktop §9/custody §§1,6,9: только ограниченные metadata, не звук/endpoint paths/codec private content. PASS T115. |
| advanced-routing001–005 | Spec scope/FR007/017/019, plan ownership и custody §§1–2: endpoint mix честный, без driver/service/routing abstraction/privacy обхода/скрытого source fallback. Сохранено. |
| advanced-routing006–010 | Spec Out of Scope, research «Пересмотр гипотезы часов и границы будущего routing», Constitution II/I и plan complexity: будущий process loopback имеет отдельные approval/prerequisites/QA; T115 его не включает. Сохранено. |
| advanced-routing011–014 | Spec FR019/020/SC008, Constitution advanced gate, plan complexity: privilege/install/rollback boundaries и отдельный будущий approved spec сохранены; DPAPI не вводит обязательное elevation. Сохранено. |
| security001–008/011/022 | Bridge §§1–9 и F277 settings: exact шесть текущих intents, envelope/display различие, 64KiB/depth8, version/nonce/replay/routes/frames; F277 internal notification v2, no host object/file/capture authority. Storage не добавляет команду, T119 не расширяет allowlist до отдельного review. Сохранено. |
| security009/010 | Bridge §§4–5,8–9, data-model §8, custody §5: replies/operations — display, сохранение запроса только после committed ACK, не web ack/removed/server proof. PASS T115. |
| security012/013 | Custody §§2–5,8–8.2: validated handles/user ACL, ciphertext temp, two-slot birth/no metadata rollback/empty ledger; strict codecs и retained recovery. Backup не означает право выбрать старую authority. PASS T115. |
| security014/015/016 | Custody §§1,6–9, desktop §7 и spec FR014/022/SC008: GRAF-only logical upload, intent→quiesce→absence→ACK; upgrade/rollback/originals/owner-approved cleanup, no DPAPI cryptographic-erasure/key-recovery claim. PASS T115. |
| security017/018/021 | Constitution hygiene/III, desktop §9, custody §§1–3,6–9: безопасная диагностика/standard user/user-scope/no secret/plaintext fallback. Оpaque technical IDs не user IDs/hashes частного содержимого на диске. PASS T115. |
| security019/020 | Plan Phase0/validation, spec FR020/SC008/010, quickstart §§2,8–9: pinned AEC inputs/notices, signature/runtime/architecture/dependencies/rollback доказательства до распространения. Storage их не заменяет. Сохранено, не release acceptance. |
| security023 | Desktop §7/первоначальный owner handshake, plan T083 и data-model §7: exact spaces→me/HTTP200/2MiB/1024/type/UUID/replay/cancel/epoch; custody §§5,7,8.1 сохраняет immutable owner/fresh cleanup authorization. PASS T115 для сохранения границы, auth runtime не принят. |
| security024/025 | Constitution II/spec technical readiness/desktop §§2–3,7: не добавлены legal/consent/password/server-policy start gates; auth/owner/delete rights не отменены. Сохранено. |
| security026/027 | Spec US5/AC7–9, data-model §9, plan Phase5 и quickstart «Постоянные ключи»: targetKey vs identityKey, V2 compatibility/default/bulk/ошибка; custody не мигрирует эти настройки как запись и не даёт app identity. Сохранено. |
| ux001/002/003/018/020 | Spec FR002/003/021/цель, parity mapping, plan reference/accessibility и Constitution VII: общий кабинет/F277, честный endpoint scope, native conventions/русские подписи/asset provenance. Второго Windows UI нет. Сохранено; общий calendar gap не принят. |
| ux004/009/019/021/022 | Spec US1–3/edge cases, desktop §§2–3,6–8 и custody §§4–8.2: pending/not_committed/ambiguous/recovery-required/unprotected-leftover не saved/normal; close/logout/quit сохраняют jobs/leases; Stop/custody независимы от WebView. PASS T115, live UI не проверялся. |
| ux005/006/007/008 | Spec FR004/015, desktop §§3,8, custody §5: native indicator/Stop, pause semantics, повторный Stop, background ownership и no DOM authority сохранены. Сохранено. |
| ux010/011/012/013/023/024/025 | Spec US5/уточнения, data-model §9/plan Phase5/Constitution II, quickstart §§2,7: Ask8s/explicit Remember/Always/Never/technical gates, background indicator, точная identity/2–15–600s/V2 errors. Исторический ux013 читается с его явным соседним отменяющим legal gate уточнением. Сохранено. |
| ux014–017 | Spec SC009, desktop §8, plan validation, quickstart §§7,11: keyboard/focus/screen reader/High Contrast/200%DPI/narrow/reduced motion/text state. IO не переносится на UI. Сохранено как требования, не accessibility PASS установленного MSIX. |

### Проверка literal T115 и восьми FR/SC

| Требование | Достаточное правило проекта | Задачи исполнения/приёмки, не предпосылка T115 |
| --- | --- | --- |
| FR012 | Custody §§1–3,6,8.2: user-scope DPAPI/ciphertext-only вся content цепочка; bytes/context/bounds/codec; originals отдельно без encrypted claim и автоматического удаления. Data-model §12 согласован. | T116, T117, T118 |
| FR013 | §§4–5,8–8.1: two-slot authority и no rollback/empty queue; typed durable ACK; v3/read-v2 logical schema/identity/receipts/accepted ranges неизменны. | T116, T117, T118 |
| FR014 | §§1,6: incremental logical hashes/exact [start,end), прежние UUID/session/part digests/server truth; нет прямого provider egress/нового сервера. | T116, T118 |
| FR022 | §§5,7,8.1: durable intent→admission fence→cancel/quiesce→actual absence→durable ACK; fresh owner authorization, Recycle Bin и server truth различаются. | T116, T117, T118 |
| SC003 | §5/quickstart §12: cap64MiB owned, cache2MiB/shared, dirty≤4blocks, pins/commands≤32, GC≤64/pass, chunks≤256KiB/reservation до allocation; native MF/DPAPI память измеряется отдельно. CPU/128MiB/60min/100ms и5s drain не ослаблены. | T116/T118 плюс прежние T063/T071/audio gates |
| SC005 | §§4–5,8: exact authority/ambiguous/epoch/restart/receipt/range/migration cuts; quickstart §12 требует100cycles. | T116, T117, T118 |
| SC006 | §§1–3,5–8: native key/user scope/strict parser/no path redirects/metadata-safe failure, ни bridge ни decrypt не даёт право. | T116, T118 и прежний bridge security gate |
| SC008 | §§7–9: lifetime при quit/update, no downgrade/reset original, explicit migration/old-reader refusal/cleanup; exact installed standard-user/offline/Home/Pro/N/Win10/11 matrix. | T117, T118 и прежние package gates |

Уточнения FR012/013/014/022 не противоречат spec/plan/data-model/quickstart и
действующей Конституции; отсутствующих или непроверяемых обязательных решений
в literal T115 на этом кандидате не найдено. Представительный64GiB bound не
стал24h server acceptance, byte cadence не стал wall-time SLA, memory-only
index и wrong entropy T114 не стали full product quota/profile-loss proof.
Retention7days/5GB/80%/95% и reserve=min(10GB,10%disk capacity) сохранены с
physical peak/orphan/pin/legacy учётом до admission. Logical v5 media роли,
AAC/WAV параметры/hash/time/UUID, short-discard marker и existing deletion
intent не переопределены защитой физического хранения.

F1–F6 независимо сопоставлены со свежим текстом: §4 закрывает singleton
metadata rollback; §8 ставит durable old-reader quarantine до rename; §5
задаёт typed outcome/continuations и actual ownership; §8.1 задаёт строгие
authority codecs; §8 отделяет prepared closing fence от готовой queue и
различает cuts, включая switch-before-receipt; §§5/8.1 восстанавливают
persistent transitive roots и валидируют exact historical birth block без
несуществующего старого index. Новых противоречий, требующих ещё одного
исследовательского scope до T115, не установлено. Runtime correctness этих
решений должна быть доказана T116–T118, а не предполагаться из PASS требований.

### Решение, непроверенное и следующая граница

**Stale reviewer-owned requirements gate T115: CLOSED / PASS на указанном
contract SHA и документном снимке.** Прежние начальные REQUEST CHANGES и строки
«review ещё не завершён» в историческом плане/кандидате не являются актуальным
отрицательным вердиктом к этим bytes; история сохранена, latest отчёт задаёт
область принятия. В изменившемся плане после предыдущего узкого review отдельно
сверены storage §T115 и research-only clock дополнения: последние не приняты
как изменение нормативного storage/§5 и не получили approval реализации.

Checked112/unchecked0 не означает112 испытаний PASS или принятие всей Feature200.
Прочитаны все112 критериев; свежая оценка относится к качеству T115 и сохранению
их существующих границ. Не подтверждены implementation/installed capture,
protected whole pipeline, actual key loss/power loss/100cycles/миграция/retirement,
accessibility/UI parity, physical x64/60min/AEC и внешняя release подпись.
Это уже назначенные будущие проверки T116–T118/T063/T071/T083/T087/T088/T097,
а **не причины требовать их завершения до принятия дизайна T115**.

Task115 checkbox рецензент не меняет. Основной агент может использовать этот
отчёт как актуальное reviewer evidence при учёте T115 и scoped issue sync с
проверкой текущих bytes/связей. Report не исполняет issue sync, не закрывает
GitHub tasks и не заменяет main analyze. Общий analyze с HIGH и остальные
обязательные gates по-прежнему препятствуют product implementation; узкий
storage PASS не даёт права обхода. Для T119 нужен свой affected requirements
review/analyze после согласования документов; его наличие не расширяет bridge.
Никаких commit/push/PR/merge/release/deploy или производственной миграции нет.
