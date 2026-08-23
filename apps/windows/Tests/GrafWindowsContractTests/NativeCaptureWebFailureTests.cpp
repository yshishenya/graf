#include "../../RecApp/Web/WebView2Host.h"
#include "../../RecApp/Shell/RecordingIndicator.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    bool stopped = false;
    RecordingIndicator indicator([&] { stopped = true; });
    indicator.publish(SessionState::recording);
    WebView2Host web;
    web.setRuntimeState(WebRuntimeState::unavailable);
    assert(web.navigate("https://rec.2brain.pro/desktop/meetings").decision == RouteDecision::allow);
    assert(indicator.snapshot().visible && indicator.snapshot().stopAvailable);
    indicator.clickStop();
    assert(stopped);
    web.close(); web.reload();
    assert(indicator.snapshot().visible);
    return 0;
}
