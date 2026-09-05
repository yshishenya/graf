#include "AudioNormalizer.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace graf::windows {

AudioNormalizer::AudioNormalizer(std::size_t maxOutputFrames)
    : maxOutputFrames_(maxOutputFrames == 0 ? 1 : maxOutputFrames) {}

bool AudioNormalizer::normalize(AudioBatch input, AudioBatch& output) {
    output = {};
    if (!healthy_ || input.sampleRate < 8'000 || input.sampleRate > 192'000 || input.channels == 0 ||
        input.channels > 32 || input.ptsFrames < 0 || input.routeGeneration == 0 || input.clockDomain == 0 ||
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

    if (!initialized_ || input.discontinuity) {
        initialized_ = true;
        inputSampleRate_ = input.sampleRate;
        nextInputPosition_ = static_cast<double>(input.ptsFrames);
        havePreviousSample_ = false;
    } else if (input.sampleRate != inputSampleRate_ ||
               static_cast<double>(input.ptsFrames) > nextInputPosition_ + 1.0 ||
               static_cast<double>(input.ptsFrames) + 1.0 < nextInputPosition_) {
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

    const auto sourceStart = static_cast<double>(input.ptsFrames);
    const auto sourceEnd = sourceStart + static_cast<double>(sourceFrames);
    const auto step = static_cast<double>(input.sampleRate) / targetSampleRate;
    output.source = input.source;
    output.sampleRate = targetSampleRate;
    output.channels = 1;
    output.clockDomain = input.clockDomain;
    output.routeGeneration = input.routeGeneration;
    output.discontinuity = input.discontinuity;
    output.ptsFrames = static_cast<std::int64_t>(std::llround(
        nextInputPosition_ * static_cast<double>(targetSampleRate) / input.sampleRate));
    output.samples.reserve(std::min(
        maxOutputFrames_, static_cast<std::size_t>(std::ceil(sourceFrames / step)) + 1));

    // Keep the native-rate path lossless. The interpolating path intentionally
    // holds the final source sample until the next batch supplies its right
    // neighbour; at 48 kHz there is no reason to hold or drop that sample.
    if (input.sampleRate == targetSampleRate) {
        output.ptsFrames = input.ptsFrames;
        output.samples = std::move(mono);
        nextInputPosition_ = sourceEnd;
        previousSample_ = output.samples.back();
        havePreviousSample_ = true;
        return true;
    }

    while (nextInputPosition_ < sourceEnd) {
        if (output.samples.size() >= maxOutputFrames_) {
            fail();
            return false;
        }
        const auto floorPosition = std::floor(nextInputPosition_);
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
        const auto fraction = static_cast<float>(nextInputPosition_ - floorPosition);
        output.samples.push_back(left + (right - left) * fraction);
        nextInputPosition_ += step;
    }

    previousSample_ = mono.back();
    havePreviousSample_ = true;
    return true;
}

} // namespace graf::windows
