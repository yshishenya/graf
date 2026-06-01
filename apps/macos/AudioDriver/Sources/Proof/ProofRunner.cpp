#include <iostream>
#include <cmath>
#include <string>
#include <vector>

#include "../Routing/MicrophoneRoute.hpp"
#include "../Routing/SpeakerRoute.hpp"
#include "../Timing/TrackClock.hpp"

namespace two_brain_rec::audio_proof {

struct VirtualDeviceExpectation {
    std::string display_name;
    std::string direction;
};

struct ContinuitySample {
    const char* track_role;
    std::int64_t monotonic_timestamp_ns;
    std::uint32_t frame_count;
    double drift_estimate_ms;
    bool dropout_detected;
};

std::vector<VirtualDeviceExpectation> ExpectedMVPDevices();
bool HasExactlyMVPDevices(const std::vector<VirtualDeviceExpectation>& devices);
bool IsContinuitySampleUsable(const ContinuitySample& sample);
bool RequiresDropoutMarker(const ContinuitySample& sample);
bool SharedAudioBufferRejectsOverflowWithoutMovingReadIndex();
bool SharedAudioBufferRejectsOversizedWrites();
bool SharedAudioBufferAcceptsZeroLengthWrite();

}  // namespace two_brain_rec::audio_proof

int main() {
    using namespace two_brain_rec::audio_proof;
    using namespace TwoBrainRec::AudioDriver;

    const auto devices = ExpectedMVPDevices();
    if (!HasExactlyMVPDevices(devices)) {
        std::cerr << "Expected exactly 2brain Rec Microphone and 2brain Rec Speaker\n";
        return 1;
    }

    const ContinuitySample sample{
        "remote_speaker",
        1'000'000,
        480,
        0.5,
        false
    };

    if (!IsContinuitySampleUsable(sample)) {
        std::cerr << "Continuity sample should be usable\n";
        return 1;
    }

    if (RequiresDropoutMarker(sample)) {
        std::cerr << "Nominal continuity sample should not require dropout marker\n";
        return 1;
    }
    if (!SharedAudioBufferRejectsOverflowWithoutMovingReadIndex()) {
        std::cerr << "SharedAudioBuffer must reject overflow without moving read index\n";
        return 1;
    }
    if (!SharedAudioBufferRejectsOversizedWrites()) {
        std::cerr << "SharedAudioBuffer must reject writes larger than capacity\n";
        return 1;
    }
    if (!SharedAudioBufferAcceptsZeroLengthWrite()) {
        std::cerr << "SharedAudioBuffer must accept zero-length writes as no-op\n";
        return 1;
    }

    std::vector<float> local_mic(960);
    std::vector<float> remote_speaker(960);
    std::vector<float> virtual_mic(960);
    std::vector<float> physical_output(960);
    std::vector<float> remote_mirror(960);

    for (std::size_t index = 0; index < local_mic.size(); ++index) {
        local_mic[index] = static_cast<float>(std::sin(static_cast<double>(index) * 0.05));
        remote_speaker[index] = static_cast<float>(std::sin(static_cast<double>(index) * 0.11));
    }

    const InterleavedAudioBuffer mic_source{local_mic.data(), 480, 2};
    const InterleavedAudioBuffer remote_source{remote_speaker.data(), 480, 2};
    const MutableInterleavedAudioBuffer virtual_mic_destination{virtual_mic.data(), 480, 2};

    if (!RouteMicrophoneFrames(mic_source, remote_source, virtual_mic_destination)) {
        std::cerr << "Microphone route should accept compatible buffers\n";
        return 1;
    }
    if (std::abs(RemoteLeakageScore({virtual_mic.data(), 480, 2}, remote_source)) > 0.05) {
        std::cerr << "Microphone route leaked remote speaker signal\n";
        return 1;
    }

    if (!RouteSpeakerFrames(
            remote_source,
            {physical_output.data(), 480, 2},
            {remote_mirror.data(), 480, 2})) {
        std::cerr << "Speaker route should accept compatible buffers\n";
        return 1;
    }
    if (physical_output != remote_speaker || remote_mirror != remote_speaker) {
        std::cerr << "Speaker route must mirror remote speaker frames to output and capture\n";
        return 1;
    }

    TrackClock clock;
    const auto first_event = clock.Observe({AudioTrackRole::RemoteSpeaker, 1, 1'000'000, 480, 48'000.0});
    const auto second_event = clock.Observe({AudioTrackRole::RemoteSpeaker, 2, 11'000'000, 480, 48'000.0});
    const auto dropout_event = clock.Observe({AudioTrackRole::RemoteSpeaker, 4, 21'000'000, 480, 48'000.0});
    if (first_event.type != ContinuityEventType::None ||
        second_event.type != ContinuityEventType::None ||
        dropout_event.type != ContinuityEventType::DropoutDetected) {
        std::cerr << "TrackClock continuity event classification failed\n";
        return 1;
    }

    std::cout << "AudioDriver proof scaffold: PASS\n";
    std::cout << "Runtime Core Audio publication proof: NOT RUN\n";
    return 0;
}
