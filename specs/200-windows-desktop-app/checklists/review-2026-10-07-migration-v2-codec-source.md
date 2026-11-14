# Round272 — независимая SOURCE-проверка migration.v2 / Birth / общих helpers

Дата: 2026-10-07. Reviewer-owned, 0 checkbox markers. Lane high-risk-product,
существующая T116. Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserve.

## Итог и точная область

**SCOPED SOURCE GO; C0 / H0 / M0 / L0** для принятого B: migration.v2 read/write
в существующем Metadata codec и schema/representation/container comparison Birth,
плюс четыре согласованных узких дополнения: hexDigest count constructor,
его forced-copy return, blockName append/copy и три direct blockName path callers.
Решение принято ПОСЛЕ лично прочитанных terminal Debug/Release exports и readback.
Это component acceptance, НЕ полная T116, MigrationPair, migration authority
или приёмка Windows-приложения. APP compile-only отдельно, не prerequisite
этого core verdict при отсутствии найденного caller compile defect.

Прочитаны полные инструкции code-reviewer и ponytail-review; применены проверки
корректности/безопасности/error boundaries и отдельная проверка переусложнения.
Полностью прочитаны принятый B gate и все четыре narrow gates. Ранее полностью
прочитанный нормативный контекст переиспользован; не повторён аудит исторических
гигантских validation. Fresh hashes/актуальная feature identity и критерии сверены.

## Зафиксированные исходники

Лично сопоставлены все204 entries source-path272.json с canonical И сохранённым
`/Users/yshishenya/Documents/graf-f200-migration-path272.d01Ilk/apps/windows`:
mismatches0 в обоих деревьях. Source map SHA
`c448101a0c45e4a6e9c61bb0d2d9269ab54da096248137dbb820e8f54589ef14`.
Рабочий diff Round272 сравнен с immutable Round271 stand, а не с накопленным
грязным HEAD diff; final helpers/tests сверены по текущим файлам и frozen copies.

| Файл в apps/windows | SHA-256 текущего снимка |
| --- | --- |
| RecApp/Storage/ProtectedCustodyMetadata.h | 28780ac32a1236d4551378621bf627dccbfe313de7ab7f05634a8f6e452c78ba |
| RecApp/Storage/ProtectedCustodyMetadata.cpp | 40375b28dcd0d1ffccdebe6cdb514d83a20d5cc62272a96ec85b45c8938aeabb |
| RecApp/Storage/Sha256.cpp | e7d6e8c5690c7bf5f1bc2f99f2b88a9dc9c284985eceb33d93458faec1da63a3 |
| RecApp/Storage/ProtectedCustodyFiles.cpp | c62a6bcd879a678178ff3b5da311b5434b2d618dc61648d1bb3b7ba769a6384c |
| Tests/GrafWindowsCoreTests/ProtectedCustodyPackageTests.cpp | d2178c77785ea8ee7f44c2d8f0ec6a7356b8f7b6d72c2d7474a6c3ddfb6c46a5 |
| Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | a20226b7e95b2a82676e460044cd85d1aa8968eaca744a3c781be7ea30e561f3 |

## SOURCE: форма, семантика и границы доверия

Metadata.h:23–33 добавляет ровно четыре fixed-storage поля в прежний source.
Metadata.cpp:46–105 сохраняет independently expected own context/gen/tx/subject/
directory, anchor и stage rules. Schema1 запрещает новые non-null поля/packed;
schema2 packed допустим лишь package canonical/media/playback, container present
уже prepared, prepared triple/extent/root null. Copied и далее требуют exact
length/SHA/gen и согласованный stamp. Queue/ledger/manifest/recovery остаются flat.
Shape использует тот же Format::decodeReference: EMPTY length0, NODE_L2 иначе,
payload0, reserved/version/extent/offset bounds и g1 empty exact appendOffset.
Это структурная проверка Ref64B, НЕ full tree/container closure.

Metadata.cpp:157–192,263–282: один прежний closed PackageJson, root12/anchor4/
source7-or11/barrier5/auth6; source masks проверены после окончательной schema,
поэтому sources до schema допустимы. Unknown/missing/decoded duplicate/type/null
не игнорируются. Fixed token300 вмещает128hex; parser не строит heap DOM.
Whole input≤65536 и strict EOF/BOM rejection сохраняются. Числа exact u64,
ASCII identities/hex остаются прежними. Nullable pattern не вводит partial stamp.
Metadata.cpp:437–485 deterministic writer сохраняет v1 bytes/семантику, v2 всегда
emit все11 полей, сортирует sources по kind и pre-reserve использует charged bytes.
Allocation refusal возвращает typed failure; размер/тип не заменяются default.

Birth:394–435 сохраняет exact cipher length/SHA, direct blockVersion/native opener,
expected tuple и g1 prepared shape. Добавлены schema equality и order-independent
representation/reserved-container equality наряду с прежними whole anchor/source
kind/length/SHA/destination IDs. Null prepared birth stamp НЕ сравнивается с sealed
current stamp. Parsed temporary value и charged plaintext освобождаются на отказах;
результат — обычное structural value, не authenticated current pair/owner/effects.
Current struct сам себя не аутентифицирует: это явно оставлено caller requirement.

Sha256.cpp:39–49 меняет лишь empty count construction и forced copy-prvalue return:
успех по-прежнему64 lowercase hex, provider/API/cursor/read error behavior прежние.
Count/copy могут бросить; named-local noexcept move и default Debug proxy root
не обходятся flags/NRVO assumptions. Shared callers portable identity/reminder/
deletion/upload и native stream/file custody/v5/transport сверены; binary protected
hash finish(array) hex formatter не вызывает. Полный Sha256.cpp прочитан.

Files.cpp:78–84 и readBlock:311–334/Birth envelope:336–355/writeBlock:357–384:
ровно принятый append/copy blockName и const name + copy path + lvalue /= в трёх
вызовах. Filename/uint64 decimal/native composition прежние; нет ручного separator.
Limit/version/role/position проверки остаются до IO, native State::read/create
confinement/ACL/reparse/hardlink/share guards не изменены. Reader bad_alloc остаётся
allocationFailed, writer caught allocation failure сохраняет sticky failed=true.
Нет изменения indexName/scanner/inspect/других paths. Временный path/allocations
в /= не объявлены отсутствующими; все фактически наблюдаемые cuts сохранены.

## Тесты: лично прочитанные assertions, не только строки PASS

PackageTests migrationTests покрывает schema1/v2 subjects и5 stages; exact
12/4/7-or11/5/6 keys, decoded duplicates/types/null/unknown, whole cap65536/+1,
tuple/role caps, flat-only kinds, schema1 typed extras, unknown representation,
packed prepared/copied partial triple/stamp combinations, mixed source order,
g1 EMPTY/nonempty NODE_L2, invalid128hex/IDs/u64 и mutations настоящего Ref64B.
Schema2 source/root key permutations включают schema после sources.
Прежняя wire-only version mutation остаётся invalid; typed unknown schema=3.
Reader при полном shared quota реально имеет0 heap allocations; это НЕ skipped
native allocation matrix. Writer actual global-new cuts + quota refusal/retry
проверяют no value/typed error/budget restoration, без отмены Debug proxy charge.

FilesTests migrationHistory:1365–1679 — четыре fixtures schema1/2 × queue/package:
реальная DPAPI birth g1/block v17, current physical indices g3/g4 без g1 index;
каждый slot реально открыт/decoded прежним BOTH validator. Source reorder positive;
valid reprotected foreign schema/anchor/source/representation/container дают
semantic invalidPlaintext с новым правильным cipher SHA, не только hash failure.
Sealed current stamps могут отличаться от null birth — positive assertion есть.
Invalid role/version/size до IO, missing/short/hardlink/reparse/native/hash errors,
no writes/flushes/renames и budget refusal/retry сохранены.

Actual global-new enumeration отдельно для Birth и envelope: каждый counted
ordinal проверяет hit, typed allocationFailed, no value, budget baseline,
fixture lease удерживается и retry0 проходит. Это actual std/Custody allocation
cuts данного пути/fixtures, НЕ все native LocalAlloc/CNG OS allocations или
полный RAM proof приложения. Pure-codec hook не притворяется job/queue admission.
Native job/exclusive lease и cancellation в конце fixture принадлежат вызывающему
составному тесту: Birth API сам не имеет cancellation/owner admission. Не заявлена
проверка точного каждого scanner cancellation point или миграционного контроллера.
Временная диагностическая DbgHelp instrumentation отсутствует в final test hash;
итоговые outputs не превращают исторические failures в PASS.

## Terminal evidence и независимое чтение readback

Внешний stand: `/Users/yshishenya/Documents/graf-f200-migration-path272.d01Ilk`.
Reviewer лично parsed UTF8/BOM квитанции без изменения файлов, прочитал оба полных
native raw logs, проверил mode/configuration/terminal/source map и EXE receipts.
12 EXE entries совпали с readback, все PE machine34404=0x8664. Выполнение native
принадлежит main, НЕ reviewer: main session12384/chunk4bec87 terminal0 и
readback session26889/chunka5317c terminal0.

| Проверка | Результат | Источник |
| --- | --- | --- |
| Native Debug selected6 | build0/test0,6/6 PASS,68.44s по main; Files46.74s raw | path-native272-debug.json / -test.log |
| Native Release selected6 | build0/test0,6/6 PASS,48.17s по main; Files29.62s raw | path-native272-release.json / -test.log |
| Portable |46/46 PASS,27.38s/build0 по main; все46 raw results parsed | portable-path272-test.log |
| Readback |source204/receipt_match=true,12 EXEs/config/hash/PE matched | readback-path272.json + personally read script |

Native targets: Sha256Tests, ProtectedCustodyCodecTests, ProtectedCustodyPackageTests,
ProtectedCustodyFilesTests, DesktopUploadQueueV2Tests, DesktopUploadRecoveryTests.
Debug каждый из4 fixture: Birth20/envelope36 cuts; Release:10/15, retry1.
Schema1 matrix45 accepted/528 rejected; schema2 75/812. Writer Debug3 cuts,
Release1 (также packed writer); bootstrap15/173 preserved. Release proxy-specific
SKIP означает отсутствие этого proxy allocation в данной STL конфигурации,
не пропуск Birth/envelope enumeration: Debug реально проверил proxy path.

| Evidence file | SHA-256 |
| --- | --- |
| path-native272-debug.json |155e9771aa3a432cab86000b724a1a85ce9974c2f5b787b5c90db3d60914bfdc |
| path-native272-debug-test.log |b8cee0342512aaa874eb8f2c794413aa0501665f948318d51de613997dcabad5 |
| path-native272-release.json |900a78b93c1677e2c37092d0f75e01b02c8499959f5b7077191917c92e22d5cb |
| path-native272-release-test.log |d56aa1a763afd91ec00add050c8d8cb2a28614cc0cb1bdca79e5bbb3b585570b |
| portable-path272-test.log |ed0c835d1efd57028844b9646d23a096f063f96035daca102be8d3b3c4b748cc |
| readback-path272.json |08a05b04b91245ebf184afaf31d392172a34b522ea0d336503c6864702fdd3b6 |
| readback-path272.ps1 |5452743c9f11b8fe9b21095a0c14b49ead670a822dc4bf8aad91911266239a97 |

Readback script проверяет native/share source204 и native/export receipt bytes,
terminal config/build/test, correct Debug/Release paths, actual EXE hashes и PE;
отказывается при активных перечисленных тестах/owned build и пишет CreateNew.
Reviewer прочитал script/result, сопоставил все12 entries с квитанциями и обе
карты с canonical/frozen; это не личное выполнение Windows readback reviewer.

## Нормы, сохранение и вывод Ponytail

T116 остаётся CRITICAL owner по tasks:568; migration.v2/Birth нормы packed §6.1
и base §8.1 не изменены. FR-012/013/014/022, SC-005/006 и Constitution VI соблюдены
в этой ограниченной реализации; full storage/admission acceptance не выводится.
Tasks120/93/27 SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Hooks шесть before/after analyze/checklist/implement по1 registered disabled,
0 enabled/0 reviewer dispatched; никаких GitHub/commit actions.

До отчёта142 markdown:10 нормативных154 checked/0 open,132 historical/context.
Нормативные totals лично пересчитаны; historical findings не переименованы в новые
обязанности. Inventory sorted basename TAB SHA256 LF SHA
`20e2cf65e015078d7509740c4c34d47615b649fd66621bb195823675d5f189aa`.
Все прежние142 reports/markers сохраняются byte-identical; добавлен только этот
отчёт с0 checkboxes. Код/tests/spec/plan/tasks/старые reports reviewer не меняет.

Ponytail-review: **Lean already. Ship.** Только в значении формы данного component
diff: существующий closed parser/Format/native IO/formatter,0 dependencies/targets/
DOM/controllers. Нет безопасного сокращения, которое возвращает доказанные
noexcept failures или убирает trust-boundary checks. Это не команда выпуска.

## Остаётся вне GO

Не выполнены MigrationPair, retained matching durable intent, bootstrap/queue/
account/path currentness authority, full root closure/GC/tombstone conflicts,
T117 migration execution, typed writer/adoption/startup consumer и full T116–T120.
Нет приложения, установки, mic/device/private content, UI/installed/parity,
physical Windows x64/60min/audio acceptance, H250 или release/PR/merge действий.
Full native ALL50 на текущем Round272 снимке НЕ заявлен; legacy AAC RED257/B1
не запускался selected6 и не закрыт успешным protected AAC fixture. Прежние
ALL49/50 и все промежуточные build/Debug failures остаются historical, не скрыты.
APP compile-only имеет отдельную квитанцию/приёмку, не installed proof.

Итог: принятый codec.v2/Birth и четыре доказанные helper corrections допускаются
как завершённый узкий SOURCE-компонент. Следующий MigrationPair требует своего
конкретного REQUIREMENTS gate; никакого автоматического закрытия общей цели.
