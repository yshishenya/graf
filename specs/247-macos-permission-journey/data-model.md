# Состояние F247

DesktopPermissionOnboardingStatus: microphone/systemAudio, каждый CapturePermissionState; ready только оба granted. Следующий шаг — первый неготовый.
История attemptedMic/attemptedSystemAudio: Bool в UserDefaults текущего bundle, никогда не дает granted; unknown+attempted ведет в Settings. Удаление/переустановка ОС разрешений имеет приоритет над историей.
Presentation: AppStorage Bool permissionOnboarding.active для явно открытой незавершённой страницы; false только по Позже/Готово. Quit не очищает его. Help section state временный, settingsOpenFailed String?; refresh не меняет presentation. Права не сохраняются локально.
Concurrency: один request/probe в момент; bounded completion возвращает максимум один результат. После возврата preflight может только понизить результат при отзыве права.
Transitions: unknown→request→granted/unknown/denied; denied/attempted unknown→Settings→refresh; granted→functional stale→retry→granted; Settings open не меняет право; Done/Later→closed.
