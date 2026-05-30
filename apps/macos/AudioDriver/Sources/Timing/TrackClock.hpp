#pragma once

#include <cstdint>

namespace TwoBrainRec::AudioDriver {

enum class AudioTrackRole {
    LocalMicrophone,
    RemoteSpeaker
};

enum class ContinuityEventType {
    None,
    DropoutDetected,
    ClockDriftDetected,
    StreamRestarted
};

struct TrackClockSample {
    AudioTrackRole role;
    std::uint64_t sequence;
    std::uint64_t host_time_ns;
    std::uint32_t frame_count;
    double sample_rate;
};

struct ContinuityEvent {
    AudioTrackRole role;
    ContinuityEventType type;
    std::uint64_t sequence;
    std::uint64_t monotonic_time_ns;
    double duration_ms;
    double drift_estimate_ms;
};

class TrackClock {
public:
    explicit TrackClock(double drift_threshold_ms = 100.0);

    ContinuityEvent Observe(const TrackClockSample& sample);

private:
    bool has_previous_;
    TrackClockSample previous_;
    double drift_threshold_ms_;
};

}  // namespace TwoBrainRec::AudioDriver
