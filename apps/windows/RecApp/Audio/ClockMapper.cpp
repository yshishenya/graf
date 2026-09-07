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
        (observation.flags & ~std::uint32_t{0x7}) != 0 ||
        (sampleRate_ != 0 && observation.sampleRate != sampleRate_)) return reject(ClockFault::invalidPacket);
    if ((observation.flags & ClockObservation::timestampError) != 0) return reject(ClockFault::timestampError);
    const bool firstPacket = sampleRate_ == 0;
    if (observation.audioClockFrequency != 0 &&
        (observation.audioClockFrequency < 8'000 || observation.audioClockFrequency > 10'000'000))
        return reject(ClockFault::invalidPacket);
    if (audioClockFrequency_ != 0 && observation.audioClockFrequency != audioClockFrequency_)
        return reject(ClockFault::invalidPacket);
    sampleRate_ = observation.sampleRate;
    if (firstPacket) audioClockFrequency_ = observation.audioClockFrequency;
    if (firstPacket && observation.flags == ClockObservation::dataDiscontinuity) {
        result.discardStartup = true;
        return result;
    }
    if ((observation.flags & ClockObservation::dataDiscontinuity) != 0) return reject(ClockFault::discontinuity);
    if (initialized_ && ((audioClockFrequency_ == 0 &&
                          (observation.qpc100ns <= lastQpc_ || observation.deviceFrames < lastDeviceFrames_)) ||
                         (audioClockFrequency_ != 0 && observation.audioClockPosition < lastAudioClockPosition_)))
        return reject(ClockFault::nonMonotonic);
    if (initialized_) {
        // IAudioClock::GetPosition is the running stream position, not the
        // packet's first-frame position. It may advance between GetBuffer and
        // the next observation, so use it for monotonic timing only. The
        // portable fixture still has a packet counter and keeps its strict
        // continuity check.
        if (audioClockFrequency_ == 0 && observation.deviceFrames - lastDeviceFrames_ != lastFrameCount_)
            return reject(ClockFault::sampleCountMismatch);
    }
    if (!initialized_) {
        firstQpc_ = observation.qpc100ns;
        firstDeviceFrames_ = observation.deviceFrames;
        firstAudioClockPosition_ = observation.audioClockPosition;
        initialized_ = true;
    }
    lastQpc_ = observation.qpc100ns;
    lastDeviceFrames_ = observation.deviceFrames;
    lastAudioClockPosition_ = observation.audioClockPosition;
    lastFrameCount_ = observation.frameCount;
    const auto clockDelta = audioClockFrequency_ == 0 ?
        observation.deviceFrames - firstDeviceFrames_ :
        observation.audioClockPosition - firstAudioClockPosition_;
    const auto expected = audioClockFrequency_ == 0 ?
        static_cast<long double>(clockDelta) :
        static_cast<long double>(clockDelta) * observation.sampleRate / audioClockFrequency_;
    const auto elapsedQpcFrames = static_cast<long double>(observation.qpc100ns >= firstQpc_ ?
        observation.qpc100ns - firstQpc_ : 0) *
        observation.sampleRate / 10'000'000.0L;
    const auto drift = elapsedQpcFrames == 0.0L ? 0.0L :
        (static_cast<long double>(expected) - elapsedQpcFrames) * 1'000'000.0L / elapsedQpcFrames;
    result.driftPpm = static_cast<std::int32_t>(std::clamp(
        drift, static_cast<long double>(std::numeric_limits<std::int32_t>::min()),
        static_cast<long double>(std::numeric_limits<std::int32_t>::max())));
    // IAudioClock owns packet continuity. GetBuffer's QPC is retained as a
    // common source origin; virtualized hosts can report packet QPC jitter.
    if (audioClockFrequency_ == 0) {
        result.qpc100ns = observation.qpc100ns;
    } else {
        const auto clockQpc = firstQpc_ + static_cast<std::uint64_t>(std::llround(
            static_cast<long double>(clockDelta) * 10'000'000.0L / audioClockFrequency_));
        const auto packetQpc = lastMappedQpc_ + static_cast<std::uint64_t>(std::llround(
            static_cast<long double>(observation.frameCount) * 10'000'000.0L / observation.sampleRate));
        result.qpc100ns = mappedQpcInitialized_ ? packetQpc : clockQpc;
    }
    lastMappedQpc_ = result.qpc100ns;
    mappedQpcInitialized_ = true;
    if (audioClockFrequency_ == 0) {
        result.valid = std::abs(static_cast<long double>(expected) - elapsedQpcFrames) <=
            elapsedQpcFrames * 0.0001L + observation.sampleRate * 0.001L + 1.0L;
    } else {
        result.valid = true;
    }
    if (!result.valid) result.fault = fault_ = ClockFault::clockDrift;
    return result;
}

void ClockMapper::reset(std::uint64_t routeGeneration) noexcept {
    routeGeneration_ = routeGeneration == 0 ? routeGeneration_ + 1 : routeGeneration;
    firstQpc_ = firstDeviceFrames_ = lastQpc_ = lastMappedQpc_ = lastDeviceFrames_ = 0;
    firstAudioClockPosition_ = lastAudioClockPosition_ = 0;
    lastFrameCount_ = sampleRate_ = 0;
    audioClockFrequency_ = 0;
    mappedQpcInitialized_ = false;
    initialized_ = false;
    fault_ = ClockFault::none;
}

} // namespace graf::windows
