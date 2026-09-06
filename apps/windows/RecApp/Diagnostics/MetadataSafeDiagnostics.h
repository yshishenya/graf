#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <cstdint>
#include <string>

namespace graf::windows {

struct MetadataSnapshot {
    std::string appVersion;
    std::string osBuild;
    std::string architecture;
    SessionState state = SessionState::idle;
    ReasonCode reason = ReasonCode::none;
    // Counts of canonical 480-sample / 10-ms blocks, not individual samples.
    std::uint64_t processedBlocks = 0;
    std::uint64_t writtenBlocks = 0;
    std::uint64_t durationMs = 0;
    std::string endpointIdentity; // Raw native identity; serialization always hashes it.
    bool trustedPrefixRetained = false;
};

class MetadataSafeDiagnostics final {
public:
    // Fixed allowlisted fields and bounded text keep every report below 1024 bytes.
    [[nodiscard]] static std::string serialize(const MetadataSnapshot& snapshot);
};

} // namespace graf::windows
