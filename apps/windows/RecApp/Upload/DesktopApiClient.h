#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace graf::windows {

struct CreateMeetingRequest {
    std::string localRecordingId;
    std::string localMediaRevisionId;
    std::string sourceKind;
    std::string mediaScribeSourceMode;
    std::uint32_t durationSeconds = 0;
};

struct UploadSessionRequest {
    std::array<std::string_view, 3> expectedTracks = kV5WireRoles;
    std::array<std::uint64_t, 3> expectedTrackSizes{};
    std::string manifestSha256;
};

class DesktopApiClient final {
public:
    static constexpr std::string_view createMeetingPath = "/api/v1/meetings";
    static constexpr std::string_view createUploadSessionSuffix = "/upload-sessions";

    [[nodiscard]] static std::optional<CreateMeetingRequest> createMeetingRequest(
        std::string_view localRecordingId,
        std::string_view localMediaRevisionId,
        std::uint32_t durationSeconds);

    [[nodiscard]] static std::optional<UploadSessionRequest> uploadSessionRequest(
        const std::array<std::uint64_t, 3>& expectedTrackSizes,
        std::string_view manifestSha256);

    [[nodiscard]] static std::string idempotencyKey(
        std::string_view scope,
        std::string_view directoryId,
        std::string_view sessionId);

private:
    [[nodiscard]] static bool safeIdentity(std::string_view value) noexcept;
    [[nodiscard]] static bool sha256(std::string_view value) noexcept;
};

} // namespace graf::windows
