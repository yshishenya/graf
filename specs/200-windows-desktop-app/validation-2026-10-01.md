# Проверка Feature 200 — 2026-10-01

## Раунд 125 — исключение до ReleaseBuffer и проверка MMCSS

Срез: `codex/200-windows-followup`, HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`, сохранённое dirty дерево.
Полоса `high-risk-product`, существующая T096/#7239, а не новая функция.

### Допуск и пределы

Независимый reviewer перечитал checklist: advanced-routing14/14,
audio-capture24/24, requirements22/22, security27/27, ux25/25; unchecked0.
`checklists/review-2026-10-01-release-custody.md` допускает только восстановление
существующей гарантии ReleaseBuffer при отказе выделения памяти. Это не
приёмка новой модели часов/хранилища, готовности T096 или установленного GRAF.
Узкий read-only analyze после текущих tasks:32FR/SC с покрытием32/32;
новых critical/high противоречий для этого исправления0. Phase0 clock/storage
остаётся NOT READY. В issue-map T096 принадлежит OPEN #7239; GitHub не менялся.
Hooks before/after analyze/implement отключены; автоматического commit нет.

### Исправление настоящего рабочего пути

В shared consumePacket перехвачено исключение только samples.resize:
normalizationFailed → проверенный release → false. Отказ release сохраняет
releaseFailed и точный HRESULT. Normalizer/callback не запускаются. Mapper
уже проверил пакет; его продвижение не откатывается и новый origin не создаётся.
Native release callable построен как std::function до Start/GetBuffer, чтобы
его возможное выделение памяти не оставляло уже полученный пакет без release.
Выполнение по-прежнему возвращается в штатный native Stop/COM cleanup.

Новый блок существующего CaptureFaultStateTests запускается в настоящем worker
thread для microphone/render и release success/failure. Thread-local one-shot
operator new отказывает только allocation480float; память машины не исчерпывается.
Недопустимый data pointer доказывает отсутствие чтения PCM на этой ветке.
Проверены одна попытка release полного count480 до Stop, точный HRESULT,
приоритет releaseFailed, false/finished/noReady/noCallback, release/Stop trace,
неизменённый normalizer (следующий искусственный batch offset0/480frames).
Контроллер/finalizer этим новым блоком отдельно не проверяются.

RED на исходном worker: build0, CTest exit8, assert releases1/stopped/rejected
в CaptureFaultStateTests.cpp:712. После catch GREEN1/1; после переноса callable
полная macOS CTest32/32 PASS. ASan/UBSan Debug build0, focused CTest1/1 PASS.
Windows MSVC /W4 /WX Release build0, CTest32/32 PASS, exit0. RecApp/Tests/Native
и CMakeLists побайтно совпадают с Windows-зеркалом; единственная посторонняя
разница dry-run — игнорируемый Python __pycache__, не исходник.

SHA256 worker:
`80b06e4b04845608cb70379bdb2ac5026f8d81e0a9a3845756b478de5a9f83a6`;
CaptureFaultStateTests:
`9b957d67a9d660623aa5e695489f5915c6862fc29676c99eeba790134270ca0c`.
ClockMapper/Normalizer/Timeline не изменены. tasks.md не изменён,
SHA256 `0debc42565eee06752e6fdaabd3288d07102dae6c4ee50546bcb9347f09c0700`.
113 задач,91 checked/22 open; T096 остаётся частичной.

Первый MSBuild solution вызов без прежних AEC3 paths остановился на действующей
provenance-защите «must link the standard library covered by build provenance».
Это отказ конфигурации вызова, не повод удалять проверку. Повторная сборка с
явными прежними verified source/build paths выполняется отдельно; её результат
не следует из CTest или старого установленного MSIX.

### Ограниченный опыт планирования Windows

Вне git: `Documents/graf-windows-followup-200/f200-mmcss-comparison.NHcQMH`.
Тот же schema6/mapper/формат/buffer100ms/65packets; строгий явный CLI
`--metadata-once-48000-mmcss`. Регистрация Audio через
AvSetMmThreadCharacteristicsW и AvRevert выполняется на одном capture thread;
revert после Stop/COM cleanup, в том числе при возврате/исключении.
Registry/service/global priorities не менялись. Raw audio не читалось,
не сохранялось, не отправлялось. JSON содержит только bounded metadata.

MSVC x64 /W4 /WX build0,4no-capture checks PASS, worst-case summary998B≤1024.
Первый build exit2: MixFormatTests включал PacketProbe.cpp, но не линковал avrt;
добавлена штатная Avrt.lib только disposable build. Product CMake уже использует avrt.
CPP SHA256 `35ea87cbfaf17346a02c208a7c2e53189bb1b68b1a94f9e922070c774bb2aa97`;
exe `9270a9b3574b9eacedc32f8dbec2a0ace140bbb18fbfe6947659257c5208df6f`;
runner `30d11b0bd4ed7218e115543fd347139a42ef36748a4805d31ad3dcf7152409e3`.

GRAF0.1.0.11, ранее запущенный main, подтверждён idle через CUA; PID15216/path/
exe hash совпали. Он завершён для исключения параллельного захвата, данные не
удалены. Первый немедленный runner получил CAPTURE_PROCESS_PRESENT и не начал
тест; после исчезновения процесса новый inventory count0 и явный запуск принят.
Принятый PID10108: parent/child exit0,829B,65packets/65releases/0release failures,
31200frames/7valid,Stop S_OK,cleanup683ms. mmcss[1,0,0]: requested,registration
и revert без ошибки. First fault packet9 sample_count_mismatch, gaps[-11,0,-11],
service28101µs/held216µs, flags1startup/0timestamp errors, startup480/buffer4800.
clock checkpoints100ns:
[2,750,-100000,-100750],[8,852,-206411,-204972],
[32,1676,-125810,-125195],[64,74280,-35601,-107590].
audio_read=false/continuity_acceptance=false. Guard/cleanup проходят, capture
integrity НЕ проходит. Это отвергает достаточность одной MMCSS регистрации,
но не причинность VM/driver, не измеряет преимущество scheduling и не заменяет
согласованную clock model. В product регистрация/новый buffer не перенесены.

### Осталось

Post-implementation review текущих двух исходников и полная AEC3-linked solution
проверяются отдельно. governance/bootstrap/YAML/diff-check пройдены перед
этой записью; после записи необходим повторный focused check.
Сверка текущей узкой реализации не выявляет новой задачи: остаток уже относится
к T094/T095/T096, полная F200 convergence не объявлена. Точность часов, protected
local stream, real recording/AEC3/60минут, installed UI/accessibility/auth/upload/
deletion, clean-image install/update и доверенная публичная подпись открыты.
Установленный MSIX0.1.0.11 не обновлялся и не содержит сегодняшнее исправление.
Commit/push/PR/merge/release/deploy нет; пользовательские записи и сервер не менялись.

Post-implementation reviewer: APPROVED NARROW, source hashes выше совпали;
callback construction reservation снята после переноса до acquisition.
Новые четыре worker случая и test allocator проверены отдельно, MSVC CTest
main прошёл32/32. Reviewer не запускал эти тесты; его историческое примечание
«Windows build выполняется» не превращается в собственный runtime proof.
Ponytail-review узкого изменения: Lean already; нет новой зависимости/API/
общего framework. Остальные dirty изменения этим code review не одобрены.

Полная повторная solution сборка завершена: Release x64, MSBuild,
SOLUTION_BUILD_EXIT=0. Явно переданы прежние verified source/build каталоги,
ValidateGrafAEC3 подтвердил source/license identity
`846fe90a289f58b7c9303a635142aa2c7caa93e5`. Защиты происхождения не отключались.
SHA256 нового build-output GrafWindowsApp.exe:
`df2d07eab2e947b8e7b83a8e3942071daeb5117146a57bd0f9ae4558e9f23630`.
Есть существующие upstream C4100 и MSBuild D9025 warnings; build exit0 не
выдаётся за отсутствие предупреждений или live AEC3 acceptance. Build-output
exe напрямую не запускался: installed-package gate принимает только
зарегистрированный MSIX. Нового пакета/установки в этом раунде нет.
Финальный VM inventory CAPTURE_PROCESS_COUNT=0, установленный0.1.0.11 StatusOk,
оба source SHA совпали с основной веткой. GRAF оставлен закрытым после idle
cleanup; запись пользователя не запускалась и ни один локальный файл не удалён.
После source/docs записей повторно governance/YAML/git diff --check PASS.

## Раунд 126 — проверка непрерывного ratio на настоящем pinned WebRTC

Риск high-risk-product; продолжается Phase0 `$speckit-plan` для T094–T096,
не реализация нового clock contract. Ветку/HEAD проверили заново:
`codex/200-windows-followup`, `a9691d4d474d918f54493d55a3aba286c749b513`.
Рабочий код ClockMapper/AudioNormalizer/RecordingAudioTimeline не менялся.
Пакет не собирался и не устанавливался, пользовательская запись не запускалась.

Внешний собственный стенд `f200-ratio-waveform.MqRx7p/RatioProof.cpp` использует
уже собранный direct WebRTC SincResampler и настоящий RecordingAudioTimeline
из Windows-зеркала. Последний побайтно совпадает с canonical source, SHA256
`0f36e9fb38018f49d4dcf42ac552b72104a4036f3e11734f21668fc4e14d2781`.
IAec3Processor здесь явно passthrough: тест нужен для сравнения волн до AEC,
не доказывает настоящий echo cancellation. Нет WASAPI/capture/UI/network,
чтения пользовательского PCM, сохранения/проигрывания generated wave.

Pin `846fe90a289f58b7c9303a635142aa2c7caa93e5` подтверждён штатным
build-graf-aec3.ps1 -VerifyBuildArtifacts (exit0). Первый вызов без process-only
ExecutionPolicy Bypass отклонён Windows до исполнения скрипта; повтор с Bypass
только в дочернем PowerShell успешен, постоянная политика не менялась.
libcommon_audio.a SHA256
`0ccc326fec7456c1c7cb1b13f2580a35fcc959686af8ed4dbf06baad170d04fe`
совпадает с provenance. Header SHA256
`c954888557538a56511b9cb59a34c447ac8d7783891ff6224782ffedb1b01063`;
implementation SHA256
`3fe2d90e190b893962084e158cd725e1d88c93bae774621c706838b181494f9c`.
MSVC x64 C++17 /MD /O2 /W4 /WX build exit0, без новой библиотеки/изменений vendor.

Вход — сумма трёх generated tones53/997/2111Hz с amplitudes0.03/0.10/0.07.
Физические частоты и start offset заранее заданы генератором (oracle), а не
оценены из WASAPI. Проверяются каждый опубликованный sample, непрерывный PTS,
точное количество полных480-frame выходов и отсутствие timeline trim.
Callback отклоняет любой запрос вне заданного входа; никогда не zero-pads.
Стартовая zero-history исключена из выдачи, конец ограничен полностью
наблюдённой поддержкой и полными input requests. Остатки явно считаются,
не маскируются successful full EOS. Это не packet-arrival/queue proof.

Финальная короткая серия exit0: семь60s вариантов и два EOS edge cases.

| Вариант | max abs waveform error | max source difference | RMS delta, dB |
| --- | ---: | ---: | ---: |
| 48k/44.1k, +100/−100ppm, fixed output480 | 0.00002043508 | 0.00002208911 | −0.00007791716 |
| Те же источники, output1/479/31/997/480/7/1024/211 | 0.00002043508 | 0.00002208911 | −0.00007791716 |
| 44.1k/48k, −100/+100ppm, source start137 output frames | 0.00002042390 | 0.00002224022 | −0.00007791746 |
| Первый вариант, input request512 вместо64 | 0.00002043508 | 0.00002209283 | −0.00007792053 |
| Negative: nominal ratio при реальных +100/−100ppm | 0.38356122375 | 0.39079168439 | −0.00005632997 |
| Смена +100→−100→+100ppm на20/40s, fixed output | 0.00002066139 | 0.00002201740 | −0.00007781420 |
| Та же смена, variable output | 0.00002066139 | 0.00002201740 | −0.00007781420 |

Каждый вариант публикует2879520sample/source. Fixed/variable output совпадают
побитно на одном интервале: rolling hash15555160554612433635, для изменяемого
ratio13015641041484654740. Hash — regression fingerprint, не cryptographic
integrity. Negative остаётся healthy по timeline/RMS, но waveform check
правильно отвергает его. Исследовательские thresholds0.0003/0.0006/0.01dB
не становятся product acceptance limits или разрешением timestamp jitter.

EOS воспроизводит ограничение API, а не обходит его. При request64/native N100
доступны32 доверенных центра, ещё37 математически поддержанных центров требуют
запрещённого полного callback. При N128 доступны96, ещё1 требует callback.
Попытка следующего output отклонена до чтения/записи данных, sentinel не меняется;
padding0. Прерывание здесь не принимается как успешный drain продукта.

Final-source SHA256 RatioProof.cpp:
`c09ab24fb7340962b6861b7f4ea76969dbcde118a86255080e1757e47d4b5ebe`;
build.cmd:
`761eb509922dc9287965a5bf32863776acaae5f9b4cf92c3a20d90bcae4012c4`.
Воспроизведение в указанном внешнем каталоге: build.cmd, RatioProof.exe,
RatioProof.exe --hour. Стенд исследовательский и не входит в продукт/MSIX.

После EOS checks тот же final-source бинарник повторно прошёл `--hour`, exit0.
За105632ms wall time обработан искусственный3600s поток, не час живого захвата.
44.1/48k,−100/+100ppm, второй источник начинает с137 output frames. Опубликовано
172799520sample/source, PTS интервал[156,172799676), каждый полный блок480
проверен. Conservative input end172799913, невыданный canonical tail237;
native unused64/62, full callbacks2700269/2480374. Trim0, zero-padding0;
max waveform error0.00002043694258, source difference0.00002204999328,
RMS delta−0.00007792133181dB; rolling hash11805989966195823840.
Final RatioProof.exe SHA256
`b6491ace9e456eb757aaac46887645cd1c73419cb94544174690caff268dd055`.
Предыдущий до EOS-check binary также проходил hour, но не используется как
exact-source финальное evidence. Duration label oracle_hour не означает
полученную запись/WAV/M4A, выполнение real-time resource gates или SC-003 PASS.

Независимый static review final-source c09ab24f…/build.cmd761eb509…:
APPROVED NARROW. Проверены centers/PTS, pre-write callback bounds, одинаковый
публикуемый интервал partition comparison, отсутствие исключений около20/40s,
prefix/EOS accounting. Reviewer также проверил SHA byte equality timeline .cpp,
.h и AudioTypes.h с canonical. Он не запускал VM/tests, не одобрял clock
estimator, настоящее AEC/encoder, ресурсы или полный EOS. Pin provenance и
exact final-source короткий/hour runtime подтверждены отдельно main выше.

Вывод: continuous-ratio преобразование на pinned native dependency сохраняет
волну при известных часах; independent PTS smoothing/nominal ratio не заменяют
коррекцию частоты. Не выбран production estimator, noise bound, slew/horizon
или протокол полного partial-EOS. Порог §5 не ослаблен. SC-003, T094/T095/T096,
реальная запись/encoder/AEC/hardware/install/UI остаются открытыми; tasks.md
не менялся, SHA256
`0debc42565eee06752e6fdaabd3288d07102dae6c4ee50546bcb9347f09c0700`.

Финальный read-only VM inventory: CAPTURE_OR_PROOF_PROCESS_COUNT=0;
установленный com.graf.desktop0.1.0.11 StatusOk, без обновления/активации.
Повторно проверены final source/build/EXE hashes. После документации:
governance/YAML/diff-check PASS, bootstrap doctor --frozen PASS.
Необязательный after_plan agent-context hook не выполняется, незавершённый
Phase0 не выдаётся за окончание plan; commit/push/PR/merge/release отсутствуют.

## Раунд 127 — повторная проверка общих страниц и исправление тестовой среды

Срез T097/#7240, существующая high-risk-product полоса; HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`, dirty изменения сохранены.
Независимый preflight: `checklists/review-2026-10-01-ui-parity.md`,
112/112 требований качества, unchecked0. Это не 112 runtime проверок.
Узкий read-only analyze текущих FR-002/003/015, SC-002/009, плана общей страницы,
T097 и конституции VI/VII: новых critical/high противоречий для test-only
исправления нет. T097 имеет текущего OPEN владельца #7240 (проверено через gh).
Новый clock/protected-storage Phase0 не разрешён и не закрыт этим допуском.
Локальный prerequisites не поддерживает --require-spec; использован его штатный
--require-tasks --include-tasks с отдельно прочитанными spec/plan/tasks.

Синтетический стенд использует текущие общие шаблоны/ресурсы, без рабочего
сервера, пользовательских данных или микрофона. Playwright1.63.0 из существующей
установки; нового framework/зависимостей нет. Пройдено: profile-menu33/33 в
Chromium и WebKit; platform-copy29/29 в каждом; settings-consistency224 сочетания
страницы/темы/ширины; оба combobox набора; notification-contract37/37.
Первый settings-consistency вызов без SETTINGS_PREVIEW_URL получил connection
refused на8874; повтор с явным текущим стендом8897 успешен. Это ошибка вызова,
не отказ продукта. Эти проверки не являются installed/native acceptance.

Свежий RED: local-recording-focus:96 ожидал05:30, получил03:30; user-time:19
ожидал02:30, получил00:30. Первый тест менял server fallback meta и повторно
подключал скрипт вместо действующего GRAFTime.setTimezone; второй не задавал
deviceZone и зависел от ОС. Исправлена только тестовая среда: browser timezoneUTC,
явный default deviceZoneAsia/Yekaterinburg, вызов публичного setTimezone.
Все прежние ожидаемые времена сохранены. Дополнительно проверены выбранная
строка, восстановление фокуса после нового markup и идентичность control после
20 повторных публикаций. Changed markup штатно заменяет строку; отсутствие
замены при изменившемся времени не заявляется. Выделение задано явно перед
сменой зоны, поскольку прежний server handoff меняет identity строки.

GREEN: user-time под TZ=UTC/Europe/Istanbul/America/New_York; local-recording-focus
на текущем компьютере и TZ=America/New_York; timezone-settings с настоящим
синтетическим HTTP autosave422/retry; local-recording-handoff.
Два соседних теста сначала отказали только на «подтверждён/подтвержден» и
«ещё/еще». git show HEAD подтвердил, что общая страница уже содержит варианты
с «е», эти строки не изменены текущим dirty diff. Исправлены две точные строки
ожиданий, без ослабления regex/удаления проверок или изменения продукта.
Полностью GREEN mixed-meeting-list и recording-deletion-recovery, включая
offline сохранение строки, явный retry и новый origin при повторном импорте.
Это synthetic UI/protocol regression, не настоящие upload/deletion E2E.

Final SHA256 четырёх изменённых тестов:

- user-time: `49fa87eeea71c0c65fa7a8cbeb7f0455b1fb6085a49ca53677339f9b560d81fc`.
- local-recording-focus: `05a5054fef7330eeb06a63b48a21699cdd59b5b285de1ffc6c20cc21ec0e62f0`.
- mixed-meeting-list: `9e55a80752cd91ee72a9818d1b9c7260fafb290abf4d2ad7b238a14897d74165`.
- recording-deletion-recovery: `c8bd22da7e8870da7ac57410ee73b4b6126b71228adc73a16305fca1cedce8cb`.

Изменён только код этих четырёх тестов и evidence; рабочие UI/audio/storage
исходники в этом раунде не менялись. T097 и другие задачи не отмечались:
tasks SHA256 `0debc42565eee06752e6fdaabd3288d07102dae6c4ee50546bcb9347f09c0700`.
Свежий VM inventory: GRAF0.1.0.11 StatusOk, capture/proof process count0,
installed EXE SHA256
`9f1ec17fb32f06f2f402b49bcd05abc0f52e5b4607ade3b712bbd9b35e176cd7`.
MSIX не обновлялся; package SHA не переподтверждался и не выводится из EXE SHA.
CUA сообщает Mac locked; живую UI/доступность приёмку не проводили и защиту
не обходили. Новый microphone test не запускался. clock_drift не исправлен
тестами интерфейса. Commit/push/PR/merge/release/deploy отсутствуют.

Post-change review четырёх test hashes: APPROVED NARROW, замечаний0;
`checklists/review-2026-10-01-ui-parity.md` содержит отдельное заключение.
Ponytail-review: Lean already; без новых зависимостей/инфраструктуры.
node --check всех четырёх файлов, governance, frozen bootstrap doctor,
YAML parse и git diff --check PASS. Собственный fixture8897 завершён штатно,
порт больше не слушается; пользовательские процессы/записи не тронуты.

## Раунд 128 — исправленный аудиокод в установленном development MSIX

Продолжение T096/#7239 и пакетной части T101, high-risk-product; HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`, dirty изменения сохранены.
Preflight reviewer: 112/112, unchecked0; отдельный version review APPROVED NARROW
в `checklists/review-2026-10-01-package-followup.md`. Единственная новая source
правка — Identity Version0.1.0.11→0.1.0.12; Name/Publisher/dependencies/capabilities
не менялись. Это техническая development версия, не публичный CalVer выпуск.
Узкий analyze FR-019/020, SC-008/010, существующих package/custody задач и
конституции: новых critical/high конфликтов для версии/проверки нет; общий
clock/protected-storage Phase0 и аппаратные критерии не закрываются.
Внешний владелец T096 #7239 повторно подтверждён OPEN. Hooks commit отключены.

Свежий MSVC CMake build/CTest32/32 PASS, WINDOWS_CORE_EXIT=0; ASan/UBSan
CaptureFaultStateTests1/1 PASS. Первое обращение к старому
/tmp/graf-feature-200-followup-build получило could not load cache, тестов там
не запускало; использован существующий sanitizer cache текущего worktree.
VerifyBuildArtifacts exit0 проверил source/header tree и все AEC3 artifacts,
pin `846fe90a289f58b7c9303a635142aa2c7caa93e5`. Нового capture/чтения PCM нет.

Первая упаковка baseline0.11 с глобальным GenerateAppxPackageOnBuild=true
получила PACKAGE_BUILD_EXIT=1: параметр попал во вложенный RecApp, чей собственный
MakeAppx payload не содержал entrypoint. После завершения этого вызова зеркало
переведено на0.12. Повторный штатный wapproj Build без глобального параметра
дал PACKAGE_BUILD_EXIT=0 в `Installer/out/round128-v12/` без ремонта project files
или отключения проверок. Есть прежние upstream C4100/D9025 и предупреждение
DesktopBridge о сочетании EntryPointExe с application reference; отсутствие
предупреждений не заявляется.

Canonical и Windows mirror: один и тот же список154 versioned/untracked
неигнорируемых файлов apps/windows; SHA256 последовательности sorted relative
path+NUL+file bytes+NUL:
`77d95afa6516e4f0cdf14d8023c2f5203d6028ac2878029484cb71046b2f4083`.
Этот digest включает незакоммиченные исходники, но не SDK/NuGet/external vendor
cache; vendor проверен отдельной provenance защитой. HEAD сам по себе не SHA
этого рабочего снимка. Manifest SHA256
`95bea5c39f980228a5238ab9384ff68c051bff8b79765a9e945b1be21c12ceed`.
Worker/fixture hashes round125 сохранились, исправление теперь входит в payload.

Подписан существующим CN=GRAF сертификатом
`816CC8B4EB216A0755BFB118992BB594AF51BF6C` через CurrentUser My: SIGN_EXIT=0,
Authenticode Valid; новые ключи/сертификаты не создавались, truststore не менялся.
Static smoke exit0: com.graf.desktop, GrafWindowsApp.exe, допустимые capabilities,
без driver/service/elevation/managed WebView projection. Manifest0.1.0.12/x64;
Microsoft.VCLibs.140.00.UWPDesktop и Microsoft.WindowsAppRuntime.2 доступны
на VM в подходящей архитектуре/версии. Это не clean-image доказательство.
Signed MSIX SHA256
`aaa7e812605d470e6400c73f9708e25ea8c411161bbe41a5525434534c5669a1`;
payload/build/installed EXE SHA256
`7c4193727f2653832da23e10641c3abe2686293d802ad5dd0edddac9ffff9994`.

Первый installation command не получил гостевую сессию; повторная независимая
инвентаризация подтвердила прежнюю0.11/Ok и process count0. Новый вызов заново
проверил точные байты пакета/старого EXE, старую identity и отсутствие GRAF/
PacketProbe/RatioProof непосредственно перед Add-AppxPackage. FRESH_IDLE_GUARD=PASS,
INSTALL_EXIT=0; без ForceApplicationShutdown, uninstall, purge или очистки данных.
Отдельная проверка регистрации подтвердила0.1.0.12/Ok и совпадение installed
EXE с payload. Транзитные PrlJob ошибки чтения не заменяли этот результат
и не приводили к повторной установке без проверки текущего состояния.

Штатный validate-aec3-build.ps1 на точном installed EXE/независимом payload hash
прошёл negative pin/library/provenance/architecture случаи и real-backend.
AppUserModelID activation --verify-audio-backend: native-msix-activation=PASS,
PID3008, exit73; verifier завершился exit0. Это настоящая установленная AEC3
самопроверка reverse-before-microphone на искусственных samples, не акустическая
приёмка. AppMain завершает этот путь до UI/profile/files/network/devices;
заблокированный Mac не обходился. Финальный inventory:0.1.0.12/Ok, exact EXE,
CAPTURE_OR_PROOF_PROCESS_COUNT=0; GRAF оставлен закрытым.

Read-only сверка GitHub master: `df3a91a01fc8e741a7ebe355ad098353c290770c`,
совпадает с origin/master; HEAD...master даёт68 веточных/20 master коммитов.
Есть новые Mac/shared изменения; master не вливался в dirty дерево, новый
пакет не объявляется их автоматически включающим. Это следующий source-parity
разбор, не выполненная синхронизация. UI/T097 требует разблокирования Mac.
T101 требует также факт готовности записи, поэтому task checkbox не менялся;
tasks SHA256 `0debc42565eee06752e6fdaabd3288d07102dae6c4ee50546bcb9347f09c0700`.
clock_drift, полный protected stream, real audio/AEC/hardware/60min, auth/upload/
deletion, clean-image/update/rollback и публичная подпись открыты.
Commit/push/PR/merge/release/deploy нет; рабочий сервер и macOS исходники не менялись.

## Раунд 129 — подтверждённые расхождения с новым master, без слияния

Read-only investigation и docs-only evidence внутри F200; продуктовый код,
основной index/HEAD, установленный пакет и устройства не менялись. HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`; проверенный master/origin/master
`df3a91a01fc8e741a7ebe355ad098353c290770c`, merge-base
`f5cca687a06dc57ad6ccbef840a0be897eaa6336`; расхождение68/20 коммитов.
Incoming apps/windows diff пуст, но общие страницы и macOS изменены.

Временный GIT_INDEX_FILE вне рабочего дерева сохранил dirty snapshot tree
`b664f6a2565a0d412a4869f27a588626519fb53e` без commit/ref. Основной index
до/после совпал. Native git merge-file на шести пересекающихся файлах выявил
3 conflict files/5 blocks: cabinet.js2, notification template1, settings test2.
CSS/combobox/integration test текстово сливаются; это не поведенческая приёмка.
Повторный разбор исправил ошибку regex диагностического счётчика: первый
12-line JS conflict имеет побайтно одинаковые стороны. Содержательная резолюция
должна сохранить platformText, data-platform-copy и fixture platform helper,
а в template assertion взять master embedded-only scope. Новые F279 series
refresh/loader и F280 preview code также должны сохраниться; резолюции пока
не применялись. Незакоммиченные изменения не сбрасывались и не прятались.

Независимый read-only code-reviewer сравнил frozen F27751bcff6b с master и
текущим Windows деревом. Найдены шесть source-parity gaps, относящихся к уже
открытым T102/T104/T105: свежий join-target/выбор приложения, bounded native
calendar intent, состояние открытия/retry в карточке, сохранение только уже
видимой карточки при transient calendar failure, nonglobal meeting IP policy,
четыре новых billing routes. Это не разрешение расширить bridge allowlist или
финансовые действия без уточнённого контракта/review. Задержка автоматического
старта8s от фактического показа уже есть в Windows; runtime acceptance открыта.

Два source gaps подтверждены исполнимым искусственным стендом с настоящими
WebViewRoutePolicy/MeetingReminderModel из свежего graf_windows_common:
четыре /billing/storage/preview, /billing/storage/cancel-selection,
/billing/subscription/early-preview, /billing/purchases/confirm получают deny;
https://[::1]/, https://[fc00::1]/ и https://[fe80::1]/ получают safeMeetingUrl=true.
Контроли /billing, обычное DNS имя и запрещённый IPv4 loopback проверены.
Стенд использует только публичные искусственные адреса, без сети/устройств/PCM.
Первый compiler вызов без SDK не нашёл array; повтор с существующим CMake SDK,
ASan/UBSan и Wall/Wextra/Wpedantic/Werror: BUILD_EXIT0, RUN_EXIT0,
SOURCE_PARITY=FAIL_CONFIRMED. Успешный run означает воспроизведение различия,
не исправленный продукт. Файл /tmp/graf-f200-master-audit.0jycQw/parity-proof.cpp:
SHA256 `c975a6bd6c7487381293f082ad6626f4e8ab6378480dc2425c2b2db3ccc7a406`;
EXE SHA256 `27064b12b9113ef8f28e19dca85d2870cf76e570639e3535b773a23ba8552ca3`.
Текущий notification v2 contract37/37 PASS, без browser/native UI.

Последний user schema6: first_fault_packet12, stats point11 error11438x100ns
=1.1438ms против действующего mapper budget≈1.03095ms при4800 frames span;
gaps0/0/0, release65/65, release failures0. Это timestamp-bound отказ, не
доказательство потери кадров, чистого звука или VM sole cause. Порог/§5 и
производственный mapper/normalizer/timeline не менялись. Phase0 остаётся открытой.
CUA повторно сообщил Mac locked; UI не читался обходными способами, пользователь
попросен разблокировать. T097/готовность записи не закрыты. Tasks SHA256 прежний
`0debc42565eee06752e6fdaabd3288d07102dae6c4ee50546bcb9347f09c0700`.
Commit/push/PR/merge/release/deploy и новый microphone test не выполнялись.

## Раунд 131 — воспроизведение несовместимости опубликованного CSS

Read-only продуктовая диагностика; scoped docs-only evidence. Независимый
review допустил только чтение UI и неразрушающую проверку T097, без аудио
и изменений исходников. Requirements checklists112/112 не заменяют runtime
приёмку; analyze для текущих spec/plan/tasks устарел, Phase0 остаётся открытой.

Публичный /static/cabinet/cabinet.css на rec.2brain.pro без cookies/session
содержал218204 bytes, SHA256
`276fc8c536d06b93aa9526f53af56feb4492e5037ae67020073579fc6361094c`:
побайтное совпадение с проверенным master, не с текущим F200 CSS
`4f394de881f2431bd9592b80a97744f396eb21e7f85bcb18a376a7d464cdd099`.
Это public-asset evidence, не чтение URL/кэша установленного WebView2.

Тот же существующий synthetic settings fixture и текущие templates/JS,
менялся только CSS. Existing profile-menu.test.cjs SHA256
`be44d7479d63643bf227e1230afb6b37d39767fee468c0605478e7f3d014508c`
на master/public CSS: exit1, Chromium «Вид stays inside viewport».
Отдельный geometry probe в Chromium/WebKit при1080/744/500×620 подтвердил
position=absolute, panel.left=viewport.width+16, width0, top−4.
В F200 CSS position=fixed, left255/right475/top227/bottom335 во всех шести
контролях, menu.left8/right256. Полный неизменённый тест с F200 CSS:
exit0, Chromium33/33 и WebKit33/33, включая клавиатуру, Escape, прокрутку,
малые окна и восстановление после искусственной ошибки сохранения.
Подтверждена несовместимость public CSS с текущей F200 разметкой/JS,
не воспроизведение полного production bundle или установленного Windows UI.

Диагностические wrappers только во временном каталоге вне Git; оба собственных
fixture процесса завершены штатно. Новые зависимости и продуктовые изменения
не добавлялись, рабочий сервер не обновлялся. Новый MSIX сам по себе не публикует
общие CSS/JS/templates; их совместную поставку ещё нужно проверить.

Mac briefly unlocked, CUA увидел Windows desktop. Фокус, повторные щелчки,
Ctrl+Escape и штатная Keyboard button Parallels не дали подтверждённого
открытия Пуска/GRAF. CLI/SendInput/UIA обход для UI не использовался.
Приложение не запускалось, запись не запускалась, private UI не сохранялся.
Installed metadata отдельно подтверждает0.1.0.12/Ok, exact EXE
`7c4193727f2653832da23e10641c3abe2686293d802ad5dd0edddac9ffff9994`,
process count0 на момент inventory. Текущий GRAF Dev теперь F280,
source SHA `10b363c815660c47e95a927b81f5320663234279`, не frozen F277;
это различие не разрешает автоматическое включение F279/F280.
T097/#7240 остаётся открытой. Commit/push/merge/PR/release/deploy нет.

## Раунд 132 — одобренный промежуточный коммит и покрытие шифрования

Прямое подтверждение владельца: промежуточный коммит и правки plan/tasks по
шифрованию. Полоса `high-risk-product`; только сохранение накопленного F200
среза и документационное уточнение, не разрешение новой clock/storage
реализации, миграции рабочих данных или выпуска.

Промежуточный commit:
`99b00a579c24b50e320465b69d9a296038bc544d`,
tree `eb1fd25120ad0e16e9daa6ea36b8f87059e65c80`,
parent `a9691d4d474d918f54493d55a3aba286c749b513`.
Включены ровно101 проверенных накопленных F200 paths: Windows source/tests,
общий cabinet UI/tests, feature fragment/specs/reviewer reports. Ни macOS source,
ни server business logic, ни root CHANGELOG в checkpoint не включены. После
commit дерево чистое; затем добавлены одобренные документы этого раунда.
Ignored per-worktree feature.json.source_sha обновлён до нового точного HEAD;
исторические source/package SHA в прежних evidence не переписаны.

Перед commit прошли свежие `cmake --build
/tmp/graf-f200-release-custody-sanitizers -j2` и CTest32/32 на тех же продуктовых
bytes (последний запуск17.08s), governance, frozen bootstrap doctor, YAML parse
и staged diff-check. Это portable ASan/UBSan проверка, не Windows API/hardware
или exact-PR-SHA CI. Поиск распространённых private-key/token сигнатур в
изменённых и новых scope files не дал совпадений; это ограниченный scan, не
универсальное доказательство отсутствия чувствительных данных.

В plan добавлена карта всех storage consumers и порядок Phase0 proof →
Phase1 contract → независимый reviewer/analyze/taskstoissues → полная
интеграция → migration → acceptance. В конец tasks добавлена Phase18 с
T114–T118 и дополнением FR/SC traceability. Прежние113 tasks/checkboxes и
прежняя часть plan сохранены побайтно. Всего118 уникальных tasks,
91 checked/27 open; никакая приёмка не закрыта. Application source в этом
раунде не изменялся; нет новых библиотек, службы, БД или очереди.

Независимый reviewer: `checklists/review-2026-10-01-encryption-plan.md`,
**APPROVED NARROW** только для достаточности документационного покрытия;
дублей/блокирующих замечаний к дополнению не найдено. Reviewer не менял
отметки, plan/tasks или исходники и не запускал VM/UI/tests. Требования
ciphertext-only media/metadata/temp, logical bytes/ranges, migration authority,
сохранность originals и запрет неподтверждённого erasure приняты как охват,
не как реализация. Общий **SOURCE IMPLEMENTATION STOP / NOT READY** сохраняется.

Повторный read-only analyze после дополнения:22FR/10SC,32/32 номинально имеют
task coverage; все5 новых задач связаны с FR/SC. C1 (пропущенное task-покрытие
полной FR-012) устранено. Новых duplication/constitution-conflict findings0;
общий допуск всё ещё не проходит: U1 HIGH — quantitative causal clock model,
U2 HIGH — combined protected-storage proof и финальный format/authority
contract незавершены. Добавление задач не закрывает эти технические вопросы
и не является полным convergence всей F200. Before/after analyze hooks
отключены; optional after_plan context update пропущен на незавершённом этапе.

Хеши проверенного документационного снимка:

- spec `9f7e0d9ca96c6be1209af723e5fad0745a9b78cf8314f2b2996d6697de5c20b2`;
- plan `7c32bca2821465a4b052839e0790b0b7938b1215c154b6c6e97f5206f19643d0`;
- tasks `2019b804de49724efbb6e6bf31f6faa490b10c1869ff88ba6a26aa889c6e0655`;
- constitution `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`.

Installed0.1.0.12/AEC3/MSIX сведения round128 остаются прежними, не новым
прогоном или пересобранным кандидатом на99b00a579. Shared UI не развёрнут.
Запись/микрофон не запускались, рабочие записи не читались/не мигрировались/
не удалялись. Push/PR/merge/release/deploy не выполнялись, issues не менялись.
Следующее безопасное действие — T114 generated-data исследование; код T116
и migration T117 остаются за gates. Документы раунда после checkpoint
пока не закоммичены и не выдаются за содержимое99b00a579.

## Раунд 133 — совместный зашифрованный stream и Media Foundation

Полоса high-risk-product, продолжается только разрешённое T114/Phase0
generated-data исследование. HEAD остаётся
`99b00a579c24b50e320465b69d9a296038bc544d`; source приложения, plan/tasks,
spec/constitution и reviewer-owned checklist отметки в этом раунде не менялись.
Рабочие записи, microphone/render endpoints и сеть не открывались.

Disposable source вне Git:
`/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/ProtectedMfProof.cpp`.
SHA256 `dd6e1c0a37b778adff8ecba6149cf89704acb646d4c19d0cf4551098ad765237`.
Переиспользованы BlockProof.cpp
`b7b638ea24d4fc6522daa7d18a880ddd75255ac965350a528cc4909f15f58410`
и CommitProof.cpp
`ced3982c08668428390f32983b1e7a374f9aec1fedbdfa928290af1de1d9b387`.
build.cmd SHA256
`5f237d4d5ec5e4d94a09c454a3f41846d432475a11dc1a0c00e84610cef4917e`;
run.ps1 SHA256
`5988eba1602ac720c6fc202b114d668cf89b68d9611d9e7faaa1951786dbc855`.
MSVC x64 /std:c++17 /MT /O2 /W4 /WX build0, EXE SHA256
`1c511c7fa517ec3a38ea41e741227eb9b7fc7a5a9c365d1891c83b67b1a60282`.
Windows11 ARM64 Parallels running, x64 executable эмулируется; это не физический
x64 аппаратный результат. Пакет GRAF не пересобирался и не переустанавливался.

Команда сборки: `prlctl exec 'Windows 11' --current-user cmd.exe /c
C:\Mac\Home\Documents\graf-windows-followup-200\f200-protected-mf-proof.jADm92\build.cmd`.
Команда проверки: `prlctl exec 'Windows 11' --current-user powershell.exe
-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File
C:\Mac\Home\Documents\graf-windows-followup-200\f200-protected-mf-proof.jADm92\run.ps1`.
Runner сверяет точный EXE hash, own45s watchdog и ограниченный metadata output;
дочерний reopen имеет собственный30s watchdog, чужие процессы не завершаются.
Один вызов Parallels вернул Invalid argument до результата запуска;
running VM/own processcount0 проверены до повторного вызова.

Последний успешный прогон точного EXE: PROBE_EXIT0, STDERR_BYTES0.

- CANONICAL:3840123 generated pattern bytes;64 exact8192B range reads после
  close/reopen;15 checkpoints, max index publication8041us, short-tail Commit8323us.
- RECOVERY:17 собственных files DPAPI/context/digest validated до corruption;
  точное прежнее поколение3670016B при corrupt-tail и invalidslot1;
  оба invalid indexes отвергают открытие, не возвращают empty success.
- MF:3000×480frames mono PCM16/48k, искусственная тишина30s (не30s wall-time
  capture);366529 logical M4A bytes,2881536 decoded PCM bytes до EOS;
  SourceReader seek10s→1s с bounded32samples и fixture timestamp oracle±1s;
  отдельный reopen child повторяет decode/seek и завершается0.
- MF4checkpoints/2rewrites, max index publication7956us; private-memory delta9613312B,
  total experiment5083ms. Delta — не peak; весь experience elapsed — не Stop
  latency. Canonical Commit — не product dispatcher/finalizer acceptance.
-6 собственных media objects проверены DPAPI/context/digest. Это ограниченный
  fixture-directory proof, не blanket absence of plaintext on the whole system.

Restricted same-user medium опыт запускался тем же runner с `-Medium`;
CreateRestrictedToken(DISABLE_MAX_PRIVILEGE/admin deny-only) и integrity8192
без глобальных UAC/desktop/profile изменений. Дочерний процесс не дошёл до
проверочного результата: exit−1073741502 (0xc0000142 DLL_INIT_FAILED), stdout
пустой, STDERR_BYTES0. Средний уровень и отсутствие admin должны проверяться
внутри child до fixture, поэтому standard-user PASS не объявлен. Причина
не установлена; нельзя считать это доказанной ошибкой DPAPI или full account
матрицей. Ни пароли, ни повышение прав, ни изменение системного desktop DACL
для обхода отказа не выполнялись.

Fixture ограничена64MiB/256entries/одним256KiBcache; SetSize только same-size,
Clone/CopyTo unsupported; GC/orphan cleanup, pinned-reader lifecycle и wire
format не реализованы. Коррупция — не power loss. Не проверены peak/bounds,
большой index, ключ другого профиля, disk-full/все partial publish boundaries,
native MediaEngine playback, product fences/5s dispatcher, migration и100cycles.
Generated artifacts сохранены только во временном каталоге стенда, не custody
приложения и не Git. T114/Phase0 и общий source implementation STOP остаются
открытыми; T115–T118 не исполнялись. Commit/push/PR/merge/deploy/release нет.

Независимый read-only review первого source dd6e… нашёл три недостатка
исследовательских assertions/метрик, не доказанный ложный PASS: generic catch
для both-invalid; отсутствие проверки последних42305 canonical bytes и
содержимого fallback; commit_max_us фактически охватывал только index publish.
Все три исправлены минимально только в disposable fixture: принимается ровно
`reopen-validated-index`, остальные исключения пробрасываются; bounded64KiB
чтение сверяет exact Stat length и все canonical/fallback bytes с pattern;
метрика названа `index_publish_max_us`. Указанные выше старые times относятся
только к публикации индекса, не полному protect/block-write/checkpoint.

Исправленный source SHA256
`141b5a293748703bf52fc50ce5d8c92a6f6df39c6a9f8fe389023e1c40b2f490`,
MSVC build0, EXE
`60ccffd7a3daa6cc5607e1213a4af4e97ec90ea8248df697aab5a0b1cdd728ea`,
runner `d5d05ba57657ab413bc39cf2a047b291244779d4d18b6d30820e86bc7187250b`.
Тот же bounded runner после точной hash-проверки: exit0/stderr0;
canonical3840123 **full_identity=true** + прежние64ranges/15checkpoints,
index-publish max57221us, short-tail Commit6279us; fallback3670016
**full_identity=true**, both-invalid отвергнут по точной ожидаемой причине.
MF logical366529/PCM2881536,2SourceReader seeks,child reopenexit0,
4checkpoints/2rewrites,index-publish max6573us, private delta7852032B,
total4376ms. Данные и условия MF прежние; не playback/peak/dispatcher acceptance.
После этой правки restricted-medium не перезапускался: его зафиксированный
отказ относится к предыдущему exact EXE1c511… и не переносится на новые bytes
как новый результат. Ни одного standard-user PASS по-прежнему нет.

Reviewer-owned `checklists/review-2026-10-01-protected-stream-proof.md`
сверил final source/EXE/runner hashes и закрыл только три замечания в коде;
не воспроизводил build/run и не принимает весь стенд/формат/F200. Main-agent
exact runtime результат выше — отдельное свидетельство, не независимый
аппаратный тест. Spec Kit governance, frozen bootstrap doctor, YAML parse и
diff-check прошли; plan/tasks hashes прежние, ни одна задача не закрыта.

## Раунд 134 — причина отказа restricted launcher и medium DPAPI/MF proof

Предыдущий goal-turn: progress — новый combined proof и исправленные assertions.
Продолжается только T114/Phase0 high-risk-product исследование. HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`; product source, plan/tasks/spec/
constitution и reviewer checklist отметки не изменены. Ни GRAF, ни устройства,
рабочие записи, account credentials, UAC/системные DACL/службы не затрагивались.

Read-only ContextProof source306c…/EXEfee51… показывает session1/WinSta0,
restricted medium8192/adminfalse, original/restricted native station/desktop
open error0 на минимальных запрошенных masks; identity revert проверен.
Это не full-access доказательство. Один minimal source
`0729e88fa8228f0bbe29e1aff012009ef40682315fd6e1f6c781366bf7bdabc7`
собран /W4 /WX /MT /O2 в x64 и native ARM64 (build0; PE machine отдельно
проверен). x64 EXE
`aeb85380caa22c65f2397f9a12b64c05bb25462d20402bc8679b959fd4e8f8ae`,
ARM64 `153ec8049f00e763fbc55c6e1055949255e38addfa90c3b32d5d61c617a6a8ce`:
оба actual self-child завершаются0xc0000142, parentexit1/stderr0. Они не
содержат MF imports и не вызывают storage. Эмуляция x64 не необходимое
условие этого launcher отказа; вывод не переносится на WASAPI clock fault.

Read-only token defaults source8ea82…/EXEf4cbb…: owner_is_user=true,
user_allow_ace=false/admin_allow_ace=true, stdin_present=true/type3 (pipe).
Проверка не читает содержимое pipe и не экспортирует SID/object names.
Затем exact source
`f8407e32ee7621fbdaa83ccd254a7dd248e40d978ce993678503a6c5d24726cc`,
EXE `a80f5b6420ff121132cbece275f3480844b06e258f803997b1353aad22ada387`,
runner `a8577c8dd2b44fb255171534cf25785640e078fc72afc09f2bd58636553b1b28`:
`-Spawn` FAILchild0xc0000142; `-UserDacl` PASSchild0/parent0/stderr0 с
actual child medium/noadmin assertions. Единственное условие A/B — добавление
current TokenUser GENERIC_ALL ACE в DefaultDacl нового filtered token через
SetEntriesInAclW/SetTokenInformation, без изменения исходного token/аккаунта/
системных ACL. Исследовательские результаты26856… и8f810… сохранены вне Git.

Final disposable ContextProof source
`78c3576b3fd3404f86c175dfc194a33e25a4a95b2dbf92c31863dd838fcd80b3`,
x64 build0, EXE
`fe4694df521254fd2aa44a31a1f49042c2e3f6b63408c72422018a4383dfc54e`,
runner `cb661045f5b0201d8d8d486025c1291947ae6543ef8d5180dd2fa89c94b35a0b`.
Source/runtime находится в том же disposable f200-protected-mf-proof.jADm92,
не в приложении. `-Mf` проверяет Media EXE hash до/после и запускает
ProtectedMfProof `--medium` через исправленный filtered token.
Media source/EXE неизменны141b…/60cc… (полные SHA в round133).
Native собственный unnamed Job Object KILL_ON_JOB_CLOSE:
CREATE_SUSPENDED → checked AssignProcessToJobObject → ResumeThread;
на assignment failure останавливается только свой suspended child.
Обычный self-child deadline10s/outer15s, MF35s/outer45s; это не product5s drain.
Job не наследуется, не имеет breakaway flags и удерживает собственный MF/reopen
process tree. Timeout/kill ветки здесь не fault-injected, не приняты как тест.

Команда свежего положительного опыта: `prlctl exec 'Windows 11' --current-user
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File
C:\Mac\Home\Documents\graf-windows-followup-200\f200-protected-mf-proof.jADm92\context-run.ps1 -Mf`.
Actual CONTEXT_EXIT0/stderr0, childexit0/medium_nonadmin_verified=true;
Media вывод restricted_medium=true. Canonical3840123 full_identity/64ranges/
15checkpoints; validated fallback3670016 full_identity и exact rejection
both-invalid,17 own cipherfiles. M4A366529/decodedPCM2881536/2SourceReader
seeks/childreopen0/4checkpoints/2rewrites;6media cipherfilesvalidated.
Index-publish maxima26722us canonical/4675us media, tailCommit8771us,
privateDelta7188480B, total3876ms; не peak/fullcheckpoint/Stop bounds.
Metadata result9759c81a… json записан только в отдельный каталог стенда;
его EXE/MF SHA и exit/output прочитаны main. Нативный process inventory после
опыта: ContextProof/ContextProofArm64/ProtectedMfProof count0.

Parallels Job getter временами возвращал Invalid argument; один CIM inventory
завершился parser error и не принят как отсутствие процессов. После него
проверен Get-Process и terminal handle, неизвестный результат не выдаётся за
PASS. Последовательные exact A/B/MF выводы и собственные metadata receipts
выше — authoritative для опыта, не для installed GRAF. Артефакты не удалялись.
Обычная отдельная account/Home/installed package, native MediaEngine playback,
large index/GC/peak/IO/fault boundaries/power loss/migration/SC-003 остаются
открытыми. T114 и вся Phase0 не закрываются; code T116/T117 не начинался,
нет commit/push/PR/merge/release/deploy или изменения issues.

Независимый reviewer-owned `checklists/review-2026-10-01-medium-launch.md`:
APPROVED NARROW для launcher/runner, не всего storage/Phase0/приложения.
Проверены final source/EXE/runner и actual-token assertions в неизменённом
Media proof; runtime main reviewer самостоятельно не воспроизводил.
A/B устанавливает влияние private TokenDefaultDacl на минимальный запуск,
не конкретный сбойный DLL/объект и не новый A/B после добавления own Job.
Context hash в runner проверяется до запуска и записывается после, но после
не сравнивается повторно; отдельный main hash-check показал прежний fe469….
`files=false` относится только к context-операциям, не к MF-tree, который
создаёт собственные synthetic ciphertext artifacts. Governance/YAML/diff-check
прошли; ни одна task/reviewer checkbox не закрыта, общий NOT READY сохраняется.

## Раунд 135 — native playback защищённого потока и отказ при повреждении

Lane: active Spec Kit high-risk Phase0/T114, generated-data disposable proof,
не продуктовая реализация. Repo/branch/HEAD прежние:
`codex/200-windows-followup`, `99b00a579c24b50e320465b69d9a296038bc544d`.
Промежуточный коммит не изменён; spec/plan/tasks/constitution hashes round134
сохранены. Источники приложения, macOS и сервер не менялись.

Опытные файлы находятся вне git в прежней Windows-visible исследовательской
папке `f200-protected-mf-proof.jADm92`. Не использованы реальные записи, ввод
устройств, пароли, сетевой media URL или открытая копия M4A. MediaEngine muted
и Volume0; штатный audio render может инициализировать выход, потому field
`output_render_possible=true`, не утверждение `devices=false` для дерева.
`application_network=false` означает отсутствие сетевого вызова/источника в
стенде, не системный network trace. `files=false/devices=false` Context
по-прежнему относится только к операциям родительской диагностики.

### Exact sources, сборка и обвязка

| Артефакт | SHA-256 |
| --- | --- |
| PlaybackProof.cpp | `599ccaf4f02b7102c35c40415ef2682478beda9608d8166f5d39681189a7e898` |
| PlaybackProof.exe | `3f80a5f3b83cb259357165886df3a80e21f42833d04decaaf568fff127ed21b5` |
| ContextProof.cpp | `ebe944228e9349a5781ecece1605f651d6fdd78cbaa9b9c932dac06cf7b244c6` |
| ContextProof.exe | `aa876c21a7657f84bfa82047f8830491208876935c95598ec6a9009f07ea65f4` |
| context-run.ps1 | `3be550b7f2b68eea3fe6e6c4c95bf7162a8fc8a82d74543dcd38b89022e45268` |
| ProtectedMfProof.cpp (общий include) | `58e65c6e914d8e54c0b868e4d0e0208225b74de57ed6769c5decebd3c9e8c3a2` |
| playback-build.cmd | `4c7f1e6b1b14fdda0c4e72a03107f7471f434d9336ac1fc8097602eaf2e2faad` |
| context-build.cmd | `941809fd29f686295999de9f1efb3bfb342d565ca5d2b1627c7f9381d6483ae3` |
| CommitProof.cpp | `ced3982c08668428390f32983b1e7a374f9aec1fedbdfa928290af1de1d9b387` |
| BlockProof.cpp | `b7b638ea24d4fc6522daa7d18a880ddd75255ac965350a528cc4909f15f58410` |

Playback включает ранее проверенный protected stream/encoder, не дублирует
его. Единственное изменение общего source — выбираемое имя исследовательского
entry point; ранее собранный ProtectedMfProof.exe60cc… не пересобирался.
Source141b…/Context78c…/EXEfe469… round133/134 — исторические bytes, не текущие.
Первая compilation дала macro collision/неверное enum имя; исправлены include
entrypoint и MF_MEDIA_ENGINE_PRELOAD_AUTOMATIC. Окончательные отдельные x64
`playback-build.cmd` и `context-build.cmd` через `prlctl exec 'Windows 11'
--current-user cmd.exe /c …` завершились0 с `/W4 /WX`.

Context добавляет только фиксированные playback/fault modes и свой sibling;
same-user medium8192/noadmin assertions, private-token user grant и собственный
Job сохранены. UAC/global ACL/учётные записи/частоты/clock thresholds не менялись.
Runner проверяет оба EXE до/после, сохраняет bounded metadata receipt и не
принимает ненулевой exit. Watchdog35/45s — ограждение опыта, не5s product fence.

### Результаты на одной окончательной сборке

Последовательно выполнялись `context-run.ps1 -Playback` и `-PlaybackFault`
через `prlctl exec 'Windows 11' --current-user powershell.exe -NoLogo
-NoProfile -NonInteractive -ExecutionPolicy Bypass -File …`. В обоих случаях
terminal exit0, Context exit0, child exit0, stderr0; child проверяет actual
medium/noadmin до собственной работы. Main прочитал exact metadata receipts:

- Positive: `context-result-22abdb51-5358-4f95-b9b2-1bf6ae8ccf31.json`.
  Generated30s AAC,366529 logical bytes. Play advances≥0.2s; после Pause позиция
  стабильна150ms в пределах0.05s. Seek10s/1s/near-end подтверждены событием SEEKED,
  IsSeeking=false и позицией±0.25s; два Resume advances≥0.2s. ENDED получен
  **после перехода к хвосту**, не после непрерывных30s прослушивания. Shutdown16ms;
  последующий Play возвращает MF_E_SHUTDOWN. Шесть собственных файлов прошли
  DPAPI-envelope проверку до и после. Это fixture oracles, не новые product limits.
- Fault: `context-result-9ea4a118-dd4b-4315-b87e-54a6939c7c40.json`.
  Fresh generated fixture validated reopen, затем изменены только свои b0-*
  ciphertext versions до MediaEngine чтения. SetSource вернул0, настоящее ERROR
  дало HRESULT0x8003001e/code4. Следующий Read вернул STG_E_READFAULT/got0,
  что подтверждает прежний отказ storage-пути, не первое чтение контрольного
  вызова (оно вернуло бы STG_E_WRITEFAULT). Shutdown/post-Play guard прошли.
  `cipher_objects=6` — **проверка до повреждения**, не шесть валидных после него.
  Timeout/произвольное исключение не принимаются за expected rejection.

Предварительный positive `60540f7c…` прошёл на source95c…/EXE0d63… и Context
15ec… с Shutdown15ms; он не заменяет проверку окончательных bytes выше.
После двух final запусков EXE/source/runner hashes совпали; отдельный scoped
Get-Process ContextProof/ProtectedMfProof/PlaybackProof завершился0 без процессов.
Все собственные terminal handles завершены; fixtures retained, ничего не удалено.

Этот результат не проверяет всё окружение disk/temp/cache, peak memory,
large index, GC/pinned readers, block/index publication faults, key loss,
power loss, миграцию, весь finalizer/dispatcher, installed GRAF/Home/отдельную
standard-user account, реальное звучание или hardware/x64 matrix. Native
callback имеет только atomic metadata и не владеет UI; ошибка закрывает engine
через RAII. Product ShellExecute пока не заменялся. T114/Phase0/FR-012 целиком
остаются открытыми, T115–T118 не начинались; нет нового commit/push/PR/merge,
release/deploy/issue изменений или закрытых reviewer checkbox.

Независимый `checklists/review-2026-10-01-native-playback.md` — APPROVED NARROW
для final code/runner и согласованности двух прочитанных receipts. Закрыто
замечание P2: MFShutdown теперь сохраняет nonzero при ошибке и не выбрасывает
исключение за пределами catch. Reviewer не воспроизводил Windows runtime и
не хешировал EXE в VM; source/runner hashes и metadata receipts проверил сам.
Main перечитал весь31-line report. Receipt SHA-256 отдельно совпали:
positive `42f296875c269eb79b79ca2b9e89bca4bddf9d0aa04bd3e16440da9ef1717a13`,
fault `943f0583471af4f158015880496625c2db0de0ca07e7645a390204adde75544f`.
Свежие `check_spec_kit_governance.py`, `speckit-bootstrap . --doctor --frozen`,
Ruby YAML parse F200 и `git diff --check` завершились0. Broader product tests
в этом docs/research-only раунде не запускались; прежние результаты не выдаются
за новую проверку установленного приложения. Общий NOT READY сохраняется.

## Раунд 136 — восстановление рабочей копии, сбои публикации и безопасный повтор

Lane: active Spec Kit high-risk Phase0/T114; generated-data исследование вне
git, не продуктовая реализация/миграция. HEAD остаётся
`99b00a579c24b50e320465b69d9a296038bc544d`, ветка `codex/200-windows-followup`.

### Восстановление рабочего дерева

После прерывания прежний каталог `200-windows-followup/crisp` и его регистрация
Git отсутствовали; ветка и промежуточный коммит сохранились. Пользователь
подтвердил, что сам дерево не переносил и не удалял. Причина исчезновения не
установлена. Прежний путь восстановлен `git worktree add …
codex/200-windows-followup`, без reset, изменения других веток или удаления.
После создания HEAD совпал, status был чистым.

Пять незакоммиченных документов и четыре reviewer reports возвращены из exact
apply_patch calls собственных main/reviewer session histories после checkpoint.
Результаты не исполнялись как JavaScript: применён только whitelist этих девяти
путей через apply_patch. Один исходный пустой неуспешный patch пропущен; остальные
20 восстановлены в исходном порядке. Временный recovery script/извлечённые
patches вне git. Plan/tasks/spec/constitution SHA-256 совпали с round135:

| Документ | SHA-256 |
| --- | --- |
| spec.md | `9f7e0d9ca96c6be1209af723e5fad0745a9b78cf8314f2b2996d6697de5c20b2` |
| plan.md | `7c32bca2821465a4b052839e0790b0b7938b1215c154b6c6e97f5206f19643d0` |
| tasks.md | `2019b804de49724efbb6e6bf31f6faa490b10c1869ff88ba6a26aa889c6e0655` |
| constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Игнорируемый per-worktree feature.json вновь указывает F200/high-risk и текущий
source_sha. Прежние private build/cache files не объявляются восстановленными.
Основной репозиторий, 0309, macOS/server/product code и root CHANGELOG не менялись.

### Исходный отказ и минимальное исправление стенда

Baseline receipt `context-result-3b89d399-3dd2-4e35-9de7-5c7466ab4193.json`
содержит 28 boundary cases/12 sticky fences и отдельно ORPHAN_RESUME_LIMITATION:
после оставшегося непубликованного блока повтор выбирал занятую версию;
CREATE_NEW давал отказ, прежний checkpoint сохранялся. Exit0 стенда здесь
означает обнаруженную ожидаемую **ограниченность**, не successful resume.
SHA-256 квитанции:
`104e9089a5a2ddaadefee6481620f80a930cde90bfff4dd8dea3d79bd42e2b64`.
Baseline Publish source78da…/EXE5ba4…/Protected69c2… — исторические bytes.

ProtectedStream теперь после validated-index selection последовательно учитывает
имена оставшихся block versions, не расшифровывая/удаляя их; максимум1024
объекта, индекс<256 и допустимые ненулевые версии. Candidate index name имеет
generation-version. Это fixture-only ограничение, не принятие 64GiB layout,
GC, adversarial path или нескольких writers. Выбранный индекс остаётся authority.

Независимый reviewer нашёл P2 в oracle введённых исключений: любой ранний
throw превращался в STG_E_WRITEFAULT и мог подменить нужный hook. Исправлено
только в тесте: reachedPoint сбрасывается перед update, устанавливается внутри
совпавшего faultProof перед исключением/ExitProcess и должен совпасть с point.
Контрольpoint0 требует S_OK; обычный throw в process-cut child не даёт exit77.

### Окончательные bytes и запуск

| Артефакт | SHA-256 |
| --- | --- |
| PublishFaultProof.cpp | `86154323134767f45fbda4d96411e8d1551ac444f28742b1438030b825f245d5` |
| PublishFaultProof.exe | `490b036c4bfbdaa34239997236ed690b5ff76e5317734106d754ad9b4da49633` |
| ProtectedMfProof.cpp | `2d61206608ddf20b4fdda0a145a9c4f242e6aac584df638b81268f46b5ae9461` |
| ContextProof.cpp | `effccaead024847d1f5979ec23513ad53c6b8a1d64dbca04ae7c7617db328d99` |
| ContextProof.exe | `3fa12e4893b0b363c99c9c35de225cd83633c689d4e87638e98db6e0fc722c2a` |
| context-run.ps1 | `9c93bbec222ed8f7c3350a99d91ce1e5e79761b34ae82daf138f02de74264f18` |
| publish-build.cmd | `10f0ecdacbee98b721b0ba86f4db036b9b379e3f68da693b7de3d5334d1e426e` |
| context-build.cmd | `941809fd29f686295999de9f1efb3bfb342d565ca5d2b1627c7f9381d6483ae3` |

Сборка x64 `/W4 /WX` завершилась0. Parallels однажды вернул getter error после
отправки команды; она могла запустить сборку. Перед опытом проверены фактический
EXE hash и scoped process inventory, собственных proof/build процессов нет.
Обнаруженный CL PID5528 относится к MSBuild от17сентября, не этому опыту;
он не останавливался. Runner закрепил final hash и проверил оба EXE до/после.

Команда: `prlctl exec 'Windows 11' --current-user powershell.exe -NoLogo
-NoProfile -NonInteractive -ExecutionPolicy Bypass -File …\context-run.ps1
-Publish`. Terminal/Context/child exit0, stderr0. Child и каждый cut child
сами проверяют medium8192/noadmin; используется тот же профиль и private-token
grant и собственный Job, не отдельная standard-user account. Main прочитал receipt
`context-result-42555b77-a62b-4cdd-b3fb-16edb5f88d90.json`, SHA-256
`f53fbd4a7a28102bd7dae2c320b9403322a27751f2e9af7c9492b555594fbe28`.

- 28 случаев: append/rewrite × введённое исключение/process exit × контроль0
  и точки1–6. При1–4 полные прежние bytes/length, при5–6 полные новые;
  это наблюдение process-cut, не power-loss durability.
- 12 writers после исключения отвергают Read/Write/Commit; got/wrote0.
- 16 случаев1–4 дополнены успешным повтором: полные новые bytes совпали,
  reader, открытый **после сбоя до повтора**, сохранил прежнюю полную версию;
  hashes прежних block/temp объектов, снятые после сбоя, не изменились
  **во время повтора**. Это не ещё16 независимых точек и не reader до сбоя.
- В каждом update изменяется один блок: append4096 к хвосту123 либо rewrite
  первых8192. Multi-block transactional commit, серия повторных сбоев,
  inventory limit/overflow и key-loss этим опытом не проверяются.

Нет ввода устройств/реальных записей/network content/UAC или global ACL edits.
Generated fixtures сохранены. Отсутствие своих proof процессов проверено после
опыта; historical CL оставлен. Watchdog35/45s — guard стенда, не5s product Stop.
Полные peak/resource/large-index/GC/key-loss/Stop/миграция/installed Home и
hardware остаются открытыми. T114 и Phase0 не закрыты; T115–T118 не начаты.
Commit/push/PR/merge/release/issue изменений в этом раунде нет.

Независимый reviewer лично перечитал source/runner и обе exact receipts,
вычислил их hashes; `checklists/review-2026-10-01-publish-faults.md` — APPROVED
NARROW/P2 closed, полный T114 NOT READY. Main перечитал весь итоговый отчёт.
Reviewer не запускал VM/сборку и не устанавливал binary-source equivalence;
helpers за пределами четырёх выбранных исходников он не проверял. Свежие
governance, frozen bootstrap doctor, YAML parse и diff check прошли0. Всего
118 уникальных задач:91 закрытая/27 открытых; T114–T118 остаются открытыми.
Plan/tasks hashes сохранены; git diff продуктовых путей пуст.

## Раунд 137 — память, IO, хвост, MF finalization и максимальный native envelope

Lane: active Spec Kit high-risk Phase0/T114, generated-only disposable опыт,
не продуктовая реализация. HEAD/branch прежние99b…/codex/200-windows-followup.
Полный current HEAD `99b00a579c24b50e320465b69d9a296038bc544d`.
План дополнен выводом о foreground/recovery/type-specific bounds; tasks,
spec, constitution, Windows/macOS/server product code не менялись.

### Exact artifacts и запуск

Прежняя внешняя Windows-visible папка `f200-protected-mf-proof.jADm92`.
ResourceProof переиспользует protected stream, pattern/identity, DPAPI helpers,
MF encoder/decoder; новые продуктовые классы/зависимости не введены. Единственное
изменение encoder helper — возвращает измеренное время Finalize, release и
tail Commit, остальные два caller игнорируют return. Context добавляет fixed
Resource sibling/60s child watchdog, старые guards35s/10s неизменны; runner
Resource70s, остальные45s/15s. Это guards опыта, не расширение product5s Stop.

| Артефакт | SHA-256 |
| --- | --- |
| ResourceProof.cpp | `062560d273dc37c7458c14bcdd952361cc4f160d0eda68152cf46e9c04135abc` |
| ResourceProof.exe | `4e989c3d8d0998d392afdff90ba251141b42a1415f3ce726a923dd6ee87f9688` |
| ProtectedMfProof.cpp | `6d09fa40dbc7b77eef34235dced9eccb247d008de08ea4564eb9f1e394acf29f` |
| ContextProof.cpp | `68a388a4acb58854de97df8aae4df2839a2f614a6d0538f0134af75f1c32fa01` |
| ContextProof.exe | `1f9840a07dd990c33b7346f26b597e9ab6f9b3a4f02b42b6903f8d3fe79aa16b` |
| context-run.ps1 | `28e9c1e6b69ea5bf4826e2132c12705ee3fd7e96bff3362f5d3f640508e25a19` |
| resource-build.cmd | `a6bd7217d1b9185c186c49bed52260c5b233a737d17c5257afc83769ff76fb3a` |
| context-build.cmd | `941809fd29f686295999de9f1efb3bfb342d565ca5d2b1627c7f9381d6483ae3` |
| CommitProof.cpp | `ced3982c08668428390f32983b1e7a374f9aec1fedbdfa928290af1de1d9b387` |
| BlockProof.cpp | `b7b638ea24d4fc6522daa7d18a880ddd75255ac965350a528cc4909f15f58410` |

Resource/Context x64 сборки `/W4 /WX` завершились0. Каждый свой tool handle
доведён до terminal; после transient waiting повторно прочитан тот же handle,
сборки из-за отсутствия вывода не перезапускались. Перед запуском scoped
inventory не показал собственных Context/Resource/proof процессов; historical
CL5528 от17сентября не трогался. Runner сверил оба exact EXE до/после.

Команда: `prlctl exec 'Windows 11' --current-user powershell.exe -NoLogo
-NoProfile -NonInteractive -ExecutionPolicy Bypass -File …\context-run.ps1
-Resource`. Terminal/Context/child exit0, stderr0, actual medium8192/noadmin.
Main прочитал всю metadata receipt
`context-result-38d913ac-efb9-4b02-b8ef-63f4bef98491.json`, SHA-256
`84be963417a7ba91685e9077bded58c346c7533df2f6123dba521cd45879c25c`.
Fresh NTFS fixed-drive directory со своим protected DACL; до записи проверено
256MiB available; сумма retained file sizes85771612B, около81.8MiB. Это ограничение
стенда, не замена product quota/reserve/disk-full checks.

### Stream результаты

Каждый случай записан chunks64KiB, Commit, освобождение writer, validated reopen,
полный oracle read, проверка всех ciphertext envelopes и сумма file sizes.
Число объектов равно ceil(length/256KiB)+2; файл-count/file-byte bounds проверены.

| Метрика | 1MiB+123 | 16MiB+123 | 64MiB-123 |
| --- | ---: | ---: | ---: |
| Logical bytes | 1048699 | 16777339 | 67108741 |
| Disk file bytes | 1050954 | 16799154 | 67192828 |
| Cipher objects | 7 | 67 | 258 |
| Elapsed us | 511628 | 5965334 | 25837847 |
| Process CPU 100ns | 2187500 | 28750000 | 117656250 |
| Process IO read bytes | 4201818 | 67190778 | 268491346 |
| Process IO write bytes | 1052028 | 16851948 | 67793792 |
| Private before / after bytes | 11481088 / 12718080 | 12718080 / 12464128 | 12464128 / 12341248 |
| Sampled private max bytes | 12234752 | 12718080 | 13570048 |
| Lifetime peak commit bytes | 13287424 | 13574144 | 13574144 |
| Lifetime peak working-set bytes | 20721664 | 20963328 | 21168128 |
| Checkpoints | 5 | 65 | 256 |
| Max Write-call us | 124842 | 30163 | 430476 |
| Max index-publication us | 5682 | 7522 | 388144 |
| Final-tail Commit us | 7560 | 2685 | 24035 |
| Validated reopen us | 143588 | 2305724 | 9441713 |

PeakPagefileUsage — lifetime process peak commit; PeakWorkingSetSize — lifetime
peak resident working set, не isolated layer budget. Samples берутся на
границах Write, не заменяют peak counter. IO/CPU относятся ко всему одному
процессу/окну опыта, не только диску/криптографии и не dispatcher. File sizes
не доказывают physical allocated sectors или отсутствие всех OS caches.
Elapsed включает несколько decrypt/verify проходов. Это accelerated batch
без input clock/60min/reference4-core x64 warm-up; SC-00325%/128MiB не принят.

Полный reopen64MiB9.44s противопоказан foreground/readiness/callback. Read-only
кодовая проверка подтверждает существующий `AppMain.cpp::LocalMetadataScan`
background inspect и open-validation; UploadRecoveryScheduler запускает upload
в worker. NativeCapture constructor синхронно load/prune ledger, туда нельзя
добавить scan всех protected media. План фиксирует reuse existing workers и
account/delete/shutdown fences; фактическая защищённая интеграция ещё не сделана.

### Media Foundation и большой envelope

В том же process: AAC generated30s → protected reopen → decode/SourceReader
seek → envelope check6files. Logical366529B, PCM2881536B, retained file bytes
728676B (включают прежние immutable versions). Finalize/reset/tail Commit
226499us; encode/decode/validate556422us. Lifetime peak commit32280576B,
working-set43868160B. Это не whole Stop/dispatcher fence и не playback test.

Затем отдельный in-memory native DPAPI envelope для выбранного upper bound
index4096+262144×16=4198400B: cipher4198694B, protect280359us,
unprotect+whole compare261735us. Lifetime peak commit37257216B,
working-set59314176B. Whole identity проверяет context/digest/payload bytes;
это **не semantic index, disk publication или full64GiB recovery**. Existing
validate helper ожидаемо отвергает payload больше1MiB; его cap не изменялся.
T115 обязан различать block/index bounds, не расширять общий media cap.

Нет input/output devices, real recording, network call, user file migration,
global ACL/UAC/profile edits. Source/hash checks совпали после опыта, inventory
не показал своих процессов; generated fixtures сохранены. Вне объёма: full
large layout, multi-reader/GC, key-loss, product Stop/dispatcher, 60min audio,
installed standard-user/Home/hardware и весь protected pipeline. T114/Phase0
и T115–T118 остаются открытыми; нового commit/push/PR/merge/release/issue нет.

Независимый `checklists/review-2026-10-01-resources.md` — APPROVED NARROW для
source/oracles и согласованности current receipt/runner, не SC-003/T114.
Main прочитал весь142-line report, включая ограничения counters, repetitive
pattern oracle, MF codec без audio-render, unhandled invalid manual arguments,
bounded-after-read stdout, и cleanup синтетических buffers при исключении.
Helpers reviewer независимо не проверял, VM/binary-source build не повторял;
Main проверил их неизменные hashes. Старые published/Playback EXE не
пересобирались и не считаются проверкой нового Resource source.
Свежие governance/frozen bootstrap doctor/YAML/diff check прошли0. Tasks/spec/
constitution hashes round136 сохранены, git diff продуктовых путей пуст.
После этого раунда plan SHA меняется; прежний encryption-plan review относится
к сохранённому тогда дополнению, не подтверждает новые resource constraints.
Current plan SHA-256:
`d052b57fe81fd919972f7017a1649f2fbc0794144a49adca0485e1f12ece7b0c`.

## Раунд138 — максимальный ZERO-only индекс, 2026-10-01

Продолжение T114/Phase0, high-risk storage research. HEAD остаётся
`99b00a579c24b50e320465b69d9a296038bc544d`; продуктовые пути не менялись.
Стенд вне Git: `Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92`.
Собственные generated файлы сохранены; пользовательские записи не читались.

### Сборка и привязка

Index x64 MSVC `/std:c++17 /EHsc /MT /O2 /W4 /WX` завершился0. Первая попытка
выявила C4245 у SetLastError(NTE_BAD_KEY_STATE), исправлен явный DWORD cast.
После transient Parallels getter error сначала проверены scoped процессы и
отсутствие EXE; затем recording wrapper доведён до terminal0. Context отдельно
пересобран до terminal0. Historical CL5528 от17сентября не трогался.

| Артефакт | SHA-256 |
| --- | --- |
| IndexProof.cpp | `1eccae197bcda610e9d33c001254e4c27be14ede461c44dd683a7b0a24b7fa97` |
| IndexProof.exe | `0ef7d9af91c3697934cdb14d4a13b2e33721a8b19b797006a3f94df324443c15` |
| ProtectedMfProof.cpp | `6d09fa40dbc7b77eef34235dced9eccb247d008de08ea4564eb9f1e394acf29f` |
| ContextProof.cpp | `e60f1ba74a25aab5e2e0e23aa006bc93ac09437a6cfdf20b40f80930cce47f55` |
| ContextProof.exe | `83ce6724332dd291f1b1ce385a953253cb10ac585d952e771018b5fa71cae148` |
| context-run.ps1 | `5ba7c738a098ffa9bc35de252d0cd3190e89dfd69d7e65f51655e4d574c447eb` |
| index-build.cmd | `96c07c22b48152989efabc2e145e67b929d4b228b56dd411b722776ea7ae1030` |
| index-build-run.ps1 | `b0a72aa89f360c34a180662a97b779b1c15f390b2dfbfdc3358df99e0efb4e6d` |
| BlockProof.cpp | `462b4658dc7c2577119fbcc89c40d075c85e6e758a4372d45790590ee5c73daa` |
| CommitProof.cpp | `ced3982c08668428390f32983b1e7a374f9aec1fedbdfa928290af1de1d9b387` |

Build receipt `index-build-result-1e39e643-0baf-4fb7-8902-fcf4cbf4dd25.json`,
SHA `a245d9988f44aaeef2c9f7e7e24444aaa4a38fd41b9c5490e4bce5e1e41eb092`:
build_exit0, source/exe совпадают. Wrapper фиксирует главный source после
сборки, не атомарную attestation всех includes; helpers сверены отдельно.

Команда: `prlctl exec 'Windows 11' --current-user powershell.exe -NoLogo
-NoProfile -NonInteractive -ExecutionPolicy Bypass -File …\context-run.ps1
-Index`. Terminal/Context/child exit0, stderr0, medium8192/nonadmin внутри
процесса. Main полностью прочитал runtime receipt
`context-result-fda8c038-fbf7-46b4-907d-cd74dc66da11.json`, SHA
`75095009e16d2b889238c04c34b344cc7bba92e78f401e8329f568c6d13005d2`.
Before/after exact source/EXE hashes совпали; своих процессов после нет.

### Результат и точные границы

262144 entries, logical_dimension68719476736B; все строки ZERO, version0,
cipher0. Заголовок32B +262144×16B =4194336B на индекс. Семантический parser
проверяет schema/generation/slot/length/count/exact size/каждую ZERO запись.
Десять negative memory-parser cases требуют false и output generation0.
Ограничения покрытия: мутации строк только в первой записи; нет отдельного
in-range count/length mismatch и cipher≠0 при flags1. Эти cases не проверяли
семантически неправильный, но корректно защищённый payload на диске.

Два NTFS ciphertext файла8389260B; до записи проверено64MiB free. Публикация
обоих индексов609295us, полное чтение/DPAPI/envelope/семантика обоих550852us;
lifetime peak commit27152384B/working set39804928B. Это весь отдельный
ZERO-only процесс; не64GiB media IO, не startup SLA и не SC-003.

Выбран latest2; после порчи index0 выбран fallback1; после порчи index1
оба отвергнуты, authority=false/generation0. Test-only key-unavailable
вводится после readCipher и до CryptUnprotectData; счётчик ровно2, authority
отсутствует, ciphertext hashes сохранены. Это не native DPAPI failure или
потеря профиля. Hash preservation проверено для двух полностью отказных
read-путей; отдельного сравнения непосредственно вокруг успешного fallback
нет. Новый temporary индекс переименуется через MoveFileEx/Flush; поколения
1/2 заполняют разные слоты, третья замена и большие crash cuts не проверены.

Default helper cap1MiB сохранён, override4198400B только в IndexProof.
ProtectedStream по-прежнему64MiB/256entries; этот отдельный parser его не
расширяет. Context35s/outer45s watchdog не изменяет product5s dispatcher
drain. Нет COM/MF startup, audio devices/network/profile/global ACL/UAC edits,
plaintext media, migration, GC или изменения приложения. Fixtures retained.

Main прочитал весь независимый `checklists/review-2026-10-01-large-index.md`:
APPROVED NARROW, T114 NOT READY. Reviewer сверил receipts/source/runner,
прочитал shared helpers; build/VM и EXE bytes независимо не воспроизводил.
Остаются Stop/fence, реальная key boundary, nonzero large references и полная
файловая матрица. T114/Phase0 и T115–T118 не закрыты; commit/push/PR/merge/
release/issue не выполнялись. Plan/tasks/spec/constitution прежней редакции.

## Раунд139 — actual dispatcher / protected Stop, 2026-10-01

T114/Phase0 high-risk research, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d` не менялся. Disposable стенд в прежней
внешней папке, generated raw float samples; устройства и пользовательские
записи не используются. Product integration T116 не начиналась.

### Источник и сборка

Строится реальный WindowsCaptureSessionController и9его существующих units,
а не копия dispatcher. Через уже существующий friend CaptureSessionTestPeer
обходится acquisition/Record/readiness: ручные session transitions и запуск
реального dispatchLoop. Native render/mic workers не создаются. Mirror RecApp
совпадает с canonical code; diff только obj и packages.lock.json в зеркале.

Stop/Context x64 MSVC `/std:c++17 /EHsc /MT /O2 /W4 /WX /utf-8` terminal0.
Первый Stop build2: NOMINMAX повторно определён shared fixture при compiler
define для product units; исправлен только local #undef перед shared include,
без отключения warnings. Успешный build receipt
`stop-build-result-65d9ed40-a9fd-4e96-8780-4b3ad7f5d489.json`, SHA
`c7f52888652f2817475b86e08265726ac0ba23c7456e4b5ca276159b9f0619a0`.
Первый build receipt с exit2 сохранён отдельно, не считается успешным.

| Артефакт | SHA-256 |
| --- | --- |
| StopProof.cpp | `2a7987064de4648042944ad22ca2c7308f6355f091bad25fd6488380cb3a8ffa` |
| StopProof.exe | `5bde468d0ca00b43e4cf5e023a0c15eaf269de9c20ae1fa780d3d6af9e5d8912` |
| stop-build.cmd | `cba4bec0a50a465f5ab6f70c6d8f0f0f4f65ba0d4cf80990cc4981ebbcd4d361` |
| stop-build-run.ps1 | `8cfa36c05870a57d49c83bba0ffa03b4c11c6e4fd06ef8eadc35d0060e6939c4` |
| stop-run.ps1 | `85e77144d1589d6fc11d9c7ac90ce9d68c2e1a8aa3e0f7657d0d1f7189908ef1` |
| ContextProof.cpp | `38edcc4f88e1e44f6d668c2fa4b74f497f6baf6bec3caef00b32ec1b0f4243e4` |
| ContextProof.exe | `ebc73774df9b89e442f6d1f516b9bbeeb4bd1012b8ad9ea1503a29cdc1e22980` |
| WindowsCaptureSessionController.cpp | `cb14524af7efcebcd37f060744ee14c30d3551ce38be587a4069f118d628a8aa` |
| WindowsCaptureSessionController.h | `45810c5008b070b40a89c4b0e85e985603aa9751ab716553098aa4d8e7e2c740` |

Shared ProtectedMf/Block/Commit hashes сохранены из round138. Полные27 source
hashes перед/после запуска записаны в runtime receipt; они не являются
подписанной аттестацией compiler/includes. Context fixed sibling StopProof
работает в собственном Job, child guard35s/outer45s. Старый context-run.ps1
обновил только expected Context SHA (его новый SHA
`3d5346c62473e1b0597430db904e40e0407174142d8f6de47cddffe28ce48dda`);
исторические round138 source/runner hashes остаются историческими.

### Runtime

Команда `prlctl exec 'Windows 11' --current-user powershell.exe -NoLogo
-NoProfile -NonInteractive -ExecutionPolicy Bypass -File …\stop-run.ps1`.
Terminal/Context/child0, stderr0, actual medium8192/nonadmin, пять PASS markers,
accepted=true. Main прочитал весь
`stop-result-0393f785-c37b-41c7-81aa-1d1a347e8b1b.json`, SHA
`fe5e0916cdc6072e8688ee903385186cf9c5d5e65c6488d1a362c00efee0380c`.

| Случай | Stored batches / sink calls | UI Stop us | Protected worker us | Decoded PCM bytes | Cipher objects |
| --- | ---: | ---: | ---: | ---: | ---: |
| normal | 255 / 255 | 680 | 560248 | 245760 | 6 |
| queue overflow | 255 / 255 | 21 | 246829 | 245760 | 6 |
| rejected sink | 3 / 4 | 29 | 111548 | 4096 | 4 |
| throwing sink | 3 / 4 | 37 | 82119 | 4096 | 4 |
| sink held5100ms | 255 / 255 | 11 | 218577 | 245760 | 6 |

Реальный dispatcher:254pendingdata +1in-flight; Stop принимает два EOS в
зарезервированные слоты до UI polling. Late batch после Stop возвращает
discard contract, не увеличивает очередь256 и не приходит в sink. Exact FIFO
и rawfloat oracle проверены после tail Commit и validated protected reopen.
EOS mask3 и dispatchFinished проверены до каждого вызова UI Finalizer.

Один asynchronous worker возвращает nullopt до release/acquire job fence;
UI повторяет poll, но не запускает вторую job. Конкурирующая synthetic
session получает rejected до terminal, accepted после terminal. Повторный
Stop с interruption не меняет исходный userRequested. Единственный normal
case savedLocal; ошибки queueOverflow/clockDiscontinuity/finalizationFailed
соответствуют исходникам, savedLocal=false, trustedPrefixRetained=true.
Timeout удерживает stopping/lease и не освобождает protected writer до sink
completion. Worker выполняет protected canonical Commit, независимый AAC
zero-PCM encode той же принятой длительности и полное SourceReader decode.
Все retained файлы проходят DPAPI/envelope; нет plaintext content files.

Worker timing включает свою gate/encode/decode, не чистый Finalize. UI Stop
не измеряет весь user-perceived stop;5s drain не расширялся. Canonical bytes
проверены точно, но AAC не кодируется из них: нет v5/timeline/AEC conversion
приёмки или worker cleanup fence. Не проверены short-recording discard,
native input/output/hardware, profile keys, migration, large nonzero layout,
SC-003 или установленное приложение. Fixtures сохранены; своих процессов
после нет, historical CL5528 от17сентября не трогался. Нового commit/push/PR/
merge/release/issue нет. T114 и T115–T118 открыты.

Независимый source/runtime review запрошен в
`checklists/review-2026-10-01-protected-stop.md`; его результат дописывается
ниже после полного чтения. Отметки reviewer-owned checklist Main не меняет.

### Повтор round139 после исправления P2 проверочного условия

Main прочитал весь независимый report. REQUEST CHANGES: mode3 мог принять
исключение fifo-order как ожидаемое introduced-sink-exception при sequence4
вместо3 на четвёртом вызове. Это недостаток проверочного условия, не найденное
нарушение в controller и не доказательство ложного результата первого run.
Первые source/EXE/receipt/timings выше — историческая версия до исправления.

Минимальная правка только StopProof: atomic injectedThrowReached ставится
непосредственно перед введённым throw, после FIFO проверки; обязательный
require(marker==(mode==3)) выполняется после dispatcher/EOS вне callback.
Постороннее исключение больше не удовлетворяет этому условию. Отдельный
runtime с искусственно нарушенным порядком не запускался; контрпример
reviewer разобран по source. Canonical controller и его зависимости не менялись.

Свежая сборка снова terminal0 /W4/WX. Финальный build receipt
`stop-build-result-c03f952c-5b0e-4de1-a351-b5e6e82268cf.json`, SHA
`92ca81f56cb4e298cf54b00b3a3b058f1f36dd51f82dae382cf6e0fa66d0a1ba`.
Тот же fixed medium Job/runner после смены expected Stop hash повторно
завершился terminal/Context/child0, stderr0, five markers, accepted=true.
Main полностью прочитал финальный runtime receipt
`stop-result-44343e83-e74f-4915-9dd0-b9e3e3162ef3.json`, SHA
`fe61c7c664401962e98fc38fcffc7efe76c22af0dd8d16a153fb529bb43dc345`.

Финальные SHA-256:

- StopProof.cpp: `d6e9a131335954832896c8978ccfde9b90b4101a35c5f40383f4e6b38e0e6522`.
- StopProof.exe: `3f393a310b4a5a0f7fd5e1ee986d6d8efc27af392fc3bc4ae3e2043156a1d34a`.
- stop-run.ps1: `97c17b9cf1f27323ca7bca5d5a0f10743772f08ee42114c2addadeefd27a2292`.
- Остальные26 source/build inputs и Context EXE неизменны.

| Mode | Stored batches / sink calls | UI Stop us | Protected job us | PCM bytes | Cipher objects |
| --- | ---: | ---: | ---: | ---: | ---: |
| normal0 | 255 / 255 | 357 | 122478 | 245760 | 6 |
| overflow1 | 255 / 255 | 7 | 89167 | 245760 | 6 |
| rejected2 | 3 / 4 | 5 | 27791 | 4096 | 4 |
| throwing3 | 3 / 4 | 4 | 33447 | 4096 | 4 |
| held5100ms4 | 255 / 255 | 5 | 83113 | 245760 | 6 |

Все внешние prefix/terminal/EOS/lease guards и новое exact-throw условие
прошли. `accepted_batches` — сохранённые sink batches, не весь принятый
enqueue объём: до mode2/3 отказа очередь приняла255, сохранено3. Bound stdout/
stderr применяется после чтения и считается .NET characters; нулевая stderr
не меняет этого ограничения. Independent rereview исправления/новых receipts
запрошен в том же отчёте. T114 и остальные границы не переотмечались.

Main полностью прочитал финальное дополнение reviewer (строки138–180):
APPROVED NARROW, P2 CLOSED. Независимо сверены27 inputs, оба EXE и20
используемых canonical/mirror files; receipts согласованы. Reviewer не
воспроизводил build/VM/negative reorder run. Это снимает только замечание
к проверочному условию; полный T114/Phase0 NOT READY. Свежие governance,
frozen bootstrap doctor, YAML parse и diff check прошли; source до/после
совпал, своих Windows proof/build процессов не осталось. Product code,
plan/tasks/spec/constitution hashes и HEAD в этом раунде не менялись.

## Раунд140 — mixed maximum-dimension index и native decrypt refusal, 2026-10-01

T114/Phase0, high-risk generated-data research. HEAD остаётся
`99b00a579c24b50e320465b69d9a296038bc544d`; product code не менялся.
Стенд находится в прежней внешней папке `f200-protected-mf-proof.jADm92`.
MixedIndexProof переиспользует IndexProof/ProtectedMf/Commit/Block helpers,
но проверяет отдельный metadata snapshot, не полноценный 64GiB IStream.
Четыре настоящие версии блоков: first/middle по256KiB, last262021B v1/v2;
три nonzero references, остальные262141 записи explicit ZERO. Logical length
68719476613B =64GiB−123, payload индекса4194336B.

В shared research readCipher добавлен optional typed byteLimit: size guard
выполняется до allocation. Default прежний; mixed block cap266240B, index
cap4198400+4096B. IndexProof получил только macro entry point для reuse.
ContextProof запускает fixed sibling MixedIndexProof в прежнем35s own Job;
outer runner45s. Это не расширяет product5s drain. Старые receipts/binaries
round138/139 остаются историческими: rebuilt Context/modified helpers нельзя
считать той же версией по старому hash. Legacy runner hashes не обновлялись.

Mixed и Context x64 MSVC `/std:c++17 /EHsc /MT /O2 /W4 /WX /utf-8` exit0.
Build receipt `mixed-build-result-a2bdb287-da43-45a9-904c-fd8a64584897.json`,
SHA-256 `c63d43548d2d3b1e96f57564c2142381ef213d2f459dadcb1c8790457e130eca`.
Первый prlctl observation error не принят за run; отсутствие собственного
процесса/receipt проверено до повторного запуска. Второй запуск завершён
terminal/Context/child0, stderr0, four markers, accepted=true, actual
medium8192/nonadmin. Main прочитал весь runtime receipt
`mixed-result-b4b5c738-e02f-4bb6-a640-387be887eed2.json`, SHA-256
`ece17c1f912e5cd93b66b24a94a11e082397319ad0fe73db7442fe67aa70421c`.
Runner сверил10 source/build/runner inputs и оба EXE до/после; stdout/stderr
bound4096/1024 применяется после чтения в .NET characters, не memory hard cap.

| Артефакт | SHA-256 |
| --- | --- |
| MixedIndexProof.cpp | `d8bd348386c4094ddd19dbf2a5e90a97d8c682cebf476e143aa3b423d14315b8` |
| MixedIndexProof.exe | `4a2e02ebb960bedcba52c35e306ba84399d248dcdba8f8341e915a72794b7a82` |
| IndexProof.cpp | `3a9bda2eb030e7e7da6b30df7a49887e55d0acaab0ab80ce037b6e1fcf731391` |
| CommitProof.cpp | `f42b7820bfb04187c32d773fbb49d269e7cce831d6a8a3ab1c6aacf9e9f79ef1` |
| ContextProof.cpp | `1cc6fbb9ffd1aba02cd8e0d16bd328b6a0f3c177ce9be12466f441fcdbaf7d70` |
| ContextProof.exe | `52455eb60f76ad3e0f65f176c9fd761012b51380b60bdcd5f0d502c209101b91` |
| mixed-run.ps1 | `c0976929ea13601b7d316b334bf319fce0df6153212a519f8cb2890dd170da31` |

Выбор generation2 проверяет все3 referenced blocks;8 boundary/EOF range queries
и exact whole-block oracle выполняются для каждого принятого snapshot.
Повреждённый last-v2 возвращает generation1. После восстановления собственного
fixture корректно выбирается2. Защищённый DPAPI generation3 с semantically
invalid middle flags отвергается, остаётся2. При invalidg3 и corruptedv2 обе
версии непригодны: generation0/empty selection, не empty successful recording.
Шесть direct parser negatives прошли; это не исчерпывающая матрица parser.

Два реальных CryptUnprotectData с несовпадающим optional entropy вернули false
и native error13; reached-count2, no authority, все6 ciphertext digests
сохранились. Это не pre-native injection, но и не actual profile/key loss:
identity не менялась, master keys не удалялись. Error13 — observed result,
не единственный допустимый error code будущего protocol. Чтение fallback и
отказа обеих версий также не меняло digests. Нет plaintext fallback/GC.

Сумма размеров6 ciphertext files9438756B; elapsed5438869us для совокупности
публикаций/повторных reads/hash/negative checks, не single reopen/Stop time.
Process lifetime peak commit32694272B/resident45043712B; не полная app/SC-003
приёмка. Только3 nonzero refs: нет fully populated64GiB media, generic stream,
power-loss/crash cuts большой публикации, migration или установленного клиента.
Нет устройств/сети/profile/global ACL/UAC изменений. Fixtures retained.
Независимый review запрошен в `checklists/review-2026-10-01-mixed-index.md`;
результат дописывается после чтения. T114/Phase0 и T115–T118 пока открыты.
Commit/push/PR/merge/release/issue не выполнялись; plan/tasks/spec/constitution
не переотмечались и не менялись в round140.

### Повтор round140 после исправления P2 проверки semantic rejection

Main полностью прочитал независимый source-only review. P2: fallback2 сам по
себе мог пройти при отказе decrypt/envelope g3 до семантического parser.
Это недостаток oracle, не подтверждённый defect product/storage или ложный
результат первого run. Первые hashes/receipt/metrics выше относятся к ревизии
до исправления и остаются историческими.

Добавлена только явная проверка опубликованного index1/g3: обязательный native
unprotect с correct context и exact payload/envelope; проверка generation3 и
точного invalid middle field; обязательный parseMixed=false/generation0.
Ранний decrypt/envelope failure теперь бросает наружу и прерывает proof до
fallback PASS. Runner дополнительно требует authenticated_semantic_rejections=1.
Отдельный runtime с искусственным ранним crypto отказом на g3 не запускался;
контрпример разобран по source. Изменения только в внешнем proof/runner.

Fresh build `/W4 /WX` terminal0; receipt
`mixed-build-result-d9bda888-217d-4570-bdc2-8d0bfe2f207f.json`, SHA-256
`a7402b1451fcce6538a0da9f0418c167ebd08adc8a5644f88f83b7172e2b9b0d`.
Main полностью прочитал fresh run receipt
`mixed-result-852974e5-90ed-4ee8-ac4f-c3f7ab68efb8.json`, SHA-256
`0263e8972073b1918e10602a20d4f8c882cc81f5900083334d450d1758128530`.
Terminal/Context/child0, stderr0, four markers plus authenticated semantic
rejection1, accepted=true. Ten inputs and both EXEs unchanged during run.
Native refusal снова2/error13, прежние snapshots/ranges/full-block oracles и
preservation guards прошли. File sizes9438756B/6objects; elapsed8086200us,
lifetime peak commit32649216B/resident44769280B. Разница во времени не
объявляется оптимизацией или новым performance threshold.

Финальные SHA-256: MixedIndexProof.cpp
`ab7b52d2930649f089dd436a4e94394435f294c59443880f610685949a112226`,
MixedIndexProof.exe
`c232fa7550119298490ee3e0b39ffe4cb66c5d8a98512427e6221b6e2c208c68`,
mixed-run.ps1
`acc0776e2857ca61f13033a3e6ba5f133385aa23ce9c09d691b48066d3a0ab31`.
Context и остальные inputs unchanged. Fresh independent rereview и точный
T114 exit audit запрошены; до результата Phase0 остаётся открытой.

Main полностью прочитал independent append-only rereview (строки143–194):
APPROVED NARROW, P2 CLOSED; новых blocking findings в этом proof нет.
Reviewer независимо пересчитал6 build/10run inputs и2EXE, сверил свежие
receipts/fixed runner. VM/build/run и отдельная g3 crypto-negative injection
им не воспроизводились. Старый текст report сохранён, early crypto/envelope
контрпример отвергнут по source. Полный T114 пока NOT READY; общий exit audit
выделен в отдельную bounded проверку, не замещён этим одобрением.
Fresh governance/frozen bootstrap doctor/YAML/diff прошли. Scoped Windows
inventory после run не нашёл собственных proof/build процессов; historical
cl.exe5528 от17сентября сохранён. Plan/tasks/spec/constitution и product code
unchanged в round140; ничего не закоммичено и не опубликовано.
