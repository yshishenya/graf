#include "../../RecApp/Capture/CaptureReasonMapping.h"

#include <array>

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>

namespace {

using graf::windows::CaptureWorkerError;
using graf::windows::ReasonCode;
using graf::windows::reasonForWorkerError;

void testAccessDeniedIsAPermissionProblem() {
    // Отказ в доступе к микрофону — это разрешение, а не отключённое устройство:
    // от этого зависит текст, который читает человек, и следующий шаг.
    assert(reasonForWorkerError(CaptureWorkerError::accessDenied, true) == ReasonCode::microphonePermissionDenied);
    assert(reasonForWorkerError(CaptureWorkerError::accessDenied, false) == ReasonCode::renderEndpointUnavailable);
    assert(reasonForWorkerError(CaptureWorkerError::accessDenied, true) != ReasonCode::endpointInvalidated);
}

void testDeviceProblemsAreNamed() {
    assert(reasonForWorkerError(CaptureWorkerError::invalidEndpoint, true) == ReasonCode::microphoneEndpointUnavailable);
    assert(reasonForWorkerError(CaptureWorkerError::invalidEndpoint, false) == ReasonCode::renderEndpointUnavailable);
    assert(reasonForWorkerError(CaptureWorkerError::initializationFailed, true) == ReasonCode::microphoneEndpointUnavailable);
    assert(reasonForWorkerError(CaptureWorkerError::initializationFailed, false) == ReasonCode::renderEndpointUnavailable);
    assert(reasonForWorkerError(CaptureWorkerError::deviceInvalidated, true) == ReasonCode::endpointInvalidated);
}

void testUnchangedMappings() {
    assert(reasonForWorkerError(CaptureWorkerError::none, true) == ReasonCode::none);
    assert(reasonForWorkerError(CaptureWorkerError::alreadyRunning, true) == ReasonCode::activeSessionExists);
    assert(reasonForWorkerError(CaptureWorkerError::unsupportedFormat, true) == ReasonCode::formatNormalizationUnavailable);
    assert(reasonForWorkerError(CaptureWorkerError::bufferOverflow, true) == ReasonCode::queueOverflow);
    assert(reasonForWorkerError(CaptureWorkerError::clockDiscontinuity, true) == ReasonCode::clockDiscontinuity);
    assert(reasonForWorkerError(CaptureWorkerError::unsupportedPlatform, false) == ReasonCode::endpointInvalidated);
}

void testEveryErrorHasAReason() {
    const std::array<CaptureWorkerError, 10> errors{
        CaptureWorkerError::none,
        CaptureWorkerError::alreadyRunning,
        CaptureWorkerError::invalidEndpoint,
        CaptureWorkerError::unsupportedFormat,
        CaptureWorkerError::initializationFailed,
        CaptureWorkerError::deviceInvalidated,
        CaptureWorkerError::bufferOverflow,
        CaptureWorkerError::clockDiscontinuity,
        CaptureWorkerError::unsupportedPlatform,
        CaptureWorkerError::accessDenied,
    };
    for (const auto error : errors) {
        for (const bool microphone : {false, true}) {
            const auto reason = reasonForWorkerError(error, microphone);
            // Ни одна ошибка не остаётся без причины: причина — то, что увидит человек.
            if (error != CaptureWorkerError::none) assert(reason != ReasonCode::none);
        }
    }
}

} // namespace

int main() {
    testAccessDeniedIsAPermissionProblem();
    testDeviceProblemsAreNamed();
    testUnchangedMappings();
    testEveryErrorHasAReason();
    std::printf("CaptureReasonMappingTests: ok\n");
    return 0;
}
