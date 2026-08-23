#pragma once

#include "VerifiedTargetRegistry.h"

#include <cstdint>

namespace graf::windows {

enum class AutomaticPromptState {
    idle,
    countdown,
    immediateStart,
    skipped,
    timedOut,
    started,
    blocked,
};

class AutomaticRecordingPolicy final {
public:
    [[nodiscard]] AutomaticPromptState observeVerifiedTarget(const VerifiedTargetIdentity& target,
                                                              bool prerequisitesReady);
    [[nodiscard]] AutomaticPromptState tick(std::uint32_t elapsedSeconds);
    [[nodiscard]] AutomaticPromptState recordNow(bool prerequisitesReady) noexcept;
    [[nodiscard]] AutomaticPromptState skip() noexcept;
    [[nodiscard]] AutomaticPromptState timeout() noexcept;
    [[nodiscard]] AutomaticPromptState alwaysRecordThisApplication() noexcept;
    [[nodiscard]] AutomaticPromptState disableAlwaysRecord() noexcept;

    [[nodiscard]] bool isAlwaysRecord(const VerifiedTargetIdentity& target) const noexcept;
    [[nodiscard]] AutomaticPromptState state() const noexcept { return state_; }
    [[nodiscard]] const VerifiedTargetIdentity& target() const noexcept { return target_; }

private:
    VerifiedTargetIdentity target_;
    VerifiedTargetIdentity alwaysRecordTarget_;
    AutomaticPromptState state_ = AutomaticPromptState::idle;
    bool alwaysRecord_ = false;
    std::uint32_t elapsedSeconds_ = 0;
};

} // namespace graf::windows
