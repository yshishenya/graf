#include "../../RecApp/Audio/RecordingAudioTimeline.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>

namespace {
class FakeAec final : public graf::windows::IAec3Processor {
public:
    bool process(const float* render, const float* microphone, float* cleaned) noexcept override {
        referenceSeen = render[0] == 0.25F;
        for (std::size_t index = 0; index < 480; ++index) cleaned[index] = microphone[index] * 0.5F;
        ++calls;
        return true;
    }
    bool referenceSeen = false;
    std::size_t calls = 0;
};
}

int main() {
    using namespace graf::windows;
    FakeAec aec;
    RecordingAudioTimeline timeline(aec);
    AudioBatch system{AudioSource::systemRender, 48'000, 1, 0, 1, 1, false, std::vector<float>(480, 0.25F)};
    AudioBatch microphone{AudioSource::microphone, 48'000, 1, 0, 1, 1, false, std::vector<float>(480, 0.5F)};
    assert(timeline.push(std::move(system)));
    assert(timeline.push(std::move(microphone)));
    const auto frames = timeline.takeFrames();
    assert(frames.size() == 1 && frames[0].mixed[0] == 0.5F);
    assert(aec.referenceSeen && aec.calls == 1);
    RecordingAudioTimeline pausedTimeline(aec);
    pausedTimeline.setMicrophonePaused(true);
    AudioBatch pausedSystem{AudioSource::systemRender, 48'000, 1, 0, 1, 1, false, std::vector<float>(480, 0.25F)};
    AudioBatch pausedMicrophone{AudioSource::microphone, 48'000, 1, 0, 1, 1, false, std::vector<float>(480, 0.5F)};
    assert(pausedTimeline.push(std::move(pausedSystem)));
    assert(pausedTimeline.push(std::move(pausedMicrophone)));
    const auto pausedFrames = pausedTimeline.takeFrames();
    assert(pausedFrames.size() == 1 && pausedFrames[0].microphone[0] == 0.0F && pausedFrames[0].mixed[0] == 0.25F);
    AudioBatch invalid{AudioSource::microphone, 48'000, 1, 480, 1, 2, false, std::vector<float>(480, 0.0F)};
    assert(!timeline.push(std::move(invalid)));
    assert(timeline.fault() == TimelineFault::routeChanged);
    RecordingAudioTimeline invalidSamples(aec);
    AudioBatch nanBatch{AudioSource::systemRender, 48'000, 1, 0, 1, 1, false, std::vector<float>(480, 0.0F)};
    nanBatch.samples[0] = std::numeric_limits<float>::quiet_NaN();
    assert(!invalidSamples.push(std::move(nanBatch)));
    assert(invalidSamples.fault() == TimelineFault::invalidFormat);
    return 0;
}
