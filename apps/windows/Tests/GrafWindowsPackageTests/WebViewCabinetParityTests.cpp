#include "../../RecApp/Shell/CabinetWindow.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    CabinetWindow cabinet; cabinet.webView().setRuntimeState(WebRuntimeState::ready);
    assert(cabinet.openCabinet().kind == RouteKind::meetings);
    assert(cabinet.open("https://rec.2brain.pro/desktop/settings").kind == RouteKind::settings);
    assert(cabinet.open("https://rec.2brain.pro/auth/recovery").kind == RouteKind::authRecovery);
    assert(cabinet.open("https://rec.2brain.pro/desktop/deletion-report/1").kind == RouteKind::deletionReport);
    // The cabinet's own footer links and the notification bell are ordinary
    // anchors, so the shell has to let them through to the same pages macOS
    // shows. The support link is a mailto: and leaves the window instead.
    assert(cabinet.open("https://rec.2brain.pro/desktop/notifications").kind == RouteKind::meetings);
    assert(cabinet.open("https://rec.2brain.pro/notifications").kind == RouteKind::meetings);
    assert(cabinet.open("https://rec.2brain.pro/desktop/deletions").kind == RouteKind::deletionReport);
    assert(cabinet.open("mailto:support@2brain.pro").kind == RouteKind::external);
    assert(cabinet.open("mailto:support@2brain.pro?subject=hello").kind == RouteKind::denied);
    return 0;
}
