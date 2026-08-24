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
        const auto status = retry_ ? retry_(*item) : DesktopTransportStatus::retryableFailure;
        switch (status) {
        case DesktopTransportStatus::uploaded:
            (void)queue_.markUploaded(item->localRecordingId);
            break;
        case DesktopTransportStatus::authRequired:
            (void)queue_.markNeedsAuth(item->localRecordingId);
            break;
        case DesktopTransportStatus::invalidPackage:
            (void)queue_.markQuarantined(item->localRecordingId, "invalid_package");
            break;
        case DesktopTransportStatus::serverRejected:
            (void)queue_.markRetry(item->localRecordingId, "server_rejected");
            break;
        case DesktopTransportStatus::unsupportedPlatform:
            (void)queue_.markRetry(item->localRecordingId, "unsupported_platform");
            break;
        case DesktopTransportStatus::retryableFailure:
            (void)queue_.markRetry(item->localRecordingId, "transport_unavailable");
            break;
        }
        if (handled >= 32) break;
    }
    return handled;
}

} // namespace graf::windows
