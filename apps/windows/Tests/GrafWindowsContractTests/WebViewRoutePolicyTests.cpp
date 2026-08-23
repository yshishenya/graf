#include "../../RecApp/Web/WebViewRoutePolicy.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    WebViewRoutePolicy policy;
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings").decision == RouteDecision::allow);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/123").kind == RouteKind::meetingDetail);
    assert(policy.evaluate("https://evil.example/desktop/meetings").decision == RouteDecision::openExternal);
    assert(policy.evaluate("file:///tmp/index.html").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/native/record").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/../settings").decision == RouteDecision::deny);
    return 0;
}
