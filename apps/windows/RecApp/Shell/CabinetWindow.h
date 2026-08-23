#pragma once

#include "../Web/WebView2Host.h"

#ifdef _WIN32
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#endif

#include <string_view>

namespace graf::windows {

class CabinetWindow final {
public:
    explicit CabinetWindow(WebView2Host host = WebView2Host());

    [[nodiscard]] RouteEvaluation openCabinet();
    [[nodiscard]] RouteEvaluation open(std::string_view url);
    [[nodiscard]] WebView2Host& webView() noexcept { return webView_; }

#ifdef _WIN32
    void attach(Microsoft::UI::Xaml::Controls::WebView2 control) { webView_.attach(control); }
#endif

private:
    WebView2Host webView_;
};

} // namespace graf::windows
