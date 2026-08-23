#include "WindowsPermissionRecovery.h"

namespace graf::windows {

RecoveryOption WindowsPermissionRecovery::forReason(ReasonCode reason) noexcept {
    switch (reason) {
    case ReasonCode::microphonePermissionDenied:
        return {reason, RecoveryAction::openMicrophonePrivacy, "Открыть настройки микрофона"};
    case ReasonCode::microphoneEndpointUnavailable:
        return {reason, RecoveryAction::choosePhysicalMicrophone, "Выбрать микрофон"};
    case ReasonCode::renderEndpointUnavailable:
        return {reason, RecoveryAction::openSoundSettings, "Открыть настройки звука"};
    case ReasonCode::storageUnavailable:
        return {reason, RecoveryAction::freeLocalStorage, "Освободить место"};
    case ReasonCode::webViewRuntimeUnavailable:
        return {reason, RecoveryAction::installWebViewRuntime, "Восстановить WebView2"};
    case ReasonCode::aacEncoderUnavailable:
        return {reason, RecoveryAction::installMediaFeaturePack, "Установить Media Feature Pack"};
    default:
        return {reason, RecoveryAction::retryReadiness, "Повторить проверку"};
    }
}

std::size_t WindowsPermissionRecovery::collect(const ReasonCode* reasons, std::size_t count,
                                                std::array<RecoveryOption, 8>& output) noexcept {
    if (reasons == nullptr) return 0;
    const auto limit = count < output.size() ? count : output.size();
    std::size_t written = 0;
    for (std::size_t index = 0; index < limit; ++index) {
        const auto option = forReason(reasons[index]);
        bool duplicate = false;
        for (std::size_t previous = 0; previous < written; ++previous) {
            if (output[previous].action == option.action) { duplicate = true; break; }
        }
        if (!duplicate) output[written++] = option;
    }
    return written;
}

} // namespace graf::windows
