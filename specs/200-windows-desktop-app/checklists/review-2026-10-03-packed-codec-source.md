# Независимая проверка исходников T116: typed packed codec — 2026-10-03

## Решение и область

**APPROVED SOURCE ONLY — C0/H0, конкретных блокирующих ошибок в прочитанных
исходниках этого codec-only шага не найдено.** Это не выполненный тестовый
допуск, не runtime/performance acceptance и не закрытие T116/F200.
Начальные round-trip tests дополнены main во время review; их прочитанный
снимок отмечен ниже. Ещё создаваемые native fault tests этим отчётом не приняты.

Worktree `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Проверяется dirty source snapshot,
не новый commit. Прежняя работа и параллельные изменения main сохранены.
Единственная запись рецензента — этот отдельный отчёт. Gate report не менялся.

Прочитаны полностью `ProtectedCustodyPrimitives.{h,cpp}`,
`ProtectedPackedCustodyCodec.{h,cpp}`, текущий v1 `ProtectedCustodyCodec.cpp`,
а также относящиеся к этой разнице format/memory/SHA helpers, CMake,
app vcxproj и test source. Нормативная область — packed contract §3 и ранее
принятый codec gate; authority/tree/descriptor/birth/commit остаются следующими
частями T116. Code-reviewer применяется к корректности/безопасности;
предыдущий опыт служит только процедурной подсказкой. Сканирование внешним
security-сервисом, новая проверка всей фичи или изменение её требований не заявлены.

## Конкретные findings

**C=0, H=0.** Новых ошибок корректности или безопасности, требующих правки
прочитанного product source, не установлено. Отсутствие ещё не реализованного
owner/tree/descriptor слоя не записано как ошибка неприсвоенной ему codec
authority. Неполнота текущих тестовых доказательств описана отдельно от findings.

## Проверенные свойства

| Область | Прочитанный путь и вывод |
| --- | --- |
| Exact output до копирования | `ProtectedCustodyPrimitives.cpp:51–71`: input/entropy non-null/nonempty, DWORD ranges, output limit и exactOutput проверены. После DPAPI проверяются native pointer, nonempty size, cap и exactOutput; лишь затем создаётся `CustodyBytes`. Packed open передаёт одновременно cap и exactOutput=128+body. |
| Native cleanup | Primitives:58–71: RAII владеет native output до вызова и выполняет SecureZeroMemory/LocalFree также при FALSE, invalid size и исключении owned allocation. GetLastError захватывается в result до destructor. Нет LOCAL_MACHINE, prompt, нового ключа или plaintext fallback. |
| Charged memory и plaintext lifetime | Packed:93/111 и 128/138/142: внутренний plaintext под WipeBytes; allocation failure ловится публичными входами. Возвращённый body сохраняет CustodyAllocator charge; h:22 явно оставляет wipe caller. CustodyAllocator сам не обещает очистку при deallocate. Native allocations отдельно от owned64MiB. |
| Shared SHA | Primitives:15–37: ByteInput заимствует готовые bytes; digest не создаёт полного payload copy, вызывает существующий incremental sha256Stream. Null/count и общий предел проверены; failed hash возвращает nullopt. Новых file/network операций нет. |
| V1 extraction | V1 codec:72–109 сохраняет builder `graf.custody.v1`, IDs, role/kind u16, selector/version u64; block version и index version0 не изменены. Общий helper вызывается с прежними outputLimit/protect и default exactOutput0. Block/index caps и последующие exact header/checksum checks остаются в v1. |
| Типы, адреса, переполнение | Packed:31–45: role allowlist через format; DATA selector<262144 и payload1..262144; NODE body4096 и base alignment64/4096/base0 по уровню. Append offset≥32896/alignment16 и проверка offset+cap до сложения. HEAD selector0/1, exact physical slot128/16512, body128, version>0 и slot rule с g1 исключением. Unknown/EMPTY/ZERO records отвергаются. |
| Header/entropy | Packed:47–70: header128, LE/schema/kind/role/IDs/container/offset/selector/version/body/flags0. Packed entropy — отдельный domain без NUL, schema u16/kind u8/role u8/три IDs/offset/selector. Контекст берётся из ожидаемых аргументов, не из native plaintext. Отсутствие version в packed entropy соответствует contract; version проверяется в typed header. |
| Envelope parsing | Packed:77–91: cap и minimal/exact HEAD cell size до чтения полей; magic/schema/type/role; ciphertext nonempty и внутри cell. Обычный record заканчивается точно после ciphertext, HEAD tail полностью zero. Pointer/iterator arithmetic выполняется после соответствующих bounds. |
| Ref SHA прежде DPAPI | Packed:129–137: intrinsic Ref shape через encodeReference, typed address, exact envelope length, затем SHA exact envelope и сравнение expected protected Ref. Только после этого вызывается open/nativeTransform. Правило действует для DATA и всех трёх NODE kinds, в том числе root NODE_L2. |
| Internal integrity | Packed:93–105: native exact size позволяет безопасно читать header; first96 bytes сравниваются с exact expected header, digest32 извлекается и zeroed. DATA проверяет exact payload SHA; NODE/HEAD — entire plaintext SHA с нулевым digest. Ошибка не возвращает body/version/default ZERO. |
| Cold HEAD | Packed:94–95/139–142: generation0 разрешена только HEAD входу; после unprotect она берётся из header и снова проходит positive-version/slot checks. Nonzero expectedGeneration сравнивается exact header. Это не чтение descriptor и не проверка paired authority. |
| Build registration | CMake:12–24/70–96 включает новые cpp через existing common glob, отдельный packed test, C++17, прежние warnings и crypt32 linkage. App vcxproj:94–96 явно включает primitives/packed codec/format; :154 сохраняет bcrypt/crypt32. Наличие записей не доказательство выполненной сборки. |

Проверка v1 — сопоставление текущего wrapper/checks с прочитанным до
извлечения builder и нормативным v1 §3, не бинарное доказательство поведения
на всех Windows. Вводимые primitive preconditions не сужают допустимые
v1 callers: их input/entropy nonempty и размеры меньше DWORD/owned limit.
V1 max index plaintext112+262144×16=4194416, существенно меньше64MiB.

Полученный `PackedDecodedRecord` содержит только `body` и `version`.
В header:19–34 явно запрещено трактовать его как permission/proof;
`openReferenced` не доказывает происхождение переданного Ref, committed
extent/parent path, ZERO/EOF или tail. Descriptor generation/length/root,
обе heads, retained roots, GuardOwner, birth, checked successor, durable
publication/readback и sticky owner failure остаются семантическому слою.
Заведомо нулевой HEAD body в тесте допустим здесь именно как opaque bytes,
не как валидный descriptor или разрешение normal use.

## Прочитанные тесты и непроверенные доказательства

Тестовый файл менялся main: сначала прочитаны initial round-trips, затем
полностью снимок182 строк SHA `cec6041f2e1b6c88cd0fda179a298a040d7acee61b56716bff46c54d438cf0b0`.
Прочитанные assertions покрывают три роли и DATA/три NODE levels,
high-u64 offset/version, независимо расположенные LE bytes, expected Ref
length/SHA/version, store/object/container и selector substitution, HEAD
g1/g2/g3 обе slots/expected generation/padding, full262144 payload/cap.

Test source:42–87 содержит отдельный native entropy builder с фиксированными
wire offsets и DPAPI перепаковку намеренно испорченного typed plaintext.
Таким образом bad header/IDs/context/flags/digest/body и short/extra plaintext
получают корректно пересчитанный внешний Ref SHA, а не отказывают случайно
только на внешней envelope checksum. Literal u64 byte arrays проверяют
sealer независимо от его собственного decoder. Это чтение конструкции
тестов, не утверждение, что эти assertions были исполнены.

Во время этого снимка отдельные native fault tests main ещё добавляет.
Не подтверждены запуском либо source review нового файла: FALSE output,
TRUE+short/oversized/corrupt output с точным доказательством отсутствия
owned copy, zero/free counters и allocation/hash failures через native shim.
Отдельный тест, включающий реальный primitives.cpp с wrapper symbols,
потребует адресной проверки CMake linkage, чтобы не дублировать обычный
primitives object. Это следующий test-source checkpoint main, не утверждение
о существующем link error и не указание дублировать его реализацию.

Перед test/runtime PASS main нужны fresh native/portable compile/run receipts
на финальных source/test bytes и v1 block/index regression после extraction.
На чтении не найдено причины менять product code для этого. Рецензент не
запускал тестов, сборок, приложение, VM, devices/audio/private inventory,
benchmark, install или release; прежние receipts не перенесены на новые bytes.

## SHA-256 проверенного снимка

Пути относительно корня рабочей копии.

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyPrimitives.h | `5b3f75a9af51aaee6b0efcc9a20f1f5039aaf7e0ea957992d7432a5038619e9c` |
| apps/windows/RecApp/Storage/ProtectedCustodyPrimitives.cpp | `a27b07ac3b04627c5286d6290b3ca6ba3a15710fa170f238be893c3e13c133b3` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyCodec.h | `df71aee96738833815a9583590a53adff44b351dc7bbde8541d9b1e16cb664e1` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyCodec.cpp | `18d6ca5a0ab0e4a454c81512c18a174dc7009d2baabee0b6bb82a80acecd153f` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp | `5372538eb3055c2b9a89786ef15089eb090e574025a3c0c030f87730873506c9` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyCodecTests.cpp | `cec6041f2e1b6c88cd0fda179a298a040d7acee61b56716bff46c54d438cf0b0` |
| apps/windows/CMakeLists.txt | `a3f8d654c5d416c842e424fbb588b0c9a54708baeedef73e56f90d683d63528e` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `24d3deaaba8ffdeb58d9e98fd241d3371a243c5870481680f83f48ccd1fe9b9a` |
| specs/200-windows-desktop-app/tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| specs/200-windows-desktop-app/checklists/review-2026-10-03-packed-codec-gate.md | `6c2882a8ea530acea4dbdc2e0175008f31941b35133b0839d800354832563888` |

## Сохранение области

Gate report и112 normative markers не изменены. Code/test/spec/plan/tasks/
constitution/GitHub/commits не редактировались рецензентом. Принят только
перечисленный product-source codec snapshot; новые test/source deltas требуют
своего адресного прочтения. T116/T117/T118 и все применимые последующие
owner/tree/integration/installed/physical/audio/release проверки остаются открыты.

## Дополнение: окончательный начальный test-source snapshot

Повторно адресно прочитаны новый `NativeCustodyProtectionFailureTests.cpp`
целиком, обновлённый `NativeHashFailureTests.cpp`, окончательные packed codec
fixtures и CMake linkage. Это дополнение заменяет выше статус «native fault
tests ещё не прочитаны», но не утверждает исполнение тестов. Product-source
hashes не изменились; **codec product-source approval остаётся C0/H0**.
В тестовом доказательстве найден один **M1 / P2**, описанный ниже.

### M1 / P2: retained-memory assertion не доказывает отсутствие transient copy

`apps/windows/Tests/GrafWindowsCoreTests/NativeCustodyProtectionFailureTests.cpp:118–125`
проверяет `ownedAtFree == base` после short/long/over-cap native output.
Однако `ownedAtFree` снимается только внутри native `LocalFree` wrapper
(строка57). Если helper сначала создаст локальный `CustodyBytes`, затем
проверит размер и вернёт invalidPlaintext, его временный vector уничтожится
до native RAII destructor; счётчик к этому моменту снова равен base. Поэтому
такой regression также удовлетворяет текущим assertions. Это статический
разбор порядка lifetime, не выполненный mutation test.

В действующем product helper проверки действительно стоят **до** owned copy
(`ProtectedCustodyPrimitives.cpp:67–71`); ошибки реализации здесь не найдено.
Проблема — более сильное утверждение тестового комментария «proves exact
native size is checked before owned copy» не обеспечено наблюдением peak
allocation. Имеющаяся полная резервация бюджета (строки126–131) проверяет
allocation refusal только для корректного native protect output, отдельно
от malformed-size cases.

Минимальное усиление: на direct-helper short/long и over-cap случаях занять
оставшийся owned budget **до** вызова, потребовать invalidPlaintext без
bad_alloc и сохранить wipe/free assertions. Тогда раннее копирование станет
наблюдаемым отказом allocator. Это рекомендация main, не редакция тестов
рецензентом. M1 не отменяет requirements-quality gate и C0/H0 для прочитанной
реализации; до исправления нельзя называть текущий assertion независимым
тестовым доказательством порядка «size-before-copy».

### Остальная проверка новых тестов

- TU-local DPAPI wrappers включают реальный primitives.cpp и не добавляют
  fault switch в приложение. Native FALSE с выделенным output сохраняет
  nativeError; TRUE short/long/empty/corrupt cases проверяют fail-closed
  результаты для DATA, трёх NODE levels и HEAD. `testFree` проверяет каждый
  native byte на ноль до настоящего LocalFree; allocation refusal проверяет
  освобождение native output при исключении owned allocation.
- External Ref SHA и declared-length mismatches для DATA/всех NODE уровней
  проверяются с неизменным числом Unprotect calls. NODE_L2 root не получает
  исключения из этого порядка; decoded body по-прежнему не является proof.
- Hash fault source покрывает create/update/finish failures при seal для
  всех пяти kinds, external hash failures при referenced open и internal
  hash failures при HEAD open. Для DATA/NODE internal hash после успешного
  external hash отдельно инъецируется **create failure на втором вызове**.
  Не заявляется отдельная инъекция всех трёх CNG failure phases именно на
  втором/internal hash DATA/NODE.
- Real-DPAPI malformed typed-plaintext fixtures имеют независимо заданный
  entropy layout и пересчитанный Ref SHA; high-LE fields сверяются с literal
  byte arrays. Это source coverage, не выполненная native acceptance.
- CMake исключает primitives.cpp из общего glob, создаёт отдельный OBJECT
  target и не добавляет его лишь к native protection fault executable,
  который включает ту же реализацию с wrappers. Native hash executable
  получает обычный primitives object, но собственный wrapped SHA source.
  По прочитанной конфигурации duplicate/unwrapped primitive linkage нет;
  оба fault executables добавляются только на WIN32.

Main сообщил о37 portable targets, rebuilt0, и выполняющейся native build.
Рецензент не запускал и не верифицировал эти команды/receipts: никаких
compile/run/runtime PASS это дополнение не присваивает.

### SHA-256 дополнения

| Файл | SHA-256 |
| --- | --- |
| apps/windows/Tests/GrafWindowsCoreTests/NativeCustodyProtectionFailureTests.cpp | `e3dfdc3571f15c93f78d3793af2b42bf4168dcff32f0ec8e3526ccc58a25fbc8` |
| apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp | `b13c2eeb1972afe6e927044072241044e0b39e9e8e6233b598537e3e90d948fe` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyCodecTests.cpp | `cec6041f2e1b6c88cd0fda179a298a040d7acee61b56716bff46c54d438cf0b0` |
| apps/windows/CMakeLists.txt | `70333c26f10ecd88a17750d7dd570ed913d859f45fc247053ac85626e1c13e93` |

Исходная CMake SHA выше сохранена как исторический checkpoint этого review,
а актуальная SHA — в таблице дополнения. Пять product-source hashes выше
повторно проверены без изменений. Gate report SHA повторно подтверждена
`6c2882a8ea530acea4dbdc2e0175008f31941b35133b0839d800354832563888`.
112 normative markers и gate report не редактировались. Единственная запись
этого follow-up — дополнение к данному source report.

### Полученные от main результаты после дополнения

Main сообщил native39/39 PASS за37.81s, portable37/37 PASS за23.74s;
полная VS Release/x64 build ещё выполняется. Эти результаты не исполнены
и не подтверждены рецензентом по журналам. Повторный hash fault-test файла
остаётся `e3dfdc3571f15c93f78d3793af2b42bf4168dcff32f0ec8e3526ccc58a25fbc8`:
direct primitive fixture с2 bytes уже входил в прочитанный снимок.
M1/P2 не закрыт успешным исполнением suite: текущие assertions не отличают
описанную transient-copy regression. Изменений product semantics для
исправления этого test-proof gap не требуется.

## Повторная проверка test-only исправления M1 — 2026-10-03

**M1/P2 RESOLVED по прочитанному test source; C0/H0/M0 открытых findings
в данном ограниченном review.** Этот вывод заменяет выше статус M1 «не закрыт»
для старого снимка, не удаляя историю наблюдений. Полностью перечитаны два
обновлённых test files; code-reviewer применён к различимости отказов,
allocator admission, native cleanup и независимости framing assertions.
Проверка ограничена исходниками и единственной записью в этот отчёт.

### Почему M1 закрыт

`NativeCustodyProtectionFailureTests.cpp:118–133` теперь резервирует весь
оставшийся owned64MiB budget **перед** direct-helper short/long и over-cap
вызовами. Malformed native output имеет ненулевую длину: fixture из2 bytes
даёт short1/long3, а over-cap protect output превышает cap1. В этих случаях
вызов обязан вернуть invalidPlaintext; исключение не ловится и провалит
исполнение теста. Поэтому прежняя regression «создать transient CustodyBytes,
потом проверить size, затем освободить» больше не проходит незамеченной:
allocator откажет ещё до копирования.

Остаются native wipe-before-free assertions в `testFree` и проверка
`ownedAtFree == limit`/отсутствия оставшегося native allocation. В той же
заполненной области **корректный** protect output обязан вызвать bad_alloc,
с native wipe/free cleanup; после освобождения reservation общий charge
возвращается к base. Таким образом malformed-size rejection и реальный
allocation refusal теперь различаются. Это достаточное исправление
конкретного M1 на уровне тестового исходника, без изменения product semantics.

### Дополнительные assertions

`ProtectedPackedCustodyCodecTests.cpp:148–150` повреждает framing bytes
0/7/8/10/11/12 и пересчитывает ожидаемый Ref SHA именно для повреждённого
envelope. Для трёх разрешённых ролей и DATA/всех NODE levels ожидается
invalidEnvelope: assertions больше не зависят от прежнего SHA mismatch.

Строки187–192 заранее вычисляют корректный full-DATA Ref и занимают весь
оставшийся owned budget. Public seal и openReferenced должны вернуть
allocationFailed, не выпускать bad_alloc наружу; charge остаётся ровно limit.
Это проверка двух перечисленных публичных путей, не заявление о новой
HEAD-specific allocation fixture или полном allocator failure matrix.

### SHA-256 принятого test-source снимка

| Файл | SHA-256 |
| --- | --- |
| apps/windows/Tests/GrafWindowsCoreTests/NativeCustodyProtectionFailureTests.cpp | `4defade304b5c95eec58d685a5a084e24cc675dfff2ab8af2b061ca6197ded18` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyCodecTests.cpp | `4f7b616e0f33768662c6ffa334e964bdb4f3b5432feb3dc523139c809188d27d` |

Все5 ранее перечисленных product-source hashes и последний CMake hash
повторно подтверждены без изменений. Tasks SHA остаётся
`ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98`,
packed contract SHA —
`7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed`,
неизменённый gate report SHA —
`6c2882a8ea530acea4dbdc2e0175008f31941b35133b0839d800354832563888`.

Предыдущие39/39 и37/37 receipts не перенесены на изменённые test bytes.
Main сообщил о предстоящих resync/rebuild/run; рецензент ничего не запускал.
Сохраняются source-only approval и прежний requirements gate112/0;
T116/F200 не закрываются, runtime/installed/release acceptance не заявлены.
Code/tests/tasks/checklist markers/gate report не редактировались рецензентом.

## Финальный frozen test-source review — 2026-10-03

**APPROVED SOURCE ONLY; C0/H0/M0 открытых findings. M1/P2 RESOLVED.**
Source review данного codec-only снимка завершён после полного перечитывания
финальных `ProtectedPackedCustodyCodecTests.cpp` (210 строк) и
`NativeCustodyProtectionFailureTests.cpp` (136 строк) и повторной сверки
их SHA-256. Новых причин изменять product source или frozen tests не найдено.
Этот финальный вывод относится к точным bytes ниже и заменяет промежуточные
статусы test snapshots, сохраняя предыдущую историю отчёта.

### Независимые fixtures

Packed test:128–138 задаёт отдельный zero-initialized golden header96B,
не вызывающий production header builder. Он сравнивает все96 bytes:
`GRFPTV2\0`, schema2, kind/role, header length128, ID placements16/32/48
(ненулевые контрольные bytes16/47/55), literal high-u64 LE offset/version,
selector0, body length3/4096 и нулевые reserved/flags. Проверка выполняется
для DATA/трёх NODE levels и трёх разрешённых ролей. Она не объявляется новым
HEAD-specific golden header или exhaustive nonzero-selector fixture.

Строки139–142 вычисляют ожидаемый plaintext digest через test-local `hash`,
не через production `internalDigest`/`custody_detail::digest`: DATA хеширует
исходный body, NODE — plaintext с явно обнулёнными bytes96–127. Проверяется
совпадение32 digest bytes в independently unprotected plaintext. Под
«независимым» здесь понимается отдельный выбор bytes и record-digest scope,
не другая криптографическая библиотека: обе ветки используют проектный SHA.
Framing mutations с пересчитанным Ref SHA, malformed typed plaintext,
round trips и public allocation refusal assertions сохранены.

Native protection test:118–133 по-прежнему занимает полный owned budget
до malformed-size calls; invalidPlaintext без throw отличает size-first
от transient-copy regression. Correct-output bad_alloc и native wipe/free
assertions сохранены. M1 не возобновляется.

### Финальные SHA-256

| Файл | SHA-256 |
| --- | --- |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyCodecTests.cpp | `95a7cd88e709cba04ce5de9dae893fe4fb68f39f50938974c951dce53eef553a` |
| apps/windows/Tests/GrafWindowsCoreTests/NativeCustodyProtectionFailureTests.cpp | `4defade304b5c95eec58d685a5a084e24cc675dfff2ab8af2b061ca6197ded18` |
| apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp | `b13c2eeb1972afe6e927044072241044e0b39e9e8e6233b598537e3e90d948fe` |

Последний NativeHashFailureTests snapshot выше не изменился: его прежний
source review сохраняется. Все5 исходных product-source SHA, CMake
`70333c26f10ecd88a17750d7dd570ed913d859f45fc247053ac85626e1c13e93`
и vcxproj
`24d3deaaba8ffdeb58d9e98fd241d3371a243c5870481680f83f48ccd1fe9b9a`
повторно подтверждены без изменений.

Tasks SHA:
`ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98`.
Packed contract SHA:
`7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed`.
Неизменённый gate report SHA:
`6c2882a8ea530acea4dbdc2e0175008f31941b35133b0839d800354832563888`.

Закрыт только данный независимый **source review**, не T116/issue/F200.
Requirements gate остаётся112 checked/0 unchecked без новых marker edits.
Owner/tree/descriptor/birth/commit не приняты этим codec review. Рецензент
не выполнял сборок, тестов или mutation execution; main должен привязать
fresh receipts к этим frozen bytes. Предыдущие PASS не перенесены.
Единственная запись рецензента — это дополнение к отдельному source report;
gate/code/tests/spec/plan/tasks/constitution/GitHub/commits не изменены.
