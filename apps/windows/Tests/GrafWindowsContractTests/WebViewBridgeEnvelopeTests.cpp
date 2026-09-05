#include "../../RecApp/Web/WebViewBridge.h"
#include "../../RecApp/Web/WebView2Host.h"
#include "../../RecApp/Contracts/WindowsDesktopContracts.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    using namespace graf::windows;
    WebViewBridge bridge("https://rec.2brain.pro");
    bridge.rotateNonce("nonce-1");
    WebViewBridgeEnvelope message{std::string(kBridgeProtocol), kBridgeProtocolVersion, 1, "nonce-1",
        "https://rec.2brain.pro", BridgeDirection::webToNative, "request_diagnostics", "{}", 1};
    assert(bridge.validate(message) == BridgeValidationError::none);
    assert(bridge.validate(message) == BridgeValidationError::replay);
    message.messageId = 2; message.command = "open_native_settings";
    assert(bridge.validate(message) == BridgeValidationError::none);
    message.messageId = 3; message.command = "capture_start";
    assert(bridge.validate(message) == BridgeValidationError::commandDenied);
    message.messageId = 4; message.command = "request_app_quit";
    assert(bridge.validate(message) == BridgeValidationError::none);
    assert(WebView2Host::isAllowedQuitPayload(R"({"action":"quit"})"));
    assert(!WebView2Host::isAllowedQuitPayload(R"({"action":"terminate"})"));
    message.messageId = 5; message.command = "request_diagnostics"; message.origin = "https://evil.example";
    assert(bridge.validate(message) == BridgeValidationError::wrongOrigin);
    message.messageId = 6; message.origin = "https://rec.2brain.pro"; message.payloadJson = std::string(65 * 1024, 'x');
    assert(bridge.validate(message) == BridgeValidationError::payloadTooLarge);
    message.messageId = 7; message.payloadJson = "not-json";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    message.messageId = 8; message.payloadJson = "{}{}";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    message.messageId = 9; message.payloadJson = "{";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    return 0;
}
