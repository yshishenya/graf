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
    return 0;
}
