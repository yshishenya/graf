#include "../../RecApp/Audio/RecordingAudioTimeline.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <cmath>
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

using namespace graf::windows;

AudioBatch batch(AudioSource source, std::int64_t pts, std::size_t count, float value) {
    return {source, 48'000, 1, pts, 1, 1, false, std::vector<float>(count, value),
        static_cast<std::uint64_t>(pts)};
}

void boundedCorrections() {
    constexpr std::int64_t origin = 48'000'000'123;
    for (const auto source : {AudioSource::systemRender, AudioSource::microphone}) {
        for (int delta = -48; delta <= 48; ++delta) {
            FakeAec aec;
            RecordingAudioTimeline timeline(aec);
            assert(timeline.push(batch(AudioSource::systemRender, origin, 480, 0.25F)));
            assert(timeline.push(batch(AudioSource::microphone, origin, 480, 0.5F)));
            assert(timeline.takeFrames().size() == 1);
            auto corrected = batch(source, origin + 480 + delta, static_cast<std::size_t>(480 - delta), 0.75F);
            corrected.normalizedFrameOffset = origin + 480;
            for (int i = 0; i < -delta; ++i) corrected.samples[i] = -0.75F;
            assert(timeline.push(std::move(corrected)));
            const auto other = source == AudioSource::systemRender
                ? AudioSource::microphone : AudioSource::systemRender;
            assert(timeline.push(batch(other, origin + 480, 480,
                other == AudioSource::systemRender ? 0.25F : 0.5F)));
            const auto frames = timeline.takeFrames();
            assert(frames.size() == 1); // Even a one-frame gap must not stall output.
            assert(frames[0].ptsFrames == origin + 480);
            for (int i = 0; i < 480; ++i) {
                const auto previous = source == AudioSource::systemRender ? 0.25F : 0.5F;
                const auto value = i < delta
                    ? previous + (0.75F - previous) * static_cast<float>(i + 1) /
                        static_cast<float>(delta + 1) : 0.75F;
                const auto system = source == AudioSource::systemRender ? value : 0.25F;
                const auto microphone = (source == AudioSource::microphone ? value : 0.5F) * 0.5F;
                assert(std::abs(frames[0].system[i] - system) < 0.000001F);
                assert(std::abs(frames[0].microphone[i] - microphone) < 0.000001F);
                assert(std::abs(frames[0].mixed[i] - std::min(1.0F, system + microphone)) < 0.000001F);
            }
            assert(timeline.nextFramePts() == origin + 960);
            assert(timeline.processedFrames() == 2 && aec.calls == 2);
        }
    }
}

void variableBatchesAndCommonStart() {
    constexpr std::int64_t origin = 9'000'000'000;
    for (const auto early : {AudioSource::systemRender, AudioSource::microphone}) {
        const auto late = early == AudioSource::systemRender
            ? AudioSource::microphone : AudioSource::systemRender;
        FakeAec aec;
        TimelineLimits limits;
        limits.maxBufferedFrames = 960;
        RecordingAudioTimeline timeline(aec, limits);
        assert(timeline.push(batch(early, origin, 960, 0.25F)));
        assert(timeline.push(batch(late, origin + 700, 480, 0.5F)));
        assert(timeline.takeFrames().empty());
        assert(timeline.nextFramePts() == origin + 700);
        // The discarded 700-frame prefix must no longer consume queue capacity.
        assert(timeline.push(batch(early, origin + 960, 220, 0.75F)));
        auto frames = timeline.takeFrames();
        assert(frames.size() == 1 && frames[0].ptsFrames == origin + 700);
        for (std::size_t i = 0; i < 480; ++i) {
            const auto value = i < 260 ? 0.25F : 0.75F;
            assert(frames[0].system[i] == (early == AudioSource::systemRender ? value : 0.5F));
            assert(frames[0].microphone[i] == (early == AudioSource::microphone ? value : 0.5F) * 0.5F);
        }
        // Arbitrarily partitioned input still emits exact contiguous pairs.
        std::int64_t pts = origin + 1180;
        for (const auto count : {1, 17, 461, 1, 7, 473}) {
            assert(timeline.push(batch(early, pts, count, 0.25F)));
            pts += count;
        }
        assert(timeline.push(batch(late, origin + 1180, 960, 0.5F)));
        frames = timeline.takeFrames();
        assert(frames.size() == 2);
        assert(frames[0].ptsFrames == origin + 1180 && frames[1].ptsFrames == origin + 1660);
        assert(timeline.nextFramePts() == origin + 2140 && aec.calls == 3);
    }

    FakeAec aec;
    TimelineLimits limits;
    limits.maxBufferedFrames = 480;
    RecordingAudioTimeline delayed(aec, limits);
    assert(delayed.push(batch(AudioSource::systemRender, origin, 16, -0.5F)));
    assert(delayed.push(batch(AudioSource::microphone, origin + 100, 480, 0.5F)));
    assert(delayed.push(batch(AudioSource::systemRender, origin + 16, 17, -0.5F)));
    assert(delayed.push(batch(AudioSource::systemRender, origin + 33, 67, -0.5F)));
    // Last sample must survive prefix purging so this one-frame gap is interpolated.
    auto afterGap = batch(AudioSource::systemRender, origin + 101, 479, 0.5F);
    afterGap.normalizedFrameOffset = origin + 100;
    assert(delayed.push(std::move(afterGap)));
    const auto frames = delayed.takeFrames();
    assert(frames.size() == 1 && frames[0].ptsFrames == origin + 100);
    assert(frames[0].system[0] == 0.0F && frames[0].system[1] == 0.5F);

    RecordingAudioTimeline lateArrivesFirst(aec, limits);
    assert(lateArrivesFirst.push(batch(AudioSource::microphone, origin + 700, 480, 0.5F)));
    assert(lateArrivesFirst.push(batch(AudioSource::systemRender, origin, 960, 0.25F)));
    assert(lateArrivesFirst.push(batch(AudioSource::systemRender, origin + 960, 220, 0.75F)));
    const auto lateFrames = lateArrivesFirst.takeFrames();
    assert(lateFrames.size() == 1 && lateFrames[0].ptsFrames == origin + 700);
    assert(lateFrames[0].system[259] == 0.25F && lateFrames[0].system[260] == 0.75F);

    RecordingAudioTimeline shortBatches(aec);
    assert(shortBatches.push(batch(AudioSource::systemRender, origin, 17, 0.25F)));
    auto shortOverlap = batch(AudioSource::systemRender, origin + 16, 2, 0.5F);
    shortOverlap.normalizedFrameOffset = origin + 17;
    assert(shortBatches.push(std::move(shortOverlap)));
    auto nextOverlap = batch(AudioSource::systemRender, origin + 17, 463, 0.75F);
    nextOverlap.normalizedFrameOffset = origin + 19;
    assert(shortBatches.push(std::move(nextOverlap)));
    assert(shortBatches.push(batch(AudioSource::microphone, origin, 480, 0.5F)));
    const auto shortFrames = shortBatches.takeFrames();
    assert(shortFrames.size() == 1);
    assert(shortFrames[0].system[16] == 0.25F && shortFrames[0].system[17] == 0.5F);
    assert(shortFrames[0].system[18] == 0.75F);
}

void rejectsUntrustedBatches() {
    for (const auto source : {AudioSource::systemRender, AudioSource::microphone}) {
        for (const bool published : {false, true}) {
            // Duplicate/reversed starts, full overlap, and both sides of the 49-frame boundary.
            for (const auto start : {1000, 999, 1432, 1431, 1529}) {
                FakeAec aec;
                RecordingAudioTimeline timeline(aec);
                assert(timeline.push(batch(source, 1000, 480, 0.25F)));
                if (published) {
                    const auto other = source == AudioSource::systemRender
                        ? AudioSource::microphone : AudioSource::systemRender;
                    assert(timeline.push(batch(other, 1000, 480, 0.5F)));
                    assert(timeline.takeFrames().size() == 1);
                }
                auto bad = batch(source, start, start == 1432 ? 48 : 480, 0.75F);
                // New contiguous input still cannot exceed the correction bound.
                if (start == 1431 || start == 1529) bad.normalizedFrameOffset = 1480;
                assert(!timeline.push(std::move(bad)));
                const auto fault = timeline.fault();
                assert(fault == (start == 1529 ? TimelineFault::clockDiscontinuity : TimelineFault::invalidTimestamp));
                for (int repeat = 0; repeat < 32; ++repeat) {
                    assert(!timeline.push(batch(source, 1000, 480, 0.75F)));
                }
                assert(!timeline.push(batch(source, 1480, 480, 0.75F)));
                assert(timeline.fault() == fault && timeline.takeFrames().empty());
                assert(aec.calls == (published ? 1U : 0U));
            }
        }
        for (int mutation = 0; mutation < 8; ++mutation) {
            FakeAec aec;
            RecordingAudioTimeline timeline(aec);
            assert(timeline.push(batch(source, 0, 480, 0.25F)));
            auto invalid = batch(source, 480, 480, 0.5F);
            switch (mutation) {
            case 0: invalid.routeGeneration = 2; break;
            case 1: invalid.clockDomain = 2; break;
            case 2: invalid.discontinuity = true; break;
            case 3: invalid.samples[0] = std::numeric_limits<float>::infinity(); break;
            case 4: invalid.samples[0] = std::numeric_limits<float>::quiet_NaN(); break;
            case 5: invalid.ptsFrames = -1; break;
            case 6: invalid.sampleRate = 44'100; break;
            case 7: invalid.channels = 2; break;
            }
            assert(!timeline.push(std::move(invalid)));
            assert(!timeline.healthy() && aec.calls == 0);
        }
        FakeAec aec;
        RecordingAudioTimeline startup(aec);
        auto discontinuous = batch(source, 0, 480, 0.5F);
        discontinuous.discontinuity = true;
        assert(!startup.push(std::move(discontinuous)) && !startup.healthy());
    }
}

void consumesSmallClockOverlapOnce() {
    for (const auto source : {AudioSource::systemRender, AudioSource::microphone}) {
        for (const auto count : {1U, 48U}) {
            FakeAec aec;
            RecordingAudioTimeline timeline(aec);
            const auto other = source == AudioSource::systemRender ? AudioSource::microphone : AudioSource::systemRender;
            assert(timeline.push(batch(source, 0, 480, 0.25F)));
            assert(timeline.push(batch(other, 0, 480, 0.5F)));
            assert(timeline.takeFrames().size() == 1);
            auto overlapped = batch(source, 480 - count, count, -0.75F);
            overlapped.normalizedFrameOffset = 480;
            assert(timeline.push(overlapped));
            assert(timeline.takeFrames().empty() && aec.calls == 1);
            assert(timeline.trimmedFrames(source) == count && timeline.nextFramePts() == 480);
            auto next = batch(source, 481, 479, 0.75F);
            next.normalizedFrameOffset = 480 + count;
            assert(timeline.push(std::move(next)));
            assert(timeline.push(batch(other, 480, 480, 0.5F)));
            const auto frames = timeline.takeFrames();
            assert(frames.size() == 1 && frames[0].ptsFrames == 480);
            const auto recovered = source == AudioSource::systemRender ? frames[0].system[0] : frames[0].microphone[0] * 2;
            assert(recovered == 0.5F); // Last retained sample, not the discarded -0.75.
            assert(!timeline.push(std::move(overlapped)));
            assert(timeline.fault() == TimelineFault::invalidTimestamp);
        }
    }
    FakeAec aec;
    RecordingAudioTimeline overflow(aec);
    auto invalid = batch(AudioSource::systemRender, 0, 2, 0.25F);
    invalid.normalizedFrameOffset = std::numeric_limits<std::uint64_t>::max() - 1;
    assert(!overflow.push(std::move(invalid)));
    assert(overflow.fault() == TimelineFault::invalidTimestamp);
}

void boundsAndOverflow() {
    for (const auto source : {AudioSource::systemRender, AudioSource::microphone}) {
        for (const auto gap : {0, 1, 48}) {
            for (const auto capacity : {959U, 960U}) {
                FakeAec aec;
                TimelineLimits limits;
                limits.maxBufferedFrames = capacity;
                RecordingAudioTimeline timeline(aec, limits);
                assert(timeline.push(batch(source, 0, 480, 0.25F)));
                auto next = batch(source, 480 + gap, 480 - gap, 0.5F);
                next.normalizedFrameOffset = 480;
                const auto accepted = timeline.push(std::move(next));
                assert(accepted == (capacity == 960));
                assert(timeline.fault() == (accepted ? TimelineFault::none : TimelineFault::queueOverflow));
            }
        }
        FakeAec aec;
        RecordingAudioTimeline overflow(aec);
        assert(!overflow.push(batch(source, std::numeric_limits<std::int64_t>::max() - 479, 480, 0.25F)));
        assert(overflow.fault() == TimelineFault::invalidTimestamp);
    }

    FakeAec aec;
    RecordingAudioTimeline lastFrame(aec);
    const auto maxPts = std::numeric_limits<std::int64_t>::max();
    assert(lastFrame.push(batch(AudioSource::systemRender, maxPts - 480, 480, 0.25F)));
    assert(lastFrame.push(batch(AudioSource::microphone, maxPts - 480, 480, 0.5F)));
    const auto frames = lastFrame.takeFrames();
    assert(frames.size() == 1 && frames[0].ptsFrames == maxPts - 480);
    assert(lastFrame.nextFramePts() == maxPts && lastFrame.healthy());

    RecordingAudioTimeline incompleteTail(aec);
    assert(incompleteTail.push(batch(AudioSource::systemRender, maxPts - 479, 479, 0.25F)));
    assert(incompleteTail.push(batch(AudioSource::microphone, maxPts - 479, 479, 0.5F)));
    assert(incompleteTail.healthy() && incompleteTail.takeFrames().empty());
    for (const auto pts : {std::numeric_limits<std::int64_t>::min(), maxPts - 480}) {
        RecordingAudioTimeline farTimestamp(aec);
        assert(farTimestamp.push(batch(AudioSource::systemRender, 0, 480, 0.25F)));
        assert(!farTimestamp.push(batch(AudioSource::systemRender, pts, 480, 0.25F)));
        assert(!farTimestamp.healthy());
    }

    TimelineLimits limits;
    limits.clockRecoveryFrames = std::numeric_limits<std::size_t>::max();
    RecordingAudioTimeline excessiveRecovery(aec, limits);
    assert(excessiveRecovery.push(batch(AudioSource::systemRender, 0, 480, 0.25F)));
    auto beyond = batch(AudioSource::systemRender, 529, 480, 0.25F);
    beyond.normalizedFrameOffset = 480;
    assert(!excessiveRecovery.push(std::move(beyond)));

    limits = {};
    limits.maxBufferedFrames = 480;
    RecordingAudioTimeline outputBound(aec, limits);
    assert(outputBound.push(batch(AudioSource::systemRender, 0, 480, 0.25F)));
    assert(outputBound.push(batch(AudioSource::microphone, 0, 480, 0.5F)));
    assert(outputBound.push(batch(AudioSource::systemRender, 480, 480, 0.25F)));
    assert(!outputBound.push(batch(AudioSource::microphone, 480, 480, 0.5F)));
    assert(outputBound.fault() == TimelineFault::queueOverflow);
    assert(outputBound.takeFrames().size() == 1); // Only the already-cleaned prefix remains.

    // Finite input must remain finite during downmix and interpolation, even at float limits.
    RecordingAudioTimeline finiteExtremes(aec);
    auto stereo = batch(AudioSource::systemRender, 0, 960, std::numeric_limits<float>::max());
    stereo.channels = 2;
    assert(finiteExtremes.push(std::move(stereo)));
    assert(finiteExtremes.push(batch(AudioSource::microphone, 0, 480, 0.0F)));
    assert(finiteExtremes.takeFrames()[0].system[0] == std::numeric_limits<float>::max());
    stereo = batch(AudioSource::systemRender, 481, 958, -std::numeric_limits<float>::max());
    stereo.channels = 2;
    stereo.normalizedFrameOffset = 480;
    assert(finiteExtremes.push(std::move(stereo)));
    assert(finiteExtremes.push(batch(AudioSource::microphone, 480, 480, 0.0F)));
    const auto extremeFrames = finiteExtremes.takeFrames();
    assert(extremeFrames.size() == 1 && extremeFrames[0].system[0] == 0.0F);
    assert(extremeFrames[0].system[1] == -std::numeric_limits<float>::max());
}
}

int main() {
    using namespace graf::windows;
    boundedCorrections();
    variableBatchesAndCommonStart();
    rejectsUntrustedBatches();
    consumesSmallClockOverlapOnce();
    boundsAndOverflow();
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
