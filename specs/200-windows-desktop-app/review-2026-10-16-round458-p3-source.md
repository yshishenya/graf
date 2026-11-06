# F200 T116/P3 — независимый source/Ponytail review round458

Дата: 2026-10-16.

## Решение и граница

**GO для проверенной узкой области исходников round458. P0: 0; P1: 0; P2: 0.**

Это source-review допуска публичной защищённой записи и применимых callers,
а не финальный runtime GO или implementation-completion. Green1 завершился
ошибкой теста; уточнённый тест green2 прочитан, его финальный результат здесь
не принят. T116/P2/P3, T117/T118/T120, установленное приложение, физические
устройства, x64, упаковка и выпуск этим решением не закрываются.

Единственная проверенная рабочая копия:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Проверялись незакоммиченные исходники, поэтому одного HEAD недостаточно:

| Файл | SHA-256 проверенного содержимого |
|---|---|
| `apps/windows/RecApp/Recording/NativeCapture.h` | `6347083384e8628d9f49a9b729a14fc3e574a39b566f7fd9b1c7960531d5b037` |
| `apps/windows/RecApp/AppMain.cpp` | `eb8a3dcaa6ea50965ab4cd6723a500451c6803d69cb96f623163afeb64c69a29` |
| `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp` — уточнение green2 | `4a728e64da1770e171de3de408384a5b373cecb82cc47d5b9c53b34778dbe94e` |

Эти три значения совпадают с `green2/source.sha256` в предоставленном каталоге
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB`.
Production `NativeCapture.h` и AppMain не изменились между прочитанными
снимками green1 и green2. Тест green1 имел другую сумму:
`b5627e8b2ada65dc0c0c50d922c4af96fd770a5dcfe01f74067455dd62dbbde0`.

Режим проверки: чтение исходников внутри действующего high-risk-product slice;
единственное разрешённое изменение — этот отчёт. Прочитаны main `AGENTS.md`,
карта guidance, применимая классификация Spec Kit, `plan.md:2560–2610`, решение
quality round458, навыки `code-reviewer` и `ponytail-review`. Повторная
инвентаризация исторических checklists не выполнялась. Сборки, запуск тестов,
VM, GitHub и commits не выполнялись; код, тесты, checklist/spec/plan/tasks
не изменялись.

## Проверенные потоки и основания GO

Пути и номера строк ниже относятся к указанной рабочей копии.

| Область | Проверка и результат |
|---|---|
| Принятое состояние очереди | `NativeCapture.h:334–343`: общий helper требует ready/adopted, startup/current value, ненулевую generation и queue context, отсутствие storage/queue errors, reconciliation, short-discard, занятой команды и непринятого результата. Его callers держат `StorageStartupWork::mutex`. Текущее значение и generation публикуются при adoption в `2853–2883`; пока worker завершает передачу, inFlight/результат удерживают запрет. Проверка не выдаёт native authority. |
| Свежая readiness | `NativeCapture.h:407–430`, `470–482`, `1486–1503`: public Record, recordingReady и текст состояния используют снимок с актуальным protected storage state. Кэш `readiness_` остаётся источником аппаратных предпосылок. Выставление storageWritable внутри private continuation в `1908–1911` по-прежнему допускается только после собственного prepared writer, не из caller boolean. |
| Допуск после COM и повторный Start | `NativeCapture.h:1844–1891`: после metadata probes/потенциального вложенного UI request повторно проверяет complete/stop/terminal/cancellation под mutex, а также shutdown/exit/update/deletion continuation. Отдельные indicator/pending/controller session gates не дают второй Start. Даже если состояние изменилось во время probes, отказ не переходит к обычной записи или синхронной factory. |
| Ручной AppMain | `AppMain.cpp:2478–2500`: проверка complete, refreshReadiness, повторный canStartRecording после возможного UI-входа и затем тот же public record. Отдельного пути, использующего старый boolean как разрешение storage, нет. |
| Автоматический AppMain | `AppMain.cpp:2141–2153`, `2207–2238`: prerequisites получают value readiness; только собственный связанный starting session освобождается от active-recording blocker. Финальная проверка сохраняет generation/session, detection evidence, permission, UI/Stop и interaction epoch. `AutomaticRecordingPolicy.cpp:305–337` подтверждает binding и acceptStart. Общий helper не запрещает свой prepared Start по recordingPending и не запрещает независимых readers. |
| Обновление | `NativeCapture.h:1323–1328`, `1386–1409`, `2936–2954`; `AppMain.cpp:2333–2346`, `2402–2414`: admission закрывается до beginInstall, localQueueComplete сохраняет принятый полный value после чистого stop/terminal, а updateWorkDrained отдельно ждёт native terminal/thread и остальные операции. Ошибки и непринятые результаты helper не превращает в complete. Cancel update требует повторной startup validation (`2851–2852`, `2931–2934`). |
| Reservation → factory → первый блок | `NativeCapture.h:2503–2521`, `2611–2618`, `2636–2707`: worker перепроверяет настоящий owner/context/generation, сохраняет reservation, ждёт adoption и лишь затем вызывает owner overload `V5LocalRecordingWriter::open`. Actual writer/prepared/cancellation/epoch/session проверяются в `1893–1916`. `WindowsCaptureSessionController.cpp:60–91`, `203–243` удерживает delivery закрытой до готовности workers и финального guard. Новый helper этот порядок не заменяет. |
| Нет plaintext fallback | Public Record всегда идёт в beginProtectedRecording. `NativeCapture.h:510–522` возвращается из protected upload ветки; отсутствие принятого protected state не позволяет пройти localQueueComplete к старой очереди. Аудио sink в `2986–3014` требует retained prepared/started writer. Нового обхода через legacy queue, публичный bool или private test continuation не найдено. |
| Исходный владелец | `NativeCapture.h:443–464`, `1857–1862`, `1898–1916` сохраняют различие unknown/signedOut/confirmed и epoch/cancellation. Новый допуск не требует login/HTTP и не присваивает неизвестной записи текущего владельца. Это проверка сохранения соответствующего потока, не новая приёмка всей ownership/upload системы. |

## Тесты и фактические журналы

RED прочитан в `red/actual-test.log:11–13`: настоящий public Record дал
`accepted=0 state=0 reason=7` (`storageUnavailable`), затем упал assert ожидания
accepted starting. Успешная сборка RED с кодом 0 сообщена основным агентом;
собственная сборка reviewer не выполнялась.

`green1/actual-test.log:11–27` подтверждает обе основные ветки:
unknown (`V5_CASE=0`) и signedOut (`V5_CASE=8`) получили public accepted
starting, прошли 3000 frames, finalization, `cold_read_verified` и `done`.
До `done` в соответствующем тестовом снимке находятся проверки update closure,
drain и clean queue. Затем прошли cancellation cases 0/1 и упал прежний общий
`!capture.localQueueComplete()` в mode2. Поэтому **green1 — не GREEN всего
NativeProtectedPendingStart**; build0/test8 сообщены основным агентом.

Уточнённый source green2 проверен отдельно:

- `NativeCaptureStorageIntegrationTests.cpp:6094–6110`: deferredStart вызывает
  настоящий `capture.record`; generated workers устанавливаются после accepted
  starting до первого pollHealth; повторный public Record отклоняется.
- `6233–6242`: после финализации проверяется complete, затем закрывается update
  admission, Record отклоняется, ожидается drain и сохраняется clean complete.
- `3628–3738`: все шесть pendingCancellation variants используют public record
  (`3653–3658`), а workers подставляются до polling. Сохраняются duplicate,
  Stop/epoch/update/exit, job pressure, отсутствие кадров, освобождение session,
  холодная проверка generation/строк/package и освобождение памяти.
- Mode2 — отклонённый StartGuard после успешной reservation/finalization:
  допускаются два generated device starts и один guard, но ноль кадров;
  сохраняется quarantined unknown row и generation 3. Новый complete=true
  в `3707–3709` соответствует принятой очереди, а не успеху capture. Остальные
  пять режимов сохраняют отрицательную completeness; общего снятия запрета нет.
- `6803–6807`: тот же target объединяет unknown, signedOut, шесть cancellation
  cases и контроль освобождения памяти. Отдельный старый private beginPending
  в `3740–3751` остаётся узкой проверкой отказа submit без storage worker;
  он не подменяет публичные положительные сценарии.

В уточнении тестов дефектов P0/P1/P2 не найдено. Final native receipts green2
и применимых регрессий на финальном source/PE остаются за основным агентом.
Остальные старые global-false asserts не проверялись как выполненная работа
и не признаны корректными или согласованными автоматически: каждое ожидание
нужно сопоставлять с фактическим принятым/ошибочным/непринятым состоянием.

## Ponytail

Lean already. Ship. Обязательных cuts в узком изменении нет; общий helper и
value snapshot достаточны, новая абстракция, зависимость или product test hook
не нужны. Это вывод о сложности исходников, не разрешение выпуска.

## Узкое дополнение — controller Record при аппаратном отказе, 2026-10-16

**GO для исходников этого дополнения. P0: 0; P1: 0; P2: 0.**
Это независимая проверка изменения guard и совместимости его callers, до
финальной runtime-приёмки. Не GO всего P3, не закрытие default/deletion
регрессий и не implementation-completion. Предыдущие разделы остаются
историческим снимком первоначального review.

Рабочая копия и HEAD прежние:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Решение привязано к прочитанному содержимому, а не только к HEAD:

| Файл | SHA-256 |
|---|---|
| `apps/windows/RecApp/Capture/WindowsCaptureSessionController.cpp` | `f1e21f50bc2ba1ef2e54df0f9d0c92ac8f489993d7d225d1cd49cfed93717125` |
| `apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp` | `2b46a0a3281da918ecaede370a7e14a2d760a29ba01c4dee416fcda8f3f8b25b` |

Суммы `NativeCapture.h` и `AppMain.cpp` повторно сверены и совпадают с
первоначальным снимком выше. Прочитаны уточнение `plan.md:2612–2622` и
независимое requirements/analyze дополнение quality report от строки 259.
Исторический diff контроллера против HEAD не трактуется как новое изменение:
предмет этого дополнения — только условие в `record`, строка 57.

### Основания решения

- `WindowsDesktopContracts.h:119–126`: `accepted()` означает не только
  разрешённый запуск. `WindowsDesktopSession::block()` возвращает принятый
  переход в `blocked`; `prepareRecording()` сохраняет первый readiness blocker
  и публикует невидимый indicator. Новый guard требует одновременно accepted
  и `starting`, поэтому возвращает этот blocked result без потери status/reason
  и без вызова launch. Rejected, включая повторный Record, также возвращается
  без запуска; принятый `starting` идёт по прежнему пути.
- `WindowsCaptureSessionController.cpp:60–91,203–243`: проверка readiness внутри
  launch, `awaitingPreparation_`, готовность обоих workers, StartGuard и повторная
  проверка состояния перед открытием audio delivery не изменены. Аппаратный
  отказ не получает обхода этих gates; повторный Record не заменяет bound guard.
- Единственный production caller controller `record` —
  `NativeCapture.h:1923`. Его ветка `startPreparedRecording` по-прежнему требует
  собственный prepared writer, актуальные session/epoch/cancellation и native
  factory ACK. При `idle/blocked/failed` она запрашивает защищённую финализацию
  по состоянию (`1933–1935`), независимо от `accepted()`: сохранение accepted
  blocked не теряет этот cleanup. Public pending-start отдельно использует
  `prepareRecording(nullptr)` и прямой `launchPreparedRecording`; этот путь
  и проверка результата в `pollHealth:590–591` не меняются. Нет нового plaintext
  fallback, синхронной factory, ослабления owner/native authority или reentry.
- Ручной AppMain (`2478–2500`) сохраняет свежие prerequisites и повторный
  admission; автоматический (`2207–2238`) признаёт успешным только accepted
  `starting/recording`, а не любой accepted blocked. Update/exit admission и
  повторные проверки private continuation остаются прежними. Прямые тестовые
  callers в `CaptureFaultStateTests.cpp` и `NativeRecordingOfflineWebViewTests.cpp`
  сохраняют starting/start-failure/duplicate ожидания; вызовы public Record в
  startup/storage integration тестах не создают второго production пути.
- Новая прямая regression в `CaptureFaultStateTests.cpp:1517–1530` проверяет
  accepted blocked с `microphonePermissionDenied`, невидимый indicator, ноль
  batch/finalizer callbacks и отказ повторного Record. Первый blocker для
  `ReadinessInputs{}` действительно permission denied. До поправки launch
  отвергал blocked как неподготовленный, и первая проверка accepted падала бы;
  тест непосредственно различает старую и исправленную семантику. Это не
  самостоятельное доказательство native shutdown/drain. Дополнительного case
  по реальному дефекту не требуется: такого дефекта в данной области не найдено.

Пересмотр меняющихся per-mode отрицаний и deletion tests не выполнялся.
Предыдущую классификацию assertions нельзя использовать как финальный oracle:
после завершения одной операции может уже идти следующая, а принятие storage
ACK требует polling. Ни сообщение о green7, ни это source-решение не заменяют
финальные actual receipts на зафиксированных исходниках/PE. Сборки, тесты, VM,
GitHub и commits reviewer не запускал; изменён только этот отчёт.

Ponytail: Lean already. Ship. Cuts нет — достаточна одна проверка `starting`,
без новой абстракции, изменения общего `accepted()` или test hook.

## Read-only sidecar — state-specific assertions, 2026-10-16

**GO для перечисленных ожиданий в исходниках; P0: 0 / P1: 0 / P2: 0.**
Проверены только ShortDiscard, PlaybackConsumer, InspectionPreparation/
ActiveStop и CLI protected-scheduler, включая stop-prepared и отказные cuts.
LostPoll/memory RED, отдельное расследование drain и остальные assertions не
проверялись. Это не runtime GO: ветки reviewer не запускал.

Рабочая копия и HEAD прежние. SHA-256 прочитанного
`apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`:
`7bb7aaab24894083e00b4705e05584e9cf6290b178c29e6612d1609d1bd08b8d`.
Production `NativeCapture.h` по-прежнему имеет SHA-256
`6347083384e8628d9f49a9b729a14fc3e574a39b566f7fd9b1c7960531d5b037`.
Номера строк ниже относятся к этому снимку; Q = localQueueComplete,
W = readiness().storageWritable.

| Ветка / проверка | Требуемое ожидание и основание |
|---|---|
| `protectedNativeShortDiscard`, `4795–4796`; CTest `NativeProtectedShortDiscard` | В достигающих assertion режимах 0/1/2/3/4/5/7/8: Q=true после успешного retirement ACK и удаления; W=true только 0/1/2/3, W=false при update/exit/shutdown 4/5/7/8. recordingReady=false не противоречит W=true: аппаратные prerequisites не публиковались в readiness_ как готовые. До этого остаются проверки finalizing, отсутствия уведомления до adoption и незавершённого short discard. Режимы 6/9 не достигают этого assertion и здесь не оценивались как drain-сценарии. |
| `protectedPlaybackConsumer`, `5833–5834`; CTest `NativeProtectedPlaybackConsumer` | Q=true/W=true: принят reservation ACK (`5825`), настоящий factory завершил preparation, retained playback clone уже отпущен и playback terminal. Prepared, но не запущенная recording не означает неполную очередь. Выход из аккаунта не закрывает admission новой unknown-owner записи. |
| `prepareConcurrentRecording`, `6404–6405`; CTest `NativeProtectedInspectionPreparation`, `NativeProtectedInspectionActiveStop`, CLI `--protected-scheduler-stop-prepared` | Q=true/W=true/expiryCalls=0 после собственного recording ACK generation 4→5 и factory preparation. Параллельная old-package inspection либо HTTP flight не тождественны занятому queue command; helper не требует отсутствия recording/upload/readers. |
| `verifyRows`, `6495–6496`; CTest `NativeProtectedInspectionActiveStop` | Q=true/W=true для scheduled после раздельных recording ACK 5→6 и upload-result ACK 6→7; для durable — после startup adoption generation 7. До первого вызова уже есть pollUploads до !uploadsBusy; строки old=retry/attempts1 и new=pending/attempts0 согласованы с единственным HTTP 503. |
| `6672–6673`; CLI `--protected-scheduler` | Q=true/W=true после upload-result adoption generation 4→5. Предыдущий успешный prepare generation 3→4 не подменяет этот ACK. |
| CLI `--protected-scheduler-stop-prepared`, `6634–6661` | Сохраняются result generation 5→6, expiryCalls=0, retired upload и cold rows retry/capture_prepared. Здесь нет blanket Q/W inversion: shutdown обработан до холодного чтения; отдельное расследование drain не дублировалось. |
| CLI `--protected-scheduler-ambiguous`, `--protected-scheduler-not-committed`, `6563–6627` | Ошибочный ticket не становится committed из-за physical readback. Сохраняются generation 5/4 соответственно, expiryCalls=0 и различие durable retry/pending. Нового безусловного Q=true/W=true в этих ветках нет. |

Проверка риска автоматически поставленной следующей операции:
`NativeCapture.h:2889–2906` действительно может установить commandReady/inFlight
для account recovery; тогда пассивное ожидание Q не принимает новый ACK.
Однако в перечисленных местах такого непринятого продолжения не найдено:

- ShortDiscard уже принял retirement ACK через pollUploads; поздние три polling
  ticks сохранены. В mode3 пара token→empty сбрасывает protectedRecoveryEpoch;
  оставшийся recovery intent без currentAccount не запускает upload.
- Playback использует pollAccount без запуска upload intent, затем logout
  сбрасывает protectedRecoveryEpoch; после reservation ACK остаётся только
  завершение factory, которое само снимает inFlight (`2732`).
- Inspection и scheduler поглотили protectedRecoveryEpoch/pendingRecovery при
  принятии первого requestProtectedUpload (`1686`). Recording preparation не
  создаёт нового recovery intent; последующие конкретные result ACK приняты
  явно. Display/inspection сами по себе не выставляют queue inFlight.

Поэтому заменить эти ожидания на отрицательные или механически добавить новые
pollUploads повсюду оснований нет. Указанное GO относится к прочитанному потоку,
а не к любому будущему случаю с Q=false: новый command/result нужно различать
по ticket и принимать его ACK polling, а не просто ждать.

Код, тесты, задачи и маркеры не изменялись; VM, сборки и тесты не запускались.
Изменён только этот отчёт. Ponytail: Lean already. Ship. Cuts нет.

## Read-only sidecar — lostPoll memory RED, 2026-10-16

**Диагноз не закрыт; runtime GO отсутствует.** По чтению нет доказанного
нового P0/P1/P2-дефекта; ниже конкретные проверяемые кандидаты, не утверждение
об установленной утечке. Equality и timeout не ослаблялись.

HEAD и рабочая копия прежние. Проверенный тестовый source SHA-256:
`427bb1f32b3774eb5b5d1734c91ea767c8e06b7cebc8f1d7df9c30fb62ac3b18`.
`NativeCapture.h` неизменён:
`6347083384e8628d9f49a9b729a14fc3e574a39b566f7fd9b1c7960531d5b037`.
`ProtectedCustodyReader.cpp`:
`2bf35e4b9390f7c5f2dc3915fe43a72bd83a0dcf4a270dda309532415393cd3f`.

Прочитан только релевантный фрагмент сохранённого green8 source и строки
17–31 actual-test.log. Green8 snapshot теста имеет SHA-256
`7bb7aaab24894083e00b4705e05584e9cf6290b178c29e6612d1609d1bd08b8d`:
normal и staleEpoch дошли до done; lostPoll достиг frames_3000 и упал на
точном сравнении памяти в строке 6237. **before.reset() в green8 уже был,
а weak observation ещё не было.** Ни удержание before, ни новая weak-ссылка
не являются объяснением исходного green8 RED.

### Цепочка владения и локализованный кандидат

`NativeCapture.h:364–379`: destructor закрывает admission, выставляет stop,
дожидается acquisition/dispatcher, уничтожает controller, передаёт finalization
в storage worker и повторно сигнализирует stop. Worker получил отдельный
shared StorageStartupWork через thread argument; обратной сильной ссылки
на NativeCapture в этом потоке не найдено. Generated producers держат лишь
ссылки на capture/emit и заканчивают работу до controller reset.

**Первый кандидат при worker_released=0 — незавершённый native finalizer,
а не отсутствующий UI ACK.** `integrationFlush:272–284` применяет
pauseAfterFlush к любому успешному FlushFileBuffers, не только queue role.
lostPoll не квалифицирует этот cut через startOwnerFlushRole. Он может быть
достигнут ещё на canonical checkpoint (`V5LocalRecordingWriter.cpp:715`),
перед WAV/AAC, semantic inspection и записью queue result. Поэтому отпущенный
cut и выполненный owned.reset не доказывают ни завершения writer finalize,
ни уничтожения настоящего store owner.

Конкретная точка ожидания — `NativeCapture.h:2488`, finalizer.get(); writer,
timeline и native proofs освобождаются только после него (`2491–2501`).
Для утверждения о deadlock нужен фактический стек/последняя завершённая стадия;
по исходникам сам deadlock не доказан. После queue-result publication ожидание
`2645` имеет условие resultAdopted **или stop**. В lostPoll stop уже выставлен,
так что возвращать UI polling как обязательное условие teardown оснований нет.
После finalize worker снимает recording/inFlight (`2818–2822`), выпускает
owner и active lease перед terminal (`2827–2841`).

### Альтернатива: static reader retention либо учёт времени жизни

Единственный найденный релевантный process-wide charged cache —
`ProtectedCustodyReader.cpp:18–31`: ReadCache содержит CustodyBytes и сырой
owner pointer, но не shared_ptr на native state. Последний ReaderState должен
очистить его при уничтожении (`67–70`). Очистка использует clear/shrink_to_fit;
bad_alloc при shrink проглатывается. Проверяемый остаток после worker release:
живой ReaderState/MF Clone удерживает payload cache либо capacity осталась
после неуспешного shrink. Это кандидат, а не доказанное событие green8.
Native MF/DPAPI allocations сами по себе не входят в CustodyOwnedMemory;
их следует связывать с удержанным CustodyAllocator-объектом, а не с RSS.

Тестовые Fixture/session/accountWire/second/hardware не имеют CustodyAllocator
payload. Ссылка reservation на строку before не владеет очередью. Сброс before
уже проверен. Новая weak StorageStartupWork действительно удерживает charged
allocate_shared control block даже после expired(), но текущий тест сбрасывает
её и завершает область временного retained перед неизменённым equality.
Следовательно новая диагностика не должна сама удержать этот charge.

### Минимальный проверяемый путь для main

1. Принять новые ABANDONED_WORK/ABANDONED_MEMORY scalars с текущего source,
   сохранив исходное equality/180s. Одного сообщения worker_released=0 после
   десятисекундного наблюдения недостаточно для окончательного диагноза на 180s.
2. Если work остаётся жив: различить resultReady/command kind и
   recording.finalizing/terminal. При resultReady=0 и выполняющемся finalize
   посмотреть стек storage worker и async finalizer у get/checkpoint/MF;
   при resultReady=1 проверить reconciliation/реальное освобождение, а не
   предполагать необходимость ещё одного UI ACK при stop=1.
3. Если worker_released=1, но equality всё ещё RED: смотреть точную дельту
   usedBytes и ReadCache owner/size/capacity после сброса weak-наблюдений.
   owner!=nullptr указывает на ещё живой ReaderState; owner==nullptr с payload
   capacity — на retained cache capacity. Только пустой Debug proxy уже входит
   в idleOwnedBytes; это не разрешение принять дополнительный остаток.
4. Нативное зависание/утечку отличать от диагностического accounting по
   освобождению strong state, последнего Reader/Clone и charged control block.
   Не заменять equality широким пределом и не увеличивать timeout.
   Для привязки остатка именно к lostPoll полезен scalar usedBytes при входе
   в case до создания capture: current worker weak не наблюдает более ранние
   cases процесса. Это диагностическое сравнение, не новый допустимый baseline.

VM, сборки и тесты reviewer не запускал; код/тесты/checklists/plan/tasks не
изменял. Дополнен только этот отчёт. Ponytail: новых абстракций или product
hooks для диагноза не требуется; достаточно существующих observations и
точечной проверки стадии/стека у основного исполнителя.
