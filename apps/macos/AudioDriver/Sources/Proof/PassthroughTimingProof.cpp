#include <cstdint>

namespace two_brain_rec::audio_proof {

struct ContinuitySample {
    const char* track_role;
    std::int64_t monotonic_timestamp_ns;
    std::uint32_t frame_count;
    double drift_estimate_ms;
    bool dropout_detected;
};

bool IsContinuitySampleUsable(const ContinuitySample& sample) {
    return sample.track_role != nullptr &&
           sample.monotonic_timestamp_ns > 0 &&
           sample.frame_count > 0;
}

bool RequiresDropoutMarker(const ContinuitySample& sample) {
    return sample.dropout_detected || sample.drift_estimate_ms > 100.0 ||
           sample.drift_estimate_ms < -100.0;
}

}  // namespace two_brain_rec::audio_proof
