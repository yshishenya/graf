#include "../../RecApp/Upload/DesktopUploadRecoveryScheduler.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>

int main() {
    using namespace graf::windows;
    const auto root = std::filesystem::temp_directory_path() / "graf-feature-200-recovery-root";
    const auto path = root / "desktop-upload-queue.json";
    const auto package = root / "recording";
    std::filesystem::remove_all(root);
    std::filesystem::create_directories(package);
    DesktopUploadQueueService queue(path, root); assert(queue.load());
    assert(queue.enqueue({"recording", "directory", "session", package, UploadQueueStatus::pending, {}, 0, ""}));
    assert(queue.enqueue({"auth-recording", "auth-directory", "auth-session", package, UploadQueueStatus::pending, {}, 0, ""}));
    assert(queue.enqueue({"invalid-recording", "invalid-directory", "invalid-session", package, UploadQueueStatus::pending, {}, 0, ""}));
    DesktopUploadRecoveryScheduler scheduler(queue, [](const UploadCustodyItem& item) {
        if (item.localRecordingId == "auth-recording") return DesktopTransportResult{DesktopTransportStatus::authRequired, std::nullopt};
        if (item.localRecordingId == "invalid-recording") return DesktopTransportResult{DesktopTransportStatus::invalidPackage, std::nullopt};
        return DesktopTransportResult{DesktopTransportStatus::uploaded, UploadServerTruth{"recording", true, true, {10, 20, 30}, true}};
    });
    assert(scheduler.run(RecoveryTrigger::launch) == 3);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);
    const std::array<std::uint64_t, 3> uploadedBytes{10, 20, 30};
    assert(queue.items()[0].acceptedBytes == uploadedBytes);
    assert(queue.items()[1].status == UploadQueueStatus::needsAuth);
    assert(queue.items()[2].status == UploadQueueStatus::quarantined);

    bool authRecovered = false;
    DesktopUploadRecoveryScheduler authScheduler(queue, [&](const UploadCustodyItem& item) {
        assert(item.localRecordingId == "auth-recording");
        authRecovered = true;
        return DesktopTransportResult{DesktopTransportStatus::uploaded,
                                      UploadServerTruth{"auth-recording", true, true, {1, 2, 3}, true}};
    });
    assert(authScheduler.run(RecoveryTrigger::authRecovered) == 1);
    assert(authRecovered && queue.items()[1].status == UploadQueueStatus::uploaded);

    assert(queue.enqueue({"retry-recording", "retry-directory", "retry-session", package, UploadQueueStatus::pending, {}, 0, ""}));
    DesktopUploadRecoveryScheduler retryScheduler(queue, [](const UploadCustodyItem&) {
        return DesktopTransportResult{
            DesktopTransportStatus::retryableFailure,
            UploadServerTruth{"retry-recording", true, true, {11, 22, 33}, false},
        };
    });
    assert(retryScheduler.run(RecoveryTrigger::networkRecovered) == 1);
    assert(queue.items()[3].status == UploadQueueStatus::retry);
    const std::array<std::uint64_t, 3> retriedBytes{11, 22, 33};
    assert(queue.items()[3].acceptedBytes == retriedBytes);
    std::filesystem::remove_all(root);
    return 0;
}
