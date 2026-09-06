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

bool safeUrl(std::string_view url) noexcept {
    return std::none_of(url.begin(), url.end(), [](unsigned char c) { return c <= 0x20 || c == 0x7f || c == '\\'; });
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

bool uuid(std::string_view value) noexcept {
    if (value.size() != 36) return false;
    for (std::size_t i = 0; i < value.size(); ++i) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (value[i] != '-') return false;
        } else if (!((value[i] >= '0' && value[i] <= '9') ||
                     (value[i] >= 'a' && value[i] <= 'f') || (value[i] >= 'A' && value[i] <= 'F'))) return false;
    }
    return true;
}

bool sharedRoute(std::string_view path, std::string_view suffix, RouteKind& kind) noexcept {
    constexpr std::string_view detail = "/shared-meetings/";
    constexpr std::string_view download = "/api/v1/cabinet/shared-meetings/";
    constexpr std::string_view audio = "/downloads/audio";
    if (startsWith(path, detail)) {
        if (!uuid(path.substr(detail.size()))) return false;
        kind = RouteKind::meetingDetail;
    } else if (startsWith(path, download) &&
               path.size() == download.size() + 36 + audio.size() && path.substr(download.size() + 36) == audio) {
        if (!uuid(path.substr(download.size(), 36))) return false;
        kind = RouteKind::artifactDownload;
    } else return false;
    constexpr std::string_view query = "?workspace_id=";
    if (!startsWith(suffix, query) || !uuid(suffix.substr(query.size(), 36))) return false;
    const auto tail = suffix.substr(query.size() + 36);
    return tail.empty() || (kind == RouteKind::meetingDetail && (tail == "#outcomes" || tail == "#recording"));
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

bool accountRoute(std::string_view path) noexcept {
    if (path == "/desktop/account" || path == "/desktop/account/profile" ||
        path == "/desktop/account/security" || path == "/desktop/account/notifications" ||
        path == "/desktop/account/fair-use") return true;
    constexpr std::string_view prefix = "/desktop/account/fair-use/";
    if (!startsWith(path, prefix)) return false;
    const auto tail = path.substr(prefix.size());
    const auto slash = tail.find('/');
    return slash != std::string_view::npos && safePathComponent(tail.substr(0, slash)) &&
        tail.substr(slash) == "/appeal";
}

} // namespace

WebViewRoutePolicy::WebViewRoutePolicy(std::string trustedOrigin)
    : trustedOrigin_(std::move(trustedOrigin)) {
    while (!trustedOrigin_.empty() && trustedOrigin_.back() == '/') trustedOrigin_.pop_back();
}

AuthContinuation WebViewRoutePolicy::authContinuationForStart(std::string_view url) const noexcept {
    if (!safeUrl(url) || !startsWith(url, trustedOrigin_) || url.size() <= trustedOrigin_.size() ||
        url[trustedOrigin_.size()] != '/') return AuthContinuation::none;
    const auto path = url.substr(trustedOrigin_.size(), url.find_first_of("?#") == std::string_view::npos
        ? std::string_view::npos : url.find_first_of("?#") - trustedOrigin_.size());
    if (path == "/login/yandex/start" || path == "/desktop/settings/provider-links/yandex/start") return AuthContinuation::yandex;
    // VK ID also serves the visible Mail.ru and OK buttons via auth_provider.
    if (path == "/login/vk/start" || path == "/desktop/settings/provider-links/vk/start") return AuthContinuation::vk;
    return AuthContinuation::none;
}

bool WebViewRoutePolicy::isAllowedDownload(std::string_view url, std::string_view sourceUrl) const {
    const auto source = evaluate(sourceUrl);
    if (source.decision != RouteDecision::allow || source.kind == RouteKind::authRecovery ||
        source.kind == RouteKind::nativeSettings || source.kind == RouteKind::artifactDownload) return false;
    const auto target = evaluate(url);
    if (target.decision == RouteDecision::allow && target.kind == RouteKind::artifactDownload) return true;
    const auto prefix = "blob:" + trustedOrigin_ + "/";
    return startsWith(url, prefix) && uuid(url.substr(prefix.size()));
}

RouteEvaluation WebViewRoutePolicy::evaluate(std::string_view url, bool topLevel, AuthContinuation auth) const {
    RouteEvaluation result;
    result.normalizedUrl = std::string(url);
    if (!topLevel || url.empty() || !safeUrl(url) || startsWith(url, "file:") || startsWith(url, "data:") ||
        startsWith(url, "javascript:") || !startsWith(url, "https://")) {
        result.kind = RouteKind::denied;
        return result;
    }
    if (!startsWith(url, trustedOrigin_)) {
        if (auth != AuthContinuation::none) {
            const auto origin = url.substr(0, url.find_first_of("/?#", 8));
            // Exact reviewed origins, not suffix matching and not Mac's blanket
            // HTTPS continuation. Never bridge or project native state here.
            if ((auth == AuthContinuation::yandex &&
                 (origin == "https://oauth.yandex.ru" || origin == "https://passport.yandex.ru")) ||
                (auth == AuthContinuation::vk && origin == "https://id.vk.ru")) {
                result.decision = RouteDecision::allow;
                result.kind = RouteKind::authProvider;
            }
            return result;
        }
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
    if (sharedRoute(path, pathEnd == std::string_view::npos ? std::string_view{} : url.substr(pathEnd), result.kind)) {}
    else if (path == "/desktop/settings/meeting-detection") result.kind = RouteKind::nativeSettings;
    else if (path == "/offer" || path == "/terms" || path == "/privacy") {
        result.kind = RouteKind::external;
        result.decision = RouteDecision::openExternal;
        result.normalizedUrl = trustedOrigin_ + std::string(path);
        return result;
    }
    else if (path == "/desktop/meetings" || path == "/desktop/shared-with-me") result.kind = RouteKind::meetings;
    else if (meetingAction(path, "deletion-report")) result.kind = RouteKind::deletionReport;
    else if (meetingAction(path, "share")) result.kind = RouteKind::share;
    else if (exactOrChild(path, "/desktop/meetings")) result.kind = RouteKind::meetingDetail;
    else if (artifactDownload(path)) result.kind = RouteKind::artifactDownload;
    else if (accountRoute(path)) result.kind = RouteKind::settings;
    else if (authContinuationForStart(url) != AuthContinuation::none) result.kind = RouteKind::authRecovery;
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
