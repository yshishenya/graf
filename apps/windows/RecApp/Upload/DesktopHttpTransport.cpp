#include "DesktopHttpTransport.h"

#include "DesktopApiClient.h"
#include "../Recording/LocalRecordingPackage.h"
#include "../Storage/Sha256.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <fstream>
#include <limits>
#include <optional>
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

#ifdef _WIN32

constexpr std::size_t kMaxJsonResponseBytes = 2 * 1024 * 1024;

std::string jsonEscape(std::string_view value) {
    std::string result;
    result.reserve(value.size());
    for (const char character : value) {
        switch (character) {
        case '\\': result += "\\\\"; break;
        case '"': result += "\\\""; break;
        case '\n': result += "\\n"; break;
        case '\r': result += "\\r"; break;
        case '\t': result += "\\t"; break;
        default: result += character; break;
        }
    }
    return result;
}

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
    const auto marker = std::string("\"") + std::string(key) + "\":");
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

std::optional<std::vector<LocalTrack>> packageTracks(const UploadCustodyItem& item, std::uint32_t* durationSeconds) {
    const auto snapshot = LocalRecordingPackage::inspect(item.packageDirectory);
    if (snapshot.integrity != PackageIntegrity::valid) return std::nullopt;
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
};

HttpResponse request(const DesktopHttpConfig& config, std::wstring method, std::wstring path,
                     const std::string& body, bool jsonBody, std::string_view idempotencyKey = {},
                     std::optional<std::uint64_t> byteOffset = std::nullopt,
                     std::string_view contentSha256 = {}) {
    HttpResponse result;
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
    WinHttpSetTimeouts(session, 15'000, 15'000, 60'000, 60'000);
    HINTERNET connection = WinHttpConnect(session, components.lpszHostName, components.nPort, 0);
    HINTERNET handle = connection ? WinHttpOpenRequest(connection, method.c_str(), path.c_str(), nullptr,
                                                        WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
                                                        WINHTTP_FLAG_SECURE) : nullptr;
    if (!handle) {
        if (connection) WinHttpCloseHandle(connection);
        WinHttpCloseHandle(session);
        result.transportFailed = true;
        return result;
    }
    std::wstring headers = L"Accept: application/json\r\nX-Client-Version: " + utf8ToWide(config.clientVersion) + L"\r\n";
    if (!config.workspaceId.empty()) headers += L"X-Workspace-Id: " + utf8ToWide(config.workspaceId) + L"\r\n";
    if (!config.deviceId.empty()) headers += L"X-Device-Id: " + utf8ToWide(config.deviceId) + L"\r\n";
    if (!idempotencyKey.empty()) headers += L"Idempotency-Key: " + utf8ToWide(idempotencyKey) + L"\r\n";
    if (byteOffset) headers += L"X-Byte-Offset: " + std::to_wstring(*byteOffset) + L"\r\n";
    if (!contentSha256.empty()) headers += L"X-Content-SHA256: " + utf8ToWide(contentSha256) + L"\r\n";
    if (config.authSessionToken) {
        const auto token = config.authSessionToken();
        if (!token.empty()) headers += L"X-Auth-Session: " + utf8ToWide(token) + L"\r\n";
    }
    headers += jsonBody ? L"Content-Type: application/json\r\n" : L"Content-Type: application/octet-stream\r\n";
    const auto sent = WinHttpSendRequest(handle, headers.c_str(), static_cast<DWORD>(headers.size()),
        body.empty() ? WINHTTP_NO_REQUEST_DATA : const_cast<char*>(body.data()), static_cast<DWORD>(body.size()),
        static_cast<DWORD>(body.size()), 0);
    if (!sent || !WinHttpReceiveResponse(handle, nullptr)) {
        result.transportFailed = true;
    } else {
        DWORD statusSize = sizeof(result.status);
        WinHttpQueryHeaders(handle, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                            WINHTTP_HEADER_NAME_BY_INDEX, &result.status, &statusSize, WINHTTP_NO_HEADER_INDEX);
        while (result.body.size() < kMaxJsonResponseBytes) {
            DWORD available = 0;
            if (!WinHttpQueryDataAvailable(handle, &available) || available == 0) break;
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
    }
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

bool uploadFile(const DesktopHttpConfig& config, const LocalTrack& track, std::string_view sessionId) {
    std::ifstream input(track.path, std::ios::binary);
    if (!input) return false;
    if (sha256File(track.path) != track.sha256) return false;
    const auto partSize = std::clamp(config.partSizeBytes, std::size_t(64 * 1024), kMaxPartBytes);
    for (std::uint64_t offset = 0, part = 0; offset < track.bytes; ++part) {
        const auto length = static_cast<std::size_t>(std::min<std::uint64_t>(partSize, track.bytes - offset));
        std::string data(length, '\0');
        input.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
        input.read(data.data(), static_cast<std::streamsize>(data.size()));
        if (input.gcount() != static_cast<std::streamsize>(data.size())) return false;
        const auto path = L"/api/v1/upload-sessions/" + utf8ToWide(sessionId) + L"/tracks/" +
            utf8ToWide(track.role) + L"/parts/" + std::to_wstring(part);
        const auto response = request(config, L"PUT", path, data, false, {}, offset, sha256(data));
        if (response.status < 200 || response.status >= 300 || response.transportFailed) return false;
        offset += length;
    }
    return true;
}

#endif

} // namespace

DesktopHttpTransport::DesktopHttpTransport(DesktopHttpConfig config)
    : config_(std::move(config)) {
    config_.partSizeBytes = std::clamp(config_.partSizeBytes, std::size_t(64 * 1024), kMaxPartBytes);
}

DesktopTransportStatus DesktopHttpTransport::upload(const UploadCustodyItem& item) const {
#ifndef _WIN32
    (void)item;
    return DesktopTransportStatus::unsupportedPlatform;
#else
    std::uint32_t durationSeconds = 0;
    const auto tracks = packageTracks(item, &durationSeconds);
    if (!tracks || !isSafeIdentifier(item.directoryId) || !isSafeIdentifier(item.localRecordingId) ||
        !isSafeIdentifier(item.sessionId)) {
        return DesktopTransportStatus::invalidPackage;
    }
    const auto localRevision = item.directoryId + "--initial";
    const auto createBody = std::string("{\"local_recording_id\":\"") + jsonEscape(item.directoryId) +
        "\",\"local_media_revision_id\":\"" + jsonEscape(localRevision) +
        "\",\"source_kind\":\"initial_mixed_recording\",\"media_scribe_source_mode\":\"single_wav_v1\",\"duration_seconds\":" +
        std::to_string(durationSeconds) + "}";
    const auto meetingKey = DesktopApiClient::idempotencyKey("meeting", item.directoryId, item.sessionId);
    if (meetingKey.empty()) return DesktopTransportStatus::invalidPackage;
    auto response = request(config_, L"POST", L"/api/v1/meetings", createBody, true, meetingKey);
    auto status = mapResponse(response);
    if (status != DesktopTransportStatus::uploaded) return status;
    const auto meetingId = jsonStringField(response.body, "meeting_id");
    if (!meetingId || !isSafeIdentifier(*meetingId)) return DesktopTransportStatus::serverRejected;
    std::string sizes = "{\"manifest\":" + std::to_string((*tracks)[0].bytes) +
        ",\"media\":" + std::to_string((*tracks)[1].bytes) + ",\"playback\":" + std::to_string((*tracks)[2].bytes) + "}";
    const auto sessionBody = std::string("{\"expected_tracks\":[\"manifest\",\"media\",\"playback\"],\"expected_track_sizes\":") +
        sizes + ",\"manifest_sha256\":\"" + (*tracks)[0].sha256 + "\"}";
    const auto sessionKey = DesktopApiClient::idempotencyKey("upload-session", item.directoryId, item.sessionId);
    if (sessionKey.empty()) return DesktopTransportStatus::invalidPackage;
    response = request(config_, L"POST", utf8ToWide("/api/v1/meetings/" + *meetingId + "/upload-sessions"),
                       sessionBody, true, sessionKey);
    status = mapResponse(response);
    if (status != DesktopTransportStatus::uploaded) return status;
    const auto serverSessionId = jsonStringField(response.body, "session_id");
    if (!serverSessionId || !isSafeIdentifier(*serverSessionId)) return DesktopTransportStatus::serverRejected;
    for (const auto& track : *tracks) {
        if (!uploadFile(config_, track, *serverSessionId)) return DesktopTransportStatus::retryableFailure;
    }
    std::string trackJson;
    for (std::size_t index = 0; index < tracks->size(); ++index) {
        if (index != 0) trackJson += ',';
        const auto& track = (*tracks)[index];
        trackJson += "{\"track_role\":\"" + track.role + "\",\"codec\":\"" + track.codec +
            "\",\"sample_rate_hz\":" + std::to_string(track.sampleRate) +
            ",\"channel_count\":" + std::to_string(track.channels) +
            ",\"duration_seconds\":" + std::to_string(track.durationSeconds) +
            ",\"byte_length\":" + std::to_string(track.bytes) + " ,\"sha256\":\"" + track.sha256 + "\"}";
    }
    const auto finalizeBody = "{\"manifest_sha256\":\"" + (*tracks)[0].sha256 + "\",\"tracks\":[" + trackJson + "]}";
    response = request(config_, L"POST", utf8ToWide("/api/v1/upload-sessions/" + *serverSessionId + "/finalize"),
                       finalizeBody, true);
    return mapResponse(response);
#endif
}

} // namespace graf::windows
