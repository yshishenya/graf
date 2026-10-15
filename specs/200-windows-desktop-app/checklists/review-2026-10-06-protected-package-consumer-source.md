# Независимая проверка исходного кода Round256b: LIVE + SEALED batch

Дата: 2026-10-06. Владелец: независимый reviewer.
Область: Feature200 / T116 / только зависимость fixed2×5 readonly member batch.
Полоса: high-risk-product storage; независимый SOURCE review без исполнения.
Единственный разрешённый edit — этот новый отчёт.

## Решение

**SOURCE GO — 18/18 требований REQ256 для LIVE+SEALED batch prerequisite.**
Замечания в этой области: **CRITICAL0 / HIGH0 / MEDIUM0 / LOW0**.
Это принятие прочитанного исходного кода при совпадении пяти frozen256b SHA
ниже и указанного поддерживающего кода, НЕ EXECUTION ALL PASS,
НЕ full protected-package consumer GO, НЕ final DOCS/installed/release GO.

Проверены обе фактические ветви: LIVE использует актуальный проверенный
checkpoint обеих closures; SEALED — exact historical generation/root/length
и whole logical SHA. Любая ошибка отклоняет весь batch без partial value.
Reader не предоставляет normal/manifest/account/short/upload/delete authority.

**Не приняты:** LocalRecordingPackage protected overload, MF/transport/app
wiring, full normal/degraded/manifest/format/duration/reason/short predicate,
bootstrap/queue/migration/account effects. T116 целиком, T117/T118/T120,
H250 и installed/hardware/release остаются открытыми. Для следующего
semantic consumer нужен отдельный REQ review, как требует исходный gate.

## Источник, метод и ограничения доказательств

Canonical:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`;
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
HEAD — якорь ветки, не идентичность незакоммиченных bytes. Dirty work сохранено.

Навыки code-reviewer и ponytail-review прочитаны целиком и применены
к локальному исходному коду. Root AGENTS и guidance index прочитаны;
более близких AGENTS в этих source/test subtrees не найдено.
Обязательный нормативный контекст лично прочитан в предшествующей REQ256
проверке; текущие spec/plan/tasks/quickstart/model, оба custody contracts
и constitution повторно сверены SHA — неизменны. §§6/6.1 packed и
logical IO/package/full-authority границы базового contract перечитаны.
Исходный REQ18 gate лично прочитан; его SHA сохранён ниже.

Лично прочитаны целиком все пять source-ready файлов, включая весь
Reader.cpp и обе native test translation units (FilesTests2197 строк
первой версии, TreeTests1954 строк первой версии). После фиксации256b
лично перечитаны изменённые single/batch lifetime scopes и сняты новые SHA;
все пять совпадают с предоставленным main frozen256b.
Прочитан git diff этих headers/Reader относительно HEAD. Он включает
более ранние изменения dirty work, поэтому не выдан за чистый Round256-only
commit diff или SOURCE review всего незакоммиченного продукта.

Лично прослежены поддерживающие пути:
- Metadata packageShape :32–68 и собственный Pair read :239–299:
  native exclusive metadata lease, BOTH payloads, strict parser/provenance;
- Files open/readBlock :242–308 и shared validator :487–599:
  физические snapshots/DATA обеих slots, missing/fallback различия;
- packed Owner Guard/open :730–880 и header:
  тот же actual expected context, mutex/job/HANDLE, readExisting без writer capability;
- Tree verify/verifyRetained :1–159, checkRead/readBlock :414–490:
  actual current BOTH closure и дополнительная historical closure;
- Memory/Codec headers: charged vectors/control blocks, общий лимит,
  pin/job admission; Sha256.cpp :208–263: exact stream length/EOF/full hash.
Реальные consumer пути LocalRecordingPackage/transport/AppMain были
прослежены лично на этапе REQ256; inspected LocalRecordingPackage h/cpp
и DesktopHttpTransport.cpp не изменились по SHA. Их adoption НЕ принят.

Reviewer не запускал VM, build, tests, приложение, устройства, GitHub,
network или mutations main файлов. `git diff --check` — только проверка
пробелов, не execution evidence. Обнаружение внешних receipt файлов
по именам не дало доступного результата; не заявляется личное чтение
RED/failed/GREEN manifests, native EXE или NTFS receipts.

## Frozen256b — лично вычисленные SHA-256

| Файл | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp` | `c6de956a7c546647afddc910fa3dd0b153d731ecb354c974b81fb8b51752767d` |
| `apps/windows/RecApp/Storage/ProtectedCustodyReader.h` | `98f688c86b0499549baec78a7ef2a225c3c80ba20754ee1fe1d9c650d399cc94` |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.h` | `7b5587e240b66492f39410c87ea55ce62664f3308843556b96173410528f6ccf` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp` | `318689445ab8056d45560e6fbc305c84457d718529e53f6e99c6be3da7cb8958` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp` | `197cf85b46b82421c1d3dcd72e53376429e59cf32c4165ca3a9a3424151fed9c` |

Первая рассмотренная256 версия тестов имела SHA Files
`e382416d3b97e7f7991e3d44ec297e5bd848a16e5455f196a2cce9ced1bf3087`,
Tree `7bfdb3cbd13fc5462ecff136785afd33d4c535278b1c939a356376223fda426a`.
Она НЕ является принятой финальной версией тестов. Production три файла
не изменились между первой личной проверкой и256b.

Коррекция256b нормативно правильна:
- Flat livePackageGroup освобождает `batch.value` перед independent single
  factory. Assertion `single.ok()` сохранён, actual Pair остаётся held.
- Packed livePackedMember открывает healthy single в отдельной области
  до batch; его real result уничтожается перед вторым exclusive owner.
  Healthy/empty assertion `single.ok()` сохранён.
- Удалён только непреднамеренный overlap двух независимых exclusive groups.
  Не ослаблены production sharing flags/locks, не введены mode/fault knobs,
  не удалены group/Clone lifetime checks. Отказ первого исполнения256
  поэтому не скрыт и не объявлен product PASS.

## Сопоставление с REQ18

PASS-SOURCE — вывод по прочитанному коду; не результат запуска.

| ID | Вывод и проверяемый источник |
| --- | --- |
| R01 | PASS-SOURCE — existing batch :302–410 обслуживает actual LIVE prerequisite без нового task/scanner/consumer. Tests livePackageGroup проверяет finalizing→sealedNormal с lower-only canonical, а не slot erase. |
| R02 | PASS-SOURCE — held own Pair :311, preflight BOTH values :313–329 и сборка BOTH physical slots :332. Pair private construction/read сохраняет обе payloads и native lease; caller-created parsed value не принимается. |
| R03 | PASS-SOURCE — :318–320 различает exact sealed triple и null LIVE. Phase/null/packed root rules установлены собственным Pair parser packageShape :38–60; LIVE разрешён только capturing/finalizing, packed live extent/root null. Null не трактуется как length0 или empty SHA. |
| R04 | PASS-SOURCE — :317–328 role1..5, same-role object/representation/container equality и cross-role duplicate object rejection ДО member IO. Context/directory :338–340 из Pair; fixed role location, не JSON path/extension. |
| R05 | PASS-SOURCE — фиксированный PackageReadLease :34–42; files/owners выбираются по role. :346/:366 открывают physical role один раз. LIVE и SEALED sibling того же role используют тот же actual owner без release/reopen gap. |
| R06 | PASS-SOURCE — :369–378 использует existing BOTH physical validator и сохраняет оба indices; :380–381 выбирает actual highest generation для LIVE. Это media checkpoint, не metadata state generation. |
| R07 | PASS-SOURCE — :372–374 отвергает trustedPrefix и отсутствие peer.generation. Generic singleton verified shared validator не становится batch success. Recovery/native cause повреждённого DATA сохраняется; для missing snapshot batch выдаёт recoveryRequired без synthetic repair. |
| R08 | PASS-SOURCE — :345–361 expected context/container и existing readExisting owner; LIVE вызывает Tree::verify того же owner. verifyImpl :109–125 проверяет actual prefix, paired heads и полный walk ОБЕИХ current closures. Никакого verifyRetained с null/synthetic stamp. |
| R09 | PASS-SOURCE — SEALED :353–360 exact protected root descriptor и verifyRetained; flat :382–387 exact доступная generation/length, не highest substitution. :397–400 whole logical SHA только SEALED. Historical g2 вне current heads проверяется отдельно от healthy current closure. |
| R10 | PASS-SOURCE — CustodyReader.state=verified означает только checkpoint; comments Reader.h явно запрещают complete-frame/manifest/normal/account/effect authority. Ни package inspector, ни upload/delete не подключены этой правкой. Empty checkpoint не объявлен normal/trusted prefix. |
| R11 | PASS-SOURCE — ReaderState.package :44 и assignment :393 удерживают ВСЮ группу. Clone :232–241 разделяет state; group не держит COM streams, cycle отсутствует. group Pair объявлен первым и освобождается после всех members. |
| R12 | PASS-SOURCE — прежние bounded readonly COM методы сохранены; Read exact length/tail/S_FALSE и got0/wipe/no cursor advance при fault. SEALED hash доказывает EOF; :402–405 rewind ALL streams в cursor0, включая LIVE/empty. Clone cursor independent; Write/SetSize denied. |
| R13 | PASS-SOURCE — shared atomic failure :65–70, status :72–83. Записанный group fault проверяется до late cancel и распространяется на siblings/Clones. Любой factory edge/proof/hash/rewind отказ возвращает nullopt; result не публикуется частично. |
| R14 | PASS-SOURCE — shared owned token :49, checks до factory/IO, после closure/state, hash/rewind и перед return :306/:333/:392/:406/:408. Native work синхронный; stack job/guard и owned buffers не освобождаются до actual completion, отмена не завершает чужую работу фиктивно. |
| R15 | PASS-SOURCE — group/state allocate_shared и Reader operator new через existing CustodyAllocator; snapshots через charged CustodyVector; fixed arrays/proofs, одна process cache≤256KiB. Memory.h сохраняет jobs4/pins32/owned64MiB. Дополнительные LIVE proof/Reader учитываются теми же admissions, лимиты не увеличены. |
| R16 | PASS-SOURCE — existing worker-only factory/read/last-release contract сохранён; нет UI/capture callback IO в этой зависимости, plaintext temp/codec URL/export/network/protocol writes/flush/publish/GC отсутствуют. Pair/group не раскрывают writable handles/proofs. |
| R17 | PASS-SOURCE — account/session/epoch/bootstrap/short/degraded/normal/finalizer effects не переносились в Reader и не ослаблены. Batch readable checkpoints не принят как whole-package authority; future protected inspector/transport требует отдельного REQ. |
| R18 | PASS-SOURCE — новые существующие native test cases содержат substantive assertions обеих representations, отказов и lifetimes; настоящие RED/GREEN сообщены main отдельно. Runtime receipts/native builds/final DOCS/installed не объявлены прошедшими этим SOURCE GO. |

## Лично прочитанные новые и сохранённые проверки

### Flat

`livePackageGroup` :1674 и далее:
- g2 bytes{1,2,3} vs actual highest g3 bytes{8,9,10,11,12};
  birth BOTH LIVE читается как actual5 bytes, single LIVE target отвергается;
- healthy SEALED g2 + LIVE g3 проверяют различающиеся exact lengths/bytes,
  S_FALSE/EOF и Write/SetSize refusal, sealed single после actual release batch;
- missing current live DATA, singleton index, bad sealed SHA и same-role
  identity mismatch дают whole result без value; missing DATA сохраняет
  ERROR_FILE_NOT_FOUND, identity mismatch — opens0/reads0 до IO;
- finalizing в противоположной slot и selected sealedNormal с media/playback/
  manifest и canonical только в lower LIVE slot. Это STRUCTURAL scenario,
  не normal manifest/format/admission acceptance;
- injected live ReadFile fault распространяется на sealed Clone, выигрывает
  у late cancel; reset Pair/table сохраняет exclusions для всех4roles и
  own package-state до actual last Clone release; нет writes/flush/rename.

`sealedFlatMembers` и `sealedPackageGroup` остаются substantive:
empty/1/65536/65537, exact old/new bytes/SHA/length/object; unavailable
generation; missing DATA/peer; all5roles/ref reverse order; asymmetric3/5;
pin32/job4/memory refusal before IO; group first native cause/late cancel;
Clone держит all members; representation mismatch preflight0IO;
lower-only bad sealed ref отклоняет healthy selected target.

Один прежний all-LIVE invalidInput negative в sealedPackageGroup :1645–1652
заменён не на success/noassert: healthy LIVE плюс preceding bad sealed SHA
по-прежнему отклоняет WHOLE group с invalidContent и actual IO.
Не заявляется побайтная идентичность тестов историческому SHA254: их
success domain намеренно расширен по REQ256, текущие retained negatives
лично прочитаны. Все прежние native confinement/codec/fault/read/MF/budget
проверки присутствуют в полностью прочитанной translation unit;
`NDEBUG` снят до assertions; новые функции включены в default native main.

### Packed и смешанная группа

`livePackedMember` :302 и далее:
- current g4 LIVE5 bytes vs retained SEALED g2/3 bytes вне current heads;
- corruption nonselected current g3 closure, historical-only g2 corruption,
  wrong SEALED SHA/container отклоняют batch целиком;
- actual empty birth0 читается exact EOF, не normal/prefix;
- healthy single отдельным scope перед batch; отмена записывается общим
  sticky fault, token reset не даёт SEALED sibling успеха;
- surviving LIVE Clone держит own Pair и packed owner, writer exclusion
  сохраняется до last release.

`mixedPackageGroup` :377 и далее сохраняет all original SEALED byte/
length/lifetime assertions и добавляет finalizing LIVE packed canonical
к прежним packed media/playback и flat manifest/recovery.
Все5roles обеих physical slots читаются; finalizing не normal authority.
Flat Clone исходной группы по-прежнему удерживает все packed/flat/Pair
exclusions. Новый batch использует тот же порядок role ownership, без
second same-role owner или slot repair.

`sealedPackedMember`, retainedStampRejections/ClosureAndEmpty/Admissions,
currentAndLowerCorruption, Reader/CopyTo/charged move/budget cases также
лично прочитаны целиком. Новые live/mixed calls есть в default native main;
portable ветвь их НЕ исполняет.

## Безопасность и простота

Ponytail: **Lean already.** Безопасного удаления/замены в этой зависимости
не найдено. Existing batch/validator/Tree/read adapter переиспользованы;
нет новой библиотеки, scanner, public mode flag, второго cache, backend,
очереди или формата. Frozen proofs для двух refs могут отдельно проверять
одни current closures — bounded≤10 cells, те же actual owner/admissions.
Объединение live proofs ради экономии не требуется для корректности и
добавило бы новую политику cache/selection; не предлагается.

Недопустимый caller COM input/unsupported operation сохраняет прежнюю
nonpoisoning область; он не стирает записанный shared fault. Valid subsequent
read/control и поздняя отмена не возвращают группу в healthy состояние.
Настоящие custody/native/semantic/read allocation faults остаются sticky.
Это не новая политика и не изменение ранее принятых COM guarantees.

Group/state/COM allocators удерживают actual memory charge до deallocation.
LIVE не создаёт ожидаемый length/SHA из null; exact selected proof/index
заморожен до last release. На исключении/частично собранном result RAII
освобождает Readers и members, но не возвращает частичный success.
Read cache содержит только один bounded block; смена owner/last state
очищает plaintext; proofs не становятся публичным writable capability.

## Исполнение main — отдельно, не личный EXECUTION GO

По сообщениям main:
- RED на старом Reader.cpp + новых existing tests: restore/build0, ctest8,
  оба batch.ok false; RED receipt SHA
  `a65bc5a18319ef7290062e9f134fbe9067ba1236e8e2bf4123802bc6878e0a06`.
- Первый native256: build0/test8, batch.ok достигнут, independent single
  отказал из-за overlap exclusive groups. Failed receipt SHA
  `501b6f6620fc8394b34842654a2747305971df227aac495e76de52996fdf9020`.
- Исправленный256b: focused native Release2/2PASS36.78s и portable46/46
  PASS21.50s, build0. Debug→SDK→Full50 main сообщил RUNNING.
- Main передал inputs manifests SHA
  `1a79aa07f2f02c9c3679d18963225b52b6c32d73d2a3aecb428f01e950dac958`
  (171 inputs) и
  `a17ee221dedbda85d07866a891de9c553e417da7f3a1eb525484a37676d2d63c`
  (178 inputs).

Все пункты этого раздела атрибутированы main, НЕ лично прочитанные
receipt/EXE/input manifests и НЕ fresh exact native ALL PASS reviewer.
Не связываю незавершённый job с успешным итогом. Последующие actual exports,
Debug/full/SDK receipts, финальные документы и source/EXE/input equality —
отдельный этап; этот SOURCE verdict от ожидания execution docs не зависит.

## Поддерживающие SHA и неизменные нормы

| Поддерживающий файл | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp` | `ae784b46f417c503e592410edd7dc71ab8131592f5cfeb04c235e0a96a817b82` |
| `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp` | `c917b43a94d09547be829694b6cf9c44efde0f91d03dce4c931d8534fa68a1f7` |
| `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h` | `3e1f12fda3e18463c6430921e16173afac5c549aaebfa222efcc9dd24b743478` |
| `apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp` | `c308ac7159695a5a1e8edc1c65a1332481c576fff4f53b2ab270c99960d97391` |
| `apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h` | `99dee259444c8a552d3e759e91e10a5a301d38991bfa655ebb90e5abb03922ed` |
| `apps/windows/RecApp/Storage/ProtectedCustodyMemory.h` | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |
| `apps/windows/RecApp/Storage/ProtectedCustodyCodec.h` | `a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde` |
| `apps/windows/RecApp/Storage/Sha256.cpp` | `84032d4a6b8f6a8c2e52e9bdd194d1cffe70050216cc3b392964ff46798ae76c` |

| Нормативный артефакт | SHA-256 |
| --- | --- |
| `specs/200-windows-desktop-app/spec.md` | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| `specs/200-windows-desktop-app/plan.md` | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| `specs/200-windows-desktop-app/tasks.md` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| `specs/200-windows-desktop-app/quickstart.md` | `bfb69e14ccf1fa01cd2e6f31bb6ac3df995e25cd0fa807cdb1fdaa8b1de2abe3` |
| `specs/200-windows-desktop-app/data-model.md` | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| `specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md` | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| `specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md` | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| `.specify/memory/constitution.md` | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

12 нормативных/consumer артефактов предыдущего REQ snapshot сверены,
изменений0; Reader.h отдельно изменён по разрешённому scope и принят
по своему fresh SHA. Это не новая проверка полной implementation всех норм.

## История checklist и граница записи

Исходный снимок SOURCE reviewer: **106** существующих Markdown файлов.
Это предыдущие105 плюс собственный REQ256 report, не106 новых obligations.
REQ report SHA:
`9ba7fc1a416ca8fb2aeb78dfc48f37dec5d35e8b882ea990d231cae93f722109`.
Индивидуальные hashes исходных105 полностью сохранены в его inventory;
он и все эти файлы остаются неизменными.

Sorted исходный106 manifest SHA:
`649d8f42bdc0eae504f9f90119fa8d36957bffbfa80fae7827ffb9d05e2e8ed7`.
Алгоритм: sorted UTF-8 repo-relative path + space + SHA256 + LF.
После сохранения этого отчёта требуется побайтная повторная сверка106.

Счёты сохраняются отдельно:
- текущие10 нормативных checklist: **154 checked /0 unchecked**;
- исторические/прочие95 предыдущего inventory: **256 checked /10 unchecked**;
- собственный REQ report:0/0; этот SOURCE report:0/0 checkbox markers;
- старый общий счёт: **410 checked /10 unchecked**, не runtime PASS;
- tasks: **120 total /93 checked /27 open**; tasks SHA
  `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.

Reviewer не редактировал старые checklists/reports, spec/plan/tasks,
code/tests/build configuration, GitHub, VM, рабочий профиль, сервер или
коммиты. Единственная запись — новый owned SOURCE report.
SOURCE GO ограничен frozen256b LIVE+SEALED prerequisite; full consumer
и H250 не закрываются, implementation tasks не отмечаются выполненными.

## Повторная сверка после сохранения SOURCE report

Лично повторно вычислены все hashes: **106/106** прежних checklist/report
файлов совпадают с исходным снимком; sorted manifest SHA остаётся
`649d8f42bdc0eae504f9f90119fa8d36957bffbfa80fae7827ffb9d05e2e8ed7`.
Все **13/13** frozen/support source файлов неизменны. HEAD повторно прочитан:
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Повторный подсчёт: текущие10 checklist154/0, исторические95 —256/10;
REQ и SOURCE reports0/0; tasks93/27. `git diff --check` exit0.

После первичной нормативной сверки main обновил quickstart subsection
«Совместное чтение рабочих и запечатанных файлов обеих версий». Поэтому
таблица выше сохраняет ИСХОДНЫЙ нормативный snapshot, а не утверждает
неизменность текущего quickstart. Fresh SHA quickstart:
`fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e`.
Из12 нормативных/consumer файлов изменился только он; остальные11 неизменны.
Подраздел лично перечитан полностью: LIVE highest/BOTH closures,
SEALED exact historical length/SHA, fixed2×5 actual ordinal, no singleton/
trustedPrefix success, whole-group leases, последовательные independent
factories и запрет slot erase/sealed workaround согласованы с SOURCE GO.
Single LIVE target по-прежнему отвергается; normal/manifest/account/wiring
и H250 не приняты. Это проверка указанного подраздела, не final DOCS GO.

Main дополнительно сообщил focused Debug2/2PASS50.37s и SDK restore/build0
с actual AEC3 identity `846fe90a289f58b7c9303a635142aa2c7caa93e5`.
Full50 сообщил RUNNING. Эти сведения остаются атрибутированными main,
не лично проверенным EXECUTION ALL PASS. На момент этой сверки директория
экспорта `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI/receipts-round256b`
ещё отсутствовала. Независимая проверка actual receipts/final docs ожидается
отдельно и не расширяет область настоящего SOURCE GO заранее.

## Финальная проверка документов и экспортированных доказательств Round256b

**DOCS / exported-evidence GO для LIVE+SEALED batch prerequisite.**
Замечания в этой области: CRITICAL0 / HIGH0 / MEDIUM0 / LOW0.
SOURCE GO18/18 для frozen256b сохраняется; это отдельное решение о
согласованности документов, входных файлов и сохранённых результатов,
НЕ независимое исполнение Windows EXE/NTFS и НЕ full consumer/product GO.

Лично прочитаны и разобраны все6 JSON из точной outsideGit директории
`/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI/receipts-round256b`:
все scalar fields, source maps и EXE maps. Windows UTF-8 BOM снят только
в памяти для JSON parse, сами receipt bytes не изменены. Индивидуальные
SHA вычислены по оригинальным bytes, включая BOM/CRLF.
Лично прочитаны manifest171 `source-live-round256b.json` и manifest178
`source-sdk-live-round256b.json` в родительской outsideGit директории;
каждый actual local файл заново hashed и сравнен со всеми map entries.
Карты6 receipts сравнены полностью, включая исторические отличия RED/
failed от frozen256b. Не заявляется совпадение старого RED кода с GREEN.

| Экспорт | Лично прочитанный terminal результат | SHA-256 |
| --- | --- | --- |
| `graf-f200-live-round256-red.json` | failed; configure/build0, test8;171 inputs,2 EXE bindings | `a65bc5a18319ef7290062e9f134fbe9067ba1236e8e2bf4123802bc6878e0a06` |
| `graf-f200-live-round256.json` | failed; configure/build0, test8;171 inputs,2 EXE bindings | `501b6f6620fc8394b34842654a2747305971df227aac495e76de52996fdf9020` |
| `graf-f200-live-round256b.json` | passed; configure/build/test0;171 inputs,2 Release EXE bindings | `aab831af6059f51087a2e43862f3362bbfbc29897a5da6715922d68044981621` |
| `graf-f200-live-round256bdebug.json` | passed; configure/build/test0;171 inputs,2 Debug EXE bindings | `b6ca2537b8c8d42cfa9fd708e66d5f017eac1628f1c61625c61e70291338f768` |
| `graf-f200-all-round256b.json` | passed; configure/build/test0;test_count50,171 inputs,50 EXE bindings | `098b44d4ae3cb27be64e40737bdcb5651adc8768bd72d5b29fa1d84f95ac41c2` |
| `graf-f200-sdk-live-round256b.json` | passed; restore/build0;178 inputs,1 app EXE binding; build-only | `cb7213a58299cee12c58caedffd15ac62a81a0f364afbcb8e895f11a5453d24f` |

Во всех6 terminal=true; заявленный source_count совпадает с числом entries;
все source/EXE digest fields — полные64 hex. Лично подтверждены:

1. Manifest171 SHA
   `1a79aa07f2f02c9c3679d18963225b52b6c32d73d2a3aecb428f01e950dac958`;
   maps focused Release/Debug/Full полностью совпадают друг с другом и с ним.
   **171/171** файлов current canonical `apps/windows` совпадают по bytes.
2. SDK manifest178 SHA
   `a17ee221dedbda85d07866a891de9c553e417da7f3a1eb525484a37676d2d63c`;
   SDK map полностью совпадает с ним; **178/178** actual local файлов MATCH.
   Его171 общих entries идентичны native map;7 дополнительных build/package
   inputs лично прочитаны в map и сверены с actual local файлами.
3. Все5 frozen256b source hashes и8 supporting hashes неизменны.
   Failed256 отличается от GREEN только2 test SHA, production3 совпадают;
   исторический RED сохраняет старые3 production и свои2 test SHA.
4. Обе focused Release EXE bindings совпадают с одноимёнными Full bindings:
   Files `71d71534357bbee6e3864916fcac78e57ccb3a3c811dc89c87e53cd0eac54cea`,
   Tree `5a8995485bcdf9b6121766c0b84f2865cf3adb6139b157d06aa3c48e0beaf633`.
   Debug имеет отдельные bindings, не заменён Release:
   Files `7cdb97c865470d07cdad27082f1f270c956910320684efb19be70ed99f1be4d4`,
   Tree `c955a4850a00bf0290b17b0d88bf2ea90887f19ae44227fc4db6d163ce837228`.
5. SDK EXE binding
   `897fad71cbe6fcead39bd7b4d93f65d1240cb504325ffeb348c308ae2138ecc4`
   совпадает с указанным в final validation/main сообщении. Это сравнение
   bindings, не личное чтение этого Windows EXE.

Лично полностью прочитаны outsideGit scripts `read-all-round256b.ps1`,
`validate-all-round256b.ps1`, focused Release/Debug и SDK build scripts,
БЕЗ запуска. Full script получает каталог ctest50, собирает50 EXE hashes и
ставит passed только после actual ctest exit0 с j1/timeout300. Export helper
повторно сверяет mirror/NTFS source, actual Release/Debug/Full/SDK EXE и
original/export hashes; existing directory отвергается до создания.
Его фактическое исполнение и чтение native файлов выполнено main, а не
reviewer. Причины assertion RED349/1716, failed single и длительности
36.78/50.37/235.72s известны из main/validation, не из содержимого этих JSON;
raw ctest logs/Windows EXE/NTFS reviewer не читал. Portable46/46, AEC3 identity
и latest governance/doctor остаются атрибутированы main, не доказаны шестью
receipt JSON. Их нельзя переименовывать independent execution ALL PASS.

Лично прочитаны весь append «Раунд256» в `validation-2026-10-02.md`, весь
`release_notes_round256_live_sealed_readers` в F200.yaml и обновлённый
quickstart подраздел. Все6 SHA таблицы validation совпадают с экспортами;
source5/input2/Release2/SDK1 bindings совпадают. Документы правильно
разделяют RED, failed lifetime setup, passed256b, build-only SDK и portable;
сохраняют j1/timeout300 и не объявляют SDK запуском приложения.
Initial Parallels invalid argument описан как setup failure main, не PASS.
Исторический initial SOURCE report SHA в validation НЕ выдан за текущий
дополненный отчёт; финальный SHA настоящего файла снимается отдельно.
T116/T117/T118/T120, full consumer, H250, installed/hardware/x64/a11y/release
остаются OPEN; задачи не закрываются, новый encryption policy не вводится.

Снимок лично прочитанных финальных документов:

| Файл | SHA-256 |
| --- | --- |
| `specs/200-windows-desktop-app/validation-2026-10-02.md` | `85ae2b2a49e1eeaadc699e061967319d22de021e4e03013258b73c6137f1a743` |
| `changes/unreleased/F200.yaml` | `74cabda7a68428284141a8cfc8df7360228a76af8110a902d7e8020d04bc5221` |
| `specs/200-windows-desktop-app/quickstart.md` | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |

Повторная сверка106 old checklist/report hashes и13 source/support hashes
после чтения exports: изменений0. Единственное отличие12 normative/consumer
от исходного снимка — согласованный quickstart. Spec/plan/tasks/contracts/
constitution и actual LocalRecordingPackage/transport bytes неизменны.
Текущие154/0 и исторические256/10 не объединены с runtime результатами;
tasks93/27 сохранены. Main сообщил повторный governance/doctor/YAML/diff
после closing docs как выполняемый этап; reviewer не запускает его параллельно
и не утверждает результата заранее.

**Итог:** SOURCE18/18 GO + scoped DOCS/exported-evidence GO, без полномочий
full normal/manifest/format/account/upload/delete и без независимого native
execution GO. Следующий existing LocalRecordingPackage protected consumer
требует отдельного REQ review до тестов/кода. Reviewer дописал только этот
owned report; старые106 reports, код, spec/plan/tasks, GitHub/VM/коммиты
не изменял.

После сохранения финального раздела лично повторно сверены:106/106 old
reports,13/13 source/support и3/3 final documents — все SHA MATCH;
SOURCE checkbox0/0, `git diff --check` exit0. HEAD снова тот же
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
