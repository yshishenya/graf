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
    std::string navigation;
    web.setNavigationHandler([&](const RouteEvaluation& route) { navigation = route.normalizedUrl; });
    // No control is attached: observe the real reload request, not a fabricated
    // current source. Account/login requests must survive pending initialization.
    for (const auto state : {WebRuntimeState::unavailable, WebRuntimeState::initializing}) {
        web.setRuntimeState(state);
        for (const auto document : {"https://rec.2brain.pro/desktop/account/profile",
                                    "https://rec.2brain.pro/login?next=/desktop/meetings"}) {
            assert(web.navigate(document).decision == RouteDecision::allow);
            assert(web.currentUrl().empty());
            navigation.clear();
            web.reload();
            assert(navigation == document);
            for (const auto nonDocument : {"https://rec.2brain.pro/desktop/settings/meeting-detection",
                                           "https://rec.2brain.pro/api/v1/cabinet/meetings/123/downloads/audio",
                                           "https://oauth.yandex.ru/authorize", "https://evil.example/",
                                           "file:///tmp/private"}) {
                (void)web.navigate(nonDocument);
                navigation.clear();
                web.reload();
                assert(navigation == document);
                assert(web.currentUrl().empty());
            }
        }
    }
    assert(!web.canGoBack() && !web.canGoForward());
    web.back(); web.forward();
    assert(indicator.snapshot().visible && indicator.snapshot().stopAvailable);
    indicator.clickStop();
    assert(stopped);
    web.close();
    navigation.clear();
    web.reload();
    assert(navigation.empty());
    (void)web.navigate("https://rec.2brain.pro/desktop/settings");
    assert(web.currentUrl().empty());
    assert(indicator.snapshot().visible);
    return 0;
}
