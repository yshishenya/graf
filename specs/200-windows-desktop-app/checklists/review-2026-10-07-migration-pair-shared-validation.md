# Round273 — дополнительная валидация общих потребителей, NOT GREEN

## Решение и область

**Доказательства дополнительных прогонов сверены; оба набора NOT GREEN.**
Release и Debug: build0, CTest exit8, 5/6 PASS и 1/6 FAIL. Единственный отказ
в каждом — прежний AAC-контрпример `NativeHashFailureTests`, assertion395.
Packed Format/Codec/Owner/Tree и NativeCustodyProtectionFailure прошли в обеих
конфигурациях. Это отдельное дополнение к доказательствам, не новый SOURCE GO,
не утверждение ALL50 GREEN и не приёмка приложения.

Основной `review-2026-10-07-migration-pair-source.md` сохранён побайтно, SHA
`efedd9ef11cbc5fd900bf4d9cf3d217295dd05233335a781f12fdaac950d7b90`.
Его узкий допуск direct-only MigrationPair не расширен до legacy inspector,
startup admission, recovery/GC или полномочий приложения. Дополнительные
проверки нужны потому, что согласованные Files изменения используются также
PackedOwner/Tree. Новый нормативный gate здесь не создаётся.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty сохранён.
Stand: `/Users/yshishenya/Documents/graf-f200-pair-accepted273.nSEy3f`.
Тот же exact map204 `source-accepted273.json`, SHA
`d87e2fdc5aeeaf461557668391e9fb42283e2c3ca375838dddefb85975d612e8`.
Все 204 canonical/frozen файла лично rehashed: mismatches0; обе дополнительные
квитанции содержат exact тот же map. Production/test inputs не менялись.

## Лично прочитанные доказательства

Reviewer прочитал оба полных raw журнала, разобрал JSON квитанций/readback,
сопоставил все12 EXE SHA/PE entries и прочитал скрипты запуска/readback.
Применён `code-reviewer` для проверки принадлежности и границ доказательств;
новый production diff не рассматривается. Reviewer не исполнял VM/CTest/CUA,
не нажимал Abort и не запускал приложение. Реальные guest действия и чтение
NTFS/EXE — main; доступные экспорты проверены независимо на Mac.
UTF8 BOM снят только в памяти при JSON.parse, исходные экспорты не переписаны.

| Тест | Release | Debug |
| --- | --- | --- |
| ProtectedPackedCustodyFormatTests | PASS0.04s | PASS0.07s |
| ProtectedPackedCustodyCodecTests | PASS0.32s | PASS0.65s |
| ProtectedPackedCustodyOwnerTests | PASS148.42s | PASS235.52s |
| ProtectedPackedCustodyTreeTests | PASS21.07s | PASS36.72s |
| NativeHashFailureTests | FAIL2.22s, assertion395 | FAIL300.05s, assertion395; CTest timeout по main terminal |
| NativeCustodyProtectionFailureTests | PASS0.06s | PASS0.24s |

Release main execution13970: terminal runner exit1, build0/test8,
5/6 PASS, total172.14s. Debug main execution91001: terminal runner exit1,
build0/test8, 5/6 PASS, total573.27s. Raw каждого содержит ровно5 `Test Passed.`
и1 `Test Failed.`, без других отказов в этих выбранных шести тестах.
Реальные commands указывают соответственно core-build/Release и /Debug;
configuration/architecture/terminal/status квитанций им соответствуют.

В обоих raw exact строка:

`AAC_MDAT_COUNTEREXAMPLE original_frames=48128 corrupt_decode_complete=1 corrupt_frames=0 explicit_root_normal=1 explicit_root_playback=1 default_root_normal=1 invalid_package=0 synthetic_sends=1`

Лично сопоставлена с текущим NativeHashFailureTests.cpp:383–395: результаты
explicit/default inspector и injected upload вычислены и напечатаны ДО первой
malformed assertion. Повреждённый mdat имеет пересчитанный manifest hash;
native decode достигает EOF с0 frames, старый inspector всё ещё признаёт
normal/playback, injected transport вызывается1 раз. Это НЕ реальная сеть.
Следующие assertions после395 не выдаются за выполненные. Причина semantic
отказа совпадает с сохранённым RED257/B1, а не доказана как новая Files регрессия.

### Отличие завершения Debug от Release

Release `0xc0000409` — сообщённый main результат native failure; экспорт
LastTest.log отдельно подтверждает assertion395/FAIL2.22s, но не содержит
сам числовой native exit code. Нельзя переносить его на Debug.

Debug raw подтверждает ту же semantic строку/assertion и длительность300.05s.
По main фактическое завершение CTest — TIMEOUT. Main через CUA наблюдал CRT
`abort() has been called` для exact Debug NativeHashFailureTests, нажал Abort
один раз (не Ignore/Retry), окно исчезло, но runner остался жив до CTest timeout.
Это наблюдение/action main, не самостоятельная screenshot-проверка reviewer.
Естественный abort/Debug `0xc0000409` НЕ заявлены. Assert options, тесты и
timeout300 не ослаблялись. Parallels update prompt не нажат; наблюдавшийся
VMHelper timeout-10005 сохранён как отдельный факт main, не причина AAC defect.

Packed cadence raw явно помечен `synthetic_only=1`, `paced=0`, target2MiB,
`storage_only_no_dispatcher_or_encoder`. Эти timings не подтверждают SC-003,
реальную60-минутную запись, hardware/performance acceptance или полную pipeline.

## Readback и точная принадлежность

Main execution94885 terminal0 — **успешная проверка принадлежности RED**, не
успешное выполнение тестов. `readback-shared-red273.ps1` намеренно требует
terminaltrue/build0/test8 обоих receipts; проверяет204 native/frozen hashes,
native/export receipts,12 actual EXE hashes и PE0x8664, отсутствие owned jobs.
Статус каждой конфигурации в export — `known_legacy_aac_red_not_green`.
Все12 exported executable entries лично сопоставлены с receipts: mismatches0.
Debug current LastTest.log также сравнивается скриптом с frozen Debug raw;
Release raw — сохранённый отдельный экспорт, не текущий перезаписанный LastTest.

Первый `validate-shared273.ps1` останавливается после failed Release; Debug
действительно запущен отдельным fresh `validate-shared-debug273.ps1`, который
проверяет тот же source и известный Release RED до исполнения всех тех же6
targets. NativeHashFailure не исключён. Source/tests/assertions не менялись.
Проверки идут serial -j1; runner exit1/test8 не переименованы в PASS.

| Неизменяемый файл в stand | SHA-256 |
| --- | --- |
| shared-native273-release.json | `c3056c9a907a00dca714df918cd21a33a9d83474a273c6429c730d6f4d85f9f4` |
| shared-native273-release-test.log | `5a53aac509e857685db2374d2b79c53b862f4bd31151068e5282de9d815ebe75` |
| shared-native273-debug.json | `0489192a92fbded30574d459ff988370c32e8be610dbf5ef6d92b462fe26ceb2` |
| shared-native273-debug-test.log | `13e1bf059a1aa87ec2f408f7ab4b537d59e881795c9529c48e24c92d87acab52` |
| readback-shared-red273.json | `4db427f934012c63a36a41b2b4ea410d9ed09da49a19ab7f10e25b83559b342b` |
| readback-shared-red273.ps1 | `63052313788c7c3773d109faa0fd2319eb9e93267a991c2ffd18033c390b6679` |
| validate-shared273.ps1 | `47b1a2a6558467474f5975b6d2bacb7f51aadb9421ff91f04b0c181680749f08` |
| validate-shared-debug273.ps1 | `412ed934953884b385216eb6964efd464c608253384a5d609989208769e45654` |

## Сохранение и нерешённые границы

Перед записью: все прежние154 отчёта byte-identical snapshot после SOURCE273.
SHA sorted basename<TAB>SHA256<LF> inventory:
`045b35eb65b2d9ad98214ab11e857bbf09deae1e61acb972d9309cd9ace76e95`.
10 текущих нормативных checklist154 checked/0 open; остальные144 документа —
исторические/review материалы, не новые нормативные checklist.
Tasks120/93/27 и SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`
не изменены. Этот отдельный отчёт имеет0 checkbox, старые markers не изменены.

Успех пяти shared consumers не устраняет AAC counterexample и не закрывает
legacy B1, H250, T116/T117/T118/T119/T120. Текущие6+дополнительные6 — выбранные
наборы на одном source, не fresh ALL50 и не установленное приложение.
Standalone tombstone/conflicts, matching durable bootstrap/intent/fixed-ID
startup admission до legacyload/sweep/recover остаются будущей областью;
следующий REQUIREMENTS gate этим дополнением не создан и не одобрен.
Нет UI/device/audio/private profile/App launch/install/network/GC/release proof.

Единственная reviewer-owned запись — этот новый0-checkbox supplemental report;
после записи повторно проверено сохранение всех154 прежних отчётов и source/tasks.

## Дополнение до фиксации отчёта: primary readback после shared прогонов

Main execution38612 terminal0 повторно проверил primary6/6 receipts и12
фактических primary EXE после дополнительных сборок/тестов, source204
native/frozen и отсутствие активных основных/дополнительных owned jobs.
Лично прочитаны `readback-primary-after-shared273.ps1` и отдельный export
`readback-primary-after-shared273.json`; все12 entries exact сопоставлены
с исходными accepted-native273-release/debug receipts: mismatches0, PE0x8664.
SHA нового readback export:
`5e9af47d9ba1ebd75398a36f78173e0ac74099a18e906cab032d4b4ea20f4800`.
Он совпадает с прежним primary readback SHA, поскольку проверенные значения
побайтно те же; свежесть исполнения основана на новом сообщённом main execution
38612 и отдельном скрипте/экспорте, не выводится из совпадения SHA само по себе.
Основной SOURCE273 не изменён; никаких primary tests повторно за этим фактом
не заявлено. Supplemental Debug по-прежнему CTest timeout300.05s после
AAC/assertion, не доказанное естественное native завершение `0xc0000409`.
