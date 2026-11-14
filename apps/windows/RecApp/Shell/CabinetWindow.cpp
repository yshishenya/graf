#include "CabinetWindow.h"

namespace graf::windows {

RouteEvaluation CabinetWindow::openCabinet() {
    return open(webView_.routePolicy().trustedOrigin() + "/desktop/meetings");
}

RouteEvaluation CabinetWindow::open(std::string_view url) {
    return webView_.navigate(std::string(url));
}

} // namespace graf::windows
