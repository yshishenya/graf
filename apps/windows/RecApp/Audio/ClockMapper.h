#pragma once

#include <cstdint>

namespace graf::windows {

enum class ClockFault {
    none, invalidPacket, timestampError, discontinuity, nonMonotonic, sampleCountMismatch, clockDrift,
};

struct CaptureClockDiagnostics {
    std::uint32_t startupDiscardedFrames = 0;
    ClockFault fault = ClockFault::none;
};

struct ClockObservation {
    // Values from AUDCLNT_BUFFERFLAGS; keep all flags, including unknown bits.
    static constexpr std::uint32_t dataDiscontinuity = 0x1, silent = 0x2, timestampError = 0x4;
    // IAudioCaptureClient::GetBuffer returns 100-ns units, not raw QPC ticks.
    std::uint64_t qpc100ns = 0;
    std::uint64_t deviceFrames = 0;
    std::uint32_t sampleRate = 48'000;
    std::uint32_t flags = 0;
    std::uint32_t frameCount = 0;
    // IAudioClock position/frequency. Zero is retained only for portable
    // mapper fixtures; the native worker requires the stream clock service.
    std::uint64_t audioClockPosition = 0;
    std::uint64_t audioClockFrequency = 0;
};

struct ClockMapping {
    bool valid = false;
    bool discardStartup = false;
    ClockFault fault = ClockFault::none;
    std::uint64_t qpc100ns = 0;
    std::int32_t driftPpm = 0;
    std::uint64_t routeGeneration = 0;
};

class ClockMapper final {
public:
    [[nodiscard]] ClockMapping observe(ClockObservation observation);
    void reset(std::uint64_t routeGeneration) noexcept;
    [[nodiscard]] bool healthy() const noexcept { return fault_ == ClockFault::none; }

private:
    std::uint64_t routeGeneration_ = 1;
    std::uint64_t firstQpc_ = 0;
    std::uint64_t firstDeviceFrames_ = 0;
    std::uint64_t firstAudioClockPosition_ = 0;
    std::uint64_t lastQpc_ = 0;
    std::uint64_t lastMappedQpc_ = 0;
    std::uint64_t lastDeviceFrames_ = 0;
    std::uint64_t lastAudioClockPosition_ = 0;
    std::uint32_t lastFrameCount_ = 0;
    std::uint32_t sampleRate_ = 0;
    std::uint64_t audioClockFrequency_ = 0;
    bool mappedQpcInitialized_ = false;
    bool initialized_ = false;
    ClockFault fault_ = ClockFault::none;
};

} // namespace graf::windows
