#pragma once

#include "../Contracts/WindowsDesktopContracts.h"
#include "../Shell/RecordingIndicator.h"

#include <string_view>

namespace graf::windows {

struct FaultRecoveryResult {
    bool trustedPrefixMayBeSaved = false;
    bool normalPackageAllowed = false;
    ReasonCode reason = ReasonCode::none;
    std::string_view userAction;
};

class CaptureFaultRecovery final {
public:
    [[nodiscard]] static FaultRecoveryResult handle(ReasonCode reason) noexcept;
    [[nodiscard]] static bool rawMicrophoneFallbackAllowed() noexcept { return false; }
};

} // namespace graf::windows
