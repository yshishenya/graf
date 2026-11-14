# Round449 — bounded source / primary / reconstruction review

2026-10-16. Independent reviewer, high-risk-product, existing T116/#7444.
Authoritative repo `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Evidence `/Users/yshishenya/Documents/graf-f200-recovery449.REsq8N`.

## Current verdict

**Bounded GREEN6 source correctness + primary runtime GO.** Blocking findings0
in the reviewed test-only delta. **Eleven regressions pending qualification;
no final Round449 runtime/cleanup GO yet.** T116 and external gates stay open.
This report supersedes GREEN5 as current source; historical failed receipts
remain failures. Used code-reviewer and ponytail-review, without executing VM,
builds or tests. No source/norm/tasks/checklist/GitHub mutations by reviewer.

## Exact source and scope

Current/frozen GREEN6 **216/216**, manifest
`99b6941e0ec32c556de10b71f3e0437eaeaacfa64b5778a761a90f2992e91443`.
Compared all216 with accepted448 manifest retained as449/red/source.sha256:
**only NativeCaptureStorageIntegrationTests.cpp differs**, SHA
`da874b323ff0472e24d40632bf2e687969d9137d03188dfb9ce11f6cd95c09af`.
All retained current frozen copies match their manifest. NativeCapture,
V5/Storage/Queue/CMake production inputs unchanged from448. Read the complete
TestTU delta versus retained448 baseline, affected helpers, actual rename/read
cuts and corresponding NativeCapture/Scheduler/AppMain callers.

Existing requirements gate remains the accepted pre-implement refresh in
round448 requirements report:198files/452checked/0unchecked, ten normative SHA
unchanged, scoped C0/H0, existing T116 open. This report does not recreate that
gate or mark implementation tasks complete.

## Source correctness and oracle conclusions

### Committed intent → held recovery → actual local purge

`protectedDeletionDisplayDrain(true,true)` uses genuine durable owned A
reservation/g2 and cold canonical content; birth owners have exited. Actual
nonempty packed read is held on existing recovery executor. The observation-only
peer reads the UI-owned deletion flight's actual phase=purge; it injects no
proof, queue state, success or owner capability.

The real `beginProtectedDeletionSelection` commits deletionIntent g2→3, then
separate pollStorage adoption precedes flight progression. While read remains
held, a100ms service window calls actual pollUploads and rejects completion,
new worker ticket or OS absence; whole package snapshot is unchanged and HTTP0.
After release the test waits the real deletion completion, requires saved1,
accepted1/pending0/rejected0/unknown0, retained deletionPurge committed g3→4,
rows0 and actual path absence, then drains/shuts down and cold reopens queue g4
empty with absence and exact idle memory. This is confined user local recycle,
not shredding, server purge or general missing-path authorization.

**Retained ticket fix is correct.** NativeCapture::protectedDeletionTicket
returns lastDeletionTicket by exact ID; pollStorageStartup updates it only for
deletion kinds. last worker ticket is not a completion registry and can already
be an unrelated uploadPrepare. In this one-row fixture intent reserves the
continuation; requestProtectedUpload refuses while continuationId exists;
no other recording/mutation is requested. Thus the sole next deletionPurge is
intent.id+1. Kind/state/base/target and independent physical/completion/cold
assertions prevent replacing the ACK with an arbitrary later ticket. This ID
arithmetic is fixture-specific, not a new production/API invariant.

**GREEN6 teardown fix is correct.** Exact GREEN5→GREEN6 delta is one line:
shutdown wait now calls capture.pollUploads before shutdownWorkDrained.
pollUploads performs value ACKs, pollAccount and scheduler.retireProtected;
shutdownWorkDrained/updateWorkDrained require !scheduler.busy. A completed
protected flight is not retired merely by observing that predicate. AppMain
refreshNativeState also continues pollUploads during exit. Admission is already
closed by shutdown, so this services existing work without admitting a new
upload, releasing a lease artificially or forcing a success result.

### Ambiguous new recording finalizer while old B read is held

`protectedRecoveryLivePlayback(true,2)` keeps original normal and committed
unfinished cases as separate calls. It reuses finishLive with actual new Start
reservation ACK/g4→5, generated100frames and EOS. Existing queue-qualified
NtSetInformationFile cut runs the real successful rename first and only then
changes observed completion status; flag consumption and actual recording
ticket ambiguous g5→6 are asserted. No fabricated enum or pre-publication-only
failure is used.

After reporting ambiguous to UI, commandReconciliation and cancellation of
old B are observed. While old nonempty read remains held, no SavedLocal,
physical readback or changed projection/g5 is permitted; updateWorkDrained is
false. After release, actual recovery result/retirement permits readback, but
UI generation remainsg5 until separate pollStorage ACK. Then actual controller
reports failed (not false Saved), storage truth isg6, and shutdown drains.
Cold inspection proves three exact owned A rows, unchanged old capture_prepared
row, new normal valid1000ms/decoded AAC, old phase capturing and **whole old
package snapshot unchanged**, neighbor unchanged, HTTP0 and exact memory.
There is no blind finalize/re-encode or new normal authority from B.

No blocking lifetime, lock-order, privacy or false-success issue found in this
bounded delta. Assertions before held-cut release intentionally fail the
generated process on a violated invariant; they do not claim graceful teardown
of an assertion failure. No resource bounds or original tests were removed.

## Independently read saved primary evidence

GREEN6 result.json terminaltrue/build0/test0/**39496ms**/postflight216/
saved owned_processes0. Native PE
`737733e2a17ae7f12a90147e29ed62d3972c01e6ee0372e29ee86ce2cff4ceb5`.
Build.log actually compiles NativeCaptureStorageIntegrationTests.cpp. Read full
stderr and validate.ps1: previous terminal/source guard, exact216 input upgrade,
changed-copy timestamp refresh, real PE hash, actual child wait240s, exit,
post216/unchangedPE and saved final CIM count. Reviewer did not issue fresh
live guest/PE/CIM commands; these are qualified saved receipts, not live claims.

Actual primary covers existing5unfinished modes, unfinished live playback,
committed Stop-before-release, **new ambiguous finalizer**, existing ambiguous
deletion-intent drain and **new physical local purge**. New traces show:

- queue-qualified actual rename → ambiguous g5/no Saved/no early readback;
  old B finish ioFailed6/native995 after release; actual readback ACK/coldg6,
  new valid decode, whole old capturing unchanged/exact memory;
- committed intent ACK/g3/actual purge waiting/held read/no premature purge;
  cancellation ioFailed6/native995 after release; retained kind6/state1,
  error/native0, base3/target4, saved1/accepted1/pending0, rows0/exists0/HTTP0;
  final coldg4/emptyqueue/OSabsence/exactmemory marker reached.

Failure history is not rewritten:

- GREEN physical-only build0/exit3/34718ms: aggregate failed; no whole PASS.
- GREEN4 build0/exit3/39168ms: ambiguous subcase reached its complete cold
  assertions, but whole candidate failed purge aggregate because latest worker
  ticket was unrelated uploadPrepare kind2/pending g4→4. Diagnostic physical
  fields were saved1/accepted1/rows0/exists0; they did not make the test PASS.
- GREEN5 build0/exit3/48854ms: retained purge ACK fixed and aggregate passed,
  but passive shutdown wait failed. No cold final purge marker; whole FAIL.
- red/green2/green3 are frozen-only, not executed RED/GREEN qualification.

Primary evidence hashes:
result.json `52f4ef6a91e6db952f522f2b2cfeab3f3ffb0a95b3c6cad07e5780e315086d05`;
stderr `704f9bae22dbcc29ab311503b4a77532f39e2bb8cb3ad79d7f6726967e92a4a7`.
Eleven adjacent regressions, JUnit and final two-PE/postflight qualification
are intentionally not accepted until their own terminal evidence is read.

## Independent reconstruction

source-origin finalstage green6,216inputs/33untracked checked. FullHEADpatch
**3231690bytes**, SHA
`9a8c6db851c3bcbbad93e90d3b490f3a02d12a8cb18478e3e95cbcc843748d3e`.
Temporary private GIT_INDEX_FILE/GIT_OBJECT_DIRECTORY with original objects
read-only as alternate: HEAD→GREEN6 reconstructed **216/216**, then independently
GREEN6→green/green2/green3/green4/green5/red each **216/216**. Each delta and
manifest hash checked against source-origin and actual reconstructed blob bytes.
red matches accepted448 manifest; historical stages retain their exact states.
Current216 also rechecked after reconstruction. Normal index SHA before/after
unchanged `662a640f866392dde2940678f5d98c82c85c145c3be3aebedf2825a524e36229`.
Normal objects/worktree/evidence copies untouched; only own temporary scratch
was automatically retired. source-origin SHA
`f47579d6612f873f5d65cd2deff8049090ad5ed5e310254fce5b85bb55e94d0a`.

Ponytail: **Lean already. Ship.** Existing fixture helpers/actual hooks reused,
one observation getter, one additional finish mode and physical branch; no
new framework/dependency/public authority. No safe deletion found that preserves
the separate negative-order/ACK/cold assertions. This verdict concerns code
shape, not release approval. Cleanup not reviewed/approved yet; preserve all
current source copies pending terminal eleven-regression qualification.

## Append-only final qualification — eleven regressions / cleanup

2026-10-16. **Final bounded GREEN6 source + runtime GO для проверенного
Round449 slice; cleanup GO только для указанного ниже exact inventory.**
Этот append заменяет pending статус предыдущего раздела, не переписывает
историю GREEN/GREEN4/GREEN5 failures и не закрывает umbrella T116.

Независимо прочитаны terminal green6/regressions.json, весь JUnit, полный
LastTest.log, ctest.log, regression-build.log и actual regressions.ps1.
Windows UTF-16LE/BOM text декодирован корректно. Receipt terminaltrue,
build0/ctest0/executed_tests11/postflight216/saved owned_processes0, failure
отсутствует. JUnit ровно11 уникальных ожидаемых names/status=run,
failures0/disabled0/skipped0 и без child failure/error/skipped. LastTest имеет
ровно11 соответствующих actual commands и Test Passed. CTest total real
**455.47s** (JUnit suite time округлён455), все тесты без timeout.

| Actual CTest | JUnit seconds |
| --- | ---: |
| V5LocalRecordingWriterTests | 104.906 |
| NativeProtectedStartOwner | 14.7808 |
| NativeProtectedStartOwnerRecovery | 32.57 |
| NativeProtectedStartOwnerDegradedRestart | 1.86914 |
| NativeProtectedStartOwnerUnfinishedRestart | 39.2345 |
| NativeProtectedRecoveryLivePlayback | 11.2461 |
| NativeProtectedDeletionDisplay | 3.5825 |
| NativeProtectedLocalPurge | 92.0716 |
| NativeProtectedLocalRemoval | 93.8022 |
| NativeProtectedPlaybackConsumer | 15.0965 |
| NativeProtectedPackageRevalidation | 46.2843 |

Это11 invocations, не11 внутренних cases. LastTest повторно доказывает:
owner primary+7 classifications+3 finalizations; normal recovery modes0–7;
degraded restart; unfinished modes0–4 и сохранённые live/Stop variants;
**новый ambiguous finalizer и физический local purge**, с обеими полными
before/after-release traces, queue-qualified rename, cold new decode/whole old
snapshot и cold empty g4/OSabsence/exactmemory; normal live-playback и
deletion-display; LocalPurge modes0–8 и LocalRemoval modes0–8, включая actual
recycle/refusals/coldqueue; consumer clone/StartACK fences; revalidation cases0–3
и pins_full freshACK. Writer повторяет3 cold playable positives/15refusals,
A cold/refusal matrix и24trace/24actual process88 cuts, sealed_cold_decode1.
Power-loss/неисполненные cuts не добавляются по аналогии.

PE hashes:

- Native `737733e2a17ae7f12a90147e29ed62d3972c01e6ee0372e29ee86ce2cff4ceb5`
  совпадает с GREEN6 primary. Regression build переиспользовал уже
  скомпилированный current PE; actual TestTU compile доказан primary build.log,
  а не выдуман для regression build.
- Writer `46e9ecf67a2ebba26bb9f6a6402f510021ee9450331e03223c61bb3bdba64f4b`.

Script требует previous primary success/terminal/process0, guest216 и native
primaryPE до build, фиксирует оба PE, запускает точные11names serial с
no-tests=error/JUnit, проверяет216 и оба неизменныхPE после тестов, затем
сохраняет CIM owned count. **Это сохранённый postflight, не fresh live CIM/guest
проверка reviewer.** VM/build/tests reviewer не запускал.

Current/frozen216/216 ещё раз совпали с manifest
`99b6941e0ec32c556de10b71f3e0437eaeaacfa64b5778a761a90f2992e91443`.
Source-origin, fullHEADpatch и все6 historical manifest/delta hashes неизменны
от уже независимо проверенной HEAD→GREEN6→history реконструкции216/216 каждого
состояния. Normal index/object/worktree не затронуты этим final review.
Evidence hashes:

- regressions.json `a44c4ffe1d00ec70e3813687c35be022f73d005c5ef60fcd97922fd3924df516`;
- JUnit `ac309966c054f162e447d3cc7def8481a9f7408a7112d39f38130fe696fefebb`;
- LastTest `c8064c562d25d028cf2f617062452c1b47b53b06f63fa8ef8b4ef97fd1ecd2fd`;
- CTest `0cffa66e4de75555cb774c34288b4c9a030c9143333431b6391a2a0203dd4718`.

### Cleanup safety / exact approval

Прочитан cleanup.rb SHA
`c5e8e0391d25aad4c51854c3de5a0cdc0929ab75288fc071e2cc6601bc82625c`.
Вызван **по абсолютному пути без --delete**: **14files/4653502bytes/deleted=false**.
Два разрешённых пути (TestTU и unchanged NativeCapture.h) в семи stages:
red, green, green2, green3, green4, green5, green6; каждый file hash соответствует
его stage manifest. Current216 guard также прошёл. Дополнительно независимо
проверены actual root/stage/apps/вложенные пути через realpath/no-symlink и
отсутствие постороннего apps parent; full HEAD patch и historical deltas остаются
вне удаляемых деревьев.

В скрипте есть anchored root/stage pattern, stage/apps symlink guards,
recursive symlink refusal, exact two-path allowlist и file hash checks.
Dot entries пропускаются до обработки и до удаления пустых директорий.
**cleanup.json с проверенным inventory записывается до первого unlink**, затем
deleted=true только после завершения; при частичном отказе начальный inventory
сохраняется. Широкого recursive rm нет. Directory prune удаляет лишь пустые
directories в проверенном текущем наборе apps trees, не logs/manifests/patches.

**Cleanup GO — только эти14files/4653502bytes и опустевшие их source directories**,
при неизменных script/evidence/inventory и обещанном свежем owner live guest
preflight непосредственно перед удалением. Запускать absolute cleanup.rb.
Не удалять repo/guest build/другие sources или artifacts; сохранить manifests,
source-origin/fullHEADpatch/6historical deltas/scripts/все failed и pass
receipts/logs/JUnit. Никакое удаление reviewer не выполнял.

Ponytail source verdict неизменен: **Lean already. Ship.** Только bounded code
shape, не approval commit/push/install/release. Production unchanged448,
исторические failed candidates остаются failures. Остальной T116, changed-row
matrix, quarantine UI/playback permissions, hardware/installed/fullfeature и
release gates этим результатом не закрыты; tasks/checklist markers не менялись.
