#pragma once
#include <cstdint>
#include <limits>

namespace graf::windows {
struct InteractionPermit {
    bool allowed = false;
    std::uint64_t epoch = 0;
};

// Positive evidence only. Native errors, unknown flags and missing subscriptions
// become false here; the portable policy owns no HWND, callbacks or capture.
struct InteractionSample {
    bool subscriptionsReady = false;
    bool sessionActive = false;
    bool sessionUnlocked = false;
    bool inputDesktop = false;
};
enum class InteractionEvent {
    sessionUnavailable, sessionAvailable, suspend, resumeAutomatic,
    resumeInteractive, desktopSwitch, shutdown
};

class InteractionPermitState final {
public:
    [[nodiscard]] InteractionPermit permit() const noexcept { return {allowed_, epoch_}; }
    // At most five registration attempts: initially, then after 1/2/4/8 s.
    // Successful native subscriptions are retained; no busy retry loop on failure.
    [[nodiscard]] bool retrySubscriptionsDue(std::uint64_t nowMilliseconds) noexcept {
        if (stopped_ || registrationAttempts_ >= 5 || nowMilliseconds < nextRegistrationAttempt_) return false;
        nextRegistrationAttempt_ = nowMilliseconds + (1000ULL << registrationAttempts_++);
        return true;
    }
    void event(InteractionEvent event) noexcept {
        revoke();
        switch (event) {
        case InteractionEvent::sessionUnavailable: sessionBlocked_ = true; break;
        case InteractionEvent::suspend:
        case InteractionEvent::resumeAutomatic: powerBlocked_ = true; break;
        case InteractionEvent::sessionAvailable:
            sessionBlocked_ = false;
            powerBlocked_ = false;
            break;
        case InteractionEvent::resumeInteractive: powerBlocked_ = false; break;
        case InteractionEvent::shutdown: stopped_ = true; break;
        case InteractionEvent::desktopSwitch: break;
        }
    }
    [[nodiscard]] InteractionPermit observe(InteractionSample sample, std::uint64_t startedAt,
                                             std::uint64_t finishedAt) noexcept {
        // Native queries may block. Timestamp completion and reject stale facts;
        // a subsequent bounded positive query can admit a new decision.
        if (finishedAt < startedAt || finishedAt - startedAt > 2500) sample = {};
        return observe(sample, finishedAt);
    }
    [[nodiscard]] InteractionPermit observe(InteractionSample sample, std::uint64_t nowMilliseconds) noexcept {
        // Also fences workers when suspend notification was missed or delayed.
        // A fresh positive sample can admit a NEW decision, never the old token.
        if (sampled_ && (nowMilliseconds < lastSample_ || nowMilliseconds - lastSample_ > 2500)) revoke();
        sampled_ = true;
        lastSample_ = nowMilliseconds;
        const bool eligible = !stopped_ && !sessionBlocked_ && !powerBlocked_ && sample.subscriptionsReady &&
            sample.sessionActive && sample.sessionUnlocked && sample.inputDesktop;
        if (allowed_ && !eligible) revoke();
        allowed_ = eligible;
        return permit();
    }
private:
    void revoke() noexcept {
        allowed_ = false;
        if (epoch_ == (std::numeric_limits<std::uint64_t>::max)()) stopped_ = true;
        else ++epoch_;
    }
    std::uint64_t epoch_ = 1, lastSample_ = 0;
    std::uint64_t nextRegistrationAttempt_ = 0;
    unsigned registrationAttempts_ = 0;
    bool allowed_ = false, sampled_ = false, sessionBlocked_ = false, powerBlocked_ = false, stopped_ = false;
};
} // namespace graf::windows
