#pragma once

#include "WebViewRoutePolicy.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

namespace graf::windows {

enum class BridgeDirection {
    webToNative,
    nativeToWeb,
};

enum class BridgeValidationError {
    none,
    wrongProtocol,
    wrongVersion,
    wrongOrigin,
    staleNonce,
    replay,
    malformedEnvelope,
    payloadTooLarge,
    payloadTooDeep,
    commandDenied,
};

struct WebViewBridgeEnvelope {
    std::string protocol;
    std::uint32_t version = 0;
    std::uint64_t messageId = 0;
    std::string nonce;
    std::string origin;
    BridgeDirection direction = BridgeDirection::webToNative;
    std::string command;
    std::string payloadJson;
    std::uint64_t sentAtMonotonicMs = 0;
};

class WebViewBridge final {
public:
    explicit WebViewBridge(std::string trustedOrigin);

    void rotateNonce(std::string nonce);
    void invalidate() noexcept;
    [[nodiscard]] BridgeValidationError validate(const WebViewBridgeEnvelope& message) noexcept;
    [[nodiscard]] bool isAllowedWebCommand(std::string_view command) noexcept;
    [[nodiscard]] std::uint64_t lastMessageId() const noexcept { return lastMessageId_; }

private:
    [[nodiscard]] static std::size_t jsonDepth(std::string_view payload) noexcept;
    [[nodiscard]] static bool jsonShapeValid(std::string_view payload) noexcept;

    std::string trustedOrigin_;
    std::string nonce_;
    std::uint64_t lastMessageId_ = 0;
    bool valid_ = false;
};

} // namespace graf::windows
