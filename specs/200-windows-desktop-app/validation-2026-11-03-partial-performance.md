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
