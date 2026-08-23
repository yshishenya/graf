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
    DesktopUploadRecoveryScheduler scheduler(queue, [](const UploadCustodyItem&) { return true; });
    assert(scheduler.run(RecoveryTrigger::launch) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);
    std::filesystem::remove_all(root);
    return 0;
}
