#include "WindowsReadinessGate.h"

namespace graf::windows {

ReadinessResult WindowsReadinessGate::evaluate(const ReadinessInputs& inputs) {
    ReadinessResult result;
    result.webViewReady = inputs.webViewRuntimeReady;
    if (!inputs.recordingPolicyAllowed) {
        result.addBlocker(ReasonCode::recordingPolicyBlocked);
    }
    if (!inputs.microphonePermissionGranted) {
        result.addBlocker(ReasonCode::microphonePermissionDenied);
    }
    if (!inputs.microphoneEndpointReady) {
        result.addBlocker(ReasonCode::microphoneEndpointUnavailable);
    }
    if (!inputs.renderEndpointReady) {
        result.addBlocker(ReasonCode::renderEndpointUnavailable);
    }
    if (!inputs.formatNormalizationReady) {
        result.addBlocker(ReasonCode::formatNormalizationUnavailable);
    }
    if (!inputs.aecReady) {
        result.addBlocker(ReasonCode::aecUnavailable);
    }
    if (!inputs.storageWritable) {
        result.addBlocker(ReasonCode::storageUnavailable);
    }
    if (!inputs.aacEncoderReady) {
        result.addBlocker(ReasonCode::aacEncoderUnavailable);
    }
    result.recordingReady = result.blockerCount == 0;
    return result;
}

} // namespace graf::windows
