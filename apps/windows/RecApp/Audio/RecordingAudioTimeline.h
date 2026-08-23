#pragma once

#include "AudioTypes.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <map>
#include <vector>

namespace graf::windows {

enum class TimelineFault {
    none,
    invalidFormat,
    invalidTimestamp,
    routeChanged,
    clockDiscontinuity,
    queueOverflow,
    aecProcessFailed,
};

struct TimelineLimits {
    std::size_t reorderWindowFrames = 48'000;
    std::size_t knownGapFrames = 48'000 * 15;
    std::size_t maxBufferedFrames = 960'000;
    std::size_t clockRecoveryFrames = 48;
};

struct CanonicalAudioFrame {
    std::int64_t ptsFrames = 0;
    std::array<float, 480> system{};
    std::array<float, 480> microphone{};
    std::array<float, 480> mixed{};
};

class IAec3Processor {
public:
    virtual ~IAec3Processor() = default;
    [[nodiscard]] virtual bool process(
        const float* renderReference,
        const float* microphone,
        float* cleanedMicrophone) noexcept = 0;
};

class RecordingAudioTimeline final {
public:
    explicit RecordingAudioTimeline(IAec3Processor& processor, TimelineLimits limits = {});

    [[nodiscard]] bool push(AudioBatch batch);
    [[nodiscard]] std::vector<CanonicalAudioFrame> takeFrames();
    void setMicrophonePaused(bool paused) noexcept { microphonePaused_ = paused; }

    [[nodiscard]] bool healthy() const noexcept { return fault_ == TimelineFault::none; }
    [[nodiscard]] TimelineFault fault() const noexcept { return fault_; }
    [[nodiscard]] std::uint64_t droppedFrames() const noexcept { return droppedFrames_; }
    [[nodiscard]] std::uint64_t processedFrames() const noexcept { return processedFrames_; }
    [[nodiscard]] std::int64_t nextFramePts() const noexcept { return nextFramePts_; }

private:
    using SampleStore = std::map<std::int64_t, float>;

    [[nodiscard]] bool normalizeAndStore(AudioBatch&& batch);
    void drain();
    void fail(TimelineFault fault) noexcept;
    [[nodiscard]] static float clamp(float sample) noexcept;

    IAec3Processor& processor_;
    TimelineLimits limits_;
    SampleStore systemSamples_;
    SampleStore microphoneSamples_;
    std::vector<CanonicalAudioFrame> frames_;
    std::int64_t lastSystemPts_ = -1;
    std::int64_t lastMicrophonePts_ = -1;
    std::int64_t nextFramePts_ = -1;
    std::uint64_t systemRouteGeneration_ = 0;
    std::uint64_t microphoneRouteGeneration_ = 0;
    std::uint64_t clockDomain_ = 0;
    std::uint64_t droppedFrames_ = 0;
    std::uint64_t processedFrames_ = 0;
    bool microphonePaused_ = false;
    TimelineFault fault_ = TimelineFault::none;
};

} // namespace graf::windows
