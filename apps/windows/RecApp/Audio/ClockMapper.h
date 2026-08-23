#pragma once

#include <cstdint>

namespace graf::windows {

struct ClockObservation {
    std::uint64_t qpcTicks = 0;
    std::uint64_t deviceFrames = 0;
    std::uint32_t sampleRate = 48'000;
};

struct ClockMapping {
    bool valid = false;
    std::int64_t ptsFrames = 0;
    std::int32_t driftPpm = 0;
    std::uint64_t routeGeneration = 0;
};

class ClockMapper final {
public:
    explicit ClockMapper(std::uint64_t qpcFrequency = 10'000'000);

    [[nodiscard]] ClockMapping observe(ClockObservation observation);
    void reset(std::uint64_t routeGeneration) noexcept;
    [[nodiscard]] bool healthy() const noexcept { return healthy_; }

private:
    std::uint64_t qpcFrequency_;
    std::uint64_t routeGeneration_ = 1;
    std::uint64_t firstQpc_ = 0;
    std::uint64_t firstDeviceFrames_ = 0;
    std::uint64_t lastQpc_ = 0;
    std::uint64_t lastDeviceFrames_ = 0;
    bool healthy_ = true;
};

} // namespace graf::windows
