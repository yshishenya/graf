# Round455 — независимый ограниченный review no-login claim

## Полномочия и привязка

Проверка исходников и сохранённых доказательств; единственная запись reviewer — этот отчёт. Исходники, нормы, задачи, checklist markers, обычный Git index, VM и GitHub не изменялись; сборки, тесты и очистка reviewer не запускались. Сообщения main agent не трактуются как полномочия человека на действия вне этой роли.

Authoritative worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Высокорисковый срез существующего T116/#7444 по принятому plan453; это не новый нормативный выбор и не закрытие T116.

Проверены manifest и содержимое всех 216 текущих inputs:

- GREEN1: `48f53547a05525e8e44e9755ce70e6c64b372479d96993e678e24f03b4195c94`; относительно текущего дерева отличается только `NativeCaptureStorageIntegrationTests.cpp`.
- GREEN2: `74f103e66c184a5671a5f48eb03b428e703089958ba098baff4dead065191176`; current/frozen **216/216**, несовпадений нет на момент проверки.
- `green/changed.json` перечисляет 11 файлов относительно RED2: AppMain; LocalRecordingPackage h/cpp; NativeCapture; ProtectedCustodyMetadata h/cpp; DesktopUploadQueueService h/cpp; WebView2Host h/cpp; NativeCaptureStorageIntegrationTests.cpp. GREEN2 меняет лишь Test TU относительно GREEN1.

Принятый gate453 остаётся основанием scope: 198 checklist-файлов / 458 checked / 0 unchecked; новые markers этим review не выставляются. Перепроверены неизменные spec/plan/tasks/quickstart SHA: `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11`, `2d1f170a0345ef0201848f6d0a934f973db596f001fa7c431e2b973c702bdd1e`, `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`, `3eb4f3a05a4295025a149ecbb91b4cce71d4caacbf94f19f24d9631f16e25c12`. Это не повторный полный аудит старых runtime-отчётов.

## Вердикт исходников: REQUEST_CHANGES

### P1 / HIGH — отменённый claim образует цикл ожидания с ambiguous finalizer новой записи

`apps/windows/RecApp/Recording/NativeCapture.h:2041–2042`, повторено в `2074–2075` и `2325–2326`: исключение для cancelled/no-proof recovery разрешено только при `!network->claimTicket`. Claim, даже уже отменённый, требует `!work->recording && !work->inFlight`.

Достижимая последовательность по actual source:

1. Claim preflight (`2388–2404`) сохраняет manual ticket в exchange и освобождает `inFlight`, прямо разрешая новый Start/Stop/finalize во время полной проверки.
2. Новый recording finalizer получает ambiguous publication. После отдельного adoption/readback handling код (`2612–2617`) оставляет `commandReconciliation=true`, recording и `inFlight` до физического readback.
3. Начало worker loop (`2009–2016`) отменяет recovery token из-за `commandReconciliation`.
4. Readback (`2037`, `2152`) намеренно не запускается, пока есть `network->recoverySnapshot`: proof должен уйти до повторного открытия owner.
5. Claim executor (`1750–1757`) ждёт `resultAdopted`, чтобы освободить proof и поставить `recoveryDone`; cancelled claim не допускается к этому переходу, пока сохраняются recording/inFlight из п.2.

Получается цикл: recording readback → claim retirement → resultAdopted → отсутствие recording/inFlight → recording readback. Установка cancellation при Stop не разрывает его. У manual flight ещё не запущен HTTP executor, поэтому альтернативное `upload->done` не является выходом.

Минимальное обязательство исправления: дать отменённому/неполучившему proof claim отдельное завершение **без эффекта**, которое не перезаписывает ticket/command чужой записи, допускает executor retirement и ждёт фактического `recoveryDone` до owner readback. Нельзя просто убрать guard и отправить такой claim в существующую ветку `2328–2335`: она безусловно восстанавливает manual ticket и может занять слот чужого recording command. Успешный claim по-прежнему должен ждать допустимого mutation fence.

Нужный узкий runtime cut уже входит в принятый scope: genuine no-login claim с удержанной проверкой → разрешённый новый Start → actual ambiguous finalizer → release/cancel → физический readback, terminal/drain и HTTP0 для отменённого claim. Это **вывод по исходникам**, не заявленное воспроизведение в VM.

### P2 — специфическая ошибка bridge затирается `conflict`

`NativeCapture.h:2523–2537`: результат `recoverPreparedRecording` сначала переносится в `ticket.error/nativeError`, но затем любой `!prepared` безусловно заменяет `ticket.error` на `conflict`. Таким образом, fresh IO/quota/cancellation/integrity failure теряет своё определённое объяснение; native-код при этом остаётся от прежней ошибки. Публикация всё ещё закрыта, но классификация результата неверна.

Минимальное исправление: назначать fallback `conflict` только если специфической ошибки ещё нет (`ticket.error == none`), сохраняя исходную пару error/nativeError. Не нужен новый тип результата или журнал.

## Проверенные положительные границы исходников

- `isPreparedUnownedRecording` — узкий фильтр формы genuine Start row: quarantine/capture_prepared, согласованные session/local/directory IDs, обе пустые owner-пары, отсутствие server identity. Это не самостоятельная normal authority. Ordinary pending/unowned не подменяет fixture и не допускается этим путём.
- Private-constructed `ProtectedInspection` по-прежнему является входом full-proof bridge. Bridge проверяет token/session, valid integrity, matched manifest session, положительную duration и sealedNormal. Owner-side операция сверяет свежую очередь с candidate, ожидаемую identity/reason/updatedAt, path/IDs, aliases/deletion/server fences и повторно валидирует actual package до candidate binding. Нового persistent формата или caller-supplied bool proof не добавлено.
- Полная проверка вынесена из storage worker в существующий executor; новый dispatcher/publisher не введён. Claim proof освобождается executor перед `recoveryDone`, HTTP launch и owner reconciliation в обычном успешном потоке.
- UI scalar `assignableNormal` привязан к exact snapshot и служит только отображению/допуску. Public claim заново получает native proof; scalar не передаётся как authority.
- AppMain проверяет document/epoch и snapshot перед public call; диалог «Назначить и отправить» использует **Close/Отмена** по умолчанию. Документная invalidation и stale polling запрашивают cancellation через ticket. Это source observations, не фактическая UI-приёмка.

## GREEN2: ограниченная квалификация сохранённого результата

Прочитаны `/Users/yshishenya/Documents/graf-f200-claim455.qUi7hI/green2/result.json`, `test.stderr.log` и соответствующая ветка теста.

- terminal=true, build=0, test_exit=0, elapsed=12408ms;
- Native PE по receipt: `b15177b7b03b244ec0faa96ed70d26952083d714c7af0de460408064441b8fce`;
- postflight=216, owned_processes=0 — **сохранённые значения receipt**, не fresh live CIM/PE чтение reviewer;
- actual log: `genuine_start=1 reservation_ack=1 generated_frames=100 normal_finish=1 cold_inspection=1 verified_account=1 no_implicit_claim=1 admitted=1 http_before_ack=0`;
- actual tail: `finalize=3 cold=1 exact_row=1 ... live=16 ... empty_cache=16`.

Выполняемый positive branch дополнительно требует committed/no-error manual ticket, actual current owner после adoption, единственный generated GET sync-state с ответом503, отсутствие HTTP до ACK, cold exact IDs/owner и valid package inspection, настоящий shutdown/drain. Затем scoped idle и Fixture destruction предшествуют итоговому target assertion.

GREEN2 ожидание `displayFinished` соответствует существующему UI admission: pending display занимает shared slot, а не даёт право обходить его. Сохранены genuine Start, confirm=false refusal, неизменный public confirm=true target, no-HTTP-before-ACK и cold proof. Дополнительные row-shape/canManualSend asserts усиливают диагностику. GREEN1 admission failure остаётся историческим FAIL, не преобразуется в PASS.

Ранее законченные RED1/RED2 Round454 сохраняют свой отдельный смысл. Дополнительно прочитан RED2 regression: NativeProtectedStartOwner 1/1, тот же PE874b…/manifest b562…, CTest total20.10s, saved post216/process0. Эта baseline-регрессия не переносится на production455. Отчёт454 не изменён.

## Ponytail и предел заключения

По установленному `ponytail-review` отдельной обоснованной рекомендации удалить production-механизм нет: используются existing exchange/owner bridge/commit/adoption и общий диалог, без новой очереди, ledger или зависимостей. **Lean already.** Это оценка простоты, не разрешение выпускать: P1/P2 выше относятся к корректности. Дублированные predicates требуют одинакового исправления; новый общий framework ради них не нужен.

Итог: GREEN2 доказывает ограниченный положительный native claim, но **source GO не дан из-за P1**, P2 также подлежит исправлению. Held-proof cancellation/stale/concurrent recording и physical-publication cuts, фактическая UI-приёмка и финальные регрессии ещё не квалифицированы этим отчётом. Full app, installed/hardware/release, public readiness и закрытие T116/T117 не заявляются. Очистка не рассматривалась и не разрешалась.

## Append — GREEN4: повторная проверка исправлений P1/P2

Проверено текущее дерево против `/Users/yshishenya/Documents/graf-f200-claim455.qUi7hI/green4/source.sha256`: manifest SHA `659fe867c17f0e0d0e8833d75604e201c3179d92361f17c681954092c57e5192`, **216/216 exact**, несовпадений нет. Этот append уточняет текущий source verdict, не переписывая историю GREEN2/GREEN3. GREEN4 runtime в этот момент не квалифицирован. Сообщённый main GREEN3 failure остаётся FAIL; новых результатов ему не приписываю.

Использован `code-reviewer`; проверка только чтением. Ранее прочитанный `ponytail-review` не является основанием убирать необходимые fences. Ничего, кроме этого append в reviewer report, не записывалось.

### P1 — исправлен по исходникам; runtime acceptance ещё открыт

В `NativeCapture.h:2042`, `2081` и `2332` cancelled/no-proof recovery снова допускается к обработке независимо от recording/inFlight. При этом отдельная claim-ветка (`2335–2343`) меняет **только `network->claimTicket`** в notCommitted, задаёт cancellation/invalid-content результат, сигналит resultAdopted и не трогает `work->ticket`, `work->command`, `work->inFlight`, `work->resultValue` или queueFailed чужой записи. Успешный claim с proof и без cancellation по-прежнему проходит лишь при отсутствии recording/inFlight и использует прежний fresh-generation dispatch.

Executor по-прежнему освобождает последнюю recoveryProof ссылку вне storage mutex перед выставлением recoveryDone. Только после actual recoveryDone worker (`2045–2056`) сохраняет bounded value-only `retiredManualSend`, отмечает этот flight done/leaseReleased, очищает upload/network/recoveryCancellation. Значит cancellation не притворяется освобождением native proof по таймеру. После этого старый commandReconciliation может выполнить owner readback, не ожидая завершения записи, которая сама от него зависит.

`pollStorageStartup:2860–2864` переносит отмену лишь в `lastManualSendTicket_` при совпадении ID. Он не заменяет `lastQueueTicket_`/recording ACK и не принимает новый queue value за отменённый claim. `pollUploads:490–493` сначала принимает этот value-only результат, затем вызывает существующий scheduler.retireProtected; scheduler освобождает flight только при done AND leaseReleased. Один bounded optional достаточен: одновременный второй upload не допускается до освобождения существующего shared slot, а UI polling забирает результат до обычной последующей admission.

Следовательно, конкретный цикл P1, описанный выше, по текущему source разорван без снятия successful-claim mutation fence и без перезаписи чужого command/ticket. Нового blocker в проверенном delta не найдено. Это не утверждение о ещё не завершившемся запуске.

### P2 — исправлен по исходникам

В `NativeCapture.h:2551–2553` fallback conflict применяется только при `!prepared && ticket.error == none`. Специфическая error/nativeError пара bridge теперь сохраняется; false/no-error остаётся закрытым conflict. Замечание P2 к прежнему присваиванию закрыто на уровне source; отдельный late-error runtime cut этим append не объявляется исполненным.

### Тестовые oracles GREEN4

Прочитана ветка `protectedStartOwnerFinalization(..., claimScenario)` и dispatch шести сценариев 0–5. Сценарий5 действительно использует удержанный actual canonical read, допускает genuine concurrent Start с двумя generated producers/100 frames, включает существующий queue-qualified ambiguous rename непосредственно перед Stop, требует actual ambiguous worker ticket и потребление cut, делает отдельный polling ACK, наблюдает commandReconciliation+cancelled recovery token, проверяет отсутствие physicalReadback до release, затем требует terminal failed новой записи, notCommitted claim, HTTP0, cold unbound original owner и неизменный original package. Те же общие assertions проверяют cold owner/package и точную idle memory. Это достаточный направленный oracle для прежнего P1, но пока лишь source qualification.

Сценарии0/3/4 проверяют успешное binding/физически опубликованный результат, сценарии1/2/5 — отсутствие binding; сценарий3 отменяет после actual resultReady и до UI ACK, сохраняя физическую truth без последующего HTTP. Старый positive target genuine Start не заменён ordinary pending fixture.

Новые 16 CalendarJoinHostTests проверяют общий `localRecordingActionAllowed` и сериализованную canSend проекцию: единственный allowed baseline, отсутствие scalar/неверный snapshot/degraded вместо normal/incomplete inventory/active session/unknown marker/partial owner/server identity/IDs/deletion/auth/document/history/ordinary pending закрывают send; open/delete остаются false, представление не назначает owner. Эти fixture-level тесты не доказывают native proof authority, фактическую работу ContentDialog или исполнение UI тестов в Windows; таких заявлений нет.

**Текущий ограниченный вердикт:** source GO на конкретные исправления P1/P2 и effect-free completion; 0 новых CRITICAL/HIGH в этом повторном delta-review. GREEN4 runtime, Windows host tests и итоговая регрессия остаются pending до actual terminal receipts. Ни whole-T116 GO, ни fullapp/installed/release/cleanup permission этим append не даются. Новый optional value-only результат и повторное использование существующего executor/scheduler не требуют отдельного ledger/dispatcher/framework; обоснованного удаления механизма не найдено.

## Append — terminal GREEN4 six-scenario qualification и GREEN5 registration

Независимо прочитаны terminal `green4/result.json`, **полный** `green4/test.stderr.log`, CLI dispatch и выполняемые assertions. Receipt: build0/test0, elapsed77566ms, manifest `659fe867c17f0e0d0e8833d75604e201c3179d92361f17c681954092c57e5192`, Native PE `72adca1407fd4768a891828ef0f2630c84b5e16cad6af92f435911efc2a89f7a`, postflight216/owned_processes0. Скрипт validate.ps1 связывает receipt с actual exe hash до/после процесса, получает его exit code, перепроверяет все source inputs после исполнения и считает scoped processes в finally. Reviewer не выполнял live guest/CIM/PE чтение: это квалификация сохранённых доказательств, не fresh process0 после начала следующей сборки.

В stderr ровно по одному completion marker сценариев **0,1,2,3,4,5**, шесть admission markers admitted1/http_before_ack0 и шесть точных idle markers live16/empty_cache16. CLI вызывает все шесть последовательно; return0 возможен после scoped cleanup и target assertion каждого сценария.

| Сценарий | Реальная ветка и сохранённое доказательство |
| --- | --- |
| 0 | Genuine signed-out Start → generated normal package → explicit claim; committed binding/ACK, один generated sync-state GET503, cold owner A и original package unchanged. |
| 1 | Actual held canonical read, explicit cancellation до эффекта; notCommitted/unbound cold, HTTP0. |
| 2 | Actual held canonical read, auth epoch invalidation до эффекта; notCommitted/unbound cold, HTTP0. |
| 3 | Claim actual resultReady после publication, cancel до UI ACK; committed physical owner truth сохраняется, HTTP0. |
| 4 | Actual held proof + concurrent generated Start/100 frames/Stop/EOS с normal finalization до release; последующий claim bound/cold owner A, один generated HTTP request. |
| 5 | Actual held proof + concurrent generated Start/100 frames + queue-qualified actual ambiguous rename; отдельный ACK, reconciliation/cancel observed и отсутствие premature physicalReadback до release; затем failed recording terminal, notCommitted/unbound old claim, HTTP0, cold valid original package/unchanged bytes и точная память. |

Для scenario5 лог содержит `START_OWNER final_queue_ambiguous qualified_role=1 actual_rename=1`, concurrent marker ambiguous1 и cold completion HTTP0. Assertions связывают эти строки с фактическим consumed cut, pending manual ticket во время held proof и последующим terminal result. Поэтому прежний P1 принят **также на уровне направленного runtime cut GREEN4**, а не только по исходникам. Не заявляется более широкая матрица всех ambiguous IO/changed-row ошибок. P2 подтверждён по source; отдельный injected bridge-error runtime этим запуском не доказан.

Затем повторно сверены все current216 с GREEN5: manifest SHA `5e588cf1937b384fe3ac2d77394247a99076d1cad880abeded6c29f1088a83f6`, **216/216 match**. Manifest-to-manifest GREEN4→GREEN5 меняет ровно CMakeLists.txt. Независимая проверка: удаление из текущего CMake ровно двух строк NativeProtectedNoLoginClaim восстанавливает SHA CMake из GREEN4. Эти строки (`179–180`) регистрируют существующий `NativeCaptureStorageIntegrationTests --protected-no-login-claim`, RUN_SERIAL TRUE, TIMEOUT240; нового test body/product поведения нет. Перенос ограниченного source verdict P1/P2 и six-case implementation на GREEN5 обоснован; CTest registration по source GO.

**Итог этого append:** bounded source GO + GREEN4 native runtime GO для перечисленных шести сценариев; новых source blockers не найдено. GREEN5 CTest9/host16 execution всё ещё pending и не засчитано по запуску либо промежуточным логам. AppMain actual dialog/navigation, installed app, fullapp compile для текущего source, устройство/оборудование, release, весь T116 и переход T117 не приняты. Предыдущие FAIL/RED не превращены в PASS; cleanup не разрешён. Единственная запись reviewer — append этого report; source/checklists/Git/VM/тесты не изменялись и не запускались.

## Append — окончательная ограниченная квалификация GREEN5 CTest9

Прочитаны actual `green5/regressions.json`, весь JUnit `regressions.xml`, весь CTest `regressions.log` с правильным декодированием UTF-16LE, релевантные строки build.log и `regressions.ps1`. Terminal receipt: build0/ctest0/executed_tests9/postflight216/owned_processes0, manifest `5e588cf1937b384fe3ac2d77394247a99076d1cad880abeded6c29f1088a83f6`. Поле owned_processes относится к завершению этого harness: отдельная AppMain syntax-проверка уже может выполняться; fresh live idle reviewer не заявляет.

| JUnit exact test name | Время, s | Результат |
| --- | ---: | --- |
| CalendarJoinHostTests | 1.2054 | run/PASS |
| NativeProtectedStartOwner | 22.8596 | run/PASS |
| NativeProtectedNoLoginClaim | 54.1748 | run/PASS |
| NativeProtectedStartOwnerRecovery | 39.9709 | run/PASS |
| NativeProtectedReadModel | 3.13509 | run/PASS |
| NativeProtectedLocalRemoval | 113.53 | run/PASS |
| NativeProtectedManualSend | 28.4165 | run/PASS |
| NativeProtectedDisplayTiming | 4.91358 | run/PASS |
| NativeProtectedPlaybackConsumer | 17.5088 | run/PASS |

JUnit suite tests9/failures0/skipped0/disabled0; каждый testcase status=run, дочерних failure/skipped нет. Имена точно соответствуют выбранным девяти, а не только числу записей. CTest log независимо показывает 9/9 и **total285.75s**. Сохранённый JUnit ограничивает отдельные system-out до1024bytes; его обрезанный вывод не выдаётся за полный transcript шести сценариев. Их полный transcript уже отдельно прочитан и квалифицирован для GREEN4, а GREEN5 исполняет неизменный six-scenario CLI целиком и возвращает0. Test body не менялся между этими стадиями.

Native PE в receipt: `72adca1407fd4768a891828ef0f2630c84b5e16cad6af92f435911efc2a89f7a`, тот же, что у GREEN4 primary. CalendarJoinHostTests PE: `b3f51b092c6ba2de97407a46ad25cb8250479047d7534b81a233bad4bab5aa35`. Build log прямо содержит компиляцию `CalendarJoinHostTests.cpp` и линковку его exe. Скрипт проверяет исходные GREEN4 inputs/PE до CMake-only upgrade, все GREEN5 inputs до/после тестов, неизменность Native PE после build и CTest. Host PE записан после build; отдельного post-CTest rehash host exe в этом скрипте нет — такого дополнительного утверждения не делаю.

Поэтому исполнение ранее source-reviewed 16 host permission edges теперь подтверждено actual CalendarJoinHostTests run. Это **16 cases внутри одного test executable**, не16 отдельных CTest и не live AppMain dialog/navigation test. Положительный native claim, cancellation до/после publication, stale-auth и concurrent normal/ambiguous finalizer остаются ограничены шестью перечисленными native сценариями. Нет new runtime claim про отдельную инъекцию специфической ошибки P2 или все возможные stale-document события.

### Current binding и сохранность исходников

Повторная независимая проверка SHA всех current files: GREEN5 **216/216 exact**, SHA manifest прежний `5e588cf1937b384fe3ac2d77394247a99076d1cad880abeded6c29f1088a83f6`.

Прочитаны `source-origin.json`, `source-reconstruction.json` и **полностью** `preserve-source.rb`. Независимо пересчитан сохранённый `green5/delta-from-head.patch`: SHA `f2f07426a77468fced3d7f681bb270110f0023a70bb8cd038904907a5c10bb6f`, размер **3266955 bytes**, совпадают с origin. Origin фиксирует HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`,216inputs/33untracked. Сохранённый reconstruction receipt фиксирует green5=216/216 и removed=true; указанный scratch сейчас действительно отсутствует.

В прочитанном алгоритме reconstruction: git archive точного HEAD apps/windows → отдельный scratch без .git → git apply полного patch без --index/--cached → SHA всех216 → удаление только identity-checked scratch. Текущий обычный index не нужен для apply; включение33 manifest-untracked производится отдельными no-index diffs. Скрипт reviewer **не исполнял**, новую временную копию/индекс не создавал; независимая повторная реконструкция этим append не заявляется. Подтверждены байты сохранённого patch, соответствие origin/current manifest и согласованность сохранённого reconstruction evidence.

**Конечный bounded verdict Round455 на данный момент:** source GO P1/P2 + GREEN4 six-case native GO + GREEN5 CTest9/host16 runtime GO. Новых blockers в квалифицированных фактах не найдено. Исторические GREEN1/GREEN3 FAIL и RED454 сохраняют прежний статус. AppMain /Zs пока только запущен main: ни syntax PASS, ни object/link/fullapp build, ни live/installed UI не заявлены. Public readiness, полный T116, T117/T118, устройства, выпуск и cleanup не приняты. Никакие checklist/task markers не менялись; reviewer записал только этот append, не выполнял VM/тесты/скрипты/Git mutations.

## Append — конечная AppMain syntax-only квалификация

Прочитаны terminal `app-syntax.json`, `app-syntax.rsp`, корректно декодированный UTF-16LE `app-syntax.log`, `app-syntax-original.rsp`, а также cmd/PowerShell wrapper как текст. Самостоятельно пересчитанный SHA arguments совпадает: `d0b7f52cc4fefae3dc1adb6837debaeab96ee646333a4acfff30de40f7ecf5ca`. Независимым сравнением строк установлено: final args точно равны исходной Release-команде с удалённым `/Zi` и добавленными `/Zs /WX`; final содержит один `/Zs`, не содержит `/Zi`, input — APPMAIN.CPP. Wrapper возвращает actual cl exit code.

Второй запуск: terminal=true, syntax_exit0, manifest GREEN5 `5e588cf1937b384fe3ac2d77394247a99076d1cad880abeded6c29f1088a83f6`, postflight216/owned_processes0. Независимо сравнены обе receipt maps: before_outputs == after_outputs, ровно три объекта — AppMain.obj, vc143.pdb, GrafWindowsApp.exe. В скрипте они хешируются до/после compiler invocation; все216 source hashes проверяются после него. Это saved evidence, не live guest recheck reviewer.

Лог содержит APPMAIN.CPP и два command-line warning D9025 о замене `/W1` на `/W4` и `/WX-` на `/WX`; syntax diagnostics/errors отсутствуют, exit0. Поэтому результат не называется warning-free. Сохранённый `app-syntax-debug-result.json` первого `/Zi` запуска имеет compiler syntax_exit0, но harness failure `EXISTING_OUTPUT_CHANGED`; он остаётся историческим FAIL. Конкретный изменившийся файл первым receipt не зафиксирован: утверждения, что это был именно pdb, нет.

**Bounded AppMain syntax GO** для второго запуска; он дополняет предыдущий source/native/CTest verdict, не заменяя его. `/Zs` не доказывает object generation, link/fullapp build, актуальность существующего app PE, installed/live dialog или public readiness. T116/T117/release/cleanup не закрываются. Единственное изменение reviewer — этот append; никакие VM/build/scripts/cleanup/Git/source/norm/tasks/checklist действия не выполнялись.
