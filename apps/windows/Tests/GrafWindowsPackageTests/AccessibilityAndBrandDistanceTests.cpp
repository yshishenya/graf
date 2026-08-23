#include "../../RecApp/Shell/AccessibilityState.h"
#include "../../RecApp/Shell/RecordingIndicator.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    const auto state = AccessibilityStateProvider::normalize({false, false, true, true, false, 200});
    assert(state.keyboardFocusVisible && state.screenReaderLabels && state.dpiScalePercent == 200);
    RecordingIndicator indicator;
    indicator.publish(SessionState::degraded, ReasonCode::clockDiscontinuity);
    assert(indicator.snapshot().visible && indicator.snapshot().stopAvailable);
    assert(indicator.snapshot().statusText == "Запись ограничена");
    return 0;
}
