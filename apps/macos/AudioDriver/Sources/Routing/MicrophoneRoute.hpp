#pragma once

#include <cstddef>

namespace TwoBrainRec::AudioDriver {

struct InterleavedAudioBuffer {
    const float* data;
    std::size_t frame_count;
    std::size_t channel_count;
};

struct MutableInterleavedAudioBuffer {
    float* data;
    std::size_t frame_count;
    std::size_t channel_count;
};

bool RouteMicrophoneFrames(
    InterleavedAudioBuffer physical_microphone,
    InterleavedAudioBuffer remote_speaker,
    MutableInterleavedAudioBuffer virtual_microphone
);

bool MicrophoneRouteShouldRemainActive(unsigned int client_io_count);

double RemoteLeakageScore(
    InterleavedAudioBuffer virtual_microphone,
    InterleavedAudioBuffer remote_speaker
);

}  // namespace TwoBrainRec::AudioDriver
