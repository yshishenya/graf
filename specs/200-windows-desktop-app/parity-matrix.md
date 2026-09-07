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
