# T116 — независимая SOURCE/runtime приёмка default wipe342

SCOPED SOURCE/RUNTIME GO342: existing Codec default теперь выполняет все39 wipe regression cases.
Блокирующих findings P0/P1/P2:0; high-risk-product lane сохранён; это test-only срез, не ALL/T116 closure.
Использованы code-reviewer и ponytail-review; reviewer не запускал builds/tests/VM/jobs/postflight/cleanup.

## Источник и единственный diff

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch `codex/200-windows-followup`.
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` + dirty bytes; injected0309 не использован.
Frozen `/Users/yshishenya/Documents/graf-f200-wipe342.fVaWAY`, source.json:
`8f9cbf93de54af8d67eb8e03cba73f12598546da1646dcd822825c798a7fa62a`.
Все209 frozen/canonical файлов rehashed exact; от341 изменён только existing ProtectedCustodyCodecTests.cpp:
`02c231ba99639d7789167ae11ceb03ad44938d4d0e8a4e16ae2a33233352824c`.
Остальные208 frozen files, включая production/CMake/dependencies, unchanged341; CTest Codec command без CLI arguments.
Normative9 exact; tasks120/93done/27open; исторические SOURCE/runtime341 reports и markers неизменны.
До этого отчёта184 checklist md;29marked/420checked/0unchecked сохранены, новые checkbox items не добавлены.

## SOURCE: default helper и oracle globals

Единственный diff:13 строк retiringMemoryTests<Value>() +3 вызова default main, без нового target/framework.
Для bytes9 heap cuts; char/wide по9heap+6string cuts; каждый reuse retiringMemoryCase(cut,true).
Immediate=true не убирает selected pre-free oracle: growth проверяет старую allocation до free, не только live tail.
Нет второго default прохода false; isolated --memory-wipe/--memory-tail CLI остаются для RED диагностики.
wipeCase получает literal cut и после серии nullptr; dangling name/чужая подпись последующих tests исключены.
arm требует !wipeAllocation, заново задаёт span/offset и сбрасывает wipeObserved; helper не маскирует leak сбросом.
Selected delete очищает pointer/offset; каждый case проверяет observed release и свой usedBytes baseline.
Новые вызовы после mutationBudgetTests, до memoryBudgetTests(c); selected oracle не пересекается с worker threads.
SSO/embedded NUL, valid string suffix alias, invalid vector self-range exclusion и raw volatile guards сохранены.
Порядок39 cases independently сверён по именам, не только общему marker count; expected tail checks30.
Ponytail: минимальное подключение existing regression к default CI; speculative abstraction/dependency:0.

## Фактический native342 и portable342

native.json `d33e15f3d2bcb7d1e8ba8b9a44c5954e8b1ea0c2a1de8c007b97be093c1de4c9`.
terminal/native_completed=true, default_wipe_green2_verified, build0; два fresh Codec default runs, arguments[].
validate.ps1 `1bb7039cc8c204a210476ce276e08371a7d1c8516ce8bb2f6f640644352cbf54` exact receipt binding.
Оба полных logs прочитаны: receipt SHA exact, combined exact stdout+stderr, zero0/assert failures0.

| Actual default run | Exit | WIPE pass | TAIL zero1 | MUTATION pass | Время |
| --- | --- | --- | --- | --- | --- |
| MSVC Debug | 0 | 39 | 30 | 3 | 13358ms |
| MSVC Release | 0 | 39 | 30 | 3 | 4349ms |
| Portable Codec внутри CTest47 | 0 | 39 | 30 | 3 | 6.82s |

Debug log `0c1f4c37d11d46f45b66547bea7b957be6a8b0f40c97bb00f21035bbd9bca581`.
Release log `888389efb97a0eb725fb5db1bfe9ea26709c5c8132139675ff761402678cd7ca`.
Build logs подтверждают recompilation test TU и link обоих Codec EXE без C4244/C2220 diagnostics.
Debug proxy16 refusal/cleanup tests проходят; Release proxy0 SKIP только отсутствующий proxy allocation proof.
portable.json `5a67dc1c2e6ef36fc0f1f23e3cd2867b8fe60f4ca9d93eb762571dfbfdfe251d`.
terminal=true, portable47_default_wipe39_verified, configure/build/test0; CTest47/47 Passed,37.74s.
Configure/build/test/default_matrix hashes exact; portable-last-test.log сохранён в evidence, не только временном build.
LastTest47 Test Passed; все39/30/3 markers находятся именно в default Codec section, CLI matrix не подменяет default.
Portable last-test SHA `2a51bfba764a392e153bb4c91a17158f72d1f588d076f1e19d5ba565482d9e90`.

## Actual postflight и неизменённые dependent артефакты341

postflight.json `72002233436c70945a69dcfa630ee45adb1c726e829b8e34e0455b779751a902`.
terminal=true, source_binary_log_postflight_verified; exact source342/native342 receipt binding,209source,idle=true.
Actual main postflight rehashes native/share209,2current Codec EXE/1Debug PDB/2logs; scripts прочитаны reviewer.
Debug EXE `445a55c956c3c59c52a3e4cd0ce12d96d9f4e915134a16e1ccc9f6a35b115830`.
Debug PDB `a56aeef5bdd1ae81844a8f59e6ad2b64c10486ef289f0bd918a040af256c9ac6`.
Release EXE `fd3610c57d827308a858a05677cd47cc691fa0ae09a9acfd320c245ef46dc029`.
Postflight отдельно сверяет8other EXE/4PDB с hard-pinned native341 receipt:
`d43a76b6783bb937f0dca7292c42e708eaf3941098fee03a6cd522653085fa51`.
Prerequisite также pinned accepted postflight341 `87d8722d601d12aebf41d337205ffabc5b46b7e5dc88e9617a402b34ae1dfc8b`.
341 dependent10 результаты остаются evidence341;8 неизменённых EXE не объявляются повторно выполненными на342.
Reviewer принял actual postflight main по квитанции/скриптам; самостоятельного VM rehash reviewer не было.

## Незакрытые границы и cleanup

342 закрывает default-CI coverage gap для forced growth/shrink/SSO; production wipe acceptance остаётся341.
Physical x64/AEC/60min SC-003, full-pipeline wipe cost, installed/hardware/release acceptance OPEN.
ALL config/request/API/hash/ranges/localtracks/result adoption/scheduler/T116/#7444/global admission OPEN.
Review gate342 завершён; inventory/cleanup main — отдельное действие, здесь ни5Mac builds, ни TEMP341 не удалялись.
Допустимость cleanup требует exact owned completed targets/idle/сохранения evidence; native core-build/remotes вне scope.
Reviewer создал только этот append-only zero-checkbox report; source/norm/tasks/старые reports/markers/GitHub/commits не менял.
