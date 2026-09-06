#pragma once

#include <filesystem>
#include <cstdint>

namespace graf::windows {

enum class LocalPurgeProof {
    none,
    // Native user confirmation only; never server deletion/ACK evidence.
    userConfirmedLocalCopy,
};

class DesktopLocalPurgeService final {
public:
    explicit DesktopLocalPurgeService(std::filesystem::path custodyRoot);

    [[nodiscard]] bool isSafePackageDirectory(const std::filesystem::path& packageDirectory,
                                              bool allowMissing = false) const;
    // Called only for a queue-validated package after native confirmation, on
    // an initialized COM STA. No permanent-delete fallback or server proof.
    [[nodiscard]] static bool recycle(const std::filesystem::path& packageDirectory, std::uintptr_t owner);

private:
    std::filesystem::path custodyRoot_;
};

} // namespace graf::windows
