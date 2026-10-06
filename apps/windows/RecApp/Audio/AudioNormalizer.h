#pragma once

#include "AudioTypes.h"

#include <cstddef>
#include <cstdint>

namespace graf::windows {

class AudioNormalizer final {
public:
    static constexpr std::uint32_t targetSampleRate = 48'000;

    explicit AudioNormalizer(std::size_t maxOutputFrames = 28'800);

    // Converts one bounded WASAPI batch with its unrounded timestamp to mono float at 48 kHz. The output
    // never contains wall-clock padding; a missing source sample is a gap.
    [[nodiscard]] bool normalize(AudioBatch input, std::uint64_t qpc100ns, AudioBatch& output);
    [[nodiscard]] bool healthy() const noexcept { return healthy_; }

private:
    void fail() noexcept { healthy_ = false; }

    std::size_t maxOutputFrames_;
    std::uint32_t inputSampleRate_ = 0;
    std::uint64_t submittedFrames_ = 0;
    std::uint64_t deliveredFrames_ = 0;
    std::uint64_t clockDomain_ = 0;
    std::uint64_t routeGeneration_ = 0;
    std::uint64_t firstQpc_ = 0;
    std::uint64_t lastQpc_ = 0;
    std::uint16_t inputChannels_ = 0;
    float previousSample_ = 0.0F;
    bool havePreviousSample_ = false;
    bool initialized_ = false;
    bool healthy_ = true;
};

} // namespace graf::windows
