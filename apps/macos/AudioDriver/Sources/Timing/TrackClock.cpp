#include "TrackClock.hpp"

#include <cmath>

namespace TwoBrainRec::AudioDriver {
namespace {

double ExpectedDurationMs(const TrackClockSample& sample) {
    if (sample.sample_rate <= 0.0) {
        return 0.0;
    }
    return static_cast<double>(sample.frame_count) / sample.sample_rate * 1000.0;
}

double ObservedDurationMs(const TrackClockSample& previous, const TrackClockSample& current) {
    if (current.host_time_ns <= previous.host_time_ns) {
        return 0.0;
    }
    return static_cast<double>(current.host_time_ns - previous.host_time_ns) / 1'000'000.0;
}

}  // namespace

TrackClock::TrackClock(double drift_threshold_ms)
    : has_previous_(false),
      previous_{},
      drift_threshold_ms_(drift_threshold_ms) {}

ContinuityEvent TrackClock::Observe(const TrackClockSample& sample) {
    if (!has_previous_) {
        previous_ = sample;
        has_previous_ = true;
        return {
            sample.role,
            ContinuityEventType::None,
            sample.sequence,
            sample.host_time_ns,
            0.0,
            0.0
        };
    }

    const double expected_ms = ExpectedDurationMs(previous_);
    const double observed_ms = ObservedDurationMs(previous_, sample);
    const double drift_ms = observed_ms - expected_ms;
    ContinuityEventType type = ContinuityEventType::None;

    if (sample.sequence != previous_.sequence + 1) {
        type = ContinuityEventType::DropoutDetected;
    } else if (std::abs(drift_ms) > drift_threshold_ms_) {
        type = ContinuityEventType::ClockDriftDetected;
    } else if (sample.host_time_ns <= previous_.host_time_ns) {
        type = ContinuityEventType::StreamRestarted;
    }

    previous_ = sample;
    return {
        sample.role,
        type,
        sample.sequence,
        sample.host_time_ns,
        observed_ms,
        drift_ms
    };
}

}  // namespace TwoBrainRec::AudioDriver
