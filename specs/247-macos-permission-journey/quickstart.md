# Проверка F247

Из корня: `swift test --package-path apps/macos --filter 'SystemAudioPermissionUXTests|AppControlAccessibilityTests|SystemAudioCaptureServiceTests|MeetingDetection'` затем `swift build --package-path apps/macos`.
`infra/scripts/ci-local.sh --fast` — обязательная локальная проверка выбранного high-risk lane; результаты отдельно от release-full.
Синтетический SwiftUI preview: initial/partial/denied/restricted/stale/ready, светлая/темная тема, ограниченная высота, фактическое имя GRAF Dev.
На отдельном тестовом Mac перед релизом: fresh TCC 14+/текущая версия; mic allow/deny; sys allow/deny; закрыть системный prompt; Settings grant/revoke; другая копия; MDM; проверка таймаута; VoiceOver + клавиатура. Не сбрасывать пользовательский TCC.
Проверить: запуск/активация не открывает prompt; Later сохраняет закрытое окно; ready не закрывает его; Record missing открывает setup без preparing; detector queued/ask не стартует в setup, после закрытия выполняет сохраненное правило с новым полным ask countdown; restart не прерывает capture/finalizing; никакое аудио не сохраняется в evidence.
