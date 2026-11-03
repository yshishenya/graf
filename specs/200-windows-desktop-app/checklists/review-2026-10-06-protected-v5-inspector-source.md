# Round259: SOURCE-проверка protected v5 inspector

## Промежуточный вердикт

**SCOPED SOURCE APPROVAL: Round259 protected v5 inspector.** SRC259-1
исправлен и подтверждён лично прочитанными frozen Release/Debug logs;
SRC259-2 закрыт для этой области по frozen172 source map и календарным
regressions. Исторические finding, snapshots и pending-состояния сохранены
ниже; итоговый scope/evidence приведён в последнем дополнении.
Нового CRITICAL/P1/P2 blocking defect в прочитанной области не установлено.
Это не принятие whole application/T116, legacy Round257 RED
и REQ257-B1 остаются открытыми.

Использован `code-reviewer`, lane existing high-risk-product. REQUIREMENTS259
полностью прочитан в предыдущем review, SHA сейчас лично повторно проверен:
`ea4e3d89b490d398d2545fbbaeb84c66f7ed75c482dec109d80b1f14f76919da`.
Read-only scope: все LocalRecordingPackage.h/.cpp, весь JsonString.h,
actual DesktopApiClient string wrapper/JsonReader/call contexts и его diff,
actual native protectedPlayback fixture/inspect assertions и используемые
Pair/Reader/packageShape/allocator/lifetime участки. Не заявляется повторное
полное ревью всех прежних storage/calendar тестов или всего DesktopApiClient.

## SRC259-1 — P2: valid optional finals без manifest всегда отвергаются

`LocalRecordingPackage.cpp:503–512`, особенно512:
`else if (ref(media) || ref(playback)) return reject()`.

Новый readonly API принимает degraded canonical+recovery без manifest, однако
отвергает тот же валидный prefix, если selected state дополнительно содержит
sealed media и/или playback. При этом batch уже проверил exact logical hashes
и refs; формат этих finals не проверяется, blanket отказ наступает до этого.
Согласованная модель требует полностью проверять каждый присутствующий final,
не требует manifest ради optional final и не объявляет его отсутствие успехом.

Producer действительно может оставить итоговый WAV без manifest: existing
V5LocalRecordingWriter.cpp:312–323 сначала переименовывает WAV, затем проверяет
playback bytes/rename; следующая ошибка выполняет retainPrefix и возвращает
recovery, не создавая manifest. Это trace существующего producer, **не**
исполненная новая protected fixture и не утверждение готовой producer migration.
Такой truthful state не должен терять degraded semantic acceptance только
из-за дополнительного исправного final.

Минимум: независимо валидировать present sealed media по actual ref length и
derived prefix duration, present sealed playback тем же native decoder и
derived duration. При present manifest descriptors должны дополнительно exact
совпасть с выбранными refs; отсутствующий referenced artifact остаётся отказом.
Не добавлять новый parser, normal/upload boolean или выдуманный manifest.
Нужны actual fixtures canonical+recovery+media/no-manifest и, где есть native
fixture, canonical+recovery+playback/no-manifest, а также плохой present final.
Это false negative, не unsafe normal claim; всё ещё блокирует SOURCE approval
согласованной normal/degraded области до исправления/явного согласования.

## SRC259-2 — validation gate: final evidence отсутствует

Main сообщил genuine RED259a configure0/build0/test8/assert semantic.ok():1857,
focused7.78s. Reviewer **не исполнял** этот тест и пока не читал immutable
receipt/rawlog/source map; сообщение не подменено personally-verified RED.
Текущий прочитанный native protectedPlayback source добавляет1s/30s valid
inspect, no-session legacy, damaged AAC с исправленным descriptor SHA и
retained owner/write-open assertion. Это полезно, но ещё не full
privacy/degraded/boundary/cancellation/cleanup acceptance.
Итоговые test bytes меняются main, поэтому snapshot hashes ниже промежуточные.

Перед SOURCE approval нужны frozen current Release/Debug и calendar regression
результаты, exact source maps/receipts/rawlogs, лично проверяемая причинная связь
assertions с их actual execution. Положительный тест не доказывает отказ
unknown/duplicate/null/Unicode/64KiB/number/time/prefix/reason/ref/format cases.
Late cancel именно в ReadSample/shutdown и native format/flags/streams cases
не выдавать за PASS по after-preflight IO или неисполненному mock.

## Что подтверждено чтением текущего source

| Узел | Наблюдение и граница |
| --- | --- |
| Genuine result | Private ctor ProtectedInspection; result удерживает Pair, BOTH readers, charged manifest. Наружу только const scalar evidence, нет stream/path/effect capability или normal cache. Struct ProtectedEvidence без владельцев сам по себе не proof. |
| Input lifetime | package reference берётся из Pair и остаётся жив после move в held. Session копируется в CustodyBytes до native waits; parser не сохраняется после вызова, result не удерживает borrowed session view. Roles из private validated package, selected sealed phases проверены. |
| Native job / release | Outer job объявлен до session/held/readers; failures unwind input owners раньше admission. AAC TU helper заканчивает MF objects/Shutdown/CoUninitialize прежде return. Success transfers group в private result; dormant group остаётся под real pins/owned memory, не под ложным активным native job. Новые операции/effect adoption не разрешены этим API. |
| Allocation / proof construction | Charged result object и shared_ptr control block, charged manifest/token/session/ID vectors. Construction exception deallocates raw; control-block bad_alloc вызывает supplied deleter. Final cancel после proof construction освобождает proof, не возвращает success. Exact native allocation/cancel types проверяются по фактическому mapping, не bool. |
| Parser | Closed field masks, normalized decoded key lookup/duplicate rejection; no DOM/recursive skip. Windows marker snake_case; true rejected. Status/reason optional только вместе; time triple optional только целиком. Bad present time/offset не silently dropped. Normal no-session legacy не claims session binding. |
| Privacy | Exact OPEN mask0x7af/closed0x7ff; known enums, bool, positive/nonnegative Int64 arithmetic, end>=start/duration exact. Gregorian UTC20B date check без wall-clock order. Charged decoded unique IDs; UTF-8/escapes через shared traversal. Quadratic uniqueness ограничена whole64KiB, это не отдельный segment cap. Runtime performance не измерен. |
| Unicode extraction | Весь79-line JsonString.h прочитан; traversal сохраняет validation UTF-8/surrogates/escaping/maxRawBytes/allowNul. Byte emitter не аллоцирует сам, caller отвечает за throw/allocation. Calendar wrapper использует прежний std::string result, v5 charged token заранее reserve(input size). Emitted invalid prefix никогда не возвращается как accepted string. Calendar runtime regression pending. |
| Prefix | Recovery exact fields/reason/hash/length; N>0 и N<=canonical_bytes/1920. Logical role limit делает N*1920 и N*10 representable. Только N*1920 читается finite-float chunks, весь объект ранее SHA-verified, tail не scanned как prefix/padding. Result не выдаёт наружу canonical stream; будущий stream accessor обязан ограничить prefix реально, не одними scalar. AEC provenance не выводится из float/SHA. |
| Normal format | Exact WAV44 header/u32 RIFF/data bytes/PCM16mono16k/duration. Native AAC helper reuse без URL/temp/reopen; full counted PCM EOS и config/duration проверки Round258 сохранены. Additional format/error/100ms boundary runtime proof остаётся отдельным. |
| Group fault / adoption | Before proof final loop Seek проверяет shared Reader status/cancel и восстанавливает cursors; group не отпускается между hash/manifest/native decode. Semantic evidence о retained bytes не заменяет current account/bootstrap/queue/admission. Снятие later cancellation не воскресит повреждённый stream group. |
| Legacy | Plain inspect остаётся4096B exact regex/header-only AAC URL. Не получил новый full decode/manifest privacy acceptance; это существующий открытый migration/adoption gap, не hidden implementation completion. |

## Текущий snapshot, не final test freeze

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty/main changes preserved.

| File | Personally-hashed SHA256 |
| --- | --- |
| LocalRecordingPackage.h | af126bc8b01d6b14a09884183e347d75bb90ea15a7d5070ac824d6607ad25fb4 |
| LocalRecordingPackage.cpp | 838b603716ef48d60ed80f0ce2d39a0bb0c9896ac4d03c3fcdd96ef11b8f6db6 |
| Contracts/JsonString.h | e07cecc28815e8803d69b07e99f5bc9ca195e0aa1d1c30f6866a92c8d27389ac |
| Upload/DesktopApiClient.cpp | a2442981a1113c985d8d9307e897161149a43e9c6895e6cc035e668b2e6373dd |
| ProtectedCustodyFilesTests.cpp | 798a5c038e037e9a04cb8e7f4ea8de79022d5d278fd054dcc6d2dcc24a9ddeff |

Reviewer write **ONLY** этот новый report. No code/tests/spec/plan/tasks/old
reports/GitHub/VM/app/profile/commit changes; native/compiler execution не было.

## Дополнение: SRC259-1 resolution и проверка исходного кода матрицы

Лично перечитаны актуальные `LocalRecordingPackage.cpp:436–533`, вся новая
`protectedRecordingSemantics():1922–2076`, reusable fixture helper
`protectRecordingMember():1784–1798` и вызов из native main:2322.
`NDEBUG` явно снят до assert; default native run вызывает и прежний
`protectedPlayback`, и новую матрицу. Portable branch их **не** исполняет.

**SRC259-1 закрыт на уровне исходного кода.** В CPP:503–516 present media
всегда проходит WAV header/ref-length/derived-duration проверку, present
playback — настоящий native decode с той же derived duration. Проверка
manifest descriptors выполняется дополнительно только при present manifest.
Запрет normal/effect authority для degraded не снят. Новый контрпример к
этому исправлению или blocking defect в прочитанных изменениях не обнаружен.
Runtime acceptance исправления ещё не выдано.

Подготовка actual protected fixtures не подменяет семантический отказ плохим
SHA: helper создаёт audio через writer/checkpoint g1 и identical one-byte
rewrite/checkpoint g2, metadata через существующий commit; current ref SHA и
length вычисляются из фактических изменённых bytes. Pair читается настоящим
private provenance API до inspect. Нет fabricated public Pair или fake
normal result. Все рассматриваемые audio/member buffers непустые.

| Source cases | Что именно установлено чтением, не новый runtime PASS |
| --- | --- |
| 45 normal/privacy/metadata | 43 именованных initial cases + history40 segments выше4096 + manifest ровно65536 bytes. Positive/negative result и error assertions присутствуют; normalized duplicate keys/IDs, Unicode/invalid UTF-8, dates/monotonic/optional ends, number/time/status/short marker cases не пропускаются. Legacy no-session acceptance не выдаётся за identity binding. |
| Protected size limit | 65536 accepted case проходит inspect. Отдельный65537 test проверяет отказ metadata commit до записи (`writes == 0`), **не** прохождение oversized sealed manifest через inspector. |
| Actual degraded producer | Prefix-only writer с encoder returning false действительно проверяет failed finalize, retained prefix и отсутствие manifest на диске. Recovery/canonical читаются из этого producer; успешные optional finals берутся из отдельно завершённого degraded writer. Это synthetic protected fixture, не уже мигрированный production writer. |
| 14 degraded cases | 0 prefix-only, 1 partial tail, 2 shorter trusted prefix; 3–8 reason/count/length/finite-float/SHA failures; 9 all finals+manifest; 10 media/no-manifest; 11 playback/no-manifest; 12 wrong WAV sample rate with correct ref; 13 unreadable whole AAC file with correct ref. Acceptance predicate и trusted-prefix/duration/integrity assertions согласованы с этими mutations. |
| Case13 accuracy | Whole playback file заполнен0xff; это native unreadable-final counterexample, **не** Round257 mdat-only mutation с сохранённым container. Test допускает typed native error, проверяет fail/non-none и не заявляет universal corruption detection или конкретный HRESULT. |
| Cancellation/quota/cleanup | Accepted normal cases проверяют pre-cancel, four active jobs и retry. current_legacy добавляет owned-memory pressure и cancel after first input read; это group/preflight IO, **не** доказанный late cancel внутри ReadSample. Result pins state до release; normal loop после release также проверяет write-open всех трёх членов. Degraded loop проверяет state release; общий owned-memory счётчик возвращается к before. Не заявлен отдельный write-open assertion каждого degraded member. |

Исходный код матрицы не выявил setup bug, который заставлял бы expected
negative cases падать до создания genuine Pair из-за неверного descriptor.
В частности case12 изменяет WAV sample-rate byte24, а затем helper заново
вычисляет protected ref SHA; case13 аналогично шифрует изменённые bytes.
Case1 recovery bytes/SHA включает partial tail; trusted prefix остаётся100
полных кадров. Case2 count99 даёт990ms без manifest и без invented padding.

### Лично повторно проверенный текущий snapshot

| File | SHA256 |
| --- | --- |
| LocalRecordingPackage.h | af126bc8b01d6b14a09884183e347d75bb90ea15a7d5070ac824d6607ad25fb4 |
| LocalRecordingPackage.cpp | c274a19b4b017b1db365ead1785a12096205b399e6f4ad839c3bdf6f744eb890 |
| Contracts/JsonString.h | e07cecc28815e8803d69b07e99f5bc9ca195e0aa1d1c30f6866a92c8d27389ac |
| Upload/DesktopApiClient.cpp | a2442981a1113c985d8d9307e897161149a43e9c6895e6cc035e668b2e6373dd |
| ProtectedCustodyFilesTests.cpp | d33dc55feaa6fb8d8991001035d416118dc7de1857db38c8a0dc9ab931629e5d |

REQ259 `ea4e3d89b490d398d2545fbbaeb84c66f7ed75c482dec109d80b1f14f76919da`
повторно hash-verified, не изменялся reviewer.
Main сообщил pre-matrix native Release259b1/1,13.49s и portable46/46,21.67s;
эти результаты здесь остаются сообщёнными main, **не** лично проверенными
fresh frozen execution доказательствами новой45+14 матрицы. Reviewer ничего
не запускал. SRC259-2 остаётся pending до чтения exact source maps, immutable
Release/Debug/calendar receipts и rawlogs. Никакого final SOURCE GO, SC-003,
full native format/performance gate, SDK build или application/T116 closure
это дополнение не выдаёт; legacy RED257/REQ257-B1 не закрыты.

## Итог: лично прочитанные immutable доказательства Round259

**SCOPED SOURCE APPROVAL** только для genuine retained protected
sealed normal/degraded semantic inspector, shared string traversal reuse и
прочитанных native assertions. SRC259-1 закрыт также по actual cases10–13
в обоих журналах. SRC259-2 закрыт для заявленной области. Это не разрешение
на обход следующих product/adoption/release gates.

Все файлы ниже лично прочитаны/parsed и SHA256 вычислены из неизменённых
bytes в `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI/`.
UTF-8 BOM в receipts снят **только в памяти** для JSON.parse; исходные
exports не переписаны. Source digest включает их действительные bytes.

| Immutable export | Лично проверенный SHA256 |
| --- | --- |
| source-v5-round259c-matrix.json | 0ea1f94d9d8a26d9a5cd91cbbafb5c16d69aaa5c7217519dc374241bbce6bf58 |
| graf-f200-v5-round259c-matrix.json | 9c2502d170a22270cfe1a479ec1c6d79d8722c0a72fc764ce79b7462d90eb456 |
| graf-f200-v5-round259c-release-test.log | 21e5f51972bf2c4518acd0541b0f321789c7b1c17069394c8e83c81dbf6563a1 |
| graf-f200-v5-round259d-debug.json | fdb27e01324ae1963445e4ad75caa7c00b6434f9d5b8e34c07f8f849d5437e35 |
| graf-f200-v5-round259d-debug-test.log | 36bbc0e202430e7699de53bcf0665aa729aeb13a981a26d6ce1f981655cf439a |
| source-v5-round259a-red.json | 13aa6010da45d9880271c1de15d42bdd9e1a2bb9602f778ba69966950d010b71 |
| graf-f200-v5-round259a-red.json | e3a45d441acb578e444d5e5db1e604d09fd8e2979cd893452beb6ea8a88472ce |
| graf-f200-v5-round259a-red-test.log | ac9dce63abbf7dba008be4b2b03cb9da369b850754080273f1cb8c218b8341e6 |
| graf-f200-v5-round259e-calendar.json | 59aebc20d835982fc22ad083e47bbd7a9b1168c6aea135066d455c256f233be2 |
| graf-f200-v5-round259e-calendar-test.log | 21506493f6470163f59c35f73ad66b18978c1a676646f179959d7bf1a7236bc0 |

### Source binding и точные результаты

Source map c содержит172 inputs. Для **каждого** path выполнена личная
проверка SHA256 соответствующего canonical `apps/windows/<path>`:
172/172 MATCH, отсутствующих файлов0. Receipts c/d/e имеют exact ту же
source_hashes map и source_count172. Независимый digest отсортированной
карты Windows paths (`path + space + SHA + LF`):
`b168d9436691b12f148d6d3d60bacab3d68db3a5d6b0d10e1a2bd59a40f0127a`.
Это hash binding всего inventory, **не** новое полное SOURCE review всех172
файлов. Five-file snapshot выше остаётся точным текущим review target.

RED a receipt: terminal=true, phase=failed, configure0/build0/test8;
source_count171 и map exact совпадает с его отдельным source export.
Raw log показывает genuine Release ProtectedCustodyFilesTests command,
`semantic.ok()` assert1857,7.78s, Test Failed. Это старая RED ревизия,
не current172: четыре общих файла изменились (DesktopApiClient,
LocalRecordingPackage.h/.cpp, FilesTests), JsonString.h добавлен.
Исторические bytes не объявлены совпадающими с current source. Этот RED
не превращён в PASS и не подменяет независимый legacy RED257.

Release c receipt: terminal=true, phase=passed, configure0/build0/test0.
Raw command — `Release/ProtectedCustodyFilesTests.exe`; один выбранный
CTest PASS25.05s. Debug d: terminal=true, phase=passed, build0/test0;
raw command — `Debug/ProtectedCustodyFilesTests.exe`, PASS32.57s.
`9/50` в журнале — индекс выбранного теста в CTest inventory,
**не** выполнение50/50.

Оба raw logs лично прочитаны целиком:45 уникальных normal/privacy/metadata
rows (11 accepted,34 rejected) и14 degraded rows (6 accepted,8 rejected).
Повторно parsed counts совпали. Cases10/11 дают accepted1/error0;12 даёт
accepted0/error7/native0;13 — accepted0/error6/native0xc00d36c4.
Таким образом правильный optional final без manifest не отвергается, а
неверный final с correct ref hash не принимается. Source assertions после
rows и итоговый native PASS связывают эти outputs с ожидаемыми результатами,
pre-cancel/mid-member-input cancel/quota/owned-allocation/retry/pins-release
проверками и возвратом общего owned-memory счётчика. Они не являются
доказательствами late cancel внутри ReadSample.

Прежние protected AAC rows в обоих logs:1s good48128frames, damaged отказ
error7/native0xc00d36b4/frames0,30s good1440768frames. Эти scalar outputs
не объявлены normal/effect proof сами по себе и не меняют legacy path.
Release явно SKIP charged-proxy allocation branches; Debug выполняет
charged-proxy regression и показывает cleanup_owned16/expected16. Такой
SKIP не скрыт как Release PASS соответствующей отсутствующей ветви.

Calendar e export найден уже завершённым: terminal=true/phase=passed,
configure0/build0/test0. Raw log содержит8 отдельных Test Passed:
CalendarJoinResolverTests, CalendarJoinWireTests, CalendarJoinHostTests,
CalendarJoinOperationTests, CalendarMeetingUrlTests,
CalendarMeetingNativeTargetTests, NativeCalendarJoinTransportTests,
NativeCalendarLauncherTests. Все команды — current Release binaries;
map172 exact current. URL corpus141/141, ICU15.1. Operation test явно
state/fence only, NativeTarget conversion only, Launcher fake statics;
это **не** real OS meeting launch или installed UI acceptance.

Receipts записывают EXE hashes (лично прочитанные поля, **не** reviewer
NTFS reread/execution): Release FilesTests
`f46d8b2f6a05bb9853e396edf068d7050500ad24f90f9ebc75831dbc2a1a15cf`,
Debug FilesTests
`8958afe3ab2a6ff540973f07f18b439418c4eb888712e55a7470a316b1ea606c`,
исторический RED FilesTests
`78eceb4870e92113effdfcd46fae2e69934e81f5ef67e2351aebcf8400ed12a7`.
Reviewer не открывал VM и не запускал эти binaries.

### Что этим итогом не принято

Нет whole application/installed/release/50-suite/SDK-current-build claim.
Новая portable rerun и Node Chromium/WebKit результаты здесь остаются
сообщениями main без personally-read frozen exports; native-only inspector
не покрывается portable46 suite. SC-003 и native memory/performance gate
не закрыты длительностью focused fixture suite или30s synthetic recording.
Late cancel actual ReadSample/shutdown, extra streams/typechanges/flags и
полная100ms boundary native matrix не заявлены выполненными.
Writer/queue/bootstrap/current account/epoch/effect adoption, bounded future
prefix accessor, migration и legacy RED257/REQ257-B1 остаются дальнейшей
работой; T116/tasks/issues не закрывались. Старые normative/historical
reports и их checkbox state не менялись. Reviewer изменил только данный
owned report, без production/tests/GitHub/VM/commit/profile действий.
