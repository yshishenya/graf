# Round448 — bounded source correctness / Ponytail review

2026-10-16. Existing high-risk-product T116 / #7444.
Repo `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

## Текущий вердикт

**Request changes: 1 P1 (alias fence до effectful B); P0 0. Source GO пока нет.**
Requirements GO448 не отозван: проблема в неполной реализации существующего
fence, а не в новой продуктовой неоднозначности. Ни whole T116, ни quarantine
UI playback, ни installed/hardware/release этим review не принимаются.

## P1 — recoveryRowCurrent не исключает другие queue aliases

Место: `Recording/NativeCapture.h:1476–1480`, использование :2218–2227.

Новый helper находит exact expected row через sameUploadIdentity,
safeReason/updatedAt/no-server и проверяет deletionBlocks только найденной
строки. Условия localId==session==directory и exact confined packageDirectory
проверяют собственную строку, **не отсутствие другой строки, ссылающейся на
тот же package/path/IDs**. Shared protected decoder не запрещает все такие
cross-row aliases: distinct local IDs могут иметь тот же directory/session/path.

Следствие: genuine owned A capture_prepared row плюс другая строка (включая
owner B/server/deletion truth), ссылающаяся на тот же unfinished package,
проходят этот helper. prepareRecovery/openUnfinished могут приобрести пакет,
а finishRecovery опубликовать finalizing/media/playback/manifest/sealedDegraded,
несмотря на конфликт authority. Изменение файла произойдёт до какого-либо
normal queue promotion gate.

Существующий `ProtectedCustodyMetadata.cpp:1009–1029`
recordingReservationConflict отвергает aliases по case-insensitive path и
directory/local/session IDs, включая чужого owner и non-rejected deletion
operations. Прежний recoverRecordingReservation вызывает его перед normal
promotion (:1127 onward). Новый B не проходит через этот путь; readPackage и
openUnfinished проверяют native/package integrity, но не заменяют row alias
policy. Поэтому зелёные happy-path и равенство собственных трёх IDs этот P1
не закрывают.

Минимальное исправление: до prepareRecovery применить эквивалентный existing
reservation-conflict fence ко **всей свежей очереди**, включая Windows
case-insensitive/confined path comparison и deletion targets. Предпочтительно
переиспользовать имеющуюся domain policy, не вводить новую public capability
или глобальный запрет legacy rows. При дальнейших conflicts cancellation
должна сохранить тот же scope. Нужен genuine cold alias fixture: обе строки
сохранены в BOTH queue, recovery достигнут/отказал, полный root/queue bytes
неизменны; A не назначается B. Runtime этого случая сейчас не проверен.

## Что в production delta проверено без дополнительных findings

- Private prepare/finish разделяет существующий recover до full
  inspectUnfinished/history/Tree verification. StoreOwner остаётся storage
  worker; executor получает настоящий terminal writer, а не arbitrary pair,
  Snapshot/boolean proof или synthetic V5WriterResult. Public recover
  последовательно использует обе private части.
- finalized_ устанавливается до acquisition; recoveryPending_ снимается перед
  первым finish attempt. Этот объект не принимает capture/privacy и не
  разрешает повторный effectful finish. Existing error mapping и B content
  construction не заменены другой реализацией.
- Пробный readonly pair reset до writable acquisition. recoveryWriter
  перемещается под work mutex на executor; finish выполняется вне mutex.
  Игнорируемый terminal result уничтожается на executor; local writer и pair
  очищены до resultReady, включая proceed=false/cancel/refusal. B не становится
  recoveryProof, не создаёт recovery queue ticket и не получает HTTP authority.
- Wait predicate, networkPending и resultReady handler согласованно допускают
  no-proof/cancelled recovery при recording/inFlight. Следующий loop при
  commandReconciliation отменяет recovery; done очищает token только после
  executor release. submitProtectedDeletion отменяет recovery для intent/purge,
  purge отказывает до фактического token retirement. Ранее найденный wait cycle
  по чтению этих ветвей разорван; это не runtime proof ambiguous сценария.
- Обычный sealedNormal proof по-прежнему не dispatch при live recording или
  inFlight; без commandReady нет повторного исполнения старой команды.
  Original owner/status/reason/updatedAt и no-server проверяются fresh;
  unrelated generation не подменяет exact-row equality.

## Проверка tests / границы доказательств

В current test TU уже **4** unfinished modes, не только первоначальные 3:
capturing→degraded; finalizing→degraded; started-output refusal; held canonical
read→shutdown cancellation и отсутствие drain до release. Birth owners
освобождены, account B действительно resolved до startup, preserved row A и
canonical/service queue сравниваются по bytes/SHA. Positives требуют cold
full ProtectedInspection, trustedPrefixFrames=100, duration=1000 и decoded AAC.
Started-output и held-read cancellation требуют прежний capturing; для mode3
добавлено полное равенство root. Memory oracle сначала сравнивает собственный
entry baseline, после full cold inspection — established exact idle baseline.

Общий protectedRecoveryLivePlayback(true) использует genuine unfinished old
package и настоящий owned pending neighbor. Проверяются actual held read,
Start ACK/g5/100frames, resultReady при live recording, muted playback/seek,
unchanged ticket/projection, EOS finish g5→6 и cold old degraded/quarantined.
Default normal variant сохранил g6→7 recovery ticket и normal assertions.
Но **old cut освобождён до Stop**: этот тест не доказывает EOS новой записи
до release старого read. Ambiguous finalizer/deletion и Stop-before-release
заявлены main как ещё не выполненные и не принимаются этим отчётом.

Dispatch нового CLI перемещён после CRT no-dialog setup и общей начальной
memory warm-up. Это полезное исправление test harness, не product change.
Новый CTest registration serial/TIMEOUT240; отсутствие runtime skip/полный
набор regressions проверяются отдельно по terminal receipt.

## Bounded primary evidence, прочитанное во время review

`green2/result.json`: terminal true, build0/test0, 18369ms, postflight216,
saved owned_processes0, PE
`8eb2a17bfcef9e7a926693e65d1af1ae95931e69978be497f00497e38a05a314`.
Build log содержит actual NativeCaptureStorageIntegrationTests.cpp compile.
test.stderr.log содержит mode0/1 actual_phase3, mode2/3 actual_phase0,
4 cold/drain markers, actual_result_ready/live/g5, muted_play_seek,
EOS/cold-three-owned и unfinished old-degraded/quarantined markers.
Содержание сопоставлено с указанными выше assertions, а не только со строками
PASS. Это saved evidence: actual guest PE/CIM заново не читались; VM commands
не запускались. Final seven-regression receipt этим review ещё не принят.
RED4/ранние ошибки dispatch/dialog и исторические candidates не засчитаны
как PASS и здесь отдельно не переквалифицировались.

## Source identity и baseline

Current **216/216** совпали с green2/source.sha256, SHA
`dae37e431654a45499c79be66a674dd38cdaad50e4989c7f6d0c01ddbebf4ea2`.
С manifest447 green4 совпадают 211/216 inputs; отличия ровно следующие пять.
Все пять retained red copies проверены по red manifest. Три production red
copies совпадают с447. Важно: red test/CMake уже содержат tests-first448,
поэтому red сам не является original447 baseline для этих двух файлов;
new function/CLI/registration прочитаны целиком отдельно от red→current diff.

| Путь относительно apps/windows | Current SHA-256 |
| --- | --- |
| CMakeLists.txt | `58678437fa96bb69f714e901522fb9b9558b1687f6761ffe32864b357f4e73c7` |
| RecApp/Recording/NativeCapture.h | `543550ad48a71ef792653f3dd94644594cd804846f2435842fe06ca3c1baac58` |
| RecApp/Recording/V5LocalRecordingWriter.h | `4d5946e88622230f4e9567d0dc1bb95baaae526ea207a4a9aa58b4c063f1616a` |
| RecApp/Recording/V5LocalRecordingWriter.cpp | `3d1b295a815fb73da492dcc051bdac45683833c303b0cd8ee4c1fb00cfe82d12` |
| Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp | `a2137569e0ed46b3490b5f7c42ae8e8cf46ccef333a96fd0b51e44ec218194cf` |

## Ponytail / действия reviewer

Lean already. Ship. — только заключение прохода по переусложнению, **не**
разрешение принимать исходники с P1 выше. Безопасных удалений не найдено:
нет нового pool/dispatcher/ledger/format; private split, once-only flag и
общий параметризованный live test обслуживают действительные разные границы.
Нужную conflict policy следует переиспользовать, а не строить общий framework.

Создан только этот отдельный reviewer report. Code/tests/CMake, нормы/tasks,
checklist markers, Git index/GitHub/VM не менялись. Reconstructibility и cleanup
не квалифицированы: запрос делать их при отсутствии findings сейчас не
выполнен из-за P1; source copies должны сохраняться до разрешения finding и
отдельной terminal qualification. Никакой cleanup GO не выдан.

## Append-only checkpoint — GREEN6 / закрытие P1 и текущие ограничения

2026-10-16. Этот раздел обновляет вердикт выше, не заменяя исторический
Request changes и failed evidence. **P0 0 / P1 0 для прочитанного production
delta; прежний alias P1 закрыт. Bounded production source GO.** Остался один
P2 точности/устойчивости нового тестового оракула, описанный ниже. Полный
Round448 runtime acceptance и cleanup GO пока не выданы: семь регрессий
GREEN6 на момент этого checkpoint ещё не квалифицированы reviewer.

### P1 fix: прежняя policy без новой authority

- `ProtectedCustodyMetadata.cpp:1008` экспортирует ровно прежний
  recordingReservationConflict; удалены anonymous namespace и defaultarg у
  definition, defaultarg находится в declaration в
  `DesktopUploadQueueService.h:244`. После этой нормализации функция побайтно
  равна red5; SHA-256 `eadd880db137687734bf45c2f3af546ca146f3d3683486bdf57e11fde70f76df`.
  Прежние три metadata callers сохранены. Новый declaration Windows-only,
  возвращает domain refusal, не выдаёт package/account/effect authority.
- `NativeCapture.h:1471–1482` использует эту policy поверх exact expected row:
  status/reason, три IDs, owner pair, sameUploadIdentity, updatedAt и отсутствие
  server truth не заменяют cross-row/deletion fence. Существующая policy теперь
  отвергает и Windows case-insensitive alias пути, и conflicting IDs/deletion.
- Fresh acquisition применяет helper после настоящего readQueueValue; loop
  повторяет тот же gate при retained recovery. Проверка путей выполняется вне
  work mutex (:1993–2001), исключение отменяет recovery, не разрешает его.
  Нативные references/proof не передаются UI. Дополнительного waiter cycle
  или ослабления sealedNormal admission в этих изменениях не найдено.
- Mode3 теперь обслуживает отдельный настоящий metadata ACK через existing
  pollStorage во время ожидания cut. Сохранены actual held-read observation,
  cancelled token, !terminal/!shutdownWorkDrained до release, cold phase и
  полный unchanged-root oracle. Это допустимое исправление harness, не отказ
  от проверки drain.

### Квалифицированная пара RED6 / GREEN6 primary

RED6 manifest `331d225cd155cf253b6027b0372ed0242fa2f95b00c2cdfbfc2e55b4b85f21ed`:
build0, isolated `--protected-start-owner-recovery-alias`, exit3, 3031ms,
postflight216, saved owned_processes0. Лог действительно достиг mode4:
`actual_phase=3 expected_degraded=0`, затем assertion capturing. Это настоящий
отрицательный результат pre-P1 production, не compile/dispatch failure и не
недостигнутый alias case. RED6→GREEN6 manifests отличаются ровно в трёх
production files: NativeCapture.h, ProtectedCustodyMetadata.cpp,
DesktopUploadQueueService.h. Test TU/CMake/V5 одинаковы.

GREEN6 manifest и текущие source inputs **216/216**:
`307500e82c7005c92ef664302c2dfc22a648a2ca93712eb8a659bd147eb92c3f`.
`green6/result.json`: terminal true, build0, test0, 18965ms,
postflight216, saved owned_processes0. PE
`997cf0d2168b5b165be49acc1f1b363a37b8867a165ccdfd2d4691ea427f62be`;
build.log содержит actual NativeCaptureStorageIntegrationTests.cpp compile.
Это не GREEN5 PE: одинаковый source manifest не доказывает одинаковые PE.
Следующие семь регрессий должны быть связаны с GREEN6, не унаследованы от
GREEN5 или раннего candidate.

Прочитан весь GREEN6 stderr и сопоставлены assertions:

- Mode0 capturing и mode1 finalizing реально стали sealedDegraded, проверены
  cold full inspection/trusted 100 frames/duration1000/AAC, owner A при current
  B, canonical/service queue bytes и generation2 без normal promotion/HTTP.
- Mode2 started-output refusal остался capturing; mode3 дошёл до actual held
  canonical read, finish вернул error6/native995 после shutdown, до release
  drain был запрещён; cold состояние и полный root неизменны.
- Mode4 alias B с uppercase same-package path остался capturing с двумя
  сохранёнными rows и полным unchanged root. Это закрывает конкретный P1.
- Дополнительный unfinished live-playback variant прошёл real held old read,
  Start ACK/g5/live frames, resultReady, muted play/seek, unchanged live/ticket,
  EOS finish и cold три rows; old degraded остаётся quarantined. Это **пять
  modes плюс один параметризованный live variant**, не вся recovery matrix.

Эти process/hash сведения прочитаны из сохранённых receipt, не из нового
guest/CIM query. VM/tests reviewer не запускал. GREEN2 regression receipt
остаётся CTest exit8, **6/7**, с отказом mode3 до held-cut. RED5 остановился
там же до alias mode4 и не является alias RED. GREEN4 диагностический отказ
на `ticket.id==0` не печатает kind/state ticket; причина конкретного отказа
по нему не установлена. Они не повышены до PASS после последующих fixes.

### P2 — допустимый auth prepare ticket назван recovery в тесте

`NativeCaptureStorageIntegrationTests.cpp:3913–3916` разрешает id0 либо
id1/kind=recovery/no-change/g2→2. В этом fixture token непустой и account B
resolved до startAndAdopt. Последний вызывает pollUploads, который после
startup ACK может успеть вызвать requestProtectedUpload (:489–496).
Этот путь явно создаёт **uploadPrepare** (:1638–1648), а не recovery. Обычная
StorageCommand::recovery в pollStorageStartup (:2777–2789) требует пустого
token; no-proof B completion recovery ticket не создаёт.

Следовательно при допустимом порядке потоков ранний no-change auth prepare
может потребовать ACK до startup scan; новый pollStorage этот ACK обслуживает,
но последующий oracle всё ещё способен ошибочно отвергнуть его kind.
GREEN5/6 PASS без печати ticket fields не доказывают исполнение разрешённой
id1/recovery ветви. Это **P2 harness flakiness / неверная классификация**, не
доказательство production failure или фактической причины прежнего mode3.

Минимальная правка — сопоставить этот узкий branch с настоящим допустимым
uploadPrepare, требуя terminal committed/no-error/no-change ticket с тем же
context и g2→2; сохранить full queue/root SHA и запрет HTTP. Не разрешать
произвольные kinds/изменённую очередь и не удалять assertions. При споре о
достигнутом пути достаточно metadata-only kind/state/id diagnostics; новый
hook/framework не нужен. Этот P2 не переоткрывает закрытый alias P1, но общий
test/source acceptance пока не объявлен безусловным.

### Независимое восстановление исходников

Проверены source-origin.json и actual full patch
`green6/delta-from-head.patch`: 3216707 bytes, SHA-256
`5a4f7ca4ad5135943022d4b9ebcc6004a0925722f4e3cf8698f1717ea433301b`.
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` → isolated index/object
directory → apply --cached --binary → GREEN6: **216/216 blobs** по SHA-256.
Из полученного final tree отдельно применены actual delta-from-final.patch
для red, red3, red4, red5, red6, green, green2, green3, green4, green5:
**каждый 216/216** совпал со своим manifest; hashes всех десяти delta и
manifest совпали с source-origin. Включены manifest inputs из full patch,
в том числе 33 untracked inputs; никакой moving dirtytree baseline не нужен.
Обычный Git index SHA-256 до/после одинаков:
`662a640f866392dde2940678f5d98c82c85c145c3be3aebedf2825a524e36229`.
Временные index/objects удалены только из собственного isolated scratch;
normal index/objects, worktree, frozen copies и evidence не менялись.

Ponytail: **Lean already. Ship.** — только вывод о форме production fix:
повторно использована одна существующая policy, без нового schema/ledger,
pool/dispatcher/publisher или capability. Для P2 достаточно исправления
оракула, не тестового framework. Final seven-regression/JUnit qualification,
targeted ambiguous/deletion/Stop-before-old-cut-release и whole T116 остаются
вне этого checkpoint. Append выполнен только в этом reviewer report;
cleanup GO до отдельного terminal review по-прежнему отсутствует.

## Append-only qualification — terminal GREEN6 семь регрессий

2026-10-16. **Bounded GREEN6 regression runtime GO для фактически выполненного
набора**, не всего Round448/T116 и не текущих новых test edits. Независимо
прочитаны regressions.json, JUnit, полный LastTest.log, ctest.log,
regression-build.log и actual regressions.ps1. UTF-16LE журналы декодированы,
не прочитаны через raw tail. Receipt terminal true, build0/ctest0,
executed_tests7/postflight216/saved owned_processes0; failure отсутствует.
JUnit имеет ровно семь ожидаемых уникальных names, status=run у всех,
failures0/disabled0/skipped0 и нет failure/error/skipped child elements.
LastTest содержит семь соответствующих команд и семь Test Passed.

| Выполненный CTest | JUnit seconds |
| --- | ---: |
| V5LocalRecordingWriterTests | 104.336 |
| NativeProtectedStartOwnerRecovery | 32.5443 |
| NativeProtectedStartOwnerDegradedRestart | 1.96286 |
| NativeProtectedStartOwnerUnfinishedRestart | 19.3145 |
| NativeProtectedRecoveryLivePlayback | 11.2864 |
| NativeProtectedPlaybackConsumer | 14.8967 |
| NativeProtectedPackageRevalidation | 46.6539 |

CTest real total **231.01s**; JUnit suite time округлён до231. Это семь
invocations, не семь внутренних cases. Actual LastTest дополнительно содержит:
3 cold playable positives/15refusals, A cold/sealed refusals, **24 trace + 24
достигнутых process88 cuts**, sealed_cold_decode1; normal recovery modes0–7;
degraded restart; unfinished modes0–4 плюс unfinished live variant; отдельный
normal live-playback; consumer real validation/clone/Start ACK fences;
revalidation cases0–3 и pins_full fresh ACK. Success labels не заменяют
соответствующие source assertions, прочитанные в предыдущих разделах.
Ни строки generic concurrent_start_frames_stop_eos, ни этот PASS не доказывают
Stop/EOS **до** release old B read: новый explicit вариант остаётся будущим.

Source manifest frozen GREEN6 по-прежнему
`307500e82c7005c92ef664302c2dfc22a648a2ca93712eb8a659bd147eb92c3f`.
Его full216 реконструкция уже проверена выше; retained семь copies ещё раз
сверены 7/7 с manifest. На момент текущей проверки current равен **215/216**:
изменился только NativeCaptureStorageIntegrationTests.cpp для следующего
test substep. Все production inputs прежние. Поэтому GREEN6 не переносится
на новый test TU/ещё неисполненный сценарий.

Saved PE hashes связаны receipt и script pre/post checks:

- Native `997cf0d2168b5b165be49acc1f1b363a37b8867a165ccdfd2d4691ea427f62be`
  совпадает с GREEN6 primary; regression build не менял этот PE.
- Writer `46e9ecf67a2ebba26bb9f6a6402f510021ee9450331e03223c61bb3bdba64f4b`.
  Regression build действительно компилировал ProtectedCustodyMetadata.cpp и
  V5LocalRecordingWriterTests.cpp; не заявляется совпадение с прежним writer PE.

Script требует GREEN6 terminal primary, guest source216 и primary PE до build;
после build фиксирует оба PE; требует actual CTest/no-tests=error/exact JUnit
names/status; после CTest сверяет guest216 и неизменность обоих PE, затем
сохраняет CIM count. Это saved postflight evidence, **не fresh live CIM/guest
query reviewer**. Собственных запусков VM/tests не было. Hashes evidence:
regressions.json `c34032f9e9d3e6e3f8e74ded1d0bfde06a8f1cf9cc91d5d71bc4c1d33599910a`,
JUnit `35010de17e9548db4c4798748bbd4b381e8717550726efa2301c6510d9600a46`,
LastTest `2ccf0771f66c8f34246a1b27ca120ccae7ecae9f661c3e92ad384ed861225b82`.
Исторический GREEN2 6/7 и остальные failed candidates остаются отказами.

## Поправка reviewer-рекомендации P2 — no-change не committed

После замечания main повторно прочитан actual source chain:
requestProtectedUpload → prepareUploads → ticket outcome → ACK/drain.
**Моя прежняя рекомендация требовать terminal committed для этого no-op была
ошибочной и этим append явно отозвана.** Правильным остаётся kind
uploadPrepare, но ожидаемый state здесь **notCommitted**.

В prepareUploads (DesktopUploadQueueService.cpp:1086+) quarantine rows не
попадают в selected, requeueNeedsAuth не меняет их. NativeCapture.h:2504–2507
при !changed и empty selected оставляет base=target и выставляет notCommitted;
no-change committed — отдельное исключение deleting. При error/native0 это
нормальный no-op, не observed storage failure. ResultReady всё равно требует
отдельного resultAdopted; queueFailed не выставляется. PrepareUpload executor
не запускается без committed, empty selection освобождает flight и lease.

Узкий oracle: id1 / uploadPrepare / notCommitted / error0 / native0 /
changed=false / same queue context / g2→2; id0 допустим, только если этот
отдельный intent не dispatch. Новое mode0 с explicit pollUploads должно
реально достичь и наблюдать id1 terminal branch, а не только разрешить его
неисполненный alternative. Сохранить queue/root SHA, original A/B separation,
HTTP0 и actual retirement. Production state менять ради теста не нужно.

GREEN8 независимо прочитан как terminal **build0/test exit3/13096ms**,
postflight216/saved process0, manifest
`248932964ed1a64319027017be8801bda70030e5a8edcc12e57384bf3c94cb6a`, PE
`e0a32957dfaf6d1ff0e10aa629950f2d48a5abea924d83a6449b2a5e13e1ec8f`.
Assertion именно waitFor uploadPrepare/state=committed до Stop case. Его
source216 отличается от GREEN6 только test TU; это сохранённый **неправильный
test oracle FAIL**, не product regression и не PASS. Current исправленный
assert использует notCommitted/noerror/context/g2→2 и metadata diagnostics,
что согласуется с прочитанным source chain; fresh execution этой правки пока
не квалифицирован. P2 runtime acceptance и новый Stop-before-release не
наследуют GREEN6 7/7.

Fresh requirements refresh отдельно добавлен в reviewer requirements-report:
198/452/0, exact aggregate и10/10 norm SHA неизменны, scoped C0/H0. Продолжение
покрыто existing T116; никакого нового product/normative выбора нет. Только
reviewer reports дополнены; source/checklist/tasks/plan/GitHub/VM не менялись,
source copies не удалялись и cleanup GO не выдавался.

## Append-only final qualification — current GREEN12

2026-10-16. **Bounded source + primary + nine-regression runtime GO для
GREEN12**, не закрытие T116/всего Round448. Новых blocking source findings в
проверенном delta нет. Предыдущая ошибочная рекомендация reviewer требовать
committed для uploadPrepare no-op отозвана выше; нынешний oracle корректен.

### Current source, P2 и фактические границы

Current **216/216** равен frozen GREEN12, manifest
`6c7927f3c4125b07f000c191bf0071c06a2fbe3ca7c2502fd1e0e0d973401f39`.
От GREEN6 изменён только NativeCaptureStorageIntegrationTests.cpp; production
остался прежним. Primary build.log действительно содержит компиляцию этого
TU. GREEN12 primary: terminal true/build0/test0/**30510ms**/postflight216/
saved owned_processes0. PE
`82bdd6b73666c538eed13b1847031985b8b4bef48d49faf1bb4ec8cf8a9e79ca`.

- **P2 закрыт в этом bounded scope.** GREEN9 и отдельно GREEN12 действительно
  исполняют mode0 id1/kind2 uploadPrepare/state2 notCommitted/error0/native0/
  changed0/context_equal1/g2→2. Это не разрешённый, но неисполненный alternative
  id0. У mode3 в финальном CTest также наблюдается правильный id1 no-op.
  Queue bytes, original owner A/current B и canonical сохранены; HTTP0.
- **Stop/EOS до release old B read исполнен.** Local finishLive переиспользует
  настоящий finalizer, committed recording ticket g5→6 и отдельный pollStorage
  ACK. SavedLocal и g6 проверяются при всё ещё удерживаемом canonical read,
  recovery resultReady ещё отсутствует. После release — actual recovery
  retirement, cold три owned rows, новый valid/decode1000ms и old degraded,
  original canonical unchanged, exact memory. Старый normal live-playback и
  unfinished muted playback/seek не заменены этим вариантом.
- **Deletion intent / ambiguous reconciliation исполнены, physical purge нет.**
  Использован existing actual rename ambiguity cut и настоящий deletion
  continuation. Пока old read удерживается, token cancellation уже true, но
  premature physicalReadback и premature drain запрещены. После release
  stage1 возвращает ioFailed6/native995; затем actual readback, отдельный ACK,
  slot retirement. Cold g3/local_delete_pending, package целиком unchanged,
  phase capturing, HTTP0 и exact memory. Это доказательство intent/drain и
  согласования результата, не удаления package и не completion физического
  purge.
- Started-output refusal mode2 и uppercase foreign-owner alias mode4 остаются
  capturing, без mutation queue/canonical; shutdown mode3 сохраняет данные и
  реально ждёт retirement удерживаемой операции. GREEN12 не наследует эти
  PASS от прежнего PE: они повторены в primary и текущем CTest.

GREEN8 wrong committed-oracle FAIL сохранён. GREEN10 и GREEN11 — только
build failures TestTU conversion, не runtime PASS. GREEN12 исправляет передачу
CustodyString через существующий ctor(data,size), не меняя production policy.

### Fresh nine-regression receipts

Независимо прочитаны GREEN12 regressions.json, полный JUnit, LastTest.log,
ctest.log, regression-build.log и regressions.ps1. Windows text корректно
декодирован. Receipt terminal true/build0/ctest0/executed_tests9/postflight216/
saved owned_processes0; failure отсутствует. JUnit имеет ровно девять уникальных
ожидаемых names, status=run, failures0/disabled0/skipped0, без child
failure/error/skipped. LastTest содержит девять соответствующих actual command
и девять Test Passed. CTest total real **259.74s** (JUnit suite time округлён).

| Actual CTest | JUnit seconds |
| --- | ---: |
| V5LocalRecordingWriterTests | 105.617 |
| NativeProtectedStartOwner | 14.4267 |
| NativeProtectedStartOwnerRecovery | 31.5514 |
| NativeProtectedStartOwnerDegradedRestart | 1.83584 |
| NativeProtectedStartOwnerUnfinishedRestart | 30.0751 |
| NativeProtectedRecoveryLivePlayback | 11.1675 |
| NativeProtectedDeletionDisplay | 3.41827 |
| NativeProtectedPlaybackConsumer | 14.8103 |
| NativeProtectedPackageRevalidation | 46.8199 |

Это девять invocations, не девять внутренних cases. LastTest включает owner
primary+7 classifications+3 finalizations (11), normal recovery modes0–7,
unfinished modes0–4 плюс оба live варианта и deletion variant, отдельный normal
live-playback/deletion-display, consumer clone/Start ACK fences, revalidation
cases0–3 и pins_full fresh ACK. Writer повторяет 3 cold playable positives,
15 refusals, A positive/refusal matrix и **24 trace /24 reached process88 cuts**
с sealed_cold_decode1. Не заявляются power-loss или неисполненные IO/cancel cuts.

PEs receipt/script-bound, неизменны до/после CTest:

- Native `82bdd6b73666c538eed13b1847031985b8b4bef48d49faf1bb4ec8cf8a9e79ca`,
  совпадает с GREEN12 primary.
- Writer `46e9ecf67a2ebba26bb9f6a6402f510021ee9450331e03223c61bb3bdba64f4b`.

Script требует terminal primary, отсутствие owned work, guest216 и primary PE
до build; далее фиксирует оба PE, запускает exact names/no-tests=error/JUnit,
проверяет guest216 и оба PE после тестов и сохраняет CIM count. Это проверенные
**saved postflight receipts**, не fresh live CIM/guest query reviewer. VM/tests
reviewer не запускал. Hashes evidence:

- primary receipt `8611910bc9abed657f0bbad8cd0bbc9e52cb481904f89afe590e0b6afa1c4334`;
- regressions receipt `4702280986fd5e13f618d00f2936f949a97de5a5f2d972d5bc7588bc6f719d99`;
- JUnit `c87edfeda23b3b8b2b4651b0ecf378457898879e17de505be17ed9fde0974535`;
- LastTest `3a8a07c35e5dde29e3699e74c6c2bbb171cd96b759b1fe25c9be04bc265a946b`;
- CTest log `aaaac263992f32d8da80e0f92a2bafb3e75b7da91adb4bf5e3c2963946645858`.

### Reconstruction и cleanup scope

Независимая проверка выполнена через isolated temporary Git index/object dir:
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` → full GREEN12 patch →
**216/216**, затем GREEN12 → все **16** historical deltas → каждый **216/216**.
Сверены hashes самих manifests/deltas/source-origin и фактических index blobs.
Full patch 3223510 bytes,
`4325c6ec3ce60ad931696c3a5e1d58a0999faf7084c7340cc62efa3bc11111e9`,
включает33 untracked manifest inputs. Normal Git index до/после одинаков:
`662a640f866392dde2940678f5d98c82c85c145c3be3aebedf2825a524e36229`.
Normal object store/worktree не менялись; собственный isolated scratch удалён.

cleanup.rb прочитан, запуск **по абсолютному пути без --delete** выполнил
только preflight: **110 files /14554515 bytes /deleted=false**. Targets —
разрешённые семь source paths в существующих red*/green*/apps/windows;
старые five-file stages не дополнены фиктивными copies. Все существующие
target ancestry дополнительно проверены realpath/no-symlink. red2 не является
runtime evidence: его совпадающие baseline staging copies не добавляют PASS.
Script проверяет current216, terminal9/9/post216/saved process0 и hashes каждого
удаляемого copy; manifests, deltas, scripts, receipts и logs не удаляет.
Relative invocation безопасно отказывается с root; использовать absolute path.

**Cleanup GO ограничен этим exact inventory**, при неизменных copies/script/
patches/receipts и повторном owner preflight непосредственно перед удалением.
Не распространяется на repo, guest build, другие artifacts или новые paths.
Reviewer ничего не удалял. После cleanup сохранить source-origin/fullHEADpatch/
16 historical deltas/manifests и все failed/pass receipts/logs.

Ponytail: **Lean already. Ship.** В смысле формы этого bounded delta: existing
helpers, два дополнительных режима и один local finishLive reuse; не найдены
безопасные удаления, которые сохранили бы независимые ACK/drain/cold assertions.
Это не release approval. Нормативный gate остаётся198 files/452 checked/0
unchecked, scoped C0/H0; tasks/T116 не закрываются. Physical purge,
ambiguous **new** finalizer и changed-row matrix остаются pending, как и
остальной umbrella T116, installed/hardware/public/release acceptance.
