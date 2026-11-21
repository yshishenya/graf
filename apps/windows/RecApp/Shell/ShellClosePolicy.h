#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

namespace graf::windows {

enum class ShellCloseIntent { window, quit };
enum class ShellCloseAction { keepVisible, hide, stopAndWait, wait, close };

// Only the shell owns windows and side effects. This decision never mutates a
// recording or replaces the capture controller's bounded finalization path.
[[nodiscard]] constexpr ShellCloseAction shellCloseAction(
    ShellCloseIntent intent, SessionState state, bool trayAvailable,
    bool indicatorAvailable, bool exitRequested) noexcept {
    const bool active = isCaptureState(state);
    if (intent == ShellCloseIntent::window && !exitRequested) {
        return trayAvailable && (!active || indicatorAvailable)
            ? ShellCloseAction::hide : ShellCloseAction::keepVisible;
    }
    if (!active) return ShellCloseAction::close;
    if (exitRequested || state == SessionState::stopping || state == SessionState::finalizing)
        return ShellCloseAction::wait;
    return ShellCloseAction::stopAndWait;
}

} // namespace graf::windows
