# Independent source review: packed cadence diagnostic / F200 T116

2026-10-04. **REQUEST CHANGES — 6 checked / 3 unchecked; C0/H2/M0.**
Runtime pending; source acceptance не выдана. Это test-only measurements,
не приёмка sustained capture, app Stop, SC-003, T116 или Windows release.

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
anchor branch/source_sha из прежнего feature.json: codex/200-windows-followup,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Git/VM/tests не выполнялись.
Lane high-risk-product storage; reviewer меняет только этот новый source-report.

## Лично прочитанный снимок

code-reviewer прочитан полностью. Requirements gate
`5c75950f05aae4a5ac5b55ed71e26b0cff93191c2ae5bbe0816042bbfb8c8222`
сверен,12/0 unchanged. Предыдущее полное чтение неизменённых Writer/Tree/Owner
и норм переиспользовано по hash. Новые участки OwnerTests лично прочитаны:
includes/allocator observer:1–79, native counters/wrappers:81–147,
codecspy:223–278, вся cadence:352–457, CLI/default main:1270–1326.
Дополнительно прочитаны actual Tree HEAD seal:334–355 и packed §4:147–167.
Остальная неизменённая full Owner history не перечитывалась и не принимается
автоматически за новое cadence evidence.

Исходный main snapshot1c6f467… уже сменился до чтения: лично обнаружен и
подтверждён текущий **896e7523b777ac65bca2f0c21e47de73299def11685ef48f3b435f79574c474a**,
включающий default packedWriterCadence(2). Main подтвердил эту freeze.
Только OwnerTests меняется в текущем этапе; production Writer/Tree и прежний
TreeTests сверены с accepted step3 snapshot. Reviewer source не изменял.

## Source критерии

- [x] PCD001 Diagnostic переиспользует existing Fixture, real Files TU wrappers, настоящие CNG/DPAPI codec calls; нет нового backend/product API/библиотеки/consumer adoption.
- [x] PCD002 Whole480-float frames, actual bytes и modelled ms отдельно от nominal target; pre-tail и post-tail generation/EOF проверены по фактическому total; milestone rows1/2/4/8/16/32/64 в explicit64MiB loop.
- [x] PCD003 DATA/NODE/HEAD seals и native/requested IO имеют точные типы/границы/labels. **H1: HEAD считается NODE**.
- [x] PCD004 Sequential full-block assertions сохраняют собственные1DATA+3NODE/290816B bounds, не общий resize ceiling. **H2**.
- [x] PCD005 Owned counter observations и sampled PrivateUsage названы ограниченно; нет fake OS/native peak, environment-dependent threshold, новых budget или giant plaintext input.
- [x] PCD006 Pinned g2 root читается после обновлений; все proof/read/writer/owner refs фактически release перед cold full verify; exact bytes проверяются bounded blocks и final owned baseline.
- [x] PCD007 Tail называется storage_only_no_dispatcher_or_encoder, без product Stop/5s/SC-003/sustained claim; cold timing отдельно от live, actual ACK не объявлен normal package.
- [x] PCD008 Short2MiB default и explicit64MiB CLI входят в прежний test executable; Release assertions включены, output generated metadata-only, существующие tests не заменены.
- [x] PCD009 Exact-final-SHA build/runtime/regression receipts подтверждают правильные observers/assertions. Текущих завершённых результатов нет; запущенные handles не PASS.

## H1 — observer считает HEAD как NODE (HIGH)

OwnerTests.cpp:226–228: `if(data)++cadenceData; else++cadenceNodes`.
Комментарий «Tree seals only DATA and NODE here, never HEAD» неверен.
OwnerTests:274–276 включает настоящий Tree.cpp под macro alias TestPackedCodec;
Tree.cpp:346–347 вызывает этот же seal с `Kind::head` для публикации cell.
Поэтому при нормальном sequential checkpoint метрика NODE содержит3NODE+1HEAD,
а `last_records` печатает1/4 вместо DATA/NODE1/3. `<=7` это пропускает.

Это не предположение по runtime и не новый предел: вызов HEAD seal лично
прочитан. Ошибка нарушает objective records-per-checkpoint measurement
(packed §7/plan step4/quickstart §14). Она может скрыть лишний NODE после
смены пути и делает сравнение с нормативным1DATA+3NODE недостоверным.

Минимально: считать NODE только для nodeL0/nodeL1/nodeL2; HEAD отдельно либо
исключить из явно DATA/NODE output. Не добавлять product knobs/framework и
не выдавать общее число seals за число новых appended DATA/NODE records.
Новые CLI receipts должны относиться к исправленному observer snapshot.

## H2 — sequential assertions используют resize budget (HIGH)

OwnerTests.cpp:403 допускает7NODE, :405 допускает327680B append на каждом
полном sequential checkpoint. Но packed §4:147–148 устанавливает здесь
**≤1DATA+3 новых NODE и append≤290816B**.7NODE+1DATA/327680 относится к resize
в том же §4:167; этот diagnostic последовательно пишет canonical frames,
не вызывает range SetSize/shrink. В текущем normal path больший bound может
пройти, но regression с4–7 настоящими NODE либо excess append тоже будет PASS.

Минимально: после исправления H1 использовать sequential bounds≤3NODE и
≤290816B для full checkpoint. DATA1/flush2 assertion остаётся; пределы
production resize/общие64MiB/5s не меняются. Это восстановление существующей
нормы, не новая performance threshold и не требование переписать Tree.

## Подтверждённое и точные пределы наблюдений

- Input:1920B фиксированного finite generated float pattern. `frameCount`
  округляет nominal target вверх до целого frame, `total=frameCount*1920`.
  Никакого padding или truncation; bytes/modelled_ms печатаются отдельно.
  Generation до tail1+accepted/block, после tail+1 при remainder≠0.
- Window `last_io/last_requested_bytes` берётся между двумя full checkpoint
  boundaries (:400–414), включая промежуточные frame write calls. Это **block
  interval** counters, не изолированный IO лишь одного checkpoint method.
  `last_checkpoint_call_ms` фактически измеряет весь crossing-frame writeAt
  (:392–406), включая RAM work/guards, не внутренний Tree commit duration.
  При документировании результатов эти границы должны быть явно названы;
  нельзя по ним заявить точную isolated commit latency. Начальный pinned
  full verify исключён из следующего native IO window, но входит в loop wall.
- `owned_new_sample_max` собирается в существующем global new, уже после
  allocator charge, не прямой native allocation observer. PrivateUsage
  sampled после full checkpoints; оно не OS peak. Final tail/pinned read
  ещё наблюдаются owned observer, cold scope начинается после выключения.
  Не заявлена доказанная peak latency/native/RSS quota по этим samples.
- Pinned g2 после первого full block остаётся до конца записи; old read
  проверяет его bytes. `old`, `pinned`, `initial`, Writer и Owner освобождены
  до reopen; tail CustodyWriterCommit не содержит Owner refs. Cold проверяет
  current generation/length и каждый full/short block, без total-sized vector.
  Это direct Tree proof, не самостоятельная новая IStream/consumer приёмка.
- Assert-owned return baseline и Release assertions сохранены. Никакого
  sleep/real-time pacing/producer/dispatcher/encoder/deadline simulation здесь
  нет; paced=0 и storage-only tail labels не принимают эти будущие gates.

## SHA-256 при независимом чтении

| Артефакт | SHA-256 |
| --- | --- |
| OwnerTests.cpp | `896e7523b777ac65bca2f0c21e47de73299def11685ef48f3b435f79574c474a` |
| Writer.cpp | `dc1e9cc31ae90186f73d989602895026cff58c2bdb34414b25ffa3f91ad6a4fd` |
| Writer.h | `649e5ca3f3fb2e3d45b151a1df26c9b7533f22de98a7aa071aab2c7c184f71f9` |
| Tree.h | `9c28432d20e49726033a1f855bc458b93040c6681d9155a81504dfad4a7a9b87` |
| Tree.cpp | `97f101c34413ac57bbe48ab64b98a6e3ecfdc11ff61ec24681c9a7f9e99a56b3` |
| TreeTests.cpp | `c3f9e9a62818f05ca1cb904ed9c5d6d1183b55c70455dab771eb611d8e8a6eb3` |
| requirements gate | `5c75950f05aae4a5ac5b55ed71e26b0cff93191c2ae5bbe0816042bbfb8c8222` |

## Execution и конечный статус этого чтения

Main сообщил: первая CopyPS отказала из-за missing apps/windows prefix,
код не исполнился; затем root исправлен, build+short запущен. Это не native
test failure/PASS. Runtime текущего диагностического снимка пока pending.
Предыдущие41/39/VS0 относятся к accepted Writer stage, не этому source delta;
v1 baseline20704 также не его execution acceptance. Reviewer ничего не запускал.

Readback: **6 checked / 3 unchecked; C0/H2/M0; REQUEST CHANGES.** H1/H2 —
конкретные test-only observer/bounds defects, не gaps norms. После минимального
test delta и завершённых exact-SHA receipts PCD003/004/009 переоцениваются;
старые failures/source states сохраняются. Нет acceptance cadence/Stop/T116/
SC-003/consumer adoption/app/install/physical/release и нет изменения старых
requirements/source reports, норм, tasks, Git/VM/GitHub.

## Первый terminal short-run — старый observer snapshot896e752…

По сообщению main: Release build и --packed-writer-cadence-short завершены
EXIT0, guest hash896e752… совпал с лично проверенным canonical snapshot.
Actual2,098,560B/1093 whole frames; milestone generations5/9 при1/2MiB;
lastIO10/24/2, DATA1/NODE4. Owned_new_sample_max1,077,574,
sampledPrivate11,866,112; storage tail71.824ms, release0.479ms,
cold326.288ms; exact_bytes_verified1, owned_after0. Исполнитель — main,
reviewer native команды не запускал. 64MiB run1 live не принят как PASS.

Этот завершённый положительный byte/lifecycle результат **не устраняет H1/H2**.
NODE4 согласуется с лично прочитанным observer, считающим3NODE+1HEAD;
печать NODE4 не доказывает четвёртый actual NODE. Более широкий resize
assertion пропускает это значение и не проверяет sequential3NODE/290816B.
Timings и memory samples сохраняются с точными ограничениями из отчёта,
не выдаются за product Stop/SC-003/native allocation peak.

Текущий verdict неизменен: **REQUEST CHANGES,6/3,C0/H2/M0**.
PCD003/004 требуют минимального test-only исправления; PCD009 остаётся
открытым для финального исправленного snapshot и его execution/regression.
Новая норма/порог/production изменение не требуется, requirements12/0
не переотмечены. Один successful short-run не принимает полную cadence.

## Повторная source оценка H1/H2 delta — frozen454febc…

**STATIC DELTA COMPLETE / EXECUTION PENDING — текущие8/1,C0/H0/M0.**
Исторические6/3 и исходные checkbox markers выше сохранены; они не текущий
verdict. Новых критериев или требований не добавлено. Source acceptance
пока не выдана: PCD009 остаётся открытым.

code-reviewer перечитан полностью. Лично прочитан current codec observer
:225–230 и measurement/assertion/output block :399–425. SHA canonical
OwnerTests **454febc71de0c1d1ef787f699afe79a8b1d612543dda8be7594c0b6824e66c23**
совпал с объявленной main freeze; Writer.cpp dc1e9cc… и requirements gate
5c75950… неизменны. Заявленную mirror identity подтверждает main; guest
ещё не обновлён и не принимается за current execution identity.

- **H1 закрыт статически:** observer :228–229 считает только exact nodeL0/
  nodeL1/nodeL2; HEAD больше не входит в NODE. Print :420 явно называется
  last_data_nodes. Production seal остаётся настоящим; второго codec/счётчика
  authority не добавлено. Предыдущее NODE4 не переобъявляется новой метрикой.
- **H2 закрыт статически:** :404 проверяет DATA1/NODE≤3/flush2, :406 проверяет
  append≤290816B — собственные sequential bounds принятого §4:147–148.
  Общий resize7NODE/327680B и прочие product quotas не изменены.
- Границы IO block-interval, crossing-frame writeAt timing, sampled native
  memory, actual release/cold и отсутствие app Stop/SC-003 claim сохраняются
  как описано выше. Timing label не принимается за isolated Tree latency.

### Текущие состояния прежних source критериев

| Критерий | Статус после delta |
| --- | --- |
| PCD001 | Подтверждён: прежний test-only Fixture/backend/real codec. |
| PCD002 | Подтверждён: whole frames/actual total/generation/milestones. |
| PCD003 | Подтверждён статически: H1 исправлен, DATA/NODE не включают HEAD. |
| PCD004 | Подтверждён статически: H2 исправлен, sequential cap сохранён. |
| PCD005 | Подтверждён: прежние ограниченные memory observations/labels. |
| PCD006 | Подтверждён: pinned/release/cold/byte checks не изменены. |
| PCD007 | Подтверждён: storage-only tail не product Stop. |
| PCD008 | Подтверждён: прежний default short/explicit CLI/Release asserts. |
| PCD009 | **Открыт:** нет current454febc native/portable terminal receipts. |

Readback текущей таблицы: **8 checked /1 unchecked; C0/H0/M0**.
Для source acceptance нужны завершённые результаты исправленного source,
а не только устранённые строки кода или выполнение старого binary.

По сообщениям main: portable старого896e752 snapshot build0/39/39PASS12.09s
сохраняется только исторически и будет повторён на current. Старый64MiB
run85049 дошёл до milestone64MiB159979.792ms, но cold/exact terminal ещё
pending; это не PASS, не corrected benchmark, не SC-003. Guest sync/main
execution ожидаются после старого run. Reviewer не исполнял ни один handle,
не менял исходники/нормы/старые отчёты/Git/VM; дописан только этот report.

### Исторический64MiB run завершён, current execution остаётся pending

Main предоставил terminal85049 EXIT0 старого896e752: loop159979.792ms,
last DATA/NODE1/4 с неверным HEAD label; storage tail76.680ms,
release0.342ms, cold10329.475ms, max frame call823.356ms,
exact_bytes_verified1/owned_after0. Это завершённая история исходного observer,
**не H1/H2 acceptance** и не evidence current454febc. Новые corrected copy/
Release build/short/64run1 запущены последовательно после завершения старого
run, результатов ещё нет. Текущие8/1,C0/H0/M0/PCD009pending не изменяются.

### Corrected short и portable — current454febc

Main сообщил завершённый подэтап: guest SHA454febc verified, Release build0,
CORRECTED_SHORT_EXIT0. Milestones1/2MiB: DATA/NODE1/3, IO10/24/2,
owned_new_sample_max1,077,574, sampledPrivate11,870,208; tail55.993ms,
release0.474ms, cold339.731ms, exact1/owned0. Это первый положительный native
результат исправленного observer/bounds, не переименование старого1/4.
Portable75226 final current454febc build0/39/39PASS11.30s command0;
Win32 cadence fixture portable не исполняет. Исполнитель обоих — main.

Native counters interpreted как block interval, timing как crossing-frame
write call; memory samples не native peak. Production unchanged. Corrected
64MiB run1 ещё live, не принят как terminal PASS. Итог остаётся
**STATIC DELTA COMPLETE / EXECUTION PENDING,8/1,C0/H0/M0; PCD009 открыт**.
Final source acceptance, sustained cadence/product Stop/SC-003 не выданы.

## Corrected64MiB run1 — terminal47899, current454febc

Main предоставил завершённый47899: build0, short0, longrun1 terminal0 на
frozen454febc. Actual67,109,760B, tail896B, finalgeneration258. Milestone
crossing-frame call ms1/2/4/8/16/32/64MiB:
141.084/126.767/139.959/166.729/124.911/139.556/128.149.
Во всех rows DATA/NODE1/3, nativeIO10/24/2; requested write/read
292352/674006B, physical64MiB70,680,704B. Это block-interval IO и whole
crossing-frame writeAt timing, не isolated commit duration/throughput guarantee.

Loop wall131115.090ms; storage-tail53.095ms, actual release1.123ms,
cold full verify9598.998ms, max-frame call288.620ms.
Owned_new_sample_max1,077,574B, sampledPrivate12,959,744B;
exact_bytes_verified1 / owned_after0. Native PrivateUsage sample не peak
DPAPI/OS allocations; холодная стоимость отдельно, не 5s Stop promise.
Все выполнения принадлежат main, не reviewer rerun.

Это подтверждает исправленный observer и первый длинный generated byte/
lifecycle результат, не final source acceptance. Second64MiB run ещё live,
полные native/Debug regression main планирует serial; ни одна незавершённая
часть не засчитана. Round229 main пока сохраняет initial pending/history,
новые receipts будут append-only. Статус **8/1,C0/H0/M0; PCD009 pending**.
Нет sustained capture/product Stop/SC-003/T116/installed/release acceptance.

## Corrected64MiB run2 — terminal56532, current454febc

Main сообщил56532 terminal0 того же corrected454febc. All milestone rows
1/2/4/8/16/32/64MiB: DATA/NODE1/3, IO10/24/2, requested write/read
292352/674006B. Crossing-frame call ms:
134.783/124.816/126.649/149.210/141.087/127.295/134.971.
Loop121765.947ms, storage-tail48.408ms, release0.316ms,
cold9463.388ms, max-frame226.950ms. Physical70,680,704B,
owned_new_sample_max1,077,574B, sampledPrivate12,902,400B;
actualwhole67,109,760B/tail896B/generation258/exact1/owned_after0.

Run1 и run2 — завершённые отдельные generated опыты, не выбор лучшего
из них и не real-time/SC-003/product Stop acceptance. Корректные счётчики и
physical extent повторились; timing/native samples остаются наблюдениями
в установленных scope границах, не новой threshold нормой.

Debug current target build+short запущен serial, затем main выполнит полный
Release41 regression; завершённых результатов этих частей ещё нет.
Main88456 governance/bootstrap doctor frozen/YAML/diff PASS0 относится к
моменту до final docs и будет повторён; reviewer эти команды не запускал.
**PCD009 pending; текущие8/1,C0/H0/M0.** Source acceptance ещё не выдана.

## Corrected Debug short — terminal83905; full Release66321 pending

Main предоставил83905: current454febc Debug target build0/short0,
terminal command0. DATA/NODE1/3, IO10/24/2, requested write/read
292352/674006B; owned_new_sample_max1,077,814B,
sampledPrivate13,418,496B; storage-tail104.788ms, release2.071ms,
cold394.992ms, max-frame190.851ms, exact1/owned_after0.
Это Debug target/short, **не full Debug Owner suite**. Выполнял main;
reviewer лично повторно проверил canonical OwnerTests SHA:
454febc71de0c1d1ef787f699afe79a8b1d612543dda8be7594c0b6824e66c23.

Последующее сообщение main: full Release66321 build0, CTest Owner ещё
live; полный41/41 terminal отсутствует и не засчитан. Main сообщил
ограниченный code-reviewer/ponytail-review текущего diagnostic delta:
Lean already, без безопасного удаления/новой абстракции. Это оценка main,
не самостоятельный Ponytail запуск reviewer и не обзор всего baseline.

Отдельное read-only наблюдение main об отсутствии строгого custody-package
parser и непригодности substring helpers как authority относится к будущему
schema/adoption этапу. Текущий test-only CLI не принимает их как authority;
это сообщение не добавляет новый gate и не принимает будущий parser.
Нормы/продуктовый код не менялись. **8/1,C0/H0/M0; PCD009 открыт до
завершённой текущей полной Release-регрессии.** Остальные границы source
acceptance, storage-only timing, SC-003/full T116/installed/release неизменны.

## Итоговая независимая приёмка — current454febc, terminal66321

**ACCEPTED — bounded test-only diagnostic source; 9 checked / 0 unchecked;
C0/H0/M0.** Этот раздел заменяет прежний pending verdict, но не изменяет
исторические записи/markers и не переобъявляет старые896e receipts новыми.

Main предоставил конечный receipt66321: command0,
CADENCE_FULL_BUILD_EXIT0; полный native Release CTest41/41 PASS215.52s,
CADENCE_FULL_CTEST_EXIT0. Owner165.95s включает default current2MiB test;
Tree18.38s, Files5.27s. Это завершённая текущая полная Release-регрессия,
не ранее запущенный handle и не прежний Writer stage. Исполнитель — main,
reviewer не исполнял сборки/тесты/VM команды. Завершённые corrected short,
два64MiB run, Debug short83905 и portable75226 относятся к той же freeze.
Полного Debug Owner не было, и он здесь не заявляется.

Reviewer лично прочитал весь текущий source report1–298 и хвост Round229
основного validation. На момент чтения его последний раздел ещё содержит
historical Debug/full-native pending: финальный66321 receipt принят из
последующего прямого сообщения main, не приписан этой старой записи.
Лично повторно проверены все шесть canonical source SHA ниже, requirements
gate и packed contract; они совпадают с принятой freeze. Исправленные
observer228–229 и sequential assertions404/406 дополнительно перечитаны.
Mirror/guest identity исполнения подтверждена main в ранее записанных
corrected receipts; последующее чтение guest6/test-binary hashes main ещё
планирует и здесь не выдано за уже выполненную проверку reviewer.

### Итоговые критерии текущего снимка

- [x] PCD001 Existing Fixture/real Files/CNG/DPAPI; test-only без нового backend/API/adoption.
- [x] PCD002 Whole480-float frames/actual bytes/generation; все1/2/4/8/16/32/64MiB milestones в двух завершённых опытах.
- [x] PCD003 Exact DATA/NODE kinds исключают HEAD; IO/requested-byte и timing boundaries явно ограничены.
- [x] PCD004 Sequential1DATA+3NODE/290816B assertions восстановлены и исполнены, resize cap не подменяет их.
- [x] PCD005 Bounded generated input/owned observations/sampled PrivateUsage без fake peak/new quota/environment threshold.
- [x] PCD006 Old pinned root, actual allrefs release, bounded cold exact-byte verification и owned baseline подтверждены.
- [x] PCD007 Storage-only tail/release/cold отдельно от dispatcher/encoder Stop/5s/SC-003; нет sustained real-time claim.
- [x] PCD008 Default short и explicit long в существующем executable; полный current Owner Release и прежние regressions исполнены.
- [x] PCD009 Exact frozen corrected source: native Release build/full41, Debug target/short, два corrected64MiB и portable39 завершены; прежние/запущенные результаты не подменяют их.

### SHA-256 итоговой freeze, проверенные reviewer

| Артефакт | SHA-256 |
| --- | --- |
| OwnerTests.cpp | `454febc71de0c1d1ef787f699afe79a8b1d612543dda8be7594c0b6824e66c23` |
| Writer.h | `649e5ca3f3fb2e3d45b151a1df26c9b7533f22de98a7aa071aab2c7c184f71f9` |
| Writer.cpp | `dc1e9cc31ae90186f73d989602895026cff58c2bdb34414b25ffa3f91ad6a4fd` |
| Tree.h | `9c28432d20e49726033a1f855bc458b93040c6681d9155a81504dfad4a7a9b87` |
| Tree.cpp | `97f101c34413ac57bbe48ab64b98a6e3ecfdc11ff61ec24681c9a7f9e99a56b3` |
| TreeTests.cpp | `c3f9e9a62818f05ca1cb904ed9c5d6d1183b55c70455dab771eb611d8e8a6eb3` |
| requirements gate | `5c75950f05aae4a5ac5b55ed71e26b0cff93191c2ae5bbe0816042bbfb8c8222` |
| packed contract | `6cb9bc197f44e689c83ddff4dc216ee818867abe06cca99fdd6c2fd8ba992644` |

H1/H2 test defects устранены; новых C/H/M findings нет. Governance88456
был PASS до финальных docs; его повтор после docs остаётся работой main,
не выполненным reviewer действием и не частью ложного release claim.
Принято только корректное устройство теста, его ограниченные measurements
и proportional regressions. Не приняты schema/package parser, consumer
adoption, cadence/deadline integration, app Stop, SC-003, полнаяT116,
установленное приложение, физическийWindows/hardware или release.
Никакие нормы/tasks/product/старые отчёты/Git/VM не изменены.

Итоговый readback/count относится **только к девяти markers данного блока**:
**9 checked / 0 unchecked; C0/H0/M0; PCD009 closed, scoped source ACCEPTED.**

### Завершающее чтение Round229 и guest identity98391

Reviewer лично перечитал новый final-native раздел Round229 основного
validation: теперь он содержит завершённые83905/66321 и guest98391,
не только прежние historical pending. Main98391 command0 подтверждает
совпадение всех шести guest source SHA с текущими canonical hashes таблицы.
Тестовые binaries: Release
`409d099b813cfafdd3724245015fc5abfaeee1fa1981c014952fa9c02e04d70b`,
Debug `f06bf12245169992d50e2ffa453fd65961aa8d61ee63921ab1a3de2a9ed655a5`.
Это hashes test executable, **не app/MSIX/installed package**. Выполнение
и guest hashing принадлежат main, reviewer лично проверил документальную
запись и canonical hashes, но не исполнял VM. Windows binary diff указан main:
`c3329c410028737c6beb2bd77ab897be428c559c5820306bf02aca7a1f791419`.

Новых source изменений или findings нет. Итоговые девять markers выше
перечитаны и пересчитаны: **9/0,C0/H0/M0; PCD009 закрыт; ACCEPTED только
bounded cadence diagnostic source**. Initial H1/H2 и прежние состояния
сохранены; другие reports не менялись. Next schema, consumer/app/device/
release и полнаяT116 в эту приёмку не входят.

## Согласование исторических маркеров — 2026-10-10

В рамках обязательного независимого ревью Spec Kit, по поручению основного агента,
reviewer закрыл только старые
PCD003/004/009 на основании уже записанного последующего terminal evidence.
Исходные failure/pending формулировки и counts сохранены как история cut896e,
а отметки отражают последующее закрытие на corrected454febc, не ретроактивный
PASS896e. SHA отчёта до согласования:
`e9375a354662ba69dc24571d5865312e8ce52237114f060d1da1db476e51b92e`.
Canonical HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

| Пункт | Независимо перечитанное основание |
| --- | --- |
| PCD003 | Раздел static delta: exact nodeL0/L1/L2 исключают HEAD; текущий OwnerTests:225–230 сохраняет это различение. |
| PCD004 | Static delta и current OwnerTests:404/406: DATA1/NODE≤3/flush2, append≤290816B, без подмены общим resize cap. |
| PCD009 | Финальный раздел этого отчёта и validation Round229: corrected OwnerTests454febc71de0c1d1ef787f699afe79a8b1d612543dda8be7594c0b6824e66c23;66321 build0/Release41/41 PASS215.52s;83905 Debug short EXIT0; portable75226 39/39 PASS11.30s; два corrected64MiB terminal0;98391 guest six-source match и полные test-binary SHA записаны отдельно. |

Это документальные terminal receipts main с их собственной freeze; reviewer
перечитал отчёт и основной validation, не исполнял VM/тесты и не пересчитывал
guest binaries. Текущий OwnerTests SHA
`ca4e041ca15b978e6573e3473fe8ac003b166ac313bbc46c54a643bfbcef3205`
не получает старый runtime PASS автоматически.
Raw counts всего этого Markdown теперь **18 checked / 0 unchecked**.
Нет полного T116/SC-003/installed/runtime320 GO. Нормы/код/tasks не изменены.
