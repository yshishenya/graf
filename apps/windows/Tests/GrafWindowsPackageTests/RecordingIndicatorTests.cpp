#include "../../RecApp/Shell/RecordingIndicator.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    RecordingIndicator indicator;
    indicator.publish(SessionState::degraded, ReasonCode::clockDiscontinuity);
    assert(indicator.snapshot().visible && indicator.snapshot().stopAvailable);
    assert(indicator.snapshot().statusText == "Запись ограничена");
    return 0;
}
