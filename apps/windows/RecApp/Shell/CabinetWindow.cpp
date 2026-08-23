#include "CabinetWindow.h"

namespace graf::windows {

CabinetWindow::CabinetWindow(WebView2Host host)
    : webView_(std::move(host)) {}

RouteEvaluation CabinetWindow::openCabinet() { return open("https://rec.2brain.pro/desktop/meetings"); }

RouteEvaluation CabinetWindow::open(std::string_view url) {
    return webView_.navigate(std::string(url));
}

} // namespace graf::windows
