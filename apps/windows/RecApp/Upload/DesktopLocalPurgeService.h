#pragma once

#include <filesystem>
#include <cstdint>

namespace graf::windows {

enum class LocalPurgeProof {
    none,
    // Native user confirmation only; never server deletion/ACK evidence.
    userConfirmedLocalCopy,
    // A purge task the server created after it deleted the meeting, matched to
    // this row by the meeting identifier the server itself returned. Only the
    // purge pass may pass this value: the user did not confirm this copy, so it
    // must never be reachable from a menu action.
    serverRequestedPurge,
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
