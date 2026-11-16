# Round456 — E1 returned recovery faults: requirements gate и source checkpoint

## Полномочия и исходная точка

Authoritative worktree: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`; actual branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Feature200/high-risk-product, существующая T116/#7444. T116 остаётся открытой по tasks.md:568; состояние GitHub reviewer не перечитывал и не менял. Сообщение main о fresh OPEN не выдано за собственное чтение GitHub.

Единственная разрешённая запись — этот report456. Report/evidence455 не изменены. Source, нормы, tasks, checklist markers, Git index, GitHub, VM, тесты и cleanup не изменялись/не запускались reviewer. Проверка нормативов использует speckit-analyze и критерии качества speckit-checklist, а не создаёт ещё один checklist под те же требования.

Прочитаны current AGENTS/router, guidance index, spec-kit-flow/product-gates, применимые положения constitution, scoped spec/plan/quickstart/contracts/tasks и конечный E1/P2 audit453. Feature pointer совпадает с feature200. У prerequisite script обычный режим имеет документированный side effect записи feature.json; в соответствии с read-only scope использован только `--json --paths-only` и отдельно прочитаны actual feature files/tasks. Его synthetic BRANCH в JSON не подменяет проверенный `git branch --show-current`. Before/after analyze/checklist commit hooks отключены, state-changing hooks не исполнялись.

## Requirements gate — GO без normative update

**198 checklist-файлов / 458 checked / 0 unchecked**, независимо пересчитано по фактическим checkbox lines. Исторические runtime narratives не перечитывались как доказательство текущей реализации. Целиком перечитаны `cold-prefix-recovery.md` (28/0) и `packed-writer.md` (12/0); новые markers не требуются. Основания существующих B CHK001–012 и native CHK013–022 сохраняются; CHK009/010/012 прямо покрывают failures, ресурсы и publish/final-ACK cuts. `[x]` означает качество требований, не выполненную E1 матрицу.

Scoped analyze: **CRITICAL0 / HIGH0**, блокирующих нормативных противоречий/clarify choices для test-only E1 не найдено. Это не повторный GO всему T116 и не снятие production P2 из audit453.

| Обязанность E1 | Current requirement / coverage | Вывод |
| --- | --- | --- |
| Effectful derived output write/flush failures | Audit453:93–97; plan B:2351–2361; local custody §4; packed §5; T116 | Existing test scope |
| Metadata bind/rollover/seal publication before/after effect | Plan B:2356–2373; quickstart B:1046–1058; local custody §4/§9; B CHK009/012 | Existing test scope; failed ACK не отменяет publication |
| Late full inspection failure после seal | Audit453 E1; plan B §6 требует последнюю full semantic inspect; B CHK008/009 | Existing обязательный fence, не новая продуктовая политика |
| Canonical/IDs/history/owner/queue preservation и отсутствие normal authority | Plan B §1–7; B CHK003–007/011; FR-012/013/014/022; T116 | Неизменные границы |
| Fresh cold outcome, error/native, actual retirement/bounds | Custody §§4–7/§9; packed §5/§6.0; B CHK009/010/012 | Доказательство execution, не новый persistent формат |

Конечный состав E1 из audit453 — минимальные реальные отказы на **derived outputs**, **metadata bind/seal**, **post-seal full inspection**, с error/native propagation, без ложного normal/playable результата, с preservation, cold observation и actual drain. Pre-cancel/quota и 24 process-termination cuts не заменяют returned IO/cancel. Разрешено разбить E1 на конечные направленные проверки без cross-product всех offsets/ошибок, честно сохраняя непроверенные части открытыми. Полный P2 continuation started/orphan outputs остаётся missing production path: этот тест не разрешает снять unused/CREATE_NEW guards, ремонтировать partial outputs либо выдавать preservation/refusal за положительное продолжение.

**Правило oracle:** ошибочный вызов recover не возвращает accepted playable result. Но если publication уже состоялась, fresh cold read может доказать valid sealedDegraded. Его нельзя объявлять отсутствующим только из-за API error; наоборот, normal запрещён, а пригодность degraded требует настоящей full inspection/AAC. Допустимы changes новых derived/state/manifest artifacts; неизменность всего root до эффекта нельзя механически требовать после эффекта.

## Current source delta — только два test/build файла

Независимо сверены current216 с frozen455 GREEN5 manifest `5e588cf1937b384fe3ac2d77394247a99076d1cad880abeded6c29f1088a83f6`: отличаются **ровно** CMakeLists.txt и `Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp`; остальные214 exact, production не менялся.

Baseline обоих файлов восстановлен **в памяти**, без scratch/index, из точного HEAD и сохранённого455 `green5/delta-from-head.patch`. SHA восстановленных байтов совпали с manifest455:

| File | Baseline455 SHA | Current checkpoint SHA |
| --- | --- | --- |
| apps/windows/CMakeLists.txt | `8b215412deb7280cf3bb421b5cb1412e94df482e4a91a33b44405a294527cb44` | `67cdffd19b2ed56fb7f3646141c6c82a4ee706eed888a823ca3699e9c145da04` |
| apps/windows/Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp | `cf9f5ef46c67b8230402095891740015eda4715212586305433e6a78818c9c54` | `28486bfebe21a1d1af8d00a8d27d7913b89690c215b84965291028c6df9949ec` |

Это source checkpoint до нового execution/freeze, не runtime evidence. CMake регистрирует существующий exe/новый CLI как `ProtectedRecoveryReturnedFaults`, RUN_SERIAL TRUE, TIMEOUT300. Существующий TU-local real Files.cpp wrapper pattern/исключение отдельного Files linkage сохранены; новой production ветки или alternate persistence не добавлено.

### Проверка wrappers и 23-case oracle

- Matrix: media/playback × first-write/first-flush/first-DATA/post-DATA HEAD-write/HEAD-flush =10; manifest/recovery/package-state × write/flush/before-rename/after-rename =12; late canonical read =1. Dispatch исполняет `coldRecoveryReturnedFaults()` в том же exe; прежний default suite не заменён этим CLI.
- `recoveryFail` сохраняет LastError перед GetFinalPathNameByHandleW classification и восстанавливает до возврата. `recoveryEvent` также сохраняет/восстанавливает его вокруг observation. При injected Write/Read ошибка явно задаётся после classification, done=0; Flush задаёт ERROR_WRITE_FAULT. Real failed calls не проходят success observation. Повторная path classification — небольшая локальная избыточность, не обнаруженная ошибка nativeError; новый classifier framework не нужен.
- Existing canonical writes/flushes по-прежнему запрещены trace assert. DATA/HEAD cuts различают offsets и размер HEAD, HEAD-flush требует actual ранее наблюдённый post-DATA HEAD-write. `hit==1` исключает ранний guard/no-op вместо фактического IO. Восстановление original package/role IDs и всего canonical role проверяется полными path/SHA maps; service root queue/bootstrap map также сохраняется.
- Rename wrapper для after-effect cut сначала вызывает настоящий NtSetInformationFile и лишь при actual status0/io.Status0 наблюдает after-event и возвращает STATUS_DISK_FULL. Поэтому это не fake pre-effect rename. Записанный NTSTATUS/HRESULT(native) проверяется явным expected oracle, не просто nonzero.
- Late cut: successful generated baseline определяет ordinal последнего event; он обязан быть package-state/after-rename. Новый прогон включает canonical ReadFile failure только после достижения этого ordinal. В текущем production `commitImpl` после publication читает paired metadata; canonical refs/hash проверяются до publication, а следующая canonical inspection выполняется после committed seal. Поэтому выбранный role0 ReadFile cut направлен на позднюю полную инспекцию, а не ранний prefix read. Ещё более важно: cold oracle независимо требует sealedDegraded/full degraded proof/exact1000ms/nonzero decoded AAC/session/known times. Одно достижение счётчика не считается доказательством пригодности.
- Любой injected fault требует recovered.ok()==false, specific non-none error и точный ожидаемый native/HRESULT. Затем fault отключается, failed owners действительно разрушаются до fresh StoreOwner/readPackage. Cold normal запрещён; late case обязан доказать degraded. Полный root hash map после cold observation должен равняться map после failure: наблюдение не repair/GC. После Fixture destructor проверяется exact idle owned memory, затем доступность всех4 jobs и32 pins. Таймер не подменяет resource release.

**Source verdict: bounded GO для написанных23 cases, новых CRITICAL/HIGH не найдено.** Runtime ни одного из них этим report не доказан; compiler/error-shape/oracle предположения должны пройти actual native run. Успешный baseline внутри теста сам по себе не принимает fault cases.

### Точные ограничения покрытия — не расширять claims

1. `recoveryFaultHits==0` выбирает **первый** подходящий IO заданной role/op. Metadata12 cases не означают все manifest rollovers, все recovery birth slots или отдельно каждый finalizing/sealed package rename. Все-stage process cuts447 остаются другим доказательством. Если отчёт называет все metadata transitions покрытыми returned faults, это будет неверно.
2. Late23 — returned IO error, не late cancellation. Эта матрица не даёт claim, что все named cancel/post-seal cuts E1 закрыты. Специфическую будущую late cancel проверку нельзя засчитать через этот ReadFile fault либо старый pre-cancel.
3. Fresh invalid/partial package может быть сохранённым отказом; это не normal и не разрешение повторно выполнять factory. Current test не реализует и не принимает P2 continuation. Нет physical power-loss, installed/hardware, fullapp/public readiness или всей T116/T117 acceptance.

## Ресурсы и граница запуска

Read-only `df` на Mac показал available39608572KiB ≈40.56GB (≈37.77GiB), ниже50GB из пользовательского правила. Reviewer ничего не чистил. Этот нормативный/source gate не разрешает крупную новую сборку, зависимости или source/archive copies при таком запасе и не отменяет resource preflight main. Использование существующего incremental executable не является разрешением расходовать неограниченный диск; runtime receipts должны назвать фактические pre/post bounds. VM/build/test запуск остаётся исключительно у main, не выполняется этим reviewer.

## Current normative SHA256

```text
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec.md
2d1f170a0345ef0201848f6d0a934f973db596f001fa7c431e2b973c702bdd1e plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks.md
3eb4f3a05a4295025a149ecbb91b4cce71d4caacbf94f19f24d9631f16e25c12 quickstart.md
6c1b4432fc37af7eb97f7d9202072344b0c8e5ccf7724d26ad3081ec8b79f716 research.md
6023a5095e3c6726fd5a885c4cf46c573dd8acc31235e0eb2d914460c33f8214 data-model.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 contracts/windows-desktop-contract.md
a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490 contracts/windows-protected-local-custody.md
a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 contracts/windows-protected-packed-custody.md
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 constitution.md
```

Итог: E1 test-only допустим existing requirements без normative update/new checklist/task/schema; aggregate198/458/0 и scoped analyze C0/H0. Source23 — bounded GO, runtime pending. P2/E1 remainder/full T116 остаются открытыми. Записан только этот новый report456, frozen455 не дополнен.

## Append — GREEN2 actual runtime qualification

Независимо прочитаны сохранённые материалы `/Users/yshishenya/Documents/graf-f200-recovery456.3YflWv/green2`: `result.json`, `result.xml`, `actual-test.log`, `test.log`, `build.log`, `source.sha256`; также `validate2.ps1`, `collect-log.ps1` и исторические root receipt/build/source. UTF16LE build/test журналы декодированы перед содержательной проверкой. Reviewer не исполнял harness, VM, build/test либо cleanup; единственная запись — этот append.

**Bounded runtime GO для фактически исполненной матрицы23.** Receipt terminal=true, build0/test_exit0/executed_tests1/postflight216/owned_processes0. JUnit содержит ровно `ProtectedRecoveryReturnedFaults`, status=run, failures0/skipped0/disabled0, actual duration **46.4911s**; CTest total46.51s. Build log явно показывает компиляцию `V5LocalRecordingWriterTests.cpp` и выпуск соответствующего Debug exe, а не только reuse старого PE.

Source manifest SHA **`1e735843026d92323a1d82c6f70f7f3780c6c636d513875e828e3394a42c614e`**, independently current216/216 match. GREEN2 harness проверяет actual guest216 до/после запуска, source upgrade только по разрешённым двум test/build paths и проверяет неизменность PE после теста. Receipt фиксирует writer PE **`fbcee840e8a77af4d35dbfe443fa76f91b505b21005d43eda0bad51821999868`**, 6812160bytes. Это квалификация сохранённой guest/PE/process проверки, не самостоятельное live CIM/PE чтение reviewer.

JUnit output действительно обрезан порогом1024bytes; он не использован как доказательство всех23 случаев. Полный `actual-test.log` имеет настоящий LastTest header/command `V5LocalRecordingWriterTests.exe --cold-recovery-returned-faults`, все23 individual lines и `Test Passed.`. `collect-log.ps1` требует prior terminal/test0, тот же PE, named test/итог и копирует real LastTest.log с overwrite=false. В полном сохранённом журнале независимо проверены точный ordered set **10 output +12 metadata +1 late read**, без пропусков/дубликатов: каждый hit1/rejected1/error6; native write=00000070, flush=0000001d, before/after rename=c000007f, late read=0000001e. Итог:

```text
COLD_RECOVERY_RETURNS cases=23 exact_memory=1 canonical_ids_queue_unchanged=1 late_seal_cold_decode=1 audio=0 network=0
```

Итоговая строка достигается после реальных scope destructors, exact idle memory и reacquisition всех4 jobs/32 pins для каждого случая. Current source требует сохранения canonical/IDs/queue, отсутствия cold repair и normal phase, а в late read — actual cold sealedDegraded/full inspection/AAC decode с exact1000ms/session/times. Эти проверки теперь исполнены, а не только предусмотрены source. Ошибка позднего API не отрицает уже состоявшийся physical seal.

Историческая первая попытка остаётся **build FAIL**: root receipt build1/failure=BUILD; build log C2220/C4456 на повторном `offset` в wrapper119. Независимое сравнение байтов old/current TestTU подтвердило ровно удаление одной внутренней дублирующей декларации offset; остальные байты неизменны. Семантика cuts/oracles не ослаблена. Production по-прежнему не изменялся. Этот build failure не переносится в runtime PASS и не считается исполнением матрицы.

Контрольные суммы прочитанных конечных доказательств:

```text
39b67190ae4b29a7e0fe57ef97a6527c163f3ea7f4d4b1144e8c8ce63e567de6 green2/result.json
58f4f514e2f977dd7ed44ebd98282c9ba81e5af515744646a432414a2b5b1f89 green2/result.xml
741072ca80b961c3bf5aad7eb3e1ea1e7869ff6b8d082af2d4b86a45a3a353f5 green2/actual-test.log
```

Receipt free_before40514453504/free_after40384061440 относится к guest C:, не доказывает восстановление требуемого запаса Mac. Новые тяжёлые действия/cleanup этим append не разрешаются.

Ограничения source checkpoint сохранены: metadata cuts — первые matching events, late cut — IO, не late cancellation; **полный V5 default regression не квалифицирован этим append**, даже если main запускает его следом. P2 started/orphan output continuation не закрыт, E1 remainder/T116/T117/public readiness/fullapp/installed/hardware/release GO не выданы. Новых runtime findings, блокирующих именно эту матрицу23, не обнаружено.

## Append — GREEN2 default regression и GREEN3 finite source review

### Завершённый GREEN2 default regression

Теперь независимо прочитаны `green2/regression.json`, `regression.xml`, декодированный UTF16LE `regression.log`, полный `actual-regression.log` и `regression.ps1`. **Bounded default V5 regression GO на GREEN2**, не на GREEN3: terminal=true/test_exit0/executed_tests1/postflight216/owned_processes0; тот же manifest `1e735843026d92323a1d82c6f70f7f3780c6c636d513875e828e3394a42c614e` и PE `fbcee840e8a77af4d35dbfe443fa76f91b505b21005d43eda0bad51821999868`. JUnit: ровно `V5LocalRecordingWriterTests`, status=run, failures/skipped/disabled0, **117.131s**, CTest total **117.14s**.

Полный actual-regression.log содержит default command без fault CLI, `Test Passed.`, actual3 positive recovery,15 individual rejected cases и summary, capturing/finalizing prefix3,3 sealed-phase refusals/9 prior refusals, все24 consecutive child ordinals с actual child_exit88/waited1 и non-vacuous sealed_cold_decode1. Script сохраняет real LastTest.log до выхода, сверяет source216 и PE до/после. Saved process0 не выдан за live CIM reviewer. XML с усечённым output не подменяет полный журнал.

```text
671fdb89e5c291eeed0430c7c20ba2a7c0d6f41b7517eaf34bda30fc94481bdd green2/regression.json
da9c5adaf863fb16b61586c87679f139014022efaa8eddae11972b25b2566f90 green2/regression.xml
0654d01aec6cb35b285c34da165d337c325658e7b19a25120857fdf4672c88d4 green2/actual-regression.log
```

### GREEN3 — только source, runtime ещё не принят

Применён code-reviewer для ограниченного diff GREEN2→GREEN3, без execution/preflight. Свежий manifest **`a6774514da8a14b6ef5726970194537a5402ee8e6c17bf6fa37a4500ef87af94`**, current216/216 совпадает; относительно GREEN2 изменён ровно TestTU (SHA `89838a21c15855c3b46b5caeaa87fafc12d1f530bd7578f943948ddd6464ca00`), остальные215 entries exact. Product/schema/norms/tasks не менялись этим diff.

**Bounded source GO для трёх добавленных cases; конкретных блокирующих ошибок не найдено.** `afterEvent` добавляет нижнюю границу ordinal к прежним exact role/op/hit1, нулевой default сохраняет исходные23 cuts. Последний baseline event обязан быть package-state/after-rename; before-event наблюдается прямо перед тем же actual rename, поэтому N−1/N направляют новые role5/op2/op3 на последний seal, а не первый finalizing transition. При before-fault actual rename не вызывается; при after-fault он сначала должен успешно завершиться. Cold oracle правильно требует finalizing до эффекта и sealedDegraded с actual full AAC после эффекта — не одинаковое состояние для двух сторон границы.

Late cancellation role0/op8 допускается лишь после actual baseline seal ordinal; wrapper устанавливает **тот же настоящий atomic cancellation token**, затем вызывает настоящий ReadFile, не возвращая выдуманный IO error. Recover обязан вернуть rejected/non-none и native995 либо HRESULT_FROM_WIN32(995), token true только в этом случае. Raw test pointer живёт внутри синхронного recover при удерживаемом shared token, очищается после вызова; fresh cold owner получает новый false token, после разрушения failed owner. Прежние canonical/IDs/queue, cold-no-repair, exact memory/jobs/pins assertions сохранены. LastError preservation в classifier не изменено.

`afterEvent` — threshold (`>=`), не assertion равенства actual ordinal: в текущем синхронном generated flow role/op и cold phase oracle достаточны для этой направленной проверки; не следует описывать поле after_event в будущей строке журнала как независимо измеренный actual ordinal. Это configured lower bound. Нового framework/helper/production switch не потребовалось.

GREEN3 now26 cases только source-reviewed: active handle74057/будущий receipt reviewer не ожидал и runtime PASS не присваивал. GREEN2 default regression не переносится на новый TestTU как execution новых трёх cases. Поздняя отмена, последние seal cuts должны быть отдельно подтверждены новым полным actual-test.log/receipt. P2/E1 remainder/full T116 остаются открытыми; новый normative update/checklist/task не требуется. Выполнен только append report456.

## Append — GREEN3 terminal runtime26

Свежим read-only проходом независимо прочитаны GREEN3 `result.json`, `result.xml`, полный появившийся `actual-test.log`, UTF16LE build/test logs, `validate3.ps1` и `collect-log3.ps1`. **Bounded runtime GO для фактически исполненных26 случаев.** Terminal=true/build0/test_exit0/executed_tests1/postflight216/owned_processes0; JUnit ровно `ProtectedRecoveryReturnedFaults`, status=run, failures/skipped/disabled0, **56.0663s**, CTest total56.07s. Build log содержит actual TestTU compilation и exe output. Saved writer PE **`548c88855a3df42ccbdb12f63d3013dea6b1e6c8332d5c872b6a36b10df99e71`**,6842880bytes; manifest **`a6774514da8a14b6ef5726970194537a5402ee8e6c17bf6fa37a4500ef87af94`**, current independently216/216 match. Guest pre/post216, unchanged PE и process0 квалифицированы по actual saved harness/receipt, не по live VM/CIM reviewer.

XML опять усечён и не доказывает26 lines. Полный actual-test.log содержит правильный CLI, exact ordered26 individual cases, каждый hit1/rejected1/error6, затем итог и `Test Passed.`. В частности actual последние3:

```text
COLD_RECOVERY_RETURN role=5 operation=2 after_event=23 hit=1 rejected=1 error=6 native=c000007f
COLD_RECOVERY_RETURN role=5 operation=3 after_event=24 hit=1 rejected=1 error=6 native=c000007f
COLD_RECOVERY_RETURN role=0 operation=8 after_event=0 hit=1 rejected=1 error=6 native=000003e3
COLD_RECOVERY_RETURNS cases=26 exact_memory=1 canonical_ids_queue_unchanged=1 late_seal_cold_decode=1 audio=0 network=0
```

Таким образом последние before/after publication возвращённые ошибки и **настоящая late cancellation native995** теперь actual executed, а не только source-intended. Source assertions вместе с успешным завершением доказывают cold finalizing для before-effect, cold sealedDegraded/full AAC для after-effect и late cancel/read error, новый false token для cold observation, сохранность canonical/IDs/queue, отсутствие cold repair и exact memory/jobs/pins после actual destructors. Configured `after_event` по-прежнему не переименован в independently measured actual ordinal.

```text
2871ab2e2f4e7d89b5a44c64c03236a76ceb96bb5f707c6415cd0c78f55ebfc3 green3/result.json
f6cb9a8d31350297d25351c5ca2921f54e151bf55a09426d94590cebdd5fedcc green3/result.xml
3b7691a4fd0157e37828b2dd2502fca9b38951f2e9580d26116942e9b89aa676 green3/actual-test.log
```

Новых blockers для этой конечной26-case матрицы не найдено. **GREEN3 default V5 regression ещё не квалифицирован** этим append; предыдущий GREEN2 default PASS остаётся только GREEN2. Никакие новые suites не запущены/не предложены. Матрица26 не объявлена всеми возможными E1 cuts; production P2 started/orphan continuation и umbrella T116 остаются открытыми. Source/norms/tasks/checklist markers/VM/Git/index/cleanup reviewer не менял; запись только в report456.

## Final append — current GREEN3 default regression и source chain

Конечный finite review456 **завершён: bounded source/runtime GO для matrix26 и default V5 regression на одном current GREEN3 manifest/PE**. Новых source/runtime blockers в назначенном объёме нет. Независимо прочитаны GREEN3 `regression.json`, `regression.xml`, декодированный UTF16LE `regression.log`, полный `actual-regression.log` и actual `regression3.ps1` (не исполнялся). Receipt terminal=true/test_exit0/executed_tests1/postflight216/owned_processes0, без failure. JUnit ровно `V5LocalRecordingWriterTests`, status=run, failures/skipped/disabled0, **116.736s**, CTest total116.74s. Exe **`548c88855a3df42ccbdb12f63d3013dea6b1e6c8332d5c872b6a36b10df99e71`** и manifest **`a6774514da8a14b6ef5726970194537a5402ee8e6c17bf6fa37a4500ef87af94`** совпадают с принятой26-case primary; script требует same PE/source до/после default run и копирует real LastTest.log overwrite=false.

Полный actual-regression.log содержит default executable command **без CLI**, Test Passed, 3 positive recovery, exact15 individual refusals, actual capturing/finalizing prefix3,3 sealed-phase refusals/9 prior refusals,24 consecutive actual process cuts (ordinals1–24, child_exit88/waited1), sealed_cold_decode1 и protected playback48128frames при held_jobs0/2. Усечённый XML не использован вместо полного output. Этот actual GREEN3 default PASS теперь принят самостоятельно, без переноса GREEN2 результата.

`source-chain.json` и `source-chain.rb` прочитаны статически, **script не запускался**. Независимым read-only сравнением manifest entries/байтов проверены current216/216, совпадение inventory с frozen455, **214 unchanged +ровно2 changed snapshots**: root `apps/windows/CMakeLists.txt` и GREEN3 TestTU. Оба полных сохранённых snapshot имеют точные final manifest hashes. HEAD остаётся `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; baseline manifest SHA `5e588cf1937b384fe3ac2d77394247a99076d1cad880abeded6c29f1088a83f6` подтверждён.

Граница source-chain: script сравнивает hashes214 unchanged с baseline manifest, **не читает214 отдельных baseline source copies и не выполняет полную reconstruction**. Формулировку method `frozen455 full source` следует понимать как зависимость от сохранённого455 baseline, а не как наличие всех loose source copies здесь: baseline CMakePresets.json loose copy уже отсутствует. Durable baseline представлен точным HEAD и сохранённым455 full patch `green5/delta-from-head.patch`, SHA **`f2f07426a77468fced3d7f681bb270110f0023a70bb8cd038904907a5c10bb6f`**,3266955bytes; файл и digest свежепроверены read-only, source-origin/source-reconstruction файлы существуют. Полная повторная HEAD reconstruction в этом конечном проходе не выполнялась и за выполненную не выдана. Chain не является самодостаточным source archive без этой внешней455 baseline-зависимости; её нельзя удалить, сохранив лишь hashes214. Это оговорка о составе доказательств, не blocker принятого finite runtime.

```text
ca2d29d6c3d595fcd666c82a7623b9ca2d524dcc3b6c32018bc3f8ca388908b5 green3/regression.json
beaf31efbdaacd722f02fb09a6d88849cc8b9eec89dc198aeed20338704bc189 green3/regression.xml
e7ed694f83a1877dd0d7615cabca95d8b738085f4012ecbdb125197966577b7e green3/actual-regression.log
5bdea3b647698947af709539a7588eaadd0642c532e96e68dfc145e014de93c8 source-chain.json
```

Final verdict относится только к этому test-only diff и actual26+default execution. E1 не объявлена всеми произвольными offsets/ошибками; P2 started/orphan continuation остаётся production OPEN, T116/переходT117/public readiness/fullapp/install/release не закрыты. Исторический C4456 build FAIL сохранён, GREEN2 и GREEN3 evidence не смешаны. Никаких новых suites, cleanup или bundle/455 edits: выполнен только append report456. Дальнейших изменений sealed evidence reviewer не выполняет.
