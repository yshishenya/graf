#include "Audio/AudioNormalizer.h"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <utility>

using namespace graf::windows;

int main() {
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
    assert(normalizer.normalize(std::move(input), output));
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
    assert(nativeRate.normalize(std::move(first), firstOutput));
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
    assert(nativeRate.normalize(std::move(second), secondOutput));
    assert(secondOutput.ptsFrames == 480 && secondOutput.samples.size() == 480);
    return 0;
}
