#include "WindowsDesktopSession.h"

#include <utility>

namespace graf::windows {

std::mutex WindowsDesktopSession::activeLeaseMutex_;
bool WindowsDesktopSession::activeLeaseHeld_ = false;

WindowsDesktopSession::WindowsDesktopSession(std::string sessionId)
    : sessionId_(std::move(sessionId)) {}

WindowsDesktopSession::~WindowsDesktopSession() {
    releaseActiveLeaseIfNeeded();
}

TransitionResult WindowsDesktopSession::beginReadinessCheck() {
    if (state_ != SessionState::idle) {
        return {TransitionStatus::rejected, state_, reason_};
    }
    std::lock_guard lock(activeLeaseMutex_);
    if (activeLeaseHeld_) {
        return {TransitionStatus::rejected, state_, ReasonCode::activeSessionExists};
    }
    activeLeaseHeld_ = true;
    ownsActiveLease_ = true;
    return transition(SessionState::checkingReadiness, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::markReady() {
    return transition(SessionState::ready, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::beginStart() {
    return transition(SessionState::starting, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::startRecording() {
    return transition(SessionState::recording, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::pause() {
    return transition(SessionState::paused, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::resume() {
    return transition(SessionState::recording, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::markDegraded(ReasonCode reason) {
    return transition(SessionState::degraded, reason);
}

TransitionResult WindowsDesktopSession::stop() {
    if (state_ == SessionState::stopping || state_ == SessionState::finalizing ||
        state_ == SessionState::savedLocal || state_ == SessionState::queued ||
        state_ == SessionState::uploaded || state_ == SessionState::blocked ||
        state_ == SessionState::failed) {
        return {TransitionStatus::idempotent, state_, reason_};
    }
    return transition(SessionState::stopping, reason_);
}

TransitionResult WindowsDesktopSession::beginFinalizing() {
    return transition(SessionState::finalizing, reason_);
}

TransitionResult WindowsDesktopSession::saveLocal() {
    return transition(SessionState::savedLocal, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::queue() {
    return transition(SessionState::queued, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::upload() {
    return transition(SessionState::uploaded, ReasonCode::none);
}

TransitionResult WindowsDesktopSession::block(ReasonCode reason) {
    return transition(SessionState::blocked, reason);
}

TransitionResult WindowsDesktopSession::fail(ReasonCode reason) {
    return transition(SessionState::failed, reason);
}

TransitionResult WindowsDesktopSession::transition(SessionState next, ReasonCode reason) {
    if (!allowed(state_, next)) {
        return {TransitionStatus::rejected, state_, reason_};
    }
    state_ = next;
    reason_ = reason;
    if (next == SessionState::savedLocal || next == SessionState::blocked ||
        next == SessionState::failed) {
        releaseActiveLeaseIfNeeded();
    }
    return {TransitionStatus::accepted, state_, reason_};
}

bool WindowsDesktopSession::allowed(SessionState from, SessionState to) noexcept {
    switch (from) {
    case SessionState::idle: return to == SessionState::checkingReadiness;
    case SessionState::checkingReadiness: return to == SessionState::ready || to == SessionState::blocked || to == SessionState::failed;
    case SessionState::ready: return to == SessionState::starting || to == SessionState::stopping || to == SessionState::blocked || to == SessionState::failed;
    case SessionState::starting: return to == SessionState::recording || to == SessionState::stopping || to == SessionState::degraded || to == SessionState::failed;
    case SessionState::recording: return to == SessionState::paused || to == SessionState::degraded || to == SessionState::stopping || to == SessionState::failed;
    case SessionState::paused: return to == SessionState::recording || to == SessionState::degraded || to == SessionState::stopping || to == SessionState::failed;
    case SessionState::degraded: return to == SessionState::stopping || to == SessionState::failed;
    case SessionState::stopping: return to == SessionState::finalizing || to == SessionState::failed;
    case SessionState::finalizing: return to == SessionState::savedLocal || to == SessionState::blocked || to == SessionState::failed;
    case SessionState::savedLocal: return to == SessionState::queued || to == SessionState::uploaded;
    case SessionState::queued: return to == SessionState::uploaded || to == SessionState::failed;
    case SessionState::uploaded: return false;
    case SessionState::blocked: return false;
    case SessionState::failed: return false;
    }
    return false;
}

void WindowsDesktopSession::releaseActiveLeaseIfNeeded() noexcept {
    if (!ownsActiveLease_) {
        return;
    }
    std::lock_guard lock(activeLeaseMutex_);
    activeLeaseHeld_ = false;
    ownsActiveLease_ = false;
}

} // namespace graf::windows
