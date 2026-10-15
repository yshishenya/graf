#pragma once

#include <cstdint>
#include <optional>
#include <vector>

namespace graf::windows {

enum class AudioSource {
    systemRender,
    microphone,
};

struct AudioBatch {
    AudioSource source = AudioSource::systemRender;
    std::uint32_t sampleRate = 0;
    std::uint16_t channels = 0;
    std::int64_t ptsFrames = 0; // Canonical output only; normalizer input uses full QPC separately.
    std::uint64_t clockDomain = 0;
    std::uint64_t routeGeneration = 0;
    bool discontinuity = false;
    std::vector<float> samples;
    std::uint64_t normalizedFrameOffset = 0; // Continuous sample range before clock correction.
    // Native admission provenance only; raw samples still require validation.
    bool microphoneSuppressed = false;
    // nullopt is an unbound adapter; zero is the first native recording epoch.
    std::optional<std::uint64_t> microphonePrivacyEpoch = std::nullopt;
};

} // namespace graf::windows
