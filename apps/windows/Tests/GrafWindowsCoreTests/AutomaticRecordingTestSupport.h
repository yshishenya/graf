#pragma once

#include "../../RecApp/MeetingDetection/AutomaticRecordingPolicy.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

namespace graf::windows::testing {
using namespace std::chrono_literals;

inline VerifiedTargetIdentity target(char executable = 'a', char publisher = 'b', std::uint32_t version = 1) {
    return {std::string(64, executable), std::string(64, publisher), "Meeting app", version,
        std::string("app_") + executable};
}

inline DetectionClock::time_point at(std::chrono::milliseconds elapsed = 0ms) {
    return DetectionClock::time_point(100s + elapsed);
}

inline AutomaticRecordingPrerequisites ready() {
    AutomaticRecordingPrerequisites result;
    result.capture.microphonePermissionGranted = true;
    result.capture.microphoneEndpointReady = true;
    result.capture.renderEndpointReady = true;
    result.capture.formatNormalizationReady = true;
    result.capture.aecReady = true;
    result.capture.storageWritable = true;
    result.capture.aacEncoderReady = true;
    result.visibleIndicatorAvailable = true;
    result.oneActionStopAvailable = true;
    return result;
}

inline TargetDetectionSnapshot snapshot(DetectionClock::time_point time, const VerifiedTargetIdentity& identity = target()) {
    return {TargetDetectionStatus::ready, time, {{identity, 42, 1234, true, true, true}}};
}

struct Preferences {
    std::string bytes;
    unsigned writes = 0;
    bool writeFails = false;
    AutomaticRecordingPreferenceStore store() {
        return {[this] { return std::optional<std::string>{bytes}; }, [this](std::string_view value) {
            ++writes;
            if (writeFails) return false;
            bytes = value;
            return true;
        }};
    }
};

inline AutomaticRecordingDecision observeFor(AutomaticRecordingPolicy& policy, int firstSecond, int lastSecond,
                                              const VerifiedTargetIdentity& identity = target()) {
    AutomaticRecordingDecision result;
    for (int second = firstSecond; second <= lastSecond; ++second) {
        const auto now = at(std::chrono::seconds(second));
        result = policy.update(snapshot(now, identity), ready(), now);
    }
    return result;
}
} // namespace graf::windows::testing
