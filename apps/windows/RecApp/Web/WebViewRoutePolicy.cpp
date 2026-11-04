#include "WebViewRoutePolicy.h"

#include <algorithm>
#include <array>
#include <utility>

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

bool hasScheme(std::string_view url, std::string_view scheme) noexcept {
    if (url.size() < scheme.size()) return false;
    for (std::size_t i = 0; i < scheme.size(); ++i) {
        const auto character = static_cast<unsigned char>(url[i]);
        const auto expected = static_cast<unsigned char>(scheme[i]);
        const auto lower = character >= 'A' && character <= 'Z' ? static_cast<unsigned char>(character + 32) : character;
        if (lower != expected) return false;
    }
    return true;
}

struct HttpsUrl {
    std::string origin;
    std::string host;
    std::string_view path;
    std::string_view suffix;
};

std::optional<HttpsUrl> parseHttps(std::string_view url) {
    if (!safeUrl(url) || !hasScheme(url, "https://")) return std::nullopt;
    const auto end = url.find_first_of("/?#", 8);
    auto authority = url.substr(8, end == std::string_view::npos ? end : end - 8);
    if (authority.empty() || authority.find('@') != std::string_view::npos) return std::nullopt;
    auto host = authority;
    std::string_view port;
    const auto colon = authority.rfind(':');
    if (colon != std::string_view::npos) {
        host = authority.substr(0, colon);
        port = authority.substr(colon + 1);
        if (port.empty()) return std::nullopt;
        unsigned number = 0;
        for (const char c : port) {
            if (c < '0' || c > '9' || number > 6553) return std::nullopt;
            number = number * 10 + static_cast<unsigned>(c - '0');
        }
        if (number == 0 || number > 65535) return std::nullopt;
    }
    if (host.empty() || host.front() == '.' || host.find("..") != std::string_view::npos) return std::nullopt;
    for (const char c : host) {
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '.')) return std::nullopt;
    }
    HttpsUrl result;
    result.host = std::string(host);
    std::transform(result.host.begin(), result.host.end(), result.host.begin(), [](unsigned char c) {
        return c >= 'A' && c <= 'Z' ? static_cast<char>(c + 32) : static_cast<char>(c);
    });
    result.origin = "https://" + result.host;
    if (!port.empty()) {
        const auto number = std::stoul(std::string(port));
        if (number != 443) result.origin += ":" + std::to_string(number);
    }
    const auto pathEnd = end == std::string_view::npos ? end : url.find_first_of("?#", end);
    result.path = end != std::string_view::npos && url[end] == '/'
        ? url.substr(end, pathEnd == std::string_view::npos ? pathEnd : pathEnd - end) : std::string_view("/");
    result.suffix = pathEnd == std::string_view::npos ? std::string_view{} : url.substr(pathEnd);
    return result;
}

bool billingRoute(std::string_view path) {
    for (const auto allowed : {"/billing", "/billing/plans", "/billing/usage", "/billing/subscription",
        "/billing/payment-method", "/billing/checkout", "/billing/history", "/billing/discounts", "/billing/storage",
        "/billing/checkout/preview", "/billing/checkout/start", "/billing/discounts/apply", "/billing/discounts/remove",
        "/billing/storage/preview", "/billing/storage/cancel-selection", "/billing/subscription/early-preview",
        "/billing/purchases/confirm",
        "/billing/trial/activate", "/billing/payment-method/delete", "/billing/subscription/cancel",
        "/billing/subscription/resume", "/billing/checkout/return"}) if (path == allowed) return true;
    constexpr std::string_view status = "/billing/checkout/status/";
    if (startsWith(path, status)) {
        const auto tail = path.substr(status.size());
        const auto slash = tail.find('/');
        if (!safePathComponent(tail.substr(0, slash))) return false;
        return slash == std::string_view::npos || tail.substr(slash) == "/refresh" || tail.substr(slash) == "/continue";
    }
    constexpr std::string_view invoice = "/billing/invoices/";
    return startsWith(path, invoice) && safePathComponent(path.substr(invoice.size()));
}

bool emailLinkForm(std::string_view path) {
    return path == "/desktop/settings/account/email-link/start" || path == "/desktop/settings/account/email-link/verify";
}

std::string encodePath(std::string_view path) {
    std::string result;
    constexpr char hex[] = "0123456789ABCDEF";
    for (unsigned char c : path) {
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
            c == '-' || c == '_' || c == '.' || c == '~') result += static_cast<char>(c);
        else { result += '%'; result += hex[c >> 4]; result += hex[c & 15]; }
    }
    return result;
}

// The cabinet links to support with a plain mailto address.  Only that shape
// leaves the window: no additional recipients, no copied address, no fragment
// and no prefilled subject, because a page could otherwise compose a message on
// the user's behalf.  Mac admits one optional subject; GRAF's own templates
// never send one, so the narrower rule costs nothing.
std::string supportMailtoUrl(std::string_view url) {
    constexpr std::string_view scheme = "mailto:";
    if (!hasScheme(url, scheme)) return {};
    const auto address = url.substr(scheme.size());
    if (address.empty() || address.size() > 254) return {};
    for (const auto character : address) {
        const auto byte = static_cast<unsigned char>(character);
        if (byte <= 0x20 || byte == 0x7f || character == '#' || character == '?' || character == ',' ||
            character == ';' || character == '\\') return {};
    }
    const auto at = address.find('@');
    if (at == std::string_view::npos || at == 0 || at + 1 >= address.size()) return {};
    if (address.find('@', at + 1) != std::string_view::npos) return {};
    return "mailto:" + std::string(address);
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

bool sharedPosition(std::string_view value) noexcept {
    if (value.empty() || value.size() > 8) return false;
    unsigned number = 0;
    for (const auto c : value) {
        if (c < '0' || c > '9') return false;
        number = number * 10 + static_cast<unsigned>(c - '0');
    }
    return number <= 86400000;
}

// Every allowed query field is ASCII. Decode once, then validate its exact
// grammar; a decoded '%' or '+' cannot acquire a second interpretation.
std::optional<std::string> sharedField(std::string_view value) {
    std::string result;
    for (std::size_t i = 0; i < value.size(); ++i) {
        unsigned char c = static_cast<unsigned char>(value[i]);
        if (c == '%') {
            const auto hex = [](char digit) {
                if (digit >= '0' && digit <= '9') return digit - '0';
                if (digit >= 'a' && digit <= 'f') return digit - 'a' + 10;
                if (digit >= 'A' && digit <= 'F') return digit - 'A' + 10;
                return -1;
            };
            if (i + 2 >= value.size()) return std::nullopt;
            const int high = hex(value[i + 1]), low = hex(value[i + 2]);
            if (high < 0 || low < 0) return std::nullopt;
            c = static_cast<unsigned char>(high * 16 + low);
            i += 2;
        }
        if (c <= 0x20 || c >= 0x7f) return std::nullopt;
        result += static_cast<char>(c);
    }
    return result.empty() ? std::nullopt : std::optional<std::string>(std::move(result));
}

template<std::size_t Count>
bool sharedValues(std::string_view query, const std::array<std::string_view, Count>& keys,
    std::array<std::string, Count>& values) {
    for (std::size_t start = 0; start <= query.size();) {
        const auto end = query.find('&', start);
        const auto item = query.substr(start, end == query.npos ? query.npos : end - start);
        const auto equal = item.find('=');
        if (equal == item.npos) return false;
        const auto key = sharedField(item.substr(0, equal));
        const auto value = sharedField(item.substr(equal + 1));
        if (!key || !value) return false;
        const auto found = std::find(keys.begin(), keys.end(), *key);
        if (found == keys.end()) return false;
        const auto index = static_cast<std::size_t>(found - keys.begin());
        if (!values[index].empty()) return false;
        values[index] = *value;
        if (end == query.npos) break;
        start = end + 1;
    }
    return true;
}

bool sharedToken(std::string_view token) noexcept {
    return token.size() >= 32 && token.size() <= 128 && std::all_of(token.begin(), token.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '-' || c == '_';
    });
}

bool sharedVersion(std::string_view value) noexcept {
    return value.size() == 24 && std::all_of(value.begin(), value.end(), [](char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
    });
}

enum class SharedUse { reader, media, continuation, download };

bool sharedQuery(std::string_view suffix, SharedUse use, bool versionRequired) {
    if (suffix.empty() || suffix.front() != '?') return false;
    const auto hash = suffix.find('#');
    const auto query = suffix.substr(1, hash == suffix.npos ? suffix.npos : hash - 1);
    if (hash != suffix.npos) {
        if (use != SharedUse::reader) return false;
        const auto fragment = suffix.substr(hash + 1);
        constexpr std::string_view position = "recording?position_ms=";
        if (fragment != "outcomes" && fragment != "recording" &&
            !(startsWith(fragment, position) && sharedPosition(fragment.substr(position.size())))) return false;
    }
    constexpr std::array<std::string_view, 5> keys = {"workspace_id", "media_version", "action", "tab", "position_ms"};
    std::array<std::string, 5> values;
    if (!sharedValues(query, keys, values) ||
        (use != SharedUse::continuation && (!values[2].empty() || !values[3].empty() || !values[4].empty())) ||
        (use == SharedUse::download && !values[1].empty())) return false;
    if (!uuid(values[0])) return false;
    const auto& version = values[1];
    if ((!version.empty() && !sharedVersion(version)) || (versionRequired && version.empty())) return false;
    return (values[2].empty() || values[2] == "sign-in" || values[2] == "sign-up") &&
        (values[3].empty() || values[3] == "outcomes" || values[3] == "recording") &&
        (values[4].empty() || (values[3] == "recording" && sharedPosition(values[4])));
}

bool sharedMeetingPath(std::string_view path) noexcept {
    return exactOrChild(path, "/shared-meetings") || exactOrChild(path, "/api/v1/cabinet/shared-meetings") ||
        exactOrChild(path, "/api/v1/cabinet/public-shares") || exactOrChild(path, "/shared-meeting/continue");
}

// Decode/normalize only to recognize aliases of reserved shared paths. Never
// navigate to this result: noncanonical input is denied before the frame rule.
bool noncanonicalSharedPath(std::string_view path) {
    if (path.find('%') == path.npos && path.find("/.") == path.npos && path.find("//") == path.npos) return false;
    std::string decoded;
    for (std::size_t i = 0; i < path.size(); ++i) {
        if (path[i] == '%' && i + 2 < path.size()) {
            if (const auto byte = sharedField(path.substr(i, 3))) {
                decoded += byte->front() == '\\' ? '/' : byte->front();
                i += 2;
                continue;
            }
        }
        decoded += path[i];
    }
    std::string canonical;
    for (std::size_t start = 0; start <= decoded.size();) {
        const auto end = decoded.find('/', start);
        const auto part = std::string_view(decoded).substr(start, end == decoded.npos ? decoded.npos : end - start);
        if (part == "..") {
            if (!canonical.empty()) canonical.resize(canonical.rfind('/'));
        } else if (!part.empty() && part != ".") {
            canonical += '/';
            canonical += part;
        }
        if (end == decoded.npos) break;
        start = end + 1;
    }
    return (path != decoded || path != canonical) &&
        (sharedMeetingPath(decoded) || sharedMeetingPath(canonical));
}

bool sharedRoute(std::string_view path, std::string_view suffix, RouteKind& kind) {
    constexpr std::string_view detail = "/shared-meetings/";
    constexpr std::string_view addressed = "/api/v1/cabinet/shared-meetings/";
    constexpr std::string_view publicShare = "/api/v1/cabinet/public-shares/";
    if (path == "/shared-meeting/continue") {
        kind = RouteKind::publicReader;
        return suffix.empty();
    }
    SharedUse use = SharedUse::reader;
    bool versionRequired = false;
    if (startsWith(path, detail)) {
        if (!uuid(path.substr(detail.size()))) return false;
        kind = RouteKind::meetingDetail;
    } else if (startsWith(path, addressed)) {
        const auto tail = path.substr(addressed.size());
        if (tail.size() < 36 || !uuid(tail.substr(0, 36))) return false;
        if (tail.substr(36) == "/downloads/audio") {
            kind = RouteKind::artifactDownload;
            use = SharedUse::download;
        } else if (tail.substr(36) == "/playback") {
            kind = RouteKind::sharedMedia;
            use = SharedUse::media;
        } else return false;
    } else if (startsWith(path, publicShare)) {
        const auto tail = path.substr(publicShare.size());
        const auto slash = tail.find('/');
        const auto token = tail.substr(0, slash);
        if (!sharedToken(token)) return false;
        kind = RouteKind::publicReader;
        if (slash != tail.npos) {
            if (tail.substr(slash) == "/playback") {
                kind = RouteKind::sharedMedia; use = SharedUse::media; versionRequired = true;
            }
            else if (tail.substr(slash) == "/continue") use = SharedUse::continuation;
            else return false;
        }
    } else return false;
    return sharedQuery(suffix, use, versionRequired);
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
    if (const auto parsed = parseHttps(trustedOrigin_)) trustedOrigin_ = parsed->origin;
}

std::optional<std::string> WebViewRoutePolicy::sharedMeetingRoute(std::string_view activation) {
    constexpr std::string_view prefix = "grafrec://";
    if (activation.size() > 16384 || !startsWith(activation, prefix) || !safeUrl(activation) ||
        activation.find('#') != activation.npos) return std::nullopt;
    const auto query = activation.find('?', prefix.size());
    if (query == activation.npos) return std::nullopt;
    // URLComponents.host decodes once; compare the entire authority so that
    // userinfo, port and any nonempty path cannot be hidden by percent encoding.
    const auto host = sharedField(activation.substr(prefix.size(), query - prefix.size()));
    if (!host || *host != "shared-meeting") return std::nullopt;
    constexpr std::array<std::string_view, 7> keys = {
        "v", "workspace_id", "meeting_id", "share_token", "tab", "position_ms", "media_version"};
    std::array<std::string, 7> values;
    if (!sharedValues(activation.substr(query + 1), keys, values) || values[0] != "1" || !uuid(values[1]) ||
        (values[2].empty() == values[3].empty()) || (!values[2].empty() && !uuid(values[2])) ||
        (!values[3].empty() && !sharedToken(values[3])) || (values[4] != "outcomes" && values[4] != "recording") ||
        (!values[5].empty() && (values[4] != "recording" || !sharedPosition(values[5]))) ||
        (!values[6].empty() && !sharedVersion(values[6]))) return std::nullopt;
    for (const auto index : {1, 2}) {
        std::transform(values[index].begin(), values[index].end(), values[index].begin(), [](char c) {
            return c >= 'A' && c <= 'F' ? static_cast<char>(c + 32) : c;
        });
    }
    auto route = values[3].empty() ? "/shared-meetings/" + values[2] : "/api/v1/cabinet/public-shares/" + values[3];
    route += "?workspace_id=" + values[1];
    if (!values[6].empty()) route += "&media_version=" + values[6];
    route += '#' + values[4];
    if (!values[5].empty()) {
        const auto first = values[5].find_first_not_of('0');
        route += "?position_ms=" + (first == values[5].npos ? std::string("0") : values[5].substr(first));
    }
    return route;
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
        source.kind == RouteKind::nativeSettings || source.kind == RouteKind::artifactDownload ||
        source.kind == RouteKind::publicReader || source.kind == RouteKind::sharedMedia) return false;
    const auto target = evaluate(url);
    if (target.decision == RouteDecision::allow && target.kind == RouteKind::artifactDownload) return true;
    const auto prefix = "blob:" + trustedOrigin_ + "/";
    return startsWith(url, prefix) && uuid(url.substr(prefix.size()));
}

RouteEvaluation WebViewRoutePolicy::evaluate(std::string_view url, bool topLevel, AuthContinuation auth, bool payment) const {
    RouteEvaluation result;
    result.normalizedUrl = std::string(url);
    if (hasScheme(url, "mailto:")) {
        const auto sanitized = topLevel ? supportMailtoUrl(url) : std::string{};
        if (sanitized.empty()) { result.kind = RouteKind::denied; return result; }
        result.decision = RouteDecision::openExternal;
        result.kind = RouteKind::external;
        result.normalizedUrl = std::move(sanitized);
        return result;
    }
    const auto parsed = parseHttps(url);
    if (!parsed) {
        result.kind = RouteKind::denied;
        return result;
    }
    if (parsed->origin == trustedOrigin_ && noncanonicalSharedPath(parsed->path)) return result;
    // Shared reader/media paths retain their strict grammar in frames too.
    if (!topLevel && (parsed->origin != trustedOrigin_ || !sharedMeetingPath(parsed->path))) {
        if (parsed->origin == trustedOrigin_ || payment) {
            result.decision = RouteDecision::allow;
            result.kind = RouteKind::frame;
        }
        return result;
    }
    if (parsed->origin != trustedOrigin_) {
        if (payment) {
            result.decision = RouteDecision::allow;
            result.kind = RouteKind::paymentProvider;
            return result;
        }
        if (auth != AuthContinuation::none) {
            const auto& origin = parsed->origin;
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
    const auto path = parsed->path;
    if (sharedMeetingPath(path) && url.size() > 16384) return result;
    if (path.find("//") != std::string_view::npos || path.find("..") != std::string_view::npos ||
        path.find('%') != std::string_view::npos) {
        result.kind = RouteKind::denied;
        return result;
    }
    if (sharedRoute(path, parsed->suffix, result.kind)) {}
    else if (path == "/desktop/settings/meeting-detection") result.kind = RouteKind::nativeSettings;
    else if (path == "/offer" || path == "/terms" || path == "/privacy") {
        result.kind = RouteKind::external;
        result.decision = RouteDecision::openExternal;
        result.normalizedUrl = trustedOrigin_ + std::string(path);
        return result;
    }
    else if (path == "/desktop/meetings" || path == "/desktop/shared-with-me") result.kind = RouteKind::meetings;
    // The cabinet sidebar and the settings pages link to the notification inbox
    // with an ordinary same-origin anchor, and the deletion page is the same kind
    // of route.  Mac admits both; denying them made the bell a dead link.
    else if (path == "/desktop/notifications" || path == "/notifications") result.kind = RouteKind::meetings;
    else if (path == "/desktop/deletions") result.kind = RouteKind::deletionReport;
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
    else if (billingRoute(path)) result.kind = RouteKind::billing;
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

bool WebViewRoutePolicy::sharesOrigin(std::string_view url) const {
    const auto parsed = parseHttps(url);
    return parsed && parsed->origin == trustedOrigin_;
}

bool WebViewRoutePolicy::canStartPayment(std::string_view source, std::string_view destination) const {
    const auto from = evaluate(source);
    const auto to = parseHttps(destination);
    if (from.decision != RouteDecision::allow || from.kind != RouteKind::billing || !to) return false;
    for (const auto host : {"api.yookassa.ru", "api.yookassa.test", "yookassa.ru", "yookassa.test", "yoomoney.ru"}) {
        if (to->host == host) return true;
    }
    return false;
}

bool WebViewRoutePolicy::allowsNativeBridge(std::string_view url) const {
    const auto route = evaluate(url);
    const auto parsed = parseHttps(url);
    return route.decision == RouteDecision::allow && parsed && !emailLinkForm(parsed->path) &&
        route.kind != RouteKind::authRecovery && route.kind != RouteKind::authProvider &&
        route.kind != RouteKind::artifactDownload && route.kind != RouteKind::nativeSettings &&
        route.kind != RouteKind::publicReader && route.kind != RouteKind::sharedMedia;
}

WebResponseEvaluation WebViewRoutePolicy::response(std::string_view url, const WebDocumentResponse& value,
    AuthContinuation auth, bool payment) const {
    using D = WebResponseDecision;
    const auto route = evaluate(url, true, auth, payment);
    if (route.decision != RouteDecision::allow) return {D::blocked};
    if (!value.transportSucceeded) return {D::unavailable};
    if (value.status < 200 || value.status > 599) return {D::malformed};
    if (route.kind == RouteKind::authProvider || route.kind == RouteKind::paymentProvider) return {D::externalDocument};
    const auto parsed = parseHttps(url);
    const auto path = parsed->path;
    if (exactOrChild(path, "/login") || exactOrChild(path, "/sign-up")) return {D::interactiveForm};
    if (value.recoveryHeader == "reselect-space") return {D::workspaceReselection};
    if (value.status == 401) return {D::expiredSession};
    auto mime = value.contentType.substr(0, value.contentType.find(';'));
    while (!mime.empty() && (mime.back() == ' ' || mime.back() == '\t')) mime.pop_back();
    const auto first = mime.find_first_not_of(" \t");
    mime.erase(0, first == std::string::npos ? mime.size() : first);
    std::transform(mime.begin(), mime.end(), mime.begin(), [](unsigned char c) {
        return c >= 'A' && c <= 'Z' ? static_cast<char>(c + 32) : static_cast<char>(c);
    });
    if (emailLinkForm(path) && mime == "text/html" &&
        (value.status < 400 || value.status == 400 || value.status == 429 || value.status == 503)) return {D::interactiveForm};
    if (value.status < 400) return {route.kind == RouteKind::authRecovery ? D::interactiveForm : D::cabinet};
    if (value.status == 403) return {D::accessDenied};
    if (value.status == 404) return {D::notFound};
    if (value.status == 408 || value.status == 504) return {D::timeout};
    if (value.status >= 500) return {D::unavailable};
    return {D::malformed};
}

std::string WebViewRoutePolicy::safeRecoveryUrl(std::string_view url, std::string_view method) const {
    if (method != "GET") return {};
    const auto parsed = parseHttps(url);
    if (!parsed) return {};
    const auto path = parsed->path;
    constexpr std::string_view publicShare = "/api/v1/cabinet/public-shares/";
    const bool sharedReader = startsWith(path, "/shared-meetings/") ||
        (startsWith(path, publicShare) && path.find('/', publicShare.size()) == path.npos);
    if (parsed->origin == trustedOrigin_ && sharedReader && evaluate(url).decision == RouteDecision::allow)
        return trustedOrigin_ + std::string(path) + std::string(parsed->suffix);
    if (!allowsNativeBridge(url)) return {};
    // This is a GET-document allowlist, not the wider navigation/action table.
    bool safe = false;
    for (const auto exact : {"/desktop/meetings", "/desktop/shared-with-me", "/desktop/notifications", "/notifications",
         "/desktop/deletions", "/desktop/settings", "/desktop/settings/account", "/desktop/settings/recording",
         "/desktop/settings/notifications", "/desktop/settings/integrations/calendar", "/desktop/settings/spaces",
         "/desktop/account", "/desktop/account/profile", "/desktop/account/security", "/desktop/account/notifications",
         "/desktop/account/fair-use", "/billing", "/billing/plans", "/billing/usage", "/billing/subscription",
         "/billing/payment-method", "/billing/checkout", "/billing/history", "/billing/discounts", "/billing/storage"}) {
        if (path == exact) safe = true;
    }
    for (const auto prefix : {"/desktop/meetings/", "/billing/checkout/status/", "/billing/invoices/"}) {
        if (startsWith(path, prefix) && safePathComponent(path.substr(std::string_view(prefix).size()))) safe = true;
    }
    if (meetingAction(path, "deletion-report")) safe = true;
    const auto result = trustedOrigin_ + std::string(path);
    return safe && evaluate(result).decision == RouteDecision::allow ? result : std::string{};
}

std::string WebViewRoutePolicy::recoveryUrl(WebResponseDecision reason, std::string_view safeDocument, bool billingContext) const {
    auto safe = safeRecoveryUrl(safeDocument);
    if (safe.empty()) safe = trustedOrigin_ + (billingContext ? "/billing" : "/desktop/meetings");
    if (reason == WebResponseDecision::expiredSession || reason == WebResponseDecision::workspaceReselection) {
        const auto parsed = parseHttps(safe);
        if (evaluate(safe).kind == RouteKind::publicReader) {
            // Only validated reader GETs reach here; media/continuations cannot
            // replace the reader. The server owns sealing the public return.
            const auto hash = parsed->suffix.find('#');
            const auto query = parsed->suffix.substr(0, hash);
            const auto fragment = hash == parsed->suffix.npos ? std::string_view{} : parsed->suffix.substr(hash + 1);
            auto continuation = trustedOrigin_ + std::string(parsed->path) + "/continue" + std::string(query) + "&action=sign-in&tab=";
            continuation += startsWith(fragment, "recording") ? "recording" : "outcomes";
            constexpr std::string_view position = "recording?position_ms=";
            if (startsWith(fragment, position)) continuation += "&position_ms=" + std::string(fragment.substr(position.size()));
            const auto route = evaluate(continuation);
            return route.decision == RouteDecision::allow && route.kind == RouteKind::publicReader
                ? continuation : trustedOrigin_ + "/desktop/meetings";
        }
        return trustedOrigin_ + "/login?next=" + encodePath(std::string(parsed->path) + std::string(parsed->suffix));
    }
    if (reason == WebResponseDecision::accessDenied || reason == WebResponseDecision::notFound)
        return trustedOrigin_ + "/desktop/meetings";
    return safe;
}

bool PaymentNavigation::begin(const WebViewRoutePolicy& policy, std::string_view source,
    std::string_view destination, std::uint64_t now) {
    if (startedAt_ || !policy.canStartPayment(source, destination)) return false;
    startedAt_ = now;
    return true;
}

bool PaymentNavigation::live(std::uint64_t now) const noexcept {
    return startedAt_ && now >= *startedAt_ && now - *startedAt_ < 900000;
}

void PaymentNavigation::loaded(const WebViewRoutePolicy& policy, std::string_view url, std::uint64_t now) {
    if (!live(now) || policy.sharesOrigin(url)) stop();
}

void SafeHistory::invalidate() noexcept {
    fresh_ = false;
    ++revision_;
}

void SafeHistory::clear() noexcept {
    entries_.clear();
    currentIndex_ = 0;
    invalidate();
}

void SafeHistory::forgetEntry(int id) noexcept {
    for (auto& entry : entries_) if (entry.browser.id == id) entry.confirmedGet = false;
    invalidate();
}

bool SafeHistory::acceptSnapshot(std::uint64_t requestRevision,
    std::vector<WebHistoryEntry> entries, std::size_t currentIndex, std::string_view currentUrl) {
    if (requestRevision != revision_) return false; // A late read must not replace a newer one.
    invalidate();
    if (entries.empty() || entries.size() > 128 || currentIndex >= entries.size() ||
        entries[currentIndex].url != currentUrl) return false;
    std::vector<Entry> next;
    next.reserve(entries.size());
    for (auto& entry : entries) {
        if (entry.id < 0 || entry.url.empty() || entry.url.size() > 8192 || !safeUrl(entry.url) ||
            std::any_of(next.begin(), next.end(), [&](const auto& prior) { return prior.browser.id == entry.id; }))
            return false;
        const auto prior = std::find_if(entries_.begin(), entries_.end(), [&](const auto& old) {
            return old.browser.id == entry.id && old.browser.url == entry.url;
        });
        const bool confirmed = prior != entries_.end() && prior->confirmedGet;
        next.push_back({std::move(entry), confirmed});
    }
    entries_ = std::move(next);
    currentIndex_ = currentIndex;
    fresh_ = true;
    return true;
}

bool SafeHistory::confirmCurrent(const WebViewRoutePolicy& policy, std::uint64_t revision,
    std::string_view responseUrl, std::string_view method) {
    if (!fresh_ || revision != revision_) return false;
    auto& entry = entries_[currentIndex_];
    entry.confirmedGet = entry.browser.url == responseUrl && method == "GET" &&
        policy.allowsNativeBridge(responseUrl);
    return entry.confirmedGet;
}

std::optional<WebHistoryEntry> SafeHistory::current() const {
    return fresh_ ? std::optional<WebHistoryEntry>(entries_[currentIndex_].browser) : std::nullopt;
}

bool SafeHistory::currentIsGet(const WebViewRoutePolicy& policy) const {
    return fresh_ && entries_[currentIndex_].confirmedGet &&
        policy.allowsNativeBridge(entries_[currentIndex_].browser.url);
}

bool SafeHistory::allGet(const WebViewRoutePolicy& policy) const {
    return fresh_ && std::all_of(entries_.begin(), entries_.end(), [&](const auto& entry) {
        return entry.confirmedGet && policy.allowsNativeBridge(entry.browser.url);
    });
}

std::optional<WebHistoryEntry> SafeHistory::target(const WebViewRoutePolicy& policy, bool back) const {
    if (!allGet(policy)) return std::nullopt;
    const auto meetingRoute = [&](std::string_view url) {
        const auto kind = policy.evaluate(url).kind;
        const auto parsed = parseHttps(url);
        return kind == RouteKind::meetingDetail || kind == RouteKind::review || kind == RouteKind::share ||
            (parsed && (parsed->path == "/desktop/meetings" || parsed->path == "/desktop/shared-with-me" ||
                        meetingAction(parsed->path, "deletion-report")));
    };
    const auto& currentUrl = entries_[currentIndex_].browser.url;
    const auto currentKind = policy.evaluate(currentUrl).kind;
    const auto currentParsed = parseHttps(currentUrl);
    const bool restrictBack = currentKind == RouteKind::meetingDetail || currentKind == RouteKind::review ||
        currentKind == RouteKind::share || (currentParsed && meetingAction(currentParsed->path, "deletion-report"));
    const auto eligible = [&](const auto& entry) {
        return entry.browser.url != currentUrl && (!back || !restrictBack || meetingRoute(entry.browser.url));
    };
    if (back) {
        for (auto i = currentIndex_; i > 0;) {
            const auto& entry = entries_[--i];
            if (eligible(entry)) return entry.browser;
        }
    } else {
        for (auto i = currentIndex_ + 1; i < entries_.size(); ++i)
            if (eligible(entries_[i])) return entries_[i].browser;
    }
    return std::nullopt;
}

} // namespace graf::windows
