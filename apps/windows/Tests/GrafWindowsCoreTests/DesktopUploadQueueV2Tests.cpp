#include "../../RecApp/Upload/DesktopUploadQueueService.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>

int main() {
    using namespace graf::windows;
    const auto path = std::filesystem::temp_directory_path() / "graf-feature-200-queue.json";
    std::filesystem::remove(path);
    DesktopUploadQueueService queue(path);
    assert(queue.load());
    assert(queue.enqueue({"recording", "directory", "session", path.parent_path(), UploadQueueStatus::pending, {}, 0, ""}));
    assert(!queue.enqueue({"recording", "directory", "session2", path.parent_path(), UploadQueueStatus::pending, {}, 0, ""}));
    assert(queue.reconcile({"recording", true, true, {10, 20, 30}, false}));
    assert(queue.items()[0].status == UploadQueueStatus::uploading);
    assert(queue.items()[0].acceptedBytes[1] == 20);
    DesktopUploadQueueService restarted(path);
    assert(restarted.load());
    assert(restarted.items().size() == 1 && restarted.items()[0].acceptedBytes[2] == 30);
    assert(queue.markUploaded("recording"));
    assert(!queue.nextPending().has_value());
    std::filesystem::remove(path);
    return 0;
}
