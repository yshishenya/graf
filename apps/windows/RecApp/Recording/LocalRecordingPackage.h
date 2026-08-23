#pragma once

#include "V5LocalRecordingWriter.h"

#include <filesystem>
#include <string>

namespace graf::windows {

enum class PackageIntegrity {
    missing,
    valid,
    malformed,
    degraded,
};

struct LocalRecordingPackageSnapshot {
    std::filesystem::path directory;
    std::string recordingId;
    PackageIntegrity integrity = PackageIntegrity::missing;
    std::uint64_t durationMs = 0;
    bool localPurgeRegistered = false;
};

class LocalRecordingPackage final {
public:
    [[nodiscard]] static LocalRecordingPackageSnapshot inspect(const std::filesystem::path& directory);
    [[nodiscard]] static bool registerLocalPurge(
        const std::filesystem::path& directory,
        const std::filesystem::path& custodyRoot = {});
};

} // namespace graf::windows
