#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace graf::windows {

enum class WasapiDataFlow {
    render,
    capture,
};

enum class EndpointEnumerationError {
    none,
    platformUnavailable,
    noDefaultEndpoint,
    enumerationFailed,
};

struct WasapiEndpointSnapshot {
    std::string stableId;
    std::string friendlyName;
    WasapiDataFlow flow = WasapiDataFlow::render;
    std::uint32_t sampleRate = 0;
    std::uint16_t channels = 0;
    bool isDefault = false;
    bool isPhysicalMicrophone = false;
    std::uint64_t routeGeneration = 0;
};

struct EndpointEnumerationResult {
    EndpointEnumerationError error = EndpointEnumerationError::none;
    std::vector<WasapiEndpointSnapshot> endpoints;

    [[nodiscard]] bool ok() const noexcept { return error == EndpointEnumerationError::none; }
};

class WasapiEndpointEnumerator final {
public:
    [[nodiscard]] EndpointEnumerationResult snapshot() const;
    [[nodiscard]] static bool isAllowedMicrophone(const WasapiEndpointSnapshot& endpoint) noexcept;
};

} // namespace graf::windows
