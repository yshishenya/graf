#include "WebViewBridge.h"

#include "../Contracts/WindowsDesktopContracts.h"

#include <algorithm>
#include <cctype>

namespace graf::windows {
namespace {

class JsonValidator final {
public:
    explicit JsonValidator(std::string_view input) : input_(input) {}

    [[nodiscard]] bool parse() noexcept {
        skipWhitespace();
        if (!parseValue(0)) return false;
        skipWhitespace();
        return cursor_ == input_.size();
    }

private:
    void skipWhitespace() noexcept {
        while (cursor_ < input_.size() && std::isspace(static_cast<unsigned char>(input_[cursor_]))) ++cursor_;
    }

    [[nodiscard]] bool parseValue(std::size_t depth) noexcept {
        if (depth > 64) return false;
        skipWhitespace();
        if (cursor_ >= input_.size()) return false;
        switch (input_[cursor_]) {
        case '{': return parseObject(depth + 1);
        case '[': return parseArray(depth + 1);
        case '"': return parseString();
        case 't': return parseLiteral("true");
        case 'f': return parseLiteral("false");
        case 'n': return parseLiteral("null");
        default: return parseNumber();
        }
    }

    [[nodiscard]] bool parseObject(std::size_t depth) noexcept {
        ++cursor_;
        skipWhitespace();
        if (cursor_ < input_.size() && input_[cursor_] == '}') { ++cursor_; return true; }
        while (cursor_ < input_.size()) {
            if (!parseString()) return false;
            skipWhitespace();
            if (cursor_ >= input_.size() || input_[cursor_] != ':') return false;
            ++cursor_;
            if (!parseValue(depth)) return false;
            skipWhitespace();
            if (cursor_ >= input_.size()) return false;
            if (input_[cursor_] == '}') { ++cursor_; return true; }
            if (input_[cursor_] != ',') return false;
            ++cursor_;
            skipWhitespace();
        }
        return false;
    }

    [[nodiscard]] bool parseArray(std::size_t depth) noexcept {
        ++cursor_;
        skipWhitespace();
        if (cursor_ < input_.size() && input_[cursor_] == ']') { ++cursor_; return true; }
        while (cursor_ < input_.size()) {
            if (!parseValue(depth)) return false;
            skipWhitespace();
            if (cursor_ >= input_.size()) return false;
            if (input_[cursor_] == ']') { ++cursor_; return true; }
            if (input_[cursor_] != ',') return false;
            ++cursor_;
            skipWhitespace();
        }
        return false;
    }

    [[nodiscard]] bool parseString() noexcept {
        if (cursor_ >= input_.size() || input_[cursor_] != '"') return false;
        ++cursor_;
        while (cursor_ < input_.size()) {
            const auto character = static_cast<unsigned char>(input_[cursor_++]);
            if (character < 0x20) return false;
            if (character == '"') return true;
            if (character != '\\') continue;
            if (cursor_ >= input_.size()) return false;
            const auto escaped = input_[cursor_++];
            if (escaped == 'u') {
                if (input_.size() - cursor_ < 4) return false;
                for (std::size_t index = 0; index < 4; ++index) {
                    if (!std::isxdigit(static_cast<unsigned char>(input_[cursor_++]))) return false;
                }
            } else if (escaped != '"' && escaped != '\\' && escaped != '/' && escaped != 'b' &&
                       escaped != 'f' && escaped != 'n' && escaped != 'r' && escaped != 't') {
                return false;
            }
        }
        return false;
    }

    [[nodiscard]] bool parseLiteral(std::string_view literal) noexcept {
        if (input_.substr(cursor_, literal.size()) != literal) return false;
        cursor_ += literal.size();
        return true;
    }

    [[nodiscard]] bool parseNumber() noexcept {
        const auto start = cursor_;
        if (cursor_ < input_.size() && input_[cursor_] == '-') ++cursor_;
        if (cursor_ >= input_.size()) return false;
        if (input_[cursor_] == '0') {
            ++cursor_;
        } else {
            if (input_[cursor_] < '1' || input_[cursor_] > '9') return false;
            while (cursor_ < input_.size() && std::isdigit(static_cast<unsigned char>(input_[cursor_]))) ++cursor_;
        }
        if (cursor_ < input_.size() && input_[cursor_] == '.') {
            ++cursor_;
            const auto fraction = cursor_;
            while (cursor_ < input_.size() && std::isdigit(static_cast<unsigned char>(input_[cursor_]))) ++cursor_;
            if (fraction == cursor_) return false;
        }
        if (cursor_ < input_.size() && (input_[cursor_] == 'e' || input_[cursor_] == 'E')) {
            ++cursor_;
            if (cursor_ < input_.size() && (input_[cursor_] == '+' || input_[cursor_] == '-')) ++cursor_;
            const auto exponent = cursor_;
            while (cursor_ < input_.size() && std::isdigit(static_cast<unsigned char>(input_[cursor_]))) ++cursor_;
            if (exponent == cursor_) return false;
        }
        return cursor_ != start;
    }

    std::string_view input_;
    std::size_t cursor_ = 0;
};

} // namespace

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
    return !payload.empty() && JsonValidator(payload).parse();
}

} // namespace graf::windows
