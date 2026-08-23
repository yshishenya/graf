#pragma once

#include "DesktopUploadQueueService.h"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>

namespace graf::windows {

enum class DesktopTransportStatus {
    uploaded,
    authRequired,
    retryableFailure,
    serverRejected,
    invalidPackage,
    unsupportedPlatform,
};

struct DesktopHttpConfig {
    std::string baseOrigin = "https://rec.2brain.pro";
    std::string workspaceId;
    std::string deviceId;
    std::string clientVersion = "windows-feature-200";
    std::size_t partSizeBytes = 4 * 1024 * 1024;
    std::function<std::string()> authSessionToken;
};

class DesktopHttpTransport final {
public:
    explicit DesktopHttpTransport(DesktopHttpConfig config = {});

    [[nodiscard]] DesktopTransportStatus upload(const UploadCustodyItem& item) const;

private:
    DesktopHttpConfig config_;
};

} // namespace graf::windows
