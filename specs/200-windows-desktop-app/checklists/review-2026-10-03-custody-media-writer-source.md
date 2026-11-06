# Независимый source review T116 — worker-only media writer

Дата: 2026-10-03, Europe/Istanbul.
Canonical: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Risk/validation lane: `high-risk-product`, независимый обзор исходников
существующего последовательного среза T116, не новый облегчённый lane.

## Решение и границы доказательства

**Approved — только correctness/security текущего bounded source snapshot.**
Подтверждённых блокирующих дефектов нового worker core не найдено.
Это не final validation/acceptance: expanded native test execution ещё pending
на момент записи, а указанные ниже пробелы тестовых оракулов не закрыты.
Старый metadata Approved и его RED→GREEN не перенесены на новый writer.
Новых RED текущего поведения reviewer не исполнял и не заявляет.

Область: Writer.h/.cpp; общий DirtySlot в Memory.h; его admission в Metadata.cpp;
перенос CustodyCommitState из Metadata.h в Files.h; фактически переиспользуемые
Files/Codec/Reader и включение writer TU в CMake/App vcxproj. Полностью прочитаны
code-reviewer и ponytail-review skills, новый requirements gate; прослежены
все методы writer и их terminal errors. Correctness/security рассмотрены
перед Ponytail. Принятые custody §§3–7 и project guidance/risk lane сохранены.

Requirements gate Tesla: PASS112/112, CRITICAL0/HIGH0 — результат другого
reviewer требований, не наше исполнение 112 runtime сценариев.
Хеш gate ниже локально подтверждён; нормативный contract не изменён.
T116/T117/T118 остаются открытыми. COM/IStream/MF adapter, V5/producer hookup,
async ticket/adoption actor, нормальный sealed package, migration/GC,
upload/playback/delete, hardware/installed app и полная Windows цель не приняты.

## Correctness/security: прослеженные пути

Ссылки далее — относительно canonical root, номера строк нового Writer.cpp
с явным include `<system_error>`.

- `Writer.cpp:132–158`: роли только canonical/media/playback; null cancellation
  и exhausted base отвергаются. Pin до Files IO; base0 использует createNew,
  не recovery missing/corrupt. Existing base принимается только из verified
  snapshot с exact generation; candidate и committed являются отдельными
  charged значениями. Ошибка open уничтожает provisional State, закрывая
  handles до Pin; произвольного writable root/URL/plaintext пути не добавлено.
- `Writer.cpp:104–123,165–185`: 64GiB проверяется до reserve/IO, сумма write
  проверяется через `bytes > limit-offset`. Большой Write проходит частями
  не более256KiB. Размер расширяется лишь до текущего принятого фрагмента:
  canonical checkpoint на полной границе не объявляет будущие bytes ZERO.
  Write означает accepted working bytes, не durable ACK всей операции.
- `Writer.cpp:85–102,104–123`: смена dirty position сначала seals/flushes
  текущую immutable version и сохраняет candidate ref, не публикуя index.
  Extension короткого DATA tail загружает старые exact bytes, увеличивает
  payload с ZERO и позже создаёт новую version. Shrink до boundary отбрасывает
  удалённый dirty block; shrink внутри блока загружает нужный boundary,
  затирает обрезанный суффикс и уменьшает payload. Повторное extension получает
  нули, а не прежний отсечённый plaintext. ZERO entries добавляются явно;
  отсутствующий/битый DATA не превращается в ZERO. Старые версии не удаляются.
- `Writer.cpp:69–83`: reserve перед content write включает block overhead и
  будущий bounded index; version берётся из реального streamed orphan inventory.
  Реальные Codec и Files seal/write/flush/reopen используются повторно; нет
  нового codec, перечисления всего inventory в памяти или plaintext spill.
  Отказ seal/reserve/enumeration/write проходит через общий sticky fail.
- `Writer.cpp:188–220`: readAt читает candidate, включая собственный dirty
  block и explicit ZERO. DATA проходит реальную integrity validation.
  EOF возвращает exact short count, не расширяет объект. При ошибке после
  копирования весь уже скопированный caller prefix затирается, value отсутствует;
  невыданная часть caller buffer не используется и не затирается произвольно.
  Проверка cancellation после копирования также очищает prefix.
- `Writer.cpp:223–259`: flushDirty → seal alternate slot `base%2` → reserve →
  последняя cancellation check → publishIndex → независимый full validated
  reopen. После начала publish cancellation больше не проверяется в этой
  операции: finish/reopen заканчивается committed либо ambiguous. ACK требует
  verified state, exact target generation/length/count и равенства всех
  version/envelopeBytes/flags; lower generation/trustedPrefix/иной valid target
  не принимается. Cipher и dirty copies освобождены перед final reopen;
  candidate и предыдущий committed checkpoint остаются charged/retained.
- `Writer.cpp:48–68,226–244`: любой terminal mutation/read/checkpoint error
  устанавливает State.failed и вызывает реальный Files::blockWrites, включая
  ранние codec/native/allocation ошибки, которые сам Files мог вернуть до
  установки failed. Post-publish reject сохраняет ambiguous; повторный
  checkpoint воспроизводит эту классификацию и target, без новых записей.
  writeAt/setSize/readAt также блокируются. Files guards действуют до
  nextBlockVersion/checkWriteReserve/writeBlock/publishIndex, не только в result.
  Committed snapshot, handles и orphan artifacts не сбрасываются при отказе.
- `Memory.h:34–49; Writer.cpp:29–46,89–91; Metadata.cpp:35–49`: четыре общих
  DirtySlot/process, не четыре на объект. Writer получает slot до owned dirty
  reserve и чтения plaintext; Metadata получает тот же slot до factory/content
  IO. Его staging mutex по-прежнему ограничивает metadata одним staging block.
  State::clearDirty сначала wipe/deallocate, затем release slot. Ошибка не
  выдаёт допуск другому writer через ранний reset retained resources.
- `Memory.h:14–30,54–89; Writer.h:15–21; Writer.cpp:29–46`: shared Pin32 и
  allocator64MiB включают actual capacity, candidate/committed indices и
  transient owned buffers. При уничтожении writer dirty plaintext очищается,
  owned snapshots/buffers и Files закрываются прежде Pin. Destructor не делает
  IO. Caller обязан удержать actual writer, включая failed state, до adoption
  или revalidation, а last release выполнять на worker. Сам scalar commit
  result не является owning async completion; будущая обвязка обязана это
  обеспечить и здесь не объявляется реализованной. Native DPAPI/MF allocations
  не выданы за доказанную часть owned64MiB.

Files.cpp остался byte-identical принятому sticky fix. Его reserve использует
HRESULT API, actual disk geometry/ActualTotalAllocationUnits, доступность с
caller quota и reserve=min(10,000,000,000B,10% actual capacity), rounding
`newFiles*(cluster-1)`. CallerTotal не является physical capacity.
Перенос enum в Files.h не меняет значения/семантику Metadata result.

## Actual tests и остающиеся пробелы

Прочитан текущий `ProtectedCustodyFilesTests.cpp`, в том числе
`protectedMediaWriter:183–314`. Тестовый TU включает реальный Files.cpp и
Sha256.cpp с локальными native wrappers; Writer/Metadata/Codec — production
TUs через common objects. CMake исключает отдельные дубли Files/SHA объектов
для native fault TU. App vcxproj включает `Storage\\ProtectedCustodyWriter.cpp`.

Есть: обе media/playback роли; write/read/extend/shrink/header rewrite;
retained old reader; canonical full-block ACK и explicit tail checkpoint;
setSize0/overflow write; sticky write/checkpoint и held Files lease после faults;
cancel после rename с successful finish; четыре dirty writers, отказ пятого,
shared Metadata admission до IO и actual release; 24 mixed-size oracle;
native read fault после copied DATA/ZERO prefix с его wipe; 32 writer Pins,
отказ33-го без writes и shared reader denial; owned memory balance после release.

Ниже — конкретные **P2 test-coverage observations**, не доказанные production
дефекты. Их RED-оракулы нужны против удаления/порчи соответствующих guards;
они не названы выполненными RED текущего кода. До полной T116/T118 приёмки
не следует считать эти ветви доказанными только зелёным Files backend тестом.

1. `Tests:228–238` проверяет лишь `state != committed`; hash/flush по ordinal1
   попадают до publish, renameCompletion — после начала publication. Удаление
   присвоения ambiguous в Writer.cpp:244 этим assert не ловится. Дополнить
   существующий real fault loop точными ожиданиями: early block flush/hash
   → notCommitted; renameCompletion → ambiguous, target1, generation0;
   второй checkpoint → ambiguous/writerFailed с тем же target и zero writes.
   `afterRename` может поставить readFailed ordinal1 для publish reopen;
   после successful publish reopen native read fault в independent resolver
   также должен дать ambiguous, а не notCommitted. Проверить setSize/readAt
   после отказа, сохранность block/index, lease exclusion и release.
2. Direct writer paths `open(base>0)` и exact-target mismatch пока не проходят
   через protectedMediaWriter tests. Создать/ACK g1, отпустить writer, открыть
   writer(base1), изменить header/tail и ACK g2; old reader должен остаться g1.
   Попытка open(base1) при actualg2 должна отказать conflict до content writes;
   trustedPrefix не writable. Для exact mismatch использовать TU-local native
   read hook, который только при final resolver reopen выдаёт иной valid
   same-context index с тем же generation/length, но другой existing DATA ref;
   physical publish readback оставить реальным. Оракул: ambiguous/conflict,
   generation остаётся base, no next mutation. Простая hash failure не
   проверяет equality branch; новый production hook для этого не нужен.
3. Writer-specific prepublication cancellation и quota/bound admission:
   afterFlush первого dirty DATA ставит cancel → checkpoint notCommitted,
   old generation retained, нет нового published index/ACK, writer sticky.
   Отдельные fixtures с зарезервированным остатком64MiB: writeAt/resize или
   checkpoint allocation refusal → allocationFailed, no later writes,
   actual charge/Pin/slot releases лишь при освобождении владельца.
   setSize(64GiB+1) и write crossing64GiB → invalidInput до allocation/IO;
   явный ZERO setSize(64GiB) → ровно262144 entries, без DATA materialization.
   Общие backend cap/budget tests не заменяют Writer catches и candidate paths.

Runnable target для этих synthetic regressions у main — уже существующий
native CTest `ProtectedCustodyFilesTests` (например
`ctest --test-dir <native-build> -R '^ProtectedCustodyFilesTests$' --output-on-failure`).
Reviewer этот target не запускал и тесты не редактировал.

## Runtime receipts: только main-observed

Main сообщил initial native focused session17761: build0,
ProtectedCustodyFilesTests1/1 PASS8.04s, total8.13s — **interim only**.
Первый link после появления writer TU/GLOB regeneration: session87302 exit1;
последующая сборка compiled0. Это не RED поведения writer.
Expanded session97083 на последнем сообщении main выполнял build; terminal
receipt ещё не получен. Свежие include/owner-comment bytes и финальный test
hash не превращают прежний interim PASS в exact-freeze final PASS.
Предыдущие full native/host/VS receipts metadata шага сюда не перенесены.

## Ponytail review — после correctness/security

Lean already. Worker core нужен следующему IStream/MF/producer шагу и не
объявлен arbitrary scaffolding. Реальные Files/Codec/Budget/Pin переиспользуются;
новых dependencies, второй crypto/disk mapper или async framework нет.
Один dirty block/writer и общий малый DirtySlot counter реализуют принятый
предел; их удаление ослабило бы требования. Local wipe/error helpers короткие;
дублирование security validation нельзя просто убрать из Files ради line count.
Metadata serialization и native/stdlib-first решения сохранены.
Безопасных delete/stdlib/native/yagni/shrink findings не найдено.

net: -0 lines possible

## SHA-256: текущие локальные bytes

HEAD — identity worktree, не commit этих dirty/untracked файлов.
Шесть изменённых source paths ниже в порядке Writer.h, Writer.cpp, Files.h,
Memory.h, Metadata.h, Metadata.cpp. Digest списка `sha256 + two spaces +
repository-relative path + LF` (UTF-8, в этом порядке):
`6bca0053f07acb1ceccb981fa83605159dcf8c3c70802fa1bcfd2e360870c4b2`.

| Source/test/support | SHA-256 |
| --- | --- |
| Storage/ProtectedCustodyWriter.h | `4458449d2b9443178c879ccd15ed1a0949bc071e11f6bf2036d085ad67e9f381` |
| Storage/ProtectedCustodyWriter.cpp | `b97a8a3cee2cfe3bd5cb6992b41b34d6394d7b2fef8ddc5be6fa840165b80e2f` |
| Storage/ProtectedCustodyFiles.h | `4b92692a1d4f67287574b3e912029fb350955861513ec668c82582c9c43f5367` |
| Storage/ProtectedCustodyMemory.h | `3a9e8e8637a21bb4be42a9167d5b7df9f5ebe5f80cd01a29761053b077b005c9` |
| Storage/ProtectedCustodyMetadata.h | `de7ba1eba3e7f26a28cb1b73461a42f4402f1f0c49adbe7e9ad1040e46af5cf0` |
| Storage/ProtectedCustodyMetadata.cpp | `d35f8e5d142bcc45a648baa70b7c8155a216949b84ae04a3fe1f2213c14397d3` |
| Storage/ProtectedCustodyFiles.cpp | `eb712a38f76eb5374f6ee4e3d964d15fb5ef92db2e212d20c77a166fd69bf142` |
| Storage/ProtectedCustodyReader.cpp | `5f39f669cccb80e8be73582fc806ff6810e44003b5cb6ba28147c951571978c2` |
| Storage/ProtectedCustodyCodec.h | `6ac5de213ce896730d87a497d512070dd55a5b496b322c38fdb2c57fa2ed53e6` |
| Storage/ProtectedCustodyCodec.cpp | `148899142a1568f9bc01c47ab63de07f3b5f8854a05faec8ed3b2e2775963fea` |
| Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `bc2ddd63f3737a30d29138473bbed07e0c431b6af6a9279d30d665dce57bac22` |
| apps/windows/CMakeLists.txt | `400b57f98d791a6739aa5be0a7140ce9d63f8d114f14cff305a39d8792eb141d` |
| RecApp/GrafWindowsApp.vcxproj | `3e6c9182d440acb7f599b7e587084b8734f52b9419ffcd8fc4fab239c55bf1ff` |
| Tests/GrafWindowsCoreTests/GrafWindowsCoreTests.vcxproj | `c53d070bbb0bae3f4262a875e593a56c3ff28847c5dec19e176d87d3e20d5df4` |
| contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| checklists/review-2026-10-03-custody-media-writer-gate.md | `39ffe9332f653e96d0ca45d76b7f4d67885c29af930afa475c89f0cc3b36999a` |

Единственная запись reviewer — этот отдельный report через apply_patch.
Код, нормы, checklist markers, прежние отчёты, tasks/Git/issues/state не
редактировались; builds/tests/runtime/install/mic/inventory не запускались.
Чужие изменения не отменялись. Изменение указанных source/test bytes требует
новой привязки обзора; будущие runtime receipts добавляются отдельно как
main-observed с их точным scope, без переписывания текущей истории.

## Append-only: восстановленный worktree и test-only review

Дата: 2026-10-03. Новый canonical root:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch/HEAD по-прежнему `codex/200-windows-followup` /
`99b00a579c24b50e320465b69d9a296038bc544d`.
Прежние218 строк сохранены буквально; их SHA-256
`f415347d47c3b444211007ed235be632e22c9f1eb69af36b57e8f3358fe6c87d`
совпал с report blob snapshot `e6ac0105029682daef08116f8defb36167f93f2e`.
Это дополнение не заменяет старый canonical path/evidence в истории.

**Approved — узкая test-source delta и ограниченность optional probe.**
Нового подтверждённого correctness/security дефекта тестов или счётчиков
не найдено. Оба review skills перечитаны полностью. Основной writer/norm
обзор не выполнялся заново: все десять Storage source hashes, CMake и оба
vcxproj, custody contract и requirements gate совпали с таблицей выше.
Product source6 digest остаётся
`6bca0053f07acb1ceccb981fa83605159dcf8c3c70802fa1bcfd2e360870c4b2`.

Actual test SHA-256:
`d858444d8889b37953c2b0e0faeaae9ef6afec519dafb68905b199e45d666c1f`.
Snapshot test blob имеет прежний hash `bc2ddd63...57bac22`;
сравнение с восстановленным рабочим файлом выполнено по содержимому,
не по Git diff для untracked path. Изменения — новые native counters,
writer regressions, optional probe и dispatch argument в существующем TU.

### Проверки, закрывающие прежние P2 observations в исходниках тестов

- `ProtectedCustodyFilesTests.cpp:193–274`: общий sticky oracle дважды
  вызывает writeAt/setSize/readAt/checkpoint, проверяя classification,
  base/target/native, unchanged size/generation/charged memory и все восемь
  counters. Early flush/hash → notCommitted; renameCompletion → ambiguous;
  native read ordinals1/2 после rename проверяют physical publish readback
  и следующий independent resolver read соответственно. Здесь index и DATA
  малы: Files::State::read делает один ReadFile на каждый envelope, без
  дополнительного EOF ReadFile. После release есть fresh lease/reopen g1.
  Artifacts oracle сравнивает names/sizes, не hashes содержимого всех файлов.
- `:275–300`: afterFlush DATA перед следующим publish ставит cancel;
  ожидаются notCommitted/writerFailed/ERROR_OPERATION_ABORTED, base1/target2,
  generation1, ровно один write/flush и ноль rename, отсутствие index1;
  повторные методы — без новых наблюдаемых IO, fresh reader после release
  возвращает прежний committed byte. Это не объявлено zero IO самого
  отменённого checkpoint: новый orphan block уже записан/сохранён.
- `:301–350`: cap+1, crossing cap и UINT64_MAX проверены до allocator/native
  counters; owned64MiB отказ отдельно на loadDirty, candidate resize и
  checkpoint, со sticky failure и actual charge release при owner destruction.
  Для quota checkpoint допускаются предшествующие reserve/enumeration reads:
  assertions требуют zero writes/flush/rename, не zero всех native вызовов.
  Byte-charge release не выдан за отдельное доказательство Pin/Slot recovery
  на каждом quota path; исходные shared admission tests остаются отдельными.
- `:351–384`: реальный writer base1 → changed header/tail → ACK g2,
  retained reader продолжает exactg1; stale base1 получает conflict без writes,
  charge возвращается к прежнему; fresh writer base2 читает обновлённые bytes.

Сохранённые пробелы: нет direct writer oracle для verified/trustedPrefix
отказа open, иного **валидного** same-generation/length index с другими refs
при final resolver reopen и equality reject; нет direct successful writer
setSize(64GiB) →262144 ZERO entries без DATA materialization. Backend maximum
и native failure tests не объявлены их заменой. Это остающиеся coverage
observations, не новый доказанный RED production кода.

### Probe: пределы и точное значение чисел

`:405–476,1322–1329`: только явный `--writer-throughput-probe` на Windows;
default CTest его не запускает, host option возвращает unsupportedPlatform.
Один generated/private-ACL fixture, synthetic pattern, один256KiB input,
строго64 full-block writes/16MiB, no real inventory/mic/network. Actual
canonical writer выполняет auto checkpoints; проверяются exact byte count,
size/generation и owner charge после actual release. Cleanup относится
только к случайному synthetic fixture после закрытия writer/handles.

Milestones1/2/4/8/16MiB используют steady_clock. Cumulative time включает
sequential loop/минимальную подготовку pattern, но не initial open и cleanup;
last_write_checkpoint_ms — весь WriteAt с auto checkpoint, не isolated
publish/reopen latency. committed — принятые full-block checkpoints; error
state счётчик обновляется при failed write. Failure counts ограничены текущим
CustodyFileError enum, dispatch/map соответствуют ему; переполнения counters
на64 шагах не обнаружено. Native read/hash-open counts — число вызовов
перехваченных API, не bytes, refs или все native allocations. owned_bytes —
текущий charged sample, не peak working set и не DPAPI memory. Probe не
проверяет plaintext output byte-for-byte отдельным reader и не доказывает
64GiB latency/SC-003/Stop/power-loss/installed acceptance.

Ponytail после correctness: дополнительные bounded regressions и optional
probe не требуют новой архитектуры; безопасного сокращения требований нет.
Lean already. net: -0 lines possible.

### Новая execution evidence, только main-observed

Main сообщил session88132: native new test SHA verified, build0,
ProtectedCustodyFilesTests1/1 PASS6.78s, total6.89s, EXIT0. Reviewer execution
не повторял. Probe ещё running, результата/скорости не принимаем.
Main также сообщил о завершённых прежних host35/native36 logs04:59 и новом
VS/core0 build, app `34e5cf31...` NOT installed. Это оставлено сообщением
main с неполным app hash, не новым independently verified full-run receipt
для testSHA d858444d и не installed proof.

Единственная новая запись — это append-only дополнение к owned report.
Исходная история, код/тесты, нормы, markers/tasks/Git/state и чужие файлы
не изменены; reviewer builds/tests/probe/runtime не запускал. T116 whole,
T117/T118 и полная цель остаются открытыми; checkbox state не изменялся.

## Append-only: final test binding и fixed64MiB probe option

Дата: 2026-10-03. Предшествующий report целиком имел SHA-256
`d53f59b2aa9fb12c01111d439f3c60389398cd29f86614332f97f2c6511c596c`;
ни одна его строка не заменена.
Последний локально подтверждённый test SHA:
`7dc2b317729df8dc5410ee9c3e37dfebf543385980dd7c984c2a63626abd270c`.
Все десять product source hashes повторно совпали с initial таблицей.

Новая test-only delta `:405–407,1322–1327` — bool extended выбирает только
16 либо64MiB. Optional `--writer-throughput-probe-64mib` даёт ровно256
full-block writes, не произвольный caller size; стандартные тесты/прежний
option не меняются. Один256KiB input и generated fixture остаются прежними,
milestones удваиваются до64MiB, native call counters на этом пределе не
переполняются. **Approved** этой ограниченной source delta; иных safety или
counter defects не найдено. Остальные ограничения измерения и coverage gaps
из предыдущего дополнения сохраняются. Ponytail: net: -0 lines possible.

Main-observed session91855, **прежний d858444d test snapshot /16MiB option**:
terminal0, cumulative14.602244s, последний write/checkpoint357.356ms,
64ACK/0fail, owned after actual release0; cumulative nativeReads8511,
hashOpens4607. Числа записаны из сообщения main, не из reviewer execution.
Это finite synthetic measurement, не60min/SC-003, не установленный продукт
и не доказательство scaling64GiB. Большой cumulative read count включает
повторную проверку прежних refs при каждом checkpoint, не8511 уникальных refs.
Сборка/64MiB probe для нового7dc2b317 snapshot пока pending: прежние
session88132 focused PASS и91855 probe0 не переименованы в latest-SHA PASS.
Ни runtime, ни тесты reviewer не запускал; добавлен только этот текст.
