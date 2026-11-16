# Round453 — конечный аудит остатка T116

Дата: 2026-10-16. Роль: независимый reviewer; чтение source/evidence, без исполнения тестов, VM, cleanup, GitHub или изменения обычного Git index. Этот отчёт не разрешает implementation/commit/push/install/release и не закрывает task.

## Итог

**T116/#7444 ещё не завершена. Следующий минимальный production gap — отсутствующий пользовательский путь явного назначения доказанной no-login Start-записи после genuine sealed-normal inspection.** Это уже предусмотрено действующими spec/plan/checklist; новая задача, схема или новое решение пользователя не требуются. T106 относится к attribution handoff и не является владельцем этого пробела.

Отдельно остаются: ограниченность cold B только unused outputs, неполная приёмка его эффектных отказов и финальное подключение общего публичного допуска. Нельзя представлять уже работающие HTTP/player/delete как целиком отсутствующие, а намеренно закрытый public Record — как одиночный ошибочный boolean.

Конечный перечень незакрытого остатка приведён ниже: **P1–P3 — production/integration; E1–E2 — обязательное подтверждение.** Это не новая очередь задач и не требование бесконечной матрицы любых сочетаний. Уже принятые положительные сценарии не предлагается повторять ради нового названия.

## Зафиксированная основа

- Authoritative repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
- Branch: `codex/200-windows-followup`; HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
- Current source совпадает со всеми **216/216** inputs Round452; manifest `/Users/yshishenya/Documents/graf-f200-removal452.pXIvdo/green/source.sha256`, SHA256 `65c022a9db2242da677aa300ab40410dde720fc5ff6ac6c261c14c9648d2aaae`; mismatches=0.
- Checklist inventory: **198 файлов, 458 checked, 0 unchecked**. Это состояние requirements review, не 458 доказательств завершённой реализации.
- Tasks: 120, checked=93, open=27. T116, T117, T118, T120 открыты. Связь T116 → #7444 записана в `tasks.md:552`; live состояние issue в этом аудите не запрашивалось.
- Прочитаны актуальные относящиеся к T116 source/plan/contracts/tasks и сохранённые receipts/logs. Исторические runtime PASS не переобъявляются PASS текущего полного source. Полная переприёмка исторических review-рассказов не выполнялась.
- Поправка авторства и превышения роли при directory-only repair452 добавлена append-only в report452. Repair исходил из указания main agent, не человека; действие было вне reviewer-роли. Других filesystem repair/cleanup действий в Round453 нет.

## Конкретный production остаток

### P1 / HIGH — доказанная no-login Start-запись не имеет разрешённого пользовательского выхода

**Требование.** `spec.md:799–815`, plan Start-owner, особенно пункты 5–8 около `plan.md:2204–2235`, CHK006 Start-owner checklist и `quickstart.md:979–993`: принадлежность сохраняется до первого блока; доказанный Start без входа отличается от unknown/missing binding. Только для `capture_prepared` с явно пустой парой owner допускается отдельное подтверждение текущего проверенного аккаунта после полной genuine sealed-normal проверки. Затем один exact-row candidate/commit/readback/adoption переводит эту строку в retry. Автоматическое назначение при входе/перезапуске запрещено.

**Фактическая цепь отказа, не гипотетический edge case:**

1. `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp:1062` сохраняет `capture_prepared` для known Start и `capture_owner_unknown` для unknown. В `finalizeRecordingReservation`, строки 1113–1117, keepable normal переводится в pending только при непустой паре owner. No-login сохраняет исходную `quarantined/capture_prepared` даже после успешного normal finish. Это правильно сохраняет доказательство, но само не реализует claim.
2. `apps/windows/RecApp/Upload/DesktopUploadQueueService.cpp:91–95`: `retryableStatus` допускает pending/retry/needsAuth/blocked, **не quarantine**. `canManualSend`, строки 965–972, проверяет этот guard раньше `confirmUnowned`. Поэтому даже true не разрешает настоящую Start-row. `prepareManualSend`, строки 975–984, наследует отказ.
3. `apps/windows/RecApp/Recording/NativeCapture.h:715–725` вызывает `canManualSend` до создания команды. Startup recovery также выбирает только valid owned row, а не no-login; это корректный запрет автоназначения, не альтернативный путь claim.
4. `apps/windows/RecApp/Web/WebView2Host.cpp:1194–1198` скрывает строки с пустым owner. На строке 1223 `canSend` вычисляется с `confirmUnowned=false`; action admission использует тот же запрет.
5. `apps/windows/RecApp/AppMain.cpp:1499–1524`: существующий обработчик send после document/auth/current projection guards вызывает `requestProtectedManualSend(..., false)` на строке 1518. Пользовательского подтверждения назначения для такого объекта нет.

**Существующее доказательство не закрывает этот путь.** `NativeCaptureStorageIntegrationTests.cpp:774–821` создаёт normal пакет и отдельно `enqueue` обычную pending row с пустым owner; true передаётся напрямую в Native API. Это реальный domain commit-before-HTTP тест, но не signed-out Start → quarantined marker → display → native confirmation. Start-owner classification проверяет durable signedout/unknown, не положительный пользовательский claim.

**Владелец:** существующая **T116/#7444**, прямо по Start-owner clarification. `tasks.md:450` определяет **T106** как F273 attribution handoff (`grafrec://attribution`, campaign/store/sign-in URL); связь с назначением владельца локальной записи отсутствует.

**Минимальный следующий implementation slice:** существующий native send/confirmation и текущая команда хранения, узко для доказанной no-login `capture_prepared` row. После свежих account/document/epoch/context/row/alias/server/deletion guards получить genuine full sealed-normal proof; только после явного подтверждения связать ровно прежние IDs/path с текущим account в одном commit/readback/adoption. До ACK HTTP0. Cancel/stale/unknown/missing fields/foreign/degraded не назначают owner. Не расширять глобально `retryableStatus` на quarantine, не подставлять true всем send и не выводить no-login из пустоты, полученной нормализацией старых данных.

### P2 / HIGH — cold B завершает только unused outputs; continuation уже начатых выходов остаётся незакрытой

**Требование и граница.** Полный protected recovery относится к T116 (`tasks.md:568`, custody contract §4 и §9, plan complete480). Принятый первый B сознательно ограничен: `plan.md:2316–2375` прямо оставляет continuation started outputs/orphan metadata/ambiguous publication незакрытой частью T116. Native B append не превращает этот отказ в восстановление.

**Факт source.** `ProtectedCustodyMetadata.cpp:1688–1724`, `openUnfinished`: union BOTH допускает canonical и необязательный bound manifest. Иная опубликованная output reference возвращает `recoveryRequired`; role без refs обязана иметь exact unused inventory. Начатые media/playback/recovery либо unbound metadata не получают repair/reuse. `V5LocalRecordingWriter::prepareRecovery/finishRecovery` и `NativeCapture::inspectRecovery` другого положительного continuation пути не добавляют.

**Что принято:** actual cold capturing/finalizing с unused outputs → complete480 → protected WAV/AAC → sealedDegraded/full inspection; canonical/privacy/owner/queue сохранены. После 24 process-crash cuts свежий повтор для started outputs честно отказывает без изменения. Это сильное preservation evidence, но не положительное завершение уже начатого восстановления.

**Что действительно missing:** конструкция безопасного продолжения доказуемо валидного interrupted output/publication, которую первый B явно отложил. Это не разрешение достраивать partial birth, чинить singleton/invalid peer, угадывать историю или перезаписывать неизвестный orphan. Для непримиримой неоднозначности сохранённый отказ остаётся правильным. Следующий дизайн обязан отделить доказуемый continuation от такого отказа; простое повторение `recover` сейчас его не реализует.

Этот остаток не принадлежит T117: речь о новых защищённых пакетах, не о миграции прежнего plaintext inventory. P1 меньше и конкретнее для ближайшего кода; P2 не следует маскировать ещё одним отрицательным тестом unused-only API.

### P3 / HIGH, намеренный closure gate — общий публичный Record всё ещё закрыт

`NativeCapture.h:395–418`: публичный `record()` первым проверяет `localQueueComplete()`. На строках 1295–1297 это `readiness_.storageWritable && !queue_.quarantined()`. Поле по умолчанию false; единственное найденное `storageWritable=true` на строке 1875 относится к локальной копии readiness в закрытом `startPreparedRecording`, не к `readiness_`.

`pollStorageStartup` принимает durable storage values/tickets, но не выдаёт общий account/Record/consumer permission. `refreshReadiness` обновляет hardware/permission/AAC, не устанавливает этот storage admission. Реальные AppMain callers (`AppMain.cpp:2191`, 2316, 2345, 2458–2476) используют публичный Record/readiness. Поэтому private native integration не является доказательством доступной пользователю записи.

Это соответствует `plan.md:1973` и другим global-false оговоркам. **Не предлагается исправление одной строкой.** Current admission должна опираться на актуальный protected owner/context, принятую проекцию, завершённые consumers и отсутствие unresolved mutation/reconciliation; legacy `queue_` не может стать доказательством authority новой protected очереди.

Нельзя сделать зависимость круговой: T116 не требует сначала закрыть T117 migration или весь T120. Требуется подключённая storage-часть privacy/T120 consumer, а не installed/physical privacy acceptance. После завершения относящихся consumers нужен единый реальный переход protected admission, не новый UI boolean/публичная capability.

## Карта требований, callers и принятого evidence

Статус «доказано ограниченно» означает конкретный выполненный generated/native сценарий, не полную текущую release-приёмку.

| Обязанность | Реальный owner/caller | Принятое evidence / граница | Статус |
|---|---|---|---|
| Шифрование canonical/WAV/AAC/manifest/recovery/queue/temp до physical write; logical byte identity | ProtectedCustody Files/PackedOwner/Writer/Reader; V5 MF stream; codecs | Core/contract suites, actual writer tests 445–451; нет URL/plaintext fallback в новом V5 пути | Реализовано; итоговая disk-snapshot/installed матрица T118 отдельно |
| BOTH g1/readback, strict codecs, selected generation, no empty ledger/unsafe fallback | StoreOwner/metadata/codec; shared parser read/decode | 441 actual logical-queue/queue-v2: 36 presence cases, 4 BOTH peers, 8 roundtrips; отрицательные сохраняют bytes/quarantine | Доказано ограниченно; исторический manifest не равен всему current source |
| Bounded memory/jobs/pins/IO и physical reserve | Custody allocator/native jobs/reader cache; Files write reserve | 443 same-lease revalidation + pinsFull32; writer/native exact memory; Files.cpp проверяет physical cap/free-space | Реализовано; полные disk-full/latency/device peaks — T118 |
| Start owner до первого audio block; factory только после commit/adoption | Native storage worker → prepareRecordingReservation → V5 factory | 437–441/451 StartOwner, held actual metadata ACK, classification/stale/shutdown/ambiguity | Положительный protected private путь доказан; public caller закрыт P3 |
| Сохранение account A, unknown не становится no-login/owner B | Auth host/native epochs + reservation parser + finalizer | 436 host/native auth cuts; 441 owner presence; 448–452 current A/B/refusal tests | Реализовано и доказано в названных случаях |
| Exact-row finish, no Saved before metadata ACK | Native EOS/finalizer → StoreOwner finalize reservation → common adoption | 438/440/451, actual ambiguous new finalizer449/452; writer/timeline release до mutation | Доказано ограниченно; не новый enqueue/UUID |
| No-login display/explicit normal claim | WebView → AppMain send → Native command → owner candidate | Существующие ordinary unowned tests не достигают Start quarantine | **Missing production P1** |
| Normal sealed Start после restart → pending только после full proof | Native inspectRecovery/requestProof → LocalPackage bridge → owner exact-row commit | 442/443 recovery modes, full hash/session/AAC, ambiguous/readback/lost poll | Доказано ограниченно |
| Cold unfinished readonly complete480 proof | LocalRecordingPackage::inspectUnfinished, genuine owner/pair/readers | 445 positives capturing/finalizing/dirty tail, refusal/resource/sealed-phase cases | Доказано для A; не normal/upload authority |
| Cold unfinished → playable sealedDegraded | V5 prepare/finishRecovery; StoreOwner openUnfinished; existing recovery executor | 446 positives/refusals; native448, Stop/EOS/ambiguousfinalizer449; owner A/current B | Доказано для unused-output B, **P2 continuation отсутствует** |
| Recovery vs live Start/Stop/playback/purge; actual drain | Native existing storage/network/proof exchange, cancellation token | 443 resultReady+live playback/seek; 448–452 held read, EOS до release, deletion cancel/drain | Названные reachable сценарии доказаны; не произвольные injected row changes |
| Logical HTTP/ranges/hash/current row/result ACK | Native protected scheduler → runUpload inspection exchange → transport | 440 six scheduler variants; 441 broader recovery; 451 current adjacent regressions | Consumer существует; нет основания объявить весь HTTP missing |
| Normal и owned degraded local playback/seek/fresh proof | Native player, owner fresh package validation, Web/AppMain gate | 443 player/pin fixes; 451 actual A/B display/player plus 15 host gates | Реализовано ограниченно, quarantine blanket allow отсутствует |
| Short positive intent → row retirement ACK → actual OS absence → notice | V5/owner exact-row retirement; genuine discard reconciliation; Native adoption/history | 430/439 owner12/native10, no-alias/cold; subsequent adjacent regression suites | Доказано в принятой матрице; crash boundary evidence E2 отдельно |
| Local/server deletion intent, physical purge ACK и original preservation | Native deletion commands; StoreOwner; shared purge helper | 449 committed intent/held B/purge; **452 публичный requestProtectedLocalRemoval** → g2→3→4, rows0/OSabsence/HTTP0 | Этот consumer не missing; новый дубль held-B negative не следующий blocker |
| Privacy storage consumer, OPEN до Pause, protected history/size | Native callback → V5 pausePrivacy/closePrivacy; controller/timeline | 438 privacy two segments; 441 privacy suites; V5 recovery history preservation446 | Storage consumer реализован; это не закрытие всего T120/private microphone/hardware |
| Реальное public Record и единое protected readiness | Native record/recordingReady/localQueueComplete → AppMain callers | Current source продолжает false; private prepared readiness не публичный допуск | **Open integration P3**, не потерянный один setter |
| Old plaintext inventory migration/retirement | T117 owner по tasks.md:569 | В этом аудите не реализовывалось/не принималось | Отдельная следующая задача после T116 |
| Full100 cycles, installed OS/device/key/disk/power-loss acceptance | T118 и прежние T063/T071/T083/T087/T088 | VM/generated/compile evidence не заменяет эти gates | Вне закрытия ограниченного native slice; T118 после T116/T117 |

## Конечный остаток runtime evidence — не новая программа бесконечных тестов

### E1 — effectful B failures и final-inspection fence

Принятые 446/447/448 сценарии уже покрывают pre-cancel/quota/refusals, process termination и held-read cancellation. Однако 24 `TerminateProcess(88)` cuts не равны returned IO error/cancel и не подтверждают поздний отказ полной inspect после sealed ACK. Действующий B quickstart отдельно оставляет эти cuts.

Не принят минимальный набор фактических отказов на разных authority-переходах: derived output write/flush, metadata bind/seal publication, post-seal full inspection. Проверка должна показать error/native propagation, неприсвоение normal/playable, canonical/history/owner/queue preservation, actual resource drain и fresh cold outcome. Это группа существующих обязательств, не cross-product всех ошибок/байтов/потоков. Late cuts нельзя считать выполненными по одному successful full inspect или pre-effect quota test.

### E2 — завершение authority-transition и публичной generated приёмки на окончательном source

`quickstart.md:965–1005` требует Start/finish/short authority boundaries, включая crash между publication/readback/adoption/birth/checkpoint/seal/row update. Имеются реальные held/cancel/stale/lost-poll/ambiguous проверки, но в собранном evidence нет полного закрытия названных process-restart cuts; B-output crash suite447 — не доказательство всех Start-owner/short-retirement границ. Missing здесь — именно остаток named authority transitions, а не «любой возможный crash».

После P1–P3 и необходимого P2 решения нужен положительный тест настоящего публичного caller: protected Start ACK → generated capture/EOS → exact-row finish ACK → cold bytes/hash/AAC → нужные logical consumers, с окончательным source/PE. Существующие private vertical tests сохраняют ценность, но не открывают public Record. Указанные quickstart Debug/Release evidence нельзя подменить Release compile-only приложения или историческим Debug PASS на другом manifest. Hardware/installed/power-loss эта проверка не закрывает и не обязана закрывать вместо T118.

## Remaining-consumer / authority readiness, без круговой зависимости

1. Writer/encoder/hash/queue/HTTP/normal playback/owned-degraded playback/local+server delete/short физический результат уже имеют реальные production paths и ограниченные доказательства. Их не надо строить заново.
2. Missing user consumer — P1 explicit claim; missing recovery continuation — P2. Их гарантии относятся к существующей T116, не к attribution T106 и не к old-inventory migration T117.
3. Privacy protected storage adapter уже подключён: `NativeCapture.h:2932–2944`, controller Pause/Resume boundary, protected V5 manifest/history. Полная T120 включает более широкое подавление microphone batches, UI/hardware и собственную приёмку; её task closure не является prerequisite T116. Нельзя объявлять весь T120 выполненным по protected privacy flow.
4. После соответствующей source/evidence приёмки объединённый readiness должен честно представлять работоспособный **current protected** путь. Legacy quarantine/migration inventory может оставаться закрытым без запрета genuine нового protected root. Нельзя сначала требовать закрыть T117, а затем разрешать T116, от которого T117 явно зависит.
5. Следовательно, T116 → T117 → T118 остаётся исходным порядком. Этот аудит не меняет tasks или global-false правило; он показывает, почему текущий private progress ещё не равен завершению T116.

## Прочитанное runtime evidence и ограничения переноса

Сохранённые receipts/logs прочитаны, но VM не запускалась. `owned_processes=0` ниже — поле сохранённого terminal receipt, не свежий CIM-снимок. Actual guest/installed PE заново не извлекались.

| Evidence root/stage | Фактически принято | Не переносить на более широкий claim |
|---|---|---|
| regress438/result.json | lifecycle7, privacy flow с двумя durable segments, owner11; build/test0, post216 | Не весь old matrix/current installed |
| cancel439/result.json | pending vertical+6cancel+submit refusal; short owner12/native10; owner11 | Helper-entry counter до ACK не direct Shell instrumentation |
| scheduler440/attempt3/result.json | 6 scheduler variants + owner invocation; build/all7 CLI0/post216 | Первые failed oracle candidates не PASS |
| owner-presence441/green2/runtime/result.json | 15 CLI0; fullRecovery408373ms, same-PE followup/post216 | Initial240s timeout и GREEN1 fixture fail остаются failures; исторический manifest |
| recovery445/green4 | A positive/refusal/sealed-phase proof, primary29070ms +6 regressions | Не native sealing/full T116 |
| recovery446/green4 | B positive3/refusal15, primary60163ms +6 regressions | Late IO/cancel/final-inspection cuts не выполнены этим PASS |
| recovery447/green4 | 24 actual child process88 cuts; sealed_cold_decode=1; primary105741ms +6 regressions | Не power-loss; started retries преимущественно preservation/refusal, не continuation |
| recovery448/green12 | Primary30510ms +9 regressions; P2 uploadPrepare notCommitted/noerror/contextsame g2→2; Stop/EOS/ambiguous deletion intent | Не physical purge этого раунда и не changed-row произвольная матрица |
| recovery449/green6 | Primary39496ms +11 regressions; retained purgeACK g3→4; ambiguous new finalizer readback/cold | Failed aggregate oracles GREEN4/5 не PASS |
| playback451/green2 | Primary43459ms +12 regressions464.76s; real owned degraded UI/player; JUnit12 failures/skips0 | Не no-login claim; не public Record |
| playback451/app-build.json | AEC/restore/build0 Release x64, PE qualification, source216 | Compile only, не install/launch/runtime Release acceptance |
| removal452/green/result.json | Primary48590ms; ownOrigin и public local-removal обе ветки; coldabsence/exactmemory | Test-only source change, не повтор всей suite/app build и не whole T116 |

Точные последние binaries из сохранённых receipts:

- 451 Native: `dc8d54ba87c9df84b389ca70f744d0d3788274a08eda21beb85b21e62f2f0bdf`.
- 451 Writer: `13077e369bc4c8d1544629ca3de6dd445bf49f67f455b93699a336fe4f260885`.
- 451 Release App: `83e6f7fdf7e43da046e69c0100e448168c44f6b03bee4217e91c61ad32607947`, 3265536 bytes, machine8664; no install/launch.
- 452 Native: `86c4a9a888c895e6aa5a446ab1b08efb222d4f81d2ae561fb1cd06a3c69678ee`.

452 отличается от 451 только test TU; прочие215 manifest inputs сохранены. Поэтому нет основания требовать бессмысленный новый fullapp build лишь для этой test-only ветки. Будущие production изменения потребуют собственного соответствующего source/PE evidence; исторические exact hashes не заменят его.

## Согласованность требований и что делать следующим

Новой CRITICAL/HIGH нормативной коллизии, требующей clarify до узкого P1, не обнаружено. **Source completion findings HIGH: P1, P2, P3; T116 closure — NO GO.** Разрешённый требованиями минимальный следующий участок — **P1, настоящая no-login Start-row → explicit native confirmation → full sealed-normal/fresh exact-row checks → один binding commit/adoption → лишь затем HTTP**. Это рекомендация по существующему scope, не полномочие reviewer изменять код или запускать работу.

Минимальное положительное доказательство P1 должно начинаться именно с genuine signed-out Start, не вручную enqueue ordinary pending row. Нужны сохранённые marker/explicit owner presence после finish/cold reopen, доступная неназначенная строка, cancel без изменения, явное подтверждение текущего A и один exact-row ACK до HTTP. Unknown/legacy missing owner/foreign/degraded не должны попадать в claim. Остальные отрицательные проверки переиспользуют существующие gates, без нового framework/ledger/task.

## Текущие нормативные SHA256

```text
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec.md
52ab9f58a277757c9c3f2eb44076eed7b9a876fb01d5441dd03d700e8b111ba7 plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks.md
4e43e6b6d187afe3b7ff2af099abf67cab4e04e9f32deea5f220723331d7d067 quickstart.md
6c1b4432fc37af7eb97f7d9202072344b0c8e5ccf7724d26ad3081ec8b79f716 research.md
6023a5095e3c6726fd5a885c4cf46c573dd8acc31235e0eb2d914460c33f8214 data-model.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 contracts/windows-desktop-contract.md
a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490 contracts/windows-protected-local-custody.md
a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 contracts/windows-protected-packed-custody.md
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 .specify/memory/constitution.md
```

## Граница действий reviewer

Записаны только данный report и ранее запрошенная append-only correction report452. Source, spec/plan/tasks, checklist markers, VM, GitHub, scripts, ordinary Git index и cleanup не изменялись. Никакой T116/T117/T118/T120 marker не отмечен; whole-feature readiness не заявлена.

## Append — независимый requirements/analyze gate явного no-login claim

Дата: 2026-10-16. Это последующая проверка уже записанных plan/quickstart append, не изменение и не повторная интерпретация конечного аудита выше.

### Решение

**Bounded normative GO для реализации существующего P1: CRITICAL 0 / HIGH 0, blocking clarification 0.** Прочитаны целиком `plan.md:2460–2503` («T116: завершение явного назначения no-login Start (аудит453)») и `quickstart.md:1086–1106`, сопоставлены с прежним Start-owner plan, spec Session 2026-10-16, desktop/custody contracts, T116 и конституцией. Новый append конкретизирует уже принятое поведение, не вводит новое право назначения, формат, сервис или prerequisite локальной записи.

**Это допуск качества требований до кода, не source/runtime GO.** Production P1 пока остаётся missing по конечному аудиту. P2, public admission P3, E1/E2 и T117/T118/T120 этим решением не закрываются.

### Проверенные границы и task coverage

| Обязательство текущего append | Нормативное основание и измеримость | Checklist / existing task |
|---|---|---|
| Только genuine no-login `quarantined/capture_prepared`, явно пустая owner pair; exact local/directory/session; без aliases/server identity/ranges/attempts/deletion/active reservation | Plan 2469–2472; spec Start-owner и Session 2026-10-16. Unknown/legacy не получают право из отсутствующих полей | CHK001/002/004/005/006; T116 |
| «Не назначена» через прежний projection, Send только при актуальном full sealed-normal display inspection | Plan 2473–2476; display scalar связан со snapshot/auth epoch и не даёт proof/playback/delete authority | CHK006; T116 |
| Явное native подтверждение назначения текущему account/workspace; default Cancel; повторная проверка document/nonce/epoch/account/row после диалога | Plan 2477–2480; quickstart positive native/WebView/AppMain route и cancel/stale checks | CHK006/009/010; T116 |
| Новый свежий genuine full-normal proof **до** candidate owner update, а не доверие display scalar | Plan 2481–2485; fresh root/queue/exact row/package revalidation после ожиданий; quickstart scalar-substitution refusal | CHK003/005/006/007; T116 |
| Full hash/AAC через существующий asynchronous inspection exchange, не UI/callback/storage mutex; Start/Stop/finalize обслуживаются во время ожидания | Plan 2481–2485; quickstart длительной inspection; прежние resource/concurrency gates | CHK004/010; T116 |
| Один candidate/commit/readback/adoption для прежних IDs и owner binding → retry; HTTP только после ACK | Plan 2486–2487; quickstart pending/lost-poll/HTTP0 до adoption, настоящий upload consumer и cold read | CHK003/005/006/009; T116 |
| До publication cancel/stale/refusal не назначают owner; после publication physical truth принимается без повторного claim и без устаревшего HTTP | Plan 2487–2491; quickstart cancel/IO/quota и ambiguous physical reconciliation | CHK005/009; T116 |
| Native ownership/proof удерживается при unknown outcome и освобождается на executor до terminal/drain | Plan 2489–2491; quickstart actual readers/jobs drain и memory limits | CHK009/010; T116 |
| RED/GREEN начинается с actual accepted signed-out Start → reservation ACK → generated EOS → normal finish → cold restart, не ordinary pending/enqueue fixture | Plan 2492–2497; quickstart 1088–1097, exact marker/pair и cold binding | CHK006/009; T116 |
| Negative boundaries и прежние owned send/playback/delete/concurrent-recording guarantees сохраняются | Plan 2494–2497; quickstart 1099–1106: unknown/legacy/degraded/unfinished/foreign/alias/server/deletion/active/cancel/stale, bytes и HTTP fences | CHK004/005/006/007/008/009/010; T116 |

Scoped analyze: 10 групп обязательств, **10/10 имеют existing task coverage T116**, unmapped requirements=0, новых tasks=0. В этом bounded delta не выявлены blocking ambiguity, duplication, constitution conflict или противоречие порядку T116 → T117 → T118. T106 attribution не получает новую обязанность. Не утверждается повторный полный analyze всех исторических feature требований.

Конституция II соблюдена: подтверждение относится к передаче/назначению уже записанного объекта, не к Record; сеть/auth и новый диалог не превращены в prerequisites локального Start/Stop. Конституция III и FR-012/014 сохраняют encryption/content/credential boundaries. Конституция IV и FR-022 сохранены exact-row/deletion guards. Конституция VI сохраняет tests-first, независимый requirements gate и раздельную source/runtime/installed приёмку.

### Достаточность существующего checklist

`checklists/start-owner-recovery.md` перечитан целиком: **10 checked / 0 unchecked**. CHK006 непосредственно покрывает no-login/unknown distinction, display/manual claim/HTTP и запрет blanket quarantine allowance; CHK009 — publication/readback/adoption, claim cuts, stale/lost poll и ownership при ambiguous. CHK001–005/007/008/010 остаются согласованными с новым append: исходный carrier/identity, active reservation, sealed proof, short/deletion и resource/visible-control границы не изменены.

Нового uncovered quality requirement не найдено. **Новый checklist не создан; существующие markers не изменены.** `[x]` продолжает означать качество требований, а не реализованный claim или выполненные новые runtime cuts.

Fresh inventory: **198 checklist-файлов / 458 checked / 0 unchecked**; tasks **120 / 93 checked / 27 open**. T116 остаётся open и связан с #7444 по текущему tasks.md. Live GitHub не запрашивался. HEAD и branch прежние; source всё ещё совпадает с 452 manifest **216/216, mismatch0**, так что review не опирается на предположение о production edits.

### Текущие SHA256 после plan/quickstart append

В сравнении с предыдущей таблицей нормативных SHA изменились только plan и quickstart. Полная текущая фиксация:

```text
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec.md
2d1f170a0345ef0201848f6d0a934f973db596f001fa7c431e2b973c702bdd1e plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks.md
3eb4f3a05a4295025a149ecbb91b4cce71d4caacbf94f19f24d9631f16e25c12 quickstart.md
6c1b4432fc37af7eb97f7d9202072344b0c8e5ccf7724d26ad3081ec8b79f716 research.md
6023a5095e3c6726fd5a885c4cf46c573dd8acc31235e0eb2d914460c33f8214 data-model.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 contracts/windows-desktop-contract.md
a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490 contracts/windows-protected-local-custody.md
a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 contracts/windows-protected-packed-custody.md
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 .specify/memory/constitution.md
1684307dd5d9ea36d9939842b53764839b87b6247e1a744e63d6640426189ec7 checklists/start-owner-recovery.md
```

### Метод и граница этого append

Применён `speckit-analyze` для bounded cross-artifact review. Before/after analyze hooks в текущем extensions.yml отключены. Обычный prerequisite mode установленного скрипта вызывает `get_feature_paths` с возможной записью feature.json; для соблюдения разрешённого write scope вместо него использован только `--json --paths-only` с `--no-persist`, а наличие spec/plan/tasks и coverage проверены чтением. Returned logical feature label не подменяет проверенные actual Git branch/HEAD.

Результат анализа записан здесь по прямому разрешению на reviewer report; остальные артефакты не редактировались. Тесты/VM/cleanup/GitHub/issue sync/commit и normal Git index mutations не выполнялись. Следующий шаг по принятому плану — квалифицированный RED на настоящем no-login Start, затем минимальная реализация и отдельное source/runtime review. Текущий нормативный GO не выдаёт public READY и не закрывает конечный аудит T116.

## Append — 2026-10-21: bounded source GO двух исправленных тестов T116/453

Независимая проверка выполнена по actual working files в `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, с применением `code-reviewer`. Область строго ограничена `DesktopUploadQueueV2Tests.cpp::testProtectedManualSend`, Send-частью `RecordingIndicatorTests.cpp::testCloseSourceWiring` и `testRecordingProblemAndShortSourceWiring`. Остальная история diff, полная реализация T116 и новые нормативные изменения не принимались.

**Решение: bounded source GO; блокирующих замечаний в этих участках нет.** Это исправление устаревших тестовых ожиданий под уже существующие ownership/admission и short-finalization правила, без разрешения ослабить production.

Проверены текущие SHA256:

```text
2bf116045647c226614e13321c1b58fc9b3473c978186aa09311b4be3169018b  apps/windows/Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp
91c17499fa74b345937ca67c32c08efc0d92c838e7c4351dac1c882d1569b6b4  apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp
```

### Основания source GO

- Queue, строки 500–568: пустая owner pair сама по себе не позволяет claim; старый retry/pristine отказывается даже с подтверждением. Положительный value-level случай требует `quarantined/capture_prepared`, согласованных UUID session/directory/local IDs и явного подтверждения. Сохранены отказы для неподтверждённого, unknown/legacy, неверного status/reason/IDs, частичного owner, попыток/ranges/server history и отмены; reject/cancel сравнивают сериализованные bytes до/после. Cold serialize equality в строках 520–525 не требует отсутствующего `Item::operator==`. Этот value-level fixture не выдаётся за genuine native sealed-package proof. Existing owned-send, deletion, allocation и memory guards сохранены.
- Send, строки 557–570: проверяется конкретная ветка `send` и замыкание с `claim`, а не старое буквальное `false`. Document/epoch, pending, action admission и повторный exact snapshot предшествуют запросу; unowned claim требует native confirmation с default Cancel, existing owned путь остаётся без нового диалога. Сверено с текущим `AppMain.cpp:1522–1545` и `isPreparedUnownedRecording`/`prepareManualSend`.
- Short, строки 990–1014: тело `keepablePackage()` проверяется на `normalPackage() && !shortRecordingDiscarded`; writer release, finish reservation, commit, result-ready, adoption и guarded physical discard остаются связанными проверками порядка. Успех discard требует `shortRemoved && ticket.error == CustodyFileError::none`; current-epoch и notice guards сохранены. Сверено с actual worker completion и `V5LocalRecordingWriter.h:60–62`.
- Исправление последнего селектора, строки 1006–1007: `finalized` начинается с первого `const bool durable =` внутри уже ограниченного `finalizer`; в actual фрагменте это единственное такое определение (`NativeCapture.h:2798`). Поэтому последний `expectBefore` сопоставляет discard-success в строке 2808 с terminal завершения в строке 2815, а не с более ранним unrelated terminal отказа `prepareRecording` в строке 2727. Проверка не удалена и не превращена в безусловный PASS. Наличие этого разделителя уже проверяется предыдущим вызовом `section` для `discard`.

### Сохраняющиеся acceptance gates и граница доказательств

Это только source review, не компиляция и не runtime PASS. По сообщению main на момент запроса `host final full48` и native3 с exact216 manifest prefix `e84da330...` ещё выполнялись; полная контрольная сумма manifest и terminal receipts здесь не проверялись. Нужны их собственные завершённые результаты, привязанные к указанным test hashes и полному manifest. Предыдущие source-assert FAIL сохраняются как исторические результаты своих версий и этим GO не переписываются; test ignore не разрешён.

Новая широкая проверка 198 checklist-файлов/477 markers этим append не заявляется; прежний requirements gate не изменён. T116/#7444, остальные задачи/issues, whole-feature acceptance, installed/deployed/UI/hardware, release и production acceptance этим решением не закрываются. Никакие issues не закрывались.

Единственная запись reviewer в этом шаге — данный append по прямому разрешению пользователя. Код, нормы, checklist/spec/plan/tasks, build targets, Git/GitHub и VM не изменялись; сборки, тесты и UI не запускались. Разрешение на commit/merge/release не выдаётся.

## Append — 2026-10-21: независимая bounded runtime-квалификация stale-test correction

**Решение: bounded runtime GO для двух исправленных тестов в рамках предыдущего source GO.** Проверены только сохранённые материалы в `/Users/yshishenya/Documents/graf-f200-public458.po8CtB`; новых запусков не было. Это не полная приёмка T116 и не перенос результатов на другие исходники.

### Фактически проверенные результаты

- `t116-stale-portable-all.xml`: 48 уникальных testcase, каждый `status=run`, failures=0, disabled=0, skipped=0; нет failure/error/skipped nodes. `t116-stale-portable-all-actual.log` содержит все 48 выполненных тестов, 48 `Test Passed.` и завершающий `End testing`. Queue: 0.84549 s; RecordingIndicator: 0.0922964 s. XML timestamp 2026-10-21T19:05:32. Это полный сохранённый portable набор 48, не полный native набор 105.
- `t116-stale-native3/result.json`: terminal=true, configuration=Debug, build=0, test_exit=0, executed_tests=2, postflight=216, owned_processes=0; failure отсутствует. Flags device_audio_read/real_network/installed=false описывают границы этого запуска, не аппаратную или установленную приёмку.
- Native XML: ровно `DesktopUploadQueueV2Tests` (2.27631 s) и `RecordingIndicatorTests` (2.00927 s), оба `status=run`; failures/disabled/skipped=0, нет failure/error/skipped nodes. `test.log` и полный `actual-test.log` подтверждают 2/2 PASS и завершение. Обозначения 14/105 и 48/105 в LastTest.log — номера выбранных тестов общей конфигурации, не исполнение всех 105.
- В полном native actual log проверены десять различных popup cases 0–9: для каждого actual_loop=1 и timeout=0. Cases 0/1/6/8 имеют callbacks=1, остальные callbacks=0; это зафиксированные варианты результата, не пропущенные тесты. Сокращённый system-out XML не использовался как замена полного журнала.

### Исходники и PE: доказательство и его пределы

SHA256 native3 `source.sha256` независимо пересчитан: `e84da3307ed78e4bd651f51aba5ba56147ae39daf7efa4d00cdfb59ccd2b334a`, совпадает с receipt. Все 216 уникальных безопасных относительных путей манифеста независимо прочитаны и сверены с current worktree: missing=0, mismatch=0. В сравнении с сохранённым `prior.sha256` изменился только `apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp`; добавленных/удалённых inputs нет, `changed.json` согласован. Обе итоговые test hashes совпадают с предыдущим source GO:

```text
2bf116045647c226614e13321c1b58fc9b3473c978186aa09311b4be3169018b  DesktopUploadQueueV2Tests.cpp
91c17499fa74b345937ca67c32c08efc0d92c838e7c4351dac1c882d1569b6b4  RecordingIndicatorTests.cpp
```

Прочитан сохранённый `validate-t116-stale.ps1`, но не запускался. Он проверяет prior/current 216 inputs до сборки, staged изменённый файл, строит именно два Debug targets, записывает PE hashes, запускает точный anchored CTest filter, копирует LastTest.log, повторно сверяет 216 inputs и оба PE после тестов, затем пишет terminal receipt. Внутри try ошибка попадает в receipt.failure; terminal сам по себе не принимался за успех. Прочитанный build.log согласован с Debug target paths из actual log.

PE hashes сохранённого receipt:

```text
60902de7d10e99a9a49e03a824b2349cd2c7805ddfcfa4ad42bf29052476de29  DesktopUploadQueueV2Tests.exe
ea45f50ca34e72170e1b0b6ff953f47c0856df41b9486ebda7d5bbe530cfa4f9  RecordingIndicatorTests.exe
```

Самих `.exe` в проверенном external evidence наборе нет: reviewer не пересчитывал их хеши и не проверял PE headers. Их before/after неизменность квалифицирована по сохранённому receipt и сценарию, а не как новая независимая binary attestation. Для host XML/actual log отдельный source/PE manifest в заданном наборе не предъявлен: принимаются наблюдаемые 48/48, без заявления независимой полной host source-to-binary привязки. Native3 даёт source-bound подтверждение обеих исправленных целей; native popup proof не приписывается portable запуску.

### Контрольные суммы сохранённых доказательств

```text
90d60aa6b5899b07dd66b1e3e6e487eadc638006948f56385524183065851d47  t116-stale-portable-all.xml
07d755e5f10c7aa4d91de0dbc71790d1e687c0c9c0bd104265de919f1761743b  t116-stale-portable-all-actual.log
8003ab3b9192cd1d045df387c673a5195801e1ea66f0343f212c3c538e9205b2  t116-stale-native3/result.json
b130a2701eccdca600a12de350506cbef749c2aed031086a97a03fae9cc78809  t116-stale-native3/result.xml
6da9c80fed06985fc66388f73e501864f04751b83c7be3f4461fd85e5a335621  t116-stale-native3/actual-test.log
c60a11e24dc6893abe6053ee05c23537cf183ecbef0a974fdc63586326546ec2  t116-stale-native3/build.log
91b6e6e0c990a1fd3a89000e5dc87a68c516ac2f3556bedab02c689da698e529  validate-t116-stale.ps1
```

Предыдущие FAIL относятся к своим версиям и остаются историческими доказательствами; test ignore/ослабление admission не применены этим review. Gate текущих двух исправленных тестов больше не ожидает runtime, но прежние отдельные whole-feature, T116/#7444, installed/deployed/UI/hardware, release и production acceptance сохраняются; issues/tasks/markers не закрывались. Проверка PE receipt не равна установке приложения. Единственная запись этого шага — данный разрешённый append; source, нормы, checklist, Git/GitHub, VM и среда выполнения не изменялись, тесты/сборки не запускались.

## Append — 2026-10-21: T120/#7590 unread synthetic consumer — source GO и bounded RED

Этот отдельный T120-срез не меняет предшествующие выводы T116. По прямому разрешению пользователя записывается независимая квалификация сохранённого RED, без запуска/изменения среды. Применён `code-reviewer`; текущая область source review — только `privacyPauseKeepsUnreadPacketsSuppressed` и CLI/default-включение в `apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp`.

**Source GO: блокирующих замечаний в данном тесте не обнаружено. Bounded RED квалифицирован для synthetic unread consumer на host и Windows Debug; это НЕ COM/FIFO acquisition acceptance и НЕ GREEN T120.**

### Привязка требований и исходников

Применимость existing T120 plan/checklist/analyze проверена в предыдущем шаге: C0/H0 по конструкции, все 12 физических пунктов privacy-pause.md прочитаны, 12 checked/0 unchecked, без правок. Ранее отдельно через read-only `gh issue view 7590` подтверждены OPEN, канонический title `[200][P0][security] T120: Не возвращать микрофонные данные паузы после возобновления записи`, body Spec tasks:T120, базовый HEAD/ветка и current tasks SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`, labels feature:200/priority:P0/area:security/gate:pr-blocker/type:bug. Assignees пусты, но tracker policy не требует assignee для task-backed ownership. Отсутствие T120 в локальном issue-map не означает отсутствия GitHub owner; прежняя неопределённость owner этим чтением снята, новый issue/re-sync не требовался. Это не новое закрытие checklist/task/issue.

Current test SHA256 независимо перепроверен:

```text
83012731734371bb7ec4787c51f7d1b6b52a19da282c02d2b524403c9c773dc0  apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp
```

Native manifest `t120-unread-native1/source.sha256` SHA256: `e13853cc5a3a374cd671413418558e2fdc5e328d141272c31e1529190ac286bb`, совпадает с receipt. Все 216 уникальных путей независимо сверены с actual worktree: mismatch=0. Prior/current delta содержит только этот test TU; добавленных/удалённых inputs нет, changed.json согласован. Production inputs не изменились относительно prior этого запуска.

### Почему тест содержателен

- Source:787–884: prefix сначала проходит worker/normalizer/dispatcher/timeline; после публичной принятой Pause создаются два ненулевых generated source packets и удерживаются до их собственного первого epoch snapshot. После Resume они поступают через существующий packet helper, без искусственной подстановки старой epoch; новый packet имеет отдельное ненулевое значение.
- Source:841–863: публичные async pause/resume, checkpoint callback и ожидание фактического завершения переходов. Render packets подаются, пока старый mic удерживается. Это конечная synthetic последовательность, не доказательство неограниченно непрерывного native producer.
- Source:864–883: до named assertion проверены worker finished/no error, четыре releases, savedLocal, один finalizer callback, оба EOS (mask3), дополнительный CLOSE при Stop, четыре output/AEC, PTS, system/mix, неизменный prefix и новый audible microphone. При blanket mic mute тест откажет раньше на fresh audible guard. Итоговые значения читаются после worker/dispatcher completion.
- CLI:1212–1214 выбирает новый случай; default:1223 также вызывает его. Прежние async/fifo/prefetch не исключены; guard и named assertion не ослаблены.

### Native terminal evidence

Прочитаны `BASE=/Users/yshishenya/Documents/graf-f200-public458.po8CtB`, `t120-unread-native1/result.json`, build.log, unread.log, control-async/fifo/prefetch.log, source/prior manifests, changed.json и сохранённый `validate-t120-unread.ps1`; сценарий не запускался.

Receipt: terminal=true, Debug, build=0, controls async/fifo/prefetch=0, unread_exit=3, expected_red=true, executed_cases=4, postflight=216, owned_processes=0; failure отсутствует. Build log подтверждает компиляцию TU и Debug CaptureFaultStateTests.exe. Control async log пустой: его успешный выход подтверждает receipt и проверенный runner, а не вымышленный печатный marker. FIFO log содержит все 4 сочетания extracted0/1 × count240/480 с suppressed=1; prefetch — все 6 hold_stage0/1/2 × acquired_paused0/1 с suppressed=1.

Полный декодированный unread log содержит:

```text
privacy_unread source_packets=2 releases=4 frames=4 aec=4 eos=3 finalizer=1 old_suppressed=0
Assertion failed: oldSuppressed && "resume_must_not_rejuvenate_unread_microphone_packets"
CaptureFaultStateTests.cpp, line 883
```

Это ожидаемый privacy failure после законченного тестового пути, не ошибка подготовки, timeout или пропущенный запуск. `executed_cases=4` записывается runner как число CLI invocations: три checked controls и unread; это не утверждение о четырёх CTest testcase или полном native suite. Expected nonzero не объявляется обычным PASS.

Runner проверяет 216 inputs до/после, выполняет три точных control CLI и unread CLI, проверяет nonzero плюс prerequisite/named markers и неизменность PE после запуска. Receipt PE SHA256: `fcbcc211750b555c41ad97db607f268602c7882816fe9e25443a30418447c2a2`. Сам бинарник в этом evidence наборе reviewer не перечитывал/не хешировал; binary bounds квалифицированы по receipt и прочитанному runner, не как новая независимая PE attestation.

### Host и точные границы

`t120-unread-host-red.log` лично прочитан: та же prerequisite строка и named assertion на строке883, SHA256 `efb1f534cc96cfcc4455981cf482fc70fb1dcca590bda5919f853afb90cbfcb3`. Отдельные host build0/runtime134 сообщены main; двухстрочный журнал сам не содержит exit/build receipt. Наблюдаемый host named RED квалифицирован, но его отдельная binary/exit привязка не выдумана.

Это реальные worker.consumePacket/normalizer/dispatcher/timeline и публичный async control, но synthetic acquisition hook/source packets, тестовый checkpoint и тестовый finalizer callback. Не пройдены настоящая COM/FIFO boundary, durable T116 writer/metadata, installed/hardware/real-audio, вся native/regression матрица или release. Receipt device_audio_read/real_network/installed=false согласован с этой областью. RED не одобряет будущий production frontier, новую authority или ещё не рассмотренный technical design. T120/#7590 и T116 остаются открыты; production fix требует отдельного source/runtime gate.

### Контрольные суммы native доказательств

```text
b69eba4a61c9073b5f0588ee02f183797e1654c9ed3e35852a0dfe4c06f9ae6a  t120-unread-native1/result.json
cbc04ddcea01126f17a6d248f8bff86659c2abb45aa51113131ceb25c396717e  t120-unread-native1/unread.log
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  t120-unread-native1/control-async.log
2084f4e382b40ef54ff6fe75cdaabf52883302f2462bf9ba9ac609d19ac8bcad  t120-unread-native1/control-fifo.log
f4fc20791e3fb2510f1a6aa684e8e91f5b419e6964817b2504eeffd5d8f96c2d  t120-unread-native1/control-prefetch.log
66cd3298414a6ee66a5feba7a95155c1486d5b03b082771e9a703cb24784e779  t120-unread-native1/build.log
17cee6919eb564d62e2ac39d1e8857126b7f5f8fe77156dd420f744dbff2cf50  validate-t120-unread.ps1
```

Записан только этот разрешённый append. Reviewer не менял code/norms/checkboxes/tasks/issues/Git, не запускал tests/build/VM/UI, не менял timeout/oracle и не выдавал commit/release authority.

## Append — 2026-10-21: T120 partial-prefix normalizer prerequisite, scoped source/runtime GO

По разрешению пользователя независимо проверены actual три файла, tests и сохранённые host/native evidence. **Scoped source GO и Windows Debug runtime GO только partial-prefix normalizer prerequisite; блокирующих замечаний в этом срезе не найдено. Unread consumer сохраняет квалифицированный RED.** Это не приёмка production frontier/controller или всей приватной Pause/Resume.

### Exact source и конструкция

```text
fe07d0278f18f16a32d913d919e2abd900a91ea0d1d051c7371a07f41ba79080  apps/windows/RecApp/Audio/AudioTypes.h
0fb6450791f7ffc51ffa2d8d7ab03ba59ef0e045bfe742df7b5ca5fcc1f116eb  apps/windows/RecApp/Audio/AudioNormalizer.cpp
47c055bcd3655077d47382fe771b3a894d76a54b87d00a7ac7e92ab4a765b00a  apps/windows/Tests/GrafWindowsCoreTests/AudioNormalizerTests.cpp
```

Применён `code-reviewer`, текущий код прочитан целиком в относящемся объёме. AudioTypes:28–29 добавляет default0 scalar в конец aggregate, в исходных frames, не interleaved samples. Нового wire/schema/public admission нет. AudioNormalizer:27–38 сохраняет полный raw-finite проход до prefix range validation, для system prefix игнорируется; invalid mic prefix даёт sticky fail, не clamp. Clock/format/count/route/domain и output budgets не ослаблены.

AudioNormalizer:59–69 обнуляет mono prefix до resampling. SuppressTail учитывает current prefix, а sourceIndex<prefix в строках134–141 оставляет целиком нулевую позицию, не примешивая свежий правый сосед к старой позиции. Позиции/count/PTS не вырезаются. Native48 путь остаётся без интерполяционных потерь suffix. Output scalar остаётся0 через output={} и отсутствие переноса input scalar. Оба пути сохраняют previousMicrophoneSuppressed_=suppressed||prefix==sourceFrames (108/151): полный prefix защищает deferred old tail следующего пакета; partial сохраняет настоящий suffix/previousSample, а не blanket mute. При prefix0 старая ordinary обработка сохраняется. Новых compile/header/lifetime hazards в этом bounded review не найдено.

AudioNormalizerTests:135–215 проверяет 160 сочетаний rate8/44.1/48/192k × mono/stereo × single/whole × mic/system × prefix0/1/half/n-1/full. Stage0 ordinary, stage1 prefix, stage2 fresh дают prefix/tail/suffix контроль. Reference normalizer получает ordinary metadata/input; ожидаемый ноль определяется integer source-floor позицией, не округлённым output count. Boundary deferred position включена в oracle; system проверяется с UINT32_MAX prefix и должен совпасть с ordinary. Output count дополнительно проверен независимой exact-ceil формулой, включая8k; metadata/PTS/offset и reset scalar проверены. 16 негативных случаев (fresh/started ×8) покрывают prefix overflow, NaN/Inf в подавляемом участке, NaN suffix, format/route/domain/discontinuity и sticky failure. Existing privacyResamplerBoundary и original clock/partition/pipeline проверки сохранены. Main:350–353 включает prefix в default и focused --privacy-prefix; full native runner запускает binary без CLI, а не только печатный prefix marker.

### Сохранённый native runtime

BASE `/Users/yshishenya/Documents/graf-f200-public458.po8CtB`, stage `t120-prefix-native1`. Прочитаны runner `validate-t120-prefix.ps1`, result.json, полный normalizer.log, три control logs, unread.log, build.log, source/prior manifests, changed.json и staged три файла. Никакой runner/test reviewer не запускал.

Manifest SHA256 `63fae10e816fc005403783f243b7448a5cbae9ead16b9d9261125247768bbb0e` независимо пересчитан и совпал с receipt. Все216 unique paths совпали с actual worktree: mismatch0; prior delta и changed.json — ровно три файла выше, без added/removed. Staged bytes всех трёх также совпали. Frontier/controller и CaptureFaultStateTests.cpp в этом delta не изменялись.

Receipt: terminal=true, Debug, build=0, normalizer_exit=0, controls async/fifo/prefetch=0, unread_exit=3, expected_red=true, executed_cases=5, postflight=216, owned_processes=0; failure отсутствует. Native build log согласован с compilation AudioNormalizer.cpp/test TU и обоими Debug executable paths. Full normalizer log: privacy_prefix cases=160 invalid=16 плюс16 прежних resampler комбинаций, каждая correct=1/audio=1. Silent original default regressions принимаются по normalizer_exit0 и прочитанному main/runner, не по вымышленным индивидуальным markers. FIFO log содержит4 suppressed=1, prefetch6 suppressed=1; async log пустой, exit0 подтверждён receipt. Executed_cases5 — full normalizer +3 CLI controls +unread, не пять CTest testcase и не full native suite.

Unread log подтверждает прежнюю named assertion строка883 после source_packets2/releases4/frames4/AEC4/EOS3/finalizer1/old_suppressed0. Это ожидаемое сохранение consumer RED: новый prefix scalar не заполняется frontier. Ненулевой unread exit не выдан за обычный PASS. Полная приватная Pause не исправлена этим prerequisite.

Runner выполняет source216 checks до/после, exact build двух Debug targets, full normalizer, controls и expected named RED, а также PE checks до/после. Receipt PE hashes:

```text
a23453bc021eff8bd3f2888d14135e56e3034deebaeabb02d2171ff18b70ee88  AudioNormalizerTests.exe
d294a15b28f000ce7f5718e414629702bf3a77f33b352583c23d556f8571dd1f  CaptureFaultStateTests.exe
```

Это PE bounds по receipt и сохранённому runner, не прямое повторное чтение guest binaries reviewer. Guest/VM не опрашивались; actual executable headers/bytes reviewer не проверял.

### Host и acceptance limits

Лично прочитаны `t120-prefix-host-green.log` (prefix160/invalid16, все16 resampler correct/audio1) и `t120-prefix-host-build.log` с завершёнными targets. Host terminal exit0 предоставлен main; отдельной host exit/source-to-binary receipt в этих двух логах нет. Исходный prefix-specific RED до normalizer implementation сообщён main ранее; его отдельный logfile здесь не перечитывался и не выдаётся за лично проверенную receipt. Native prerequisite GREEN и сохранённый unread RED проверены независимо как описано выше.

Общий host full-all build по последнему сообщению main ещё выполнялся, CTest не начинался; общий host/full-native GREEN не заявляется. Нет real audio/network/install; нет принятой COM/FIFO frontier, durable T116 checkpoint, installed/hardware/release приёмки. T120/#7590/T116 остаются открыты; public capture admission не меняется. Следующий frontier/design/source/runtime gate самостоятельный. Нормы и12/0 checklist не переотмечаются этим source/runtime append.

### SHA256 сохранённых материалов

```text
9dedb846f1a392a96de4d8b5d2a790aac99c1b69dafa9dcb8fb1c6fbeecd9532  t120-prefix-native1/result.json
2588481974442a22d3e693f6a2ab003dd418815d1b9993b0b54138b85e6cb5f2  t120-prefix-native1/normalizer.log
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  t120-prefix-native1/control-async.log
2084f4e382b40ef54ff6fe75cdaabf52883302f2462bf9ba9ac609d19ac8bcad  t120-prefix-native1/control-fifo.log
f4fc20791e3fb2510f1a6aa684e8e91f5b419e6964817b2504eeffd5d8f96c2d  t120-prefix-native1/control-prefetch.log
725d222de7a3a00da7adcfaf278a9aa19b674ffc4fb7ae6b8ed26cefb662e4c4  t120-prefix-native1/unread.log
8ca273f3d09cddcdf3b05085ee20993238dee0fb1f991766b9a66de4252e8ee1  t120-prefix-native1/build.log
decb0917c7a7802c89b499bbfcc0b1bf3b9379554e14570450237538a898ba88  validate-t120-prefix.ps1
6309ffe67e4d75e1a9c45cbc702eff780ed7d98630a10ffaa836eef174d73501  t120-prefix-host-green.log
6fa136622c65ab8a69e63cef600f87e662408d7f5f2248a51d43f1625acf8db4  t120-prefix-host-build.log
```

Единственная запись reviewer — этот разрешённый report append. Код/нормы/checkboxes/tasks/Git/issues/VM/build targets не изменялись; tests/build/UI не запускались, текущий full build не трогался, commit/release authority не выдавалась.

## Append — 2026-10-21: T120 native Resume, actual clock mathematics / prefix consumer SOURCE GO

По прямому запросу пользователя применён `code-reviewer` к actual working files в `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`; Git, VM, build/tests не запускались. Область — `WasapiCaptureWorker.cpp/.h`: native QPC callback, logical B, clock/released-end checks, prefix consumer. Controller прочитан только как caller/admission context; полная двухфазная передача READY/ACK, CLOSE и гонки Stop/handler остаются отдельной независимой проверкой. Test TU меняется у main: его окончательная версия и runtime здесь не принимаются.

**Scoped actual SOURCE GO: блокирующих дефектов математической/clock части и consumer не найдено. Это не Windows compilation PASS, не runtime GO, не COM/device acceptance и не закрытие T120/#7590.** Ранее снятое требование физической точности микрофона <1 frame не возвращается: проверяется логическая stream-coordinate boundary по принятой семантике API.

Проверенная версия, SHA-256 (повторное чтение hashes до report append совпало):

```text
ecf010a71c9e5433da1fb0be7073747aeecf88634e14e88877ac490831a6a970  apps/windows/RecApp/Audio/WasapiCaptureWorker.cpp
0d5711205cc9316ec7808fdcb4840961ff720e2e4f4d3fd5a8c24fd1e506ec6c  apps/windows/RecApp/Audio/WasapiCaptureWorker.h
ed28dfbf508a05ef0adde80d274c2978b44ccf6ecc64f692c368269c5968c23a  apps/windows/RecApp/Capture/WindowsCaptureSessionController.cpp
```

### Проверенные свойства

1. `WasapiCaptureWorker.cpp:51–60`: counter100ns отклоняет отрицательный counter/неположительную QPF; quotient/remainder дают floor(counter*10M/QPF) без преждевременного целочисленного деления. Оба произведения и сумма проверены до вычисления. Консервативный отказ, если промежуточное remainder*10M не представимо, не является unsafe fallback.
2. `:250–268`: callback захватывает те же живые audioClock/format, полученные от IAudioClient capture stream. QPC before/after окружают GetPosition; обе native output позиции имеют 64-битные unsigned поля. Default/ошибка QPC или преобразования не дают успешного sample. Tolerance = ceil(10M/QPF)+1: один реальный QPC tick плюс 100ns округление, не произвольная 1ms добавка. Wall/steady фиксируются после native чтения; packet PTS не заменяются этим timestamp.
3. `:423–444`: exact result==0, диапазоны f8k..10M/r8k..192k и совпадение с текущим stream, наличие validated releasedEnd, неубывание p, before<=after и paired bracket проверяются до READY. Нижний конец saturating без unsigned underflow; верхнее сложение выполняется только после проверки max-tolerance. Истёкший исходный deadline отклоняет результат. Фактический нормативный deadline здесь 1s, не ранее обсуждавшийся пример 750ms.
4. `:437–444`: B = (p/f)*r + ((p%f)*r)/f +1 точно реализует floor(p*r/f)+1, inclusive current logical frame. (p%f)*r <= 9,999,999*192,000 < 2e12, то есть не переполняет uint64. Integral multiplication проверяется short-circuit до использования, fraction<r, поэтому max-fraction-1 не underflow; сумма/+1 защищены. B==releasedEnd допускается, B<releasedEnd отклоняется, max-подгонки нет. f<r/неделимость не вводят новый аппаратный критерий.
5. `:493–510,537–560`: packet exclusive end проверен до сложения, clock p не откатывается относительно принятого Resume sample. Старый ClockMapper также продолжает проверять packet sequence/flags/frequency/PTS; его drift envelope не изменён. releasedEnd и stream/clock state публикуются acquisition thread после успешного ReleaseBuffer и finite/format normalization. Startup discard не создаёт Resume authority; до первого нормального пакета Resume отказывает по отсутствию releasedEnd.
6. `:538–549`: prefix только microphone, только для соответствующей expected even epoch; вычитание B-deviceFrames делается лишь при B>deviceFrames, затем min с frameCount до uint32 cast. Полностью старые пакеты дают full prefix, пересекающие B — partial prefix, начинающиеся на/после B — zero prefix. Старые odd/stale acquired-epoch guards остаются. Все исходные samples копируются и проверяются normalizer до обнуления; system path prefix не получает. Normalizer получает прежний mapping.qpc100ns, то есть GetBuffer packet timestamp. Существующий partial-prefix prerequisite обнуляет до resample и не допускает boundary blend; его прежний source/runtime GO здесь не расширяется.
7. `:282,300` и header `:103–105`: native service вызывается между пакетами, не с удерживаемым COM buffer, в том числе на следующей итерации после WAIT_TIMEOUT и внутри непустой FIFO. Native clock callback остаётся на acquisition thread. Controller `:179–188` действительно использует worker receipt/expected epoch, а не прежнее прямое Resume без native clock observation; `:608–613` сохраняет downstream epoch/sequence guards. Полный handshake/CLOSE verdict этому reviewer не поручен.

### Windows compilation types — source check, не исполнение компилятора

В MSVC std::uint64_t — unsigned long long, а unsigned __int64 является тем же типом; UINT64 outputs GetPosition не требуют reinterpret_cast. LONGLONG/LARGE_INTEGER.QuadPart подходят counter100ns; HRESULT явно преобразуется в int32 и exact S_OK проверяется как 0. Optional-to-value comparisons и используемые std::chrono/CV overloads совместимы с C++17. `apps/windows/CMakeLists.txt:4–10` задаёт C++17 и NOMINMAX для Windows, поэтому новые numeric_limits::max/std::min не конфликтуют с Win32 macros. В .h optional уже доступен через AudioTypes.h. Конкретной ошибки типов/заголовков в прочитанном коде не найдено, но _WIN32 ветка требует настоящей Windows build проверки.

Первичные источники, сверенные read-only:

- https://learn.microsoft.com/en-us/cpp/c-runtime-library/standard-types?view=msvc-170
- https://learn.microsoft.com/en-us/cpp/cpp/data-type-ranges?view=msvc-170
- https://learn.microsoft.com/en-us/windows/win32/winprog/windows-data-types

### Сохраняющиеся проверки перед runtime GO

Main добавляет fault tests; здесь не выданы их execution/coverage PASS. Нужны actual results exact-source для native compile, QPC bracket boundaries/invalid ordering/overflow, S_FALSE и clock/frequency/rate refusal, logical fractional/non-frame-unit B, isolated multiplication/add/+1 overflow, B==releasedEnd и B<releasedEnd, old/full/partial/fresh packet prefix с сохранёнными PTS/count, повторный p и rollback после Resume. Synthetic clock не доказывает фактический COM callback; ранее qualified unread RED нельзя считать закрытым одним source GO. Handshake/retry/late result/Stop/exception/CLOSE проверяются отдельно. Installed/hardware/real-audio/whole-regression/release gates и T120/#7590 остаются открытыми.

Единственная запись этой проверки — данный reviewer-owned append; source, нормы, checklist markers, tasks, Git/GitHub, VM и build targets не менялись. Полный historical audit/checklist scan не повторялся.

## Append — 2026-10-21: T120 resume-native3, bounded saved Windows Debug runtime qualification

По прямому разрешению пользователя reviewer прочитал сохранённые evidence в `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t120-resume-native3`, actual runner и текущие source216. Применён `code-reviewer`; команды в VM, build/tests, Git/GitHub и UI не запускались. Это квалификация сохранённого выполнения, а не новый прогон.

**Bounded runtime GO для Windows Debug synthetic native-worker Resume/packet consumer и семи объявленных групп.** Receipt и все журналы согласованы; блокирующих противоречий в этом наборе не найдено. Это НЕ runtime acceptance настоящего IAudioClock/GetPosition callback, оборудования или всего T120/#7590.

### Source и runner bounds

- `source.sha256` SHA256 = `45c9b7e02d3103260515f7161be45af4baa01b8300d559ea666e935951b6438c`; независимая локальная проверка всех 216 текущих файлов: 216 match / 0 mismatch, без повторяющихся путей.
- `prior.sha256` = `e423d851175b3acae4e4986526b4e9f553dbe653dd7e06ca9af756389b43cf71` (native2). ВАЖНО: prior native3 уже native2, не прежний prefix63fa. Native1 не выдаётся за исполненный проход.
- `changed.json` содержит ровно `apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp`; actual manifest delta относительно native2 — только этот файл, SHA256 `a3066e2ec5c2259e88fe3ba3ead49970e363e8750d5cff685210c3a41c5b25ad`. Staged bytes совпадают с manifest/current. Единственная source delta — квалификация вызова в default lambda: `CaptureSessionTestPeer::resumeSample()` вместо unqualified `resumeSample()`. Oracles/guards/runtime logic этим не ослаблены. Worker math/consumer source и Controller после native2 не менялись.
- `validate-t120-resume.ps1` SHA256 = `6a24d2a52b4a4769314b43ae31c4005b5d49e3d1ef4c9f309f73b0e8d013b3f7`, тот же independently reviewed runner. Он требует prior216, staged source equality, current216 до build, Debug build0, семь sequential exits0 и markers, postflight216, PE equality до/после выполнения и финальный owned0.

### Receipt и actual logs

`result.json`: terminal=true, configuration=Debug, build=0, exits normalizer/async/fifo/prefetch/unread/resume-clock/full все 0, executed_groups=7, postflight=216, owned_processes=0, manifest точно совпадает с вышеуказанным. Поля failure нет. device_audio_read=false, real_network=false, installed=false. terminal=true само по себе не использовано как критерий PASS.

Windows logs прочитаны с декодированием UTF-16LE, без изменения файлов:

| Группа | Проверенный actual результат |
|---|---|
| normalizer | prefix cases160 invalid16; все прежние16 resampler combinations correct1/audio1; default binary продолжает original regressions, exit0 |
| async | журнал 0 bytes; это соответствует assertion-only CLI :1393–1397, вызывающему три async tests, а не skip. Вызов и exit0 подтверждены runner/receipt; отдельного печатного маркера нет |
| fifo | 4 combinations extracted0/1 × frames240/480, все suppressed1 |
| prefetch | 6 combinations hold_stage0/1/2 × acquired_paused0/1, все suppressed1 |
| unread | boundary1440/1200 с delayed_ack0 и boundary1440 delayed_ack1; каждый releases4/frames4/aec4/eos3/finalizer1/old_suppressed1 |
| resume-clock | rejected13/retry13/eos13/finalizer13; late retry1/stop1/late_epoch_commit0; accepted_after_deadline1/stop_after_commit1/throwing_handler1 |
| full | повторены все перечисленные FIFO/prefetch/unread/clock markers; затем `Native endpoint ID roundtrips: 2 (no capture)`; receipt full exit0 |

Fractional B (`p=boundary*8-1`, r/f=1/8) подтверждён actual consumer oracle: для boundary1200 второй unread packet содержит 240 нулевых/240 слышимых samples; prefix1440 подавляет оба старых пакета целиком; fresh packet и доверенный prefix проверяются отдельно. Delayed ACK1100ms также проходит реальные последующие packet consumer/sample assertions, а не только проверку state. Case12 f=r8000/pUINT64_MAX изолирует final +1 overflow до успешного retry; это не выдаётся за исчерпывающий extreme-math набор.

В current source `main:1432–1435` после privacy cases безусловно вызывает interruptedStartRecovery и finalAutomaticStartGate. Последний `:343` имеет 3 entry ×11 scenario =33 комбинации с generated acquisition и assertions для acceptance/отказов/финализации/recovery. Full exit0 и более поздний actual endpoint marker подтверждают прохождение этого участка по source-bound runner. Нет отдельного per-scenario runtime marker, поэтому число33 выведено из реально исполняемого bounded source loop, не из отсутствующего test XML. Native endpoint enumeration/ID roundtrip действительно выполнялся; это не activation/capture и не COM audio-clock acceptance.

`build.log` подтверждает MSBuild17.14.51, Debug outputs обоих бинарников и компиляцию CaptureFaultStateTests.cpp. Остальные common objects использованы инкрементально; этот журнал не выдаётся за clean rebuild clock TU.

### PE / terminal evidence limits

Receipt PE hashes:

```text
dc9ee7bdf79368ac4dcaa4ab1855ecfb4dbcdbb4c0dcd5c0a8bf9a041a82e738  AudioNormalizerTests.exe
0f5bb242fc31e125029902bb09a41180c254188adeba37a43fa517b06efced8a  CaptureFaultStateTests.exe
```

Runner хеширует PE после успешного build и сравнивает после всех семи групп. В прочитанном local evidence нет .exe/.xml; reviewer не читал actual guest PE и не выполнял новый hash/process query в VM. Поэтому PE/guest postflight/owned0 приняты как проверенные runner-receipt evidence, не как независимая новая guest attestation. Внешний terminal prl handle/exit main ещё собирает по сообщению пользователя; reviewer не наблюдал его лично и не утверждает отдельный outer-process exit0. Внутренний terminal receipt уже согласован со всеми семью логами; ожидание внешнего handle не выдано за новый запуск.

### Открытые границы

Privacy Resume tests используют synthetic acquisition/clock/checkpoint/finalizer; actual native GetPosition/QPC callback runtime этим не вызван. Общий full binary дополнительно упражняет generated recording/storage scenarios, но это также не реальный захват микрофона. Windows build успех не подменяет COM clock runtime. Extreme clock math покрыт частично: существующие integral multiplication overflow, fractional floor consumer и отдельный final +1 case; новые обещания полноты QPC conversions/bracket endpoint/max arithmetic/всех rates не даются. Установленное приложение, real audio/hardware/UI/manual, durable end-to-end privacy, whole-feature и release gates остаются открытыми. T120/#7590 не закрывается; markers/tasks/issues не меняются. Прежний unread RED заменён GREEN только для перечисленных synthetic scenarios на данном exact source.

Контрольные суммы прочитанных evidence (SHA256, native3):

```text
38fb8f3762555bc84d0b8454b9dd6605ff99de459e0df4c5efd94fe7165b5ab3  result.json
91f032ccb4ea0fd895d9d71b582a12f6d69ac16bbcd25a8a3055b2a302f04260  build.log
2588481974442a22d3e693f6a2ab003dd418815d1b9993b0b54138b85e6cb5f2  normalizer.log
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  async.log
2084f4e382b40ef54ff6fe75cdaabf52883302f2462bf9ba9ac609d19ac8bcad  fifo.log
f4fc20791e3fb2510f1a6aa684e8e91f5b419e6964817b2504eeffd5d8f96c2d  prefetch.log
56187898eeafbad546cc67197c231ba966c7ca3a2b0b804628852b7ef1eb86b3  unread.log
25a4dcc2dbfa957c05a6458359f0cb88eae9267c92f09ac3aa14bb6d818c1d3c  resume-clock.log
873ab7fe0f492842193468f4262664d0d559988c0d9e3586ae7c4473858fd316  full.log
```

Единственная запись reviewer — этот разрешённый append. Код/нормы/checklists/tasks/Git/GitHub/VM/build/tests не менялись и не запускались; сторонние изменения сохранены.

## Append — 2026-10-21: T120, round151 metadata evidence versus actual native clock callback

Read-only construction/evidence review по запросу пользователя; применён code-reviewer. Native4 live не опрашивался и не затрагивался. Это не повторная qualification native4/source216 и не разрешение запускать новую пробу.

**Вывод: round151 не содержит before/after QPC bracket и не подтверждает, но также не опровергает свежесть pairedQPC нового callback. Старая диагностическая оболочка пригодна для reuse; неизменённый старый бинарник не является проверкой actual production callback.**

Прочитаны PairProbe.cpp, PairStats.h (фактическое имя, не ClockPairStats), Run-One.ps1/build.cmd, связанные PacketStats.h/ServiceTiming.h и ровно раздел round151 в validation-2026-10-02.md:546–619. Внешняя директория: `/Users/yshishenya/Documents/graf-windows-followup-200/f200-clock-pair.LXFJPO/`.

- PairProbe.cpp:262 берёт packet metadata/opaque PCM pointer; :280 вызывает GetPosition до ReleaseBuffer (:287). Ни QueryPerformanceCounter, ни QueryPerformanceFrequency для bracket в старой пробе нет.
- PairStats.h:48–51 вычисляет разность current p/f и packet frames/r, paired current QPC минус packet first-frame QPC и их residual. Это не сравнение с текущим QPC вызывающего потока. ServiceTiming.h:5–9,22–28 измеряет service/hold intervals, не отдельный clock-call bracket. Максимумы timing_us не позволяют восстановить отсутствующие before/after origins.
- Round151:578–602 сохраняет один actual metadata run: 41 acquired/released, 39 принятых metadata observations, Stop0/owned0, 441ms through cleanup; terminal discontinuity на packet41. Три exported pairs имеют QPC deltas 14.6458/3.7205/0.042ms и residuals +4.6458/−6.2795/−9.958ms. По ним нельзя установить попадание pairedQPC в локальный bracket, устаревание clock value или причину различий. Никакой физический <1frame критерий этим не вводится.
- Независимые SHA256 чтения совпали с frozen round151: PairProbe.cpp `9552ea6431a5cf72c7f4a34310fe22f3bfe5780cdf9dd551e8c0ad5a5cda8878`; PairStats.h `c1eaae908376f58bdb44c526f77d32894b47ae2536af10c76ab2ceb808745711`; Run-One.ps1 `66063a5193aac0b9f0dac8898c09e34e95b9595ef1f6dca2c16bb5a7e67cd511`; local x64/PairProbe.exe `1d6be686af31e4c6f664f152230c5aa1dc5300e66127117c6432cacc7f8113f2`. PE только прочитан для hash, не исполнен и не сверялся с новым guest state. Safe JSON здесь прочитан из сохранённого validation appendix; отдельный original stdout не выдаётся за найденный.

Current source read: WasapiCaptureWorker.cpp:250–269 действительно содержит native QPF/QPCbefore→GetPosition→QPCafter/checked100ns/tolerance body; :282,300 обслуживает Resume между released packets. Guard :429–449 использует exact S_OK, bracket, frequency/rate/state/deadline и logical floor(p*r/f)+1. Header :84 содержит существующий friend, но локальную lambda из тестового TU он отдельно вызвать не может. consumePacket :530–535 копирует PCM до sink, поэтому обычный worker.start с пустым sink НЕ удовлетворяет no-audio-read. SHA256 прочитанных cpp/h: `179b33626ef1ca8f47c5599f2015c9ae0b3a231f7388c808a87099f463385415` / `79cc4a9b0cfbcef5d2442db18e9672719dac74e8f2ad86c60e33d7813779fe99`; весь source216 в этом исследовании не пересчитывался.

### Минимальный следующий шаг — предложение, не выполненная правка/проверка

1. Сохранить старую visible Start/Stop/RAII/cancel/deadline/parent watchdog оболочку, один explicit control case, отсутствие PCM dereference/copy/save и отсутствие device-ID/absolute-origin exports. Для соответствия current native profile не наследовать незаметно старый 100ms Initialize: PairProbe.cpp:188 использует 1,000,000100ns, production :211 — 100,000100ns (10ms). Не добавлять MMCSS/44100 sweep.
2. Для actual production primitive coverage минимально вынести неизменённое тело :250–269 в один закрытый Windows helper; production lambda делегирует ему, test-only friend вызывает ту же compiled implementation на живом IAudioClock, полученном от того же diagnostic IAudioClient/GetFrequency/mix format. Не делать копию арифметики или новый public API. Это только construction candidate для отдельного source gate. Без такой связки новая bracket-версия внешнего PairProbe докажет лишь отдельный API experiment, не actual callback.
3. Все GetBuffer metadata acquisitions немедленно ReleaseBuffer; PCM pointer остаётся opaque. Callback sample берётся только без удерживаемого buffer и после повторной cancel/deadline проверки, как в production service locations. Существующие native/flags/cleanup faults не очищаются ради продолжения. Не подделывать releasedEnd/epoch/READY, чтобы объявить полноценный Resume PASS.
4. Bounded receipt должен различать attempts/S_OK/other HRESULT/conversion failure/bracket failure и фактически принятое число samples. Нужны ненулевой явно заданный охват, корректный порядок before<=after и тот же production tolerance без ms-loosening, checked logical B и metadata consistency; только bounded relative margins/durations/counts, без PCM/absolute QPC/positions/endpoint IDs. Все S_OK observations учитываются, failures не исчезают при фильтрации. Invalid/empty run — не PASS. Сохранить source/helper hashes и PE binding, release count/Stop/through-cleanup deadline/owned0.

Проверка живого примитива даже после успеха не доказывает native two-phase Resume/ACK/CLOSE, packet-prefix privacy end-to-end, physical hardware accuracy, весь T120 или release/install acceptance. Потребуются отдельные source review и явное разрешение реальной bounded активации микрофонного stream. В этой работе не запускались VM/build/tests/probe/audio/Git; единственная запись — данный разрешённый reviewer-owned append.

## Append — 2026-10-21: T120 protected-privacy-flow, qualified as-is RED and bounded test-only source GO

По запросу пользователя применён code-reviewer. Прочитаны saved as-is receipt/build/privacy-flow logs, actual runner, all generatedProducer callers, полный узкий diff относительно физической копии с проверенным baseline hash и current worker/controller/normalizer consumers. VM/build/tests/Git/GitHub не запускались; source, нормы и markers не менялись. Единственная запись reviewer — данный разрешённый append. Requirements GO Descartes предоставлен пользователем; широкая requirements/checklist проверка здесь не повторяется.

**SOURCE GO для запуска только bounded двух-durable-segments metadata path. Конкретных compile/flow/lifetime/overflow blockers в прочитанном изменении не найдено. Это не runtime GREEN кандидата, не fresh-after-Resume audio proof и не acceptance всего T120.**

### Saved RED qualification

`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t120-protected-as-is1/result.json`: terminal=true, Debug, build0, test_argument=--protected-privacy-flow, test_exit3, failure=TEST, postflight216, owned_processes0; device_audio_read/real_network/installed=false. Manifest SHA256 `59ad0f4787682aa19fb7b30b5aa6297ad5b17dc6302b49a46fe8d1b29a34569c`; prior bytes равны source bytes, changed.json пуст. Build log подтверждает компиляцию тестового TU и output PE; это не clean rebuild всех common TU.

UTF16LE privacy-flow.log содержит baseline0/empty_proxy16, V5_CASE0 start, frames_3000 elapsed_ms19919, затем exact assertion ожидания `!capture.privacyPending() && ...state == SessionState::recording` на frozen line6248. Нет markers двух закрытых durable segments/cold_read_verified. Это настоящий failing run, не skip, не build failure и не GREEN. PowerShell NativeCommandError обрамляет stderr; конкретный failure подтверждён последующей строкой CRT assertion и exit3.

Runner SHA256 `474ab3a491622217ff0c54eaf7a979a6681482ed2006cb5e82853d8b4391f17f`: до build проверяет source216, хеширует PE, выполняет настоящий CLI, после него проверяет source216/неизменность PE; test_exit!=0 вызывает TEST прежде положительных markers, finally сохраняет terminal/owned. Receipt PE `0f823aa46af1d2f95eae7b3ece4162f69632af24336aa7ee9d6b6a103aa90fcc`. Reviewer не читал новый guest PE/process state и не наблюдал внешний runner exit; эти части приняты как source-checked runner receipt, не как независимая VM attestation.

Контрольные суммы RED evidence: result.json `17964998411829bb71e5ac9fbe9132a9fbfc047ec2d5bf387e9e2aa927758ded`; privacy-flow.log `a758e5537c7191c55b3569358171c68043a6b6017a16f2175d0dbfe4d601b2f7`; build.log `0394e201b0133d24eb7df0ea2b911ff1a7ad2b3a14436f21cb5982178b8345fc`.

Cause, source-supported: frozen generatedProducer вызывает callback напрямую, минуя consumePacket и заполнение worker releasedEnd/frequency/rate; после последнего пакета только спит, не вызывает servicePrivacyResume. Controller processPrivacy (:179–195) теперь требует настоящего worker mailbox. Такой fixture не может удовлетворить Resume независимо от ожидания UI. Это несовместимость тестового источника с новым worker prerequisite; данный RED сам по себе не доказывает production Resume defect.

### Exact candidate and scope

- Current test: `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`, SHA256 `11573c62b0108200855e5ee1b336d971db4a57fb800f222caf19b36b7bd7a6e7`.
- Baseline test SHA256 из RED manifest `fc85c594db6e82a7660b264a0dd58ef6cce4a74343733d73a66d229b5f4e655e` независимо совпал с physical `BASE/diag15-native-delays/apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`. Обычный diff этих файлов прочитан полностью: только AudioNormalizer include, три peer delegates, opt-in producer path и один privacyFlow microphone caller.
- Current216 относительно RED: 215 match, ровно этот test delta. `BASE/t120-protected-green1/source.sha256` hash `d995b9cfb313fd651d22c7c61b548cbefb148e787e82824bcfb12a8132a81e5b`: все216 unique/current match; staged test byte-equal current, changed.json содержит только этот путь. Production не изменён относительно RED в проверенном 216-file наборе. Кандидат проверен как source, не как уже выполненный GREEN.

### Construction checks

1. TestTU :10 включает полный AudioNormalizer; :648–665 existing friend только возвращает настоящий microphone worker, вызывает servicePrivacyResume с synthetic clock value и consumePacket с synthetic release. Не меняет epoch/releasedEnd/frequency/mailbox status/accepted serial; последние возникают из реального consumePacket/service/controller flow. Прежний device-ready.store(true) сохранён как synthetic acquisition readiness, не подмена Resume mailbox READY/ACK.
2. :3861–3895 добавляет последний defaultfalse privacyPackets. Просмотрены все16 invocation sites: 10 коротких producer calls (5 render/mic пар, frameCount100) и 6 frameCount3000 calls (3 пары). Только :6209 может включить флаг через privacyFlow; :6208 render и deferred/scheduled pairs остаются false. Все actual calls protectedRecordingVerticalAndRestart проверены: privacyFlow=true только existing CLI :6933–6936. Late-device delay, direct callback branch, sleeps/backpressure/emit semantics и прежние assertions не удалены. ClockMapper/AudioNormalizer constructors у false branch не запускают нормализацию или COM.
3. Для privacy=true worker reference получается внутри его generated device thread, не пересекает время жизни controller; реальные Stop/completion/join fences остаются. Mapper/normalizer живут весь producer run. Sample buffer остаётся жив до синхронного consumePacket; production копирует samples до возврата. Новый consumePacket result assert исполняется и в Release: в начале TU NDEBUG явно undef.
4. :651–664 использует 48kHz mono float32, packets480, clock f384000, qpc100ns=i*100000, deviceFrames=i*480, current clock p=((i+1)*480-1)*8, exact synthetic S_OK и успешный release count480. ClockMapper видит непрерывные/монотонные metadata без startup-discontinuity; normalizer проходит настоящий finite/native48k lossless путь, prefix/epoch берёт worker из существующего controller binding. Packet QPC/PTS/count не подменяются Resume sample timestamp.
5. Fixed current bounds i=0..2999, nextFrame<=3000: максимум packet QPC299900000, deviceEnd1440000, Resume p11519999, все произведения/casts безопасны. После последнего пакета packet-clock p11519992; Resume p11519999 не идёт назад и даёт B=floor(p/8)+1=1440000==actual releasedEnd. У nextFrame0 clock value0 не переполняется; до первого пакета production guard по отсутствующему releasedEnd сохраняется, не обходится. Обобщённый UINT64 frameCount этими тестовыми helper не обещан.
6. :3873,3877,3890 обслуживает настоящий mailbox до пакета, при emit/backpressure ожидании и после всего потока. Ключевой final loop нужен именно этому smoke: все3000 packets уже получены до Resume. Worker service сам делает READY, Controller applyPrivacyBoundary сам меняет epoch, resumeMicrophone сам делает ACK; тест только даёт synthetic clock sample (1000/1000/1000 bracket/tolerance1 + actual wall/steady now). Это не реальное COM/QPC freshness evidence.
7. :6258–6287 сохраняет Pause→3000 generated10ms blocks→Resume→Pause→Stop без новых samples после Resume. :6396–6408 проверяет cold metadata двух silenced segments с двумя end fields; :6418–6426 оставляет sealedNormal/integrity/duration30000/decodedFrames>0. Stop/EOS/finalization/queue adoption/cold inspect и exact idle guard :6935 не ослаблены. Тест не проверяет свежий слышимый suffix после Resume и не выдаётся за это.

### Последующие границы

Следующий минимальный audio-proof slice отдельно: deterministic generated microphone marker, отличный от continuous render; hold не менее двух старых mic packets до acquisition/epoch, настоящий Resume mailbox/consumePacket, затем явно выпущенный новый post-boundary marker. После EOS/finalizer читать настоящий cold canonical PCM через существующий protected reader и проверять нулевой вклад старого mic плюс ненулевой свежий marker при сохранённом render/count/PTS. Для точных численных assertions использовать canonical, а не точное равенство lossy AAC; существующий AAC cold integrity/decode остаётся. Не переносить эти новые требования в текущий smoke gate и не объявлять их уже выполненными.

Перед bounded runtime GREEN нужны actual build0/test0, оба существующих markers, exact candidate source/PE bounds, postflight216/owned0 и unchanged idle. Native COM clock, real audio/hardware, installed/manual, все остальные T120 scenarios и release acceptance остаются открытыми. Никакие issues/tasks/checkboxes не закрыты.

## Append — 2026-10-21: bounded Ponytail review, protected-privacy-flow test-only delta

По прямому запросу пользователя reviewer полностью прочитал `ponytail-review/SKILL.md` установленного plugin 4.9.0 и применил только complexity pass после correctness GO выше. Scope — все новые/изменённые строки одного NativeCaptureStorageIntegrationTests.cpp относительно verified baseline `fc85c594db6e82a7660b264a0dd58ef6cce4a74343733d73a66d229b5f4e655e`; candidate повторно проверен: `11573c62b0108200855e5ee1b336d971db4a57fb800f222caf19b36b7bd7a6e7`, unchanged. Physical unified diff считает +41/-8, net+33; проверены все hunks независимо от описания «38 новых строк». Это не новый source delta.

Удаляемого переусложнения не найдено. Три peer delegates (:648–665) обеспечивают private access и reuse настоящих worker packet/mailbox путей без нового public API; их слияние либо инлайнинг с переносом генератора в friend не даёт нужного сокращения и расширяет diff. Последний defaultfalse параметр (:3862) нужен для сохранения остальных producer callers, не speculative option. Состояния ClockMapper/AudioNormalizer обязаны сохраняться между пакетами; дополнительная optional/lazy обёртка здесь только увеличит код. Три места обслуживания Resume (:3873,3877,3890) покрывают разные состояния acquisition thread: свободную выдачу, ожидание emit/backpressure и окончание выдачи; не предлагаются к удалению. Existing smoke/assert/release-count, epoch read, finite/normalization и bounded metadata assertions остаются целиком. Новых зависимостей/форматов/архитектурных слоёв нет; косметическое уплотнение строк не считается полезным cut.

Ponytail verdict: **Lean already. Ship.** Здесь Ship означает отсутствие complexity objections к уже ограниченному SOURCE GO, не runtime/release approval. `net: -0 lines possible.` Нет предложенных изменений замороженного кандидата.

Green1 по сообщению пользователя уже запущен; reviewer не открывал его runtime receipt/logs и не утверждает результат. VM/build/tests/Git/код/нормы/checklists не затрагивались; запись только в данном reviewer-owned report. Все acceptance limits предыдущего append сохраняются.

## Append — 2026-10-21: protected-green1 saved runtime qualification

После предыдущего Ponytail pass пользователь сообщил terminal wrapper exit0 (main exec96144) и отдельно поручил проверку сохранённых evidence. Reviewer read-only прочитал полный runner, result.json и полные UTF16LE build/privacy-flow logs из `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t120-protected-green1`; ничего в VM не выполнял. **Bounded runtime GO: Debug --protected-privacy-flow действительно прошёл путь двух durable privacy metadata segments и cold verification на exact source.** Это заменяет as-is RED только для данного исправленного synthetic smoke, не для всего T120.

Независимая проверка current source216: 216 unique /216 match /0 mismatch. Manifest SHA256 `d995b9cfb313fd651d22c7c61b548cbefb148e787e82824bcfb12a8132a81e5b`; prior `59ad0f4787682aa19fb7b30b5aa6297ad5b17dc6302b49a46fe8d1b29a34569c` byte-equal as-is RED source manifest. Actual delta ровно один test TU: baseline `fc85c594db6e82a7660b264a0dd58ef6cce4a74343733d73a66d229b5f4e655e` → current/staged `11573c62b0108200855e5ee1b336d971db4a57fb800f222caf19b36b7bd7a6e7`. changed.json согласован, staged bytes равны current. Нет новых production изменений в этом manifest scope.

Receipt: terminal=true, configuration Debug, build0, test_exit0, postflight216, owned_processes0; failure отсутствует, test_argument --protected-privacy-flow. Runner SHA256 `474ab3a491622217ff0c54eaf7a979a6681482ed2006cb5e82853d8b4391f17f` совпадает с ранее прочитанным RED runner; он проверяет pre/post source216, staged equality, pre/post PE equality, exit0 и оба required markers. Build log подтверждает MSBuild17.14.51, компиляцию NativeCaptureStorageIntegrationTests.cpp и output target; не утверждается clean rebuild всех common objects.

Actual log: `baseline=0 empty_proxy=16`, V5_CASE0 start, frames_3000 elapsed_ms18517, finalized, cold_read, `PRIVACY_FLOW two_durable_segments_closed=1`, cold_read_verified, done. CRT assertion из RED отсутствует. PowerShell NativeCommandError wrapper вокруг первого stderr diagnostic не является новым failed assertion: сохранены последующие terminal markers, test_exit0 и отсутствие failure. Никакой CTest/XML не использовался: это прямой CLI invocation, не skipped CTest case. Source-bound CLI :6933–6936 безусловно вызывает данный flow и после возврата проверяет exact idleOwnedBytes; exit0 доказывает прохождение этого assert. Full log done соответствует :6795 после cold restart/adoption assertions и released(restarted), а не раннему служебному marker.

Source/runtime scope: настоящие generated consumePacket/normalization, worker Resume mailbox, Controller epoch/ACK, durable OPEN/CLOSE/Stop closure, EOS/finalizer, adoption и cold inspect в этом пути сохранены. Cold checks :6406–6408 требуют два segmentId, два endMonotonicMs и два silenced treatments; :6418–6426 требуют sealedNormal, valid integrity, duration30000, decodedFrames>0. Успешный Resume и последующая вторая Pause достигнуты до этих markers. Все3000 generated10ms blocks уже выданы до Resume; новых post-Resume samples нет. Поэтому runtime GO НЕ доказывает слышимый fresh suffix/подавление unread packets именно на durable audio output, настоящий COM GetPosition/QPC callback, реальный микрофон/AEC, hardware/installed/manual или whole T120/release acceptance. Device_audio_read=false/real_network=false/installed=false соответствует synthetic device body и выбранному normal offline scenario, не отсутствию чтения generated samples.

PE по receipt `dac446a713678ed2cfc98df2cfe85cd2a8c33aa452e036da6d015d4a13dc6850`; runner хеширует его после build и проверяет неизменность после исполнения. В local saved evidence actual .exe нет; reviewer не выполнял guest Get-FileHash/process query, main собирает отдельную guest PE проверку. Внешний terminal wrapper exit0 сообщён main, не наблюдался reviewer напрямую. Это предел независимой saved evidence qualification, не скрытая новая VM attestation.

SHA256 сохранённых evidence:

```text
d1f37b29ecfa9b93f634dd12d4df1b1f17477c2a74c20055d13bbb1f80ef8e5d  result.json
526f12ac32966c6072a3545bd9e16c455349fc6986c78a4933d8f8678c871aac  privacy-flow.log
0394e201b0133d24eb7df0ea2b911ff1a7ad2b3a14436f21cb5982178b8345fc  build.log
```

Ponytail verdict остаётся без cuts; test/source не изменены ради GREEN. Предыдущий RED evidence сохранён. Никакие norms/checklists/tasks/issues не менялись и T120 не закрывался; единственная запись reviewer — данный append.

## Append — 2026-10-21: actual clock primitive, pre-code construction review

По новому запросу пользователя полностью прочитан code-reviewer skill и bounded current worker/header/CMake плюс относящиеся к конструкции места старой PairProbe/Run-One/build/PacketStats. **Construction GO для предложенного минимального private extraction и отдельной metadata-only пробы при условиях ниже; это не actual source/build/runtime GO и не разрешение reviewer запускать COM/VM.** Requirements gate Descartes выполняет отдельно. Существующий source ещё без этого patch: cpp `179b33626ef1ca8f47c5599f2015c9ae0b3a231f7388c808a87099f463385415`, h `79cc4a9b0cfbcef5d2442db18e9672719dac74e8f2ad86c60e33d7813779fe99`.

### Private extraction and compile/link boundary

- Global `struct IAudioClock;` вне namespace graf::windows и только под _WIN32 совместим с использованием `::IAudioClock&`; объявление private static метода должно идти после ResumeClockSample и также под _WIN32. Definition остаётся в Windows части .cpp. Native callable делегирует через настоящий объект, например `*audioClock.Get()`, с исходными audioClockFrequency/mix sample rate. Existing friend в namespace graf::windows может вызвать private static и вернуть auto без public proof/API или хранения COM interface в worker mailbox.
- Тело :250–269 переносится без изменения QPF→QPCbefore→GetPosition→QPCafter→time/conversion/tolerance semantics; servicePrivacyResume :429–449 не изменяется. Не называть параметр stream frequency просто `frequency`, если переносится существующий local `LARGE_INTEGER frequency{}`: это redeclaration, не механическое извлечение. Достаточно назвать параметр streamFrequency, сохранив независимую QPC frequency. Не добавлять новое noexcept, другой результат ошибки/округление/раннюю фильтрацию S_FALSE в рамках extraction.
- External TU определяет только свой существующий friend pattern и линкует actual Debug common implementation. Старый build.cmd с /MT /O2 и старым ClockMapper.cpp не подходит без адаптации: CRT/_DEBUG/_ITERATOR_DEBUG_LEVEL должны совпасть с actual Debug common build (обычно /MDd, не /MT); тот же compiler/architecture/C++17/NOMINMAX. `graf_windows_common` в CMake :128 — OBJECT target; actual MSVC .lib/object artifact нужно подтвердить build evidence, не предполагать переносимый static-library target. Не линковать одновременно старый замороженный mapper/worker source вместо symbols из current library, не использовать /FORCE:MULTIPLE или обход CRT mismatch. Build-only отдельно подтверждает resolution вспомогательных native symbols; исходная конструкция этого сама не доказывает.
- Freeze должен включать current216 (только два worker файла меняются внутри scope), external probe/runner/build source, hash actual common artifact и final PE. После build требуется actual source review; никакого auto-start capture в build.cmd/summary tests. Старый build.cmd сам исполнял unit binaries; его нельзя бездумно выдавать за build-only.

### Acquisition/order and result oracle

1. Single 48000 shared EVENTCALLBACK/10ms control, без изменения формата через resampling flags, без MMCSS/44100 branches. IAudioClock/GetFrequency/capture/mix получаются от одного IAudioClient, COM lifetime на одном probe worker до Stop/release. Retain visible Start/Stop/Esc/cancel, whole-case5s watchdog и parent12s, reserve cleanup time; убийство только собственного disposable process при overrun, без detached thread/COM cross-thread Stop. Probe требует отдельного разрешения на реальную активацию stream даже при opaque PCM.
2. Каждый успешно acquired GetBuffer немедленно получает ровно один ReleaseBuffer; buffer-empty не считается acquisition. Сохранённые position/count/flags — только scalar metadata; PCM pointer не читается/копируется/логируется. При failed release/известном invalid count или flags/отмене/deadline после release — stop/refusal без следующего native clock read. Первый разрешённый startup discontinuity допускается только по unchanged mapper discardStartup rule, не как normal valid sample. Не продолжать старый canContinueMetadataAfter обход (:302–311): предложение требует остановки на metadata/mapper faults.
3. После release и проверок вызывается actual helper. Он только читает sample: численные bracket guards живут в servicePrivacyResume, поэтому probe обязан проверять exact result0, frequency/rate context, before<=after, tolerance!=0, safe upper addition и тот же saturating lower/upper bracket predicate. Нужны monotonic metadata/clock checks и неизменённый current ClockMapper, без p==packet-position-at-other-time требования. Если считается logical B, только existing checked floor(p*r/f)+1 и known released metadata comparison; не создавать/заполнять product epoch/releasedEnd/READY/ACK ради пробы. Diagnostic oracle не является новой product authority.
4. Minimum16 учитывает только normal accepted samples после всех guards, не acquired/startup/S_FALSE/raw call count; cap65 относится ко всем acquired packets. Нужны заранее объявленный normal stop criterion и итог: valid>=16, no sticky native/conversion/bracket/mapper/release/Stop error, успешная cleanup в срок, owned0, bound source/PE. Достижение16 не стирает поздний fault и не превращает user cancel/deadline/watchdog в PASS. При fault после16 результат остаётся отказом; при малом числе samples — insufficient evidence. Старый Run-One :40–49 проверял privacy/cleanup, но не такую положительную clock oracle; старого exit0 недостаточно.
5. Output только bounded counts/relative margins/durations, с проверкой signed conversion/clipping до casts, без absolute QPC/p/device IDs/PCM и неограниченного per-packet log. S_FALSE отдельно, когда возвращён именно1; result=-1 у unchanged helper не позволяет однозначно различить QPF/QPC/конверсию и native error, поэтому использовать честную общую категорию unusable sample, не выдумывать точную conversion cause. Все attempts/failures учитываются, ошибка сохраняется до terminal receipt. Удобное малое byte budget допустимо менять только явно и с SummaryTests, а не молча обрезать failures.

### Acceptance scope

Предложение проверяет реально вызванный production read primitive плюс observed numeric bracket на данном bounded stream; это не весь production acquisition loop и не mailbox Resume/ACK/CLOSE integration. Не подтверждает fresh-after-Resume audio, physical <1frame, оборудование, installed/manual, все rates/hosts и T120 closeout. Дополнительных product answers или public API для этой конструкции не обнаружено; конкретные future source/build gates выше обязательны. Сейчас reviewer не правил два worker файла/нормы/runner, не делал Git/VM/build/tests/audio; единственная запись — данный разрешённый append.

## Append — 2026-10-21: actual native1 helper/probe/build/run source gate — REQUEST CHANGES

По запросу пользователя полностью прочитан code-reviewer skill, actual helper/header, полный external ClockProbe.cpp, build.cmd, Build-Probe.ps1 и появившийся Run-Probe.ps1. Ничего не исполнялось: ни VM, ни compiler/child tests, ни COM/audio. Единственная запись — данный reviewer-owned append. Snapshot обновлён после добавления --self-check и Process::new для pure children; первоначальные промежуточные bytes не выдаются за финальные.

Helper-only SOURCE GO: private global-forward IAudioClock* extraction корректно ограничен _WIN32, declaration после Sample; actual native lambda вызывает тот же out-of-line static method. Body .cpp:68–87 механически соответствует старому :250–269 (исходный cpp из native4 сравнен обычным diff); stream frequency и QPC frequency не смешаны. Borrowed pointer фактических callers nonnull от successful GetService, COM остаётся жив на acquisition thread; новая null-authority/public API не создаётся. Consumer/service guards не менялись. Это source check, не выполненная Windows compile/runtime acceptance.

Независимо проверен stage native1: source216 `396766d44cf35e929a2abe91a2f345f347f2adef140490f93174053d010f5b2d`, 216 unique/current match; prior `d995b9cfb313fd651d22c7c61b548cbefb148e787e82824bcfb12a8132a81e5b`. Ровно два staged/current byte-equal worker paths: cpp `65ddf184bbb884047f26b3f59176d47180f1f9f6ecdab1752d582a090891a9d4`; h `061f3a1e36067e86522856cac93c2e8cedfcaeb834130d4854d250f827bf35c2`. Consumer test из green1 не изменён.

### Три конкретных замечания, препятствующих общему GO

1. **[Build blocker] build.cmd:6 links insufficient three objects.** WasapiCaptureWorker.cpp:616 вызывает non-inline `WasapiEndpointEnumerator::isAllowedMicrophone`; определение только в WasapiEndpointEnumerator.cpp:122–125. Его нет в WasapiCaptureWorker/AudioNormalizer/ClockMapper.obj и перечисленных системных libraries. Debug link /DEBUG без явно доказанного удаления соответствующего кода не разрешает рассчитывать на отбрасывание остальных функций worker.obj. Минимально добавить actual Debug WasapiEndpointEnumerator.obj и его hash до/после в Build receipt; не писать fake implementation или /FORCE. Это source-proven unresolved dependency, не наблюдавшийся LNK2019: reviewer сборку не запускал. Сам non-device build harness по execution scope корректен, но как составленный успешную линковку не обеспечивает.
2. **[P2 flow] ClockProbe.cpp:182 читает clock до known metadata validation :184 и mapper flags check :188–191.** При count0/count>4800/device-end overflow лишний native GetPosition уже выполнен, затем return до ClockStats.observe; такой actual native read даже не отражается в reads/read_hr. При timestampError/unknown flags/недопустимом discontinuity тоже делается лишний clock call после уже доступного признака отказа. Минимально после release/cancel/deadline и ДО helper проверить count/end overflow/known invalid flags с сохранением единственного допуска first startup discontinuity; затем каждый реально совершённый helper call сразу передать в ClockStats.observe. Unchanged ClockMapper всё равно остаётся окончательным metadata guard. Это требуется обещанием no filtered native calls/stop on known faults, не ослаблением guards.
3. **[P2 false acceptance edge] ClockProbe.cpp:195–196 даёт packet_limit при packets65 даже если вышли из-за deadline.** Реальный путь: 65-й GetBuffer/ReleaseBuffer возвращается после soft deadline, :181 прерывает inner loop без clock read; финальный else-if packets65 заменяет deadline на packet_limit. При уже64valid Run-Probe :49–52 может принять это за measurement success. Аналогично 65-й GetPosition может вернуться за soft deadline. Минимально после cancelled поставить явный deadline check перед packet_limit. Добавить чистый self-check такой terminal-reason precedence без COM; 16 предшествующих успехов не отменяют deadline. UI5s watchdog не устраняет окно soft deadline=hardDeadline-200ms.

### Что уже корректно, не требует переделки

- Opaque GetBuffer pointer нигде не читается; ReleaseBuffer идёт немедленно, до нового helper. Failed release останавливает пробу. Stop destructor теперь сохраняет прежний end/native reason, stopHr отдельно; INT_PTR casts соответствуют x64.
- SelfCheck :68–84 только synthetic ClockStats values; entry :293 --self-check возвращается до COM/UI/device, --unsupported возвращает64; live path тоже вызывает selfCheck до активации. Это разумная pure build guard, не runtime proof native helper. Не исчерпывающая extreme math matrix.
- Single48000/stereo float/native10ms, тот же IAudioClient/capture/clock/frequency, no MMCSS/44100/continuation, startup discard исключён из validPackets, packet cap65, UI/Stop/Esc/5s + owned-parent12s сохранены. Result только counters/relative margins/duration; signed-cast риска при используемых unsigned differences не найдено.
- Появившийся Run-Probe действительно устраняет прежний отсутствующий positive oracle: :49–53 требует packet_limit, valid_packets>=16, reads>=16 и zero all guards/nativeHr; cleanup отдельно, обычный отказ сохраняет clock-summary/run-result и wrapper1. Поэтому отсутствие minimum16 в самом probe больше НЕ отдельный blocker при обязательном использовании этого runner. Это, однако, не лечит пункт3 выше.
- Build-Probe current :47–56 использует Process::new с 5s deadline для --self-check0/--unsupported64; разрешённые входы возвращаются до любой COM активации. Source216/inputs/objects/PE до/после и owned0 предусмотрены. Run-Probe проверяет build receipt, те же inputs/objects/PE, source216, свой runner hash и owned0; source review не заменяет будущий saved build receipt.

Latest inspected SHA256 external files in `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/native-clock.r6Lltd/`:

```text
9517759750ef99e5d9c08c60175d0d14989b800ea01ff0a0749b428cbd3e44c4  ClockProbe.cpp
9a642e2ba552fe0fe83997c4ff4822d06f15c57f5c7933beff788206ed7d874e  build.cmd
c2432def727367f950d10c6b01017f279400359ba1a53245003bcb4d1d373fa8  Build-Probe.ps1
dbfc729a50eb320b5dcc0710d86a7ac7a7a09cf211b17eef70b82e93056db3a1  Run-Probe.ps1
```

**Итог: helper SOURCE GO; общий native probe/build/run SOURCE gate REQUEST CHANGES по трём пунктам выше.** После точечной коррекции нужен delta source review и actual non-device build/pure-check receipt до отдельного launch approval. Не предлагались новые нормы/product questions, не менялся acceptance scope; real COM/fresh-after-Resume audio/hardware/installed/whole T120 остаются непринятыми. Код, runner, нормы, Git и VM reviewer не менял.

## Append — 2026-10-21: native-clock delta review, three findings resolved — SOURCE GO

По запросу пользователя применён code-reviewer: перечитан полный skill, актуальные изменённые ClockProbe/build/Build-Probe участки, полный Run-Probe, связь добавленного Enumerator object с его настоящим implementation. Review ограничен тремя предыдущими findings и сохранностью harness; VM/build/pure tests/COM не исполнялись. **Все три source замечания исправлены; новых blocking defects в этой bounded delta не найдено. SOURCE GO для рассмотренного helper/probe/harness, следующий этап — actual non-device build и два pure child checks.** Это не утверждение успешной компиляции или разрешение пропустить build receipt перед отдельным actual launch gate.

1. build.cmd:6 теперь линкует actual Debug WasapiEndpointEnumerator.obj вместе с worker/normalizer/mapper. Это настоящий provider non-inline isAllowedMicrophone, без заглушки или /FORCE. Build-Probe.ps1:37–38 включает все четыре объекта, :58 проверяет их после children; Run-Probe.ps1:18 автоматически проверяет каждый объект receipt до/после. Прочитанный Enumerator implementation не вводит static device activation: COM calls находятся в вызываемом snapshot, а не global initializer. Конкретное успешное разрешение всех symbols всё равно подтверждается только будущим compiler/linker result.
2. ClockProbe.cpp:186–197 теперь сначала освобождает acquired buffer, проверяет release/cancel/deadline, count/end overflow и flags, лишь затем вызывает native helper. Unknown flags/timestampError/non-startup discontinuity возвращают отказ без clock call. Единственный разрешённый first flags==dataDiscontinuity проходит startup discard rule. Каждый реально выполненный helper непосредственно передаётся ClockStats.observe; прежнего пути «read, затем invalid count return без учёта read» больше нет. ClockMapper guard и отказ после него сохранены.
3. ClockProbe.cpp:69–76 вводит общий terminalReason с приоритетом cancel→deadline→packet_limit и четыре pure проверки: cancel+expired+65, expired+65, normal65, short64. :205 применяет именно этот helper при выходе из циклов, поэтому soft-deadline на 65-м пакете больше не принимается за packet_limit; ранние fault returns его не вызывают и не маскируются. Явный <cstring> добавлен. Проверки source-read, не выполнены reviewer.

Run-Probe не изменён: minimum16 normal valid packets +reads>=16, zero clock/mapper/native errors, end packet_limit, отдельная cleanup acceptance, сохранение clock-summary при обычном отказе, owned-parent12s и source/objects/PE checks остаются. Build-Probe запускает только --self-check и --unsupported через Process::new/5s own-child watchdog; оба соответствующих entry paths расположены до COM/UI/device activation. Положительный exit executable сам по себе по-прежнему не measurement PASS: обязательный runner сохраняет этот guard.

Независимо повторён source216 check: 216 unique /216 match /0 mismatch. Native1 manifest и оба production worker hashes unchanged; previous helper-only SOURCE GO сохраняется. Final прочитанные hashes:

```text
396766d44cf35e929a2abe91a2f345f347f2adef140490f93174053d010f5b2d  source216 manifest
65ddf184bbb884047f26b3f59176d47180f1f9f6ecdab1752d582a090891a9d4  WasapiCaptureWorker.cpp
061f3a1e36067e86522856cac93c2e8cedfcaeb834130d4854d250f827bf35c2  WasapiCaptureWorker.h
298cdcafff666a602d904c8563cd9ee4d9595c3878e645490ccdf66fb28f8374  ClockProbe.cpp
906985751ed73a46ac7b69e07fe43d028fbf30e65a3ed31a8366478573e2e3dc  build.cmd
755aa27dd46be26673070d655c099b0da7641b2585807d20805eaa332f5d7084  Build-Probe.ps1
dbfc729a50eb320b5dcc0710d86a7ac7a7a09cf211b17eef70b82e93056db3a1  Run-Probe.ps1
```

Только reviewer-owned append; source/нормы/tasks/checklists/Git/VM не менялись. Requirements gate Descartes этим не подменён. Actual build0/link/pure checks, receipt/source/PE binding и отдельное согласование запуска остаются до native activation. Никакого runtime COM bracket, fresh-after-Resume audio, hardware/installed/full T120 acceptance этим SOURCE GO не заявляется.

## Append — 2026-10-21: clock-native1 saved non-device build qualification and conditional single-launch GO

По прямому запросу пользователя применён code-reviewer, прочитаны полный skill, build-result.json и оба полных UTF16LE native-build/probe-build logs из `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t120-clock-native1`. Повторно сверены external inputs/Run-Probe hashes и current216. Ни VM, ни build/tests/probe reviewer не запускал. **Saved non-device build qualification GO: build/link/pure-check receipt согласован с reviewed harness и logs. Условный GO ровно на один bounded native запуск через неизменённый Run-Probe после разблокировки и свежего визуального/preflight контроля; сейчас locked desktop не разрешает запуск.**

Receipt terminal=true, Debug, native_build0, probe_build0, pure_checks2, postflight216, owned_processes0; failure отсутствует; device_started=false/device_audio_read=false. Build log подтверждает MSBuild17.14.51, actual WasapiCaptureWorker.cpp compilation и common target; также инкрементально пересобраны CaptureReasonMapping.cpp/WindowsCaptureSessionController.cpp. Это не дополнительный source delta: independently current216 match сохраняется. Probe-build log подтверждает VS2022 environment x64, компиляцию ClockProbe.cpp; ошибок линковки в полном журнале нет, probe_build0 и subsequent checks подтверждают создание используемого PE. Это incremental Debug build, не clean rebuild всех common objects.

Source manifest `396766d44cf35e929a2abe91a2f345f347f2adef140490f93174053d010f5b2d`: независимо 216 unique/216 current match/0 mismatch. Все три build inputs receipt byte hashes равны текущим reviewed files: ClockProbe.cpp `298cdcafff666a602d904c8563cd9ee4d9595c3878e645490ccdf66fb28f8374`; build.cmd `906985751ed73a46ac7b69e07fe43d028fbf30e65a3ed31a8366478573e2e3dc`; Build-Probe.ps1 `755aa27dd46be26673070d655c099b0da7641b2585807d20805eaa332f5d7084`. Run-Probe.ps1 отдельно сверён с reviewed `dbfc729a50eb320b5dcc0710d86a7ac7a7a09cf211b17eef70b82e93056db3a1`.

Pure checks квалифицированы по source-checked Build-Probe flow/receipt: настоящий child --self-check обязан дать0, следующий --unsupported64, каждый с собственным5s watchdog; только после обоих harness выставляет pure_checks2. Отдельных child stdout/result files нет, поэтому per-child output не выдуман. Оба entry paths до COM/UI/device, и в прочитанных четырёх linked objects source нет диагностического auto-activation initializer. Это не реальный clock read, даже при successful PE execution.

Guest object/PE hashes по receipt, с pre/post equality, обеспеченной reviewed Build-Probe:

```text
420263169d8b9fb9a0b67e0762c3154ec3fd87150ccdfd74ed91489210f0d8dd  WasapiCaptureWorker.obj
3cd6574f4045f172a2d916c001569293d82052b1b747cc814d65ebd0e223573a  AudioNormalizer.obj
1c584c8b80ed00254186a59c697926a895332af8194bd4ab9619c9187f375694  ClockMapper.obj
3f56183896897748d4e92cee4bd85919b7be4ee4a5a999d36520eadc4169e883  WasapiEndpointEnumerator.obj
4064ccfa651babd420e548de242dd68692fbdf5e19b6484b4025762f15339569  ClockProbe.exe
```

Local saved evidence не содержит .obj/.exe; reviewer не хешировал actual guest files и не запрашивал guest processes. Поэтому это independent qualification сохранённого source-checked receipt, не новая guest attestation. Reviewed Run-Probe повторно проверит те же четыре объекта/PE/inputs/source216 непосредственно перед запуском и после. Outer build terminal0 сообщён main; reviewer не наблюдал его отдельный execution handle.

### Условия ровно одного запуска

- Сначала Mac и guest desktop реально разблокированы, видимый Start/Stop/Esc интерфейс доступен; свежая проверка отсутствия competing native capture/app/build/test, не ссылка на старое UI наблюдение. Main сообщил Mac locked: до выполнения этого условия launch остаётся HOLD. Независимая host portable сборка здесь не квалифицируется и не считается автоматически завершённой.
- Использовать только reviewed Run-Probe.ps1 с Stage t120-clock-native1 и ExpectedHash `4064ccfa651babd420e548de242dd68692fbdf5e19b6484b4025762f15339569`, без изменения inputs/guards/профиля. Ровно один metadata-once-48000 case, 10ms/shared/event, cap65/min16, visible5s watchdog/parent12s. Микрофонный stream будет реально активирован, но PCM pointer остаётся opaque: никаких contents/copy/save/network.
- Любой native/mapper/bracket/cleanup/deadline отказ сохраняется; wrapper1/measurement_accepted=false не выдаётся за PASS и не запускается автоматический повтор. Сохранить receipt/clock-summary и terminal ownership evidence для отдельной post-run qualification.
- SOURCE/build GO не означает, что bracket уже проверен в живом COM. Этот запуск не принимает full Resume/ACK/CLOSE, fresh-after-Resume audio, hardware accuracy, installed/manual или весь T120.

SHA256 сохранённых build evidence:

```text
f21a30f5b81b00a82e5a4025349ab7b0be4eb2b2ec17156dfecb557a1dd1da91  build-result.json
a8ad55513511f75ec322a5926038da99f8862b450e1419f0a1fc2907a5dddeee  native-build.log
31f6cad0ff8e051b15675da271bad79c06d8382713be8946a37f3c544afceaf2  probe-build.log
```

Единственная запись reviewer — данный append; source/нормы/tasks/checklists/Git/VM не менялись, аппаратные/аудио проверки не выполнялись, T120 не закрывался.

## Append — 2026-10-21: clock helper saved regression1/protected-helper1 qualification and mechanical Ponytail review

По прямому запросу пользователя прочитаны оба terminal receipts, все полные сохранённые build/test logs и оба runner scripts; применены code-reviewer и ponytail-review. Reviewer не выполнял VM/process/build/test/audio/Git actions. Единственная запись — этот append. **Saved-runtime bounded GO** для `t120-clock-regression1` и `t120-protected-helper1`; это квалификация сохранённых результатов, не новая runtime-проверка.

`t120-clock-regression1/result.json` SHA256 независимо совпал с main: `81661ca4582a76b7492f2fc88c7b5ccc8dd7e7467661032defabda1765074072`. Receipt terminal=true, Debug, build0, executed_groups7, все семь exits0 (normalizer/async/fifo/prefetch/unread/resume-clock/full), postflight216, owned_processes0, failure отсутствует. Runner `validate-t120-resume.ps1` SHA256 `6a24d2a52b4a4769314b43ae31c4005b5d49e3d1ef4c9f309f73b0e8d013b3f7` выполняет каждую группу последовательно и прекращает путь при nonzero; full запускает CFS без CLI фильтра. Это семь выполненных групп, не вымышленный CTest suite/case count. Пустой async.log соответствует source без обязательной печати и не означает skipped; его выполнение подтверждено receipt/runner exit0.

Actual logs подтверждают prefix160/invalid16 и прежние16 resampler cases; FIFO4/prefetch6 suppressed1; unread обе boundary1440/1200, releases4/frames4/aec4/eos3/finalizer1/old_suppressed1 плюс delayed_ack1; clock rejected13/retry13/eos13/finalizer13, late retry1/stop1 и committed ACK/throwing handler. Full.log повторяет эти markers и содержит `Native endpoint ID roundtrips: 2 (no capture)`; завершение оставшейся default main подтверждено full exit0. После исчезновения PID5876 нет основания называть старый процесс живым/зависшим. По сообщению main diagnostic script остановился на noPID guard, CDB никогда не вызывался; reviewer не наблюдал процессы или debugger и не устанавливает причину длительности по одному flushed marker.

`t120-protected-helper1/result.json` SHA256 `c445cf5b145a4459d0ae5c2d3c260c79d9629673001282f244f4bfea5ca6a75c`: terminal=true, Debug, build0, argument --protected-privacy-flow, test_exit0, postflight216, owned_processes0, failure отсутствует. Runner hash `474ab3a491622217ff0c54eaf7a979a6681482ed2006cb5e82853d8b4391f17f` совпал с receipt. Полный privacy-flow.log содержит frames_3000, finalized, two_durable_segments_closed1, cold_read_verified, done. PowerShell NativeCommandError оборачивает диагностический stderr `NATIVE_STORAGE baseline=0 empty_proxy=16`; это не самостоятельный ненулевой test exit и не игнорирование отказа. Оба build logs согласованы с успешными Debug targets, без ошибок; incremental, не clean build.

Оба source manifests byte-identical, SHA256 `396766d44cf35e929a2abe91a2f345f347f2adef140490f93174053d010f5b2d`; independently current216 match/0 mismatch. changed.json обоих прогонов пуст. PE по receipts:

```text
ff76d94ad8a7c5059cff39c890159c759a733a8f65db978f20746790ec36c211  CaptureFaultStateTests.exe
c819fe052b8e4a03eba36a9fabcbf5b9e3c33b20e6c2a7736d0bf1418bdedc84  AudioNormalizerTests.exe
f1958d364201a7c5cb68d608cd62e864b2e498112323592a6f31b663d5c34e49  NativeCaptureStorageIntegrationTests.exe
```

Main отдельно сообщил guest PE MATCH для всех трёх; reviewer самостоятельно проверил saved receipts/runner pre/post PE equality logic, но guest binaries не читал. Outer0 обоих прогонов сообщён main; отдельные execution handles reviewer не наблюдал. Host48/48 отдельно сообщён main, не повторно квалифицирован этим append.

Mechanical helper review: actual WasapiCaptureWorker.cpp diff сопоставлен с сохранённым native4 baseline, чей worker hash равен protected-green1 baseline. Тело старой native lambda перенесено в private static readResumeClockSample без изменения порядка QPF/QPC/GetPosition/timepoints/checked conversion/tolerance; единственные substitutions — explicit clock pointer и sampleRate аргумент. Lambda делегирует тому же compiled method; header ограничен _WIN32/global IAudioClock forward declaration/private method. Новых dependencies/state/public API/virtual adapter или второй clock реализации нет. Existing callable construction до Start/GetBuffer сохраняется. Обоснованных удалений/упрощений в этом механическом scoped diff не найдено. **Lean already. Ship.** net: 0 lines possible. Это вывод о минимальности данного extraction, не разрешение релиза/закрытия T120.

Границы: synthetic acquisition/normalizer/dispatcher/checkpoint/finalizer и bounded durable metadata/cold read; protected smoke не доказывает fresh audio after Resume. Actual native readResumeClockSample COM bracket всё ещё runtime не проверен. Нет audio contents/network/install/hardware/full T120 acceptance. Mac по свежему сообщению main locked, actual clock launch не выполнялся и остаётся HOLD до выполнения прежних условий разблокировки/видимости/preflight; автоматический повтор/расширение не разрешены. Tasks остаются OPEN. Нормы/checklists/tasks/source не изменялись.

## Append — 2026-10-21: protected-samples1 frozen test-only SOURCE review

По прямому запросу пользователя применён code-reviewer; полностью прочитан actual test-only diff против сохранённого baseline `11573c62b0108200855e5ee1b336d971db4a57fb800f222caf19b36b7bd7a6e7` (baseline snapshot protected-green1 совпадает с entry protected-helper1 manifest), relevant producer/controller/normalizer/ClockMapper/timeline/storage-reader/writer call paths, existing finalization/cold inspection/restart/CLI и новый external Run.ps1. **SOURCE GO для frozen t120-protected-samples1: blocking findings не осталось.** Ни build/test/VM/Git/audio/process actions reviewer не выполнял; runtime GREEN ещё не заявлен.

Exact test SHA256 current=staged: `1ef83170385a6ab3c6d077d31fd46238b2847ccda8e46c78936cf2979cc61c1b`. Source216 manifest `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`: independently current216 match/0 mismatch; prior `396766d44cf35e929a2abe91a2f345f347f2adef140490f93174053d010f5b2d`; manifests differ in exactly this test TU, changed.json lists the same single path. External Run.ps1 SHA256 `f2e545f93d0cf7b0ede625a0be87190504ea262ec6d7f42a77f4ea8e2668d270`.

Flow findings checked against actual source:

- NativeCaptureStorageIntegrationTests.cpp:6196–6238 local privacyProducer instances own independent mapper/normalizer/unread arrays; only microphone invokes actual consumePacket/epoch sampling/release. Frame0 must reach writer before public Pause; two unread mic packets are created only after paused checkpoint and held before packet()/epoch acquisition. System render continues with existing +32 backpressure; timeline requires both sources, so it cannot silently write past frame0 while mic is held. Public Resume uses the real mailbox on the acquisition worker; main releases unread only after recording&&!privacyPending. No epoch/READY/ACK setter or substitute dispatch/storage writer.
- Peer at :651–664 uses fixed B1200 -> P1199*8, f384000/r48000 => floor(P*r/f)+1=1200. Initial packet clock479*8 and releasedEnd480 are compatible; delivered frame1 clock max959/1199 ->1199 and frame2 clock1439 preserve nondecreasing lastClockPosition after Resume. QPC packet steps100000 and device steps480 agree exactly at48k. All frame/offset/multiply/read sizes bounded by3000 and480; no configurable/unbounded overflow exposure in this fixture. Partial packet2 keeps first240 old0.5 and replaces last240 with fresh0.25 after accepted Resume; subsequent mic remains0.25. These are generated values, not physical capture authority.
- :6290–6324 retains public Pause/Resume, second public Pause and Stop CLOSE. Early candidate direct renderPackets/microphonePackets assertion was racy because enqueue/consume return and producer counter increment are not synchronized with writer frames. Frozen :6318 now uses existing bounded waitFor for BOTH exact3000 counters before second Pause, resolving that specific false-failure window; equality/proof is not weakened.
- :6446–6467 opens genuine group readers from cold retained package pair, selects canonical by current ref index/selected slot, requires SEALED length5760000 bytes and verified reader. Production openProtectedCustodyReaders verifies retained roots/hash and rewinds stream to0 before return (:605–620). Writer stores frame.mixed at1920bytes/block; GeneratedAec is identity, so exact binary-representable expected mixed values are .1875 for indices0..479, .0625 for480..1199, .3125 for1200..1439999. All1440000 float values, each full1920byte S_OK read and final S_FALSE/got0 EOF are asserted. This catches lost full suppression, wrong partial frontier, muted fresh suffix, altered prefix, truncation and surplus data, not only manifest strings.
- Fresh readers retire at privacyFlow block end before existing inspectProtected. Genuine30s/hash/media/AAC inspection, two closed privacy segments, queue identity/adoption/restart, forbidden plaintext-file scan and CLI exact idle-memory check remain. Generic generatedProducer privacyPackets branch is removed because its sole caller moved to privacyProducer; every other caller retains previous source/count/lateDevice defaults. Existing CLI and nonprivacy branches are unchanged apart from removing that unused last option.

New external Run.ps1 compared in full to immutable validate-t120-protected-flow.ps1: only oracle list adds exact `PRIVACY_SAMPLES unread=2 boundary=1200 old_suppressed=1 fresh_suffix=240 canonical_samples=1440000 eof=1` and `stage=done`. Existing build/test exit checks, sequential single invocation, pre/prior/post216, staged hash scope, PE pre/post equality, owned0, terminal/failure receipt and old two-CLOSE/cold markers remain. Old runner/receipts untouched. This SOURCE GO permits the separately controlled synthetic no-device build/run for the exact frozen candidate; it is not runtime qualification or approval to execute actual clock probe while locked.

Acceptance boundary: if executed successfully, this strengthens the generated durable consumer test to prove old-prefix suppression AND audible fresh suffix after public Resume all the way into cold canonical, with genuine package/AAC integrity inspection. It does not prove actual COM GetPosition/bracket runtime, real hardware/endpoint pause behavior, microphone accuracy, installed/manual/whole T120 or release. Actual native clock probe remains HOLD while desktop locked; tasks OPEN. Only reviewer-owned report appended, no source/norm/task/checkbox changes.

## Append — 2026-10-21: protected-samples1 scoped Ponytail review during active synthetic run

По прямому запросу пользователя полностью прочитан ponytail-review skill и повторно только small test TU diff против protected-helper1-equivalent baseline11573c62; current SHA256 по-прежнему `1ef83170385a6ab3c6d077d31fd46238b2847ccda8e46c78936cf2979cc61c1b`. Scope — минимальность этого diff, без повторного normative/design review. Обоснованных безопасных сокращений без ухудшения ясности и доказательной силы не найдено. Локальная factory lambda обслуживает два source без нового generic adapter; unused privacyPackets branch уже удалён. Три handshake flags и два bounded counters имеют разные контрольные функции; canonical ref/verified/SEALED/length/full-samples/EOF assertions и exact marker — необходимые проверки, не лишний код. Сведение loops/branches в компактные выражения либо отдельную универсальную test abstraction здесь не даёт полезного упрощения. **Lean already. Ship.** net: 0 lines possible.

Это не runtime verdict и не предложение менять frozen candidate во время выполнения. Original exec session4560 по сообщению main активна; reviewer её не опрашивал, receipt/logs не квалифицировал, процессов/VM/build/tests/Git не касался. Единственная запись — этот report append; actual native clock HOLD и прежние acceptance boundaries неизменны.

## Append — 2026-10-21: protected-samples1 saved-runtime bounded qualification

По прямому запросу пользователя выполнена независимая read-only квалификация сохранённого samples1: прочитаны terminal result.json, полные UTF16LE build.log/privacy-flow.log, повторно проверены source/current/staged identity и reviewed Run.ps1. **Bounded runtime GO: generated post-Resume fresh-suffix + old-unread suppression доказаны до genuine cold SEALED canonical consumer в этом exact тесте.** Никаких VM/process/build/test/audio/Git actions reviewer не выполнял; единственная запись — этот append.

Receipt SHA256 `931064c4b466053760c4b4ad6b9a84933fe2543a3324dc0049aea16e357e94e9` и privacy-flow.log SHA256 `fcd2342ef972e0f40e09bdac7db2c007cd1d40d7c4a9aa73e905bfc54b6c695b` независимо совпали с сообщёнными main. Receipt terminal=true, Debug, build0/test_exit0, postflight216, owned_processes0, failure отсутствует, argument --protected-privacy-flow, device_audio_read/real_network/installed=false. Run.ps1 hash `f2e545f93d0cf7b0ede625a0be87190504ea262ec6d7f42a77f4ea8e2668d270` совпал с reviewed SOURCE и receipt. Manifest `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`, independently current216 match/0 mismatch; staged/current test TU byte-identical, SHA256 `1ef83170385a6ab3c6d077d31fd46238b2847ccda8e46c78936cf2979cc61c1b`.

Полный build log подтверждает compilation NativeCaptureStorageIntegrationTests.cpp и успешный Debug target без build errors; это incremental build. Полный runtime log содержит frames_3000 elapsed_ms18024, finalized, cold_read, two_durable_segments_closed1, точный PRIVACY_SAMPLES unread2/boundary1200/old_suppressed1/fresh_suffix240/canonical_samples1440000/eof1, cold_read_verified и done. NativeCommandError в начале PowerShell log — представление диагностического stderr baseline0/empty_proxy16, не ненулевой test exit. Runner требует старые и новые markers плюс actual exit0, post-source/PE equality и owned0; нет skip/retry/ignore ветки.

Квалификация sample-proof опирается не только на строку: matching current source :6446–6467 перед её печатью открывает genuine group readers, требует verified stream и SEALED canonical exact5760000bytes, читает все1440000 floats с точными full reads, сравнивает .1875 для0..479, .0625 для480..1199, .3125 для1200..1439999 и требует S_FALSE/got0 на EOF. Затем выполняется прежний inspectProtected/30s/hash/AAC proof; done следует после настоящего queue cold restart/shutdown, а CLI возвращает0 только после exact idleOwnedBytes. Source/public-control flow уже отдельно reviewed; этот receipt переводит именно его generated sample assertions из SOURCE-only в executed PASS, без расширения полномочий.

PE receipt `964b564c4a988a87536e74637350c70b6c2335cce23e216391c5cd95a124e781`; main отдельно сообщил actual guest GetFileHash MATCH. Reviewer проверил saved receipt и reviewed runner pre/post PE equality logic, но actual guest PE не читал. Original session4560 outer0 сообщён main, execution handle reviewer не опрашивал.

Это не реальный microphone/COM clock/bracket/hardware/installed/full T120 или release acceptance и не доказательство sample-exact AAC decoded waveform (AAC integrity inspection сохранён отдельно). Tasks/checklists не менялись. Новая clock-native2 rebind/build/4objects пока не квалифицирована этим append; предыдущий clock artifact нельзя выдавать за автоматически bound к новому216 manifest. Actual clock launch остаётся HOLD, пока desktop locked. Никаких норм/code/source changes reviewer не делал.

## Append — 2026-10-21: clock-native2 saved non-device build and conditional single-launch qualification

По прямому запросу пользователя применён code-reviewer: прочитаны native2 build-result.json, оба полных native/probe build logs и unchanged Build-Probe/Run-Probe scripts; независимо сверены external input hashes и current216. **Saved non-device build GO; условный GO ровно на один bounded actual native clock run после проверки main guest PE, unlocked visible desktop и свежего preflight.** Reviewer VM/process/build/test/Git/audio actions не выполнял. Authoritative exec54450 handle по сообщению main missing: receipt сохранён, но reviewer не подтверждает outer exit/handle terminal и не подменяет это утверждением outer0. Основание данного вывода — terminal saved receipt + согласованные logs/source-checked harness.

Receipt SHA256 `813e52f5ef856e8f53462fc15a00abcaef21d453e3612b0552112d0c8dd5ae00`: terminal=true, Debug, native_build0/probe_build0/pure_checks2/postflight216/owned_processes0, failure отсутствует, device_started=false/device_audio_read=false. Native build log подтверждает успешный common target MSBuild17.14.51 без новой compilation marker; это incremental reuse, не clean rebuild четырёх objects. Probe-build log подтверждает VS2022 x64 compilation ClockProbe.cpp, без errors; probe_build0/pure checks согласованы с успешным link/execution. Pure paths --self-check0/--unsupported64 обязательны reviewed Build-Probe до выставления pure_checks2, оба до COM/device; отдельных child receipts/stdout нет.

Source216 manifest `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`: independently current216 match/0 mismatch, byte-identical samples1 manifest и native2 prior; changed.json empty. Это явный rebind после pure test delta, не перенос старой native1 attestation на другой manifest без проверки.

Inputs совпали с receipt и прежним reviewed SOURCE: ClockProbe.cpp `298cdcafff666a602d904c8563cd9ee4d9595c3878e645490ccdf66fb28f8374`; build.cmd `906985751ed73a46ac7b69e07fe43d028fbf30e65a3ed31a8366478573e2e3dc`; Build-Probe.ps1 `755aa27dd46be26673070d655c099b0da7641b2585807d20805eaa332f5d7084`; Run-Probe.ps1 отдельно `dbfc729a50eb320b5dcc0710d86a7ac7a7a09cf211b17eef70b82e93056db3a1`.

Все четыре exact object hashes в native2 receipt совпадают с native1 accepted set:

```text
420263169d8b9fb9a0b67e0762c3154ec3fd87150ccdfd74ed91489210f0d8dd  WasapiCaptureWorker.obj
3cd6574f4045f172a2d916c001569293d82052b1b747cc814d65ebd0e223573a  AudioNormalizer.obj
1c584c8b80ed00254186a59c697926a895332af8194bd4ab9619c9187f375694  ClockMapper.obj
3f56183896897748d4e92cee4bd85919b7be4ee4a5a999d36520eadc4169e883  WasapiEndpointEnumerator.obj
265bf145fcafd545ea570bac358cb216aa9a9e2a7ac375584c8751ef69e40f21  ClockProbe.exe (native2)
```

Saved stage содержит только receipt/logs/manifests/changed, без local .obj/.exe: reviewer не хешировал actual guest objects/PE и не наблюдал guest process state. Hash equality квалифицирована как сохранённое свидетельство reviewed harness с pre/post assertions. Main сам выполнит свежий guest PE MATCH и UI check; Run-Probe повторно проверяет current216, все inputs, четыре actual objects и expected PE непосредственно перед/после запуска. Изменённый PE при тех же inputs/objects сам по себе не свидетельствует о source delta; determinism build не заявлен.

Условия единственного разрешённого запуска: только unchanged Run-Probe.ps1, Stage=t120-clock-native2, ExpectedHash=`265bf145fcafd545ea570bac358cb216aa9a9e2a7ac375584c8751ef69e40f21`; перед ним подтверждены main actual PE MATCH, разблокированный видимый Mac/guest desktop и доступные Start/Stop/Esc, отсутствие competing native capture/app/build/tests. Если locked — HOLD. Один --metadata-once-48000/10ms shared-event профиль, cap65/min16;5s UI watchdog/12s owned-parent deadline, без PCM read/copy/save/network. Это реальная активация mic stream, не pure test; никаких автоматических повторов/ослабления guards при refusal. Сохранить clock-summary/run-result и terminal owned0 для отдельной post-run qualification; measurement_accepted=false/wrapper1 не считать PASS, cleanup отделён от принятия измерения.

Native-build log SHA256 `1344c175e12a8bf02292c7af1a2abff0e6617ea4f84b16a0c3f00907ebb74807`; probe-build log `31f6cad0ff8e051b15675da271bad79c06d8382713be8946a37f3c544afceaf2`. Actual live COM bracket пока не квалифицирован; нет full Resume/ACK/CLOSE, real fresh audio/hardware accuracy, installed/manual/full T120/release acceptance. Только report append; source/norms/tasks/checklists unchanged.

## Append — 2026-10-21: app-build1 external script SOURCE review and Debug isolation

По прямому запросу пользователя применён code-reviewer; прочитан весь current external Build-App.ps1, current vcxproj/Directory.Build.props, AEC VerifyBuildArtifacts branch и native-clock build paths. Script SHA256 `757f6d0eaad2e980fcfcd2f4391440d02e94f4311a0d2460a35699c5a2dad83b`, manifest `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`, independently current216 match/0 mismatch. Reviewer не выполнял VM/process/build/tests/Git; only report append.

**SOURCE request changes / один исправимый evidence-preservation blocker:** Build-App.ps1:18 throws STAGE_ALREADY_USED внутри try, catch:52 устанавливает failure, но finally:56 безусловно Set-Content в тот же existing result.json. Следовательно повторный ошибочный вызов не просто отказывается: он перезапишет сохранённый terminal build receipt отказом и уничтожит исходное свидетельство. Это противоречит заявленному freshStage guard и сохранению результатов. Минимальное исправление — вынести проверку existing result.json перед try/finally, чтобы early refusal не входил в receipt writer; никаких новых файлов/архитектуры/ослабления guards не требуется. Текущий stage ещё fresh, но script guard некорректен; до этой узкой правки final script SOURCE GO не выдан.

Прямого конфликта путей с native2 Debug artifacts не найдено: Directory.Build.props:13 задаёт apps/windows/out/x64/Release, :14 apps/windows/out/obj/GrafWindowsApp/x64/Release для этого exact project/configuration. Native2 использует отдельные root/build/graf_windows_common.dir/Debug/{4objects} и root/build/Debug/ClockProbe.exe; vcxproj компилирует source TUs напрямую и не ссылается на CMake common target/Debug PE. Поэтому штатная /t:Build Release/x64 не перетирает эти четыре объекта или native2 PE. AEC root explicit внешний round238, target ValidateGrafAEC3 :189–194 остаётся активен и вызывает только VerifyBuildArtifacts; тот проверяет provenance/source/actual artifact hashes и выходит до meson compile. Стандартные Content copy направлены в app OutDir. Это source path analysis, не observation actual evaluated guest MSBuild properties; пользовательские external/global imports или overrides вне прочитанного script не аттестованы. Run-Probe всё равно повторно проверяет четыре hashes/PE перед real launch.

Остальной scoped script согласован с build-only замыслом: exact vcxproj /t:Build Release/x64, нет /restore/install/launch/CMake commands; source216 pre/post, owned0 pre/post, AEC provenance/runner equality, fresh AppMain.obj/EXE times, compilation/link/AEC log checks, MZ+PE/x64 machine и SHA. Если Build полностью up-to-date, fresh-compile guard корректно откажет, не подменяя это новой compile validation. Проверка PE здесь только MZ/PE signature/machine, не Authenticode/installed/runtime qualification. Старый build450.ps1 не найден в двух ограниченно проверенных local evidence roots; утверждение о byte-for-byte reuse450 не делается, вывод основан на actual current script/project/recipe. Final runtime/build receipt ещё отсутствует; clock launch HOLD при locked desktop, tasks/checklists unchanged.

## Append — 2026-10-21: app-build1 freshStage guard delta SOURCE GO

По запросу пользователя повторно прочитан actual Build-App.ps1; единственная дельта — STAGE_ALREADY_USED guard теперь :17 вне try/finally, try начинается :18. При early refusal existing result.json больше не попадает в finally writer; единственный previous blocker устранён. Обратный перенос этих двух строк в stdout без записи файлов воспроизвёл прежний script SHA256 `757f6d0eaad2e980fcfcd2f4391440d02e94f4311a0d2460a35699c5a2dad83b`, подтверждая отсутствие иных изменений. Current script SHA256 `2541a865841d1baa0894d28dffb383f09c9f3e245ca4229c174cc324aabe217c`; manifest unchanged `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`, independently current216 match/0 mismatch.

**Bounded SOURCE GO** на отдельно управляемый build-only exact GrafWindowsApp.vcxproj Release/x64 этим script, без restore/install/app launch/audio/network capture. Предыдущие source/owned0/AEC provenance/fresh compile+link/PE/postflight guards и разделение Release app outputs от native2 Debug four objects/PE сохранены. Actual build/terminal receipt ещё не квалифицированы; при отказе не обходить guards и не переиспользовать stage с receipt. Actual clock launch HOLD при locked desktop; tasks/checklists без изменений. Reviewer ничего не запускал и не менял кроме этого report append.

## Append — 2026-10-21: app-build1 saved Release/x64 compile/link qualification

По прямому запросу пользователя применён code-reviewer, прочитаны saved terminal result.json и полный UTF16LE build.log, повторно проверены current216 и approved script/hash, active AEC target и receipt PE checks. **Bounded saved build GO: актуальное GrafWindowsApp Release/x64 compile/link подтверждено сохранёнными свидетельствами.** Reviewer не запускал VM/process/build/tests/app/audio/Git; единственная запись — этот append.

Receipt SHA256 `b0a1e86ec7ca1799489969b9172fce1cc80b04439991f9e173f48ad64c9f0801`; полный build.log `bec339c98df8f16500d284e1e63cf3fe838cf98d478ab77ebabd53c6a2725c50`. Receipt terminal=true, Release/x64, build0, preflight216/postflight216, owned_processes0, elapsed160190ms, failure отсутствует. Manifest `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`, independently current216 match/0 mismatch. Script `2541a865841d1baa0894d28dffb383f09c9f3e245ca4229c174cc324aabe217c` совпадает с SOURCE GO и receipt.runner; current AppMain.cpp `a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38` включён в matching manifest.

Полный log явно содержит AppMain.cpp и compilation изменённых AudioNormalizer/WasapiCaptureWorker/controller/HTTP/reminder/storage consumers, затем Creating library, LTCG Generating code и exact output apps/windows/out/x64/Release/GrafWindowsApp.exe. Это successful incremental build, не clean/full recompile: log прямо сообщает reused previous compilation functions. Warnings присутствуют: D9025 /W1 overridden by/W4 и upstream WebRTC C4100 unused parameters; warning-free не заявляется, build errors в полном log не обнаружены.

Свежесть AppMain.obj и executable относительно start проверена approved script до записи qualified fields; receipt appmain_object SHA256 `47c39d081c6a6b018eb86b63c5522811a0530b546d8b41cfb9039ad29b4d45f6`. PE receipt: SHA256 `d3e35da2604665251d72515688b120d3c43b021cf06013c591e6e163aee4be80`,3319808bytes,writtenUTC2026-10-21T18:44:04.1223001Z,machine0x8664; script проверяет MZ/PE signature/x64, но не подпись/AuthentiCode/installed suitability. Local stage не содержит EXE/OBJ; reviewer не читал actual guest binary/header. Main отдельно выполнит actual guest PE hash; это ещё не приписано независимой reviewer guest verification. Original exec27184 outer terminal0 без перезапусков сообщён main, reviewer handle не опрашивал.

AEC guard не обходился: current vcxproj ValidateGrafAEC3 BeforeTargets=PrepareForBuild вызов VerifyBuildArtifacts сохранён; log подтверждает source/license identity verified commit846fe90a289f58b7c9303a635142aa2c7caa93e5. При successful native target этот reviewed branch проверяет source/build identity, headers/artifact inventory/hashes и provenance. Receipt pre/post provenance hash `ebe9b371f9ef9ab8e78f45c607ab7a661235ad9396d4001e2079395b08aae0fe` без изменения. Reviewer не читал actual guest AEC cache/provenance file, поэтому это квалификация guard execution по source/log/receipt, не новая cache attestation.

NoRestore scope подтверждён command /t:Build без restore switch/target и отсутствием restore activity в полном log; receipt.restore_performed=false согласован с этим. Нет app execution/install/audio commands; receipt device_started/app_network/installed/launched=false. Это не независимый сетевой мониторинг всех build tools и не runtime acceptance приложения. Release app outputs source-isolated от native2 Debug four objects/PE; actual hashes тех объектов в этом app receipt не измерялись, Run-Probe должен повторно проверить их перед будущим real launch.

Build GO не закрывает native COM clock bracket, endpoint/hardware/fresh real audio, installed/manual UI, MSIX/signing/release или full T120. Mac по сообщению main locked, real clock launch HOLD; tasks/checklists/source/norms без изменений.

### App-build1: supplemental main guest hash confirmation

После saved qualification main отдельно сообщил actual guest GrafWindowsApp.exe GetFileHash MATCH `d3e35da2604665251d72515688b120d3c43b021cf06013c591e6e163aee4be80` и сохранность actual Debug ClockProbe.exe hash `265bf145fcafd545ea570bac358cb216aa9a9e2a7ac375584c8751ef69e40f21` после full app build; микрофон не запускался. Это прямое свидетельство main, не reviewer VM action. Оно дополняет уже независимо проверенные receipt b0a1e86e/log bec339c9 и source216. Full log действительно показывает2973/29002 functions compiled(10.3%), rest reused/LTCG; incremental/non-clean и D9025/upstreamC4100 warnings остаются явными ограничениями. Четыре Debug object hashes после app build этим сообщением отдельно не подтверждены; будущий Run-Probe проверит их. Bounded compile/link GO сохранён; actual clock measurement/HOLD и прочие acceptance boundaries не изменены.

## Append — 2026-10-21: T103 history baseline delta and runner construction

Применён code-reviewer. Read-only source review current three files против предоставленных exact baseline copies из external t103-history1/baseline, а не против dirty HEAD. Baseline SHA256: WebView2AuthNativeTests.cpp `a43f9e303509921a6bfe650b8d8f0a82992f5faeaaf9b35c03b68cf47029c0e7`; WebView2AuthLoopback.py `27bebbb1416390c2b1141b23a26138675ddc294be3db02b0141b365dac9bfc3f`; RunWebView2AuthNativeTests.ps1 `9f5fb28436810f644acfe555af8eba91dd127dded64525eb6a04cf6913319bc3`. Current и frozen staged copies независимо совпадают: соответственно `ddd1ae3835866d84bac879e8e0bc701496daf17c373429decf6555b6506361ec`, `0c90192e49c06700f59f8d8c82a01d4cd14b34e0cf56f74ad59b4fe0a065a916`, `eb4b7c600bdeb29c255b40685177f4a5173115e935146b30cd3d32887a9f82e4`.

В bounded history delta подтверждён test-construction SOURCE GO: actual host back/forward, GET A/B/C/B/A/B/C и POST A/B/C/A/C, real requestSubmit, server exact synthetic body validation и B DOM input value, phase completion threshold + asynchronous generation/phase fence, runtime ready/actual bridge/native_ready и обе source identities. Нет нового fake READY/ACK или cookie authority. Counts GET3..7/POST0 и GET2..4/exactPOST1 независимо ограничивают сетевые повторы; старые fourteen scenario branches/oracles не ослаблены. Это не runtime PASS: current WebView2Host.cpp:1021–1034/:1852–1853 делегирует обычные native GoBack/GoForward, POST-safe history behaviour подлежит meaningful runtime RED/qualification. Session/T088 и полный T103 acceptance не входят. Перепроверка 198 checklist files не проводилась; refreshed requirements GO/477/0 сообщены main, не присвоены этой source проверке.

Current runner :32 содержит прежний manual fifteen-TU list и не покрывает нынешние protected custody implementation dependencies; :40 также не содержит полного native MF/custody library closure. Это runnable-build prerequisite, а не доказанный history behaviour RED. По отдельному предложению main **bounded construction GO** заменить только build source enumeration на standard XML parse actual RecApp/GrafWindowsApp.vcxproj, exact ItemGroup/ClCompile[@Include] с namespace (не ItemDefinitionGroup/ClCompile), resolving Include относительно project directory RecApp. Current project содержит55 literal unconditional Includes; исключить ровно AppMain.cpp и ../Native/GrafAEC3/GrafAEC3WebRtcAdapter.cpp, добавить existing fixture once:54 TU. Проверить существование файлов и case-insensitive object-basename uniqueness до compilation; оба exact exclusions должны действительно находиться, а не silently fail из-за slash/path normalization. Новый runner actual patch ещё не существует и SOURCE GO ему не приписан.

Сохранить MSVC /std:c++17,/MD,/EHsc,/W4,/WX,/utf-8,/bigobj,/await:strict,GRAF_WINDOWS_APP_SDK, текущие Unicode/Win32 defines и GeneratedHeaders. CMake RecApp/Native GrafAEC3 include dirs можно сохранить явно; current source quoted includes преимущественно relative. К имеющимся system libraries добавить mfplat,mfreadwrite,mfuuid,oleaut32,avrt,wintrust,crypt32 как current CMakeLists.txt:173; existing user32/gdi32/comdlg32/ws2_32 и прочие не убирать. Текущие source pragmas сохраняют normaliz/urlmon/icu/Wtsapi32 dependencies. Не копировать product AEC preprocessor definitions/third-party link branch в standalone fixture. Не компилировать прежние fifteen TU вторично поверх project-derived list.

AEC terminology verified: Native/GrafAEC3/GrafAEC3.cpp:11–19 отвергает missing backend/process, :24–37 вызывает предоставленный backend; untreated microphone fallback отсутствует. Включение C ABI при исключённых AppMain и WebRtcAdapter не создаёт AEC backend и не вызывает capture. Adapter::create callers найдены только в AppMain.cpp:471/:3804, который исключается. Production vcxproj:189–194 ValidateGrafAEC3/VerifyBuildArtifacts остаётся без изменений; standalone test-only recipe не является product app build и не ослабляет shipping guard. Runtime/profile/browser exit/owned-process cleanup/watchdogs/scenarios/counts и PE equality должны остаться прежними. Compile/link failure не считать meaningful RED; прежде нужен successful fresh fixture build, затем отдельный actual history result. Reviewer не запускал VM/build/tests/Python/Git/app/capture и не менял ничего, кроме этого report append.

### T103: actual XML runner delta SOURCE GO

Повторно применён code-reviewer. Actual RunWebView2AuthNativeTests.ps1 SHA256 `46b21a17ff406b95dff47009dceb4411b3811cd4d9b0b2eb412b780556486ce2` прочитан против frozen prior candidate `eb4b7c600bdeb29c255b40685177f4a5173115e935146b30cd3d32887a9f82e4`. **Bounded SOURCE GO, actionable defects в этой delta не найдены.** Изменены только enumeration/path/exclusion/duplicate checks и link libraries; остальной script byte delta отсутствует. Namespace-aware ItemGroup/ClCompile[@Include], rejection conditional/nonliteral entries, resolving project-relative source paths, slash normalization, exact-once exclusions, case-insensitive hashtable object-basename guard и single fixture append соответствуют одобренной конструкции. Current literal project даёт54 TU including fixture. Compiler policy прежняя; seven native libraries добавлены без удаления прежних. C++/Python hashes остаются `ddd1ae3835866d84bac879e8e0bc701496daf17c373429decf6555b6506361ec` / `0c90192e49c06700f59f8d8c82a01d4cd14b34e0cf56f74ad59b4fe0a065a916`.

SDK environment — отдельная compile precondition, не дефект XML delta. Единственный explicit /I GeneratedHeaders не является доказательством полного SDK include closure: нужны VS x64 CRT/Windows SDK (включая cppwinrt) environment и используемые WinRT projections/native supporting headers. Прочитан сохранённый external app-syntax.rsp (UTF16): он содержит отдельные Generated Files, WebView2 native/include и include-winrt, WindowsAppSDK WinUI/Foundation/Runtime и другие package include dirs, также ненужные fixture AEC dirs/production defines. Этот rsp не доказывает current guest INCLUDE и сам не объявлен свежим mainapp receipt. Самый узкий wrapper-only способ — дополнить process-local INCLUDE actual pinned non-AEC SDK directories из current mainapp compile recipe, сохранив developer environment и GeneratedHeaders; не копировать wholesale rsp, auto-bootstrap/GRAF_AEC3_AVAILABLE defines, /WX- или product flags. Дополнительные project-local /IRecApp/Native не требуются из-за существующих relative quoted includes в просмотренном source. Независимого утверждения, что каждый package directory из app rsp необходим этому fixture, нет. Успешная fresh compile/link должна предшествовать meaningful history RED; build failure не считать RED. VM/Git/build/tests не запускались, единственная запись — данный report append; runtime/full T103 acceptance по-прежнему не заявлены.

### T103 history2: external harness SOURCE GO

Code-reviewer: полностью прочитаны actual Run-History.ps1, Invoke-Runner.ps1, run.cmd; финальный Invoke повторно прочитан после единственного добавления WebView2 include-winrt. **Bounded SOURCE GO** на compilation и три controlled synthetic scenarios login-post400/history-get/history-post reviewed runner; actionable source blockers не обнаружены. SHA256 Run-History `8903d0f0352c172f003068ff7aa4b83dcaea731b0e8c0525ddb1a076691a19da`; Invoke `52bc8a8522eace8a9b8e7583d6723216aefdb24992c7b4243c734c36d443f0e0`; run.cmd `6f7f910053d16b0082cc107fb7db6d5a186caaa7d7a3f3466d56ec0a14e7178b`. Frozen three source files совпадают с предыдущим SOURCE GO (runner46b21a17/C++ddd1ae38/Python0c90192e). Manifest SHA `a5d845b5a17a4c29973f5f9f9cd18a3a4ba7db440654c9cf415f937e7b948c5e` независимо проверен против actual worktree:216 rows,0 mismatch. Diff manifest против exact prior `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2` содержит ровно эти три test changes.

Harness проверяет prior216 до fixed-three copy, затем current216 до/после child; runtime DLL и wrapper/cert/key input hashes до/после, fresh-stage refusal вне try/finally, run exit и owned0. Cmd получает vcvarsall x64 и запускает отдельный PowerShell; семь pinned SDK directories (включая WebView2 native include и include-winrt) проверяются на существование и добавляются только process-local перед inherited INCLUDE. Production/AEC/auto-bootstrap defines не переносятся. GeneratedHeaders указывает actual out/obj Generated Files, не отсутствующий RecApp/Generated Files. Outer600000ms watchdog taskkill привязан к запущенному child PID/tree, canonical runner сохраняет собственные35s case/profile/browser-exit/cleanup guards; retained nonzero run_exit не превращается в PASS, terminal receipt записывается и на отказе. Owned-process predicate не является универсальным аудитом всех browser/Python процессов; normal success browser exit/fixture/server cleanup доказывает сам canonical flow, а failure/timeout receipt должен квалифицироваться отдельно, не только по terminal=true.

Публичная synthetic certificate metadata прочитана openssl x509 без запуска harness: CN/SAN graf.test, self-issued,2026-10-21T19:00:44Z..2026-10-23T19:00:44Z; private key contents не читались. Trust-store mutation commands в harness отсутствуют. Existing fixture uses scoped synthetic certificate handling; это не acceptance real-site TLS. Guest existence/version/content SDK headers/Python и runtime execution reviewer не проверял — остаются actual compile/run prerequisites, а не уже пройденные proofs. VM/Git/build/tests/capture не запускались, единственная запись — этот append. GO не означает runtime PASS/full T103/T088/session/installed/UI/hardware acceptance; meaningful RED требует успешной сборки и actual named behaviour failure, не build/dependency failure.

### T103 history2: saved runtime qualification and oracle limitation

По запросу main полностью прочитаны run.log(169lines), run.err(0bytes), result.json; повторно прочитаны history oracle/completion observer, actual native back/forward и document completion/finalizer paths. Receipt SHA256 `12bfb187fd9c80ab282f914af83e8842edd8f1b74bf8870248773dc70c1657fa`; log `160d67ddac58dfc8a03e291d578b62a8045ba66a4cb1c2671bbe820b6a0de533`; err empty `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Manifest a5d845b5 independently current216 match/0 mismatch. Terminal=true/run_exit1/postflight216/owned0/NATIVE_RUN_FAILED согласованы с log2/3 passed. Внешний exec42395 exit1 сообщён main; reviewer handle/VM не опрашивал.

**Подтверждены compile/link PASS и два runtime controls, не общий GREEN.** Log содержит54 compile TU, successful fresh fixture build и PE SHA `4414a1c70ee479b1f16c19096cb26cc92ff3659eae073a4def767810ece6e793`; PE/hash аттестован canonical script/log, не direct guest file read reviewer. Login-post400 PASS exactcounts0/1/0/0/0/1; history-get PASS actual seven documents A/B/C/B/A/B/C с AUTHORITY1 в каждой фазе, exactcounts7/0/0/0/0/0. Каждый scenario имеет browser-exit PASS, fixture terminal exit, server exit0; own process cleanup не дала ошибки, failure GUID diagnostics сохранены. Receipt inputs совпадают с approved final harness hashes; source/runtime pre/post fences пройдены approved harness. Это не installed/hardware/full auth/session acceptance.

**History-post — действительный integration RED пути Back, но пока не чистое доказательство wrong committed history target.** Log135–167 подтверждает A/POST-B/C с ready+authority; после одного host->back (C++403–405) nav5 completed status0/success0/web_error0, host перешёл в unavailable (enum0), затем fixture FAIL history-document-identity; GET2/POST1/other0. Повтор POST и лишний GET в этой попытке не наблюдались. В логе нет actual DOM page id на отказе, source identity/category, failureDetail или следующего committed document. Web_error0 сам по себе не доказывает OperationCanceled/источник отмены/POST resubmit dialog. Эти причины не присваиваются.

Подтверждён ограничивающий дефект observation barrier oracle: C++586–598 увеличивает completions для любого NavigationCompleted, включая failed/cancelled; :350–351 принимает один такой callback как разрешение читать DOM; :372 немедленно проверяет expected page ДО :373–374 terminal/ready/authority проверки. Generation/phase fence :365 отсеивает stale callback, но не доказывает новый committed document: beginDocumentNavigation :686 увеличивает generation ещё до commit. Поэтому named history-document-identity может быть выдан для retained DOM при неудачном/промежуточном переходе. finish :130–133 затем закрывает host/control, отсекая возможность наблюдать дальнейший settle. Предыдущий construction SOURCE GO не превращает этот runtime observation в доказательство settled wrong target.

Это не позволяет объявить всё pure fixture false-positive: до fixture close уже независимо записан HOST_STATE0, то есть actual host unavailable после Back, а actual back/forward сейчас прямые GoBack/GoForward без safe-POST traversal. Но pending follow-up commit, фактический retained DOM и первичная причина по сохранённым данным не различены. Минимальный следующий test-only diagnostic/oracle gate (пока без реализации): отделить failed completion от successful/current committed-ready document; page identity утверждать только после current generation/navigation correlation + ready/authority, а current terminal host failure квалифицировать отдельным reason. Добавить только bounded metadata phase/navId/generation/success/status/error/host state и synthetic page id/source-match/failure category; preserve POST1/network/authority/original deadline и не превращать failed completion в success/skip. Не повышать timeout, не исправлять production на основании одного named identity assert. Чистый RED конкретного safe-history contract потребует этой однозначности; нынешнее свидетельство сохраняется как первый actual failing integration attempt с зелёными controls. Никаких VM/Git/build/tests/code/norm/checkbox actions; только этот report append.

### T103: actual navigation-correlated oracle correction SOURCE GO

По запросу main code-reviewer read-only проверил actual C++ против frozen history2 `ddd1ae3835866d84bac879e8e0bc701496daf17c373429decf6555b6506361ec`. Current WebView2AuthNativeTests.cpp SHA256 `952123e959f6a33b6be46fd01362fa839443ecd424007bce2c9a275a3141f801`. **Bounded SOURCE GO** на test-only correction; actionable compile/flow/security defects в этой delta не найдены. Изменения ограничены двумя observed navId fields, actual callback assignments и history observation/admission/diagnostic. Canonical runner остаётся `46b21a17ff406b95dff47009dceb4411b3811cd4d9b0b2eb412b780556486ce2`, Python `0c90192e49c06700f59f8d8c82a01d4cd14b34e0cf56f74ad59b4fe0a065a916`; reuse допустим без изменения cases/controls/cleanup.

Before-read :352 требует phase completion threshold и completed==started; async owner callback :367–368 повторяет captured navId с обеими live observed IDs плюс generation/phase/probeExit fence. Failed completion не допускает identity assertion: :388 отдельно fails history-host-unavailable; :389 перед :390 требует ready, successful completion и bridge/native_ready. Exact page order, accepted POST value, both Source identities, GET bounds/exactPOST1, deadlines и navigation actions прежние. Numeric diagnostics :383–386 не выводят URL/page content/cookie/nonce; failureDetail getter использует actual fail() stage+hex code (WebView2Host.cpp575–587), а не network response text. Existing stage literals/hex допустимы для этой synthetic fixture.

Оставшееся явное ограничение (не SOURCE blocker): GetResults/DOM parsing/Core.Source чтение всё ещё может бросить до проверки state, тогда reason будет history-script, а не гарантированно history-host-unavailable. Такой future result нужно честно квалифицировать как script/observation failure, не приписывать ему host terminal diagnosis или wrong-document proof; current patch не создаёт false PASS. Captured navId fence устраняет принятие другого pending navigation при async read; он не доказывает физическую/hardware authority и не заменяет runtime evidence. Fresh54TU compile+same3 runtime пока не выполнены/не квалифицированы. Stage3 должен иметь новый immutable manifest для952123e9 и prior a5d845b5; старые history2 scripts/receipt/log/source сохраняются как отдельная попытка, старый prior0de guard не обходится. Reviewer не выполнял VM/Git/build/tests/code/norm actions, только этот report append. Existing requirements GO используется в прежнем bounded scope, повторная whole-feature checklist/analyze проверка не заявляется; production rootcause/full T103/T088 acceptance открыты.

### T103 history3: frozen wrapper delta SOURCE GO

По запросу main проверены exact external stage3 wrapper delta и frozen input/source bindings. **SOURCE GO** на fresh54TU build и те же три synthetic cases через stage3. Run-History.ps1 отличается от reviewed stage2 ровно тремя expected manifest constants: prior=a5d845b5 и staged/postflight=c99dafc3. Current SHA256 `3e4cd11f43e02a876fd50502bb43d3ec31c823b34fe08687af7b56582af1d122`. Fresh-stage guard и остальная lifecycle/receipt logic неизменны. Invoke `52bc8a8522eace8a9b8e7583d6723216aefdb24992c7b4243c734c36d443f0e0`, cmd `6f7f910053d16b0082cc107fb7db6d5a186caaa7d7a3f3466d56ec0a14e7178b` совпали; cert/key cmp byte-identical, key contents не выводились.

Stage3 prior manifest SHA `a5d845b5a17a4c29973f5f9f9cd18a3a4ba7db440654c9cf415f937e7b948c5e`; source `c99dafc360f4f3cd8e3c0b245c2616b502698d8b2af5adaad53eb46ee96f62c1`; diff ровно одна C++ hash replacement ddd1ae38→952123e9. Frozen C++ соответствует предыдущему actual SOURCE GO `952123e959f6a33b6be46fd01362fa839443ecd424007bce2c9a275a3141f801`; runner46b21a17/Python0c90192e прежние. Независимый current worktree manifest check216/0 mismatch. Нового runtime результата нет; stage2 integration RED и oracle limitation не отменяются. Main сообщил direct actual guest PE4414a1c7 MATCH и GUID-owned profile processes0 через Check-Terminal.ps1; это дополнение main, не reviewer guest observation. VM/Git/build/tests не запускались; только report append. SOURCE GO не является rootcause diagnosis, runtime GREEN или full T103/T088/session/installed/hardware acceptance.

### T103 history3: saved corrected-oracle meaningful RED qualification

Code-reviewer по прямому запросу main полностью прочитал actual run.log180lines, result.json и empty run.err; повторно проверил current216 и script/hash bindings. **Квалифицирован meaningful integration RED: actual Back после A/POST-B/C приводит current host в unavailable, а не к требуемому ready A.** Это отдельный результат corrected oracle, не переименование старого stage2 wrong-document assertion. Successful committed wrong-page diagnosis и первичная причина не подтверждены.

Receipt SHA256 `b70cf738690833f9d7d2c89e96945b2dc56404c27c9344184575bbecc88cb359`; full log `58e18587bdb6bc5b59dd349278bbea077bda2bbe8646862bc1ce0b5dec1d852a`; err0bytes SHA e3b0c442. Manifest `c99dafc360f4f3cd8e3c0b245c2616b502698d8b2af5adaad53eb46ee96f62c1` independently current216 match/0 mismatch. Receipt terminal=true/preflight216/staged216/postflight216/run_exit1/owned0,elapsed134874ms,NATIVE_RUN_FAILED соответствует всем трём executed cases в log (2PASS/1FAIL), не timeout/build failure/skip. Approved Run-History3e4cd11f/Invoke52bc8a85/cmd6f7f9100 hashes совпали. Main outer89174 exit1 принят как сообщённое main свидетельство; reviewer handle не опрашивал.

Log подтверждает fresh54TU fixture compile/link PASS, printed PE SHA256 `63a38a88eed81f603a3adf24a31bc23ebe6d9f6857980c3e76fbe59dcebbfcf6`, проверенный reviewed canonical runner до/после cases; это source/log/script-bound PE evidence, не direct guest PE hash reviewer. Login-post400 PASS counts0/1/0/0/0/1, DOM flags74 bridge0/handshake0. GET control PASS: семь успешных документов A/B/C/B/A/B/C, каждый state2/authority1/source_matches1,1 и correlated nav/generation2..8; counts7/0/0/0/0/0. History-post A/POST-B/C также имеют successful200/ready2/authority1/source_matches1,1; Bpost1 подтверждает genuine accepted form value. После Back observed phase3/nav5/generation5/success0/status0/error0/state0/document0/post0/source_matches0,0,detail=document+0x00000000; distinct FAIL history-host-unavailable. Counts2/0/0/0/0/1: server не видел второго POST/лишнего GET/неожиданного path. Failed completion не проходил identity/success admission; текущий host failure наблюдён до fixture close, поэтому прежняя возможность преждевременного history-document-identity не объясняет этот distinct terminal assertion.

Не доказаны: почему nav5 завершился неуспешно (POST resubmission/browser policy/cancellation/response handling/иная причина), какой конечный URL/HTTP response был целью nav5, и выбран ли неверный committed history target. Synthetic document0 означает только отсутствие узнаваемого synthetic marker в прочитанном DOM, не доказательство about:blank/error-page identity. Source-match0,0 означает несовпадение с ожидаемой A, не полный URL. Detail code0 передан production fail как numeric stage detail; он не является доказательством HRESULT S_OK или конкретного transport error. Web_error0 не даёт права на вывод OperationCanceled. В сохранённом логе separator stage/hex искажён text encoding (`document A… 0x00000000`), но stage и numeric code читаются; новой содержательной ошибки из этого не выводится.

Во всех трёх случаях log содержит BrowserExited PASS/serverexit0/fixture terminal; canonical owned cleanup errors отсутствуют, failure GUID сохранён. Wrapper owned0 не является полным независимым profile/browser inventory. Main ещё отдельно проверит actual guest PE/profile processes — здесь этот будущий факт не присвоен. Ни VM/Git/build/tests/code/norm changes, ни installed/UI/hardware/session/full T103 acceptance не выполнялись/не заявлены; единственная запись — этот report append. Production rootcause остаётся открытым; RED достаточно для дальнейшей scoped причинной диагностики, но не для выбора непроверенного production fix.

### T103 history4: actual CDP diagnostic delta and frozen harness SOURCE GO

По запросу main code-reviewer прочитал полную actual three-file delta против frozen history3 C++952123e9/Python0c90192e/runner46b21a17; затем external stage4 wrapper delta и input/source bindings. **Bounded SOURCE GO** на fresh54TU fixture build и пять synthetic cases в одном PE (original3+history-entry+history-entry-same-url). Actionable compile/flow/security blockers в этой delta не найдены. Это test-only API feasibility experiment, не production Back fix/acceptance.

Actual/frozen SHA256 совпали: C++ `aeb0fd948d964a24bbd4de3094151244c92d3b5f266f1463aa54fb6d0ae7d846`; Python `ca11fc3c7c26cdc0419e2ec1d8d9e2560780bcdaee3637e7f151615b8c1f6b11`; runner `4f19af1fe9fc2e6331cc276bbd71501f0f9033c86e1b929a0c7d95f71b51f0d8`. New source manifest `19f2382b50d14ad1dfa7fb271f36e639b0007d5f9769f4e625f53b34dd46ce7f` independently current216/0 mismatch; prior c99dafc3 diff ровно эти три test files. Production/normative changes не входят.

C++359–408 извлекает прежние actions в advanceHistory: non-entry scenarios по-прежнему вызывают host->back/forward; прежние GET/POST page order, accepted form value, authority/source/nav fences и timeout неизменны. Только entry scenarios после C выбирают stored A, после A stored C через Page.navigateToHistoryEntry(entryId); URL navigation fallback отсутствует. ScriptPending удерживает ожидание command completion/GetResults; empty command result проверяется, command completion itself не считается successful document. Новый actual document затем заново проходит прежние DOM/ready/authority/source/current-nav checks и snapshot restored-id checks. Command callback намеренно phase/exit-fenced, не old-generation-fenced, поскольку команда должна сменить generation; snapshot callback имеет generation/nav/phase/exit fences.

Snapshot :411–459 запускается лишь после actual successful document/DOM validation. На return повторяет ready/success/host+core source и strict generation progress; parsed currentIndex/ids finite/nonnegative/integral<=INT_MAX, entries<=128/index in bounds. A/B/C IDs distinct; returned A/C сохраняют exact stored IDs; chosen target присутствует ровно один раз с ожидаемым fixed URL и правильным направлением относительно currentIndex. Same-url fixture GET-A и POST-B имеют одинаковый URL, но разные DOM markers/post flag и entry IDs; Python .index(path) для GET intentionally возвращает A, actual validated POST response возвращает B. Не добавлены fake READY/ACK/native authority или URL-from-message route grant. Existing POST body validation сохранена; server counters exactPOST1/other0 и GET2..4 обязательны для обоих новых cases, server drain прежний.

External Run-History SHA `d796e49d74b922be55955908586f12e0b073806d9503d806ea127951c7afabea`: ровно три manifest swaps prior=c99dafc3/current19f2382b плюс requested five-case array. Invoke SHA `52fb4945df2482178df58c47ea93a9dccf018b1b3462d2eb57b26dd0180dca11`: только Scenarios five-case array. Cmd `6f7f9100…` и synthetic cert/key побайтно unchanged stage3. Fresh stage/input/runtime/source/owned/watchdog/cleanup guards не менялись. Canonical runner после обычного scenario FAIL продолжает остальные cases и возвращает общий nonzero; wrapper по-прежнему сохраняет NATIVE_RUN_FAILED, не объявляет expected RED общим PASS. Future individual case results должны квалифицироваться раздельно. Actual CDP support/return/history restoration пока runtime не доказаны; это назначение experiment. Даже future API-positive не исправит/не закроет host history-post RED.

Stage3 saved qualification уже выполнена выше; main дополнительно сообщил actual guest PE63a38a88 MATCH и GUID profile processes0 через отдельный CheckTerminal. Это main supplemental evidence, не reviewer VM observation. Reviewer не выполнял VM/Git/build/tests/Python/production/norm/code changes; only report append. Requirements construction GO main/Descartes используется в прежнем bounded test-only scope; whole-feature review/checklist/issue/session/installed/hardware/full T103 acceptance не повторялись и не заявлены.

### T103 history4: saved two-entry-case API runtime qualification

Code-reviewer полностью прочитал full run.log278lines/result.json/empty run.err, повторно проверил current216 и approved wrapper hashes. **Bounded API feasibility runtime GO для обоих новых entry cases; overall run остаётся RED4/5, production host POST failure сохранён.** Receipt SHA256 `4d36e272f92e210839306ef4fa91a34fcb330be45cadbdad72d6914a31f66007`; log `d4d479fef449513d322542d9301658ad7d583d0da09af2cf91dd05e2d360f33f`; err0bytes SHA e3b0c442. Receipt terminal=true/preflight216/staged216/postflight216/run_exit1/owned0/elapsed151740ms/NATIVE_RUN_FAILED согласован с пятью actual executed cases и итогом4PASS/1FAIL. Manifest `19f2382b50d14ad1dfa7fb271f36e639b0007d5f9769f4e625f53b34dd46ce7f` independently current216/0 mismatch; Run-Historyd796e49d/Invoke52fb4945/cmd6f7f9100 совпали с SOURCE GO и receipt. Main originalexec46423 terminalexit1 сообщён main, reviewer handle не опрашивал.

Fresh54TU build PASS, один printed PE SHA `271d6e0231da85ba5517d38e2761e30ce1cdb9122328fecc626a239345766487`, canonical script сохраняет PE equality до/после cases. Для history-entry и history-entry-same-url log отдельно доказывает пять successful200/current ready документов A/POST-B/C/A/C: nav/generation2..6, authority1, source_matches1,1. Snapshot entry IDs в каждом isolated case5/6/8/5/8; distinct A/B/C и exact restored A/C, history count1/2/3/3/3. Same-url flag1 только во втором case; approved fixture действительно использует один URL для GET-A/POST-B, различая DOM/post marker и IDs. Оба завершились actual-browser-entry-traversal PASS, fixtureexit0/serverexit0, exactcounts4/0/0/0/0/1. Это реальные CDP entry selection + actual page/authority restoration без второго POST; ни command result alone, ни URL-only lookup не заменяли document proof.

Original controls сохранены в том же PE: login-post400 PASS exact0/1/0/0/0/1, GET history PASS семь документов и counts7/0/0/0/0/0. ORIGINAL host history-post снова FAILED history-host-unavailable после nav5/status0/success0/state0/document0/source_matches0,0, counts2/0/0/0/0/1, как stage3; API positives не подменили host back и не замаскировали общий nonzero. Во всех пяти случаях browser-exit PASS, serverexit0 и завершённый fixtureexit; canonical cleanup errors отсутствуют, failed-run GUID сохранён. Wrapper owned0 не равен отдельной полной GUID/process inventory; direct actual guest PE и GUID inventory main проверит отдельно, reviewer не присваивает эти будущие сведения.

Узкий вывод: reviewed Page.navigateToHistoryEntry primitive способен в этих двух synthetic fixtures восстановить выбранные GET entry IDs через POST entry, включая одинаковый A/B URL, без server POST replay. Это не доказательство production atomicity/gesture semantics/session behaviour и не production fix; первоначальная причина host GoBack failure остаётся не установленной. Нет installed/UI/hardware/full T103 acceptance. Никаких VM/build/tests/Git/code/norm изменений; единственная запись — этот report append.

### T103 history5: bounded cancel-before-start test SOURCE GO

Read-only comparison actual three-file delta against frozen history4 and external history5 wrapper delta: **SOURCE GO for one bounded Windows build/run of login-post400, history-get, original history-post, cancel-before-start.** No actionable compile/flow blocker found. Earlier fixture NavigationStarting subscriber cancels exact B before product subscriber; actual matching NavigationCompleted must report OperationCanceled/status0/unsuccessful, exactly two starts/completions. A must remain ready with unchanged generation/auth callback count and real A DOM/host+core source. Actual shim update click dispatches exactly one native update handler under retained generation, proving more than surviving bootstrap flags; no installer or forged nonce/readiness. Subsequent C requires successful200, third start/completion, increased generation, second auth callback and real C bootstrap. This covers already-cancelled-before-host only, not cancellation by a later subscriber or the cause of original POST RED. Current production still ignores args.Cancel; proposed production guard is not implemented/accepted by this test-only gate.

Current/frozen three files equal: C++ `8d42bb61f727f9bba0807f472efff526d90c6bcbad6acb7c919c386d8a893303`; Python `ebc37aea02c14227e2a5ffd60f35d8f2f5d8f526b4b757e9c84b1e81c3694300`; runner `66237bee9798ed52233b8402c65f4858ebc8bf17ea948148de67dd4870309d8c`. Manifest SHA `a305e0d933902d685228492dbca658c2b3e3a83c7a26adf035a50bd19024a8f1` independently current216/0 mismatch; prior SHA19f2382b matches history4. Canonical new case allows only cabinet GET2..3/other0/POST0; original cases unchanged. External wrapper changes only prior/current bindings and requested four-case arrays; existing source/runtime/input/owned/watchdog/cleanup guards remain. Original POST RED and overall nonzero are not masked. Build/runtime/cancellation event behaviour remain future evidence; no VM/Git/build/tests/code/norm changes performed, only this report append. No full T103/session/installed/hardware acceptance.
