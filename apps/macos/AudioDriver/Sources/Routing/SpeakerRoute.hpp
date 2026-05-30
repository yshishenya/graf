#pragma once

#include "MicrophoneRoute.hpp"

namespace TwoBrainRec::AudioDriver {

bool RouteSpeakerFrames(
    InterleavedAudioBuffer virtual_speaker_input,
    MutableInterleavedAudioBuffer physical_output,
    MutableInterleavedAudioBuffer remote_capture_mirror
);

}  // namespace TwoBrainRec::AudioDriver
