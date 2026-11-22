# Round274 — SOURCE: bootstrap → own migration intent

Дата: 2026-10-07. Независимый reviewer-owned отчёт, 0 checkbox.
Lane: high-risk-product, существующая T116 / #7444.

## Вердикт и точная область

**SCOPED SOURCE GO — C0 / H0 / M0 / L0** для
`ProtectedCustodyMigrationPair::read(retainedBootstrap, cancellation)`
на приведённом ниже corrected204. Приняты исходники, тестовая коррекция и
точно привязанные normal native Release/Debug результаты этого компонента.

Это подтверждение linked own-intent pair, НЕ startup admission, НЕ готовность
очереди, НЕ разрешение legacy load/sweep/recover/network/purge/GC. Не закрывает
T116/T117/T118/T119/T120, H250, известный legacy AAC RED или конечную цель Windows.
При подготовке core-решения App build-only был pending; результат не является
условием этого узкого GO. Позднее подтверждён отдельно, см. дополнение ниже.
Установка/запуск приложения, working profile, микрофон и сервер не проверялись.

## Identity, неизменность и нормативная область

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.

Accepted stand:
`/Users/yshishenya/Documents/graf-f200-bootstrap-link-accepted274.IAtzud`.
`source-accepted274.json`: 204 входа, SHA-256
`d4d5279141a2ad4a8bad84b10da5dfb636fc14eac79ccc823ce3f359c04dca16`.
Reviewer лично перепроверил все 204 canonical и frozen байта: mismatches=0.
От accepted273 `graf-f200-pair-accepted273.nSEy3f/apps/windows` изменены ровно
четыре production-файла и один существующий FilesTests; новый target/schema/
parser/backend не добавлены.

До записи этого отчёта все 156 прежних Markdown проверены побайтно:
changed=0; sorted basename<TAB>SHA256<LF> inventory SHA-256
`a503bd41a21dd3eafbd08718ca89867b90ee6f9029ba59145d1134d337ccce84`.
10 текущих нормативных checklists: 154 checked / 0 open. Их распределение:
advanced-routing14, audio-capture24, calendar-launcher5, calendar-operation8,
calendar-wire5, packed-writer12, privacy-pause12, requirements22, security27,
ux25. Все markers сохранены. Прочитанные полностью при REQUIREMENTS нормы
переиспользованы; текущие их хеши и состояние повторно проверены.
Остальные 146 файлов — отчёты/исторический контекст: 256 checked / 10 unchecked;
исторические unchecked не объявлены новыми нормативными обязательствами или
закрытыми этой проверкой.

Tasks: 120 / 93 checked / 27 open, SHA-256
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
T116 остаётся OPEN; #7444 OPEN/canonical — последнее сообщение main,
не самостоятельная GitHub-проверка reviewer. Issue/task mutations не выполнялись.
Constitution, spec, plan, data-model, quickstart, base/packed contracts,
feature.json/extensions.yml совпадают с хешами accepted REQUIREMENTS gate.
Before/after implement/analyze/checklist: EACH registered1, enabled0;
reviewer dispatched0. Commit/GitHub/VM/hooks/tests не запускались.

REQUIREMENTS gate лично перечитан до EOF:
`review-2026-10-07-bootstrap-intent-link-gate.md`, SHA-256
`a0513714410a013b20ec9d4d97cb319dadd4a7fe7480e7486f366392f75ba18e`.
Трассируемость: base custody §2/§4/§7/§8/§8.1, packed §6.1,
spec FR-012/013/014/022 и существующая T116. Закрытая форма этого gate реализована;
полные stage/effect/admission требования им не подменены.

## Проверка исходников и владения

Полностью прочитан incremental production diff относительно exact accepted273,
новая linked тестовая функция, все добавленные native adapters/assertions и
релевантные существующие Files/Codec/Bootstrap/BOTH/Birth/Memory вызовы.
Применены `code-reviewer` и `ponytail-review`; их полные инструкции прочитаны.
Общий dirty diff против HEAD не использован как граница Round274.

| Проверенная граница | SOURCE вывод |
| --- | --- |
| Metadata.h:80–111,154–156; Metadata.cpp:482–502 | Новый overload не принимает caller root. Private ctor/strong parent; non-null cancellation и genuine discovered queueLease обязательны. Explicit-only bootstrap отвергается до IO. |
| Metadata.cpp:490–501 | Selected migrating обязателен; каждый migrating peer имеет тот же transaction/subject/directory. Старый protected peer допускается, selected protected отвергается. Ожидания не берутся из intent JSON. |
| Files.h:109–120; Files.cpp:255–272 | trustedRoot только private friend accessor. Private discover узко расширен migrationIntent queue/package; тот же confined openImpl, exact16 IDs, ACL/reparse/hardlink/exclusive handles, no create/repair/scan. |
| Metadata.cpp:498–537 | Root/tuple references принадлежат удерживаемому bootstrap, shared_ptr move не перемещает native объект. Discovered intent store сравнивается с parent store. Discovery и semantic decode используют одну lease без reopen. |
| Metadata.cpp:539–578 | Existing BOTH физический validator, single positive ≤64KiB DATA, обе strict v1/v2 payloads по их generation и direct Birth. Bad peer/singleton не пропускаются. Отмена после openBlock перед JSON parse сохранена. |
| Metadata.cpp:564–567 | Для queue strict codec уже требует один ledger source: его destinationObjectId безопасно сравнивается в обоих slots с fixed queue ID. Для package сравнивается anchor.objectId. Это не проверка anchor generation/hash или destination closure. |
| Metadata.cpp:579–594 | Existing cross-slot progression/sticky receipt/Birth алгоритм сохранён; blockWrites только после чтения. Allocated private object и shared control block charged, final cancellation после материализации. Typed errors без fallback/default queue. |

Один `CustodyNativeJob` в readImpl: declared перед `held`, затем дополнительный
Pin и intent lease. Parent/intent cleanup при отказе/throw завершается до
release admission; retained parent сохраняет собственный Pin и fixed leases.
Ctor сначала завершает throwing indices/proxy initialization, затем передаёт
Pin/parent/lease. На controlblock failure deleter уничтожает объект при ещё
действующем job. На успехе родитель хранится до последнего intent owner.

Destructor стирает fixed semantic values до reverse member destruction:
values/indices, intent lease, parent, own Pin. Local values/parsed Birth и
plaintext scratch очищаются соответствующими существующими guards.
Нет публичных Files/HANDLE/writer прав. Успех не выполняет IO в destructor.
Pre-IO failure без начатого native IO не объявлен прерванной native работой.
Синхронные native calls не получают обещания принудительной отмены/latency.

Старый explicit root/own overload использует общий readImpl без parent и
сохраняет direct-only семантику. Existing selection/progression/schema/writer
bytes не изменены. Files sticky failure и blockWrites не ослаблены.

## Тестовая матрица и пределы её доказательств

FilesTests: новая `linkedMigrationPairs()` начинается на 1372; вызывается в
обычном native target перед прежним explicit `protectedMigrationPairs()`.
Assertions активны; targets/timeout/security checks не ослаблены.

- Native generated schema1/2 × queue/package; g1 equality, разные generations,
  stages, reordered sources, immutable/sticky mutations, BOTH authenticated
  payload failures, singleton/missing/bad index/block и direct Birth faults.
- Matching prepared queue с independently reserved ID без queue indices —
  link-only success. Bad queue indices намеренно не читаются; package linkage
  также не доказывает actual queue snapshot/authority.
- Bootstrap mode/peer tuple, null/explicit-only/cancel, fixed queue mismatch,
  malformed/missing/foreign physical ID, hardlink/ACL/reparse faults.
- RootA/B имеют одинаковые ID bytes и различные intent payloads: overload читает
  retained A независимо от process cwd B; corrupt B не заменяет источник A.
  Это root-binding witness, не доказательство произвольной hostile rename race.
- Last-owner native store/bootstrap/queue/intent locks, release/cleanup/retry;
  один active job и два retained Pins, job/pin/quota refusal.
- Все actual linked allocation failure/cancellation ordinals, все 10 native read
  fault/cancel ordinals, 14 hash creation ordinals и exact cleanup/fresh retry.
  Source подтверждает after-decode/final publication polls; runtime cuts не
  объявлены exact scanner-location coverage.
- Job/lease witnesses в afterRead относятся к реальным intent index/Birth reads.
  Global allocation hook для migrationFactory не утверждает эти witnesses на
  каждой ранней allocation ordinal: часть выделений предшествует полной lease.
  Lifetime до cleanup отдельно подтверждён SOURCE ordering и cleanup/retry.
- noEffects проверяет product native counters writes/flushes/renames/searches/
  diskChecks/creates=0. writerArtifacts сравнивает bootstrap subtree, не весь
  файловый мир; generated setup/repair находится вне factory invocation.
  Восстановление отрицательной fixture не является production repair.

## RED, chronology и узкая исправленная причина

Лично прочитаны RED receipt/map/raw:
`graf-f200-bootstrap-link-red274.BRuMZK`, 204 frozen входа совпадают с map,
receipt.source совпадает с map; build0/test8, assertion1405, 0.14s.
Native parent уже valid; stub не возвращал linked result. Это runtime RED,
не compiler failure и не подтверждение будущей полной матрицы.

Первый loader19202 имел shell quoting refusal до build/tests. Его outer
prlctl exit0 НЕ PASS. Исправленный runner запускался отдельно; reviewer
не исполнял loader и не переписывал эту историю.

Initial final274.g19Ips normal Release был build0/test8, 5/6, Files38.13s,
assert1909. Четыре linked cut rows завершились, но native-ID matrix ещё не прошла.
Диагностический LcqnDH запуск build0/test8, Files38.29s выявил:
schema2 subjectqueue fault3 ok0/value0/error12/native13 при expected7.

Реальная цепочка: discover получает изменённый object ID из id.bin; этот ID
входит в DPAPI entropy старого index; CryptUnprotectData отказывает до JSON parse.
nativeFailed/GetLastError → codecFileError → protectionFailed, не invalidContent.
Native/unknown отказ не переименован в доказанную corruption.
Узкая корректировка теста: fault3 expected protectionFailed и exact
ERROR_INVALID_DATA, при сохранении no-result/cleanup/no-effects/repair/retry.
Сохранённый stderr вывод — только schema/subject/fault/error/native числовые
метаданные, без содержимого/путей. Production для этой коррекции не изменён.
Initial failed и diagnostic exports сохранены отдельно, не заменены GREEN.

## Принятые реальные execution artifacts

Все ниже — исполнения main; reviewer лично прочитал Mac exports, BOM удалял
только в памяти при JSON parse, байты/хеши неизменны. Reviewer не выполнял
Windows/NTFS/EXE execution или собственный VM readback.

| Lane | Реальный результат на corrected204 |
| --- | --- |
| Native Release x64 | build0/test0, normal selected6/6, main total105.44s; raw Files89.63s |
| Native Debug x64 | build0/test0, те же normal6/6, main total251.18s; raw Files231.70s |
| Portable macOS | build0/test0, full46/46, receipt12.14s; NOT native DPAPI |
| Readback main61923 EXIT0 | source204 native/frozen match; native/export receipts match; 12 EXE hashes и PE0x8664; owned process guard successful |

Шесть normal targets: Sha256Tests, ProtectedCustodyCodecTests,
ProtectedCustodyPackageTests, ProtectedCustodyFilesTests,
DesktopUploadQueueV2Tests, DesktopUploadRecoveryTests. Raw Command paths
соответствуют Release/Debug, а не только label. Все 12 readback entries лично
сопоставлены с configuration receipts; mismatches=0.
Readback script прочитан: проверяет actual native/share source bytes,
native/export receipt bytes, actual EXE hashes/PE и active owned jobs.
Его фактическое исполнение — main evidence, не заявлено reviewer execution.

Linked factory actual cuts EACH schema1/2:
Release queue228/package246; Debug queue503/package539.
В каждой строке reads10/hashes14/directBirth2/final allocation cancel checked.
Debug iterator proxies реально charged (16B), отказ/cleanup/move регрессии прошли.
Release proxy=0 SKIP существующих proxy-only regressions не выдан за Debug proof.
Native-ID fault3 для обоих subjects actual error12/native13/expected12, value0.

Зелёные protected AAC/V5 строки внутри FilesTests не исправляют отдельный
legacy NativeHashFailureTests. В этой wave нет ALL50 или supplemental packed
consumer rerun; прошлый known AAC RED/не-GREEN fullsuite остаётся открытым.

## SHA-256 финального снимка и подтверждений

| Файл | SHA-256 |
| --- | --- |
| Files.h | `e0df4ebdd58b923ddd98b0b5319e8184189fd6746dceee0f8786cfe7009acba0` |
| Files.cpp | `6da9cb41f71eb230fe6c0522dfcac4a705d807d550259b890d46ed00724c241f` |
| Metadata.h | `e22c13fbfe7b0e3275cb3373103496a2db7539abbf9be1dcba0bc1b71c3d7631` |
| Metadata.cpp | `afa2a449fb73dc25b6eba5a38533732b4f523a74911ef850179668a052083993` |
| FilesTests.cpp | `46767008a8db6c35bb9a63df1f23fdf42c79866c81612906e989b2fcc08f6846` |
| source-red274.json | `ae767d5c7a200fe4872e808089ca76eda929100da57eebc5b31a5ef671c01d2d` |
| red-native274-release.json | `5f22e08d35f34a39473fb8346b962653cc50e077928f16de9a61a293d97605a6` |
| red-native274-release-test.log | `3d0265e361fd3b24797bf6a0a8a0c451d830d31688563d8a73399aa876bd5e0e` |
| final-native274-release.json (failed initial) | `ed7c4b09bd9ad84a924b488f3b8ba974b8b31cafe483e63fa40e4547701f52c0` |
| final-native274-release-test.log (failed initial) | `1b7ff2fcb93a0d2fa38034d634a7ec53868d1fe1995cd314910e5acc58b7c538` |
| diagnostic-native274-release.json | `b0ed829d0c89cb2f230edc9de9851bac4adb8e308f38bbdd7ecc15df9e3af85d` |
| diagnostic-native274-release-test.log | `78089f552f591bc4701d26240bb0a39941773e9e57c761f5ad734a177aef1dbe` |
| accepted-native274-release.json | `a368f1a3291aea03dd7177d5ba9a0aa620475d0df4abde504f91e27e7dcc65a9` |
| accepted-native274-release-test.log | `5e4febcd8c918410fec47fdbd02c1709baf927c6585b32c4b53160d287163be3` |
| accepted-native274-debug.json | `edf0964baa28f4692ee30df996131feb7f6c01f5518cf54ee524b54d966f3fa8` |
| accepted-native274-debug-test.log | `cb062ab0247b9abb671395dba4685d53fba110d283f8243e0e88daba72bddeac` |
| readback-accepted274.json | `18e15e3997408b0d706e797867d35203a3088cdc85231e0db01e0ae69945993e` |
| portable-accepted274.json | `cefddd18db58741fd129eda84f2f913ef2dcbc1b7fbeea8fcafddfc3449ab72a` |
| portable-accepted274-test.log | `1c85d6770bab33dff4414599097b832881850f5d5229dbc952f216f9ddc13a76` |

## Ponytail и обязательное продолжение

Ponytail: **Lean already. Ship.** Только в смысле формы принятого компонента,
НЕ shipment продукта. `net: -0 lines possible.`
Новый overload/private friend/shared readImpl переиспользуют один native/BOTH/
semantic flow. Удаление retained parent, per-slot fixed ID binding или final
poll нарушило бы требования; второй scanner/owner/framework не нужен.

Следующий owner должен связать эту genuine пару с actual protected logical
queue/destinations и stage authority, независимо проверить account/epoch/
currentness/source hashes, root absence/inventory и tombstone conflicts,
закрыть startup fence ДО legacy load/sweep/recover. Protected selected rejection
этого overload не разрешает effects. Prepared reserved queue без indices
остаётся DENY fence, не empty queue. Copy stamps не whole-tree proof.

T116 и конечная цель приложения не закрыты; physical Windows x64, installed
parity/audio/auth/upload/accessibility/signing/release отдельны. Новое issue,
task marker, commit/merge/release разрешение не выдаётся.
Единственная запись reviewer — этот новый отчёт; все 156 прежних файлов,
normative/task/governance/production/test inputs сохраняются.

## Дополнение до финальной фиксации: App build-only, не runtime

После core SOURCE проверки main сообщил session48582 terminal0/build0.
Reviewer лично прочитал app-accepted274.json и validate-app/readback-app scripts.
Receipt terminal=true, build_exit=0, mode=build-only-no-install,
configuration=Release, architecture=x64; source совпадает с тем же map204.
Script выполняет GrafWindows.sln /restore /t:Build в отдельном fresh root,
Windows SDK/WebView2 с pinned native AEC guard; ничего не устанавливает/запускает.

- app-accepted274.json SHA-256:
  `9685f73d4b43aacefe6123007aa2d52468af663e8336edab444cbc0a59270733`.
- EXE SHA-256 из build receipt:
  `dbf6cd3a25543ac8870c07792954dccfc0cb84b372e822660f4f039afeb5dfd3`,
  machine34404 = PE0x8664.
- AEC provenance SHA-256:
  `14bff774615f3dfa12188d53dea8fcad1a19fbcf7800f66faa46ce76c549556e`;
  pinned AEC source `846fe90a289f58b7c9303a635142aa2c7caa93e5` verification
  сообщён main, guard не обходился.

Первый App readback prlctl255 до исполнения НЕ PASS. Main после fresh running
check сообщил retry95866 terminal0: source204/native+frozen, native/export
receipt, actual EXE/PE совпадают; owned build/test0. Reviewer прочитал script,
проверяющий именно эти bytes/guard; результат выполнения принят как сообщение
main, НЕ reviewer VM execution. Script выводит stdout, отдельный
readback-app-accepted274.json не создаёт и reviewer не заявляет его наличие.

D9025/C4100 warnings сохраняются; zero-warning/NuGet security audit не заявлены.
Это только совместимость сборки текущего204, не execution/MSIX/installed proof,
не startup/queue admission. Root CHANGELOG reviewer не менял; main сообщил
append-only validation/F200 fragment. Core scoped GO и открытые пределы выше
не расширены данным дополнением.
