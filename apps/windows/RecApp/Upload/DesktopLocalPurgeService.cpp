#include "DesktopLocalPurgeService.h"

#include <system_error>

namespace graf::windows {

bool DesktopLocalPurgeService::purge(const std::filesystem::path& packageDirectory, LocalPurgeProof proof) {
    if (packageDirectory.empty() || proof == LocalPurgeProof::none || !std::filesystem::exists(packageDirectory)) return false;
    std::error_code error;
    std::filesystem::remove_all(packageDirectory, error);
    return !error && !std::filesystem::exists(packageDirectory);
}

} // namespace graf::windows
