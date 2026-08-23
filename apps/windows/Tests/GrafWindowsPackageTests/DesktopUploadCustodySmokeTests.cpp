#include "../../RecApp/Upload/DesktopLocalPurgeService.h"
#include "../../RecApp/Upload/DesktopUploadQueueService.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>

int main() {
    using namespace graf::windows;
    const auto directory = std::filesystem::temp_directory_path() / "graf-feature-200-custody";
    std::filesystem::create_directories(directory);
    assert(!DesktopLocalPurgeService::purge(directory, LocalPurgeProof::none));
    assert(DesktopLocalPurgeService::purge(directory, LocalPurgeProof::tombstoneConfirmed));
    return 0;
}
