# Независимая source review: packed Writer reuse / F200 T116

Дата: 2026-10-04. **REQUEST CHANGES — 5 checked / 4 unchecked; C0/H2/M1.**
Исполнение новой реализации pending. Это не приёмка T116 или Windows-приложения.

## Область и лично прочитанные материалы

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Anchor `.specify/feature.json`: `codex/200-windows-followup`, source_sha
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; Git повторно не проверялся.
Lane: high-risk-product storage. Разрешён только этот новый report.
Requirements gate `c5f271c5c70a3c617494601aca8b24642279abedc9500000c0984dbfe8c7302d`
и checklist `a1f18f2cdfe6ebcdb369ad0ed6a877f77af4658bc388a4cab1475c50b45b62a0`
остаются immutable 12/0; обнаруженные ниже дефекты — source, не новые нормы.

Лично прочитаны Writer.h и вся Writer.cpp (State, обе open overloads, все API,
checkpoint/destruction), текущая Tree.h и изменённые role/friend/makeProof
участки Tree.cpp, packedWriter:265–325 и main:1477–1552 в TreeTests, lifecycle
Fixture и existing Guard/job/pin/dirty/owned admission. Reader и неизменённые
нормы/guidance переиспользованы после свежего SHA/readback предыдущего gate;
current packed §6.0 перечитан. `code-reviewer` прочитан полностью. Git diff
заменён прямым чтением файлов по прямому запрету Git; тесты/VM/сборки не запускались.

Во время чтения Writer.cpp сменился с `41fbb461c6751d843a5a3674ae374929640cdcd8f90c4b6194b6ff98a8873e3c`
на текущий `dcad323e15039b7944bfd57a318f8b5aabc2e40b9cfac244bc4cca7e14a28bc6`
(локальная переменная flushPacked теперь `published`). Актуальные участки
повторно прочитаны; H1/H2/M1 остаются в текущем снимке. Это изменение main,
не reviewer. Старые Writer/Tree/Reader PASS не принимают этот новый код.

## Source критерии

- [x] PWW001 Один Writer/State/API, проверенный Tree-derived role, private friend без нового Tree Write API/второго backend/dispatcher. Изменение role сохраняет verified context из Guard и переносит его в successor proof.
- [x] PWW002 Обычные partial/header/cross-block/sparse пути различают pending length и committed Tree; gap publish ограничен start целевого блока, не всей ещё не записанной DATA длиной; merge читает точный старый DATA, packed не заполняет flat entries.
- [x] PWW003 Отмена между несколькими actual Tree transitions прекращает следующие публикации, сохраняя прежний ACK/root/base/target/lease. **H1**.
- [x] PWW004 Shrink flush→Tree trim и grow dirty merge стирают отрезанный suffix; pending Read имеет короткий EOF, guarded read/final check и wipe скопированного prefix на ошибке. Старые Reader/Clone остаются immutable.
- [x] PWW005 Наблюдаемый same-Owner fault/revocation не скрывается RAM-only write/no-op/input error; первая native причина передаётся в sticky Writer. **H2**.
- [x] PWW006 Все owned allocations, включая State и оболочку Writer, учтены до allocation; общие dirty/pin/job/physical caps не расширяются. State charge/sizeof≤4096 есть, но **M1**.
- [x] PWW007 Healthy destruction очищает dirty RAM, revokeWrites не blockWrites; actual Owner/pins удерживаются proof/result/Reader до release; failed open не устанавливает capability и не отзывает исправный Owner. Нет destructor flush/checkpoint/disk I/O. Статическое наличие wipe не заменяет его runtime доказательство.
- [x] PWW008 Первоначальный generated positive fixture проверяет три role, DATA prefix вместо premature ZERO, header/cross/sparse pending bytes, dirty shrink/regrow, EOF, pinned Clone после release и exact cold bytes/generation. Native asserts включены даже Release. Это оценка только этого fixture, не полного failure coverage.
- [x] PWW009 Exact-current-SHA native execution/failure cuts/cancellation/pressure/actual wipe и v1 regression подтверждены terminal receipts. Пока отсутствуют; ещё нужны H1/H2/M1 counterexamples. Нет native PASS по факту запуска handle.

## H1 — отмена после ACK не проверяется перед следующей публикацией (HIGH)

Места: `ProtectedCustodyWriter.cpp:95–105`, `159–162`, `329–335`.
`flushDirty()` проверяет cancellation лишь до `flushPacked()`. Sparse flush
выполняет `setSize(start)` и принимает его committed ACK на:99–100, затем
сразу `appendBlock/replaceBlock` на:103–104 без нового ready/cancellation check.
Tree не получает cancellation token. Аналогично после flush ACK checkpoint
сразу начинает отдельный setSize, а shrink — отдельный trim.

Контрпример: empty Tree; pending sparse Write в block2; checkpoint начал
explicit gap transition; cancellation становится true после его независимого
ACK, но до возвращения в flushPacked. Вместо остановки на подтверждённом gap
код выполняет ещё одну DATA/HEAD публикацию. При pending SetSize suffix возможна
та же лишняя resize-публикация после DATA ACK. Это не отмена уже выполняющегося
native commit: **следующий** transition ещё не начинался.

Packed §6.0:266–267,283–287 и base §7:295–305 требуют отмены без false rollback,
сохранения actual публикации/owner и запрета новых effects. Минимальное
исправление: повторно проверять cancellation/готовность между actual transitions
и после native работы до нового byte ACK. Уже принятый snapshot/gen не откатывать;
результат последующего отказа должен иметь фактический latest ACK base/lease,
а не объявлять весь большой вызов отсутствующим. Новый backend не нужен.

Нужен real-worker counterexample: cancel точно после первого committed gap ACK,
до второго append; наблюдать отсутствие второго DATA/HEAD write, сохранённые
gap generation/length, sticky native cancellation и retained Owner. Отдельно
проверить cancellation после DATA ACK перед pending resize и mid-large Write.

## H2 — ready не проверяет same-Owner fault или write capability (HIGH)

Места: `ProtectedCustodyWriter.cpp:70–80`, `126–127`, `154–158`, `245–264`.
`ready()` смотрит только локальный failed и cancellation. При попадании в
dirtyPosition `loadDirty()` сразу возвращает RAM buffer; same-size resize
возвращает успех без Guard. Таким образом наблюдаемый fault общего Owner ещё
не попавший в локальный State не препятствует новому accepted Write.

Конкретный последовательный сценарий, без гонки/второго writer: открыть packed
media Writer, принять один short dirty byte; на том же Owner выполнить
`owner->blockWrites()` (либо получить sticky physical read fault в shared Reader);
после этого `writer.writeAt(0,&byte,1)` возвращает bytes success через dirty hit.
`setSize(writer.size())` и valid empty Write тоже успешны. При invalid Write
раньше Guard возвращается invalidInput/native0, скрывая ранее наблюдённую
physical причину. `owner->revokeWrites()` отдельно также не проверяется этими
write-admission путями. Только позже Tree commit обнаружит проблему.

Это нарушает FR-012:480, packed §2/§6.0:281–287 и принятую семантику "observed
fault не скрывается cached/control success". `readAt` уже делает checkRead
до/после выдачи, но write/no-op его не вызывают; read check не проверяет writable.
Минимальное исправление: переиспользовать существующую private Guard authority
при готовности packed write/SetSize, с first native error precedence до input/
dirty/no-op success. Не использовать полный cold verify/второй owner и не
расширять jobs4. Если guard admission отказал, не принимать новые bytes.

Counterexamples должны включать populated dirty→Owner fault→write/same-size/
empty/invalid-input, отдельно revokeWrites без physical fault, и реальный
native first error через тот же Owner. После отказа повторные вызовы не пишут;
healthy Reader после одного лишь revoke сохраняет возможность чтения.

## M1 — оболочка Writer остаётся неучтённой owned allocation (MEDIUM)

Места: `ProtectedCustodyWriter.h:23–43`, `.cpp:193–196,221–235`.
State теперь выделяется через CustodyAllocator, но `new ProtectedCustodyWriter`
в обеих open overloads остаётся обычным new: в классе нет charged new/delete.
Небольшой fixed pointer-holder ограничен pins32, но его app-owned allocation
не входит в owned64MiB. Учитываемый State не включает отдельную оболочку.
Packed §6 и requirement gate CHK009 требуют owned admission, не дополнительного
неучтённого fixed бюджета. Минимально переиспользовать тот же class-specific
CustodyAllocator new/delete, без allocator framework. Сохранить v1 regressions
и проверить отказ/actual release accounting оболочки при memory pressure.

## Execution evidence на момент отчёта

По сообщению main: RED47999 native Release build0, missing packed open stub
дал assertion `opened.ok` line275/EXIT3. Ранее test-only compile98537 имел
macro/enum исправления; это не implementation PASS. GREEN native Tree/Files
ещё выполнялся последовательно; terminal receipt текущего снимка не получен.
Все эти execution факты принадлежат main, не reviewer. Новых VM действий нет.

Не подтверждены новые actual native Writer fault cuts, cancellation после ACK,
pressure/pin/job refusals и освобождение/wipe real dirty allocation. Existing
Tree fault matrix/старый resize wipe не покрывают автоматически Writer State.
PWW009 оставлен открытым по отсутствию evidence, не по дополнительному новому gate.

## SHA-256 текущего снимка

| Файл | SHA-256 |
| --- | --- |
| ProtectedCustodyWriter.h | `803c73259d66437cd04862edacfd796e386c81450e0e7d6b655e479b9e156cde` |
| ProtectedCustodyWriter.cpp | `dcad323e15039b7944bfd57a318f8b5aabc2e40b9cfac244bc4cca7e14a28bc6` |
| ProtectedPackedCustodyTree.h | `d4af3ceb8e5735b9ceb7a72fe250f0c5dfffa677879ea829d68166589d70565e` |
| ProtectedPackedCustodyTree.cpp | `1d5da2a3923880155720b18cb7f1c841f1b33ef8eee6d121538acec69cfca59a` |
| ProtectedPackedCustodyTreeTests.cpp | `c3f9e9a62818f05ca1cb904ed9c5d6d1183b55c70455dab771eb611d8e8a6eb3` |
| Guard implementation ProtectedCustodyFiles.cpp | `c7ddc8367c205a9f6e2177ff54b9a46ccc7e8b7a039079dba863378e67b11882` |
| ProtectedCustodyMemory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |
| packed contract | `6cb9bc197f44e689c83ddff4dc216ee818867abe06cca99fdd6c2fd8ba992644` |
| plan | `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8` |

## Конечный статус этого первого чтения

**5/4; C0/H2/M1; REQUEST CHANGES. PWW009 pending.**
Исправления H1/H2 необходимы до source acceptance, M1 — небольшой конкретный
дефект учёта. Нормы/старые marks менять не требуется. После source delta и
точных terminal receipts повторно оцениваются только изменённые критерии.
Нет принятия полного T116/consumers/schema/migration/T120/cadence/Stop/app/
installed/private inventory/audio/hardware/release.

## Повторное чтение source delta H1/H2/M1 — 2026-10-04

**Текущая статическая оценка: 8 подтверждены / 1 открыт; C0/H0/M0.
PWW009 pending; source acceptance НЕ выдана.** Начальные 5/4 и H1/H2/M1
выше сохранены как история первого снимка, включая его исходные checkboxes.
Таблица ниже — текущая оценка тех же девяти критериев, не новый gate и не
повторное принятие норм. До terminal execution она не заменяется PASS.

Лично перечитаны полностью текущие Writer.h/Writer.cpp, Tree.h и private
checkWrite, существующие Guard constructor/check/writeReady/reject и общий
allocator. Прочитаны OwnerTests:1–497 (реальная interposition, allocation
observer, Fixture, четыре новых Writer проверки), их CLI/main dispatch,
неизменённый packedWriter:265–325, §6.0 и связанные пояснения requirements
gate. Не заявляю повторное полное чтение остальных старых Owner тестов.
code-reviewer прочитан полностью; неизменённый контекст переиспользован после
проверки SHA. Никаких тестов, VM, Git или изменений implementation reviewer
не выполнял.

### Доказательства исправлений в текущем коде

- **H1 закрыт статически.** Writer.cpp:114 проверяет ready между ACK explicit
  gap и DATA append/replace; :175 — между dirty flush ACK и shrink; :360–365 —
  между flush и отдельным resize. Write :279 проверяет готовность до byte ACK.
  Checkpoint :351–357 при уже подтверждённом exact dirty DATA и совпавшем EOF
  возвращает этот actual ACK, не начинает лишний no-op после поздней отмены.
  adopt :99–106 сохраняет actual result/lease и новый proof; отказ между
  переходами удерживает уже подтверждённый Tree, не откатывает gap/DATA.
  Cancellation fixture :340–361 ставит token при втором actual HEAD readback
  в real Files wrapper :116–122: sparse checkpoint прекращается на generation2,
  несparse возвращает уже полученный committed ACK; следующая запись отказана.
  Это два конкретных сценария, не заявление об исчерпывающем тестировании
  всех мест отмены, например отдельного shrink после ACK или большого Write.
- **H2 закрыт статически.** Private Tree.cpp:374–378 использует ровно один
  прежний Guard/writeReady; новых owner, файлов, full closure или лимитов нет.
  Writer.ready :73–89 проверяет shared fault/write capability до input, dirty
  hit, same-size/empty успеха и cancellation. stopped :92–95 отдаёт первый
  guard error однократно и удерживает native; повтор возвращает writerFailed
  с той же native причиной. fail :61–71 не превращает writerFailed/native0
  revocation в physical blockWrites; здоровый Reader остаётся допустим.
  Admission fixture :362–395 содержит 3 causes × 4 actions: blockWrites,
  revokeWrites и actual ERROR_READ_FAULT; dirty write, empty write, same-size
  SetSize, invalid-input. Проверяет error/native, отсутствие новых writes,
  sticky checkpoint и здоровое чтение после одного лишь revoke.
- **M1 закрыт статически.** Writer.h:25–28 включает оболочку в прежний
  CustodyAllocator; обе open используют тот же new/delete. State остаётся
  charged и sizeof≤4096. Resources :396–454 проверяет owned pressure,
  точный sizeof(Writer) allocation refusal, pins32/jobs4 и dirty4 без новых
  cipher reads/writes/flushes при отказе open и с возвратом owned baseline.
  Последний участок связывает raw allocation с actual DATA body через codec
  spy; inspectPlainFree :45–50 проверяет все байты до реального free для
  healthy flush и failed flush→Writer release. Наличие observer/assertions
  не означает, что текущий снимок уже исполнил их успешно.
- **Failure matrix прочитана, не исполнена reviewer.** OwnerTests:455–497
  измеряет реальные write/read/flush counts успешного partial dirty rewrite
  nonempty generation2. Для семи faults перебирает каждый измеренный ordinal,
  проверяет HEAD-attempt ambiguity, base2/target≤3, native read/write error,
  неизменные counters на повторе и retained native lease после owner.reset.
  Counts захвачены до дополнительных проверок. Это fixture partial rewrite,
  не автоматическая приёмка каждого mode/consumer/T116.

### Текущая оценка прежних критериев

| Критерий | Текущий статус | Основание |
| --- | --- | --- |
| PWW001 | Подтверждён | Один State/API/Owner; новый checkWrite private, reuse Guard. |
| PWW002 | Подтверждён | Pending bytes и committed EOF по-прежнему разделены; sparse gap не включает несохранённую DATA. |
| PWW003 | Подтверждён статически | H1 delta и два actual-boundary cancellation counterexamples прочитаны; runtime относится к PWW009. |
| PWW004 | Подтверждён | Dirty shrink/regrow, pending Read/wipe, неизменённый pinned fixture; новый ready не убирает эти пути. |
| PWW005 | Подтверждён статически | H2 delta, first shared native fault и revoke без physical poisoning; 12 admission cases. |
| PWW006 | Подтверждён статически | M1 allocator delta и unchanged quotas; accounting/refusals проверяются в новом fixture. |
| PWW007 | Подтверждён | Destructor RAM wipe/revoke/refs; failed open не устанавливает packed capability, retained failed base остаётся owned. |
| PWW008 | Подтверждён | Трёх-role positive fixture неизменён; новые real failure/resource fixtures прочитаны, но не приняты как PASS. |
| PWW009 | **Открыт** | Нет terminal receipts exact-current snapshot native/portable execution и v1 regression. |

Итого текущей таблицы: **8/1, C0/H0/M0**. Исторические task markers первого
чтения намеренно не переписаны. Новых подтверждённых статических blocker нет;
результат — **STATIC DELTA REVIEW COMPLETE / EXECUTION PENDING**, не acceptance.

### Новые RED и ограничение evidence

По сообщениям main (не собственное исполнение reviewer): H1 native86409
Release build0, cancellation/head3 assertion EXIT3; H2 native73138 Release
build0, dirty-hit admission assertion EXIT3. Они подтверждают исходные
контрпримеры. Старый96700 Tree19.24/Files5.68, 2/2 PASS25.02 на dcad/c3f9 —
исторический положительный результат, НЕ доказательство новых исправлений.
Текущие native Release/CLI/Tree/Files и portable39 находятся в исполнении;
запущенный handle не принят. Для PWW009 требуются завершённые результаты с
тождеством актуального source, фактическими cancellation/admission/resources/
cuts и пропорциональной v1 regression. Reviewer не назначает новый gate,
не запускает проверки и не приписывает себе main execution.

### Лично проверенный SHA-256 delta snapshot

| Файл | SHA-256 |
| --- | --- |
| ProtectedCustodyWriter.h | `649e5ca3f3fb2e3d45b151a1df26c9b7533f22de98a7aa071aab2c7c184f71f9` |
| ProtectedCustodyWriter.cpp | `dc1e9cc31ae90186f73d989602895026cff58c2bdb34414b25ffa3f91ad6a4fd` |
| ProtectedPackedCustodyTree.h | `9c28432d20e49726033a1f855bc458b93040c6681d9155a81504dfad4a7a9b87` |
| ProtectedPackedCustodyTree.cpp | `97f101c34413ac57bbe48ab64b98a6e3ecfdc11ff61ec24681c9a7f9e99a56b3` |
| ProtectedPackedCustodyTreeTests.cpp | `c3f9e9a62818f05ca1cb904ed9c5d6d1183b55c70455dab771eb611d8e8a6eb3` |
| ProtectedPackedCustodyOwnerTests.cpp | `060ec8fa18b042bbab96ae19f69e3ab3a1344b4eee772913c11128b46c6157dd` |

Current packed contract `6cb9bc197f44e689c83ddff4dc216ee818867abe06cca99fdd6c2fd8ba992644`,
plan `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8`
и requirements report `c5f271c5c70a3c617494601aca8b24642279abedc9500000c0984dbfe8c7302d`
не изменились. Source/table readback не даёт принятия всей T116, schema,
consumer adoption, migration, T120, app/package/audio/hardware/release.

## Исправление attribution H1 RED / observer — 2026-10-04

**86409 и 18481 НЕ принимаются как H1 RED.** Main отозвал прежнее сообщение:
ASSERT `cancellationHeadReads<=2` был ошибкой тестового observer, а не
доказательством дополнительного перехода implementation. Предыдущее
утверждение в разделе «Новые RED» о подтверждении обоих контрпримеров
отозвано в части H1; история сохранена, но не используется для acceptance.

Reviewer лично проверил узкий реальный путь: Files.cpp:1077–1089 делает
собственный readback опубликованной HEAD cell; затем Tree.cpp:354 вызывает
readHeads, чей цикл :35–37 читает обе HEAD cells. Таким образом один
нормальный actual commit уже содержит **три** наблюдаемых HEAD чтения после
попытки публикации. Третье чтение само по себе не доказывает вторую публикацию.
Ранее описанные observer «cancel при втором» и runtime граница в разделе H1
delta также больше не принимаются как доказательство правильной тестовой
границы; статическое чтение проверок между переходами от этого не меняется.

Текущий OwnerTests.cpp:119–123 исправлен main: cancel при третьем чтении,
assert допускает ровно до3 и отвергает четвёртое; fixture :354 требует3.
Это лично прочитанный source delta, **не успешное исполнение** исправленного
observer. Новых terminal receipts пока нет. H2 RED73138 остаётся действительным
по сообщению main и не отзывается этим уточнением.

Лично проверенные текущие SHA:
- Writer.cpp `dc1e9cc31ae90186f73d989602895026cff58c2bdb34414b25ffa3f91ad6a4fd`
  не изменился относительно предыдущего статического чтения.
- OwnerTests.cpp `2a30db694c70c0858fb39057c4a33ab443c6ab4723478398aa9988abd2939923`
  — новый observer snapshot; прежний `060ec8…` не его execution identity.

**Статическая оценка сохраняется 8/1, C0/H0/M0; PWW009 открыт.** H1 не имеет
принятого runtime RED в текущем evidence. Source acceptance не выдана; её
нельзя вывести из ошибочного observer или запущенного handle. Reviewer
изменил только это append-only уточнение; product/norm/tests/VM/Git не менял
и ничего не исполнял. Дальнейшие terminal receipts должны быть привязаны к
актуальным hashes и корректному observer.

## Частичный terminal packet — Release91577

По terminal сообщению main: session91577 завершена command EXIT0; build трёх
targets EXIT0. Canonical/mirror/guest identity совпадает для текущих шести
source hashes; reviewer лично повторно проверил canonical SHA всех шести:
649e5ca… / dc1e9cc… / 9c28432… / 97f101c… / c3f9e9a… / 2a30db6…
соответственно Writer.h/cpp, Tree.h/cpp, TreeTests, OwnerTests. VM/guest
identity и execution принадлежат main, не собственным действиям reviewer.

Release результаты исправленного observer и новых проверок:
- cancellation CLI EXIT0: sparse0 committed generation2/headReads3;
  sparse1 notCommitted generation2/headReads3;
- admission12 EXIT0; resources EXIT0;
- cuts EXIT0, измерены writes9/reads22/flushes2;
- Tree22.26s / Files6.40s, CTest2/2 PASS28.75s, command EXIT0.

Это завершённый положительный Release результат текущего observer, а не
восстановление отозванного H1 RED86409/18481. Targeted Owner CLI не выдаётся
за полную Owner suite. Длительности не доказывают capture cadence/Stop.

**PWW009 остаётся открытым; текущая оценка 8/1, C0/H0/M0, source acceptance
не выдана.** Debug тех же четырёх CLI и Tree/Files запущен, portable44507 ещё
выполняется; полного текущего Owner Release результата пока нет. Все три
незавершённые части не засчитаны. История прежних failures/pending сохранена.
Новых требований, source edits, VM запусков или принятия T116/app/release нет.

## Частичный terminal packet — Debug20733 / portable44507

По завершённому сообщению main: Debug20733 command EXIT0, build трёх targets
EXIT0; четыре CLI cancel/admission/resources/cuts EXIT0, cuts9/22/2.
Debug Tree29.77s / Files9.51s, CTest2/2 PASS39.45s, command EXIT0.
Portable44507 full build EXIT0, 39 tests PASS11.33s, command EXIT0.
Portable не исполняет Windows-native fault fixtures; Debug четырёх Owner CLI
не означает full Debug Owner suite. Это main execution, не reviewer rerun.

Canonical SHA шести файлов лично перепроверены: текущий OwnerTests2a30db6…,
Writer.cpp dc1e9cc… и остальные четыре совпадают с сохранённым delta snapshot.
Новых source изменений при этом чтении не обнаружено. Round228 и correction
H1 RED документируются main; отозванные86409/18481 не возвращены в evidence.

**PWW009 pending, текущая оценка8/1, C0/H0/M0.** Полный native Release build
и все41 CTest запущены отдельно, terminal пока не предоставлен; полная
текущая Owner Release suite не засчитана до этого результата. Final source
acceptance ещё не выдана. Остальные scope ограничения остаются неизменными.

## Окончательная независимая оценка PWW009 — 2026-10-04

**ACCEPTED — bounded packed Writer reuse; 9 checked / 0 unchecked,
C0/H0/M0. PWW009 подтверждён.** Это конечный статус текущего source снимка;
начальные и промежуточные markers/pending выше остаются историей и не
суммируются с девятью итоговыми критериями ниже. Новых gates не добавлено.

### Финальный terminal packet и личная сверка

Main предоставил завершённый native38336: command EXIT0, полный Release
cmake build EXIT0, CTest **41/41 PASS250.90s**, FULL_RELEASE_EXIT0.
Owner188.38s / Tree23.93s / Files6.93s. Это полный текущий Owner Release,
а не только targeted CLI или промежуточная строка Owner PASS. Длительности
не используются как доказательство real-time capture/cadence/Stop.

Лично перечитаны текущие delta/correction/execution разделы этого отчёта и
Round228 в validation-2026-10-02.md. Последняя прочитанная строка main
validation пока хранит исторический «Full Release38336 ещё выполняется»;
текущий terminal статус взят из нового явного финального сообщения main,
а не приписан незавершённой строке/старому handle. Его исполнитель — main.
Reviewer не запускал VM, сборку, тесты или дополнительные проверки.

Повторно лично вычислены все шесть canonical SHA — точное совпадение с
Release91577 / Debug20733 / portable44507 / final38336 freeze:

| Файл | Финальный SHA-256 |
| --- | --- |
| ProtectedCustodyWriter.h | `649e5ca3f3fb2e3d45b151a1df26c9b7533f22de98a7aa071aab2c7c184f71f9` |
| ProtectedCustodyWriter.cpp | `dc1e9cc31ae90186f73d989602895026cff58c2bdb34414b25ffa3f91ad6a4fd` |
| ProtectedPackedCustodyTree.h | `9c28432d20e49726033a1f855bc458b93040c6681d9155a81504dfad4a7a9b87` |
| ProtectedPackedCustodyTree.cpp | `97f101c34413ac57bbe48ab64b98a6e3ecfdc11ff61ec24681c9a7f9e99a56b3` |
| ProtectedPackedCustodyTreeTests.cpp | `c3f9e9a62818f05ca1cb904ed9c5d6d1183b55c70455dab771eb611d8e8a6eb3` |
| ProtectedPackedCustodyOwnerTests.cpp | `2a30db694c70c0858fb39057c4a33ab443c6ab4723478398aa9988abd2939923` |

Mirror/guest identity сообщена main и записана в Round228; собственная
проверка reviewer относится к canonical. Packed contract6cb9bc…,
plan5b5996… и requirements reportc5f271… лично сверены: неизменны.

### Почему PWW009 теперь подтверждён

- Release91577 и Debug20733 успешно исполнили четыре реальные native CLI:
  cancellation с корректными тремя HEAD чтениями, admission12, resources
  (owned/wrapper/pin/job/dirty refusal и actual before-free plaintext wipe),
  measured seven-fault cuts9/22/2. Эти assertions и interposition ранее лично
  прочитаны; закрытие H1/H2/M1 не опирается только на положительный byte test.
- Final38336 исполнил всю текущую Release suite41, включая полный Owner
  со встроенными новыми проверками, Tree и proportional прежние v1 Files
  regressions того же изменённого Writer. Набор не выдан за full Debug41:
  Debug20733 — четыре targeted CLI и Tree/Files2/2.
- Portable44507 full build0/39 PASS11.33s дополняет regression evidence;
  не заменяет Win32/DPAPI/native fixtures. Canonical snapshot не сменился.
- **86409/18481 остаются отозванными test-observer failures, не H1 RED.**
  Раннее утверждение о валидном H1 RED не восстановлено. Исправленный observer
  и static guards плюс новые положительные native результаты достаточны для
  bounded acceptance; не заявляется повторное RED против прежнего product.
  H2 RED73138 и missing-open RED47999 остаются отдельными historical evidence.

### Итоговые markers только для этого замороженного этапа

- [x] PWW001 Один прежний Writer/State/API/Owner, verified role, private Guard reuse без нового backend или Tree Write API.
- [x] PWW002 Partial/header/cross/sparse bytes, pending/committed EOF, отсутствие premature ZERO и flat entries подтверждены source и текущими fixtures.
- [x] PWW003 Guards между actual transitions и перед byte ACK, сохранённые actual root/base/lease и corrected cancellation runtime подтверждены; отозванный H1 RED исключён.
- [x] PWW004 Dirty shrink/regrow, pending Read/EOF/wipe, старый immutable Reader/Clone и cold exact bytes подтверждены в ограниченном scope.
- [x] PWW005 First shared native error до RAM/input/no-op, sticky repeat и здоровое чтение после одного revoke подтверждены admission12 и source.
- [x] PWW006 Charged State и Writer wrapper, неизменные owned/dirty/pin/job caps, отказы и release accounting подтверждены source/resources.
- [x] PWW007 RAM-only destruction/wipe/revoke без destructor IO; retained actual failed lease и healthy pinned Reader lifecycle подтверждены.
- [x] PWW008 Generated positive fixtures трёх role и реальные новые cancellation/admission/resources/cuts прочитаны и исполнены main в указанной матрице.
- [x] PWW009 Exact frozen source: native Release41/41, targeted Debug CLI+Tree/Files, portable39/39 и proportional v1 regression имеют завершённые результаты main.

Readback итоговых markers: **9 checked / 0 unchecked; C0/H0/M0;
ACCEPTED только для bounded worker-only packed Writer reuse.** Исторические
5/4 и8/1 не являются текущим статусом. Окончательные результаты принадлежат
main; независимыми действиями reviewer были source/evidence review и SHA
сверка. Изменён только этот append-only report.

App VS build не условие этого gate и не принят по одному факту запуска.
Установленного/запущенного нового приложения, MSIX, user inventory/audio,
hardware или внешнего release нет в этой приёмке. Полный T116 (MF/IStream
adapter, strict schema, consumers и cadence/Stop), T117/T118/T120, migration,
полная Windows функциональность/дизайн и release остаются отдельной работой.
Нет закрытия tasks/issues, commit/push/PR/merge/install/release authorization.

## Согласование исторических маркеров — 2026-10-10

В рамках обязательного независимого ревью Spec Kit, по поручению основного агента,
reviewer закрыл старые PWW003/005/006/009
по последующему final frozen-source evidence. Исходные findings, текст и
counts5/4 оставлены как история; эти отметки не означают PASS первого cut.
SHA отчёта до согласования:
`62a2f6b76f7bac7e043bce46ca83a2824e26c3ac94519f3bc91b3d4148ff251e`.
Canonical HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

| Пункт | Независимо перечитанное основание |
| --- | --- |
| PWW003 | Последующие Writer guards между gap/DATA, flush/shrink и перед byte ACK; actual result/root/lease сохраняются. Current Writer:114,175,322,400–415 и cancellation fixture:451–473 сохраняют эту конструкцию. Исправленные Release91577/Debug20733 CLI исполнили cancellation с HEAD reads3. |
| PWW005 | ready проверяет same-owner fault до RAM/input/no-op/cancel, stopped сохраняет native причину; revoke без physical poisoning. Current Writer:61–95, Tree:419–426, admission fixture:474–511 (3causes×4actions); terminal91577/20733 admission EXIT0. |
| PWW006 | Writer.h:26–28 и State:31–32 используют прежний charged CustodyAllocator; resources fixture:512–573 проверяет wrapper/owned/pin/job/dirty refusal, baseline и actual wipe-before-free. Terminal91577/20733 resources EXIT0. Это Writer-scope, НЕ принятие ALL HTTP buffers. |
| PWW009 | Финальный раздел и validation Round228: frozen Writer.cppdc1e9cc31ae90186f73d989602895026cff58c2bdb34414b25ffa3f91ad6a4fd; OwnerTests2a30db694c70c0858fb39057c4a33ab443c6ab4723478398aa9988abd2939923;38336 build0/Release41/41 PASS250.90s;91577/20733 targeted CLI и Tree/Files;44507 portable39/39 PASS11.33s. Отозванные observer failures86409/18481 НЕ восстановлены как product RED. |

Перечитаны текущие исправленные границы и соответствующие fixtures.
Current Writer.cpp SHA
`a0fe79760d101b4aec8e72f311bd3972dd5c88266f217e6cb973b159a2255a0a`;
Writer.h `855547cc256f6f5a73fbff82c6d3c3d96188f45b53771ae198316a7593b090f9`;
Tree.cpp `c308ac7159695a5a1e8edc1c65a1332481c576fff4f53b2ab270c99960d97391`;
OwnerTests `ca4e041ca15b978e6573e3473fe8ac003b166ac313bbc46c54a643bfbcef3205`.
Исторические execution receipts принадлежат main и своим frozen SHA, не
текущим bytes. Reviewer не запускал тесты/VM и не проверял guest binaries.
Raw counts всего этого Markdown теперь **18 checked / 0 unchecked**.
T116/ALL HTTP quota/scheduler/result/T120 и full320 acceptance не заявлены.
