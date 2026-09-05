#include "../../RecApp/Web/WebViewRoutePolicy.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    WebViewRoutePolicy policy;
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings").decision == RouteDecision::allow);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/shared-with-me").kind == RouteKind::meetings);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/123").kind == RouteKind::meetingDetail);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/123/share").kind == RouteKind::share);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/123/deletion-report").kind == RouteKind::deletionReport);
    assert(policy.evaluate("https://rec.2brain.pro/api/v1/cabinet/meetings/123/downloads/audio").kind == RouteKind::artifactDownload);
    assert(policy.evaluate("https://rec.2brain.pro/sign-up").kind == RouteKind::authRecovery);
    assert(policy.evaluate("https://rec.2brain.pro/api/v1/auth/callback/google").kind == RouteKind::authRecovery);
    assert(policy.evaluate("https://rec.2brain.pro/billing/plans").kind == RouteKind::billing);
    assert(policy.evaluate("https://rec.2brain.pro/admin").decision == RouteDecision::openExternal);
    assert(policy.evaluate("https://evil.example/desktop/meetings").decision == RouteDecision::openExternal);
    assert(policy.evaluate("file:///tmp/index.html").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/native/record").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/?next=/desktop/meetings").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/../settings").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/api/v1/cabinet/meetings/123/downloads/secret").decision == RouteDecision::deny);
    return 0;
}
