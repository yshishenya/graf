#include "WebRuntimeState.h"

namespace graf::windows {

WebRuntimeProjection WebRuntimeStateProjection::unavailable(ReasonCode reason) {
    return {WebRuntimeState::unavailable, true, reason, "Кабинет временно недоступен. Запись и локальное сохранение не остановлены."};
}

WebRuntimeProjection WebRuntimeStateProjection::ready() {
    return {WebRuntimeState::ready, true, ReasonCode::none, "Кабинет доступен."};
}

WebRuntimeProjection WebRuntimeStateProjection::closed() {
    return {WebRuntimeState::closed, true, ReasonCode::none, "Кабинет закрыт. Нативное управление записью доступно."};
}

} // namespace graf::windows
