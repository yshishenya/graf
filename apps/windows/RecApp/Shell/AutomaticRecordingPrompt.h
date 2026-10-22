#pragma once

#include "../MeetingDetection/AutomaticRecordingPolicy.h"

#include <string>

namespace graf::windows {

struct AutomaticPromptView {
    bool visible = false;
    std::string title;
    std::string applicationName;
    std::string accessibleDescription;
    std::string primaryAction;
    std::string secondaryAction;
    std::string rememberChoiceLabel;
    std::uint32_t secondsRemaining = 0;
};

class AutomaticRecordingPrompt final {
public:
    [[nodiscard]] static AutomaticPromptView view(const AutomaticRecordingPolicy& policy,
        DetectionClock::time_point now = DetectionClock::now());
};

} // namespace graf::windows
