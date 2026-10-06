#include "AutomaticRecordingPrompt.h"

namespace graf::windows {

AutomaticPromptView AutomaticRecordingPrompt::view(const AutomaticRecordingPolicy& policy, DetectionClock::time_point now) {
    const auto remaining = policy.secondsRemaining(now);
    return {policy.state() == AutomaticPromptState::countdown, "Записать встречу?", policy.target().displayName,
        "Запись начнётся через " + std::to_string(remaining) + " с. Будет записан общий звук устройства и микрофон.",
        "Записать сейчас", "Не записывать", "Запомнить выбор", remaining};
}

} // namespace graf::windows
