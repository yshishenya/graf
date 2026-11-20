# Round457 — P2 completion: independent source / Ponytail review

**Актуальный статус:** bounded GREEN3 source/runtime GO; первичные completion5,
default regression3 и returned3/26 приняты в append ниже. Исторический P1/HIGH отозван:
его достижимость была ошибочно заявлена reviewer. Первоначальный REQUEST
CHANGES ниже не является текущим verdict. Узкий completed scope457 принят;
весь P2/T116, public/installed/release и cleanup не приняты.

Дата: 2026-10-16. **REQUEST CHANGES: один P1/HIGH в общем sealed validator.**
Нет обнаруженного CRITICAL. Узкий requirements GO не отменён; source GO пока
не выдан. Единственная запись reviewer — этот отчёт. Code/checklists/norms/
tasks/Git/index/GitHub/VM/frozen456 не изменялись; сборки, тесты, cleanup и
evidence scripts reviewer не запускал. Main agent messages не расширяют роль.

## Снимок и способ сравнения

Authoritative `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
та же feature200/T116. Использованы полностью прочитанные skills code-reviewer
и ponytail-review. Target — только delta457, не весь dirty diff от HEAD.

RED manifest: `20f5a2a446b71648192fc35956b996f41fb466fe509c77bb33b8f1e5aca43f8e`.
GREEN1 manifest: `52d7c6e513e8be68711a777b78261b0ee348e22b94a3b066067ba3a30e7a96ae`.
`green1/changed.json` перечисляет ровно восемь production files; их current
bytes независимо совпали с полными GREEN1 snapshots. На момент проверки
current против RED меняет эти восемь и один TestTU (позднейшее test-only
дополнение GREEN2); остальных production изменений нет.

RED хранит только полные изменённые test/CMake copies, не полные старые восемь
production files. Поэтому для точной старой стороны использован preserved
patch455: в памяти извлечены новые стороны hunks, неизменные gaps дополнены
из current только с контекстными anchors, результат проверен по SHA RED.
Так полностью проверены семь из восьми baseline files, включая весь
LocalRecordingPackage.cpp/h, V5.cpp и Metadata.cpp/h. Для Files.cpp полное
восстановление этим способом не завершено: новые строки попадают в старые
между-hunk gaps. Его изменённые функции и прежние контексты прочитаны напрямую;
полная независимая реконструкция восьмого baseline не заявляется. Никаких
scratch files, обычного/временного Git index или Git commands для этого нет.

| Current production file | SHA256 (равен GREEN1 copy) |
|---|---|
| Recording/LocalRecordingPackage.cpp | `c244f90c47823883d323a356142f9982aea0beda1f75384cdc3ed007382962a8` |
| Recording/LocalRecordingPackage.h | `fb219e2543f4028196cd4af511b0fa81a961fb7b93adcc88258daad5d45be85b` |
| Recording/V5LocalRecordingWriter.cpp | `6da439e346cbf5f4fa72b83af13f51efea77ce8802112a9eecbbd6499764ec06` |
| Storage/ProtectedCustodyFiles.cpp | `35ccd7ab2dd43351c067fd902bab03c799a5929b16d9c9d84f1d67574fb927e7` |
| Storage/ProtectedCustodyFiles.h | `4fc25d83edcf960084f850b1858ec4aa7e6c034ac004eaa4913e0c25635847c7` |
| Storage/ProtectedCustodyMetadata.cpp | `70d63f75ceef51c97a677d48265b107ca92eb161212dd4bb002450c699b0eb53` |
| Storage/ProtectedCustodyMetadata.h | `f75584b979ffe154280f0cd61e45b2ef85aa2d8ed6dbd8c5fdfeb4ea76c63fde` |
| Storage/ProtectedPackedCustodyOwner.h | `09217ebdb9a02e077165984452e649bbc7b30098c0ae8d63d8525c9e7124e0e7` |

## P1/HIGH — существующий пустой manifest стал «отсутствующим»

**LocalRecordingPackage.cpp:706–711, также повторный emptiness guard ниже.**
До выделения common helper `inspectProtectedImpl` проверял наличие manifest
по ref. При существующем ref он всегда выполнял `RecordingJson(...).manifest`,
включая length0: пустой документ закономерно отвергался. Новая
`validateProtectedContent` выбирает parse по `!manifestBytes.empty()` и допускает
пустоту для sealedDegraded как отсутствие manifest.

Это достижимая разница: `packageShape` в Metadata.cpp:213–215 требует наличие
optional length и верхний bound, но **не запрещает значение0**. Protected
metadata birth/empty value и SHA пустых bytes также не равны отсутствию ref.
При действительных canonical/recovery refs такой sealedDegraded доходит до
degraded evidence; при media/playback refs дополнительно обходятся проверки
привязки этих artifacts к существующему manifest. Прежний reader отказал бы
раньше. Это статически прослеженный контрпример, не исполненный reviewer тест
и не утверждение о скомпрометированной криптографии или normal upload.

**Минимальное исправление:** определять наличие по
`ref(CustodyRole::manifest)`, а не по длине полученных bytes. Существующий ref
всегда обязан пройти closed parse и прежние reason/phase/artifact/session
правила. Разрешённая degraded форма **без ref** должна остаться совместимой.
Не делать global nonempty/schema change вместо сохранения прежнего consumer
контракта. Один адресный genuine protected-reader контрпример length0 ref
достаточен; новая широкая матрица не нужна.

GREEN completion positive не проверяет этот случай: сам completeUnfinished
обязательно парсит terminal selected manifest, а проблема введена в общий
sealed consumer, который используется и вне completion.

## Остальной bounded source trace

- **Acquisition:** private openUnfinished(mode) оставляет unused guard; после
  effect-free recoveryRequired V5 получает новую acquisition без переноса
  refused package/proof. Store validate выполняет root inventory и BOTH
  bootstrap/queue checks. Package-state writeExisting, completed roles
  readExisting; fixed identities и collision checks сохраняются.
- **Readonly discovery:** optional candidate out ограничен prepared readExisting
  media/playback и zero caller container. Prefix читается с того же content
  handle; full prefix comparison остаётся. Candidate ещё не Tree/proof/ref:
  completeUnfinished вызывает Tree::verify, который проверяет оба heads и все
  reachable closures, затем hash/read. Writable capability discovery не выдаёт.
- **Inventory / metadata:** completedPackageRole допускает только id/content
  либо оба indices и blocks, referenced BOTH indices. Unknown children и старые
  unreferenced metadata версии отказывают — это намеренно узкая конструкция,
  не GC/repair. completedMetadata заново читает BOTH, проверяет selected bound
  generation; recovery только g1 и равные payloads. Manifest candidate ref
  сравнивается с actual current bound ref.
- **History / content:** terminal manifest closed/degraded/artifacts/session;
  BOTH snapshots closed parse, exact raw privacy и original time values;
  duration/artifacts могут отличаться у прежнего live snapshot. Три genuine
  Trees/readers, actual hashes/lengths, finite complete canonical prefix,
  WAV header и полный AAC decode переиспользуют общий алгоритм. Prefix frames
  дополнительно равен floor(canonical length/1920); partial tail не дополняется.
- **Publication:** candidate — value-only, не искусственный Pair/ProtectedInspection.
  Temporary readers/metadata buffers уходят перед commit; native owners остаются.
  commitImpl перепроверяет candidate refs и BOTH старого state, selected generation,
  затем публикует ровно package generation+1. Content/metadata role writes и
  повторное encoding в этой ветке отсутствуют. После физического ACK вызывается
  настоящий inspectProtected; только его proof даёт semanticVerified/prefix.
- **Ошибки / lifetime:** recoveryPending снимается до effectful attempt; тот же
  writer не получает второй retry. Cancellation принадлежит package и native
  states, job/pin/charged-buffer limits не увеличены. RAII освобождает local
  readers/proofs и native leases; allocator стирает retiring allocations.
  Postpublication failure не даёт semantic success; свежий cold state остаётся
  источником physical truth. Runtime late-cancel/drain для нового completion
  пока не принимается по одному source trace.
- **Native consumers:** NativeCapture не изменён. Existing prepare/finish handoff
  и executor retirement остаются прежними; completed branch возвращает genuine
  degraded proof, не normal recoveryProof/queue promotion. Новый read-barrier
  consumer не получает callable public mode, raw handle или claim capability.

Других конкретных HIGH/deadlock findings в перечисленном прочитанном пути не
найдено. Это не доказательство отсутствия всех ошибок и не full T116 acceptance.

## Ponytail

`ProtectedCustodyFiles.cpp:L1498: delete: if(discoveredContainer) state->context.object = actual; все store/object/role поля непосредственно перед этим уже сравнены с context.object, а state->context=context установлен выше. Замена: ничего.`

`net: -1 lines possible.`

Shared acquisition вместо второго backend, common content validator и один
private terminal bridge оправданы реальными двумя callers. Новых dependencies,
ledger, proof hierarchy, dispatcher/publisher не добавлено. Обнаруженный P1 —
ошибка сохранения semantics при выделении helper, не аргумент удалить проверки.

## Прочитанное bounded runtime evidence

RED457 actual result.json: terminal, build0, CTest exit8, executed1,
postflight216, saved owned_processes0; PE
`addfbbf24f49db01e46e5c5f770f4fcf612119add54f45656483649e8d5529ec`.
Actual-test.log содержит `accepted=0 error=13`, точный assert
`completed_recovery_must_finish_without_reencoding_members` на строке454.
Driver/CTest outcome не принят как GREEN. Это квалифицированный named RED.

GREEN1 actual result.json: terminal/build0/test0/executed1/postflight216/saved
owned_processes0. Actual-test.log и XML показывают accepted1/error0, cases1, generation_plus_one,
five_members_ids_queue_unchanged/cold_aac_history/exact_memory и Test Passed,
8.88sec. Точный PE из прочитанного receipt:
`9e0abe892614372b068715cd03e5e9d24f0ee178c2626f46ab9bd279e3e2f26c`.
Это bounded positive evidence одной completed fixture, не снятие source P1.
Счётчик processes — сохранённый receipt, live CIM reviewer не вызывал.

Позднейшие GREEN2 четыре cases/default regression/returned26 сообщены main;
их финальная независимая runtime qualification этим первым report пока не
заявляется. Ни ранний positive, ни будущая регрессия не исправляют source P1.

## Итог

**Source: REQUEST CHANGES по P1/HIGH выше.** Минимум — presence-by-ref,
адресный empty-manifest regression и fresh evidence на исправленном source.
Нормативный gate457 сохраняется. Arbitrary partial outputs, весь P2/T116,
public admission, T117/T118/T120, installed/device/power-loss/release и cleanup
не приняты. Checklist/task markers не менялись.

## Append — GREEN3: исправление достижимости finding и текущий source verdict

Дата: 2026-10-16. Этот append **заменяет текущую оценку P1/HIGH и REQUEST
CHANGES выше**, сохраняя исходную ошибочную запись как историю проверки.

Возражение main подтверждено повторным trace обоих единственных callers
`validateProtectedContent`. В прежнем выводе я пропустил уже существующую
проверку `protectedMetadata` (LocalRecordingPackage.cpp:319–322):
`!length || length > manifestLimit` возвращает invalidContent.

- `inspectProtectedImpl`: наличие manifest ref приводит к обязательному вызову
  `protectedMetadata` и проверке его результата до общего helper (строки786–800).
  Поэтому manifest ref с length0 отвергался и до нового presence guard.
- `completeUnfinished`: selected terminal manifest обязательно проходит closed
  `RecordingJson(...).manifest` с degraded/artifacts/session проверками, затем
  проверяются оба history snapshots до общего helper (строки657–678).
  Пустой selected manifest не достигает общего helper и этим путём.

Следовательно, `packageShape` с допустимой числовой length0 само по себе
**не доказывает достижимый обход**. Моё прежнее утверждение «это достижимая
разница» и присвоение P1/HIGH были ошибочны. **P1/HIGH отозван: доказанного
достижимого дефекта или уязвимости по этому контрпримеру нет.** Адресный RED
обнаруженной уязвимости не заявляется и для отзыва finding не требуется.

Current helper теперь определяет `hasManifest` по ref и использует его во всех
трёх ветках: closed parse, duration и artifacts. Это явное сохранение локального
контракта presence-by-ref, а не доказанное устранение runtime bypass. Отсутствие
ref в разрешённой degraded форме не запрещено глобально. Проверка nonempty в
`protectedMetadata` остаётся на месте.

Независимо перечитаны current изменения против сохранённых GREEN1 production
и GREEN2 TestTU. Из GREEN2 в GREEN3 изменены ровно четыре входа: LocalPackage
(hasManifest и три условия), Files (удалено избыточное context assignment),
Metadata (только отступы), TestTU (исходные OPEN/CLOSE privacy histories в двух
positive fixtures; три refusal сохранены). Остальные 212 входов совпадают.
Все **216/216 current bytes** совпали с GREEN3 manifest; SHA256 самого manifest:
`fe48793a1db8a3512aa9ee96bc5f32baeba6602d5f411b56a27adbe2d35110a1`.

**Текущий bounded source verdict: GO, CRITICAL 0 / HIGH 0 findings** в ранее
прочитанном delta457 с указанными узкими изменениями. Это исправление оценки
reviewer, не перенос runtime с прежнего кандидата. Ponytail: предложенная
лишняя строка удалена; дополнительных обоснованных удалений в этой правке нет.
`Lean already` относится только к проверенному source scope.

Дополнительно прочитаны GREEN3 result.json и actual-test.log: terminal,
build0/test0/executed_tests1/postflight216/saved owned_processes0; PE
`7ce4a24f7aa2cd395d780362ff44c5f5e4fc0e7611013476f09ff4e88790ebc8`.
Лог содержит две accepted1/error0 строки, три preserved refusal и summary
cases5/positive2/preserved_refusals3, cold AAC OPEN/CLOSE history, exact memory,
Test Passed, 25.18sec. Это пять внутренних cases одного выполненного CTest,
не пять самостоятельных CTests. Live guest/CIM reviewer не вызывал.

Новые default regression и returned26 на этом PE этим append **не приняты**:
их финальная независимая квалификация остаётся отдельной до terminal evidence.
Весь P2/T116, public/installed/device/power-loss/release и cleanup остаются вне
этого GO. Записан только этот append; frozen456 и bundle457 не изменялись.

## Append — final GREEN3 default regression: terminal evidence принято

Дата: 2026-10-16. Независимо прочитаны `regression3/result.json`, result.xml,
test.log и полный actual-test.log; validate.ps1 только прочитан, не исполнялся.
Receipt terminal true, build0/test_exit0/executed_tests1/postflight216,
saved owned_processes0, без failure. XML содержит ровно один testcase
`V5LocalRecordingWriterTests`, tests1/failures0/disabled0/skipped0/status run,
208.445sec; полный LastTest copy — Test Passed, 208.45sec.

Manifest GREEN3, regression3 и returned3 побайтно одинаковы; current снова
проверен 216/216 без несовпадений. SHA256 manifest:
`fe48793a1db8a3512aa9ee96bc5f32baeba6602d5f411b56a27adbe2d35110a1`.
Сохранённый PE в regression3 совпадает с primary GREEN3:
`7ce4a24f7aa2cd395d780362ff44c5f5e4fc0e7611013476f09ff4e88790ebc8`,
6923776 bytes. Script проверяет actual guest source до/после, записывает PE
до CTest и отказывает при изменении после; это проверка сохранённой привязки
доказательств, не самостоятельное live чтение PE/CIM reviewer.

XML output обрезан на 1024 bytes и не использован как доказательство всех cuts.
В полном actual-test.log независимо пересчитаны:

- все 24 ordinal1–24, каждый child_exit88/waited1/canonical_queue_unchanged1;
- continued1 ровно у ordinal22 и23; у остальных continued0;
- summary cases24/sealed_cold_decode1/continued2/process_crash1/power_loss0;
- прежние три positive modes0/1/2 с cold AAC/history и 15 отдельных отказов
  case0–14, summary unchanged_disk/exact_memory/all_jobs_pins_returned;
- прежние cold-prefix/sealed-phase guards и два protected playback outcomes
  held_jobs0/2 с ok1, затем общий Test Passed.

**Verdict: final default V5 regression3 PASS принят на точном GREEN3 source/PE.**
Это один CTest с внутренними cases, не 24 самостоятельных теста и не
доказательство power-loss или произвольных offsets. Исторический named RED и
ранние кандидаты не переписаны этим PASS.

**returned3: ещё не принят.** На момент последнего чтения в каталоге были
source/prior/changed/build/test files, но отсутствовали result.json, result.xml
и actual-test.log. Наличие начатого CTest/успешного build не считается terminal
результатом 26 returned faults. Общий finite runtime closeout остаётся pending
до чтения этих финальных материалов; новых запусков/ожиданий в цикле reviewer
не выполнял. Единственная запись — этот report, включая указатель актуального
статуса сверху. Bundle457/frozen456/source/norms/tasks/markers не изменялись.

## Append — final returned3: terminal evidence и finite runtime closeout

Дата: 2026-10-16. Этот append заменяет только прежний pending returned3.
Прочитаны final returned3/result.json, result.xml, полный actual-test.log и
test.log (UTF16LE декодирован). Receipt terminal true/build0/test_exit0,
executed_tests1/postflight216/saved owned_processes0, без failure. XML:
ровно `ProtectedRecoveryReturnedFaults`, tests1/failures0/disabled0/skipped0,
status run, 120.955sec. Полный LastTest copy — Test Passed, 120.96sec;
CTest total120.97sec. Обрезанный XML system-out не заменяет полный журнал.

Все 26 строк COLD_RECOVERY_RETURN независимо пересчитаны: каждая hit1,
rejected1/error6. Есть обе точные late publication ошибки role5/operation2
after_event23 и role5/operation3 after_event24 с native c000007f, а также
реальная late cancellation role0/operation8 с native000003e3 (995).
Итоговый summary: cases26/exact_memory1/canonical_ids_queue_unchanged1/
late_seal_cold_decode1/audio0/network0. Это конечные 26 выбранных cuts,
не все произвольные offsets и не power-loss acceptance.

Current заново проверен: 216/216 без расхождений, manifest returned3 побайтно
равен GREEN3 и regression3. Точный SHA256:
`fe48793a1db8a3512aa9ee96bc5f32baeba6602d5f411b56a27adbe2d35110a1`.
Final receipt PE равен primary/default:
`7ce4a24f7aa2cd395d780362ff44c5f5e4fc0e7611013476f09ff4e88790ebc8`,
6923776 bytes. Process0 — сохранённый факт harness, не live CIM reviewer.

**Итог: bounded source/runtime GO для completed scope457 на final GREEN3.**
Приняты отдельные фактически выполненные primary completion5 (2 positive
OPEN/CLOSE +3 refusal), default V5 regression3 (включая24 process cuts с
continued ровно22/23) и returned3/26 на одном manifest/PE. Это три отдельных
CTest исполнения, не новая широкая suite и не закрытие всего P2/T116.
Исторический named RED и отзыв ошибочного P1/HIGH сохранены. Новых
CRITICAL/HIGH findings нет; Ponytail verdict не изменён.

Reviewer изменил только этот отчёт. VM/tests/evidence scripts/cleanup/Git
не запускались; source, frozen456, bundle457, code/norms/tasks/checklists
не изменялись. Sealing evidence выполняет main; данный GO не даёт полномочий
на cleanup, commit/push/install/release или public readiness.
