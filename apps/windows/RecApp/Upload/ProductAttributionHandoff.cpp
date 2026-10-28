#include "ProductAttributionHandoff.h"
#include "../Web/WebViewRoutePolicy.h"

#include <algorithm>
#include <array>
#include <charconv>
#include <fstream>
#include <limits>
#include <utility>
#include <vector>

namespace graf::windows {
namespace {
constexpr std::array<std::string_view, 5> campaignNames{
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"};
constexpr std::string_view magic = "GRAF_ATTRIBUTION_V1";

std::string_view trim(std::string_view text) {
    // Foundation .whitespacesAndNewlines, encoded as UTF-8. Labels themselves
    // remain ASCII; Unicode whitespace is removed only at their boundaries.
    constexpr std::string_view spaces[]{
        " ", "\t", "\r", "\n", "\v", "\f", u8"\u0085", u8"\u00a0", u8"\u1680",
        u8"\u2000", u8"\u2001", u8"\u2002", u8"\u2003", u8"\u2004", u8"\u2005",
        u8"\u2006", u8"\u2007", u8"\u2008", u8"\u2009", u8"\u200a", u8"\u200b", u8"\u2028",
        u8"\u2029", u8"\u202f", u8"\u205f", u8"\u3000"};
    bool changed = true;
    while (changed && !text.empty()) {
        changed = false;
        for (const auto space : spaces) {
            if (text.substr(0, space.size()) == space) { text.remove_prefix(space.size()); changed = true; }
            if (text.size() >= space.size() && text.substr(text.size() - space.size()) == space) {
                text.remove_suffix(space.size()); changed = true;
            }
        }
    }
    return text;
}

bool asciiAlnum(char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9');
}

std::string lower(std::string_view text) {
    std::string result(text);
    for (auto& c : result) if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + ('a' - 'A'));
    return result;
}

int hex(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

std::optional<std::string> decode(std::string_view text) {
    std::string result;
    for (std::size_t i = 0; i < text.size(); ++i) {
        if (text[i] != '%') { result += text[i]; continue; }
        if (i + 2 >= text.size() || hex(text[i + 1]) < 0 || hex(text[i + 2]) < 0) return std::nullopt;
        result += static_cast<char>(hex(text[i + 1]) * 16 + hex(text[i + 2]));
        i += 2;
    }
    // URI query semantics, not form encoding: '+' is not decoded as a space.
    return result;
}

std::string encode(std::string_view text) {
    constexpr char digits[] = "0123456789ABCDEF";
    std::string result;
    for (const auto c : text) {
        if (asciiAlnum(c) || c == '-' || c == '_' || c == '.' || c == '~') result += c;
        else {
            const auto byte = static_cast<unsigned char>(c);
            result += '%'; result += digits[byte >> 4]; result += digits[byte & 15];
        }
    }
    return result;
}

bool safeBridge(std::string_view value) {
    constexpr std::string_view prefix = "graf_attr_";
    if (value.substr(0, prefix.size()) != prefix) return false;
    const auto suffix = value.substr(prefix.size());
    return suffix.size() >= 8 && suffix.size() <= 64 &&
        std::all_of(suffix.begin(), suffix.end(), [](char c) { return asciiAlnum(c) || c == '_' || c == '-'; });
}

bool safeLabel(std::string_view value) {
    if (value.empty() || value.size() > ProductAttributionHandoff::maximumLabelBytes) return false;
    if (!std::all_of(value.begin(), value.end(), [](char c) {
        return asciiAlnum(c) || c == '_' || c == '.' || c == ':' || c == '-';
    })) return false;
    const auto lowered = lower(value);
    for (const auto word : {"token", "secret", "password", "passcode", "signed_url", "api_key"})
        if (lowered.find(word) != std::string::npos) return false;
    // Mac's phone pattern: digit, >=8 digits/separators, digit. After the ASCII
    // allowlist above, only '.' and '-' remain possible phone separators.
    std::size_t firstDigit = std::string_view::npos;
    for (std::size_t i = 0; i < value.size(); ++i) {
        const bool digit = value[i] >= '0' && value[i] <= '9';
        if (digit) {
            if (firstDigit == std::string_view::npos) firstDigit = i;
            else if (i - firstDigit >= 9) return false;
        } else if (value[i] != '.' && value[i] != '-') firstDigit = std::string_view::npos;
    }
    return true;
}

bool safeLanding(std::string_view value) {
    return !value.empty() && value.front() == '/' && value.size() <= ProductAttributionHandoff::maximumLabelBytes &&
        std::all_of(value.begin(), value.end(), [](char c) { return asciiAlnum(c) || c == '/' || c == '_' || c == '-'; });
}

bool validTime(std::int64_t value) {
    return value >= 0 && value <= std::numeric_limits<std::int64_t>::max() - ProductAttributionHandoff::validitySeconds;
}

ProductAttributionHandoff sanitized(const ProductAttributionHandoff& input) {
    ProductAttributionHandoff result;
    result.receivedAt = input.receivedAt;
    result.fallbackRecovered = input.fallbackRecovered;
    if (input.bridgeID && safeBridge(*input.bridgeID)) result.bridgeID = input.bridgeID;
    if (input.landingPath && safeLanding(trim(*input.landingPath))) result.landingPath = trim(*input.landingPath);
    for (const auto name : campaignNames) {
        const auto item = input.campaign.find(std::string(name));
        if (item != input.campaign.end() && safeLabel(trim(item->second)))
            result.campaign.emplace(name, trim(item->second));
    }
    return result;
}

std::optional<std::int64_t> timestamp(std::string_view text) {
    std::int64_t value = 0;
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size() || !validTime(value)) return std::nullopt;
    return value;
}
} // namespace

std::optional<ProductAttributionHandoff> ProductAttributionHandoff::parse(std::string_view raw, std::int64_t received) {
    if (raw.size() > maximumLinkBytes || !validTime(received)) return std::nullopt;
    const auto link = trim(raw);
    const auto scheme = link.find("://");
    if (scheme == std::string_view::npos || lower(link.substr(0, scheme)) != "grafrec") return std::nullopt;
    if (std::any_of(link.begin(), link.end(), [](unsigned char c) { return c < 0x20 || c == 0x7f; })) return std::nullopt;
    const auto rest = link.substr(scheme + 3);
    auto authority = rest.substr(0, rest.find_first_of("/?#"));
    // Like URLComponents, select by scheme/host, not by an arbitrary path or
    // userinfo. Ignored components are never propagated to the login URL.
    if (const auto at = authority.rfind('@'); at != std::string_view::npos) authority.remove_prefix(at + 1);
    if (const auto colon = authority.find(':'); colon != std::string_view::npos) {
        const auto port = authority.substr(colon + 1);
        if (!std::all_of(port.begin(), port.end(), [](char c) { return c >= '0' && c <= '9'; })) return std::nullopt;
        authority = authority.substr(0, colon);
    }
    const auto host = decode(authority);
    if (!host || lower(*host) != "attribution") return std::nullopt;
    ProductAttributionHandoff result;
    result.receivedAt = received;
    const auto queryStart = rest.find('?');
    const auto fragment = rest.find('#');
    if (queryStart == std::string_view::npos || (fragment != std::string_view::npos && fragment < queryStart)) return result;
    auto query = rest.substr(queryStart + 1, fragment == std::string_view::npos ? fragment : fragment - queryStart - 1);
    std::map<std::string, std::string> values;
    while (!query.empty()) {
        const auto amp = query.find('&');
        const auto pair = query.substr(0, amp);
        const auto equals = pair.find('=');
        const auto name = decode(pair.substr(0, equals));
        if (name && (*name == "bridge" || *name == "fallback" || *name == "landing_path" ||
                     std::find(campaignNames.begin(), campaignNames.end(), *name) != campaignNames.end())) {
            const auto value = decode(equals == std::string_view::npos ? std::string_view{} : pair.substr(equals + 1));
            values.emplace(*name, value.value_or(""));
        }
        if (amp == std::string_view::npos) break;
        query.remove_prefix(amp + 1);
    }
    if (const auto it = values.find("bridge"); it != values.end()) result.bridgeID = it->second;
    if (const auto it = values.find("landing_path"); it != values.end()) result.landingPath = it->second;
    const auto flag = lower(trim(values["fallback"]));
    result.fallbackRecovered = flag == "1" || flag == "true" || flag == "yes";
    result.campaign = std::move(values);
    return sanitized(result);
}

bool ProductAttributionHandoff::isExpired(std::int64_t now) const noexcept {
    return !validTime(receivedAt) || now >= receivedAt + validitySeconds;
}

std::string_view ProductAttributionHandoff::reliability(bool accountConnected) const noexcept {
    if (!campaignKnown()) return "unknown";
    return accountConnected && !fallbackRecovered ? "linked" : "weak";
}

ProductAttributionHandoffStore::ProductAttributionHandoffStore(std::filesystem::path path, Writer writer)
    : path_(std::move(path)), writer_(writer ? writer : &AtomicFileStore::write) {}

AttributionStoreRead ProductAttributionHandoffStore::read() const {
    AttributionStoreRead result;
    std::error_code error;
    if (path_.empty()) { result.error = AttributionStoreError::ioError; return result; }
    if (!std::filesystem::exists(path_, error)) {
        if (error) result.error = AttributionStoreError::ioError;
        return result;
    }
    if (!std::filesystem::is_regular_file(path_, error) || error) { result.error = AttributionStoreError::ioError; return result; }
    std::ifstream input(path_, std::ios::binary);
    if (!input) { result.error = AttributionStoreError::ioError; return result; }
    std::array<char, maximumBytes + 1> buffer{};
    input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
    if (input.bad()) { result.error = AttributionStoreError::ioError; return result; }
    const auto length = static_cast<std::size_t>(input.gcount());
    if (length > maximumBytes) { result.error = AttributionStoreError::tooLarge; return result; }
    std::string_view remaining(buffer.data(), length);
    std::vector<std::string_view> fields;
    while (!remaining.empty() && fields.size() <= 11) {
        const auto end = remaining.find('\n');
        if (end == std::string_view::npos) break;
        fields.push_back(remaining.substr(0, end));
        remaining.remove_prefix(end + 1);
    }
    result.error = AttributionStoreError::invalidData;
    if (!remaining.empty() || fields.size() != 11 || fields[0] != magic) return result;
    if (fields[1] != "-") {
        result.accountConnectedAt = timestamp(fields[1]);
        if (!result.accountConnectedAt) return result;
    }
    if (fields[3] != "0" && fields[3] != "1") return result;
    if (fields[2] == "-") {
        if (fields[3] != "0" || std::any_of(fields.begin() + 4, fields.end(), [](auto f) { return !f.empty(); })) return result;
    } else {
        const auto received = timestamp(fields[2]);
        if (!received) return result;
        ProductAttributionHandoff value;
        value.receivedAt = *received;
        value.fallbackRecovered = fields[3] == "1";
        if (!fields[4].empty()) {
            if (!safeBridge(fields[4])) return result;
            value.bridgeID = fields[4];
        }
        if (!fields[5].empty()) {
            if (!safeLanding(fields[5])) return result;
            value.landingPath = fields[5];
        }
        for (std::size_t i = 0; i < campaignNames.size(); ++i) {
            if (!fields[6 + i].empty()) {
                if (!safeLabel(fields[6 + i])) return result;
                value.campaign.emplace(campaignNames[i], fields[6 + i]);
            }
        }
        result.handoff = std::move(value);
    }
    result.error = AttributionStoreError::none;
    return result;
}

AttributionStoreError ProductAttributionHandoffStore::write(const AttributionStoreRead& state) const {
    // Private versioned fixed-field format: allowed values cannot contain LF.
    // Only sanitized fields are persisted, never the activation URL or unknown keys.
    std::string content = std::string(magic) + "\n";
    content += state.accountConnectedAt ? std::to_string(*state.accountConnectedAt) : "-";
    content += '\n';
    content += state.handoff ? std::to_string(state.handoff->receivedAt) : "-";
    content += '\n';
    content += state.handoff && state.handoff->fallbackRecovered ? "1\n" : "0\n";
    content += state.handoff ? state.handoff->bridgeID.value_or("") : "";
    content += '\n';
    content += state.handoff ? state.handoff->landingPath.value_or("") : "";
    content += '\n';
    for (const auto name : campaignNames) {
        if (state.handoff) {
            const auto it = state.handoff->campaign.find(std::string(name));
            if (it != state.handoff->campaign.end()) content += it->second;
        }
        content += '\n';
    }
    return writer_(path_, content, maximumBytes).ok() ? AttributionStoreError::none : AttributionStoreError::ioError;
}

AttributionStoreRead ProductAttributionHandoffStore::current(std::int64_t now) const {
    auto state = read();
    if (state.error != AttributionStoreError::none) { state.handoff.reset(); state.accountConnectedAt.reset(); return state; }
    if (state.handoff && state.handoff->isExpired(now)) {
        state.handoff.reset();
        state.error = write(state);
    }
    return state;
}

AttributionStoreError ProductAttributionHandoffStore::saveLink(std::string_view link, std::int64_t receivedAt) {
    const auto value = ProductAttributionHandoff::parse(link, receivedAt);
    return value ? save(*value) : AttributionStoreError::rejected;
}

AttributionStoreError ProductAttributionHandoffStore::save(const ProductAttributionHandoff& handoff) {
    if (!validTime(handoff.receivedAt)) return AttributionStoreError::rejected;
    auto state = read();
    if (state.error == AttributionStoreError::ioError) return state.error;
    if (state.error != AttributionStoreError::none) state = {};
    state.handoff = sanitized(handoff);
    return write(state);
}

AttributionStoreError ProductAttributionHandoffStore::markAccountConnected(std::int64_t at) {
    if (!validTime(at)) return AttributionStoreError::rejected;
    auto state = current(at);
    if (state.error == AttributionStoreError::ioError) return state.error;
    if (state.error != AttributionStoreError::none) state = {};
    state.accountConnectedAt = at;
    return write(state);
}

AttributionStoreError ProductAttributionHandoffStore::clear() {
    std::error_code error;
    if (path_.empty()) return AttributionStoreError::ioError;
    if (std::filesystem::exists(path_, error) && !std::filesystem::is_regular_file(path_, error)) return AttributionStoreError::ioError;
    if (error) return AttributionStoreError::ioError;
    std::filesystem::remove(path_, error);
    return error ? AttributionStoreError::ioError : AttributionStoreError::none;
}

std::string applyingSignInQueryItems(std::string_view plain,
    const std::optional<ProductAttributionHandoff>& handoff, std::int64_t now) {
    if (!handoff || handoff->isExpired(now)) return std::string(plain);
    const auto clean = sanitized(*handoff);
    std::vector<std::pair<std::string_view, std::string>> items{{"graf_attribution_fallback", "1"}};
    if (clean.bridgeID) items.emplace_back("graf_attribution_ref", *clean.bridgeID);
    for (const auto name : campaignNames) {
        const auto it = clean.campaign.find(std::string(name));
        if (it != clean.campaign.end()) items.emplace_back(name, it->second);
    }
    if (clean.landingPath) items.emplace_back("landing_path", *clean.landingPath);

    const auto fragmentAt = plain.find('#');
    const auto head = plain.substr(0, fragmentAt);
    const auto queryAt = head.find('?');
    std::string result(head.substr(0, queryAt));
    if (queryAt != std::string_view::npos) {
        result += '?';
        auto query = head.substr(queryAt + 1);
        bool first = true;
        while (true) {
            const auto end = query.find('&');
            const auto field = query.substr(0, end);
            // Decode names only to replace equivalent encoded attribution keys.
            // Values (especially next) must never be decoded or reconstructed.
            const auto name = decode(field.substr(0, field.find('=')));
            const bool replaced = name && std::any_of(items.begin(), items.end(),
                [&](const auto& item) { return item.first == *name; });
            if (!replaced) {
                if (!first) result += '&';
                result += field;
                first = false;
            }
            if (end == std::string_view::npos) break;
            query.remove_prefix(end + 1);
        }
    } else {
        result += '?';
    }
    for (const auto& item : items) {
        if (result.find('?') != result.size() - 1 && result.back() != '&') result += '&';
        result += std::string(item.first) + "=" + encode(item.second);
    }
    if (fragmentAt != std::string_view::npos) result += plain.substr(fragmentAt);
    return result;
}

std::string productAttributionSignInUrl(const WebViewRoutePolicy& policy, std::string_view next,
    const std::optional<ProductAttributionHandoff>& handoff, std::int64_t now) {
    const auto candidate = !next.empty() && next.front() == '/' && next.substr(0, 2) != "//"
        ? policy.trustedOrigin() + std::string(next) : std::string(next);
    auto safe = policy.safeRecoveryUrl(candidate);
    if (safe.empty()) safe = policy.trustedOrigin() + "/desktop/meetings";
    const auto plain = policy.trustedOrigin() + "/login?next=" + encode(safe.substr(policy.trustedOrigin().size()));
    return applyingSignInQueryItems(plain, handoff, now);
}

} // namespace graf::windows
