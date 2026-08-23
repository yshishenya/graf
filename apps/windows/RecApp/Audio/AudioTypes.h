#pragma once

#include <cstdint>
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
    std::int64_t ptsFrames = 0;
    std::uint64_t clockDomain = 0;
    std::uint64_t routeGeneration = 0;
    bool discontinuity = false;
    std::vector<float> samples;
};

} // namespace graf::windows
