#include "ClockMapper.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace graf::windows {

ClockMapping ClockMapper::observe(ClockObservation observation) {
    ClockMapping result;
    result.routeGeneration = routeGeneration_;
    const auto reject = [&](ClockFault fault) {
        result.fault = fault_ = fault;
        return result;
    };
    if (!healthy()) return reject(fault_);
    if (observation.sampleRate < 8'000 || observation.sampleRate > 192'000 ||
        observation.frameCount == 0 || observation.frameCount > 4'800 ||
        observation.audioClockResult != 0 ||
        (observation.flags & ~std::uint32_t{0x7}) != 0 ||
        (sampleRate_ != 0 && observation.sampleRate != sampleRate_)) return reject(ClockFault::invalidPacket);
    if ((observation.flags & ClockObservation::timestampError) != 0) return reject(ClockFault::timestampError);
    const bool firstPacket = sampleRate_ == 0;
    if (observation.audioClockFrequency != 0 &&
        (observation.audioClockFrequency < 8'000 || observation.audioClockFrequency > 10'000'000))
        return reject(ClockFault::invalidPacket);
    if (!firstPacket && observation.audioClockFrequency != audioClockFrequency_)
        return reject(ClockFault::invalidPacket);
    if (!firstPacket && audioClockFrequency_ != 0 && observation.audioClockPosition < lastAudioClockPosition_)
        return reject(ClockFault::nonMonotonic);
    sampleRate_ = observation.sampleRate;
    if (firstPacket) audioClockFrequency_ = observation.audioClockFrequency;
    lastAudioClockPosition_ = observation.audioClockPosition;
    if (firstPacket && observation.flags == ClockObservation::dataDiscontinuity) {
        result.discardStartup = true;
        return result;
    }
    if ((observation.flags & ClockObservation::dataDiscontinuity) != 0) return reject(ClockFault::discontinuity);
    if (initialized_ && (observation.qpc100ns <= lastQpc_ || observation.deviceFrames < lastDeviceFrames_))
        return reject(ClockFault::nonMonotonic);
    if (initialized_) {
        // GetBuffer identifies the packet's first frame. The current stream
        // clock is supplementary and cannot excuse missing/duplicated data.
        if (observation.deviceFrames - lastDeviceFrames_ != lastFrameCount_)
            return reject(ClockFault::sampleCountMismatch);
    }
    if (!initialized_) {
        firstQpc_ = observation.qpc100ns;
        firstDeviceFrames_ = observation.deviceFrames;
        initialized_ = true;
    }
    lastQpc_ = observation.qpc100ns;
    lastDeviceFrames_ = observation.deviceFrames;
    lastFrameCount_ = observation.frameCount;
    const auto expected = static_cast<long double>(observation.deviceFrames - firstDeviceFrames_);
    const auto elapsedQpcFrames = static_cast<long double>(observation.qpc100ns - firstQpc_) *
        observation.sampleRate / 10'000'000.0L;
    const auto drift = elapsedQpcFrames == 0.0L ? 0.0L :
        (static_cast<long double>(expected) - elapsedQpcFrames) * 1'000'000.0L / elapsedQpcFrames;
    result.driftPpm = static_cast<std::int32_t>(std::clamp(
        drift, static_cast<long double>(std::numeric_limits<std::int32_t>::min()),
        static_cast<long double>(std::numeric_limits<std::int32_t>::max())));
    result.qpc100ns = observation.qpc100ns;
    // Fixed timestamp uncertainty does not accumulate or reset per packet.
    result.valid = std::abs(expected - elapsedQpcFrames) <=
        elapsedQpcFrames * 0.0001L + observation.sampleRate * 0.001L + 1.0L;
    if (!result.valid) result.fault = fault_ = ClockFault::clockDrift;
    return result;
}

void ClockMapper::reset(std::uint64_t routeGeneration) noexcept {
    routeGeneration_ = routeGeneration == 0 ? routeGeneration_ + 1 : routeGeneration;
    firstQpc_ = firstDeviceFrames_ = lastQpc_ = lastDeviceFrames_ = lastAudioClockPosition_ = 0;
    lastFrameCount_ = sampleRate_ = 0;
    audioClockFrequency_ = 0;
    initialized_ = false;
    fault_ = ClockFault::none;
}

} // namespace graf::windows
