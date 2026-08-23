#include "ClockMapper.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace graf::windows {

ClockMapper::ClockMapper(std::uint64_t qpcFrequency)
    : qpcFrequency_(qpcFrequency == 0 ? 10'000'000 : qpcFrequency) {}

ClockMapping ClockMapper::observe(ClockObservation observation) {
    ClockMapping result;
    result.routeGeneration = routeGeneration_;
    if (!healthy_ || observation.sampleRate == 0 || observation.qpcTicks < lastQpc_ ||
        observation.deviceFrames < lastDeviceFrames_) {
        healthy_ = false;
        return result;
    }
    if (!initialized_) {
        firstQpc_ = observation.qpcTicks;
        firstDeviceFrames_ = observation.deviceFrames;
        initialized_ = true;
    }
    lastQpc_ = observation.qpcTicks;
    lastDeviceFrames_ = observation.deviceFrames;
    const auto qpcDelta = observation.qpcTicks - firstQpc_;
    const auto deviceDelta = observation.deviceFrames - firstDeviceFrames_;
    // QPC ticks grow throughout the process lifetime; multiplying the raw
    // counter by sampleRate overflows uint64_t on ordinary long captures.
    const auto expected = static_cast<std::uint64_t>(
        (static_cast<long double>(qpcDelta) * observation.sampleRate) / qpcFrequency_);
    result.ptsFrames = static_cast<std::int64_t>(firstDeviceFrames_ + deviceDelta);
    const auto denominator = expected == 0 ? 1.0L : static_cast<long double>(expected);
    const auto drift = (static_cast<long double>(deviceDelta) - expected) * 1'000'000.0L / denominator;
    result.driftPpm = static_cast<std::int32_t>(std::clamp(
        drift, static_cast<long double>(std::numeric_limits<std::int32_t>::min()),
        static_cast<long double>(std::numeric_limits<std::int32_t>::max())));
    result.valid = result.driftPpm >= -100 && result.driftPpm <= 100;
    if (!result.valid) healthy_ = false;
    return result;
}

void ClockMapper::reset(std::uint64_t routeGeneration) noexcept {
    routeGeneration_ = routeGeneration == 0 ? routeGeneration_ + 1 : routeGeneration;
    firstQpc_ = firstDeviceFrames_ = lastQpc_ = lastDeviceFrames_ = 0;
    initialized_ = false;
    healthy_ = true;
}

} // namespace graf::windows
