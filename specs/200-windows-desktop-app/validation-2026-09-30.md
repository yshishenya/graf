# Проверка Feature 200 — 2026-09-30

Срез: ветка `codex/200-windows-followup`, `HEAD a9691d4d474d918f54493d55a3aba286c749b513`; рабочее дерево содержит несохранённые изменения. Исторические раунды и SHA из `validation-2026-09-29.md` не переписываются.

## Раунд 110 — регрессии часов и изолированные проверки WebView2

### Часы WASAPI

В `apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp` добавлены три детерминированные проверки `ClockMapper` без изменения рабочего алгоритма и его допуска:

- 65 пакетов с чередующимся смещением QPC на ±0,4 мс проходят без ложного отказа;
- одиночный скачок QPC на 2,5 мс на 11-м пакете завершается `clockDrift`, а следующий пакет после возврата метки к прежней траектории не снимает первый отказ;
- граница на 63 интервалах закреплена тестом: +1,08 мс допускается, +1,09 мс отклоняется.

Проверки собраны и прошли отдельно на macOS и в Windows. Полный набор CTest: macOS **32/32**, Windows 11 VM **32/32**. SHA-256 изменённого тестового файла: `2724e4cb6bceea597b7ae21239f877b0c9f25bf1bed7f0831084c7cafb072727`.

Четыре повторно переданных пользователем Schema 5 совпадают с уже разобранными контрольными и отказными запусками. Новых точек сбоя они не содержат. Причина расхождения packet-QPC на Parallels не установлена; порог не ослаблен, звук тестами не читался и не сохранялся. T094/T096 остаются открытыми.

### Нативный WebView2

Два самостоятельных стенда собраны в Windows x64 Developer Command Prompt из актуальных исходников `WebView2Host` и запускаются в изолированных одноразовых профилях. Серверы слушали только loopback, сертификат и ответы были искусственными; настоящий GRAF, аккаунт, оплата и рабочий сервер не использовались.

- T103, вход и восстановление: **14/14 PASS** — начальная загрузка, HTML-ошибки 400/429/503, явное повторное действие, billing/meeting возврат, обрыв соединения, TLS-ошибка и POST-ошибка.
- T102, ограниченное платёжное окно: **12/12 PASS** — форма/всплывающее окно, вложенные окна и кадры, задержанная отправка, отмена, отказ навигации, перенаправления 303/307 и отсутствие запроса в запрещённых сценариях.
- Оба стенда подтвердили завершение собственных процессов и очистку временных каталогов. Для T102 потребовалась повторная попытка очистки после кратковременной блокировки файла; итоговый статус — PASS.

Это подтверждает изолированные нативные переходы, но не свежую приёмку установленного приложения с настоящим входом. T102/T103 не закрываются только этими испытаниями.

### Блокер самопроверки AEC3 и границы текущего пакета

Повторно проверены только метаданные Windows, без остановки приложения. Установленный GRAF 0.1.0.9 по-прежнему отвечает. Кандидат MSIX 0.1.0.8 имеет SHA-256 `C996C15AFA31D696BD48D86C65F329F98CD0C0E477407D60D6F938B5E61428E4`; исполняемый файл внутри него совпадает с отдельно собранным x64-файлом SHA-256 `BD750D684097C91DFCC9A26EA3112031CEA769282DC30AD1E538DBEEBF027EB1`.

Для этого отдельного файла уже зафиксировано падение команды `--verify-audio-backend`: WER `BEX64`, модуль `ucrtbase.dll`, исключение `0xC0000409`, данные fail-fast `7`. Это не подтверждает работоспособность backend в кандидате. Ранее установленный 0.1.0.9 завершал тот же самотест кодом `73`, но это старый двоичный файл. Стек нового падения получить не удалось: в ВМ нет `cdb`/`windbg`; первопричина остаётся открытой.

Кандидат не устанавливался поверх уже работающего приложения: его версия ниже установленной, а заблокированный Mac не позволяет безопасно проверить, что запись не идёт. Установка, прекращение процесса и возможная потеря текущей записи не выполнялись. Требуется собрать кандидат с версией выше установленной, безопасно закрыть GRAF и повторить проверку именно установленного пакета.

### Статус

Новые синтетические проверки пройдены; это не аппаратная приёмка. Физический Windows x64, непрерывная запись, фактическая причина clock fault, проверка точного установленного пакета и визуальная приёмка остаются открытыми. Публичный выпуск и доверенная внешняя подпись не подтверждены. Коммит, push, PR, merge, установка и выпуск в этом раунде не выполнялись.

## Раунд 112 — полная сборка и подписанный пакет-кандидат

Рабочая ветка и HEAD не менялись: `codex/200-windows-followup`,
`a9691d4d474d918f54493d55a3aba286c749b513`. Все изменённые и новые файлы
`apps/windows` побайтно совпали с Windows-зеркалом перед сборкой.

- `GrafWindows.sln`, Release x64, MSBuild 17.14.51: `MSBUILD_EXIT=0`.
- CMake Release: `CMAKE_BUILD_EXIT=0`, перестраивать нечего; CTest после этого
  шага: **32/32 PASS**.
- Граница WebView2: **7/7 PASS**.
- Аудиоконтракт: синтетические тесты **4/4 PASS**; custody-проверки **3/3
  PASS** после повторного прохождения аудионабора **4/4**.
- `GrafWindows.Package.wapproj`, Release x64, MSIX 0.1.0.11: `PACKAGE_BUILD_EXIT=0`.
  Пакет собран в новом каталоге `apps/windows/Installer/out/round112/`.
- Статическая проверка пакета: `MSIX static smoke passed`; подпись действительна,
  издатель `CN=GRAF`, отпечаток тестового сертификата
  `816CC8B4EB216A0755BFB118992BB594AF51BF6C`.
- SHA-256 MSIX: `5B12304830B42FC831EF4D49127A9B1A21A087356DC43A8A81A7B0B51530EBDF`.
- SHA-256 `GrafWindowsApp.exe` внутри MSIX совпадает с файлом полной сборки:
  `8AD8AFD8D46996CF825F82A6BD6917FFA313896B04406D08630E199F347DA032`.
- В сборке проверена идентичность AEC3 и лицензии, upstream
  `846fe90a289f58b7c9303a635142aa2c7caa93e5`.

В Windows 11 VM (сборка 26200.9168, ARM64 с эмуляцией x64) установлена
версия 0.1.0.9, процесс GRAF PID 2256 отвечает. Открыты два окна PacketProbe
schema6. Версия 0.1.0.11 не устанавливалась, процессы не закрывались;
состояние записи через заблокированный Mac проверить нельзя. Поэтому не
выполнена самопроверка AEC3 именно из установленного MSIX и не принята живая
работа интерфейса.

Переданные четыре schema5 совпадают с четырьмя результатами раунда 105 и не
добавляют точку первого отказа. Они не объясняют чередование `clock_drift`;
допуск и алгоритм `ClockMapper` не менялись. Нужна точка первого отказа из
schema6, затем проверка продукта на точном установленном пакете. Это не
приёмка записи: сырой звук не читался, не сохранялся и не отправлялся.

Рабочее дерево осталось незакоммиченным. Сервер, Mac-приложение, настройки
Windows и пользовательские записи не изменялись. Физический Windows x64,
длительная запись, установочная/обновительная матрица, доступность и визуальная
приёмка остаются открытыми; внешний выпуск не подтверждён.

## Раунд 113 — общие страницы и повторное подтверждение границ (2026-09-30)

Проверки выполнены на незакоммиченном состоянии Feature 200, ветка
`codex/200-windows-followup`, HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`.

- Общие тексты и сценарии платформы: Playwright Chromium **29/29**, WebKit
  **29/29**. Проверены Windows/Mac/старый WebView без метки платформы,
  поздняя установка нативного моста, реальная HTMX-замена фрагмента,
  настройки уведомлений и записи, подписи локального удаления и отсутствие
  ошибок страницы.
- Общее меню профиля: Chromium **33 сценария**, WebKit **33 сценария**;
  проверены боковое раскрытие вправо, встроенный вариант при нехватке места,
  границы окна, прокрутка, закрытие Escape и возврат фокуса.
- Список интеграций/комбобокс: пройдены фильтр и массовый выбор, явное
  подтверждение, клавиатура/IME, сброс, недоступные варианты, обновление
  каталога, 600 вариантов и узкая ширина.
- Согласованность настроек: **224 проверки** страниц, тем, размеров,
  общих элементов, системной тёмной темы, перестроения и диалогов.
- `git diff --check`, разбор `changes/unreleased/F200.yaml` и
  `scripts/check_spec_kit_governance.py`: PASS.

Это синтетическая проверка общего кабинета, не свежая приёмка установленного
GRAF. Последние четыре schema5 повторяют контрольные и отказные результаты,
разобранные в раундах 105/112; новой точки отказа schema6 нет. Порог
`ClockMapper` не менялся. В Windows установленный GRAF 0.1.0.9 всё ещё
отвечает (PID 2256), открыты два окна PacketProbe schema6. Кандидат 0.1.0.11
не устанавливался, процессы и аудиоустройства не изменялись. Mac заблокирован,
поэтому безопасная установка и управление окнами диагностики сейчас
недоступны.

Физическая Windows x64, реальная непрерывная запись, холодная самопроверка
AEC3 из точного установленного пакета, живая приёмка окон, доступность и полный
установочный цикл остаются открытыми. Эти проверки не подтверждают целостность
звука или готовность внешнего выпуска. Commit/push/PR/merge/release не
выполнялись. Legacy: untouched.

## Раунд 114 — повторная нативная сборка и MSIX-кандидат (2026-09-30)

После полного набора синтетических проверок отдельно перепроверен Windows
исходный срез и подготовлен новый пакет. Временное предложение удалить
ограничение истории уведомлений было отвергнуто: `RecordingIndicatorTests`
специально закрепляет предел 50 на входе `WindowsTray`, независимо от
ограничения источника; пробное удаление воспроизводимо провалило этот контракт.
Строка восстановлена, зеркало в Parallels побайтово совпало (`cmp`).

- macOS: сборка CMake и CTest **32/32 PASS**.
- Windows 11 VM: CMake Release пересобрал изменённый общий shell; CTest
  **32/32 PASS**.
- Полное `GrafWindows.sln`, Release x64, MSBuild 17.14.51:
  **BUILD_EXIT=0**. Сборка использовала чистый upstream AEC3
  `846fe90a289f58b7c9303a635142aa2c7caa93e5` и отдельный проверенный каталог
  сборки; `build-graf-aec3.ps1 -VerifyBuildArtifacts` прошёл.
- Новый MSIX 0.1.0.11 собран в
  `apps/windows/Installer/out/round114/`; подпись действительна (`CN=GRAF`,
  тестовый отпечаток `816CC8B4EB216A0755BFB118992BB594AF51BF6C`), статический
  smoke подтвердил `identity=com.graf.desktop`, `entryPoint=GrafWindowsApp.exe`
  и допустимые capabilities. Доверенное хранилище не изменялось.
- SHA-256 MSIX:
  `BCE24CB877F6BB0AB2AFADB37DB44862687892651E5393944D26E78B1618B110`.
  Исполняемый файл в пакете и файл полной сборки совпадают:
  `9F1EC17FB32F06F2F402B49BCD05ABC0F52E5B4607ADE3B712BBD9B35E176CD7`.

Кандидат **не установлен**. В VM всё ещё отвечает установленный GRAF 0.1.0.9
(PID 2256) и открыты два окна PacketProbe schema6; хеш старого установленного
EXE — `9C1ED6177DDD3AF81145385A1364A2287C3EBF9454BF5E0310CC66A101878176`.
Остановка процесса или запись в нём не проверялись. Mac снова заблокирован,
поэтому нельзя подтвердить безопасное закрытие приложения и провести тест
точного установленного MSIX или получить управление окном schema6.

Эта сборка подтверждает компиляцию и состав пакета, но не запуск установленной
версии, AEC3 из неё, живую запись, звук, UI/accessibility или физическую
Windows x64. Остальные аппаратные и release-гейты остаются открыты; commit,
push, PR, merge и release не выполнялись. Legacy: untouched.

## Раунд 115 — установленный MSIX, штатный AEC3 verifier и schema6

HEAD `a9691d4d474d918f54493d55a3aba286c749b513`, ветка
`codex/200-windows-followup`, проверяется dirty snapshot. Эта запись дополняет,
не переписывает исторический статус «не установлен» раунда 114.

После разблокировки CUA показал отказную запись/Start, не активный capture.
Add-AppxPackage -ForceApplicationShutdown установил пакет раунда 114 без
удаления приложения/пользовательского состояния или изменения trust store:
INSTALL_AND_EXACT_HASH=PASS. Регистрация
`com.graf.desktop_0.1.0.11_x64__jqvfym1syd7bp`, Status=Ok.
MSIX SHA-256 `BCE24CB877F6BB0AB2AFADB37DB44862687892651E5393944D26E78B1618B110`;
installed EXE совпал с payload/build:
`9F1EC17FB32F06F2F402B49BCD05ABC0F52E5B4607ADE3B712BBD9B35E176CD7`.
Development CN=GRAF не подтверждает внешнюю подпись.

Первый штатный validate-aec3-build.ps1 получил null ExitCode после WaitForExit,
не доказанный crash. Повтор той же COM MSIX activation с удержанием Handle дал
PID7084, finished=true, exit73. В проверенном 15-минутном окне Event1000 нет
AEC-crash 0.1.0.11; есть старый 0.1.0.9 ntdll c0000005 при shutdown. Старый
непакетный c0000409 не является результатом установленной версии.

Независимый reviewer разрешил только узкое исправление T101 verifier. Добавлены
удержание Process.Handle перед WaitForExit и Dispose в finally. Сохранены
SHA/MSIX/exit73 checks, отказ null/timeout, отсутствие Kill. Зеркало совпало
побайтно (cmp). Product EXE, часы, capture, custody/AEC3 не менялись.
После правки **штатный verifier exit0**:

- Восемь ожидаемых отказов PASS: missing-backend, forced-availability,
  unsupported-architecture, alternate-library, wrong-source-pin,
  missing-provenance, changed-library, stale-source-provenance.
- real-backend=PASS, pin `846fe90a289f58b7c9303a635142aa2c7caa93e5`.
- native-msix-activation=PASS pid=11868 exit=73; AEC3_VERIFIER_EXIT=0.

Самопроверка создаёт настоящий AEC3 и выполняет reverse-before-microphone
на нулевом 480-sample блоке без устройств, записей, профиля и сети. Это proof
установленного backend, не готовность настоящей записи и не closure T101.

Пользователь запустил schema6: 65 packets/31200 frames, released65,
release_failures0, startup_discarded480, один стартовый discontinuity,
timestamp_error0, gaps min/max/residual0. Первый clock_drift packet60 (stats59):
packet QPC error12707 × 100 ns, current-clock error-10001, paired span shift-22708.
Пересчёт: 1.2707 ms > 1.0789604 ms budget. audio_read=false,
continuity_acceptance=false: lossless audio/alignment не подтверждены.
Выводы сверки открытого Windows-кода записаны в research.md. VM как причина
не доказана. Нажатия CUA через Parallels не запускали probe, нажатие пользователя
сработало; это не признано дефектом кнопки GRAF.

Review: 112/112 буквальных пунктов, но общий REQUEST_CHANGES/HIGH RQ30-H1
(шифрование local buffers/custody). ACL и AEC3 PASS его не закрывают. Новый
GUI запуск/T097, hardware/60-minute capture, auth/upload/deletion E2E,
accessibility, clean-image install/update/rollback и внешняя подпись остаются
непроверенными. Governance и git diff --check после verifier PASS.
Commit/push/PR/merge/release/deploy не выполнялись. Legacy: untouched.

## Раунд 116 — уточнения и одинаковая диагностика x64/ARM64

Ветка `codex/200-windows-followup`, HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`, dirty worktree. Исходный
и установленный продукт этого раунда не пересобирался/не менялся. Пользователь
подтвердил закрытие GRAF/старых PacketProbe; перед запуском новой диагностики
проверено `graf_or_probe_running=0`. Настройки устройств не менялись.

### Синтетическая цепочка, без VM и микрофона

Стенд вне git `/tmp/graf-f200-clock-replay.2sWtSF/check.cpp` связывает
настоящие ClockMapper/AudioNormalizer/RecordingAudioTimeline. SHA-256 стенда
`b71f46c3a28fbd5d3a57cd7ecfc75887961929be18b6b84311c7aaa8b3299a31`.
Повторный запуск: ideal contiguous PASS; одиночная ошибка метки 1.2707 ms
при budget 1.07896 ms даёт sticky clockDrift PASS; один отсутствующий frame
даёт sampleCountMismatch PASS. Контрфактический обход mapper только в стенде
показывает следующий отказ timeline: скачок 61 при разрешённых 48 frames.
Это не полный replay аппаратных пакетов и не проверка AEC/записи; все sample
values искусственные. Увеличение только порога mapper не исправляет цепочку.

### Сборка сравнения архитектур, без запуска захвата

Обе diagnostics собраны Visual Studio 2022 17.14.39, MSVC14.44.35207 из
одного неизменённого PacketProbe schema6 и настоящего ClockMapper. Mapper
cpp/h побайтно совпадают с product source (`cmp`). Build directory вне git:
`Documents/graf-windows-followup-200/f200-arch-comparison.gJ8bq3`.

- X64_BUILD_EXIT=0, PE machine0x8664; exe SHA-256
  `69EA65FDF702189D94F530A5BFB419F712BB945EB3677AEB0E52A9B6307CDD07`.
- ARM64_BUILD_EXIT=0, PE machine0xAA64; exe SHA-256
  `3B4128C5CC633CF460EAF9F8BEA457B80C43332D4F107193AE4510C447D9E6B1`.
- На каждой архитектуре четыре self-checks PASS: ServiceTiming, MixFormat,
  PacketStats, Summary; worst-case summary964 bytes <1024. Эти проверки
  не вызывают COM capture и не читают устройства.
- PacketProbe.cpp SHA-256
  `580d5f440ce04991bd9f8d08415383d41fd7291db1badf3a4edacd372cbcc9af`;
  ClockMapper.cpp SHA-256
  `3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827`.

После exact hash/zero-process guard открыт только ARM64 GUI PID2956.
Start не запрошен CLI: тест требует явного нажатия в окне и ограничен
65 packets/64 stats, 5s deadline, checked release/Stop. В stdout допускается
только bounded aggregate schema6, без звука, абсолютных меток, путей устройств
и сети. Последняя проверка: result.jsonl пуст; CUA не передаёт нажатия в
Windows, меню «Пуск» перекрывает часть окна. Пользователю предложено нажать
Start48000; результата этого запуска пока нет. X64 GUI не открывался.
Сравнение влияния эмуляции и аппаратная приёмка НЕ завершены; ARM64-продукт
не объявлен поддерживаемым.

### Требования и исследование

Spec Kit high-risk-product: clarify уточняет применимость FR012/F057 к
локальным/временным файлам; ACL не считается шифрованием. Исследователь
проследил writer/readers/queue/upload/playback/purge; кандидаты DPAPI/CNG и
ограничения EFS/MP4 описаны в research.md. Найдено whole-file allocation
в sha256File, не совместимое с доказательством часового memory gate.
Plan отмечает незавершённую Phase0, не разрешает пока реализацию нового
clock/protection формата. В quickstart убрана устаревшая гипотеза resampling,
противоречившая действующему exact device/count §5. Его числа не менялись.

Независимый review текущих уточнений запрошен; общий RQ30-H1 и аппаратные/
сквозные/визуальные гейты не закрыты. Governance, frozen bootstrap doctor,
YAML parse и git diff --check PASS до добавления этого раздела; повторный
контроль после всего diff нужен отдельно. Reviewer checkboxes не отмечались
основным агентом. Коммит/push/PR/merge/release/deploy не выполнялись.

## Раунд 117 — исследовательская проверка DPAPI/CNG и Media Foundation streams

Тот же dirty worktree/HEAD `a9691d4d474d918f54493d55a3aba286c749b513`.
Предыдущий goal-turn — progress: уточнения и same-source diagnostics build;
в этом раунде исследование получило новый исполнимый результат, не только план.

Независимый reviewer принял явное наследование шифрования в FR012 и исправление
quickstart как ограниченные уточнения. Исходная неполнота формулировки RQ30-H1
снята, но общий gate NOT READY: формат, contract/data-model/tasks и реализация
открыты. Append-only review: checklists/review-2026-09-30.md:489–566;
прежние 487 строк сохранены, 112/112 checkbox не являются новой приёмкой
расширенной защиты. Tasks113/91 checked/22 open без изменений. Mapper threshold
и §5 не изменены; контракт SHA-256
`8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135`.

Research fixture вне git:
`Documents/graf-windows-followup-200/f200-storage-stream-proof.b5wKeF`.
Первый build строго /W4 /WX отклонил signed/unsigned enum stream ID;
исправлены явные DWORD conversion без отключения warnings. Последний build
exit0, исполнение exact-SHA exe с 15s parent watchdog exit0, stderr0 bytes.

- CPP SHA-256:
  `4d01cafe61de132fc6a8b1184a88b89d81e318101427d77b8542dfacbf2b65da`.
- EXE SHA-256:
  `5ceef206c39fe9ab6cec30107efc4c6ec87b9eb264f68f8c103853cc8745cf05`.
- DPAPI user-scope random key protect/unprotect + CNG AES-GCM exact logical
  bytes и три tamper guards (ciphertext/tag/block-identity AAD): PASS.
- Native IStream/MFByteStream AAC encode, encrypted/decrypted fixture bytes,
  reopen/source reader/decode to EOS: PASS; M4A12929 bytes, PCM96256 bytes.
- synthetic_only=true, devices=false, media_files=false, network=false,
  product_changed=false. Ключи/звук/byte content не экспортировались.

Маленький секундный fixture весь в памяти, не file-backed encrypted stream;
не доказывает hour/memory128MiB, disk/restart/integrity recovery, seek rewrite,
nonce lifecycle, migration, другие профили, WindowsHome/10 или воспроизведение.
Runner Administrator role=True: standard-user gate этим запуском не закрывается.
Продукт/устройства/пользовательские пакеты не менялись. Native wrapper выбран
как API-граница; весь формат ещё не выбран, Phase0 не завершена.

Повторная проверка ARM64 probe: PID2956 отвечает, path соответствует exact
comparison exe; GRAF_RUNNING=0, result.jsonl0 bytes. Это живое ожидание явного
Start, не результат сравнения архитектур. Новый capture не запускался;
предыдущий MSIX/самопроверка AEC3 не переоцениваются как аудиоприёмка.
Коммит/push/PR/merge/release/deploy не выполнялись.

## Раунд 118 — нативные bounded DPAPI blocks и исследование commit/recovery

Рабочее дерево `codex/200-windows-followup`, HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`, dirty. Предыдущий goal-turn —
progress (native stream/crypto fixture и независимый review), не завершение
общего планирования. В этом раунде проверен более простой block crypto путь;
runtime/storage/пакет GRAF и частные записи не менялись.

Fixture вне git `f200-dpapi-block-proof.PRtfBz/BlockProof.cpp`, SHA-256
`b7b638ea24d4fc6522daa7d18a880ddd75255ac965350a528cc4909f15f58410`;
x64 exe SHA-256
`24f85b5cc7d45d1853c1b71411947a50d5dfe1cb0e03a8c1f72b5dfa64b7026f`.
/W4 /WX build exit0. Guarded exact-hash execution PID15812, 30s own-process
watchdog, exit0, stderr0. Synthetic payload только в памяти, без устройств,
media files, сети и экспорта содержимого/ключей.

Три размера (64KiB/256KiB/1MiB), на каждом 12 round trips после warmup: PASS;
на каждом шесть guards PASS — ciphertext mutation, truncation, index,
generation, expected length и corrupted decoded output. После TRUE от DPAPI
дополнительно проверяется context/точная длина/инкрементальный SHA256; Microsoft
предупреждает, что TRUE сам по себе не гарантирует неповреждённый результат.
Protect mean/max µs: 5492/6430, 20295/30808, 76957/92806;
unprotect: 5059/5592, 21143/53442, 73950/97597. Cipher overhead294 bytes.
Это наблюдаемое wall-time в VM, не CPU/memory/диск/часовой SC003 proof,
не стандартный пользователь: тот же runner admin role=True в раунде117.

Независимый исследователь прочитал AtomicFileStore/path/readiness/purge helpers
и предложил immutable encrypted block versions + два protected index slots.
Найдены отсутствие CREATE_NEW, native FlushFileBuffers и handle-based guards,
ACL после записи, неполная storageWritable проверка; каталог блоков не проходит
старый short-recording regular-files-only discard. Предложение и ограничения
зафиксированы в research.md; source не правился. Existing AppInstance/lease и
async finalizer существуют — ещё один lock service/queue не создавался.
Отключение питания и падение процесса различаются; barrier/весь формат пока
не проверены. RQ30-H1 и Phase0/review gate остаются открытыми.

Первый Parallels build call вернул PrlJob invalid argument без live session;
проверены VM running и cmd/ver, повтор той же команды успешно собрал fixture.
Смена VM/устройства, перезапуск и новый capture не выполнялись. ARM64 schema6
result.jsonl всё ещё0 bytes; новая архитектурная аудио-приёмка не заявляется.
GitHub/commit/push/PR/merge/release/deploy не выполнялись.

## Раунд 119 — file-backed process-crash/recovery на synthetic ciphertext

Worktree `codex/200-windows-followup`, HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`, dirty сохранён. Проверена
хронология раундов117/118. Повторные governance, YAML parse и diff --check
после раунда118 PASS. Риск high-risk-product; продолжается Phase0 speckit-plan,
не production implementation. Необязательный after_plan agent-context hook
не применяется к незавершённому этапу; commit hooks выключены.

Новый fixture вне git `f200-dpapi-commit-proof.9xdyLi/CommitProof.cpp`, SHA-256
`ced3982c08668428390f32983b1e7a374f9aec1fedbdfa928290af1de1d9b387`;
build.cmd SHA-256 `dd4319df1753db90de9e5dfd910b77e91c49dd6d4e827347e62dd9c3de9c1a1a`.
Повторное использование BlockProof.cpp раунда118, без нового crypto provider.
x64 /W4 /WX build exit0, EXE SHA-256
`3cc539dd67d84f0f283c78576a55fb2229f66577e3c3420c7c6aac0df61858fc`.
Первый запуск exit0, второй guarded exact-hash запуск exit0/stderr0. Parent
watchdog30s, each own child10s; stage1–6 child ExitProcess77 проверен родителем.

Семь вариантов (без сбоя и шесть точек остановки) PASS: до публикации
восстанавливается generation1, после неё generation2. Дополнительные guards:
неактивный slot заменяется generation3, повреждённый block3 даёт только
generation2/invalid1, усечение второго index даёт generation0/invalid2;
CREATE_NEW collision отклонён во всех семи вариантах. Подробности/ограничения
в research.md. Bytes только искусственные64KiB, devices/network=false;
новые каталоги на fixed Windows-local NTFS с DACL до записи, а не C:\Mac.
Синтетические encrypted fixtures оставлены для проверки; пользовательские
файлы/настройки/устройства и runtime GRAF не менялись. Ни power-loss,
ни standard-user, ни полный format/resource/security gate не закрываются.

ARM64 diagnostic PID2956 всё ещё Responding, GRAF отсутствует. Через CUA
повторены два отдельных разрешённых нажатия Start48000; свежий screenshot
до них показывает «микрофон НЕ включен». После них stdout result.jsonl0 bytes.
Новое аудио-наблюдение/сравнение x64/ARM64 не получено, VM-причина не доказана.
Не создавался обход GUI Start и не запускался unattended capture.
Численные §5/ClockMapper не менялись, T094/T097 и общий RQ30-H1 открыты.
Commit/push/PR/merge/release/deploy не выполнялись.

## Раунд 120 — подтверждённый ARM64 clockDrift и переход к x64

Предыдущий turn — progress: process-crash ciphertext fixture. Текущее дерево
`codex/200-windows-followup`, HEAD `a9691d4d474d918f54493d55a3aba286c749b513`.
Получен новый реальный результат metadata-only от пользователя; совпадение со
stdout PID2956/path/hash ARM64 подтверждено. Файл820 bytes. End packet_limit,
65packets31200frames, released65/releaseFailures0/Stop S_OK, startup480,
gaps0/0/0, firstFaultPacket12 clockDrift, valid10, elapsed665ms.
Численные пять checkpoint values и ограничения приведены в research.md.

ARM64 code hash `3b4128c5cc633cf460eaf9f8bea457b80c43332d4f107193ae4510c447d9e6b1`;
x64 `69ea65fdf702189d94f530a5bfb419f712bb945eb3677aeb0e52a9b6307cdd07`.
Сначала проверены завершение теста и отсутствие GRAF, затем остановлен только
свой ARM64 PID2956. Немедленный count guard увидел ещё завершающийся процесс
и остановил первый launch script с OTHER_PROBE_RUNNING; никакой второй capture
не стартовал. Повторный process inventory подтвердил0, после чего открыт
только exact-hash x64 GUI PID11832. Responding=True, count1/GRAF0, stdout0.
Пользователю предложен один explicit Start48000. GUI launch не включает mic;
сравнение архитектур пока не завершено. Storage/другие VM benchmark tests не
запускались одновременно, чтобы не добавлять нагрузку этому сравнению.

CPP synthetic isolation `/tmp/graf-f200-clock-replay.2sWtSF/check.cpp` SHA-256
`c6b918256b47e3debba80b5c100596e326eaa1e7d2f42cf3c8b9f9903002d799`,
exe `abbfe2b9637379f90aaa5b0e9be655b6f6b7ea14af960674cdc4c77ad8e9b5d0`:
clang++ C++17/Wall/Wextra/Werror build0/run0. Historical1.2707ms/61frames и
native ARM64 checkpoint1.1438ms/55frames cases PASS: ideal, sticky mapper
fault, missing-frame reject, counterfactual bypass downstream reject. Только
искусственные samples/QPC, не replay всех hardware packets и не audio/AEC test.
ClockMapper.cpp/h cmp с diagnostic copies PASS. §5 SHA-256 неизменен:
`8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135`.

speckit-plan setup existing plan preserved; risk high-risk-product/Phase0.
Нативный ARM64 результат исключает только объяснение «сбой исключительно из-за
x64 emulation», не доказывает VM/драйвер root cause. T094/SC003/общая модель
часов и RQ30-H1 открыты; задачи/checklist не закрывались, код продукта не правился.
Commit/push/PR/merge/release/deploy не выполнялись.

## Раунд 121 — конкретный выбор storage пути и проверка bounds

Тот же worktree/HEAD `a9691d4d474d918f54493d55a3aba286c749b513`, dirty
сохранён. Предыдущий turn — progress: verified native ARM64 outcome/clock-chain
isolation. Сейчас speckit-plan Phase0 получил конкретные storage decisions,
а не только новые неизвестные: user-scope DPAPI, immutable256KiB blocks,
two protected slots, bounded16B index entries, native byte-stream playback.
Независимый read-only исследователь дал предложение; основным агентом оно
уточнено по реальным границам writer/server. Reviewer gate не выдаётся за PASS.

Предложение16GiB расширено до64GiB только как representation/parser bound,
чтобы не ограничивать canonical writer раньше его существующего RIFF u32
boundary25769803554bytes. Строка local parser≤24h не означает server accepts24h:
config max_recording_duration_seconds14400 и ingest policy =4h. Ни сервер,
ни продуктовые duration/quota настройки не менялись; обнаруженное расхождение
зафиксировано до последующей приёмки паритета. Группа4blocks не используется
для ожидания5.46s checkpoint: canonical full-block cadence≈1.365s при192000B/s,
явный Flush/Pause/Stop публикует tail; raw accepted≠durable checkpoint.

Вне git `/tmp/graf-f200-storage-bounds.dMZocV/check.cpp`, CPP SHA-256
`278566e785580d3c37b1200f14cd9e89007fafb9bc7671d1285995a43fe93aea`,
exe `141adde778303c2603ccc1239b9af8b39052dfb0b1d1d9a464565b20f9a6f9c0`:
clang++ C++17/Wall/Wextra/Wpedantic/Werror/ASan/UBSan build0/run0.
PASS dimensions0/partial/full/max, oversized/UINT64/offset/count guards,
exact index byte length, flags/ZERO, cipher bound; canonical1h/4h/24h numeric
cases2637/10547/63282blocks. Это только design arithmetic, не production parser,
allocation/resource/crypto/power-loss/streamed media acceptance.

Прочитаны actual LocalMetadataScan/open-validation background paths, существующий
whole-file hashing и upload part reader. Новый scanner/queue не создаётся.
Microsoft native Media Engine docs подтверждают byte-stream source/audio-only
flag/required callback; runtime playback не проверен. Ошибочный URL варианта
метода и несуществующего audio-only attribute отброшены, правильные первичные
страницы приведены в research.md. Исследователь завершён/закрыт; files он не правил.

VM benchmark не запускался, чтобы не добавлять нагрузку x64/ARM64 сравнению.
Live x64 PID11832 подтверждён Responding с exact comparison path, result0 bytes,
явный Start пока ожидается. Новое capture не запускалось. Первое составное
apply_patch не прошло проверку plan context и не изменило файлов; после чтения
контекста выполнены отдельные точные изменения research/plan.
Общий Phase0 NOT READY: coherent clock model и точный Phase1 package migration/
wire/contract остаются; задачи/checklist не закрывались. Source/runtime/installed
MSIX, реальные записи и GitHub не менялись; commit/push/PR/merge/release/deploy нет.

## Раунд 122 — синтетическая проверка различимости часов

Работа в `codex/200-windows-followup`, HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`; dirty сохранён.
speckit-plan setup/prerequisites подтвердили существующие F200 paths; optional
after_plan не применяется к незавершённому этапу. Windows inventory: exact-path
x64 PacketProbe PID11832 Responding=True, result0/stderr0 bytes; GRAF отсутствует.
Ожидается ранее запрошенный явный Start. Новая проверка микрофона не запускалась,
нагрузочные тесты/сборка в VM не выполнялись.

Standalone `/tmp/graf-f200-clock-feasibility.yvkwK5/check.cpp`, SHA-256
`3b54380d082bfb858446424f14a4be3de000a2304442726f91f6cd28dc3d6f32`,
exe `a295fcd2655ffe790135cc0c2eaf47fb8da5a7259c515d9c3389fb32027f1374`:
clang++ C++17/Wall/Wextra/Wpedantic/Werror/ASan/UBSan build0/run0.
Проверены идеальный час, bounded alternating noise/одиночный timestamp residual,
±100ppm, пересечение phase intervals, неоднозначность100/200ppm на120s и
исключение сразу за границей, phase step/sticky reject/overflow guards.
Actual ClockMapper rejects missing/repeated frame/midstream flags. Sparse ARM64
checkpoints fit nominal slope при гипотетическом J3ms с phase width3712200ns;
это не полный аппаратный trace, не новый3ms threshold и не audio acceptance.

Независимая математическая проверка различает 2J/T uncertainty, 4J/Δe guaranteed
separation при неизвестной phase и 2J/Δe с независимым точным anchor. Исследователь
завершён и закрыт, files не правил. Неверный первый send_input не прошёл schema
validation и не доставился; повтор с target принят. Обоснование/primary sources
добавлены в research. §5 и исходники product mapper/normalizer/timeline не менялись.
Production PTS model/Phase0 и T094/SC003 открыты; tasks/reviewer checklist не
закрывались. Commit/push/PR/merge/release/deploy не выполнялись.

## Раунд 123 — контрпример к сглаживанию меток без адаптации resampler

`codex/200-windows-followup`, HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`,93 dirty entries сохранены.
Предыдущий turn — progress: deterministic frequency identifiability evidence.
Теперь проверен отдельный counterfactual phase filter с настоящими Windows
normalizer/timeline исходниками; product mapper не подменялся/не редактировался.
Четыре60s synthetic constant cases0/0,+100/−100ppm fixed/variable batches PASS;
10s synthetic tone counterexample отверг алгоритм для дальнейшей реализации:
healthy timeline, RMS−0.000899928dB, max reference/joint error0.5 при amplitude0.25,
trimmed render frames1415. Значит, constant/RMS-only проверки недостаточны.
Все числа относятся только к экспериментальной модели с assumed±3ms uncertainty.

`/tmp/graf-f200-clock-filter.vAEmXa/check.cpp` SHA-256
`9ef5c4cd01d4c2fc6092c72af973b764cb31ea9eda23b425d4fb32f1d7890683`,
exe `23f9d6c2ae28efb163058f91ce92c543a39ce60baa49e956a4dda0000727f502`.
clang++ C++17/O2/Wall/Wextra/Wpedantic/Werror/ASan/UBSan build0/run0; дополнительно
sticky200ppm/noiseless rejection packet6021, count loss/repeat и phase jump PASS.
Нет actual AEC/device/private PCM/network; не SC00360minute/resource acceptance.
Ранее записанные первый проход/хеши fixture заменены только в новом evidence:
окончательный стенд включает tone counterexample; исторические файлы не менялись.

Прочитаны primary Chromium pinned SnooperNode ratio correction, WebRTC capture
latency/flags, GStreamer slave-method API; relaxed/silence/drop paths отвергнуты,
сторонний код не копировался. Gitiles503 обойдён read-only GitHub primary mirror,
commit pin получен из публичного API. setup-plan сохранил existing plan;
after_plan context hook не выполняется для открытой Phase0.

CUA видит unlocked Parallels/schema6 GUI с пустым результатом; screenshot-only
не сохранялся в git. Coordinate click переводит указатель на Start, но не
включает тест. Native menus открываются через AX; Escape не закрыл меню,
documented Cancel закрыл. Keyboard toolbar AX вызовы дали failure; в меню
Devices/Keyboard нет обычного Return/Tab. Меню закрыто через Cancel; VM/devices/
shortcuts/security настройки не менялись. Никакой обходной UI automation нет.
Новое capture не подтверждено, ранее запрошенный x64 Start ожидается.
Tasks/checklists/§5/installed package не изменены; commit/push/PR/merge/release/deploy нет.

## Раунд 124 — собственный CLI и последовательное сравнение архитектур

`codex/200-windows-followup`, HEAD
`a9691d4d474d918f54493d55a3aba286c749b513`;93 dirty entries сохранены.
speckit-plan/prerequisites подтвердили F200; Phase0 не закрывается,
after_plan context hook не запускался. Работа исследовательская, не product
implementation. Пользователь ранее разрешил последовательные тесты микрофона
до решения основной задачи; PCM не читается/сохраняется/отправляется.

Вне git `Documents/graf-windows-followup-200/f200-cli-comparison.nHD4Qk`:
PacketProbe.cpp SHA256
`37376933d26f4590a4fdfb982acb5036713b1ea472e5009b43d29f580a470a44`;
неизменённый ClockMapper.cpp
`3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827`;
PacketStats.h `898fc1f00e385a7759fade2d0c956eca907fa68446af5ef673f48baf1637ab3a`.
ClockMapper.cpp/h cmp с продуктом и PacketStats с прежней schema6 PASS.
build.cmd `522cedfa3b023d60c74b81500ce1361235196b0430e8822f6783b1081918e935`.
x64 PE8664 exe
`9b98b000f81ebc753a3d13b2b8e07239dbbdcaf5f5f1b994abf89ae7e6e6fd2e`;
ARM64 PEaa64 exe
`809f512c74bacc866e2195f7838ad9782a44e97af699db1def3bb32a6904a017`.
Обе сборки /W4 /WX C++17 /O2 /MT build0, по4 no-capture selfcheck PASS:
ServiceTiming, MixFormat, PacketStats, Summary/strict command parser.
Worst-case summary964B≤1024. Неизвестные CLI args exit64 до захвата.

Старый ручной probe PID11832 завершён только после проверки точного пути/hash
и отсутствия результата; GRAF отсутствовал. Вместо синтеза нажатий добавлен
явный CLI, который использует существующий beginProbe/worker, показывает окно
и индикатор до capture, сохраняет Stop, выдаёт stdout только после join/cleanup.

Первый parent на Start-Process PID6060 дал null ExitCode и пустые stdout/stderr;
parent exit1/PROBE_EXIT_FAILED. Этот запуск НЕ принят как capture PASS и не
использован для сравнения. Файлы cli-result.jsonl/cli-error.txt сохранены пустыми.
Parent заменён на Diagnostics.Process с retained handle и redirected pipes,
12s own-child watchdog; bounded summary исключает переполнение pipe. Само
наблюдение ограничено5s. Никакая UI automation/настройка UAC/устройств не добавлена.

Последовательные принятые запуски через current-user Parallels CLI:

| Поле | x64 PID12124 | ARM64 PID11032 |
|---|---|---|
| Parent/child exit | 0/0 | 0/0 |
| Summary bytes | 788 | 733 |
| Packets / released / release failures | 31/31/0 | 7/7/0 |
| Frames / valid packets / cleanup ms | 14880/21/352 | 3360/5/91 |
| Stop HRESULT | 0x00000000 | 0x00000000 |
| First fault | clock_drift packet23 | discontinuity packet7 |
| End / guard | metadata_guard/discontinuity | metadata_guard/discontinuity |
| Discontinuity / timestamp-error flags | 2/0 | 2/0 |
| Startup discarded / buffer frames | 480/4800 | 480/4800 |
| Clean-prefix frame gaps min/max/residual | 0/0/0 | 0/0/0 |
| Service / held-packet µs | 20857/190 | 22265/33 |

x64 relative clock checkpoints100ns:
`[2,-900,-100000,-99100],[8,-13,-119933,-119920],[22,12869,-99113,-111982]`;
ARM64: `[2,1522,-100000,-101522]`.
Оба audio_read=false/continuity_acceptance=false. Runner проверил native Stop,
release counts, deadline, bounded JSON и отсутствие capture processes после
каждого опыта. Это успешное выполнение диагностики, НЕ успешность часов/записи.
Серии короткие и разной длины: architecture performance вывод запрещён.

Runner SHA в двух опытах
`176d1873f8260cc453b1cb088db61927f70a84e1a93b3e049388a15d6ac07c5a`.
После опытов добавлен только finally/Dispose при ошибке; окончательный runner
`399ae873d5da09ebadc613848c6d6ff0e1f1c5adaa8c146e957cf574b8be047b`.
Повторное capture ради этой правки не выполнялось; Windows parser и process
inventory проверяются отдельно. Результаты прежней оболочки не выдаются за
исполнение нового hash. Metadata-only сравнение подтверждает, что x64 эмуляция
не является необходимым условием сбоя; VM/driver sole-cause не установлена.
§5/SC003/production ClockMapper/Normalizer/Timeline, задачи и reviewer checklist
не менялись; installed0.1.0.11 не обновлялся. Реальные пользовательские файлы,
состояние устройств, сервер и GitHub не затронуты. Commit/push/PR/merge/release/deploy нет.

Дополнительные проверки round124: final runner Windows AST parse PASS,
CAPTURE_PROCESS_COUNT=0 до открытия GRAF. Focused governance PASS, YAML parse
PASS и git diff --check PASS. После этого для независимого осмотра UI запущен
ранее установленный MSIX0.1.0.11: Package Status=Ok, точный exe hash
`9f1ec17fb32f06f2f402b49bcd05abc0f52e5b4607ade3b712bbd9b35e176cd7`.
CUA подтверждает главное окно, загруженную общую страницу, native idle/Start,
выбор Windows-микрофона; «WebView2 недоступен» не показан. Новая запись не
запускалась, страницы встреч/личные сведения не сохранялись как evidence.
Coordinate focus/profile click, AX Raise и double click не открыли меню;
полная интерактивная приёмка T097 остаётся неподтверждённой. UI обхода через
Win32/SendInput/UIA нет; не надо повторять эту же неработающую последовательность.

В ходе чтения native worker найден дополнительный scheduling вопрос: ни
product worker, ни probe не регистрируют capture thread в MMCSS. Product
requested buffer10ms, probe100ms; новая100ms величина не перенесена в GRAF.
Microsoft AvSetMmThreadCharacteristics описывает регистрацию текущего thread
и обязательный AvRevert; это основание следующего ограниченного сравнения,
не доказательство причины clock_drift и не permission менять registry/service/
global priority. Пока добавлены только исследовательские сведения.

Независимый исследователь Pascal завершён/закрыт, files не менял: direct pinned
WebRTC SincResampler SetRatio сохраняет phase, existing libcommon_audio link
reuse возможен на уровне исходников/API; местные vendor headers/artifacts
в этом worktree отсутствуют. PushSincResampler/discrete Resampler отвергнуты.
Численные clock estimator/phase correction bounds, sinc startup/partial EOS
остаются неподтверждёнными. Main перепроверил exact pinned header/implementation
через primary source; чужой код не копировался и новая dependency не добавлена.

Новый bounded synthetic counterexample к exception custody:
`/tmp/graf-f200-release-allocation.ZT2GOG/check.cpp`, CPP SHA256
`205d0494ba01a56ea1bbe2138ff6346cc5a28758fa18452b8f7ce380501e3fd4`,
exe `8702f73577a90c237b0ddb61cf77b000d8eda17e0e9e36cfe5b7d3fc93f0c52b`.
Actual worker/ClockMapper/Normalizer/EndpointEnumerator compiled C++17/O2/
Wall/Wextra/Wpedantic/Werror/ASan/UBSan build0/run0. Одно искусственное
bad_alloc только для480float allocation, без исчерпания RAM или устройств:
`ALLOCATION_FAULT_REPRODUCED=1 RELEASE_CALLS=0 CUSTODY_ACCEPTED=0`.
Это успешное воспроизведение ошибки, НЕ успешный custody test. Product exception
ветка требует исправления по T096; рабочий код не правился и задача не закрыта.
Прежний pending request на ручной Start больше не нужен: CLI исследования
заменяет этот entrypoint, но не GUI acceptance T097. GRAF оставлен открытым
в проверенном idle; новую запись main не начинал.
