#include "SpeakerRoute.hpp"

#include <algorithm>

namespace TwoBrainRec::AudioDriver {
namespace {

bool Compatible(InterleavedAudioBuffer source, MutableInterleavedAudioBuffer destination) {
    return source.data != nullptr &&
           destination.data != nullptr &&
           source.frame_count == destination.frame_count &&
           source.channel_count == destination.channel_count &&
           source.channel_count > 0;
}

}  // namespace

bool RouteSpeakerFrames(
    InterleavedAudioBuffer virtual_speaker_input,
    MutableInterleavedAudioBuffer physical_output,
    MutableInterleavedAudioBuffer remote_capture_mirror
) {
    if (!Compatible(virtual_speaker_input, physical_output) ||
        !Compatible(virtual_speaker_input, remote_capture_mirror)) {
        return false;
    }

    const auto sample_count = virtual_speaker_input.frame_count * virtual_speaker_input.channel_count;
    std::copy(
        virtual_speaker_input.data,
        virtual_speaker_input.data + sample_count,
        physical_output.data
    );
    std::copy(
        virtual_speaker_input.data,
        virtual_speaker_input.data + sample_count,
        remote_capture_mirror.data
    );
    return true;
}

bool SpeakerRouteShouldRemainActive(unsigned int client_io_count) {
    return client_io_count > 0;
}

}  // namespace TwoBrainRec::AudioDriver
