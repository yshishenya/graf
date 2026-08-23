#include "DesktopApiClient.h"

#include <cctype>

namespace graf::windows {

std::optional<CreateMeetingRequest> DesktopApiClient::createMeetingRequest(
    std::string_view localRecordingId,
    std::string_view localMediaRevisionId,
    std::uint32_t durationSeconds) {
    if (!safeIdentity(localRecordingId) || !safeIdentity(localMediaRevisionId) || durationSeconds == 0) {
        return std::nullopt;
    }
    return CreateMeetingRequest{
        std::string(localRecordingId),
        std::string(localMediaRevisionId),
        std::string(kV5SourceKind),
        std::string(kV5MediaScribeSourceMode),
        durationSeconds,
    };
}

std::optional<UploadSessionRequest> DesktopApiClient::uploadSessionRequest(
    const std::array<std::uint64_t, 3>& expectedTrackSizes,
    std::string_view manifestSha256) {
    if (!sha256(manifestSha256)) {
        return std::nullopt;
    }
    return UploadSessionRequest{kV5WireRoles, expectedTrackSizes, std::string(manifestSha256)};
}

std::string DesktopApiClient::idempotencyKey(
    std::string_view scope,
    std::string_view directoryId,
    std::string_view sessionId) {
    if (!safeIdentity(scope) || !safeIdentity(directoryId) || !safeIdentity(sessionId)) {
        return {};
    }
    return "desktop-upload:" + std::string(scope) + ":" + std::string(directoryId) + ":" + std::string(sessionId);
}

bool DesktopApiClient::safeIdentity(std::string_view value) noexcept {
    if (value.empty() || value.size() > 300) {
        return false;
    }
    for (const unsigned char character : value) {
        if (!(std::isalnum(character) || character == '-' || character == '_')) {
            return false;
        }
    }
    return true;
}

bool DesktopApiClient::sha256(std::string_view value) noexcept {
    if (value.size() != 64) {
        return false;
    }
    for (const unsigned char character : value) {
        if (!std::isxdigit(character) || std::isupper(character)) {
            return false;
        }
    }
    return true;
}

} // namespace graf::windows
