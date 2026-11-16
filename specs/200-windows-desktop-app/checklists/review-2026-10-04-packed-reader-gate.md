# Проверка качества требований: packed read-only IStream / T116

**Purpose**: независимая проверка достаточности требований к ограниченному
шагу чтения packed snapshot через существующий ProtectedCustodyReader до
изменения исходников и тестов. Это не source acceptance и не принятие T116.
**Created**: 2026-10-04.
**Feature**: `specs/200-windows-desktop-app/spec.md`, FR-012/013/014/022;
plan «Поправка масштабирования хранения», Step3; T116–T118;
quickstart §14; packed contract §§1–7; Constitution IV/VI.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch/source anchor: `codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, с сохранением dirty round223.
Risk lane: independent requirements-quality review внутри существующего
high-risk-product Spec Kit среза. Список reviewer-owned: `[X]` означает
качество требований, а не готовность кода, установленного клиента или выпуска.
Main читает результат и не меняет отметки. Все20 пунктов сначала сгенерированы
без отметок; отдельная независимая оценка будет записана ниже.

## Источники и обозначения предложения

Нормативная основа остаётся в существующих spec/plan/tasks/contracts.
Следующие P1–P6 — указатели на техническое предложение main и его уточнение,
не новая норма, решение человека или разрешение adoption:

- P1 — явная перегрузка openProtectedCustodyReader для non-null immutable
  Tree proof и cancellation; непрерывный прежний Owner, без caller stamp/path,
  reopen, downgrade и package/upload/delete authority. Прежний flat-v1 factory
  выбирается явно и сохраняется для v1 служебного представления.
- P2 — существующие Reader/ReaderState/ReadCache/COM методы и mutex;
  fixed proof и snapshot length, каждый stream/Clone имеет pin до allocations;
  общий state через CustodyAllocator, fixed state/root≤4KiB. Уточнение main:
  фиксированный COM Reader также учитывается class-specific operator new/delete
  через существующий CustodyAllocator<Reader>, exact sizeof, без новой системы
  выделения памяти; это изменение затрагивает и v1 Reader.
- P3 — Tree::checkRead через один private Guard, без full closure/new proof/ACK;
  bad_alloc отклоняется через удерживаемый Guard. Shared status сначала
  обрабатывает cancellation, сохраняет первое HRESULT и ошибки native/alloc;
  исключения не выходят через noexcept. Guard перед cache use и Read final,
  Seek/Stat/Clone/Commit. Jobs4 и memory64MiB имеют отказ до новых эффектов.
- P4 — один общий cache≤256KiB в общем ceiling2MiB, exact immutable state+block;
  cache miss делегирует Tree::readBlock, verified bytes перемещаются без нового
  native owner. SHA/context/full-short/ZERO семантика остаётся в Tree.
  Cache не обещает fresh disk на каждом hit и не скрывает observed Owner fault.
- P5 — Read: got0 на входе, при fault очистить уже скопированные bytes, не
  сдвигать cursor и не выдавать partial success; обычный EOF/S_FALSE и нулевой
  запрос сохраняют COM семантику. Seek signed SET/CUR/END, beyond-EOF до
  LLONG_MAX; unnamed private Stat, denied Write/SetSize. Clone разделяет exact
  proof/state/failure/cancel/cache, но не cursor. CopyTo удерживает source и
  destination через callbacks, не держит IO lock при target Write, использует
  bounded/wiped buffer и учитывает partial-write/error.
- P6 — RED до implementation; actual generated native Reader/Tree/Files
  проверки full/short/ZERO/cross-boundary/old snapshot/fault/lifetime/admission;
  существующие v1 FilesTests сохраняются, включая31 admitted concurrent Clones,
  cancellation и CopyTo OOM. Release/Debug Tree+Owner+Files, полный Release41,
  portable39 отдельно, AppBuild пропорционально final SHA. Не установка,
  устройства, private inventory, package/migration/adoption или full T116.

## Полнота и границы полномочий

- [X] CHK001 Достаточно ли явно ограничен шаг чтением существующего packed proof и отделён от полного WriteAt/SetSize/shrink, schema/adoption/migration, cadence и готовности приложения? [Полнота, Plan Step3–7, T116–T118, P1/P6]
- [X] CHK002 Определены ли допустимые входы и основание доверия: non-null proof/cancellation, отсутствие принятой отмены, частный неизменяемый Tree proof того же непрерывного Owner, без caller descriptor/root/path или создания нового proof? [Ясность, FR-012, Packed §§1–2, P1/P3]
- [X] CHK003 Явно ли разделены packed overload и flat-v1 factory, без угадывания представления, decoder downgrade или plaintext fallback при ошибке? [Согласованность, FR-012/013, Packed §§1/6.1, P1]
- [X] CHK004 Определено ли, что verified результат Reader подтверждает только читаемый media snapshot, а не normal package, account/epoch/stamp, upload/delete полномочия или новый logical ACK? [Ясность, FR-013/014/022, Packed §§1/5/6.1, P1/P3]

## Владение, память и допуск

- [X] CHK005 Полны ли требования к непрерывному Owner: writer revoke не отзывает чтение, Clone/CopyTo сохраняют файл после освобождения caller/Tree/Owner, а cold reacquire допустим лишь после actual last release и новой полной проверки? [Покрытие, Packed §§2/5/7, FR-012/022, P2/P5/P6]
- [X] CHK006 Явно ли задан общий предел pins32 и admission до allocations для factory/Clone с собственным pin каждого stream; нет ли ошибочного обещания31 packed Clones сверх уже удерживаемых Owner/Tree/result pins? [Измеримость, Packed §6, P2/P6]
- [X] CHK007 Достаточно ли определён учёт owned64MiB для shared control/state, фиксированного COM Reader/Clone, cache и временных буферов, fixed state/root≤4KiB, с отказом до allocation и корректным release, без per-block/N-sized packed state или нового allocator framework? [Полнота, Packed §§4/6, SC-003, P2/P4/P6]
- [X] CHK008 Определены ли отказ при jobs4/memory/pins exhaustion, отсутствие успешного чтения после shared failed state и сохранение первого native error/HRESULT, без маскировки EOF, invalid-size или cache-hit результатом? [Покрытие ошибок, FR-012, Packed §§1/2/6/7, P3/P6]

## Кэш и проверка наблюдаемой ошибки

- [X] CHK009 Достаточно ли ограничена проверка текущего read status одним Guard существующего Owner без full old-DATA scan, нового HANDLE/epoch, проверки новых HEAD вместо старого pinned root или обновления authority? [Согласованность, FR-012, Packed §§2/4/5, P3]
- [X] CHK010 Определены ли точный ключ cache по immutable state/proof/root и block, ceiling256KiB внутри2MiB, проверка SHA/context/exact full/short/ZERO до кэширования и очистка при замене/actual state release? [Ясность, Packed §§3/4/6, P2/P4]
- [X] CHK011 Полны ли требования к проверке observed Owner fault перед cache use и успешным завершением Read/Seek/Stat/Clone/Commit, без обещания свежести носителя на каждом cache hit и без successful cached bypass после blockWrites? [Согласованность, FR-012, Packed §§1/4/7, P3/P4/P6]

## Семантика чтения и COM

- [X] CHK012 Однозначно ли определён отказ Read до и после частичного копирования: got0, очистка выданной части, неизменный cursor, первое sticky HRESULT в общем state всех Clone, без partial-success при fault? [Полнота, FR-012, Packed §§1/2/7, P3/P5/P6]
- [X] CHK013 Определены ли обычный partial EOF/S_FALSE с exact got, нулевой запрос, empty snapshot, short tail и explicit ZERO без padding, а также исключения native/copy/seek/status с отказом вместо выхода через noexcept? [Покрытие границ, Packed §§3–5/7, P3/P5/P6]
- [X] CHK014 Явно ли заданы signed Seek SET/CUR/END, negative/overflow refusal, допустимый cursor beyond EOF до LLONG_MAX, точная неизменная длина в unnamed Stat и denied Write/SetSize без commit authority? [Ясность, Plan Step3, Packed §§2/3, P5]
- [X] CHK015 Достаточно ли определены независимый cursor Clone, общие proof/failure/cancel/cache и sticky cancellation после сброса флага, без serialization/refresh root или raw controller lifetime? [Полнота, Packed §§2/4/7, P2/P3/P5/P6]
- [X] CHK016 Определены ли CopyTo actual source/destination lifetime через callback, отсутствие shared IO lock во время target Write, предел и очистка buffer, partial/error accounting и отсутствие нового plaintext файла или неявной authority? [Покрытие, FR-012/022, Packed §§2/6, P5/P6]

## Проверяемость требований и зависимости

- [X] CHK017 Задано ли объективное покрытие exact bytes full+short/cross-boundary/Seek/Stat/EOF/ZERO, immutable старого stream после HEAD eviction/rewrite/growth, retained Clone, external-writer/cold-open refusal до release и fresh full verify после release? [Измеримость, Packed §7, Quickstart §14, P6]
- [X] CHK018 Полны ли требования к отрицательным сценариям: fault before/mid Read, copied bytes wipe/got0/cursor unchanged/all Clones failed, warmed cache затем observed Owner fault, exact error/admission limits до success? [Покрытие ошибок, FR-012, Packed §§1/6/7, Quickstart §14, P3/P6]
- [X] CHK019 Явно ли сохранены существующие v1 Reader/Files/metadata no-rollback regressions при общем COM allocation изменении, и ограничены ли изменения повторным использованием нынешних Tree/Reader/Memory/fixture/COM методов без второго framework/lifecycle? [Согласованность, FR-013, Packed §§1/6/7, P2/P6]
- [X] CHK020 Достаточно ли разделены requirements approval, будущий independent source review, RED, final exact-source native Release/Debug/полный Release, portable exclusions, AppBuild и отдельная installed/hardware/полная приёмка без task closing или автоматического commit? [Прослеживаемость, Constitution VI, Plan Step3–7, T116–T118, Quickstart §14, P6]

## Примечания при генерации

Создан новый список20/20 без отметок: **0 checked / 20 unchecked**.
Это не blocker findings: независимая оценка ещё не записана. Уточняющие
вопросы о человеке/product policy не требуются: область, владелец, глубина
и исключения заданы в запросе. Новый source report не создан; source-ready
ещё не получен. Старые отчёты/marks, код/tests, нормы/tasks, VM/Git/GitHub,
installation/private inventory/commit/release не изменялись и не выполнялись.

`.specify/extensions.yml` лично прочитан и успешно разобран Ruby YAML:
before_checklist/after_checklist содержат только enabled:false commit hooks;
они не выполнялись. Read-only prerequisite с checklist-template вернул
canonical active FEATURE_DIR и шаблон. speckit-checklist/code-reviewer,
root AGENTS/guidance index и нужные guidance лично прочитаны полностью.
Packed contract §§1–7 перечитан полностью; релевантные FR/SC, plan Step3–7,
T116–T118, quickstart §14, Constitution IV/VI перечитаны. Прежнее полное чтение
неизменных активных норм/PRD/status/data-model/local-custody переиспользовано
только после fresh SHA проверки, не заявляется новым полным чтением всех норм.

Нормативные SHA-256:

| Файл | SHA-256 |
| --- | --- |
| spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |
| data-model.md | `ed7da763ddaa281f7cca2d05b9f4349eca9c9af5293d807008371e6e9a42c16d` |
| PRD | `5c93f6a3a72e639e0cf835518f2ef5e03680b3b500c53734e3478cdd59448212` |
| current-product-status.md | `014243c9fc34ad4a7c77028685c82edcfba8ef8e2a4fcff64ed0479f728d4482` |

Связь с неизменным round223 source acceptance:
`c6e9d0bed5e019e1a36570d82d4121e53d01f5aca420791a9b2aee3ec41013fe`.
Его9/0 не переносится на будущую реализацию Reader. Лично прочитаны полные
текущие Reader.h/cpp и Memory.h, Guard check/revoke/blockWrites, Tree readBlock
и v1 FilesTests reader lifetime/cancel/failure/admission участки как основание
оценки reuse и совместимости, не как proof новой реализации.

## Независимая оценка после генерации

Уточнение main до реализации включено в P6: scope состоит из шести файлов —
Tree.h/cpp, Reader.h/cpp, TreeTests.cpp, OwnerTests.cpp. Управляемые native
fault cuts переиспользуют уже существующий interposed REAL Files/Tree в
OwnerTests, не новый backend. Warm block0 cache → Seek0 → отказ следующего
native read при cross-block запросе позволяет задать отказ после копирования
cached prefix без guessed ciphertext ordinals. TreeTests содержит обычные COM,
seek/pins/old-root/release/CopyTo случаи, v1 FilesTests остаётся неизменным.
CMake изменений не ожидается; зависимость не добавляется без факта сборочного
требования и отдельной оценки. Source acceptance всё ещё отсутствует.

Ниже основания отметок — письменные требования и лично прочитанный действующий
путь, а не будущие результаты тестов:

| Пункт | Независимое основание достаточности требований |
| --- | --- |
| CHK001 | P1/P6 прямо ограничивают этап Reader; plan Step3 разделяет reader/seek и writer/resize, Step5–7 оставляют schema/consumers/migration/acceptance. T116–T118 открыты. |
| CHK002 | P1/P3 задают private Tree proof и тот же Owner; packed §§1–2 запрещает serialized/caller-derived proof и ownership-gap reuse. Current Tree удерживает actual Owner. |
| CHK003 | P1 сохраняет явный v1 factory, packed §§1/6.1 отдельно определяют representation; ошибка packed не выбирает старый decoder. |
| CHK004 | P1 и нынешний Reader.h уже отделяют verified bytes от account/package/upload/delete полномочий; packed §6.1 требует отдельный strict protected stamp до consumers. |
| CHK005 | P2/P5/P6 и packed §2 задают actual release, не counter-only lifetime. Files.cpp revokeWrites меняет writable, blockWrites устанавливает recoveryRequired fault: это разные состояния. |
| CHK006 | P2 и Memory.h задают единый CustodyPin admission32 до allocation. Уже живые owner/proof/result pins входят в этот предел;31 Clones сохраняется как v1 regression, не новая гарантия packed32+owners. |
| CHK007 | Уточнение P2 устраняет uncharged COM object: reuse существующего CustodyAllocator, exact fixed size, shared state/control, bounded cache/buffer. Нормы64MiB/4KiB/2MiB не повышаются. |
| CHK008 | P3/P6 уточняют отказ до effects и exact first native/alloc mapping; действующие Guard check и readError показывают совместимые outcome classes без нового recovery path. Подробнее ниже. |
| CHK009 | P3 checkRead не rereads closure/HEAD и не создаёт proof; Guard check относится к physical Owner. Поэтому новая HEAD publication не инвалидирует old pinned logical snapshot сама по себе. |
| CHK010 | P2/P4 неизменный state удерживает единственный exact proof/root/epoch; state+block ключ однозначен, capacity≤256KiB и clear/release wipe заданы нынешним ReadCache и packed §§3–4. |
| CHK011 | P3/P4/P6 требуют status перед cache и завершением; readError получает fault, даже если bytes уже cached. Packed §4 явно не требует fresh disk cache-hit и запрещает observed-fault bypass. |
| CHK012 | P5 задаёт got0/wipe/no cursor advance/shared sticky fault; действующий Reader::Read уже имеет reject и финальную status границу. Новый native cross-block cut даёт объективный контрпример. |
| CHK013 | P3/P5 плюс existing Read min(length-cursor,request) задают EOF/zero semantics отдельно от fault; Tree readBlock проверяет exact full/short и explicit ZERO; noexcept exception outcome задан. |
| CHK014 | P5 сохраняет существующую checked signed Seek арифметику и unnamed Stat; bounded64GiB snapshot помещается ниже LLONG_MAX, beyond-EOF cursor не становится логическими данными. |
| CHK015 | P2/P3/P5 общий state/failure/cancel и отдельный cursor/pin, без refresh; existing Clone и CAS failure демонстрируют ожидаемую совместимость, не доказательство новых packed веток. |
| CHK016 | P5 и нынешний CopyTo удерживают реальные COM ссылки, bounded/wiped CustodyBytes и освобождают global IO lock перед target Write; progressive read/written accounting отделён от атомарного отказа одного Read. |
| CHK017 | P6 и quickstart §14 перечисляют exact bytes, old roots после eviction и actual-release/reacquire checks, не только successful factory/счётчик pins. Fixtures уже генерируют full/short и compact ZERO. |
| CHK018 | Дополнение P6 задаёт actual next-native cut после cached prefix и Owner blockWrites, metadata allocation/jobs failures: measurable got0/wipe/cursor/all-clone/error outcomes, не inferred PASS. |
| CHK019 | P2/P6 требуют unchanged v1 FilesTests и общие COM methods. Reader/Memory лично прочитаны; allocator для Reader меняет accounting, не decoder/ledger/no-rollback scope. |
| CHK020 | P6 явно требует RED и current identity Release/Debug/полный regression, portable отдельно; Constitution VI и plan Step5–7 запрещают принять приложение по одному примитиву. |

### Точные границы отказа и совместимости

На уровне Reader требования используют прежнее readError: allocationFailed
становится E_OUTOFMEMORY; ненулевой Win32 nativeError — HRESULT_FROM_WIN32
точного nativeError; остальные ошибки чтения — STG_E_READFAULT. Отказ
Guard admission jobs4 не разрешает IO/cache success: при активной операции
Reader он фиксируется общим failure state, shared Clones не продолжают Read.
Factory возвращает неуспех без принятого stream; pin/COM allocation refusal
Clone также не создаёт объект. Нехватка свободного pin не предполагает новую
политику принудительного закрытия всех ещё исправных объектов. Physical
first fault остаётся в Owner; invalid-size/EOF/cached bytes его не заменяют.
Status обрабатывает cancellation и сохраняет первый уже принятый HRESULT,
bad_alloc/native ошибки преобразуются без исключения через noexcept, прочие
неожиданные исключения дают sticky E_UNEXPECTED. Нет retry/empty success.

Writer revoke сам по себе не read fault; Owner blockWrites/observed integrity
fault — read fault. CheckRead не обновляет descriptor по текущим heads и
не переименовывает verified Tree в normal package. Только Read выдаёт caller
plaintext; Stat/Seek/Clone возвращают обычные COM metadata/results, не путь.
CopyTo может уже передать destination успешно прочитанные предыдущие порции:
никакой rollback внешней записи или атомарности всей CopyTo не обещается.
Отказ конкретного Read остаётся got0/wipe/cursor unchanged. Buffers и actual
owner освобождаются после реального завершения, cancellation не закрывает
работающую операцию. Эти границы соответствуют существующим P3/P5/COM methods,
не добавляют новую product policy.

### Сверенный исходный снимок до новых правок

| Источник | SHA-256 |
| --- | --- |
| Reader.h | `d1dc47e71865bd09a67cde2fe281e9be24a92fae690a9a8b2ea90f6f8b6a91b4` |
| Reader.cpp | `59a72176bff303c5abb34a352015a755481766126f8ff7c5c84c04607f7ab7d9` |
| Memory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |
| Tree.h | `edbce5c8939d19601d99330d556925065ba4838d27b3007dc6df9c0cf0ad70bc` |
| Tree.cpp | `dc8f71fd3c5be15068545fcab3b35ff63a02ca62d030681f83ec6922cd212712` |
| TreeTests.cpp | `991f14df6e336134e70dc933295bec7cd72ac0417de4da483451ae9a2b09fb2c` |
| OwnerTests.cpp | `6b097ac7f085d3b1923737181af50e454ba497ec8bcbe1f6dcf0d752206bb210` |
| FilesTests.cpp | `e00d64cf3c4682eb21dce1dbaa5c99d78970c60e3b2aa9e03633ae827b26ffe5` |
| CMakeLists.txt | `34512b061361516a997c0581b6a693d9535d3d5e6893cb2b017a2a061b96e295` |

## Вердикт качества требований

**REQUIREMENTS GATE ACCEPTED:20 checked /0 unchecked; C0/H0/M0.**
Blocking clarification gaps не выявлены. Уточнения памяти и actual fault
матрицы main рассмотрены до implementation; новый human policy/architecture
не требуется. Все пункты имеют ссылки на P1–P6 и действующие нормы. Список
создан unchecked, затем оценён независимым reviewer по явному поручению;
main не ставил отметки. Перед выдачей вердикта список и дополнение перечитаны,
счётчики checked/unchecked подтверждены. Hooks повторно parsed: active0/0.

Это разрешает main пройти следующий implementation шаг при сохранении
остальных действующих gates, но **не source acceptance**. Новая реализация
должна пройти отдельный reviewer-owned source report после source-ready и
terminal exact-SHA execution. Старое round2239/0 не принимает новый Reader.
Полная T116–T118 и Windows цель остаются открытыми. Reviewer создал/изменил
только этот NEW gate; old reports, код/tests/нормы/tasks, VM/Git/GitHub,
install/audio/private inventory/commit/release не менял и не исполнял.

## Последнее уточнение COM перед source edits

Main явно подтвердил прежнюю COM семантику отказов. Clone pin/owned-memory
admission refusal возвращает **STG_E_INSUFFICIENTMEMORY / null output** до
создания объекта и сам по себе **не портит уже исправный shared State**.
Factory admission refusal не выдаёт stream и не уничтожает прежний proof;
ошибка actual Owner check отдельно наблюдается/фиксируется Owner. Ошибки
Read/native/integrity/cancellation/CopyTo allocation фиксируют shared State
и Owner в применимой области, но произвольный admission отказ не становится
новой глобальной политикой poison. Invalid Seek flags/pointers и подобные
ошибки caller сохраняют прежнюю nonpoisoning COM семантику: они не заменяют
уже сохранённый first Owner fault новой ошибкой и не разрешают cached success.

Cursor изменяется только после final status успешного Read. При shared failure
Seek/Read отказывают; требование unchanged cursor доказывается отсутствием
increment на source error paths, а не новым публичным introspection/debug API.
Reader остаётся final; class-specific allocator new/delete могут не именовать
неиспользуемый size parameter. Требования fixed size/accounting остаются;
новый wrapper/base class/abstract Reader не нужен.

Это уточнение согласовано с P2/P3/P5, existing Reader/Memory и CHK007/008/012–016;
новых требований или blocking ambiguities не создаёт. После его независимой
оценки итог остаётся **20/0, C0/H0/M0, REQUIREMENTS GATE ACCEPTED**.
Source acceptance до новой реализации/чтения/исполнения не выдаётся.

## Уточнение CHK019: учёт COM Clone в существующем v1 regression

Main сообщил первый Release Tree PASS35.74s и v1Files FAIL на прежней
строке950 `usedBytes()==cachedCharge`. Это промежуточные результаты main,
не reviewer execution и не current source acceptance. До правки теста
reviewer лично прочитал FilesTests918–1025/1038–1110 и соответствующие
Reader operator new/delete. FilesTests SHA до разрешённого уточнения:
`e00d64cf3c4682eb21dce1dbaa5c99d78970c60e3b2aa9e03633ae827b26ffe5`.

Факт: cachedCharge измерен в945 после первого Read, Clone создаётся в947,
cache-hit Read в949 сохраняет тот же cache/IO count, а950 требует отсутствия
любой новой owned allocation. Теперь требуемый P2 allocator учитывает
фиксированный Reader для каждого Clone: это ожидаемая дополнительная
allocation, не duplicated cache. Поэтому буквальное прежнее ожидание950
противоречит принятому CHK007/P2 и общему64MiB учёту. Его сохранение потребовало
бы снова сделать COM object uncharged, что не допускается требованиями.

**Точечное test-only уточнение принято.** Седьмой файл допустимого source/test
scope — `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp`.
CHK019/P6 «unchanged v1FilesTests» означает сохранение полного поведения и
защитных regression assertions, с этим единственным исключением устаревшего
memory-accounting ожидания в существующем reader/cache/Clone сценарии.
Нормы не меняются, limits не увеличиваются; второй framework/backend и CMake
изменения не требуются. Исторический six-file/unchanged текст выше фиксирует
предыдущее предложение; текущий scope — семь файлов, только accounting delta
в седьмом. Новых checklist items или задач это уточнение не создаёт.

Достаточные условия минимальной правки main:

- Измерить cloneCharge после успешного Clone и потребовать
  `cloneCharge>cachedCharge`, а не разрешить произвольный рост без проверки.
- После warmed Clone Read сохранить exact `usedBytes()==cloneCharge` вместе
  с прежними byte/got/native-read assertions: cache-hit не создаёт новых
  retained content allocations и не заменяется weakened comparison.
- Проверить exact освобождение COM charge при **actual Release/Reset** в
  сопоставимом lifetime. CachedCharge945 нельзя напрямую сравнивать с памятью
  после1092: original stream уже Reset в1068, cache менялся, последний Clone
  освобождает shared State/cache вместе с COM object. Для exact возврата к
  cachedCharge требуется короткая Clone/Reset пара около исходного замера,
  пока original stream/state и тот же cache живы; затем основной retained
  Clone сценарий продолжается в прежнем объёме. Допустима и эквивалентная
  локальная проверка с явно сопоставимыми живыми владельцами. Не создавать
  public introspection API и не сравнивать несопоставимые baseline snapshots.
- Не удалять и не ослаблять последующие private Stat, bytes/full/short/ZERO,
  Seek/EOF/readonly, CopyTo/native MF, old snapshot/cache separation, actual
  retained Clone lifetime, process32/31 concurrent Clones, sticky cancellation,
  failure/wipe и OOM проверки. Итоговая memory baseline проверка сохраняется.
- Новый FilesTests SHA входит в будущий final **seven-source** identity packet;
  прежний FAIL не объявляется PASS. Повторные native Files/Tree/Owner
  Release/Debug и согласованный полный regression требуются на новом снимке.

Согласованность independently подтверждена: accounting assertion меняется
из-за уже принятого product allocation требования, а не для обхода byte,
integrity или native fault regression. При соблюдении указанной lifetime
границы итог требований остаётся **20 checked /0 unchecked, C0/H0/M0,
REQUIREMENTS GATE ACCEPTED**. Конкретная опасность неверного размещения
release comparison устранена письменным условием до правки теста;
неразрешённого requirements blocker нет. Source-ready ещё отсутствует,
source report/acceptance не создавался. Reviewer изменяет только этот gate;
FilesTests и product code сам не правит, VM/tests не выполняет.

Hook YAML после исправления опечатки в первой read-only Ruby invocation
успешно parsed: before_checklist/after_checklist active0/0, hooks не запускались.

## Уточнение CHK007/019/020: доказуемый first-use учёт пустого кэша в Debug

Main сообщил terminal Debug22379: **1/3 PASS, EXIT8** — Owner и Tree
завершились отказом конечного `usedBytes()==before`, Files прошёл. Это реальный
неуспешный прогон, не транспортный отказ и не source acceptance. Release30311
41/41 и portable55088 39/39 не подменяют его. На момент этой оценки actual
delta ещё не измерена, поэтому причина рассматривается как проверяемая
гипотеза, а не подтверждённая утечка или готовое исправление.

Reviewer лично перечитал действующие Reader.cpp14–27/45–48/253–268,
TreeTests main1292–1347 и `emptyProxyCharge`1128–1133, OwnerTests main868–941,
Memory.h и текущий append round224 в validation-2026-10-02.md. Исходные
Reader/TreeTests/OwnerTests SHA на момент оценки совпадают с source-ready:
Reader.cpp `0d38daf7ce709d112ca14edb3e87cb7a4a774c562ef48984c2ef91ad265977b9`,
TreeTests `c7715f8e98c79c05edee71f56c2a8d80f8a001eae892dcd52fefe3a7f659ecca`,
OwnerTests `10c7f58885f3ee4a44d77f50edf1c8e4deb76c753596bfbd1d618c80413cc4d1`.
Неизменное прежнее чтение норм переиспользовано после уже проведённой fresh
identity проверки; новые нормы или вопросы о product policy не требуются.

В коде существует один process-static `ReadCache`, содержащий пустой
`CustodyBytes`. Factory вызывает `cache()` до создания ReaderState, а
уничтожение последнего stream освобождает state/Owner и очищает принадлежащие
state plaintext bytes, но не уничтожает сам process-static объект. Поэтому
начальный замер до первого Reader и конечный замер после Reader могут иметь
разные живые фиксированные объекты. При Debug STL возможная allocator charge
пустого vector должна быть **измерена и точно подтверждена**, а не исключена
из учёта или разрешена как произвольная погрешность. Это согласуется с P2/P4
и CHK007: постоянный кэш по-прежнему учитывается в существующих64MiB.

**Предложенное test-only уточнение принято до правок.** Разрешены только
TreeTests.cpp и OwnerTests.cpp внутри уже принятой области семи файлов,
без изменений product code, CMake, allocator, limits или других нормативных
артефактов. Достаточные и обязательные условия setup:

1. До first-use warmup измерить `usedBytes()` вне lifetime временного пустого
   `CustodyBytes`; внутри отдельного scope создать именно пустой vector и
   вычислить его фактическую charge. После выхода из scope потребовать
   **точный возврат** к исходному замеру. Не использовать заданные16B, число
   из предыдущего failed run, размер непустого vector или допускаемый диапазон.
2. Затем в отдельном scope выполнить реальный generated empty Owner →
   `Tree::verify` → packed `openProtectedCustodyReader`, проверить успешный
   результат/пустую длину и нормальную семантику пустого чтения. Освободить
   результат, stream, proof, Owner и fixture **фактически**, до последующего
   замера. Не вызывать внутренний cache напрямую и не заменять настоящие
   Reader/Files/Tree заглушкой, счётчиком или новым тестовым backend.
3. После полной очистки warmup потребовать **точное равенство** наблюдаемого
   process charge исходному замеру плюс independently measured empty-vector
   charge. Это assertion проверяет гипотезу, не принимает любую остаточную
   память. При нулевой measured charge в Release также выполнить warmup и
   точное сравнение; не пропускать контрольный случай по условию `proxy==0`.
4. Только после успешного точного сравнения взять прежний основной `before`
   для всех последующих случаев. **Оригинальные конечные равенства** памяти
   оставить, включая оба Owner равенства, all-pins/all-jobs admission и все
   fault/bytes/wipe/Clone/actual-release проверки. Измерение постоянного
   пустого объекта не разрешает retained plaintext/capacity/state/COM/Owner
   утечки. Не переопределять baseline после failing test, не вычитать
   наблюдённый конечный избыток и не вводить tolerance либо больший лимит.
5. Если warmup delta отличается от independently measured proxy или
   последующие конечные сравнения всё ещё отказывают, расследовать отказ,
   не подбирать поправку до PASS. Ни это requirements approval, ни старые
   Release результаты не доказывают причину Debug отказа. Обновлённые два
   test SHA войдут в новый seven-source packet; повторить согласованные
   native Release/Debug Tree+Owner+Files и полный regression. Source review
   возобновляется на новом снимке, старый Debug FAIL сохраняется в evidence.

Вердикт независимой оценки: **REQUIREMENTS CLARIFICATION ACCEPTED,
20 checked /0 unchecked, C0/H0/M0**. CHK007/019/020 не ослаблены: проверка
стала сравнивать одинаковые живые объекты при доказуемом точном учёте
дополнительного process-static объекта. Новых checklist items, полномочий
adoption или задач это не создаёт. Это разрешает main только описанную
test-setup правку и следующие проверки; **source acceptance не выдана**,
Debug остаётся неуспешным до новых terminal receipts. Reviewer изменил
только этот gate; source/tests, нормы/tasks, старые отчёты, VM/Git/GitHub,
installation/audio/private inventory/commit/release не изменял и не исполнял.
