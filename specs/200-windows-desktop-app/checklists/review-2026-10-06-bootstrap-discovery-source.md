# Round264 — SOURCE: retained fixed bootstrap discovery

Дата: 2026-10-06. Независимый SOURCE review, high-risk-product, T116/#7444.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.

## Финальное решение

**SCOPED SOURCE GO для bounded fixed bootstrap discovery на exact264b
172 inputs и SDK264d179. C0/H0/M0/L0 новых неустранённых замечаний этого
компонента.** Порог: нет unresolved CRITICAL/HIGH или blocking clarification.
Release/Debug/portable/SDK и full regression/readback рассмотрены ниже.
Full native **НЕ GREEN:49/50**, известный legacy AAC RED257/B1 сохранён.
Это не queue/admission/application GO, не закрытие T116 и не release approval.
Наличие retained fixed queue ID не заменяет logical queue/matching intent/
account/currentness/actual caller adoption. SOURCE approval263 не использован
как автоматическое одобрение нового discovery.

Принятый REQUIREMENTS264 gate лично прочитан; сохранён SHA
`3f2a26836c705745f750f1dff722dd8004b2fec61000eec8e5fec015b10f35a1`.
Использованы `code-reviewer` и `ponytail-review`; обе инструкции прочитаны
полностью. Лично прочитаны изменённые Files/Metadata declarations, common
identity/openImpl/readImpl/constructor/destructor, native discovery test block,
TU fault interception, fixture, actual main call и относящиеся прежние проверки.
AGENTS/constitution/current REQUIREMENTS context сохраняют силу; новая схема
или другой risk lane не вводились. Reviewer не запускал VM/tests/native EXE.

## Exact кандидат и границы сравнения

Лично parsed `source-bootstrap-discovery-round264b-release.json`,172 inputs,
SHA `6c5b8db5e76aebc3e83a7476d5fb91768d4b407a477f300c66280ca81c0b2005`.
Все172 SHA сравнивались с canonical bytes: mismatches0. Относительно принятой
263c map изменены ровно пять следующих inputs; остальные167 byte-identical.
JSON exports с BOM parsed после удаления BOM только в памяти; файловый SHA
считался по исходным bytes. Ни exports, ни product parser не переписаны.

| Input | SHA-256 |
| --- | --- |
| Files.h | `9bbb8305400a31dd6a5765da31f37f26bff1bc3548f5df156081e638146dde5f` |
| Files.cpp | `95d40e76dc8404d1703594c3100a88eff22c65077e85f3aba148ad77abae7b36` |
| Metadata.h | `fb15d53480d1281f5ffb1e6eea428c1b8ecca19d67a27d2d4b1b1cef8efc4480` |
| Metadata.cpp | `f7eb2cf8cfb1d9ad524461c5c3501e3984762ce050742a0ef0e8bf93c5d6c2ae` |
| FilesTests.cpp | `c2f0a77e8d669bbba5ee0904ec626b45be573be64ea55f8f7c60e9411b1ad42c` |

Это сравнение карт/actual canonical bytes, не заявление о native NTFS readback
самим reviewer и не проверка всей ранее накопленной dirty разработки от HEAD.

## Корректность, безопасность и lifetime

| Область | Actual source / заключение |
| --- | --- |
| Fixed source | Files.cpp236–241/269–296: private discover допускает лишь bootstrap/queue; fixed root paths, writeExisting, expected=null только внутри discovery. Нет JSON directory/ID lookup, scan/create/regenerate/repair. |
| Один security backend | Files.cpp166–179/243–304: прежние openFile/inspect/ACL/reparse/hardlink/exact16 checks и ancestor locks. open публично вызывает тот же openImpl с discover=false. Нет второго слабого path/backend. |
| Store immutability | Files.cpp168–169/272–273: discover=true передаёт immutable=true для store; GENERIC_READ и FILE_SHARE_READ only. Оба observations остаются actual handles в двух State. Metadata.cpp571–573 сравнивает store IDs до использования independent queue ID. |
| Object exclusion | Fixed object identity использует GENERIC_READ\|GENERIC_WRITE с FILE_SHARE_READ, без записи. Queue blockWrites574 и bootstrap600 до result; private owners не дают Files/HANDLE наружу. |
| BOTH/semantics | Metadata.cpp576–598: прежний physical readValidatedMetadataPair и strict bootstrap codec обоих DATA с собственной generation/own context и actual queue ID. No singleton/invalid-peer rollback. No public factory reopening удержанного bootstrap. |
| Known overload | Metadata.cpp534–545: прежняя public signature сохранена, общий readImpl, discover=false и queueLease=null. Expected context/queue codec rules не заменены discovery. Прежний store-sharing режим known Files.open не расширен скрыто. |
| Cancellation | Metadata.cpp550/555/564/570/584/591/594/599: null/pre-cancel до IO; after bootstrap/queue compound opens, между slot IO/decrypt и перед result. Cancel не обрывает/free текущий native call. Open включает bounded два identity reads; immediate per-ReadFile abort внутри этого compound не заявлен. |
| Job/pin | Metadata.cpp556–559: один job≤4/pin≤32 до discovery; вложенный public factory/job отсутствует. Native job local до actual owners cleanup, retained pin до last result owner. |
| Constructor/exception | Metadata.cpp522–527: throwing indices transfer выполняется до noexcept lease/pin transfers. Placement construction failure освобождает raw charged block; shared_ptr(raw,deleter,allocator) failure вызывает deleter, закрывая оба owners/pin. Последнее — SOURCE reasoning, не специально выполненный control-block fault. |
| Destruction order | Metadata.h private members: pin перед обеими leases; reverse destruction закрывает queue/bootstrap owners прежде pin release. Metadata.cpp529–532 wipe retained semantic values; locals WipeValues581 очищаются на всех exits. |
| Typed failure | Open/IO/identity/codec/native/quota failures возвращаются без partial result, native code сохраняется. Собственные payloads не превращаются в empty/default ledger; missing IDs не восстанавливаются. |
| Scope of proof | Retained queue lease доказывает стабильный reserved ID, НЕ queue indices/ledger/account/root inventory/matching intent/current epoch. Protected/migrating mode не открывает effects. AppMain/caller adoption отсутствует в пяти-input delta. |

Как и в accepted263, путь/State/native allocations не все входят в shared
owned charge; новый result/control block и codec bytes charged прежним
allocator. Не заявляется wipe каждой stack/register копии opaque IDs.
Cleanup освобождает leases, не удаляет и не меняет существующий id.bin.

## Прочитанное покрытие нового test block

FilesTests1512–1657 и actual native main2792: реальная existing DACL/DPAPI
fixture и два actual fixed object directories. Нет fabricated public Pair.

- Protected и migrating queue, equal g1, последующий g2/mode switch; actual
  current store/bootstrap/queue identities сравниваются с fixture. Queue без
  indices положителен только как reservation; tests не заявляют queue authority.
- Owning копия после reset первой ссылки удерживает все leases. Actual write
  и DeleteFile для store/bootstrap/queue id.bin дают ERROR_SHARING_VIOLATION;
  protocol writers отвергаются. Last release позволяет повторный writer/store
  open. Discovery counters: writes/flushes/renames/searches0.
- Read faults ordinal1..10; cancel ordinal1/2 завершает compound bootstrap
  identity open с reads2, ordinal3/4 — queue compound с reads4, далее slot
  отмены. Null/pre-cancel и job4/pin32 до opens; owned pressure после полного
  CustodyBytes ctor; hash/allocation failure + retry и final usedBytes equality.
- Size0/15/17 для всех трёх IDs; missing каждого ID; short read; missing each
  bootstrap peer; hardlink/private DACL violations, queue junction, отсутствующая
  queue directory, changed actual queue ID vs protected JSON: whole rejection.
- Новый TU-local FileFault::identityMismatch меняет returned read3 bytes второго
  store observation, не файл/native sharing. Отказ и reads4 проверяют explicit
  equality guard. Это fault counterexample, не свидетельство реальной гонки
  изменения уже удержанного immutable store.

Некоторые варианты (migrating package, padded64KiB, malformed peer JSON и g3/g4)
покрываются сохранённым known-overload block через тот же readImpl. Нет claim
о новом отдельном discovery PASS каждого такого варианта или о concurrent
race exhaustive proof. Нет отдельного targeted result/control-block allocation
fault. Прочитанный pressure test доказывает отказ общего owned budget/retry.

## Лично прочитанные terminal artifacts

Exports root: `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
RED map не является current: RED264a и candidate264b различаются
в пяти inputs, RED сохранён как историческое TDD evidence.

| Artifact | SHA-256 / результат |
| --- | --- |
| source264a-red172 | `e21b8bb9882825c8442b9e5b98eeb587958bbc41c644aded0682bfab4a651ee2` |
| receipt264a-red | `2dba1816e69c29449913264d2d2a62f8b48e5fc8d6f80f3158b21b9b3f979693`; terminal failed, configure0/build0/test8 |
| raw264a-red | `de620adb75c3d117f49a21b466ad54e217e3bf9d63d9e1b7a8e5d1816bf4e75d`; Files assertion result.ok line1532, 0.10s; другие3 PASS |
| receipt264b-release | `e75e00e12ef23e974812b626dde5b0ec773e8cbf96919b11a723218b9d255770`; terminal passed, configure0/build0/test0, source_count172 |
| raw264b-release | `5105e9dcd68c246f7096935407238352410738d20c11aaf81f1219d360924140`; actual Release commands,4/4 PASS, Files24.68s |
| receipt264c-debug | `803dd506a182981d93348b131dcca1fb5bfe80bdd66f2002b161173717c18a2e`; terminal passed, configure0/build0/test0, exact source_hashes равны candidate172 |
| raw264c-debug | `e740cf25e878f8bf8b7829af10500119fe5da4a45a8f776e3eb1459fb7fed7a6`; actual Debug commands,4/4 PASS, Files33.89s |
| raw264b-portable | `b555e0059427f351152f5daf25a6061611c01904e0a3cce345d8d6d450be5f3f`; actual Mac command paths,46/46 PASS, native discovery branch исключена #ifdef |
| source-sdk264d179 | `82f5807af25d13d6f27c0ad567dd233d64965d3b8896060fc10c41456175147f`; personally parsed, canonical179 mismatches0 |
| receipt-sdk264d | `1924173a9a6ca4c96f2b53fb5ab541fca9d27a627c32912fccf5c213eeb3d7f9`; terminal passed, restore0/build0, source_hashes exact SDK179 map |
| receipt264e-all | `f0345998d80a8d82a4246fa5c4ffb7176ce9cd6053956200910767a125b582e1`; terminal failed, configure0/buildALL0/test8, exact same172 map и focused Release EXE hashes |
| raw264e-all | `77816af74a7b1afeef9daa6e6ca3596992548435eee1135ca540c2e938139591`; actual50 Release commands,49 PASS/1 FAIL |

Release raw содержит прежние migration44/490 и bootstrap15/173, protected
AAC/v5/degraded rows. Наличие scalar logs не подменяет новые discovery asserts;
они исполняются до прежних blocks в FilesTests. EXE hashes из receipt прочитаны,
но independent actual native byte reread reviewer не выполнял.
Debug helper лично прочитан полностью: build --config Debug, ctest -C Debug,
exe_hashes также из Debug, source verification до запуска, immutable exports.
Raw LastTest.log суммы округлённых case times: RED2.18s, Release26.76s,
Debug37.05s, portable22.14s — это не точное CTest total elapsed stdout.
SDK264d build-only EXE SHA
`f4cf76c9caf6afe9859681d2b50602a04a76e061fa718382868f3cae44d2b0e0`;
build helper прочитан, app не launched/packaged/signed/installed. Main supplied
actual elapsed: Release26.77s, Debug37.06s, portable22.18s/build0; эти stdout
totals отделены от лично parsed LastTest.log rounded case sums.
Full264e helper лично прочитан: build ALL, CTest Release без -R/filter,
sequential -j1, immutable exports. Raw parsed все50 blocks: единственный
FAIL #47 NativeHashFailureTests, assert395, прежний AAC_MDAT_COUNTEREXAMPLE:
original_frames48128, corrupt_decode_complete1, corrupt_frames0,
explicit_root_normal1/explicit_root_playback1/default_root_normal1,
invalid_package0/synthetic_sends1. Files и остальные48 PASS. Это всё ещё
legacy RED257/B1, НЕ full-native GREEN и не новая regression discovery.
Roundedsum50 case times280.77s, не CTest total stdout. Error termination code
в LastTest.log отсутствует; конкретный native exit не выдумывается.
Main supplied actual full264e total281.74s и native termination0xc0000409
для #47; это actual main stdout evidence, не поле прочитанного raw log.

## Финальный actual readback — main execution отдельно от reviewer

Read264f script лично прочитан полностью и hashed:
`56f05818bc3804455f073fab21b3632bd9719d2aaebc309c32abbe2e0360f8f1`.
Проверяет terminal receipt состояния, Release264b/Debug264c source172 в
mirror+NTFS и EXE в правильных Release/Debug folders, затем SDK264d source179
и actual SDK EXE. Main сообщил выполненный tool chunk **74d295**, exit0,
после terminal full264e:

- Release264b: `MIRROR_NTFS_SOURCE_AND_EXE_MATCH`;
- Debug264c: `MIRROR_NTFS_SOURCE_AND_EXE_MATCH`;
- `SDK179_MIRROR_NTFS_SOURCE_AND_EXE_MATCH`;
- `ROUND264F_READONLY_EXIT=0`.

Это executed-main readback evidence из прямого сообщения main, НЕ запуск VM
reviewer и не самостоятельно прочитанный standalone stdout artifact. Reviewer
лично parsed receipts/maps/raw logs, прочитал скрипт и повторно rehashed
canonical172/179: mismatches0. Main подтвердил закрытие всех owned sessions.
Known legacy AAC RED257/B1 не disabled/fixed данным dependency; full application
GO и T116–T120/H250 closure исключены независимо от focused PASS.

## Ponytail и неизменяемая история

Ponytail-only: `Lean already. Ship.` — найдено0 безопасных сокращений,
net:-0 lines possible. Это оценка формы diff, НЕ разрешение release/merge или
замена correctness/evidence gates. Один common openImpl/readImpl, private
reuse, native-first, без нового dependency/parser/controller/target.

До записи captured123 report SHA; после записи все прежние123 hashes лично
сверены: mismatches0, добавлен только этот новый SOURCE report (теперь124).
Tasks SHA остаётся
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Старые reports/markers/tasks/код reviewer не редактировал; diff-check PASS.
Нормативный inventory остаётся10/154checked/0open; tasks120/93/27. Все шесть
before/after implement/analyze/checklist hooks зарегистрированы по одному,
disabled; dispatch0. Отдельного live GitHub запроса/issue mutation не было.
Main supplied fresh T116/#7444 OPEN, reviewer independently GitHub не читал.
