#include "DesktopHttpTransport.h"

#include "DesktopApiClient.h"
#include "../Recording/LocalRecordingPackage.h"
#include "../Storage/Sha256.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <chrono>
#include <fstream>
#include <limits>
#include <optional>
#include <set>
#include <sstream>
#include <string_view>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#endif

namespace graf::windows {
namespace {

constexpr std::size_t kMaxPartBytes = 16 * 1024 * 1024;

bool cancelled(const DesktopHttpConfig& config) {
    return config.cancellation && config.cancellation->load();
}

std::optional<std::string> accountField(
    const std::map<std::string_view, std::string_view>& fields, std::string_view key) {
    const auto field = fields.find(key);
    if (field == fields.end()) return std::nullopt;
    auto value = field->second;
    if (value.size() != 38 || value.front() != '"' || value.back() != '"') return std::nullopt;
    value.remove_prefix(1); value.remove_suffix(1);
    if (!DesktopApiClient::accountId(value)) return std::nullopt;
    return std::string(value);
}

#ifdef _WIN32

constexpr std::size_t kMaxJsonResponseBytes = 2 * 1024 * 1024;

#endif

std::optional<std::string> jsonStringField(std::string_view json, std::string_view key) {
    const auto marker = std::string("\"") + std::string(key) + "\":\"";
    const auto start = json.find(marker);
    if (start == std::string_view::npos) return std::nullopt;
    const auto valueStart = start + marker.size();
    std::string value;
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

std::optional<std::uint64_t> jsonNumberField(std::string_view json, std::string_view key) {
    const auto marker = std::string("\"") + std::string(key) + "\":";
    const auto start = json.find(marker);
    if (start == std::string_view::npos) return std::nullopt;
    const auto valueStart = start + marker.size();
    const auto valueEnd = json.find_first_not_of("0123456789", valueStart);
    if (valueEnd == valueStart) return std::nullopt;
    const auto end = valueEnd == std::string_view::npos ? json.size() : valueEnd;
    auto delimiter = end;
    while (delimiter < json.size() && std::isspace(static_cast<unsigned char>(json[delimiter]))) ++delimiter;
    if (delimiter < json.size() && json[delimiter] != ',' && json[delimiter] != '}') return std::nullopt;
    try {
        return std::stoull(std::string(json.substr(valueStart, end - valueStart)));
    } catch (...) {
        return std::nullopt;
    }
}

#ifdef _WIN32
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
#endif

bool isSafeIdentifier(std::string_view value) noexcept {
    if (value.empty() || value.size() > 300) return false;
    for (const auto character : value) {
        if (!std::isalnum(static_cast<unsigned char>(character)) && character != '-' && character != '_') {
            return false;
        }
    }
    return true;
}

#ifdef _WIN32

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

struct LocalTrack {
    std::string role;
    std::filesystem::path path;
    std::string codec;
    std::uint32_t sampleRate = 1;
    std::uint32_t channels = 1;
    std::uint32_t durationSeconds = 1;
    std::uint64_t bytes = 0;
    std::string sha256;
};

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
    return std::vector<LocalTrack>{
        {"manifest", manifestPath, "json", 1, 1, 1, manifestSize, sha256File(manifestPath)},
        {"media", mediaPath, "wav-pcm-s16le", 16'000, 1, *durationSeconds, *mediaBytes, *mediaDigest},
        {"playback", playbackPath, "m4a-aac-lc", 48'000, 1, *durationSeconds, *playbackBytes, *playbackDigest},
    };
}

std::wstring utf8ToWide(std::string_view value) {
    if (value.empty()) return {};
    const auto length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
        static_cast<int>(value.size()), nullptr, 0);
    if (length <= 0) return {};
    std::wstring result(static_cast<std::size_t>(length), L'\0');
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()),
                            result.data(), length) != length) return {};
    return result;
}

struct HttpResponse {
    DWORD status = 0;
    std::string body;
    bool transportFailed = false;
    std::string retryAfter;
    std::string authExpiresAt;
};

// A response header that must be ASCII digits and nothing else. macOS reads the
// same header with the same rule, so a decorated or localized value is not a
// deadline on either platform.
std::optional<std::int64_t> parseEpochSeconds(std::string_view raw) {
    if (raw.empty() || raw.size() > 19) return std::nullopt;
    std::int64_t value = 0;
    for (const char character : raw) {
        if (character < '0' || character > '9') return std::nullopt;
        value = value * 10 + (character - '0');
    }
    return value;
}

struct ByteRange {
    std::uint64_t start = 0;
    std::uint64_t end = 0;
};

#endif

std::optional<std::string_view> jsonObjectField(std::string_view json, std::string_view key) {
    const auto marker = std::string("\"") + std::string(key) + "\":";
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
HttpResponse request(const DesktopHttpConfig& config, std::wstring method, std::wstring path,
                     const std::string& body, bool jsonBody, std::string_view idempotencyKey = {},
                     std::optional<std::uint64_t> byteOffset = std::nullopt,
                     std::string_view contentSha256 = {}) {
    HttpResponse result;
    if (cancelled(config)) { result.transportFailed = true; return result; }
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(30);
    auto url = utf8ToWide(config.baseOrigin);
    if (url.empty()) { result.transportFailed = true; return result; }
    URL_COMPONENTS components{};
    components.dwStructSize = sizeof(components);
    components.dwSchemeLength = static_cast<DWORD>(-1);
    components.dwHostNameLength = static_cast<DWORD>(-1);
    components.dwUrlPathLength = static_cast<DWORD>(-1);
    if (!WinHttpCrackUrl(url.data(), 0, 0, &components) ||
        components.nScheme != INTERNET_SCHEME_HTTPS || components.lpszHostName == nullptr) {
        result.transportFailed = true;
        return result;
    }
    HINTERNET session = WinHttpOpen(L"GRAF/Feature200", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
                                    WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!session) { result.transportFailed = true; return result; }
    if (!WinHttpSetTimeouts(session, 5'000, 5'000, 10'000, 10'000)) {
        WinHttpCloseHandle(session);
        result.transportFailed = true;
        return result;
    }
    const std::wstring host(components.lpszHostName, components.dwHostNameLength);
    HINTERNET connection = WinHttpConnect(session, host.c_str(), components.nPort, 0);
    HINTERNET handle = connection ? WinHttpOpenRequest(connection, method.c_str(), path.c_str(), nullptr,
                                                        WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
                                                        WINHTTP_FLAG_SECURE) : nullptr;
    if (!handle) {
        if (connection) WinHttpCloseHandle(connection);
        WinHttpCloseHandle(session);
        result.transportFailed = true;
        return result;
    }
    // Native session-header transport does not inherit browser cookies or
    // follow redirects carrying authentication to another endpoint/origin.
    DWORD disabled = WINHTTP_DISABLE_REDIRECTS | WINHTTP_DISABLE_COOKIES;
    if (!WinHttpSetOption(handle, WINHTTP_OPTION_DISABLE_FEATURE, &disabled, sizeof(disabled))) {
        WinHttpCloseHandle(handle);
        WinHttpCloseHandle(connection);
        WinHttpCloseHandle(session);
        result.transportFailed = true;
        return result;
    }
    std::wstring headers = L"Accept: application/json\r\nX-Client-Version: " + utf8ToWide(config.clientVersion) + L"\r\n";
    if (!config.workspaceId.empty()) {
        headers += L"X-Workspace-Id: " + utf8ToWide(config.workspaceId) + L"\r\n";
    }
    if (!config.workspaceId.empty() && !config.deviceId.empty()) {
        headers += L"X-Device-Id: " + utf8ToWide(config.deviceId) + L"\r\n";
    }
    if (!idempotencyKey.empty()) headers += L"Idempotency-Key: " + utf8ToWide(idempotencyKey) + L"\r\n";
    if (byteOffset) headers += L"X-Byte-Offset: " + std::to_wstring(*byteOffset) + L"\r\n";
    if (!contentSha256.empty()) headers += L"X-Content-SHA256: " + utf8ToWide(contentSha256) + L"\r\n";
    if (!config.sessionToken.empty()) headers += L"X-Auth-Session: " + utf8ToWide(config.sessionToken) + L"\r\n";
    // A scoped mutation declares which account it is for. Both identifiers are
    // validated before they are serialized, so a malformed scope cannot travel
    // as a header the server would read as permission for another actor.
    if (config.scopedAccount) {
        const auto scoped = DesktopApiClient::scopedAccountHeaders(*config.scopedAccount);
        if (scoped.size() == 2) {
            headers += utf8ToWide(scoped[0].first) + L": " + utf8ToWide(scoped[0].second) + L"\r\n";
            headers += utf8ToWide(scoped[1].first) + L": " + utf8ToWide(scoped[1].second) + L"\r\n";
        }
    }
    headers += jsonBody ? L"Content-Type: application/json\r\n" : L"Content-Type: application/octet-stream\r\n";
    const auto sent = !cancelled(config) && WinHttpSendRequest(handle, headers.c_str(), static_cast<DWORD>(headers.size()),
        body.empty() ? WINHTTP_NO_REQUEST_DATA : const_cast<char*>(body.data()), static_cast<DWORD>(body.size()),
        static_cast<DWORD>(body.size()), 0);
    if (!sent || cancelled(config) || !WinHttpReceiveResponse(handle, nullptr)) {
        result.transportFailed = true;
    } else {
        DWORD statusSize = sizeof(result.status);
        WinHttpQueryHeaders(handle, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                            WINHTTP_HEADER_NAME_BY_INDEX, &result.status, &statusSize, WINHTTP_NO_HEADER_INDEX);
        // The header is read only so the scheduler can wait as long as the server
        // asked; it never changes what the response means.
        DWORD retrySize = 0;
        WinHttpQueryHeaders(handle, WINHTTP_QUERY_CUSTOM, L"Retry-After",
                            WINHTTP_NO_OUTPUT_BUFFER, &retrySize, WINHTTP_NO_HEADER_INDEX);
        if (retrySize > sizeof(wchar_t) && retrySize <= 256) {
            std::wstring raw(retrySize / sizeof(wchar_t), L'\0');
            if (WinHttpQueryHeaders(handle, WINHTTP_QUERY_CUSTOM, L"Retry-After", raw.data(), &retrySize,
                                    WINHTTP_NO_HEADER_INDEX)) {
                raw.resize(std::wstring::traits_type::length(raw.c_str()));
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
        WinHttpQueryHeaders(handle, WINHTTP_QUERY_CUSTOM, L"X-GRAF-Auth-Expires-At",
                            WINHTTP_NO_OUTPUT_BUFFER, &expirySize, WINHTTP_NO_HEADER_INDEX);
        if (expirySize > sizeof(wchar_t) && expirySize <= 64) {
            std::wstring raw(expirySize / sizeof(wchar_t), L'\0');
            if (WinHttpQueryHeaders(handle, WINHTTP_QUERY_CUSTOM, L"X-GRAF-Auth-Expires-At", raw.data(), &expirySize,
                                    WINHTTP_NO_HEADER_INDEX)) {
                raw.resize(std::wstring::traits_type::length(raw.c_str()));
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
        while (result.body.size() < kMaxJsonResponseBytes) {
            if (cancelled(config) || std::chrono::steady_clock::now() >= deadline) {
                result.transportFailed = true;
                break;
            }
            DWORD available = 0;
            if (!WinHttpQueryDataAvailable(handle, &available)) { result.transportFailed = true; break; }
            if (available == 0) break;
            const auto remaining = kMaxJsonResponseBytes - result.body.size();
            const auto count = std::min<std::size_t>(available, remaining);
            const auto start = result.body.size();
            result.body.resize(start + count);
            DWORD read = 0;
            if (!WinHttpReadData(handle, result.body.data() + start, static_cast<DWORD>(count), &read)) {
                result.transportFailed = true;
                break;
            }
            result.body.resize(start + read);
            if (read == 0) break;
        }
        if (result.body.size() == kMaxJsonResponseBytes) result.transportFailed = true;
    }
    if (cancelled(config)) result.transportFailed = true;
    WinHttpCloseHandle(handle);
    WinHttpCloseHandle(connection);
    WinHttpCloseHandle(session);
    return result;
}

DesktopTransportStatus mapResponse(const HttpResponse& response) {
    if (response.transportFailed || response.status == 408 || response.status == 429 || response.status >= 500) {
        return DesktopTransportStatus::retryableFailure;
    }
    if (response.status == 401 || response.status == 403) return DesktopTransportStatus::authRequired;
    if (response.status < 200 || response.status >= 300) return DesktopTransportStatus::serverRejected;
    return DesktopTransportStatus::uploaded;
}
#endif

std::size_t trackIndex(std::string_view role) {
    if (role == "manifest") return 0;
    if (role == "media") return 1;
    return 2;
}

std::optional<std::array<std::uint64_t, 3>> acceptedBytes(std::string_view json) {
    const auto object = jsonObjectField(json, "accepted_bytes_by_track");
    if (!object) return std::nullopt;
    std::array<std::uint64_t, 3> result{};
    for (const auto role : {std::string_view("manifest"), std::string_view("media"), std::string_view("playback")}) {
        const auto value = jsonNumberField(*object, role);
        result[trackIndex(role)] = value.value_or(0);
    }
    return result;
}

#ifdef _WIN32
std::optional<std::array<std::vector<ByteRange>, 3>> missingRanges(std::string_view json) {
    const auto object = jsonObjectField(json, "missing_ranges_by_track");
    if (!object) return std::nullopt;
    std::array<std::vector<ByteRange>, 3> result;
    for (const auto role : {std::string_view("manifest"), std::string_view("media"), std::string_view("playback")}) {
        const auto marker = std::string("\"") + std::string(role) + "\":[";
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
            const auto start = jsonNumberField(rangeObject, "start");
            const auto finish = jsonNumberField(rangeObject, "end");
            if (!start || !finish || *finish <= *start) return std::nullopt;
            result[trackIndex(role)].push_back({*start, *finish});
            cursor = end + 1;
        }
        if (cursor >= object->size() || (*object)[cursor] != ']') return std::nullopt;
    }
    return result;
}
#endif

std::optional<std::string> nestedStringField(std::string_view json, std::string_view objectKey,
                                             std::string_view field) {
    const auto object = jsonObjectField(json, objectKey);
    if (!object) return std::nullopt;
    return jsonStringField(*object, field);
}

// Server statuses are compared the way the macOS client compares them: case and
// surrounding whitespace must not decide whether accepted media is re-uploaded.
std::string normalizedStatus(std::string value) {
    const auto notSpace = [](unsigned char character) { return std::isspace(character) == 0; };
    const auto first = std::find_if(value.begin(), value.end(), notSpace);
    const auto last = std::find_if(value.rbegin(), value.rend(), notSpace).base();
    std::string result(first, last);
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char character) { return static_cast<char>(std::tolower(character)); });
    return result;
}

} // namespace

std::optional<DesktopRemoteUploadState> DesktopHttpTransport::decodeSyncState(
    std::string_view json, std::string_view localRecordingId) {
    const auto meetingId = nestedStringField(json, "meeting", "meeting_id");
    if (!meetingId || !isSafeIdentifier(*meetingId)) return std::nullopt;
    DesktopRemoteUploadState result;
    result.meetingId = *meetingId;
    result.truth.localRecordingId = std::string(localRecordingId);
    result.truth.meetingExists = true;
    result.truth.meetingId = *meetingId;
    if (const auto session = jsonObjectField(json, "upload_session")) {
        if (const auto id = jsonStringField(*session, "session_id")) {
            if (!isSafeIdentifier(*id)) return std::nullopt;
            result.sessionId = *id;
            result.truth.uploadSessionExists = true;
        }
        if (const auto status = jsonStringField(*session, "status")) result.sessionStatus = *status;
        if (const auto accepted = acceptedBytes(*session)) result.truth.acceptedBytes = *accepted;
    }
    // The server's own fingerprint: which revision it accepted, which session
    // carries it and how far the meeting and its processing have come. macOS
    // keeps the same values in its queue row.
    if (const auto revision = jsonObjectField(json, "media_revision")) {
        if (const auto id = jsonStringField(*revision, "media_revision_id"))
            result.truth.mediaRevisionId = *id;
        // The revision status is a lifecycle state of its own; it is kept as the
        // server names it and never guessed from the upload session.
        if (const auto status = jsonStringField(*revision, "status"))
            result.truth.mediaRevisionStatus = normalizedStatus(*status);
    }
    if (result.truth.uploadSessionExists) result.truth.uploadSessionId = result.sessionId;
    if (const auto meetingStatus = nestedStringField(json, "meeting", "status"))
        result.truth.serverStatus = normalizedStatus(*meetingStatus);
    if (const auto processing = jsonObjectField(json, "processing")) {
        if (const auto status = jsonStringField(*processing, "status"))
            result.truth.processingStatus = normalizedStatus(*status);
    }
    const auto conflictState = nestedStringField(json, "conflict", "state");
    if (!conflictState) return std::nullopt;
    // The server owns the retry classification. The Windows port records it and
    // lets the scheduler act on it instead of retrying every conflict blindly.
    if (const auto custody = jsonObjectField(json, "custody")) {
        if (const auto retryClass = jsonStringField(*custody, "retry_class"))
            result.retryClass = normalizedStatus(*retryClass);
    }
    // The server drops terminal upload sessions from its active selection, so a
    // finalize whose response was lost comes back as no session at all. The
    // meeting status is then the only server-owned evidence that this revision
    // was already accepted. Without it the client creates a second session for
    // an immutable revision, gets media_revision_immutable and burns its retry
    // budget instead of moving the item to uploaded. The accepted statuses are
    // the same ones the macOS client treats as finalized.
    const auto meetingStatus = nestedStringField(json, "meeting", "status");
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

namespace {
#ifdef _WIN32

bool isUnknownRecording(const HttpResponse& response) {
    return response.status == 404 && jsonStringField(response.body, "code") == std::optional<std::string>("recording_not_found");
}

DesktopTransportStatus uploadFile(const DesktopHttpConfig& config, const LocalTrack& track, std::string_view sessionId,
                                  const std::vector<ByteRange>& ranges,
                                  std::array<std::uint64_t, 3>* accepted, std::uint32_t* retryAfter) {
    std::ifstream input(track.path, std::ios::binary);
    if (!input) return DesktopTransportStatus::invalidPackage;
    if (sha256File(track.path) != track.sha256) return DesktopTransportStatus::invalidPackage;
    const auto partSize = std::clamp(config.partSizeBytes, std::size_t(64 * 1024), kMaxPartBytes);
    for (const auto range : ranges) {
        for (std::uint64_t offset = range.start; offset < range.end;) {
            if (cancelled(config)) return DesktopTransportStatus::retryableFailure;
            const auto length = static_cast<std::size_t>(std::min<std::uint64_t>(partSize, range.end - offset));
            std::string data(length, '\0');
            input.clear();
            input.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
            input.read(data.data(), static_cast<std::streamsize>(data.size()));
            if (input.gcount() != static_cast<std::streamsize>(data.size())) return DesktopTransportStatus::invalidPackage;
            const auto path = L"/api/v1/upload-sessions/" + utf8ToWide(sessionId) + L"/tracks/" +
                utf8ToWide(track.role) + L"/parts/" + std::to_wstring(offset / partSize);
            const auto response = request(config, L"PUT", path, data, false, {}, offset, sha256(data));
            const auto status = mapResponse(response);
            if (status != DesktopTransportStatus::uploaded) {
                if (retryAfter != nullptr) {
                    *retryAfter = DesktopHttpTransport::rateLimitPauseSeconds(response.status, response.retryAfter);
                }
                return status;
            }
            const auto acceptedOffset = jsonNumberField(response.body, "byte_offset");
            const auto acceptedLength = jsonNumberField(response.body, "byte_length");
            if (!acceptedOffset || !acceptedLength || *acceptedOffset != offset || *acceptedLength != length) {
                return DesktopTransportStatus::serverRejected;
            }
            if (accepted != nullptr) (*accepted)[trackIndex(track.role)] += *acceptedLength;
            offset += length;
        }
    }
    return DesktopTransportStatus::uploaded;
}

#endif

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

std::optional<DesktopAccountIdentity> DesktopHttpTransport::decodeAccountIdentity(std::string_view json) {
    const auto fields = DesktopApiClient::jsonObjectFields(json);
    if (!fields) return std::nullopt;
    const auto user = accountField(*fields, "user_id"), workspace = accountField(*fields, "workspace_id"),
               session = accountField(*fields, "active_session_id");
    if (!user || !workspace || !session) return std::nullopt;
    return DesktopAccountIdentity{*user, *workspace};
}

std::optional<std::string> DesktopHttpTransport::decodeActiveWorkspace(std::string_view json) {
    const auto fields = DesktopApiClient::jsonObjectFields(json);
    if (!fields) return std::nullopt;
    const auto spaces = fields->find("spaces");
    if (spaces == fields->end()) return std::nullopt;
    const auto rows = DesktopApiClient::jsonArrayValues(spaces->second);
    if (!rows) return std::nullopt;
    std::set<std::string> ids;
    std::optional<std::string> workspace;
    for (const auto row : *rows) {
        const auto entry = DesktopApiClient::jsonObjectFields(row);
        if (!entry) return std::nullopt;
        const auto id = accountField(*entry, "id");
        const auto active = entry->find("active");
        if (!id || !ids.insert(*id).second || active == entry->end() ||
            (active->second != "true" && active->second != "false")) return std::nullopt;
        if (active->second == "true") {
            if (workspace) return std::nullopt;
            workspace = *id;
        }
    }
    return workspace;
}

DesktopHttpTransport::IdentityResult DesktopHttpTransport::accountIdentity(const IdentityGet& get) const {
    return resolveAccountIdentity(config_, get);
}

DesktopHttpTransport::IdentityResult DesktopHttpTransport::resolveAccountIdentity(
    const DesktopHttpConfig& confirmed, const IdentityGet& get) {
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
        return {identity, DesktopTransportStatus::uploaded};
    }
    if (!get || confirmed.sessionToken.empty() ||
        (!confirmed.workspaceId.empty() && !DesktopApiClient::accountId(confirmed.workspaceId))) return {};
    auto config = confirmed;
    config.deviceId.clear();
    IdentityResult result;
    const auto read = [&](std::string_view path) -> std::optional<std::string> {
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
        return response.body;
    };
    if (config.workspaceId.empty()) {
        const auto response = read("/desktop/settings/spaces");
        if (!response) return result;
        const auto workspace = decodeActiveWorkspace(*response);
        if (!workspace) return {};
        config.workspaceId = *workspace;
    }
    const auto response = read("/api/v1/auth/me");
    if (!response) return result;
    auto identity = decodeAccountIdentity(*response);
    if (!identity || identity->workspaceId != config.workspaceId) return {};
    return {identity, DesktopTransportStatus::uploaded};
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
DesktopDeletionResponse deletionCall(const DesktopHttpConfig& base, const DeletionScope& scope,
                                     std::wstring method, std::string_view path, const std::string& body) {
    DesktopDeletionResponse result;
    // The local refusals come first and read the same on every platform: a scope
    // that does not name a real account, or a session there is nothing to delete
    // with, is never sent.
    if (DesktopApiClient::scopedAccountHeaders(scope).size() != 2) {
        result.safeReason = "invalid_scope";
        return result;
    }
    if (base.sessionToken.empty()) {
        result.safeReason = "auth_required";
        return result;
    }
#ifndef _WIN32
    (void)method; (void)path; (void)body;
    result.transportFailed = true;
    return result;
#else
    auto config = base;
    config.scopedAccount = scope;
    const auto response = request(config, std::move(method), utf8ToWide(path), body, true);
    result.status = response.status;
    result.body = response.body;
    result.transportFailed = response.transportFailed;
    result.retryAfterSeconds = DesktopHttpTransport::rateLimitPauseSeconds(response.status, response.retryAfter);
    result.authExpiresAt = parseEpochSeconds(response.authExpiresAt);
    return result;
#endif
}
} // namespace

DesktopDeletionResponse DesktopHttpTransport::notificationContext(const DeletionScope& scope) const {
    return deletionCall(config_, scope, L"GET", DesktopApiClient::notificationContextPath, {});
}

DesktopDeletionResponse DesktopHttpTransport::requestDeletion(std::string_view path, std::string body,
                                                              const DeletionScope& scope) const {
    if (path.empty()) {
        DesktopDeletionResponse result;
        result.safeReason = "invalid_target";
        return result;
    }
    return deletionCall(config_, scope, L"POST", path, body);
}

DesktopDeletionResponse DesktopHttpTransport::recordingLifecycle(const std::vector<std::string>& origins,
                                                                const std::vector<std::string>& meetingIds,
                                                                const DeletionScope& scope) const {
    if (!DesktopApiClient::validLifecycleSelection(origins, meetingIds, kLifecycleSelectionLimit)) {
        DesktopDeletionResponse result;
        result.safeReason = "invalid_selection";
        return result;
    }
    return deletionCall(config_, scope, L"POST", DesktopApiClient::lifecyclePath,
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
    return deletionCall(config_, scope, L"POST", path, {});
}

DesktopDeletionResponse DesktopHttpTransport::localPurgeTasks(const DeletionScope& scope) const {
    return deletionCall(config_, scope, L"GET", DesktopApiClient::purgeTasksPath, {});
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
    return deletionCall(config_, scope, L"POST", path, body);
}

std::optional<DesktopAccountIdentity> DesktopHttpTransport::accountIdentity() const {
    return accountIdentity(requestIdentity).identity;
}

std::string_view DesktopHttpTransport::ownerBlockReason(
    const UploadCustodyItem& item, const std::optional<DesktopAccountIdentity>& identity) {
    if (!DesktopApiClient::accountId(item.ownerUserId) || !DesktopApiClient::accountId(item.ownerWorkspaceId))
        return "local_owner_unclaimed";
    if (!identity || !DesktopApiClient::accountId(identity->userId) || !DesktopApiClient::accountId(identity->workspaceId))
        return "account_identity_unavailable";
    if (item.ownerUserId != identity->userId || item.ownerWorkspaceId != identity->workspaceId)
        return "account_mismatch";
    return {};
}

std::string DesktopHttpTransport::replacementUploadSessionKey(
    const UploadCustodyItem& item, std::string_view expiredSessionId) {
    if (!isSafeIdentifier(expiredSessionId)) return {};
    // Bind replacement to server truth, never the resettable retry counter.
    // Retrying a lost response reuses this key; another expiry gets a new key.
    return DesktopApiClient::idempotencyKey("upload-session-after-" + std::string(expiredSessionId),
                                          item.directoryId, item.sessionId);
}

DesktopTransportResult DesktopHttpTransport::upload(const UploadCustodyItem& item) const {
    if (cancelled(config_)) return {DesktopTransportStatus::retryableFailure, std::nullopt};
    if (ownerBlockReason(item, std::nullopt) == "local_owner_unclaimed")
        return {DesktopTransportStatus::authRequired, std::nullopt, "local_owner_unclaimed"};
    if (config_.sessionToken.empty()) return {DesktopTransportStatus::authRequired, std::nullopt};
#ifndef _WIN32
    (void)item;
    return {DesktopTransportStatus::unsupportedPlatform, std::nullopt};
#else
    std::uint32_t durationSeconds = 0;
    std::uint64_t startedAtMs = 0;
    std::uint64_t stoppedAtMs = 0;
    int displayOffsetMinutes = 0;
    const auto tracks = packageTracks(item, &durationSeconds, &startedAtMs, &stoppedAtMs, &displayOffsetMinutes);
    if (!tracks || !isSafeIdentifier(item.directoryId) || !isSafeIdentifier(item.localRecordingId) ||
        !isSafeIdentifier(item.sessionId)) {
        return {DesktopTransportStatus::invalidPackage, std::nullopt};
    }
    // Resolve with the same copied session used by every following request, and
    // prefer the snapshot the shell confirmed for it. This precedes sync-state
    // too: recording_not_found is not claim authority.
    const auto account = resolveAccountIdentity(config_, requestIdentity);
    const auto block = ownerBlockReason(item, account.identity);
    if (!block.empty()) return {account.identity ? DesktopTransportStatus::authRequired : account.status,
                               std::nullopt, std::string(block)};
    UploadServerTruth truth;
    truth.localRecordingId = item.localRecordingId;
    const auto localRevision = item.directoryId + "--initial";
    // A 429 is the server asking the client to wait, so the pause travels with
    // the result and the scheduler holds the attempt until it elapses instead of
    // spending the retry budget on a request the server just refused.
    auto withTruth = [&truth](DesktopTransportStatus status, const HttpResponse* response = nullptr) {
        DesktopTransportResult result{status, truth.meetingExists ? std::optional<UploadServerTruth>(truth) : std::nullopt};
        if (response != nullptr) {
            result.retryAfterSeconds = DesktopHttpTransport::rateLimitPauseSeconds(response->status, response->retryAfter);
            result.authExpiresAt = parseEpochSeconds(response->authExpiresAt);
        }
        return result;
    };

    std::optional<DesktopRemoteUploadState> remote;
    const auto syncPath = std::string("/api/v1/desktop/recordings/") + item.directoryId +
        "/sync-state?local_media_revision_id=" + localRevision;
    auto response = request(config_, L"GET", utf8ToWide(syncPath), "", true);
    if (isUnknownRecording(response)) {
        remote = std::nullopt;
    } else {
        const auto syncStatus = mapResponse(response);
        if (syncStatus != DesktopTransportStatus::uploaded) return withTruth(syncStatus, &response);
        remote = decodeSyncState(response.body, item.localRecordingId);
        if (!remote) return withTruth(DesktopTransportStatus::serverRejected);
        truth = remote->truth;
        if (remote->blockedByConflict) {
            // A conflict the server classified as paused or not retryable must
            // not become another automatic attempt. The class travels with the
            // result so the queue can stop and show the real reason.
            auto blocked = withTruth(DesktopTransportStatus::serverRejected);
            blocked.retryClass = remote->retryClass;
            return blocked;
        }
        if (truth.finalized) {
            return withTruth(DesktopTransportStatus::uploaded);
        }
    }

    std::string meetingId = remote ? remote->meetingId : std::string{};
    if (meetingId.empty()) {
        const auto meetingRequest = DesktopApiClient::createMeetingRequest(
            item.directoryId, localRevision, durationSeconds, startedAtMs, stoppedAtMs, displayOffsetMinutes);
        if (!meetingRequest) return withTruth(DesktopTransportStatus::invalidPackage);
        const auto createBody = DesktopApiClient::createMeetingBody(*meetingRequest);
        const auto meetingKey = DesktopApiClient::idempotencyKey("meeting", item.directoryId, item.sessionId);
        if (meetingKey.empty()) return withTruth(DesktopTransportStatus::invalidPackage);
        response = request(config_, L"POST", L"/api/v1/meetings", createBody, true, meetingKey);
        const auto status = mapResponse(response);
        if (status != DesktopTransportStatus::uploaded) return withTruth(status, &response);
        const auto createdMeetingId = jsonStringField(response.body, "meeting_id");
        if (!createdMeetingId || !isSafeIdentifier(*createdMeetingId)) return withTruth(DesktopTransportStatus::serverRejected);
        meetingId = *createdMeetingId;
        truth.meetingExists = true;
        truth.meetingId = *createdMeetingId;
    }

    std::string serverSessionId = remote && !remote->needsNewUploadSession ? remote->sessionId : std::string{};
    if (serverSessionId.empty()) {
        const std::array<std::uint64_t, 3> sizes{
            (*tracks)[0].bytes, (*tracks)[1].bytes, (*tracks)[2].bytes};
        const auto sessionRequest = DesktopApiClient::uploadSessionRequest(sizes, (*tracks)[0].sha256);
        if (!sessionRequest) return withTruth(DesktopTransportStatus::invalidPackage);
        std::string expectedTracks = "[";
        std::string expectedSizes = "{";
        for (std::size_t index = 0; index < sessionRequest->expectedTracks.size(); ++index) {
            if (index != 0) {
                expectedTracks += ',';
                expectedSizes += ',';
            }
            expectedTracks += "\"" + std::string(sessionRequest->expectedTracks[index]) + "\"";
            expectedSizes += "\"" + std::string(sessionRequest->expectedTracks[index]) + "\":" +
                std::to_string(sessionRequest->expectedTrackSizes[index]);
        }
        expectedTracks += ']';
        expectedSizes += '}';
        const auto sessionKey = remote && remote->needsNewUploadSession
            ? replacementUploadSessionKey(item, remote->sessionId)
            : DesktopApiClient::idempotencyKey("upload-session", item.directoryId, item.sessionId);
        if (sessionKey.empty()) return withTruth(DesktopTransportStatus::invalidPackage);
        const auto sessionBody = std::string("{\"expected_tracks\":") + expectedTracks +
            ",\"expected_track_sizes\":" + expectedSizes + ",\"manifest_sha256\":\"" +
            sessionRequest->manifestSha256 + "\"}";
        response = request(config_, L"POST", utf8ToWide("/api/v1/meetings/" + meetingId + "/upload-sessions"),
                           sessionBody, true, sessionKey);
        const auto status = mapResponse(response);
        if (status != DesktopTransportStatus::uploaded) return withTruth(status, &response);
        const auto createdSessionId = jsonStringField(response.body, "session_id");
        if (!createdSessionId || !isSafeIdentifier(*createdSessionId)) return withTruth(DesktopTransportStatus::serverRejected);
        serverSessionId = *createdSessionId;
        truth.uploadSessionExists = true;
        const auto accepted = acceptedBytes(response.body);
        if (!accepted) return withTruth(DesktopTransportStatus::serverRejected);
        truth.acceptedBytes = *accepted;
    } else {
        truth.uploadSessionExists = true;
    }

    response = request(config_, L"GET", utf8ToWide("/api/v1/upload-sessions/" + serverSessionId + "/missing-ranges"), "", true);
    auto status = mapResponse(response);
    if (status != DesktopTransportStatus::uploaded) return withTruth(status, &response);
    const auto ranges = missingRanges(response.body);
    if (!ranges) return withTruth(DesktopTransportStatus::serverRejected);
    for (const auto& track : *tracks) {
        std::uint32_t pauseSeconds = 0;
        status = uploadFile(config_, track, serverSessionId, (*ranges)[trackIndex(track.role)], &truth.acceptedBytes,
                            &pauseSeconds);
        if (status != DesktopTransportStatus::uploaded) {
            auto result = withTruth(status);
            result.retryAfterSeconds = pauseSeconds;
            return result;
        }
    }

    response = request(config_, L"GET", utf8ToWide("/api/v1/upload-sessions/" + serverSessionId + "/missing-ranges"), "", true);
    status = mapResponse(response);
    if (status != DesktopTransportStatus::uploaded) return withTruth(status, &response);
    const auto remaining = missingRanges(response.body);
    if (!remaining) return withTruth(DesktopTransportStatus::serverRejected);
    for (const auto& rangesForTrack : *remaining) {
        if (!rangesForTrack.empty()) return withTruth(DesktopTransportStatus::retryableFailure);
    }

    std::string trackJson;
    for (std::size_t index = 0; index < tracks->size(); ++index) {
        if (index != 0) trackJson += ',';
        const auto& track = (*tracks)[index];
        trackJson += "{\"track_role\":\"" + track.role + "\",\"codec\":\"" + track.codec +
            "\",\"sample_rate_hz\":" + std::to_string(track.sampleRate) +
            ",\"channel_count\":" + std::to_string(track.channels) +
            ",\"duration_seconds\":" + std::to_string(track.durationSeconds) +
            ",\"byte_length\":" + std::to_string(track.bytes) + ",\"sha256\":\"" + track.sha256 + "\"}";
    }
    const auto finalizeBody = "{\"manifest_sha256\":\"" + (*tracks)[0].sha256 + "\",\"tracks\":[" + trackJson + "]}";
    response = request(config_, L"POST", utf8ToWide("/api/v1/upload-sessions/" + serverSessionId + "/finalize"),
                       finalizeBody, true);
    status = mapResponse(response);
    if (status == DesktopTransportStatus::uploaded) truth.finalized = true;
    return withTruth(status, &response);
#endif
}

} // namespace graf::windows
