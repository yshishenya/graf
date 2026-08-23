#include "WebView2Host.h"

namespace graf::windows {

WebView2Host::WebView2Host(WebViewRoutePolicy policy)
    : policy_(std::move(policy)) {}

RouteEvaluation WebView2Host::navigate(std::string url) {
    const auto evaluation = policy_.evaluate(url);
    if (runtimeState_ == WebRuntimeState::ready && evaluation.decision == RouteDecision::allow) {
        currentUrl_ = std::move(url);
    }
    if (navigationHandler_) navigationHandler_(evaluation);
    return evaluation;
}

void WebView2Host::reload() {
    if (!currentUrl_.empty()) (void)navigate(currentUrl_);
}

} // namespace graf::windows
