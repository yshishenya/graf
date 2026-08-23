#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <array>
#include <cstddef>

namespace graf::windows {

struct ReadinessInputs {
    bool recordingPolicyAllowed = false;
    bool microphonePermissionGranted = false;
    bool microphoneEndpointReady = false;
    bool renderEndpointReady = false;
    bool formatNormalizationReady = false;
    bool aecReady = false;
    bool storageWritable = false;
    bool webViewRuntimeReady = false;
    bool aacEncoderReady = false;
};

struct ReadinessResult {
    bool recordingReady = false;
    bool webViewReady = false;
    std::array<ReasonCode, 8> blockers{};
    std::size_t blockerCount = 0;

    void addBlocker(ReasonCode reason) noexcept {
        if (blockerCount < blockers.size()) {
            blockers[blockerCount++] = reason;
        }
    }
};

class WindowsReadinessGate final {
public:
    [[nodiscard]] static ReadinessResult evaluate(const ReadinessInputs& inputs);
};

} // namespace graf::windows
