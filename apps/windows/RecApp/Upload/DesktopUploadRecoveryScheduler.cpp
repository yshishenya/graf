#include "DesktopUploadRecoveryScheduler.h"

namespace graf::windows {

DesktopUploadRecoveryScheduler::DesktopUploadRecoveryScheduler(DesktopUploadQueueService& queue, RetryHandler retry,
                                                               std::uint32_t maxAttempts)
    : queue_(queue), retry_(std::move(retry)), maxAttempts_(maxAttempts) {}

std::size_t DesktopUploadRecoveryScheduler::run(RecoveryTrigger) {
    std::size_t handled = 0;
    while (const auto item = queue_.nextPending()) {
        if (item->attempts >= maxAttempts_) {
            (void)queue_.markRetry(item->localRecordingId, "retry_budget_exhausted");
            break;
        }
        ++handled;
        if (retry_ && retry_(*item)) (void)queue_.markUploaded(item->localRecordingId);
        else (void)queue_.markRetry(item->localRecordingId, "transport_unavailable");
        if (handled >= 32) break;
    }
    return handled;
}

} // namespace graf::windows
