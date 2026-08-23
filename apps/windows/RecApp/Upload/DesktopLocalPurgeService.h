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
    explicit DesktopLocalPurgeService(std::filesystem::path custodyRoot);

    [[nodiscard]] bool purge(const std::filesystem::path& packageDirectory, LocalPurgeProof proof) const;

private:
    std::filesystem::path custodyRoot_;
};

} // namespace graf::windows
