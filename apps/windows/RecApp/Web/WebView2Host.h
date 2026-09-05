#pragma once

#include "WebViewRoutePolicy.h"
#include "WebViewBridge.h"

#include <functional>
#include <string>
#include <string_view>
#include <utility>

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#endif

namespace graf::windows {

enum class WebRuntimeState {
    unavailable,
    initializing,
    ready,
    authRequired,
    closed,
};

class WebView2Host final {
public:
    using NavigationHandler = std::function<void(RouteEvaluation)>;
    using WebMessageHandler = std::function<void(WebViewBridgeEnvelope)>;
    using RuntimeHandler = std::function<void(WebRuntimeState)>;
    using QuitHandler = std::function<void()>;
    using AuthSessionHandler = std::function<void(std::string)>;

    explicit WebView2Host(WebViewRoutePolicy policy = WebViewRoutePolicy());
    ~WebView2Host();

    WebView2Host(const WebView2Host&) = delete;
    WebView2Host& operator=(const WebView2Host&) = delete;
    WebView2Host(WebView2Host&&) = delete;
    WebView2Host& operator=(WebView2Host&&) = delete;

    void setRuntimeState(WebRuntimeState state) noexcept;
    [[nodiscard]] WebRuntimeState runtimeState() const noexcept { return runtimeState_; }
    [[nodiscard]] bool genericHostObjectsAllowed() const noexcept { return false; }
    [[nodiscard]] RouteEvaluation navigate(std::string url);
    void close() noexcept;
    void reload();
    void setNavigationHandler(NavigationHandler handler) { navigationHandler_ = std::move(handler); }
    void setWebMessageHandler(WebMessageHandler handler) { webMessageHandler_ = std::move(handler); }
    void setRuntimeHandler(RuntimeHandler handler) { runtimeHandler_ = std::move(handler); }
    void setQuitHandler(QuitHandler handler) { quitHandler_ = std::move(handler); }
    void setAuthSessionHandler(AuthSessionHandler handler) { authSessionHandler_ = std::move(handler); }
    [[nodiscard]] static bool isAllowedQuitPayload(std::string_view payload) noexcept;

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
    void attach(winrt::Microsoft::UI::Xaml::Controls::WebView2 control);
#endif

    [[nodiscard]] const std::string& currentUrl() const noexcept { return currentUrl_; }
    [[nodiscard]] const WebViewRoutePolicy& routePolicy() const noexcept { return policy_; }

private:
    WebViewRoutePolicy policy_;
    NavigationHandler navigationHandler_;
    WebMessageHandler webMessageHandler_;
    RuntimeHandler runtimeHandler_;
    QuitHandler quitHandler_;
    AuthSessionHandler authSessionHandler_;
    WebViewBridge bridge_;
    WebRuntimeState runtimeState_ = WebRuntimeState::unavailable;
    std::string currentUrl_;
    std::function<void(std::string_view)> nativeNavigate_;
    std::function<void()> nativeReload_;

};

} // namespace graf::windows
