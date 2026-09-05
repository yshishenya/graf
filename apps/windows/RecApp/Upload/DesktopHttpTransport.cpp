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

struct ByteRange {
    std::uint64_t start = 0;
    std::uint64_t end = 0;
};

struct RemoteUploadState {
    std::string meetingId;
    std::string sessionId;
    std::string sessionStatus;
    UploadServerTruth truth;
    bool blockedByConflict = false;
    bool needsNewUploadSession = false;
};

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

std::optional<std::string> nestedStringField(std::string_view json, std::string_view objectKey,
                                             std::string_view field) {
    const auto object = jsonObjectField(json, objectKey);
    if (!object) return std::nullopt;
    return jsonStringField(*object, field);
}

std::optional<RemoteUploadState> parseRemoteState(std::string_view json, std::string_view localRecordingId) {
    const auto meetingId = nestedStringField(json, "meeting", "meeting_id");
    if (!meetingId || !isSafeIdentifier(*meetingId)) return std::nullopt;
    RemoteUploadState result;
    result.meetingId = *meetingId;
    result.truth.localRecordingId = std::string(localRecordingId);
    result.truth.meetingExists = true;
    if (const auto session = jsonObjectField(json, "upload_session")) {
        if (const auto id = jsonStringField(*session, "session_id")) {
            if (!isSafeIdentifier(*id)) return std::nullopt;
            result.sessionId = *id;
            result.truth.uploadSessionExists = true;
        }
        if (const auto status = jsonStringField(*session, "status")) result.sessionStatus = *status;
        if (const auto accepted = acceptedBytes(*session)) result.truth.acceptedBytes = *accepted;
    }
    const auto conflictState = nestedStringField(json, "conflict", "state");
    const auto nextAction = nestedStringField(json, "conflict", "next_action");
    result.needsNewUploadSession =
        (conflictState && *conflictState == "upload_session_expired") ||
        (nextAction && *nextAction == "create_upload_session") ||
        result.sessionStatus == "expired";
    result.blockedByConflict = conflictState && *conflictState != "none" && !result.needsNewUploadSession;
    return result;
}

bool isUnknownRecording(const HttpResponse& response) {
    return response.status == 404 && jsonStringField(response.body, "code") == std::optional<std::string>("recording_not_found");
}

DesktopTransportStatus uploadFile(const DesktopHttpConfig& config, const LocalTrack& track, std::string_view sessionId,
                                  const std::vector<ByteRange>& ranges,
                                  std::array<std::uint64_t, 3>* accepted) {
    std::ifstream input(track.path, std::ios::binary);
    if (!input) return DesktopTransportStatus::invalidPackage;
    if (sha256File(track.path) != track.sha256) return DesktopTransportStatus::invalidPackage;
    const auto partSize = std::clamp(config.partSizeBytes, std::size_t(64 * 1024), kMaxPartBytes);
    for (const auto range : ranges) {
        for (std::uint64_t offset = range.start; offset < range.end;) {
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
            if (status != DesktopTransportStatus::uploaded) return status;
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

DesktopHttpTransport::DesktopHttpTransport(DesktopHttpConfig config)
    : config_(std::move(config)) {
    config_.partSizeBytes = std::clamp(config_.partSizeBytes, std::size_t(64 * 1024), kMaxPartBytes);
}

DesktopTransportResult DesktopHttpTransport::upload(const UploadCustodyItem& item) const {
#ifndef _WIN32
    (void)item;
    return {DesktopTransportStatus::unsupportedPlatform, std::nullopt};
#else
    std::uint32_t durationSeconds = 0;
    const auto tracks = packageTracks(item, &durationSeconds);
    if (!tracks || !isSafeIdentifier(item.directoryId) || !isSafeIdentifier(item.localRecordingId) ||
        !isSafeIdentifier(item.sessionId)) {
        return {DesktopTransportStatus::invalidPackage, std::nullopt};
    }
    UploadServerTruth truth;
    truth.localRecordingId = item.localRecordingId;
    const auto localRevision = item.directoryId + "--initial";
    auto withTruth = [&truth](DesktopTransportStatus status) {
        return DesktopTransportResult{status, truth.meetingExists ? std::optional<UploadServerTruth>(truth) : std::nullopt};
    };

    std::optional<RemoteUploadState> remote;
    const auto syncPath = std::string("/api/v1/desktop/recordings/") + item.directoryId +
        "/sync-state?local_media_revision_id=" + localRevision;
    auto response = request(config_, L"GET", utf8ToWide(syncPath), "", true);
    if (isUnknownRecording(response)) {
        remote = std::nullopt;
    } else {
        const auto syncStatus = mapResponse(response);
        if (syncStatus != DesktopTransportStatus::uploaded) return withTruth(syncStatus);
        remote = parseRemoteState(response.body, item.localRecordingId);
        if (!remote) return withTruth(DesktopTransportStatus::serverRejected);
        truth = remote->truth;
        if (remote->blockedByConflict) return withTruth(DesktopTransportStatus::serverRejected);
        if (!remote->needsNewUploadSession &&
            (remote->sessionStatus == "finalized" || remote->sessionStatus == "degraded")) {
            truth.finalized = true;
            return withTruth(DesktopTransportStatus::uploaded);
        }
    }

    std::string meetingId = remote ? remote->meetingId : std::string{};
    if (meetingId.empty()) {
        const auto meetingRequest = DesktopApiClient::createMeetingRequest(
            item.directoryId, localRevision, durationSeconds);
        if (!meetingRequest) return withTruth(DesktopTransportStatus::invalidPackage);
        const auto createBody = std::string("{\"local_recording_id\":\"") +
            jsonEscape(meetingRequest->localRecordingId) +
            "\",\"local_media_revision_id\":\"" + jsonEscape(meetingRequest->localMediaRevisionId) +
            "\",\"source_kind\":\"" + jsonEscape(meetingRequest->sourceKind) +
            "\",\"media_scribe_source_mode\":\"" + jsonEscape(meetingRequest->mediaScribeSourceMode) +
            "\",\"duration_seconds\":" + std::to_string(meetingRequest->durationSeconds) + "}";
        const auto meetingKey = DesktopApiClient::idempotencyKey("meeting", item.directoryId, item.sessionId);
        if (meetingKey.empty()) return withTruth(DesktopTransportStatus::invalidPackage);
        response = request(config_, L"POST", L"/api/v1/meetings", createBody, true, meetingKey);
        const auto status = mapResponse(response);
        if (status != DesktopTransportStatus::uploaded) return withTruth(status);
        const auto createdMeetingId = jsonStringField(response.body, "meeting_id");
        if (!createdMeetingId || !isSafeIdentifier(*createdMeetingId)) return withTruth(DesktopTransportStatus::serverRejected);
        meetingId = *createdMeetingId;
        truth.meetingExists = true;
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
        const std::string sessionScope = remote && remote->needsNewUploadSession
            ? std::string("upload-session-retry-") + std::to_string(item.attempts)
            : std::string("upload-session");
        const auto sessionKey = DesktopApiClient::idempotencyKey(sessionScope, item.directoryId, item.sessionId);
        if (sessionKey.empty()) return withTruth(DesktopTransportStatus::invalidPackage);
        const auto sessionBody = std::string("{\"expected_tracks\":") + expectedTracks +
            ",\"expected_track_sizes\":" + expectedSizes + ",\"manifest_sha256\":\"" +
            sessionRequest->manifestSha256 + "\"}";
        response = request(config_, L"POST", utf8ToWide("/api/v1/meetings/" + meetingId + "/upload-sessions"),
                           sessionBody, true, sessionKey);
        const auto status = mapResponse(response);
        if (status != DesktopTransportStatus::uploaded) return withTruth(status);
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
    if (status != DesktopTransportStatus::uploaded) return withTruth(status);
    const auto ranges = missingRanges(response.body);
    if (!ranges) return withTruth(DesktopTransportStatus::serverRejected);
    for (const auto& track : *tracks) {
        status = uploadFile(config_, track, serverSessionId, (*ranges)[trackIndex(track.role)], &truth.acceptedBytes);
        if (status != DesktopTransportStatus::uploaded) return withTruth(status);
    }

    response = request(config_, L"GET", utf8ToWide("/api/v1/upload-sessions/" + serverSessionId + "/missing-ranges"), "", true);
    status = mapResponse(response);
    if (status != DesktopTransportStatus::uploaded) return withTruth(status);
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
    return withTruth(status);
#endif
}

} // namespace graf::windows
