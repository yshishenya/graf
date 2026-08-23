#pragma once

#include <filesystem>

namespace graf::windows {

enum class LocalPurgeProof {
    none,
    serverDeletionConfirmed,
    tombstoneConfirmed,
    cryptographicUnrecoverabilityConfirmed,
};

class DesktopLocalPurgeService final {
public:
    [[nodiscard]] static bool purge(const std::filesystem::path& packageDirectory, LocalPurgeProof proof);
};

} // namespace graf::windows
