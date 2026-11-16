# T116 — независимая SOURCE/runtime приёмка wipe341

SCOPED SOURCE/RUNTIME GO: минимальный wipe-срез341 принят на фактических generated-data проверках.
Текущих блокирующих findings P0/P1/P2:0; high-risk-product lane и все широкие gates сохранены.
Это НЕ закрытие T116/ALL, НЕ готовность Windows, НЕ physical SC-003/installed/release acceptance.
Использованы code-reviewer и ponytail-review; reviewer не запускал VM/jobs/build/tests/postflight.

## Идентичность и неизменность

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch `codex/200-windows-followup`.
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` + dirty bytes; injected0309 не использован.
Frozen `/Users/yshishenya/Documents/graf-f200-wipe341.WiXPp2`, source.json:
`9aa96c5c9a1acfba681d06d5a6ea7543c95d90677ca1a8a93984653134ec88e6`.
Reviewer повторно rehashed все209 frozen и canonical файлов: exact209, расхождений0.
SOURCE report `review-2026-10-10-custody-wipe-source.md` сохранён неизменным:
`6a257d9096db6d659671dd1e7862318b10c187fa037fc252bb9fdb254d03869f`.
Diff339→341 только2 production headers + existing CodecTests; R1–R4 source audit не расширен.
Normative9 повторно exact; tasks120/93done/27open; до отчёта183md/29marked/420checked/0unchecked.

## Native — полное terminal evidence

native.json `d43a76b6783bb937f0dca7292c42e708eaf3941098fee03a6cd522653085fa51`.
terminal/native_completed=true, stage=wipe_green168_verified, configure/build0.
validate.ps1 `461acbfa85a2e31d2a6adc7ba4fbd285ab3c493ba4d356987fd050ec5c82f016` exact receipt binding.
Прочитаны harness/run и все168 logs: каждый hash exact receipt, combined bytes exact stdout+stderr.
Все168 completed/exit0, unique configuration/name; matrix arguments exact mode/type/cut; пропусков/дублей0.
Configure и оба build logs прочитаны с UTF-16 decoding; C4244/C2220/error diagnostics отсутствуют.

| Полоса | Retiring cases | Immediate cases | Budget | Dependent targets | Итого |
| --- | --- | --- | --- | --- | --- |
| Native Debug | 39 | 39 | 1 | 5 | 84 |
| Native Release | 39 | 39 | 1 | 5 | 84 |

Все156 matrix cases: поодному WIPE_ORACLE zero=1 и WIPE_CASE=pass; zero0/assert failures0.
В каждом tail-наборе30 TAIL_ORACLE zero=1; growth/self/destroy не уменьшают size и не требуют tail marker.
Heap observed spans: bytes64, char80, Windows wide144 bytes; SSO char3/wide6 включая embedded NUL.
Оба budget logs содержат по3 MUTATION_BUDGET=pass: bytes/char/wide, включая destruction baseline assertion.
Full quota проверяет shrinking/alias/copy/literal/init-list/chaining/erase iterator/refusal/invalid position/destructor.
Debug proxy16: реальные default/move allocation failures caught, cleanup/self-move/assignment complete.
Release proxy0: соответствующий proxy-refusal proof честно SKIP; остальные full-quota/assert tests выполняются.
Dependent5: NativeCalendarJoinTransportTests, ProtectedCustodyCodecTests, DesktopDeletionProtocolTests,
DesktopUploadRecoveryTests, NativeCaptureStorageIntegrationTests — каждый Debug/Release exit0.
Recovery elapsed422816ms/276334ms: terminal success, не принят по состоянию CPUbusy или одному запуску.
Integration3000: healthy sync returned1/calls1/retryable0/truth1/finalized1;
pressured sync returned1/calls1/retryable1/truth0/finalized0 в обеих configurations.
Account known_workspace0/1 quota refusal, direct charged response, ACK progress/cancel fences сохранены.
Integration явно пишет protected_result_adoption=pending; это не успешное shipping scheduler adoption.
SHA sorted168 строк filename+space+SHA256+LF: `fdd9c370a086a4bde2de9f063df6f53107527e9ca8f3433b5e7fe7512ef29cb7`.

## Portable и actual native postflight

portable.json `9d42f928ef602ccfea369c9269c4b7fb3b60f5c648d05970eb26bc9874ca3f9d`.
terminal=true, portable47_plus_wipe78_verified, configure/build/test0; source manifest binding exact341.
Portable script прочитан; configure/build/test log hashes exact; CTest47/47 Passed, failures0,34.11s.
LastTest.log дополнительно прочитан:47 Test Passed; Codec default выполняет budget/старые tests, не CLI39.
Все78 CLI logs rehashed: exit0/no signal, WIPE_CASE=pass/retiring zero1; tail30zero1; пропусков/дублей0.
Libc++ wide SSO-move теперь green; native wide2bytes и portable wide4bytes не смешаны.
SHA sorted78 portable case log строк: `4304b5774d7e7f70eee8f40e442ca68f7babfb5ce530d3592793a060414704ff`.
postflight.json `87d8722d601d12aebf41d337205ffabc5b46b7e5dc88e9617a402b34ae1dfc8b`.
terminal=true, source_binary_log_postflight_verified; exact source/native receipt hashes, source_count209.
Actual main postflight подтверждает native/share209,10EXE/5DebugPDB,168log hashes и idle=true.
Reviewer прочитал postflight.ps1/mjs: повторные реальные Get-FileHash, process idle, count и receipt checks.
postflight.ps1 `a0199d68e6047110967a5a34fffb456938c6eb77b292f08d7fe958836b378d4f`.
Это принятый actual postflight main, НЕ самостоятельный VM rehash reviewer; новую VM-команду reviewer не выполнял.
Receipt содержит10 unique stable EXE hashes/5PDB; Codec Debug EXE:
`9291bc45e558345a3f9a26a1f2262ec46795444aa08c8caf0cb8a45fff48dce7`;
Codec Release EXE `4a162879834f8c6998f83f86f242e3c2cf30e32c1e6ebc16abaa640777bc02d0`.

## Объём принятия и дальнейшая граница

RED338/339 → GREEN341 подтверждает retiring full allocation и immediate live-tail wipe, не только destructor masking.
R2 no-allocation принят для проверенных MSVC Debug/Release и portable STL/full quota; не universal C++17 promise.
Base& interception не обещается; concrete actual caller R4 покрыт прежним SOURCE audit и текущими regressions.
Ponytail: existing2headers/oracle, новый framework/target/dependency:0; optional trim−6lines не blocker и не применён.
341 terminal+postflight gate завершён; можно перейти к согласованному test-only342 default39 helper.
Для test-only342 достаточно fresh Codec Debug/Release + portable47 при exact production/CMake/dependency hashes.
341 dependent10 остаются evidence341; не переименовывать их в342 и не повторять без затронутой причины.
Physical x64/AEC/60min SC-003, стоимость wipe полного pipeline, installed UI и hardware acceptance OPEN.
ALL config/request/API/hash/ranges/localtracks/result adoption/scheduler/T116/#7444/global admission/release OPEN.
TEMP inventory/cleanup этим postflight не доказаны; cleanup выполняет только main по собственным проверенным targets.
Reviewer создал только этот zero-checkbox report; source/norm/tasks/markers/исторические reports/GitHub/commits неизменны reviewer.
