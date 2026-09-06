#include "DesktopApiClient.h"

#include <cctype>
#include <set>

namespace graf::windows {
namespace {

// Only root fields are retained. Nested objects/arrays are validated and
// skipped, so policy/device fields cannot impersonate account authority.
class JsonReader final {
public:
    explicit JsonReader(std::string_view json) : json_(json) {}
    std::optional<std::map<std::string_view, std::string_view>> read() {
        if (json_.size() > 2 * 1024 * 1024 || !take('{') || !object(0)) return std::nullopt;
        whitespace();
        if (cursor_ != json_.size()) return std::nullopt;
        return fields_;
    }
    std::optional<std::vector<std::string_view>> readArray() {
        if (json_.size() > 2 * 1024 * 1024 || !take('[')) return std::nullopt;
        std::vector<std::string_view> values;
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
        return values;
    }

private:
    void whitespace() {
        while (cursor_ < json_.size() && std::string_view(" \r\n\t").find(json_[cursor_]) != std::string_view::npos) ++cursor_;
    }
    bool take(char c) {
        whitespace();
        if (cursor_ == json_.size() || json_[cursor_] != c) return false;
        ++cursor_;
        return true;
    }
    bool string() {
        if (!take('"')) return false;
        while (cursor_ < json_.size()) {
            const auto c = static_cast<unsigned char>(json_[cursor_++]);
            if (c < 0x20) return false;
            if (c == '"') return true;
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
        while (cursor_ < json_.size() && json_[cursor_] >= '0' && json_[cursor_] <= '9') ++cursor_;
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
        if (depth > 32) return false;
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
        std::set<std::string_view> keys;
        do {
            whitespace();
            const auto keyStart = cursor_;
            if (!string()) return false;
            const auto key = json_.substr(keyStart + 1, cursor_ - keyStart - 2);
            if (key.find('\\') != std::string_view::npos || !keys.insert(key).second) return false;
            if (!take(':')) return false;
            whitespace();
            const auto start = cursor_;
            if (!value(depth + 1)) return false;
            if (depth == 0) fields_.emplace(key, json_.substr(start, cursor_ - start));
        } while (take(','));
        return take('}');
    }

    std::string_view json_;
    std::size_t cursor_ = 0;
    std::map<std::string_view, std::string_view> fields_;
};

} // namespace

std::optional<std::map<std::string_view, std::string_view>> DesktopApiClient::jsonObjectFields(std::string_view json) {
    return JsonReader(json).read();
}

std::optional<std::vector<std::string_view>> DesktopApiClient::jsonArrayValues(std::string_view json) {
    return JsonReader(json).readArray();
}

bool DesktopApiClient::accountId(std::string_view value) noexcept {
    if (value.size() != 36 || value == "00000000-0000-0000-0000-000000000000") return false;
    for (std::size_t i = 0; i < value.size(); ++i) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (value[i] != '-') return false;
        } else if (!(value[i] >= '0' && value[i] <= '9') && !(value[i] >= 'a' && value[i] <= 'f')) return false;
    }
    return true;
}

std::optional<CreateMeetingRequest> DesktopApiClient::createMeetingRequest(
    std::string_view localRecordingId,
    std::string_view localMediaRevisionId,
    std::uint32_t durationSeconds) {
    if (!safeIdentity(localRecordingId) || !safeIdentity(localMediaRevisionId) || durationSeconds == 0) {
        return std::nullopt;
    }
    return CreateMeetingRequest{
        std::string(localRecordingId),
        std::string(localMediaRevisionId),
        std::string(kV5SourceKind),
        std::string(kV5MediaScribeSourceMode),
        durationSeconds,
    };
}

std::optional<UploadSessionRequest> DesktopApiClient::uploadSessionRequest(
    const std::array<std::uint64_t, 3>& expectedTrackSizes,
    std::string_view manifestSha256) {
    if (!sha256(manifestSha256)) {
        return std::nullopt;
    }
    return UploadSessionRequest{kV5WireRoles, expectedTrackSizes, std::string(manifestSha256)};
}

std::string DesktopApiClient::idempotencyKey(
    std::string_view scope,
    std::string_view directoryId,
    std::string_view sessionId) {
    if (!safeIdentity(scope) || !safeIdentity(directoryId) || !safeIdentity(sessionId)) {
        return {};
    }
    return "desktop-upload:" + std::string(scope) + ":" + std::string(directoryId) + ":" + std::string(sessionId);
}

bool DesktopApiClient::safeIdentity(std::string_view value) noexcept {
    if (value.empty() || value.size() > 300) {
        return false;
    }
    for (const unsigned char character : value) {
        if (!(std::isalnum(character) || character == '-' || character == '_')) {
            return false;
        }
    }
    return true;
}

bool DesktopApiClient::sha256(std::string_view value) noexcept {
    if (value.size() != 64) {
        return false;
    }
    for (const unsigned char character : value) {
        if (!std::isxdigit(character) || std::isupper(character)) {
            return false;
        }
    }
    return true;
}

} // namespace graf::windows
