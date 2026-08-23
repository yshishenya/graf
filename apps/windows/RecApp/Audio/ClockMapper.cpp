#include "ClockMapper.h"

#include <cstdlib>

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
    if (firstQpc_ == 0) {
        firstQpc_ = observation.qpcTicks;
        firstDeviceFrames_ = observation.deviceFrames;
    }
    lastQpc_ = observation.qpcTicks;
    lastDeviceFrames_ = observation.deviceFrames;
    const auto qpcDelta = observation.qpcTicks - firstQpc_;
    const auto deviceDelta = observation.deviceFrames - firstDeviceFrames_;
    const auto expected = (qpcDelta * observation.sampleRate) / qpcFrequency_;
    result.ptsFrames = static_cast<std::int64_t>(firstDeviceFrames_ + deviceDelta);
    const auto difference = static_cast<std::int64_t>(deviceDelta) - static_cast<std::int64_t>(expected);
    const auto denominator = expected == 0 ? 1 : expected;
    result.driftPpm = static_cast<std::int32_t>((difference * 1'000'000) / static_cast<std::int64_t>(denominator));
    result.valid = std::llabs(result.driftPpm) <= 100;
    if (!result.valid) healthy_ = false;
    return result;
}

void ClockMapper::reset(std::uint64_t routeGeneration) noexcept {
    routeGeneration_ = routeGeneration == 0 ? routeGeneration_ + 1 : routeGeneration;
    firstQpc_ = firstDeviceFrames_ = lastQpc_ = lastDeviceFrames_ = 0;
    healthy_ = true;
}

} // namespace graf::windows
