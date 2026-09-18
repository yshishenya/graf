#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <string>

namespace graf::windows {

// Текст исхода неудачной записи по коду причины. Пользователь должен понимать,
// что именно случилось: нет доступа к микрофону, недоступно устройство, мало
// места или не удалось завершить файл. Без этого любая неудача выглядит как
// «проверьте устройство и место», и человек ищет причину не там.
[[nodiscard]] std::wstring recordingFailureText(ReasonCode reason, bool trustedPrefixRetained);

// Отказ в доступе к микрофону важнее механизма отказа. Когда система не даёт
// доступ, звуковое устройство отвечает как отключённое, и без этой поправки
// человек читает «устройство отключилось» вместо «нет разрешения» — и ищет
// причину не там. Другие причины (место, кодирование) поправка не задевает.
[[nodiscard]] ReasonCode effectiveFailureReason(ReasonCode reason, bool microphonePermissionGranted) noexcept;

// Причина ограничена микрофоном: запись продолжается системным звуком.
[[nodiscard]] bool isMicrophoneOnlyReason(ReasonCode reason) noexcept;

// Что человеку сказать про ограниченную запись: она сохранена, но без голоса.
[[nodiscard]] std::wstring recordingDegradedText(ReasonCode reason);

} // namespace graf::windows
