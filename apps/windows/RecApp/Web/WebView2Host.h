#pragma once

#include "WebViewRoutePolicy.h"
#include "WebViewBridge.h"

#include <functional>
#include <string>

#ifdef _WIN32
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#endif

namespace graf::windows {

enum class WebRuntimeState {
    unavailable,
    initializing,
    ready,
    closed,
};

class WebView2Host final {
public:
    using NavigationHandler = std::function<void(RouteEvaluation)>;
    using WebMessageHandler = std::function<void(WebViewBridgeEnvelope)>;
    using RuntimeHandler = std::function<void(WebRuntimeState)>;

    explicit WebView2Host(WebViewRoutePolicy policy = WebViewRoutePolicy());

    void setRuntimeState(WebRuntimeState state) noexcept;
    [[nodiscard]] WebRuntimeState runtimeState() const noexcept { return runtimeState_; }
    [[nodiscard]] bool genericHostObjectsAllowed() const noexcept { return false; }
    [[nodiscard]] RouteEvaluation navigate(std::string url);
    void close() noexcept;
    void reload();
    void setNavigationHandler(NavigationHandler handler) { navigationHandler_ = std::move(handler); }
    void setWebMessageHandler(WebMessageHandler handler) { webMessageHandler_ = std::move(handler); }
    void setRuntimeHandler(RuntimeHandler handler) { runtimeHandler_ = std::move(handler); }

#ifdef _WIN32
    void attach(Microsoft::UI::Xaml::Controls::WebView2 control);
#endif

    [[nodiscard]] const std::string& currentUrl() const noexcept { return currentUrl_; }
    [[nodiscard]] const WebViewRoutePolicy& routePolicy() const noexcept { return policy_; }

private:
    WebViewRoutePolicy policy_;
    NavigationHandler navigationHandler_;
    WebMessageHandler webMessageHandler_;
    RuntimeHandler runtimeHandler_;
    WebViewBridge bridge_;
    WebRuntimeState runtimeState_ = WebRuntimeState::unavailable;
    std::string currentUrl_;
};

} // namespace graf::windows
