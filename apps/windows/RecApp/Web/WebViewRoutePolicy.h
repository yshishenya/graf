#pragma once

#include <string>
#include <string_view>

namespace graf::windows {

enum class RouteKind {
    meetings,
    meetingDetail,
    artifactDownload,
    settings,
    authRecovery,
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

class WebViewRoutePolicy final {
public:
    explicit WebViewRoutePolicy(std::string trustedOrigin = "https://rec.2brain.pro");

    [[nodiscard]] RouteEvaluation evaluate(std::string_view url, bool topLevel = true) const;
    [[nodiscard]] const std::string& trustedOrigin() const noexcept { return trustedOrigin_; }

private:
    std::string trustedOrigin_;
};

} // namespace graf::windows
