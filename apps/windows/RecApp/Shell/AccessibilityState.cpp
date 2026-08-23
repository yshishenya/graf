#include "AccessibilityState.h"

namespace graf::windows {

AccessibilityState AccessibilityStateProvider::normalize(AccessibilityState state) noexcept {
    if (state.dpiScalePercent < 100) state.dpiScalePercent = 100;
    if (state.dpiScalePercent > 400) state.dpiScalePercent = 400;
    state.keyboardFocusVisible = true;
    state.screenReaderLabels = true;
    return state;
}

} // namespace graf::windows
