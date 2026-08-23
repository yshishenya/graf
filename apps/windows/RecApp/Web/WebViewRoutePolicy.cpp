#include "WebViewRoutePolicy.h"

#include <algorithm>

namespace graf::windows {
namespace {

bool startsWith(std::string_view value, std::string_view prefix) noexcept {
    return value.size() >= prefix.size() && value.substr(0, prefix.size()) == prefix;
}

bool exactOrChild(std::string_view path, std::string_view base) noexcept {
    return path == base || (startsWith(path, base) && path.size() > base.size() && path[base.size()] == '/');
}

} // namespace

WebViewRoutePolicy::WebViewRoutePolicy(std::string trustedOrigin)
    : trustedOrigin_(std::move(trustedOrigin)) {
    while (!trustedOrigin_.empty() && trustedOrigin_.back() == '/') trustedOrigin_.pop_back();
}

RouteEvaluation WebViewRoutePolicy::evaluate(std::string_view url, bool topLevel) const {
    RouteEvaluation result;
    result.normalizedUrl = std::string(url);
    if (!topLevel || url.empty() || startsWith(url, "file:") || startsWith(url, "data:") ||
        startsWith(url, "javascript:") || !startsWith(url, "https://")) {
        result.kind = RouteKind::denied;
        return result;
    }
    if (!startsWith(url, trustedOrigin_)) {
        result.decision = RouteDecision::openExternal;
        result.kind = RouteKind::external;
        return result;
    }
    const auto boundary = trustedOrigin_.size();
    if (url.size() <= boundary || (url[boundary] != '/' && url[boundary] != '?' && url[boundary] != '#')) {
        result.kind = RouteKind::denied;
        return result;
    }
    const auto pathStart = url[boundary] == '/' ? boundary : url.find('/', boundary);
    if (pathStart == std::string_view::npos) { result.kind = RouteKind::denied; return result; }
    const auto pathEnd = url.find_first_of("?#", pathStart);
    const auto path = url.substr(pathStart, pathEnd == std::string_view::npos ? url.size() - pathStart : pathEnd - pathStart);
    if (path.find("//") != std::string_view::npos || path.find("..") != std::string_view::npos) {
        result.kind = RouteKind::denied;
        return result;
    }
    if (path == "/desktop/meetings") result.kind = RouteKind::meetings;
    else if (exactOrChild(path, "/desktop/meetings")) result.kind = RouteKind::meetingDetail;
    else if (exactOrChild(path, "/desktop/settings")) result.kind = RouteKind::settings;
    else if (exactOrChild(path, "/auth")) result.kind = RouteKind::authRecovery;
    else if (exactOrChild(path, "/desktop/review")) result.kind = RouteKind::review;
    else if (exactOrChild(path, "/desktop/deletion-report")) result.kind = RouteKind::deletionReport;
    else if (exactOrChild(path, "/desktop/share")) result.kind = RouteKind::share;
    else { result.kind = RouteKind::denied; return result; }
    result.decision = RouteDecision::allow;
    return result;
}

} // namespace graf::windows
