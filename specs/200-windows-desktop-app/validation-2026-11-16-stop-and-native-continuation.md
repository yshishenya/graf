# F200: Stop, выход и продолжение native-проверок — 2026-11-16

Полоса: high-risk-product; продолжение существующих B31/T108/T110, T088 и T126. Рабочая ветка `codex/200-windows-followup`, исходный HEAD `3dfeaff5a6774ab12be781547e4a300f9ce2a46c`; рабочие изменения ещё не закоммичены. Этот документ не принимает весь dirty diff или установленное приложение.

## Исправление Stop и выхода

Stop доступен в starting/recording/paused/degraded. В stopping/finalizing индикатор остаётся видимым с состоянием завершения, повторный Stop недоступен. Проверка существования окна больше не зависит от enabled кнопки; следующий Start восстанавливает её штатным путём. F6 не переводит фокус на disabled Stop.

Независимое ревью обнаружило обход обновления UI в ранней exitRequested-ветке. Общая `publishCaptureState()` теперь публикует состояния трёх Stop-кнопок, текст/доступность и трей как в обычном обновлении, так и после запроса выхода и при ожидании drain. Она не создаёт окно и не начинает новую работу. Обычная публикация остаётся после восстановления индикатора, чтобы новый контрол получил актуальный статус в том же tick. Сохранены shutdown/drain/lease/единственная финализация.

Независимое source review: `.dev/f200-stop-independent-code-review-20261115.md`, повторное рассмотрение 2026-11-16 — PASS, открытых замечаний 0. Startup path также просмотрен. Проверки по исходному тексту не заменяют WinUI runtime.

Окончательные portable Debug/Ninja проверки: **4/4 PASS** — RecordingIndicatorTests, WindowsDesktopSessionTests, AutomaticRecordingSmokeTests, NativeCaptureWebFailureTests. Журналы/точные команды/контрольные суммы: `.dev/f200-stop-focused-final-20261116/`; scratch автоматически удалён.

- `apps/windows/RecApp/AppMain.cpp`: `e0708472b380996dfb8bed640c3725254e4925fcc92af2df339a2291eb4055f0`
- `apps/windows/RecApp/Shell/RecordingIndicator.cpp`: `ce4f6a3555751ec9127b131e20da228e9d2694271a53b83a9b948feb2af49112`
- `apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp`: `7096911a9e338106dac44b49d521a71df91424444e0d10c89acdf2c8cb12f310`

## Native Windows

До переноса текущих изменений проверены все 262 сохранённых входа `C:\GrafQA\T124Wiring-20261112\pr`: полное совпадение с прежней базой. Перенесено ровно пять файлов; после переноса все 262 совпали с текущими host-байтами. Запущены build ALL, полный набор CTest и отдельный NativeProtectedAecFailureDuringStop. Фактический план содержит 127 уникальных тестов с 127 командами; T071 — прежний аргумент --protected-aec-failure-during-stop, RUN_SERIAL, timeout120; T124 — прежние восемь аргументов и timeout180. Результат выполнения ещё нужно приложить. Доказательства: `.dev/native127-current-20261116/`.

## AAC: результат эксперимента не является исправлением продукта

FFmpeg AAC-LC/M4A контроль B719/B960 с исходными N1440/switch720 и порогом >0.015 прочитан Windows MFSourceReader из точных bytes в памяти до EOF. Оба файла проходят исходный порог по обеим частотам, но actual decode N3072 и начальные окна показывают priming. В отдельной следующей пробе `.dev/f200-package-041/ffmpeg-mf-consumer-20261115-01428e6ee1234c85bec0e5793c1ead1d/` оба B получили MF_PD_DURATION=300000 в единицах100ns (HRESULT0, VT_UI8), а MediaEngine через clone того же memory stream — GetDuration=0.03с, ready4/HasAudio, LOADEDMETADATA+CANPLAY без ошибки. Mute/noAutoPlay, Play не вызывался. Источник `a86f693f9953e74a70cb79b4c49b6622255a0dc2f4633a30a21f547ab3efb8ce`; driver `79bf745a69224ffec136f2faaadf23ec735598452c3d47cef10a6c0c5b333dcd`. Это подтверждает presentation metadata, но не прослушивание/seek/полное воспроизведение/защищённый AVIO или encoder Windows. Encoder продукта не заменён. Никаких crop/padding/изменения порога. Host media scratch и успешный guest build удалены. Результат: `.dev/f200-package-041/ffmpeg-mf-consumer-20261115-155f01d08c444a4abe0aadf3e17de8e3/`.

## T088: фактические несовпадения предположений пробы

Первые проверки не дошли до storage assertions: standard profile name у Runtime157 оказался пустым; затем после успешного Close свойство Source оставалось доступным из памяти. Для default-profile исправлен только необоснованный запрет empty name и sentinel инициализации identity (вместо name используется проверенный ненулевой browserPid). Прежние проверки собственного actual UDF/path/PID/InPrivate и exact identity сохранены; независимое review PASS. RunC дошёл до Close, но завершился FAIL на предположении Source; cleanup PASS с normal BrowserProcessExited того же PID. В runD проверка использует отказ фактического ExecuteScript после Close вместо cached Source. Независимое ревью ограниченной дельты — PASS. **RunD: PASS, assertions=1, cleanup=1**, Runtime157.0.4341.46, источник `856a25a6e962493e14d7831f67c0efbaa8977fb4c52bb9a7920f77165670ce2f`, EXE `82ea467a147afb55a952f21708f07672fdbeef524a69608c1b73e2338896acf3`. Проверены настоящий single-inflight CDP callback до U Navigate, A→B→C stale drain, отсутствие U.local/U.session и возврата старого writer, живые F.local/F.session/cookies, U cookie, native sentinel и invalid-mask HRESULT. Cleanup дождался normal exit того же PID12156 и удалил собственный temp profile. `.dev/t088-origin-clear-runtime-20261116D/` содержит результаты. Ошибки dispatcher/Close/unknown проверены только скалярной моделью, не реальными fault-инъекциями. XAML/продукт не проверены; реализация T088 в приложении остаётся открытой.

## Текущий master

2026-11-16 выполнен fetch origin/master: `e44aae0a3` (последний F295). Дельта от прежнего эталона `494ddc70f88a865b5df3ff8b5b2f663a5af96d7a` переносится трёхсторонним сравнением каждого пути без reset/stash/checkout поверх рабочей копии. Четыре конфликта только в документах (CHANGELOG и F292 tasks/quickstart/validation): current-часть конфликтного блока была пустой; восстановлены upstream-секции при совпадении полных before/current и сохранении остальных clean-merge частей. `.dev/f200-master-sync/e44aae0a3-20261115T213009Z/main-resolution.json` фиксирует байты. Настоящий Git merge и независимое source review интеграции ещё не выполнены. Обновлённая часть прошла 183 Mac-теста и 7 серверных F292 missing-time тестов (0 ошибок); временные сборки и одноразовый PostgreSQL удалены штатно. 42 применённых пути повторно сверены с хешами; четыре main-resolved документа проверены на отсутствие ошибок пробелов. Отчёт `report.md` и `manifest-final.json` в том же каталоге. Это не Windows acceptance. Найдена отдельная разница политики локального места Mac/Windows; проверка её назначения продолжается.

## Незавершённые критерии

127 native результаты и отдельный T071; сборка настоящего WinUI приложения; установленный пакет и UI/клавиатура/доступность; T088 product storage cleanup и continuations; правильная AAC длительность/воспроизведение и product исправление; физическая Windows x64/60min/AEC матрица; публичная Code Signing. Подпись пользователь отложил, разработку продолжать. Задачи не закрыты, выпуск не подтверждён.

## Продолжение: независимое ревью и исправление F295

Независимое ревью всех 46 перенесённых путей проверило исходные и итоговые байты, четырёхсторонние документы и оба Python merge. Обнаружено одно P2: после таймаута `LocalRecordingFootprintProvider` освобождал `inFlight`, хотя синхронная файловая операция ещё работала. Повторный refresh и invalidate позволяли параллельные обходы. Исходный отчёт `.dev/f200-master-sync/e44aae0a3-20261115T213009Z/independent-source-review-20261116.md` сохранён как REQUEST_CHANGES; исторический manifest не переписан.

В существующем F295/FR-013/T002 исправлен только жизненный цикл измерения: timeout завершает ожидание, invalidate отзывает поколение/кэш, а actual measurement освобождает slot и публикует кэш лишь своего поколения после файловых операций. До завершения старого поколения новый обход не начинается. Политика места, данные, удаление, UI, плеер и сервер не менялись этим исправлением.

`testTimeoutRetryAndInvalidationRetainTheRunningScan` показал RED на точном upstream исходнике: семь нарушенных утверждений, `calls=3` до освобождения первой операции и `maximum=2`. После исправления тот же тест и полный прежний focused-набор прошли: **184 теста, 0 ошибок**, включая TTL, generation fence, off-main, manual/automatic warning, tray и performance contracts. Доказательства `.dev/f200-f295-single-flight-20261116/{red-result.json,red.log,green-result.json,green.log}`. Временная SwiftPM сборка удалена после завершения.

- `LocalRecordingStorageUsage.swift`: `b79374e84e8489aa1b4669dc90542ef4eb58a3db622acceabef572c755c11e2a`
- `LocalRecordingStorageUsageProviderTests.swift`: `fca4045a6bc0e915ae116a871e9449253b676d11b71f3c9b1a2b83cccb4d84ff`

Повторное независимое ревью исправления запрошено. Это не установленная macOS-приёмка и не обновление GRAF Dev.

## T088: продуктовая версия после native127 snapshot

Подготовлена ограниченная интеграция Host/header/AppMain и двух тестов. Она закрывает прежний документ и payment children, удерживает ту же actual Environment/profile, создаёт самостоятельный blank Core, ждёт настоящие Ensure и CDP completion до первой Navigate, последовательно обрабатывает A→B→C и оставляет ошибку/unknown/lost dispatch закрытыми. API `Profile2/AllDomStorage` не используется. Пустое default ProfileName допустимо; cookies/foreign origin/native custody не очищаются. Блок Stop publication сохранён побайтно.

`.dev/t088-product-integration-20261116/` содержит ограниченный patch, before-снимки, исходные хеши и переносимый результат **5/5 PASS**. Текущий Host SHA-256 `9c54db66f2bc19fad6a91d91145af158e402b6bd8405228a4914c0baee1329ab`; AppMain `a2ddab6d57c3ad69d751d7629555f880a43b0c21a0dac7bc05e94232dcd1d524`. Независимое source review и Windows/XAML compile/runtime ещё впереди. Результаты текущего native127 к этим новым байтам не относятся.

## Сравнение Code Signing

Подготовлено отдельно: `.dev/f200-package-041/t124-public-code-signing-options-independent-20261112.md`, по первичным источникам на 2026-11-12. Документальная USB-ЭП не признана Code Signing; покупка, регистрация, смена Publisher, доверие к сертификатам и публичная подпись не выполнялись. Доступность выдачи российскому ИП и окончательная цена не подтверждены. Публичная подпись остаётся открытой T124 и не блокирует независимую разработку.

## Продолжение: завершённые native127 и T071

Полная нативная сборка Windows завершена, 186 шагов. Сверены 127 фактических
команд с 127 JUnit cases: **126 PASS / 1 FAIL**, errors/skipped/disabled — 0.
Время CTest 3507,27 с. Все 262 исходных входа после выполнения совпали с
замороженным snapshot. Единственный отказ — `SelectedMicrophoneLossTests`,
exit `0xc0000409`, исходное утверждение AAC на строке 769:
`2 * hypot(sine, cosine) / decoded.size() > 0.015`. Порог, сигнал и
знаменатель не изменялись; `max_abs_pcm_delta=0` не отменяет отказ AAC.

Исходный PowerShell runner остановился при обработке stderr CTest до записи
`full_exit` и отдельного T071. Его `result.json` сохранён без исправления:
stage `full127`, `RemoteException`; полный exit code не зафиксирован.
Фактические full JUnit/LastTest/LastTestsFailed собраны отдельно. Затем выполнен
только недостающий T071: `NativeCaptureStorageIntegrationTests.exe
--protected-aec-failure-during-stop`, **1 PASS / exit 0**. Полный набор повторно
не запускался. Артефакты `.dev/native127-current-20261116/collection.json` и
`collected/`, обе завершённые scheduled tasks удалены после сбора доказательств.
Это результаты версии до новой T088, а не приёмка последующих Host/AppMain.

## Продолжение: T088 WinUI build и проверка общего кода

Независимое ревью ограниченного T088 patch завершено: **PASS**, конкретных
P0/P1/P2 нет (`.dev/t088-product-integration-20261116/independent-source-review-20261116.md`).
В QA ARM отдельно собран настоящий `GrafWindowsApp.vcxproj`, Release/x64,
unpackaged, с production AppMain, WebView2Host и проверяемым AEC3 backend.
Restore и WinUI build — exit 0. EXE 3 991 040 байт, SHA-256
`929745fe1a29fba3e43eafd496da6f3e22e0ec96a2369f015ea1b10a496c661a`.

Отдельные native CMake configure/build и CTest пяти целей — exit 0,
**5 PASS / 0 FAIL**, без skipped/error. Проверены
WebView2HostLifecycleTests, CalendarJoinHostTests, WebViewRoutePolicyTests,
WebViewBridgeEnvelopeTests и WebViewCabinetParityTests. Сверены JUnit имена,
`status=run`, журналы и SHA передачи; source postcheck **262/262 MATCH**.
`.dev/t088-product-native-20261116/{collection.json,collected/,task-cleanup.json}`.
Завершённая scheduled task удалена; сборочное дерево пока сохранено для активной
проверки окна. Приложение этим запуском не установлено. Native XAML runtime,
last-Core/default-profile, actual account transitions и UI ещё не приняты.

## Продолжение: повторное ревью F295 и gates T127

Отдельное повторное независимое ревью исправления single-flight F295 — **PASS**
(`.dev/f200-f295-single-flight-20261116/independent-review.md`); исходный
REQUEST_CHANGES интеграции выше сохранён. Mac Dev не обновлялся.

Требования T127 прошли отдельное reviewer-owned ревью **8/8**, открытых 0;
scoped analyze **C/H/M/L 0/0/0/0**. Отчёты
`.dev/f200-master-sync/e44aae0a3-20261115T213009Z/t127-requirements-review.md`
и `t127-analyze-20261116.md`. Создана открытая задача
[T127 #8060](https://github.com/yshishenya/graf/issues/8060) после проверки
всех 116 F200 issues в состояниях open/closed и отсутствия владельца T127.
Ссылка в tasks — только метаданные, требования и task checkbox не изменены.
Issue-canon validation и решение Main о начале реализации фиксируются отдельно.
Один запрос состояния хранилища не заменяет видимую функцию или installed T097.

## Продолжение: опыт native FFmpeg

Исходники ограниченного синтетического x64 HGLOBAL/AVIO опыта и скрипты сборки
прошли независимые проверки. Начальный запуск DLL build остановился на
скачивании: HTTP 500, stage `download`, process/task exit 1. В scratch пока
только архив MSYS base; компиляция и AAC опыт этим запуском не выполнялись.
Исходные result/progress сохранены в `.dev/f200-ffmpeg-native-20261116/`.
Продолжение доставки/сборки проверяется отдельно. Encoder продукта не заменён,
отказ AAC и остальные аппаратные/пакетные/выпускные условия остаются открыты.


## Продолжение: реализация T127 и границы переносимой проверки

Issue-canon validation завершилась успешно для 271 issue. Source GO Main
зафиксирован в `.dev/f200-master-sync/e44aae0a3-20261115T213009Z/t127-source-go-20261116.json`.
После допуска добавлено наблюдение места через удерживаемую queue/rootLease
на существующем worker. Getter UI читает скалярное состояние; действующие
factory/ACK/Start/Stop и политика 5 ГБ / 80% / 95% не меняются. AppMain
показывает текст с именем доступности и раскрывает инспектор при предупреждении.
Backend patch и manifest: `.dev/t127-backend-20261116/`; ограниченный UI patch
и итоговые хеши: `.dev/t127-ui-20261116/`.

Переносимая сборка backend успешна; результаты набора — **8 PASS / 1 FAIL**.
Отказ `ProtectedCustodyCodecTests`, `WIPE_ORACLE case=sso-clear zero=0 bytes=3`,
воспроизведён автором на отдельных неизменённых codec/primitives/Sha256/test
без T127; assert не ослаблен. На Mac native selector возвращает
unsupportedPlatform, выполненных новых native cases — 0. Это не Windows PASS.

Новые механические проверки строк AppMain удалены после review Main;
`RecordingIndicatorTests.cpp` побайтно совпадает с исходным снимком автора.
Существующая переносимая регрессия — **1 PASS**, но не проверяет новое условное
поведение XAML. Actual UI/AX и installed T097 остаются NOT_RUN. Task T127 и
issue #8060 открыты; независимое backend review и настоящие Windows selectors
должны подтверждаться отдельными результатами.

## Продолжение: FFmpeg, сохранённые ошибки подготовки

Исходные отчёты не заменялись успешными: retry1 остановилась на GPG-проверке
make из-за Windows-путей/неимпортированного публичного keyring; retry2 — на
извлечении make, потому что `zstd` отсутствовал в PATH процесса. Подпись make
после исправления POSIX-путей и scratch-only keyring — VALIDSIG
`5F944B027F7FE2091985AA2EFA11531AA0AA7F57`.

В retry3 обе подписи и извлечение успешны, но configure завершился
`Host compiler lacks C11 support`: target MSVC найден и C17 checks успешны,
а host compiler остался `gcc` и отсутствовал. Launcher `Start-Process -Wait`
оставался в ожидании без native compiler/MSYS children. Main проверил журнал
и отсутствие активных native jobs, штатно остановил только собственную task;
результат планировщика 267014, а не придуманный build exit. Собраны все 16
файлов retry3 плюс config.log; `.dev/f200-ffmpeg-native-20261116/`
`retry3-collection.json` и `retry3-stop-receipt.json`. DLL build и опыт AAC
этой попыткой не выполнены. Подготовлен отдельный hostcl build с явным
`--host-cc=cl.exe`, новым build/prefix и прямым ожиданием точного процесса;
его source review/запуск/результат отмечаются отдельно.


## Продолжение: независимый source review T127

В `.dev/t127-backend-20261116/independent-review.md` сохранён исходный P2:
новые integration cases были доступны только ручному selector. Main добавил
в Windows CMake `NativeStorageWarning`, команду `--storage-warning`,
RUN_SERIAL и TIMEOUT 240. Reviewer повторно проверил это исправление и
финальный UI patch: текущие C/H/M/L — **0/0/0/0**, исходный finding сохранён.
CMake SHA-256 `e14173188dced5ed59889309586ef49d3af966ef1cf8d034fc3ae38f31db8e9a`.
Новый current snapshot содержит 262 входа, семь отличий от T088; передача
262/262 сверена. Main запустил `.dev/t127-native-20261116/launch.py --launch`:
WinUI restore завершён exit 0, дальнейшая сборка/9 регрессий/2 native selectors
на момент этой записи ещё выполняются. Это не результат приёмки.

Отдельный source-only разбор переносимого SSO failure сохранён в
`.dev/t127-backend-20261116/portable-sso-review.md`. Полный прежний журнал
подтверждает zero live tail после clear, но не полностью нулевую область
после базового libc++ destructor перед free. Точную причину конкретного binary
и наличие исходного plaintext он не доказывает. Тест и гарантии не ослаблены;
отдельный portable memory gate остаётся открытым.

## Продолжение: FFmpeg hostcl и проверка преобразования путей

Hostcl configure прошёл: три библиотеки, AAC/ipod/MOV, без decoders/protocols,
лицензия LGPL 2.1 или новее. Затем make отказал exit 2 / task 1: CL D8043
получил POSIX absolute source path без преобразования. Отчёты и config
собраны в `.dev/f200-ffmpeg-native-20261116/hostcl-collected/`; это не DLL PASS.
Причина — прежние process-only MSYS2_ARG_CONV_EXCL=* и MSYS_NO_PATHCONV=1.
Один маленький native smoke с unset обеих переменных успешно скомпилирован,
связан и выполнен; `smoke-paths-result.json`, exit 0. D9024 о расширении .o
не скрыто. Из официального зеркального механизма MSYS2 получен diffutils
3.12-1, подпись проверена pinned keyring/fingerprint
`5F944B027F7FE2091985AA2EFA11531AA0AA7F57`; в own MSYS извлечён только cmp.exe.
Проверки cmp: version 0, same 0, different 1. Пакет и tool hashes сохранены.
Отдельная conv-подготовка прошла независимый source review C/H/M 0/0/0;
на момент этой записи не запущена, поскольку выполняется T127 compiler job.

## Продолжение: первый last-Core запуск остановлен до компиляции

Для no-navigation опыта Main временно отключил только net0 QA ARM и проверил
Disconnected внутри Windows. Guard остановил запуск stage vcvars / task 2:
`Get-Command -CommandType Application` вернул оба MSVC пути (x64 первым,
arm64 вторым), а launcher ошибочно сравнивал массив как один путь. EXE и Core
не создавались; это не проверка гипотезы last-Core. Terminal reports и source/
SDK/tool postchecks собраны `.dev/t088-last-core-20261116/collection.json`.
Сеть затем штатно подключена и проверена Up; `network-restore.json`.
Отдельный read-only toolchain diagnostic подтвердил первый x64 cl/link и SDK;
новая попытка B требует выбирать ровно фактический первый PATH executable,
сохраняя точные SHA и не меняя прежние результаты. Продукт T088 не принят.


## Продолжение: настоящий T127 native результат и сохранённый RED

Коллекция `.dev/t127-native-20261116/collections/20261115T234145Z-b3cf2149/`
подтверждает WinUI restore/build exit0 и девять прежних регрессий PASS.
EXE SHA-256 `81d725c101a662f1c9cb194e517156771399208e082cf8d668a39ece594b1a1f`;
262 входа сверены до/после. Новый `NativeStorageWarning` завершился FAIL10.82s,
assert7755: ожидание предупреждения во время записи. CTest exit8.
Следующий `--storage-pressure-query` **не выполнялся**, поскольку runner
остановился на отказе. Исходный RED и замороженные входы сохранены.
Разбор выявил недостаточный вход самого теста:80×1920B не достигают
физического checkpoint256KiB; наблюдение давления обновляется при фактической
проверке резерва. Подготовленная test-only правка использует границу137 кадров
и проверяет новый disk check, не добавляя сканирования из UI/на каждый кадр.
Независимая проверка и отдельный native повтор ещё требуются. T127/#8060 открыты.

## Продолжение: last-Core B — ограниченный Win32 PASS

`.dev/t088-last-core-20261116B/collection.json` и независимый
`independent-result-review.md` подтверждают compile/run/task exit0 на Runtime
157.0.4341.46. Без дополнительного живого Core и навигации немедленный B после
Close единственного A использовал тот же actual Environment/UDF/profile/PID8880;
фактическое пустое имя профиля принято. После Close(B) normal process exit и
signaled handle подтверждены; удалён только собственный временный профиль.
EXE SHA-256 `114412e2ab74eb8649f205c0adc9be4cc5418619db8069a700bc73821f52399b`.
Это не доказывает постоянное удержание процесса одним Environment, поведение
после задержки или actual XAML/AppMain account A→B→C. Эти критерии открыты.
Сеть только QA ARM восстановлена, Ethernet Up; network-restore.json сохранён.

## Продолжение: FFmpeg Conv terminal FAIL

Conv configure успешно прошёл с преобразованием путей, make дошёл до настоящей
компиляции. MSVC14.44.35207 HostARM64/x64 завершился внутренней ошибкой C1001
при libavformat/cbs.c (включает libavcodec/cbs.c108); build_exit2/task1.
Все восемь небольших terminal файлов и SHA собраны в
`.dev/f200-ffmpeg-native-20261116/conv-collected/` и conv-collection.json.
Активных native jobs после окончания нет. Это не успешная DLL, syntheticAAC
не запускался, продуктовый encoder не заменён. Причина и минимальный следующий
вариант сборки исследуются отдельно с сохранением этого отказа.


## Решение владельца о подписи и следующий native запуск

Владелец отложил получение/использование публичной Code Signing, поручил
закончить приложение и подготовить сравнение параллельно. Сравнение уже есть:
`.dev/f200-package-041/t124-public-code-signing-options-independent-20261112.md`,
источники проверены12ноября, не выдаются за повторную проверку16ноября.
Регистраций, покупок, обращений к поставщикам и использования документальной
USB-ЭП не было. T124 остаётся открытой; это не разрешение на публичный выпуск
без требуемой доверенной подписи. Разработка и внутренние испытания продолжаются.

Test-only T127 fix прошёл независимое ревью C/H/M0. Main подтвердил262/262
live/frozen inputs и suffix-only reuse четырёх скриптов; отдельная попыткаB
запущена `.dev/t127-native-20261116B/launch.py --launch`. Restore/WinUI build/
CMake configure/build/selected-plan завершились exit0; регрессии ещё выполняются.
Новый EXE SHA-256 `ac3c1a32ba15d62655e562c68de6d1ee22ca2ce165ceffb05625c7e0d3254e41`.
WinUI EXE не установлен и не запущен. Новый native результат фиксируется после
terminal collection; прежний RED не изменён.

Исследовательская NoOpt подготовка прошла Main и независимое source review,
замечаний0. Штатный `--disable-optimizations` — единственная дельта configure,
кроме нового prefix. Рекомендация основана на сохранённом C1001 и закреплённом
исходнике; это ещё не доказательство успешного обхода. Сборка ждёт окончания
T127. Последующий AVIO runner привязан ровно к успешному NoOpt report/prefix,
без fallback; Main проверил его двухстрочную дельту путей. Продуктовые гарантии
памяти и существующий encoder не менялись.


## Продолжение: T127 attemptB — PASS_NATIVE_SCOPE

Terminal task0 и неизменные262/262 входа подтверждены сборщиком:
`.dev/t127-native-20261116B/collections/20261116T000751Z-5cdbf094/collection.json`.
WinUI restore/build, CMake configure/build, точный selected plan и все команды
завершились exit0. Девять прежних CTest-регрессий PASS без пропусков;
`NativeStorageWarning` PASS3.9801s; отдельный `--storage-pressure-query` PASS с
маркером genuine held-queue boundaries/errors/no-effects, не unsupportedPlatform.
EXE SHA-256 `ac3c1a32ba15d62655e562c68de6d1ee22ca2ce165ceffb05625c7e0d3254e41`.
Test EXE SHA-256 `a818875ccca672599d1a48e0ec257ed8c8e79233c1cde74205c8ae301f80ed60`.
Старый RED сохранён. Ошибок collection нет; отсутствует только необязательный
LastTestsFailed.log. Actual UI/AX, установленный кандидат и видимость idle/
recording/paused не проверены этим запуском. T127 и #8060 остаются открытыми.

После terminal collection Main запустил отдельную NoOpt задачу;
`.dev/f200-ffmpeg-native-20261116/noopt-launch-result.json` фиксирует передачу
трёх SHA-совпавших входов и Running. Это ещё не DLL build result.


## Продолжение: NoOpt terminal FAIL

NoOpt завершился build_exit2/task1 с прежним MSVC C1001 на libavformat/cbs.c.
Actual CFLAGS из config.mak уже без -O2, поэтому гипотеза достаточности
`--disable-optimizations` не подтверждена. Восемь terminal файлов и SHA сохранены
в `.dev/f200-ffmpeg-native-20261116/noopt-collected/`, noopt-collection.json.
AVIO synthetic runner не запускался: успешных DLL ещё нет. Source/кодеки
автоматически не менялись. Read-only compiler-alternatives-20261116.json
подтверждает имеющиеся HostARM64/x64 и Hostx64/x64 MSVC, отсутствие clang-cl
по проверенному пути, активных GRAF tasks0. Следующий ограниченный опыт сравнит
компиляцию самого проблемного translation unit; подготовки недостаточно для PASS.


## Продолжение: источник C1001 найден в upstream

Main напрямую прочитал официальный FFmpeg commit
`6a59c847b50c6bc30630df7fca56ccd6cd8a5a8c` через GitHub API;
`upstream-cbs-fix-confirmation.json` сохраняет message и три patch. Автор
описывает пустую CBS-таблицу как некорректный C и возможный MSVC internal error
в минимальной MOV-конфигурации. Это совпадает с нашим config и отказом.
Независимый source-разбор `conv-next-after-noopt.md` установил отсутствие
исправления в проверенных8.1.3/8.0.3 и отсутствие проблемного lavf CBS-пути в
поддерживаемой7.1.5. Main выбрал отдельный исследовательский опыт stock7.1.5
с прежним минимальным AAC/IPOD scope. Сравнение compiler hosts больше не нужно;
его заготовки не запускались. Это не downgrade установленного приложения и
не принятое продуктовое решение о библиотеке. Новые source/signature/ABI pins,
GPG verification и независимое review обязательны до запуска.

Свежий `git fetch origin master` подтвердил
`5223422357487ab28cfc83084c9e45717d0a6568` и FETCH_HEAD. Git merge не выполнен.
Read-only integration inventory установил provenance114/114 общих путей и
155 уже чистых Windows-файлов, которые нельзя потерять при переносе.
Рекомендуется чистая временная ветка от master с явным manifest целевого
остаточного diff; исходная dirty ветка и результаты проверок сохраняются.


## Продолжение: stock FFmpeg7.1.5 — native build PASS

После Main и независимого source review запущена одна отдельная715 попытка.
Проверены точные bytes/SHA архива и подписи, существующий fingerprint GPG до
распаковки; trust и keyring не менялись. Scheduled task завершилась Ready/0,
runner complete, signature/extract/build/process exit0. Весь terminal report
собран read-only с проверкой размеров/SHA; все artifacts повторно совпали с
manifest, ошибок0. Материалы: `.dev/f200-ffmpeg-native-20261116/715-collections/20261116T004047Z-21c7d1fe/`.
Это PASS_LIBRARY_BUILD_SCOPE, не приёмка продукта. Три DLL ABI61/61/59 созданы;
import libraries фактически установлены в bin. AVIO test-only скрипт исправлен
ровно по этим четырём путям и повторно прошёл Main/независимый source review.
PS SHA `c14a4c1ffb957970e35e77b8061a8bb6ce8cd1bc5feec2e5e7a5109f447c1bf5`;
native PS parser ошибок0. После проверки отсутствия других native jobs Main
запустил отдельную synthetic AVIO715 пробу. Её terminal результат на момент
этой записи ещё не собран. Продуктовый encoder/память/гарантии не изменены.

## Продолжение: настоящая интеграционная основа master

Повторный fetch подтвердил `5223422357487ab28cfc83084c9e45717d0a6568`.
Создана отдельная временная рабочая копия
`/Users/yshishenya/.codex/worktrees/f200-integration-20261116/crisp`, ветка
`codex/200-windows-integration-20261116`, HEAD точно равен этому master.
Main проверил все782 source/base hashes неизменного manifest и перенёс ровно
его782 операции; postcheck782/782, staged0, commit/push/PR/merge не выполнялись.
Это применение проверяемого baseline в отдельной копии, не merge старой ветки.
Исходная dirty копия сохранена. Три upstream docs и исключённые пути остаются
из master, отдельный F295 fix не смешан. Незавершённые три ABC test-only входа
пока не включены; потребуется отдельная дельта после source review. Свидетельство:
`.dev/f200-integration-applied-20261116.json`. Общая validation в baseline также
зафиксирована прежним hash; последующие записи добавляются отдельной дельтой.

## Продолжение: AVIO715 — фактический synthetic PASS

Main собрал terminal collection
`.dev/f200-ffmpeg-avio-native-20261116/collection-20261116T004501Z/`.
Task Ready/0, compile/probe/process/headers/dependencies exit0; runner verdict
`synthetic_library_gate_pass`. Независимый фактический разбор Ohm:
`.dev/f200-ffmpeg-avio-native-20261116/independent-result-review.md`, SHA-256
`e8f5ae5948ad8c03e6aeb3cc4bde0c105ed579b426b9ba1a820282ddfba5447c`,
P0/P1/P2/P3 0/0/0/0 в пределах этой проверки. Повторный запуск не выполнялся.

Оба exact synthetic случая B719/B960 получили исходные1440 samples как1024+416.
Full EOF декодировал3072 samples; обе частоты в каждом случае проходят прежний
порог0.015, без crop/ослабления. Media hashes AVIO/HGLOBAL/MediaEngine совпали.
MF и MediaEngine сообщают presentation duration30ms; фактический полный PCM
содержит64ms с priming/tail. Metadata не доказывает слышимое воспроизведение
ровно1440 samples или правильный seek. Muted/noAutoPlay проверены, Play не вызван.
Микрофон, настоящие записи и открытые медиафайлы не использовались.

Peak working set45953024B, peak commit40611840B — показатели короткого процесса,
не общий лимит продукта. Проверенный allocator7.1.5 сохраняет ограничения прежнего
разбора8.1.3: per-block av_max_alloc, CRT aligned family, отсутствие payload wipe
в штатном av_free. Полный общий учёт/затирание памяти, защищённый IStream,
длительная запись, Play/seek, упаковка/установка и приёмка продукта остаются
открытыми. Вопрос владельцу о границе памяти отправлен; ответа пока нет.
Продуктовый encoder, гарантии памяти и выбранная для продукта версия не изменены.

## Продолжение: интеграционная проверка Spec Kit — среда не совпала с lock

В отдельной интеграционной копии `git diff --check` завершился без ошибок.
`python3 scripts/check_spec_kit_governance.py` завершился отказом frozen doctor:
установлен specify v1.2.6/ref9eacc24ffe47eadf035a3af601e4dabfb15b8fde,
а lock требует v1.0.7/reffe1d00e3ccaf495880aaf90fb0e17679e82f065b.
Это незакрытая проверка, не PASS. Lock и общая установка инструментов сохранены;
готовится изолированный запуск официальной точной версии без обхода doctor.
Commit/push/PR/merge в интеграционной копии ещё не выполнялись.

## Продолжение: точная изолированная среда Spec Kit — PASS

Main проверил предложенный read-only рецепт и штатно установил из локального
кэша официальный specify1.0.7 с полным Git pin
`fe1d00e3ccaf495880aaf90fb0e17679e82f065b` в собственный временный tool root.
Настоящие Python shebang, METADATA и direct_url.json проверены до запуска.
`specify --version`, неизменённый `speckit-bootstrap --doctor --frozen` и
`python3 scripts/check_spec_kit_governance.py` завершились exit0 на интеграционной
копии. Прежний отказ из-за1.2.6 сохранён как исторический, не переписан.
Квитанция и stdout/stderr:
`.dev/f200-integration-toolchain-main-20261116/result.json` и соседние журналы.
Before/after SHA проектного lock, общих launcher/bootstrap/direct_url совпали.
Только созданный этим запуском временный tool root штатно удалён после проверок.
Это PASS инструментальной проверки, не продуктовая приёмка/merge/release GO.

## Продолжение: focused-проверка объединённой версии — 198 PASS без пропусков

В интеграционной копии от master5223422357487ab28cfc83084c9e45717d0a6568
завершён focused-r4: **198 passed, 0 skipped, exit0**. Это пять файлов из
плана ci-local, включая два варианта с настоящим disposable MinIO. Предыдущие
отказы192/196 и ошибки подготовки Docker сохранены, не переименованы в PASS.
MinIO запущен из точного имеющегося image в отдельной bridge network после
проверки пересечений subnet; credentials были только временными в окружении.
После тестов удалены только owned container/network; PostgreSQL fixture также
завершил очистку. Evidence: `.dev/f200-integration-focused-20261116/`,
`focused-r4-result.json` и журналы. Это локальная проверка рабочего дерева,
не exact-SHA GitHub CI, приёмка установленного приложения или готовность к выпуску.

Для объединения Main отдельно исправил ровно пять тестовых/механических файлов:
проверку reduced-motion с числовым положительным пределом0.01ms и удалением
повторного assert; явное вычисление urlsplit.port через `_ =` без смены
исключения ValueError; сортировку импортов в трёх файлах. Продуктовый CSS не
менялся. Итог: settings contract25PASS; Ruff всего сервераPASS. Квитанция
`post-review-test-lint-receipt.json` ссылается на фактический вывод; исходные
журналы Ruff FAIL сохранены как исторические. Эта дельта сверх manifest782
подлежит отдельной фиксации и независимому review.

## Продолжение: общие страницы, платформенные подписи и меню — browser PASS

Из integration copy на собственном случайном loopbackport поднят существующий
synthetic settings harness с продуктовыми шаблонами и CSS/JS. Другой стенд8897
не использовался. В Chromium153.0.8010.12 и WebKit26.6 прошли:

- platform-copy: по29PASS; системные подписи Windows/Mac и пользовательский
  текст проверяются раздельно;
- profile-menu: по44 сценария, включая открытие подменю вправо/влево,
  клавиатуру, тему, узкое окно, границы экрана и переход мышью через зазор;
- settings-consistency: по224 случая страниц/тем/ширины, общие элементы,
  системная тёмная тема, переносы и диалоги;
- settings-autosave: ChromiumPASS — последняя правка, пустое имя, тема,
  ошибка/повтор/чтение результата, IME, уход со страницы и режим без JavaScript.

Evidence: `.dev/f200-integration-browser-20261116/results.json`, журналы и
`cleanup.json`. Собственный harness штатно остановлен, очистка подтверждена.
Отдельно ранее прошли41 notification-contract и settings-combobox Chromium;
их evidence находится в focused/settings-extra-results.json. Это автоматические
проверки общего веб-интерфейса на искусственных данных, не доказательство окон
или доступности установленного Windows-кандидата.

## Продолжение: T088ABC R1 — native build FAIL, R2 меняет только стенд

Настоящий WinUI build R1 закончился Ready/task1, restore0, stage failed.
Source pre/post264/264 совпали. В журнале шесть ошибок: пропущены shellapi.h
и projection Windows.Foundation.Collections; UIElementCollection не имеет
VectorChanged, остальные три ошибки являются следствием неверной подписки.
Evidence: `revisions/r1-cookie-readback/build-collection-20261116T010540Z/`.
Продукт не запускался; прежнее source review PASS не считается native PASS.

Dirac и Boole независимо подтвердили дефект способа наблюдения. Main разрешил
R2 только для производной тестовой копии: одна синхронная observer statement
после InsertAt, перед существующим attach; при ошибке attach не продолжается.
Теперь11 sections должны быть exact, два перекрывающихся sections явно
instrumented; удаление ровно одной разрешённой вставки должно восстанавливать
оба исходных участка побайтно. Утверждение13/13 exact не переносится в R2.
Продуктовые AppMain/Host и их алгоритм не меняются; cookie-readback B/C,
исходные Close/Ensure/CDP и lifecycle-проверки остаются обязательны. Подготовка,
независимое review, build и runtime R2 на момент этой записи ещё не завершены.

## Продолжение: source review общей дельты — найден ожидающий addressed seek

Ohm завершил actual source review shared135 и пяти новых механических файлов.
Обнаружена одна P2: обновление расшифровки той же записи может снять ожидающий
loadedmetadata-переход к позиции из ссылки до готовности аудио. Требуется
исправление с browser regression; отсутствие autoplay и отмена при смене
версии/навигации/ручной перемотке сохраняются. Отчёт
`.dev/f200-integration-actual-source-review-20261116.md`; это REQUEST CHANGES,
не общее разрешение merge. Mendel назначен на минимальное исправление и тест,
после чего нужен независимый повторный review. Commit/push/PR/merge пока нет.

## Продолжение: дополнительные общие границы — 253/210/231 PASS

На integration рабочем дереве завершены три неперекрывающихся по выбранным
pytest-файлам запуска; фактические XML и exit receipts сверены Main:

- 253PASS,0skip: восстановление хранилища, strict writer/cleanup/assembly,
  конфликт номера части, renewal/logout, MinIO HTTP cancellation, native join,
  кабинет, lifecycle, normalization worker, sharing contracts/parity browser и
  границы production-smoke scripts на искусственных данных.
- 210PASS,0skip: strict multipart journal, account lifecycle, egress, sharing,
  удаление встречи/исходников/временных медиа, MediaScribe submit через doubles,
  normalization workflow и миграции на отдельном настоящем PostgreSQL.
- 231PASS,0skip: Windows PR JUnit validator и release-images governance tests.

Evidence: `.dev/f200-integration-additional-results-20261116.json` с SHA JUnit,
командами/журналами в трёх указанных каталогах. Оба PostgreSQL запуска подтвердили
`postgres_test_cleanup=isolated_container_removed`; реальная серверная среда и
реальные записи не использовались. Это не полная RLS/production-role/MinIO-матрица,
не GitHub exact-SHA CI и не выпускная приёмка. Проверки прошли до завершающего
исправления адресной перемотки; изменение JS требует собственного RED/GREEN,
а не переноса этих результатов на будущие байты без оговорок.

## Продолжение: независимый допуск узкого исправления адресной перемотки

Ohm перепроверил reviewer-owned F292 UX/security до реализации: UX10/0,
security11/0; все21пункта обоснованы. Уточнение относится к существующему T006,
не расширяет права/API. Разрешено сохранить только неприменённый запрос для
прежнего полного URL/media_version и перенести его на актуальный detail/player.
Применённое или отменённое ожидание не восстанавливается; version/navigation/
manual seek/tab, no-autoplay и сохранение внешнего фокуса обязательны. Отчёт:
`.dev/f292-t006-pending-seek-requirements-review-20261116.md`.
Это requirements GO, не source PASS/закрытие P2. Reviewer добавил примечания
к двум F292 чеклистам в integration; Main их checkbox не изменял. Эти два пути
нужны в отдельной дельте к исходному manifest782.

## Продолжение: T088ABC R2 — source PASS, native build начат

Boole независимо проверил264source/10code-evidence/27build-files и42R1-evidence,
drift0; полный derivative восстановлен и сопоставлен с архивом. Итог R2 — source/
methodology PASS (11exact+2явноinstrumented), без native/runtime claims. Main
прочитал отчёт, проверил seals и local-only verifier, PS5 parser ошибок0.
После проверки отсутствия других jobs запущен только Build R2, не приложение.
Task `GRAF-F200-T088-ABC-Build-R2-20261116`, exact archive SHA-256
`7703f5691defb312f6799892ef38816e8aa213a04ee987154333fc9c55a465e1`.
На момент этой записи task Running/winui-build; terminal result ещё не собран.
Методику стенда одобрил Main в рамках общей авторизации пользователя; отдельного
пользовательского согласия на11+2 не заявляется. R1FAIL и все прежние результаты
сохранены. Build/runtime/installed приемка T088 по-прежнему отдельны.

## Продолжение: T088ABC R2 — фактическая сборка PASS

Main собрал terminal evidence Build R2: task Ready/LastTaskResult0, stage complete,
restore/build/process exits0; source pre/post264/264. Все9файлов сборочной collection
проверены по SHA256, три source receipts побайтно совпали. Build log:0ошибок/4warning.
EXE SHA256 `ef70f4d26efc6c9246cbd9451880d14f5169a4809d625850b99c303b4a7c9841`,
размер3974656. Raw result SHA256
`e2e8fe969c4ae7035cdb34309c710c007bede654824a4cda96e8dc4375f34f44`.
Evidence: `.dev/t088-xaml-abc-20261116/revisions/r2-pre-attach-observer/` →
`build-collection-20261116T015338Z/`; независимый Boole build review PASS в
`build-result-independent-review.md`. Исторический R1 compileFAIL сохранён.
Один read-only stdin transport timeout не был ошибкой сборки; повторный запуск
не выполнялся, terminal collection получена прямым EncodedCommand.
Runtime package готовится отдельно; сборка не доказывает работу окна/приёмку T088.

## Продолжение: адресная перемотка — независимый SOURCE PASS

F292/T006 P2 исправлен в integration: неприменённое ожидание metadata сохраняется
только для того же полного URL/media_version и актуального detail/player.
Применённый/отменённый переход не возрождается; версия/навигация/ручная перемотка/
выбор вкладки отменяют его. Autoplay и перехвата фокуса нет.
Один окончательный browser test даёт RED на закреплённом before и GREEN на
исправленном source в Chromium153.0.8010.12 и WebKit26.6: по10новых сценариев и
прежние проверки. Это настоящий HTMLMediaElement/WAV с Range, не подмена metadata.
Source SHA256 `a5f01e0bfc260f74a89bcf78a91124187601e7e7334083c392e1eea9e231bd9b`;
test SHA256 `d871c3072658fa6955cc753f268b1735bfccf6e8eac5f6396d5353be15ed10c2`.
Mendel report/manifest и все60артефактов сверены независимо Ohm; SOURCE PASS,
новых блокирующих P0/P1/P2 нет. Отчёт
`.dev/f200-integration-p2-independent-source-review-20261116.md`, SHA256
`9493fd21277294c1e376ec0e6c6ed76b9fb20310b8cf728e7fa2ece034e51e0f`.
Это закрытие найденного source P2 в рассмотренном объёме, не полная приёмка F292,
F200, installed Windows/macOS, exact-SHA CI или release. T006/#7905 остаётся открыт.

## Продолжение: отдельные неготовые границы

Подпись публичного выпуска отложена по решению пользователя; сравнение Code Signing
готово отдельно, покупок/регистраций/сообщений поставщикам нет. ЭП ИП для документов
не считается подписью программ. Продуктовая интеграция FFmpeg/пересмотр памяти
не выполнены: решение о внутренней памяти библиотеки остаётся неподтверждённым.
Трёхточечная синтетическая SSO диагностика прошла независимое review proposal;
Main разрешил её ограниченное выполнение вместе с неизменённым baseline, без
VM/продукта/реальных данных и без ослабления исходного zero oracle. На момент
этой записи фактический результат не получен. Общая цель/выпуск не закрыты.

## Продолжение: промежуточный коммит и проверки GitHub

Интеграция786путей закреплена коммитом
`f497000e89bd0fe8b98fcc0c1884a6198b90fae1`, отправлена в отдельную ветку
`codex/200-windows-integration-20261116`; создан draft PR#8061.
Base остаётся `5223422357487ab28cfc83084c9e45717d0a6568`.
GitHub macos-pr run43792439612 и pr-metadata run43792714266 прошли.
Governance run43792439613 остановился на исходном оформлении четырёх
сторонних лицензий; Windows run43792713670 — на недоступном Get-FileHash
в дочернем PowerShell5.1. Это реальные отказы; последующие правки не меняют
их исторический результат. Точное узкое сохранение оформления лицензий,
без изменения их байтов/SHA, прошло независимый review и закреплено отдельным
коммитом `5b66572543a525a9b8c724424024ce382acfcdd9`.
Merge и выпуск не выполнялись; новый SHA требует новых проверок.

## Продолжение: SSO — фактический отказ сохранён

Неизменённый контроль --memory-tail char sso-clear на текущем libc++ даёт
after-clear zero=1, но pre-free zero=0/SIGABRT6. Независимо проверенное
исполнение трёхточечной диагностики показывает111→111→000, exit2:
выбранные три байта нулевые после clear и полного derived wipe, но ненулевые
перед free. Совпадения с исходным синтетическим маркером нет; происхождение
ненулевых байтов и утечка секрета этим не установлены. Исходный zero oracle
сохранён. Отчёт исполнения SHA256
`e4005c561a2e1f0b2c98ff3113bd60c4a11b74919cfe425550665b8fc253b195`;
независимый result/fix-scope report SHA256
`06b4e6c6eda41994456082a79c72a68b9dfcbbfe4ddc9ee910e6e6186c994f03`.
Это Mac synthetic evidence, не утверждение о текущем Windows runtime.
Исправление порядка завершения BasicCustodyString ещё не реализовано.

## Продолжение: T088 — настоящий ограниченный запуск R3 завершился отказом

R2 transport сохранил REQUEST_CHANGES: длинный EncodedCommand не проходит
через Parallels. Отдельная frozen R3 подготовка использует gzip всего запроса,
короткий фиксированный -Command и предел полной гостевой команды<3800.
Независимый delta review PASS; Main actual PS5 parse5/5 и C# Add-Type PASS
без запуска приложения закреплены отдельно. R2 не переименован в PASS.

Main выполнил ровно один запуск R3 в QA ARM после свежего preflight и
отключения только net0. Exact EXE ef70f4d… совпал; source pre/post264/264,
raw input hashes совпали. Task Ready/3, Job Created/Assigned/ProcessSignaled/
JobEmpty=true, TimedOut/Forced=false, exit3. Первое окно initialized/core/
navigation и seed readback прошли, затем abc_host_available остановил сценарий.
Только1из3окон; B/C, окончательный readback и cookie preservation не подтверждены.
Raw evidence сохранено в `.dev/t088-xaml-abc-20261116/revisions/` →
`r2-pre-attach-observer/runtime-r3-short-command/` →
`runtime-collection-20261116T024527181290Z/`.

Fixture сохранила свой профиль при unknown; внешней очистки/повторного запуска
не было. Main postflight подтвердил отсутствие GRAF и исходного browser12080;
другие WebView2 процессы существовали до запуска и не используют fixture UDF.
После подтверждения terminal/JobEmpty сеть QA возвращена к прежнему shared net0.
Рабочая Windows11 не затронута. Требуется разбор причины; T088/F200 остаются открыты.

## Продолжение: T124 — среда PowerShell и чтение журнала

Узкая правка Windows CI запускает весь T124 шаг в Windows PowerShell5.1;
CTest больше не передаёт ему пути модулей PowerShell7 через промежуточный процесс.
Исходный PS1, SHA-256 проверка,8аргументов команды,180s timeout,111сценариев,
JUnit и запреты пропусков сохранены. Журнал Tee-Object остаётся в исходном
UTF16LE+BOM, проверяющий читает его как UTF-16. Реальная цепочка соответствует
описанному Microsoft механизму; выбранный module manifest в старом CI не измерялся.
Новые регрессии воспроизводят отказ прежней конфигурации и ошибку кодировки;
финальный existing governance suite:20PASS/0skip,0.55s, exit0. Embedded Python
validator действительно исполняется на UTF16LE bytes, отвергает duplicate marker
и CTest exit8; raw bytes не переписываются. Это локальный результат на Mac,
не новый Windows CI PASS. Отчёт: `.dev/f200-ci-psmodule-fix-20261116.md`.
Дополнительно Main проверил полный изменённый шаг штатным Parser Windows
PowerShell5.1.26100.9457 в QA:0ошибок; Get-FileHash доступен из
Microsoft.PowerShell.Utility3.1.0.0. Сам шаг/CTest не исполнялся; это syntax
qualification, не suite111. Exact workflow SHA256
`b12468ee32462cacecbe77474c4527015d4f01ca0862f985d70e682f6c231958`;
квитанция `.dev/f200-ci-ps5-qualification-20261116.json`.

Независимое ревью выявило отдельный P2: legacy native argv в PS5 теряет
кавычки Python here-string при передаче через -c. Оба блока теперь поступают
через `$checkPlan | python -I -` и `$checkReport | python -I -`; -I и проверки
кодов выхода сохранены. Тест дополнительно закрепляет оба пути и ASCII-текст
блоков для штатной кодировки stdin PS5. Final focused suite:21PASS/0skip,
0.58s, exit0. Workflow SHA256
`918a58a487dd1f31d3a4c57512c37d3b8793fc38b92d2a9c2d50c9fd84005537`;
test SHA256 `22eae913422ff7616faafea96d6eeb11af5d1454581b04086658e96654899b21`.
Прежний review REQUEST_CHANGES сохранён; новый независимый verdict и GitHub
CI ожидаются. PS5 parser-квитанция выше относится к прежним байтам и не
доказывает выполнение native argv или нынешнего шага. Python в QA не установлен;
его установка ради этой узкой проверки не выполнялась.
Повторный независимый SOURCE PASS получен для точных финальных двух файлов:
`.dev/f200-ci-psmodule-stdin-rereview-20261116.md`, SHA256
`deef89f4b1c497a459348e30ed6f914244316d85abe0139df5bd0d32f15577fb`.
P2 устранён, новых блокирующих замечаний нет; suite111/hosted CI этим не заменены.
