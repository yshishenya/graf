#include "CaptureReasonMapping.h"

namespace graf::windows {

ReasonCode reasonForWorkerError(CaptureWorkerError error, bool microphoneSource) noexcept {
    switch (error) {
    case CaptureWorkerError::none: return ReasonCode::none;
    case CaptureWorkerError::alreadyRunning: return ReasonCode::activeSessionExists;
    case CaptureWorkerError::unsupportedFormat: return ReasonCode::formatNormalizationUnavailable;
    case CaptureWorkerError::normalizationFailed: return ReasonCode::formatNormalizationUnavailable;
    case CaptureWorkerError::bufferOverflow: return ReasonCode::queueOverflow;
    case CaptureWorkerError::sinkRejected: return ReasonCode::queueOverflow;
    case CaptureWorkerError::clockDiscontinuity: return ReasonCode::clockDiscontinuity;
    case CaptureWorkerError::accessDenied:
        return microphoneSource ? ReasonCode::microphonePermissionDenied : ReasonCode::renderEndpointUnavailable;
    case CaptureWorkerError::invalidEndpoint:
    case CaptureWorkerError::initializationFailed:
        return microphoneSource ? ReasonCode::microphoneEndpointUnavailable : ReasonCode::renderEndpointUnavailable;
    case CaptureWorkerError::waitFailed:
    case CaptureWorkerError::packetReadFailed:
    case CaptureWorkerError::bufferReadFailed:
    case CaptureWorkerError::audioClockFailed:
    case CaptureWorkerError::releaseFailed:
    case CaptureWorkerError::deviceInvalidated:
    case CaptureWorkerError::unsupportedPlatform:
        return ReasonCode::endpointInvalidated;
    }
    return ReasonCode::endpointInvalidated;
}

} // namespace graf::windows
