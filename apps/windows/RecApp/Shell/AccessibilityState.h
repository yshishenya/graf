#pragma once

namespace graf::windows {

struct AccessibilityState {
    bool keyboardFocusVisible = true;
    bool screenReaderLabels = true;
    bool highContrast = false;
    bool largeText = false;
    bool reducedMotion = false;
    unsigned dpiScalePercent = 100;
};

class AccessibilityStateProvider final {
public:
    [[nodiscard]] static AccessibilityState normalize(AccessibilityState state) noexcept;
};

} // namespace graf::windows
