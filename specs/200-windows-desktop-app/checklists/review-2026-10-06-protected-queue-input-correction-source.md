# Round266 — окончательное SOURCE после исправления теста конкуренции

Дата: 2026-10-06. Canonical
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.
Lane high-risk-product, существующий T116/#7444.

## Решение

**SCOPED SOURCE GO: C0/H0/M0/L0 открытых замечаний этой области.**
SRC266-1 закрыт на текущем исправленном native тесте и свежих k/l результатах.
Допуск относится к private retained `ProtectedCustodyQueueInput`, readonly
discovery prerequisite и существующему FilesTests, НЕ к logical queue authority,
account/epoch, admission/effects, migration, startup/adoption или всему приложению.
Нет основания для новой волны изменений/тестов в этом компоненте.

Исторический `review-2026-10-06-protected-queue-input-source.md` сохранён
побайтно с SHA
`77e299585fcab918d11e2a0367b51db48360417a9d5d6335665a65952b1e981f`.
Его NO-GO отражает реальный прежний тест; этот новый отчёт фиксирует исправление,
не переписывает историю. REQUIREMENTS266 gate также неизменен:
`bdd99d7bcf602f463b2521f13a41ac9fe83719d772efb6067244aab136736c78`.

## Независимая проверка и SRC266-1

Reviewer лично прочитал `code-reviewer`/`ponytail-review`, обязательные instructions/
guidance и REQUIREMENTS gate при текущей SOURCE работе; переиспользовал уже
прочитанные active normative основания T116. Лично прочитаны новый production
flow, shared Files/Codec/Memory ownership и native test matrix; повторно
проверены окончательные competing-thread test и allocation/transfer paths.
Reviewer не выполнял VM/native/portable tests, app/profile/mic/GitHub/hooks/
commit и не изменял production/tests/tasks. Единственная новая запись здесь —
этот correction report.

Прежний `afterRead` вызывал std::mutex::try_lock из уже владеющего потока.
Это нарушение предусловия, а не допустимое доказательство busy. Старые f/g
PASS не используются для закрытия этой причины. Новый FilesTests:1590–1600
запускает nested read в отдельном `std::thread`, внешний поток держит lock
до `join`; nested получает conflict/ERROR_BUSY до Files/IO. `reads` проверяется
после join, `busy` опубликован синхронизацией join. Main thread не продолжает
native IO во время join; competing read не достигает глобальных IO counters.
После освобождения внешний read и последующий retry успешно проходят.
Same-thread рекурсивного вызова больше нет.

Production read не содержит callback/reentrant flow. Область — нерекурсивная
worker operation и отказ конкурирующему worker, не обещанная same-thread
reentry capability. Поэтому достаточно исправления теста; std::mutex корректен
для этого использования. Ранее предложенный atomic_flag был вариантом для
более сильной reentry гарантии, НЕ обязательной новой production архитектурой.
Recursive-mutex/unblock/нового registry/API не требуется и не добавлено.

## Подтверждённые свойства исходников

| Область | Основание решения |
| --- | --- |
| Genuine input | Private ctor, retained discover-created BootstrapPair; null inputs и known-context parent без fixed queueLease отвергаются. Независимые native fixed IDs, не caller JSON/path. |
| Readonly correction | Files.cpp:298 после прежних успешных identity locks выставляет только writable=false. Native object/store/ancestor access/share/ACL/confinement не ослаблены. Удалён redundant queue blockWrites; sticky failed никогда не сбрасывается. |
| BOTH и размеры | Existing readValidatedMetadataPair проверяет обе physical closures. ОБЕ positive<=4MiB lengths/entry counts/DATA-only проверяются до целых owned buffers. Per-block<=256KiB; checked cap исключает опасные casts/arithmetic. Missing/bad peer/empty/ZERO не становятся empty/default ledger. |
| Charged ownership | Payloads/indices/result/control используют existing CustodyAllocator shared64MiB; parent и extra pin удерживаются результатом. Две copies до8MiB не считаются бесплатным cache/native-memory proof. No public Files/writer. |
| Construction failures | Metadata.cpp:613–618 завершает потенциально throwing Debug indices/payload transfers до pin/parent transfer. Constructor failure освобождает raw allocation и построенные members; control-block failure shared_ptr вызывает deleter. CustodyBytes wipe сохраняется. |
| Lifetime | В read локальный held сохраняет родителя при каждом throw/return; scratch/result освобождаются под job, lock освобождается до held, held до job. В result members payloads/indices -> parent -> pin. Native operation не переживает admitted job. |
| Отмена | Nonnull token, pre-IO, before/after bounded compound helper, каждого consumer readBlock/openBlock и final publication checkpoint. Нет fake inner interrupt/hard latency/принудительного release активного OS вызова. |
| Typed failures | Native DPAPI failure остаётся protectionFailed/native code, не semantic invalidContent. Busy/job/pin refusals не дают IO/effects. Sticky pair fault требует fresh owner, не reset. |
| Границы | Raw bytes и const views, valid only with owner. Не parser/candidate/current account/intent/epoch/ACK/effect authority. Нет schema/parser/dependency/target/app/server/Mac change в этом slice. |

Allocation/control transfer и final-cancel ordering подтверждены SOURCE и
узнаваемым существующим allocator/shared_ptr pattern. **Отдельная runtime
инъекция raw object allocation, control allocation и late-publication cancel
не выполнялась и не объявляется PASS.** Partial last-read pressure проверяет
отказ внутри native read/decode, а не каждую из этих точек. Debug существующие
proxy/move-budget проверки проходят, но это не runtime proof каждого нового
QueueInput constructor transfer. Этот честно ограниченный SOURCE proof
достаточен для данного private input prerequisite; отдельного C/H дефекта нет.

## Лично прочитанные финальные доказательства

Внешний stand `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
WinPS BOM удалялся только из in-memory JSON view; exports не переписывались.
Карты лично parsed/rehashed относительно canonical:172/179, mismatch0.
Receipt source_hashes совпадают с нужными maps; EXE hashes прочитаны из receipt,
не выдаются за reviewer-executed NTFS/EXE проверку.

| Файл | SHA-256 / результат |
| --- | --- |
| source-protected-queue-input-round266k-release.json | `9e81068eaf9494be43bf966cff09cb1acb197b74402eb938e52eb60b6ecd9b79`;172 inputs, canonical mismatch0. |
| graf-f200-protected-queue-input-round266k-release.json | `a7041b8069679d4edd8649bc334673cbf017536de6a0fa28b63ae79a1e4c8a12`; terminal configure/build/test0,4/4. |
| graf-f200-protected-queue-input-round266k-release-test.log | `3f4dc42836be0190535031c5f94fbd5e16e1d8dc70b52508d99b04cb2725f9a0`; четыре actual Release commands/PASS, Files26.20s. Total28.18s reported main; raw LastTest log не содержит aggregate total. |
| graf-f200-protected-queue-input-round266l-debug.json | `b7492710988ee3bac6e497bd23c9d6a0c27be86a5b1b0b389e4729af4376d0fc`; terminal configure/build/test0, source172 совпадает с k. |
| graf-f200-protected-queue-input-round266l-debug-test.log | `e6ca99c94ef07b61b8bebb4608e118be9cc3c2381400d97e50678301bb0a980e`; четыре actual Debug commands/PASS, Files35.80s. Total38.76s reported main, не inferred из stdout label. |
| graf-f200-protected-queue-input-round266p2-portable.json | `8c5ebc7f49ab2d7c180864db632116fd47e5216245d356cc73dfc4115684d9d9`; build/test0,46/46,8.21s, source172 совпадает с k; applicability only. |
| graf-f200-protected-queue-input-round266p2-portable-test.log | `8cde3ba13032962a52288a2f46985b62c6e3fc97797025361bad77b98b5afbaa`;46 commands/46 Test Passed/0 Failed лично parsed; Windows/DPAPI QueueInput branch не выполняется. |
| source-sdk-round266m.json | `3c2d317dd2fa8715b47a59cc56b99ae076cb670a7e4a33fc34e4f6b4106926c7`;179 inputs, canonical mismatch0. |
| graf-f200-sdk-live-round266m.json | `18ea9a2e86cf81a9a29051b18843985dd2f6a774bdf85d8b61a097f2d5017660`; terminal restore/build0, full-sdk-app-build-only;source179 совпадает. |
| read-protected-queue-input-round266n.ps1 | `80682cff9f288301184ad248a94f605a1f917e9b537709148d9c5d501d1f34bd`; лично FULL read, корректные k Release/l Debug/m SDK sources+EXE paths и fail-closed comparisons. |

SDK EXE receipt SHA:
`82ac2b803b568efa6895fb5e231199c12f3e6c66d68ae2649f9bf90c7e4a2582`.
Actual readback n executed **main**, session19033/chunkc3505c, terminal0:
Release266k и Debug266l MIRROR_NTFS_SOURCE_AND_EXE_MATCH;
SDK179_MIRROR_NTFS_SOURCE_AND_EXE_MATCH. Это переданное main доказательство
реального выполнения, НЕ собственное VM execution reviewer и не выдуманный
отдельный stdout export. Оно согласуется с лично прочитанным n script и
canonical/receipt maps. Все owned main executions terminal по его сообщению.

Current final inputs:

| Input | SHA-256 |
| --- | --- |
| Metadata.h | `524a040b07a3264369406d7bdbcd9e9bcb90417b471f4f3455ced9109f02b615` |
| Metadata.cpp | `6b9566e55edb24e6880d971777cb0d2b852e04cafb28831530395c161dcefba1` |
| Files.cpp | `484e81430bc57e2c15e130179d5a7a740f0a9b821bf6b89801dc3df7442a824c` |
| FilesTests.cpp | `dfccb4b9f27cdc78435b69c6f7bf58ad4316dd0839c6ba233df58cc40ca9f7f1` |

Vs f172 изменён ONLY FilesTests thread correction; три production hashes
не изменены. Vs previous265g172 slice по-прежнему имеет четыре inputs.
Genuine RED266r build0/test8/writerFailed9/input.ok assertion сохранён;
b/c fixture failures и f/g/h до test correction не выданы за финальный proof.
No repeated full native50 текущего кандидата claimed; последний известный
full265k49/50 legacy AAC false acceptance остаётся NOT GREEN/OPEN.

## Ponytail и сохранность

Проверка сложности не нашла безопасных cuts. Existing Files/codec/allocator
переиспользованы, retained private result необходим для two buffers+parent
lifetime. Изменение ТОЛЬКО теста — минимальная коррекция SRC266-1 без новой
production abstraction. Итог complexity pass (не release approval):
**Lean already. Ship.**

До записи129 .md files:10 normative154 checked/0 open, отдельно119
historical/context; historical10 unchecked не новые normative obligations.
Tasks120/93checked/27open, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
В before/after implement/analyze/checklist registry по одному disabled git.commit,
enabled0/dispatch0 reviewer. Fresh issue7444 и7540 OPEN/canon labels переданы
main; reviewer не выполнял live GitHub query/mutation.

После записи лично сверены129 prior hashes: changed0, только один new report130;
normative154/0 и hashes исторического SOURCE/REQ сохранены. git diff --check PASS.
Следующий обязательный T116 шаг — exact bounded logical queue decode в shared
allocation domain, owner/context/currentness/intent и typed adoption/mutation,
затем actual producer/consumer/startup wiring. Он не заменяется two raw buffers.
T116/T117/T118/T119/T120, H250, B1/legacyAAC, installed/hardware/whole Windows
acceptance остаются OPEN; component GO не закрывает task/issue/goal.
