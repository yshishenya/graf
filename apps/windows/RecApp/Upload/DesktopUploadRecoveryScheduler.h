#pragma once

#include "DesktopUploadQueueService.h"

#include <cstdint>
#include <functional>

namespace graf::windows {

enum class RecoveryTrigger {
    launch,
    activation,
    authRecovered,
    networkRecovered,
    wake,
    scheduled,
};

class DesktopUploadRecoveryScheduler final {
public:
    using RetryHandler = std::function<bool(const UploadCustodyItem&)>;

    DesktopUploadRecoveryScheduler(DesktopUploadQueueService& queue, RetryHandler retry,
                                   std::uint32_t maxAttempts = 8);
    [[nodiscard]] std::size_t run(RecoveryTrigger trigger);

private:
    DesktopUploadQueueService& queue_;
    RetryHandler retry_;
    std::uint32_t maxAttempts_;
};

} // namespace graf::windows
