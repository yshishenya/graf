#include "RecordingAudioTimeline.h"

#include <algorithm>

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
    if (batch.sampleRate != 48'000 || batch.channels == 0 || batch.ptsFrames < 0 ||
        batch.routeGeneration == 0 || batch.clockDomain == 0 || batch.discontinuity) {
        fail(batch.discontinuity ? TimelineFault::routeChanged : TimelineFault::invalidFormat);
        return false;
    }
    const auto frameCount = batch.samples.size() / batch.channels;
    if (frameCount == 0 || frameCount * batch.channels != batch.samples.size()) {
        fail(TimelineFault::invalidFormat);
        return false;
    }

    auto& lastPts = batch.source == AudioSource::systemRender ? lastSystemPts_ : lastMicrophonePts_;
    auto& routeGeneration = batch.source == AudioSource::systemRender
        ? systemRouteGeneration_ : microphoneRouteGeneration_;
    if (routeGeneration == 0) {
        routeGeneration = batch.routeGeneration;
    } else if (routeGeneration != batch.routeGeneration) {
        fail(TimelineFault::routeChanged);
        return false;
    }
    if (clockDomain_ == 0) {
        clockDomain_ = batch.clockDomain;
    } else if (clockDomain_ != batch.clockDomain) {
        fail(TimelineFault::clockDiscontinuity);
        return false;
    }
    if (lastPts >= 0 && batch.ptsFrames + static_cast<std::int64_t>(limits_.reorderWindowFrames) < lastPts) {
        fail(TimelineFault::invalidTimestamp);
        return false;
    }
    lastPts = std::max(lastPts, batch.ptsFrames);

    auto& target = batch.source == AudioSource::systemRender ? systemSamples_ : microphoneSamples_;
    for (std::size_t frame = 0; frame < frameCount; ++frame) {
        float sum = 0.0F;
        for (std::size_t channel = 0; channel < batch.channels; ++channel) {
            sum += batch.samples[frame * batch.channels + channel];
        }
        target.emplace(batch.ptsFrames + static_cast<std::int64_t>(frame), sum / batch.channels);
    }
    if (systemSamples_.size() > limits_.maxBufferedFrames ||
        microphoneSamples_.size() > limits_.maxBufferedFrames) {
        fail(TimelineFault::queueOverflow);
        return false;
    }
    if (nextFramePts_ < 0 && !systemSamples_.empty() && !microphoneSamples_.empty()) {
        nextFramePts_ = std::max(systemSamples_.begin()->first, microphoneSamples_.begin()->first);
    }
    return true;
}

void RecordingAudioTimeline::drain() {
    if (!healthy() || nextFramePts_ < 0) {
        return;
    }
    while (healthy()) {
        const auto frameEnd = nextFramePts_ + 480;
        const auto systemFirst = systemSamples_.lower_bound(nextFramePts_);
        const auto microphoneFirst = microphoneSamples_.lower_bound(nextFramePts_);
        if (systemFirst == systemSamples_.end() || microphoneFirst == microphoneSamples_.end()) {
            return;
        }
        if (systemFirst->first > nextFramePts_ || microphoneFirst->first > nextFramePts_) {
            const auto earliest = std::min(systemFirst->first, microphoneFirst->first);
            if (earliest - nextFramePts_ > static_cast<std::int64_t>(limits_.knownGapFrames)) {
                fail(TimelineFault::clockDiscontinuity);
            }
            return;
        }
        if (systemSamples_.find(frameEnd - 1) == systemSamples_.end() ||
            microphoneSamples_.find(frameEnd - 1) == microphoneSamples_.end()) {
            return;
        }

        CanonicalAudioFrame frame;
        frame.ptsFrames = nextFramePts_;
        for (std::size_t offset = 0; offset < frame.system.size(); ++offset) {
            const auto pts = nextFramePts_ + static_cast<std::int64_t>(offset);
            const auto system = systemSamples_.find(pts);
            const auto microphone = microphoneSamples_.find(pts);
            if (system == systemSamples_.end() || microphone == microphoneSamples_.end()) {
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
            systemSamples_.erase(nextFramePts_ + static_cast<std::int64_t>(offset));
            microphoneSamples_.erase(nextFramePts_ + static_cast<std::int64_t>(offset));
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
