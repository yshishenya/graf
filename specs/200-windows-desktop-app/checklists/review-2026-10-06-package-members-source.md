# Независимый SOURCE review Round253: own pair → sealed member Reader

Дата: 2026-10-06. Владелец: независимый reviewer.
Полоса: Feature200/high-risk-product storage, T116 dependency5; ограниченная
проверка исходного кода с единственным новым отчётом. Новых checkbox markers,
задач или параллельного gate нет. Requirements report не изменяется.

## Конечный вердикт — frozen253c

**SOURCE APPROVED / scoped GO для одного verified sealed member из held own
pair, direct protected SHA helper и общей очистки старого hash buffer.**
Открытые замечания: CRITICAL=0 / HIGH=0 / MEDIUM=0 / LOW=0.
Все 20 пунктов собственного requirements gate прослежены в границах этого
шага. Первоначально обнаружен один MEDIUM/P2: маскировка первого typed отказа
flat peer; для frozen253b выдан ранний NO-GO. Исправление main лично перечитано
в frozen253c; ниже сохранены исходное замечание и отдельное его закрытие.
Ни исходный NO-GO, ни новая проверка не заменены runtime PASS.

**FULL BOTH-MEMBERS / ASSEMBLY / PHASE / EFFECT AUTHORITY — НЕ ПРИНЯТА.**
Этот Reader не проверяет все refs обеих package slots, live capture recovery,
actual normal WAV/AAC/manifest, trusted prefix/short predicate, аккаунт/epoch,
network/upload/playback admission, bootstrap/intent/barriers, deletion/GC.
Подключение приложения, working profile, installed/native execution и выпуск
не приняты. T116 остаётся открытой; T117/T118/T120 и H250-1/H250-2 не закрыты.

## Снимок и метод

Единственная рабочая копия:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Лично проверены branch `codex/200-windows-followup` и HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty work сохранён;
идентичность рассматриваемого кода задают файловые SHA, а не один HEAD.

Область diff — ровно восемь файлов из задания, относительно неизменного
baseline `/tmp/graf-f200-member-reader-baseline.aUWupS`, сопоставленного по
basename. Полностью прочитаны incremental hunks всех восьми файлов; прочитаны
actual Reader/hash/error/allocator/lifetime paths и непосредственно применимые
Files/Tree/Pair/Codec/Primitives callers. Это не повторный общий аудит app
readers/finalizer, который выполняет main.

Прочитаны и применены `code-reviewer`, затем `ponytail-review`: первая проверка
охватывает correctness/security/errors/lifetime/budget/testability, вторая —
только лишнюю сложность. Использованы root guidance, действующий high-risk lane
и собственный [requirements gate](review-2026-10-06-package-members-gate.md),
особенно R01–R20, base §8.1 и packed §6.1. Дополнительных продуктовых решений,
schema fields, допусков или permission mechanisms не введено.

Requirements report SHA-256 неизменен:
`cf6391d837687df20f555c16caeb2f482b0fbb040fbab74488ba4983e23f1276`.

Лично вычислены hashes всех **171/171** файлов из final manifest
`/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI/source-members-round253c.json`:
несовпадений0. SHA-256 самого manifest:
`303d2204a278963e8e9b109a3bf20b741737773f7baad3ee31991cd3747aa577`.
Проверка остальных163 файлов — проверка идентичности manifest, не расширение
incremental review и не принятие их реализации.

Первоначальный253 →253b меняет только NativeHashFailureTests и FilesTests:
distinct old/current bytes/SHA и сброс внешнего ComPtr внутри Read.
253b →253c меняет только Reader.cpp и FilesTests; остальные6 файлов совпали.
Manifest253b был лично проверен171/171 до поправки, SHA-256:
`6c5f0c2e0e8882c9a3a65f403217908e5a0fb4208b113380d77272a437534aed`.

## Исходное замечание и narrow fix — история NO-GO253b

### M253-1 / P2 / MEDIUM — первая причина peer отказа заменялась recoveryRequired

Точное место в253b:
`apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp:312–313`.
Reader.cpp SHA-256 той версии:
`3dbcf51836002c8e0039b26eb367478952f6af127eeb8b04239bc68b436d4e3b`.

Первоначальный код объединял `state != verified || !peer.generation` и
возвращал `{nullopt, recoveryRequired, snapshot.nativeError}`. Shared validator
в `ProtectedCustodyFiles.cpp:535–551/564–578` может вернуть trustedPrefix для
canonical/media при валидном одном index и повреждённом другом DATA/index.
При этом `snapshot.recoveryError/nativeError` содержат исходную причину.
Например, invalidContent peer превращался в recoveryRequired; отсутствие
DATA другого slot аналогично теряло ioFailed при сохранённом FILE_NOT_FOUND.

Stream не выдавался, unsafe success не обнаружен. Однако отсутствие index/
generation и наблюдённая порча/ошибка DATA — разные причины. Первоначальная
typed ошибка скрывалась на новой границе, вопреки own gate R15 и правилу
сохранения первого observed fault. Это нарушение error contract нового
consumer, не новое требование к схеме или восстановлению. Первоначальный
вердикт: **SOURCE NO-GO253b**, без ожидания SDK/native/Debug результатов.

Предложенное минимальное исправление: разделить два условия. Для non-verified
snapshot возвращать исходные recoveryError/nativeError без результата;
для verified singleton с peer.generation0 оставить recoveryRequired.
Unavailable exact generation также остаётся recoveryRequired. Ни новый
scanner, ни fallback, ни public proof API не нужны.

### Повторное чтение253c — M253-1 RESOLVED, только source

Текущее точное место:
[Reader.cpp:312](/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp:312).
Строки312–313 теперь возвращают original recoveryError/nativeError для
non-verified snapshot; строка314 отдельно отвергает missing peer;
строки315–317 сохраняют unavailable generation refusal и actual peer selection.
Ни ошибка, ни default stream не выдаются как healthy partial result.

Actual regression source:
`apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp:1499–1506`.
После package generation7 выбран здоровый media ref generation1 в slot0;
удаляется DATA generation2 **другого** physical member index. Новый overload
обязан вернуть no value, exact `ioFailed/ERROR_FILE_NOT_FOUND`. Это6 непустых
случаев: schema1/2 × lengths1/65536/65537. Затем отсутствие index.1 отдельно
проверяет recoveryRequired singleton, включая length0. На253b этот новый
assertion получил бы recoveryRequired и обнаружил исходное маскирование.
Полного CTest/RED исполнения reviewer не проводил: это source causal proof,
а не заявление о выполненной регрессии.

Поправка соответствует предложенному narrow fix и не ослабляет BOTH validator.
Новых конкретных дефектов в конечном incremental scope не найдено.

## Прослеживаемость собственного gate20 к конечному коду

Обозначения: `Reader` = Storage/ProtectedCustodyReader.cpp; `Hash` =
Storage/Sha256.cpp; `Files`/`Tree`/`Pair` — существующие Files/Tree/Metadata APIs.
«Соответствует» ниже означает source этого ограниченного шага, не runtime PASS
и не выполнение перечисленных отдельно full-package обязательств.

| ID | Конкретное доказательство / сохраняемая граница | Source итог |
| --- | --- | --- |
| R01 | Reader.h:20–24/35–40 различает byte checkpoint, own-pair sealed member и authority; result не содержит новых admission flags | Соответствует |
| R02 | Reader:275–278 адресует любой physical slot0/1 и его refIndex, не только selectedSlot. Полный обход всех refs BOTH остаётся assembly T116 | Соответствует границе шага |
| R03 | Reader:286–288 берёт store/directory из held own value, role/object из её ref; packed context:298. Нет caller-created descriptor/bool verified/path из JSON | Соответствует |
| R04 | Reader:279–280 требует sealed stamp; flat:315–320 exact actual generation/length; packed:294–304 exact descriptor;330–332 whole logical digest | Соответствует |
| R05 | Owner::open(readExisting) и Tree::verifyRetained:299–305; actual both-head closures плюс retained old root, без fake historical head. Sha helper читает retained descriptor | Соответствует |
| R06 | Files.h:104–110 exact friend только нового overload; Reader:307–314 reuse private BOTH DATA validator под writeExisting lease. trustedPrefix/singleton stream не выдаются | Соответствует после M253-1 fix |
| R07 | Reader:315–317 выбирает current или actual decoded peer; absent exact generation → recoveryRequired. Нет реконструкции по immutable block names/version или second scan | Соответствует |
| R08 | Nullable sealed length допускает structural0, но не normal package. API не принимает WAV/AAC/manifest/normal cross-member semantics | Соответствует границе шага |
| R09 | Reader:279 явно отвергает live ref, даже если ref length/stamp отсутствуют корректно по schema. Capture/finalizing recovery не добавлены | Соответствует |
| R10 | Можно проверить sealed bytes degraded/discard ref, но нет phase/short/reason/marker interpretation или upload/cleanup effects | Соответствует границе шага |
| R11 | ReaderState:35 держит pair первым полем; files/packed закрываются до pair.325–329 помещают её в общий state; Clone:215–224 разделяет этот state, независимый cursor/pin | Соответствует |
| R12 | Public result — существующий CustodyReader/IStream; Write/SetSize:140–143/165 denied; flat Files private и blockWrites:321. Packed Owner не выходит наружу из нового API | Соответствует |
| R13 | Hash:218–246 проверяет cursor0, exact chunks, EOF probe и full CNG digest; Reader:330–337 сравнивает SHA, требует successful Seek0 и cancel check до return | Соответствует |
| R14 | Reader:282–284 existing job/pin до member IO; Hash:215–217 charged64KiB до Read; state/control-block/Reader через existing CustodyAllocator. cache/jobs/pins/limits не увеличены | Соответствует |
| R15 | Прямые Files/Tree errors сохраняются; non-verified recovery cause:312–313 теперь не маскируется. Hash own CNG create/update/finish → hashFailed; failed COM Read/Seek → ioFailed с HRESULT; cancel/allocation без result | Соответствует после M253-1 fix |
| R16 | Hash:179–183 старый stack64KiB wipe guard на всех exits, allocation strategy прежняя.217 новый CustodyBytes buffer с существующим wiping destructor. Нет plaintext file/fallback | Соответствует |
| R17 | Ни один из8 diff не добавляет account/session/epoch grant, network/delete/GC; existing Reader.h caller admission contract сохранён | Соответствует границе шага |
| R18 | Worker-only API, owned cancellation и actual synchronous lifetimes; no backend/interface/callback configuration/schema/lifecycle changes | Соответствует |
| R19 | Final253c171/171 hashes совпали; новые test bytes и source отдельно от исторического runtime. Terminal execution final cohort ещё не принят reviewer | Source evidence соответствует; execution отдельно |
| R20 | Изменение связано с existing T116 dependency5 и её требованиями;8 scoped файлов, один новый отчёт, без новых задач или дублирующего gate | Соответствует |

Проверены actual failures: null pair/cancel, slot/ref bounds, live отказ;
Files/Owner/context/closure failure; no peer/exact generation; wrong length/SHA;
allocator/job/pin admission; Read/Seek/CNG failure, short/extra/invalid got,
cancellation. Ничто из этого не возвращает частичный digest или stream.
Существующая COM граница Reader выдаёт HRESULT; generic failed IStream
Read/Seek в hash helper имеет именно согласованную ioFailed семантику.
Это не новое утверждение, что произвольный IStream передаёт typed ошибки
всех своих внутренних codecs. Public error/interface redesign не требуется.

Лично проверено владение при возвратах/throwing allocation: pair остаётся
function parameter до принятия state, затем хранится в shared ReaderState;
new Reader использует existing charged allocation/pin; helper держит ComPtr
и owned cancel до окончания синхронных Seek/Read/CNG. На отмене выполняющийся
native call не обрывается освобождением буфера/owner. Last Clone release
освобождает member прежде parent. Не введено общей ownership/GC registry.

## Source тестов, без переноса execution PASS

| Файл / строки | Новое покрытие, прочитанное в source |
| --- | --- |
| NativeHashFailureTests.cpp:75–165 | Direct helper lengths0/1/64KiB/64KiB+1, CNG create/update1/update2/finish, early/extra/failed/short/invalid-count/unknown-HRESULT/Seek/cancel, null inputs, jobs4/owned memory exhaustion, usedBytes restoration |
| NativeHashFailureTests.cpp:162–164 | Внешний ComPtr.Reset внутри Read: helper held ComPtr сохраняет actual COM completion до digest/EOF. Не borrowed pointer lifetime |
| FilesTests.cpp:1427–1498 | Schema1/2, обе physical slots, current/lower distinct0x57/0x58 и distinct SHA для непустых inputs, cursor0 после hash, readonly, pair+member writer exclusion через Clone, bad hash/length/identity, unavailable generation |
| FilesTests.cpp:1499–1506 | Healthy chosen ref не скрывает missing DATA peer: no value и original ioFailed/FILE_NOT_FOUND; missing index singleton отдельно recoveryRequired |
| TreeTests.cpp:241–292 | Protected schema2 ref к историческому root после новых generations3/4; обе metadata slots, original3 bytes вместо current5, cursor0, Clone parent/member exclusion, wrong SHA/container/future stamp, corrupt historical DATA |

Эти assertions добавлены к прежним cases; прежние проверки не ослаблены.
Ни старые50 PASS, ни прежние retained-root/pair результаты не принимают новые
member/hash bytes. Прочитанное source покрытие не означает полный runtime
fault/wipe/Debug/SDK matrix PASS. В частности, execution evidence полной
матрицы из requirements report остаётся предметом проверки main, не выдано
от одного чтения новых tests и не сокращает full T116 acceptance.

## Ponytail review — только сложность

Лишних зависимостей, proof classes, interfaces, callback options, публичного
audio metadata API, второго scanner/selector/hash backend или speculative
систем не обнаружено. Existing NativeHash расширен маленьким typed finish;
новый native IStream helper не строит std::streambuf adapter. Exact friend
переиспользует existing BOTH validator; единственный общий state сохраняет
leases/Clone. Проверка EOF и разделение ошибок не предлагаются к удалению.

Ponytail-only verdict: `Lean already. Ship.` **Только оценка формы diff**, не
разрешение runtime/release/full package. `net: -0 lines possible.`
Correctness M253-1 рассмотрен отдельно и закрыт только после actual source fix.

## Идентичность восьми файлов: baseline → final253c

Пути ниже относительно `apps/windows/`. Final incremental diff: +405/-6 lines;
новых production файлов0. Для source приёмки действуют именно эти bytes.

| Файл | Baseline SHA-256 | Final253c SHA-256 |
| --- | --- | --- |
| RecApp/Storage/Sha256.h | `e51b352aa346036708ad30867fed412b67000434b87d88aeb02c45549c43cc60` | `5e1e0691eea152ad7877ee663e9bc3ac4d11698a692880ee24e179f881f633c0` |
| RecApp/Storage/Sha256.cpp | `af51b5cef94a0855773c1310b05bc7ef1d13a65939d2f8bc4b960ff403f0a4d2` | `84032d4a6b8f6a8c2e52e9bdd194d1cffe70050216cc3b392964ff46798ae76c` |
| RecApp/Storage/ProtectedCustodyFiles.h | `cb0e4eb64f72c0b2332c9adee8f0d3824cd8063a5ef4e2bed5458293b65fdfa1` | `9c230612de5ab10a5cfb6463e1434b3efdd7267db4435826faee204655dc87f6` |
| RecApp/Storage/ProtectedCustodyReader.h | `c76be03233949ff2779740dbc8a4f32eaa81da1921ff48f8a9ebcc60e532479d` | `a0a899339cac7f401791ed5355a1a53464a542b7e9cc034bf404aada724389aa` |
| RecApp/Storage/ProtectedCustodyReader.cpp | `0d38daf7ce709d112ca14edb3e87cb7a4a774c562ef48984c2ef91ad265977b9` | `8c04a690f0511a4073717f0dbce837e7ab76a760a3eeb66fb925dc6af83f26de` |
| Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp | `b13c2eeb1972afe6e927044072241044e0b39e9e8e6233b598537e3e90d948fe` | `1e7cf8102a89373cc884749063dba8dea6c795deb9a8c8a7c5b9a31d242e3478` |
| Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `f6424220ccfb4067ee7204eaec0d05275ff4273a3da981a570f514ada143d08b` | `5a80927dcbca4c3f5be17dee09e10d24c07daf1129154c7cfe8c0d17d9d4e1c7` |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | `c52782725acf10d1a3faaa9a0815c14177b99380038265b74dede8bd3e6c06b3` | `5e376d0b9f04b76636f2eee552ff60d5ce2832fd2d95c5c58266c24a9ae6878e` |

## Execution и сохранённые старые gates

Main сообщил исходный native8/8 за33.14s и portable build terminal0.
Это исторический контекст исходной253, не execution final253c. Усиление двух
tests в253b, затем изменение Reader/FilesTests в253c инвалидируют применение
старых8/8 к новому набору. SDK/live/Debug receipts не открывались и не запускались
reviewer; terminal SDK/build/test acceptance не утверждается и не ожидается
для этого source verdict. Нужен отдельно привязанный к253c execution evidence.

Прежние100 checklist Markdown files перед записью:410 checked/10 unchecked.
Новые checkbox markers0. Исторические unchecked не редактировались и не
превращаются в новый PASS. Round252 own BOTH payloads и Round251 retained
root closure использованы как свои ограниченные prerequisites, не как
готовая проверка всех actual members или normal/effect authority. Requirements
20/20 design GO не принимается автоматически за implementation GO: M253-1
это продемонстрировал. H250-1/H250-2 и full assembly pending сохранены.

Единственная запись reviewer — этот новый отчёт. Код, requirements report,
spec/plan/tasks/старые checklists, GitHub, runtime и рабочий профиль reviewer
не изменял. Main выполнял указанные поправки и параллельные проверки сам.
Build/test/VM/app/install/network/GC/commit/push reviewer не исполнял.

Конечное решение: **scoped SOURCE GO253c, M253-1 resolved; открытых findings0.**
Оно принимает только examined8-file diff и exact sealed member byte/lease
bridge. Полная T116 цель не сужена; execution и дальнейшая assembly/effects
требуют собственных доказательств и решения parent после личного чтения отчёта.

После сохранения отчёт лично перечитан целиком. Повторная проверка:
20 уникальных R-строк, новых checkbox markers0, trailing whitespace0;
final manifest171/171 совпал, прежние100 checklist hashes и spec/plan/tasks
совпали103/103 с предзаписным снимком. Branch/HEAD сохранены;
`git diff --check` восьми исходных файлов без ошибок. Проверка самого отчёта
не исполняла runtime. Новый Quickstart appendix не входит в этот SOURCE verdict:
его DOCS review остаётся отдельным поручением, не условием partial bridge GO.

## DOCS appendix Round253 — отдельное ограниченное поручение, 2026-10-06

**DOCS APPROVED / scoped GO; CRITICAL=0 / HIGH=0 / MEDIUM=0 / LOW=0.**
Приняты только содержание, команды и границы заявлений новых трёх разделов.
SOURCE GO253c выше не пересматривается; это не повторное чтение реализации,
не execution review и не full-feature approval. Main лично прочитал SOURCE
GO7e56ea; reviewer не проверял receipts/EXE/NTFS/mirror/live source повторно,
runtime не запускал и не ожидал для DOCS решения. Новых задач/gates/checkbox
markers нет; требования partial bridge не расширены до all-feature acceptance.

### Прочитанная конечная область

| Документ / точное начало нового раздела | SHA-256 всего документа на DOCS review |
| --- | --- |
| quickstart.md:791, «Защищённое описание → точный запечатанный файл» | `26d4595412c10968706dc3eaadd1fd242e146e1d1e954d0ebc452a6ac0ee2747` |
| validation-2026-10-02.md:10311, «Раунд253 — собственное описание → точный sealed member», включая10417 «Окончательный actual reread253c» | `aa9ac2c37d54a232c436e9741992067e7b1b881217cfa992f72610d021759439` |
| changes/unreleased/F200.yaml:1826, release_notes_round253_protected_sealed_member, включая четыре конечные строки Debug/SDK/source | `945b0167a1a8d7ffd53d25ff9a6d9a33d96b9a7aa19c2905da3c3568b26174e9` |

Разделы прочитаны целиком, включая последнее дополнение main. Остальной
Quickstart прочитан только для непосредственного command setup: host
prerequisites, root Developer PowerShell и существующий configure того же
`out\windows-package-contracts` в строках688–694/722–730. Прежняя validation
история и другие release notes не являются текущим DOCS scope.

### Проверка команд и требований

- Release build перечисляет ровно8 targets; anchored CTest regex перечисляет
  те же8 имён без лишних или отсутствующих. Debug build/CTest аналогично3/3.
  Сопоставление выполнено статическим разбором документированных команд,
  не их исполнением и не новым source review CMake/tests.
- `$taskBuild` соответствует существующему x64 configure из предшествующего
  setup. Build `--config Release/Debug`, CTest `-C Release/Debug`, `-j 1`,
  `--timeout 300`, `--output-on-failure`, exit-code throws и последовательность
  Release→Debug согласованы. `-j 2` относится к build, не конкурентному CTest;
  `/nodeReuse:false` сохранён. Команды подразумевают уже configured tree,
  как установленный setup runbook, и не разрешают параллельный native test/build.
- Явно требуются terminal8/8 и3/3 с matching frozen source/EXE hashes.
  Regex/exit0 сами по себе не называются выполнением нужного числа cases.
  Нет установки, подписи, запуска приложения или доступа к рабочему профилю.
  Синтетические/generated files не называются записью микрофона.
- Flat current/actual peer, exact generation/length/SHA, BOTH physical DATA,
  packed both heads/retained closure, rewind0 и parent/member Clone lifetime
  описаны в пределах accepted SOURCE. Live refs и недоступный старый flat
  index не превращены в sealed success. M253-1 и исходная причина peer отказа
  отражены без нового repair/fallback допуска.
- Direct hash64KiB charged+wiped и общий старый stack wipe описаны без
  изменения прежней allocation семантики. CNG/IO, EOF/count/cancel/owned/job
  проверки не названы исчерпывающими allocation/rewind/wipe cuts даже в Debug.
  Не введены новые budgets, численные аудиодопуски или schema/backend/lifecycle.
- One-member byte proof явно не принимает refs BOTH metadata slots в целом,
  live recovery, actual manifest/formats/duration/trusted prefix/positive short
  predicate и normal package. Account/epoch/effects, upload/playback/delete/GC,
  V5/MF/queue wiring, T117 migration, H250 и полная T118 приёмка сохраняются.
  Release notes не объявляют encrypted application, готовый выпуск или перенос
  существующих записей. Это не сокращение T116 или all-feature convergence.

### Execution statements — только документальные заявления main

Validation различает первоначальные253/253b8/8 и окончательные253c bytes;
не заявляет executable RED новой peer-DATA регрессии вместо source causal proof.
Final Release8/8 за32.72s, Debug3/3 за45.46s, portable46/46 за21.59s и SDK
restore/build0 обозначены как **MAIN-EXECUTED**, не независимо воспроизведённые
reviewer результаты. Portable не принимает DPAPI/sharing, SDK Build не равен
Rebuild/package/sign/install/launch. Warning D9025 сохранён. Старый full50
Round252 явно исторический; новый full50 не заявлен. Counts/durations и
границы release notes согласованы с validation и latest user handoff.

Первоначальная запись pending actual reread сохранена как история, затем
append10417–10433 документирует MAIN45177/597967 terminal0 и matching171/178,
8 Release/3 Debug EXE/SDK app. Указанные receipt SHA5526a114…/f0af2934…/f57c464b…
и app ec40e07… прочитаны только как текст документа. Reviewer их не вычислял,
не открывал actual receipts/EXE и не выдаёт этот DOCS GO за independent runtime
receipt/source reread. Проверка actual execution принадлежит main и не является
условием этого отдельного решения по документации.

### Идентичность SOURCE prefix и сохранение старого отчёта

Якорь `f2b42478ac5935a0d415f350fdc205ed8c118ffddc56c75e08af6ad5cd178ec8`,
упомянутый validation:10351–10352 и заданием, лично проверен как SHA-256
**первых234 строк SOURCE prefix**, включая исходный terminal GO253c.
Он не является checksum всего242-строчного файла перед DOCS append.
Полный pre-DOCS файл с прежним post-save verification footer имеет SHA-256
`46968d257b8f95dba224c709c6873a9b7b098d1a1d672506965f11d874b2d842`.
Это уточнение области documentary hash, не смена SOURCE verdict или runtime
identity. Все242 прежние строки, не только обязательные234, сохраняются
byte-for-byte. Нельзя использовать prefix hash как full-file hash после append.

T116/full assembly, T117, T118, H250-1/H250-2 и working-profile блокировка
остаются без изменения. Tasks120/93/27 не переотмечены. Новых checkbox markers
в трёх рассмотренных разделах0; исторические markers не переписаны.
Единственная запись reviewer — этот append. Quickstart/validation/F200,
requirements, spec/plan/tasks, исходники, GitHub и runtime reviewer не изменял.
**Конечный ограниченный DOCS GO не требует полного Feature200 PASS и не даёт его.**

После записи DOCS append лично перечитан целиком. Проверены сохранение всего
прежнего242-строчного prefix, exact SHA первых234 строк, отсутствие новых
checkbox markers/trailing whitespace и совпадение106/106 предзаписных hashes
старых checklists и охраняемых документов. Tasks лично пересчитаны93checked/
27open=120 без изменения. Ни одна из этих проверок не исполняла команды runbook
и не открывала runtime receipts или исходники реализации.
