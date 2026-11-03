# Независимая проверка требований Round253: protected package → sealed member Reader

**Дата**: 2026-10-06. **Владелец**: независимый reviewer.
**Purpose**: качество требований и scoped analyze первого реального связующего
reader API в существующей T116, dependency5, после сравнения с полной
обязанностью проверки членов обоих package metadata slots.
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md), [tasks.md](../tasks.md).
**Полоса**: high-risk-product storage; read-only review с единственным новым отчётом.
**Review Ownership**: оценки ниже принадлежат reviewer. Это отчёт, а не новый
чеклист задач; новых checkbox markers нет. Прежние markers не редактируются.

## Решение и точная граница GO

**REQUIREMENTS APPROVED / scoped GO для первого sealed-member consumer bridge;
CRITICAL=0 / HIGH=0 / MEDIUM=0 / LOW=0 в качестве требований этого шага.**
Все 20 критериев качества требований ниже удовлетворены по текущим нормам.
Не требуется новая schema, продуктовый выбор, численный допуск или задача.
Основной агент может лично прочитать этот GO и выбрать начало RED/ограниченной
реализации. Reviewer не начинает реализацию и не принимает будущий исходный код.

Разрешённый результат: read-only logical Reader **одного** sealed ref,
полученного из выбранного physical slot удерживаемой собственной
`ProtectedCustodyPackagePair`, после проверки actual member context/snapshot,
полной logical length/SHA и сохранения обеих actual leases через Reader/Clone.
Это первая связь доказанного metadata provenance с реальным member consumer.

**FULL PACKAGE / EFFECT AUTHORITY — НЕ ПРИНЯТА.** Этот GO не принимает
проверку всех refs BOTH slots, live capture recovery, manifest/format/trusted
prefix/positive short predicate, переходы фаз, bootstrap/intent/barrier roots,
права аккаунта, upload/playback/discard/delete/GC или подключение приложения.
Общая обязанность T116 остаётся полной; assembly/phase validator следует
отдельно в той же задаче. T116/T117/T118/T120 и H250-1/H250-2 не закрываются.
Source нового overload и native/portable/installed execution: NOT REVIEWED / NOT RUN.

Уточнения main рассмотрены последовательно. Окончательная форма использует
прямой `sha256ProtectedStream` с existing `NativeHash`, **без** std::streambuf
adapter. Ранее предложенный adapter не является требованием и не сохраняется
как параллельная ветвь. Это выбор формы реализации в пределах уже принятых норм.

## Снимок, метод и действующие предпосылки

Единственная рабочая копия:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Лично проверены ветка `codex/200-windows-followup` и HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty bytes сохранены;
HEAD не идентифицирует незакоммиченные файлы. `.specify/feature.json`
указывает Feature200/high-risk-product и эту ветку. Prerequisites
`--json --paths-only` разрешает тот же feature directory; его поле BRANCH
`200-windows-desktop-app` — feature routing, не замена actual git branch.

Лично прочитаны `speckit-analyze`, `speckit-checklist`, `code-reviewer`, root
AGENTS, guidance index, spec-kit-flow, product-gates, worktree guidance,
constitution7.1.0 и применимые правила validation/evidence. Прочитаны
относящиеся sections spec/plan/tasks/model/quickstart, оба custody contracts,
PRD local-buffer policy и current merged custody status. Research/history
не используются как замена нормативному wire/authority contract.

`speckit-analyze` применён к согласованности и покрытию требований;
`speckit-checklist` — к полноте/ясности/проверяемости, без генерации дублирующего
чеклиста; `code-reviewer` — к границам существующих API и отказов, **не** как
source approval ещё не написанного bridge. Main отдельно трассирует finalizer/
actual app readers; reviewer не повторяет полный аудит реализации этих consumers.

Extensions YAML прочитан: before/after analyze/checklist commit hooks disabled.
Никакие hooks не исполнялись. Обычный prerequisite script имеет side effect
записи feature pointer и не поддерживает `--require-spec`; поэтому использован
его существующий `--paths-only --no-persist` путь, а обязательные spec/plan/tasks
прочитаны непосредственно. Скрипты/feature pointer не изменялись. Сохранение
отчёта — прямая разрешённая пользователем запись, не изменение анализируемых норм.

Терминальные границы предпосылок лично перечитаны:

| Предпосылка | Что принято | Что ею не принято |
| --- | --- | --- |
| Round252 metadata-pair gate/source, включая конечный DOCS appendix | Own BOTH physical indices и оба strict package payloads под private readonly identity lease; соответствующие текущие Files/Metadata hashes совпали с SOURCE таблицей | Actual members/roots/SHA, manifest, account/effects/GC; array/value не самостоятельная frozen lease |
| Round251 retained-root gate/source, конечное подтверждение | `Tree::verifyRetained`: readonly cold root closure, свой immutable descriptor и actual owner | Protected stamp provenance и whole finalized logical SHA, полный набор external retainers, package/effect authority |
| Package parser gate, конечные SOURCE/DOCS sections | Strict package.v1/v2 structural values, в том числе допустимые structural length0/EMPTY | Normal artifact acceptance; `sealed_normal` во входном JSON ещё не normal package |

Validation Round252 содержит запись main о terminal native50/50 и новых
source/EXE receipts. Она прочитана как документальный контекст; actual runtime
receipts/EXE не открывались и reviewer ничего не исполнял. Эти PASS не
переносятся на новые sealed-member/hash случаи. T116/#7444 OPEN и labels
freshly verified main `a09005` — информация из задания; GitHub reviewer
не запрашивал и не менял, независимой live tracker проверкой её не называет.

## Полная обязанность BOTH slots: согласованный минимум остаётся прежним

Нормативные источники: base §§2–7/8.1, packed §§1–6/6.1,
model §§12/13, plan dependency5, quickstart §§12/14 и существующая T116.
Ни одна строка следующей таблицы не становится выполненной от одного bridge GO.

| Обязанность полного consumer/assembly validator | Минимум по существующим нормам | Вклад первого bridge / оставшаяся работа |
| --- | --- | --- |
| Own metadata и оба slots | Actual protected pair, каждый payload связан с own index generation/context/directory; missing/invalid lower slot не скрывается higher; no singleton/default/rollback | Reuse pair Round252; новый API принимает только её held shared_ptr, не caller-created value |
| Все member refs обоих values | У каждой ссылки своя role/object identity, binding/representation, generation/length/SHA; packed также container/extent/root. Старая slot не теряет keep-edge от выбора current | Bridge проверяет один адресуемый sealed ref любого slot; orchestration всех refs обоих slots и удержание общего набора остаются T116 |
| Physical provenance и exact bytes | Confined fixed role location; actual store/object/container IDs и native identity/ACL/path. Full referenced closure, own generation/length, whole logical SHA; не ciphertext SHA/mtime/file size | Bridge устанавливает это для одного sealed ref; Tree сам по себе не подтверждает происхождение stamp |
| Normal sealed package | Current phase `sealed_normal`, reason empty, short=false; sealed media/playback/manifest обязательны. Actual v5 WAV/AAC/manifest, formats/hashes/duration/trusted capture semantics проверены до normal inspect/upload | Hash/byte proof отдельных членов не заменяет manifest/format/cross-member/phase validator. EMPTY/length0 structural успех не normal recording; одного length>0 тоже мало |
| Capturing/finalizing и live refs | canonical live обязателен; generation/length/SHA=null, packed extent/root=null, container уже задан. Live paired checkpoint выбирается по recovery правилам; canonical prefix=floor(length/1920)×1920 без padding/повторной AEC | Live ref этим API отвергается; actual capture recovery остаётся отдельной работой T116. Старая capturing slot сохраняет live retainer, а не становится sealed от новой slot |
| Degraded и short discard | Degraded: непустой safe reason, validated trusted prefix, upload запрещён. Discard: positive прежний short predicate, short=true и protected manifest marker; durable intent/queue removal и marker-last ordering | Sealed ref этих фаз может дать только его проверенные bytes. Bridge не подтверждает prefix/short/marker semantics и не открывает inspect/upload/cleanup |
| Lifetime, restart и effects | BOTH metadata roots, pins/jobs/retained results сохраняются до actual completion. После gap full closure. Bootstrap/intent/historical barriers, account/context admission и durable delete/removed ACK независимы | Pair+member leases через Reader/Clone необходимы, но не полная retainer enumeration, не новые network/delete/GC полномочия |

`BOTH slots` не означает, что все refs обязаны быть sealed: schema явно допускает
live refs в capturing/finalizing. Для полного validator это два разных
нормативных пути. Нельзя молча пропустить старый live edge, превратить null
stamp в empty/sealed объект либо требовать SHA незафиксированного live хвоста.
Частичный Reader не является удостоверением здоровья всей пары членов:
порча другого ref не проверена этим вызовом и сохраняет блокировку общего admission.

## Разрешённые формы существующих API

### Reader из held pair

Допустим один overload существующего `openProtectedCustodyReader`:

```text
openProtectedCustodyReader(trustedRoot,
    shared_ptr<const ProtectedCustodyPackagePair>, slot, refIndex, ownedCancel)
    -> CustodyFileResult<CustodyReader>
```

Slot — actual physical0/1, refIndex — в пределах refCount **этой** slot.
Pair/token не null; sealed triple и representation берутся из retained const
value, не из отдельного caller descriptor/context/`bool verified`. Context:
store из own package context, object/role из его ref, directory из own
validated package directory; packed container из exact sealed ref. trustedRoot
независимо доверен для того же custody scope, actual member open сверяет
store.id/id.bin и confinement. Input JSON или ref не задаёт внешний path.

Package.v1 остаётся flat-only. Package.v2 имеет ровно9 top-level fields
и10 fields/ref; flat stamp additions=null; packed лишь canonical/media/playback.
Нельзя расширять schema/field sets, угадывать representation по extension
или пробовать flat/legacy после packed failure. Manifest/recovery — flat_v1.
Role limits прежние: canonical/media/playback≤64GiB, manifest/recovery≤64KiB;
package payload≤64KiB, refs≤5, JSON depth≤4/keys≤16. Buffer/process limits
owned64MiB/cache2MiB/pins32/jobs4 не увеличиваются;64GiB не device quota.
PRD7days/5GB/80%/95%/reserve=min(10GB,10%capacity) сохраняются для своих
admission/mutation путей. Read-only bridge не создаёт новый physical write
peak и не выдаёт сохранённый hash за принятие дисковой квоты или SC-003.
Никакого independent member-proof класса, backend interface, фабрики,
callback configuration, отдельного lifecycle/dispatcher/queue не нужно.

Packed: existing Owner открывается в existing confined location по expected
context. Existing `Tree::verifyRetained` проверяет обе current heads/closures
и exact protected retained stamp под тем же guard, включая root вне current
heads. Descriptor строится из ref и фиксированных protocol constants; не
создаются fake historical heads. Затем existing Reader читает этот immutable
descriptor; whole logical SHA сверяется с ref до возврата. Same-generation
descriptor обязан совпасть с соответствующей head; older extent не превосходит
более поздние heads; newer-than-current stamp не normalizes rollback.

Flat: reuse Files `readValidatedSnapshot`, existing Codec `openIndex/readIndex`
и existing ReaderState. Нужны обе actual physical indices и их referenced
DATA checks; trustedPrefix либо успех audio-singleton не достаточны для этого
sealed bridge. Public `readValidatedMetadataPair` запрещён audio и не расширяется
до audio ради обхода. ReadIndex peer при необходимости допустим вместе с
existing decoder/physical validator; одно успешное чтение peer envelope ещё
не closure его DATA. Повторный самостоятельный scanner/selector не нужен.

Выбирается **точная** ref generation и matching logical length. Если это lower
peer, его собственный decoded index используется как snapshot; не highest с
подставленной generation. Его DATA/tail/context и весь hash проверяются.
Пара/peer должны быть согласованно получены при удержанном владении: ordinary
readExisting допускает protocol writer и не называется frozen. Существующий
private writeExisting→blockWrites lease pattern допустим для исключения writer
без content write; либо используется уже доказанное непрерывное владение.
Наружу не передаются Files/HANDLE/write capability. Exact actualFiles+snapshot
удерживаются во время hash, чтения и Clone, включая keep-roots pinned versions.

Если нужный flat generation уже отсутствует в обоих физически доступных
indices и нет ранее удержанного actual validated snapshot, **ref остаётся
blocked/recovery-required**. Имена immutable blocks, version==generation,
похожая длина/SHA или декодируемый highest не восстанавливают утраченный index.
Standalone migration birth-barrier validator base §8.1 — другой fixed-role
путь и не универсальный historical flat reader. Не вводятся третий index,
новая historical schema, in-place repair, автопереход на packed или удаление.
Это существующий fail-closed предел, не разрешение ослабить полный BOTH gate.

ReaderState сохраняет actualPair shared_ptr и actual member lease/proof.
Clone разделяет **тот же** state/leases/cache и имеет independent cursor/pin.
Сброс ссылки main/исходного Reader не освобождает lease живого Clone. Перед
return hash сравнен и Seek(0) успешно выполнен; отказ rewind не выдаёт stream.
Выданные logical bytes имеют sealed-member проверку, но `verified` byte state
не означает `sealed_normal` package/account/effect authority.

### Прямой protected hash, reuse NativeHash

Допустим небольшой Windows-only helper в существующем `Sha256.*`:

```text
sha256ProtectedStream(IStream*, expectedLength, ownedCancel)
    -> CustodyFileResult<array<uint8_t,32>>
```

Строго проверенная digest string той же длины тоже допустима; выбор типа
не продуктовый вопрос. Existing `NativeHash`/CNG переиспользуется напрямую,
без portable fallback после native failure и без второго SHA implementation.
Helper удерживает ComPtr на stream и owned cancellation token до actual
завершения, возвращает только digest, не доказательство полномочий.

Вход — logical stream с подтверждённой нулевой позицией. Один
`CustodyBytes`64KiB резервируется существующим allocator **до** Read, очищается
на всех выходах, включая исключения. Hash выполняется bounded chunks≤64KiB,
каждый Read возвращает ровно ожидаемые bytes с корректным HRESULT/got;
ранний EOF/short read/лишние bytes/invalid count не дают prefix digest.
После expectedLength проверяется настоящий EOF; stat.cbSize или length из JSON
не заменяет этот check. expectedLength0 даёт SHA пустых bytes только при actual
EOF, не normal package. Cancel проверяется до/после IO, до завершения hash/
публикации результата. Late cancel не уничтожает ещё выполняющийся Read/CNG
и не освобождает его buffers/ComPtr/job. Наблюдаемый stream error не маскируется EOF.

Typed ошибки различаются: CNG create/update/finish failure — hashFailed,
failed IStream Read/Seek — ioFailed с исходным native/HRESULT свидетельством;
bad allocation/admission — allocationFailed, invalid input — invalidInput,
cancel — существующий cancellation error. Semantic length/SHA/context mismatch
остаётся existing content/conflict failure, не «успешный hash» и не generic
codec-repair. Нет empty/default digest при отказе, повторного native hash либо
перехода к sha256File. First fault/observed sticky failure не затираются.

Отдельно необходим минимальный shared-cause fix: в existing
`sha256Stream(std::istream&)`64KiB stack buffer появляется secure wipe guard
на все return/throw paths. Лично прочитанные Sha256.cpp:162–184 сейчас
не очищают эту plaintext копию; Primitives.cpp:31 вызывает тот же helper для
custody payload hashing. Очистки нового direct buffer недостаточно для старых
callers. Старый stack allocation strategy/публичные return semantics не меняются
ради переноса на CustodyAllocator: это создало бы новую budget семантику старого
codec. Новый protected helper имеет собственный charged buffer; это не заявление
о полном quota/wipe аудите всех прежних hash internals/native allocations.

## Качество требований: независимая оценка

PASS — качество написанных требований и соответствие предложенной формы им,
не реализация. Новых checklist markers нет; traceability20/20.

| ID | Вопрос к требованиям | Оценка и основание |
| --- | --- | --- |
| R01 | Определено ли отличие protected pair provenance от actual member proof и полной authority? | PASS — base §§6/7/8.1, packed §6.1; pair и retained-root terminal boundaries явно исключают следующий consumer gate |
| R02 | Однозначно ли BOTH включает refs обеих slots, даже не selected/current? | PASS — base §§5/8.1, packed §6.1, model §§12/13; bridge выбирает один ref, общий validator сохраняет полный набор |
| R03 | Полны ли точные схемы, role/location/context и запрет input self-authorization? | PASS — base §§2/3/8.1 и packed §6.1: own context/generation/directory, strict9/6/10fields; expected identity независимо от JSON |
| R04 | Ясны ли sealed triple, actual generation/length и whole logical SHA? | PASS — base §§6/8.1, packed §§6/6.1; digest finalized bytes, не envelope/file_size/частичный hash |
| R05 | Заданы ли packed stamp/root/extent/обе heads/cold closure под actual owner? | PASS — packed §§2–5/6.1; retained-root prerequisite даёт closure, protected pair добавляет происхождение stamp |
| R06 | Определена ли точная flat snapshot проверка без audio fallback для sealed proof? | PASS — base §§3/4/6/8.1; обе physical slots/DATA и matching sealed index, trustedPrefix не sealed normal authority |
| R07 | Явно ли недоступный historical flat index не реконструируется произвольно? | PASS — base §§3/4/8.1: pinned index обязателен; direct historical barrier имеет собственный закрытый validator |
| R08 | Разделены ли sealed_normal, required actual artifacts и structural zero/EMPTY? | PASS — spec FR-011/012, base §4/8.1, packed §6.1; parser terminal zero-length clarification сохраняет внешний actual validator |
| R09 | Ясны ли live capturing/finalizing refs и отдельное canonical recovery? | PASS — base §§4/8.1 и packed §§5/6.1: canonical live/null triple, exact frame prefix, не sealed Reader/inspect/upload |
| R10 | Полны ли degraded/short требования без новых решений о результате записи? | PASS — base §§4/7/8.1: reason/trusted prefix/no upload и positive short/protected manifest/marker-last; bridge их не принимает |
| R11 | Однозначно ли удержание actualPair+member leases после factory и через Clone? | PASS — base §§5–7, packed §2; same proof/state/owner, independent cursor, last actual release, не временный borrow |
| R12 | Задана ли readonly capability без public mutable handles/Writer rights? | PASS — base §6, packed §§2/6.0; существующий Reader/readonly retained result, private leases и const pair values |
| R13 | Определены ли весь exact hash input/EOF и rewind до выдачи Reader? | PASS — base §6 verified logical bytes/exact tail/CNG hash; expected stamp из §8.1/packed §6.1, existing independent cursor |
| R14 | Согласованы ли memory/cache/pin/job/IO ограничения без изменения допусков? | PASS — base §5 и packed §6: owned64MiB/cache2MiB/pins32/jobs4/chunks≤256KiB; новый64KiB hash буфер входит в прежний budget |
| R15 | Полны ли crypto/native/allocation/cancel failures без partial result? | PASS — base §§3–7, packed §§1/2/5/7; DPAPI FALSE и TRUE+invalid, CNG failures, sticky observed fault и retained lifetime |
| R16 | Определена ли защита plaintext временной памяти, включая общий старый hash buffer? | PASS — base §§1/5/6, FR-012; новый charged+wiped буфер и shared wipe отвечают одной существующей обязанности |
| R17 | Отделены ли admission/account/epoch/effects от проверенных bytes? | PASS — base §§5/7, FR-013/014/022; caller должен проверить current owner/session/state, byte proof не запускает сеть/GC |
| R18 | Ясны ли границы worker-only, privacy/evidence и отсутствие новых систем? | PASS — FR-012/SC-006, base §§1/5/6, packed §6.1; existing Files/Tree/Reader/CNG, никакого UI IO/plaintext temp/backend/lifecycle |
| R19 | Проверяемы ли критерии без переноса old PASS и без сужения общей приёмки? | PASS — quickstart §§12/14 и tasks T116→T117→T118; отдельные source/native receipts, full package и installed не приняты этим шагом |
| R20 | Прослеживается ли bridge/shared wipe к существующей задаче без дублирования gate? | PASS — plan:1517–1521/1586–1588, tasks:568 и package gate CHK009–012; всё внутри T116/dependency5, дальнейшая assembly остаётся там же |

## Scoped analyze, замечания и покрытие

| ID | Категория / уровень | Место | Вывод |
| --- | --- | --- | --- |
| B01 | Граница source / existing implementation debt | Sha256.cpp:162–184; Primitives.cpp:31; T116 | Общий plaintext hash buffer пока unwiped. Исправление входит в предлагаемый шаг; source baseline не получает approval. Это не missing/ambiguous требование и не новая задача |
| B02 | Граница доказательства / fail-closed | base §8.1; Files snapshot API | Older flat generation вне доступной пары без actual retained index не доказуем. Ref/package остаётся blocked; fake index/head недопустим. GO не обещает его поддержку |
| B03 | Граница полноты / existing T116 | base §§4/8.1; packed §6.1; quickstart §§12/14 | Все refs BOTH slots, live recovery и assembly/phase/effect authority ещё не приняты. Одно успешно проверенное sealed member не закрывает их |

B01–B03 — явно сохранённые implementation/acceptance boundaries, **не**
открытые дефекты качества требований. Unresolved requirement findings
C0/H0/M0/L0; ambiguity0, duplication0. Если реализация не сможет выполнить
эти границы, её результат blocked/source NO-GO, а не ослабление нормы ради PASS.
Не найдено неразрешённого продуктового выбора, требующего уточнения владельца.

| Requirement key | Есть задача? | Existing task / конкретное покрытие |
| --- | --- | --- |
| FR-011 | Да | T116: logical v5 format сохранён; assembly normal-format/duration acceptance остаётся позже |
| FR-012 | Да | T116: protected provenance→actual sealed snapshot→whole SHA→readonly lease; без plaintext copy |
| FR-013 | Да | T116: proof не заменяет ledger/current state/deletion truth, no empty/rollback; migration T117 отдельно |
| FR-014 | Да | T116: hash logical bytes, сохраняет прежние ranges; API не делает network/upload acceptance |
| FR-022 | Да | T116: leases/pins/effects разделены, cleanup/GC не разрешаются из proof; T117/T118 отдельно |
| SC-006 | Да | T116: input/context/schema/failure/evidence boundary; полная bridge matrix не принимается |

Scoped requirements6, executable task1=T116; coverage6/6=100%, unmapped0.
20/20 требований-quality вопросов удовлетворены, неподтверждённых0. Это не
full-feature analyze22FR/10SC/120tasks и не выполнение task T116.
Constitution II/III/IV/VI согласованы: видимые capture controls сохранены,
локальная защита не меняет серверную plaintext observability, deletion truth/
независимый review остаются обязательными. Новый schema/backend/lifecycle,
account authorization, network/GC, tolerance/product quota не вводятся.

## Минимальные доказательства будущего source/validation review — NOT RUN

Это следствия действующих критериев, не новые tasks или checklist gates.
Main представляет exact baseline/final changed-file hashes и frozen diff:

- Own held pair schema1/2, оба physical slots с разными generations/refs:
  slot/ref bounds/null/live отказ, wrong actual IDs/role/container/directory,
  representation отказ, chosen lower sealed ref не заменяется current.
- Packed retained root вне current heads: exact прежние bytes/length/EOF/SHA,
  tampered historical NODE/DATA и испорченная любая current head/closure,
  future/equal-conflicting generation/extent/root — отказ без stream.
- Flat обе actual indices/referenced DATA, own sealed lower snapshot; missing
  peer/audio-singleton/trustedPrefix и unavailable older index не выдаются
  за sealed result. Source по reuse shared validator, без duplicated scanner.
- Whole logical SHA: boundary0/1/64KiB/64KiB+1/exact tail, wrong expected
  length/digest, premature EOF/extra bytes/failed Read/invalid got, CNG
  create/update/finish failure и cancel cuts; no prefix/default digest.
- Member reader начинается в0 после hash; refused rewind не возвращает
  stream. Clone после release pair/main Reader удерживает exact pair/member
  leases; independent cursors, readonly Write/SetSize, no hidden mutable access.
- Pin32/job4/owned64MiB pressure, object/control-block/throwing transfer
  boundaries и actual before-free wipe на success/failure/cancel. Hash keeps
  ComPtr до native completion; shared stack wipe покрывает прежние callers
  без изменения их allocation/result semantics; old hash/codec regressions.

Не достаточно прежних parser5/5, retained-root6/6, pair/full50/50 или portable
PASS. Runtime results main должны быть terminal и привязаны к новым exact
source/test bytes. Reviewer runtime/profile/device/audio/network/migration
не запускает. Следующий source review — отдельное поручение после реализации;
приёмка исполнения, working inventory, installed x64/hardware и release отдельны.

## Все существующие checklist markers и их terminal scope

Перед записью перечислены и пересчитаны **99** существующих Markdown файлов.
Физические markers: **410 checked / 10 unchecked**. Это append-only повторы,
не420 уникальных обязательств и не новый implementation PASS.
Sorted manifest SHA-256 (`filename + space + sha256 + LF`, UTF-8):
`205babb76c92b5dcd19ccd259055634e63979114b5c8664545070e534966d0c5`.

| Действующий нормативный checklist | Checked | Unchecked |
| --- | ---: | ---: |
| requirements | 22 | 0 |
| audio-capture | 24 | 0 |
| advanced-routing | 14 | 0 |
| security | 27 | 0 |
| ux | 25 | 0 |
| calendar-launcher | 5 | 0 |
| calendar-operation | 8 | 0 |
| calendar-wire | 5 | 0 |
| packed-writer | 12 | 0 |
| privacy-pause | 12 | 0 |
| **Всего десять файлов** | **154** | **0** |

Другие report markers суммарно256/10. Все десять unchecked прочитаны:
tree-source строки61/62/586 —3; writer-source34/36/37/40 —4;
cadence-source34/35/40 —3. Они сохранены буквально. Конечные append verdicts
writer9/0 и cadence9/0 принимают только свои frozen worker/diagnostic scopes;
tree terminal17/1 сохраняет непроведённый engaged-snapshot error-return cut.
Ни история pending/H3, ни последующие локальные ACCEPTED не принимают нынешний
member bridge; старые unchecked не превращаются в10 новых requirements blockers.
Package parser12/0 и metadata-pair14/14/retained-root12/12 — также свои scopes.
В tasks120=93checked/27unchecked; T116/T117/T118 открыты. Отметок не менял.

## Лично вычисленная идентичность прочитанных норм и API baseline

Ниже SHA-256 до нового implementation; это привязка review к dirty bytes,
не freeze будущего bridge. Пути source — `apps/windows/RecApp/Storage/`.

| Артефакт | SHA-256 |
| --- | --- |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| quickstart.md | `5ff63ffb0519448fbe853ef7aefd573355b4f6a400d90be9162035c2847197a3` |
| base custody contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed custody contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| pair requirements report | `5d26889dd72a59a16d6fefc5a84d13e12690c6d75890558656ddb3e7d1f9a496` |
| pair source/DOCS report | `bd6b98afcd839b938f0634f488bd8208b0f60d8f0ef88ae5ab14b24047ead4cc` |
| retained-root source/DOCS report | `3338f25fa2562bc81c7aa48efb167cc52fc0a64f6a7ce616c31f0a5a20a2b4cf` |
| retained-root requirements report | `5d7d2d8f1652a4f28ba42025f66d3ad710cbe07e51c64f8488c57824201332e0` |
| ProtectedCustodyFiles.h | `cb0e4eb64f72c0b2332c9adee8f0d3824cd8063a5ef4e2bed5458293b65fdfa1` |
| ProtectedCustodyFiles.cpp | `ae784b46f417c503e592410edd7dc71ab8131592f5cfeb04c235e0a96a817b82` |
| ProtectedCustodyMetadata.h | `3e1f12fda3e18463c6430921e16173afac5c549aaebfa222efcc9dd24b743478` |
| ProtectedCustodyMetadata.cpp | `c917b43a94d09547be829694b6cf9c44efde0f91d03dce4c931d8534fa68a1f7` |
| ProtectedCustodyReader.h | `c76be03233949ff2779740dbc8a4f32eaa81da1921ff48f8a9ebcc60e532479d` |
| ProtectedCustodyReader.cpp | `0d38daf7ce709d112ca14edb3e87cb7a4a774c562ef48984c2ef91ad265977b9` |
| ProtectedPackedCustodyTree.h | `12221fc52c6955c3bd79efa11e37764dc93f7a80dfea25ef01704d8c742dfa6c` |
| ProtectedPackedCustodyTree.cpp | `c308ac7159695a5a1e8edc1c65a1332481c576fff4f53b2ab270c99960d97391` |
| Sha256.h | `e51b352aa346036708ad30867fed412b67000434b87d88aeb02c45549c43cc60` |
| Sha256.cpp | `af51b5cef94a0855773c1310b05bc7ef1d13a65939d2f8bc4b960ff403f0a4d2` |
| ProtectedCustodyPrimitives.cpp | `a27b07ac3b04627c5286d6290b3ca6ba3a15710fa170f238be893c3e13c133b3` |

## Терминальное решение

**Scoped requirements GO: existing sealed-member Reader overload + direct
NativeHash helper + shared old hash-buffer wipe; quality20/20, C0/H0/M0/L0.**
Это конечный отчёт требований, без ожидания будущего runtime PASS. Parent
самостоятельно решает immediate implementation после личного прочтения GO.
Полный BOTH-members/assembly/phase/live-recovery/account/effect gate остаётся
непринятым existing T116, миграция T117 и acceptance T118 не сокращены.

Единственная запись reviewer — этот новый файл. Исходный код, spec/plan/tasks,
старые checklists/markers, feature pointer, GitHub и runtime не изменялись.
Commit/push/PR/merge/build/test/VM/app/install/audio/network/GC не выполнялись.
После записи отчёт лично перечитан целиком. Повторный подсчёт:20 уникальных
R-критериев, новых checkbox markers0; прежние99 checklist hashes совпали99/99.
Сравнение SHA всех5984 исходных tracked/non-ignored untracked файлов показало
0 изменений и единственное добавление — этот отчёт. Branch/HEAD прежние,
`git diff --check` без ошибок. Проверка отчёта не исполняет продуктовый runtime.
