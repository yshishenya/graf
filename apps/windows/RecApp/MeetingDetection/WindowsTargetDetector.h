#pragma once

#include "VerifiedTargetRegistry.h"

#include <chrono>
#include <optional>

namespace graf::windows {

using DetectionClock = std::chrono::steady_clock;

struct TargetObservation {
    VerifiedTargetIdentity identity;
    std::uint32_t processId = 0;
    std::uint64_t processCreatedAt = 0;
    bool hasRenderStream = false;
    bool hasCaptureStream = false;
    bool signatureVerified = false;
};

enum class TargetDetectionStatus { ready, noVerifiedTargets, platformUnavailable, enumerationFailed };

struct TargetDetectionSnapshot {
    TargetDetectionStatus status = TargetDetectionStatus::platformUnavailable;
    DetectionClock::time_point observedAt{};
    std::vector<TargetObservation> observations;
};

class WindowsTargetDetector final {
public:
    // Call off the UI thread. Initializes a scoped MTA; no audio is captured and
    // no processes are enrolled. Empty/unavailable evidence always fails closed.
    [[nodiscard]] static TargetDetectionSnapshot snapshot(const VerifiedTargetRegistry& registry);
    // Read-only proof for a known installed process, NOT approval/enrollment.
    // No displayName: a process name never establishes trust.
    [[nodiscard]] static std::optional<TargetObservation> inspectProcess(std::uint32_t processId);
    [[nodiscard]] static bool isPromptCandidate(const TargetObservation& observation,
                                               const VerifiedTargetRegistry& registry) noexcept;
};

} // namespace graf::windows
