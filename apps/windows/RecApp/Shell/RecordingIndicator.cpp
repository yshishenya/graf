#include "RecordingIndicator.h"

namespace graf::windows {

RecordingIndicator::RecordingIndicator(StopHandler stopHandler)
    : stopHandler_(std::move(stopHandler)) {}

void RecordingIndicator::publish(SessionState state, ReasonCode reason) {
    snapshot_.state = state;
    snapshot_.reason = reason;
    snapshot_.visible = isCaptureState(state);
    snapshot_.stopAvailable = snapshot_.visible;
    snapshot_.accessibleName = snapshot_.visible ? "GRAF: остановить запись" : "GRAF: запись не активна";
    snapshot_.statusText = std::string(toString(state));
}

void RecordingIndicator::hide() noexcept {
    snapshot_.visible = false;
    snapshot_.stopAvailable = false;
}

void RecordingIndicator::clickStop() {
    if (snapshot_.stopAvailable && stopHandler_) stopHandler_();
}

} // namespace graf::windows
