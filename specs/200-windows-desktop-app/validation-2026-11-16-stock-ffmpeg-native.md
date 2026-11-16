# T116: настоящая Windows-сборка штатного FFmpeg и первые регрессии

2026-11-16. Полоса: существующий high-risk-product, T116/#7444 и T118/#7446. **Приёмка не завершена; выпуск запрещён до остальных обязательных проверок.**

Исходная ветка `codex/200-windows-stock-ffmpeg-20261116`, HEAD `d32fe13da6ec5d0ad95a8ed26c21d8bbfc05e24f`. Проверялся незакоммиченный снимок исходников; результаты ниже привязаны к манифестам, а не объявлены проверкой чистого Git SHA.

Среда: отдельная GRAF F200 QA ARM в Parallels, Windows ARM64 с исполнением x64, пользовательский сеанс с ограниченными правами. Искусственные данные; реальные микрофон и встречи не использовались. MSVC 19.44.35230 / toolset 14.44.35207, SDK 10.0.26100.0; Debug с активными assertions.

## Сборка зависимости

Штатный FFmpeg 7.1.5 собран в Windows, проверены LGPL-конфигурация, закреплённые исходники/архитектура/состав/экспорты и созданный заголовок с контрольными суммами. Три тестовых EXE собраны успешно. Отдельный фактический dumpbin подтвердил отсутствие startup/delay imports FFmpeg в первой сборке. Независимая проверка сохранённых материалов сборки: PASS в этих границах, без подмены запуска приложения.

Первый build result SHA256: `94aa760db4477465a15bf0d400fee32d9d513de132584492bfb671016ddb8ff4`.
Первый source manifest: `cd9ca1e12bd4e235f62bdfcab2ade6b3df4d932d8b2f4d15c05299e45d4d1b27`, 273 файла до/после.

R2/R3 повторно проверяют тот же FFmpeg prefix и собирают новые EXE в отдельных каталогах. Старые снимки и журналы не перезаписываются. DLL SHA256 одинаковы во всех трёх сборках:

- avutil-59.dll: `a21e8a9130a28b24fb569cc62d469a4da6a4a3eff8df18af086131704e167a70`.
- avcodec-61.dll: `56f696134f4d01db11acc1e4e5ac71daed2672ae5a01b71a1de7d452ee9cc22b`.
- avformat-61.dll: `7e56e5a8c677747bc2e63ac8585504a9ac2026c00fec8b5cfe21c010464d6c9f`.

## Результаты запусков

Во всех трёх terminal collections сверены 273 файла исходников и шесть выходных артефактов до/после; задача завершена, тестовых процессов нет. JUnit, actual exits, планы CTest и журналы сохранены отдельно.

| Проверка | R1 | R2: диагностика | R3: совместимость AAC |
|---|---|---|---|
| T116StockFFmpegLoaderFaults | FAILED | FAILED | FAILED |
| NativeProtectedPlaybackBatches | FAILED | FAILED | FAILED |
| SelectedMicrophoneLossTests | UNKNOWN | FAILED | PASSED |
| ProtectedCustodyCodecTests | NOT_RUN | PASSED | PASSED |
| NativeProtectedShortMediaEngine | NOT_RUN | FAILED | FAILED |

R1: SelectedMicrophoneLossTests содержит assertion, затем CTest timeout 180 с; этот запуск UNKNOWN, а не обычный завершившийся отказ. R2 выводит CRT assertion в stderr и завершает процесс с отказом без модального окна. R3 эта же проверка проходит за 7,85 с.

### R1

- Source manifest: `cd9ca1e12bd4e235f62bdfcab2ade6b3df4d932d8b2f4d15c05299e45d4d1b27`.
- Build receipt: `94aa760db4477465a15bf0d400fee32d9d513de132584492bfb671016ddb8ff4`.
- Acceptance result: `2f9ecd9709b66b05f0653727ccbca7854ce2a5931120056368d31d306468e42c`.
- Материалы: `.dev/t116-stock-ffmpeg-acceptance-20261116/main-t116-acceptance-collection-123628749441`.
- Итог harness: `UNKNOWN`, actual process exit `2`.

### R2

- Source manifest: `0048dbaa6ddc6f6606ac8a407b8363ded4782c1fa81e8880ea242cc5380f3d3e`.
- Build receipt: `d7e869b003e808353339153ee6cea07ac64e69ecdfa224fc8393a98b00132f7e`.
- Acceptance result: `c1bdea179d6fa4d7186c339a00f3264b36f4e9fd5d33811bca32a5764a438b72`.
- Материалы: `.dev/t116-stock-ffmpeg-diag-r2-acceptance-20261116/main-t116-diag-r2-acceptance-collection-125156223311`.
- Итог harness: `FAILED`, actual process exit `1`.

### R3

- Source manifest: `228b13c6dcad9205e01456db9d33f66717d8260cfef420db783b5971e041caac`.
- Build receipt: `c872d9ebab51aeb3dba9d316a5b487f1e8db17f9850372c091b29351f52382b9`.
- Acceptance result: `b17bda711c672a3d18db67e87b4b4de07fff44ded62604a7845f6ccbff9cf22d`.
- Материалы: `.dev/t116-stock-ffmpeg-fix-r3-acceptance-20261116/main-t116-fix-r3-acceptance-collection-130908573661`.
- Итог harness: `FAILED`, actual process exit `1`.

## Подтверждённые причины и исправления

R2 показал MF_MT_USER_DATA размером 17 байт: `000000000000000000000000118856e500`. Старый reader принимал только 14 байт. Новый узкий validator принимает прежний ASC `1188` и ровно `118856e500`: тот же AAC-LC 48 кГц, mono, явное отсутствие SBR. Остальные profile/payload/reserved/size проверки сохранены; заявленная и прочитанная длина совпадают. Сверка с исходным aacenc.c закреплённого FFmpeg подтверждена независимым ревью. Таблица из 229 проверок проходит на Mac с ASan/UBSan и в R3 Windows перед настоящим декодированием.

R3: все batch fixtures 30/310/320/330/10000 мс завершаются normal и проходят первоначальный независимый decode до EOF. Сценарий потери выбранного микрофона на искусственном сигнале и ProtectedCustodyCodecTests проходят. Это не приёмка реальных устройств.

Loader R2 подтвердил ложное module_identity из-за сравнения `C:` и `\\?\C:`. Исправление сравнивает полные канонические пути из тех же открытых handles, сохраняя volume/file ID. В R3 identity проходит, но positive затем отказывает на проверке освобождения файла.

## Оставшиеся отказы

- Loader остаётся 8/16. После успешного полного load/unload inventory пуст, но GENERIC_WRITE к avutil получает native32. Прямая загрузка/освобождение без FfmpegApi ещё не измерена. Причина не объявлена ошибкой Parallels или устранённой утечкой.
- Live-locks baseline rename каталога получает native5 до создания FfmpegApi; работающий EXE лежит в этом каталоге. Тест не доказывает directory pin, пока не появится различающий контроль.
- Parent Fixture cleanup получает native5. Поздняя read-only проба видит только три остаточных файла последнего child; WRITE/DELETE opens у них успешны, DLL уже удалены частичной очисткой. Это не доказательство доступности DLL в момент отказа.
- R3 batch tone loop отказывает при открытии второй группы читателей, пока inspection ещё удерживает первую. Подготовлено освобождение первой группы по существующему образцу SelectedMicrophoneLossTests; новая Windows-проверка ещё нужна.
- R3 короткий контроль ожидает 2048 decoded frames для 30 мс, а FFmpeg + MF SourceReader возвращают 3072 при правильной длительности контейнера 300000 единиц по 100 нс. Старые assertions, пороги амплитуды и допуски не ослаблены. Исследуется корректная обработка задержки кодировщика; прохождение короткого MediaEngine ещё не подтверждено.

## Незавершённые условия

T116/T117/T118 остаются открыты. Нужны оставшиеся native/fault/recovery проверки, полный EOF/частоты/амплитуды/начало-конец, 10/60 минут и SC-003, новый installed MSIX и пользовательские сценарии. Физическая Windows x64/60min/AEC, полный паритет интерфейса и публичная подпись не заменяются Parallels, этой сборкой или отдельными PASS. Новых выпускных утверждений и закрытия issues этот отчёт не делает.

## R4 — время жизни читателей, частоты и отдельная короткая диагностика

Новый Debug build завершился успешно. Единственное отличие 273-файлового
снимка от R3 — тестовый `NativeCaptureStorageIntegrationTests.cpp`; продуктовые
writer/reader и зависимости совпадают. R3 результаты SelectedMicrophoneLossTests
и ProtectedCustodyCodecTests здесь повторно не запускались и не объявляются R4 PASS.

- Source manifest: `58c2603516381a8b9f2e3d639f3346277039264ef2207b33f05c99045d7f8879`.
- Build receipt: `454b0ead30e75dd9816e8ea454e84f9e852d3b6c90928759c61879f03b9636bf`.
- NativeCaptureStorageIntegrationTests.exe: `4c22d0b296f759954ec1bb36c3b8f4dfbd471b9d438afd2d550481e8a6fe41d2`.
- Acceptance result: `fb6905c59dd26f5c1b141e136617e1a3fe1aed0e777a6b066584f66aeca5502d`.
- Материалы: `.dev/t116-stock-ffmpeg-loader-r4-acceptance-20261116/main-t116-loader-r4-acceptance-collection-133529074165`.
- Terminal task Ready, actual process exit1; тестовых процессов нет; source273
  и artifacts6 совпали до/после. Коллекция32/32 независимо сверена Main.

| Проверка R4 | Результат | Границы |
|---|---|---|
| T116StockFFmpegLoaderFaults | FAILED | Исходные16 cases/guards сохранены; непроходящие проверки не закрыты |
| NativeProtectedPlaybackBatches | PASSED,29,24с | Все batches, четыре full-EOF tone-случая и существующие fault assertions |
| T116StockFFmpegRawLoaderControls | FAILED до загрузки | Все4 child отказали на raw_platform; реальный raw load/unload ещё NOT_RUN |
| T116DiagnosticShortMediaEngine | PASSED,2,17с | Только diagnostic strict_acceptance=0, muted, без доказательства waveform coverage |
| NativeProtectedShortMediaEngine | FAILED | Прежний exact2048 для30ms; actual3072; assertion не изменён |

После явного освобождения inspection перед второй reader group все tone readers
открылись с error0/native0. При полном EOF, без crop/нормализации и с прежним
порогом обеих амплитуд >0,015 измерено:

| Вход10-мс блоков | Raw decoded frames | Амплитуда1кГц | Амплитуда2кГц |
|---:|---:|---:|---:|
|3|3072|0,034732122491358437|0,032803520738309562|
|31|16384|0,067755926605619271|0,068357766551035912|
|32|16384|0,069943215778456219|0,070762138925162005|
|33|17408|0,067874970240423216|0,068730686399785593|

Отдельный10ms probe прошёл настоящий production inspect/open: raw2048,
container100000, logical10ms; ready1/muted1/duration10ms/playHRESULT0/ended1/
error0/closed1, owned0→0. Это подтверждает жизненный цикл проигрывателя,
но не применение priming или сохранность всех480 исходных отсчётов на выходе.

Raw diagnostic не достиг LoadLibraryExW: IsWow64Process2 успешно вернул
process_machine0000/native_machineAA64 на actualAMD64 EXE. Это подтверждённый
дефект диагностического platform guard, не результат проверки DLL. Parent
post-exit открыл все3DLL для WRITE/DELETE, но EXE WRITE получил native32 даже
без загрузки DLL; process/thread handles в этот момент ещё удерживались parent.
Освобождение DLL нельзя выводить из этого EXE наблюдения или неисполненного
raw-контроля. Нужен исправленный узкий контроль и новый отдельный запуск.

Исходные strict short assertions и пороги сохранены. Далее требуются actual
priming/container metadata, выравнивание начала/перехода/конца и полный useful
interval, затем завершение loader/fault/memory/installed acceptance.

## R5 — прямой контроль загрузчика и выравнивание AAC

Новый Debug build завершён. Снимок273 исходников и шесть артефактов совпали
до/после запуска; задача Ready, тестовых процессов нет. Main повторно сверил
20/20 файлов коллекции. Это незакоммиченный снимок той же ветки, не новый
проверенный Git SHA.

- Source manifest: `4ee089b83c20e37596a42a02afc4ea57bc9cac8096bf1e54954a12295ae7b4f1`.
- Build receipt: `a0e9446816796682e9fe5a0c22d62a5c6f3d4c4f9a40cc26ff05639da4164a54`.
- NativeCaptureStorageIntegrationTests.exe: `35034322c4a49ce547520788389ca04a1a71142dca6b77cf39ba66775096bc55`.
- Acceptance result: `51e5f7aa088ef0911be38dd21281252be39020926c28ddc64b8fb4cc9e170d42`.
- Материалы: `.dev/t116-stock-ffmpeg-loader-r5-acceptance-20261116/main-t116-loader-r5-acceptance-collection-140727099814`.
- Итог harness FAILED, actual process exit1: RawLoaderControls FAILED20,13с;
  AacAlignment PASSED2,43с, только диагностика `strict_acceptance=0`.

Исправленный platform guard проверил PE собственного EXE: AMD64. Успешный
IsWow64Process2 с UNKNOWN/ARM64 допустим для x64 на Windows ARM; он больше
не останавливает raw-контроль до загрузки.

Все четыре raw-случая реально выполнили LoadLibraryExW и FreeLibrary без
FfmpegApi. Все загрузки успешны, все освобождения вернули1/native0. В двойной
группе подтверждены одинаковые HMODULE и refs2→1→0. После final release inventory
пуст, owned0→0. Parent после terminal/GetExitCodeProcess успешно закрыл оба
process/thread handle до post-exit проверки.

| Случай | WRITE до загрузки | WRITE после FreeLibrary и после exit | DELETE после FreeLibrary и после exit |
|---|---|---|---|
| Только avutil | Все3DLL доступны | avutil native32; незагруженные codec/format доступны | Все3DLL доступны |
| Группа, DOS path | Все3DLL доступны | Все3DLL native32 | Все3DLL доступны |
| Группа, canonical path | Все3DLL доступны | Все3DLL native32 | Все3DLL доступны |
| Двойная группа | Все3DLL доступны | Все3DLL native32 | Все3DLL доступны |

EXE также получает WRITE native32/DELETE0 после terminal; это отдельное
диагностическое наблюдение. Прямой контроль воспроизводит блокировку WRITE
без загрузчика GRAF, но не доказывает её конкретную причину или аппаратное
поведение x64. Исходные16 критериев не изменены; их отказы остаются открыты.
Требуется различающий контроль file/directory pins без native DLL mapping.

AAC-диагностика построила30ms/1440 исходных PCM-отсчётов и проверила canonical
без расхождений. Контейнер независимо разобран через ограниченный parser:
movie_scale1000/duration30, media_scale48000/duration2464,
edit_duration30/media_time1024/rate1. Метаданные явно задают priming1024.
SourceReader полностью декодировал три samples по1024, raw3072 до EOS;
результат совпал с production inspector. При фиксированном metadata-offset1024
проверены все1440 исходных отсчётов, prefix1024 и tail608, без выбора лучшего
смещения, нормализации, crop или записи PCM на диск.

| Фиксированная область | Gain | RMSE |
|---|---:|---:|
| Весь исходный интервал | 0,97700605159986997 | 0,009752669084848134 |
| Начало0–240 | 0,99996611294625448 | 0,0032715984818026071 |
| Конец1200–1440 | 0,9224242015554811 | 0,010264478448219892 |

Амплитуды1/2кГц на полном исходном интервале:0,074205563188668541/
0,069954400722462964. Без metadata-offset RMSE0,20680973132722535;
начальные240 отсчётов RMS0,00044829428957977765. Обе заранее определённые
модели сохранены, неудачный участок не исключён. DecodeHRESULT0, completed1,
owned0→0. Это подтверждает наличие и положение полезных данных в raw decode;
применение priming проигрывателем MediaEngine и полный audible interval ещё
не подтверждены. Прежние strict short assertions остаются без изменений.

## R5 — отдельные функциональные регрессии

Проверен тот же неизменный273-файловый снимок R5 и те же шесть артефактов.
Задача Ready, last_result2, процессов тестов нет. Коллекция50/50 файлов сверена
Main по размерам и SHA256. Итог UNKNOWN: тайм-аут не объявляется обычным FAIL
или успешной проверкой последующих случаев.

- Материалы: `.dev/t116-stock-ffmpeg-r5-regressions-20261116/main-t116-r5-regressions-collection-142638866387`.
- Result SHA256: `0e9bb88fa75f8371b47dea20ed1cd2a509fc1735a06756afb289148b019ef370`.
- Source manifest и build receipt совпадают с R5 выше; source273/artifacts6
  сверены до/после. Все данные искусственные, реальные устройства не открывались.

| Проверка | Результат | Время runner |
|---|---|---:|
| NativeProtectedMediaEngine | PASSED | 8,19с |
| NativeProtectedPlaybackConsumer | PASSED | 18,52с |
| NativeProtectedEncoderWriteFailure | PASSED | 25,81с |
| NativeProtectedStartOwnerRecovery | PASSED | 27,54с |
| NativeProtectedRecoveryLivePlayback | PASSED | 8,11с |
| NativeProtectedPrivacyDegraded | UNKNOWN, CTest TIMEOUT180с | 180,12с |
| NativeProtectedInspectionActiveStop | NOT_RUN | — |
| NativeProtectedPackageRevalidation | NOT_RUN | — |

Перед timeout журнал подтвердил все три PRIVACY_DEGRADED и обе
DEGRADED_MANIFEST_CUT проверки. Следующий вызов selector — прежний
protectedPrivacyCapacity(true), у которого пока нет промежуточных отметок.
Это локализует недостающую проверку, но не доказывает зависание или ошибку
FFmpeg. Нужна различающая отметка progress перед повторным запуском; тайм-аут
не увеличивался. Два последующих случая после UNKNOWN не запускались.

### R5 — отдельный последующий запуск двух оставшихся случаев

На том же снимке R5 два случая выполнены отдельно, без повторения остановившейся
проверки истории пауз. `NativeProtectedInspectionActiveStop` — PASSED, 88,50с;
`NativeProtectedPackageRevalidation` — PASSED, 29,36с. Исторические NOT_RUN в
таблице выше относятся к первому запуску и сохраняются.

Материалы: `.dev/t116-stock-ffmpeg-r5-additional-20261116/main-t116-r5-additional-collection-143624728053`.
Result SHA256: `70fe90af5578c84658636226414f06a72e2e31bb814af7620fe4cbbee2734473`.
Main сверил все 19 файлов коллекции по размеру и SHA256; задача Ready,
last_result0, процессов нет. Source273/artifacts6 совпадают до/после. Это
функциональные проверки искусственных записей в VM, не установленная или
аппаратная приёмка и не закрытие T116/T118.

## R6 — сборка наблюдения памяти и защита каталогов загрузчика

Свежая MSVC19.44.35230 x64 Debug сборка в QA ARM завершилась успешно.
Собраны `NativeCaptureStorageIntegrationTests`, `StockFFmpegMemoryTests` и
`ProtectedCustodyCodecTests`; предупреждения компилятора считаются ошибками.
FFmpeg7.1.5 переиспользован после проверки прежних source/build/artifact pins.

- Source manifest275: `5ee5ab6f25d872763818890d3e20a353ef39c99c810ba4c7d0dcffca825504e0`.
- Build result: `342de4cc49480a34fad4ee7f50b4d5cd9dd485faccc2eca46f7668380f494fbd`.
- Integration EXE: `0f67dfd66512407f51f43a5de26ad9dd04480e3b0891c7c6d24b7c59730feb72`.
- Memory EXE: `0597555c973ae83ad65f7f9f13c0ac4d19bbcd7f48831c8ef0f90a2718ea45c4`.
- Материалы: `.dev/t116-stock-ffmpeg-r6-20261116/main-t116-r6-build-collection-145438591282`.

Main сверил12/12 файлов коллекции, source275 до/после сборки и соответствие
локального снимка на момент сверки. Сборка не является результатом long run.
Новый `peakBytes()` — консервативный максимум допущенных собственных резервов
GRAF за жизнь процесса, а не память FFmpeg или точное фактическое выделение.
Он не сбрасывается и не меняет прежние admission/wipe правила. Независимое
ревью memory/header/CMake — SOURCE GO без блокирующих замечаний.

Waveform-кандидат R6 отдельно остановлен **до запуска**: независимое ревью
нашло неверные `SINGLE_SAMPLE_PER_BUFFER` flags для несжатого аудио в тестовом
наблюдателе и ошибку повторного извлечения helper в host selfcheck. Это дефект
диагностики, не обнаруженный дефект production проигрывателя. Только будущий
waveform case исключён из текущего запуска; остальные испытания не менялись.
Исходный сгенерированный CTest-файл сохранён с суффиксом `.review-held`;
квитанция — `.dev/t116-stock-ffmpeg-r6-runtime-20261116/waveform-review-hold.json`.
После исправления нужен отдельный source/build binding. Strict short assertions
и продуктовые критерии этим действием не изменены.

### R6 — фактический результат и полная 10-минутная запись

Коллекция `.dev/t116-stock-ffmpeg-r6-runtime-20261116/main-t116-r6-runtime-collection-151834994260`:
Main сверил42/42 файла. Result SHA256:
`06cb10fc4562ad8b4b50a8ec5682ad083976e532201b21e09640ea197d74ba78`.
Задача Ready, last_result2, процессов нет. Source275 и artifacts6 совпали
до/после. Общий итог UNKNOWN из-за отдельного тайм-аута истории пауз.

| Проверка | Результат | Время runner |
|---|---|---:|
| Реальные directory pins до первой загрузки, штатное освобождение после отказа | PASSED | 18,30с |
| ProtectedCustodyCodecTests, включая admission high-water | PASSED | 51,47с |
| Переносимая самопроверка memory probe | PASSED | 0,76с |
| Искусственная запись10мин, полный canonical compare и AAC до EOS | PASSED | 912,99с |
| История приватных пауз, прежний общий лимит180с | UNKNOWN, TIMEOUT | 180,14с |
| Waveform старого кандидата | NOT_RUN, остановлен по ревью | — |

Длинный случай:60000 блоков,28800000 исходных отсчётов, длительность600000мс.
Все исходные bytes совпали; контейнер6000000000×100нс, расхождение0.
AAC прочитан до EOS:28801024 raw-отсчёта, столько же у холодного inspector;
амплитуды1/2кГц —0,14992408499275237/0,099945291181803245. Это full-EOF tone
проверка с прежним порогом0,015; priming/presentation отдельно NOT_ASSESSED.
MFShutdownHRESULT0; собственные резервы0→0, admitted lifetime peak1450150байт
при limit67108864. Открытые файлы звука не создавались, устройства не открывались.

| Показатель процесса | Значение, байт |
|---|---:|
| Private Bytes: initial / warm / sampled peak / final | 13500416 / 25128960 / 46284800 / 23134208 |
| Working Set: initial / warm / sampled peak / final | 22441984 / 44331008 / 45522944 / 17801216 |
| Наблюдаемый post-warm Working Set growth | 1191936 |
| OS lifetime peak commit / Working Set | 46542848 / 46034944 |

Sampler запросил5мс, фактический максимальный промежуток80968мкс;
54350 измерений, ошибок0. Эти sampled maxima не объявляются непрерывным
измерением или памятью только FFmpeg. SC-003 и native/hardware приёмка не
закрыты (`strict_sc003_acceptance=0`).

Время append213368мс, finalize387927мс, холодная проверка/декодирование307889мс.
Это Debug в x64-эмуляции QA ARM, не измерение скорости установленной Release.
Для сравнения требуется тот же неизменный production source с оптимизацией
Release; медленное завершение не скрывается и не объявляется исправленным.

Новые отметки истории пауз доказали вход в `protectedPrivacyCapacity(true)`
и продвижение64→128 сегментов перед прежним180с timeout; граница capacity
и финальная проверка не достигнуты. Это исключает прежнюю неопределённость
«неизвестно, вошли ли в цикл», но не доказывает FFmpeg fault или deadlock.
Следующая проверка оптимизированного профиля сохраняет те же функции,
assertions, полный workload и лимит180с.

### R7 — Release и наблюдение выхода MediaEngine

Сборка Release завершилась успешно; Main сверил12/12 файлов коллекции
`.dev/t116-stock-ffmpeg-r7-20261116/main-t116-r7-build-collection-152418237230`.
Source275: `b71e4fc3858450d4cde814347a96cffb89f8bf18a6a5705701e8cd2e4fbf47b6`;
result: `04b186c612a3b056108ddd885c3df06dee90166da81c324243ab4b4842ce4b45`.
Production source совпадает с R6; изменение test header — удаление двух
неверных SINGLE_SAMPLE_PER_BUFFER flags после независимого ревью.
Assertions тестовых translation units сохранены при Release.

Один opt-in waveform запуск завершился за6,246с. Коллекция
`.dev/t116-stock-ffmpeg-r7-waveform-20261116/main-t116-r7-waveform-collection-152730734785`:
13/13 файлов сверены; result SHA256
`fd26deb59e2a3fca813db5f9dd2243912e54d184efb43f4b9838a6587928a346`.
Source275/artifacts6 совпали до/после; Ready/last_result2/processes[].
Итог **UNKNOWN**, намеренный semantic exit96; CTest failure не переименован
в PASS. Наблюдатель находится в audio effect перед renderer и не доказывает
слышимый выход или применение trim внутри renderer.

| Искусственный источник | 30мс /1440 отсчётов | 10мс /480 отсчётов |
|---|---:|---:|
| Отличающиеся canonical samples | 0 | 0 |
| Raw PCM у inspector и effect | 3072 | 2048 |
| Контейнер,100нс | 300000 | 100000 |
| Effect samples по1024 float32 mono48кГц | 3 | 2 |
| Первый timestamp,100нс | 0 | 0 |
| Ready/ended/error/close | 1/1/0/1 | 1/1/0/1 |
| Живые test factories/MFT после закрытия | 0/0 | 0/0 |

Для1440 metadata parser подтвердил edit media_time1024 и offset1024.
В raw-начале без сдвига first240 tone1кГц0,00010519; модель с точным
metadata offset даёт0,14999069. Последние240 той же модели сохраняют
2кГц0,13834369; full useful interval RMSE0,00975231. Это сравнение моделей,
не дополнительная обрезка входа, изменение допуска либо proof renderer.
Для480 reused parser рассчитан на1440 и не принимает полный timing guard:
`metadata_known=0`; offset не угадан. Без сдвига first240 tone1кГц0,00001157.
Оба случая сохраняют `trim_stage=UNKNOWN`, `presentation=UNKNOWN`.
Owned0→0. Короткая запись/priming остаются незакрытой приёмкой T116.

Отдельный Release functional runner после waveform завершился **PASSED**.
Main сверил33/33 файла коллекции
`.dev/t116-stock-ffmpeg-r7-functional-20261116/main-t116-r7-functional-collection-154600874137`.
Result SHA256 `8825d4b3994a251ad9aca081769f8778492f191f561d973f9bb8abe747236b7a`;
Ready/last_result0/processes[]; source275/artifacts6 совпали до/после.

| Проверка | Итог | Время runner |
|---|---|---:|
| Directory pins | PASSED | 0,320с |
| ProtectedCustodyCodecTests | PASSED | 16,244с |
| Полная искусственная запись10мин и memory | PASSED | 620,268с |
| История приватных пауз, прежний общий лимит180с | PASSED | 129,301с |

Privacy достигла207 сегментов и штатного отказа по размеру; итоговый manifest
64997байт. Полная история, degraded finalization и cold readback прошли без
обрезки, уменьшения нагрузки или расширения timeout. Debug timeout остаётся
историческим UNKNOWN; новый Release PASS его не переписывает.

Memory10:60000блоков/28800000 исходных отсчётов, все canonical bytes совпали;
duration600000мс, container6000000000×100нс, difference0.
AAC fullEOS28801024, inspector столько же; tone1/2кГц
0,14992408499275237/0,099945291181803245. MFShutdown0; owned0→0,
admitted lifetime peak1449286байт при limit67108864.

| Показатель процесса | Значение,байт |
|---|---:|
| Private Bytes initial / warm / sampled peak / final | 10731520 / 17612800 / 38555648 / 17666048 |
| Working Set initial / warm / sampled peak / final | 15048704 / 30236672 / 31367168 / 16814080 |
| Post-warm Working Set growth | 1130496 |
| OS lifetime peak commit / Working Set | 38723584 / 31891456 |

Запрошено5мс, максимальный фактический интервал86330мкс;36569измерений,
ошибок0. Память всего процесса не приравнивается к allocations FFmpeg;
`strict_sc003_acceptance=0`, priming/presentation NOT_ASSESSED.

Append130467мс, finalize253321мс, cold inspect/compare/decode226477мс.
Release быстрее Debug, но **завершение записи всё ещё занимает4мин13с**
в этой x64-эмуляции. Это нерешённая производительность; ни FFmpeg, ни VM
не назначаются причиной без разделения фактических стадий. Полный60мин
случай с cooperative2700с сейчас не запускается: даже линейная оценка по
10мин превышает его бюджет. Сначала требуется локализация стоимости,
затем обоснованный длинный запуск;60мин и установленная приёмка остаются открыты.


### R7 — обычное приложение WinUI и фазовый замер хранения

Обычный `GrafWindowsApp.vcxproj`, без тестового AppMain, собран в Release.
Main сверил12/12 файлов коллекции
`.dev/t116-stock-ffmpeg-r7-winui-r2-20261116/main-t116-r7-winui-r2-collection-155926598165`;
result SHA256 `07ac035dff426d669a6c8d74ca999775cf349c8f888d5568812899651c51345d`.
Source275 совпал до/после; restore/build exit0, Ready/last_result0/processes[].
EXE3990016байт: `b28bee3e9d52a92570d4ade1fcb18bae4a458db552b0c64cc47646cd8e3a6f5a`;
три FFmpeg DLL совпали с проверенным prefix, WebView2Loader закреплён.
Ошибок0;11предупреждений в сторонних AEC3/FFmpeg headers. Это только сборка:
приложение не запускалось и новый MSIX не устанавливался. Первая попытка
остановилась до MSBuild на сравнении пути с двойным разделителем; исправлен
только запускатель через `GetFullPath`, её результат сохранён отдельно.

Существующий `--protected-storage-profile` выполнен на том же frozen R7:
искусственные1000тиков/10с, audio/network0; PASSED за8,527с.
Main сверил12/12 файлов коллекции
`.dev/t116-stock-ffmpeg-r7-storage-profile-20261116/main-t116-r7-storage-profile-collection-160539556579`;
result SHA256 `e035b76a62744403b2caf598f98d194f0c98fc82ef18a3087e699d9e03c396e0`.
Source275/artifacts6 совпали до/после, Ready/last_result0/processes[].

| Фаза | Время, мкс |
|---|---:|
| Открытие | 153158 |
| Добавление звука | 2487866 |
| Завершение целиком | 5604623 |
| Внутри завершения: canonical seal | 264788 |
| WAV | 603268 |
| AAC, включая protected IO/seal/hash/full MF decode | 2367954 |
| Итоговая inspection | 1298301 |
| Остаток завершения вне четырёх фаз | 1070312 |
| Очистка | 7503 |

Все четыре фазовых входа/возврата1/1, unwound0, adapter selfcheck PASS.
В finalize измерено56624/24414/32732/55748вызовов четырёх metadata APIs;
время этих API1123396/58113/258221/771630мкс. Это thread-local измерение
конкретных обращений, а не все IO/crypto/MF threads. Разность wall и этих
счётчиков не равна времени AAC encoder. Замер локализует дорогие пути,
но сам по себе не обосновывает удаление confinement/ACL/BOTH/hash проверок.
Производительность длинного завершения, установленная приёмка и60мин
по-прежнему открыты; T116/T118 не закрыты.


### R8 — исправленный loader: 16 внутренних случаев прошли, suite FAILED

После независимого source review C0/H0/M0 собран отдельный Release snapshot:
source275 manifest `f7237279a91c3a6de5335793d27a5b8f14a2e12991c67c5d76c1f2414f3a1afb`.
От frozen R7 изменён только loader-блок integration TU, production source
не менялся. Main сверил22/22 файла build collection; result SHA256
`aa18bd5343acd0136b082ac752e5a975dac525ad6b5d228a57cc65c94314ce3d`.
Build/configure/dependency verify/plan exit0, source275pre/post.
Integration EXE `639e44f9fa056219e0d174f2b33d209ce06c1965a3be3fb6e32911aac165ac8f`.

При переносе исходников Parallels дважды вернул transport255/Invalid argument.
Перед продолжением выполнены отдельные read-only reconciliation: сначала
подтверждено отсутствие файлов, затем8полученных частей сверены по hash/size;
перенесены только отсутствующие части, итоговые275source hashes проверены.
Build не повторялся вслепую. Первая попытка functional runner остановилась
до runtime на BUILD_RECEIPT_INVALID: при подготовке Main ошибочно изменил
строковую контрольную сумму. Исправлен только runner, создан отдельный r2;
продуктовые исходники, бинарники и критерии не изменены.

R2 collection:
`.dev/t116-stock-ffmpeg-r8-loader-functional-r2-20261116/main-t116-r8-loader-functional-r2-collection-162348099411`.
Main сверил20/20 файлов; result SHA256
`3c191d177153ebc43f2d5ee8821ff71273ee8054ccda40c0ad853c2a3f6ce2d7`;
source275/artifacts6 совпали до/после, Ready/last_result1/processes[].

- Original16: все16child cases завершились exit0 с case PASS; native ledger
  не показал outstanding/release failures. Включены partial-real-load unwind
  и два настоящих одновременных владельца.
- В конце original16 реальный `Fixture::remove_all` вернул system error5
  (ERROR_ACCESS_DENIED); assert завершил родительский тест ошибкой.
  Поэтому весь original16 **FAILED**, а не PASS, несмотря на completed16/16.
- DirectoryPins/B1: **PASSED**,213мс. Original16 runner занял6548мс.

Отдельная read-only инвентаризация после terminal показала: все DLL и
остальные case trees уже удалены; остался только скопированный EXE последнего
writer-missing-format child и его родительские каталоги/два журнала.
EXE имеет Archive, без ReadOnly/reparse; native child processes отсутствуют.
В16:26:47Z отдельное открытие DELETE access успешно, handle штатно закрыт;
файл сохранён. Это не actual deletion и не исправляет исторический FAILED.
В16:27:42.2330852Z один настоящий DeleteFileW той же закреплённой
сгенерированной копии EXE завершился успешно (native0), файл отсутствует.
Receipt SHA256 `9679aa15c2fb396ec2f3dc626e9e3de52460e357caa2a8c0833795e0e9bdbdb9`.
Это подтверждает временное препятствие удалению, но не устанавливает его причину
и не изменяет исторический FAILED. Подготовлено ограниченное исправление
приёмочного теста: после настоящего terminal/close повторять actual delete
только при errors5/32, не дольше10с и внутри прежнего suite deadline300с;
реальное удаление и отсутствие файла обязательны. Новый native результат
ещё ожидается. Принудительная выгрузка, ослабление ACL/identity и подмена
cleanup успехом не применялись. T116/T118 остаются открыты.


### R9 — настоящий cleanup загрузчика и измеритель AVIO

Три независимых source review дали C0/H0/M0: ограниченный cleanup EXE,
измеритель Write и исправление наблюдаемого release новой process-loopback
диагностики. Main подключил диагностику ровно четырьмя строками TU;
обычные selectors/строгие критерии не менялись. Собрана штатная Release
конфигурация MSVC19.44.35230/SDK10.0.26100.0 на Windows ARM64 под x64 emulation.
Это не physical x64 acceptance и не установка приложения.

Source276 manifest `8c485564f7b90c9ef7701a493c4157b7cc1d01d112c302aeed52a218e67c12ce`.
От R8 изменены только V5 writer test-only Write observer, integration TU
и новый test header. Параметры FFmpeg/IO/flush/security не менялись.
Main сверил22/22 build payloads; build result SHA256
`bcc423ca9f8e2315478f34e2eb52051b01b1047c2a917f886dac32524a73e05d`.
Build/configure/dependency verify/plan exit0; source276pre/post.
Integration EXE `e2d61341ffcf60589707d1b2211ee8a18815b9990d993eccb3554e401d0e36b9`.
Одна read-only status попытка вернула transport255; сборка не повторялась,
следующее чтение установило normal terminal success.

Main сверил19/19 functional payloads; result SHA256
`024f7a3550c3cd5baf27aa0805ec51e3306202bac69b248efce108c369b4fca0`;
source276/artifacts6 совпали до/после, Ready/last_result0/processes[].

- Original16: PASSED,11796мс. Все16 cases exit0, completed16/16.
  В каждом случае подтверждены actual DeleteFileW=true и actual file absence;
  окончательный строгий Fixture cleanup теперь тоже прошёл.
- DirectoryPins/B1: PASSED,194мс.

Исторический R8 FAILED сохранён. R9 исправляет приёмочный cleanup;
причина временного удержания EXE системой по-прежнему не установлена.
Производительность, presentation trim, длинная/установленная проверка
и T116/T118 остаются открытыми.

### R9 — измерение сохранения и граница process-loopback

Storage-profile: Main сверил12/12 файлов; result SHA256
`0baa82c4fc953dc10f8383c16726aafff4337b330fc22f9ba8032d1de9dd0557`.
Source276/artifacts6 совпали до/после; Ready/last0/processes[]. Тест1000×10мс
искусственного звука PASSED за6800мс. Append2081384мкс, finalize4473514мкс;
в finalization canonical seal221839мкс, WAV479632мкс, AAC1780317мкс,
inspection1098801мкс. AVIO выполнил473 Write размером4..2642байт:
requested=written123710, failures0/partial0,1283377мкс — около72% AAC.
Повторные проверки пути/идентичности/ACL/потоков занимают около79% времени
Write. Измеритель test-only; проверки безопасности не удалялись.

Process-loopback: Main сверил13/13 файлов; result SHA256
`375cb3b485172f05f62e80083eb767f0f7ec8bb9404e53919ec6b2cfbe2b0dc7`.
Source276/artifacts6 совпали до/после; Ready/last2/processes[]. Результат
**UNKNOWN**, не PASS. До Play два пакета по480кадров вернули device position0,
но QPC продвинулся ровно на100000×100нс=10мс. Observer ошибочно отверг
второй пакет из-за ожидания device position480; Play ещё не вызывался.
Это не доказательство разрыва звука или отказа проигрывателя. Actual cleanup
завершён: три native release successful, owned baseline=final0. Диагностика
не подтверждает presentation trim, полный слышимый source или приёмку продукта.

Минимальные последующие исправления проходят отдельное source review и новый
снимок R10: отключение per-packet flush в существующем32КиБ AVIO-буфере;
пакетная полная сверка canonical в тесте памяти; учёт виртуальной семантики
device position только в диагностическом observer. Результаты R9 к этим
изменениям не относятся. Все прежние критерии целостности и приёмки сохранены.

### R10 — исправление буферизации и восемь регрессий

Три независимых source review дали C0/H0/M0. От R9 изменены ровно четыре
файла: writer использует существующий32КиБ AVIO без per-packet flush;
storage-profile проверяет не более16 Write на прежней10с fixture; тест памяти
сравнивает каждый480-float блок внутри bounded32-block reads; диагностический
virtual observer отличает недоступную device position от реального QPC gap.
Проверки protected IO,64MiB admission/wiping, EOF, ошибок, отмены, частот,
амплитуды и прежние строгие short assertions не ослаблены.

Source276 manifest `e09e2b9a974e3627ad408f222c2cb06375dffab94235fac106a0f3ddfe7f4851`.
Main сверил22/22 build payloads, result SHA256
`aac273c0010d91d5c5ebf3ea9c736127579ab3fd1e422c5e5b75cb6151876c44`.
MSVC Release build/configure/dependency verify/plan exit0, source276pre/post.
Integration EXE `ac260d6e1c00a44380e2225cdf724a9171bd2b7d1a37a21d9ade843af94ed0ef`.

Main сверил61/61 functional payloads и все8 actual JUnit testcase, result
SHA256 `b00856118125875a52883672493e3ce8230e869c18adf5f727d40fb31d1065cb`.
Source276/artifacts6 совпали до/после; Ready/last0/processes[].

| Проверка | Результат | Время, мс |
|---|---|---:|
| Loader original16 | PASSED |7735|
| Directory pins | PASSED |197|
| Owned codec | PASSED |12037|
| Playback batches, полное чтение и tone/fault cases | PASSED |17632|
| Настоящий отказ записи производного AAC | PASSED |15009|
| История приватных пауз | PASSED |104507|
| Storage profile | PASSED |5743|
| Memory helper selfcheck | PASSED |1149|

На той же10с fixture число Write уменьшилось **473→7**, сумма переданных
байтов осталась123710, failures0/partial0. AAC1780317→516426мкс, около3,45раза
быстрее; сами Write1283377→23562мкс. Finalize4473514→3358958мкс, около25%
меньше. Это два стендовых измерения в VM, не обещание такого ускорения
любому клиенту или доказательство длительности Stop/60min/hardware.

Длинная память, strict short/presentation, установленное приложение,
физическая x64/AEC матрица и выпуск остаются отдельными открытыми проверками.

R10 process-loopback дошёл до actual Play и EOS: execution_complete1/native0,
45пакетов/21600кадров, gaps0, ended1, cleaned1, render_signal_observed1.
На выходе наблюдаются обе заданные частоты, все native releases завершены,
owned baseline=final0. Main сверил13/13 файлов, source276/artifacts6 до/после;
result SHA256 `f3e736d577cb3d5903c3b004a737681b3be6a8e1883806c82bb4e21e780da26b`.
Прежний ложный device-gap устранён. Итог остаётся **diagnostic96/UNKNOWN**:
5мс окна, привязанные к QPC вызова Play, ещё не доказывают source alignment,
точное применение priming/trim или сохранность каждого участка30мс записи.
Сами дополнительные raw AAC frames не доказывают потерю звука: закреплённый
encoder отдаёт priming и padding, SourceReader и renderer — разные этапы.
Оба исторических short assertions и их FAILED сохранены до отдельной
обоснованной коррекции тестового oracle; проигрыватель под них не обрезается.

R10 десятиминутная искусственная запись прошла полный цикл за438733мс.
Main сверил12/12 файлов, source276/artifacts6 до/после; Ready/last0/processes[].
Result SHA256 `849ab29c2fa2abdb56f4a0aeb34c26859707450a684326eb02998c7e513277cd`.
Проверены все28800000 canonical frames; полный AAC decode до EOS дал28801024
raw frames, обе частоты выше прежнего порога0,015; container duration ровно
6000000000×100нс. Все владельцы освобождены, owned baseline=final0.
Пик admission1449286байт при лимите67108864; наблюдённый пик Private Bytes
38088704, Working Set31617024; post-warm Working Set growth1470464байт.
Системный lifetime peak commit39387136байт. Сэмплер:25786измерений, запрос5мс,
фактический максимальный промежуток111464мкс, failures0. Это измерение процесса,
не доказанный полный учёт/затирание внутренних выделений FFmpeg.

Stop→verified307635мс включает finalization и отдельную полную холодную
проверку136976мс; это не задержка кнопки Stop/главного потока. Исторический
полный R7 цикл занимал620268мс; новый — примерно на29%меньше, при полной
сверке каждого canonical блока. Приёмка SC-003/60min/installed остаётся открытой.
Простая проекция438,7с×6≈2632с почти исчерпывает прежний внутренний лимит2700с
для60min. Запуск длинной проверки с таким запасом без калибровки бюджета
не выполнен; продуктовые допуски и лимиты памяти из-за этого не меняются.


## R10 — фактическая сборка установщика MSIX

Из того же снимка276 файлов собран настоящий WinUI/MSIX через штатный
`GrafWindows.Package.wapproj`, Release x64. Новый отдельный каталог сборки;
исходники R10, AEC3/FFmpeg/NuGet/MSVC/SDK закреплены и сверены до/после.
Сбой передачи четвёртого файла разрешён чтением фактического состава:
первые три целы, четвёртый отсутствует, scratch пуст, задачи/процессы сборки
отсутствуют. Продолжение передало только отсутствующие файлы; исходная
неоднозначная квитанция сохранена, повтор create/write вслепую не выполнялся.

Main сверил **32/32** собранных файла по длине/SHA256. Родной PowerShell5.1
разобрал10 скриптов без ошибок; MSIX build, FFmpeg postverify и AEC3
postverify завершились0. Задача Ready/last0, процессов сборки нет.
Source276 и22 входных pin records совпали до/после. Result SHA256:
`8fb399553cbdbebe7c3b858759d048d2bb59d618b1e16354dbaa06549037e4ae`.

Пакет `GrafWindows.Package_0.1.0.17_x64.msix`, **15352024 байта**,
SHA256 `b0bfa4e3f132a7c4e077f0ec0c31d44d3ccbe2cdc60aa0cb09313d22605e40ea`.
Actual identity: `com.graf.desktop`, publisher `CN=GRAF`, x64,0.1.0.17.
Версия взята из исходного manifest без исторического QA override.
В48 package entries проверены соответствие EXE/WebView2Loader/трёх DLL
FFmpeg фактическим build outputs и все **21** обязательные notices,
включая полный corresponding-source архив FFmpeg7.1.5.

Сборка сообщила12 предупреждений/0 ошибок: сторонние заголовки FFmpeg/WebRTC
и DesktopBridge о явном EntryPointExe при наличии project reference.
Actual manifest/EXE проверены; предупреждения не скрыты и не превращены
в доказательство runtime. `AppxSignature.p7x` отсутствует: это **unsigned
build PASS**, не установленная или публично подписанная версия. Новое доверие
сертификатам, установка и запуск на этом этапе не выполнялись. Полная
установленная/пользовательская/x64/выпускная приёмка остаётся открытой.
