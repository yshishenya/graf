#pragma once

#include <string>
#include <string_view>

namespace graf::windows {

enum class RouteKind {
    meetings,
    meetingDetail,
    artifactDownload,
    settings,
    nativeSettings,
    authRecovery,
    authProvider,
    review,
    deletionReport,
    share,
    billing,
    external,
    denied,
};

enum class RouteDecision {
    allow,
    openExternal,
    deny,
};

struct RouteEvaluation {
    RouteDecision decision = RouteDecision::deny;
    RouteKind kind = RouteKind::denied;
    std::string normalizedUrl;
};

enum class AuthContinuation { none, yandex, vk };

class WebViewRoutePolicy final {
public:
    explicit WebViewRoutePolicy(std::string trustedOrigin = "https://rec.2brain.pro");

    // Host grants a short-lived, provider-specific continuation only after an
    // approved same-origin start route. It never grants bridge permissions.
    [[nodiscard]] RouteEvaluation evaluate(std::string_view url, bool topLevel = true,
        AuthContinuation auth = AuthContinuation::none) const;
    [[nodiscard]] AuthContinuation authContinuationForStart(std::string_view url) const noexcept;
    [[nodiscard]] bool isAllowedDownload(std::string_view url, std::string_view sourceUrl) const;
    [[nodiscard]] const std::string& trustedOrigin() const noexcept { return trustedOrigin_; }

private:
    std::string trustedOrigin_;
};

} // namespace graf::windows
