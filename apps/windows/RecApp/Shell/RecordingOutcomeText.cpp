#include "RecordingOutcomeText.h"

namespace graf::windows {

ReasonCode effectiveFailureReason(ReasonCode reason, bool microphonePermissionGranted) noexcept {
    if (microphonePermissionGranted) return reason;
    switch (reason) {
        case ReasonCode::endpointInvalidated:
        case ReasonCode::microphoneEndpointUnavailable:
        case ReasonCode::microphonePermissionDenied:
            return ReasonCode::microphonePermissionDenied;
        default:
            return reason;
    }
}

bool isMicrophoneOnlyReason(ReasonCode reason) noexcept {
    return reason == ReasonCode::microphonePermissionDenied ||
           reason == ReasonCode::microphoneEndpointUnavailable;
}

std::wstring recordingDegradedText(ReasonCode reason) {
    switch (reason) {
        case ReasonCode::microphonePermissionDenied:
            return L"Микрофон недоступен: нет разрешения. Запись сохранена с системным звуком, "
                   L"голос в неё не попал.";
        default:
            return L"Микрофон недоступен. Запись сохранена с системным звуком, голос в неё не попал.";
    }
}

std::wstring recordingFailureText(ReasonCode reason, bool trustedPrefixRetained) {
    switch (reason) {
        case ReasonCode::microphonePermissionDenied:
            return L"Нет доступа к микрофону. Откройте «Настройки GRAF» → «Автозапись» → "
                   L"«Разрешения Windows» и разрешите доступ, затем повторите запись.";
        case ReasonCode::microphoneEndpointUnavailable:
            return L"Микрофон недоступен. Выберите другое устройство записи в панели «Запись».";
        case ReasonCode::renderEndpointUnavailable:
            return L"Системный звук недоступен. Проверьте устройство воспроизведения в параметрах Windows.";
        case ReasonCode::formatNormalizationUnavailable:
            return L"Не удалось подготовить звук к записи. Проверьте устройство и повторите попытку.";
        case ReasonCode::aecUnavailable:
            return L"Не удалось включить обработку эха. Закройте другие программы, которые работают со звуком, и повторите запись.";
        case ReasonCode::aacEncoderUnavailable:
            return L"Не удалось запустить кодирование звука. Перезапустите GRAF и повторите запись.";
        case ReasonCode::storageUnavailable:
            return L"Не хватает места для записи. Освободите место на диске и повторите попытку.";
        case ReasonCode::queueOverflow:
            return L"Очередь отправки переполнена. Дождитесь отправки записей и повторите попытку.";
        case ReasonCode::endpointInvalidated:
            return L"Устройство звука отключилось во время записи. Подключите его и повторите запись.";
        case ReasonCode::clockDiscontinuity:
            return L"Часы записи сбились. Проверьте системное время и повторите запись.";
        case ReasonCode::activeSessionExists:
            return L"Запись уже идёт. Остановите текущую запись перед новой.";
        default:
            break;
    }
    if (trustedPrefixRetained) {
        return L"Запись прервана. Подтверждённый фрагмент сохранён локально, но не отправлен. "
               L"Проверьте устройство перед новой записью.";
    }
    return L"Не удалось сохранить запись. Проверьте устройство и свободное место перед новой попыткой.";
}

} // namespace graf::windows
