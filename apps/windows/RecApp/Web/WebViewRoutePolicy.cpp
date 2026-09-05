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

bool safePathComponent(std::string_view value) noexcept {
    if (value.empty()) return false;
    for (const auto character : value) {
        if (!((character >= 'a' && character <= 'z') || (character >= 'A' && character <= 'Z') ||
              (character >= '0' && character <= '9') || character == '_' || character == '-' || character == '.')) {
            return false;
        }
    }
    return true;
}

bool artifactDownload(std::string_view path) noexcept {
    constexpr std::string_view prefix = "/api/v1/cabinet/meetings/";
    if (!startsWith(path, prefix)) return false;
    const auto remainder = path.substr(prefix.size());
    const auto separator = remainder.find("/downloads/");
    if (separator == std::string_view::npos) return false;
    const auto meetingId = remainder.substr(0, separator);
    const auto artifact = remainder.substr(separator + 11);
    return safePathComponent(meetingId) &&
        (artifact == "audio" || artifact == "transcript" || artifact == "summary");
}

bool authCallback(std::string_view path) noexcept {
    constexpr std::string_view prefix = "/api/v1/auth/callback/";
    return startsWith(path, prefix) && safePathComponent(path.substr(prefix.size())) &&
        path.find('/', prefix.size()) == std::string_view::npos;
}

bool meetingAction(std::string_view path, std::string_view action) noexcept {
    constexpr std::string_view prefix = "/desktop/meetings/";
    if (!startsWith(path, prefix)) return false;
    const auto remainder = path.substr(prefix.size());
    const auto separator = remainder.find('/');
    if (separator == std::string_view::npos) return false;
    const auto meetingId = remainder.substr(0, separator);
    return safePathComponent(meetingId) && remainder.substr(separator + 1) == action;
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
    // A slash in a query or fragment is data, not a path separator.  Only a
    // literal path beginning at the trusted-origin boundary may be classified.
    const auto pathStart = url[boundary] == '/' ? boundary : std::string_view::npos;
    if (pathStart == std::string_view::npos) { result.kind = RouteKind::denied; return result; }
    const auto pathEnd = url.find_first_of("?#", pathStart);
    const auto path = url.substr(pathStart, pathEnd == std::string_view::npos ? url.size() - pathStart : pathEnd - pathStart);
    if (path.find("//") != std::string_view::npos || path.find("..") != std::string_view::npos) {
        result.kind = RouteKind::denied;
        return result;
    }
    if (path == "/desktop/meetings" || path == "/desktop/shared-with-me") result.kind = RouteKind::meetings;
    else if (meetingAction(path, "deletion-report")) result.kind = RouteKind::deletionReport;
    else if (meetingAction(path, "share")) result.kind = RouteKind::share;
    else if (exactOrChild(path, "/desktop/meetings")) result.kind = RouteKind::meetingDetail;
    else if (artifactDownload(path)) result.kind = RouteKind::artifactDownload;
    else if (exactOrChild(path, "/desktop/settings")) result.kind = RouteKind::settings;
    else if (exactOrChild(path, "/auth") || exactOrChild(path, "/login") ||
             exactOrChild(path, "/signup") || exactOrChild(path, "/sign-up") || authCallback(path)) {
        result.kind = RouteKind::authRecovery;
    }
    else if (exactOrChild(path, "/desktop/review")) result.kind = RouteKind::review;
    else if (exactOrChild(path, "/desktop/deletion-report")) result.kind = RouteKind::deletionReport;
    else if (exactOrChild(path, "/desktop/share")) result.kind = RouteKind::share;
    else if (exactOrChild(path, "/billing")) result.kind = RouteKind::billing;
    else if (exactOrChild(path, "/admin") || exactOrChild(path, "/referrals") ||
             exactOrChild(path, "/account/referrals")) {
        result.decision = RouteDecision::openExternal;
        result.kind = RouteKind::external;
        return result;
    }
    else { result.kind = RouteKind::denied; return result; }
    result.decision = RouteDecision::allow;
    return result;
}

} // namespace graf::windows
