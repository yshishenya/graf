#pragma once

#include "../Contracts/WindowsDesktopContracts.h"
#include "WebView2Host.h"

#include <string>

namespace graf::windows {

struct WebRuntimeProjection {
    WebRuntimeState state = WebRuntimeState::unavailable;
    bool captureRemainsAvailable = true;
    ReasonCode reason = ReasonCode::webViewRuntimeUnavailable;
    std::string userMessage;
};

class WebRuntimeStateProjection final {
public:
    [[nodiscard]] static WebRuntimeProjection unavailable(ReasonCode reason = ReasonCode::webViewRuntimeUnavailable);
    [[nodiscard]] static WebRuntimeProjection ready();
    [[nodiscard]] static WebRuntimeProjection closed();
};

} // namespace graf::windows
