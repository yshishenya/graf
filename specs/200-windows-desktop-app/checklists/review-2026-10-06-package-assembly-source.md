# Round254 — SOURCE: совместное удержание ALL-SEALED refs BOTH slots

Дата: 2026-10-06. Независимый reviewer; significant/high-risk storage lane.
Область: только новый batch Reader и делегирование single sealed Reader,
пять файлов относительно `/tmp/graf-f200-assembly-baseline.NE0hiG`.
Основание: reviewer-owned `review-2026-10-06-package-assembly-gate.md`,
R01–R20. Этот отчёт не переписывает предыдущие checklist/evidence.

## Решение

**Scoped SOURCE GO для прочитанной версии реализации. C0 / H0 / M1 / L0.**
M254-1 ниже — неполная явная регрессия двух batch boundaries, не найденный
дефект реализации. Она остаётся открытой для validation closeout. Все20
R-условий имеют подтверждённый source path; это НЕ20/20 выполненных тестов.

**Runtime/installed/feature acceptance: NOT APPROVED этим отчётом.**
Сборки, тесты и VM reviewer не запускал. Требуется новый точный receipt main
для frozen compiler inputs/EXE и текущих assertions; старые Round253 PASS
не принимают новую batch реализацию. T116/T117/T118/T120 остаются открыты.
Live recovery, нормальный пакет, phase admission и actual consumer wiring
не входят в SOURCE GO. Основная цель Windows не считается достигнутой.

## Frozen source identity — первая версия254a

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Dirty bytes задаются SHA-256 ниже; HEAD сам по себе их не описывает.
Пять hashes повторно совпали после сообщения main о formatter/freeze.

| Файл (от корня репозитория) | Прочитанная текущая версия SHA-256 | Baseline SHA-256 |
| --- | --- | --- |
| `apps/windows/RecApp/Storage/ProtectedCustodyReader.h` | `4d3d2074fce96ae3c41581c6a5016fed63ea5b2cafcf91e28ca6c02415415cd9` | `a0a899339cac7f401791ed5355a1a53464a542b7e9cc034bf404aada724389aa` |
| `apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp` | `7e54f7fd7e53f9efaedf69fe3add1243bc4740336d2573c578ed7b477d0b0b17` | `8c04a690f0511a4073717f0dbce837e7ab76a760a3eeb66fb925dc6af83f26de` |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.h` | `8a64d67931c8aa8e86cb673bb7875ce768890ceaacfa1c4914f5390eaaf4ee9c` | `9c230612de5ab10a5cfb6463e1434b3efdd7267db4435826faee204655dc87f6` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp` | `4ce0d2e73ccb2b011eb6ae58446f78d9c5a549325a435b7f24422cabaa85a14b` | `5a80927dcbca4c3f5be17dee09e10d24c07daf1129154c7cfe8c0d17d9d4e1c7` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp` | `58e16474bf1883ca4720e438e02028cf1eff6b5039ebfb6b43e6d9a02cf01d9b` | `5e376d0b9f04b76636f2eee552ff60d5ce2832fd2d95c5c58266c24a9ae6878e` |

Requirements gate SHA-256:
`88e011636cbfdea661c9b0d26f0931bfdc9d9b428600c5121285026ea8f438ae`.
Tasks SHA-256:
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Любая следующая semantic/style/test правка требует сверки новых bytes;
этот SOURCE GO не переносится автоматически на новый hash.

## Findings

### M254-1 — явное покрытие union refs и representation conflict ещё неполно

Ссылки: `ProtectedCustodyFilesTests.cpp:1427`, `:1523`;
`ProtectedPackedCustodyTreeTests.cpp:241`, `:307`;
gate R02/R05 и раздел «Минимум следующего source/validation review».

В frozen новых batch fixtures обе slots содержат одинаковые наборы ролей:
1/1 или5/5, хотя порядок пяти ролей меняется. Поэтому successful mixed
10-stream case не является проверкой missing/bad member, присутствующего
ТОЛЬКО в lower/nonselected slot. Старый peer DATA failure проверяет нижний
индекс одного member, а не union разных member refs. Нельзя смешивать эти
две границы. Отдельного flat/packed conflict одной роли в batch также нет;
container/object conflict existing single regressions покрывают другие входы.

Source не пропускает эти edges: preflight проходит BOTH values в :314–328,
assembly BOTH slots в :332–397; mismatch representation отклоняется в :323.
Это validation gap, не основание заменять правильную реализацию новым backend.

Минимальное дополнение main: own Pair с различающимися refCount, здоровым
selected member и отдельной sealed ролью только lower slot; missing/bad lower
member должен отклонить batch И single выбранного здорового member без
частичного value. Добавить structurally valid same-role flat/packed conflict
между slots с identityMismatch и counters opens/reads==0 после получения Pair.
После этого новая точная native проверка; не ослаблять старые assertions.

## Трассировка корректности и R01–R20

Ссылки ниже относятся к текущему Reader.cpp, если не указан иной файл.
PASS-SOURCE означает проверенную форму кода, не runtime execution.

| ID | Source path и результат |
| --- | --- |
| R01 | PASS-SOURCE — :302–403 один worker batch; Reader.h:44–51 явно ограничивает ALL-SEALED, не полным T116. |
| R02 | PASS-SOURCE — preflight BOTH :314–328, selected-first BOTH :332–397, fixed2×5 table; нет selected-only scanner. M254-1 остаётся для tests. |
| R03 | PASS-SOURCE — :318–320 проверяет sealed/optional fields до первого member open :350/:362; live не skipping/empty/hash success. |
| R04 | PASS-SOURCE — owned shared const Pair :34–42/:311–312; существующая Pair::read/private ctor проверяет actual metadata BOTH, directory/context. Нет caller-created Pair. |
| R05 | PASS-SOURCE — role1..5, object/packed/container equality и cross-role object conflict :317–328; context/directory берутся из own Pair, не caller ref. |
| R06 | PASS-SOURCE — group files/owners индексируются ролью, первый open только при null :349/:361; старый и новый view одной identity используют один actual exclusive owner. |
| R07 | PASS-SOURCE — :365–384 переиспользует readValidatedSnapshotImpl actual BOTH/DATA, сохраняет original trustedPrefix error/native, требует peer.generation, ищет actual exact index. Нет fabricated historical flat index. |
| R08 | PASS-SOURCE — :339–359 actual packed owner + verifyRetained stamp. Existing verifyImpl проверяет current BOTH full closure и historical retained closure; не принимает ref stamp как authority. |
| R09 | PASS-SOURCE — :390–398 SHA всех logical bytes, проверенный true EOF существующего sha256ProtectedStream, compare whole SHA, rewind S_OK/0. Flat length exact; packed immutable descriptor length. |
| R10 | PASS-SOURCE — byte proof не читает manifest/WAV/AAC/phase semantics; API comments запрещают normal/full package authority. |
| R11 | PASS-SOURCE — :386 state→group; Clone :233–243 разделяет тот же state; group удерживает Pair, ВСЕ files/owners/proofs/indices независимо от сброшенной таблицы. |
| R12 | PASS-SOURCE — Reader cursor отдельный :242/:248; только IStream read capabilities, Write/SetSize deny. Group не хранит streams/state, ownership cycle отсутствует. |
| R13 | PASS-SOURCE — :65–86 shared atomic first fault + per-state sticky; group fault проверяется раньше late cancel. Factory возвращает nullopt при любом edge/hash/rewind отказе. Нет частичного результата. |
| R14 | PASS-SOURCE — shared owned cancellation живёт в каждом state; synchronous methods/ComPtr удерживают actual операции; exception boundary bad_alloc, charged shared allocations и RAII освобождают staged result. Отмена не forcibly closes owner. |
| R15 | PASS-SOURCE — allocate_shared/Reader operator new/CustodyVector сохраняют owned charge; batch job :307, прежние pin32/job4/owned64MiB/cache/chunk limits не изменены. Вложенные lifetimes разобраны ниже. |
| R16 | PASS-SOURCE — существующий Reader/cache/codec/hash CustodyBytes wipe; no plaintext file/tmp/URL/export. Worker-only open/read/last-release остаётся требованием caller, не новой UI dispatch guarantee. |
| R17 | PASS-SOURCE — нет account/epoch/effect/GC/delete/migration capabilities; Pair/group bytes не становятся admission. H250 и consumer debt остаются. |
| R18 | PASS-SOURCE — single :289–300 сохраняет null/bounds/target-live preflight и делегирует общему batch, затем move requested cell. Header прямо документирует tightened sibling success domain. |
| R19 | PASS-SOURCE для идентичности — baseline/current hashes выше, fixtures прочитаны, новый receipt всё ещё PENDING. Это не source-bound runtime PASS. |
| R20 | PASS-SOURCE — scope не меняет schema/manifest/v5/backend/tasks, public batch лишь bytes2×5. Production callers нового batch отсутствуют за исключением delegating single; full integration не одобрена. |

## Lifetime, pins/jobs, memory и ошибки

`PackageReadLease` member order :34–42 означает обратное уничтожение:
proofs/owners/indices/files закрываются до Pair. `ReaderState::package`
объявлен первым :44; own snapshot/proof/cache cleanup происходят прежде
last group release. Borrowed identities указывают только на values held Pair.
Группа не хранит Reader/ReaderState, поэтому stream→state→group→Pair не цикл.

Разные ref orders корректны: физические owners indexed role-1, proofs
indexed physical slot*5+refIndex, results indexed physical slot/refIndex.
Group остается у каждого surviving state даже после single delegating factory
уничтожения остальных девяти streams. Flat Clone удерживает packed members:
это прямо проверяется source assertions mixedPackageGroup :375–390.

Pins32 не увеличен. Консервативная верхняя оценка требований26 постоянных
pins остаётся безопасной; фактическая mixed3packed+2flat source форма:
Pair1 + packed owners3 + retained proofs6 + Readers10 =20. Flat Files не
добавляет свой отдельный CustodyPin. Packed plaintext read добавляет временный
pin1; Clone конкурирует с общим32. Tree verification удерживает один новый
proof pin и не materializes второй независимый physical owner. Эти числа —
трассировка lifetimes кода, не замер реального runtime peak.

Jobs4: batch1, в hash sha256ProtectedStream ещё1, один packed Guard/check/read
ещё1; операции status/read serial, Guard destructor освобождает job до
следующего Guard. Verify/open также не совмещают два tree Guards одного owner.
Нет дополнительной очереди или параллельного fan-out в batch. External
pressure может безопасно отклонить операцию, а не увеличить лимит.

PackageReadLease и ReaderState control blocks/Reader allocations charged через
CustodyAllocator. Все flat indices capacities и копии immutable snapshots
также charged прежним CustodyVector. Копии не выданы за бесплатные ссылки:
при их allocation failure RAII уничтожает result и group, возвращая отказ.
Hash buffer64KiB, shared plaintext block cache256KiB и временные codec blocks
сохраняют wipe. Не доказана возможность максимальных simultaneous packages
при любом давлении — quota admission должна отказывать, не превышать64MiB.
Native DPAPI/CNG/CRT allocations не выдаются за измеренный owned total.

Shared fail compare_exchange сохраняет первую причину. `Read` обнуляет got,
при позднем отказе wipe copied bytes и не двигает cursor; sibling/Clone status
видит group HRESULT прежде cancel. Invalid caller operation/read-only Write
не становится новым content authority или причиной стереть observed fault.
Factory state != verified сохраняет original peer recoveryError/native
(M253-1), missing actual peer/generation остаётся recoveryRequired.

## Прочитанные тесты и сохранение старых регрессий

- `sealedFlatMembers` обе schema1/2, sizes0/1/65536/65537, actual g1/g2 bytes
  и initial cursor0 теперь проверяет batch BOTH под одним владельцем, также
  old single checks/readonly/Clone/exclusion/hash/length/object failures.
- В g6 old future-generation assert не выкинут: теперь g5 wrong-ID sibling
  явно ожидает identityMismatch. После clean g7 и future g8 сохранён исходный
  unavailable-index recoveryRequired. g9 oldg1, peer DATA FILE_NOT_FOUND с
  exact native error и missing peer index regressions остаются.
- `sealedPackageGroup` all5roles с обратным INPUT ref order, 10 streams, job4/pin32/
  owned64MiB pressure opens/reads0; nonrequested sibling bad SHA; live sibling
  whole rejection before member IO. Реальный injected ReadFile fault на одном
  state распространяется на sibling/Clone прежде late cancel.
  Уточнение после receipt main: serializer нормализует INPUT order, поэтому
  эта первая версия НЕ проверяла reversed physical order и её slot1 expected
  bytes assertion оказалась ошибочной. Коррекция ниже, это не product defect.
- `sealedPackedMember` batch historical g2 сохранил old bytes за current heads,
  existing container/future/hash/retained-DATA corruption tests не удалены.
- `mixedPackageGroup` три packed роли: historical g2 вне heads g3/g4, current
  g4 с иными bytes/length3/5; две flat metadata birthg1; surviving flat recovery
  Clone удерживает все five members и parent, last release снимает exclusions.

Это лично прочитанные assertions, а не утверждение, что они выполнились.
M254-1 и exact runtime validation остаются отдельными условиями closeout.

## Ponytail review — только сложность

**Lean already. Ship.** Для frozen bounded SOURCE diff безопасного значимого
удаления не найдено. Общая группа не speculative abstraction: необходима,
чтобы каждый surviving Clone держал ВСЕ member leases без вторых open/scanner.
Existing validators, IStream и std::array/shared_ptr переиспользованы; нет
новой зависимости, interface hierarchy, registry или live backend.
Эта формула означает отсутствие complexity findings, не разрешение выпуска.

## Execution receipts и оставшиеся границы

Только MAIN-REPORTED, не независимо выполнено reviewer:

- RED session75351 exit1 C3861: batch identifier отсутствовал в baseline.
- Первый GREEN attempt25974 terminal8: Tree PASS23.62s, Files FAIL на прежнем
  future-gen expectation из-за wrong-ID sibling. Причина и строгая новая
  success domain явно исправлены без удаления unavailable-index проверки.
- Main сообщил freeze и запуск final native8suite session92635; receipt
  `C:/Temp/graf-f200-members-round254.json` и manifest171inputs
  `source-members-round254.json` пока не читались reviewer. Terminal result,
  exact compiler inputs/EXE identity и completion не объявляются PASS.

Не делалось: builds/VM/device/audio/installed run, GitHub/commit/push/merge,
consumer wiring, working-profile mutation, spec/tasks/constitution edits.
H250-1/H250-2, full package/format/admission, live recovery, producer/consumer
integration, migration и privacy Pause acceptance не закрыты.

Работа reviewer: лично прочитаны пять текущих файлов/изменённые тестовые
области и baseline diffs; повторно traced Pair, Files actual validator,
packed Guard/verifyRetained/readBlock, hash EOF, charge/pin/job primitives.
Применены code-reviewer, speckit-analyze boundaries и ponytail-review.
Нет утверждения, что заново аудированы все строки большого historical test
файла или все consumers. До записи этого отчёта git diff --check пяти файлов
PASS; единственная запись reviewer — этот новый отчёт.

## Последующая personally-read сверка254b — только FilesTests

После сообщения main о native8suite7/8 лично проверена причина в существующем
`ProtectedCustodyMetadata.cpp:211`: writeCustodyPackage сериализует refs по
role, поэтому initial reversed INPUT не равнялся reversed stored array.
Terminal92635/5979b3,7/8 — MAIN-REPORTED, не проверенный мной receipt. Этот
failed run сохранён как отказ, не объявлен успешной валидацией новой версии.

Лично прочитана новая изменённая область FilesTests:1540–1651. Наблюдённый
SHA-256 FilesTests: `d8ce53aed2e42ed2fd9f0c3c76c873c47793c02100bc21904c0b6e69028f4f08`.
Остальные четыре hashes остаются таблицей254a; новое SOURCE рассмотрение
касается только этой тестовой поправки, не ещё неизвестного receipt254b.

- Expected byte теперь вычисляется из actual heldPair ref.role/generation,
  не из неверного ordinal assumption.
- Test дополнительно обращает actual serialized JSON refs перед commitg2,
  проверяет Pair slot1 refs[0]==recovery/refs[4]==canonical. Это даёт SOURCE
  основание для нового reversed stored-order assertion; runtime пока pending.
  Разбор fixed synthetic JSON в тесте не новый production scanner.
- Bad sibling в g4 теперь повреждает INPUT recovery ref[0], а requested
  lower g3 playback остаётся здоровым; single отказывает из-за другой ссылки.
- g3 refCount3 playback/manifest/recovery против lower g2 all5roles создаёт
  реальный asymmetric3/5 Pair; current playback Clone удерживает lower-only
  canonical/media. Это закрывает SOURCE часть успешной lower-only retention
  регрессии, но не failure missing/bad lower-only member.

M254-1 сужается: ещё нужны explicit missing/bad lower-only refusal и
same-role flat/packed conflict opens/reads0. Success retention не подменяет
refusal regression. Scoped SOURCE GO реализации сохранён, execution и
validation closeout остаются PENDING. Новых C/H source findings нет.

Финальная readback сверка: все пять текущих hashes совпали с254b выше;
102/102 предыдущих checklist файлов сохранили SHA-256. Единственный новый
файл — этот отчёт. Его текст лично перечитан полностью; scoped diff --check
PASS. Source-only решение готово, ожидание native receipt не задерживает
его передачу main и не превращается в runtime GO.

## Подтверждение SOURCE freeze254b после сообщения о native8/8

Все пять SHA-256 повторно лично проверены и совпали с254b выше; production
Reader/headers/TreeTests не изменились. **Scoped SOURCE GO сохранён:
C0/H0/M1/L0. Ponytail: Lean already. Ship.** Только bounded ALL-SEALED
BOTH-slots prerequisite, не полный T116 или функциональная готовность Windows.

MAIN-REPORTED: final254b native8/8 PASS36.33s, terminal91591/616376,
configure/build/test exit0;171input freeze совпадает с указанными main hashes.
Reviewer лично проверил пять source hashes, но не прочитал terminal/receipt
и полный171-input manifest; поэтому runtime result не назван независимо
подтверждённым. Предыдущие failed attempts остаются историческими отказами.

MAIN-REPORTED governance/doctor PASS93046/aea6b2. Debug3 и latest portable46
ещё выполняются main последовательно; прежний portable46 PASS21.46s относится
к более ранним bytes и не принимается за current254b execution. Mac portable
checks не доказывают Windows-native выполнение. M254-1 не закрывается одним
8/8 без отсутствующих assertions. No full-feature/installed/release GO.

## Append-only переоценка254c — M254-1 устранён в SOURCE

Лично перечитаны текущий `sealedPackageGroup`, diff FilesTests относительно
исходного `/tmp/graf-f200-assembly-baseline.NE0hiG` и применимый packageShape
в `ProtectedCustodyMetadata.cpp`. Все пять hashes повторно проверены:

| Файл | SHA-256 текущего254c |
| --- | --- |
| `ProtectedCustodyReader.h` | `4d3d2074fce96ae3c41581c6a5016fed63ea5b2cafcf91e28ca6c02415415cd9` |
| `ProtectedCustodyReader.cpp` | `7e54f7fd7e53f9efaedf69fe3add1243bc4740336d2573c578ed7b477d0b0b17` |
| `ProtectedCustodyFiles.h` | `8a64d67931c8aa8e86cb673bb7875ce768890ceaacfa1c4914f5390eaaf4ee9c` |
| `ProtectedCustodyFilesTests.cpp` | `2ba824f47a2d89070d90745b7204a30f44f978a696d2218cda18cf941ee32941` |
| `ProtectedPackedCustodyTreeTests.cpp` | `58e16474bf1883ca4720e438e02028cf1eff6b5039ebfb6b43e6d9a02cf01d9b` |

От254b изменился FilesTests hash; остальные четыре точные версии прежние.
HEAD остаётся `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Ранее указанные M1/отказы/receipts остаются историческими и не переписаны.

### Same-role flat/packed conflict — SOURCE PASS

FilesTests:1560–1567/:1652–1659: g6 flat canonical и g7 schema2 packed
canonical имеют ту же object identity. Packed reference структурно допустим:
birth generation1, logical length0, empty SHA, appendOffset и encoded empty
root; packageShape допускает его. Commit/Pair read должны успешно завершиться
до тестируемого member boundary, это не malformed metadata rejection.

После получения own Pair counters сбрасываются. Batch требует null value,
identityMismatch, opens/reads0. Single запрашивает здоровый selected media
slot0/ref1 и требует тот же отказ/null value/opens/reads0. Таким образом,
исключён ошибочный проход только requested member или IO до conflict preflight.
Отсутствие actual packed container здесь намеренно: его не должны открывать.

### Bad lower-only member — SOURCE PASS

FilesTests:1558/:1661–1668: в g8 меняется SHA INPUT canonical ref[4]; g9
содержит лишь playback/manifest/recovery, refCount3. Actual selectedSlot0
и current refCount3 проверяются явно. Canonical остается только lower g8
slot1; selected playback slot0/ref0 здоров, member data/index не менялись.

Batch и single healthy playback требуют null value и invalidContent. Это
отдельная регрессия union refs: повреждение не в selected slot, не в peer
индексе того же requested member и не в malformed own Pair. Bad SHA lower
canonical достаточен для требовавшейся missing/bad lower-only refusal
границы; этот отчёт не утверждает отдельный новый FILE_NOT_FOUND case.
Старые actual peer DATA/missing index assertions сохранены.

**M254-1: RESOLVED-SOURCE. Текущее scoped SOURCE GO: C0/H0/M0/L0.**
Новых замечаний в этих тестовых поправках нет. Это закрытие конкретного
пробела SOURCE assertions, а не выполненного runtime gate. Production Reader
не изменён; прежняя оценка bounded lifetime/first fault/quota сохранена.
Дополнительной архитектуры/сканера нет; прежний Ponytail complexity verdict
не требует production refactor из-за добавления необходимых регрессий.

Runtime254c Release/Debug/SDK: PENDING, main выполняет последовательно.
Reviewer не запускал тесты/сборки/VM и не проверял новые receipts. Native8/8
из254b относится к прежнему FilesTests hash d8ce53... и не доказывает новые
assertions254c. No full T116/full-feature/installed/release acceptance.

Изменение reviewer ограничено добавлением этого раздела в собственный SOURCE
отчёт; tasks/spec/plan/другие checklist/GitHub/code не менялись. Задачи не
закрывались. Полнота consumer integration/live recovery и прочие ранее
названные acceptance gates остаются за пределами решения.

### Новое сообщение main о выполнении254c — MAIN-REPORTED

- Native Release8/8 PASS34.53s, terminal26203/b81119, configure/build/test0;
  Files8.53s, Tree23.58s.
- Current portable46/46 PASS8.29s, terminal95561/85c6d3.
- Main подтвердил FilesTests SHA-256
  `2ba824f47a2d89070d90745b7204a30f44f978a696d2218cda18cf941ee32941`,
  который совпадает с лично прочитанной reviewer версией254c.
- Source171 manifest SHA-256, сообщённый main:
  `906e564cea7a897e7dfbeba90de682c71155558039637450294e555b3f36a541`.
- SDK178 manifest SHA-256, сообщённый main:
  `357ef9755ad0a6a29521d4a7acfe898e2bbc0c89be18462cc63461fa0ec39b4e`.

Debug254c и SDK ещё PENDING по сообщению main. Reviewer не читал эти
terminal receipts/manifest contents и не запускает тесты или VM: hashes
полных manifests и runtime PASS здесь main-reported, не независимый runtime
GO. SOURCE решение C0/H0/M0/L0 и RESOLVED-SOURCE M254-1 сохраняются.
Задачи и full-feature/installed/release gates не закрыты.

## Предварительный DOCS review Round254 — окончательное решение PENDING

Область лично прочитанного текста:
`validation-2026-10-02.md:10452` Round254 tail,
`quickstart.md:831` совместное чтение запечатанных файлов,
`changes/unreleased/F200.yaml:1842` только
`release_notes_round254_joint_protected_readers`.
Соседние Round253 сведения не принимаются за evidence254c. Код, три main
документа, tasks и GitHub reviewer не меняет; запись только append этого отчёта.

Прочитанные текущие SHA-256 всего файла (не отдельных секций):

| Документ | SHA-256 |
| --- | --- |
| `validation-2026-10-02.md` | `2d4abaffa1447cce2ceed2d799997944cf3d13a621fe7fcdc997cc29d7af8b9a` |
| `quickstart.md` | `565fd909cf3a79a6adfc21f7ab0e8ea146f850f2ddc146e115778e42ba29014c` |
| `changes/unreleased/F200.yaml` | `9fcaa3cdacf0fb23b5d26a1672209efdf09d667ea7d4a4e5276f0a1afcb452eb` |

Tasks лично hashed без изменения:
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Scoped diff --check трёх документов PASS; F200 YAML parse PASS, нужный ключ
присутствует. Enabled before/after_analyze hooks0, hooks не запускались.
Skill prerequisite command с `--require-spec` оказался неподдерживаемым;
help и поддерживаемый `--json --require-tasks --include-tasks` вернули canonical
feature200. Это tooling-совместимость, не product defect; новых задач нет.

### Подтверждено по тексту

- ALL-SEALED union BOTH slots, fixed2×5, shared lifetime через last Clone,
  identity/representation conflict, exact length/SHA/EOF, quotas и shared
  first fault соответствуют лично принятому SOURCE254c.
- Strict-superset single success domain и live whole-batch refusal явны.
  Quickstart отдельно запрещает удаление старой live slot или лишний sealed
  commit ради обхода отказа. Partial result не разрешён.
- Full manifest/formats/phase/trustedPrefix/account/admission, actual
  writer/upload/playback consumers, migration и working-profile/H250 не
  объявлены принятыми. Приложение не выдано за полностью подключённое.
- Native8/Debug3/portable46 числа совпадают с сообщениями main. Validation
  называет их MAIN terminal evidence, не независимо выполненной reviewer
  проверкой. Debug не exhaustive matrix, portable не native DPAPI evidence.
- SDK и final actual receipts/source/EXE reread явно PENDING в Round254;
  прежний SDK/read PASS в соседнем Round253 fragment не перенесён на254c.
  Failed254/прежний254b не переписаны и не принимаются за новые assertions.
- Source acceptance «без оставшихся замечаний» относится к устранённому
  M254-1 и C0/H0/M0/L0 данного bounded source среза, не full-feature GO.

### D254-1 — MEDIUM: scoped FR/SC mapping не совпадает с requirements gate

Validation:10493–10494 приписывает20 prerequisite obligations шесть mappings
`FR012/013/014/022 и SC003/006`. Requirements gate:169–170 фиксирует другой
scoped набор: `FR-011/012/013/014/022 и SC-006`.

SC-003 требует60-minute reference capture, frame/duration/level/CPU/memory
показателей; joint reader source/native generated tests не принимают эту
матрицу. Валидация в целом правильно оставляет её открытой, но эта короткая
scoped analyze строка неоднозначно подменяет approved gate coverage.

Минимальная коррекция main: привести перечень к exact requirements gate;
либо явно отделить собственную карту будущего полного T116/SC-003 от mapping
20 bounded prerequisite obligations. В обоих случаях mapping не означает
выполнение FR-011 formats или SC-003 hardware/60min. Не требуется изменение
spec/plan/tasks, code или повторный новый task ради этой строки.

**Предварительно DOCS: C0/H0/M1/L0; итоговый DOCS verdict PENDING.**
SOURCE254c C0/H0/M0/L0 и RESOLVED-SOURCE M254-1 не отменены этой текстовой
неточностью. Финальное DOCS решение reviewer оставляет до requested actual
receipt read main и повторного чтения его окончательного append; текущие
числа/manifest identities пока main-reported.

Новый SDK254c terminal29580/b120af restore/build0 и full Windows50 running —
только сообщение main, не лично прочитанный receipt. Reviewer не запускает
VM/tests и не превращает SDK build в full-feature/installed acceptance.
GitHub7540 OPEN/canonical labels — main-reported, reviewer не читает/пишет
GitHub в этом DOCS scope. Tasks не закрываются. Исторические prefixes этого
SOURCE отчёта сохраняются, окончательного DOCS GO пока нет.

### D254-1 — исправление лично перечитано, RESOLVED-TEXT

Лично сверены validation:10493–10498: scoped перечень теперь exact
`FR011/012/013/014/022 и SC006`, как в requirements gate. Отдельная строка
явно говорит: карта связи не принимает FR011 formats или SC003/60min.
Это устраняет найденную неоднозначность без изменения spec/plan/tasks/code.

Новый validation whole-file SHA-256:
`eee7d6da2f6ca4024ac6f2b9bde4c3decf99ff589d9f060b18c214632b2602fa`.
Quickstart/F200 hashes прежние из предварительного DOCS раздела; tasks hash
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`
повторно совпал. Source verdict C0/H0/M0/L0 сохраняется.

**Текстовые DOCS findings теперь C0/H0/M0/L0; итоговый DOCS verdict всё ещё
PENDING по requested actual-read/full50 gate.** Main сообщил личное чтение
reviewer append345–417/fd5dce, но actual receipts read/full50 ещё ожидают
terminal. Reviewer не запускает повторный job, VM или тесты и не объявляет
SDK/receipt/full-feature acceptance. Предыдущие разделы отчёта не переписаны.

## FINAL DOCS Round254c — scoped GO C0/H0/M0/L0

Финальный личный read: validation Round254:10452 и весь новый раздел
«Окончательное выполнение254c и перечитывание фактических файлов»;
quickstart joint-sealed:831–849; F200 только ключ
`release_notes_round254_joint_protected_readers`, включая новые строки1853–1855.
**Итоговый DOCS scoped GO: C0/H0/M0/L0. D254-1 RESOLVED-TEXT.**
Предыдущие PENDING в этом отчёте/validation — исторические состояния,
дополненные текущим решением, не переписанные как прежний PASS.

Final personally hashed whole documents:

| Файл | SHA-256 |
| --- | --- |
| `validation-2026-10-02.md` | `c4cc23a6bb421bf04774804ed1cd550b247b2e46d7c2a7246ddd37712d120408` |
| `quickstart.md` | `565fd909cf3a79a6adfc21f7ab0e8ea146f850f2ddc146e115778e42ba29014c` |
| `changes/unreleased/F200.yaml` | `1c554674ea4aa19ae082dd62b64372053b6b348e75e7360f1956c2bb4a3daa29` |

Все five source254c hashes повторно лично совпали с выше принятой таблицей;
FilesTests2ba824f47a2d89070d90745b7204a30f44f978a696d2218cda18cf941ee32941,
остальные четыре неизменны. Tasks80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f
также совпал; reviewer задачи не меняет и не закрывает.

### Scope F200 addition подтверждён независимо по тексту

YAML parsed, новый full50/SDK/read текст находится в значении Round254 key,
не Round253 или более ранних разделов. Дополнительно reviewer убрал только
эти три строки из считанного текста В ПАМЯТИ, не редактируя файл: SHA полного
остатка точно равен предыдущему personally-reviewed F200
`9fcaa3cdacf0fb23b5d26a1672209efdf09d667ea7d4a4e5276f0a1afcb452eb`.
Следовательно, relative to этому baseline старые YAML fragments побайтово
сохранены. Scoped diff --check трёх документов PASS, YAML parse PASS.

### Runtime claims сверены с сообщениями main, не исполнены reviewer

Новый validation append точно сохраняет границы и MAIN provenance:

- Native8 Release34.53s, Debug3/47.87s и portable46/8.29s — current254c.
- SDK29580/b120af restore/build0 со штатным Windows App SDK/AEC3; прежний
  D9025 warning не скрыт и не объявлен warning-free build.
- Full50 terminal35353/b3dd43 configure/build/test0 PASS241.88s; longest
  Owner180.42s при прежнем300s, без exclusions/увеличенного timeout.
- MAIN actual read2995/45f239: four receipts terminal/passed, actual NTFS
  и Mac mirror inputs/executables совпали; canonical171/178 MATCH3f2315.
- Четыре receipt SHA совпадают с последним сообщением main:
  Release `a6e4bfb909763327d08fe26ec2b221ff025dd2f249bf355495510d9bde36d96f`;
  Debug `66535beb91e944f1071f3e74502ceb716400703a48d3fe540df77e2d4fae18f9`;
  Full `f384cd205de1cc09409392bce1d6a4ec05bafb6bd5a7206d8b02f3df30db810d`;
  SDK `59839952b45269a6e4ee5b79c5539a4d0555a72fabafd07859efa72b49be19fa`.
- SDK app SHA в тексте/сообщении main:
  `734f187c18f957f3a39ccb4d694c1c602f36800b97422f495fefa0be515a5055`.
  Source171/SDK178 manifests остаются906e564c…/357ef975… из предыдущего
  лично прочитанного validation раздела; reviewer не сверял contents manifests.

Это independently-reviewed DOCS consistency, **не независимый runtime GO**.
Reviewer не читал actual receipt/EXE bytes, не проверял NTFS/mirror171/178 и
не запускал tests/VM. Release/Debug Files EXE hashes в новом append принадлежат
main actual read; дополнительным личным доказательством reviewer не названы.
Main сообщил all build/test/read terminal, а последний governance/doctor/YAML/
diff rerun ещё выполнялся в момент запроса DOCS verdict; его completion этим
обзором не объявляется. DOCS решение не заменяет required checks/commit gates.

### Окончательные пределы решения

SOURCE254c и DOCS текущего bounded ALL-SEALED BOTH-slots prerequisite приняты.
R01–R20 не становятся full-feature acceptance. Общая группа bytes/leases не
принимает live recovery, manifest/formats/duration/phase/trustedPrefix,
normal package/admission, account/effect authority или actual V5/MF/queue/
upload/playback wiring. T116 CRITICAL partial, T117 migration HIGH и T118
full pipeline acceptance HIGH остаются открытыми; T119/T120/T097/H250 и
physical/hardware/installed/release тоже не закрыты. Goal не complete.

Reviewer writes ONLY append в собственный SOURCE report; main docs/source/
tasks/GitHub/Git/work profile/OS/audio/install не менялись этим review.
Исторический префикс собственного отчёта сохраняется побайтово.
