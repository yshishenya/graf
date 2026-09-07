#include "RecordingAudioTimeline.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace graf::windows {

RecordingAudioTimeline::RecordingAudioTimeline(IAec3Processor& processor, TimelineLimits limits)
    : processor_(processor), limits_(limits) {}

bool RecordingAudioTimeline::push(AudioBatch batch) {
    if (!healthy() || batch.samples.empty()) {
        return false;
    }
    if (!normalizeAndStore(std::move(batch))) {
        return false;
    }
    drain();
    return healthy();
}

std::vector<CanonicalAudioFrame> RecordingAudioTimeline::takeFrames() {
    std::vector<CanonicalAudioFrame> result;
    result.swap(frames_);
    return result;
}

bool RecordingAudioTimeline::normalizeAndStore(AudioBatch&& batch) {
    if (batch.sampleRate != 48'000 || batch.channels == 0 ||
        batch.routeGeneration == 0 || batch.clockDomain == 0 || batch.discontinuity) {
        fail(batch.discontinuity ? TimelineFault::routeChanged : TimelineFault::invalidFormat);
        return false;
    }
    const auto frameCount = batch.samples.size() / batch.channels;
    if (batch.source != AudioSource::systemRender && batch.source != AudioSource::microphone) {
        fail(TimelineFault::invalidFormat);
        return false;
    }
    if (frameCount == 0 ||
        frameCount * batch.channels != batch.samples.size()) {
        fail(TimelineFault::invalidFormat);
        return false;
    }
    if (batch.ptsFrames < 0 || frameCount > static_cast<std::uint64_t>(
        std::numeric_limits<std::int64_t>::max() - batch.ptsFrames)) {
        fail(TimelineFault::invalidTimestamp);
        return false;
    }
    for (const auto sample : batch.samples) {
        if (!std::isfinite(sample)) {
            fail(TimelineFault::invalidFormat);
            return false;
        }
    }

    auto& state = batch.source == AudioSource::systemRender ? system_ : microphone_;
    auto& other = batch.source == AudioSource::systemRender ? microphone_ : system_;
    if (state.routeGeneration != 0 && state.routeGeneration != batch.routeGeneration) {
        fail(TimelineFault::routeChanged);
        return false;
    }
    if (state.channels != 0 && state.channels != batch.channels) {
        fail(TimelineFault::invalidFormat);
        return false;
    }
    if (clockDomain_ == 0) {
        clockDomain_ = batch.clockDomain;
    } else if (clockDomain_ != batch.clockDomain) {
        fail(TimelineFault::clockDiscontinuity);
        return false;
    }
    if (frameCount > std::numeric_limits<std::uint64_t>::max() - batch.normalizedFrameOffset ||
        (state.routeGeneration != 0 && batch.normalizedFrameOffset != state.nextNormalizedOffset)) {
        fail(TimelineFault::invalidTimestamp);
        return false;
    }

    const auto inputEnd = batch.ptsFrames + static_cast<std::int64_t>(frameCount);
    auto start = batch.ptsFrames;
    if (state.endPts >= 0) {
        // Both timestamps are nonnegative, so their difference cannot overflow.
        const auto delta = batch.ptsFrames - state.endPts;
        const auto recovery = std::min<std::size_t>(48, limits_.clockRecoveryFrames);
        if (static_cast<std::uint64_t>(delta < 0 ? -delta : delta) > recovery) {
            fail(delta < 0 ? TimelineFault::invalidTimestamp : TimelineFault::clockDiscontinuity);
            return false;
        }
        start = state.endPts;
    }

    if (commonStartPts_ < 0 && other.routeGeneration != 0) {
        // Preserve absolute QPC offsets; never move either first batch to zero.
        commonStartPts_ = std::max(batch.ptsFrames, other.samples.begin()->first);
        nextFramePts_ = commonStartPts_;
        other.samples.erase(other.samples.begin(), other.samples.lower_bound(commonStartPts_));
    }
    // Early-source packets may still precede the common interval during startup.
    start = std::max(start, commonStartPts_);
    if (start < nextFramePts_) {
        fail(TimelineFault::invalidTimestamp);
        return false;
    }
    const auto retained = inputEnd > start ? static_cast<std::uint64_t>(inputEnd - start) : 0;
    if (state.samples.size() > limits_.maxBufferedFrames ||
        retained > limits_.maxBufferedFrames - state.samples.size()) {
        fail(TimelineFault::queueOverflow);
        return false;
    }

    const auto monoSample = [&batch](std::size_t frame) {
        double sum = 0.0;
        for (std::size_t channel = 0; channel < batch.channels; ++channel) {
            sum += batch.samples[frame * batch.channels + channel];
        }
        return static_cast<float>(sum / batch.channels);
    };
    const auto firstSample = monoSample(0);
    for (auto pts = start; pts < inputEnd; ++pts) {
        float value;
        if (pts < batch.ptsFrames) {
            const auto fraction = static_cast<double>(pts - state.endPts + 1) /
                static_cast<double>(batch.ptsFrames - state.endPts + 1);
            value = static_cast<float>(state.lastSample +
                (static_cast<double>(firstSample) - state.lastSample) * fraction);
        } else {
            value = monoSample(static_cast<std::size_t>(pts - batch.ptsFrames));
        }
        state.samples.emplace(pts, value);
    }
    state.nextNormalizedOffset = batch.normalizedFrameOffset + frameCount;
    if (state.endPts > batch.ptsFrames) state.trimmedFrames += std::min<std::uint64_t>(
        static_cast<std::uint64_t>(state.endPts - batch.ptsFrames), frameCount);
    if (inputEnd > state.endPts) {
        state.endPts = inputEnd;
        state.lastSample = monoSample(frameCount - 1);
    }
    state.routeGeneration = batch.routeGeneration;
    state.channels = batch.channels;
    return true;
}

void RecordingAudioTimeline::drain() {
    if (!healthy() || nextFramePts_ < 0) {
        return;
    }
    auto& systemSamples = system_.samples;
    auto& microphoneSamples = microphone_.samples;
    while (healthy()) {
        if (nextFramePts_ > std::numeric_limits<std::int64_t>::max() - 480) {
            return; // No complete representable frame remains.
        }
        const auto frameEnd = nextFramePts_ + 480;
        if (systemSamples.find(nextFramePts_) == systemSamples.end() ||
            microphoneSamples.find(nextFramePts_) == microphoneSamples.end()) {
            return;
        }
        if (systemSamples.find(frameEnd - 1) == systemSamples.end() ||
            microphoneSamples.find(frameEnd - 1) == microphoneSamples.end()) {
            return;
        }
        if (frames_.size() >= limits_.maxBufferedFrames / 480) {
            fail(TimelineFault::queueOverflow);
            return;
        }

        CanonicalAudioFrame frame;
        frame.ptsFrames = nextFramePts_;
        for (std::size_t offset = 0; offset < frame.system.size(); ++offset) {
            const auto pts = nextFramePts_ + static_cast<std::int64_t>(offset);
            const auto system = systemSamples.find(pts);
            const auto microphone = microphoneSamples.find(pts);
            if (system == systemSamples.end() || microphone == microphoneSamples.end()) {
                return;
            }
            frame.system[offset] = system->second;
            frame.microphone[offset] = microphonePaused_ ? 0.0F : microphone->second;
        }
        if (!processor_.process(frame.system.data(), frame.microphone.data(), frame.microphone.data())) {
            fail(TimelineFault::aecProcessFailed);
            return;
        }
        for (std::size_t offset = 0; offset < frame.mixed.size(); ++offset) {
            frame.mixed[offset] = clamp(frame.system[offset] + frame.microphone[offset]);
        }
        frames_.push_back(frame);
        ++processedFrames_;
        for (std::size_t offset = 0; offset < frame.system.size(); ++offset) {
            systemSamples.erase(nextFramePts_ + static_cast<std::int64_t>(offset));
            microphoneSamples.erase(nextFramePts_ + static_cast<std::int64_t>(offset));
        }
        nextFramePts_ += 480;
    }
}

void RecordingAudioTimeline::fail(TimelineFault fault) noexcept {
    if (fault_ == TimelineFault::none) {
        fault_ = fault;
    }
}

float RecordingAudioTimeline::clamp(float sample) noexcept {
    return std::max(-1.0F, std::min(1.0F, sample));
}

} // namespace graf::windows
