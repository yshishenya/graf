#include "DesktopLocalPurgeService.h"

#include <system_error>
#include <utility>

namespace graf::windows {

DesktopLocalPurgeService::DesktopLocalPurgeService(std::filesystem::path custodyRoot)
    : custodyRoot_(std::move(custodyRoot)) {}

bool DesktopLocalPurgeService::purge(const std::filesystem::path& packageDirectory, LocalPurgeProof proof) const {
    if (custodyRoot_.empty() || packageDirectory.empty() || proof == LocalPurgeProof::none) return false;
    std::error_code error;
    const auto root = std::filesystem::weakly_canonical(custodyRoot_, error);
    if (error) return false;
    error.clear();
    const auto target = std::filesystem::weakly_canonical(packageDirectory, error);
    if (error || target == root || target.parent_path() != root || !std::filesystem::is_directory(target)) return false;
    std::filesystem::remove_all(packageDirectory, error);
    return !error && !std::filesystem::exists(target);
}

} // namespace graf::windows
