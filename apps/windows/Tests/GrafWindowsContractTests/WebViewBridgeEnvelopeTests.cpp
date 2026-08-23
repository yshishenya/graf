#include "../../RecApp/Web/WebViewBridge.h"
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
    message.messageId = 2; message.command = "capture_start";
    assert(bridge.validate(message) == BridgeValidationError::commandDenied);
    message.messageId = 3; message.command = "request_diagnostics"; message.origin = "https://evil.example";
    assert(bridge.validate(message) == BridgeValidationError::wrongOrigin);
    message.messageId = 4; message.origin = "https://rec.2brain.pro"; message.payloadJson = std::string(65 * 1024, 'x');
    assert(bridge.validate(message) == BridgeValidationError::payloadTooLarge);
    message.messageId = 5; message.payloadJson = "not-json";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    message.messageId = 6; message.payloadJson = "{}{}";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    message.messageId = 7; message.payloadJson = "{";
    assert(bridge.validate(message) == BridgeValidationError::malformedEnvelope);
    return 0;
}
