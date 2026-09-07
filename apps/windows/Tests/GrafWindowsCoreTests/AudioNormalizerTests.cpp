#include "Audio/AudioNormalizer.h"
#include "Audio/ClockMapper.h"
#include "Audio/RecordingAudioTimeline.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <utility>

using namespace graf::windows;

namespace {
AudioBatch batch(std::int64_t pts, std::size_t count, std::uint32_t rate = 48'000) {
    return {AudioSource::systemRender, rate, 1, pts, 1, 1, false, std::vector<float>(count, 0.25F)};
}

void sourceClockRegressions() {
    ClockMapper system, microphone;
    constexpr std::uint64_t epoch = 1'000'000'000;
    // Independent device origins must not become presentation origins.
    assert(system.observe({epoch - 200'000, 0, 48'000, ClockObservation::dataDiscontinuity, 480}).discardStartup);
    assert(microphone.observe({epoch - 100'000, 0, 48'000, ClockObservation::dataDiscontinuity, 480}).discardStartup);
    const auto render = system.observe({epoch, 23'000, 48'000, 0, 480});
    const auto mic = microphone.observe({epoch + 100'000, 700, 48'000, 0, 480});
    assert(render.valid && mic.valid);
    assert(render.qpc100ns == epoch);
    assert(mic.qpc100ns - render.qpc100ns == 100'000);

    // GetBuffer's devicePosition may use endpoint-frame units while the
    // engine packet uses the mix rate. IAudioClock position is the shared
    // stream clock for the packet count; qpc remains only the common origin.
    ClockMapper resampledEndpoint;
    assert(resampledEndpoint.observe({epoch, 0, 48'000, 0, 482, 0, 384'000}).valid);
    const auto endpointPacket = resampledEndpoint.observe(
        {epoch + 90'000, 448, 48'000, 0, 487, 3'896, 384'000});
    assert(endpointPacket.valid && endpointPacket.qpc100ns == epoch + 101'458);
    assert(resampledEndpoint.observe({epoch + 190'000, 896, 48'000, 0, 488,
                                      7'800, 384'000}).valid);
    ClockMapper badAudioClock;
    assert(badAudioClock.observe({epoch, 0, 48'000, 0, 480, 0, 384'000}).valid);
    // GetPosition is a running stream clock rather than a packet boundary;
    // its delta may include scheduling time between observations.
    assert(badAudioClock.observe({epoch + 100'000, 480, 48'000, 0, 480,
                                  4'000, 384'000}).valid);
    const auto repeatedAudioClock = badAudioClock.observe(
        {epoch + 200'000, 960, 48'000, 0, 480, 4'000, 384'000});
    assert(repeatedAudioClock.valid && repeatedAudioClock.qpc100ns > epoch + 100'000);

    ClockMapper rounded;
    assert(rounded.observe({epoch, 0, 48'000, 0, 480}).valid);
    // One frame of timestamp quantization is not a settled 2083 ppm drift.
    assert(rounded.observe({epoch + 100'208, 480, 48'000, 0, 480}).valid);
    assert(rounded.observe({epoch + 200'000, 960, 48'000, 0, 480}).valid);

    // 60 minutes of metadata only: not the SC-003 audio/performance gate.
    for (const int ppm : {-100, 0, 100, 1'000}) {
        ClockMapper drift;
        bool valid = true;
        for (std::uint64_t packet = 0; packet <= 360'000 && valid; ++packet) {
            const auto ticks = static_cast<std::uint64_t>(std::llround(
                static_cast<double>(packet) * 100'000 / (1.0 + ppm * 0.000001)));
            valid = drift.observe({epoch + ticks, packet * 480 + 900, 48'000, 0, 480}).valid;
        }
        assert(valid == (ppm != 1'000));
    }
    ClockMapper inconsistentCount;
    assert(inconsistentCount.observe({epoch, 0, 48'000, 0, 482}).valid);
    assert(!inconsistentCount.observe({epoch + 101'522, 448, 48'000, 0, 487}).valid);
}

std::vector<float> partitioned(const std::vector<std::size_t>& sizes, std::uint64_t epoch = 0) {
    AudioNormalizer normalizer;
    std::vector<float> samples;
    std::int64_t inputPosition = 0;
    for (const auto count : sizes) {
        auto input = batch(inputPosition, count, 44'100);
        for (std::size_t i = 0; i < count; ++i)
            input.samples[i] = std::sin(static_cast<float>(inputPosition + i) * 0.01F);
        AudioBatch output;
        const auto qpc = static_cast<std::uint64_t>(std::llround(inputPosition * 10'000'000.0 / 44'100));
        assert(normalizer.normalize(std::move(input), epoch + qpc, output));
        if (!output.samples.empty()) {
            const auto origin = static_cast<std::int64_t>((epoch * 48'000 + 5'000'000) / 10'000'000);
            assert(output.ptsFrames == origin + static_cast<std::int64_t>(samples.size()));
            samples.insert(samples.end(), output.samples.begin(), output.samples.end());
        }
        inputPosition += static_cast<std::int64_t>(count);
    }
    return samples;
}

class PassthroughAec final : public IAec3Processor {
public:
    bool process(const float*, const float* microphone, float* cleaned) noexcept override {
        for (std::size_t i = 0; i < 480; ++i) cleaned[i] = microphone[i];
        return true;
    }
};

void pipeline(std::uint32_t microphoneRate, int ppm, bool singleSample = false) {
    PassthroughAec aec;
    TimelineLimits limits;
    // Exact clocks must not need timeline repair for resampler partitioning.
    if (ppm == 0) limits.clockRecoveryFrames = 0;
    RecordingAudioTimeline timeline(aec, limits);
    ClockMapper clocks[2];
    AudioNormalizer normalizers[2];
    std::uint64_t positions[2]{};
    std::uint32_t packets[2]{};
    constexpr std::uint64_t epoch = 1'000'000'000;
    std::int64_t previousPts = -1;
    std::size_t outputBlocks = 0;
    const auto rate = [&](int source) { return source == 0 ? 48'000U : microphoneRate; };
    const auto qpc = [&](int source) {
        const auto factor = 1.0 + (source == 0 ? ppm : -ppm) * 0.000001;
        return epoch + (source == 0 ? 0 : 100'000) + static_cast<std::uint64_t>(std::llround(
            static_cast<double>(positions[source]) * 10'000'000 / (rate(source) * factor)));
    };
    while (positions[0] < 3 * rate(0) || positions[1] < 3 * rate(1)) {
        const int source = positions[0] >= 3 * rate(0) ? 1 :
            positions[1] >= 3 * rate(1) ? 0 : qpc(0) <= qpc(1) ? 0 : 1;
        const auto hz = rate(source);
        const std::uint32_t sizes[]{1, 2, hz / 100 - 3, hz / 100, hz / 50};
        const auto count = static_cast<std::uint32_t>(std::min<std::uint64_t>(
            singleSample ? 1 : sizes[packets[source]++ % 5], 3 * hz - positions[source]));
        const auto mapping = clocks[source].observe({qpc(source),
            positions[source] + (source == 0 ? 20'000 : 700), hz, 0, count});
        assert(mapping.valid);
        auto input = batch(0, count, hz);
        input.source = source == 0 ? AudioSource::systemRender : AudioSource::microphone;
        AudioBatch output;
        assert(normalizers[source].normalize(std::move(input), mapping.qpc100ns, output));
        if (!output.samples.empty()) {
            const auto pts = output.ptsFrames;
            const auto countOut = output.samples.size();
            const auto accepted = timeline.push(std::move(output));
            if (!accepted) std::fprintf(stderr, "pipeline rate=%u ppm=%d source=%d input=%llu pts=%lld count=%zu fault=%d\n",
                hz, ppm, source, static_cast<unsigned long long>(positions[source]),
                static_cast<long long>(pts), countOut, static_cast<int>(timeline.fault()));
            assert(accepted);
            for (const auto& frame : timeline.takeFrames()) {
                if (previousPts >= 0) assert(frame.ptsFrames == previousPts + 480);
                else assert(frame.ptsFrames >= 4'800'480 && frame.ptsFrames <= 4'800'482);
                previousPts = frame.ptsFrames;
                assert(std::all_of(frame.system.begin(), frame.system.end(), [](float sample) {
                    return std::abs(sample - 0.25F) < 0.00001F;
                }));
                ++outputBlocks;
            }
        }
        positions[source] += count;
    }
    assert(timeline.healthy() && outputBlocks >= 297 && outputBlocks <= 300);
}
}

int main() {
    sourceClockRegressions();
    for (const auto epoch : {0ULL, 113ULL, 1'000'000'113ULL}) {
        const auto whole = partitioned({882}, epoch);
        for (const auto& sizes : {std::vector<std::size_t>{441, 441},
                                  std::vector<std::size_t>{1, 2, 37, 101, 1, 300, 440}}) {
            const auto split = partitioned(sizes, epoch);
            assert(split.size() == whole.size());
            for (std::size_t i = 0; i < split.size(); ++i)
                assert(std::abs(split[i] - whole[i]) < 0.00001F);
        }
    }
    // PTS jitter belongs to the shared timeline, not resampler phase.
    AudioNormalizer jitter;
    AudioBatch jitterOutput;
    assert(jitter.normalize(batch(0, 480), 0, jitterOutput));
    assert(jitter.normalize(batch(0, 480), 100'417, jitterOutput));
    assert(jitterOutput.ptsFrames == 482 && jitterOutput.samples.size() == 480);
    AudioNormalizer channels;
    assert(channels.normalize(batch(0, 480), 0, jitterOutput));
    auto stereoChange = batch(0, 960);
    stereoChange.channels = 2;
    assert(!channels.normalize(std::move(stereoChange), 100'000, jitterOutput));
    for (const bool started : {false, true}) {
        AudioNormalizer broken;
        if (started) assert(broken.normalize(batch(0, 480), 0, jitterOutput));
        auto flagged = batch(started ? 480 : 0, 480);
        flagged.discontinuity = true;
        assert(!broken.normalize(std::move(flagged), started ? 100'000 : 0, jitterOutput));
        assert(!broken.healthy());
    }

    AudioNormalizer normalizer;
    AudioBatch input;
    input.source = AudioSource::microphone;
    input.sampleRate = 44'100;
    input.channels = 2;
    input.ptsFrames = 0;
    input.clockDomain = 1;
    input.routeGeneration = 1;
    input.samples.resize(441 * 2);
    for (std::size_t frame = 0; frame < 441; ++frame) {
        input.samples[frame * 2] = 0.25F;
        input.samples[frame * 2 + 1] = 0.5F;
    }
    AudioBatch output;
    assert(normalizer.normalize(std::move(input), 0, output));
    assert(normalizer.healthy());
    assert(output.sampleRate == 48'000 && output.channels == 1);
    assert(output.samples.size() == 479);
    assert(std::all_of(output.samples.begin(), output.samples.end(), [](float sample) {
        return std::isfinite(sample) && std::abs(sample - 0.375F) < 0.001F;
    }));

    AudioNormalizer nativeRate;
    AudioBatch first;
    first.source = AudioSource::systemRender;
    first.sampleRate = 48'000;
    first.channels = 1;
    first.ptsFrames = 0;
    first.clockDomain = 1;
    first.routeGeneration = 1;
    first.samples.assign(480, 0.125F);
    AudioBatch firstOutput;
    assert(nativeRate.normalize(std::move(first), 0, firstOutput));
    assert(firstOutput.ptsFrames == 0 && firstOutput.samples.size() == 480);

    AudioBatch second;
    second.source = AudioSource::systemRender;
    second.sampleRate = 48'000;
    second.channels = 1;
    second.ptsFrames = 480;
    second.clockDomain = 1;
    second.routeGeneration = 1;
    second.samples.assign(480, 0.25F);
    AudioBatch secondOutput;
    assert(nativeRate.normalize(std::move(second), 100'000, secondOutput));
    assert(secondOutput.ptsFrames == 480 && secondOutput.samples.size() == 480);
    for (const auto rate : {44'100U, 48'000U})
        for (const int ppm : {-100, 0, 100}) pipeline(rate, ppm);
    pipeline(48'000, 100, true);
    return 0;
}
