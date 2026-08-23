#pragma once

#include "VerifiedTargetRegistry.h"

#include <string>

namespace graf::windows {

struct TargetObservation {
    VerifiedTargetIdentity identity;
    bool hasRenderStream = false;
    bool ordinaryMediaPlayback = false;
};

class WindowsTargetDetector final {
public:
    [[nodiscard]] static bool isPromptCandidate(const TargetObservation& observation,
                                                 const VerifiedTargetRegistry& registry);
};

} // namespace graf::windows
