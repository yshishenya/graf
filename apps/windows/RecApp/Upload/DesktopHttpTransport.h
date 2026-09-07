#pragma once

#include "DesktopUploadQueueService.h"

#include <cstddef>
#include <atomic>
#include <cstdint>
#include <functional>
#include <optional>
#include <memory>
#include <string>
#include <string_view>

namespace graf::windows {

enum class DesktopTransportStatus {
    uploaded,
    authRequired,
    retryableFailure,
    serverRejected,
    invalidPackage,
    unsupportedPlatform,
};

struct DesktopTransportResult {
    DesktopTransportStatus status = DesktopTransportStatus::retryableFailure;
    std::optional<UploadServerTruth> serverTruth;
    std::string safeReason = {};
};

struct DesktopRemoteUploadState {
    std::string meetingId;
    std::string sessionId;
    std::string sessionStatus;
    UploadServerTruth truth;
    bool blockedByConflict = false;
    bool needsNewUploadSession = false;
};

struct DesktopHttpConfig {
    std::string baseOrigin = "https://rec.2brain.pro";
    std::string workspaceId;
    std::string deviceId;
    std::string clientVersion = "windows-feature-200";
    std::size_t partSizeBytes = 4 * 1024 * 1024;
    // Copied on the UI thread before dispatch; never persisted. No UI callbacks.
    std::string sessionToken = {};
    std::shared_ptr<const std::atomic_bool> cancellation = {};
};

class DesktopHttpTransport final {
public:
    explicit DesktopHttpTransport(DesktopHttpConfig config = {});

    [[nodiscard]] DesktopTransportResult upload(const UploadCustodyItem& item) const;
    [[nodiscard]] std::optional<DesktopAccountIdentity> accountIdentity() const;
    struct IdentityResponse {
        std::uint32_t status = 0;
        std::string body;
        bool transportFailed = false;
    };
    struct IdentityResult {
        std::optional<DesktopAccountIdentity> identity;
        DesktopTransportStatus status = DesktopTransportStatus::authRequired;
    };
    // Read-only, bounded, no-redirect WinHTTP GET; retain HTTP/transport failure
    // separately so an unavailable server does not require a new login.
    using IdentityGet = std::function<IdentityResponse(const DesktopHttpConfig&, std::string_view)>;
    [[nodiscard]] IdentityResult accountIdentity(const IdentityGet& get) const;
    [[nodiscard]] static std::optional<std::string> decodeActiveWorkspace(std::string_view json);
    [[nodiscard]] static std::optional<DesktopAccountIdentity> decodeAccountIdentity(std::string_view json);
    [[nodiscard]] static std::string_view ownerBlockReason(
        const UploadCustodyItem& item, const std::optional<DesktopAccountIdentity>& identity);
    // The production sync-state decoder is portable so recovery decisions can
    // be tested without WinHTTP or a live recording/account.
    [[nodiscard]] static std::optional<DesktopRemoteUploadState> decodeSyncState(
        std::string_view json, std::string_view localRecordingId);
    [[nodiscard]] static std::string replacementUploadSessionKey(
        const UploadCustodyItem& item, std::string_view expiredSessionId);

private:
    DesktopHttpConfig config_;
};

} // namespace graf::windows
