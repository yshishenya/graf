#include "AutomaticRecordingPolicy.h"

namespace graf::windows {

AutomaticPromptState AutomaticRecordingPolicy::observeVerifiedTarget(const VerifiedTargetIdentity& target,
                                                                      bool prerequisitesReady) {
    target_ = target; elapsedSeconds_ = 0;
    if (!prerequisitesReady) return state_ = AutomaticPromptState::blocked;
    return state_ = alwaysRecord_ ? AutomaticPromptState::started : AutomaticPromptState::countdown;
}

AutomaticPromptState AutomaticRecordingPolicy::tick(std::uint32_t elapsedSeconds) {
    if (state_ != AutomaticPromptState::countdown) return state_;
    elapsedSeconds_ += elapsedSeconds;
    if (elapsedSeconds_ >= 8) state_ = AutomaticPromptState::started;
    return state_;
}

AutomaticPromptState AutomaticRecordingPolicy::recordNow(bool prerequisitesReady) noexcept {
    state_ = prerequisitesReady ? AutomaticPromptState::immediateStart : AutomaticPromptState::blocked;
    return state_;
}

AutomaticPromptState AutomaticRecordingPolicy::skip() noexcept {
    state_ = AutomaticPromptState::skipped; return state_;
}

AutomaticPromptState AutomaticRecordingPolicy::timeout() noexcept {
    state_ = AutomaticPromptState::timedOut; return state_;
}

AutomaticPromptState AutomaticRecordingPolicy::alwaysRecordThisApplication() noexcept {
    alwaysRecord_ = true; state_ = AutomaticPromptState::started; return state_;
}

bool AutomaticRecordingPolicy::isAlwaysRecord(const VerifiedTargetIdentity& target) const noexcept {
    return alwaysRecord_ && target.executableFingerprint == target_.executableFingerprint &&
           target.publisherFingerprint == target_.publisherFingerprint && target.registryVersion == target_.registryVersion;
}

} // namespace graf::windows
