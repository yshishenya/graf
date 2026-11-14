#include "CalendarMeetingOpener.h"
#include <algorithm>
#include <array>
#include <charconv>
#include <cstdint>
#include <cstring>
#include <memory>
#include <vector>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <urlmon.h>
#include <wrl/client.h>
#include <icu.h>
#pragma comment(lib, "normaliz.lib")
#pragma comment(lib, "urlmon.lib")
#pragma comment(lib, "oleaut32.lib")
#pragma comment(lib, "icu.lib")
#else
#include <arpa/inet.h>
#endif

namespace graf::windows {
namespace {
constexpr std::size_t maxRawBytes = 8192, maxNormalizedBytes = 32768;
std::string lower(std::string value) {
    for (auto& c : value) if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + ('a' - 'A'));
    return value;
}
std::string trimDots(std::string value) {
    const auto first = value.find_first_not_of('.');
    return first == std::string::npos ? std::string{} : value.substr(first, value.find_last_not_of('.') - first + 1);
}
#ifdef _WIN32
std::optional<std::wstring> wideCharacters(std::string_view value) {
    if (value.empty() || value.size() > maxNormalizedBytes) return std::nullopt;
    const auto size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0);
    if (!size) return std::nullopt;
    std::wstring result(static_cast<std::size_t>(size), L'\0');
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), result.data(), size) != size)
        return std::nullopt;
    for (std::size_t i = 0; i < result.size(); ++i) {
        std::uint32_t scalar = result[i];
        if (scalar >= 0xd800 && scalar <= 0xdbff) {
            if (++i >= result.size() || result[i] < 0xdc00 || result[i] > 0xdfff) return std::nullopt;
            scalar = 0x10000 + ((scalar - 0xd800) << 10) + (result[i] - 0xdc00);
        } else if (scalar >= 0xdc00 && scalar <= 0xdfff) return std::nullopt;
        const auto category = u_charType(static_cast<UChar32>(scalar));
        // Cc/Cf, not Foundation's observed Plane14 false positives (review H1).
        if (category == U_CONTROL_CHAR || category == U_FORMAT_CHAR) return std::nullopt;
    }
    return result;
}
std::optional<std::string> utf8(std::wstring_view value) {
    if (value.empty() || value.size() > maxNormalizedBytes) return std::nullopt;
    const auto size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    if (!size || size > static_cast<int>(maxNormalizedBytes)) return std::nullopt;
    std::string result(static_cast<std::size_t>(size), '\0');
    if (WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), result.data(), size, nullptr, nullptr) != size)
        return std::nullopt;
    return result;
}
#endif
bool validCharacters(std::string_view value) {
#ifdef _WIN32
    return wideCharacters(value).has_value();
#else
    // This test adapter deliberately makes no Unicode/IDNA acceptance claim.
    return std::all_of(value.begin(), value.end(), [](unsigned char c) { return c >= 0x20 && c < 0x7f; });
#endif
}
std::optional<std::string> decodeHost(std::string_view value, bool repairPercent = false) {
    std::string result;
    for (std::size_t i = 0; i < value.size(); ++i) {
        if (value[i] != '%') { result += value[i]; continue; }
        unsigned byte = 0;
        bool valid = false;
        if (i + 2 < value.size()) {
            const auto decoded = std::from_chars(value.data() + i + 1, value.data() + i + 3, byte, 16);
            valid = decoded.ec == std::errc{} && decoded.ptr == value.data() + i + 3;
        }
        if (!valid) {
            if (!repairPercent) return std::nullopt;
            result += '%'; continue;
        }
        result += static_cast<char>(byte); i += 2;
    }
    return result;
}
std::optional<std::string> normalizeHost(std::string value, bool ipv6) {
    if (!validCharacters(value)) return std::nullopt;
    for (const auto c : value) {
        if (static_cast<unsigned char>(c) <= 0x20 || std::string_view("@/\\?#[]%").find(c) != std::string_view::npos ||
            (!ipv6 && c == ':')) return std::nullopt;
    }
    value = lower(std::move(value));
    if (!ipv6) value = trimDots(std::move(value));
    if (value.empty()) return std::nullopt;
#ifdef _WIN32
    if (!ipv6) {
        const auto wide = wideCharacters(value);
        if (!wide) return std::nullopt;
        const auto size = IdnToAscii(0, wide->data(), static_cast<int>(wide->size()), nullptr, 0);
        if (!size || size > static_cast<int>(maxNormalizedBytes)) return std::nullopt;
        std::wstring ascii(static_cast<std::size_t>(size), L'\0');
        if (IdnToAscii(0, wide->data(), static_cast<int>(wide->size()), ascii.data(), size) != size) return std::nullopt;
        const auto converted = utf8(ascii);
        if (!converted) return std::nullopt;
        value = trimDots(lower(*converted));
    }
#endif
    if (value.empty() || value.find_first_of("@/\\?#[]% \t\r\n") != std::string::npos ||
        (!ipv6 && value.find(':') != std::string::npos)) return std::nullopt;
    return value;
}
bool readAddress(std::string_view host, bool ipv6, std::array<unsigned char, 16>& bytes) {
    const std::string text(host);
    if (ipv6) {
        in6_addr address{};
#ifdef _WIN32
        if (InetPtonA(AF_INET6, text.c_str(), &address) != 1) return false;
#else
        if (inet_pton(AF_INET6, text.c_str(), &address) != 1) return false;
#endif
        std::memcpy(bytes.data(), &address, 16); return true;
    }
    in_addr address{};
#ifdef _WIN32
    if (InetPtonA(AF_INET, text.c_str(), &address) != 1) return false;
#else
    if (inet_aton(text.c_str(), &address) != 1) return false;
#endif
    std::memcpy(bytes.data(), &address, 4); return true;
}
struct Range { std::string_view address; unsigned prefix; };
bool globalAddress(const std::array<unsigned char, 16>& bytes, bool ipv6) {
    constexpr Range denied4[] = {{"0.0.0.0",8},{"10.0.0.0",8},{"127.0.0.0",8},{"169.254.0.0",16},
        {"172.16.0.0",12},{"192.0.0.0",24},{"192.0.0.170",31},{"192.0.2.0",24},{"192.168.0.0",16},
        {"198.18.0.0",15},{"198.51.100.0",24},{"203.0.113.0",24},{"240.0.0.0",4},{"255.255.255.255",32},{"100.64.0.0",10}};
    constexpr Range exceptions4[] = {{"192.0.0.9",32},{"192.0.0.10",32}};
    constexpr Range denied6[] = {{"::1",128},{"::",128},{"::ffff:0.0.0.0",96},{"64:ff9b:1::",48},
        {"100::",64},{"2001::",23},{"2001:db8::",32},{"2002::",16},{"3fff::",20},{"fc00::",7},{"fe80::",10}};
    constexpr Range exceptions6[] = {{"2001:1::1",128},{"2001:1::2",128},{"2001:3::",32},
        {"2001:4:112::",48},{"2001:20::",28},{"2001:30::",28}};
    bool valid = true;
    const auto matches = [&](const Range& range) {
        std::array<unsigned char, 16> network{};
        if (!readAddress(range.address, ipv6, network)) { valid = false; return false; }
        for (unsigned bit = 0; bit < range.prefix; ++bit) {
            const auto mask = 1u << (7 - bit % 8);
            if ((bytes[bit / 8] & mask) != (network[bit / 8] & mask)) return false;
        }
        return true;
    };
    bool denied = false, exception = false;
    if (ipv6) {
        for (const auto& range : denied6) denied |= matches(range);
        for (const auto& range : exceptions6) exception |= matches(range);
    } else {
        for (const auto& range : denied4) denied |= matches(range);
        for (const auto& range : exceptions4) exception |= matches(range);
    }
    return valid && (exception || !denied);
}
bool allowedHost(std::string_view host) {
    if (host == "localhost" || (host.size() > 10 && host.substr(host.size() - 10) == ".localhost")) return false;
    const bool ipv6 = host.find(':') != std::string_view::npos;
    std::array<unsigned char, 16> bytes{};
    if (!readAddress(host, ipv6, bytes)) return !ipv6; // DNS name: no DNS lookup or pinning claim
    if (ipv6 && std::all_of(bytes.begin(), bytes.begin() + 10, [](auto b) { return b == 0; }) && bytes[10] == 255 && bytes[11] == 255) {
        std::array<unsigned char, 16> mapped{};
        std::copy(bytes.begin() + 12, bytes.end(), mapped.begin());
        return globalAddress(mapped, false);
    }
    return globalAddress(bytes, ipv6);
}
std::string authority(std::string_view host, bool ipv6, std::optional<unsigned> port) {
    return (ipv6 ? "[" + std::string(host) + "]" : std::string(host)) + (port ? ":" + std::to_string(*port) : "");
}
std::optional<std::string> decodedComponent(std::string_view value) {
    auto result = decodeHost(value, true);
    if (!result) return std::nullopt;
#ifdef _WIN32
    if (!result->empty() && !MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, result->data(),
        static_cast<int>(result->size()), nullptr, 0)) return std::nullopt;
#else
    // Portable ASCII policy only; native tests cover decoded UTF-8 separately.
    if (std::any_of(result->begin(), result->end(), [](unsigned char c) { return c >= 0x80; })) return std::nullopt;
#endif
    return result;
}
std::string encodedQueryItem(std::string_view value) {
    std::string result;
    constexpr char hex[] = "0123456789ABCDEF";
    for (const auto raw : value) {
        const auto c = static_cast<unsigned char>(raw);
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
            std::string_view("!$'()*+,-./:;?@_~").find(raw) != std::string_view::npos) result += raw;
        else { result += '%'; result += hex[c >> 4]; result += hex[c & 15]; }
    }
    return result;
}
}

std::optional<std::string> CalendarMeetingOpener::validatedHTTPS(std::string_view raw) noexcept {
    try {
        if (raw.size() < 9 || raw.size() > maxRawBytes || lower(std::string(raw.substr(0, 8))) != "https://" || !validCharacters(raw))
            return std::nullopt;
        const auto end = raw.find_first_of("/?#", 8);
        const auto originalAuthority = raw.substr(8, (end == std::string_view::npos ? raw.size() : end) - 8);
        const auto suffix = end == std::string_view::npos ? std::string_view{} : raw.substr(end);
        if (originalAuthority.empty() || originalAuthority.find_first_of("@\\") != std::string_view::npos) return std::nullopt;
        const bool ipv6 = originalAuthority.front() == '[';
        std::string_view originalHost = originalAuthority;
        std::size_t colon = std::string_view::npos;
        if (ipv6) {
            const auto bracket = originalAuthority.find(']');
            if (bracket == std::string_view::npos || bracket < 3) return std::nullopt;
            originalHost = originalAuthority.substr(1, bracket - 1);
            if (bracket + 1 < originalAuthority.size()) {
                if (originalAuthority[bracket + 1] != ':') return std::nullopt;
                colon = bracket + 1;
            }
        } else {
            colon = originalAuthority.find(':');
            if (colon != std::string_view::npos) originalHost = originalAuthority.substr(0, colon);
        }
        std::optional<unsigned> port;
        if (colon != std::string_view::npos) {
            const auto digits = originalAuthority.substr(colon + 1);
            unsigned number = 0;
            if (digits.empty()) return std::nullopt;
            for (const auto c : digits) {
                if (c < '0' || c > '9' || number > (65535u - static_cast<unsigned>(c - '0')) / 10) return std::nullopt;
                number = number * 10 + static_cast<unsigned>(c - '0');
            }
            port = number;
        }
        if (ipv6 && originalHost.find('%') != std::string_view::npos) return std::nullopt;
        const auto decoded = decodeHost(originalHost);
        auto host = decoded ? normalizeHost(*decoded, ipv6) : std::nullopt;
        if (!host) return std::nullopt;
        std::array<unsigned char, 16> address{};
        if (ipv6 && !readAddress(*host, true, address)) return std::nullopt;
        auto result = "https://" + authority(*host, ipv6, port) + std::string(suffix);
#ifdef _WIN32
        const auto wide = wideCharacters(result);
        if (!wide) return std::nullopt;
        Microsoft::WRL::ComPtr<IUri> uri;
        constexpr auto flags = Uri_CREATE_CANONICALIZE | Uri_CREATE_NO_PRE_PROCESS_HTML_URI |
            Uri_CREATE_NO_DECODE_EXTRA_INFO | Uri_CREATE_NO_IE_SETTINGS;
        if (CreateUri(wide->c_str(), flags, 0, &uri) != S_OK || !uri) return std::nullopt;
        BOOL userInfo = FALSE;
        DWORD actualPort = 0;
        if (uri->HasProperty(Uri_PROPERTY_USER_INFO, &userInfo) != S_OK || userInfo ||
            uri->GetPort(&actualPort) != S_OK || actualPort != port.value_or(443)) return std::nullopt;
        BSTR rawScheme = nullptr;
        const auto schemeStatus = uri->GetSchemeName(&rawScheme);
        std::unique_ptr<wchar_t, decltype(&SysFreeString)> scheme(rawScheme, SysFreeString);
        if (schemeStatus != S_OK || !scheme || std::wstring_view(scheme.get(), SysStringLen(scheme.get())) != L"https") return std::nullopt;
        BSTR rawHost = nullptr;
        const auto hostStatus = uri->GetHost(&rawHost);
        std::unique_ptr<wchar_t, decltype(&SysFreeString)> parsedHost(rawHost, SysFreeString);
        if (hostStatus != S_OK || !parsedHost) return std::nullopt;
        const auto actualHost = utf8(std::wstring_view(parsedHost.get(), SysStringLen(parsedHost.get())));
        host = actualHost ? normalizeHost(*actualHost, ipv6) : std::nullopt;
        if (!host) return std::nullopt;
        result = "https://" + authority(*host, ipv6, port) + std::string(suffix);
#endif
        if (result.size() > maxNormalizedBytes || !allowedHost(*host)) return std::nullopt;
        return result;
    } catch (...) { return std::nullopt; }
}

std::optional<std::string> CalendarMeetingOpener::nativeTarget(std::string_view raw) noexcept {
    try {
        const auto safe = validatedHTTPS(raw);
        if (!safe) return std::nullopt;
        const std::string_view url(*safe);
        const auto end = url.find_first_of("/?#", 8);
        const auto hostPort = url.substr(8, (end == url.npos ? url.size() : end) - 8);
        const auto colon = hostPort.find(':');
        if (colon != hostPort.npos && hostPort.substr(colon) != ":443") return std::nullopt;
        const auto host = hostPort.substr(0, colon);
        const auto suffix = end == url.npos ? std::string_view{} : url.substr(end);
        const auto decodedPath = decodedComponent(suffix.substr(0, suffix.find_first_of("?#")));
        if (!decodedPath) return std::nullopt;
        if (host == "teams.microsoft.com" && decodedPath->rfind("/l/meetup-join/", 0) == 0)
            return "msteams://" + std::string(hostPort) + std::string(suffix);
        if (host == "telemost.yandex.ru" && decodedPath->rfind("/j/", 0) == 0) return safe;
        const auto endsWith = [&](std::string_view tail) {
            return host.size() >= tail.size() && host.substr(host.size() - tail.size()) == tail;
        };
        if (host != "zoom.us" && host != "zoom.com" && !endsWith(".zoom.us") && !endsWith(".zoom.com")) return std::nullopt;
        std::vector<std::string_view> segments;
        const std::string_view path(*decodedPath);
        for (std::size_t start = 0; start < path.size();) {
            const auto slash = path.find('/', start);
            const auto part = path.substr(start, (slash == path.npos ? path.size() : slash) - start);
            if (!part.empty()) segments.push_back(part);
            if (slash == path.npos) break;
            start = slash + 1;
        }
        if (segments.size() != 2 || segments[0] != "j" || segments[1].size() < 9 || segments[1].size() > 11 ||
            !std::all_of(segments[1].begin(), segments[1].end(), [](char c) { return c >= '0' && c <= '9'; })) return std::nullopt;
        std::string result = "zoommtg://" + std::string(hostPort) + "/join?action=join&confno=" + std::string(segments[1]);
        const auto fragment = suffix.find('#'), question = suffix.find('?');
        if (question != suffix.npos && (fragment == suffix.npos || question < fragment)) {
            const auto query = suffix.substr(question + 1, (fragment == suffix.npos ? suffix.size() : fragment) - question - 1);
            // Foundation queryItems preserves empty items and distinguishes nil/empty values.
            for (std::size_t start = 0; start < query.size();) {
                const auto amp = query.find('&', start);
                const auto item = query.substr(start, (amp == query.npos ? query.size() : amp) - start);
                const auto equal = item.find('=');
                const auto name = decodedComponent(item.substr(0, equal)).value_or("");
                if (name != "action" && name != "confno") {
                    result += '&'; result += encodedQueryItem(name);
                    if (equal != item.npos) if (const auto value = decodedComponent(item.substr(equal + 1)))
                        result += '=' + encodedQueryItem(*value);
                }
                if (amp == query.npos) break;
                start = amp + 1;
                if (start == query.size()) result += '&';
            }
        }
        if (fragment != suffix.npos) result += suffix.substr(fragment);
        return result.size() <= maxNormalizedBytes ? std::optional<std::string>(std::move(result)) : std::nullopt;
    } catch (...) { return std::nullopt; }
}
}
