#include "MicrophoneRoute.hpp"

#include <algorithm>
#include <cmath>

namespace TwoBrainRec::AudioDriver {
namespace {

bool Compatible(InterleavedAudioBuffer source, MutableInterleavedAudioBuffer destination) {
    return source.data != nullptr &&
           destination.data != nullptr &&
           source.frame_count == destination.frame_count &&
           source.channel_count == destination.channel_count &&
           source.channel_count > 0;
}

float MonoSample(InterleavedAudioBuffer buffer, std::size_t frame) {
    double sum = 0.0;
    for (std::size_t channel = 0; channel < buffer.channel_count; ++channel) {
        sum += buffer.data[frame * buffer.channel_count + channel];
    }
    return static_cast<float>(sum / static_cast<double>(buffer.channel_count));
}

}  // namespace

bool RouteMicrophoneFrames(
    InterleavedAudioBuffer physical_microphone,
    InterleavedAudioBuffer remote_speaker,
    MutableInterleavedAudioBuffer virtual_microphone
) {
    if (!Compatible(physical_microphone, virtual_microphone)) {
        return false;
    }

    const auto sample_count = physical_microphone.frame_count * physical_microphone.channel_count;
    std::copy(
        physical_microphone.data,
        physical_microphone.data + sample_count,
        virtual_microphone.data
    );

    // Remote speaker frames are intentionally ignored here. This keeps the
    // virtual microphone path isolated from participant audio.
    (void)remote_speaker;
    return true;
}

bool MicrophoneRouteShouldRemainActive(unsigned int client_io_count) {
    return client_io_count > 0;
}

double RemoteLeakageScore(
    InterleavedAudioBuffer virtual_microphone,
    InterleavedAudioBuffer remote_speaker
) {
    if (virtual_microphone.data == nullptr ||
        remote_speaker.data == nullptr ||
        virtual_microphone.frame_count == 0 ||
        remote_speaker.frame_count == 0) {
        return 0.0;
    }

    const auto frame_count = std::min(virtual_microphone.frame_count, remote_speaker.frame_count);
    double dot = 0.0;
    double mic_energy = 0.0;
    double remote_energy = 0.0;

    for (std::size_t frame = 0; frame < frame_count; ++frame) {
        const double mic = MonoSample(virtual_microphone, frame);
        const double remote = MonoSample(remote_speaker, frame);
        dot += mic * remote;
        mic_energy += mic * mic;
        remote_energy += remote * remote;
    }

    if (mic_energy <= 0.0 || remote_energy <= 0.0) {
        return 0.0;
    }
    return dot / std::sqrt(mic_energy * remote_energy);
}

}  // namespace TwoBrainRec::AudioDriver
