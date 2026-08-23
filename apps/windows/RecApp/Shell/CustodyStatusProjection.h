#pragma once

#include "../Upload/DesktopUploadQueueService.h"

#include <string>

namespace graf::windows {

struct CustodyStatusProjection {
    std::string localRecordingId;
    UploadQueueStatus status = UploadQueueStatus::pending;
    std::uint32_t attempts = 0;
    std::string safeReason;
};

class CustodyStatusProjector final {
public:
    [[nodiscard]] static CustodyStatusProjection project(const UploadCustodyItem& item) {
        return {item.localRecordingId, item.status, item.attempts, item.safeReason};
    }
};

} // namespace graf::windows
