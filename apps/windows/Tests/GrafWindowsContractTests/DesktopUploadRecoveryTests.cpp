#include "../../RecApp/Upload/DesktopUploadRecoveryScheduler.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>

int main() {
    using namespace graf::windows;
    const auto path = std::filesystem::temp_directory_path() / "graf-feature-200-recovery.json";
    std::filesystem::remove(path);
    DesktopUploadQueueService queue(path); assert(queue.load());
    assert(queue.enqueue({"recording", "directory", "session", path.parent_path(), UploadQueueStatus::pending, {}, 0, ""}));
    DesktopUploadRecoveryScheduler scheduler(queue, [](const UploadCustodyItem&) { return true; });
    assert(scheduler.run(RecoveryTrigger::launch) == 1);
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);
    std::filesystem::remove(path);
    return 0;
}
