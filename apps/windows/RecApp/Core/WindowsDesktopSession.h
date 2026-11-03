#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <mutex>
#include <memory>
#include <string>

namespace graf::windows {

class WindowsDesktopSession final {
public:
    explicit WindowsDesktopSession(std::string sessionId);
    ~WindowsDesktopSession();

    WindowsDesktopSession(const WindowsDesktopSession&) = delete;
    WindowsDesktopSession& operator=(const WindowsDesktopSession&) = delete;

    [[nodiscard]] TransitionResult beginReadinessCheck();
    [[nodiscard]] TransitionResult markReady();
    [[nodiscard]] TransitionResult beginStart();
    [[nodiscard]] TransitionResult startRecording();
    [[nodiscard]] TransitionResult pause();
    [[nodiscard]] TransitionResult resume();
    [[nodiscard]] TransitionResult markDegraded(ReasonCode reason);
    [[nodiscard]] TransitionResult stop();
    [[nodiscard]] TransitionResult beginFinalizing();
    [[nodiscard]] TransitionResult saveLocal();
    [[nodiscard]] TransitionResult queue();
    [[nodiscard]] TransitionResult upload();
    [[nodiscard]] TransitionResult block(ReasonCode reason);
    [[nodiscard]] TransitionResult fail(ReasonCode reason);

    [[nodiscard]] const std::string& sessionId() const noexcept { return sessionId_; }
    [[nodiscard]] SessionState state() const noexcept { return state_; }
    [[nodiscard]] ReasonCode reason() const noexcept { return reason_; }

private:
    friend class NativeCapture;
    struct ActiveLease {
        bool armed = false;
        ~ActiveLease();
    };
    [[nodiscard]] TransitionResult transition(SessionState next, ReasonCode reason);
    [[nodiscard]] static bool allowed(SessionState from, SessionState to) noexcept;
    void releaseActiveLeaseIfNeeded() noexcept;

    std::string sessionId_;
    SessionState state_ = SessionState::idle;
    ReasonCode reason_ = ReasonCode::none;
    // A native finalizer can retain this existing slot after the UI is gone.
    std::shared_ptr<ActiveLease> activeLease_;

    static std::mutex activeLeaseMutex_;
    static bool activeLeaseHeld_;
};

} // namespace graf::windows
