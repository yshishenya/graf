# Независимый source correctness/security review — metadata commit T116

Дата: 2026-10-03, Europe/Istanbul.
Canonical root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Risk/validation lane: **high-risk-product**, независимый обзор ограниченного
шага существующего T116; единственная разрешённая запись — этот отчёт.

## Решение — correctness/security первым

**Request Changes: один P1-блокер.** Перепроверен предоставленный main source
freeze refresh: все шесть individual SHA совпали с фактическими bytes.
Native execution не повторялся; окончательные результаты main ещё не предоставлены.
Это заключение по указанным ниже локальным bytes, не по committed tree HEAD,
не приёмка всей T116 и не разрешение commit/merge/build/install/release.

### P1 — ambiguous result не всегда запрещает запись через retained Files lease

Место: `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp:17–21`,
`:87–91`; связанный путь
`apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp:419–429`, `:466`.

Конкретная цепочка:

1. Birth успешно публикует g1/slot0. Его `publishIndex` после своего reopen
   сбрасывает `state_->failed = false` в Files.cpp:466.
2. Второй `publishIndex` может вернуть `notPublished` **до** temporary create:
   например, `openIndex` получает native hash failure в Files.cpp:419–420.
   Другой такой путь — отказ `BCryptGenRandom` в :427–429. Эти returns не
   выставляют `state_->failed`.
3. `copy == 1`, поэтому Metadata.cpp:90 правильно не отменяет
   `publicationStarted`. `reject` возвращает `ambiguous`, без snapshot,
   сохраняя actual lease и private pin. Однако он меняет только поле результата,
   а не writable/failed состояние этого lease.
4. После снятия временного native отказа `result.lease->nextBlockVersion(0)`
   всё ещё проходит проверку `writable/failed` и выдаёт следующий номер;
   `writeBlock` и `publishIndex` тоже не получают обязательный `writerFailed`.
   Через этот же публичный lease можно продолжить mutation или достроить
   singleton, не выполнив свежую reconciliation.

Это не гипотеза о JSON или будущей UI-интеграции: уже существующий public
result содержит mutable Files lease (`ProtectedCustodyMetadata.h:18`), а
реальный путь отказа оставляет его открытым для записи. Новое открытие object
при удержанном lease запрещено, но запрет нового открытия не запрещает методы
на уже удержанном instance. Дополнительное чтение singleton впоследствии
выставит failed; требование запрещает следующую запись **до** такого чтения.

Основание: contract `windows-protected-local-custody.md:131–135` требует
sticky failed writer и запрет next generation/GC после post-publish failure;
writer gate, таблица «Cancellation / ambiguity» и обязательные native cuts,
также требуют сохранённых artifacts и sticky отказа следующей записи до
reconciliation. Требования не менялись и не ослабляются этим finding.

Нужно при terminal ambiguous переводить **сам удержанный Files instance** в
необратимый запрет дальнейшей записи, сохраняя handles/pin/artifacts до release
или передачи полного владения. Применить ко всем post-start reject путям,
включая exact-target mismatch после внешне успешного snapshot reopen
(Metadata.cpp:98–102), а не только к native rename/flush ошибкам.
Не заменять это ранним закрытием lease или комментарием «caller должен помнить».

Минимальная проверка для main: успешный slot0 → hash failure только при decode
второго publish → `ambiguous` → убрать injected fault → `nextBlockVersion`,
`writeBlock`, `publishIndex` на retained lease возвращают `writerFailed`.
Проверить сохранность slot0/blocks, отсутствие ACK/snapshot, удержание
exclusion/pin и blocked singleton после release/restart. Уже имеющиеся
TU-local hash/flush hooks позволяют сделать это без production fault knobs;
здесь эта проверка не создавалась и не выполнялась.

## Что подтверждено чтением исходников

- Metadata.cpp:23–27 проверяет шесть metadata roles, null cancellation,
  empty/oversize value и generation exhaustion до candidate/chunk allocation.
  Codec role caps повторно используются: manifest4096B, queue4MiB, остальные
  четыре metadata roles64KiB. Семантика JSON явно оставлена caller.
- Metadata.cpp:34–44 резервирует общий pin до ожидания process-wide staging
  mutex и повторно проверяет cancel после lock. Одна staged dirty chunk≤256KiB;
  нет второго независимо разрешённого набора dirty metadata buffers.
- Base0 использует exclusive createNew. Update сначала получает полностью
  verified snapshot с generation==base; mismatch не пишет DATA. Имя object не
  создаётся из неподтверждённого JSON, Files confinement/ACL/identity сохранены.
- Полное значение записывается chunks≤256KiB через реальные codec DPAPI и
  Files write/flush/reopen. Только после всех DATA формируется полный index;
  промежуточные JSON ACK/частичные generations не публикуются.
- Отмена до первого publish даёт notCommitted и сохраняет checkpoint/orphans.
  После начала publish код не проверяет cancel между birth slots и при final
  reopen: g1 pair завершается, а поздняя отмена не превращает committed в
  доказанное отсутствие commit. Отказ второго slot правильно классифицирован
  ambiguous; дефект выше касается запрета последующей записи.
- Birth защищает slot0/slot1 независимо; update slot=`base%2`. Final reopen
  использует resolver обоих slots/всех DATA refs и сравнивает exact generation,
  length, count, version/envelopeBytes/flags, не принимает иной verified target.
  Writer cipher copies освобождаются перед reopen, plaintext chunk вытирается.
- Files.cpp:328–370 stream-обходит block-position versions без vector inventory,
  сохраняет orphan/unknown names, учитывает occupied canonical versions без
  доверия их содержимому, отвергает overflow, UINT64_MAX и ошибки enumeration.
  CREATE_NEW остаётся последним запретом overwrite при collision.
- Files.cpp:372–395 проверяет HRESULT disk query, actual geometry/overflow,
  actual capacity для `min(10'000'000'000, capacity/10)`, caller available как
  отдельное ограничение, pool unavailable, incremental peak и верхнюю границу
  per-file rounding `newFiles*(cluster-1)`. CallerTotal не процентная база.
  Literal PRD: `docs/prd-voice-layer-final.md:749`. Query не резервирует диск;
  реальные write/flush failures по-прежнему обязательны.
- Private pin объявлен до lease/snapshot и уничтожается последним. При
  обычном уничтожении результата snapshot/lease освобождаются раньше pin;
  move переносит admission, не удваивает его. Reject без actual lease снимает
  factory pin; reject с lease сохраняет его. Reader/Clone используют тот же
  `CustodyPin` с process≤32, не второй 32-owner счётчик.
- App vcxproj:96 включает новую Metadata TU. Это проверка project inclusion,
  не самостоятельное доказательство native compile/link или installed EXE.
- Новый refresh переиспользует единственный `codecFileError` в Files.h:15–25
  для обоих seal calls и Files; отдельного mapper в worker больше нет.
  Metadata.cpp:107 преобразует `std::system_error` в typed ioFailed, включая
  отказ staging lock. Это не исправляет P1: terminal reject всё ещё не
  устанавливает sticky failed на retained lease.

Native API facts отдельно сверены с официальными Microsoft Learn страницами
`GetDiskSpaceInformationW` и `DISK_SPACE_INFORMATION`: HRESULT, root volume,
Actual/Caller distinction, sectors-per-allocation-unit и bytes-per-sector.
Источники: https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdiskspaceinformationw
и https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-disk_space_information.
Эта сверка не runtime proof Windows support matrix или power-loss durability.

## Тесты — чтение, не execution

Прочитан предложенный final test freeze `ProtectedCustodyFilesTests.cpp`,
SHA-256 `3e73ed99d0b0f332c58d0ddfab85512ca09523bb3c38d1aa7ec89e362a50eaa5`:
real source TU wrappers,
birth/update/shrink, old-reader snapshot reuse, stale base, prepublish и
between-slots cancel, temp/published flush cuts, rename/completion/read faults,
lost slot1/no healing, orphan version, enumeration failure/exhaustion/overflow,
exact cap/+1 refusal для всех шести metadata roles,
owned-budget exhaustion, 4MiB full value, общий reader/Clone/result limit,
disk rounding/quota/query rejection. CMake использует реальный Files source
с TU-local native wrappers и общий production metadata object, не поддельный
переписанный persistence algorithm.

Дыры/замечания для финальной заморозки main:

- P1-путь выше отсутствует: first-slot success → second publish pre-create
  hash/RNG refusal → mutating APIs retained lease. Общие flush/rename cuts его
  не покрывают, поскольку сами выставляют Files failed.
- В текущем расширенном снимке main исправил ожидание pin exhaustion:
  FilesTests.cpp:385 ожидает `STG_E_INSUFFICIENTMEMORY`, как Reader.cpp:193.
  Прежнее `E_OUTOFMEMORY` было ошибкой теста, не production behavior. Это
  замечание снято чтением новых bytes; native PASS reviewer не заявляет.
- Final freeze закрыл прежние пробелы role caps и numeric overflow:
  FilesTests.cpp:330–332 проверяет canonical version=UINT64_MAX+1;
  :357–370 проверяет пять остальных metadata roles на cap/+1, queue — отдельно.
  :286–295 отказ native Read после обеих publications проверяет final reopen,
  а не только reopen внутри отдельного publishIndex. Эти замечания сняты.
- Не увидено целевых worker regressions для отмены именно после ожидания
  staging mutex и валидного, но не exact-target final snapshot. Это оставшиеся
  дополнительные проверки; native read failure не равен exact-target mismatch.

Сообщённые main native build результаты, basic focused PASS2.76s старого
source и expanded PASS3.97s до последних cap/reopen дополнений не являются
reviewer execution или PASS текущего final freeze. Финальный запуск main
pending. Coverage достаточен по перечисленным основным сценариям, но P1-ветка
sticky запрета не покрыта и final runtime PASS здесь не заявлен.

## Затем Ponytail

**Lean already. net: -0 lines possible.**

Не найдено безопасного удаления в данном ограниченном diff: используются
существующие Files/codec/allocator и native API, обычный mutex и общий pin.
Полное значение, оба birth slots, exact reopen, reserve и ownership нужны
принятому contract; они не speculative abstraction. Удалять их ради размера
diff нельзя. Исправление P1 — correctness, не Ponytail-сокращение.

## Привязка к исходникам

Пути в таблице от canonical root. SHA-256 локальных dirty/untracked bytes,
**не** committed HEAD. Source6 digest — SHA-256 stdout `shasum -a 256` для
первых шести путей ниже в указанном порядке (relative path, две пробельные
позиции перед path, LF):
`6da17d18950844e218ecd096af520ac7212eb9422f4d2d6c761a39c839f1b4bf`.

| Артефакт | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | `3afe6f936d70c6e94c104c4dad7772dc2a420a7f13f572ff359a13f68d362302` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `7ae138a79bd4d460454bdda115a7775d5094e26643b725955488a52ee6f71254` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.h | `fd3ecc8b1e2a10176a80e566fb998c6fd72acc835f9bee328bda362eaa3bc067` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `e987120c8f52b913fca20031134eeed9f06aee4c95e4d27db10b5bda785fbd60` |
| apps/windows/RecApp/Storage/ProtectedCustodyMemory.h | `13d3cff525a76976d1462f21848c088b154d01fa169553c48f0867bd9a81d64b` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `5f39f669cccb80e8be73582fc806ff6810e44003b5cb6ba28147c951571978c2` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `abcd92596cc2f763ecdced8cbd9f7ac277964be968a24d755eb3345fda7aba54` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp — proposed final freeze, runtime pending | `3e73ed99d0b0f332c58d0ddfab85512ca09523bb3c38d1aa7ec89e362a50eaa5` |
| specs/200-windows-desktop-app/checklists/review-2026-10-03-custody-writer-gate.md | `a8d3c46fdfa4c8afbd01c90a586261a6d38aac357d4152f5d2bfc6d37159185c` |
| specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |

Scope не включает UI async ticket/adoption, semantic parser, producer wiring,
GC roots, миграцию T117, приёмку T118 или закрытие всей T116. Полная цель Windows,
tasks и нормативные границы сохранены. Только этот report создан через
apply_patch; код, нормы, tasks, Git/issues, builds/tests/install/mic не менялись
и не исполнялись reviewer. Чужие dirty/untracked файлы не отменялись.

## Повторный независимый обзор — 2026-10-03, sticky writer fix

Этот раздел добавлен после исходного обзора. Прежний P1, его Request Changes,
старые source/test hashes и статус прежних запусков выше сохранены без изменений.
Исходный report:16605B, SHA-256
`d46803c02c1175bbee2bc0b21d0b997346dcfcadb106dc8802363d9cd9942866`.
Canonical root/branch/HEAD повторно проверены и остаются прежними. Нормативный
contract/writer gate и App vcxproj сохранили SHA-256 из предыдущей таблицы.
Risk/validation lane: high-risk-product; область остаётся bounded metadata
worker T116, не полная приёмка Windows. Execution reviewer не дублировал.

### Correctness/security — решение

**Approved для повторно проверенного source snapshot. P1 исправлен;
новых блокирующих correctness/security findings в этом изменении нет.**
Это source approval ограниченного слоя, не закрытие всей T116, не разрешение
commit/merge/install/migration/release и не результат полного final native/VS.

Проверен корень ошибки, а не только симптом теста:

- Metadata.cpp:17–23 теперь имеет единственный terminal `reject`: при actual
  retained lease вызывает `lease->blockWrites()`, иначе освобождает provisional
  pin. Состояние ambiguous определяется отдельно по publicationStarted;
  исходные error/nativeError не теряются. Блокировка применяется также к
  notCommitted с lease: отказ не оставляет instance пригодным для следующей
  mutation, но не переименовывается ошибочно в post-publication ambiguous.
- Files.h:77–78 объявляет `blockWrites() noexcept`; Files.cpp:328 устанавливает
  уже существующий `state_->failed = true`. Нет allocation/IO/close/reset или
  исключения в этом переходе. Handles, immutable blocks и private pin остаются
  во владении результата; раннего освобождения admission/exclusion не введено.
- Все отказы worker действительно идут через этот reject: role/input/base
  overflow, cancel до lock/после ожидания/после DATA/до publish, отказ factory,
  current snapshot/base mismatch, reserve, version enumeration, block seal/write,
  index seal, любой non-published result, final reopen и exact-target mismatch
  (Metadata.cpp:99–103), `bad_alloc` и `system_error` (:107–108).
  Единственный прямой успешный return (:104–106) следует за exact reopen.
  Нет отдельной ветки, способной вернуть retained failed result без блокировки.
- Общий failed guard стоит **до** codec/enumeration/disk/native write:
  writeBlock — Files.cpp:308; nextBlockVersion — :334;
  checkWriteReserve — :378; publishIndex — :420.
  readValidatedSnapshot — :481 также отказывает на том же failed instance.
  Единственный `failed=false` (:468) находится внутри успешного publishIndex,
  до которого повторный вызов на blocked instance уже не дойдёт.
- readIndex/readBlock сохраняют возможность bounded ciphertext inspection
  при удержанных handles. Это не ACK/выбор authority: snapshot resolver остаётся
  blocked до fresh instance. По диагностическому slot0 нельзя автоматически
  достроить birth или возобновить запись через старый lease.
- Сам private pin/result layout и reader/Clone общий счётчик не изменены.
  Failed result с lease сохраняет pin до release/полной передачи владения;
  при уничтожении snapshot/lease закрываются до private pin. Reject без lease
  не удерживает лишний process32 slot. Сериализация staging и process64MiB
  allocator сохранены; новая блокировка ничего не копирует и не освобождает.

Тем самым конкретный путь «slot0 success → second publish pre-create hash
failure» больше не оставляет writable lease. Та же точка исправления закрывает
RNG refusal второго publish и exact-target mismatch после внешне verified
reopen, даже если сам Files publish не успел выставить failed. Нормы о cancel
до publication/после начала, завершении g1 pair и полном exact reopen сохранены.

### Регрессия P1 и доступные runtime evidence

Прочитан текущий `ProtectedCustodyFilesTests.cpp:249–274`, SHA в таблице ниже.
После первого реального native rename `afterRename` включает hashOpen ordinal2:
ordinal1 проходит reopen первого slot, ordinal2 отказывает на decode второго
publish **до** temporary create. Это тот же production Files/codec flow,
а не отдельная имитация persistence algorithm.

Тест затем снимает injected fault и проверяет:

- ambiguous/hashFailed без snapshot; nextBlockVersion возвращает writerFailed;
- writeBlock и publishIndex возвращают writerFailed без новых native writes;
- slot0 остаётся readable/декодируемым, не уничтожен ради sticky отказа;
- retained lease по-прежнему исключает второго writer;
- block.0.1 сохранён, index.1 отсутствует;
- после release fresh reader отклоняет singleton, не выдаёт normal authority.

Этот тест достаточен для найденного P1 и его guard/retention последствий.
Прежнее широкое покрытие caps, 4MiB queue, birth/g2/shrink/old reader,
cancel/cuts/reopen/enumeration/overflow, actual-vs-caller reserve и общих
pin/memory limits не удалено. Дополнительные проверки staging-wait cancellation
и valid-but-wrong exact target остаются полезными, но не являются повторным
неисправленным P1: соответствующие source paths теперь используют общий reject.

Main сообщил настоящий RED до исправления: build0, assert на :258,
CTest exit8/0xc0000409. После исправления сообщил terminal GREEN session11602:
native CMake focused build0; ProtectedCustodyFilesTests1/1 PASS4.39s
(total4.45s); `STICKY_GREEN_TEST_EXIT=0`, source/test mirror/native hashes
проверены им перед build. Reviewer независимо сверил canonical bytes и
прочитал регрессию, но не запускал VM/build/tests и не выдаёт этот receipt
за собственный execution. Предварительный full36/36 старого теста не перенесён
на этот snapshot. Final host/native full и VS по сообщению main пока pending.
Install/реальный inventory/mic/network effects этой проверкой не разрешены.

### Затем Ponytail

**Lean already. net: -0 lines possible.**

Исправление — один noexcept переход существующего failed state и вызов из
общего reject. Новых зависимостей, счётчиков, retry/reconciliation abstraction
или второй реализации native IO нет. Удаление setter/вызова либо регрессии
снова откроет P1; безопасных сокращений не найдено.

### Привязка повторного обзора

SHA-256 локальных bytes; HEAD по-прежнему
`99b00a579c24b50e320465b69d9a296038bc544d`, не committed снимок этих файлов.
Source6 digest в том же порядке/формате, что выше:
`7ab14add6179730ed86d33d460dafb1ebdc3ab692e014f7ca4ed1d5138041044`.

| Артефакт от canonical root | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | `3afe6f936d70c6e94c104c4dad7772dc2a420a7f13f572ff359a13f68d362302` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `7e9c23aed46905cbcc61e473ecc0941a6d006b0ce9addcae35db648cb10cc6b9` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.h | `3b7e8fb45bce2ac3ff084af1e482a88c8f1ce277fe35b0149cf7a7383b614e0f` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `eb712a38f76eb5374f6ee4e3d964d15fb5ef92db2e212d20c77a166fd69bf142` |
| apps/windows/RecApp/Storage/ProtectedCustodyMemory.h | `13d3cff525a76976d1462f21848c088b154d01fa169553c48f0867bd9a81d64b` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `5f39f669cccb80e8be73582fc806ff6810e44003b5cb6ba28147c951571978c2` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `3d2c6dda5f1d7c8a01b455a214ea340d21dccfc92a6621d70b72534d1167fc34` |

Ownership соблюдён: только дополнение этого report через apply_patch. Прежний
текст/P1/Request Changes не переписан; код, нормы, checklist markers, tasks,
Git/issues/state, сборки/тесты/установки и чужие изменения reviewer не менял.

### Дополнение terminal evidence — 2026-10-03

После записи повторного обзора main сообщил terminal результаты текущего
неизменного source/test freeze из последней таблицы. Историческое pending
выше сохранено: на момент записи того раздела final receipts ещё не пришли.
Ни один запуск ниже не является execution reviewer, не проверкой установленного
приложения и не дополнительным полномочием на commit/merge/install/release.

| Main-observed проверка | Session | Terminal результат |
| --- | --- | --- |
| Native focused sticky RED→GREEN | 11602 | build0; FilesTests1/1 PASS4.39s, total4.45s; STICKY_GREEN_TEST_EXIT=0 |
| Final native CMake/full CTest | 58977 | build0; 36/36 PASS32.19s; FilesTests3.86s; FINAL_NATIVE_CTEST_EXIT=0 |
| Final host CMake/full CTest | 44286 | build0; 35/35 PASS19.85s |
| VS GrafWindows.sln Release/x64 | 57358 | build0; coreexe0; AEC3 identity проверена main; existing D9025 warning |
| Post-build mirror/native eight-path hash match | 85704 | FINAL_SOURCE_MATCH=True |

Сообщённый main AEC3 identity:
`846fe90a289f58b7c9303a635142aa2c7caa93e5`.
Сообщённый SHA-256 собранного, **НЕ установленного** app:
`c4920d176ae56f3a3aa30b38b55de6aae40ae1ffc06ec125f33d4cfdff4dbcb3`.
Reviewer не хешировал этот binary и не проверял его запуск/установку.

Две oversized combined prlctl команды по сообщению main завершились255
до создания guest session, без test execution; разделённые команды дали
terminal0. Это отдельно отмеченный отказ оболочки запуска, не замаскированный
native test failure или дополнительный PASS. Полные raw runtime receipts
reviewer самостоятельно не извлекал; источник этих результатов — сообщения
main в текущем обзоре. Canonical source/test hashes сверены reviewer отдельно.

**Итог повторного source review остаётся Approved, P1 снят для указанного
снимка.** Runtime evidence main теперь terminal, но вся T116, T117/T118,
installed app, реальный inventory, hardware/mic, network effects и release
по-прежнему не приняты этим отчётом. Затем Ponytail: net: -0 lines possible.
