# Round258: SOURCE-проверка protected AAC consumer

## Итоговый ограниченный вердикт

**SCOPED SOURCE correctness/evidence APPROVED** для exact source ниже после
личного чтения frozen Release258g/Debug258h receipts, rawlogs и171-file maps.
Это НЕ full native format/performance gate, НЕ приложение или T116 acceptance.
Прежние pending/NO-GO выводы ниже — история промежуточных snapshots; итоговое
решение и ограничения приведены в последнем разделе. Lane high-risk-product; `code-reviewer`
для корректности/ошибок, действующий Round258 REQUIREMENTS gate неизменён.
Own write: только этот новый отчёт; старые110 checklist/report files неизменны.

Проверены полностью `LocalRecordingPackage.h/cpp`, новый `protectedPlayback`
native test и используемые input/job/Reader lifetime участки. Header API
возвращает два scalar; прежний private `canonicalPlayback` остаётся header-only
URL-путём. Round257 legacy RED не исправлен и не принимается как GREEN.

## Точечные findings до SOURCE acceptance

### SRC258-1 — P2: native нехватка памяти теряет typed allocation error

`LocalRecordingPackage.cpp:213–215`: любой failed HRESULT кроме
MF_E_INVALIDMEDIATYPE возвращается как `CustodyFileError::ioFailed`.
Поэтому E_OUTOFMEMORY от MF или native Reader (ReaderState::status/Read
именно преобразует bad_alloc в E_OUTOFMEMORY) сохраняет nativeError, но теряет
категорию allocationFailed. C++ bad_alloc ниже и quota denial выше эту
категорию сохраняют; один и тот же отказ памяти даёт разные typed результаты.
Это не fail-open, но не соответствует заявленной границе typed allocation /
native failure. Минимум: явно сохранить allocationFailed для известного
out-of-memory HRESULT без потери точного nativeError; не превращать неизвестные
native errors в semantic corruption. Нужен countercase на существующем native
механизме отказов, не production fault switch.

### SRC258-2 — P2: монотонность timestamps проверена косвенно, не полностью

`LocalRecordingPackage.cpp:204–208` сравнивает time с counted-frame position с
допуском209×100ns, но не с предыдущим actual sample time. Для минимальных
samples это допускает регрессию: source predicate примет length2/time208/span208
при frames0, затем length2/time0/span208 при frames1 (timestamp=time, flags0).
Обе distance <=209, хотя actual time уменьшается. Это арифметический
counterexample к predicate, **не исполненная native AAC fixture** и не
утверждение, что Microsoft decoder реально выдаёт такие packets.
Предложение обещает reject timestamp regression; минимум — явно проверить
nondecreasing actual time, сохранив текущий quantization tolerance для
time/frame correspondence, без расширения100ms. Либо предъявить native
инвариант, исключающий такую регрессию для всех принятых выходных samples;
один1s positive не является таким доказательством.

### SRC258-3 — блокирующий validation gap: actual native verdict отсутствует

В промежуточном snapshot main пытался исправить media g1 singleton: writer отпускается,
member открывается с его own context, sealIndex(context,1,snapshot.index) и
publishIndex(1) вручную дублируют g1. Это **не корректная конечная audio fixture**;
актуальное writer g1/g2 исправление описано ниже. Package-state commit создаёт свою пару.
Лично прочитано в `ProtectedCustodyFilesTests.cpp:1829–1845`.
Первый RED со stub и failed positive1844 **не доказывал BOTH member closures**;
его нельзя описывать как codec-negative на полностью проверенном batch.
Неудачный publish с package-state context также setup failure, не decoder fault.
Нужны итоговый positive и damaged verdict на исправленной паре, exact source /
EXE / receipt, native Release/Debug; пока не предъявлены/не проверены.

### SRC258-4 — блокирующий validation gap: отмена в ходе чтения и отказ sibling

Исходный reviewed test (`ProtectedCustodyFilesTests.cpp:1784–1868`) содержит1s positive,
damaged mdat, cancellation **до входа**,4-job exhaustion и повторный success.
В этом исходном snapshot нет вызова с cancellation во время IO/decode или с bad
sibling. Старые batch/Reader tests полезны, но не показывают MF continuation /
shutdown / last release нового вызова при этих отказах. Требуются реальные
через этот API cases с existing afterRead и corrupted sibling; показать stage,
не переименовать cancel во время batch setup в cancel внутри ReadSample.
После отказа проверить освобождение member leases и job/pin/owned memory,
возможность следующего вызова. Late cancel не выдаёт evidence. Native format /
extra stream / flags /100ms boundary cases и performance remain pending;
неосуществимые native fixtures честно NOT RUN, без выдуманных PASS.

## Что подтверждено чтением кода

| Узел | Наблюдение и предел |
| --- | --- |
| Actual input | Private Pair current phase и sealed playback проверяются до decoder; group открывается существующим BOTH-slot batch и удерживает все siblings. Нет path cache/future fabricated owner или новых effect bool. |
| Native jobs | Outer job объявлен раньше held Pair и readers; в обратном уничтожении они отпускаются раньше outer admission. Вложенные batch/hash/packed jobs используют прежний общий<=4 счётчик, quota не обходится. Actual concurrency throughput пока не измерен. |
| COM/MF lifetime | Runtime после inputs, inner lambda содержит MF types/reader/bytes; per-iteration sample выходит до lambda release. Lambda objects уничтожаются до explicit MFShutdown. Failure/bad_alloc unwind выполняет Runtime cleanup, затем input owners, затем job. Success делает CoUninitialize, reset readers/held, final cancellation, только потом return/job destruction. Pair parameter moved, не оставляет скрытой call-owned копии после job. Caller-held Pair не обязан исчезнуть. |
| Cancellation | Wrapper проверяет общий flag до и после successful native calls; failed native error сохраняет первичную причину. MFStartup started отмечается даже при late cancel; MFShutdown не пропускается. Нет timeout, принудительного освобождения или обещания interrupt синхронного ReadSample. |
| Native format | stream0 audio/AAC48kmono; только MF_E_INVALIDSTREAMNUMBER для stream1;14B config/WORDprofile/нулевые reserved/ASC1188; optional missing только MF_E_ATTRIBUTENOTFOUND; фактический PCM16mono48k/block2/avg96000 без принудительного rate/downmix. Type-change/unknown flags отвергаются. |
| Sample/buffer | `GetTotalLength` — сумма **valid current lengths** всех sample buffers, не container duration. Zero/misaligned/over-bound output отвергается; данные последнего sample с EOS учитываются. Отсутствие Lock/PCM copy само по себе не дефект этой scalar evidence: native ReadSample выполняет decode; sample bytes не сохраняются и content не проверяется. No-buffer/zero-length sample не даёт положительного count. |
| Arithmetic | duration <=LONGLONG_MAX/10000−100 до multiplication; `(duration+100)*48` представим. `decodedFrames<=bound` сохраняется при каждом increment; bound−frames не underflow. ticks использует quotient/remainder, не overflow полного frames*10000000. Container и counted duration положительны и независимо сравниваются в100ms. Нет wall-clock padding. |
| EOS | NULL допустим только с EOS; flags0/EOS, stream0 и nonnegative timestamp. EOS с0frames не проходит close. Не универсальная проверка всякой AAC порчи; известный mdat counterexample требует native outcome. |
| Fixture | Plain generated AAC только внутри disposable synthetic test root; ciphertext protected media/member refs получают actual exact hashes. Test-only MP4 mutation сохраняет headers/sample tables и меняет mdat; production parser/temp не добавлен. Диагностика только bool/error/HRESULT/count, без PCM. |

`GetTotalLength` semantics сверены с
[Microsoft IMFSample::GetTotalLength](https://learn.microsoft.com/en-us/windows/win32/api/mfobjects/nf-mfobjects-imfsample-gettotallength).
Synchronous ReadSample действительно может ждать; NULL EOS и tick имеют
разный смысл: [Microsoft IMFSourceReader::ReadSample](https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/nf-mfreadwrite-imfsourcereader-readsample).
Ни одно из этих свойств не доказывает измеренный MF allocation peak или SC-003.

## Exact source snapshot — не frozen test receipt

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved, main меняет своё.

| Source | SHA256 |
| --- | --- |
| LocalRecordingPackage.h | fd4d8721893fea6ba706d978c3d2a28b08ccaed416d97e0213607633fb2ce710 |
| LocalRecordingPackage.cpp | 361f93518aa07d6d7e894d3430505684b91f1f197d257ecd9b93aa429c64586a |
| ProtectedCustodyFilesTests.cpp | 6748af17843c221836eae43bd08a142d474cc875115d683c2c07ddccf943678a |
| NativeHashFailureTests.cpp (Round257 unchanged) | a2d6d9a8e1dd0ea75832d987502b4cfd6a41cfd0414e6506c60ea933cc8f3f76 |

## Уточнение main после258e — не final acceptance

По сообщению main native focused Release258e прошёл1/1 за8.90s, portable46/46
не проверяет native branch. Reviewer ещё не получил/не сверил final receipt,
поэтому не выдаёт независимый GREEN/GO. Первоначальные compile/setup failures
не считаются codec failures или полной BOTH-closure RED-проверкой.

Предыдущий абзац SRC258-3 описывает intermediate snapshot6748af…, **не конечную
корректную fixture**: вручную продублировать g1 audio в обе slots недостаточно.
В новом personally-read snapshot writer делает g1/slot0, затем идентичный1byte
write и checkpoint g2/slot1; sealed ref указываетg2. Context каждого member
сохраняется, ручной peer publish удалён. Это два реальных writer checkpoints,
не package-state birth exception, перенесённое на audio.

Test сейчас расширен до positive1s/damaged1s/positive30s, pre-cancel,
quota4/retry, afterRead cancellation после отдельно посчитанного batch preflight
и readFailed с последующим reset fault. Отдельного consumer retry после IO
failure в этом snapshot пока нет; retry после cancellation есть. Это source
presence, **не выполненный final test verdict**.
afterRead на beforeDecoder+1 относится к первому IO после batch, который может
происходить уже при SourceReader creation; не утверждать, что отмена доказана
внутри ReadSample. readFailed default ordinal1 относится к batch setup, не
доказывает native decoder IO failure. Bad sibling через новый API, native
allocation category и явная timestamp monotonicity остаются findings/pending.

Production header/CPP hashes выше не изменились. Новый test snapshot:
`121b341bc24d45ffcfb242424133ff96c2ed10a6c5794369c4c3d959cc772a22`.
Два P2 source findings не исправлены этим тестовым изменением. CRITICAL/P1
fail-open или ошибку порядка COM/job/input last release в прочитанном коде
reviewer не установил; это не замена final evidence и не whole-feature GO.

Reviewer не выполнял compiler/tests/VM, не правил production/tests/old reports,
не менял GitHub/profile и не выдаёт SOURCE или whole-feature approval.

## Проверка исправлений после258f — final receipt/Debug pending

Два P2 findings **исправлены по личному чтению текущего source**:

- SRC258-1: CPP216–218 теперь возвращает allocationFailed для E_OUTOFMEMORY,
  сохраняя точный HRESULT в nativeError. Остальные native errors не становятся
  invalidContent. CPP catch/batch/quota категории сохраняются.
- SRC258-2: CPP193/207/209 хранит previousTime и отвергает time<previousTime;
  прежние209ticks и100ms не расширены. Source counterexample208→0 теперь
  отвергается. Это исправление predicate, не mock/native format acceptance.

Лично перечитаны новые native tests1854–1891: pre-cancel, quota4/retry,
afterRead cancellation после измеренного batch, readFailed, throw bad_alloc на
beforeDecoder+1 с allocationFailed и retry, настоящая порча1cipher byte у
media sibling `block.0.2`, invalidContent и восстановление exact byte/retry.
Owned memory сравнивается с before после завершения fixtures; Pair отпускается
и package-state write-open проверяется. Никакой production fault knob не добавлен.
Код сохраняет исходные positive1s/damaged1s/positive30s.

Это закрывает прежнее **отсутствие исходного кода** для mid-input cancel и bad
sibling; исполнение SRC258-3/4 ещё требует final native receipts. Отмена и
allocation на первом IO после batch могут происходить при SourceReader
creation, не обязательно в ReadSample. readFailed ordinal1 остаётся batch
failure; следующий successful retry после reset и allocation-case подтверждает
задуманную повторную проверку, не отдельный decoder-stage IO-fault verdict.
Allocation test проверяет typed category; точный HRESULT сейчас подтверждён
source mapping, а не отдельным test assert nativeError==E_OUTOFMEMORY.

Main сообщил native258f1/1 GREEN11.55s; reviewer его **не исполнял и не проверял
export/EXE source map**. Debug/new freeze pending. Format/extra-stream/type
change/flags cases не объявляются native PASS без настоящих fixtures, bounded
memory/CPU/performance и whole T116/T118 также не принимаются.

Текущие personally-hashed bytes:

| Source | SHA256 |
| --- | --- |
| LocalRecordingPackage.h | fd4d8721893fea6ba706d978c3d2a28b08ccaed416d97e0213607633fb2ce710 |
| LocalRecordingPackage.cpp | 0ccedb1a67363be192460349cc87d2fa0ddce97184f32fc7027112f47416da6c |
| ProtectedCustodyFilesTests.cpp | dff07b7f5a0bb790564f952d43644346310ab947f70b2bce21ec464d9131391f |
| NativeHashFailureTests.cpp | a2d6d9a8e1dd0ea75832d987502b4cfd6a41cfd0414e6506c60ea933cc8f3f76 |

Для этой версии новых CRITICAL/P1 или открытых P2 production defects по
прочитанному scope не установлено. Это **не final SOURCE GO**: независимая
проверка frozen native evidence ещё не выполнена. REQUIREMENTS gate и все
старые отчёты не меняются, legacy Round257 RED остаётся отдельным NO-GO.

## Final frozen258g/258h: ограниченный SOURCE approval

Reviewer лично read/parse/hash проверил оба terminal receipts, оба полных
rawlogs и source171 map; каждый из171 canonical files захеширован на Mac.
Release source_hashes == Debug source_hashes == отдельный g source map,
canonical mismatches0. UTF8 BOM удалён только в памяти при диагностическом
JSON.parse; exports не переписаны, hashes включают actual BOM. Два неудачных
readonly Ruby comparison invocations (syntax / Ruby2.6 filter_map) ничего не
изменили; затем each_with_object comparison успешно выполнен.

Путь exports: `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.

| Export | SHA256 |
| --- | --- |
| graf-f200-aac-round258g-green.json | 3ce76eccf2fb36cfe2c3c51c9bb1c5b7cb0fa869c50ca9e2353f6471bcfc4427 |
| source-aac-round258g-green.json | ed2fef4129753f58a69314ed7ef1363bd5a89eeae254641f2d19231758947bcd |
| graf-f200-aac-round258g-release-test.log | 7b503d79045a4e212c67847080176ef4433254ea81e6bc24e2ead32d9c23148e |
| graf-f200-aac-round258h-debug.json | 5be071b13dd954e62fca566e1826b4f23b25965fa1783ea98a40549809e15315 |
| graf-f200-aac-round258h-debug-test.log | c2f4b1d6bd8a8119ec24636b49c63ab02c8b80fd2980d39c4205788cf186bf2b |

Release receipt: schema1, mode `aac-payload-red` (reused label, НЕ RED verdict),
phase passed, terminal true, configure/build/test0, source_count171.
Debug: schema1, mode protected-aac-debug, phase passed, terminal true,
build/test0, source_count171; configure_exit отсутствует, не выдуман.

Rawlogs содержат ровно focused `ProtectedCustodyFilesTests` с actual command
`C:/Temp/graf-f200-calendar-native-build-UjB7WI/{Release,Debug}/ProtectedCustodyFilesTests.exe`,
Test Passed,12.67s/17.93s. `9/50` — registered suite index, не50/50 PASS.
Exe hashes из personally-parsed receipts:

- Release `84011cb1583c2c690693b07299635bcc86b9c083659bd561e2feef7f11d9b307`.
- Debug `c8c34baa13e57d6904ef18ff512189c9cbe0ce7afbffbe136bcb05623feea2ee`.

Reviewer НЕ выполнял NTFS/VM EXE reread. Main сообщил о последовательной
проверке mirror/NTFS/EXE; её completion не подменяется этим receipt reading.
Первоначальный global preflight STOP не результат теста и не повод убивать
чужие cl jobs; reviewer процессы не трогал.

Одинаковые scalar rows в обоих rawlogs:

| Case | Наблюдённый результат |
| --- | --- |
| Generated1s | accepted1/error0/native0, returned decodedFrames48128 |
| Damaged1s | accepted0/error7 (invalidContent), native0xc00d36b4 (MF_E_INVALIDMEDIATYPE), result absent |
| Generated30s | accepted1/error0/native0, returned decodedFrames1440768 |

Damaged row frames0 — test printer выдаёт0 при отсутствующем result; это **не
отдельное измерение внутреннего decoder frame count**. Из этого ряда не
следует HRESULT decoder failure, полный corruption detector или причина
отказа до/после EOS. Round257c zero-PCM proof остаётся отдельным evidence.

Лично source-bound assertion trace: native main без negative-control argument
вызывает protectedPlayback; NDEBUG явно undef доcassert. Поэтому successful
focused process исполняет positive/damaged/30s, pre-cancel, quota4/retry,
after-preflight input cancel/retry, readFailed, afterRead bad_alloc с typed
allocationFailed/retry, настоящую ciphertext media sibling corruption и
restore/retry, final owned-memory equality и release/write-open assertions.
Для этих непечатаемых cases источник доказательства — **source asserts +
passed whole focused executable**, не выдуманные отдельные scalar rows.
Exact native allocation HRESULT source mapping сохраняет E_OUTOFMEMORY;
test проверяет error category, не отдельный assert exact nativeError.
SRC258-1/2 source findings закрыты; SRC258-3/4 подтверждены в этом ограниченном
объёме final exports, не в более широком decoder-stage/performance смысле.

### NOT RUN / не принимается этим approval

- late-cancel, воспроизведённый именно внутри actual ReadSample или shutdown;
  after-preflight+1 IO может происходить при SourceReader creation;
- native IO fault именно после decoder startup; default readFailed ordinal1
  остаётся batch setup fault;
- дополнительные/отсутствующие streams, malformed/HE config, type-change,
  unknown flags/tick/empty sample и точные100ms boundary counterfixtures;
- отдельно воспроизведённая native timestamp regression;
- MF native allocation peak, CPU/memory/concurrency/collection/Stop performance,
  полный SC-003 и format gate:30s generated positive не заменяет измерения;
- current Windows SDK/Visual Studio solution build, полный native CTest,
  installed/MSIX/real-device/physicalx64/accessibility/release acceptance;
- full protected semantic manifest/privacy/normal/degraded/short/account/
  bootstrap/queue/effect adoption и legacy migration/retirement.

Portable46/46 — сообщение main, не personally-read portable receipt и не
native branch proof. Нет задачи/checkbox closure, wholeT116/T118 GREEN,
обхода B1 для прежних callers или исправления Round257 legacy RED.

**Итог:** для exact header fd4d872…, CPP0ccedb1…, test dff07b7… (полные hashes
выше,171 frozen files personally MATCH) correctness/source evidence принят
в описанном scope; новые CRITICAL/P1/P2 code findings не установлены.
Approval разрешает дальнейшее проектирование/интеграцию только через её
собственные gates, не выдаёт приложению authority из двух scalar результатов.
