# Независимый requirements-quality gate: packed live writer / Step 3

Дата: 2026-10-04. Reviewer: независимый рецензент текущего продолжения F200;
`code-reviewer` прочитан лично. Отметки ниже принадлежат только reviewer.

## Решение

**Scoped APPROVED по качеству требований: CRITICAL=0 / HIGH=0;
14 checked / 0 unchecked.** Принятый packed-контракт вместе с точными
техническими ограничениями предложения основного агента достаточен для следующего
worker-only этапа открытой T116. Обязательное новое продуктовое уточнение
перед его синтетическими RED-тестами не найдено. Это не source/runtime PASS,
не закрытие Step 3/T116 и не замена текущего scoped analyze/остальных gates.

Канонический checkout: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Проверенные нормы и исходники идентифицированы SHA-256 ниже.

Область: persistent packed tree logical Write/SetSize/checkpoint;
private `inherited_live` proof того же непрерывного Owner; bounded changed-path
проверка с exact unchanged-child refs; paired HEAD readback; старые pinned
readers; ZERO/shrink/grow/short tail; admission и классификация отказов.

Допустим первый **неполный prerequisite**: один FULL sequential append block
262144B при aligned logical EOF, не более 1 DATA + 3 NODE,
candidate=exact selected base+1. Partial/unaligned Write, rewrite, SetSize и tail
не должны изображаться поддержанными этим первым API. Их дальнейшая реализация
и проверки остаются обязательными для полной Step 3. Никакого сужения T116.

Вне допуска: adoption в приложение; historical metadata-root restoration,
package/migration schemas и consumers; migration/GC; real inventory;
hardware/audio/installed/physical/signing/release. Full historical closures
§6.1 остаются обязательными до их собственного adoption/GC gate, но не
являются предпосылкой этого изолированного worker-only шага.

## Лично прочитанное и актуальность

Прочитаны root AGENTS/индекс guidance, code-reviewer, codex-worktrees,
spec-kit-flow, product-gates и применимая validation guidance;
spec.md, plan.md, tasks.md, quickstart.md и constitution целиком;
packed contract целиком (ранее лично прочитанная неизменная первая часть
сопоставлена по SHA); data-model §13, применимые commit/resource/async нормы
базового local-custody contract, storage/claim границы PRD и current status.
Прочитаны актуальное продолжение packed amendment review, прежний tree gate,
актуальный итог tree-source report; исходники Tree/Owner/Guard/admission.

Исторические REQUEST CHANGES H1/H2/M1 в amendment report заменены его явным
последующим APPROVED C0/H0/M0. Их нормативные исправления присутствуют:
checked base+1, selected-base peer, expected envelope SHA всех NODE/root.
Прежний tree gate намеренно исключал writer и потому не принимается за его
готовность. Исторический общий запрет Phase0 в plan заменён разделом
«Актуальный порядок: независимый срез хранения»; clock/T119 не зависимость
этого этапа. T115 checked; T116/T117/T118 остаются unchecked.

Пять существующих нормативных checklists имеют текущие счётчики
requirements22/0, audio24/0, advanced14/0, security27/0, ux25/0 — **112/0**.
Их отметки не изменены; это качество требований, не проверка приложения.
Итог прежнего tree-source review **17/1**, H3 CLOSED/source C0/H0/M0,
сохранён: engaged-snapshot metadata worker return fault остаётся точной
необязательной границей исполнения, не новым HIGH и не условием этого gate.
Ни прежние receipts main, ни их runtime attribution здесь не расширены.

## Reviewer-owned требования

`[X]` подтверждает полноту, однозначность, измеримость и согласованность
требования в указанной области. Не означает, что будущий тест уже прошёл.
«Предложение» ниже — техническое предложение основного агента в текущем
продолжении. Оно согласовано с уже принятым spec/contract и не является новым
разрешением пользователя или исключением из норм. Конкретный technical scope,
FULL-block API, exact pair, preallocated result и Guard extension предложены
основным агентом как implementation constraints. Они не вводят новую норму;
точное сравнение прежней пары и подготовка результата не приписываются
дословно старому контракту, а оценены на согласованность с его continuous-owner,
admission и ACK нормами.

- [X] LW001 Определены ли отдельная worker-only область, первый FULL append prerequisite и запрет принять по нему всю Step 3/T116? Доказательства: FR-012; plan, packed dependency order Steps 3–7; tasks T116–T118; quickstart §14; предложение.
- [X] LW002 Замкнута ли provenance нового root: только от immutable private Tree proof того же Owner/epoch/native identity/container, без публичных raw descriptors/from-fields/verified flags? Доказательства: packed §§1–2, §4:139–145; data-model §13; Tree.h:17–39; предложение. Decode descriptor сам по себе не authority.
- [X] LW003 Определён ли один Guard с тем же State mutex, одним admitted job и strong Owner через DPAPI, append/flush/diff, оба readback этапа, catch и result; запрещены ли второй mutex, reopen и nested lock-taking public IO? Доказательства: packed §2, §5; Owner.h:39–54; Files.cpp:706–758; предложение.
- [X] LW004 Требуется ли под этим Guard перечитать/decode обе HEAD и сравнить exact прежнюю авторизованную пару по slots, а не только highest generation; stale/nonselected/foreign base отказывает до append/head effects? Доказательства: packed §5:166–169; quickstart Generation/peer; immutable Tree heads_; предложение. Pre-I/O refusal означает до append/head I/O, не запрет необходимых проверочных чтений.
- [X] LW005 Однозначны ли checked candidate=selected base+1, u64/length/offset exhaustion, target=(generation−1)%2 и empty-g1 tie slot0? Доказательства: packed §§3,5; quickstart Generation/peer. Jump, wrong target и overflow не нормализуются.
- [X] LW006 Ограничен ли structural diff разрешёнными Write/SetSize диапазонами, с точным равенством каждого unchanged Ref64, context/level/base/version/tail/extent правилами; запрещены ли full scan при checkpoint и flat per-block structures? Доказательства: packed §4:127–155, §3; quickstart Live delta; предложение.
- [X] LW007 Заданы ли append-only immutable DATA/children/parents после actual EOF, первый flush и независимый disk readback всех новых records до HEAD; expected envelope length/SHA до DPAPI, затем typed context/checksum? Доказательства: packed §3:112–118, §5:170–173; quickstart NODE/root Ref. Writer copies освобождаются до независимых чтений, orphan tail не truncate/reuse.
- [X] LW008 Требует ли committed ACK второй flush, positioned readback обеих HEAD как exact candidate и exact selected base (не lower peer), соседство/slots, повторную проверку новых records и confinement до выпуска private live proof? Доказательства: packed §5:174–180, §2; quickstart Cuts/async. Published одной cell не logical ACK.
- [X] LW009 Определены ли admission proof pin и подготовка потенциально выделяющего память result/proof до публикации, отсутствие преждевременной выдачи authority и удержание Guard/custody при классификации исключения; сохраняется ли первый exact error/nativeError без зависимости от optional NRVO? Доказательства: packed §§2,5–6; base contract §5; Guard::reject/State::fail; предложение. Будущий return путь требует собственного source/test proof, не переноса старого runtime PASS.
- [X] LW010 Сохраняют ли старые pinned readers/Clone immutable прежний root и actual Owner после нового commit/writer release, при независимых cursor и без отмены sticky fault? Доказательства: packed §§2,4,6; Tree.h const heads_/selected_; quickstart Read/Clone/seek. Старый root может оставаться пригодным для чтения, но не для следующей записи.
- [X] LW011 Полны ли ZERO/shrink/grow/tail нормы: explicit extension только ZERO; новые beyond-EOF refs EMPTY по §4; short DATA exact; partial shrink tail переписывается; grow не раскрывает отрезанные bytes; старые roots неизменны? Доказательства: packed §4:127–145; base contract §§3,5; quickstart §§12,14. ZERO не заменяет missing/corrupt DATA; большой ZERO range не разворачивается в массив blocks.
- [X] LW012 Измеримы ли admission owned64MiB/cache2MiB/dirty4/pins32/jobs4 и ≤4KiB stamp, FULL append ≤1DATA+3NODE/284KiB envelope budget; учитываются ли retained result/cipher/plain/control storage, physical peak/orphans и free reserve без wall-time promise? Доказательства: packed §§4,6; base contract §5; CustodyMemory.h; PRD local buffer policy; предложение. Native DPAPI/MF allocation не выдаётся за доказанную owned quota.
- [X] LW013 Однозначны ли outcome границы: до первой HEAD-write attempt not_committed, с начала HEAD I/O failure ambiguous/sticky, даже если cell write succeeded; cancel/stale UI не откатывает disk fact, fault блокирует normal effects/новый commit/GC до reconciliation? Доказательства: packed §5:173–192; base contract §5; quickstart Cuts/async. Артефакты и фактические работающие owners не освобождаются таймером.
- [X] LW014 Есть ли ограниченная synthetic-first проверочная матрица с отдельным будущим source acceptance, без production fault switch, application adoption или требования полного v1 gate? Доказательства: packed §7; quickstart §14; plan dependency order; предложение; матрица ниже. Непроведённый тест не становится PASS.

## Минимальный путь реализации, не готовая реализация

Tree уже хранит private immutable `heads_[2]`, selected slot и actual Owner;
это пригодная основа proof, а не повод вводить второй тип публичной authority.
Private trusted transition может подготовить следующий Tree и выдавать его
только после полного ACK. Зарезервированное staging/storage до ACK ещё не proof.

Guard уже удерживает нужные owner/job/State mutex. Его узкое private расширение
append/flush/publish должно переиспользовать существующие confinement,
positioned transfer, bounds, reserve и sticky failure механизмы.
Нынешние public physical методы берут собственный job/mutex; вызов их из
удержанного Guard не соответствует этому допуску. Private операция не должна
повторять backend или обходить его проверки. Physical `publishHead()` очищает
свой headAttempted после readback одной cell (Files.cpp:994–1038); logical worker
обязан сохранять свою ambiguity boundary до **всей** проверки пары/records/result.

Резервировать result/proof pin и все потенциально бросающие конструкции
результата до HEAD write; проверять реальный move/error-return путь, не полагаться
на NRVO. Catch классифицирует ошибку при ещё удержанных Guard/owner/job.
Не вызывать lock-taking `blockWrites()` из-под того же mutex вместо private reject.
Отказ job/pin admission до операции не доказывает corruption: нет I/O/нового
proof/ACK; уже замеченный fault нельзя заменить quota error или normal result.

## Минимальные будущие синтетические доказательства

Это требования к проверке main, **в этом review ничего не исполнялось**.

| Этап | Достаточное ограниченное доказательство |
| --- | --- |
| FULL append prerequisite | Empty-g1 → g2 и следующий блок; переходы radix64/4096 и последний допустимый block у 64GiB через компактную синтетическую base fixture; ≤1DATA+3NODE, exact bytes/root/pair, без giant allocation. Upper bound отвергается до append/head. |
| Authority/freshness | Forged/raw/foreign proof недоступен/отвергнут; валидная другая пара с той же highest generation, stale Tree после нового commit, nonselected base, wrong target/peer и generation overflow не вызывают append/head writes. |
| Changed paths | Попытка заменить sibling/unchanged subtree на другой structurally valid Ref; unauthorized range/version/level/base/tail/extent; expected NODE/root envelope SHA mismatch при самосогласованном inner checksum — отказ без proof/ACK. |
| Publication cuts | Actual worker cuts на records write/flush/первом readback, затем HEAD write/flush/обеих cells/повторном records readback/final check/result. Pre-head not_committed; post-head ambiguous. Writer copies не используются как readback; wrong lower-peer pair не ACK. |
| Ownership/error | Public physical операция не interleave в Guard; exception ловится до release lock/job/owner; first exact error/nativeError сохранён; последующий commit/read не скрывает fault. Job exhaustion не начинает IO; pin/result-memory exhaustion не начинает HEAD publication. Retained results остаются charged/pinned до уничтожения. |
| Старые readers | Два/более последовательных commits вытесняют прежний root из обеих HEAD, но прежний pinned Tree/Clone читает прежние bytes; writer release не закрывает actual HANDLE. Loss/reacquire не переносит live proof на новый Owner. |
| Остальная Step 3 | Partial Write/seek/rewrite, Flush/checkpoint tail, SetSize shrink→grow ZERO, partial shrink tail, большие ZERO ranges, EOF и short read; грязные groups/admission ограничены. Эти кейсы не закрываются FULL append prerequisite. |
| Detection-time/bounds | Unchanged old DATA не сканируется на каждый live checkpoint; observed corruption при fresh read/full reopen sticky и без normal result. Учёт records/paths/memory, а не заявление sustained capture по big-O/одному лучшему времени. |

## Когда допуск больше не применим

Новых unresolved C/H требований не найдено. Следующий source acceptance
остаётся blocked, если writer принимает caller descriptors, сверяет только
generation вместо exact previous pair, не доказывает unchanged refs, использует
lower peer для ACK, отпускает Guard до catch/result, допускает allocation/pin
после publication без безопасной классификации, считает одну physical cell
logical ACK или выдаёт unsupported tail/SetSize за реализованную Step 3.
Это критерии соответствия уже принятым требованиям, не новые замечания к ним.
Изменение указанных границ требует повторного scoped review; приложение,
metadata integration/migration/GC/T118 сохраняют собственные последующие gates.

## SHA-256 проверенного снимка

Пути в таблице относительно canonical checkout. Hash report не включён в сам
report, чтобы не создавать self-hash. Guidance/source чтение — read-only;
reviewer lane: requirements review внутри high-risk-product + docs-only report.

| Файл | SHA-256 |
| --- | --- |
| specs/200-windows-desktop-app/spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| specs/200-windows-desktop-app/plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| specs/200-windows-desktop-app/tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| specs/200-windows-desktop-app/quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |
| specs/200-windows-desktop-app/data-model.md | `ed7da763ddaa281f7cca2d05b9f4349eca9c9af5293d807008371e6e9a42c16d` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `7209dbfb5a8ba40e0f3afe9032a6bc8d15c2a70b71e54868b518a6fe5edcd586` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `ac096cb8521e1c818b70c0a8147f4b93661b434fa117068149286ea4c7412b75` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `b29146e86800531c0ef3447fb32bd7846fc17214c418abe5bf5d2e83a7af1825` |
| apps/windows/RecApp/Storage/ProtectedCustodyMemory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |
| specs/200-windows-desktop-app/checklists/review-2026-10-03-packed-tree-source.md (не изменён) | `ebe1cab3f9621a316fb46fa7c16c193d0b9b534bd8a32be37d872cc4205db45d` |

При завершении чтения замечена чужая shared правка
`specs/200-windows-desktop-app/validation-2026-10-02.md`; reviewer её не менял,
не откатывал и не использовал как новое runtime доказательство.
Единственная reviewer-owned запись — этот NEW файл. Source/spec/plan/tasks/
feature/старый report/GitHub/VM не изменялись; builds/tests/commit/release не
выполнялись. После записи перечитаны критерии и подсчитаны **14/0**.

## Round250 — stage-only diagnostics for existing full owner test

**Scoped requirements/analyze APPROVED: C0/H0/M0/L0** for the proposed
diagnostic-only edit, not its as-yet unsubmitted source delta. Existing LW001–014
remain **14 checked / 0 unchecked**, requirements quality only; no marker changed.
Personally read the current test main and logicalAppendFaults flow. Actual file
is `apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp`
(not ContractTests), SHA-256
`ca4e041ca15b978e6573e3473fe8ac003b166ac313bbc46c54a643bfbcef3205`.

The seven existing main calls at lines1318–1324 cover default full append,
short append(3), tail(5), interior(262144), shrink(1), grow(1), empty(1).
Each runs its existing synthetic setup, native production path and fault-cut
assertions. The proposal may add one fixed metadata-only stderr stage label
immediately before each call, using existing stdio, without content/path/ID/
key/URL/exception data. A label means only entry into that stage, not completion
or PASS. No new logger, timer, diagnostics framework or production seam is needed.

Preserve all seven calls, arguments, ordering, fault loops and assertions,
existing final result/exit behavior, native DPAPI/dependencies, resource/cache/
pin/job/disk budgets, CMake registration and the current external300s limit.
Do not split/remove/skip cases, promote a command-line subset to full acceptance,
replace DPAPI with a successful fake, or raise a timeout to turn failure green.
Fixed stage output is compatible with FR021 metadata-only evidence and T116/
quickstart§12/14 diagnostics; it changes observability, not custody authority,
durability, bounds, migration rights or the approved technical design.

Main reports run76270 remains LIVE at the existing broad stage label, with
rebuild0, source17 manifest and a completed exact-byte2MiB cadence around
245–313ms/checkpoint. Reviewer did not inspect or operate the native process.
This is not terminal full-test evidence or a causal diagnosis of a timeout.
Do not edit its frozen mirrored executable or start a competing owner test while
it runs. If/when this run terminates, retain the actual timeout/failure/pending
receipt. A separately frozen diagnostic rebuild must have its own source/EXE/
manifest and result; printed stages or a narrow PASS cannot close the full test.
Instrumentation timing is not a performance acceptance proof.

Fresh normative inputs: spec
`b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658`,
tasks `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`;
plan `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c`,
quickstart `5cc51e712a6b1543771aab46ba922b3f90768f177e0e274d548df4a8eb6681d2`,
packed contract `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5`,
Constitution7.1.0 `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`.
CMake read/hash `0b2c7322965c523df5fc5a98aabe94900fc11acfcf77bbfbf9298c94ffa68202`.
Full project-local checklist/analyze instructions and relevant risk/product/
privacy/validation guidance personally read in the current Round250 safety
review; disabled commit hooks remain disabled. No new normative gap or task
coverage change; existing T116 owns this bounded generated-data diagnostic.

Pre-append report hash
`7fb4f75180745620091241fd569e47677efeda113080f3b452155bca84181a5f`.
Only this reviewer-owned appendix changed. No test/product/norm/task/marker/
Git/GitHub/VM/build/audio/profile/user-record writes or executions. T116 full
source/runtime acceptance, T117/T118, installed T119/T097 and the separate
Round250 working-profile safety NO-GO are not closed by this approval.
