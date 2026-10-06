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
    bool playbackAvailable = false;
    // Wall clock of the captured audio, epoch milliseconds UTC, and the display
    // offset of its start. Zero means the package predates these fields or the
    // manifest did not carry a usable pair.
    std::uint64_t startedAtMs = 0;
    std::uint64_t stoppedAtMs = 0;
    int displayTimezoneOffsetMinutes = 0;
};

class LocalRecordingPackage final {
public:
    [[nodiscard]] static LocalRecordingPackageSnapshot inspect(
        const std::filesystem::path& directory,
        const std::filesystem::path& custodyRoot = {});
};

} // namespace graf::windows
