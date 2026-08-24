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
        if (item.localRecordingId == "auth-recording") return DesktopTransportStatus::authRequired;
        if (item.localRecordingId == "invalid-recording") return DesktopTransportStatus::invalidPackage;
        return DesktopTransportStatus::uploaded;
    });
    assert(scheduler.run(RecoveryTrigger::launch) == 3);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);
    assert(queue.items()[1].status == UploadQueueStatus::needsAuth);
    assert(queue.items()[2].status == UploadQueueStatus::quarantined);
    std::filesystem::remove_all(root);
    return 0;
}
