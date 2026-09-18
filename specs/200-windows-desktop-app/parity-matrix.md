# Parity matrix: macOS → Windows

Это контракт смысла, а не требование повторить Swift/AppKit implementation.
Windows может использовать WinUI 3/Win32 conventions, но пользовательское
состояние, privacy boundary, custody и server-owned cabinet должны иметь тот же
смысл.

| Область macOS | Source of truth | Windows owner | Обязательный смысл | Допустимое отличие |
|---|---|---|---|---|
| Manual Record/Pause/Resume/Stop | `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`, `CaptureControlViewCore.swift` | `RecApp/Capture/WindowsCaptureSessionController.*` | One active session, explicit transitions, idempotent Stop, privacy Pause | Windows controls/tray placement |
| Native indicator | `CaptureStatusItem.swift` and Feature 197 surface | `RecApp/Shell/RecordingIndicator.*` | Visible active/degraded/paused state and one-action Stop outside web | Windows notification/tray conventions |
| Permission onboarding | `DesktopPermissionOnboardingView.swift`, `RecordingPrerequisiteGate.swift` | `RecApp/Permissions/*` + `RecApp/AppMain.cpp` | Separate microphone/system-audio/storage/runtime reasons and recovery | Windows Privacy Settings destination |
| System audio + microphone | `SystemAudioCaptureService.swift`, `MicrophoneCaptureService.swift` | `RecApp/Audio/*` | Native capture, separate sources, timestamped batches, no raw fallback | WASAPI shared render loopback replaces ScreenCaptureKit |
| AEC3/timeline | `RecordingEchoProcessor.swift`, `RecordingAudioTimeline.swift`, Feature 177 | `Native/GrafAEC3/*`, `RecApp/Audio/RecordingAudioTimeline.*` | Reference before mic, exact 10 ms frames, one alignment owner, trusted prefix | WASAPI/QPC clock mapping replaces Core Audio/PTS sources |
| Local package | `V5LocalRecordingWriter.swift`, `LocalRecordingManifestService.swift`, `LocalRecordingStore.swift` | `RecApp/Recording/*`, `RecApp/Storage/*` | v5-compatible manifest, ASR WAV, playback M4A, integrity before queue | User-scoped `%LOCALAPPDATA%\GRAF` and Windows ACL/atomic rename |
| Upload custody | `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`, `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`, Feature 193/194 | `RecApp/Upload/*` | `desktop-upload-queue.v2`, server truth, accepted ranges, retry/reconcile | Windows scheduler/power hooks |
| Cabinet routes | `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`, `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `RecApp/Web/*`, `CabinetWindow.*` | Same server origin/routes, exact allowlist, no duplicate meeting UI | WebView2 runtime and Windows navigation handoff |
| Profile menu / Close GRAF | macOS `EmbeddedCabinetQuitBridge` and shared embedded cabinet profile menu | server-owned embedded template + `WebView2Host.*` | Same profile actions and one explicit shell-close action; quit remains native and route-bound | WinUI window close lifecycle instead of `NSApp.terminate` |
| Native/web bridge | `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetSessionBridge.swift`, upload/capture bridge contracts | `RecApp/Web/WebViewBridge.*` | Versioned bounded JSON, exact origin, session nonce, no generic host object | WebView2 web-message API instead of WKWebView bridge |
| Auth/review/deletion | server cabinet route and existing desktop API contracts | WebView cabinet + native custody | Server owns business truth; native owns local purge evidence | Windows runtime/offline state outside page |
| Automatic recording | `MeetingDetection*`, Constitution 7 | `RecApp/MeetingDetection/*` | Local Always/Ask/Never per target, default Ask, 8-second countdown, explicit-only Remember, same Stop; no legal-policy/participant-consent start gate | Windows executable identity/publisher proof |
| Diagnostics | `DiagnosticRedactor.swift`, `RecordingEvidenceService.swift` | `RecApp/Diagnostics/*` | Metadata-only, bounded reason/counters, no raw/content/private paths | Windows endpoint fingerprint class |
| Native settings | `MeetingDetectionSettingsView.swift`, app lifecycle settings window | `RecApp/AppMain.cpp` | Prompt preference, permission recovery and account-settings handoff remain discoverable | WinUI settings window and `ms-settings:` links |
| Tray / minimized capture | `CaptureStatusItem.swift`, capture indicator | `RecApp/Shell/WindowsTray.*` + native strip/CompactOverlay | Active capture keeps a visible status and one-action Stop outside the cabinet | Windows tray may be hidden in overflow; a separate native indicator is required |
| Packaging/update | macOS installer/release gates | `Installer/*`, scripts | Signed package, dependency/runtime check, rollback/preservation evidence | MSIX/App Installer; no macOS notarization semantics |

## Route/state acceptance mapping

| Cabinet surface | Windows acceptance | Native state that must survive navigation failure |
|---|---|---|
| `/desktop/meetings` | Same meetings list and Russian copy as browser/macOS | capture state, indicator, local custody |
| `/desktop/meetings/{id}` | Same detail/review and playback contract | local package/upload truth |
| `/desktop/settings/...` | Same server settings; native-only permissions/settings opened through bounded intent | permission/readiness state |
| Auth recovery | Same server-mediated login/recovery flow | local queue and pending package |
| Share/deletion-report | Same server lifecycle truth | local purge acknowledgement and safe status |

## Evidence rule

Parity is claimed only when the matrix has a route/state/copy/accessibility
evidence entry for every in-scope macOS action. A native Windows screenshot or
synthetic test cannot prove server route parity by itself; browser/WebView route
comparison and native ownership evidence are separate gates.

## Проверка после master от 2026-09-06

Подробные результаты: [validation-2026-09-06.md](validation-2026-09-06.md).
Ни одна строка исходной матрицы не закрывается только по наличию кода.

| Область | Текущий факт | Остаётся |
|---|---|---|
| Кабинет / WinUI | Release x64 сборка от 2026-09-06 запущена в Parallels. Подтверждены вход, раскрытие/сворачивание панели, нативные настройки, их прокрутка и переход в аккаунт. После устранения пересоздания списка внутри обработчика выбора микрофона шесть UIA-переключений прошли без завершения процесса, выбор пережил перезапуск; исходный default восстановлен | Все остальные страницы, клавиатура/диктор, отказы сохранения, другие размеры и оборудование. Эти проверки не подтверждают приватность очереди или полный UI-паритет |
| WebView lifecycle | Native MSBuild и portable/native contract tests проходят; исправлены same-document source, downloads/dialogs, bounded OAuth continuation и account routes | Реальные цепочки OAuth, сбой браузерного процесса, экспорт и пользовательские диалоги |
| Захват / пакет | Worker fault завершает сохранение; verified prefix не становится нормальным upload; настоящий Windows AAC/decoder test PASS | WASAPI с реальным оборудованием, AEC/route/sleep/device fault и качество звука |
| Локальный список | Подключён существующий server-owned список и bounded native open/send/delete; метаданные проверяются вне потока UI | Проверка показанных строк и действий в авторизованном кабинете |
| Локальное удаление | Windows IFileOperation synthetic proof PASS; занятый/сетевой файл не удаляется; подтверждение native | Нажатия/отмена/смена состояния в настоящем UI |
| Очередь / аккаунт | [Контракт §7](contracts/windows-desktop-contract.md#7-local-custody-and-upload) прошёл независимый review требований. Реализован путь `/desktop/settings/spaces` → `/api/v1/auth/me` с одним снимком сессии, строгими типами/лимитами и отменой; portable/native тесты PASS. Сервер не менялся | Реальная проверка в кабинете: Record фиксирует владельца; Send требует совпадения; A→B/выход/запоздалые ответы/сбой сохранения не допускают чужую отправку. Неизвестный владелец назначается только после отдельного нативного подтверждения Send; известный неизменяем. T083 остаётся открыт |
| Автозапись | Отменённые правовые условия удалены. Индикатор подготавливается скрытым, готовность не зависит от главного окна. Слежение с starting, точная identity и пороги 2/15/600 секунд проверены синтетически. V2 сохраняет все три режима по ключу продукта при одобренном обновлении; точный EXE нельзя подменить общим ключом. Первая запись Teams ARM64 подтверждена native WinVerifyTrust; переносимые и Windows-тесты 20/20 | Остальные приложения/версии, настоящие положительные/отрицательные сценарии встреч в фоне. Подпись одного Teams и синтетические проверки не являются приёмкой автозаписи |
| Серверная очистка | Неиспользуемый постоянный `DesktopLocalPurgeService::purge(..., LocalPurgeProof)` и маркер `LocalRecordingPackage::registerLocalPurge` удалены; enum/маркер не были доказательством очистки. Исторический T040 не означает приёмку FR-022 | SAFE-BLOCKED в T083: достоверная авторизация конкретной установки, соответствие записи и фактическое доказательство до purge/ACK. Нативное удаление локальной копии через Корзину — отдельный сценарий |
| Пакет / выпуск | Выпуска не было | T070/T071, подпись, clean image, update, физический x64, полный release gate |

Здесь SAFE-BLOCKED означает незакрытое условие приёмки и запрет действия по
контракту, а не доказательство, что выполняемая сейчас версия уже реализовала
все проверки. Сборка, singleton-smoke и удаление неиспользуемого кода не
закрывают T083/T084 и не подтверждают защиту записи A при входе в B.

После удаления `CaptureHealthProjection.*` состояние и reason code поступают
из `WindowsCaptureSessionController` в `RecordingIndicator::publish`, затем
через `NativeCapture::indicator()` в нативный UI/tray `AppMain.cpp`.
Исторический T047 уточнён ссылками на этот рабочий путь; аппаратные ошибки,
доступность и полнота counters/bridge остаются предметом отдельной приёмки.

### Проверка 2026-09-07

Отправка: реализованы явный повтор после исчерпания, сетевое восстановление
проверки аккаунта, восстановление uploading после перезапуска, устойчивый
ключ замены истёкшей сессии и выбор следующей доступной записи. Независимый
анализ одобрен; portable/native CTest 20/20. Реальный authenticated upload
E2E не подтверждён.

Запись: после перехода worker на `GetNextPacketSize` и добавления bounded
dispatch queue настоящий сценарий `--run-unmuted` прошёл Record/Pause/Resume/
WebView reload/Stop до локального сохранения: `state=saved_local`,
`reason_code=none`, 960 обработанных и 960 записанных блоков. Повторный
сценарий с временным Mute микрофона также прошёл и восстановил состояние
микрофона. В обоих прогонах стартовый `DATA_DISCONTINUITY` был ограниченно
отброшен (`render=480`, `microphone=482` кадров), дальнейших clock fault не
зафиксировано.

Ограниченная очередь не позволяет WASAPI callback выполнять timeline/AEC3/writer;
переполнение и сбой worker завершают запись fail-closed. Stop дожидается уже
принятых пакетов. Проверки неизвестных флагов, timestamp error, ReleaseBuffer,
монотонности часов и повторного разрыва сохранены. Подробные metadata-only
результаты и актуальный SHA EXE находятся в
`validation-2026-09-06.md`.

Отдельный `--quiet` в Parallels ожидаемо завершился с
`endpoint_invalidated`, 0 блоков и 0 пакетов: одновременно не было пригодного
непрерывного системного источника и микрофона до startup deadline. Это не
принимается как успешный тихий старт и не заменяет отдельную проверку
отсутствующего render на реальном устройстве.

| Область | Актуальный статус | Остаётся |
|---|---|---|
| Manual Record/Pause/Resume/Stop | Проверено в реальном Windows-приложении через native UIA и внешний metadata-safe helper; `saved_local` | 60 минут, физический x64, качество/AEC, другие устройства |
| Native indicator и WebView reload | Индикатор виден; перезагрузка WebView не остановила нативную запись; Stop вернул idle | Полная матрица окон, клавиатура/диктор, разные размеры |
| Захват / пакет | bounded WASAPI dispatch, локальная финализация и `reason_code=none` подтверждены | SC-003 и аппаратная матрица |
| Локальный список / очередь | Контрактные и локальные проверки PASS | Настоящая серверная отправка и auth A→B/выход |
| WebView / кабинет | Сборка, запуск, навигация и панель подтверждены | Все страницы, OAuth, экспорт и диалоги |
| Автозапись | Синтетические правила и проверенный Teams identity сохранены | Настоящие фоновые встречи, остальные приложения и версии |
| Пакет / выпуск | Release x64 EXE собран, SHA зафиксирован | Подписанный MSIX, clean-image install/update/rollback, физический x64 |

T084 и техническая часть T085 закрыты соответствующим evidence. T063, T070,
T071, authenticated upload, SC-003 и внешний выпуск остаются открытыми.

### Проверка 2026-09-17 — сверка upload/auth/моста с master (T083)

База: рабочее дерево ветки на коммите `4b25d6cd2`. Эталон — master.
Корневая причина большинства расхождений одна: master-коммит `977310d1a`
«[F262] Согласовать удаление локальных и серверных записей (#6911)» изменил и
схему очереди, и мост удаления, и добавил серверные API жизненного цикла.
Windows-порт этого среза не содержит.

Сверка выполнена чтением исходников обеих платформ и серверных маршрутов;
Windows-тесты при этом не запускались, а `deleteSelection` в живом кабинете не
проверялся. Это анализ кода, а не приёмка.

#### Совпадает

| Объект | Основание |
| --- | --- |
| `local_recording_id` = каталог, `local_media_revision_id` = `<каталог>--initial` | `DesktopHttpTransport.cpp:615,661`; `DesktopUploadClient.swift:1155-1156` |
| Ключ идемпотентности сессии `desktop-upload:upload-session:<каталог>:<сессия>` | `DesktopApiClient.cpp:169-177`; `DesktopUploadClient.swift:1037-1039` |
| Тело `POST .../upload-sessions`, `PUT` частей с offset/sha, `POST .../finalize` | `DesktopHttpTransport.cpp:731-733`; `ingest/finalize.py:506` |
| Заголовки идентичности `X-Device-Id`/`X-Workspace-Id` | обе платформы в проде полагаются на привязку из сессии (`auth/dependencies.py:513-529`) |
| `X-Auth-Session` как основной путь | `AppMain.cpp:377,559` |
| Команды моста `request_app_quit` и `local_recording` | `WebViewBridge.cpp:173`; эффект совпадает с macOS, форма различается по FR-006 |
| Проверка устройства/владельца при отправке | `DesktopHttpTransport.cpp` `ownerBlockReason`; тесты `DesktopUploadRecoveryTests.cpp:61-68` |

#### Расходится

| Объект | Windows | macOS (master) | Риск |
| --- | --- | --- | --- |
| Удаление записей из кабинета | мост выставляется только вместе с исполнителем: выбор из кабинета разбирается воротами, сохраняется в реестре, отправляется проходом из трёх фаз и подтверждается странице по квитанциям | `GRAFRecordingDeletionBridgeVersion = 1`, `grafLocalRecording` | R1 закрыт 2026-09-18: разбор запроса, ворота, исполнитель и ответ. Исполнитель читает контекст уведомлений перед первой отправкой, поэтому старый сервер не получает ни одного изменения, а копия, о которой сервер не знает, удаляется локально без запроса |
| Страницы нативных настроек | оба обработчика отвечают кабинету тем же протоколом, что macOS; правила автозаписи читаются и пишутся через общее хранилище, страница уведомлений получает правду о платформе | `grafRecordingSettings`, `grafNotificationSettings` | R2 закрыт 2026-09-18: до этого обе страницы ждали ответ пятнадцать секунд и печатали «Не удалось загрузить настройки этого Mac» |
| `deleteSelection`, `deletionCompleted` | разбор `deleteSelection` с теми же правилами, что в macOS; ответ уходит странице из `finishDeletionSelection` и читается обратно из реестра | есть | R1 закрыт 2026-09-18: ответ собирается из фаз, записанных квитанциями, а не из отправленных запросов |
| Поля строки локальной записи | 15 полей: те же 13 плюс `localDeletionPending`, `deletionIsLocalOnly` | 16 полей: те же плюс `progressPercent` | R5 закрыт 2026-09-18 целиком: `progressPercent` считается так же, как в macOS — принятые сервером байты по дорожкам против веса дорожек локального пакета; неизмеримый прогресс не отправляется вовсе, а не показывается нулём. Время начала, префикс заголовка, длительность сессии и признак частичной записи выводятся из локального пакета. `deletionIsLocalOnly` повторяет правило исполнителя удаления (`hasServerIdentity`), поэтому диалог удаления обещает ровно то, что приложение сделает: «Эти записи ещё не отправлялись на сервер». `localDeletionPending` показывает строку как незавершённую очистку и не даёт нарисовать её записью, а прерванное удаление доводится до конца в обычном проходе восстановления — поэтому обещание «повторим автоматически» правда. `progressPercent` не передаётся: кабинет его не читает, в macOS процент стоит в тексте состояния |
| `meetingId` в строке | есть | есть, используется 53 раза | R5 закрыт 2026-09-17 |
| `GRAFLocalRecordings.update` — арность | 3 аргумента: строки, удаления в работе, признак скрытых записей | 3 аргумента | R5 закрыт 2026-09-18: панель «Удаления» и уведомление о скрытых записях появляются; `recoveryRequired` на Windows всегда `false`, потому что строки не скрываются, а показываются с причиной |
| Тело `POST /api/v1/meetings` | 10 полей; календарного контекста нет | 11 полей, включая `calendar_match_attempt_id` | R6 закрыт 2026-09-18: набор полей совпадает везде, кроме календаря, а интеграция с календарём исключена из объёма Feature 200 (`spec.md:296`) |
| Поля манифеста локального пакета | snake_case, сокращённый набор: `schema_version`, `canonical_mix_profile`, `source_kind`, `media_scribe_source_mode`, `capture_status`, `capture_reason_code`, `duration_ms`, время записи, `artifacts` | camelCase, 23 обязательных поля по `tests/macos/contract/local-recording-manifest.json` | Не блокирует: сервер тело манифеста не разбирает, только сверяет `sha256` дорожки `manifest` с объявленным (`ingest/finalize.py:505`) и проверяет роли дорожек и их параметры (`ingest/manifest.py:18`, `MIXED_RECORDING_V5_DESCRIPTOR_CONTRACT`). Пакет отправляется и принимается; расхождение проявится только у инструмента проверки контракта macOS. Отдельная задача — свести имена и состав полей |
| Определение финализации | `upload_session.status` и `meeting.status` (`ingested_pending_processing`, `degraded`) | то же | R3 закрыт 2026-09-17: потерянный ответ `finalize` больше не порождает вторую сессию для неизменяемой ревизии |
| Классификация конфликтов sync-state | `custody.retry_class`: `paused_until_user_action` → `needsAuth`, `paused_until_admin_action`/`not_retryable` → `blocked`, `terminal` → карантин | то же | R4 закрыт 2026-09-17: причина остановки видна владельцу, автоповторы не тратятся на то, что сервер уже назвал неретраибельным |
| Схема очереди | `desktop-upload-queue.v3`: 16 полей строки с отметкой времени, отметка времени документа, `deletion_operations` и `purge_acknowledgements` | `v3`, `updatedAt`, `deletionOperations` | R9 закрыт 2026-09-18 в части схемы: у каждой строки есть `updated_at_ms`, у документа — своя отметка, а запросы удаления живут в реестре и переживают перезапуск. Старые реестры `v2` по-прежнему читаются и обновляются при первой же записи: очередь хранит записи, которых больше нигде нет. Вместе с отпечатком сервера строка содержит 16 полей; конфликт и срок хранения остаются вне строки осознанно — см. следующую строку |
| Server truth, конфликт и срок хранения в реестре | отпечаток сервера сохраняется в строке (`media_revision_id`, `upload_session_id`, `server_status`, `processing_status`, `media_revision_status`); конфликт и срок хранения — нет | сохраняются целиком (`ServerTruthFingerprint`, `syncConflictState`, `RetentionDecision`) | R9 закрыт 2026-09-18 в части отпечатка: приложение больше не теряет при перезапуске то, что сервер сказал о строке. Конфликт и срок хранения переносятся иначе и остаются расхождением: конфликт приходит серверным классом повтора (`custody.retry_class`) и превращается в `blocked` или `needsAuth` с причиной, а локальные копии удаляются только по задаче сервера (`local-purge-tasks`), а не по сроку хранения. Семнадцать значений `syncConflictState` macOS в Windows не нужны: у порта своя, более узкая лестница состояний, и каждая достижимая причина названа |
| `GET /api/v1/auth/me` в пути отправки | один раз на сессию: оболочка подтверждает аккаунт и передаёт снимок в полёт | нет | R12 закрыт 2026-09-18: попытка больше не спрашивает сервер заново. Снимок не является полномочием сам по себе — он должен описывать настоящий аккаунт и совпадать с рабочим пространством, с которым едет, а смена токена сессии стирает его до начала любой отправки |
| Состояние удаления в кабинете | передаются строки, удаления в работе и признак скрытых записей: `GRAFLocalRecordings.update(rows, operations, recoveryRequired)`, фазы теми же именами, причины ожидания в словаре страницы | то же | R5 закрыт 2026-09-18: до этого кабинет получал только строки, поэтому панель «Удаления» и уведомление о скрытых записях не появлялись никогда. `recoveryRequired` на Windows всегда `false`: macOS скрывает строки с недоступным жизненным циклом, Windows показывает строку с её причиной |
| Серверные API жизненного цикла и purge | ворота протокола с живым вызывающим, область запроса, чтение жизненного цикла, задачи очистки: адресация, разбор, подтверждение и выполнение | `deletion-requests`, `local-purge-tasks`, `recordings/lifecycle`, `notification-context` | R8 закрыт 2026-09-18 целиком: `notification-context`, `recordings/lifecycle`, `deletion-requests` для обеих целей и `local-purge-tasks` (создание, список, подтверждение) собраны из точного контракта сервера, локальные отказы не доходят до сети. Задача сопоставляется со строками очереди только по встрече, которую вернул сервер, локальные копии удаляются тем же безопасным путём, что и подтверждённые пользователем, а подтверждается только доказанное: непроверяемый тип задачи отвечает `local_purge_unverified` и не трогает файлы. Доказанное удаление записывается в реестр до отправки ответа, потому что строка уходит вместе с копией и ответить второй раз из неё нельзя. `ack_url` из ответа не используется как адрес — путь всегда строится из проверенного идентификатора задачи (сознательно строже macOS) |
| `Retry-After` | читается на 429: пауза не даёт начать попытку раньше срока и не расходует лимит | читается (`DesktopUploadClient.swift:1454`, только 429, секунды или HTTP-дата, по умолчанию 60 с) | R10 закрыт 2026-09-18 в части `Retry-After`: сервер GRAF всегда присылает секунды, поэтому форма HTTP-даты не разбирается и даёт те же 60 с. Пауза живёт в памяти планировщика |
| `X-GRAF-Auth-Expires-At` | читается и ставится на cookie кабинета | читается (`DesktopCabinetSessionBridge.swift:178`) | R10 закрыт 2026-09-18: транспорт читает заголовок только из цифр, срок доходит до потока владельца и переписывает `__Host-twobrain_rec_owner_session` через `WebView2Host::extendAuthCookieExpiry`. Переписывание отклоняется, если токена нет, значение cookie уже другое или срок в прошлом — три отказа macOS `renewalExpiry`/`renewalCookies`. Срок нигде не хранится: его хранит cookie, как и в macOS. Проверено на живом сервере не было — нет входа в аккаунт |
| `X-Graf-Expected-Actor`/`Expected-Workspace` | отправляются для scoped-операций удаления; без обоих заголовков запрос не уходит | отправляются для scoped-операций | R8 закрыт 2026-09-18: идентификаторы проверяются до сериализации, а запрос без полной области не отправляется вовсе |
| `/desktop/deletions`, `/desktop/notifications`, `/notifications` | разрешены как точные маршруты | разрешены | R7 закрыт 2026-09-18: колокольчик уведомлений и страница удалений были мёртвыми ссылками. Дочерние пути остаются закрытыми |
| `/api/v1/notifications/{id}/read` | отклоняется как навигация | разрешено | Осознанно уже: кабинет обращается к этому адресу через `fetch` (`cabinet.js:8988`), а `fetch` не становится переходом документа, поэтому политика маршрутов его не видит. Расширять список до изменяющего состояние GET не нужно |
| Ссылка поддержки `mailto:` | отклоняется | открывается, если адрес прошёл проверку | R7 закрыт 2026-09-18 в узком виде: разрешён один адрес без темы, копий и вложений. macOS допускает ещё одну тему письма; шаблоны кабинета её не задают |
| `/desktop/settings/meeting-detection` | нативное окно с отменой навигации | страница кабинета | Расхождение осознанное и остаётся (R2, 2026-09-18): сервер такой страницы не отдаёт — в `cabinet/web_routes/settings.py` есть `/desktop/settings/recording`, `/notifications`, `/summaries`, `/workspace`, `/account`, но не `meeting-detection`. macOS разрешает адрес как документ кабинета и получил бы ответ об отсутствующей странице; в Windows для определения встреч есть работающая нативная страница, и показывать вместо неё пустующую было бы шагом назад |
| Тема оформления | окно следует теме кабинета: страница объявляет `data-theme` (`app_appearance`), принимаются ровно `light`, `dark`, `system`; у оболочки две палитры — тёмная и светлая — по значениям кабинета и macOS `DesktopDesignTokens` | обработчик `grafAppAppearance` выставляет `NSApplication.appearance`, цвета токенов динамические | R11 закрыт 2026-09-18: окно читает `data-theme` у страницы после рукопожатия (объявление приходит только с одноразовым значением и на старте опаздывает), задаёт `prefers-color-scheme` кабинета явно, а собственные кисти оболочки берёт из набора в двух темах. Проверено снимками в светлой и тёмной системных темах |
| Повторная сессия при истечении — ключ | новый | прежний; оба варианта сервер принимает | Расхождение допустимое: ключ идемпотентности выводится из цели и аккаунта, поэтому повтор после истечения сессии создаёт новую операцию только у Windows. Сервер принимает оба варианта, и ни один не приводит к двойному удалению: удаление подтверждается квитанцией, а не отправкой |

#### Порядок исправлений

1. **R3 и R9** — читать `meeting.status` и хранить server truth в реестре. Без
   этого Windows не отличает уже принятую запись от новой и создаёт лишнюю
   сессию, получая `409 media_revision_immutable` и восемь бесполезных повторов.
   R3 закрыт 2026-09-17, часть R9 (идентификатор встречи в реестре) закрыта
   вместе с R5.
2. **R4** — различать классы конфликтов вместо общего авто-повтора. Закрыт
   2026-09-17: очередь действует по `custody.retry_class`.
3. **R5** — передавать `meetingId` и остальные поля строки; это следствие R3/R9.
   Закрыт 2026-09-17 в части идентификатора встречи: он сохраняется в реестре,
   принимается один раз и передаётся кабинету, поэтому серверная строка замещает
   локальную. 2026-09-18 закрыта часть, выводимая из локального пакета: строка
   получает время начала, префикс заголовка, длительность сессии и признак
   частичной записи, поэтому кабинет показывает «Запись 18.09.2026, 14:05» вместо
   «На этом компьютере» и умеет сообщать «Сохранено X из Y». Остальные поля
   требуют R8 и R9.
4. **R8** — серверные вызовы жизненного цикла удаления; только после них имеет
   смысл R1. Закрыт 2026-09-18 в части ворот, области и чтения:
   `notification-context` читается до любой мутации — иначе клиент не отличит
   старый сервер, который игнорирует заголовки ожидаемого аккаунта, от нового, а
   нечитаемая квитанция пришла бы уже после удаления. Запросы `deletion-requests`
   для локальной записи и встречи и `recordings/lifecycle` собираются из точного
   контракта сервера: одна проверенная часть пути, литерал подтверждения,
   `extra="forbid"`. Непригодная область или пустая сессия не доходят до сети.
   Дополнено 2026-09-18: контракт задач очистки закрыт — адресация по встрече и
   по задаче, разбор одной задачи и списка со всеми типами и состояниями,
   подтверждение с кодом доказательства из словаря клиента. `ack_url` из ответа
   не используется как адрес: путь строится из проверенного идентификатора
   задачи. Остался поток целиком: сопоставить задачу со строками очереди, удалить
   локальные копии, подтвердить доказанное. R1 закрыт, поэтому такой поток стал
   возможен: сервер создаёт задачи очистки после пользовательского удаления.
   Дополнено 2026-09-18: R8 закрыт целиком — у потока появился вызывающий,
   поэтому `local-purge-tasks`, `purge_local_buffers`, `purge_acknowledgements`,
   `local_artifacts_deleted` и `local_purge_unverified` есть в установленном
   приложении. Задача сопоставляется со строками только по встрече от сервера,
   удаляются лишь те копии, которые сервер уже считает своими, а доказанное
   удаление записывается в реестр раньше ответа.
5. **R1** — мост удаления. Закрыт 2026-09-18 целиком: версия моста выставляется
   странице только вместе с исполнителем, потому что до появления настоящей
   серверной операции это было бы фиктивным подтверждением удаления, которое из
   Windows-порта уже удаляли. Исполнитель ведёт проход в три фазы (сохранить выбор
   на потоке владельца — отправить рабочим потоком без доступа к реестру —
   записать ответы на потоке владельца), читает контекст уведомлений до первой
   отправки и подтверждает странице только то, что названо квитанциями. Осталось
   непроверенным живым сценарием нажатие «Удалить» в кабинете под настоящей
   сессией аккаунта: сквозного входа в кабинет на стенде пока нет (то же
   ограничение записано для T082).
6. **R6** — тело `POST /api/v1/meetings`. Закрыт 2026-09-18: писатель пакета
   сохраняет время начала и окончания записи и смещение часового пояса, читатель
   пакета их проверяет, а транспорт отправляет `title`, `title_source`,
   `started_at`, `ended_at` и `recording_display_timezone_offset_minutes` в тех же
   условиях, что и macOS. Заголовок строится из местного времени начала записи
   (`Meeting - ГГГГ-ММ-ДД ЧЧ:ММ`), источник — `generic`, как у общего заголовка
   macOS. `calendar_match_attempt_id` не отправляется, потому что интеграция с
   календарём исключена из объёма Feature 200; macOS тоже не отправляет это поле,
   когда попытки сопоставления не было.
7. **R2, R10, R11, R12** — по убыванию пользы.
   `Retry-After` закрыт 2026-09-18: 429 больше не превращается в немедленный
   повтор, который расходовал попытки и зря беспокоил сервер. `X-GRAF-Auth-Expires-At`
   закрыт тогда же: срок сессии ставится на cookie кабинета, а место в реестре
   очереди не понадобилось — macOS тоже хранит этот срок только в cookie.
   R12 закрыт 2026-09-18: подтверждение аккаунта больше не повторяется на каждую
   попытку отправки. Оболочка подтверждает аккаунт для текущей сессии и передаёт
   этот снимок в полёт, а транспорт использует его вместо нового `/auth/me`.
   Проверка владельца перед отправкой сохранена, порядок «сначала пространство,
   потом `/auth/me`» остаётся для первой проверки.
   R7 закрыт 2026-09-18, кроме строки ниже: страницы уведомлений и удалений
   открываются, ссылка поддержки ведёт в почтовую программу. Осталось поведение
   `/desktop/settings/meeting-detection`: Windows отменяет переход и показывает
   нативное окно, macOS оставляет страницу кабинета. Решено 2026-09-18 вместе с
   R2: сервер эту страницу не отдаёт, поэтому у Windows остаётся своя работающая
   нативная страница определения встреч; расхождение записано строкой выше.

#### Тестовые пробелы

Пробелы, записанные здесь 2026-09-17, закрыты вместе с исправлениями. Покрытие на
2026-09-18:

| Область | Проверка |
| --- | --- |
| `deleteSelection`, версия моста | `RecordingDeletionBridgeTests.cpp` — 6 проверок, включая объявление `GRAFRecordingDeletionBridgeVersion = 1` только вместе с исполнителем |
| Квитанции, типы и состояния удаления | `DesktopDeletionProtocolTests.cpp` — 13 проверок |
| Реестр удалений, задачи очистки, строки кабинета | `DesktopDeletionLedgerTests.cpp` — 27 проверок |
| Мосты настроек | `NativeSettingsBridgeTests.cpp` — 9 проверок |
| `GRAFLocalRecordings.update(rows, operations, recoveryRequired)` | `DesktopDeletionLedgerTests.cpp`: фазы, причины ожидания и цель передаются странице |
| `X-GRAF-Auth-Expires-At` | `DesktopUploadRecoveryTests.cpp::testSessionDeadlineHeader` (разбор строки) и `WebView2HostLifecycleTests.cpp` (правило переписывания cookie) |
| Server truth в реестре | `DesktopUploadQueueV2Tests.cpp`: круг «запись → перезапуск → чтение» и отказ записывать непригодное значение |
| Очередь, повторы, пауза `Retry-After`, классы конфликтов | `DesktopUploadRecoveryTests.cpp` — 13 проверок |

Остаётся одна неточность фикстуры: в `testSyncDecoder` есть строка
`metadata_mismatch`, а сервер выдаёт `server_expected_metadata_mismatch`.
Проверка ожидает блокировку для любого неизвестного конфликта, поэтому на
результат это не влияет, но имя в фикстуре не совпадает с серверным словарём.

### Доступ к микрофону и причины отказа (2026-09-18, раунд 25)

| Область | macOS | Windows | Состояние |
| --- | --- | --- | --- |
| Экран разрешений | `DesktopPermissionOnboardingView`: «Чтобы вас было слышно», шаги микрофона и системного звука, «Открыть настройки», «Проверить еще раз», «Позже» | Панель «Запись»: неактивная «Начать запись», строка «Разрешите доступ к микрофону в настройках Windows», кнопка «Разрешить микрофон» и диалог «Разрешите запись звука» с «Открыть настройки», «Повторить проверку», «Позже» | Паритет по смыслу; проверено живьём 2026-09-18 |
| Определение запрета | `AVCaptureDevice.authorizationStatus` | Согласие читается по имени семейства пакетов в `ConsentStore\microphone`, затем `NonPackaged` | Закрыто 2026-09-18: раньше читался только `NonPackaged`, поэтому запрет не замечался |
| Текст отказа | Причина называется прямо | У каждой причины свой текст и следующий шаг (`RecordingOutcomeText`) | Закрыто 2026-09-18: раньше любая неудача сводилась к «проверьте устройство и свободное место» |
| Меню значка в области уведомлений | Нативное меню macOS в оформлении приложения | Пункты меню рисуются приложением кистями `ShellPalette`; тема приходит из того же решения, что и у окон | Закрыто 2026-09-18: раньше меню использовало системные цвета |
| Значок окна | Знак GRAF из ресурсов приложения | Знак GRAF из `Installer/Assets/Graf.ico` через `AppWindow::SetIcon`; ставится всем окнам общим вызовом `applyWindowIcon` | Закрыто 2026-09-18: раньше в заголовке был системный значок-заглушка, а окна настроек, автозаписи и полосы записи оставались без знака |
| Отказ одного источника | `markDegraded(source:)` помечает сессию ограниченной для любого источника; `degradedSourceRecovery` называет отказавший | Отказ любого источника переводит сессию в `degraded`, второй источник продолжает писать, причина едет в `CaptureFinalization::degradedReason` и называет источник (`microphoneEndpointUnavailable` или `renderEndpointUnavailable`) | Закрыто 2026-09-18: паритет по обоим источникам; запись обрывается только когда писать нечем |

### Живые проверки раунда 42 (2026-09-19)

Проверялось на установленном из MSIX приложении в машине «Windows 11», а не на
модульных заглушках.

| Область | Что смотрели | Результат |
| --- | --- | --- |
| Мост оформления кабинета (T091) | `%LOCALAPPDATA%\Packages\com.graf.desktop_jqvfym1syd7bp\LocalState\bridge.log` и `appearance.log` | Кабинет прислал настройку, оболочка её приняла: `accepted app_appearance` / `appearance system`, затем `received #F5F6F8 announced=system dark=0`. Светлая тема доходит до нативных окон тем же путём, что и раньше |
| Сохранение сессии и аккаунта (T088) | Приложение переустановлено из нового пакета и запущено заново | Кабинет открылся со встречами аккаунта без повторного входа: сессия и выбранный аккаунт пережили и перезапуск, и переустановку пакета |
| Инварианты удаления (T087) | `%LOCALAPPDATA%\GRAF\recordings`: файл очереди `desktop-upload-queue.v2` против каталогов записей | 12 записей в очереди и 12 каталогов, ровно один к одному; **осиротевших каталогов 0**; у каждой записи каталог на месте; реестр удалений (`deletion_operations`, `purge_acknowledgements`) присутствует и пуст; у всех записей `attempts=0` — наружу не ушло ничего |
| Причины остановки записи | Поля `status` и `safe_reason` в очереди | `status=5` с `capture_interrupted` у девяти записей и `status=4` без причины у двух — причина сохраняется рядом с записью, а не теряется |
| Промежуточные файлы пакета | `.canonical-mix.f32.tmp` внутри каталогов записей | Это штатный файл пакета (`Recording/V5LocalRecordingWriter.cpp`, `Recording/LocalRecordingPackage.cpp`), а не мусор: прерванная запись сохраняется вместе с ним |
| Три режима автозаписи (T082) | Окно настроек, список «Для всех приложений» | Живые варианты «Всегда», «Спрашивать», «Никогда»; ниже отдельные строки «Microsoft Teams» и «Yandex Telemost» со значением «Спрашивать» |
| Пользовательское время (T090) | Строки кабинета | Время записи показывается в местном времени машины (`19.09.2026, 01:03`), а не в времени сервера |

Что **не** проверено живьём и остаётся границей:

- само удаление записи из кабинета до конца, то есть путь «строка кабинета →
  задача очистки → локальное хранилище»: реестр удалений пуст, потому что ни
  одна запись ещё не удалялась; в этом раунде дойти до кнопки удаления в
  кабинете не удалось;
- выключение уведомлений (T089): переключатель в интерфейсе машины не найден,
  проверено только модульными тестами;
- живое срабатывание автозаписи (T082): в комнате был один участник, потока
  воспроизведения не возникло — подробности в `validation-2026-09-17.md`,
  раздел раунда 41.

### Мёртвая ветка моста (2026-09-19, раунд 43)

| Область | macOS | Windows до правки | Состояние |
| --- | --- | --- | --- |
| Команды страниц кабинета | Оболочка принимает `native_settings` и удаление записи; страницы настроек и удаление работают | Конверт пропускал только `request_app_quit`, `local_recording` и `app_appearance`; `native_settings` и `delete_selection` отбрасывались с `validation-rejected` | Исправлено: обе команды разрешены, разбор полей остался строгим в обработчиках; журнал моста показывает `accepted native_settings` |
| Страница настроек уведомлений | Показывает предпочтения и разрешение системы | Показывала «Не удалось загрузить настройки этого Мака» вместо ответа | Исправлено: страница показывает правду платформы («Windows: напоминания о встречах в приложении не поддерживаются»), переключатели неактивны |
| Текст страницы уведомлений | «На этом Mac», кнопка «Настройки macOS» | Тот же маковский текст на Windows | Открыто: копия серверной страницы общая с macOS, правка затронет обе платформы — нужно решение владельца |
| Удаление записи из кабинета | Работает через мост | Команда не доходила до приложения | Команда проходит; полный путь «строка → задача очистки → локальное хранилище» живьём не пройден |

## Итог паритета (2026-09-19)

Сводка по задачам, которые определяют паритет Windows-приложения с macOS. Под
каждой строкой — не обещание, а то, чем состояние подтверждено.

| Задача | Состояние | Чем подтверждено |
| --- | --- | --- |
| T070 Установка, обновление, откат | закрыта | живые сценарии в машине: `INSTALL_OK`, обновление поверх, отказ при занятых ресурсах `0x80073D02`, отказ понижения `0x80073D06`, удаление и откат |
| T080, T081 Автозапись и её пороги | закрыта | портируемая полоса и проверки автозаписи; живьём видны три режима и строки приложений |
| T086 Порог короткой записи | закрыта | живьём: остановка через четыре секунды пакета не оставила, как и требует правило F6796 |
| T063 Полный quickstart и ворота | открыта по одному пункту | `quickstart-run-2026-09-19.md`: разделы 2, 3, 5, 6, 8, 9 пройдены; `ci_local_result=pass mode=fast` на замороженном дереве. Открыт единственный пункт — аппаратные доказательства Windows x64 |
| T071 Физический x64 | отложена владельцем | решение владельца: гейт до появления физического компьютера x64 |
| T082 Живое срабатывание автозаписи | открыта | Teams и Телемост установлены и распознаны каталогом; в комнате нужен второй участник, иначе у приложения нет потока воспроизведения |
| T083 Сверка upload/auth/моста с master | открыта по живому входу | матрица расхождений и двенадцать исправлений записаны в разделе «Проверка 2026-09-17»; кабинет под входом открывается, сессия переживает переустановку |
| T087 Жизненный цикл удаления | открыта по локальному пути | отчёт об удалении в кабинете открывается (`active purge complete`, `purged` / `purge requested`); команда удаления проходит проверку моста (раунд 43). Не пройден путь до локального хранилища: новую запись в машине создать нельзя, а записи владельца не трогались |
| T088 Сессия и данные | открыта по живому входу | кабинет под входом открылся после переустановки пакета и перезапуска без повторного входа |
| T089 Управление уведомлениями | открыта | страница отвечает правдой платформы («Windows: напоминания о встречах в приложении не поддерживаются»), кнопка системных настроек скрыта, слова приведены к платформе; подтверждение глазами на живой машине осталось открытым |
| T090 Оформление и темы | открыта по живой проверке | три темы живьём вместе с нативной панелью и заголовком окна; «Системная» следует теме машины |
| T091 Мост настроек и загрузки | открыта по живой проверке | найдена и исправлена мёртвая ветка моста (`native_settings`, `delete_selection` отбрасывались); журнал пишет `accepted native_settings`; подтверждён путь восстановления WebView2 без перезапуска приложения |

### Что исправлено за эти круги и почему это важно

| Дефект | Суть | Где живёт исправление |
| --- | --- | --- |
| Мёртвая ветка моста | `native_settings` и `delete_selection` не были разрешены в конверте, поэтому страницы настроек кабинета не работали, а удаление не доходило до приложения | `WebViewBridge.cpp`, проверки в `WebViewBridgeEnvelopeTests.cpp` |
| Windows назывался «Маком» | общая страница настроек говорила «На этом Mac» и предлагала «Настройки macOS» | `NativeSettingsBridge.cpp` (правка в оболочке, сервер и macOS не тронуты) |
| Телемост не распознавался | в каталоге не было записи для Яндекс Телемоста | `VerifiedTargetRegistry.cpp`, проверки политики |

### Границы, которые нельзя закрыть в этой машине

- физический x64 с двумя реальными источниками звука (T071, отложено владельцем);
- второй участник во встрече для живого срабатывания автозаписи (T082);
- захват системного звука в текущем состоянии виртуальной машины: приложение
  честно отвечает «Не удалось сохранить запись. Системный звук недоступен»;
- буквальный прогон на образе Windows без среды разработки.

Ни одна из этих границ не является заявлением о готовности к выпуску: публикация
и развёртывание не выполнялись и не заявлялись.
