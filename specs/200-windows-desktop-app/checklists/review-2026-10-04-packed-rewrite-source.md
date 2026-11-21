# Независимая проверка исходников: packed existing-block rewrite / T116

Дата: 2026-10-04. Владелец отметок — независимый reviewer.
Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch/HEAD: `codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Risk lane: independent source review внутри active high-risk-product.

## Первоначальный ограниченный вердикт до M1 delta

**7 checked / 2 unchecked. SOURCE ACCEPTANCE НЕ выдан.
Статические findings: CRITICAL=0 / HIGH=0 / MEDIUM=1 (M1).
Execution evidence текущих новых веток пока pending (PRS009).**
M1 — конкретный пробел заявленной отрицательной матрицы, не доказанный баг
production. Новый full-last success case прочитан и принят статически.
Предыдущее tail source acceptance не перенесено на этот diff.

Requirements gate16/0 принят ранее, SHA-256
`91870c1e8ffe1d7a2bacaf8cc64c4e90a77542b5daef2992da537ca3accf51b5`.
Source-ready разрешал чтение, не автоматическое принятие до terminal receipts.
Reviewer изменяет только этот NEW report. Старые reports/marks, нормы, задачи,
код, тесты, CMake и dirty round222 не изменяет; VM/build/tests/GitHub/install/
commit/release не исполняет. Read-only source/hash операции — свои;
native/portable execution ниже — сообщения main, не свои запуски.

## Reviewer-owned source критерии

- [X] PRS001 Два public API делегируют один private commit с optional existing index; absent=append и present index0 не смешаны, obsolete replaceTail/alias удалён, caller descriptors/второй backend/mutex отсутствуют.
- [X] PRS002 Index<count проверяется до multiplication; full/interior принимает exact full, short-last same/growth; replacement count неизменен, max length/ceil count и generation/slot arithmetic безопасны на 64GiB и UINT64_MAX. Invalid input/shrink/hole не создают candidate effects.
- [X] PRS003 Сохранены Guard/job/Owner/mutex, writeReady/first observed fault/nativeError, exact прежняя pair/selected authority, stale refusal, pre-HEAD admission и result/base lease без throwing return.
- [X] PRS004 Authenticated BASE paths и все exact unchanged refs ограничивают structural diff одним index; tail/siblings не растут при interior rewrite. Exact selector/version/extent/SHA/decode, ZERO splitting и ≤1DATA+3NODE/290816B сохранены без full old-DATA scan/flat index.
- [X] PRS005 Первый flush/readback, pre-HEAD prospective proof allocation, physical HEAD attempt/flush/обе exact cells/selected-base peer/repeated records и confinement предшествуют ACK; before-head notCommitted/post-head ambiguous/sticky, orphan tail не truncate/reuse.
- [X] PRS006 Старые immutable bytes/root/length и pins/custody сохранены после новых publications/eviction; read выдаёт exact full/short bytes и cold verify проверяет обе closure, не переносит proof через ownership gap.
- [X] PRS007 Согласованная success/refusal/forged-tail матрица в исходниках прочитана: first/middle/full-last/short-last, neighbors/short-tail/pinned/stale/cold/radix/limits/admission. M1 исправлен новым BadDescriptor::fullTail: real sealed DATA3/root, valid descriptor lengthB/count1 до real HEAD publication, затем rejectsAndLatches; прежний tail mismatch3→4 сохранён. Это достаточность тестовых исходников, не результат исполнения нового case; исполнение остаётся PRS009.
- [X] PRS008 Actual shared-worker fault matrix отдельно full/short append, short-tail replacement и interior full rewrite на nonempty base использует per-mode measured cuts/HEAD boundary, exact outcome/first error/custody/admission и valid non-target sibling negative под real codec/SHA/DPAPI/child semantics. Read payload выполняется после фиксации completedCounts; CMake/Release assertions не ослаблены.
- [X] PRS009 Terminal результаты на текущем после-M1 снимке представлены main: guest26240 MATCH4/4 EXIT0; allReleasebuild37589 EXIT0 → Windows CTest34017 41/41 PASS EXIT0; Debug2targetbuild58951 EXIT0 → Windows CTest60220 2/2 PASS EXIT0. Четыре локальных SHA лично повторно сверены. Portable10915/37381 39/39 PASS учитывается отдельно, без native fixtures; прежние RED/build failures не объявлены PASS. Reviewer исполнения не выполнял; подробности и границы принятия в заключительном дополнении.

## M1: отсутствует явный full-block payload mismatch negative

При прочитанном TreeTests SHA `def2e7b…` точное место:
`apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp`
**680–704**, `BadDescriptor`/`descriptors()`, особенно **699**.
Generated DATA содержит3 bytes; case tail ставит logical length4, с корректным
count1, records и HEAD sealing. Это полезный short-tail mismatch, но не
full-block edge, требуемый main proposal и gate CHK013.

Прочитанный FormatTests:215–220 отдельно проверяет tail7→8; это тоже не
full edge. Успешные full rewrites и invalid input B−1 не заменяют отказ
от authenticated on-disk full-block layout с коротким DATA.

Минимальное действие main: добавить generated native отрицательный case
с реальным sealing/DPAPI/checksum/envelope SHA, у которого descriptor length
ровно B=262144/count1, а reachable DATA payload короткий (например3 илиB−1).
Путь/root/type/offset/version/hash должен оставаться корректным, чтобы
`decodeChild`/exact full payload semantics отвергли его, а не ранний framing
или checksum. Существующий `rejectsAndLatches` подходит для absence of proof,
first fault и запрета normal effects; затем новый exact source SHA и native
исполнение. Это дополнение уже заявленного покрытия, не новый product gate,
архитектура или требование полного T116. Действующий код выглядит способным
отказать такому объекту, но этот случай ещё не предъявлен в тестовых исходниках.

## Прямое чтение production пути

Полностью прочитаны Tree.h, Tree.cpp и оба test caller файла. После
двух сообщённых изменений заново прочитаны изменённые участки: private
параметр `replacement` и full-last aligned rewrite; их fresh hashes ниже.
code-reviewer перечитан. Полное прежнее чтение неизменных норм и Guard/Files
переиспользовано только после fresh SHA сравнения; это не новое полное чтение
всей продуктовой документации. Лично повторно прослежены Guard methods,
Format::decodeChild/descriptor и CMake routing. Root guidance/active нормы
и requirements доказательства остаются из gate по неизменному SHA.

### API и арифметика

Tree.h37–46/Tree.cpp114–120 дают public appendBlock/replaceBlock и один private
`commitBlock(input, optional<uint64_t> replacement)`. `std::optional` в bool
context проверяет наличие, не численное значение: existing index0 не append.
Параметр index→replacement не меняет алгоритм и устраняет C4457 hiding loops.

Tree.cpp134–143: writeReady перед input. Built-in `||` short-circuit гарантирует,
что `*replacement>=base.blockCount` отвергается до вычисления offset. Private
verified descriptor уже имеет length≤64GiB и count=ceil(length/B), поэтому
existing index≤262143, offset<length и offset≤64GiB−B. Ни умножение, ни
вычитание не overflow/underflow. Global input≤B плюс input≥min(B,length−offset)
означает exact B для full/interior и oldTail..B для last-short.

Tree.cpp152–155,238–239: generation проверен до +1, block из index илиcount;
length=max(oldLength,block×B+inputSize); replacement count=oldCount,
append count=oldCount+1. Interior/full-last не увеличивает EOF; short-last
growth сохраняет прежний ceil count. Aligned append на length<limit имеет
≥B свободного представимого диапазона и даёт именно oldLength+inputSize.
Count≤262144 помещается в u32. Slot=(generation−1)%2. Bounds не disk quota.

### Structural proof, ACK и сохранность

Tree.cpp144–151 проверяет pin/dirty и exact previous heads/selected до записей.
163–196 читает authenticated BASE path и валидирует64 children каждого node;
slots вычислены по stride4096/64/1 и проверяются<64. ZERO splitting создаёт
только changed path, сохраняя прежние explicit ranges и short tail. Для
interior/full replacement length неизменна, значит другие child payload rules
не меняются; для last-short growth нет другого DATA, которому нужен full tail.

201–239 append ровно1DATA+3NODE после actual EOF, с bounded append span и
новыми version=base+1; старые references копируются exact. Validate240–262
independently openReferenced по protected ref, exact envelope SHA до decode,
exact payload size и все64 expected children, включая точное побайтное
сравнение unchanged BASE refs. Код не доверяет caller root или writer body.

264–299 сохраняют прежний порядок двух flush/readback этапов и обеих heads.
Prospective Tree/control allocation в269 до HEAD. Logical headStarted не
исчезает при завершении physical publish; catch всё ещё держит Guard/job/
mutex/owner. Pair equality, actualSelected и selected-base peer в291–292,
повтор validate в293 предшествуют snapshot/committed в295–297. Base lease
сформирован до try; result shared_ptr/scalars nothrow в tests static_asserts.

readBlock303–370 проверяет block<count, Guard/child path и exact count
min(B,length−block×B); decoded body должно иметь этот exact размер. ZERO
только явные zero ranges внутри descriptor. Старый root immutable; новые
records append-only. verify77–111 streaming-проверяет обе HEAD closures
перед proof, не делает выбор одного валидного highest head вместо старого peer.

## Прямое чтение test coverage

TreeTests273–331:3 full DATA+short tail, index1/0/2 rewrite с разными bytes,
проверка всех трех full и unchanged short tail до/после каждой операции,
generation+1/bounded growth, pinned old root после eviction обеих HEAD,
UINT64_MAX/EOF index, wrong full-size input, stale no-growth и actual cold reopen.
332–365: compact64GiB ZERO base, indices0/63/64/4095/4096/262143, exact new
bytes/neighbor zeros/old pinned read/noEOFbytes и отдельный cold verify.
366–453: предыдущие short1/3/B−1/B success/refusal/admission tests converted
на existing index0, same/grow→full→nextshort, old-tail immutability;
424–430 — новый full-last at aligned EOF success с actual bytes.
Далее liveBoundaries/inlineZERO/descriptor/shape/pair/corruption/owner lifetime/
allocator pressure прежние; generation max append и existing replace проверены.

OwnerTests240–257: mode CommitCase::append/tail/interior; replace выбирает1.
Tail base full0+short1; interior base full0/1/2+short3. Main740–743 вызывает
полный append, short3, replacement5 и interior B. Codec spy154–198 меняет
slot0 DATA→valid ZERO, не target1; generation=actualbase+1, length actual
candidate и count=ceil(length/B), поэтому short-tail/interior layouts не
прикрываются guessed count2. Actual decode flag требует успешных real
SHA/DPAPI/inner context/child semantics перед structural diff отказом.

OwnerTests287–305 сначала исполняет successful mode baseline, сохраняет
completedCounts и pre-HEAD pressure checkpoint, а затем читает committed
payload. Поэтому readBlock не расширяет commit cut ordinals. Loops306–343
вводят failed/short/zero write, read/changed/throwing read, flush, pre/post
metadata exceptions на measured actual IO, проверяют logicalHeadAttempted,
notCommitted/ambiguous, no snapshot, retained base lease, native first error,
sticky retry без IO, invalid othermode не маскирует fault, external writer denied.
345–363 проверяют prospective proof pressure после первого flush/validate,
до HEAD. 387–403 — initial owned pressure/no native IO/sticky failure.

REAL Files.cpp TU включён до codec macro, REAL Tree.cpp — после, codec
делегирует real seal/open; product fault flags не добавлены. CMake97–102
исключает duplicate Tree OBJECT только для WIN32 OwnerTests, portable
получает обычный object. `/W4 /WX` и #undef NDEBUG сохранены; native fixtures
не исполняются на portable. Ни portable count39, ни build не доказывают matrix.

## Снимок, лично сверенные SHA-256

| Артефакт | SHA-256 |
| --- | --- |
| Tree.h | `edbce5c8939d19601d99330d556925065ba4838d27b3007dc6df9c0cf0ad70bc` |
| Tree.cpp, после parameter rename | `dc8f71fd3c5be15068545fcab3b35ff63a02ca62d030681f83ec6922cd212712` |
| TreeTests.cpp, после aligned full-last | `def2e7b231eccb6458fb3d8f2e5ba0eeeca2da757370d720f31f40fbbe8441cf` |
| OwnerTests.cpp | `6b097ac7f085d3b1923737181af50e454ba497ec8bcbe1f6dcf0d752206bb210` |
| apps/windows/CMakeLists.txt, baseline unchanged | `34512b061361516a997c0581b6a693d9535d3d5e6893cb2b017a2a061b96e295` |
| ProtectedPackedCustodyOwner.h, baseline unchanged | `99dee259444c8a552d3e759e91e10a5a301d38991bfa655ebb90e5abb03922ed` |
| ProtectedCustodyFiles.cpp, baseline unchanged | `c7ddc8367c205a9f6e2177ff54b9a46ccc7e8b7a039079dba863378e67b11882` |

Source paths в таблице: Storage — `apps/windows/RecApp/Storage/`,
test caller файлы — `apps/windows/Tests/GrafWindowsCoreTests/`.
Нормативные свежие hashes совпали с requirements gate: spec7c212…, plan876bf…,
tasksce8aaf…, quickstart2a1c49…, constitutiond28f83…, packedcontract7ff9a1….

Первоначально лично прочитанные Tree.cpp `1d5b4147…` и TreeTests `fa95f5bf…`
заменены двумя явно сообщёнными изменениями; новые участки перечитаны.
Старый portable receipt не принят для текущих SHA. Любая следующая source
правка требует отдельного diff/read/identity review; эта таблица не будущий SHA.

## Сообщения main о выполнении — не execution reviewer

- RED41003: Windows Release compile **EXIT1**, C2039 missing replaceBlock
  в новых test lines303/307/315/324 до API реализации. Это ожидаемый RED,
  не successful native implementation.
- First implementation Releasebuild94529 **EXIT1**, C4457/WX: optional index
  скрывал loop index. Main исправил только private parameter replacement
  и четыре usage context; warnings не ослаблены. Текущий cpp SHA сверён,
  но terminal native build после исправления пока не представлен.
- Initial portable52331 BUILD0 / CTest5573 **39/39 PASS27.20s / EXIT0** —
  предыдущий cpp parameter snapshot, `_WIN32` fixtures исключены.
- Main сообщил final portablebuild57790 **EXIT0**, final CTest dispatched;
  terminal результата пока нет. Не принимается как native PASS.
- Main сообщил guest TreeTest copy19899 **EXIT0** и новое Release2targetbuild
  после terminal27062. Receipt полного final guest4SHA/native execution
  пока отсутствует; доступность/копирование/dispatch не terminal suite PASS.

Ни будущий Release/Debug PASS, ни остальные39regressions, AppBuild/EXE,
installed/app/hardware/audio/performance/cadence/Stop acceptance не выданы.
M1 и PRS009 открыты независимо: successful native tests не добавят отсутствующий
counterexample. При закрытии M1 нужны новый test hash и исполнение этого случая.

## Итог перечитывания

Отметки и report перечитаны: **7 checked / 2 unchecked**. Остались M1
с точным действием main и PRS009 с pending terminal native evidence.
Новых C/H алгоритмических дефектов не выявлено; конкретный тестовый пробел
не объявлен production vulnerability. Не требуются новый backend/нормы/
product policy или полная T116 для этого prerequisite.
Reviewer изменил только новый source report; gate16/0 и старые reports/marks
сохранены. T116–T118, последующие WriteAt/SetSize/shrink/cursor/Clone/adoption/
migration и общая Windows приёмка остаются открытыми.

## Дополнение: terminal portable/build, native suite ещё pending

Main сообщил final portablebuild57790 **BUILD0 / EXIT0** и CTest97846
**39/39 PASS, 24.56s, EXIT0** на текущем final snapshot. Это новый portable
receipt, не начальный5573; native `_WIN32` fixtures по-прежнему исключены.
Final Windows Release2targetbuild67257 **EXIT0**, actual CTest23574 pending.
Governance92066 OK, doctor frozen OK, YAML0 и неизменность нормативных hashes
— отдельные проверки main, не native test outcome. Reviewer их не исполнял.

**Итог остаётся 7/2, C0/H0/M1; SOURCE ACCEPTANCE не выдан.** M1 требует
короткого DATA на full-block layout negative; PRS009 — terminal актуальное
native исполнение. Ни сборка, ни portable PASS не закрывают эти два пункта.
Длительности не cadence/Stop/performance evidence. Новые источники, старые
reports/marks и нормы reviewer не менял; установки/private audio не выполнял.

## Дополнение: завершённый native Release23574

Main сообщил Windows Release CTest23574 **2/2 PASS, 111.02s, EXIT0**:
OwnerTests **97.59s**, TreeTests **11.85s**, на записанных final4SHA.
Это terminal native исполнение текущих новых веток, не portable/build PASS;
reviewer его не исполнял. Локальные four source hashes повторно сверены,
совпадают с таблицей. Предыдущее pending Release состояние историческое.

Debug2targetbuild dispatched после завершения Release; terminal Debug
build/test и остальные39 Release regression receipts ещё не представлены.
PRS009 остаётся открытым до этих согласованных execution результатов.
M1/PRS007 остаётся независимо открытым: Release PASS не создаёт отсутствующий
full-block mismatch negative. После его добавления тестовый SHA и исполнение
должны соответствовать новому снимку; старый PASS не переносится автоматически.

Окончание текущего статического прохода: **7 checked / 2 unchecked,
C0/H0/M1; SOURCE ACCEPTANCE не выдан**. Source findings сформулированы по
исходникам; native время не performance/cadence/Stop proof. Изменён только
этот report; старые отметки, нормы, код, tests, VM/install/Git/GitHub mutations
не выполнялись. Основному агенту передаётся точное действие M1, не новая
архитектура и не требование завершить полный T116 для этого prerequisite.

## M1 delta: повторное чтение и закрытие статического замечания

Source-ready M1 delta получен отдельно. Лично прочитан текущий
TreeTests680–709: `fullTail` добавлен в enum, loop и switch; case700 меняет
только logical length на262144, сохраняя count1 и реальный short DATA3,
reachable путь/root с correct context/version/offset/envelope SHA из fixture.
Строки704–706 прямо требуют успешный decodeDescriptor и exact lengthB/count1
до fixturepublish; descriptor/framing не могут подменить ожидаемый отказ.
Реальное sealing HEAD в708 и прежний rejectsAndLatches в709 проверяют отсутствие
Tree proof, first-fault retention и запрет normal effects. `tail`3→4 в699
сохранён. Прочитанная decodeChild семантика требует payloadB для этого
descriptor, поэтому case адресует именно недостающее full-block mismatch.

**M1 закрыт по исходникам; PRS007 отмечен [X]. Новых C/H/M замечаний нет.**
Это не native PASS нового случая. Правка минимальна, production путь и Owner
matrix не изменены; новый API/архитектура/нормы не требуются.

Fresh personally verified final source SHA-256:

| Файл | SHA-256 |
| --- | --- |
| TreeTests.cpp после M1 | `991f14df6e336134e70dc933295bec7cd72ac0417de4da483451ae9a2b09fb2c` |
| Tree.h без изменения | `edbce5c8939d19601d99330d556925065ba4838d27b3007dc6df9c0cf0ad70bc` |
| Tree.cpp без изменения | `dc8f71fd3c5be15068545fcab3b35ff63a02ca62d030681f83ec6922cd212712` |
| OwnerTests.cpp без изменения | `6b097ac7f085d3b1923737181af50e454ba497ec8bcbe1f6dcf0d752206bb210` |

Предыдущий снимок TreeTests def2e7b… и его portable/Release receipts остаются
историческими. Debug84108 BUILD0 также относится к pre-M1 test hash, без
terminal CTest; не принимается как current execution. Main сообщил новые
native и portable rebuild/retests pending: никакой будущий PASS не принят.

Отметки и дополнение перечитаны: **8 checked / 1 unchecked (PRS009),
C0/H0/M0; финальный SOURCE ACCEPTANCE НЕ выдан**. Только terminal исполнение
актуального после-M1 снимка может закрыть PRS009. Границы полного T116,
installed/hardware/audio/выпуска неизменны. Reviewer обновил только этот
свой report/marks; старые reports, gate16/0, код/тесты/нормы, VM/Git/GitHub/
install/commit/release не менял и не исполнял.

## После M1: portable PASS и allRelease build, suites pending

Main подтвердил текущий TreeTests991f14df… и остальные три неизменных SHA.
Сообщены post-M1 portable10915 **BUILD0** и CTest37381 **39/39 PASS,
11.52s, EXIT0**; native allReleasebuild37589 **EXIT0**. Исполнение принадлежит
main, не reviewer. Portable `_WIN32` cases не выполняет; этот результат
не native acceptance fullTail.

Полный Windows Release CTest41 dispatched, terminal результата пока нет.
В отличие от прежнего этапа, main планирует один полный41-run; он не принят
заранее и не подменён суммой прежних2+39. DebugTree rebuild и2CTest следуют
последовательно; их terminal receipts также pending.

Сообщённый current Windows binary diff SHA-256:
`4538a9f57856462188ad7f8d5f326590505bc7b9100c9a982594be49b5c5f9e1`.
Это hash diff, не built/installed EXE или package digest.
**Итог 8/1, C0/H0/M0; PRS009 открыт, SOURCE ACCEPTANCE не выдан.**
Отметки/дополнение перечитаны; M1 закрыт статически, его новый native outcome
не выдуман. Только свой report обновлён, без новых gates или расширения scope.

## После M1: завершён полный Windows Release41-run

Main предоставил guest26240 **MATCH4/4, EXIT0**, включая TreeTests
`991f14df6e336134e70dc933295bec7cd72ac0417de4da483451ae9a2b09fb2c`,
и terminal Windows Release CTest34017 **41/41 PASS, 156.32s, EXIT0** после
allReleasebuild37589 **EXIT0**. OwnerTests **93.85s**, TreeTests **12.16s**;
остальные39 cases также включены в этот один полный запуск. Это post-M1
native исполнение, не сумма старых2+39 и не перенос pre-M1 результата.
Portable37381 **39/39 PASS, 11.52s, EXIT0** остаётся отдельным ограниченным
portable доказательством. Все эти запуски/guest checks выполнял main,
reviewer их не повторял.

Main сообщил отсутствие новых source правок; четыре локальных SHA повторно
сверены с после-M1 таблицей, совпадают. Новый fullTail имеет terminal Release
исполнение вместе с остальной матрицей. Final Debug2targetbuild dispatched
последовательно после полного Release; terminal Debug build/test пока нет.
**PRS009 открыт только по оставшемуся актуальному Debug evidence;
итог 8/1, C0/H0/M0; SOURCE ACCEPTANCE ещё не выдан.**
Предыдущие pending Release записи исторические. Длительности не
performance/cadence/Stop proof; installed/fullT116/audio/release не приняты.
Отметки и дополнение перечитаны; обновлён только собственный report.

## Заключительное дополнение: после-M1 Debug и ограниченное принятие исходников

Main предоставил terminal Debug2targetbuild58951 **BUILD0 / EXIT0** и
Windows Debug CTest60220 **2/2 PASS, 129.34s, EXIT0**: OwnerTests **111.58s**,
TreeTests **16.50s**. Это текущий после-M1 снимок, не прежний Debug84108.
Вместе с guest26240 **MATCH4/4 / EXIT0**, allReleasebuild37589 **EXIT0** и
полным Windows Release CTest34017 **41/41 PASS, 156.32s, EXIT0** согласованные
native критерии PRS009 выполнены. Portable10915 **BUILD0** / CTest37381
**39/39 PASS, 11.52s, EXIT0** остаются отдельным результатом: `_WIN32`
fixtures на portable не исполняются. Все сборки, guest checks и тесты
выполнял main; reviewer лично проверял исходники, изменения и локальные хеши,
но не запускал VM/build/CTest. Времена запусков не являются доказательством
performance, cadence или длительности Stop.

При окончательной сверке четыре локальных исходника совпали с таблицей
после-M1: Tree.h `edbce5c8939d19601d99330d556925065ba4838d27b3007dc6df9c0cf0ad70bc`,
Tree.cpp `dc8f71fd3c5be15068545fcab3b35ff63a02ca62d030681f83ec6922cd212712`,
TreeTests `991f14df6e336134e70dc933295bec7cd72ac0417de4da483451ae9a2b09fb2c`,
OwnerTests `6b097ac7f085d3b1923737181af50e454ba497ec8bcbe1f6dcf0d752206bb210`.
Сверены также неизменные CMakeLists.txt, Owner.h, Files.cpp, spec, plan,
tasks, quickstart, constitution и packed contract. Requirements gate
`91870c1e8ffe1d7a2bacaf8cc64c4e90a77542b5daef2992da537ca3accf51b5`
не изменён: **16 checked / 0 unchecked**.

**SCOPED SOURCE ACCEPTED: 9 checked / 0 unchecked; C0/H0/M0.**
PRS009 отмечен независимым reviewer; M1 исправлен и исполнен на текущем
снимке. Принят только bounded existing-block rewrite: прежний единый worker
для appendBlock и replaceBlock, точные размеры/границы и сохранение EOF/count,
неизменные sibling/short-tail bytes, pinned roots, cold verification и
согласованная native success/refusal/fault matrix. Исторические 7/2, M1,
pre-M1 hashes и pending receipts выше сохранены как история, а не текущий
вердикт. Любая новая source правка требует новой сверки и соответствующих
доказательств; принятие не переносится автоматически на будущий снимок.

Отдельные дополнительные сообщения main, не условия source acceptance:
AppVSbuild28243 incremental Release/x64 `/t:Build` **EXIT0**; прежний D9025
warning остаётся, clean rebuild/zero warnings не заявлены. Built EXE SHA-256
по89147 **EXIT0**:
`e79bb4e7bba94d9d82e0b929d7ecbd1e528076fc0d1a06bcdc78ec3b2249b090`.
Reviewer EXE не читал и не запускал. Main также сообщил governance43706
OK / doctor frozen OK / YAML / diff **EXIT0**. Эти результаты не означают
package/install/runtime/hardware acceptance и не подменяют native tests.

Полная T116 не принята: arbitrary/partial/cross-block WriteAt, SetSize/shrink,
cursor/Clone, consumer integration и последующие T117–T118/migration остаются
отдельной незавершённой работой. Установка, запуск нового EXE, пакет, private
audio, аппаратная приёмка, полная Windows функциональность и выпуск здесь
не подтверждаются. Commit/push/PR/merge/release не выполнялись.

Reviewer применил code-reviewer внутри существующего high-risk Spec Kit
пути и изменил только этот собственный source report/marks. Код, тесты,
нормы, tasks, gate16/0, старые отчёты и отметки не изменялись. Заключительное
дополнение и все девять отметок перечитаны; итог **9/0, C0/H0/M0**, без
новых требований, задач или расширения объёма принятия.
