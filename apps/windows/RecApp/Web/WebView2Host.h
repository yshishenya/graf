#pragma once

#include "WebViewRoutePolicy.h"

#include <functional>
#include <string>

namespace graf::windows {

enum class WebRuntimeState {
    unavailable,
    ready,
    closed,
};

class WebView2Host final {
public:
    using NavigationHandler = std::function<void(RouteEvaluation)>;

    explicit WebView2Host(WebViewRoutePolicy policy = WebViewRoutePolicy());

    void setRuntimeState(WebRuntimeState state) noexcept { runtimeState_ = state; }
    [[nodiscard]] WebRuntimeState runtimeState() const noexcept { return runtimeState_; }
    [[nodiscard]] bool genericHostObjectsAllowed() const noexcept { return false; }
    [[nodiscard]] RouteEvaluation navigate(std::string url);
    void close() noexcept { runtimeState_ = WebRuntimeState::closed; }
    void reload();
    void setNavigationHandler(NavigationHandler handler) { navigationHandler_ = std::move(handler); }

    [[nodiscard]] const std::string& currentUrl() const noexcept { return currentUrl_; }
    [[nodiscard]] const WebViewRoutePolicy& routePolicy() const noexcept { return policy_; }

private:
    WebViewRoutePolicy policy_;
    NavigationHandler navigationHandler_;
    WebRuntimeState runtimeState_ = WebRuntimeState::unavailable;
    std::string currentUrl_;
};

} // namespace graf::windows
