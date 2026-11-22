# Независимая проверка исходников: первый FULL packed append / T116

Дата: 2026-10-04. Отчёт и отметки принадлежат независимому проверяющему.
Область — high-risk-product, изолированный worker-only prerequisite T116;
единственная разрешённая запись проверяющего — этот новый файл.

## Начальный статус — до сигнала готовности исходников

**Допуск по требованиям применим. Вердикт по исходникам не вынесен.**
Проверка исходников и тестовых доказательств начинается только после явного
сигнала основного агента о готовности. На начальном этапе **0 checked / 9 unchecked**:
это ожидающая source-проверка, не новые замечания к требованиям и не запрет
на реализацию уже допущенного этапа.

Канонический checkout:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
Лично проверенный HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

Список требований `review-2026-10-04-packed-live-writer-gate.md` лично
перечитан целиком. SHA-256 совпал с переданным утверждённым снимком:
`7fb4f75180745620091241fd569e47677efeda113080f3b452155bca84181a5f`.
В нём **14 checked / 0 unchecked, scoped CRITICAL=0 / HIGH=0**. Его допуск
прямо включает первый FULL sequential append block 262144B при aligned EOF
на existing private Tree proof с тем же Owner/Guard. Нового разрыва
требований для этой области не найдено.

Root AGENTS, guidance index, code-reviewer и применимые spec-kit-flow,
codex-worktrees/product-gates перечитаны. Ранее прочитанные активные артефакты
сверены по текущим SHA; packed-контракт и применимые актуальные разделы
spec/plan/tasks/quickstart проверены повторно. Исторические Phase0 ограничения
не отменяют явно принятого независимого storage-порядка.

Техническое предложение основного агента не является новым разрешением
владельца. Проверка не расширяет допуск до partial/unaligned Write, rewrite,
SetSize, short tail, metadata integration, migration/GC или adoption в
приложение. Полная Step 3 и T116–T118 остаются открытыми; hardware, audio,
installed package, доступность, подпись и выпуск здесь не принимаются.

## Ожидающие критерии проверки исходников

Каждый пункт отмечается только после чтения готовых исходников и конкретных
доказательств. До сигнала готовности все пункты оставлены неподтверждёнными.

- [X] LWS001 Закрытая authority: новый proof происходит только от private доказанного Tree того же непрерывного Owner; нет caller descriptor/root/verified flag. Exact прежняя пара перечитывается под Guard; stale/nonselected/foreign base отказывает до append/head effects.
- [X] LWS002 Один admitted job, strong Owner и прежний State mutex охватывают подготовку, DPAPI, native IO, оба readback этапа, catch и классификацию результата. Нет nested public lock-taking IO, второго backend/mutex или reopen; первый exact error/nativeError сохраняется.
- [X] LWS003 API явно ограничен одним FULL block при aligned EOF; checked base+1, slot formula, length/offset exhaustion и 64GiB edge соблюдены. Не более 1 DATA + 3 NODE/284KiB append, без flat индекса или N-sized bitmap.
- [X] LWS004 Bounded structural diff проверяет точное равенство всех unchanged Ref64 и разрешённость единственной changed позиции. Сохранены context/level/base/version/tail/extent и expected envelope SHA до decode; old DATA не сканируется целиком на checkpoint.
- [X] LWS005 Native append/flush/publish переиспользует confinement, positioned IO, bounds/reserve и sticky failure существующего backend. Новые records после actual EOF, orphan tail не переиспользуется; первый flush и независимый readback выполняются без writer plaintext/cipher copies.
- [X] LWS006 Потенциально бросающие result/proof конструкции и pin admission подготовлены до HEAD publication; provisional authority не выдаётся. Move/error-return не опирается на optional NRVO, отказ сохраняет реальные custody/lock/job и charged retained result.
- [X] LWS007 До HEAD-write attempt отказ not_committed; с первой попытки до полного ACK отказ ambiguous/sticky. После второго flush перечитаны обе HEAD как exact candidate и exact selected base с соседством/slots, повторно проверены новые records/confinement; одна physical cell не logical ACK.
- [X] LWS008 Старый pinned Tree остаётся immutable/readable после нескольких commit и writer release; actual Owner/HANDLE не закрывается преждевременно. Ownership gap не переносит live proof, observed fault не маскируется quota/normal result.
- [X] LWS009 Тесты проверяют actual worker, а не заменяющий алгоритм: sequential/radix/upper bound, exact-pair/stale/unchanged-child substitution, publication cuts, admission/error/old readers. Portable model и native исполнение различены; receipts привязаны к текущим исходникам и не принимают installed/full T116.

## Снимок нормативных артефактов

| Файл | SHA-256 |
| --- | --- |
| spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| contracts/windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |
| data-model.md | `ed7da763ddaa281f7cca2d05b9f4349eca9c9af5293d807008371e6e9a42c16d` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Независимый проверяющий не менял чужие shared правки validation/report,
код, spec/plan/tasks/feature, Git/GitHub/VM; builds/tests/install/microphone/
commit/release не выполнялись. Source-ready сигнал на момент этой записи
не получен; никаких source/runtime PASS эта запись не содержит.

## Проверка первого source-ready снимка

Получен явный сигнал source-ready для пяти изменённых файлов. Перечитаны
их фактические diff и полные Tree/Owner declarations/реализация Tree; прослежены
Guard/State, реиспользуемые native методы, format/codec checks и вызывающие
тесты. SHA требований остался прежним. HEAD не изменён.

**Подтверждённых дефектов алгоритма CRITICAL/HIGH на этом снимке не найдено.
Полный source acceptance пока НЕ выдан: 8 checked / 1 unchecked.**
LWS001–008 отмечены по статическому чтению, не по утверждению, что fault tests
прошли. LWS009 остаётся открытым по конкретной недостаточности новых тестов.

### Прямые доказательства исходников

- Authority/freshness: Tree.h private constructor/immutable `heads_`,
  Tree.cpp:114–145 удерживает существующий Owner, сравнивает обе exact
  дескрипторные ячейки с private парой и проверяет selected slot до append.
  Caller задаёт только bytes, не root или generation.
- Один Guard: Tree.cpp:119 расположен вне try и остаётся жив в catch/return;
  Owner.h Guard держит owner/job/тот же State mutex. Files.cpp:759–789
  использует private Locked методы; public методы 932–1111 используют те же
  реализации, а не второй backend. Native `State::fail` сохраняет первый
  fault/nativeError. Admission refusal не очищает состояние fault.
- Bounds/diff: Tree.cpp:131–145 rejects unsupported length/tail/max generation;
  153–185 читает не более трёх base nodes, включая decode всех 64 siblings.
  196–227 append строит ровно четыре records после actual EOF и ограничивает
  их общий span. 230–252 дважды сверяет decoded child с changed ref либо
  exact прежним 64B sibling; `openReferenced` проверяет expected envelope SHA
  перед decrypt/context/body checks. Старые DATA на checkpoint не сканируются.
- Copies/readbacks: новые `body`/sealed writer buffers выходят из своих
  scopes до первого validate. `prior` содержит только authenticated BASE
  ref bodies, необходимые для diff, не новые readback substitutes.
  Caller input остаётся caller-owned входом API; новая worker plaintext copy
  для сравнительного readback не сохраняется. Первый flush предшествует
  независимым positioned reads. После publish scope HEAD writer copies также
  уничтожены до logical pair readback.
- Result/admission: prospective Tree/pin и оба charged shared ownership
  allocations создаются в `makeProof` до публикации. `PackedTreeCommit`
  содержит только shared_ptr/scalars, поэтому его copy/move/error return
  не требуют нового heap storage и не зависят от NRVO. `next` не выходит
  наружу до полного ACK; после отказа base lease удерживает actual Owner.
  Внутренние native allocations этим доказательством не принимаются.
- ACK/outcome: Tree.cpp:274–284 сохраняет собственный logical `headStarted`
  и не использует очищенный physical `headAttempted` как полный ACK.
  Физическая публикация возвращает published/ambiguous/notPublished;
  обе HEAD затем сверяются с candidate/exact selected base, соседством и
  slots. Второй validate проверяет новые records и confinement перед выдачей
  snapshot. Bad-allocation catch классифицирует результат под удержанным Guard.
- Old readers: immutable `heads_`/selected и strong Owner старого Tree
  не заменяются при новом commit. Новый Tree имеет отдельный pin;
  readBlock использует private прежний descriptor и проверяет sticky state.
  Native state/HANDLE принадлежат shared Owner, не временному writer result.

### LWS009 — чего ещё не доказывает первый тестовый diff

`liveFullBlocks()` (TreeTests.cpp:259–287 в снимке ниже) вызывает actual
`appendFullBlock`, проверяет g1→g2→g3→g4, bytes/selected slots/append span,
старый g2 reader после вытеснения из обеих HEAD и stale-base refusal.
Это правильный начальный тест, но не полная согласованная fault/bounds матрица.

Ещё не представлены целевые native тесты actual append worker на radix64/
4096/последний допустимый block и limit/overflow, валидную иную exact pair
с той же highest generation, unchanged-sibling substitution, отказ на
records/flush/первом readback, HEAD write/flush/обеих HEAD/втором readback,
pin/job/prospective-result memory exhaustion и сохранение lease/first error.
Старые tests cold verify/physical publish/return budgets сами по себе не
исполняют эти новые logical commit ветки и не закрывают LWS009.

Сообщение main о RED `55099 EXIT1 C2039` — сообщённое им доказательство
отсутствия нового API в старом продукте, не лично исполненный reviewer test.
Сборки/26270/Windows Release, заявленные как текущие intentions/processes,
не приняты за PASS; terminal receipts ещё не прочитаны. Reviewer не запускал
код/тесты/VM и не ждёт полной T116 runtime матрицы: открыта только ограниченная
проверка этого prerequisite. Для следующей проверки нужны актуальные
test/source hashes и терминальные целевые результаты main.

### SHA-256 первого source-ready снимка

| Путь относительно canonical checkout | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `a7f44c1c5e54286ec6427301e091444b81f860bf34eb5ebb73b2a2ddc66ce8a4` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `e0a0841d392ffd63386b9685ab890904023763a04b8e66b99fecadcd99288696` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `99dee259444c8a552d3e759e91e10a5a301d38991bfa655ebb90e5abb03922ed` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `9fdd3ed413ca206d614cc48f336187e573e9c5f981ccaa58551caf6031aed7cf` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | `64e01cd39db67e8075790a8aaa2fde9da201ee3277ffe8bdfba48c4319ab5f2f` |

Чужие правки продолжают сохраняться. Единственная запись reviewer — этот
report. Итог перечитан: **8 checked / 1 unchecked (LWS009)**. Это ни полная
Step3/T116, ни app parity, installed acceptance или разрешение выпуска.

## Source-ready продолжение: два расширенных тестовых файла

Четыре product SHA из предыдущего снимка лично сверены повторно и не
изменились. Теперь в область чтения входит шестой файл —
`ProtectedPackedCustodyOwnerTests.cpp`; его изменение test-only, не новое
разрешение на backend/adoption. Перечитаны оба test diff, существующие
TU-local wrappers, новый `logicalAppendFaults`, fixtures и CMake routing.

**Новых подтверждённых C/H дефектов product-кода или тестового алгоритма
не найдено. Текущая отметка остаётся 8/1; LWS009 ещё не закрыт.**

Что действительно добавлено:

- CMake исключает обычный Files object из native OwnerTests и включает
  REAL `ProtectedCustodyFiles.cpp` с прежними TU-local wrappers в этот
  executable; Tree worker берётся из общего product object. Нет замены
  logical алгоритма тестовым алгоритмом или production fault switch.
- `logicalAppendFaults()` измеряет числа write/read/flush в успешном actual
  worker, затем проверяет каждый номер этих вызовов на новом generated
  контейнере. HEAD boundary наблюдается непосредственно у вызова с offset
  128/16512, count16384 и OffsetHigh0, до возможного отказа. Это не guessed
  HEAD ordinal. Покрыты failed/short/zero write, оба flush, failed/changed/
  throwing read и два metadata allocation exceptions до/после HEAD attempt.
- После отказа тест проверяет no snapshot, retained base lease, outcome по
  observed HEAD attempt, повтор без новых native read/write/flush с тем же
  error/nativeError; reset caller Owner/Tree не освобождает HANDLE, что
  проверяется actual sharing refusal. Derived bad_alloc destructor проверяет
  ещё удержанный worker job при обработке metadata exception.
- TreeTests добавляет no-IO-write job/pin refusal, затем реальные commits
  при трёх чужих admitted jobs (для worker остаётся ровно один); FULL result
  copy/move nothrow traits и sizeof(Tree)≤4096 проверяются компилятором.
- Компактные validated ZERO fixtures с logical blocks1/63/64/4095/4096/
  262143 проверяют append/read old zero prefix/cold verify new pair и отказ
  следующего append при exact64GiB. Старые g2 pinned bytes после g3/g4
  проверяются actual logical commits. Giant allocation/full64GiB IO нет.

Точные ещё не представленные проверки LWS009 в этом снимке:

1. Другая **валидная exact previous pair при той же highest generation**,
   отказ до append/head; отдельный u64 generation exhaustion и unsupported
   short/unaligned input. Stale g2 после g4 не заменяет same-highest case.
2. Структурно допустимая подмена unchanged sibling/HEAD peer, которую не
   объясняет обычная порча framing/expected envelope SHA. Изменение первого
   ciphertext byte в `changedRead` — не этот case.
3. Actual owned-memory refusal при подготовке prospective proof/control
   storage до HEAD publication: no new snapshot/HEAD, custody и cleanup.
   Pin/job tests и искусственный metadata bad_alloc — иные branches.
4. Терминальные native результаты актуальных двух тестовых SHA. Для
   throwing read/metadata полезен прямой assert `allocationFailed`, а не
   только ненулевого error; нынешний source catch этот код сохраняет, но
   новый тест явно его не утверждает.

Это ограниченные недостающие доказательства prerequisite, не запрос на
полную Step3/T116 или installed/audio runtime. Необходимость новой
архитектуры/production hooks из этого чтения не следует.

Main сообщил `64495 BUILD_EXIT0` и `26270 EXIT0` как сборки; reviewer не
запускал их и не выдаёт их за native execution PASS. Новые native2groups и
portablefull пока заявлены running; результатов нет в прочитанном evidence.
Завершение процессов не выводится из source-ready или зелёной сборки.

| Расширенный test-only snapshot | SHA-256 |
| --- | --- |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | `cc0925c4371cf5fb0dc5d3e46111822a2518e033704356520aece3d17d729392` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | `a4930cc29df983730d347dd42aa751085eb80d761a79d896a49ee45292a71dda` |

Перечитаны отметки: **8 checked / 1 unchecked (LWS009)**. Reviewer менял
только этот report; shared code/docs/VM и execution не затрагивались.

## Follow-up: C4459 и новые pre-effect отказы

Main сообщил терминальный `96551 BUILD_EXIT1`: OwnerTests включает реальный
Files.cpp в TU с существующим global `Fault fault`, поэтому новый local
`fault` в Guard::reserve вызывал C4459 при `/W4 /WX`. CTest не выполнялся.
Этот отрицательный результат не превращён в PASS и не означает runtime
отказ worker.

Лично проверенная product-правка — только local `fault` → `rejected` в
Guard::reserve; использованы те же `error/nativeError`, тот же reject и return.
Другие три product SHA не изменились. Warning suppression/ослабления flags
в diff нет. Исторический Files SHA `9fdd3ed…` больше не является текущим.

Дополнительно прочитаны текущие test-only изменения:

- TreeTests проверяет dirty4 exhaustion вместе с job4/pin32 до изменения
  physical extent; после освобождения admission обычный FULL commit остаётся
  возможен. Прежний короткий tail3B отказывает без append и остаётся readable.
- Generation exhaustion fixture создаёт допустимую final пару max/max−1
  с empty roots/extent32896, затем actual worker отказывает без изменения
  размера файла. Это самостоятельный u64 guard, не только 64GiB limit.
- OwnerTests заполняет shared charged budget до64MiB, не читая synthetic
  pressure storage; actual append возвращает allocationFailed/notCommitted
  без native read/write/flush. После снятия pressure ошибка sticky и повтор
  не выполняет IO; pressure действительно deallocated.

Новых C/H product дефектов не найдено. **8/1 сохраняется.** Новый pressure
case отказывает ещё при первом charged read buffer, до disk read; он
**не исполняет** allocation failure именно prospective Tree/control block
после первого readback. Same-highest altered pair и structurally valid
unchanged sibling/peer case также пока отсутствуют. Прямая проверка short
input при aligned base отдельно не представлена; old short tail покрыт.
Native rerun ещё не принят за execution PASS; источник результатов — main,
reviewer не запускал сборки/CTest/VM. Полная T116/runtime матрица не запрошена.

| Текущий изменившийся файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `c7ddc8367c205a9f6e2177ff54b9a46ccc7e8b7a039079dba863378e67b11882` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | `49a15344e96e774083c515d795c25c44a98043101995f47ed757ec49c9ab7645` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | `1d81a48f58625c1f162c98e49481984c074a798376f1bc8d180ce37ddac7d949` |

HEAD прежний b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1; requirements gate
не расширен. Reviewer изменял только свой report, перечитал отметки: **8/1**.

## Терминальные результаты main после C4459

Main сообщил завершённые `83245 BUILD0 / native CTest2/2 PASS13.66s EXIT0`
и `89283 full incremental BUILD0 / portable CTest39/39 PASS31.83s EXIT0`.
Reviewer лично повторно сверил все шесть SHA предыдущего снимка: совпали
Files c7ddc836…, Owner.h99dee259…, Tree.cpp e0a0841d…, Tree.h a7f44c1c…,
OwnerTests49a15344… и TreeTests1d81a48f…; полные hashes приведены выше.
Это атрибутированные main terminal receipts, не самостоятельно запущенные
reviewer процессы и не native тесты на Mac. Исторический 96551 BUILD1
сохраняется отдельно; текущие результаты его не переписывают.

На текущем test snapshot LWS009 остаётся открытым — **8/1**. Запланированные
same-highest exact pair/valid peer substitution/prospective proof allocation
tests ещё не прочитаны и не признаны выполненными. После их добавления старые
test SHA/результаты не доказывают новый test snapshot. Ни полная Step3/T116,
ни installed Windows или выпуск этими двумя прогонами не принимаются.

## Итог последнего source-ready снимка

Прямое повторное чтение последних двух тестов и сверка всех шести SHA
подтвердили текущие OwnerTests `244d8c4af5595858cec25ef436b25c42a477b0a3f082e73df4f657d9b8375986`
и TreeTests `1ddd8bf15754f302814e02c88d970f55c47adbdb9890368d6bf2c043c9c811ac`.
Четыре product SHA прежние; чтение собственного report и main round221
сохраняет attribution: reviewer ничего не исполнял.

**Вердикт: REQUEST CHANGES только по оставшемуся доказательству LWS009;
product source C0/H0, coverage MEDIUM1, checklist8 checked/1 unchecked.**
Полная Step3/T116/app acceptance не является условием этого замечания.

Новые проверки действительно закрывают ранее указанные ограниченные gaps:

- Same-highest изменённая lower pair теперь сначала проходит независимый
  cold verify; старый Tree отказывает conflict, physical extent не меняется.
  Invalid1B input, old short tail, generation max и64GiB также представлены.
- Valid DPAPI empty g2 HEAD подменяется только после observed g3 HEAD
  attempt. Framing/header/context/descriptor допустимы, pair adjacent;
  отказ ambiguous invalidContent происходит из exact candidate/base сравнения,
  а не обычной повреждённой framing. Это точная проверка **HEAD peer**.
- Prospective pressure не является guessed magic ordinal. Baseline отслеживает
  последний pre-HEAD read count и минимум owned bytes при первом flush.
  По чтению Tree.cpp:230–259 минимум после последнего validated NODE достигается
  в финальном `validate()->guard.check()`: ciphertext/decoded bodies уже
  уничтожены, prospective Tree/control storage ещё не выделены. Последующие
  pre-HEAD checks держат также prospective Tree и HEAD buffers, поэтому их
  charge выше. Повтор на этом измеренном metadata checkpoint подтверждает
  тот же final read count и exact baseline floor, заполняет64MiB, затем
  `makeProof` отказывает до HEAD с одним flush, retained lease/sticky error.
  Pressure deallocated. Это доказательство prospective Tree allocation,
  не отдельного отказа каждой внутренней shared_ptr allocation; второго
  отдельного случая для этого scoped review не требую.
- Throwing read/metadata теперь явно утверждают allocationFailed. Native
  main receipts текущих test SHA:31945 Release2/2 PASS15.49s EXIT0,
  51827 Release41/41 PASS52.26s EXIT0,91788 Debug2/2 PASS19.06s EXIT0.
  Portable74577 BUILD0/39/39 PASS11.62s EXIT0 — не native branch execution.
  Main identity36121 подтверждает152 cpp/header guest↔mirror; broad77576
  generated JSON/cache mismatch не нормализован в source PASS155/155.
  Reviewer personally сверил canonical hashes, не выполнял VM comparison.

### M1 — одно оставшееся отрицательное доказательство structural diff

Требование gate LW006 и Changed-path matrix различает **NODE unchanged
Ref64** и **HEAD peer**. В текущем тестовом снимке отсутствует execution
отказа Tree.cpp:242–248 при структурно допустимом, но отличающемся unchanged
sibling нового NODE. `substitutedPeer` меняет HEAD, а `changedRead` портит
framing/envelope SHA и отказывает до child equality. Ни один не доказывает
этот конкретный structural-diff отказ. Поэтому LWS009 нельзя честно отметить
целиком по нынешним тестам.

Нужен один bounded test-only случай actual append worker: второй/следующий
FULL append с существующим nonempty sibling; новый NODE содержит иной
структурно допустимый sibling, при этом envelope/reference SHA и inner
checksum согласованы. Отказ должен происходить до HEAD publication без
snapshot/ACK, с удержанием custody/sticky failure. Допустимо переиспользовать
существующий native test-wrapper pattern, но не product fault switch или
новый алгоритм вместо real worker. Обычный hash/framing отказ и замена
HEAD peer не должны называться таким случаем. Требовать широкий hardware/
installed/full v1 gate или новую архитектуру для него оснований нет.

Последние all-source совпадения не закрывают отсутствующий сценарий.
Итог перечитан: **8/1, только LWS009 открыт**, без новых C/H product findings.
Запись reviewer ограничена этим report; source/tasks/issue/VM/commit/release
и установленное приложение не менялись.

## Проверка предложенного пути test-only исправления M1

Предложение выборочно подменить seal нового NODE_L0 для второго FULL append,
оставив BASE и реальные open/hash/DPAPI проверки, соответствует предмету M1.
Исходник/результат такого теста пока не готов; verdict по нему не вынесен.

Обнаружено конкретное несоответствие объяснения linking текущему CMake:
`graf_windows_common` объявлен **OBJECT** (CMakeLists.txt:79), а executable
получает `$<TARGET_OBJECTS:graf_windows_common>` непосредственно (строка87).
Tree.cpp не исключён из common glob. Поэтому это **не** archive-member
selection и нельзя рассчитывать, что повторное включение REAL Tree.cpp в
OwnerTests автоматически заменит обычный Tree object. Предложенная схема
без исключения исходного Tree object несёт дубли определений; терминального
доказательства такой новой сборки нет. Это замечание к техническому пути,
не новый product-defect verdict и не требование новой архитектуры.

Использовать существующий pattern отдельного OBJECT (как Files/Primitives)
или другое явно проверенное test-only исключение дублирующего Tree input;
не опираться на несуществующий selective archive. Product hooks/ослабление
linker warnings не нужны. LWS009 по-прежнему открыт, checklist8/1.

## Исправление M1 в исходниках и отдельное включение Tree

Лично прочитаны новая подмена codec, её вызов в `logicalAppendFaults`,
реальный `validate` worker и полный актуальный CMake. Снимок теперь включает
семь файлов: четыре product, два теста и CMake. Product SHA не изменились;
TreeTests остаётся `1ddd8bf15754f302814e02c88d970f55c47adbdb9890368d6bf2c043c9c811ac`.

По исходникам **M1 адресован корректно**, новых C/H замечаний нет:

- Тест создаёт actual g2 с DATA, затем второй FULL append строит g3. Подмена
  действует только при seal нового NODE_L0 g3 и утверждает, что sibling0
  исходно DATA. Заменяется ровно один Ref64 на допустимый ZERO; BASE не
  меняется. Реальный codec пересчитывает inner checksum/DPAPI, а worker
  получает SHA фактически записанного envelope.
- REAL Files.cpp включён до codec macro и не использует spy. REAL Tree.cpp
  включён под macro, но алгоритм worker не заменяется. `openReferenced`
  делегирует настоящему codec; отдельный `decodeChild` подтверждает допустимый
  ZERO при длине двух blocks, selector и parent extent. `siblingDecoded`
  утверждается после actual append. Значит ожидаемый отказ не объясняется
  hash/framing/DPAPI или недопустимым дочерним элементом.
- Worker сравнивает sibling0 с прежним private DATA Ref64 в первом validate.
  Тест утверждает один flush, отсутствие HEAD attempt, notCommitted,
  invalidContent, no snapshot, retained lease и повтор с той же ошибкой без
  нового native IO. Actual HANDLE удержан, что проверяется sharing refusal.
  Native case вызывается из main; assertions не отключены в Release
  (`NDEBUG` снят до `<cassert>`). Подмена выключается после нужного вызова.
- CMake исключает Tree.cpp из общего glob и создаёт отдельный
  `graf_windows_custody_tree OBJECT`. Его object подключён ко всем тестам,
  кроме WIN32 OwnerTests, где уже включён REAL Tree TU. На portable OwnerTests
  native TU отсутствует, поэтому обычный Tree object остаётся подключённым.
  Существующие `/W4 /WX /EHsc /utf-8` и portable warning flags сохранены.
  Предыдущее замечание о дублировании Tree inputs устранено в build graph.

Лично сверенные новые SHA-256:

| Файл | SHA-256 |
| --- | --- |
| apps/windows/CMakeLists.txt | `34512b061361516a997c0581b6a693d9535d3d5e6893cb2b017a2a061b96e295` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | `de29a55cca725aa0643517c12b9b3ca77bdf1322c1c22b1dba04b65b6522d33c` |

Main сообщил terminal16829 BUILD1 LNK2005/LNK1169 до исправления CMake;
CTest не выполнялся. Это подтверждённый main отрицательный build receipt,
а не execution нового siblingDecoded snapshot. Старые native PASS относятся
к прежним test SHA и не закрывают новый случай.

Для нового CMake main сообщил portable17410 BUILD0/39of39 PASS39.26s EXIT0.
Native case там исключён; этот результат не является его исполнением.
Свежий native Release/41 заявлен запущенным после синхронизации CMake34512…
и OwnerTestsde29…, но terminal receipt пока отсутствует.

**Текущий статус: source gap M1 устранён; execution acceptance ожидает exact
native receipt. Checklist остаётся 8 checked / 1 unchecked (LWS009),
без новых product C/H findings.** После корректного терминального результата
этого снимка оснований требовать полную T116 runtime матрицу для закрытия
данного bounded checklist нет. Полная Step3/T116, adoption, installed app,
hardware/audio и release этим review не принимаются. Reviewer записал только
свой report и не запускал code/build/CTest/VM или иные запрещённые действия.

### Промежуточный native8433 — не полный terminal PASS

Повторное прямое чтение spy/actual negative case/CMake и сверка семи SHA
подтвердили тот же снимок CMake34512…/OwnerTestsde29…/TreeTests1ddd… и
неизменные четыре product файла. Main сообщил BUILD passed после regeneration
и отдельные текущие CTest результаты Owner PASS12.55s / Tree PASS10.85s.
Новый siblingDecoded case входит в actual Owner executable. Это положительные
целевые результаты main, но весь8433 ещё выполняется: общий CTest EXIT0 и
41/41 пока не заявлены. Последний full portable17410 относится к текущему
CMake, но native branch там отсутствует. Будущий Debug не принят заранее.

Checklist по просьбе main остаётся8/1 до окончательного terminal receipt;
новых source замечаний нет. MainApp SHA/solution build относятся к отдельной
проверке приложения и не являются installed/adoption evidence в этом report.

## Окончательный ограниченный вердикт после native8433

**SCOPED SOURCE ACCEPTED: 9 checked / 0 unchecked;
CRITICAL=0 / HIGH=0 / MEDIUM=0 в рассмотренной области. M1 закрыт.**
Этот итог заменяет прежний REQUEST CHANGES/ожидание LWS009 только для
проверенного первого FULL sequential append block на existing private Tree
proof с прежним Owner/Guard. Исторические отрицательные результаты и
промежуточные статусы выше сохранены, не превращены задним числом в PASS.

Основание — независимое прямое чтение product алгоритма, новых actual-worker
tests и CMake, плюс атрибутированный main окончательный terminal receipt:
**native8433 BUILD0 / CTest41of41 PASS226.92s / EXIT0**. Main явно привязал
его к CMake34512…/OwnerTestsde29…/TreeTests1ddd… после regeneration и sync;
новый valid unchanged sibling case действительно выполнен в native OwnerTests.
Целевые результаты того же запуска: Owner12.55s, Tree10.85s. Portable17410
BUILD0/39of39 PASS39.26s относится к текущему CMake, но не исполняет native case.
Reviewer сам сборки/тесты/VM не запускал и результаты main не выдаёт за свои.

Перед отметкой LWS009 лично повторно сверены все семь полных SHA, указанных
выше: совпали. Requirements gate SHA также остался
`7fb4f75180745620091241fd569e47677efeda113080f3b452155bca84181a5f`;
HEAD прежний `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Четыре product файла не менялись после исходной проверки алгоритма.
Подмена sibling проходит реальные SHA/DPAPI/child semantic проверки и
отказывает именно при bounded structural diff до HEAD; отдельный OBJECT
устраняет повторные Tree definitions без waiver. Это закрывает оставшуюся
конкретную coverage gap, а не подменяет её hash/framing отказом.

Main отдельно сообщил медленный `DesktopUploadRecoveryTests171.44s`:
тест прошёл, причина длительности не установлена. Из этого результата не
следуют performance, audio continuity, Stop deadline или отсутствие иных
рисков. Read-only48012, по сообщению main, наблюдал реально работающий CTest
в период ожидания; он не является отдельным тестовым PASS. Последующий
Debug ещё выполняется и не принят заранее; актуальный Release receipt уже
достаточен для данного ограниченного review.

**Не закрыты этим отчётом:** полная Step3/T116–T118, partial/unaligned Write,
rewrite/SetSize/short tail, metadata integration, migration/GC, adoption в
приложение, installed Windows/macOS parity, hardware/audio, доступность,
подпись и публичный выпуск. Acceptance не разрешает новые scope, commit,
merge/release или изменение reviewer-owned требований основным агентом.
Любое последующее изменение семи проверенных файлов требует соответствующей
повторной проверки; старый exact-snapshot PASS не переносится автоматически.

Reviewer изменил только данный report; code/spec/plan/tasks/feature/Git/
GitHub/VM/install/mic/commit/release не менял и не исполнял. Окончательные
отметки перечитаны: **9/0**. Risk lane остаётся high-risk-product, не scoped
low-risk implementation lane; ограничен предмет независимой приёмки.

### Завершённые дополнительные результаты после принятия

Main сообщил окончательные результаты того же проверенного снимка без
последующих source changes:

- native23015 Debug BUILD0 / CTest2of2 PASS27.98s / EXIT0;
- identity32771: cpp/h + CMake153of153 MATCH / EXIT0;
- host183 tracked Windows files MATCH;
- прежний native8433 Release BUILD0 / CTest41of41 PASS226.92s / EXIT0
  остаётся привязанным к тем же семи SHA.

Это дополнительные атрибутированные main receipts, не лично исполненные
reviewer процессы. По сообщению main, активных его сборок/тестов больше нет.
Новых проверок исходников или исполнения reviewer не проводил: исправление
M1 и отдельное включение Tree уже непосредственно проверены выше.

Окончательный опубликованный вердикт остаётся **SCOPED SOURCE ACCEPTED,
9 checked / 0 unchecked, scoped CRITICAL=0 / HIGH=0 / MEDIUM=0**.
M1/LWS009 закрыты только в указанной области первого FULL sequential append.
Ограничения полного T116, adoption, installed app, hardware/audio и release
сохраняются. Commit/install/release не выполнены и не заявлены; reviewer
добавил только эту запись в собственный report.
