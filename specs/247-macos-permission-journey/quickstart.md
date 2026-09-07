# Проверка F247

Из корня: `swift test --package-path apps/macos --filter 'SystemAudioPermissionUXTests|AppControlAccessibilityTests|SystemAudioCaptureServiceTests|MeetingDetection'` затем `swift build --package-path apps/macos`.
`infra/scripts/ci-local.sh --fast` — обязательная локальная проверка выбранного high-risk lane; результаты отдельно от release-full.
Синтетический SwiftUI preview: initial/partial/denied/restricted/stale/ready, светлая/темная тема, ограниченная высота, фактическое имя GRAF Dev.
На отдельном тестовом Mac перед релизом: fresh TCC 14+/текущая версия; mic allow/deny; sys allow/deny; закрыть системный prompt; Settings grant/revoke; другая копия; MDM; проверка таймаута; VoiceOver + клавиатура. Не сбрасывать пользовательский TCC.
Проверить: запуск/активация не открывает prompt; Later сохраняет закрытое окно; ready не закрывает его; Record missing открывает setup без preparing; detector queued/ask не стартует в setup, после закрытия выполняет сохраненное правило с новым полным ask countdown; restart не прерывает capture/finalizing; никакое аудио не сохраняется в evidence.

## Регрессия внешнего перезапуска (T007)

Собрать отдельный GRAF Local.app через `GRAF_LOCAL_APP_BUILD_DIR="$PWD/apps/macos/.build/permission-journey" apps/macos/Scripts/build-local-app.sh`. Затем `python3 apps/macos/Scripts/test-permission-restart.py 'apps/macos/.build/permission-journey/GRAF Local.app'`. Нужен macOS с графической сессией. Сценарий создаёт отдельную копию с уникальным bundle ID, явно открывает настройку, отправляет Quit Apple Event, проверяет штатную очистку без таймаута и повторяет после запуска. TCC не меняет; временные настройки удаляет.

На тестовом Mac дополнительно: нажать именно «Завершить и открыть снова» в System Settings после выдачи системного звука; проверить продолжение настройки и фактическую готовность. Проверить вариант отмены перезапуска/возврата в GRAF и обычный выход во время системного запроса. После Позже/Готово и перезапуска должна открыться основная страница. Проверка Apple Event доказывает внешний Quit приложения, но не является проверкой настоящей выдачи TCC или системной кнопки перезапуска.

## Пользовательская настройка (T008)

Запустить профильные тесты с `GRAF_PERMISSION_PREVIEW_DIR=<каталог>`: все снимки теперь рендерятся через настоящий NSHostingView, включая request-wait/checking, а footer остаётся вне ScrollView при 380 pt. Native UI: initial → раскрыть помощь → открыть Settings → первичный запрос всё ещё доступен; request pending → Настроить позже → Подготовить запись → то же ожидание без второго запроса. Quit во время ожидания выполняет штатную очистку. Не выдавать разрешение тестовой копии. Управление системным UserNotificationCenter недоступно инструменту CUA; это ограничение проверки, не свидетельство прохождения реального allow/deny.
