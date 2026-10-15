# Round267 — SOURCE: точные поля существующего queue codec

Дата: 2026-10-06. Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`;
dirty preserved. Lane: **high-risk-product**, существующая T116 / #7444.

## Решение

**SCOPED SOURCE GO только исправлению извлечения полей существующего logical
v3/read-v2 ledger codec.** CRITICAL=0, HIGH=0, MEDIUM=0, LOW=0 новых
неустранённых замечаний в проверенной области; blocking clarification=0.
Это не protected logical adoption, выполнение T116 или готовность приложения.
Known legacy AAC RED257/B1 не исправлен и не переименован в GREEN.

Принятый REQUIREMENTS267 gate лично прочитан полностью; его SHA-256
`05a7d90499ba7cb32e5ab300985ea816300dc9181576b9c603d9cd986399102a`
не изменён. По сравнению с frozen172 Round266k изменились ровно два input:
`RecApp/Upload/DesktopUploadQueueService.cpp` и существующий
`Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp`; removed inputs=0.
Header, общий JsonReader, JsonString, schemas и targets неизменны.

## Личное чтение и проверка исходного потока

Использованы лично полностью прочитанные `code-reviewer` и `ponytail-review`.
Применимая AGENTS/Spec Kit/constitution/guidance и активные нормативные
артефакты прочитаны в REQUIREMENTS267; их область не расширяется этим отчётом.
Лично прочитаны конечные helpers, все их вызовы для item/operation/purge ACK,
`load`/`decodeLedger`, predicates/serializer, JsonReader map/array wrappers,
полный JsonString и V2Tests, включая entry point. Tests/VM/EXE/GitHub/hooks
reviewer не исполнял; сделаны только чтение, разбор экспортов и сверка SHA.

| Проверенный участок | SOURCE вывод |
| --- | --- |
| QueueService.cpp:52–88 | Helpers получают существующий per-object `Fields`; ищут exact root key, не textual marker внутри nested values. Purge ACK также имеет свой map перед извлечением, CPP:382–386. Все три группы потребителей используют только этот путь. |
| CPP:55–64; JsonString.h | Raw token bound4MiB проверяется до reserve; общий decoder валидирует quoted token/UTF-8/escape/surrogate, `allowNul=false`. Неуспешное decoding не выдаёт частичный output, allocation exceptions не скрываются. |
| CPP:67–87 | `from_chars` проверяет error code и точный конец unsigned token; `accepted_bytes` использует существующий array wrapper и ровно3 таких числа. JSON grammar предварительно проверена map/array reader, поэтому leading-zero или trailing-invalid JSON не обходят integral check. |
| CPP:213–290 | Domain bounds/owner pair остаются; для всех7 optional known fields present+invalid отказывает, missing сохраняет прежние defaults. Nested optional не устанавливает значение. Owner raw ASCII/accountId и отказ escaped key names не расширены. |
| CPP:296–302 | Root document stamp сохраняет18-digit guard и исправленный `npos` отказ Round265. Это прежний отдельный stamp parser, не новый from_chars consumer; allocation failure не ловится как malformed number. |
| CPP:317–356,382–397 | Operation и ACK получают точные собственные поля; required absence, domain failure и duplicate ACK отказывают до adoption. Unknown extensions не восполняют required поля. |
| CPP:119–194 | Fresh temporary candidate, whole decode/root validation, required v2/recovery persist и только затем swaps трёх vectors/stamp сохранены. Malformed false ведёт к quarantine; allocation/I/O exception — failure без переименования source. Старые данные остаются лишь projection, effects блокированы. |
| CPP:1250–1313 | Writer/schema/filename не изменены. Map/array views живут внутри исходного ledger string; наружу сохраняются owned decoded значения, не borrowed views. |

Нормативная связь остаётся принятой: FR-013/data-model §7 — точная identity и
accepted ranges; FR-012/013/security CHK013 — fail-closed candidate publication;
FR-022/Constitution IV — точные operation/ACK без новой deletion authority;
custody §§3,5,8.1 — прежние пределы и отдельная protected ownership dependency;
plan:1501–1597/tasks:568–570/quickstart §12 — необходимый prerequisite T116.
Scoped analyze не обнаружил новой схемы, orphan task или блокирующего выбора.

Пределы прежнего parser сохранены: отдельный object/array2MiB, depth32,
array1024; cap4MiB ledger не расширяет их. Fixed root tail grammar остаётся.
Unknown item/operation/ACK extensions допускаются как раньше; отчёт не
утверждает универсальную strict UTF-8 проверку пропущенных unknown strings.
Не утверждается roundtrip любого Unicode/control path: serializer unchanged,
положительный roundtrip доказан лишь на допустимых значениях конечного теста.

## Конечные тесты и классификация отказов

V2Tests:230–245 проверяет retained projection/stamp/owner/operation/ACK,
quarantine и отсутствие допустимых effects. Actual load cases:252–369
покрывают nested conflicting и nested-only required поля всех трёх групп;
все7 optional invalid/omission; malformed escapes/UTF-8/surrogates/NUL и
decoded forbidden identity/path; valid escaped ASCII/path/origin, whitespace
tokens, UInt64 max/overflow и exact3 tuple; duplicate ACK. Assertions включены
и при Release (`NDEBUG` снят); `main`:553 вызывает этот тест.

Numeric rejection:395–411 не выдаётся за OOM: huge numeric status/tuple
отказывает как content, allocation hook остаётся неиспользованным, source
quarantined. Genuine reserve failure:412–422 на raw safe_reason1024 использует
прежний test-only operator-new hook, подтверждает его срабатывание,
retained projection/source без rename и успешный retry после fault.
Нет production seam. Предыдущие v2/recovery, malformed tail/stamp/root,
repeated/omitted ACK, missing-known/virgin, writer false/throw и cap случаи
сохранены. OS short-read/growth race не был детерминированно воспроизведён;
его guards — только SOURCE доказательство, не новый runtime PASS.

## Лично прочитанные конечные экспорты

External read-only root: `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
JSON прочитан с удалением UTF-8 BOM только в памяти; SHA относится к исходным
байтам, экспорты не переписаны. Лично разобраны все source maps и receipt maps:
172 Release,172 Debug,179 SDK — каждый совпал с canonical, mismatches=0.
Raw logs прочитаны; конфигурации установлены по actual commands/EXE paths,
не по надписи итогового runner flag.

| Выполнение main / прочитанный export | Подтверждённый предел |
| --- | --- |
| Portable RED raw | Old codec: actual load nested-id assertion257 failed,0.45s; не compile failure. Build0/test8 и old source/test SHA сообщены main; отдельная frozen RED map здесь не выдана за лично проверенную. |
| Release267a | Receipt terminal/passed,configure0/build0/test0; raw6/6 PASS, actual Release paths. Main CTest total15.40s. |
| Debug267b | Receipt terminal/passed,configure0/build0/test0; raw6/6 PASS, actual Debug paths. Main total17.99s. Script имеет --config Debug/-C Debug и Debug EXE hashes; случайная финальная надпись RELEASE не меняет конфигурацию. |
| Portable267 | Raw46/46 Test Passed, V2 PASS; main total21.94s. Это portable applicability, не Windows DPAPI/device/full-app доказательство. |
| SDK267c | Receipt terminal/passed,restore0/build0,179 exact inputs; build-only. App EXE SHA ниже, без launch/install/package. |
| Readback267d | Main сообщил фактический exit0/session89726/chunk8887cf: обе172 input maps и12 focused EXE +SDK179/EXE MATCH. Reviewer лично прочитал весь readback script и экспортированные maps/receipts; Windows readback выполнен main, не reviewer. Standalone stdout export не заявлен. |

Release/Debug CTest выполнялись последовательно. SDK начат при завершении
последнего Debug теста в отдельном build/source path; утверждения о полной
последовательности всех VM build commands нет. Preparatory PowerShell parser
failure был до dispatch тестов и не является RED. Новый ALL50 в267 не запускался;
исторический265k49/50, only known NativeHashFailureTests AAC counterexample,
остаётся NOT GREEN. Не сделано installed/UI/hardware/audio/account/network
или full shared-memory acceptance.

## SHA-256 anchors

| Артефакт | SHA-256 |
| --- | --- |
| QueueService.cpp | `bdc76ef8cf30d83c53a75f83e844386285f2bad6dc6beb93bf2f77f276a66613` |
| QueueService.h unchanged | `b3de437363e7e85adb19c649221408dd6f6ff0081932c51e69a46c634399fc6f` |
| V2Tests.cpp | `1a81865e5d4990cfec3bb0302c56181a020e4d91a4d70ee2cd6e6290f7f72dd0` |
| source-queue-fields-round267a-release.json =267b-debug.json | `269083951a818a545824b068b11a0cec9c4449f4141a761c0fb7e354b2588cd1` |
| source-sdk-round267c.json | `0b0547abdd35ba9663c3670b849d23fa036a90840a27c1a2b46767232bd5cf52` |
| graf-f200-queue-fields-round267a-release.json | `d075c2cfc0c5710619bb6d3e93badfac985241c6e7812dcceb9b6769bfc09b47` |
| graf-f200-queue-fields-round267b-debug.json | `c9991549185238e57dc70e30488806a7b924740fe2f5ce44d84cb4bcf16a4b0c` |
| graf-f200-sdk-live-round267c.json | `3ef608bad67b54e1999bb93b449bba7a8d118f5084be3aea759c2011f6ccc80c` |
| RED267 raw | `296d6f3be853625ab478cb6f013f68e7bccb45365614fcd855a3f1fe12fd4f2a` |
| Release267a raw | `01d20918d4904d2021869f147e5562627426619609f6d232373ec9b9f8f8c2d5` |
| Debug267b raw | `616446bd6588de5ed7c6f775d53c72c8a1e32d54c7992771961515e384b6b95a` |
| Portable267 raw | `18668be05d45f3c6185da811290bd6ffbbfd14afdd66bfa249fd800f1c0500cf` |
| read-queue-fields-round267d.ps1 | `e38716596c8620de1fe27f27be0735352c5d8ef08bc2a13b08e0267599713e80` |
| SDK app EXE (receipt/main native readback) | `0f5966ae03f199da6180b49c0dcd3061e09bfbc1ef878f91d22c66e0074acda5` |
| tasks.md unchanged | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |

## Ponytail, инвентарь и оставшиеся границы

`ponytail-review`: **Lean already. Ship.** Без безопасных cuts: исправлена
первопричина через существующие map/array/string traversal и стандартный
integral parser; нет новых классов/схем/public API/targets/dependencies.
Это scoped complexity verdict, не разрешение merge/release.

До записи131 `.md`:10 current normative **154 checked/0 open**;
отдельно121 historical/context reports **256 historical checked/10 open**.
Исторические unchecked не превращены в новые нормативные checklist задачи.
Inventory131 SHA (sorted basename + space + SHA + LF):
`f94ca3e7cdc7f36da29d2311fe31a10be117747609df18c2fbeb0414c7445e93`.
После записи132; все прежние131 hashes сверены с до-review inventory без
расхождений, added только этот SOURCE report. Маркеры и tasks120/93/27 не
изменены. Каждая из6 before/after implement/analyze/checklist стадий имеет
1registered git.commit disabled; enabled0/dispatch0. Hooks не запускались.

**GO лишь двум конечным input-файлам исправления legacy field extraction.**
Shared64MiB scratch/results ownership, protected logical candidate, matching
intent/queue/account/epoch, typed mutation/admission/startup, полный
producer/consumer и T117 migration остаются следующими зависимостями T116.
T116–T120, H250, B1/AAC и полная Windows/macOS функциональная/installed/release
приёмка не закрываются этим SOURCE решением.
