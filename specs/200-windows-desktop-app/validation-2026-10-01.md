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
