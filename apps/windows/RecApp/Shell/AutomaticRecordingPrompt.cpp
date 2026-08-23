#include "AutomaticRecordingPrompt.h"

namespace graf::windows {

AutomaticPromptView AutomaticRecordingPrompt::view(const AutomaticRecordingPolicy& policy) {
    const auto remaining = policy.state() == AutomaticPromptState::countdown ? 8U : 0U;
    return {"Записать встречу?", "Автоматическая запись для подтверждённого приложения. Доступны клавиатурные действия.",
            "Записать сейчас", "Пропустить", "Всегда писать это приложение", remaining};
}

} // namespace graf::windows
