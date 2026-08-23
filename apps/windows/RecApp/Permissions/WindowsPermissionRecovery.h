#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <array>
#include <cstddef>
#include <string_view>

namespace graf::windows {

enum class RecoveryAction {
    none,
    openMicrophonePrivacy,
    openSoundSettings,
    choosePhysicalMicrophone,
    freeLocalStorage,
    installWebViewRuntime,
    installMediaFeaturePack,
    retryReadiness,
};

struct RecoveryOption {
    ReasonCode reason = ReasonCode::none;
    RecoveryAction action = RecoveryAction::none;
    std::string_view label;
};

class WindowsPermissionRecovery final {
public:
    [[nodiscard]] static RecoveryOption forReason(ReasonCode reason) noexcept;
    [[nodiscard]] static std::size_t collect(
        const ReasonCode* reasons,
        std::size_t count,
        std::array<RecoveryOption, 8>& output) noexcept;
};

} // namespace graf::windows
