#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <cstdint>
#include <string>
#include <string_view>

namespace graf::windows {

struct MetadataSnapshot {
    std::string appVersion;
    std::string osBuild;
    std::string architecture;
    SessionState state = SessionState::idle;
    ReasonCode reason = ReasonCode::none;
    std::uint64_t droppedFrames = 0;
    std::uint64_t overflowCount = 0;
    std::uint64_t durationMs = 0;
    std::string endpointFingerprint;
};

class MetadataSafeDiagnostics final {
public:
    [[nodiscard]] static std::string redactedEndpointFingerprint(std::string_view stableEndpointIdentity);
    [[nodiscard]] static std::string serialize(const MetadataSnapshot& snapshot);
};

} // namespace graf::windows
