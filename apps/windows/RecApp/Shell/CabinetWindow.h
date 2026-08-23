#pragma once

#include "../Web/WebView2Host.h"

#include <string_view>

namespace graf::windows {

class CabinetWindow final {
public:
    explicit CabinetWindow(WebView2Host host = WebView2Host());

    [[nodiscard]] RouteEvaluation openCabinet();
    [[nodiscard]] RouteEvaluation open(std::string_view url);
    [[nodiscard]] WebView2Host& webView() noexcept { return webView_; }

private:
    WebView2Host webView_;
};

} // namespace graf::windows
