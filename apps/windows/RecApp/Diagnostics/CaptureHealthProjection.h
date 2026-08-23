#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <cstdint>

namespace graf::windows {

struct CaptureHealthSnapshot {
    SessionState state = SessionState::idle;
    ReasonCode reason = ReasonCode::none;
    std::uint64_t droppedFrames = 0;
    std::uint64_t overflowCount = 0;
    std::uint64_t gapCount = 0;
    std::uint64_t durationMs = 0;
};

class CaptureHealthProjection final {
public:
    void observeDrop() noexcept { ++snapshot_.droppedFrames; }
    void observeOverflow() noexcept { ++snapshot_.overflowCount; }
    void observeGap() noexcept { ++snapshot_.gapCount; }
    void setState(SessionState state, ReasonCode reason) noexcept { snapshot_.state = state; snapshot_.reason = reason; }
    void setDuration(std::uint64_t durationMs) noexcept { snapshot_.durationMs = durationMs; }
    [[nodiscard]] const CaptureHealthSnapshot& snapshot() const noexcept { return snapshot_; }

private:
    CaptureHealthSnapshot snapshot_;
};

} // namespace graf::windows
