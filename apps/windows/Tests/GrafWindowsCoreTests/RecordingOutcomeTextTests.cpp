#include "../../RecApp/Shell/RecordingOutcomeText.h"

#include <array>
#include <string>

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>

namespace {

using graf::windows::ReasonCode;
using graf::windows::effectiveFailureReason;
using graf::windows::isMicrophoneOnlyReason;
using graf::windows::isRenderOnlyReason;
using graf::windows::recordingDegradedText;
using graf::windows::recordingFailureText;

bool contains(const std::wstring& text, const wchar_t* needle) {
    return text.find(needle) != std::wstring::npos;
}

// Каждый исход обязан называть следующий шаг: без него человек не знает, что
// делать, и сообщение превращается в отписку.
bool namesNextStep(const std::wstring& text) {
    // Слово-действие может стоять и в начале предложения: проверяем оба написания.
    const wchar_t* steps[] = {L"повторите", L"Повторите", L"выберите", L"Выберите",
                              L"проверьте", L"Проверьте", L"откройте", L"Откройте",
                              L"дождитесь", L"Дождитесь", L"подключите", L"Подключите",
                              L"перезапустите", L"Перезапустите", L"освободите", L"Освободите",
                              L"остановите", L"Остановите", L"разрешите", L"Разрешите",
                              L"закройте", L"Закройте"};
    for (const auto* step : steps) {
        if (contains(text, step)) return true;
    }
    return false;
}

void testEveryReasonIsExplained() {
    const std::array<ReasonCode, 16> reasons{
        ReasonCode::none,
        ReasonCode::activeSessionExists,
        ReasonCode::microphonePermissionDenied,
        ReasonCode::microphoneEndpointUnavailable,
        ReasonCode::renderEndpointUnavailable,
        ReasonCode::formatNormalizationUnavailable,
        ReasonCode::aecUnavailable,
        ReasonCode::storageUnavailable,
        ReasonCode::webViewRuntimeUnavailable,
        ReasonCode::aacEncoderUnavailable,
        ReasonCode::endpointInvalidated,
        ReasonCode::clockDiscontinuity,
        ReasonCode::queueOverflow,
        ReasonCode::finalizationFailed,
        ReasonCode::malformedLedger,
        ReasonCode::authRequired,
    };
    for (const auto reason : reasons) {
        for (const bool retained : {false, true}) {
            const auto text = recordingFailureText(reason, retained);
            assert(!text.empty());
            // Ни один исход не остаётся без следующего шага.
            assert(namesNextStep(text));
        }
    }
}

void testPermissionDenialPointsAtWindowsSettings() {
    const auto text = recordingFailureText(ReasonCode::microphonePermissionDenied, false);
    assert(contains(text, L"микрофон") || contains(text, L"Микрофон"));
    assert(contains(text, L"Разрешения Windows"));
    // Отказ в доступе — не проблема диска: иначе человек ищет причину не там.
    assert(!contains(text, L"места на диске"));
}

void testDeviceProblemsNameTheDevice() {
    assert(contains(recordingFailureText(ReasonCode::microphoneEndpointUnavailable, false), L"Микрофон недоступен"));
    assert(contains(recordingFailureText(ReasonCode::renderEndpointUnavailable, false), L"Системный звук"));
    assert(contains(recordingFailureText(ReasonCode::endpointInvalidated, false), L"отключилось"));
    assert(contains(recordingFailureText(ReasonCode::aacEncoderUnavailable, false), L"кодирование"));
    assert(contains(recordingFailureText(ReasonCode::storageUnavailable, false), L"место на диске"));
    assert(contains(recordingFailureText(ReasonCode::activeSessionExists, false), L"уже идёт"));
}

void testUnknownReasonKeepsTheOldCopy() {
    const auto generic = recordingFailureText(ReasonCode::none, false);
    assert(generic == L"Не удалось сохранить запись. Проверьте устройство и свободное место перед новой попыткой.");
    const auto retained = recordingFailureText(ReasonCode::finalizationFailed, true);
    assert(contains(retained, L"Подтверждённый фрагмент"));
    // Один и тот же код причины даёт разные тексты только по сохранённому фрагменту.
    assert(retained != recordingFailureText(ReasonCode::finalizationFailed, false));
    // Осмысленная причина важнее общего текста про фрагмент.
    assert(recordingFailureText(ReasonCode::storageUnavailable, true) ==
           recordingFailureText(ReasonCode::storageUnavailable, false));
}

void testDeniedPermissionWinsOverTheDeviceMechanism() {
    // Система отвечает на запрет как на отключённое устройство: без поправки
    // человек читает неверное объяснение и не находит разрешение.
    assert(effectiveFailureReason(ReasonCode::endpointInvalidated, false) == ReasonCode::microphonePermissionDenied);
    assert(effectiveFailureReason(ReasonCode::microphoneEndpointUnavailable, false) == ReasonCode::microphonePermissionDenied);
    // Когда разрешение есть, причина остаётся исходной.
    assert(effectiveFailureReason(ReasonCode::endpointInvalidated, true) == ReasonCode::endpointInvalidated);
    // Другие причины поправка не задевает: место и кодирование важнее.
    assert(effectiveFailureReason(ReasonCode::storageUnavailable, false) == ReasonCode::storageUnavailable);
    assert(effectiveFailureReason(ReasonCode::aacEncoderUnavailable, false) == ReasonCode::aacEncoderUnavailable);
    assert(effectiveFailureReason(ReasonCode::none, false) == ReasonCode::none);
    // Текст для этой причины указывает на разрешения Windows.
    assert(contains(recordingFailureText(effectiveFailureReason(ReasonCode::endpointInvalidated, false), false),
                    L"Разрешения Windows"));
}

void testDegradedRecordingIsExplained() {
    // Запись без микрофона сохранена: об этом нужно сказать прямо, иначе
    // человек узнает о пропаже голоса только на расшифровке.
    assert(isMicrophoneOnlyReason(ReasonCode::microphonePermissionDenied));
    assert(isMicrophoneOnlyReason(ReasonCode::microphoneEndpointUnavailable));
    assert(!isMicrophoneOnlyReason(ReasonCode::endpointInvalidated));
    assert(!isMicrophoneOnlyReason(ReasonCode::storageUnavailable));
    const auto denied = recordingDegradedText(ReasonCode::microphonePermissionDenied);
    assert(contains(denied, L"нет разрешения"));
    assert(contains(denied, L"системным звуком"));
    assert(contains(recordingDegradedText(ReasonCode::microphoneEndpointUnavailable), L"системным звуком"));
    // Ограничение — не отказ: текст не должен пугать потерей записи.
    assert(!contains(denied, L"Не удалось сохранить"));

    // Отказать может и системный звук: тогда запись остаётся с микрофоном, и
    // текст обязан назвать именно системный звук — иначе человек пойдёт чинить
    // микрофон.
    assert(isRenderOnlyReason(ReasonCode::renderEndpointUnavailable));
    assert(!isRenderOnlyReason(ReasonCode::microphoneEndpointUnavailable));
    assert(!isRenderOnlyReason(ReasonCode::endpointInvalidated));
    const auto render = recordingDegradedText(ReasonCode::renderEndpointUnavailable);
    assert(contains(render, L"Системный звук недоступен"));
    assert(contains(render, L"микрофоном"));
    assert(!contains(render, L"Не удалось сохранить"));
}

} // namespace

int main() {
    testEveryReasonIsExplained();
    testPermissionDenialPointsAtWindowsSettings();
    testDeviceProblemsNameTheDevice();
    testUnknownReasonKeepsTheOldCopy();
    testDeniedPermissionWinsOverTheDeviceMechanism();
    testDegradedRecordingIsExplained();
    std::printf("RecordingOutcomeTextTests: ok\n");
    return 0;
}
