# F200 — измерение завершения защищённой записи

Дата: 2026-11-03. Продолжение существующей T116, lane `high-risk-product`.
Цель — локализовать задержку Debug-проверки восстановления частичного AAC,
сохранив полную проверку содержимого и ограничения времени. T116/T117 и
приёмка установленного приложения этим измерением не закрываются.

## Существующий измеритель: terminal PASS

Выполнен уже реализованный `NativeCaptureStorageIntegrationTests.exe
--protected-storage-profile`. Исходники и тесты для этого запуска не менялись.
Он создаёт искусственную запись из 1000 кадров (10 секунд), использует
настоящие защищённые потоки, Media Foundation/AAC и проверку пакета.
Микрофон, системный звук, сеть и пользовательские записи не используются.

Stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t116-existing-profile-y3c9h8si`.
Собственный каталог фикстур Windows:
`C:\Temp\graf-settings-chain-li1qcg1c\fixtures-t116-existing-profile-y3c9h8si`.
Использован ранее собранный Debug EXE:
`e7eea37d137d930b7a65aec24f943586fe9abd70537f2f6408f001bca17fd512`.

Запускатель завершился с кодом 0; самопроверка измерителя и признак возврата
собственной памяти в исходное состояние подтверждены. Совпали 225 входных
файлов до/после, хеш EXE до/после и хеш установленного GRAF 0.1.0.15.
Процессов собственной сборки после завершения — 0. Установленный GRAF
не обновлялся и не останавливался этим измерителем.

| Этап | Полное время, мкс | Внутри четырёх измеряемых системных вызовов, мкс |
| --- | ---: | ---: |
| Открытие | 242297 | 19345 |
| Добавление кадров | 5162728 | 2196046 |
| Завершение целиком | 8017068 | 866570 |
| ↳ Запечатывание исходного потока | 309534 | 68870 |
| ↳ WAV | 832168 | 233794 |
| ↳ AAC | 4014861 | 142719 |
| ↳ Проверка содержимого | 1550776 | 211270 |
| Освобождение | 13298 | 0 |

Четыре вызова: `GetFinalPathNameByHandleW`, `GetFileInformationByHandleEx`,
`GetSecurityInfo`, `FindFirstStreamW`. Их сумма не учитывает чтение, шифрование,
сброс на диск и работу кодеков. Строки со стрелкой вложены в завершение;
складывать их с полным временем завершения нельзя. Этап AAC включает чтение
защищённого исходного потока, кодирование, запись, запечатывание и независимое
декодирование; это не отдельное измерение скорости кодировщика.

`terminal-evidence.json` SHA-256:
`c1bafc2be8cd3b2888e66cf138ba3f9d43152fcfe535bffedd3901d88e804c39`.
Он сохраняет точные значения и хеши запускателя, входов, результата и журналов.

## Что пока не установлено

Успех обычного завершения 10-секундной записи не заменяет проверку
восстановления 60-секундного частичного AAC. Два уже сохранённых запуска
`ProtectedRecoveryPlaybackPartial` превысили неизменённый предел CTest 180 с.
В последнем запуске восстановление достигло `partial_recovered` на 174500 мс
и `cold_pair_read` на 174657 мс, но окончательная независимая проверка,
неизменность файлов и возврат всех ресурсов не успели подтвердиться.

Следующий шаг — измерить границы существующих prepare/finish при восстановлении
в самом тесте. Нельзя объявлять причиной VM, ослаблять доказательства целостности,
увеличивать предел времени или менять размер кэша по результату этого профиля.

## Повтор с фазовыми метками: terminal TIMEOUT

Независимый requirements/analyze GO и затем SOURCE GO записаны в
`review-2026-11-03-partial-performance.md`. Фактический patch добавил метки
времени в единственную функцию `coldRecoveryPlaybackPartial`, сохранил
`GetLastError` вокруг вывода и разделил два вызова `recover` на существующие
`V5RecoveryTestPeer::prepare/finish` с теми же аргументами и непрерывным владением.
Все 27 прежних asserts и весь код вне функции побайтно прежние; новые два
assert проверяют успешную подготовку перед единственным finish.

Stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t116-partial-phases-1au8f_o_`.
Test SHA-256:
`dea4cbe211192797adda5df68711d6101f980713aad428dd1255e335e23b012f`.
Run.ps1 SHA-256:
`51a4420784dd2dee49f7b095f20e8513775b0217c68a4f37f65229cd77d7dedd`.

Перед сборкой совпал прежний frozen manifest225; в изолированной копии Windows
заменены ровно test/AppMain/vcxproj. Последние два файла приводят manifest к
нынешнему checkout и не входят в выбранный CMake target. Новые 225 входов
совпали до и после выполнения. Debug-сборка V5 завершилась с кодом 0;
EXE `402ea81a0d986691a624125ca963de050c3c413c1a7226746adb9b24d65e547a`
побайтно прежний после теста. Установленный GRAF 0.1.0.15 не изменён,
собственных процессов по завершении — 0, принудительной очистки wrapper нет.

| Граница | Начало, мс | Конец, мс | Затрата, мс |
| --- | ---: | ---: | ---: |
| Baseline prepare | 9421 | 9484 | 63 |
| Baseline finish | 9484 | 62843 | 53359 |
| Partial prepare | 103031 | 103140 | 109 |
| Partial finish | 103140 | 168328 | 65188 |
| Независимая cold inspection | 168484 | 178656 | 10172 |

Actual partial AAC: 524288 байт против complete732186, generation3;
старый partial отказал именно codec-content ошибкой `0xc00d36c4`.
Восстановление сохранило прежние extent/original hashes, что подтверждено
существующими asserts до cold reopen. Независимая cold inspection завершилась,
но privacy/read-only/idle конец и `COLD_PARTIAL_RECOVERED` до deadline
не подтверждены. Результат — **CTest exit8 / Timeout180.032**, wrapper exit1.
Это отказ полного теста, а не успешное восстановление по промежуточной метке.

`terminal-evidence.json` SHA-256:
`0bd061575510619344efe3e583ed0702b2348f4c7e44683aec55dd1512b666c4`.
До реального запуска сохранены две отдельные ошибки запускателя: запрет
`-File` текущей ExecutionPolicy и отказ Parallels открыть длинную команду.
Они не запустили сборку/тест. Короткая команда проверила доступность гостя;
одобренный scriptblock затем выполнен с проверкой точного SHA. Политика
исполнения, права Windows, доверие к сертификатам и пользовательские данные
не менялись. Эти ошибки не включены в результат CTest.

Теперь известно, что основная затрата внутри finish, а не prepare. Разница
между baseline и partial сама по себе не доказывает стоимость WAV или кэша.
Нужен отдельный воспроизводимый счётчик чтений при чередовании двух потоков;
предел180, fixture6000 и все доказательства остаются прежними.

## Чередование двух actual readers: terminal PASS

После отдельного requirements/analyze и SOURCE review расширен только
существующий cross-state сценарий ProtectedCustodyFilesTests: current/old
ReaderState действительно возвращают четыре байта77/42, прогреты оба,
затем выполнены8 пар чтений block0. Существующий native `reads` дал
**32 дополнительных DATA-read**. По количеству не вводилось нового условия
успеха: это наблюдение нынешнего кэша, не RED будущего исправления.
Счётчик означает вызовы существующей обёртки ReadFile, а не число промахов,
расшифровок или физических обращений к носителю.
Все прежние проверки файла сохранены; production reader/cache не менялся.

Stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t116-cache-alternation-pwnja25m`.
Полный Debug ProtectedCustodyFilesTests: **PASS344.13s**, build0/CTest0/wrapper0,
225 входов до/после, PE unchanged, installed0.1.0.15 unchanged, own_processes0.
Внешний driver900 соответствует ранее измеренному363.859s этого полного
набора; CTest properties и partial CTest180/child60 не менялись.
Test SHA-256 `cedc84a1428b01df77461b020cb5e5517cb401ce7c5d0e0bf42e276620b507f9`;
Run SHA-256 `927a9a59770247f4e28320ae2720341fe6fb1d6e9c965146246ef5dbc556f690`;
PE SHA-256 `d0dfbe2a9b68566a9e514fcdd251c98d11014ce775322b26e0566b578ba56d49`;
terminal-evidence SHA-256
`21147befe0981bc14d24c02cfa2089a8178d08a0d02437f4d4ab60574b96452b`.

Доказан механизм вытеснения общей записи кэша между разными ReaderState
на actual flat-v1 пути. Доля этой работы в packed finish и устранение
partial timeout пока не доказаны. Кандидат с двумя источниками и отдельными
проверками отказов описан в plan/research/quickstart для независимого review;
код приложения до нового GO не изменяется.


## Причинный RED двух источников — 2026-11-03

На прежнем production reader `50622e2a4468bf41a1246a6a692af88e08803ebbdd2f6fd218329a971ae453ec`
assert `two_active_readers_must_not_reload_warmed_blocks` завершил настоящий
Debug ProtectedCustodyFilesTests с CTest8/Failed за259.541s, без Timeout.
Восемь прогретых пар действительно потребовали32 дополнительных вызова
ReadFile-обёртки; проверки Seek и байтов77/42 перед assert прошли.
Это подтверждает вытеснение кэша, но не доказывает его долю в packed finish.
Следующие части suite намеренно не исполнены; wrapper0 означает qualified
expected RED, не product PASS.

Stage `t116-cache-red-0m4c1xlm`: terminal-evidence.json
`ba0509af40542fdc699e6aa7b2a8d030164b7864f6eca2b6e927380640d12f62`;
new Debug PE `2ffebe1d9231fe7ea4f55b55e6c119b931ec816e651f412d863b87f537debd0c`.
Source225 проверен до/после, PE неизменён после теста, installed0.1.0.15
не изменён, own_processes0. Session63431 terminal exit0.
Новый production/test candidate в отдельном stage требует SOURCE review
и нового GREEN; T116/T117/T118 и установленное приложение остаются HOLD.


## Ограниченный двухисточниковый кэш: первый GREEN — 2026-11-03

Production reader теперь сохраняет по одному блоку для двух ReaderState,
не более512KiB plaintext суммарно, под прежним mutex. Собственный state
замещает свой block; новый использует свободную запись, иначе LRU. Ключ
публикуется после успешного optional.emplace существующего CustodyBytes.
reset/destructor возвращают capacity и Debug proxies через wiping allocator;
проверки packed status до/после, ZERO, sticky failure, cursor и prefix wipe
сохранены. Поддерживающие baseline asserts усилены до cold idle0 в пяти
наборах и NativeIntegration. Requirements/research/plan описывают пределы.

До GREEN source review исправил скрытую index entry и два старых WriteStream
proxy allowances. Первый actual v4 build остановился на /WX C4456/C4244 в
новом FilesTests (tail shadowing, int→uint8 fill); CTest не запускался.
Отказ и его квитанции сохранены. V5 меняет только эти три тестовые строки;
предупреждения не подавлены, compiler options неизменны.

Stage `t116-cache-green-v5-zr81wqjp`, session91219 terminal0:
six Debug targets build0; five CTest PASS/0:

| Набор | Секунды |
| --- | ---: |
| ProtectedPackedCustodyOwnerTests | 234.631 |
| ProtectedPackedCustodyTreeTests | 36.706 |
| ProtectedCustodyFilesTests | 315.742 |
| ProtectedCustodyWriteStreamTests | 3.78925 |
| ProtectedRecoveryPlaybackPartial | 171.89 |

Фактические markers: cache alternation8 пар additional_native_reads0;
cold-cache-close в составе FilesTests два pressure close и cleanup0;
partial — полный COLD_PARTIAL_RECOVERED, child_exit88, immutable_old_extent1,
readonly_unchanged1. Partial6000 frames/60000ms, child60s и CTest180s прежние.
Phase timestamps ms: baseline prepare8750→8797, finish8797→65922;
partial prepare105328→105453, finish105453→154703;
cold inspect154844→164406; privacy171750; readonly/idle171781.
Это один PASS с запасом около8.1s; стабильный performance margin не доказан.
Baseline finish не ускорился относительно предыдущего прогона, поэтому
не приписывать весь итоговый выигрыш только новому cache или всей VM.

Terminal evidence SHA256:
`8b01b9bb4ee5b8dbdd7bf5872f9c5b04942f026733f01e58f4f90d0d1996863a`.
Source225 совпал до/после, все6 PE после тестов неизменны, установленный
GRAF0.1.0.15 не изменён (hash baseline до build), own_processes0.
Нет микрофона, настоящего network или установки. Отдельный genuinely-cold
CLI и57 оставшихся cases той же matrix62 ещё обязательны. T116/T117/T118,
полная Windows/installed/hardware/release acceptance остаются открыты.


## Remaining57: terminal отказ native scheduler resume — 2026-11-03

Stage `t116-cache-remaining-ymgmcx_l`, session73168 завершился host/wrapper1,
CTest8: 44 PASS, один Failed,12 не запускались из-за stop-on-failure.
Отдельный genuinely-cold CLI exit0: две pressure closures, cleanup_owned0.
NativeProtectedSchedulerResume завершился за180.44s на внутреннем assert
deadline, строка7009 NativeCaptureStorageIntegrationTests.cpp; CTest240s
не сработал и не изменялся. Искусственные14000 кадров записаны на94151ms;
на deadline controller finalizing, acquisition_dispatch_done1/both_eos1,
storage command3/in_flight1, recording finalizing1/terminal0. Это отказ
до cold-read/upload/resume assertions, не подтверждённая ошибка сетевого retry.

Terminal evidence SHA256:
`51e9958f0cd1fc0943f285adf43aeee55758d8067a78475d930a4d342b3eb176`.
225 source до/после,6PE unchanged, installed0.1.0.15 EXE unchanged, own0;
нет forced cleanup/audio/network/установки. Union с прежними5 —49 PASS,
один Failed и12 unrun, не62/62. Причина задержки пока не установлена.

Следующий bounded диагностический шаг — переиспользовать четыре существующих
finalize phase observers в этом же generated-data native worker: entry/exit,
время и returned/unwound, сохраняя GetLastError. Только test executable;
предел180/CTest240,14000frames, семантические assertions, source/PE/installed
guards неизменны. Метки должны показать активную фазу при отказе; сами по себе
не доказывают причину и не разрешают ослаблять проверки целостности.


## Read-only сверка остатка T116

Независимая сверка текущего кода не подтвердила старые P1–P3 как
отсутствующие production consumers: manual claim, interrupted recovery и
public Record имеют реальные protected worker/owner вызовы. Это source
инвентаризация, не runtime/installed acceptance и не закрытие T116.

Отдельно от нынешнего performance отказа quickstart §native startup требует
настоящую смерть процесса и cold restart на семи группах границ:

1. Start reservation: до queue index rename, после rename до readback,
   после readback до adoption, после adoption до factory.
2. Package birth: до первого package-state index, между slots, после BOTH
   до canonical birth; canonical singleton/BOTH различаются.
3. Canonical checkpoint: DATA/NODE до HEAD и настоящая новая HEAD до ACK.
4. Stop/EOS: до Stop и после drain до первого finalization publication.
5. Terminal package seal: до/после sealedNormal либо discardPending,
   до inspect/queue update.
6. Finish queue: rename/readback/adoption для normal reservation update
   и short row retirement; это иной oracle, чем Start reservation.
7. Short physical discard: после retirement до recycle, после actual effect
   до postflight, после postflight до UI notice. Нового removed ACK record нет.

Смежные физически одинаковые точки не дублируются как разные cold outcomes,
но readback/adoption/lifecycle события должны быть реально достигнуты.
Нынешние native tests проверяют in-process hold/cancellation/ambiguous и
release/reopen, а существующий V5 child harness — recovery уже созданного
пакета. Ни то ни другое само по себе не заменяет перечисленные child cuts.
Переиспользовать existing native file wrappers, qualified NtSetInformationFile,
TestPeer и V5 child TerminateProcess88 pattern; точное role/slot/event,
missing-event89/timeout всегда failure, никаких user data/device/network.
Новый production fix нужен только при конкретном RED, а не по этой карте.
T117 остаётся отдельной migration engine работой; неизвестный реальный
quarantine сохраняется. Исторический BOM artifact без отпечатка текущего файла
не является основанием классификации/удаления.


## Native finalize phases: terminal повторный отказ

Stage `t116-native-finalize-phase-yum6p3di`, session92815: Debug Native build0,
existing profile CLI0/selfcheck8 сочетаний/idle memory PASS. Сам длинный
NativeProtectedSchedulerResume снова Failed180.487s по внутреннему общему
deadline, теперь7025; CTest240 неизменён.14000 кадров достигнуты на95217ms.

| Наблюдаемый span | Результат | Время |
| --- | --- | ---: |
| Canonical seal / phase0 | returned1, unwind0 |4.046339s|
| WAV / phase1 | returned1, unwind0 |9.887855s|
| AAC / phase2 | returned1, unwind0 |53.071825s|
| Protected inspection / phase3 | enter, нет exit до assert |не измерен полностью|

Returned означает обычный возврат, не отдельный success oracle. Сумма
закрытых фаз67.006019s не является всем finalize: между ними есть metadata
publication и до/после — работа owner. Последняя активная фаза локализует
отказ, но не доказывает deadlock, API/диск/VM/cache причину.140s фикстура,
семантика и проверки целостности не сокращены. Counter profile отдельного
1000-frame CLI не переносится на async finalizer длинного case.

Terminal SHA256:
`637eb4c1a82ff18724871e214364ee97fb4d2941bd9b4bb40d4408bf17c33084`;
Native PE `eac9d997aeedcb4ce7c7caf7e479cdee328a53a687fbf274db47cf6ad8cfc53b`.
225 source до/после,6 post-buildPE unchanged, installed0.1.0.15 unchanged,
own0; нет forced cleanup/audio/network/install. Это подтверждённая
диагностика отказа, не fix/PASS/T116 completion.

Перед изменением production проверить реальные callers/границы повторных
проверок и native кодировщика. Не отключать backpressure, не менять MF sample
cadence/кэш/budgets либо native pre/post guards по одной временной метке.


## Writer admission: actual test-first RED

Stage `t116-writer-ready-candidate-pc6nqypk/red`, session55946: Debug Owner
build0, actual existing --packed-writer-admission exit3 с новым budget assert
на629, без Timeout. Writer остался
`a0fe79760d101b4aec8e72f311bd3972dd5c88266f217e6cb973b159a2255a0a`.
Нативный FindFirstStreamW hook измерил один ready pass12 queries; warmed
overwrite36 (3passes), grow48 (4passes). До assert прошли exact pending bytes,
настоящий checkpoint и чтение committed snapshot. Это metadata calls,
не физические disk reads и не доказанная доля полной ingest latency.

Wrapper/host0 квалифицирует ожидаемый RED, не PASS Owner suite: последующие
post-fault/SetSize cases не исполнялись. Terminal receipt SHA256
`386fb34bea2ddb94470ef9809e7c39ba13180ce67e4415973c8308d2b288fb85`;
Owner PE `3b29a5df88462c92af554202345fc13a718632d7a18d1a38283e4bb8205b1158`.
225 до/после,6PE unchanged, installed0.1.0.15 unchanged, own0, no forced
cleanup/audio/network/install. Production candidate ещё не применён.

GREEN candidate усиливает existing first-fault SetSize oracle: счётчик writes
снят до denied и сверяется после, дополнительно к прежнему sticky-checkpoint.
Новый test SHA52b8509e0d6901c1fcace609245b1eeeb217e49344b904b41646884a598aded9;
квалифицирующий RED prefix не меняется. После independent SOURCE gate
сначала admission/cancellation/real MF, профиль и original resume; четыре
широких набора только если focused путь прошёл, на тех же225/sixPE.


## Writer admission: GREEN terminal, шесть текущих наборов

Stage `t116-writer-ready-candidate-pc6nqypk/green`, session93431: actual host0,
wrapper0, шесть Debug targets build0. Source delta ровно Writer
`99e9185a34b70ecb9e6ea013e1a99009abc2f4672b191f319ef26e504c4e22df`
и OwnerTests `52b8509e0d6901c1fcace609245b1eeeb217e49344b904b41646884a598aded9`.
Убраны повторные ready на первом chunk и private resize; public entry,
следующие chunks, final byte ACK и nested actual IO guards сохранены.

Admission CLI0: native metadata overwrite24/grow24 при calibrated guard12,
вместо RED36/48. Exact pending/committed bytes, no IO на warmed write,
post-fault sticky/no-byte-ACK/no-IO marker, прежние21 first-fault combinations
прошли. Cancellation CLI0 и profile1000/selfcheck8/idle-memory0 прошли.

| Текущий CTest | Результат | Время, с |
| --- | --- | ---: |
| ProtectedCustodyWriteStreamTests | PASS |3.11154|
| NativeProtectedSchedulerResume | PASS |235.361|
| ProtectedPackedCustodyOwnerTests | PASS |231.530|
| ProtectedPackedCustodyTreeTests | PASS |35.8854|
| ProtectedCustodyFilesTests | PASS |302.928|
| V5LocalRecordingWriterTests | PASS |105.267|

Native original14000/shared inner180/CTest240 неизменён; пройдены actual
partial ACK, failed-result adoption, cold suffix4194304, retry и server-truth
continuation без повторной отправки принятого префикса. Phases0–3 вернулись
за4.071935/9.088517/41.318510/17.933925s. Это72.412887s covered spans, не вся
finalization. Whole-case запас4.639s до240 — один PASS, не стабильная
производительность. Отдельный короткий append3.095730s против прежних5.000769s
на том же diagnostic fixture — единичное сравнение, не доказательство всей
причины задержек или устойчивого выигрыша.

225 source pre/post, все6 post-build PE unchanged, installed0.1.0.15 EXE
unchanged, own0/no forced cleanup. Native PE
`2d2df479690a6622c61616e0951965ec5e9dfa307e35b99865d20aa6c04efcc1`;
terminal receipt SHA256
`3b6bb027f6fd6a77c63c7213121742307bddde1bd4cec6fb0319120ca72abe0c`.
Независимый terminal review запрошен; это6/62 текущих CTest names плюс
3 CLI/profile, не полный62 и не T116 completion. ProtectedRecoveryPlaybackPartial
6000/180 и остальные56 требуют текущего PE повторения; старые результаты
не переносятся на новый Writer автоматически. Обычный GRAF не обновлялся;
T117 migration и вся installed/hardware/release приёмка остаются открытыми.

Независимый terminal review принят: собственный review report §GREEN terminal
со735, SHA `7e82f08998ae8b5c82ec2989166d1191d59d2a621d590dbe7b1d724c320406c3`.
Проверены32/32 terminal file pins, три JUnit sections, actual native resume
markers и current225. Разрешён remaining56 без rebuild/copy на тех же6 PE;
execution HOLD снят только для этого шага. Stage
`t116-writer-ready-remaining-_gwfhneq`, Run SHA
`860fa705b161ece9e584fa99fc2817ba623ed00d2bb07ad787a522793268209c`,
PS parser PASS, host session80464 начат с настоящим12000s host deadline.
Это запущенная проверка; её terminal результат пока отсутствует.


## Read-only подготовка следующей зависимости T117

Независимая сверка Lorentz подтвердила отсутствие runtime migration engine;
ни checkout, ни VM/рабочие данные в рамках сверки не менялись. Это подготовка,
не начало исполнения T117 до T116 и не новая редакция contract/tasks.

Есть строгие migration/bootstrap codecs, BOTH-pair/historical birth readers,
native path/handle guards, protected writer/checkpoint/readback и чистый
ProtectedUploadQueueValue::decode в DesktopUploadQueueService.cpp. Не готова
следующая полная последовательность под непрерывным exclusive lease:

1. Bounded fixed-name legacy source handle, identity/length/EOF/SHA/stamp;
   повторная source validation до copy/switch. load() не использовать:
   он может quarantine/rewrite и менять domain rows. sha256File() без lease
   также не заменяет confined source proof.
2. Reserve тех же identities без пустой очереди; prepared intent g1 BOTH,
   prepared g2 с historical birth ref; затем закрывающий bootstrap ACK.
   lockStoreRoot сейчас требует virgin inventory; обычный StoreOwner birth
   создаёт empty queue, оба входа не являются migration. Internal commitImpl
   с held Files может стать связью reserved id.bin и первой записи.
3. Exact bytes copy queue/manifest/recovery flat и media packed в заранее
   reserved IDs; cold whole length/hash и metadata-pair/packed proof;
   copied_verified. Обычный createPackage создаёт новый directory и требует
   regular owner, поэтому не заменяет переход существующего package.
4. Durable old-reader gate до rename, fixed legacy.originals, exact ciphertext
   sentinel/readback; проверить historical barrier copies и roots до GC.
   Неизвестный реальный quarantine сохраняет blocking semantics.
5. Switch + restart reconciliation всей contract table, включая cut authority
   switched/intent ещё copied_verified. Проверенный handoff должен учитывать
   обе bootstrap slots и intent/original/sentinel inventory: сейчас regular
   validate отвергает migrating любую slot и migration histories. Не просто
   whitelist имён. Исторический receipt не замораживает последующие current
   queue generations/hashes.
6. Fresh cleanup authorization, native identities/pins/conflicts, actual
   absence и durable complete; без неё originals сохраняются. Retirement
   должен убрать regular legacy inspect/hash/upload/playback, а не толькоload.

Первый generated RED после T116 обязан проверить весь positive путь:
непустой legacy ledger + makeGeneratedLegacyPackage → реальный NativeCapture
startup → queue+package migration/switch → release → cold regular owner и
inspectProtected с exact bytes/ranges/owner/deletion/purge → одна обычная
queue mutation → ещё один cold open. Original hashes сохраняются, старые
readers закрыты, devices/real network0. Сегодня opened будет RED на legacy
inventory. Один closing fence не является исправлением или handoff.

Contract §8 hard stop2026-11-01 уже прошёл: незавершённый переход блокирует
публикацию, не разрешает plaintext fallback или удаление originals. Полная
interruption/cleanup/retirement матрица и T118 остаются отдельными условиями.


## Writer remaining56: terminal FAIL, отдельные44 PASS

Host session80464 завершилась: host1 / CTest8. Из запрошенных56 выполнены45:
44 PASS, NativeProtectedLargeUploadParts TIMEOUT240.077s,11 UNRUN из-за
stop-on-failure. Это не полный62 PASS. В том же source225/sixPE ранее
прошли6; вместе подтверждены50 PASS,1 FAIL,11 UNRUN.

Large fixture52500 frames/525000ms дошёл до finalize на174537ms;
finalize_returned отсутствует. Это не доказательство сбоя HTTP или потери
данных; точная оставшаяся стадия пока неизвестна. Исходный240s не изменён.
Cold-cache-close CLI0/two pressure closes/cleanup0; source225 pre/post,
sixPE и installed0.1.0.15 EXE unchanged; own0, forced cleanup нет.
Terminal SHA256
`080e4c640f07ebebcab907ed5f1ed8c323678c0376a121ba56f877e4b40a35da`.
Новый Start crash donor не применён; текущая source/PE основа сохраняется
для отдельных11 unrun. Производительность большого пакета и T116 остаются
открытыми независимо от последующего результата11.


## Writer last11: terminal PASS на прежних225/sixPE

Host session7081 завершилась0 при настоящем4200s host cap; CTest0, exact11
ранее UNRUN прошли без skip/error/failure. AccountProblems0.490s, DisplayTiming2.752s,
DisplayOwnerQuota0.856s, MetadataReadAdmission0.726s, OwnerCancellation0.866s,
ReaderReleaseDrain0.514s, MediaEngine7.979s, PlaybackConsumer10.165s,
PlaybackBatches20.063s, PackageRevalidation26.690s, LiveBornInspection10.722s.
Cold CLI0/two pressure closes/cleanup0, current225 pre/post,6PE unchanged,
installed0.1.0.15 EXE unchanged, own0/no forced cleanup. Terminal SHA256
`c395ceae7c24cbdd7cf25c7c06514b698522053502594755ce4bf2e20d75f444`.

Три отдельных запуска6+44+11 дают61 PASS на одной source/PE основе;
LargeUploadParts сохраняет отдельный Timeout240.077, поэтому это НЕ62 PASS.
Readonly tracing Lorentz:240 — общий унаследованный CTest cap, не найденный
SC-бюджет всей finalization. Исторический Release diagnostic509979ms
(validation-2026-10-02.md:32430) другой source/PE, не переносится как current
proof. Следующая диагностика повторит полные52500 frames и оба exact-wire
oracle через existing CLI с конечным900s cap; исходный CTest240 не меняется.
Цель — раздельно увидеть append/four finalize phases/cold reads/inspect/
два multipart прогона, не удалить guards ради тестового времени.


## Actual Start process death и полный large-parts diagnostic

Stage`t116-start-crash-large-phase`, Native test-only SHA
`bb9b2728cc46a66168c3345c49f8569a3d4cb2c2ceed69e568ca165fec23cb58`.
SOURCE/checklist/analyze принят независимым reviewer перед apply; production
и CMake не менялись. Actual Debug MSVC build0; malformed child CLI89.
Три исходных CTest PASS: StartOwner11.8702s, PendingStart79.7597s,
ShortDiscard85.604s. Parent действительно получил child exit88 после
успешного native queue rename до commit/readback возврата; первый cold owner
прочитал g2/exact reservation, package отсутствовал, snapshots unchanged и
owned baseline восстановлен. Это signed-out cut, не power-loss/A→B/all cuts.

Existing Large CLI завершился0 при конечном900s diagnostic guard; весь путь
через cleanup646632ms. Append закончился173909ms, finalize вернулся489346ms
с normal1/error0/storage0/native0. Его315437ms включают четыре disjoint spans:
canonical seal15.497877s, WAV33.938540s, AAC151.480109s, inspection66.238823s.
Оставшиеся около48.3s не покрыты этими spans; их нельзя приписать MF/crypto.
Cold pair46ms, read_expected71897ms, independent inspect66563ms, wire4MiB9499ms,
wire16MiB9204ms, cleanup71ms. Все четыре enter/returned, без unwound.

Прежние52500frames/525000ms/media16800044 сохранены. Actual wire oracle:
4MiB — четыре полных media parts+tail22828;16MiB — один полный+tail22828.
Exact bytes/offset/index/SHA/accepted/final truth/body lifetime и idle memory
assert прошли. Прежний CTest240 остаётся отдельным FAIL; CLI не является
его PASS, SC-003 timing или полным T116. Это обоснование отдельного
пересмотра общего harness cap, не удаления guards ради старого cap.

Actual TEMP/TMP с кириллицей и пробелом подтверждены UTF16 codepoints и
encoding-runtime.json, а не только parser. Pre/post225,6PE unchanged после
build, все5 unrelated PE равны предыдущим; installed0.1.0.15 EXE unchanged,
own0/no forced cleanup. Native PE
`ac9d2ef86ff73a9b3cc8c9e406d438afcc42901f62aea1287c6c6449e0931394`.
Terminal receipt SHA
`997f5d144cab89b94646c3884e57dd6dececd24b6dd1ba09842523f01e8377ca`.
Независимое terminal review запрошено. Прежние61 PASS относятся к старому
Native PE; новая three-case/CLI проверка не переаттестует его полный набор.

## 2026-11-04 — три Start cuts и новый actual Large CTest

Stage `t116-start-three-cuts-large-ctest`, host95435 завершён0 с настоящим
3600s host cap. Actual Debug MSVC build0; malformed path/mode CLI89/89.
Native source `7ac27ac3efa639ac7dd81f7d2e22fbb03b6872c3d67c8aeb49e5645915715e14`,
CMake `58b607bf5262b646b975200657601b80b0e6572ac5887bb3cd73e18494d2e53a`.
Native PE `8adafca5d74771173d2e8e0d5d8a03a2f779a0b72dad86fc34bf63f7ae1ad410`.

StartOwner CTest PASS12.6275s: три отдельных child завершились88 до rename,
после успешного native rename и после commit/readback до adoption. Первый
cold owner прочитал соответственно queue g1/0rows, g2/1row, g2/1row; exact
signed-out reservation/IDs, отсутствие package, unchanged snapshots и возврат
owned memory подтверждены. Это process death, не power loss или account A→B.

Сверка generated CTest configuration110 cases подтвердила единственный delta:
Large TIMEOUT240→900; commands, RUN_SERIAL и прочие properties равны.48
непостроенных catalog entries не запускались. Actual Large CTest PASS664.723s,
полные52500frames/525000ms и два exact-wire oracle сохранены: media16800044,
4MiB/full4/tail22828 и16MiB/full1/tail22828. Все четыре finalize spans вернулись
без unwind:15.389826/34.294927/146.910630/66.110633s. normal/error/storage/native,
byte/SHA/range/accepted/final truth/body lifetime и idle assertions прошли.
Прежний240s FAIL и отдельный646632ms CLI diagnostic сохранены отдельно.

Actual Unicode TEMP/TMP и UTF16 codepoints подтверждены;225 source inputs
до/после равны,6 PE после build неизменны,5 unrelated PE равны предыдущим.
Installed GRAF0.1.0.15 EXE неизменён; own processes0, forced cleanup отсутствует.
Terminal receipt SHA256
`a3218bbf2f5f9c464bd19b18593e876b8bfe2bbab0d0a6287d03dcda59104e96`.
Независимое terminal review запрошено. Это2 текущих CTest PASS, не full62,
не product performance/SC-003, не закрытие T116/T117/T118 или installed acceptance.

## 2026-11-04 — seven-cut build PASS, snapshot helper FAIL

Независимый SOURCE/checklist/analyze GO в reviewer report §Seven Start cuts.
Применены ровно три рассмотренных файла;225 совпали с manifest
`ee915b02df8af4312b0e11182c809103c3211a0a9aca337acaef1b32ded3ef36`.
Stage `t116-start-seven-cuts`, host14666 завершился1; MSVC Native+V5 build0.
Start CTest8/FAIL1.81478s: первые четыре child exit88 и cold queue proofs
пройдены. Пятый package-before-index0 child тоже завершился88, но parent
остановился на `snapshot` SHA-size assert до cold package read. V5 UNRUN.
Все225/6postbuildPE/installed EXE unchanged, own0/no forced cleanup. Из-за
exit1 runtime UTF16 receipt не создан; его PASS для этого запуска не заявлен.
Failed terminal SHA
`7968192b69cb3e8f70d9567f9317229d1d6c305cdef5a4fe9d98057b87cef9b6`.

Отдельная bounded диагностика только generated fixture подтвердила MAX_PATH
в test snapshot helper: тот же374-byte orphan index.tmp при ordinary265
UTF16 units не открывается (DirectoryNotFoundException), с Win32 extended
prefix269 units читается с SHA64. Остальные18 файлов, включая progress, доступны;
это не доказательство product hash/storage fault. Production native layer
уже создаёт длинные temporary через extended path. Candidate меняет только
snapshot helper: сохраняет все файлы, SHA64 assert и relative keys, добавляет
prefix для длинного local generated path; Unicode fixture не сокращается.
Новый SOURCE/runner review и повторный actual CTest ещё требуются.

После независимого GO применён только snapshot donor2fee. Stage
`t116-start-seven-cuts-snapshot-fix`, host53499 завершился1; build0, Native
CTest8/FAIL1.94991s, V5 UNRUN. SHA assert больше не срабатывает: пятый child88
и следующий parent cold/read-only path пройдены до Fixture destructor.
Там сработал сохранённый `remove_all` error assert1034: normal namespace
не удаляет оставшийся длинный temporary. Отдельного пятого cold/released
marker нет, released PASS не заявлен.225/6PE/installed unchanged, own0,
forced cleanup отсутствует; runtime UTF16 receipt вновь отсутствует.
Failed terminal SHA
`5cd0b6174e8c74e29e8c5a4961f5449398a61786b39bb9a872632b151aa050d6`.
Следующий candidate ограничен generated Fixture destructor: тот же точный
созданный parent и error assert, но extended path для cleanup. Никакого
удаления рабочих данных, игнорирования ошибок или сокращения fixture.

После независимого cleanup GO применён только Native donor0e3826.
Stage `t116-start-seven-cuts-snapshot-cleanup`, host73990: build0,
Start CTest PASS14.3234s. Все семь child88/cold queue/package/read-only/
released markers подтверждены, включая before index0, between indices и
BOTH semantic ACK before canonical birth. Неполные metadata pairs отвергнуты;
после BOTH прочитаны обе g1 capturing slots, canonical content отсутствует.
Native PE `9bc231dd3383c579bdd41f3d3919f3316410c7592c16e036f501c14ea1e61057`.

Следующий V5 CTest FAIL27.9059s/exit8: первый recovery child вернулся3
до записи child progress; у родителя остался только parent_launch. Это
не process-death88 и не PASS recovery matrix. Все225/6PE/installed unchanged,
own0; success-only runtime UTF16 receipt отсутствует. Partial terminal SHA
`6d3799d5e77e093dfc04900f596a6691ca8e6cc1f193a9e970d2ed2745ef1ff4`.
В старом V5 test CLI root берётся из narrow argv[2], хотя CreateProcessW
передаёт Unicode. Следующий узкий candidate повторяет существующий Native
CommandLineToArgvW/LocalFree pattern, без изменения recovery/events/fixtures/
deadlines. Его SOURCE review и actual повторный V5 CTest ещё требуются;
новый Native PASS не превращает весь запуск в успешный.

Независимая квалификация уточняет формулировку partial receipt `beforeentry`:
доказано отсутствие первого child progress marker, а не отсутствие входа
в main/coldCrashChild. Точный assert ребёнка не попал в журнал. Narrow path
decoder содержит отдельный конкретный дефект Unicode fidelity; причина
наблюдённого child exit3 окончательно связывается с ним только повторным
запуском при единственном рассмотренном изменении.


## 2026-11-04 — Unicode CLI: V5 CTest PASS

После независимого SOURCE/runner GO применено единственное изменение V5 test
CLI: `CommandLineToArgvW` вместо narrow argv для Unicode root. Production-код,
24 recovery events, размеры фикстур, их длина пути и пределы времени прежние.
Stage `t116-start-seven-cuts-unicode-cli-test`: host0, MSVC build0,
`V5LocalRecordingWriterTests` PASS101.695s. Журнал подтверждает все24 recovery
process-death cuts, child failures отсутствуют. Получено отдельное фактическое
подтверждение Unicode TEMP/TMP и точных UTF16 codepoints.

Новый V5 EXE `e7f888bd65063d25b607b0306c1d9fac31a3c6f3319cdbf2624128ed8f5b8b3c`.
Остальные5 EXE не менялись, в том числе ранее принятый Native seven-cut
`9bc231dd3383c579bdd41f3d3919f3316410c7592c16e036f501c14ea1e61057`.
Все225 source files совпали до/после, все6 postbuild EXE неизменны после теста,
каталог110 CTest commands/properties прежний, installed GRAF0.1.0.15 unchanged,
own processes0/no forced cleanup. Terminal SHA
`4479d00cd9fc03cb352b7549cc8e9be7ba74ff77cadfd335e61e60cd4abc3d10`.

Сохранённый partial receipt73990 остаётся NativePASS/V5FAIL; новый успешный
повтор при единственном исправлении декодирования подтверждает устранение
наблюдённого сбоя Unicode CLI. Точные внутренние причины старого child exit3
отдельно не трассировались. Это не новый запуск Native, не полные62 current
теста, не закрытие T116 или приёмка установленного приложения.


## 2026-11-04 — Native lifecycle, исходник и границы проверки

Независимый SOURCE/checklist/analyze GO рассмотрел четыре actual process-death
границы внутри existing FinalizeAdmission: после Stop/двух EOS до seal;
перед native queue index0 rename g2→g3; после commit/readback до adoption;
после принятого retirement и реального recycle/absence до возврата владельцу.
Используется прежняя100-frame фикстура и interruption для первых трёх,
userRequested для short. Это не укороченная large/SC-003 проверка.

Перед сборкой Main нашёл outer first/inner first shadow при /W4 /WX;
донор6ef не применялся/не собирался. Независимо принята замена только двух
имён loop bounds, итоговый Native test
`b0a289743bb58fa3a94a210e642052961edf7606c5ca0d55afde8fd5a0356295`.
Применён только этот файл. Stage `t116-native-lifecycle-four-cuts`,
manifest225 `29282369bfaf58b1615b5e2049867f38ca6160200ac46eb8b276e649a05a9dca`,
Run `eeae6ae890bf80a0daa63e4cca070e224e809a751032d1ff3668cfca5e84b22c`.

Значимая история short/problem уведомлений заполняется до quiet guard,
поэтому history.empty проверяет отсутствие ранней попытки такого уведомления.
Сам presentation counter в quiet недостаточен; finalizing indicator отдельно
исключает savedLocal в выбранной точке. Визуальная приёмка карточек этим не
заменяется. Новый fixture prefix на7 символов короче прежнего Unicode CLI
повтора; нельзя объявлять его повтором того же MAX_PATH stress. Все прежние
длинные snapshot/cleanup proofs сохранены отдельно. Пределы CTest не менялись:
Start explicit240; FinalizeAdmission default1800 при внешнем пределе240.


Фактический запуск91436 завершился0: MSVC build0, StartOwner PASS14.8878s
(все7 child88/cold/released), FinalizeAdmission PASS14.7771s (все4 новые
child88/cold/released). После EOS сохранены finalizing g2 и100 полных кадров;
до finish rename очередьg2, после readbackg3; оба normal пакета прошли полную
проверку хешей/session/AAC. После фактического short recycle очередьg3/0rows,
пакет отсутствует. Холодные открытия не меняют файлы; ресурсы возвращены.

Native EXE `ca962da8b6fe4724aac7ad203b300aa56a662f5cd195a1c9a25916b61fa58587`.
Все225 source/6postbuildPE/installed unchanged, остальные5PE не пересобраны,
110 CTest commands/properties unchanged, own0/no forced cleanup, Unicode
TEMP/TMP/codepoints подтверждены отдельным runtime receipt. Terminal SHA
`aee2503f2b26b055b8b186a373a26957b9bc1e3dcc52adc2ec4b6c1337fea676`.
Это generated-data process-death proof; power-loss, Stop-before-EOS,
initial canonical DATA/NODE/HEAD и захваченный AccountA→B не утверждаются.
Полная текущая матрица и T116/T117/T118/installed приёмка остаются открытыми.


## 2026-11-04 — первоначальные canonical DATA/NODE/HEAD, исходник

Подготовлен отдельный test-only донор трёх process-death границ первоначальной
записи canonical, а не восстановления ранее checkpointed файла. Реальный V5
writer создаёт пакет и начинает137-й кадр. Граница квалифицирует typed DATA,
полный путь NODE L0/L1/L2 и HEAD generation2/262144 bytes, включая split native
writes. До HEAD cold stream должен быть пустым; после полного HEAD write,
но до flush/readback/byte ACK, ожидаются136 полных480-frame блоков и1024-byte
остаток, который не дополняется до кадра. Это не power-loss durability proof.

Независимый review нашёл неверный cold queue oracle1: reservation commit от
base1 публикует generation2. Доноры470/88 не применялись и не собирались.
Однострочное исправление принятого oracle рассмотрено отдельно, итоговый
V5 test `6c1137af32bf240b7518411ce16a6a394707cd9a0c1e294055c2ab7a1e1cb7a4`.
Один вызов добавлен перед прежним default coldPlayablePrefix, поэтому новые
три случая выполняются обычным V5 CTest без отдельного CMake entry. Прежние
24 recovery cuts и старый execution tail сохранены; production не меняется.

Stage `t116-initial-canonical-three-cut-test`, manifest225
`8ef1a73510b93565ae27a665f8ba65235ea38bfa3b5c131d84bbd3f963a1a518`,
Run `d1d5cc599018529666e7f9b2985bbc5d9eb5510f92fa1d4f52c14afd8451a974`.
Применён только V5 test после SOURCE/checklist/analyze/runner GO C0/H0.
Ожидаются полное сравнение bytes/finite samples обоих cold streams, exact EOF,
BOTH metadata/queue IDs, неизменность ciphertext snapshot и возврат ресурсов.


Фактический запуск19129: host0/build0, whole V5 CTest PASS103.227s.
Три новые actual-death границы прошли с cold completeFrames0/0/136;
точные bytes/finite samples обоих readers/EOF, BOTH/queue IDs, неизменные
raw snapshots и baseline ресурсов подтверждены. Прежние24 recovery cuts
выполнены полностью, actual88/canonical+queue unchanged, cold sealed decode
пройден; failed-child markers отсутствуют.

Новый V5 EXE `d4e5b6b1bfa3ed667e35bfba9409416fcb50092a8bffaf5509a869c52a261715`.
Остальные5PE, включая Nativeca962d, не пересобраны.225 source/6postbuildPE/
installed GRAF0.1.0.15 unchanged, config110 commands/properties unchanged,
own0/no forced cleanup, фактические Unicode TEMP/TMP/codepoints подтверждены.
Terminal SHA `64c38cbfbdfa6690be0bb7f6286ef2c138282ba890b22bbf41d931805e43aa7e`.
Это процессный сбой до ACK, не потеря питания до flush и не полная текущая
Debug/Release матрица; T116/T117/T118/installed приёмка остаются открытыми.


## 2026-11-04 — свежая сверка master перед интеграцией

`git fetch origin master --no-tags` завершился успешно. Актуальный
origin/master `e00ffe326d9648732212a065177e6c660b366852`, последние изменения
F140 billing; это тот же ранее просмотренный master. Ветка остаётся70ahead/
371behind от текущего HEAD. Incoming diff от merge-base не меняет apps/windows,
но затрагивает общий cabinet (в том числе rendering.py/cabinet.js/CSS).
Fetch не менял рабочие файлы;352 dirty entries сохранены. Это свежая проверка
состояния remote, не merge/sync или развёртывание. Интеграция master должна
сохранить актуальный общий кабинет и платформенные исправления F200.


## 2026-11-04 — полная обычная Release x64 сборка PASS

Stage `t116-current-release-compile`: MSBuild `GrafWindows.sln /t:Rebuild`
Release/x64, ограничение600s/host900s. Использованы225 input files manifest8ef1
и прежний проверенный AEC build/provenance ebe9b371. Никаких test forced
includes/compiler environment CL overrides; обычные GrafWindowsCoreTests и
GrafWindowsApp полностью пересобраны. Host0/build0. Свежесть AppMain.obj/EXE
проверена относительно начала rebuild, PE machine0x8664, выбранные строки
изолированных test payload в обычном EXE отсутствуют.

Production EXE `a31d43282655d7558ccd92f982dc85957d72d0aaff1d3cc2d01d70287594d1bb`;
AppMain.obj `73049a866d336574d9680ced4957972043db59a8a6d9acb883568628c9d55efc`.
225 inputs pre/post unchanged;6 CMake test EXE unchanged; installed0.1.0.15
unchanged; build processes0/no forced cleanup. Terminal SHA
`a19b3bcfac137281470ed91ae18410688847197a85522356ff559fc5a017fdd5`.
В build log два прежних SDK warningD9025 (/W1→/W4) и два сторонних WebRTC
warningC4100; собственных source warnings/errors не найдено. Это не zero-warning
сборка, не запуск core tests, не MSIX/signature/install/runtime/release acceptance.
Запуск/запись/операции изменения доверия не выполнялись.


## 2026-11-04 — Stop до обработки EOS: actual PASS

После независимого SOURCE/runner GO C0/H0 применён только Native test2869.
Stage `t116-stop-before-eos-check`, manifest225
`297991683aad65ff57b8d3ae459ae2c0df724c86388425da92e1b4a1aaeef13b`.
Существующий wrapper сначала выполняет настоящий FileIdInfo, затем удерживает
точный canonical handle на dispatcher при writtenFrames99. Stop(interruption)
реально принят, admission закрыт, два различных EOS стоят в очереди, ни один
не обработан, finalizer/phase0 ещё не запускались. Удержание остаётся до
настоящего TerminateProcess88; missing event не считается успехом.

Host53142/build0: StartOwner PASS15.3415s (7 прежних child88),
FinalizeAdmission PASS15.7096s (4 прежних плюс новый Stop child88).
Cold owner нового случая читает прежние queueg2/one reservation и capturing
packageg1/BOTH. Canonical ciphertext совпал с child before-hold SHA; оба
logical streams имеют0 bytes и точный EOF.99 принятых RAM frames меньше
256KiB checkpoint и не объявляются durable prefix. inspectUnfinished честно
отказал invalidContent/native0; snapshot unchanged, memory/jobs/pins baseline.
source_frames100 — размер фикстуры, не отдельное доказательство доставки
100 batch от каждого producer.

Новый Native EXE `1e7bd649067b2ca136fa4264656ccb2f36c42ce03fdddd629823b293253cfa6f`.
Все225 source/6postbuildPE/installed unchanged; остальные5PE не пересобраны,
config110 commands/properties unchanged, own0/no forced cleanup. Фактический
Unicode TEMP/TMP/codepoint receipt PASS. Terminal SHA
`eba0585fc0ef4ff5718e8c1b6d8314d793f49c0e90255ed168e8411eb896acd9`.
Это generated process-death proof, не physical/power-loss/wholeT116 acceptance.


Свежий обычный Release `GrafWindowsCoreTests.exe` также реально выполнен
отдельно, stage `t116-current-release-core-run`: host0/test0, активные asserts
сохранены исходным `#undef NDEBUG` перед cassert. Проверяются session/readiness,
хеширование/atomic store/metadata и strict calendar target decoding; это один
console test process, не новая CTest-матрица. EXE
`8565bc5377cd1fe79577549ee7de28f32929538f117de155beec5bf45e8aafe7`
не изменился;225 inputs pre/post manifest297991 и installed EXE unchanged,
собственный временный каталог удалён, own0. Test stdout/stderr пустые.
Terminal SHA `6db5d3b61b909796c8bf638458e816c110b1f1fa7d9f80c882f194a7b08e13d9`.


## 2026-11-04 — последние три границы завершения: actual PASS

После независимого SOURCE/runner GO C0/H0 применён только Native test
`a173dd64b324dc1eebcb479f01b6354308bd43c309e942e68944723ad51774a7`.
Stage `t116-last-three-lifecycle-check`, frozen225
`f6d6c3bfb593564b3983a02745b855f35a6cdb72177285ac44d40b4e08c6339b`.
Фактически прошли build0/host0, NativeProtectedStartOwner15.3982s
(7 настоящих child88) и NativeProtectedFinalizeAdmission26.6247s
(8 настоящих child88, включая три новых). Исходные 12 случаев сохранены.

Новые случаи: retirement queue readback до adoption; positive short-delete
intent перед входом в OS recycle service; normal finish adoption до доставки
terminal UI. Cold parent подтвердил соответственно queueg3/0rows с
discardPending package, queueg3/0rows с тем же сохранённым package и
queueg3/1original row с sealedNormal package. Проверены BOTH metadata,
UUID/owner/canonical length, полные logical bytes/AAC, неизменность raw
inventory и возврат memory/jobs/pins. В pre-OS случае os_attempts0 означает
отсутствие входа в purge service; owner RAM attempted-флаг уже установлен.
Последний случай подтверждает undelivered native savedLocal при ещё
finalizing UI, не визуальный показ карточки «Сохранено».

Новый Native PE `ae48ab4b2f87b73fdf80326e435e172a43fdd71029adbb7b6573a4fefdba7ec8`;
остальные5 PE неизменны. 225 source/6 postbuildPE/installed0.1.0.15 неизменны;
config110 commands/properties unchanged, own0/no forced cleanup. Сохранены
UTF8 parser и runtime UTF16 TEMP/TMP/codepoints PASS. Terminal SHA
`a32c88463ff17516018eb1a7f5b82528ef804556650f14b386eba73ef2cd1ee8`.
Это ограниченная проверка process death на искусственных данных; без
power-loss/device/network/install/full62/T116 completion. Следующий шаг —
единый исходный набор62 на этих же225 source и6 PE без пересборки.


## 2026-11-04 — cohesive62: runner preflight и actual FAIL сохранены

Первый stage `t116-current-cohesive-62` остановился до тестов по REQUESTED_SET:
PowerShell5 обернул JSON array в ещё один массив. Исправлена только внешняя
обёртка @(); отдельный preflight подтвердил реальные62 строки/type/unique.
Неудачный stage не перезаписан и не считается результатом тестов.

В `t116-current-cohesive-62-r2` реально выполнились лишь три из62 cases:
Owner PASS233.073s, Tree PASS36.4235s, Files FAIL205.864s, stop-on-failure.
Остальные59 не выполнялись. Точный отказ — ProtectedCustodyFilesTests.cpp:3249,
первый valid owner-presence v3 case: standard.load() либо rewrite count не
соответствовали ожиданию. TEMP содержит кириллицу/пробел; это новый
наблюдаемый отказ, а не прежний timeout. Предварительный разбор выявил narrow
filesystem path construction из decoded UTF8 и narrow quarantine/serialization
paths в legacy consumer; причина/исправление требуют отдельной проверки.

Host1/CTest8/TEST_matrix, исходные225 и6PE/installed0.1.0.15 неизменны,
config110 unchanged, own0/no forced cleanup. Runtime UTF16 postproof отсутствует:
runner завершился exit1 до этого шага, его не объявляем PASS. Parser/preflight
receipt сохранён отдельно. Полный62/T116 не принят; переход T117 не начат.


## 2026-11-04 — отдельный logical-queue: тот же отказ до исправления UTF-8

В stage `t116-logical-queue-unicode-red` без пересборки запущен существующий
`ProtectedCustodyFilesTests.exe --logical-queue` с тем же Unicode TEMP/TMP.
Фактический test_exit3/host1, `LOGICAL_CASE_FAILED`; воспроизведён тот же assert3249
на первом корректном owner-presence v3. Это отдельное воспроизведение отказа,
а не успешная приёмка. Исходные225/6PE/installed0.1.0.15 не изменились,
config110 unchanged, own0/no forced cleanup; success-only UTF16 postproof отсутствует.
Terminal SHA `72e23327e685757a679bffb6329749e3f9f00c1bc114978bb850b8cc6780f781`.

После независимого requirements/analyze/SOURCE GO C0/H0 применены ровно четыре
файла исправления UTF-8: legacy queue consumer, Files/V2/Deletion tests.
Новый frozen225 `8a012f484acd5129e79464ebd90711563c748b6c4d97153d848cacd764c20334`.
Изменены только преобразование UTF-8/native path и добавление `.quarantine`
без narrow roundtrip; защищённый CustodyString и валидация не меняются.
Повторная сборка и результат исправленного кода пока не подтверждены.


## 2026-11-04 — исправление UTF-8: сборка и целевые проверки прошли

Stage `t116-queue-unicode-green-r2`: build8/host0/logical0, три CTest PASS:
ProtectedCustodyFilesTests305.434s, DesktopUploadQueueV2Tests3.30376s,
DesktopDeletionLedgerTests0.42916s. Повторены существующие проверки в Unicode
TEMP/TMP без ослабления assertions/лимитов. 225 source и8 postbuildPE неизменны,
installed0.1.0.15 unchanged/own0/no forced cleanup; runtime UTF16 codepoints PASS.
У всех110 CTest неизменны свойства и сроки; только у двух ранее несобранных
QueueV2/Deletion впервые появились точные команды Debug EXE без аргументов.
Это не byte-identical commands и не изменение CMake/условий проверки.
Terminal SHA `0fca52be3a8aa66147fdd5dffc5f6370f65952add003efdfb9ecf2e42f5d5ecf`.

После отдельного bounded runner GO запущен `t116-current-cohesive-62-r3`:
тот же исходный набор62, source2258a012 и exact8PE из целевого успешного запуска,
без пересборки/копирования/установки. Предыдущие отказы сохранены. Пока набор
выполняется, его результат не объявляется PASS и T116/T117 остаются открыты.

## 2026-11-04 — единый текущий набор62 завершился PASS

`t116-current-cohesive-62-r3` завершился host0/CTest0: ровно исходные62
сценария выполнены, все PASS, total3814.87s. Main сверил exact requested set,
JUnit и result; прежние RED/r2 остаются отдельными отказами, не частью этого PASS.
Terminal `b0a2eabaa03701b2e8d8e4f2e94f5a13e5c5f8dda80744713fd9cbf8464e7e83`.
Source225 `8a012f484acd5129e79464ebd90711563c748b6c4d97153d848cacd764c20334`
и восемь PE из целевого GREEN не изменились; predecessor terminal совпадает
с0fca52be… выше. Сохранены configuration110 со всеми командами/свойствами,
original deadlines, installed0.1.0.15 и EXE, own0/no forced cleanup. Runtime
UTF16 TEMP/TMP с кириллицей и пробелом и контрольные суммы launcher подтверждены.

Ключевые времена: Partial152.567/180s; Resume238.116/240s;
LargeUploadParts656.456/900s. Малый запас Resume отражается как ограничение
устойчивости по времени, не устраняется увеличением cap. Весь NativeCapture
default case274.992s использует общий1800s, а не отдельный Resume240.
Выполнены также protected files311.836, writer106.141, privacy manifest211.709,
privacy degraded206.573 и owner232.11s. Это Debug correctness в Parallels,
не принятая производительность записи/Stop, физическая x64 или SC-003.

Источники Windows соответствуют39572 и последующему1aecf44621e2ea4c169525138ea3d9240c04a054:
последний меняет только CI/docs. Новый MSIX не установлен; device audio,
реальная сеть, пользовательские записи и сертификаты не использовались.
Независимая terminal qualification запрошена. Технический набор не закрывает
целиком T116/T117/T118, установленные и аппаратные критерии. Следующий срез
T117 — проверенное обнаружение завершённой истории без transaction в bootstrap;
оно не даёт обычной queue authority, разрешения очистки или обхода карантина.


## 2026-11-04 — T117: воспроизведён отказ чтения завершённой истории

Первый test-only запуск `t117-completed-history-red` остановился на строке1612
при создании index fixture: поколения4/5 не соответствовали slots0/1.
Это ошибка тестовых данных, не продуктовый RED. Отдельный terminal
`fb850eb79e2b74c1e8836cdbc54936afb6a8e9229d291506d5ec4e864428cde6`
сохраняет classification `fixture_setup_failure_not_T117_RED`.

После четырёх числовых поправок (g5/slot0, g6/slot1, selected6, 5+slot)
тот же тест на прежнем production-коде дошёл до целевого положительного
assert1682 и отказал: `t117-completed-history-red-r2`, build0/host0/case3.
Terminal `1d97b37d1e788f2653163a0bd25eadd45063dbc054c5e4db042664b6bab8ac9d`,
source225 `eb7ae8eddac028e74bfa431fe20365dda4736e199885e19c6b38e31f8bb5c140`.
Конфигурация110 byte-identical до/после, прочие7PE и установленный GRAF
не менялись, own0/no forced cleanup; runtimeUTF16 с кириллицей и пробелом PASS.
Независимый bounded verdict C0/H0 подтвердил именно target RED.

Только после этого применён ранее отдельно проверенный SOURCE GO C0/H0
production candidate: ProtectedCustodyMetadata.cpp4b9718d7… и .h5db8fb93… .
BOTH protected/null bootstrap разрешает обнаружить историю ROOT QUEUE:
текущий JSON задаёт лишь ограниченный locator, transaction берётся из отдельно
аутентифицированного immutable Birth. Затем оба current records проходят
строгую проверку, связь с Birth, native queue identity и progression под
непрерывным lease. Новый parser/schema/public API не добавлены.

Запущен `t117-completed-history-green`: source225
`56f62701580049455531059084511d1fa5fc97ce52e7bcf784a9729ee5bf703f`,
wrapper `0b19653e398c0512171c87d54fa8f8364563865b4a3e0bf283fd9e9e20036ad2`.
После одной сборки Files идут существующий --migration-pair и полный CTest
ProtectedCustodyFilesTests, без изменения configuration110 и сроков.
Результат ещё не принят. Этот срез читает только provenance: обычный
StoreOwner, copy/switch/cleanup/GC и все barrier copies не разрешаются.
T117, просроченное исключение old reader и блокировка выпуска остаются открыты.
Рабочие записи, учётная запись, сертификаты и установленный пакет не менялись.


## 2026-11-04 — T117 metadata history: RED → GREEN подтверждён

`t117-completed-history-green` завершился host0/build0/CLI0/fullFiles0.
Полный CTest ProtectedCustodyFilesTests PASS956.16s (CTest total956.19s).
Main terminal `6ef4d600adf74bb1e15eb58c06f21bbae01e3f3eba46856140a77b916829f389`;
предшественник — квалифицированный target RED1d97b37d… на1682, не ошибочный
fixture FAIL1612. Windows source22556f627… неизменен, ровно те же110 CTest
byte-identical до/после. Files PE
`e317d26bf1d0fb9680d559b077a99f0c1569ebd35e0364b7b5e847e5e7bba07f`;
остальные7PE не менялись. После запуска: own0/no forced cleanup,
installed0.1.0.15/EXE unchanged, UTF16 TEMP/TMP с кириллицей и пробелом PASS.

В stderr CLI — ровно16 прежних CUSTODY_BOOTSTRAP_INTENT_NATIVE_ID diagnostic
строк для schema2 × subjects0/1 × faults0..7. actual_error совпадает с expected,
нативные коды соответствуют существующим assertions; чужой текст/assertion
квалификатор не принимает. Пустой stderr не требуется от этих намеренных
отрицательных проверок. Test/runner/prod условия и сроки не ослаблены.

Время заметно больше прежнего311.836s; точная причина различия не установлена.
Метаданные одного измерения гостя: доступно3295MiB из9210MiB, тестовый процесс
работал; это не доказывает причину и не является SC-003. Срок1800s не менялся.
Источник62PASS8a012… остаётся прежним источником, не переименован в56f627… .
Независимая финальная квалификация этого GREEN запрошена. Ни StoreOwner
после migration, ни copy/switch/cleanup engine, ни T117 целиком не закрыты.

Следующий test-only donor обычного cold open остаётся вне репозитория:
реальные generated v5 bytes, очередь после двух последующих commits, все
barrier copies и отдельный retained packed root. До его применения необходимы
проверка подготовки и самостоятельный target RED; готовность приложения
не выводится из этого metadata-only результата.

Независимая финальная квалификация GREEN завершена: scoped GO C0/H0,
225/225 исходников и24 receipt pins сверены; прежний SOURCE GO сохранён.
Разрешён промежуточный checkpoint этого среза, не приёмка всего приложения.


## 2026-11-04 — T088 publisher → Windows, проверенный срез

Включён точный Mac publisher visibleRecordings через существующие document
scripts и private nonce/send в отдельную команду visible_recordings. Native
handler проверяет весь список против текущей полной защищённой проекции,
source/route/detail UUID, nonce/message_id, cookie/HTML identity и native
account/authGeneration. Приоритет только в памяти; навигация/runtime/account/
публикация отзывают его. Серверный publisher и native local_recording сохранены.
Lifecycle worker и внешние квитанции ещё не реализованы: T088 остаётся открытой.

На прежнем мосте фактически получен целевой RED CalendarJoinShimTests:84,
actual0/expected1, после проверки двух точных вызовов настоящего publisher
и отсутствия script errors. После исправления тот же набор прошёл в Chromium
и WebKit, exit0. SOURCE review C0/H0 сохранён. Portable C++ сборка сначала
выявила C++20 starts_with при C++17; заменено только выражение prefix на
substr/equality, независимо проверено. Native test сначала дал2/3: fixture
не восстанавливал два сбрасываемых navigation callbacks. Добавлены ровно
две строки timeReader+inventoryPublisher после новых detail/settings docs,
все guards/oracles сохранены. После исправления три целевых CTest PASS2.27s;
11 соседних CTest (WebView lifecycle/settings/attribution/cabinet/offline/
deletion/calendar) PASS12.35s. Публикация COM моделируется: это portable tests
на Mac, не WinRT parser execution и не установленная Windows-приёмка.

Текущий WebView2Host.cpp SHA256
17eb243401a87d0b195f5ae46da86e7d45459b963cf9fb56de1e4788251b96ef;
CalendarJoinHostTests.cpp
cc1224177ce7b5ea05d17436f190543988667659599cbb9f49db150dc7dfae0d.
Восьмифайловый source/log receipt
69fb1f68f0270838288e5d82e10654422b7aa20b7a6cbd697e2a53bcd2e75f8e.

## 2026-11-04 — T117 ordinary admission: квалифицированный RED

Первый запуск остановился на1522 readers.ok до SETUP_OK: ProtectedInspection
удерживал member streams. Это fixture failure, не продуктовый RED;
terminal37d730e3e38490b09d781e25c5b085109e142c9da668f4f681442478c9056bf2.
Тест теперь освобождает inspection перед следующим readers open, сохраняя
inspection assertion и Pair. Следующая попытка не дошла до сборки из-за
Parallels host255 Invalid argument; отдельный запрос подтвердил отсутствие
build/test процессов и прежний test22bc в VM. Неуспешные журналы сохранены.

Повтор с принятой fixture a88d прошёл подготовку generated v5 package,
queue g2→g4, switched histories и retained root, затем отказал ровно на1738
ordinary StoreOwner::open. Stdout точный:
COMPLETED_HISTORY_SETUP_OK case=0 copy_g=2 current_g=4. host0/build0/CLI3.
Terminal9432c75b32bbb420f14314d62168752ef941873bbd4bf9411683418bc1fb59df.
Source225/configuration110/8PE после запуска и installed0.1.0.15 сохранены,
own0/no forced cleanup/Unicode TEMP+TMP PASS. Production admission candidate
на момент RED ещё не применён; успешного runtime результата пока нет.

## 2026-11-04 — GitHub exact checkpoint

b38eb07c93a10467244fc8a6b6cf5e3373c53b6b отправлен; governance-fast41754394236
PASS. macos-pr41754394218 FAIL: три существующих аудиотеста отказали на
system.isDrained после15s loop. Mac source между предыдущим PASS1aec и b38
не менялся; причина не установлена. Отдельный macos-diagnostic41756369386
выполняется на точном b38 и не заменяет required check. Таймауты не ослаблены.
PR7331 обновлён штатным sync-pr-metadata после successful exact code proof;
описание содержит b38, реальные результаты и blockers. Old-reader expiry
2026-11-01 не продлевался; merge/release по-прежнему закрыты.


## 2026-11-04 — b38 required macOS check, attempt2

Повтор только failed jobs исходного macos-pr41754394218 завершён успешно
на b38eb07c93a10467244fc8a6b6cf5e3373c53b6b, attempt2. Последний required
macos-pr SUCCESS; первоначальный FAIL и отдельный diagnostic PASS сохранены.
Mac source/таймауты не менялись, причина разницы времени не доказана.
Полный журнал attempt2 SHA256 62c1b075d0fc83f3a29a85a7a23b940cb84218060ee04ae3c873dc01b1c0df25.
pr-metadata41756995865 всё ещё FAIL: compatibility exception expiry must
be in the future (UTC). Срок 2026-11-01 не продлевался, merge/release закрыты.
Текущий dirty Windows diff отдельно прошёл check_spec_kit_governance.py
с pinned CLI1.0.7, YAML parse и git diff --check. Эти проверки не заменяют
Windows runtime GREEN или точные проверки будущего коммита.


## 2026-11-04 — T088 receipt decoder: фактический RED

Применены только два тестовых изменения red-tests.patch
06b90cd875ca914d3557f32354e44c2b7c00185aa74eea252eba7c25732366eb.
Восемь производственных bases повторно сверены и не менялись; VM не менялась.
Portable Debug C++17 сборка DesktopDeletionProtocolTests и
DesktopDeletionLedgerTests завершилась exit0. Прямой первый тест обработчика
завершился SIGABRT/-6 на testLifecycleCannotAcceptWithoutReceipt:318:
старый decoder принимает canceled_before_creation без receipt. Строка317 —
начало assert в исходнике; фактический runtime report содержит318. Это
целевой RED, не compile/fixture failure. Квитанция с test/exe/build/log pins
e52137170da9f8ed6af2648868b29d2a9b2c8d39014a9ef0f01845e9d7b40bff.
Native RED и производственный кандидат пока не исполнены/не применены.


## 2026-11-04 — T117 ordinary completed-history admission: GREEN

Принятые четыре производственных файла и supplement активного Pair
прошли настоящий Windows Debug прогон: host0/build0/CLI0, полный Files
CTest1/1 PASS944.42s (total944.44s). Все три case0/1/2 прошли; после
SETUP_OK сохранены штатные прежние stdout markers и ровно16 ожидаемых
negative diagnostic строк stderr. Current queue g4 не приравнивается
историческому copy g2, последующие commits/cold open сохраняются; corrupt
barrier и noncurrent retained root отклоняются без побочных действий.
225source/configuration110 неизменны во время проверки; остальные7PE
и installed0.1.0.15 сохранены, own0/noForce/UnicodeTEMP+TMP PASS. Terminal
c93d8df8a4b9cfeaf4521af13ea0a542fe90e5492989531c885957a6f2f5d071.
В VM пока нет восьми dirty Web bridge файлов; это отдельная квалификация
storage source, не combined-source62 или installed acceptance. Полный
координатор миграции/cleanup/missing-original recovery не принят, T117 открыт.


## 2026-11-04 — T088 bridge: Windows CMake14/14 GREEN

После квалифицированного storage GREEN в VM перенесены ровно восемь
ранее проверенных bridge/test файлов. Windows Debug build0, host0, CTest
14/14 PASS143.80s; NativeRecordingOfflineWebViewTests PASS128.08s на
сгенерированном звуке. Native device/audio/network/install0. Начальная
конфигурация110 имела null command у14 ещё не собранных целей; разрешён
только переход этих14 к одному точному Debug/<same-name>.exe, остальные
команды/имена/свойства неизменны. Source225 и8custodyPE сохранены;14новых
bridgePE проверены после тестов; installed0.1.0.15 неизменён, own0/noForce
и UnicodeTEMP/TMP PASS. Terminal93a0dea0bbef036017e0ffb5ecbd887e0c08c6d48319b2f360c72c635b1aa97e.
Первая попытка разбора результата ожидала запятую и явный текст0failed;
этот CTest пишет100% tests passed out of14. Квалификатор поправлен только
на две известные формы итоговой строки; все14 точных PASS/name/exit/guard
проверки сохранены. Это ошибка формата квалификатора, не runtime failure.
GRAF_WINDOWS_APP_SDK/оригинальный WinRT parser в CMake не исполняется;
установленный пакет/COM/UI приёмка и весь T088 по этому прогону не закрыты.

## 2026-11-04 — T088: нативная фоновая сверка, RED → GREEN

После checkpoint `e7c30956e2c2bbedfd746724bd4ed658d4e99e2b` продолжена
существующая T088. Реальный Windows тест прежней реализации завершился
ожидаемым отказом на `NativeProtectedDeletionApplication:1503`: внешняя
квитанция не принималась. Перед этим успешно создана и открыта непустая
защищённая очередь. Host0/build0/case3 — сборщик собрал именно ожидаемый RED,
это не успешный продуктовый тест. Terminal
`66215779b13a25564ff282ceb591ad261306e0830c8be929c3bac2085b67ec44`.

Реализация запускает существующий нативный lifecycle независимо от WebView,
использует проверенный аккаунт и защищённый снимок очереди. Видимые записи
дают лишь приоритет; фоновый обход сохраняется без открытого кабинета.
Проверяются полное покрытие ответа, область аккаунта и квитанции; результат
публикуется после защищённого сохранения, независимого чтения и принятия.
Первая внешняя квитанция создаёт сразу принятое состояние без локального
DELETE-намерения. Нового таймера, серверного API или формата очереди нет.

Первая Windows сборка кандидата остановилась до тестов: C2665 в
`NativeCapture.h:500`, вызов несуществующего конструктора строки парой
итераторов. Исправлен один вызов на существующий конструктор
`id.data(), id.size()`. Исходные журналы сохранены; после отказа отдельно
сверены программы и конфигурация, поэтому повтор использует фактическую
базу после неудачной сборки. Terminal отказа
`49f53d2aea4a6b19f87245e7721fc01994ff1ad3ac84115351fb5f1c8ee35682`.

Повтор `t088-lifecycle-worker-green-r2`: host0/build0, CTest3/3 PASS76,83с.
`DesktopDeletionLedgerTests` PASS2,38с, `DesktopDeletionProtocolTests`
PASS3,74с, `NativeProtectedDeletionApplication` PASS70,64с. Последний
проверяет >200 origins, приоритет и фоновый обход без WebView, холодное
повторное чтение принятой квитанции, отказ для неполного/чужого/устаревшего
ответа, конфликта поколения и неоднозначного сохранения; исходный пакет
сохраняется. Конфигурация110 побайтно неизменна, source225 совпадает с
рабочей копией, восемь custody и четырнадцать bridge EXE проверены.
Установленный GRAF0.1.0.15 сохранён, оставшихся процессов0, принудительного
завершения нет, фактические TEMP/TMP с кириллицей и пробелом подтверждены.
Terminal `9da80c392e6a49eedc6780507706d213dc612ce058a011413213300d1673c762`.
Переносимые decoder/ledger проверки также PASS2/2 (2,67с).

Это проверка искусственных данных без устройств и настоящей сети.
Постоянное состояние доступа owner/unknown и его использование для
воспроизведения/отправки ещё не повторяют Mac; T088 остаётся открытой.
Обычная Release сборка AppMain/WinRT и установленная приёмка — отдельные
проверки; этот CMake результат их не заменяет.

## 2026-11-04 — проверки промежуточного коммита e7

`e7c30956e2c2bbedfd746724bd4ed658d4e99e2b` отправлен в
`codex/200-windows-followup`. GitHub `governance-fast41762226050` и
`macos-pr41762226446` завершены SUCCESS на этом точном SHA. Описание PR7331
обновлено штатным `sync-pr-metadata.py` после подтверждённой проверки кода;
helper вернул `pr_metadata=updated` с тем же SHA. Нативный lifecycle из
текущего рабочего дерева ещё не входит в e7. Просроченное исключение старого
reader сохранено, его срок не продлён; PR остаётся черновиком, слияние и
публикация не выполнены.

## 2026-11-04 — T088: Release-сборка, сохранённые промежуточные отказы

Обычный `/t:Rebuild` Release/x64 не завершился за внешний предел600с;
запускатель остановил только собственное дерево сборки. Это не отказ
продуктового теста и не успешная сборка. Source225,22 Debug EXE и установленный
GRAF сохранены, процессов сборки после очистки0. AppMain.obj создан именно
этим Rebuild: SHA256
`3312cf2e2f3fddb642a9b18a3ee2362f2ee16df8375e5bea2b283567e24d73e4`,
UTC03:09:10 внутри окна сборки03:03:02→03:12:59. Итогового EXE ещё нет.
Terminal `51ded7b0b8e2254788a0a56c37603b7d717ff735c417cc5b0202c04faab04421`.

Для завершения тех же исходников выбран штатный `/t:Build`, с прежним
внешним пределом600с и проверкой происхождения AppMain.obj. Первая подготовка
остановилась до MSBuild: ошибочный `[DateTime]` cast переводил сохранённый
UTC в местное время Windows и сравнивал разные шкалы. Независимый read-only
запрос подтвердил одинаковые hash/UTC и свежесть файла; все шесть casts
заменены на `DateTimeOffset.UtcDateTime`. Никакие проверки hash, равенства
времени или границ окна не удалены. Повторная сборка требует свежий EXE и
либо свежий AppMain.obj, либо точный проверенный объект исходного Rebuild.
Обе неудачные попытки сохранены отдельно; пользовательские данные,
установленное приложение и пределы продуктовых тестов не менялись.

Исправленный `/t:Build` (`t088-current-release-build-r2`) также достиг создания
EXE/LTCG, но не завершился за600с: `BUILD_DEADLINE`, host1, собственное дерево
сборки остановлено. Source225,22 Debug EXE и установленный GRAF сохранены,
процессов сборки после очистки0. Это второй реальный предел ожидания сборки,
не PASS и не новая ошибка продуктового теста.

Для завершения обычной Release/x64 сборки подготовлен отдельный полный
`/t:Rebuild` с внешним пределом1800с и пределом host2100с. Изменены только путь
журналов и время ожидания запускателя; исходники, конфигурация, AEC3, проверки
свежести AppMain.obj/EXE,225 исходных файлов,22 тестовых EXE и установленного
пакета сохранены. Пределы продуктовых тестов не увеличены. Обе предыдущие
остановки сохранены; результат нового запуска фиксируется отдельно.

## 2026-11-04 — T088: сходимость промежуточного среза и следующий этап

Срез нативной фоновой сверки сопоставлен с FR-006/013/022 и существующей
T088/#7231: получение внешней квитанции, полный scoped batch, конечный обход
без WebView, protected commit/readback/adoption покрыты приведёнными выше
RED/GREEN. Персистентный доступ и холодное локальное восстановление ещё не
реализованы. Они остаются в T088; перенос originals и retirement — в T117/#7445,
полная защищённая приёмка — в T118. Новых самостоятельных обязательств вне
этих открытых задач не выявлено, `tasks.md` не изменён. Всего задач120,
закрыто93, открыто27; прежние отметки не закрывают новый этап.

Технический проект следующего этапа внесён в шесть существующих документов:
local queue v4/read2/3/4, nullable raw access, один authenticated local context,
отдельные local/network полномочия, bounded revalidation и cancel/drain перед
применением отзыва доступа. Это инженерные решения для выбранного пользователем
Mac-паритета, не отдельное пользовательское утверждение wire-формата. Независимый
requirements/analyze review точных шести кандидатов — C0/H0; встроенный набор
reviewer checklist477/0 не выдаётся за проверку ещё не написанного кода.
Проверка Spec Kit governance после этой правки PASS. Реализация и новые
результаты следующего этапа фиксируются отдельно.

Проверен свежий `origin/master` = `20393b9b3a8c65434aa5c1a71b30f522e8ff8a71`:
один новый коммит F140 затрагивает billing observation/server/infra/docs,
без Windows/Mac исходников. На момент этой записи он ещё не включён в ветку;
синхронизация следует после проверенного промежуточного коммита Windows.

## 2026-11-04 — T088: обычная Release/x64 сборка завершена

Полный `/t:Rebuild` в `t088-current-release-rebuild-1800` завершился:
host0, MSBuild0, terminal=true, machine0x8664. Созданы свежие AppMain.obj и
GrafWindowsApp.exe из текущих225 исходных файлов; WinRT/WebView2 ветка собрана
обычным проектом без тестовых вставок. SHA256 EXE
`61a1c50f23ffcca3644b6748aa5ca84a623d850a6426214fe0b44c00f52d526a`,
AppMain.obj `470bd2083769c33965658a7e7d8dd90f94ce8e9ae226600d0b067e8082dd8a96`.
Итоговая квитанция `terminal-evidence.json` SHA256
`aaadc149a8ee303aa8672967071526e1cb0bcc507c58f4cae3939883c8a7a8ae`.
Повторная проверка всех сохранённых raw pins и текущих225 исходников PASS.

Все22 прежних Debug тестовых EXE сохранены побайтно; установленный
GRAF0.1.0.15 и его EXE не изменены. Сборочных процессов после завершения0,
принудительной очистки нет. Предупреждения4: два D9025 о `/W1`→`/W4` и два
C4100 в закреплённой зависимости AEC3. Новых ошибок компиляции нет.
Предыдущие попытки600с остаются неуспешными; увеличен только внешний предел
ожидания этой сборки, не продуктовых тестов.

Это проверка сборки к уже подтверждённым portable2/2 и native3/3 T088,
не установка и не проверка поведения нового EXE на пользовательских данных.
T088, T117 и T118 остаются открыты; текущий промежуточный срез не разрешает
слияние или публикацию с просроченным исключением старого reader.

## 2026-11-04 — промежуточный коммит и свежий master

Проверенный lifecycle-срез сохранён коммитом
`a832dda2dc3a27f95175642a2cdb2c17858833e1`. Master
`20393b9b3a8c65434aa5c1a71b30f522e8ff8a71` включён без конфликтов;
итог `8c17bea5e4eba38b4e4f10a842987fcaae243fd6` отправлен в существующую
ветку PR7331. Все225 Windows source pins квалифицированного Release сохранены
побайтно. Spec Kit governance после совмещения PASS. Это не слияние PR;
проверки нового head/base фиксируются отдельно, прежние GitHub PASS не
переиспользуются как доказательство нового SHA.

## 2026-11-04 — T088: test-only RED нового логического формата

В существующем portable target `DesktopUploadQueueV2Tests` добавлен один
непустой generated v4 literal с access/context. Build0; CTest8 с точным
`testV4CodecRed:589 assert(decoded.ok())`: нынешний v2/v3 decoder ожидаемо
отказывает в новом формате. Result SHA256
`1cf2c5db93487afca364b3e5dff44f9b8ad864c67dbcd27d7a9ef00391b5ebfc`.
Raw build/CTest pins сверены независимо. Тестовый base восстановлен побайтно;
этот результат ещё не доказывает новый writer, mixed BOTH или native restore.

## 2026-11-04 — T117: целевой RED координатора после настоящей подготовки

Новый `--migration-pair` строит настоящую generated legacy очередь и пакет
через существующий generated AAC/v5 helper. Первые две попытки не дошли до
целевого отказа: C2248 на private Files::context в interface и затем на private
QueueValue::decode в тесте. Обе ошибки компиляции сохранены, не названы RED:
terminal `4604e7bf038d082a962252a5bbd225dd979ec65e8366f53d332d3700a0844a22`
и `f19ae32d7e5f6076ec5ee866494bafab0a43d8a7721d938efc50e07a3db8b21c`.
После каждой сверены все22 EXE и конфигурация110 без изменений. Независимый
reviewer признал пропуски компилируемости; прежний SOURCE GO не выдаётся за
результат компилятора.

Минимальные поправки только в outside test/interface: friend существующего
production-кандидата для QueueMigration и вызов decode через уже разрешённый
pure-data TestPeer. В `t117-coordinator-engine-red-r3` host0/build0/case3:
сначала `MIGRATION_COORDINATOR_SETUP_OK scenario=0`, затем stub recoveryRequired
и ровно `assert(opened.ok())` FilesTests1535. Terminal SHA256
`60b4a9c725effde2b6363bb0a805a689b1feab9b022a728f7cfd82b0c4b61dfb`.
Конфигурация110, source225, прочие21 EXE, установленный GRAF и его EXE сохранены;
проверяемый FilesTests EXE неизменен после запуска, own0, forced cleanup нет,
Unicode TEMP/TMP подтверждён. Это целевой test-first отказ отсутствующего
координатора после успешной подготовки, не успешная миграция и не работа с
пользовательскими originals. Production-кандидат T117 ещё не принят.

## 2026-11-04 — установленное окно после входа

После сообщения пользователя о завершении входа read-only query подтвердил:
GRAF0.1.0.15, package Ok, процесс запущен/Responding. Прямой просмотр текущего
экрана VM подтвердил загруженный авторизованный кабинет и нативную ошибку
«Защищённое локальное хранилище недоступно. Записи не изменены»; Start отключён.
Это не исправление записи и не приёмка T097. Снимок использован только для
осмотра, не включён в evidence/repo и удалён из временного каталога; содержимое
кабинета не переписано в журнал. Пользовательские записи/ключи не менялись.

## 2026-11-04 — T088: v4 codec/domain, целевая регрессия и portable GREEN

Первый v4 candidate не менял access для положительного lifecycle-ответа о
записи без meetingId. Исправленный test-only срез воспроизвёл это отдельно:
build0/CTest8, `testV4CodecAndDomain:724`,
`unbound.applyLifecycleEntries(...) && changed`. Проверен и связанный допуск
восстановления prepared owned записи: nullable/exact owner сами по себе его
не блокируют; прочие допустимые access codes блокируют. Неопределённый ответ
о записи без meetingId сохраняет прежнее значение access. Прежний unowned
helper и receipt branch не менялись.

Final r2 source pins для семи code/test файлов сверены с применёнными байтами.
Portable Debug build0, CTest0: ContractFixtures, DesktopUploadQueueV2Tests,
DesktopDeletionLedgerTests и DesktopUploadRecoveryTests — 4/4 PASS,8.60с.
Result SHA256 `32b65d4d26472fc0db5f662a2cb078748f873e252d4c9e01d526d589fd178ae9`;
build log `1a690c70a212761a879349336a667dda74525d14cfa5f8933712f869eee8465d`;
CTest log `796747dc0a0438515193725209522c10923058ed96fc142b07339052a9043998`.
Независимый reviewer сверил raw logs, pins и текущие семь файлов: C0/H0 в этом
объёме. Новых зависимостей и тестовых targets нет; изменены три прежних
ожидания версии writer, исторические v2/v3 входы сохранены.

Это проверка strict logical codec, сохранения nullable access/context и
доменных правил. Native fingerprint/restore, wire access, потребители,
cancel/drain/adoption, mixed protected BOTH и отказ настоящего old reader ещё
не приняты. Windows native, установленный пакет, T088/T117/T118 и выпуск
остаются открыты.

## 2026-11-04 — обязательные GitHub checks промежуточного SHA

Для `8c17bea5e4eba38b4e4f10a842987fcaae243fd6` macos-pr run41770288058
SUCCESS. Governance-fast run41770288026 FAILURE:2091 passed,2 skipped,1 failed;
`test_stopped_same_active_sigkill_and_exact_retry[after-permit]` остановился
на ненулевом результате повторного worker. Сохранённый GitHub output обрезает
середину stderr, поэтому точная причина ещё не установлена. Этот результат
не переименован в случайный сбой или PASS; начата отдельная диагностика.
Прежние успешные checks другого SHA его не заменяют. Описание PR7331 пока не
синхронизировано как принятое; просроченное исключение old reader не продлено.

Узкое локальное воспроизведение того же `after-permit` с полным traceback:
1 passed,35.61с. Log SHA256
`4cf3c19928fe1133409a7f51d0a6cd5e38439ed5151c7a7999812ee1cfb3dc6f`.
Сбой не воспроизведён; это не заменяет GitHub check и не доказывает причину
прежнего отказа. Production harness и fixture по предположению не менялись.

## 2026-11-04 — T117: независимое SOURCE review уточнения r4

В outside candidate устранены два блокера полного review r3: private packed
factory принимает точного удерживаемого migration parent и retained failure
owner до переноса lease; plaintext source до первой persistent записи принимает
только v2/v3, общий protected decoder продолжает читать v4. Existing ordinary
factory guards сохранены. Production delta31/−9, три файла; patch SHA256
`fde6de82e0f9f07bc209d4bdf49009fec3d1ec34af14c75f2252b3406c77d86c`.
Focused tests заморожены до production delta: protected v4 без записей,
отказ plaintext v4 без изменений и packed birth readback failure с последующим
release/reopen через writeExisting; SHA256
`11afd5d31765573c42116b90bb74ec2fee538e9d3cf869fa9c5b56b08732c92b`.

Независимый reviewer проверил delta, фабрики, базу r3, восемь файлов и три v4
зависимости: C0/H0, SOURCE GO. Это не compile/runtime GREEN; candidate ещё
не применён в repository. Cleanup caller, delete_purge, retirement executable
legacy и recovery неизвестного quarantine остаются открыты. Никаких операций
над пользовательскими originals или установленным GRAF этот review не выполнял.

## 2026-11-04 — T088: первый native v4 прогон и поправка ожидания

В `t088-v4-native-green` фактический результат — FAIL: build0/CTest8/host1,
QueueV2 и Ledger PASS, NativeProtectedDeletionApplication FAILED на прежнем
ожидании `valid == (edge == 0 || edge >= 5) && !changed`, строка1624.
Result SHA256 `cb2503eb1de92180be8d940c36a54e8692cabce954aa068ebab9eb61e0c65068`;
CTest log `83f1bac816b4186e894f24709a6df8c4f23926ee690b3423f4d45ecdc5e66e0b`.
Независимо сверены source225, configuration110,22 PE после сборки и запуска;
прочие19 PE и установленный EXE сохранены, own0/build0, forced cleanup нет.
Финальный runtime UTF16 receipt отсутствует: host завершился раньше этой
проверки, поэтому encoding PASS этому запуску не присваивается.

В fixture допустимые ответы остались ровно edge0/5/6. Для edge5 (`allowed`
без meetingId) исправлено устаревшее ожидание: теперь required changed/owner,
сохранённая accepted receipt и действующий deletionBlocks. Для всех остальных,
включая отвергнутые1..4 и unavailable без meetingId, требуется точное равенство
сериализации. Исходный snapshot проверяется неизменным после каждой итерации.
Production по этому отказу не менялся. Поправка fixture ещё требует отдельного
фактического native прогона; первый FAIL сохранён и не переименован в PASS.

## 2026-11-04 — T088: sync-state access, portable RED → GREEN

Подключено поле непосредственного `meeting.access_state` из server sync-state
к existing ServerTruth. Строгий existing reader проверяет root/meeting, decoded
duplicate keys, UTF-8 и bounds; значения1–64 safe ASCII сохраняются без
нормализации. Missing/null не стирают cached nonowner. Прежние charged allocator
и cancellation используются и приватным защищённым вызовом. Новых parser,
публичного API или зависимостей нет; Mac/server не изменялись.

Test-only RED: build0/CTest8, точный assert owner в testSyncAccessDecoder:274,
а не ошибка подготовки. Result SHA256
`b7d9725bdce029e7a585fc7139148b55d5f5be21a6bbb91088a0291215da50b4`.
После отдельно проверенного production patch: Debug build0/CTest0,
ContractFixtures/QueueV2/Ledger/Recovery — 4/4 PASS,10.75с. Result SHA256
`dbe57e304b76f0758ad015bfbde6be8cc4f8e7526954e387c706fbe2c2234176`;
CTest log `51c1a91817f09bd3848582e8db4079bc2694c91d4ce9be8c129cc55dffe6a299`.
Тесты включают decode → reconcile → cold reload с двумя raw отказами,
missing/null и последующим явным owner. Reviewer независимо сверил точные
candidate pins, старые test bodies, сырые журналы и receipts: C0/H0.

Это portable AppleClang/Debug на dirty candidate поверх8c17…, а не MSVC или
установленный пакет. Защищённый Windows template call и runtime отмены/квоты
ещё требуют проверки. Native context/consumers/cancel-drain, T088 и T117
не закрыты; сохранение поля само по себе не выдаёт доступ к содержимому.

## 2026-11-04 — T088: native r2 остаётся FAIL, начата диагностика завершения

После единственной поправки Native fixture (source225 manifest
`9fa56b59eed336bada8554d5c70abb03495b7bcb03e41a178d130b17f4a47412`)
сборка прошла, QueueV2/Ledger PASS; NativeProtectedDeletionApplication FAILED
42.87с без assertion/output. CTest8/host1, полный набор не принят. Source225,
configuration110,22 PE после запуска и установленный EXE сохранены; own0,
active-build0, forced cleanup нет. CTest LastTest.log также не содержит причины
или дочернего exit code. Отсутствие сообщения не доказывает конкретное исключение.

Следующая ограниченная диагностика запускает только прежний Native CLI без
сборки и копирования исходников, чтобы получить настоящий signed/hex exit code.
Даже host0 этой диагностики не объявляется product PASS; original r2 FAIL
сохранён. Ни production, ни пользовательские записи по гипотезе не менялись.

Диагностика завершилась: тот же неизменённый EXE напрямую выполнил весь CLI
`--protected-deletion-application`, включая lifecycle211 и18 режимов удаления,
с signed exit0/hex0/host0. Source225/configuration110/22 PE/installed сохранены,
own0/build0/noforce, Unicode TEMP/TMP подтверждён. Terminal SHA256
`843957c30caf40d9273813c2fa3dbcf9055218791c53f3b16f595fdf397347a8`.
Этот результат не объясняет предыдущий CTest FAIL и не заменяет его успешным
набором. Ошибка остаётся открытой; production по догадке не менялся. Проверку
T117 можно вести отдельно от неё по точным текущим source/PE/config pins:
сам T117 сначала проверяет protected-v4 dependency перед plaintext-границей.

## 2026-11-04 — T117: остановка копирования до сборки, не тестовый RED

`t117-coordinator-r4-red-live-baseline` завершился host1 до сборки и CLI:
Copy-Item отказал на ProtectedCustodyFiles.h с ReadOnly. Три предшествующих
исходника успели скопироваться; отдельный readback проверил все225: только
LocalRecordingPackage.cpp/.h и ProtectedCustodyFiles.cpp имеют ожидаемые
новые хеши, остальные222 — прежние. Все22 PE и установленный EXE сохранены,
own0/build0, принудительного завершения нет. Поле exes_unchanged=false здесь
не означает изменение PE: postbuild-карта не была создана, прямое сравнение
с предыдущей картой подтверждает равенство. Нужный assertion не достигнут,
поэтому результат не считается test-first RED и не заменяет прежние FAIL.

Следующий ограниченный повтор продолжит с фактических225 исходников и
скопирует только оставшиеся пять заданных целей. Для них сохраняются и
восстанавливаются точные атрибуты; временно снимается только ReadOnly. ACL,
права пользователя, установленное приложение и рабочие записи не меняются.

В существующий Native protected-deletion test добавлены22 строки наблюдения
за std::terminate: фиксированные phase/case, accounted bytes и ограниченный
вид исключения без его текста. Assertions, сроки и production не менялись;
handler заканчивает процесс с ошибкой. Независимый SOURCE review C0/H0,
candidate SHA256 `a6f660897fbf2aa262c3dbad3a1da97d0a2bd95f1ea16bf50814de36d978b7a1`.
Это средство выяснить прежний необъяснённый CTest FAIL; его компиляция и
исполнение пока не подтверждены, отсутствие terminate marker не исключает
системный crash. T088/T117 и приёмка установленного пакета остаются открыты.

## 2026-11-04 — T117 r4: подтверждённый native test-first RED

Повтор с сохранением атрибутов (`t117-coordinator-r4-red-live-baseline-r2`)
прошёл подготовку и Debug build0. Первый protected-v4 positive завершился;
затем CLI вернул3 на точном assertion строки1507:
`!refused.ok() && refused.error==CustodyFileError::invalidContent`.
Это нужный RED границы plaintext v4, а не compile/setup failure. Packed birth
case ещё не запускался; общего GREEN нет. Host0 означает успешное наблюдение
ожидаемого отказа, а не работоспособность продукта.

Source225 manifest `45219a6dc7cc3833c5b0b277e63fc7f4ec28611e39066e8b477f4de193d70584`;
configuration110 неизменна,22 PE после теста сохранены; из них21, кроме
FilesTests, также совпадает с предыдущей сборкой. Атрибуты всех восьми целей
восстановлены, installed EXE прежний, own0/build0/noforce; runtime UTF16 PASS.
Result SHA256 `25b6292e4462a38db712a5e71b35e5f7a8a84a66ff53471e32d9b5bc7d5ef659`,
terminal SHA256 `df82e2ca0489c2a396f05edd900c720763a86e357f249b299c9a5018f3d9ec51`.
Предыдущие FAIL сохранены. Следующий шаг — отдельно применить три production
изменения r4 к этому стенду и выполнить прежний полный migration-pair CLI.

## 2026-11-04 — T117 r4: full migration-pair остаётся FAIL

После трёх production-изменений r4 outside stage `t117-coordinator-r4-green`
скомпилирован успешно, но full migration-pair вернул3/host1: scenario7
дошёл до setup marker и assertion строки1575 о packed birth readback fault.
Числа hit/ok/error/native первоначальный тест не вывел, причина ещё не
установлена. Это не GREEN и не повод менять ожидаемый тип ошибки по догадке.
Предшествующие protected-v4 и plaintext-v4 проверки пройдены до этой точки.

Source225 SHA256 `c960df2d67cd6eeea9a786be5578d0b594b1cc28c4b84e37084894c861c20f9e`,
config110 unchanged,22 PE после сборки/теста сохранены;21 посторонний PE
совпадает с RED baseline. Атрибуты восстановлены, installed unchanged,
own0/build0/noforce. Terminal SHA256
`528ac8d2a4beee0b915037ea3ad306bbbe32f6ff7dcf7816eca4303370ea605c`.
Эти production-изменения пока не применены в репозиторий или приложение.

Следующая диагностика добавляет только одну строку числового вывода перед
прежним assert: hit/ok/error/native/read/write/flush. FilesTests candidate
`e24067a6c577549ccf76848bf8e456116785b57b2176a18c7d13b3c26ab995c3`.
Test expectation, native hook, generated fixture и сроки неизменны.

Независимое SOURCE review также допустило отдельный test-only same-cookie
A→B сценарий в существующем NativeProtectedAccountProblems: свежие fake GET
через spaces/auth/me/notification-context, coalesced lookup и настоящий drain,
без присвоения identity через TestPeer. Он применён в repository поверх
наблюдения terminate; Native test SHA256
`1d239f552ee011c4fceac5c154d34bbd73cd8fcebe574bfd0aafc3955498839d`.
Фактический native RED этого сценария пока не получен; production auth не менялся.

## 2026-11-04 — T117: packed fault не достигнут, проверяется sharing violation

В `t117-coordinator-r4-packed-observed` сборка завершилась0, full migration-pair
вернул3/host1 на прежнем assertion (теперь строка1576). Наблюдение перед ним:
`hit=0 ok=0 error=13 native=3221225539 reads=104 writes=18 flushes=26`.
Это recoveryRequired и NTSTATUS0xC0000043 (sharing violation); намеренный
packed-read fault ещё не достигнут. Ожидаемый assertion сохранён.
Source225 SHA256 `dd22d701f13941a54276de2f32430c43d1cbdfd4e2074fa7bb3f6560424a53f3`;
configuration110,22 PE после исполнения,21 посторонний PE, точные атрибуты
и installed EXE сохранены; own0/build0/noforce. Terminal SHA256
`adf6d3bb4bdbf66a14387a73c6b97cac25d0a609b8d93091572a140e43a11064`.
Это фактический FAIL, не успешная диагностика продукта.

Подготовлен отдельный кандидат ровно двух строк: временные target-directory
handles queue/package rename допускают FILE_SHARE_WRITE, сохраняя запрет
FILE_SHARE_DELETE; source handles и последующий строгий directory lock
не изменены. SOURCE review C0/H0, candidate Files.cpp SHA256
`957a15abd9ea4c4d184bba0ece0ac269718aaab8deaa7d47b5541a69694b2d54`.
Причина конкретного native отказа и эффективность изменения пока не доказаны
исполнением. В repository и installed app этот кандидат ещё не применён.

После сообщения пользователя «вошел» read-only проверка установленного
0.1.0.15 подтверждает Responding=True и прежний EXE SHA256
`e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`.
При визуальном осмотре кабинет загружен, запись закрыта сообщением о
недоступном защищённом хранилище. Содержимое встреч не сохранялось;
временный снимок удалён после осмотра. Вход не принимается за приёмку
хранилища, записи или нового кандидата; рабочие записи/ключи не менялись.

## 2026-11-04 — T088: фактический same-cookie native RED

`t088-native-auth-red`: MSVC Debug build0, затем существующий
NativeProtectedAccountProblems вернул CTest8 за10.42с на точном
`same_cookie_requires_fresh_native_workspace_proof`, строка3091.
Это нужный test-first RED через fake spaces/auth-me/context, без устройств
и настоящей сети. Host0 означает успешное наблюдение ожидаемого отказа,
не product PASS. Текущая Windows-компиляция strict wire также успешна,
но весь wire/runtime набор этим не принят.

Source225 SHA256 `39e3bd830437e7b7aa362b54320487f58ca7d0c8aeba14dfabaa3fad6048b168`;
configuration110 и её commands/properties неизменны; все22 PE сохранены
после сборки/теста,21 посторонний PE совпал с предыдущим. Атрибуты
восстановлены, installed EXE прежний, own0/build0/noforce, UTF16 PASS.
Native PE SHA256 `04fe094a9b1c679d209e31fc62b9538b9714a3a4ab91f83ee4ce2b81a0048b55`;
Main terminal evidence SHA256
`c51607a4424308d2a626b64f5563c2509281a88f18a320fbf54a2c5cd6e97da3`.
T117 sharing FAIL и прежний необъяснённый T088 deletion CTest FAIL сохранены.
Production native account/context пока не применён; следующий этап —
отдельная проверка кандидата и прежних регрессий. Ни task, ни issue не закрыты.

## 2026-11-04 — T117: sharing-кандидат прошёл packed-границу, cleanup FAIL

В `t117-coordinator-r4-target-sharing-runtime` MSVC build0, но полный
`--migration-pair` завершился3/host1. После двухстрочного изменения
намеренный packed fault достигнут: `hit=1 error=6 native=30`; прежний assert
пройден, как и последующие history/BOTH-auth проверки. Сценарии0–5
координатора завершились до scenario6, где `cleaned.ok()` (строка1653)
отказал с `error=13 native=0`. Queue/package subject первоначальный вывод
не различал; причина cleanup пока не доказана. Успешный хвост и общий
migration PASS не заявляются; исходный FAIL сохранён.

Source225 SHA256 `3e1dd707cff7df58617d69de1cadf73ae21770851a4488fae055d8adf132eaa5`,
config110 unchanged,22 post-build/post-test PE совпали,21 посторонний PE
сохранён относительно predecessor; attrs restored/installed unchanged,
own0/build0/noforce. Main terminal SHA256
`a66e2b34a1082b0c805c340e49254a02640c85bb88193948aad1610098da8d6c`;
независимая проверка raw hashes/результата подтвердила FAIL. Runtime UTF16
receipt не создан при host1, его PASS этому запуску не приписывается.

## 2026-11-04 — T088: Native context кандидат применён, первая сборка FAIL

После фактического same-cookie RED и независимого SOURCE review C0/H0
применены точные5 production и3 test файла из handoff: native account/context,
offline local content/document binding, строгий отказ upload continuation
после nonowner. Полный restrictive cancel/drain остаётся отдельной открытой
частью того же принятого плана; T088 не завершена.

`t088-native-context-green`: исходники225 скопированы, MSVC build1/C2039
в NativeCapture.h:3437 — BasicUploadResponse содержит raw `retryAfter`,
а не `retryAfterSeconds`. Тесты не запускались. Это настоящий compile FAIL,
не test RED/GREEN. Минимальное исправление одной expression переиспользует
`DesktopHttpTransport::rateLimitPauseSeconds(answer.status, std::string_view(answer.retryAfter))`;
независимый SOURCE review C0/H0. Native SHA256 после исправления
`ccb5f34a300e9f581bf1ee5bd82866358c8289fc1b5d58368292f9edd84650f7`.

Неуспешный build source225 SHA256
`f5d32d780ecfa35be0db279fd348539501141ab0dba02f9e8e5b5951af72043e`.
Все22 фактических postflight PE совпадают с прежними; exes_unchanged=false
означает несозданную post-build map, а не изменённые EXE. Отдельный актуальный
configuration readback подтвердил110 case с теми же commands/properties.
Атрибуты восстановлены, installed unchanged, own0/build0/noforce.
Main terminal SHA256 `ec602c692166b17d373b5f8bc1886970faff1218611cb234ab97fc896222b2a0`.
Следующий неизменный набор из5 существующих CTest проверяет исправленную
компиляцию; AppMain отдельно требует полной сборки приложения.

## 2026-11-04 — T088: сборка исправлена, фактический набор2/5, три отказа

`t088-native-context-green-r2`: MSVC Debug build0 всех трёх целей. До тестов
runner остановился на `CONFIGURATION_COMMAND DesktopUploadRecoveryTests`:
впервые собранный executable разрешил прежде отсутствовавший command.
Сверка110 имён/параметров и остальных commands не обнаружила изменения
конфигурации продукта.22 прежних PE сохранены; фактический23-й Recovery PE
`3d6a430dde0fad0e42fefb33a9243668b2a8b198e968299cedc7077d50d3b251`.
Main evidence SHA256 `496ee2f681a36e5ff441df373c9f95d65c223e181751683bd1723c871be81fe7`.
Это build PASS, но runner FAIL без запущенных сценариев, не product PASS.

Первый CTest-only запуск `t088-native-context-ctest` завершился host255 до
выполнения guest script: `PrlJob_GetResult: Invalid argument`. Сохранён
отдельно; следующая база взята с фактического успешного build, не с255.
В `t088-native-context-ctest-r2` применён EncodedCommand launcher; product
source/PE/config не менялись и повторной сборки не было.

Фактический CTest8/host1 за598.74с: Recovery PASS295.77с; AccountProblems
PASS0.82с; Calendar FAIL280.49с на localPlaybackDocumentCurrent(document,
nonce-1), строка316; DeletionApplication FAIL15.58с на retained, строка1691;
PlaybackConsumer FAIL6.05с на enqueue, строка7620. В собственном Calendar
процессе наблюдалось CRT-окно abort; после точной проверки PID/контролов
отправлена команда штатной кнопки Abort. Assertions не игнорировались,
принудительного завершения процесса не было; время Calendar включает диалог.

Source225 SHA256 `7711c37ea3225112ce5bf0529c2d9531257a90f95ad366e2e4bb57c4588519dd`;
все23 PE до/после совпали,110 commands/properties неизменны, installed EXE
прежний, own0/build0/noforce. Runtime encoding receipt при host1 отсутствует,
UTF16 PASS этому запуску не приписывается. Main terminal SHA256
`c0c26f8e6e4aff8b9e047d64c73c66230691f33cdcbc6fd2b85fa23c17cdbf65`.
Результат2/5 не закрывает T088; старые ошибки T117/Deletion сохранены.

Проверка исходников выявила ошибку новой Playback fixture: enqueue запрещает
серверные meeting/access fields при добавлении локальной записи. То же
ограничение затрагивает пока не применённый restrictive-drain RED donor.
Кандидат RED до исправления подготовки не квалифицируется. Независимый
SOURCE review restrictive-drain production также нашёл блокировку повторной
физической сверки после отказа readback: запрет новых upload должен стоять
после existing reconciliation signal. Этот кандидат пока не применён;
исправления и повторная проверка требуются до GREEN/приёмки.

## 2026-11-04 — T117: busy package подтверждён наблюдением

`t117-coordinator-r4-cleanup-observed`: MSVC build0, полный прежний CLI
`--migration-pair` завершился3/host1 на cleaned.ok(), строка1655. Test-only
наблюдение сохранило все прежние assertions и production. Queue cleanup
начинается subject0/stage2/auth0/sources1/owner_failed0; package cleanup после
существующей отрицательной проверки удерживаемого Pair — subject1/stage2/
auth0/sources3/owner_failed1, затем recoveryRequired13/native0. Следовательно,
в данном сценарии healthy owner блокируется до положительного cleanup уже
после busy-negative; queue-ветка не является местом отказа.

Source225 SHA256 `eb52be1d19ead0add7aaa3bc755610745a5aec7d1637a6491e8b90982ba838ad`;
FilesTests PE `a057f0e3e4bddfe291be543b4537661d4a16023c9ff04ef6a09092c648c9e074`;
config110 неизменна,23 PE после сборки/теста совпали,22 посторонних PE
не изменились. Атрибуты восстановлены, installed прежний, own0/build0/noforce.
Main terminal SHA256 `972c31038d78d105443cd7412965a2322ed5541d6c0f0cc1089cbedb3a83c9dc`.
Runtime encoding receipt при host1 отсутствует; результат остаётся FAIL.

Подготовлен внешний кандидат+6 строк: cleanup получает существующую
исключительную lease целевого package-state до полного cold validate;
отказ возвращается локально без порчи owner, успешная временная lease
освобождается до прежней полной проверки. Global validate/sticky failure,
authority/BOTH/history и cleanup effects не меняются. Ещё не применён,
требует независимого SOURCE и фактической проверки. T117 остаётся открытой.

Calendar test-only корректировка теперь охватывает четыре места с локальной
привязкой до account: первоначальные отрицательные проверки сохранены,
повторная привязка воспроизводит порядок AppMain. Все259 прежних assertions
побайтно и по порядку сохранены; независимый SOURCE C0/H0 для
`bd640ef52565ae00988754cba76cc1c955ef2960c518c4cf49a4e4db683c083f`.
Исправленный runtime проверяется отдельно; прежний Calendar FAIL не стёрт.

## 2026-11-04 — Calendar принят тестом; T117 busy-owner RED подтверждён

`T088_calendar_fixture_correction`: MSVC build0, CTest0, настоящий
CalendarJoinHostTests PASS за1.44с. Запускатель завершился host1 только на
`EXACT_ONE_CASE_PASS_REQUIRED`: CMake вывел иной текст успешной сводки.
Отказ запускателя сохранён отдельно от успешного сценария; повтор ради
переписывания сводки не выполнялся. Main terminal SHA256
`24b2c47f6abb4ca47794fcfb9109431cc526f2fc95d6c49e5be300b41d73df0c`.

Offline playback fixture исправлена без изменения защиты продукта: enqueue
получает локальную строку без серверного meetingId; matching typed result
устанавливает серверные сведения через applyUploadResult. Независимый review
подтвердил сохранение1847 прежних assertions и добавление одного.
Следующий test-only restrictive-drain RED применён после независимого review
SOURCE GO/C0H0: Native test SHA256
`309e7f39626531dab1db420ebe0d6e3a62defe3140ce4c50d737a45c2cd61168`.
Настоящий upload и lifecycle HTTP должны быть одновременно удержаны до
целевой проверки1627. Выполнение этого нового сценария ещё не подтверждено.

`t117-coordinator-r4-cleanup-busy-red`: build0, полный прежний migration-pair
CLI3, host0 как ожидаемый отрицательный результат. Точный assert1651
`!ProtectedCustodyMigrationTestPeer::failed(*owner)` воспроизводит порчу
healthy owner после отказа занятого package; это не ошибка подготовки.
Source225/PE23/config110 сохранены, атрибуты восстановлены, installed EXE
прежний, own0/build0/noforce, runtime UTF16 PASS. Main terminal SHA256
`1442066034699a5d0e2bce39340558ea406032b45f06b533cea0168138ece4a0`.
После review запущен отдельный полный migration-pair с шестистрочным
preflight-исправлением; его результат пока не объявлен успешным.

Режим остаётся high-risk-product в существующих T088/T117. Записи и ключи
пользователя не изменялись; ошибку installed protected store эти проверки
сами по себе не закрывают. Новых задач/закрытия issues, коммита, push или
выпуска в этом проходе пока нет.

## 2026-11-04 — busy cleanup исправлен, полный переход ещё отказывает

`t117-coordinator-r4-cleanup-busy-green`: MSVC build0. Полный прежний CLI
migration-pair завершился3/host1 после completed-history case2, без stderr.
Queue и package cleanup прошли место прежнего отказа с owner_failed0;
это не полный GREEN. Main terminal SHA256
`02eab0f7b783b1474c439eca215f566e081dc670d5a651cd5555ede3b170c508`.
Source225/PE23/config110, атрибуты, installed и фактический drain проверены.
Runtime encoding receipt отсутствует при host1. Для следующего отказа нужна
служебная диагностика точного этапа/типа исключения; причина не выдумывается.

`t088-native-lifecycle-first-red-r3`: MSVC build0; существующий
NativeProtectedDeletionApplication CTest8, точный именованный assert1627,
25.54с. Настоящие held upload/lifecycle предпосылки пройдены. Это целевой
RED отсутствующей отмены до изменения очереди. Отдельный прежний
NativeProtectedPlaybackConsumer CTest8/18.31с дошёл дальше исправленного
enqueue и отказал7840: offline_display_must_not_starve_behind_network_recovery.
Его FAIL не считается PASS запускателя. Main terminal SHA256
`fa6bf18733fd031c58af38b0b641e4d0fa7503b80271a71d81254ea0c0f668c8`.
Host0 подтверждает ожидаемый RED и сохранённый отдельный FAIL; source225,
PE23/config110, attrs/installedsame/own0/noforce/UTF16 проверены. T088 открыт.

Проверка процесса Spec Kit: check_spec_kit_governance.py PASS,
speckit-bootstrap --doctor --frozen PASS с закреплённым CLI1.0.7. Это не
проверки нового commit SHA, не установочная и не полная продуктовая приёмка.

## 2026-11-04 — уточнение отказа миграции и подготовка нативных исправлений

`t117-silent-failure-runtime`: MSVC build0, полный прежний migration-pair
CLI3/host1. После `completed_history_end` перехватчик завершения записал
`exception=bad_alloc code=0 owned_bytes=2174`. Это уточняет границу отказа,
но не доказывает его причину и не принимает T117. Main сверил source225
(изменён только диагностический FilesTests), PE23 (изменён только FilesTests),
config110, восстановление атрибутов, прежний установленный EXE, own0/build0
и отсутствие принудительной очистки. Main terminal SHA256:
`e69a5bab57f4a80778705c3c7a37e3a21f2e3b5d465875f3c31caf47ffcf92ac`.
При host1 отдельный runtime encoding receipt не создан; успех не заявляется.

В исходники Main после отдельных независимых SOURCE GO/C0H0 внесены
удержание restrictive lifecycle answer до настоящего upload drain и
перестановка отмены display после upload admission guards. Второе исправляет
подтверждённое голодание локального display при недоступной сети. NativeCapture
SHA256: `23c3dd0b80e6ba8f708861599d57f783a7330ddd6dc30cebee1130f32b4ac2d5`.
Полное расширение существующего теста с исправленным порядком смены A→B
прошло независимый повторный просмотр mode7; SHA256:
`eed0f66cb3d7849dc79d8ce9ddc63ff306f33b64f88c0c379a80f50bc5835834`.
Прежние assertions, quota, deadlines и маршруты CTest сохранены.
Это разрешение по исходникам; Windows GREEN этих изменений ещё не получен.
Установленный GRAF, пользовательские записи и ключи не изменены.

## 2026-11-04 — offline playback GREEN, reconciliation остаётся открытым

`t088-lifecycle-drain-green-r5`: MSVC build0; отдельно запущенный существующий
`NativeProtectedPlaybackConsumer` CTest0/PASS, 19.33с. Прежний FAIL7840
offline display воспроизведён до исправления и устранён текущим порядком
upload admission. Это фактический Windows runtime результат, не установка.

`NativeProtectedDeletionApplication` CTest8/137.66с: сценарии0–7 прошли
свои проверки до сценария8, который отказал1789 при ожидании lifecycle ticket
после physical readback retry. Предшествующий именованный assert физического
retry пройден; полный Deletion GREEN не получен, причина следующего отказа
ещё не установлена. Общий host1 сохраняет этот FAIL, несмотря на Playback PASS.
Оба результата записаны отдельно; deadlines не менялись.

Main сверил source225 с ровно двумя Native заменами, PE23 (изменился только
Native test), прежнюю config110, атрибуты, installed EXE и завершение всех
своих процессов без принудительной остановки. Main terminal SHA256:
`e67d1ffffba050d87077e09a47fc143ae940772d0dd90152a8934edeaafcd655`.
Ни T088, ни T117/T118, ни полная установленная/аппаратная приёмка не закрыты.

## 2026-11-04 — точный allocation cut миграции и исправление mode8 fixture

`t117-silent-failure-runtime-r2`: build0, полный прежний migration-pair CLI3,
host1. Последняя отметка перед `bad_alloc`:
`linked_factory_invoke schema=1 subject=0 fail_at=8 cancel_at=0 fault=0 ordinal=1`.
Начальные fixtures и history прошли дальше прежней отметки. Причина исключения
внутри этой factory ещё требует анализа; marker сам по себе её не доказывает.
Диагностика +21 строк не меняет assertions, allocation ordinals, квоты, IO cuts
или сроки. Main подтвердил source225/PE23/config110, прежний installed EXE,
восстановление атрибутов и own0/build0/noforce. Main terminal SHA256:
`9c0491bcde2eaa4c60020d9a07786d680206f5f4d2c38f05e1847b149687daed`.

Независимый анализ mode8 показал несовпадение fake ответа из двух записей с
новой приоритетной пачкой из одного playback origin после same-account
revalidation. Production strict decoder корректно отвергает лишнюю цель.
В Main применён test-only r6 +10/−1 после SOURCE GO/C0H0: публичный visible hint
перед новым запросом, проверка фактических двух origins и сохранение прежнего
cursor для этой приоритетной пачки. Фоновые cursor-проверки других modes
сохранены; остальные старые assertions и пределы не менялись.
Native test SHA256:
`f40866c1fe0a324964f86f4904968ba4a6bf5fd687f5cdfdab57eb70ead60441`.
Начат новый отдельный runtime прогон; успех заранее не заявляется.

## 2026-11-04 — режимы отзыва доступа пройдены; фаза quota проверяется отдельно

`t088-lifecycle-drain-green-r6`: MSVC build0, существующий
`NativeProtectedPlaybackConsumer` CTest0/PASS20.62с. Все девять новых
сценариев restrictive drain дошли до прежнего отдельного negative quota
fixture. Полный `NativeProtectedDeletionApplication` CTest8/154.25с,
retained assert2067; общий host1. Это FAIL полного набора.

Наблюдение quota: до poll answer0/waiting0/used67108864, после
answer1/waiting2/used67103776; posts1/operations0/generation2. Поток был
завершён, но его future ещё удерживал память. Обычный poll забрал реальный
ответ и освободил часть памяти перед обработкой. Это объясняет ошибочную
фазу заполнения квоты в fixture, а не подтверждает превышение product limit.
Main terminal SHA256:
`0238dbb97ca9cde10b241f6a93361d5eddb72b38112f98ddf6ba0023486b195a`.
Source225/PE23/config110, attrs/installed EXE unchanged, own0/build0/noforce.

После независимого SOURCE GO/C0H0 применён test-only r7 +11/−1. TestPeer
сначала забирает настоящий ответ фактически завершённого потока через
join/get/reset; затем прежняя 64MiB квота заполняется и существующий
pollLifecycle проверяет удержание. Старые assertions, включая retained,
posts1 и отсутствие операций, сохранены; добавлены четыре проверки.
Production не изменён. Тест SHA256:
`dda37c86facc8d2179f1bc51830eb70c40ceb390573fe919d47ba6f291103cef`.
Runtime r7 ещё не выполнен.

В параллельных материалах T117 сохранены первичные заголовки установленного
MSVC14.44.35207: пустой filesystem::path использует noexcept basic_string
constructor с Debug proxy allocation. Это согласуется с cut8 в новой
MigrationSource::path; требуется точечное исправление и подтверждение прежним
полным allocation-cut CLI. Ничего в квотах/отказах/ordinals не ослаблено.
Полная Release x64 solution-сборка текущей VM source225 запущена отдельно;
результат ещё ожидается. Установка и пользовательские данные не менялись.

## 2026-11-04 — текущие локальные проверки процесса

После test-only r7 выполнены `git diff --check`,
`python3 scripts/check_spec_kit_governance.py` и
`speckit-bootstrap . --doctor --frozen`: PASS. Использован прежний
проверенный pinned CLI1.0.7/bootstrap0.11.0, без обновления lock/dependencies.
Повторное чтение checklist state:198 файлов,477 checked,0 unchecked; Main
их не изменял. Lane остаётся high-risk-product, tasks не закрыты.

Контекст после сжатия восстановлен из оригиналов: guidance index,
document-reading, development-process, product-gates; применимые constitution
I/II/IV/VI/ProductAndPlatform/Workflow/Governance, PRD4.x/4.y;
plan3748–3820, data-model269–310, quickstart1520–1557,
local-custody7.1 и8 (применимая начальная restart-safe часть), taskT117.
Хеши обязательных источников совпали с прежним собственным чтением в том же
диалоге. Полная память о старом чтении не принята вместо нынешних разделов.
Это запись восстановления контекста и локальные diagnostics, не exact-SHA
CI/merge/release разрешение. Main source HEAD остаётся
`8c17bea5e4eba38b4e4f10a842987fcaae243fd6` с незакоммиченным diff.

## 2026-11-04 — полная Release x64 solution прошла

`t088-current-fullsolution-rebuild-draft`: фактические MSBuild0/host0,
Rebuild Release x64. Свежие AppMain.obj, WebView2Host.obj и x64 EXE;
production compile commands не содержат forced include/test definitions,
тестовые payload markers отсутствуют. AEC provenance сохранён.
EXE SHA256:
`1ed664d9ef249003b50900873bde75f5ea10fee398b65951ea2101e10789f1c3`.
AppMain.obj SHA256:
`ade22908a4a0161a7c961dbb54005d9c1d9f28ec9164e894ff29305448d889f0`.
WebView2Host.obj SHA256:
`57015d47d2983cbfe36494dc8960850bb2169936a02fd8f84132db0984ba9860`.

Main подтвердил source225 без копирования, PE23 unchanged, полное равенство
before/after CTest configuration JSON110, installed EXE unchanged, own0 и
active-build0, noforce. В прежней configuration31 случаев не имеют command
из-за ещё не собранных соответствующих CMake targets; они не исполнялись
и не считаются PASS. Обе выбранные Native commands присутствуют.
Solution compile не принимает весь CTest110 или установленный пакет.

Main terminal SHA256:
`2c9fe0cc23f09477c1ad5024bf2eddcbac9836b01c1f7bc4c013bb0066569aed`.
Это сборка фактической VM source225 с семью ранее подготовленными T117
файлами, ещё не применёнными в Main repo; Native test остаётся r6.
Результат не переносится на незакоммиченный Main r7 или будущую T117 правку.
Установка/запуск/записи/сертификаты/сеть/микрофон не менялись.

## 2026-11-04 — Native restrictive lifecycle и offline playback GREEN

`t088-lifecycle-drain-green-r7`: build0/host0. Существующие два случая
выполнены раздельно и завершились штатно: NativeProtectedDeletionApplication
CTest0/PASS178.98с, NativeProtectedPlaybackConsumer CTest0/PASS19.75с.
Полный Deletion case теперь прошёл прежний negative quota assert2067,
а также все новые restrictive/reconciliation/account-switch modes. Квоты,
сроки и assertions не ослаблены. Предыдущий r6 FAIL остаётся историческим
результатом, новый GREEN относится только к текущему r7 source/test.

Main сверил source225 с единственной заменой Native test f408→dda37,
PE23 (изменён только Native test), полное before/after configuration JSON110,
атрибуты33 до/после, installed EXE unchanged, own0/build0/noforce.
Дополнительный UTF16 runtime receipt подтверждает реальные TEMP/TMP с
кириллицей и пробелом и точный runner.
Main terminal SHA256:
`fb0c3446ce0a422d1a2dadd9f301b611f5a4da2ae74e67ae2c384dbd49ef8dfc`.
Native test EXE SHA256:
`1a66e8ab2371f304281dc64f95916a2ecc3342bed19b92592101e43b0a218df9`.

Это focused Windows runtime GREEN для T088. T088 целиком, T117/T118,
установленный MSIX, аппаратная x64/AEC/60min, доступность и реальный
auth/upload E2E не приняты по этим двум случаям. Задачи не закрывались.
Следующая проверка — существующий полный migration-pair CLI с точечной
двухстрочной production правкой; FilesTests2f192 не меняется.

## 2026-11-04 — T117: полный migration-pair GREEN после исправления empty path

В отдельном кандидате Files.cpp изменены ровно два инициализатора пустого
filesystem::path: MigrationSource::path (все6 элементов) и migrationSourcePath
создаются через пустой wstring_view. Пустое значение и последующие реальные
присваивания не меняются; существующий обработчик bad_alloc получает отказ
вместо terminate в MSVC Debug proxy allocation. Правка получила независимый
SOURCE GO/C0H0 и проверена на точном кандидате SHA256:
`c15e6b84cc453ab62b455020ddb07c46bf0e208264bd63299c3ce6809873651b`.
FilesTests2f192, assertions, ordinals, limits и deadlines не менялись.

`t117-migration-source-empty-path-runtime`: build0, полный существующий
`ProtectedCustodyFilesTests --migration-pair` CLI0, выбранный host-retry0.
Последовательность fail8→control→fail9 подтверждает allocationFailed,
released() и successful retry; linked_end и protected_end пройдены,
terminate отсутствует. Полный CLI продолжен до штатного выхода0.
Это наблюдение нового кандидата, не снятый стек прежнего cut8.

Первый launcher завершился255 (`PrlJob_GetResult: Invalid argument`) без
начала runner. Сохранён отдельно; Main readonly проверил own0/build0,
исходный Files957a/attributes32 и отсутствие result/build logs перед повтором.
Короткий ASCII launcher выполнил тот же неизменный Run8b8d; его receipt
`host-retry-exit.json` не перезаписывает исходный отказ. Отдельный UTF16
runtime receipt в коротком launcher отсутствует и не заявляется.

Main квалифицировал source225/ровно1 Files delta957a→c15e, PE23/ровно1
FilesTests изменение, before/after config110 exact, attributes32 restored,
installed EXE unchanged, own0/build0/noforce. Main terminal SHA256:
`ebf0192d46c0c9fbf3a473e8afa9a8651d925455ff9ed2b54f7aa89470a48b09`.
FilesTests EXE SHA256:
`be882cb4171ef2e52356d500cc97e813495b489116275ce0c2dfe00dfeb90a35`.

T117 не закрыта: подключение coordinator к обычному initial NativeCapture
startup, полный generated legacy→adopt→cold restart и retirement ещё
требуются. Unknown quarantine не обходится и не удаляется. Main repo пока
не получил семь T117 production файлов/FilesTests; VM proof не объявляется
сборкой текущего Main HEAD. Установленный пакет и реальные записи не менялись.

## 2026-11-04 — проверенный T117 coordinator перенесён в Main repo

После SOURCE reviews и полного migration CLI GREEN Main применил ровно
семь production файлов T117 и существующий FilesTests2f192. Каждая исходная
версия совпала с HEAD (не было чужого dirty diff в этих8 файлах), каждый
кандидат — с actual source225 manifest. Сохранены target-sharing исправление,
cleanup busy preflight и empty-path обработка отказа; v4 codec не заменялся.
После применения все225 tracked source inputs Main побайтно совпали с
испытанным VM snapshot. Native initial hook пока НЕ изменён.
Main application receipt SHA256:
`111317a35d9a211830ad5a3066db352b03ef379f4668c7482438fc4aac4a5047`.
`git diff --check`: PASS. Это незакоммиченный набор исходников, не exact-SHA CI.

Следующий bounded срез в existing NativeProtectedReadModel прошёл отдельный
requirements/analyze review C0H0: настоящий legacy→worker ready→adoption→
обычная recovery mutation→cold restart; unknown quarantine exact preservation
на двух cold launches; один native-qualified ambiguous bootstrap switch и
повтор после полного release. Сохраняются virgin/protected проверки. Новые
CLI/CMake/tasks/quotas/deadlines не требуются, assertions не ослабляются.
Только initial startup будет использовать Migration::open; reconciliation
reopen останется StoreOwner::open. Допуск к design не является SOURCE/runtime
PASS будущих изменений. Исходники/test donor готовятся отдельно до RED.

## 2026-11-04 — сходимость промежуточного T088 + T117 checkpoint

Независимая повторная сверка: C0/H0, новых обязательных задач не выявлено.
225/225 repo inputs и8/8 T117 donors совпадают с последним tested manifest;
18/18 T117 terminal artifact pins проверены. Прежние scoped SOURCE reviews
применимы к совпавшим r4/target-sharing/busy-preflight/empty-path/test pins.
Принятый промежуточный состав — T088 access/context/drain и T117 coordinator,
без ещё не написанного Native startup hook. Задачи и reviewer checklists не
закрыты. Release compile относится к своему более раннему manifest, не
переобозначается сборкой нового current source225.

После применения прошли YAML parse F200, `git diff --check` и governance.
Ранее подтверждённое пользователем сохранение промежуточного этапа используется
для implementation checkpoint; push/merge/release этой записью не выполняются.
Открыты native initial migration→adopt→mutation→cold restart, cleanup caller/
delete-purge/retirement, installed/auth/upload/accessibility/hardware acceptance.

## 2026-11-04 — промежуточный коммит и актуальная идентичность PR

Промежуточный этап сохранён коммитом
`159f539903c7df9d0716b2658f2f82c70e51b8f1` и отправлен в
`origin/codex/200-windows-followup`. Main повторно проверил remote ref и
`headRefOid` PR7331: оба равны этому SHA; PR открыт как draft. После коммита
закреплённые governance и doctor/frozen прошли с Spec Kit1.0.7/bootstrap0.11.0.
Все225 source inputs совпали и с рабочими файлами, и с Git objects коммита.
Это связывает прежние локальные результаты с тем же содержимым, но не
превращает их в exact-SHA GitHub или установленную приёмку.

Описание PR обновлено по существующему шаблону с exact source SHA и
ограничениями последних трёх проверок. Remote body сверено после обновления;
SHA256 `3da5695390133f63076fcf5ebc301f77109652d6c3ceff3c4343d078d487d96d`.
`gh pr edit` отказал на устаревшем GraphQL projectCards до записи; Main
проверил отсутствие изменения и применил тот же body через REST PATCH.
Новый metadata run41799447077 сохранил единственный отказ: срок исключения
совместимости должен быть в будущем UTC. Прежний SHA mismatch устранён;
исключение2026-11-01 не продлевается. Merge/release запрещены до retirement.
Source runs41798787888/41798787929 и их text-reuse runs41799446485/
41799446589 на момент этой записи ещё выполняются; PASS не присваивается.

Следующая существующая регрессия `ProtectedCustodyFilesTests` запущена
Main отдельно, без сборки/копирования исходников и без `--migration-pair`.
Источник225 `31891dbab92994628ecad98a1ef0009b659a55eecf3d1d415abb37079a50a04a`,
EXE `be882cb4171ef2e52356d500cc97e813495b489116275ce0c2dfe00dfeb90a35`;
runner `0b511466441d53d7884bde270bf7cf8ac3a5230feeefb5b7ed57d44db0a46462`.
Сохранены configuration110/PE23/installed0.1.0.15, внешний предел600s,
no-force и новый generated TEMP с кириллицей/пробелом. Результат пока pending.

## 2026-11-04 — обычная файловая регрессия после T117: PASS

Тот же запуск завершился штатно: host0/CTest0, существующий точный
`ProtectedCustodyFilesTests`1/1 PASS422,23s (общее время422,24s). Сборка и
копирование исходников не выполнялись. Main сверил первичные result/host/log
и binding/SHA256SUMS, сравнил все225 source inputs, все23 EXE и полную
configuration110 до/после. Изменений нет. Установленный0.1.0.15/EXE
`e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`
сохранён, атрибуты исходников не менялись, own0/build0/no-force.

Main terminal SHA256
`80ed1a22e52588dac50c0846c3d4e4498cec5dfbf41649de6d8df47f6232418b`;
classification `ACTUAL_EXISTING_DEFAULT_FILES_CTEST_PASS_NO_BUILD_NO_SOURCE_CHANGE`.
31 зарегистрированная команда отсутствует по прежнему состоянию unbuilt
targets; они не запускались и не засчитаны. Unicode fixture использован, но
отдельного runtime encoding receipt в этой оболочке нет. Это регрессия
обычных файловых операций, не ещё не написанная Native startup интеграция,
не whole-product/installed/physical acceptance и не закрытие T117.

GitHub source `macos-pr`41798787929 на exact159f539903c7df9d0716b2658f2f82c70e51b8f1
завершился success; его text-reuse41799446589 также success. Source
governance41798787888 пока выполняется. Metadata по-прежнему blocked expiry;
успех одного required check не разрешает merge.

## 2026-11-04 — календарный тест и подготовка Native migration

Source governance41798787888 на159f539903c7df9d0716b2658f2f82c70e51b8f1
завершился отказом в `test_calendar_native_join_ui.py[False]`: общий счётчик
подсказок видимости вырос1→2. Ограниченное воспроизведение показало реальную
автопрокрутку после click и дополнительное допустимое сообщение `offscreen-local`
между двумя наблюдениями. Это не доказательство пропуска malformed input.
В тесте начальная позиция, отправка семи прежних неправильных payload и сбор
результатов теперь выполняются в одном синхронном `page.evaluate`.
Product scripts, семь отрицательных случаев и положительные проверки сохранены.
Независимое SOURCE review — C0/H0. Main применил тест с SHA256
`c0789c13fbb9e882b59901d201fc98ced114d496dc09c17d2f1ce44bc8782962`:
прямой Node запуск прошёл Chromium/WebKit; настоящий Python renderer —2/2 PASS
для embedded=false/true, также в обоих движках. Сохранённое предупреждение
pytest об уже импортированной fixture не является пропуском теста.
Оба процесса exit0; журнал Python SHA256
`f337a8e4ab69b366e43e0bd1bec9ab5edd3e990792f98e4bef2f501b4eb85492`.
Это локальная проверка изменённого теста, не новый GitHub PASS.

Первый Native migration test0b3b с прежним startup23c3 дал build0/CTest8,
assert4170 за2,97s. После однострочного подключения migration21e7 тот же
тест снова дал build0/CTest8, assert4170 за2,67s, error3/unsafePath.
Main квалифицировал второй результат как
`ACTUAL_UNEXPECTED_NATIVE_STARTUP_FAILURE`: host1, источник225, configuration110,
посторонние22 EXE и установленный0.1.0.15 сохранены; own0/build0/no-force.
Это отказ, а не GREEN или приёмка T117.

Независимая повторная проверка обнаружила ошибку положительной фикстуры:
generated helper создавал root с унаследованной DACL вместо protected DACL
текущего SID. Main подтвердил в гостевой Windows только безопасные признаки:
protected=false, rule_count=5, exact_private=false. SID и содержимое записей
не выводились. Первая read-only команда отказала на синтаксисе, вторая —
на execution policy; третья штатно прочитала ACL с exit0. Политика не менялась.
Прежний SOURCE GO подготовки исправлен reviewer на H1; эти два падения
не различают отсутствие migration hook и неверную подготовку каталога.
Для функционального RED→GREEN нужны новая закрытая generated root/package
фикстура и повтор обоих вариантов startup. Production ACL-проверка сохраняется;
unknown quarantine не разрешается обходить. Задачи и checklists не закрыты.

## 2026-11-04 — Native initial migration и восстановление очереди

Положительная generated fixture исправлена: root/package создаются с explicit
protected current-user DACL, как существующая FilesFixture. Производственные
ACL-проверки не менялись. Независимый source reviewer подтвердил исправление;
неиспользованный вариант с дополнительным include не применялся.

Исправленный тест с прежним startup дал build0/CTest8: точный
`native_startup_must_migrate_valid_legacy_before_ready_admission`, error13
(recoveryRequired), 3,31s. Это квалифицированный RED, в отличие от прежних
падений на unsafePath. После подключения `ProtectedCustodyMigration::open`
startup прошёл; следующий отказ на `readers.ok()` выявил удерживаемую самим
тестом inspection lease. Её срок ограничен существующим образцом scope:
все проверки сохранены, независимые readers открываются после освобождения.
Поэтому окончательный тест отличается от RED также этой поздней правкой
времени жизни; идентичность байтов теста между RED и GREEN не заявляется.

Окончательный `NativeProtectedReadModel` прошёл: build0/CTest0, 1/1 Passed
18,88s. Native SHA256 `21e7cfd8eb43371a437bcfa76dbf6647a65044c54b218b323f220345c0363dfc`,
тест `5e3c67c97d4860873fb8751692588b8ed4942878dd22aa91e2d5acd53c08383a`.
Запускатель вернул host1/ACTUAL_CASE_PASS_REQUIRED: он дополнительно искал
маркер успешного stderr, который CTest --output-on-failure не печатает.
Исходный отказ запускателя сохранён; Main и независимый reviewer отдельно
подтвердили фактический PASS теста по exit0 и точной строке CTest.

Проверены v2/v3, initial ACK/adoption, реальная последующая mutation/commit,
cold restart, сохранность UUID/session/ranges/operations/purge ACK, exact
logical bytes и retained originals, BOTH history и повторный холодный запуск.
Неизвестный quarantine блокирует два запуска без изменения snapshot.
Source225 совпадает с Main, configuration110 неизменна, built/postflight PE23
согласованы, посторонние22 EXE и installed0.1.0.15 сохранены; own0/build0/no-force.
Классификация `ACTUAL_NATIVE_READMODEL_CTEST_PASS_WRAPPER_ORACLE_FAILURE`.
Звук устройств и реальная сеть не использовались. Initial ambiguous switch,
cleanup caller/delete-purge/retirement и установленная приёмка остаются открыты.

## 2026-11-04 — обычная Native storage регрессия текущего startup

На том же EXE без новой сборки/копирования запущен существующий точный
`NativeCaptureStorageIntegrationTests`: host0/CTest0, 1/1 Passed299,69s
(общее299,70s). Здесь проверка результата опирается на exit0 и точную
строку Passed, без маркера подавленного успешного stderr. Main сверил
source225 с текущей рабочей копией, configuration110 и все23 PE до/после:
изменений нет. Установленный0.1.0.15/EXE e6094e4d… сохранён;
own0/build0/no-force, runtime encoding receipt не заявляется.
Result SHA256 `56a3152a15212503a26cf53a92671a6fa3eb470e0413d456589351b3ad2a52ee`.

Независимый ограниченный convergence audit подтвердил существующих owners:
Native migration/fixture lifetime — T117, atomic visible-recordings observation
test — T088; новых CRITICAL/HIGH findings и непокрытых новых задач нет.
22FR/10SC, tasks120/93checked/27open, reviewer checklists198/477checked/0unchecked.
Родительские задачи и reviewer markers не менялись. Это не whole-feature
converged и не installed acceptance. Governance и frozen doctor прошли с
project-pinned CLI1.0.7; первый вызов governance без pinned PATH отказал из-за
глобального CLI1.2.6, после выбора закреплённого CLI выполнен успешно.
Скрипт prerequisites этой закреплённой версии не знает --require-spec;
повтор с поддерживаемыми --require-tasks/--include-tasks и отдельной проверкой
наличия spec.md подтвердил тот же каталог F200, инструменты не менялись.

## 2026-11-04 — checkpoint и initial authority-switch ambiguity

Промежуточный этап сохранён и отправлен:
`d4bb3f59be5621459b0918c246800c8d31e73ba7`. PR7331 остаётся draft, описание
сверено с exact HEAD; metadata отказывает только на истёкшем исключении,
которое не продлевалось. Postcommit project-pinned governance прошёл.

В следующем срезе из pollUploads удалён недостижимый plaintext upload tail.
localQueueComplete требует protected startup/projection, при которых прежняя
ветка уже возвращала управление. Старый exit drain был достижим, но без
создаваемого legacy flight возвращал0; protected retire/cancel/admission
сохранены. Независимое source review — C0/H0. Общие legacy APIs и их test-only
обращения пока остаются, полное retirement этим удалением не заявляется.

Добавлен generated initial-switch тест: fixed native paths/IDs и CNG codec
аутентифицируют bootstrap candidate, ожидаемый transaction берётся из BOTH
ранее принятого migrating bootstrap. Qualifier проверяет kind10, exact target,
next generation и copied_verified intent. Выполняется настоящий native rename;
только после return0/io.Status0 и подтверждения file ID/final path один раз
подменяется io.Status на0xC0000022, исходный return и LastError сохраняются.
Generic ambiguousRename выключен. Первый Native отказывает без admission;
после полного drain два cold startup восстанавливают те же store/queue/intent
IDs/transaction, exact v3 bytes, package bytes и retained originals.
Это in-process ambiguous completion, не доказательство power-loss durability.

Main собрал существующие NativeCaptureStartupTests и Native storage target:
build0, host0/CTest0, 2/2 PASS — startup0,25s и read-model27,61s, всего27,88s.
Native SHA256 `2d56774a0ad9fb32a843c11769097171903508db754ec642846e984fa4b36357`,
тест `1b6647ff5e74c1772610c4ddb79ca8b9620eb09b10de369c5c0edc5867c260c6`.
Source225 совпадает с Main; все прежние23 PE после build стабильны, посторонние
22 не менялись. Отдельно built/postflight совпал новый Startup EXE. Единственная
разница configuration110 — появилась command ранее не собранного Startup
target: Main удалил именно её из after JSON и сравнил весь объект с before.
Оставшиеся30 команд отсутствуют как прежде и PASS не засчитываются.
Installed0.1.0.15 сохранён; own0/build0/no-force, runtime encoding receipt нет.
Result SHA256 `2de6ac13c676cd03845a8a78c43e0c8d27195da0b00fa14cae2a25458bd7a2f8`.

## 2026-11-04 — реальный отказ migrated local removal и lifetime migration fences

В существующий NativeProtectedLocalRemoval добавлен generated сценарий:
обычный Native startup переносит v3/WAV/AAC seed, принимает startup ACK,
проверяет владельца через искусственный transport, сохраняет и принимает
local_delete_pending до OS effect, затем проверяет actual recycle, adoption
и cold restart. Root migration history/original ledger, gate/sentinel,
посторонние deletion operation/ACK должны оставаться неизменными; local removal
не создаёт server purge ACK. Device audio и реальная сеть не используются.

Сценарий выявил настоящий отказ: intent принят (generation1→2), но purge
возвращал unchanged generation2, pending1/accepted0, пакет оставался на месте.
Несколько последовательных диагностических запусков сохранены как FAIL,
а не PASS. Проверка пути прошла; различие plain/extended path не выявлено.
Настоящий CoInitializeEx(STA) вернул S_OK, поэтому гипотезы MAX_PATH и COM
не приняты. PreDelete подтвердил exact source identity и recycle flag;
PostDelete получил0x80270027 без destination, PerformOperations0x80004004.
Безопасный sink отклонил операцию; permanent fallback не выполнялся.

Разбор lifetime выявил собственные deny-delete handles: queue migration
открывала package directory в inventory и повторно для ledger row,
сохраняла оба в root State::directories и передавала root ordinary owner.
retireMigrationQueueSource закрывал source/barriers, но оставлял эти handles.
В кандидате помечены ровно два вида временных package guards; существующая
точка retirement удаляет все помеченные entries после завершения migration.
Root/ancestor/service/legacy-originals guards и sharing flags не ослаблены.
Move сохраняет метку, erase использует noexcept move assignment без выделения
памяти. Все ранние отказы сохраняют RAII и не возвращают admitted owner;
финальная cold validation обязательна. Временная диагностика из production
DesktopLocalPurgeService и тестов удалена. Независимая SOURCE оценка C0/H0;
runtime результат этого кандидата фиксируется отдельным следующим разделом.

## 2026-11-04 — native migrated removal: исправление проверено

Кандидат Native SHA256 `2d56774a0ad9fb32a843c11769097171903508db754ec642846e984fa4b36357`,
Files `3746d43e2cc93011d2c99c88dc546b94844976f524c0bf00cde42b89034c60da`,
test `799b63492f3464227bceed861827d16465bce9133b2d5a942d188ab40774d24d`.
Main: build0/host0/CTest0, NativeProtectedLocalRemoval1/1 PASS64,18s.
Новый migrated сценарий подтвердил intent_adopted/actual_recycle/purge_adopted/
cold=1; прежние modes0–8 завершились. Mode8 сохранил внешний deny-delete,
затем после release восстановил удаление и cold queue. Проверка exact source
identity, существующие RUN_SERIAL/timeout240s/команда не менялись.

Независимое source/runtime review — scoped GO, C0/H0: 10/10 frozen inputs,
source225 совпадают с Main, configuration110 до/после равна baseline;
из24 PE изменился только целевой NativeCaptureStorageIntegrationTests,
посторонние23 сохранены. Built/postflight hashes совпали, attributes сохранены,
installed0.1.0.15/EXE e6094e4d… неизменён, own0/build0/no-force.
Result SHA256 `a80a9435f39b1947e3fabcf7f1b6c2c87731806bd79acd5cef3da3ddd8f4e0fb`.
Runtime encoding receipt и product PASS не заявляются. Startup/readmodel и
migration-pair относятся к отдельному следующему запуску на тех же исходниках.

На checkpoint d4bb3f59be5621459b0918c246800c8d31e73ba7 GitHub подтвердил
SUCCESS governance-fast, macos-pr и Swift build/tests. pr-metadata остаётся
FAIL из-за истёкшего legacy exception; исключение не продлевается. Эти CI
результаты относятся только к checkpoint и не переносятся на будущий коммит.

## 2026-11-04 — повторная проверка startup/read-model/migration-pair после lifetime fix

На тех же source225 и Native/Files/test SHA предыдущего раздела Main собрал
ProtectedCustodyFilesTests и NativeCaptureStartupTests. Build0/host0;
CTest0, NativeCaptureStartupTests и NativeProtectedReadModel2/2 PASS26,49s.
Затем отдельный существующий ProtectedCustodyFilesTests --migration-pair
завершился exit0 с linked_end и protected_end. Проверены обе schema и оба
subject, fault/allocation/cancellation matrix; native фабрики отчитались
515/535 allocation/cancel cuts с повторным открытием. Чужие процессы не
завершались, новые тестовые команды/таймауты в CMake не добавлялись.

Main отдельно сверил frozen inputs, все225 исходных хешей с рабочей копией,
configuration110 до/после и24 PE: built/postflight одинаковы, менялись только
два собранных target; посторонние22 PE неизменны. Installed0.1.0.15/EXE e6094e4d…
сохранён, attributes сохранены, terminal own0/build0/no-force.
Result SHA256 `c835b305f0dc7f8442c68fb4213561ff6e7f503f41fcec07a8e923c608bea1df`.
Governance прошёл с project-pinned PATH. Первый doctor без PATH выбрал
глобальный CLI1.2.6 и отказал; повтор с pinned CLI1.0.7 — doctor OK.
Это принятие узкого исправления; T117/T118, installed acceptance, настоящий
сервер и аппаратные gates остаются открытыми, задачи/reviewer markers не менялись.

## 2026-11-04 — полный Release checkpoint и новая основа master

Lifetime fix сохранён и отправлен в76ad794c2394e651adde74bd722414e0e8f5515c.
Первый SSH push отказал publickey; повтор через существующий gh credential
helper/HTTPS прошёл без изменения remote/auth settings. PR7331 остаётся draft,
REST подтвердил exact head/body; gh pr edit отказал из-за Projects classic,
поэтому использован штатный REST PATCH. Metadata по точному SHA отказывает
только на expiry; исключение не продлевалось, merge/release не выполнялись.

Из exact checkpoint Main выполнил полный GrafWindows.sln Rebuild Release x64:
exit0/host0, machine0x8664, fresh AppMain.obj и production EXE без test payload
markers. EXE SHA256 `e32744dbde830f381f94a4bd1971eb741199e9e0d02741699a7f32adae89d057`,
AppMain.obj `5c6139ec7d32eeb8370da54b85c481e3e29de3268ab2dc72f7f14bb18afeda9f`.
Source225 до/после совпали,24 Debug test EXE и installed0.1.0.15 сохранены;
build_processes0/no-force. Установка/запуск/звук/trust не выполнялись.
Result SHA256 `58e7a39492a9e71d36f969b8f85c103ab9855ad9edb17934ca8d5b87468fc2e4`.

Read-only inventory пользовательского root подтвердил legacy ledger и
отдельный quarantine без protected store.id. Только существование/размеры,
без чтения содержимого; записи/ключи не менялись. Неизвестный quarantine
остаётся блокирующим; generated migration PASS не разрешает его обход.

Свежий remote master перешёл с20393b9b… на5485b92ec3489b8c39b8e6f23c8667d8fa286b5f:
F292 sharing и подготовка релиза. merge-tree подтвердил clean merge, затем
master принят через --no-commit без переписывания feature history. Входящие
изменения Mac/server/CHANGELOG сохранены как опубликованная основа; собственных
правок серверной логики или сборки корневого CHANGELOG не выполнялось.
Source225 Windows совпадают с проверенным checkpoint. Новая функция Mac
выявила отдельный HIGH: Windows не обрабатывает shared-meeting activation,
новые public reader routes и auth continuation с вкладкой/позицией. После
независимого bounded convergence review добавлена открытая T121; это не T106
attribution и не T119 calendar join. Runtime allowlist пока не расширен.

На совмещённых общих страницах первый pytest selection:218 PASS, один отказ
из-за отсутствующего локального .venv пути и две setup errors без isolated
PostgreSQL. Это ошибки подготовки, не квалифицированные product RED. Подключён
существующий Python environment временной локальной ссылкой, без установки
или изменения пакетов; после проверки удалена только эта созданная ссылка. Непройденные случаи и новая F292 integration проверены
штатным run_local_postgres_tests.sh --focused с UV_NO_SYNC=1:16 PASS25,42s,
phase pass30s, isolated_container_removed. Новые public-sharing/owner/auth-return
browser проверки входили в первоначальные успешные случаи. Настоящий сервер
и пользовательские данные не использовались; полнота Windows sharing не заявляется.

Независимое bounded SOURCE review объединённых четырёх общих файлов и
Phase21/T121 — C0/H0. Подтверждено121 задач/93 checked/28 open; старые
задачи и reviewer-owned checklists не менялись. Новая T121 сначала требует
уточнения spec/contract/plan/quickstart, review/analyze и issue sync; внешний
issue до нового analyze не создавался. Продуктовый Windows allowlist не менялся.

## 2026-11-04 — исходная регрессия перед T117 delete/purge cleanup

На source HEAD `c3c07df72d5b5599393cd97286b06d620a046320` выполнен прежний
`NativeProtectedPurgeFlight`: 1/1 PASS, 88,28s, CTest/host exit0. Новые тесты
cleanup ещё не применены; это исходная регрессия, не RED/GREEN нового пути.
Проверены прежние 13 режимов на искусственных данных, включая cold proof;
devices/audio/real network0. Source225 до/после, все24 Debug PE и config110
не изменены; source/build mutations отсутствуют. Installed0.1.0.15 сохранил
EXE `e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`.
Own processes/builds0, штатное завершение, forced cleanup0.
Внешний result SHA256:
`dce0f7d483cca4a104a5a89cb5f3b411fee793a94238491e4813eaaef72e0aef`.
T117, установленное приложение, hardware и release остаются открытыми.

## 2026-11-04 — требования T121, текущий analyze и добавочная issue sync

Применён проверенный docs-r2: spec, bridge§11, plan и quickstart. Patch SHA256
`50a3e969dd779d2d5b7ed4178c221df10573c2b86fbcdfc84c4b46ffc6b42ab2`.
Независимое исходное review C0/H0; M1 о различии UUID syntax/account authority
исправлено. Дополнено native own-session cookie reconciliation публичного
reader без bridge. Точный текущий requirements/checklist gate T117/T121 —
`review-2026-11-04-t117-delete-purge-current-gate-source.md`:477 checked/0 open,
маркеры сохранены. Main analyze текущей дельты после tasks: C0/H0/M0;
22FR/10SC,121 task/93 checked/28 open. Новые технические и пользовательские
сценарии относятся к T121; старые T106/T119 и storage scope не меняются.
Findings реализации в открытых tasks не выдаются за принятый код.

После поиска открытых/закрытых issues через GitHub создан единственный владелец
T121 — #7933. Ensure PASS без изменения управляемых файлов; validate PASS,
272 Spec Kit issues. Дополнена issue-map; закрытий/новых task markers нет.
Продуктовый handler/allowlist T121 ещё не изменён. Приёмка runtime, установленного
MSIX, аппаратуры и release остаётся отдельной.

## 2026-11-04 — T117 test-only r2: ранний отказ, не целевой RED

Test source `c02d301fb1aa12f1d8b8cebd70cd36a265005ec25e05e07d54fcd7115233ce5e`
собран: build0. Старые13 purge-flight режимов прошли; новый сценарий остановился
на немедленном beginProtectedLocalPurgePass, до проверки cleanup. Case8/host1;
qualified_red=false. Причина конкретного отказа не установлена этим журналом.
Terminal guard подтвердил source225/config110, неизменность23 посторонних PE,
installed hash, source attributes, own/build processes0; forced cleanup0.
Production не изменён. Отдельный reviewed r3 меняет только admission ожидание
на существующий waitFor/pollUploads с прежними10s/CTest240, без обхода guards.
R2 сохраняется как неквалифицированный отказ, не доказательство дефекта cleanup.

## 2026-11-04 — T117 delete_purge: квалифицированный r3 RED → GREEN

Reviewed test-only r3 `699af8ac70100a5967be1563c270d5c8ff72fe7f51cce26a844a495b25ca407c`
на прежней production: build0/CTest8/host0,88,55s. Все13 старых режимов прошли;
новый positive прошёл adopted intent/generation, purge ACK и package absence,
затем отказал на точном assert4911: migration original остался. Это целевой
RED, независимо квалифицированный reviewer, не ранний admission/fixture отказ.
Result SHA256 `d125084a532bb46211a4991bac23a949015ea7b7293c5dc0e314a77931456c7f`.

После RED применён reviewed production patch
`955e03ccc738117a0b0906d2b5a3c2c0e3055993d218fe699dc5f38c63ab6587`:
NativeCapture передаёт origin в существующий server-purge continuation;
StoreOwner связывает cleanup с одной accepted operation/receipt, точным
account/workspace/origin и правом на все historical rows. Существующая
authorization не перепривязывается. BOTH pending до unlink и actual absence
до BOTH complete сохранены; history/job leases освобождены до recycle.
Новый parser/schema/очередь и startup/GC cleanup не добавлены.

Тот же test r3 с новым кодом: build/CTest/host0,1/1 PASS140,35s при прежнем
CTest240. Прежние13 и новые10 режимов, включая cold recovery/negative rights,
прошли. Result SHA256:
`a2c01e70020e456cfc18f58026948841d038e115479fc3abdb37279fcde215b2`.
Source225/config110 exact; изменён только Native test PE,23 прочих сохранены;
installed0.1.0.15/EXE hash и attributes сохранены, own/build processes0,
forced cleanup0. Это generated/source-qualified срез, не installed/hardware
приёмка. Partial-unlink/restart, busy/OOM/cancel внутри нового cleanup пути
и следующий unrelated purge не объявляются покрытыми этими10 режимами.
Неизвестный пользовательский quarantine не читался/не менялся. T117/T118 открыты.

## 2026-11-04 — T117: соседние пути и полная прежняя migration-pair регрессия

После GREEN на тех же225 исходниках пересобраны существующие
ProtectedCustodyFilesTests и NativeCaptureStartupTests: build0.
NativeCaptureStartupTests, NativeProtectedReadModel и
NativeProtectedLocalRemoval:3/3 PASS,88,30s. Затем отдельный прежний
ProtectedCustodyFilesTests --migration-pair завершился exit0, с обоими
linked_end/protected_end. Проверены прежние schema1/schema2 queue/package
матрицы, включая allocation/cancellation cuts и retry; эти проверки не
подменяют ещё открытые fault cases нового server-purge cleanup.

Host0/terminal=true; source225 до/после, configuration110 неизменна.
Из24 Debug PE пересобраны только два выбранных target; остальные22 сохранены,
включая GREEN Native EXE. Built/post PE совпадают, source attributes сохранены.
Installed0.1.0.15/EXE hash прежний, own processes/builds0, forced cleanup0.
Внешний result SHA256:
`2dee0086c73908ff2585b22c4ff881db2c2b1e7ae54fc7f648e66101af8a178d`.
Независимое SOURCE/runtime и Ponytail review T117 production-r2/test-r3:
C0/H0; новые parser/schema/framework не добавлены. Полная F200, installed,
физическая x64, 60min/AEC, публичная подпись и release не приняты.

## 2026-11-04 — T117: полная Release x64 сборка текущего исправления

GrafWindows.sln /t:Rebuild /p:Configuration=Release /p:Platform=x64:
build0/host0, terminal=true, active builds0. Проверено реальное обновление
AppMain.obj и EXE, machine0x8664; test payload markers отсутствуют.
Production EXE SHA256:
`0b4ef451a37dbb1ed0fa7ab3b8f73d7a4b23ac9e5d4fe8d1cb167c6713b728b0`.
Result SHA256:
`69d57f752a7f16743a013dd646823b7ffc1367af22546ff1159fbd20b4dec9a1`.
Все225 исходников до/после и в Main совпадают; все24 Debug test PE и
установленный EXE сохранены. AEC3 проверен существующим provenance validator.
Установка/запуск, чтение аудио, сеть и изменение доверия к сертификатам0.

Scoped convergence сверила остаток T117 и требования T121 с действующими
владельцами: новых дублирующих задач0;121 task/93 checked/28 open. Это не
полная сходимость F200. T117/#7445, T118/#7446 и T121/#7933 остаются открытыми.
Governance и frozen doctor проходят с закреплённым проектным CLI1.0.7;
глобальный CLI1.2.6 не заменялся. YAML fragment и whitespace проверки PASS.

## 2026-11-04 — переносимая сборка и состояние установленного клиента после входа

Checkpoint2282a715f0d49344320fff2a28205aa00d64ffd7 закоммичен и отправлен;
все225 Windows inputs прежних runtime/Release проверок сверены с его Git bytes.
PR7331 остаётся draft; новая локальная проверка его metadata отклоняет только
истёкшую дату legacy exception, не продлённую этим этапом.

При отдельной переносимой проверке обнаружены три -Wunused-parameter/-Werror
в не-Windows заглушках новых параметров. Это compile failure, не runtime RED.
Исправление: два существующих #ifndef _WIN32 участка, только void casts.
Windows ветви не меняются. На текущем Main Debug build0, существующие
WebViewRoutePolicyTests/WebViewBridgeEnvelopeTests/WebView2HostLifecycleTests:
3/3 PASS1,23s. Source SHA256 ProtectedCustodyMetadata.cpp:
`28f1fd1fe78078cbd82cccc59386de8ff9c85ad5190e2247f44cf22f467e4ac0`.
Новая редакция не выдаётся за точные225 inputs предыдущей Windows сборки.

Отдельная read-only сводка установленного0.1.0.15 после сообщения о входе:
package Ok, процесс1; старый JSON-реестр v3 содержит12 строк, у9 заполнены оба
поля владельца, у3 оба отсутствуют. Это наличие полей, не подтверждённые права
текущего аккаунта. Рядом есть неизвестный quarantine382bytes;
служебного custody-каталога, store ID и оригинала ledger нового формата нет.
Прочитаны только реестры/форма служебных файлов; медиафайлы и известные файлы
ключей не читались, неизвестный контейнер не расшифровывался, содержимое и
идентификаторы не публиковались. Файлы/права/установка не менялись.
Этот inventory не разрешает очистку quarantine, присвоение неизвестных строк
вошедшему пользователю или создание пустого хранилища вместо прежнего.
T117 recovery и проверка установленной записи остаются открытыми.

Уточнение классификации quarantine: диагностический скрипт назвал non_json
файл, первый байт которого не равен открывающей фигурной скобке. Это не полная
проверка JSON/BOM/encoding и не установленный формат контейнера. Его тип и
происхождение остаются неизвестными; вывод не даёт прав на очистку или импорт.

## 2026-11-04 — синхронизация с master2ca без конфликтов

После отдельного portability checkpoint0caf84c94 включён master
`2ca0465aa1721be293cd9b479d8f9d75b8854bfa`; merge HEAD
`d876c885d03095e129c0653511ec5eb7c4b5c4fc`. Конфликтов нет. Windows/Mac
исходники входящей дельтой не менялись; три общих server-файла совпадают с
master побайтово. Корневой CHANGELOG получен только из master, вручную не менялся.

Штатный run_local_postgres_tests.sh --focused с существующим окружением,
UV_NO_SYNC=1:79 PASS7,59s, phase PASS12s, runner exit0/19,719s,
isolated_container_removed. Проверены playback normalization contract,
recording share UI, workflow accessibility, RLS policy/table inventory и
billing reconciliation unit tests. Новые зависимости/серверы не установлены;
рабочий backend и пользовательские данные не использовались. Внешний result
SHA256 `ee5934d6142fbeb17f47f7a200417d8ae3898d6e84245e5f8317ea61c982ccfe`.
Это направленная проверка совмещения, не release-full или live UI/audio.


## 2026-11-04 — T121: строгие маршруты общей встречи и изоляция публичной страницы

На Main0bf9 применён проверенный route-policy r2, только существующие
WebViewRoutePolicy.cpp/.h и WebViewRoutePolicyTests.cpp. Разделены публичный
reader и media resource, проверяются точные paths/query/fragment, UUID,
token/version/position и граница16KiB. Public reader/continuation/media не
получают native bridge, local inventory/actions или native/blob download.
Обычные auth/payment/frame правила сохранены.

Независимое SOURCE/Ponytail review выявило в r1 M1: encoded alias shared-family
в frame мог пройти общий same-origin allow. r2 распознаёт такой alias до общего
правила и только отказывает: decoded/normalized path не становится URL для
навигации. Реальный тест на r1 build0/CTest8, точная assertion
T121_noncanonical_shared_frame_must_be_denied; тот же тест r2 build0/CTest0.
Старые assertions, включая предыдущие89 строк T121, сохранены. Lorentz повторно
проверил исходники, оба полных патча и43 terminal artifacts: C0/H0/M0, SOURCE GO.
Полный production patch SHA256:
`11a07be40c57c44a810ca06ed4f28584d34e4861c2a4c5da2dc4e20e45a82c00`.

Main независимо сверил43/43 pins и затем собрал текущие файлы: build0,
WebViewRoutePolicyTests, WebViewBridgeEnvelopeTests, WebView2HostLifecycleTests,
CalendarJoinHostTests и ProductAttributionHandoffTests:5/5 PASS2,59s.
Все tracked Windows bytes до/после совпали. Исходники проверены как dirty diff
на0bf9, без выдачи результата за будущий commit/installed build. Result SHA256:
`2fc03be45f1a03a273f081b73491a301ae38d9219162d4c0f4604260063f1787`.

Отдельный test-only Host lifecycle кандидат получил квалифицированный RED
T121_public_HTML_must_display_without_native_authority на прежнем Host и
закреплённой policy r1. Independent C0/H0/M0; прежние346 asserts сохранены,
добавлены35. Main сверил35/35 pins. Это доказательство следующего пробела,
не уже применённое исправление Host. Policy r2 сама не закрывает protocol
activation, public HTML/cookie lifecycle, recovery или T121/#7933.
477 требований checklist/0 open и current analyze C0/H0 сохранены;
полная F200121/93/28, installed/SDK/hardware/release acceptance не меняются.

## 2026-11-04 — T117: уточнение формата существующего quarantine без изменения данных

После входа пользователя отдельная read-only проверка16bytes обнаружила
UTF-8 BOM, не custody envelope. Следующий bounded strict UTF-8/JSON разбор
после снятия BOM показал известное имя schema desktop-upload-queue.v2 и массив
из1 непустого item; оба owner-поля отсутствуют, deletion operations0,
purge acknowledgements0. Основной schema v3 ledger:12 items,9 с обоими
owner-полями,3 без обоих, operations0/acks0. Это структурный разбор, не принятие
строгого queue codec, происхождения, целостности или прав на строки.

Первоначальная диагностика по первому байту была недостаточной. Промежуточные
PowerShell counts для отсутствующих arrays были исправлены: @($null).Count
не равен числу операций. Приняты только исправленные non-null counts.
Содержимое/IDs/пути записей не выведены; keys/media не читались, расшифровки0,
изменения данных/ACL/install0. Header probe подтвердил неизменность length,
attributes и last-write. Установленный0.1.0.15 StatusOk, процесс1.
Новый .custody-v1/store.id/legacy.originals отсутствует. Известное имя schema
не разрешает удалять quarantine, назначать владельца или создавать вместо
него новую пустую authority; нынешний recoveryRequired остаётся действующим.
Нужен отдельный безопасный recovery в пределах T117, без обхода контракта§7.
Сводка и pins диагностических скриптов SHA256:
`278b6620c8c69cfbb58bdf742e4f4fbb470505e2c090b501a6d81ad797774810`.


### T117 — установленный кабинет и точное происхождение старого тестового файла (2026-11-04)

После сообщения пользователя о входе видимый кабинет установленного GRAF
загрузился. Кнопка начала записи оставалась недоступна с ошибкой защищённого
хранилища, автоматическая запись приостановлена. Это наблюдение не принимает
T097, запись или отправку. Приватный снимок просмотрен и удалён; содержимое
встреч в доказательства не переносилось.

Повторная проверка истории DSH, которую пользователь ранее попросил изучить,
нашла создание искусственного однострочного v2 ledger в записи12664 исходной
сессии. Историческая команда не запускалась: из неё строго извлечены только
литералы package/row/doc, разрешена единственная подстановка LOCALAPPDATA,
ожидаемые JSON bytes с UTF-8 BOM рассчитаны в памяти. Текущий карантин имеет
ровно382bytes и SHA-256 `8a5be90dd7baef65c06b85453232aaa67221149eb38d5dc2d69b29ff0b3323df`;
ожидаемый тестовый файл имеет те же длину и SHA-256. Его last-write UTC —
2026-09-17T20:15:23.7750782Z. Исторический журнал
`validation-2026-09-17.md` описывает этот BOM-файл как артефакт первой версии
скрипта и восстановление исходного реестра после проверки.

Metadata-only receipt `historical-bom-fixture-match-20261104.json` находится
в закрытых материалах текущей проверки. SHA исходной записи истории —
`8f11c4d1a19a28f130d1d6a65f681a748672a430967d08d7cf459479f7a1828d`.
На данном этапе очистка не выполнялась. Для неё отдельно нужны независимая
проверка происхождения, завершённый GRAF и удержание точной native file identity.
Рабочий реестр, пакеты, владельцы, ключи и ACL не менялись. Общее правило
отказа для неизвестного карантина остаётся обязательным; это не разрешение
автоматически удалять карантин клиентов или назначать владельца старым строкам.


### T121 — совместный parser/recovery/Host checkpoint (2026-11-04)

После отдельного независимого SOURCE review C0/H0/M0 в текущую рабочую копию
включены строгий protocol parser, сохранение shared query/fragment при recovery,
показ подтверждённого публичного HTML без native bridge и fenced native чтение
собственной session cookie. Sealed server continuation cookie клиент не читает.
CookieManager/SourceChanged ветки ещё требуют настоящей Windows SDK проверки.

Совместный Host r1+recovery тест сначала обнаружил потерю fragment в correlated
response: HTTP request URL его не содержит. Однострочная поправка использует
уже связанный `navigationUrl_`; проверка correlation, метода и origin сохранена.
Тесты между FAIL и GREEN не менялись. Независимый review поправки — SOURCE GO.

Добавлен `RouteEvaluation::userInitiated=false`: только принятый native Starting,
который сам WebView2 отметил как user-initiated и не redirect, выставляет true.
Поле сообщает об явной замене страницы и не расширяет допуск маршрута. Этот
native event path прошёл SOURCE review, но portable запуск его не исполняет.

На actual Main заново собраны пять существующих targets: RoutePolicy,
BridgeEnvelope, HostLifecycle, CalendarJoinHost, ProductAttributionHandoff.
Build0, CTest0, **5/5 PASS**, 2.67s. Все225 tracked Windows inputs до/после
побайтно совпали. Материалы `t121-main-combined-20261104`, result SHA-256
`9a88f4b222ae78c5c10fdbb149b436562850b2f34a43e6cd73819c053f09dcc2`. Это текущие локальные исходники с diff, не evidence коммита или MSIX.

AppMain cold/warm activation и существующая ShellClose SDK фикстура находятся
на отдельном SOURCE review; в этот совместный PASS они ещё не входят.
T121/T097/T063 и внешняя приёмка остаются открытыми. Текущий master повторно
сверен с GitHub: `2ca0465aa1721be293cd9b479d8f9d75b8854bfa`, уже в ветке.
GRAF завершён обычной командой трея: один процесс до, ноль после, forced=false.


### T121 — AppMain, полная Windows SDK сборка и настоящая оболочка (2026-11-04)

Lane: high-risk-product, существующая T121/#7933. После независимого SOURCE
review всей связанной цепочки C0/H0/M0 включены общий обработчик protocol
activation, один latest-valid pending local route и подтверждение принятия
по revision. Парсинг идёт до mutex, навигация вне mutex; невалидная ссылка
не стирает допустимую, более новая ссылка во время open не теряется. Cold
configure и warm dispatch используют один путь. Подтверждённая смена session
cookie/owner tuple, принятый пользовательский переход, нативные кнопки и выход
отменяют pending. Unknown/same-cookie read не считаются logout. Старый
calendar resolver отзывается до перехода и не может заменить reader своим login.
Сохранены прежние attribution, capture/update, account и document gates.

AppMain SHA-256:
`b35c41239f1ec8acae9ff9b3bff3570c30c3e5350486681955d67e8b5fcc3630`.
Существующий AppMainShellCloseUiLaunch.inc дополнен ограниченной prephase;
прежние девять фаз, шесть закрытий, два повторных открытия и 8000ms deadline
не переписаны. Production fixture helper подтвердил 17 неизменных методов.

Фактический full solution Rebuild Release x64 прошёл build0, terminal=true,
225 source inputs. Production EXE SHA-256:
`863bb8e17172a1c49d5d13d8ddafb8011ae6eddb3afbc379d28ea3407e3f7b44`;
AppMain.obj `8ef87db55572c0f38d90d17c01e453aa7a9b47a4b8420e8804e226a6e5fc22ca`.
Fixture markers отсутствуют. Receipt result.json SHA-256:
`cf554dbe6f9daf2e1be053883e3609f278fe3d63df36a99aa6ca0c0407d69d5b`.
Это текущий diff над HEAD0bf9bd4c57212731243d36b13be883746fd34678, не
доказательство нового коммита либо установленного MSIX.

Два предварительных запуска runner остановились до компиляции: сначала
show-only multiconfig CTest был вызван без -C Debug, затем копирование одного
из owned source отказало из-за ReadOnly. В r3 зафиксированы Debug и сохранение
исходного ReadOnly вокруг точного копирования. Конфигурация не менялась;
предварительные отказы сохранены отдельно, не названы ошибками продукта.

Отдельная SDK derivative собрана build0; заменены ровно AppMain и test-only
vcxproj. EXE `f09d6dfb9eae7a8aa61afa1b25d96418e93e6175d0adefafca01ae8aa9b6885d`.
Реальный WinUI запуск завершился штатно exit73, terminal=true, forced=false.
Ровно по одному подтверждению prephase PASS, закрытия pending/rejection после
exit и исходного SHELL_CLOSE terminal: phases9/closes6/reopens2/quit1,
drained1/lease_released1/no_files1. Проверены cold-before-cabinet, latest-valid,
невалидные/слишком длинные UTF-16/UTF-8, A→B во время open, update pause/resume,
closed host/reconfigure, known session change/logout, unknown read и выход.
Native WebView/profile/root/account worker prephase — 0. Звук/устройства,
настоящая сеть и сертификаты не использованы. Receipt fixture-run-result.json:
`5c9fd786b5c35d0c3e60d863321eecabf8b98fc40ae37070674857e167a7933e`.

До/после сборок и запуска сохранены 225 inputs, прежняя CTest конфигурация110,
24 посторонних Debug EXE и установленный0.1.0.15. Это проверки неизменности,
не повторное исполнение110 тестов. После test derivative назначено отдельное
восстановление production inputs и полный Rebuild; его результат записывается
отдельно. Без него test EXE не упаковывается и не устанавливается.

Actual CookieManager/SourceChanged/public response, реальный single-instance
protocol dispatch, same-cookie owner switch, history-busy и установленный
MSIX cold/warm ещё не приняты этим device-free запуском. T121/T097/T063 и
остальные открытые задачи, физический x64, release/signing gates не закрыты.

### T117 — ограниченная очистка: SelfTest PASS, рабочая проверка отказала (2026-11-04)

Для удаления только ранее доказанного искусственного382-byte quarantine
подготовлена отдельная одноразовая операция, не код продукта. Независимое
ревью r1 обнаружило отсутствие фактического GrafWindowsApp в process guard
и чувствительное к регистру сравнение protected-root имени; оба исправлены
двумя локальными строками в r3. Итоговое SOURCE GO C0/H0/M0. Скрипт r3 SHA-256:
`881dcffcc48fc7a303a5d15f2b9f01c1e70d17c24ee07d2c426f1778c8687de6`.

Windows SelfTest: несовпадающий файл сохранён, точный искусственный файл удалён,
собственные временные объекты штатно очищены; SELFTEST_TWO_CASES_PASS, process0.
Следующий отдельный Inspect рабочего root остановился UNKNOWN_ROOT_FILE,
stage inventory, ReadOnly=true, DeleteRequested=false. Отдельная metadata-only
проверка показала кроме ledger7647bytes и quarantine382bytes ещё один корневой
файл5709bytes с именем из семейства queue. Его содержимое не читалось;
audio/keys не читались. Apply не назначался и никакие рабочие файлы не удалены.
Причина и допустимый способ сохранения этого дополнительного объекта требуют
отдельной проверки; расширение допуска неизвестных файлов не выполнено.


### T121 — возврат к production и текущая проверка полноты (2026-11-04)

После штатного завершения SDK-сценария восстановлены ровно AppMain.cpp и
vcxproj из проверенных production donors. Атрибуты сохранены, все225 source
inputs вновь совпали. Полный solution Rebuild Release x64: build0,
terminal=true, own_processes0; свежие AppMain.obj и production PE0x8664.
ForcedInclude и test payload markers отсутствуют. Новый production EXE:
`9509d32c6091087bc43bdfc0fff07897efe1204f581ed0057f37717a419b7a29`;
AppMain.obj `7de3549f3d15d200d652e7f0a87f899a8d9978e47b4debe9cbe54161a74f6bab`.
Receipt restore-production-result.json SHA-256:
`4f750493e74e826cb469338ca2d414937673c6d44a9ac7c87dc293f4fb449e94`.
Конфигурация110, все24 Debug PE и установленный0.1.0.15 неизменны.
Установка/запуск production EXE, устройства, звук, сеть и trust — 0.

Независимая оценка converge по текущим code/spec/plan/tasks не обнаружила
новых пробелов без существующего владельца в проверенной области.22FR/10SC,
121task/93checked/28open; T121 остаётся открытой до настоящих WebView2 и
MSIX сценариев. Остальные незавершённые требования принадлежат существующим
T063/T071/T083/T087/T088/T094–T097/T101–T113/T116–T120. Новых дублирующих задач
не добавлено; tasks.md побайтно сохранён. Это partial assessment, не
объявление F200 converged. Reviewer-owned checklist counters31files/477checked/
0unchecked проверены без изменения отметок; они не означают готовность продукта.

Governance, YAML и diff whitespace — PASS. Doctor с глобальным CLI1.2.6
правильно отказал из-за несовпадения с project lock1.0.7; с уже имеющимся
закреплённым CLI1.0.7 --doctor --frozen PASS. Lock/skills/расширения не менялись,
новые зависимости не устанавливались. GitHub head/base проверки после нового
коммита обязательны; expired old-reader exception сохраняет merge/release HOLD.


### T117 — точная очистка исторической искусственной пробы (2026-11-04)

После checkpoint коммита f5d61539fc0fbcdd4a05f7416054fa1ac8e2ea57
независимая проверка исходной DSH-сессии подтвердила назначение дополнительного
файла5709bytes: это desktop-upload-queue.v2.before-migrate, созданный Copy-Item
до синтетической пробы и позже использованный для восстановления реестра.
Сопоставлены SHA имени, команда12664 и её сохранённый результат12670. Это
не доказывает нынешние bytes и не разрешает удалить backup. Он сохранён.

Однострочный r4 допуск этого точного сохраняемого имени не выдаёт ему DELETE,
не читает/не хеширует содержимое и не меняет production migration allowlist.
Все прочие неизвестные root files по-прежнему отказывают. Независимое полное
337-line review: SOURCE GO C0/H0. Script r4 SHA-256:
`e55b900ec63fdf459add59ae3677bc10f7f4c4fb83a6a0c36c805d57b1b1204d`.
Отдельный r4 Windows SelfTest PASS2cases и temporary cleanup PASS; прежний r3
SelfTest не использован вместо его исполнения.

Рабочий r4 Inspect: INSPECT_EXACT_FIXTURE, Success=true, readonly, process0,
67entries/13directories; snapshot и retained hashes до/после совпали.
Только после чтения этого результата отдельно назначен Apply. Он завершён
штатно EXACT_FIXTURE_REMOVED: Success=true/DeleteRequested=true/AbsenceProved=true,
67→66entries. Все13directory objects сохранены. Ledger7647bytes SHA до/после:
`569cd2d8f42d682239f9eaaabd1732b6521288561be44af0c175864950d237fe`;
retained metadata snapshot до/после:
`c269805ec9bf28108ad544a8729516c073bd7e52e612eda8b5d81d5bb7bdffdd`.
Удалена только точная382-byte искусственная проба по её удерживаемому handle.
Пакеты, backup, владельцы, ключи и ACL не менялись; audio/key content reads0,
копий0, migration0, app launch/install0, trust changes0. Process guards0.

Receipts SHA-256: SelfTest
`f3142e6a9b9d9c0c499ef17126bb4513eaa5a8801ac2724659d677440d57aab6`;
Inspect `961f6ad4d6af20a5694d2d8b1d62559a73249b7537c61626b520ea09f06117c3`;
Apply `296e94c3ee82288fa053dea8f85556c52a322c9cb21eaa6b331079e4d0fe7d75`.
Это отдельная локальная операция над доказанным тестовым артефактом, не новый
автоматический cleanup клиентов и не готовность T117. Сохраняемый backup
остаётся дополнительным root file; его безопасное сохранение вне active root
требует отдельной проверенной операции. Запись ещё не объявляется разблокированной.


### T097 — обновление установленного MSIX до 0.1.0.16 (2026-11-04)

Исходник: f5d61539fc0fbcdd4a05f7416054fa1ac8e2ea57 и единственное отличие
225 Windows inputs — development manifest0.1.0.15→0.1.0.16. Это внутренний
тестовый пакет, не публичный CalVer-релиз. Полная повторная компиляция через
существующий packaging project Build Release/x64 завершена build0; свежие
production EXE/AppMain.obj, PE0x8664, test payload отсутствует. Подпись
существующим сертификатом CN=GRAF: Valid; новых сертификатов, изменения
доверия, экспорта ключа и timestamp-запроса нет. Статический smoke PASS;
проверки валидатора6/6 signature,2/2 native WebView2,6/6 resource-language PASS.
Source225/configuration110/Debug24 и прежняя установка до update неизменны.
Временный packaging output удалён после terminal acceptance; итоговый MSIX
и журналы сохранены вне Git.

MSIX SHA-256:
`275320838343c225e5718d8ec48dd07e03578e61ae838a0548228efe0589e549`;
его payload EXE и установленный EXE совпадают:
`7aacbc65019bebb8c76bbce10dd31ff60a9077dbc786150790ebcab6c84d26c3`.
Обычный Add-AppxPackage обновил0.1.0.15→0.1.0.16, StatusOk; без reset,
uninstall, Force или запуска интерфейса. Все22 файла содержимого пакета
проверены по SHA. Метаданный снимок пяти областей пользовательских данных
до/после совпал, доверие к сертификатам неизменно, source225 повторно совпали.
Содержимое рабочих записей, ключей и cookies не читалось. Отдельная
IApplicationActivationManager-активация точного установленного AUMID с
--verify-audio-backend: exit73, terminal=true, без принудительного завершения,
устройств и аудиозахвата. Это доступность настоящего AEC backend в MSIX,
не приёмка живой записи и не T097/T118 completion.

Receipts SHA-256: build
`ce120469c32f0fa192e84789dc3c92355720bd148898aa8d8afc4aa1871adc24`;
install `96c2ddaa7e086c828b638962bf5f900962debef6c5ef5064e83bf548527231cd`;
packaged AEC `b5db763087ca836bdde546bb7cd12d3d11eff66e15003531c3506839efad83d1`.
Предыдущая попытка packaging r2 штатно отказала до MSBuild на запрещённом
вложенном PowerShell-файле, сохранив manifest0.16 и остальные inputs. Для
успешного r3 разрешение Bypass задано только процессу проверки; постоянная
ExecutionPolicy, registry, UAC и trust не менялись. Прежний отказ сохранён.

GitHub governance-fast41895822528 и macos-pr41895822570 завершены success
для точного f5d61539fc0fbcdd4a05f7416054fa1ac8e2ea57. Общий validator
PR7331 всё ещё отказывает: pr-metadata не принимает истёкшее old-reader
исключение. Срок не продлён; merge/release HOLD сохраняется до T117 retirement.
Живая UI/Record, cold/warm shared activation, hardware и clean-image gates
этим обновлением не закрыты.


### 2026-11-04 — T117: сохранение прежней резервной копии и T097: первый обычный запуск 0.16

Под ранее подтверждённым порядком восстановления выполнены отдельные SelfTest,
Inspect и Apply узкой операции переноса единственной известной прежней резервной
копии очереди. Это прежний файл5709B, не вновь созданная копия. Native rename
сохранил тот же файловый объект, размер, время изменения и права файла; очередь
7647B и метаданные остальных объектов совпали до/после. В активном дереве66→65
объектов,13 каталогов без изменений. Новый отдельный каталог восстановления
создан сразу с правами только текущего пользователя. Существующие права
исходного файла и родителя не менялись. Рабочие записи, очередь и backup не
удалялись; содержимое backup не читалось и не копировалось. Прежний открытый
backup остаётся plaintext exception, не доказательством полного шифрования.

SelfTest подтвердил сохранение объекта неверного размера и перенос того же
объекта правильного размера; временные искусственные объекты удалены. Прежние
кандидаты с неподходящей проверкой прав/Win32 rename87 завершились отказом,
без переноса рабочего backup; их не выдают за PASS. Успешный кандидат использует
существующий в продукте handle-relative NtSetInformationFile с проверкой обоих
статусов. Проверка исходника независимым агентом: C0/H0/M0.

SHA-256 операционного скрипта:
`e803ef37f6f3d63cc76c98a442fd1b2447cbfdf488465d309b120f0ecb677f9e`;
SelfTest receipt `dfd0b129146101cc603454110779cfcfd72020f89e7c617059e15a9596e64ac5`;
Inspect `7052e200fbef0a1701cf2fd42082cab95c262091f682116b236b5b69b6c9b24c`;
Apply `c7aaa896cead328af515667c1f99b6e5bd2f51de1232ea6da3444de91c68fabf`.
Частные пути, файловые идентификаторы, права в исходной форме и хеши
пользовательского содержимого сохранены только в локальных закрытых материалах.

Обычный запуск установленного GRAF0.1.0.16 показал общую страницу встреч
с действующим входом. Однако нативная панель всё ещё сообщает о недоступности
защищённого хранилища; «Начать запись» отключено. Root без .custody-v1;
сохранились12 прежних каталогов и очередь. Проверка source выявила отдельный
барьер: lockRoot требует privateAcl текущего пользователя, у прежнего root
права унаследованы. Это ещё не точный runtime-код ошибки и не разрешение
ослабить privateAcl либо автоматически менять права существующих данных.
Migration/Record/T097 не объявлены принятыми. UI-снимок с частными данными
остаётся вне Git. Перед изолированным тестом приложение штатно завершено
через собственную команду трея; exit подтверждён, force не применялся.


### 2026-11-04 — T121: настоящий WebView2 public reader / own cookie / возврат

Добавлен только явный сценарий shared-reader-session в существующий native
fixture и loopback helper; прежний набор по умолчанию не меняется. Три фазы:
собственный кабинет → публичная общая страница → собственный кабинет.
Все данные искусственные; настоящий CookieManager читает собственную cookie,
реальные correlated GET/HTML200 и navigation completions подтверждаются
независимыми наблюдателями. Fixture не назначает host identity/ready/nonce.

RED со старым Host de710ea7… и текущими совместимыми header/route/test inputs:
сборка PASS, первая privileged фаза PASS, затем actual public GET/HTML200,
но targeted failure shared_public_reader_must_reconcile_own_cookie_without_bridge,
state0. Fixture exit1, server exit0, counts2/0/0/0/0/0, browser exited PASS.
Это воспроизведение дефекта допуска публичной страницы, не setup/TLS/build fail.

GREEN с текущим Host: все три фазы PASS, cookie reads3, bridge1/0/1;
на публичной странице отсутствуют nonce/bootstrap/local publication, семь
реально полученных forged запросов не дали native effects. Возврат требует
нового genuine nonce и повторного настоящего bridge callback. Fixture/server
exit0, counts3/0/0/0/0/0, временный профиль удалён; wrapper terminal/accepted
true и own_processes0 в обеих фазах. Установленный0.16,225 production inputs,
24 Debug EXE,110-test configuration, Release runtime и generated headers
не изменились. Гостевая production tree не получила тестовые наложения.

Независимый reviewer исходников и квалификации RED: C0/H0/M0. Python syntax,
git diff --check, F200 YAML, governance и frozen bootstrap doctor PASS.
Receipt SHA-256: RED
`a77f34e863e8b4a9e595b6927207bc335455d3f9617ee4d259e7ce0dcce77b33`;
GREEN `5bee0f7bb90aeba8dae1741aa1130de8e5fc7c7a64b0fbfec04b27d0bc7d7aea`.
Runner `7a4421b070538b67412eef6b42bf51d1f539d1dc92932d2ce02af10cde097cf0`;
patch `1342c04d063c598a477569fccf60b36690e4e1dab962ce37b056662e00059172`.

Предел: это direct SDK/WebView2 synthetic native proof, не installed cold/warm
activation, не настоящий серверный login/continuation и не AppMain account
recovery. Детерминированный late-cookie/context и весь T121 остаются открыты.
Аудиоустройства, trust, рабочие записи и сервер не менялись. Тестовые методы
не добавлены в публичный мост приложения.

Независимая проверка полного GREEN журнала,12 receipt-связей и текущей
шестифайловой дельты: COMMIT GO, C0/H0/M0. Все225 Windows-файлов Main
совпали с GREEN manifest. После terminal acceptance два отдельных временных
дерева исходников теста удалены; production tree, установленный пакет и
рабочие записи не затронуты. Итоговые журналы, manifests и receipts сохранены.
