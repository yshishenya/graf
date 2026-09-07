#include "AudioNormalizer.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace graf::windows {

AudioNormalizer::AudioNormalizer(std::size_t maxOutputFrames)
    : maxOutputFrames_(maxOutputFrames == 0 ? 1 : maxOutputFrames) {}

bool AudioNormalizer::normalize(AudioBatch input, std::uint64_t qpc100ns, AudioBatch& output) {
    output = {};
    if (!healthy_ || input.sampleRate < 8'000 || input.sampleRate > 192'000 || input.channels == 0 ||
        input.channels > 32 ||
        input.routeGeneration == 0 || input.clockDomain == 0 || input.discontinuity ||
        input.samples.empty() || input.samples.size() % input.channels != 0) {
        fail();
        return false;
    }

    const auto sourceFrames = input.samples.size() / input.channels;
    if (sourceFrames == 0 || sourceFrames > 4'800) {
        fail();
        return false;
    }
    for (const auto sample : input.samples) {
        if (!std::isfinite(sample)) {
            fail();
            return false;
        }
    }

    if (!initialized_) {
        initialized_ = true;
        inputSampleRate_ = input.sampleRate;
        clockDomain_ = input.clockDomain;
        routeGeneration_ = input.routeGeneration;
        inputChannels_ = input.channels;
        firstQpc_ = qpc100ns;
    } else if (input.sampleRate != inputSampleRate_ ||
               input.clockDomain != clockDomain_ || input.routeGeneration != routeGeneration_ ||
               input.channels != inputChannels_ || qpc100ns <= lastQpc_) {
        fail();
        return false;
    }
    lastQpc_ = qpc100ns;
    if (submittedFrames_ > (1ULL << 52) - sourceFrames) {
        fail();
        return false;
    }

    std::vector<float> mono(sourceFrames, 0.0F);
    for (std::size_t frame = 0; frame < sourceFrames; ++frame) {
        for (std::size_t channel = 0; channel < input.channels; ++channel) {
            mono[frame] += input.samples[frame * input.channels + channel];
        }
        mono[frame] /= static_cast<float>(input.channels);
    }

    // Resampler phase follows samples, not a second interpretation of QPC.
    const auto sourceStart = static_cast<double>(submittedFrames_);
    const auto sourceEnd = sourceStart + static_cast<double>(sourceFrames);
    const auto step = static_cast<double>(input.sampleRate) / targetSampleRate;
    auto nextInputPosition = static_cast<double>(deliveredFrames_) * step;
    output.source = input.source;
    output.sampleRate = targetSampleRate;
    output.channels = 1;
    output.clockDomain = input.clockDomain;
    output.routeGeneration = input.routeGeneration;
    output.discontinuity = input.discontinuity;
    output.normalizedFrameOffset = deliveredFrames_;
    const auto origin = (firstQpc_ / 10'000'000) * targetSampleRate +
        ((firstQpc_ % 10'000'000) * targetSampleRate + 5'000'000) / 10'000'000;
    const auto elapsedFrames = static_cast<long double>(qpc100ns - firstQpc_) * targetSampleRate / 10'000'000;
    const auto residual = elapsedFrames - static_cast<long double>(submittedFrames_) * targetSampleRate / input.sampleRate;
    output.ptsFrames = static_cast<std::int64_t>(origin + deliveredFrames_) +
        static_cast<std::int64_t>(std::llround(residual));
    output.samples.reserve(std::min(
        maxOutputFrames_, static_cast<std::size_t>(std::ceil(sourceFrames / step)) + 1));

    // Keep the native-rate path lossless. The interpolating path intentionally
    // holds the final source sample until the next batch supplies its right
    // neighbour; at 48 kHz there is no reason to hold or drop that sample.
    if (input.sampleRate == targetSampleRate) {
        if (sourceFrames > maxOutputFrames_) {
            fail();
            return false;
        }
        output.samples = std::move(mono);
        submittedFrames_ += sourceFrames;
        deliveredFrames_ += sourceFrames;
        previousSample_ = output.samples.back();
        havePreviousSample_ = true;
        return true;
    }

    while (nextInputPosition < sourceEnd) {
        if (output.samples.size() >= maxOutputFrames_) {
            fail();
            return false;
        }
        const auto floorPosition = std::floor(nextInputPosition);
        const auto index = static_cast<std::int64_t>(floorPosition - sourceStart);
        float left = 0.0F;
        float right = 0.0F;
        if (index == -1) {
            if (!havePreviousSample_) break;
            left = previousSample_;
            right = mono.front();
        } else if (index < -1) {
            fail();
            return false;
        } else {
            const auto sourceIndex = static_cast<std::size_t>(index);
            if (sourceIndex + 1 >= mono.size()) break;
            left = mono[sourceIndex];
            right = mono[sourceIndex + 1];
        }
        const auto fraction = static_cast<float>(nextInputPosition - floorPosition);
        output.samples.push_back(left + (right - left) * fraction);
        ++deliveredFrames_;
        nextInputPosition = static_cast<double>(deliveredFrames_) * step;
    }

    previousSample_ = mono.back();
    havePreviousSample_ = true;
    submittedFrames_ += sourceFrames;
    return true;
}

} // namespace graf::windows
