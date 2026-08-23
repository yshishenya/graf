#include "CaptureFaultRecovery.h"

namespace graf::windows {

FaultRecoveryResult CaptureFaultRecovery::handle(ReasonCode reason) noexcept {
    switch (reason) {
    case ReasonCode::networkUnavailable:
    case ReasonCode::webViewRuntimeUnavailable:
        return {true, true, reason, "Сохранить локально и повторить позже"};
    case ReasonCode::endpointInvalidated:
    case ReasonCode::clockDiscontinuity:
    case ReasonCode::queueOverflow:
    case ReasonCode::finalizationFailed:
        return {true, false, reason, "Остановить и сохранить только подтверждённый фрагмент"};
    default:
        return {false, false, reason, "Проверить разрешения и устройство"};
    }
}

} // namespace graf::windows
