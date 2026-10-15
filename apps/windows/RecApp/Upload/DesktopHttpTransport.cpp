#include "DesktopHttpTransport.h"

#include "DesktopApiClient.h"
#include "../Recording/LocalRecordingPackage.h"
#include "../Storage/Sha256.h"
#include "../Contracts/JsonReader.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <charconv>
#include <chrono>
#include <fstream>
#include <limits>
#include <optional>
#include <set>
#include <sstream>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#endif

namespace graf::windows {
namespace {

constexpr std::size_t kMaxPartBytes = 16 * 1024 * 1024;
using HttpResponse = DesktopHttpTransport::UploadResponse;
template<class String> using UploadJsonReader = std::conditional_t<std::is_same_v<String, CustodyString>,
    json_detail::JsonReader<CustodyAllocator, CustodyString>, json_detail::JsonReader<>>;

template<class String> String fieldMarker(std::string_view key, std::string_view suffix) {
    String marker("\"");
    marker.append(key.data(), key.size());
    marker.append(suffix.data(), suffix.size());
    return marker;
}

template<class Config> bool cancelled(const Config& config) {
    return config.cancellation && config.cancellation->load();
}

template<class Fields>
std::optional<std::string_view> accountField(const Fields& fields, std::string_view key) {
    const auto field = fields.find(key);
    if (field == fields.end()) return std::nullopt;
    auto value = field->second;
    if (value.size() != 38 || value.front() != '"' || value.back() != '"') return std::nullopt;
    value.remove_prefix(1); value.remove_suffix(1);
    if (!DesktopApiClient::accountId(value)) return std::nullopt;
    return value;
}

constexpr std::size_t kMaxJsonResponseBytes = 2 * 1024 * 1024;

template<class String = std::string>
std::optional<String> jsonStringField(std::string_view json, std::string_view key) {
    const auto marker = fieldMarker<String>(key, "\":\"");
    const auto start = json.find(marker);
    if (start == std::string_view::npos) return std::nullopt;
    const auto valueStart = start + marker.size();
    String value;
    bool escaped = false;
    for (std::size_t index = valueStart; index < json.size(); ++index) {
        const auto character = json[index];
        if (escaped) {
            value += character;
            escaped = false;
        } else if (character == '\\') {
            escaped = true;
        } else if (character == '"') {
            return value;
        } else {
            value += character;
        }
    }
    return std::nullopt;
}

template<class String = std::string>
std::optional<std::uint64_t> jsonNumberField(std::string_view json, std::string_view key) {
    const auto marker = fieldMarker<String>(key, "\":");
    const auto start = json.find(marker);
    if (start == std::string_view::npos) return std::nullopt;
    const auto valueStart = start + marker.size();
    const auto valueEnd = json.find_first_not_of("0123456789", valueStart);
    if (valueEnd == valueStart) return std::nullopt;
    const auto end = valueEnd == std::string_view::npos ? json.size() : valueEnd;
    auto delimiter = end;
    while (delimiter < json.size() && std::isspace(static_cast<unsigned char>(json[delimiter]))) ++delimiter;
    if (delimiter < json.size() && json[delimiter] != ',' && json[delimiter] != '}') return std::nullopt;
    std::uint64_t value = 0;
    const auto parsed = std::from_chars(json.data() + valueStart, json.data() + end, value);
    if (parsed.ec != std::errc{} || parsed.ptr != json.data() + end) return std::nullopt;
    return value;
}

std::optional<std::uint64_t> jsonTrackNumber(std::string_view json, std::string_view track,
                                              std::string_view field) {
    const auto marker = std::string("\"") + std::string(track) + "\":{";
    const auto start = json.find(marker);
    if (start == std::string_view::npos) return std::nullopt;
    const auto end = json.find('}', start + marker.size());
    if (end == std::string_view::npos) return std::nullopt;
    return jsonNumberField(json.substr(start + marker.size(), end - start - marker.size()), field);
}

bool isSha256(std::string_view value) noexcept {
    if (value.size() != 64) return false;
    for (const auto character : value) {
        if (!std::isdigit(static_cast<unsigned char>(character)) &&
            (character < 'a' || character > 'f')) return false;
    }
    return true;
}

bool isSafeIdentifier(std::string_view value) noexcept {
    if (value.empty() || value.size() > 300) return false;
    for (const auto character : value) {
        if (!std::isalnum(static_cast<unsigned char>(character)) && character != '-' && character != '_') {
            return false;
        }
    }
    return true;
}

std::string readBoundedText(const std::filesystem::path& path, std::size_t maxBytes) {
    std::ifstream input(path, std::ios::binary);
    if (!input) return {};
    input.seekg(0, std::ios::end);
    const auto size = input.tellg();
    if (size < 0 || static_cast<std::uintmax_t>(size) > maxBytes) return {};
    input.seekg(0, std::ios::beg);
    std::string result(static_cast<std::size_t>(size), '\0');
    input.read(result.data(), static_cast<std::streamsize>(result.size()));
    return input.good() || input.eof() ? result : std::string{};
}

template<class String> struct BasicLocalTrack {
    String role;
    std::conditional_t<std::is_same_v<String, CustodyString>, std::nullptr_t, std::filesystem::path> path;
    String codec;
    std::uint32_t sampleRate = 1;
    std::uint32_t channels = 1;
    std::uint32_t durationSeconds = 1;
    std::uint64_t bytes = 0;
    String sha256;
#ifdef _WIN32
    IStream* stream = nullptr; // Borrowed from the proof held through uploadPrepared.
#endif
};
using LocalTrack = BasicLocalTrack<std::string>;
template<class String, class Value> using UploadVector = std::conditional_t<
    std::is_same_v<String, CustodyString>, CustodyVector<Value>, std::vector<Value>>;

template<class String, class Integer> void appendNumber(String& target, Integer value) {
    char digits[24];
    const auto end = std::to_chars(std::begin(digits), std::end(digits), value);
    target.append(digits, static_cast<std::size_t>(end.ptr - digits));
}

template<class String> String digestHex(const std::array<std::uint8_t, 32>& digest) {
    String hex(64, '\0');
    for (std::size_t i = 0; i < digest.size(); ++i) {
        hex[i * 2] = "0123456789abcdef"[digest[i] >> 4];
        hex[i * 2 + 1] = "0123456789abcdef"[digest[i] & 15];
    }
    return hex;
}

std::optional<std::vector<LocalTrack>> packageTracks(const UploadCustodyItem& item, std::uint32_t* durationSeconds,
                                                     std::uint64_t* startedAtMs = nullptr,
                                                     std::uint64_t* stoppedAtMs = nullptr,
                                                     int* displayOffsetMinutes = nullptr) {
    const auto snapshot = LocalRecordingPackage::inspect(item.packageDirectory);
    if (snapshot.integrity != PackageIntegrity::valid) return std::nullopt;
    // The snapshot already validated the wall-clock bounds, including rejecting
    // an impossible pair, so they are taken from it rather than re-read here.
    if (startedAtMs != nullptr) *startedAtMs = snapshot.startedAtMs;
    if (stoppedAtMs != nullptr) *stoppedAtMs = snapshot.stoppedAtMs;
    if (displayOffsetMinutes != nullptr) *displayOffsetMinutes = snapshot.displayTimezoneOffsetMinutes;
    const auto manifestPath = item.packageDirectory / "manifest.json";
    const auto manifest = readBoundedText(manifestPath, 256 * 1024);
    if (manifest.empty()) return std::nullopt;
    const auto durationMs = jsonNumberField(manifest, "duration_ms");
    const auto mediaBytes = jsonTrackNumber(manifest, "media", "bytes");
    const auto playbackBytes = jsonTrackNumber(manifest, "playback", "bytes");
    const auto mediaDigest = jsonStringField(manifest, "sha256");
    if (!durationMs || !mediaBytes || !playbackBytes || !mediaDigest || !isSha256(*mediaDigest)) return std::nullopt;
    const auto playbackDigestMarker = manifest.find("\"playback\"");
    if (playbackDigestMarker == std::string_view::npos) return std::nullopt;
    const auto playbackDigest = jsonStringField(manifest.substr(playbackDigestMarker), "sha256");
    if (!playbackDigest || !isSha256(*playbackDigest)) return std::nullopt;
    const auto manifestSize = std::filesystem::file_size(manifestPath);
    const auto mediaPath = item.packageDirectory / "meeting-transcription.wav";
    const auto playbackPath = item.packageDirectory / "meeting-review.m4a";
    std::error_code error;
    if (std::filesystem::file_size(mediaPath, error) != *mediaBytes || error) return std::nullopt;
    error.clear();
    if (std::filesystem::file_size(playbackPath, error) != *playbackBytes || error) return std::nullopt;
    if (durationMs.value() == 0 || durationMs.value() > 24ULL * 60 * 60 * 1000) return std::nullopt;
    *durationSeconds = static_cast<std::uint32_t>((durationMs.value() + 999) / 1000);
    const auto manifestDigest = sha256File(manifestPath);
    if (!isSha256(manifestDigest)) return std::nullopt;
    return std::vector<LocalTrack>{
        {"manifest", manifestPath, "json", 1, 1, 1, manifestSize, manifestDigest},
        {"media", mediaPath, "wav-pcm-s16le", 16'000, 1, *durationSeconds, *mediaBytes, *mediaDigest},
        {"playback", playbackPath, "m4a-aac-lc", 48'000, 1, *durationSeconds, *playbackBytes, *playbackDigest},
    };
}

#ifdef _WIN32
CustodyWideString utf8ToWide(std::string_view value) {
    if (value.empty() || value.size() > static_cast<std::size_t>(std::numeric_limits<int>::max())) return {};
    const auto length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
        static_cast<int>(value.size()), nullptr, 0);
    if (length <= 0) return {};
    CustodyWideString result(static_cast<std::size_t>(length), L'\0');
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()),
                            result.data(), length) != length) return {};
    return result;
}

// A response header that must be ASCII digits and nothing else. macOS reads the
// same header with the same rule, so a decorated or localized value is not a
// deadline on either platform.
#endif

std::optional<std::int64_t> parseEpochSeconds(std::string_view raw) {
    if (raw.empty() || raw.size() > 19) return std::nullopt;
    std::int64_t value = 0;
    for (const char character : raw) {
        if (character < '0' || character > '9') return std::nullopt;
        const auto digit = character - '0';
        if (value > (std::numeric_limits<std::int64_t>::max() - digit) / 10) return std::nullopt;
        value = value * 10 + digit;
    }
    return value;
}

struct ByteRange {
    std::uint64_t start = 0;
    std::uint64_t end = 0;
};

template<class String = std::string>
std::optional<std::string_view> jsonObjectField(std::string_view json, std::string_view key) {
    const auto marker = fieldMarker<String>(key, "\":");
    const auto markerStart = json.find(marker);
    if (markerStart == std::string_view::npos) return std::nullopt;
    const auto start = markerStart + marker.size();
    if (start >= json.size() || json[start] != '{') return std::nullopt;
    std::size_t depth = 0;
    bool quoted = false;
    bool escaped = false;
    for (std::size_t index = start; index < json.size(); ++index) {
        const auto character = json[index];
        if (escaped) { escaped = false; continue; }
        if (quoted && character == '\\') { escaped = true; continue; }
        if (character == '\"') { quoted = !quoted; continue; }
        if (quoted) continue;
        if (character == '{') ++depth;
        if (character == '}' && depth > 0 && --depth == 0) {
            return json.substr(start, index - start + 1);
        }
    }
    return std::nullopt;
}

#ifdef _WIN32
template<class Response = HttpResponse, class Config = DesktopHttpConfig>
Response request(const Config& config, const CustodyWideString& method, const CustodyWideString& path,
                     std::string_view body, bool jsonBody, std::string_view idempotencyKey = {},
                     std::optional<std::uint64_t> byteOffset = std::nullopt,
                     std::string_view contentSha256 = {},
                     std::optional<std::chrono::steady_clock::time_point> operationDeadline = {},
                     std::chrono::steady_clock::time_point (*now)() = std::chrono::steady_clock::now) {
    Response result;
    if (body.size() > std::numeric_limits<DWORD>::max()) { result.transportFailed = true; return result; }
    const auto deadline = operationDeadline.value_or(now() + std::chrono::seconds(30));
    const auto active = [&] { return !cancelled(config) && (!operationDeadline || now() < deadline); };
    // Synchronous handles belong to this worker. Cancellation never closes a
    // handle from another thread; a late OS completion is discarded instead.
    const auto phase = [&](auto call, HINTERNET timeoutHandle = nullptr) {
        if (result.transportFailed || !active()) { result.transportFailed = true; return false; }
        if (operationDeadline && timeoutHandle) {
            const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - now()).count();
            const auto budget = static_cast<int>(std::clamp<std::int64_t>(remaining, 1, 15'000));
            if (!WinHttpSetTimeouts(timeoutHandle, std::min(budget, 5'000), std::min(budget, 5'000),
                std::min(budget, 10'000), std::min(budget, 10'000)) || !active()) {
                result.transportFailed = true; return false;
            }
        }
        const bool success = call();
        if (!active()) { result.transportFailed = true; return false; }
        return success;
    };
    if (!active()) { result.transportFailed = true; return result; }
    auto url = utf8ToWide(config.baseOrigin);
    if (url.empty()) { result.transportFailed = true; return result; }
    URL_COMPONENTS components{};
    components.dwStructSize = sizeof(components);
    components.dwSchemeLength = static_cast<DWORD>(-1);
    components.dwHostNameLength = static_cast<DWORD>(-1);
    components.dwUrlPathLength = static_cast<DWORD>(-1);
    if (!phase([&] { return WinHttpCrackUrl(url.data(), 0, 0, &components) != FALSE; }) ||
        components.nScheme != INTERNET_SCHEME_HTTPS || components.lpszHostName == nullptr) {
        result.transportFailed = true;
        return result;
    }
    HINTERNET session = nullptr;
    using HandleOwner = std::unique_ptr<void, decltype(&WinHttpCloseHandle)>;
    HandleOwner sessionOwner(nullptr, WinHttpCloseHandle), connectionOwner(nullptr, WinHttpCloseHandle),
        requestOwner(nullptr, WinHttpCloseHandle);
    const bool opened = phase([&] {
        sessionOwner.reset(WinHttpOpen(L"GRAF/Feature200", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
                                      WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0));
        session = sessionOwner.get();
        return session != nullptr;
    });
    if (!opened) {
        result.transportFailed = true; return result;
    }
    if (!phase([&] { return operationDeadline ? true :
            WinHttpSetTimeouts(session, 5'000, 5'000, 10'000, 10'000) != FALSE; }, session)) {
        result.transportFailed = true;
        return result;
    }
    const CustodyWideString host(components.lpszHostName, components.dwHostNameLength);
    HINTERNET connection = nullptr, handle = nullptr;
    const bool connected = phase([&] {
        connectionOwner.reset(WinHttpConnect(session, host.c_str(), components.nPort, 0));
        connection = connectionOwner.get();
        return connection != nullptr;
    }, session);
    const bool requested = connected && phase([&] {
        requestOwner.reset(WinHttpOpenRequest(connection, method.c_str(), path.c_str(), nullptr,
                                            WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE));
        handle = requestOwner.get();
        return handle != nullptr;
    }, session);
    if (!requested) {
        result.transportFailed = true;
        return result;
    }
    // Native session-header transport does not inherit browser cookies or
    // follow redirects carrying authentication to another endpoint/origin.
    DWORD disabled = WINHTTP_DISABLE_REDIRECTS | WINHTTP_DISABLE_COOKIES;
    if (!phase([&] { return WinHttpSetOption(handle, WINHTTP_OPTION_DISABLE_FEATURE,
                                           &disabled, sizeof(disabled)) != FALSE; }, handle)) {
        result.transportFailed = true;
        return result;
    }
    CustodyWideString headers = L"Accept: application/json\r\n";
    const auto appendHeader = [&](std::wstring_view name, std::string_view value) {
        headers.append(name.data(), name.size()); headers.append(L": ");
        const auto wide = utf8ToWide(value);
        headers.append(wide.data(), wide.size()); headers.append(L"\r\n");
    };
    appendHeader(L"X-Client-Version", config.clientVersion);
    if (!config.workspaceId.empty()) {
        appendHeader(L"X-Workspace-Id", config.workspaceId);
    }
    if (!config.workspaceId.empty() && !config.deviceId.empty()) {
        appendHeader(L"X-Device-Id", config.deviceId);
    }
    if (!idempotencyKey.empty()) appendHeader(L"Idempotency-Key", idempotencyKey);
    if (byteOffset) {
        char digits[20];
        const auto formatted = std::to_chars(std::begin(digits), std::end(digits), *byteOffset);
        appendHeader(L"X-Byte-Offset", std::string_view(digits, static_cast<std::size_t>(formatted.ptr - digits)));
    }
    if (!contentSha256.empty()) appendHeader(L"X-Content-SHA256", contentSha256);
    if (!config.sessionToken.empty()) appendHeader(L"X-Auth-Session", config.sessionToken);
    // A scoped mutation declares which account it is for. Both identifiers are
    // validated before they are serialized, so a malformed scope cannot travel
    // as a header the server would read as permission for another actor.
    if (config.scopedAccount) {
        const auto scoped = DesktopApiClient::scopedAccountHeaders(*config.scopedAccount);
        if (scoped) {
            for (const auto& header : *scoped) {
                const auto name = utf8ToWide(header.first);
                appendHeader(std::wstring_view(name.data(), name.size()), header.second);
            }
        }
    }
    headers += jsonBody ? L"Content-Type: application/json\r\n" : L"Content-Type: application/octet-stream\r\n";
    const auto sent = phase([&] { return WinHttpSendRequest(handle, headers.c_str(), static_cast<DWORD>(headers.size()),
        body.empty() ? WINHTTP_NO_REQUEST_DATA : const_cast<char*>(body.data()), static_cast<DWORD>(body.size()),
        static_cast<DWORD>(body.size()), 0) != FALSE; }, handle);
    if (!sent || !phase([&] { return WinHttpReceiveResponse(handle, nullptr) != FALSE; }, handle)) {
        result.transportFailed = true;
    } else {
        DWORD statusSize = sizeof(result.status);
        if (!phase([&] { return WinHttpQueryHeaders(handle, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                WINHTTP_HEADER_NAME_BY_INDEX, &result.status, &statusSize, WINHTTP_NO_HEADER_INDEX) != FALSE; }, handle))
            result.transportFailed = true;
        // The header is read only so the scheduler can wait as long as the server
        // asked; it never changes what the response means.
        DWORD retrySize = 0;
        phase([&] { return WinHttpQueryHeaders(handle, WINHTTP_QUERY_CUSTOM, L"Retry-After",
            WINHTTP_NO_OUTPUT_BUFFER, &retrySize, WINHTTP_NO_HEADER_INDEX) != FALSE; }, handle);
        if (retrySize > sizeof(wchar_t) && retrySize <= 256) {
            CustodyWideString raw(retrySize / sizeof(wchar_t), L'\0');
            if (phase([&] { return WinHttpQueryHeaders(handle, WINHTTP_QUERY_CUSTOM, L"Retry-After", raw.data(), &retrySize,
                                    WINHTTP_NO_HEADER_INDEX) != FALSE; }, handle)) {
                raw.resize(CustodyWideString::traits_type::length(raw.c_str()));
                // Only ASCII digits are usable; anything else is left empty so the
                // client falls back to the macOS default instead of guessing.
                bool usable = !raw.empty();
                for (const auto character : raw) {
                    if (character < 0x20 || character > 0x7e) { usable = false; break; }
                }
                if (usable) {
                    result.retryAfter.reserve(raw.size());
                    for (const auto character : raw) result.retryAfter.push_back(static_cast<char>(character));
                }
            }
        }
        // The server renewed its session while answering, and the deadline it
        // names is what the cabinet's own cookie has to learn. The header is read
        // the same way macOS reads it: digits only, or nothing at all.
        DWORD expirySize = 0;
        phase([&] { return WinHttpQueryHeaders(handle, WINHTTP_QUERY_CUSTOM, L"X-GRAF-Auth-Expires-At",
            WINHTTP_NO_OUTPUT_BUFFER, &expirySize, WINHTTP_NO_HEADER_INDEX) != FALSE; }, handle);
        if (expirySize > sizeof(wchar_t) && expirySize <= 64) {
            CustodyWideString raw(expirySize / sizeof(wchar_t), L'\0');
            if (phase([&] { return WinHttpQueryHeaders(handle, WINHTTP_QUERY_CUSTOM, L"X-GRAF-Auth-Expires-At", raw.data(), &expirySize,
                                    WINHTTP_NO_HEADER_INDEX) != FALSE; }, handle)) {
                raw.resize(CustodyWideString::traits_type::length(raw.c_str()));
                bool digestible = !raw.empty();
                for (const auto character : raw) {
                    if (character < L'0' || character > L'9') { digestible = false; break; }
                }
                if (digestible) {
                    result.authExpiresAt.reserve(raw.size());
                    for (const auto character : raw) result.authExpiresAt.push_back(static_cast<char>(character));
                }
            }
        }
        const auto maximum = operationDeadline ? 65536U : kMaxJsonResponseBytes;
        while (!result.transportFailed && (operationDeadline || result.body.size() < maximum)) {
            if (cancelled(config) || now() >= deadline) {
                result.transportFailed = true;
                break;
            }
            DWORD available = 0;
            if (!phase([&] { return WinHttpQueryDataAvailable(handle, &available) != FALSE; }, handle)) {
                result.transportFailed = true; break;
            }
            if (available == 0 && !operationDeadline) break;
            const auto remaining = maximum - result.body.size();
            if (operationDeadline && available > remaining) { result.transportFailed = true; break; }
            // At the inclusive calendar cap, still prove EOF with a bounded read.
            // A valid JSON prefix is never permission to ignore a trailing byte.
            if (operationDeadline && available == 0) {
                char tail = 0;
                DWORD read = 0;
                if (!phase([&] { return WinHttpReadData(handle, &tail, 1, &read) != FALSE; }, handle) || read > 1) {
                    result.transportFailed = true; break;
                }
                if (read == 0) break;
                if (remaining == 0) { result.transportFailed = true; break; }
                result.body.push_back(tail);
                continue;
            }
            const auto count = std::min<std::size_t>(available, remaining);
            const auto start = result.body.size();
            result.body.resize(start + count);
            DWORD read = 0;
            if (!phase([&] { return WinHttpReadData(handle, result.body.data() + start,
                    static_cast<DWORD>(count), &read) != FALSE; }, handle) || read > count) {
                result.transportFailed = true;
                break;
            }
            result.body.resize(start + read);
            if (read == 0) break;
        }
        if (!operationDeadline && result.body.size() == maximum) result.transportFailed = true;
    }
    if (!active()) result.transportFailed = true;
    requestOwner.reset();
    connectionOwner.reset();
    sessionOwner.reset();
    if (!active()) result.transportFailed = true;
    return result;
}

template<class Response = HttpResponse, class Config = DesktopHttpConfig,
    class Request = DesktopHttpTransport::UploadRequest>
Response sendUploadRequest(const Config& config, const Request& call) {
    // Own bytes until request() has received the response or closed all native
    // handles, including stack unwinding. Cancellation never releases this early.
    const auto held = call.protectedBody;
    const auto body = call.bodyView();
    if (!body) return {0, {}, true};
    return request<Response>(config, utf8ToWide(call.method), utf8ToWide(call.path), *body, call.jsonBody,
                   call.idempotencyKey, call.byteOffset, call.contentSha256);
}

#endif

template<class Response> DesktopTransportStatus mapResponse(const Response& response) {
    if (response.transportFailed || response.status == 408 || response.status == 429 || response.status >= 500) {
        return DesktopTransportStatus::retryableFailure;
    }
    if (response.status == 401 || response.status == 403) return DesktopTransportStatus::authRequired;
    if (response.status < 200 || response.status >= 300) return DesktopTransportStatus::serverRejected;
    return DesktopTransportStatus::uploaded;
}

template<class Result> void resetUploadStatus(Result& result, DesktopTransportStatus status) noexcept {
    result.status = status;
    result.safeReason.clear();
    result.retryClass.clear();
    result.retryAfterSeconds = 0;
    result.authExpiresAt.reset();
}

template<class Response, class Result> void uploadResponse(const Response& response, Result& result) {
    resetUploadStatus(result, mapResponse(response));
    result.retryAfterSeconds = DesktopHttpTransport::rateLimitPauseSeconds(response.status, response.retryAfter);
    result.authExpiresAt = parseEpochSeconds(response.authExpiresAt);
    // Only these two root codes on a fully received HTTP 400 are permanent.
    // Validate the whole bounded document; never retain title/detail or match a
    // substring/nested/duplicate key as authority.
    if (!response.transportFailed && response.status == 400) {
        const auto fields = UploadJsonReader<typename Result::StringType>(response.body).read();
        if (fields) {
            const auto code = fields->find("code");
            if (code != fields->end() &&
                (code->second == "\"unsupported_recording_source_kind\"" ||
                 code->second == "\"invalid_recording_source_mode\"")) {
                result.safeReason = code->second.substr(1, code->second.size() - 2);
                result.retryClass = "not_retryable";
            }
        }
    }
}

std::size_t trackIndex(std::string_view role) {
    if (role == "manifest") return 0;
    if (role == "media") return 1;
    return 2;
}

template<class String = std::string>
std::optional<std::array<std::uint64_t, 3>> acceptedBytes(std::string_view json) {
    const auto object = jsonObjectField<String>(json, "accepted_bytes_by_track");
    if (!object) return std::nullopt;
    std::array<std::uint64_t, 3> result{};
    for (const auto role : {std::string_view("manifest"), std::string_view("media"), std::string_view("playback")}) {
        const auto value = jsonNumberField<String>(*object, role);
        result[trackIndex(role)] = value.value_or(0);
    }
    return result;
}

template<class String = std::string>
std::optional<std::array<UploadVector<String, ByteRange>, 3>> missingRanges(std::string_view json) {
    const auto object = jsonObjectField<String>(json, "missing_ranges_by_track");
    if (!object) return std::nullopt;
    std::array<UploadVector<String, ByteRange>, 3> result;
    for (const auto role : {std::string_view("manifest"), std::string_view("media"), std::string_view("playback")}) {
        const auto marker = fieldMarker<String>(role, "\":[");
        const auto markerStart = object->find(marker);
        if (markerStart == std::string_view::npos) continue;
        auto cursor = markerStart + marker.size();
        while (cursor < object->size() && (*object)[cursor] != ']') {
            while (cursor < object->size() && std::isspace(static_cast<unsigned char>((*object)[cursor]))) ++cursor;
            if (cursor < object->size() && (*object)[cursor] == ',') ++cursor;
            while (cursor < object->size() && std::isspace(static_cast<unsigned char>((*object)[cursor]))) ++cursor;
            if (cursor >= object->size() || (*object)[cursor] != '{') return std::nullopt;
            const auto end = object->find('}', cursor + 1);
            if (end == std::string_view::npos) return std::nullopt;
            const auto rangeObject = object->substr(cursor, end - cursor + 1);
            const auto start = jsonNumberField<String>(rangeObject, "start");
            const auto finish = jsonNumberField<String>(rangeObject, "end");
            if (!start || !finish || *finish <= *start) return std::nullopt;
            result[trackIndex(role)].push_back({*start, *finish});
            cursor = end + 1;
        }
        if (cursor >= object->size() || (*object)[cursor] != ']') return std::nullopt;
    }
    return result;
}

template<class String = std::string>
std::optional<String> nestedStringField(std::string_view json, std::string_view objectKey,
                                             std::string_view field) {
    const auto object = jsonObjectField<String>(json, objectKey);
    if (!object) return std::nullopt;
    return jsonStringField<String>(*object, field);
}

// Server statuses are compared the way the macOS client compares them: case and
// surrounding whitespace must not decide whether accepted media is re-uploaded.
template<class String> String normalizedStatus(String value) {
    const auto notSpace = [](unsigned char character) { return std::isspace(character) == 0; };
    const auto first = std::find_if(value.begin(), value.end(), notSpace);
    const auto last = std::find_if(value.rbegin(), value.rend(), notSpace).base();
    if (first >= last) return String{};
    String result(std::string_view(value.data() + (first - value.begin()), static_cast<std::size_t>(last - first)));
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char character) { return static_cast<char>(std::tolower(character)); });
    return result;
}

template<class String>
std::optional<BasicDesktopRemoteUploadState<String>> decodeSyncStateUsing(
    std::string_view json, std::string_view localRecordingId) {
    const auto meetingId = nestedStringField<String>(json, "meeting", "meeting_id");
    if (!meetingId || !isSafeIdentifier(*meetingId)) return std::nullopt;
    BasicDesktopRemoteUploadState<String> result;
    result.meetingId = *meetingId;
    result.truth.localRecordingId.assign(localRecordingId.data(), localRecordingId.size());
    result.truth.meetingExists = true;
    result.truth.meetingId = *meetingId;
    if (const auto session = jsonObjectField<String>(json, "upload_session")) {
        if (const auto id = jsonStringField<String>(*session, "session_id")) {
            if (!isSafeIdentifier(*id)) return std::nullopt;
            result.sessionId = *id;
            result.truth.uploadSessionExists = true;
        }
        if (const auto status = jsonStringField<String>(*session, "status")) result.sessionStatus = *status;
        if (const auto accepted = acceptedBytes<String>(*session)) result.truth.acceptedBytes = *accepted;
    }
    // The server's own fingerprint: which revision it accepted, which session
    // carries it and how far the meeting and its processing have come. macOS
    // keeps the same values in its queue row.
    if (const auto revision = jsonObjectField<String>(json, "media_revision")) {
        if (const auto id = jsonStringField<String>(*revision, "media_revision_id"))
            result.truth.mediaRevisionId = *id;
        // The revision status is a lifecycle state of its own; it is kept as the
        // server names it and never guessed from the upload session.
        if (const auto status = jsonStringField<String>(*revision, "status"))
            result.truth.mediaRevisionStatus = normalizedStatus(*status);
    }
    if (result.truth.uploadSessionExists) result.truth.uploadSessionId = result.sessionId;
    if (const auto meetingStatus = nestedStringField<String>(json, "meeting", "status"))
        result.truth.serverStatus = normalizedStatus(*meetingStatus);
    if (const auto processing = jsonObjectField<String>(json, "processing")) {
        if (const auto status = jsonStringField<String>(*processing, "status"))
            result.truth.processingStatus = normalizedStatus(*status);
    }
    const auto conflictState = nestedStringField<String>(json, "conflict", "state");
    if (!conflictState) return std::nullopt;
    // The server owns the retry classification. The Windows port records it and
    // lets the scheduler act on it instead of retrying every conflict blindly.
    if (const auto custody = jsonObjectField<String>(json, "custody")) {
        if (const auto retryClass = jsonStringField<String>(*custody, "retry_class"))
            result.retryClass = normalizedStatus(*retryClass);
    }
    // The server drops terminal upload sessions from its active selection, so a
    // finalize whose response was lost comes back as no session at all. The
    // meeting status is then the only server-owned evidence that this revision
    // was already accepted. Without it the client creates a second session for
    // an immutable revision, gets media_revision_immutable and burns its retry
    // budget instead of moving the item to uploaded. The accepted statuses are
    // the same ones the macOS client treats as finalized.
    const auto meetingStatus = nestedStringField<String>(json, "meeting", "status");
    const bool meetingFinalized = meetingStatus.has_value() &&
        (normalizedStatus(*meetingStatus) == "ingested_pending_processing" ||
         normalizedStatus(*meetingStatus) == "degraded");
    const bool finalized = meetingFinalized ||
        (result.truth.uploadSessionExists &&
         (normalizedStatus(result.sessionStatus) == "finalized" ||
          normalizedStatus(result.sessionStatus) == "degraded"));
    // Processing is a separate lifecycle: a lost finalize response must not
    // turn already accepted media back into an upload retry.
    const bool processingOnly = *conflictState == "processing_failed" || *conflictState == "processing_blocked";
    const bool uploadConflict = *conflictState == "none" || *conflictState == "upload_session_expired";
    result.needsNewUploadSession = uploadConflict && !finalized &&
        (*conflictState == "upload_session_expired" || result.sessionStatus == "expired");
    result.blockedByConflict = *conflictState != "none" &&
        !result.needsNewUploadSession && !(processingOnly && finalized);
    result.truth.finalized = finalized && !result.blockedByConflict;
    return result;
}

} // namespace

std::optional<DesktopRemoteUploadState> DesktopHttpTransport::decodeSyncState(
    std::string_view json, std::string_view localRecordingId) {
    return decodeSyncStateUsing<std::string>(json, localRecordingId);
}

namespace {

template<class Response> bool isUnknownRecording(const Response& response) {
    if (response.status != 404) return false;
    const auto code = jsonStringField<typename Response::StringType>(response.body, "code");
    return code && *code == "recording_not_found";
}

template<class Config, class Send, class String, class Result>
DesktopTransportStatus uploadFile(const Config& config, const Send& send,
                                  const BasicLocalTrack<String>& track, std::string_view sessionId,
                                  const UploadVector<String, ByteRange>& ranges,
                                  std::array<std::uint64_t, 3>* accepted, Result& result) {
    const auto finish = [&result](DesktopTransportStatus status) noexcept {
        resetUploadStatus(result, status);
        return status;
    };
    try {
        std::optional<std::ifstream> input;
#ifdef _WIN32
        if (!track.stream)
#endif
        {
            if constexpr (std::is_same_v<String, CustodyString>) {
                return finish(DesktopTransportStatus::invalidPackage);
            } else {
                input.emplace(track.path, std::ios::binary);
                if (!*input || !isSha256(track.sha256) || sha256File(track.path) != track.sha256)
                    return finish(DesktopTransportStatus::invalidPackage);
            }
        }
        const auto partSize = std::clamp(config.partSizeBytes, std::size_t(64 * 1024), kMaxPartBytes);
        for (const auto range : ranges) {
            if (range.end <= range.start || range.end > track.bytes)
                return finish(DesktopTransportStatus::serverRejected);
            for (std::uint64_t offset = range.start; offset < range.end;) {
                if (cancelled(config)) return finish(DesktopTransportStatus::retryableFailure);
                const auto length = static_cast<std::size_t>(std::min<std::uint64_t>(partSize, range.end - offset));
                String path("/api/v1/upload-sessions/");
                path.append(sessionId.data(), sessionId.size()); path += "/tracks/";
                path += track.role; path += "/parts/"; appendNumber(path, offset / partSize);
                typename DesktopHttpTransport::BasicUploadRequest<String> call{"PUT", path, "", false, {}, offset};
#ifdef _WIN32
                if (track.stream) {
                    auto bytes = std::allocate_shared<CustodyBytes>(CustodyAllocator<CustodyBytes>{}, length);
                    LARGE_INTEGER at{}; at.QuadPart = static_cast<LONGLONG>(offset);
                    if (cancelled(config) || FAILED(track.stream->Seek(at, STREAM_SEEK_SET, nullptr)))
                        return finish(DesktopTransportStatus::retryableFailure);
                    for (std::size_t filled = 0; filled < length;) {
                        const auto count = static_cast<ULONG>(std::min<std::size_t>(256 * 1024, length - filled));
                        ULONG got = 0;
                        if (cancelled(config)) return finish(DesktopTransportStatus::retryableFailure);
                        const auto hr = track.stream->Read(bytes->data() + filled, count, &got);
                        if (cancelled(config) || FAILED(hr)) return finish(DesktopTransportStatus::retryableFailure);
                        if (hr != S_OK || got != count) return finish(DesktopTransportStatus::invalidPackage);
                        filled += got;
                    }
                    call.protectedBody = std::move(bytes); // No mutable alias survives dispatch.
                } else
#endif
                {
                    call.body.resize(length);
                    input->clear(); input->seekg(static_cast<std::streamoff>(offset), std::ios::beg);
                    input->read(call.body.data(), static_cast<std::streamsize>(length));
                    if (input->gcount() != static_cast<std::streamsize>(length))
                        return finish(DesktopTransportStatus::invalidPackage);
                }
                if (cancelled(config)) return finish(DesktopTransportStatus::retryableFailure);
                call.contentSha256 = digestHex<String>(sha256Digest(*call.bodyView()));
                const auto response = send(config, call);
                uploadResponse(response, result);
                if (result.status != DesktopTransportStatus::uploaded) return result.status;
                const auto acceptedOffset = jsonNumberField<typename Result::StringType>(response.body, "byte_offset");
                const auto acceptedLength = jsonNumberField<typename Result::StringType>(response.body, "byte_length");
                if (!acceptedOffset || !acceptedLength || *acceptedOffset != offset || *acceptedLength != length) {
                    return finish(DesktopTransportStatus::serverRejected);
                }
                if (accepted != nullptr) (*accepted)[trackIndex(track.role)] += *acceptedLength;
                offset += length;
            }
        }
        return finish(DesktopTransportStatus::uploaded);
    } catch (const std::bad_alloc&) {
        return finish(DesktopTransportStatus::retryableFailure);
    }
}

} // namespace

std::optional<std::int64_t> DesktopHttpTransport::epochSecondsFromHeader(std::string_view raw) {
    return parseEpochSeconds(raw);
}

std::uint32_t DesktopHttpTransport::rateLimitPauseSeconds(std::uint32_t status, std::string_view retryAfter) {
    // Only a rate limit is a request to wait. An unavailable endpoint keeps the
    // client's own schedule, which is what macOS does as well.
    if (status != 429) return 0;
    // macOS reads the same header and falls back to 60 s, so a value this client
    // cannot read must never turn into "retry immediately".
    constexpr std::uint32_t fallback = 60;
    constexpr std::uint32_t maximum = 24 * 60 * 60;
    if (retryAfter.empty()) return fallback;
    std::uint64_t seconds = 0;
    for (const auto character : retryAfter) {
        if (character < '0' || character > '9') return fallback;
        seconds = seconds * 10 + static_cast<std::uint64_t>(character - '0');
        if (seconds >= maximum) return maximum;
    }
    // "Retry-After: 0" is not a pause, and the server may not mean "now".
    if (seconds == 0) return fallback;
    return static_cast<std::uint32_t>(seconds);
}

DesktopHttpTransport::DesktopHttpTransport(DesktopHttpConfig config)
    : config_(std::move(config)) {
    config_.partSizeBytes = std::clamp(config_.partSizeBytes, std::size_t(64 * 1024), kMaxPartBytes);
}

namespace {
template<class Reader, class String = std::string>
std::optional<BasicDesktopAccountIdentity<String>> decodeAccountIdentityUsing(std::string_view json) {
    const auto fields = Reader(json).read();
    if (!fields) return std::nullopt;
    const auto user = accountField(*fields, "user_id"), workspace = accountField(*fields, "workspace_id"),
               session = accountField(*fields, "active_session_id");
    if (!user || !workspace || !session) return std::nullopt;
    return BasicDesktopAccountIdentity<String>{String(*user), String(*workspace)};
}

template<class Reader, class String = std::string>
std::optional<String> decodeActiveWorkspaceUsing(std::string_view json) {
    const auto fields = Reader(json).read();
    if (!fields) return std::nullopt;
    const auto spaces = fields->find("spaces");
    if (spaces == fields->end()) return std::nullopt;
    const auto rows = Reader(spaces->second).readArray();
    if (!rows) return std::nullopt;
    using Keys = typename Reader::RawKeys;
    Keys ids(std::less<std::string_view>{}, typename Keys::allocator_type{});
    std::optional<String> workspace;
    for (const auto row : *rows) {
        const auto entry = Reader(row).read();
        if (!entry) return std::nullopt;
        const auto id = accountField(*entry, "id");
        const auto active = entry->find("active");
        if (!id || !ids.insert(*id).second || active == entry->end() ||
            (active->second != "true" && active->second != "false")) return std::nullopt;
        if (active->second == "true") {
            if (workspace) return std::nullopt;
            workspace = String(*id);
        }
    }
    return workspace;
}

template<class Reader, class String = std::string, class Config, class Get>
DesktopHttpTransport::BasicIdentityResult<String> resolveAccountIdentityUsing(
    const Config& confirmed, const Get& get) {
    if (cancelled(confirmed)) return {std::nullopt, DesktopTransportStatus::retryableFailure};
    // The shell confirms the account once for the session it holds. Asking again
    // for every attempt adds a request the server has already answered and gives
    // a rate limiter one more reason to answer 429. The snapshot is not authority
    // on its own: it must still describe a real account and agree with the
    // workspace it travels with, and it is cleared on any session change.
    if (confirmed.confirmedIdentity) {
        const auto& identity = *confirmed.confirmedIdentity;
        if (!DesktopApiClient::accountId(identity.userId) || !DesktopApiClient::accountId(identity.workspaceId))
            return {};
        if (!confirmed.workspaceId.empty() && confirmed.workspaceId != identity.workspaceId) return {};
        return {BasicDesktopAccountIdentity<String>{String(std::string_view(identity.userId)),
            String(std::string_view(identity.workspaceId))}, DesktopTransportStatus::uploaded};
    }
    // The public legacy getter is nullable; the internal direct-send lambda is
    // always present. Check after the snapshot branch, preserving zero GETs.
    if constexpr (std::is_same_v<Get, DesktopHttpTransport::IdentityGet>) {
        if (!get) return {};
    }
    if (confirmed.sessionToken.empty() ||
        (!confirmed.workspaceId.empty() && !DesktopApiClient::accountId(confirmed.workspaceId))) return {};
    auto config = confirmed;
    config.deviceId.clear();
    DesktopHttpTransport::BasicIdentityResult<String> result;
    const auto read = [&](std::string_view path, auto decode) -> decltype(decode(std::string_view{})) {
        if (cancelled(config)) {
            result.status = DesktopTransportStatus::retryableFailure;
            return std::nullopt;
        }
        const auto response = get(config, path);
        if (cancelled(config) || response.transportFailed || response.status == 0 ||
            response.status == 408 || response.status == 429 || response.status >= 500) {
            result.status = DesktopTransportStatus::retryableFailure;
            return std::nullopt;
        }
        if (response.status != 200) return std::nullopt;
        // The response owns these bytes until decoding has finished. Only the
        // existing owning account DTO leaves this scope, never a borrowed view.
        return decode(std::string_view(response.body.data(), response.body.size()));
    };
    if (config.workspaceId.empty()) {
        const auto workspace = read("/desktop/settings/spaces", decodeActiveWorkspaceUsing<Reader, String>);
        if (!workspace) return result;
        config.workspaceId.assign(workspace->data(), workspace->size());
    }
    const auto identity = read("/api/v1/auth/me", decodeAccountIdentityUsing<Reader, String>);
    if (!identity) return result;
    if (std::string_view(identity->workspaceId) != std::string_view(config.workspaceId)) return {};
    return {identity, DesktopTransportStatus::uploaded};
}
} // namespace

std::optional<DesktopAccountIdentity> DesktopHttpTransport::decodeAccountIdentity(std::string_view json) {
    return decodeAccountIdentityUsing<json_detail::JsonReader<>>(json);
}

std::optional<std::string> DesktopHttpTransport::decodeActiveWorkspace(std::string_view json) {
    return decodeActiveWorkspaceUsing<json_detail::JsonReader<>>(json);
}

DesktopHttpTransport::IdentityResult DesktopHttpTransport::accountIdentity(const IdentityGet& get) const {
    return resolveAccountIdentity(config_, get);
}

DesktopHttpTransport::IdentityResult DesktopHttpTransport::resolveAccountIdentity(
    const DesktopHttpConfig& confirmed, const IdentityGet& get) {
    return resolveAccountIdentityUsing<json_detail::JsonReader<>>(confirmed, get);
}

namespace {
DesktopHttpTransport::IdentityResponse requestIdentity(const DesktopHttpConfig& config, std::string_view path) {
#ifdef _WIN32
    auto response = request(config, L"GET", utf8ToWide(path), "", true);
    return {response.status, std::move(response.body), response.transportFailed};
#else
    (void)config; (void)path;
    return {0, {}, true};
#endif
}

// One deletion-protocol call. Nothing is sent without a scope that names a real
// account: the server would read a request without the expected-account headers
// as an unscoped one, which is exactly the ambiguity the gate exists to remove.
template<class String, class Send>
BasicDesktopDeletionResponse<String> deletionCallValue(const BasicDesktopHttpConfig<String>& base,
    const BasicDeletionScope<String>& scope, std::string_view method, std::string_view path,
    std::string_view body, const Send& send) {
    BasicDesktopDeletionResponse<String> result;
    // The local refusals come first and read the same on every platform: a scope
    // that does not name a real account, or a session there is nothing to delete
    // with, is never sent.
    if (!DesktopApiClient::scopedAccountHeaders(scope)) {
        result.safeReason = "invalid_scope";
        return result;
    }
    if (base.sessionToken.empty()) {
        result.safeReason = "auth_required";
        return result;
    }
    auto config = base;
    config.scopedAccount = scope;
    typename DesktopHttpTransport::BasicUploadResponse<String> response;
    if (send) {
        typename DesktopHttpTransport::BasicUploadRequest<String> call;
        call.method = method; call.path = path; call.body = body;
        response = send(config, call);
    } else {
#ifdef _WIN32
        response = request<typename DesktopHttpTransport::BasicUploadResponse<String>>(
            config, utf8ToWide(method), utf8ToWide(path), body, true);
#else
        result.transportFailed = true; return result;
#endif
    }
    if (response.body.size() > kMaxJsonResponseBytes) { result.transportFailed = true; return result; }
    result.status = response.status;
    result.body = std::move(response.body);
    result.transportFailed = response.transportFailed;
    result.retryAfterSeconds = DesktopHttpTransport::rateLimitPauseSeconds(response.status, response.retryAfter);
    result.authExpiresAt = parseEpochSeconds(response.authExpiresAt);
    return result;
}
DesktopDeletionResponse deletionCall(const DesktopHttpConfig& base, const DeletionScope& scope,
    std::string_view method, std::string_view path, const std::string& body) {
    return deletionCallValue(base, scope, method, path, body, DesktopHttpTransport::UploadSend{});
}
// Only the named operations below can prepare a request. This helper does not
// expose arbitrary authenticated paths to a caller or trust an ack_url.
template<class Prepare>
std::shared_ptr<const ProtectedDeletionResponse> protectedDeletionCall(
    const ProtectedDesktopHttpConfig& config, bool readProtocolGate,
    const DesktopHttpTransport::ProtectedUploadSend& send, const Prepare& prepare) {
    std::shared_ptr<ProtectedDeletionResponse> result;
    try {
        result = std::allocate_shared<ProtectedDeletionResponse>(CustodyAllocator<ProtectedDeletionResponse>{});
        if (!config.cancellation || cancelled(config)) { result->safeReason = "connection"; return result; }
        if (!config.scopedAccount || !config.confirmedIdentity ||
            config.scopedAccount->userId != config.confirmedIdentity->userId ||
            config.scopedAccount->workspaceId != config.confirmedIdentity->workspaceId ||
            config.workspaceId != config.confirmedIdentity->workspaceId ||
            !DesktopApiClient::scopedAccountHeaders(*config.scopedAccount) ||
            !DesktopUploadQueueService::validServerOrigin(config.baseOrigin)) {
            result->safeReason = "invalid_scope"; return result;
        }
        DesktopHttpTransport::ProtectedUploadRequest call;
        const auto refusal = prepare(call);
        if (!refusal.empty()) { result->safeReason = refusal; return result; }
        std::optional<std::int64_t> expiry;
        if (readProtocolGate) {
            auto context = deletionCallValue(config, *config.scopedAccount, "GET", DesktopApiClient::notificationContextPath, {}, send);
            expiry = context.authExpiresAt;
            BasicDeletionWireResult<CustodyString> wire;
            wire.status = context.status; wire.body = std::move(context.body);
            wire.transportFailed = context.transportFailed; wire.waitReason = std::move(context.safeReason);
            const auto reason = DesktopUploadQueueService::deletionGateReason(wire, *config.confirmedIdentity, config.cancellation.get());
            if (!reason.empty()) {
                result->status = context.status; result->transportFailed = context.transportFailed;
                result->retryAfterSeconds = context.retryAfterSeconds; result->authExpiresAt = expiry;
                result->safeReason = reason; return result;
            }
        }
        if (cancelled(config)) { result->safeReason = "connection"; return result; }
        *result = deletionCallValue(config, *config.scopedAccount, call.method, call.path, call.body, send);
        if (!result->authExpiresAt) result->authExpiresAt = expiry;
    } catch (...) {
        if (result) { result->status = 0; result->body.clear(); result->transportFailed = true; }
    }
    return result;
}
} // namespace

std::shared_ptr<const ProtectedDeletionResponse> DesktopHttpTransport::deletionProtected(
    const ProtectedDesktopHttpConfig& config, const BasicDeletionRequestPlan<CustodyString>& entry,
    bool readProtocolGate, const ProtectedUploadSend& send) {
    return protectedDeletionCall(config, readProtocolGate, send, [&](auto& call) -> std::string_view {
        call.method = "POST";
        call.path = entry.target == DeletionTarget::meeting ?
            DesktopApiClient::meetingDeletionPath<CustodyString>(entry.targetId) :
            entry.target == DeletionTarget::ownOrigin ? DesktopApiClient::ownOriginDeletionPath<CustodyString>(entry.targetId) : CustodyString{};
        call.body = entry.target == DeletionTarget::meeting ? DesktopApiClient::meetingDeletionBody<CustodyString>() :
            DesktopApiClient::originCancellationBody<CustodyString>(entry.operationId);
        if (!DesktopApiClient::accountId(entry.operationId) || call.path.empty() || call.body.empty() ||
            entry.path != call.path || entry.body != call.body) return "invalid_target";
        return {};
    });
}

std::shared_ptr<const ProtectedDeletionResponse> DesktopHttpTransport::localPurgeTasksProtected(
    const ProtectedDesktopHttpConfig& config, bool readProtocolGate, const ProtectedUploadSend& send) {
    return protectedDeletionCall(config, readProtocolGate, send, [](auto& call) -> std::string_view {
        call.method = "GET"; call.path = DesktopApiClient::purgeTasksPath; return {};
    });
}

std::shared_ptr<const ProtectedDeletionResponse> DesktopHttpTransport::ensureLocalPurgeTaskProtected(
    const ProtectedDesktopHttpConfig& config, std::string_view meetingId, bool readProtocolGate,
    const ProtectedUploadSend& send) {
    return protectedDeletionCall(config, readProtocolGate, send, [&](auto& call) -> std::string_view {
        call.method = "POST"; call.path = DesktopApiClient::localPurgeTaskPath<CustodyString>(meetingId);
        return call.path.empty() ? "invalid_target" : std::string_view{};
    });
}

std::shared_ptr<const ProtectedDeletionResponse> DesktopHttpTransport::acknowledgeLocalPurgeTaskProtected(
    const ProtectedDesktopHttpConfig& config, std::string_view taskId, LocalPurgeAckState state,
    std::string_view reasonCode, std::string_view completedAtIso, bool readProtocolGate,
    const ProtectedUploadSend& send) {
    return protectedDeletionCall(config, readProtocolGate, send, [&](auto& call) -> std::string_view {
        call.method = "POST"; call.path = DesktopApiClient::localPurgeAckPath<CustodyString>(taskId);
        if (call.path.empty()) return "invalid_target";
        call.body = DesktopApiClient::localPurgeAckBody<CustodyString>(state, reasonCode, config.clientVersion, completedAtIso);
        return call.body.empty() ? "invalid_body" : std::string_view{};
    });
}

DesktopDeletionResponse DesktopHttpTransport::notificationContext(const DeletionScope& scope) const {
    return deletionCall(config_, scope, "GET", DesktopApiClient::notificationContextPath, {});
}

DesktopDeletionResponse DesktopHttpTransport::requestDeletion(std::string_view path, std::string body,
                                                              const DeletionScope& scope) const {
    if (path.empty()) {
        DesktopDeletionResponse result;
        result.safeReason = "invalid_target";
        return result;
    }
    return deletionCall(config_, scope, "POST", path, body);
}

DesktopDeletionResponse DesktopHttpTransport::recordingLifecycle(const std::vector<std::string>& origins,
                                                                const std::vector<std::string>& meetingIds,
                                                                const DeletionScope& scope) const {
    if (!DesktopApiClient::validLifecycleSelection(origins, meetingIds, kLifecycleSelectionLimit)) {
        DesktopDeletionResponse result;
        result.safeReason = "invalid_selection";
        return result;
    }
    return deletionCall(config_, scope, "POST", DesktopApiClient::lifecyclePath,
                        DesktopApiClient::lifecycleBody(origins, meetingIds));
}

DesktopDeletionResponse DesktopHttpTransport::ensureLocalPurgeTask(std::string_view meetingId,
                                                                  const DeletionScope& scope) const {
    const auto path = DesktopApiClient::localPurgeTaskPath(meetingId);
    if (path.empty()) {
        DesktopDeletionResponse result;
        result.safeReason = "invalid_target";
        return result;
    }
    return deletionCall(config_, scope, "POST", path, {});
}

DesktopDeletionResponse DesktopHttpTransport::localPurgeTasks(const DeletionScope& scope) const {
    return deletionCall(config_, scope, "GET", DesktopApiClient::purgeTasksPath, {});
}

DesktopDeletionResponse DesktopHttpTransport::acknowledgeLocalPurgeTask(std::string_view taskId,
                                                                       LocalPurgeAckState state,
                                                                       std::string_view reasonCode,
                                                                       std::string_view completedAtIso,
                                                                       const DeletionScope& scope) const {
    const auto path = DesktopApiClient::localPurgeAckPath(taskId);
    if (path.empty()) {
        DesktopDeletionResponse result;
        result.safeReason = "invalid_target";
        return result;
    }
    // The answer carries a proof code from the client's own vocabulary; an empty
    // or malformed one would tell the server nothing about the local copies.
    const auto body = DesktopApiClient::localPurgeAckBody(state, reasonCode, config_.clientVersion, completedAtIso);
    if (body.empty()) {
        DesktopDeletionResponse result;
        result.safeReason = "invalid_body";
        return result;
    }
    return deletionCall(config_, scope, "POST", path, body);
}

std::optional<DesktopAccountIdentity> DesktopHttpTransport::accountIdentity() const {
    return accountIdentity(requestIdentity).identity;
}

CalendarJoinResolution DesktopHttpTransport::calendarJoinTarget(std::string_view eventId,
    std::chrono::steady_clock::time_point deadline, const CalendarJoinGet& get) const {
    using State = CalendarJoinResolutionState;
    deadline = std::min(deadline, std::chrono::steady_clock::now() + std::chrono::seconds(15));
    const auto stopped = [&]() -> std::optional<CalendarJoinResolution> {
        if (cancelled(config_)) return CalendarJoinResolution{State::cancelled};
        if (std::chrono::steady_clock::now() >= deadline) return CalendarJoinResolution{};
        return std::nullopt;
    };
    if (const auto result = stopped()) return *result;
    const auto path = DesktopApiClient::calendarJoinTargetPath(eventId);
    if (path.empty()) return {State::invalidTarget};
    const auto safeHeader = [](std::string_view value, std::size_t maximum) {
        return !value.empty() && value.size() <= maximum &&
            std::all_of(value.begin(), value.end(), [](unsigned char c) { return c >= 0x21 && c <= 0x7e; });
    };
    const auto& identity = config_.confirmedIdentity;
    if (!identity || !DesktopApiClient::accountId(identity->userId) ||
        !DesktopApiClient::accountId(identity->workspaceId) || config_.workspaceId != identity->workspaceId ||
        !safeHeader(config_.sessionToken, 4096)) return {State::authRequired};
    if (config_.baseOrigin.compare(0, 8, "https://") != 0 ||
        !DesktopUploadQueueService::validServerOrigin(config_.baseOrigin) ||
        !safeHeader(config_.clientVersion, 120)) return {State::invalidTarget};
    if (!get) return {};
    auto config = config_;
    config.deviceId.clear();
    config.scopedAccount = DeletionScope{identity->userId, identity->workspaceId};
    UploadResponse response;
    try {
        if (const auto result = stopped()) return *result;
        response = get(config, path, deadline);
    } catch (...) {
        if (const auto result = stopped()) return *result;
        return {};
    }
    if (const auto result = stopped()) return *result;
    if (response.transportFailed || response.status == 0 || response.status == 408 ||
        response.status == 429 || response.status >= 500) return {};
    if (response.status == 401) return {State::authRequired};
    if (response.status == 403 || response.status == 404 || response.status == 410) return {State::eventUnavailable};
    if (response.status != 200) return {State::invalidTarget};
    auto target = DesktopApiClient::decodeCalendarJoinTarget(response.body, eventId);
    const auto expiry = parseEpochSeconds(response.authExpiresAt);
    if (const auto result = stopped()) return *result;
    if (!target) return {State::invalidTarget};
    return {State::resolved, std::move(target), expiry};
}

CalendarJoinResolution DesktopHttpTransport::calendarJoinTarget(std::string_view eventId,
    std::chrono::steady_clock::time_point deadline) const {
#ifdef _WIN32
    return calendarJoinTarget(eventId, deadline, [](const DesktopHttpConfig& config,
        std::string_view path, std::chrono::steady_clock::time_point limit) {
        return request(config, L"GET", utf8ToWide(path), {}, true, {}, {}, {}, limit);
    });
#else
    return calendarJoinTarget(eventId, deadline, {});
#endif
}

namespace {
template<class Item, class Identity> std::string_view ownerBlockReasonUsing(
    const Item& item, const std::optional<Identity>& identity) {
    if (!DesktopApiClient::accountId(item.ownerUserId) || !DesktopApiClient::accountId(item.ownerWorkspaceId))
        return "local_owner_unclaimed";
    if (!identity || !DesktopApiClient::accountId(identity->userId) || !DesktopApiClient::accountId(identity->workspaceId))
        return "account_identity_unavailable";
    if (std::string_view(item.ownerUserId) != std::string_view(identity->userId) ||
        std::string_view(item.ownerWorkspaceId) != std::string_view(identity->workspaceId))
        return "account_mismatch";
    return {};
}
} // namespace

std::string_view DesktopHttpTransport::ownerBlockReason(
    const UploadCustodyItem& item, const std::optional<DesktopAccountIdentity>& identity) {
    return ownerBlockReasonUsing(item, identity);
}

namespace {
template<class String, class Item> String replacementSessionKey(const Item& item, std::string_view expiredSessionId) {
    if (!isSafeIdentifier(expiredSessionId)) return {};
    // Bind replacement to server truth, never the resettable retry counter.
    // Retrying a lost response reuses this key; another expiry gets a new key.
    String scope("upload-session-after-"); scope.append(expiredSessionId.data(), expiredSessionId.size());
    return DesktopApiClient::idempotencyKey<String>(scope, item.directoryId, item.sessionId);
}
}
std::string DesktopHttpTransport::replacementUploadSessionKey(
    const UploadCustodyItem& item, std::string_view expiredSessionId) {
    return replacementSessionKey<std::string>(item, expiredSessionId);
}

DesktopTransportResult DesktopHttpTransport::upload(const UploadCustodyItem& item) const {
#ifdef _WIN32
    return upload(item, sendUploadRequest<>);
#else
    return upload(item, {});
#endif
}

namespace {
template<class Config, class Item, class Send, class LoadTracks, class Result>
void uploadPrepared(const Config& config_, const Item& item,
    const Send& send, LoadTracks loadTracks, Result& result) {
    using String = typename Result::StringType;
    using Request = DesktopHttpTransport::BasicUploadRequest<String>;
    using Response = std::invoke_result_t<const Send&, const Config&, const Request&>;
    const auto publish = [&result]() noexcept {
        if (result.serverTruth && !result.serverTruth->meetingExists) result.serverTruth.reset();
    };
    const auto withTruth = [&result, &publish](DesktopTransportStatus status, const Response* response = nullptr) {
        if (response) uploadResponse(*response, result);
        else resetUploadStatus(result, status);
        publish();
    };
    try {
        // Both callers construct this truth together with the result, before config,
        // package validation or account lookup. No result is constructed after ACK.
        auto& truth = *result.serverTruth;
        if (cancelled(config_)) return withTruth(DesktopTransportStatus::retryableFailure);
        if (DesktopUploadQueueService::isPermanentUploadReason(item.safeReason)) {
            withTruth(DesktopTransportStatus::serverRejected);
            result.safeReason = item.safeReason;
            result.retryClass = "not_retryable";
            return;
        }
        if (ownerBlockReasonUsing(item, std::optional<BasicDesktopAccountIdentity<String>>{}) == "local_owner_unclaimed") {
            withTruth(DesktopTransportStatus::authRequired);
            result.safeReason = "local_owner_unclaimed";
            return;
        }
        if (config_.sessionToken.empty()) return withTruth(DesktopTransportStatus::authRequired);
        if (!send) return withTruth(DesktopTransportStatus::unsupportedPlatform);
        std::uint32_t durationSeconds = 0;
        std::uint64_t startedAtMs = 0;
        std::uint64_t stoppedAtMs = 0;
        int displayOffsetMinutes = 0;
        auto sourceFailure = DesktopTransportStatus::invalidPackage;
        const auto tracks = loadTracks(&durationSeconds, &startedAtMs, &stoppedAtMs, &displayOffsetMinutes, &sourceFailure);
        if (!tracks || !isSafeIdentifier(item.directoryId) || !isSafeIdentifier(item.localRecordingId) ||
            !isSafeIdentifier(item.sessionId)) {
            return withTruth(sourceFailure);
        }
        // Resolve with the same copied session used by every following request, and
        // prefer the snapshot the shell confirmed for it. This precedes sync-state
        // too: recording_not_found is not claim authority.
        const auto account = resolveAccountIdentityUsing<UploadJsonReader<String>, String>(config_, [&](const Config& config, std::string_view path) {
            return send(config, {"GET", String(path), "", true});
        });
        const auto block = ownerBlockReasonUsing(item, account.identity);
        if (!block.empty()) {
            withTruth(account.identity ? DesktopTransportStatus::authRequired : account.status);
            result.safeReason = block;
            return;
        }
        truth.localRecordingId.assign(item.localRecordingId.data(), item.localRecordingId.size());
        String localRevision(std::string_view(item.directoryId)); localRevision += "--initial";
        // A 429 is the server asking the client to wait, so the pause travels with
        // the result and the scheduler holds the attempt until it elapses instead of
        // spending the retry budget on a request the server just refused.
        std::optional<BasicDesktopRemoteUploadState<String>> remote;
        String syncPath("/api/v1/desktop/recordings/"); syncPath += item.directoryId;
        syncPath += "/sync-state?local_media_revision_id="; syncPath += localRevision;
        auto response = send(config_, {"GET", syncPath, "", true});
        if (isUnknownRecording(response)) {
            remote = std::nullopt;
        } else {
            const auto syncStatus = mapResponse(response);
            if (syncStatus != DesktopTransportStatus::uploaded) return withTruth(syncStatus, &response);
            remote = decodeSyncStateUsing<String>(response.body, item.localRecordingId);
            if (!remote) return withTruth(DesktopTransportStatus::serverRejected);
            truth = remote->truth;
            if (remote->blockedByConflict) {
                // A conflict the server classified as paused or not retryable must
                // not become another automatic attempt. The class travels with the
                // result so the queue can stop and show the real reason.
                withTruth(DesktopTransportStatus::serverRejected);
                result.retryClass = remote->retryClass;
                return;
            }
            if (truth.finalized) {
                return withTruth(DesktopTransportStatus::uploaded);
            }
        }

        String meetingId;
        if (remote) meetingId = remote->meetingId;
        if (meetingId.empty()) {
            const auto meetingRequest = DesktopApiClient::createMeetingRequest<String>(
                item.directoryId, localRevision, durationSeconds, startedAtMs, stoppedAtMs, displayOffsetMinutes);
            if (!meetingRequest) return withTruth(DesktopTransportStatus::invalidPackage);
            const auto createBody = DesktopApiClient::createMeetingBody(*meetingRequest);
            const auto meetingKey = DesktopApiClient::idempotencyKey<String>("meeting", item.directoryId, item.sessionId);
            if (meetingKey.empty()) return withTruth(DesktopTransportStatus::invalidPackage);
            response = send(config_, {"POST", "/api/v1/meetings", createBody, true, meetingKey});
            const auto status = mapResponse(response);
            if (status != DesktopTransportStatus::uploaded) return withTruth(status, &response);
            const auto createdMeetingId = jsonStringField<String>(response.body, "meeting_id");
            if (!createdMeetingId || !isSafeIdentifier(*createdMeetingId)) return withTruth(DesktopTransportStatus::serverRejected);
            meetingId.assign(createdMeetingId->data(), createdMeetingId->size());
            truth.meetingExists = true;
            truth.meetingId = *createdMeetingId;
        }

        String serverSessionId;
        if (remote && !remote->needsNewUploadSession) serverSessionId = remote->sessionId;
        if (serverSessionId.empty()) {
            const std::array<std::uint64_t, 3> sizes{
                (*tracks)[0].bytes, (*tracks)[1].bytes, (*tracks)[2].bytes};
            const auto sessionRequest = DesktopApiClient::uploadSessionRequest<String>(sizes, (*tracks)[0].sha256);
            if (!sessionRequest) return withTruth(DesktopTransportStatus::invalidPackage);
            String expectedTracks("[");
            String expectedSizes("{");
            for (std::size_t index = 0; index < sessionRequest->expectedTracks.size(); ++index) {
                if (index != 0) {
                    expectedTracks += ',';
                    expectedSizes += ',';
                }
                const auto name = sessionRequest->expectedTracks[index];
                expectedTracks += '"'; expectedTracks.append(name.data(), name.size()); expectedTracks += '"';
                expectedSizes += '"'; expectedSizes.append(name.data(), name.size()); expectedSizes += "\":";
                appendNumber(expectedSizes, sessionRequest->expectedTrackSizes[index]);
            }
            expectedTracks += ']';
            expectedSizes += '}';
            const auto sessionKey = remote && remote->needsNewUploadSession
                ? replacementSessionKey<String>(item, remote->sessionId)
                : DesktopApiClient::idempotencyKey<String>("upload-session", item.directoryId, item.sessionId);
            if (sessionKey.empty()) return withTruth(DesktopTransportStatus::invalidPackage);
            String sessionBody("{\"expected_tracks\":"); sessionBody += expectedTracks;
            sessionBody += ",\"expected_track_sizes\":"; sessionBody += expectedSizes;
            sessionBody += ",\"manifest_sha256\":\""; sessionBody += sessionRequest->manifestSha256; sessionBody += "\"}";
            String sessionPath("/api/v1/meetings/"); sessionPath += meetingId; sessionPath += "/upload-sessions";
            response = send(config_, {"POST", sessionPath,
                                    sessionBody, true, sessionKey});
            const auto status = mapResponse(response);
            if (status != DesktopTransportStatus::uploaded) return withTruth(status, &response);
            const auto createdSessionId = jsonStringField<String>(response.body, "session_id");
            if (!createdSessionId || !isSafeIdentifier(*createdSessionId)) return withTruth(DesktopTransportStatus::serverRejected);
            serverSessionId.assign(createdSessionId->data(), createdSessionId->size());
            truth.uploadSessionExists = true;
            const auto accepted = acceptedBytes<String>(response.body);
            if (!accepted) return withTruth(DesktopTransportStatus::serverRejected);
            truth.acceptedBytes = *accepted;
        } else {
            truth.uploadSessionExists = true;
        }

        String sessionPath("/api/v1/upload-sessions/"); sessionPath += serverSessionId;
        String rangesPath(sessionPath); rangesPath += "/missing-ranges";
        response = send(config_, {"GET", rangesPath, "", true});
        auto status = mapResponse(response);
        if (status != DesktopTransportStatus::uploaded) return withTruth(status, &response);
        const auto ranges = missingRanges<String>(response.body);
        if (!ranges) return withTruth(DesktopTransportStatus::serverRejected);
        for (const auto& track : *tracks) {
            if (uploadFile(config_, send, track, serverSessionId, (*ranges)[trackIndex(track.role)],
                &truth.acceptedBytes, result) != DesktopTransportStatus::uploaded) {
                publish();
                return;
            }
        }

        response = send(config_, {"GET", rangesPath, "", true});
        status = mapResponse(response);
        if (status != DesktopTransportStatus::uploaded) return withTruth(status, &response);
        const auto remaining = missingRanges<String>(response.body);
        if (!remaining) return withTruth(DesktopTransportStatus::serverRejected);
        for (const auto& rangesForTrack : *remaining) {
            if (!rangesForTrack.empty()) return withTruth(DesktopTransportStatus::retryableFailure);
        }

        String trackJson;
        for (std::size_t index = 0; index < tracks->size(); ++index) {
            if (index != 0) trackJson += ',';
            const auto& track = (*tracks)[index];
            trackJson += "{\"track_role\":\""; trackJson += track.role;
            trackJson += "\",\"codec\":\""; trackJson += track.codec;
            trackJson += "\",\"sample_rate_hz\":"; appendNumber(trackJson, track.sampleRate);
            trackJson += ",\"channel_count\":"; appendNumber(trackJson, track.channels);
            trackJson += ",\"duration_seconds\":"; appendNumber(trackJson, track.durationSeconds);
            trackJson += ",\"byte_length\":"; appendNumber(trackJson, track.bytes);
            trackJson += ",\"sha256\":\""; trackJson += track.sha256; trackJson += "\"}";
        }
        String finalizeBody("{\"manifest_sha256\":\""); finalizeBody += (*tracks)[0].sha256;
        finalizeBody += "\",\"tracks\":["; finalizeBody += trackJson; finalizeBody += "]}";
        sessionPath += "/finalize";
        response = send(config_, {"POST", sessionPath, finalizeBody, true});
        status = mapResponse(response);
        if (status == DesktopTransportStatus::uploaded) truth.finalized = true;
        return withTruth(status, &response);
    } catch (const std::bad_alloc&) {
        // The terminal and its truth already exist. Clear incomplete response
        // fields without allocating; publish the SAME owner and known ACKs.
        withTruth(DesktopTransportStatus::retryableFailure);
    }
}
} // namespace

DesktopTransportResult DesktopHttpTransport::upload(const UploadCustodyItem& item, const UploadSend& send) const {
    DesktopTransportResult result;
    result.serverTruth.emplace();
    uploadPrepared(config_, item, send, [&item](auto* duration, auto* started, auto* stopped, auto* offset, auto*) {
        return packageTracks(item, duration, started, stopped, offset);
    }, result);
    return result; // Ordinary compatibility API; protected callers retain an owner.
}

#ifdef _WIN32
std::shared_ptr<const ProtectedDesktopTransportResult> DesktopHttpTransport::uploadProtected(
    const ProtectedDesktopHttpConfig& config, const ProtectedUploadQueueValue::Item& item,
    std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> proof, const ProtectedUploadSend& send) {
    std::shared_ptr<ProtectedDesktopTransportResult> result;
    try {
        result = std::allocate_shared<ProtectedDesktopTransportResult>(CustodyAllocator<ProtectedDesktopTransportResult>{});
        result->serverTruth.emplace();
        if (!config.cancellation) return {};
        auto loadTracks = [proof = std::move(proof), &item, &config](std::uint32_t* duration, std::uint64_t* started,
                std::uint64_t* stopped, int* offset, DesktopTransportStatus* failure) -> std::optional<CustodyVector<BasicLocalTrack<CustodyString>>> {
                if (!proof || !proof->pair_ || proof->evidence_.integrity != PackageIntegrity::valid ||
                    proof->pair_->current().phase != CustodyPackagePhase::sealedNormal ||
                    std::string_view(proof->pair_->current().directory.data()) != std::string_view(item.directoryId) ||
                    std::string_view(reinterpret_cast<const char*>(proof->session_.data()), proof->session_.size()) != std::string_view(item.sessionId))
                    return std::nullopt;
                const auto& evidence = proof->evidence_;
                if (!evidence.durationMs || evidence.durationMs > 24ULL * 60 * 60 * 1000) return std::nullopt;
                *duration = static_cast<std::uint32_t>((evidence.durationMs + 999) / 1000);
                *started = evidence.startedAtMs; *stopped = evidence.stoppedAtMs; *offset = evidence.displayTimezoneOffsetMinutes;
                const auto& package = proof->pair_->current();
                constexpr std::array<CustodyRole, 3> roles{CustodyRole::manifest, CustodyRole::media, CustodyRole::playback};
                constexpr std::array<const char*, 3> names{"manifest", "media", "playback"};
                constexpr std::array<const char*, 3> codecs{"json", "wav-pcm-s16le", "m4a-aac-lc"};
                constexpr std::array<std::uint32_t, 3> rates{1, 16'000, 48'000};
                CustodyVector<BasicLocalTrack<CustodyString>> tracks; tracks.reserve(3);
                for (std::size_t role = 0; role < roles.size(); ++role) {
                    std::size_t index = 0;
                    while (index < package.refCount && package.refs[index].role != roles[role]) ++index;
                    if (index == package.refCount) return std::nullopt;
                    const auto& ref = package.refs[index];
                    if (!ref.sealed || !ref.length || !*ref.length || !ref.sha256) return std::nullopt;
                    auto* stream = proof->readers_[proof->pair_->selectedSlot()][index].stream.Get();
                    LARGE_INTEGER zero{};
                    if (cancelled(config) || !stream || FAILED(stream->Seek(zero, STREAM_SEEK_SET, nullptr))) {
                        *failure = DesktopTransportStatus::retryableFailure; return std::nullopt;
                    }
                    const auto digest = sha256ProtectedStream(stream, *ref.length, config.cancellation);
                    if (!digest.ok()) { *failure = DesktopTransportStatus::retryableFailure; return std::nullopt; }
                    if (*digest.value != *ref.sha256) return std::nullopt;
                    BasicLocalTrack<CustodyString> track{names[role], {}, codecs[role], rates[role], 1, role == 0 ? 1 : *duration, *ref.length, {}, stream};
                    track.sha256 = digestHex<CustodyString>(*digest.value);
                    tracks.push_back(std::move(track));
                }
                return tracks;
            };
        if (send) uploadPrepared(config, item, send, std::move(loadTracks), *result);
        else uploadPrepared(config, item, &sendUploadRequest<ProtectedUploadResponse, ProtectedDesktopHttpConfig, ProtectedUploadRequest>, std::move(loadTracks), *result);
    } catch (const std::bad_alloc&) {
        if (result) {
            resetUploadStatus(*result, DesktopTransportStatus::retryableFailure);
            if (result->serverTruth && !result->serverTruth->meetingExists) result->serverTruth.reset();
        }
    }
    return result;
}
#endif

} // namespace graf::windows
