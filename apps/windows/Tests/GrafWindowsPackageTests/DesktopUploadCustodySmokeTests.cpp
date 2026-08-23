#include "../../RecApp/Upload/DesktopLocalPurgeService.h"
#include "../../RecApp/Upload/DesktopUploadQueueService.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>

int main() {
    using namespace graf::windows;
    const auto root = std::filesystem::temp_directory_path() / "graf-feature-200-custody";
    const auto directory = root / "package";
    std::filesystem::remove_all(root);
    std::filesystem::create_directories(directory);
    DesktopLocalPurgeService purge(root);
    assert(!purge.purge(directory, LocalPurgeProof::none));
    assert(!purge.purge(std::filesystem::temp_directory_path(), LocalPurgeProof::tombstoneConfirmed));
    assert(purge.purge(directory, LocalPurgeProof::tombstoneConfirmed));
    std::filesystem::remove_all(root);
    return 0;
}
