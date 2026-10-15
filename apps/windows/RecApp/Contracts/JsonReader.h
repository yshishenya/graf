#pragma once

#include "JsonString.h"
#include <atomic>
#include <cctype>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <vector>

namespace graf::windows::json_detail {
struct ParseCancelled {};
inline void checkCancellation(const std::atomic<bool>* token) {
    if (token && token->load()) throw ParseCancelled{};
}
// Only root fields are retained. Nested objects/arrays are validated and
// skipped, so policy/device fields cannot impersonate account authority.
template<template<class> class Allocator = std::allocator, class String = std::string>
class JsonReader final {
public:
    using Fields = std::map<std::string_view, std::string_view, std::less<std::string_view>,
        Allocator<std::pair<const std::string_view, std::string_view>>>;
    using Values = std::vector<std::string_view, Allocator<std::string_view>>;
    using Keys = std::set<String, std::less<String>, Allocator<String>>;
    using RawKeys = std::set<std::string_view, std::less<std::string_view>, Allocator<std::string_view>>;
    explicit JsonReader(std::string_view json, unsigned maxDepth = 32, bool strictStrings = false,
        const std::atomic<bool>* cancellation = nullptr)
        : json_(json), maxDepth_(maxDepth), strictStrings_(strictStrings), cancellation_(cancellation),
          rootKeys_(std::less<String>{}, Allocator<String>{}),
          fields_(std::less<std::string_view>{}, Allocator<std::pair<const std::string_view, std::string_view>>{}) {}
    std::optional<Fields> read() {
        if (json_.size() > 2 * 1024 * 1024 || !take('{') || !object(0)) return std::nullopt;
        whitespace();
        if (cursor_ != json_.size()) return std::nullopt;
        return std::optional<Fields>{fields_};
    }
    std::optional<Values> readArray() {
        if (json_.size() > 2 * 1024 * 1024 || !take('[')) return std::nullopt;
        Values values(std::size_t{0});
        if (!take(']')) {
            do {
                whitespace();
                const auto start = cursor_;
                if (values.size() == 1024 || !value(1)) return std::nullopt;
                values.push_back(json_.substr(start, cursor_ - start));
            } while (take(','));
            if (!take(']')) return std::nullopt;
        }
        whitespace();
        if (cursor_ != json_.size()) return std::nullopt;
        return std::optional<Values>{values};
    }

private:
    std::optional<String> decodedString(std::string_view raw, std::size_t maxBytes, bool allowNul) {
        checkCancellation(cancellation_);
        String text;
        std::size_t emitted = 0;
        if (!decodeString(raw, maxBytes, allowNul, [&](char byte) {
            if ((emitted++ & 4095) == 0) checkCancellation(cancellation_);
            text += byte;
        })) return std::nullopt;
        return text;
    }
    void whitespace() {
        checkCancellation(cancellation_);
        while (cursor_ < json_.size() && std::string_view(" \r\n\t").find(json_[cursor_]) != std::string_view::npos) {
            ++cursor_;
            if ((cursor_ & 4095) == 0) checkCancellation(cancellation_);
        }
    }
    bool take(char c) {
        whitespace();
        if (cursor_ == json_.size() || json_[cursor_] != c) return false;
        ++cursor_;
        return true;
    }
    bool string() {
        if (!take('"')) return false;
        const auto start = cursor_ - 1;
        auto lastChecked = cursor_;
        while (cursor_ < json_.size()) {
            if (cursor_ - lastChecked >= 4096) {
                checkCancellation(cancellation_);
                lastChecked = cursor_;
            }
            const auto c = static_cast<unsigned char>(json_[cursor_++]);
            if (c < 0x20) return false;
            if (c == '"') {
                if (!strictStrings_) return true;
                std::size_t emitted = 0;
                return decodeString(json_.substr(start, cursor_ - start), json_.size(), true, [&](char) {
                    if ((emitted++ & 4095) == 0) checkCancellation(cancellation_);
                });
            }
            if (c != '\\') continue;
            if (cursor_ == json_.size()) return false;
            const auto escape = json_[cursor_++];
            if (escape == 'u') {
                for (int i = 0; i < 4; ++i) {
                    if (cursor_ == json_.size() || !std::isxdigit(static_cast<unsigned char>(json_[cursor_++]))) return false;
                }
            } else if (std::string_view("\"\\/bfnrt").find(escape) == std::string_view::npos) return false;
        }
        return false;
    }
    bool digits() {
        const auto start = cursor_;
        while (cursor_ < json_.size() && json_[cursor_] >= '0' && json_[cursor_] <= '9') {
            ++cursor_;
            if ((cursor_ & 4095) == 0) checkCancellation(cancellation_);
        }
        return cursor_ != start;
    }
    bool number() {
        if (cursor_ < json_.size() && json_[cursor_] == '-') ++cursor_;
        if (cursor_ == json_.size()) return false;
        if (json_[cursor_] == '0') ++cursor_;
        else if (!digits()) return false;
        if (cursor_ < json_.size() && json_[cursor_] == '.') {
            ++cursor_;
            if (!digits()) return false;
        }
        if (cursor_ < json_.size() && (json_[cursor_] == 'e' || json_[cursor_] == 'E')) {
            ++cursor_;
            if (cursor_ < json_.size() && (json_[cursor_] == '-' || json_[cursor_] == '+')) ++cursor_;
            if (!digits()) return false;
        }
        return true;
    }
    bool value(unsigned depth) {
        if (depth > maxDepth_) return false;
        whitespace();
        if (cursor_ == json_.size()) return false;
        if (json_[cursor_] == '"') return string();
        if (take('{')) return object(depth);
        if (take('[')) {
            if (take(']')) return true;
            do { if (!value(depth + 1)) return false; } while (take(','));
            return take(']');
        }
        for (const auto literal : {std::string_view("null"), std::string_view("true"), std::string_view("false")}) {
            if (json_.substr(cursor_, literal.size()) == literal) { cursor_ += literal.size(); return true; }
        }
        return number();
    }
    bool object(unsigned depth) {
        if (take('}')) return true;
        RawKeys keys(std::less<std::string_view>{}, Allocator<std::string_view>{});
        Keys decodedKeys(std::less<String>{}, Allocator<String>{});
        do {
            whitespace();
            const auto keyStart = cursor_;
            if (!string()) return false;
            auto key = json_.substr(keyStart + 1, cursor_ - keyStart - 2);
            if (strictStrings_) {
                auto decoded = decodedString(json_.substr(keyStart, cursor_ - keyStart), json_.size(), true);
                if (!decoded) return false;
                auto& ownedKeys = depth == 0 ? rootKeys_ : decodedKeys;
                const auto inserted = ownedKeys.insert(std::move(*decoded));
                if (!inserted.second) return false;
                key = *inserted.first;
            } else if (key.find('\\') != std::string_view::npos || !keys.insert(key).second) return false;
            if (!take(':')) return false;
            whitespace();
            const auto start = cursor_;
            if (!value(depth + 1)) return false;
            if (depth == 0) fields_.emplace(key, json_.substr(start, cursor_ - start));
        } while (take(','));
        return take('}');
    }

    std::string_view json_;
    unsigned maxDepth_;
    bool strictStrings_;
    const std::atomic<bool>* cancellation_;
    std::size_t cursor_ = 0;
    // Strict response key views remain valid until this reader is destroyed.
    Keys rootKeys_;
    Fields fields_;
};

} // namespace graf::windows::json_detail
