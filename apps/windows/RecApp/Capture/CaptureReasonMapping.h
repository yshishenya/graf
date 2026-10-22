#pragma once

#include "../Audio/WasapiCaptureWorker.h"
#include "../Contracts/WindowsDesktopContracts.h"

namespace graf::windows {

// Код причины для человека выводится из ошибки устройства и источника звука.
// Отказ в доступе к микрофону и недоступное устройство требуют разных действий,
// поэтому источник входит в решение.
[[nodiscard]] ReasonCode reasonForWorkerError(CaptureWorkerError error, bool microphoneSource) noexcept;

} // namespace graf::windows
