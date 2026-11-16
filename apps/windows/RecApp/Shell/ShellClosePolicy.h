#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

namespace graf::windows {

enum class ShellCloseAction { keepVisible, hide, wait, close };

// Only the shell owns windows and side effects. This decision never mutates a
// recording or replaces the capture controller's bounded finalization path.
[[nodiscard]] constexpr ShellCloseAction shellWindowCloseAction(
    SessionState state, bool trayAvailable, bool indicatorAvailable, bool exitRequested) noexcept {
    const bool active = isCaptureState(state);
    if (!exitRequested) {
        return trayAvailable && (!active || indicatorAvailable)
            ? ShellCloseAction::hide : ShellCloseAction::keepVisible;
    }
    return active ? ShellCloseAction::wait : ShellCloseAction::close;
}

} // namespace graf::windows
