#pragma once

#include "../Web/WebView2Host.h"

#include <string_view>

namespace graf::windows {

class CabinetWindow final {
public:
    CabinetWindow() = default;

    [[nodiscard]] RouteEvaluation openCabinet();
    [[nodiscard]] RouteEvaluation open(std::string_view url);
    [[nodiscard]] WebView2Host& webView() noexcept { return webView_; }

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
    void attach(winrt::Microsoft::UI::Xaml::Controls::WebView2 control) { webView_.attach(control); }
#endif

private:
    WebView2Host webView_;
};

} // namespace graf::windows
