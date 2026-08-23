#pragma once

#include "../MeetingDetection/AutomaticRecordingPolicy.h"

#include <string>

namespace graf::windows {

struct AutomaticPromptView {
    std::string title;
    std::string accessibleDescription;
    std::string primaryAction;
    std::string secondaryAction;
    std::string tertiaryAction;
    std::uint32_t secondsRemaining = 0;
};

class AutomaticRecordingPrompt final {
public:
    [[nodiscard]] static AutomaticPromptView view(const AutomaticRecordingPolicy& policy);
};

} // namespace graf::windows
