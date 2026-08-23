#include "WebViewBridge.h"

#include "../Contracts/WindowsDesktopContracts.h"

#include <algorithm>

namespace graf::windows {

WebViewBridge::WebViewBridge(std::string trustedOrigin)
    : trustedOrigin_(std::move(trustedOrigin)) {}

void WebViewBridge::rotateNonce(std::string nonce) {
    nonce_ = std::move(nonce);
    lastMessageId_ = 0;
    valid_ = !nonce_.empty();
}

void WebViewBridge::invalidate() noexcept {
    valid_ = false;
    nonce_.clear();
    lastMessageId_ = 0;
}

BridgeValidationError WebViewBridge::validate(const WebViewBridgeEnvelope& message) noexcept {
    if (!valid_) return BridgeValidationError::staleNonce;
    if (message.protocol != kBridgeProtocol) return BridgeValidationError::wrongProtocol;
    if (message.version != kBridgeProtocolVersion) return BridgeValidationError::wrongVersion;
    if (message.origin != trustedOrigin_) return BridgeValidationError::wrongOrigin;
    if (message.nonce != nonce_) return BridgeValidationError::staleNonce;
    if (message.messageId == 0 || message.messageId <= lastMessageId_) return BridgeValidationError::replay;
    if (message.command.empty() || message.payloadJson.size() > kBridgeMaxSerializedBytes) return BridgeValidationError::payloadTooLarge;
    if (!jsonShapeValid(message.payloadJson)) return BridgeValidationError::malformedEnvelope;
    if (jsonDepth(message.payloadJson) > kBridgeMaxPayloadDepth) return BridgeValidationError::payloadTooDeep;
    if (message.direction == BridgeDirection::webToNative && !isAllowedWebCommand(message.command)) {
        return BridgeValidationError::commandDenied;
    }
    lastMessageId_ = message.messageId;
    return BridgeValidationError::none;
}

bool WebViewBridge::isAllowedWebCommand(std::string_view command) noexcept {
    return command == "request_native_settings" || command == "request_diagnostics" ||
           command == "request_runtime_repair" || command == "ack_display";
}

std::size_t WebViewBridge::jsonDepth(std::string_view payload) noexcept {
    std::size_t depth = 0, maximum = 0;
    bool quoted = false, escaped = false;
    for (const char character : payload) {
        if (escaped) { escaped = false; continue; }
        if (character == '\\' && quoted) { escaped = true; continue; }
        if (character == '"') { quoted = !quoted; continue; }
        if (quoted) continue;
        if (character == '{' || character == '[') maximum = std::max(maximum, ++depth);
        else if ((character == '}' || character == ']') && depth > 0) --depth;
    }
    return maximum;
}

bool WebViewBridge::jsonShapeValid(std::string_view payload) noexcept {
    std::size_t depth = 0;
    bool quoted = false, escaped = false;
    for (const char character : payload) {
        if (escaped) { escaped = false; continue; }
        if (character == '\\' && quoted) { escaped = true; continue; }
        if (character == '"') { quoted = !quoted; continue; }
        if (quoted) continue;
        if (character == '{' || character == '[') ++depth;
        else if (character == '}' || character == ']') {
            if (depth == 0) return false;
            --depth;
        }
    }
    return !quoted && !escaped && depth == 0;
}

bool WebViewBridge::containsForbiddenCommand(std::string_view command) noexcept {
    return command.find("capture") != std::string_view::npos || command.find("file") != std::string_view::npos ||
           command.find("token") != std::string_view::npos || command.find("cookie") != std::string_view::npos ||
           command.find("process") != std::string_view::npos;
}

} // namespace graf::windows
