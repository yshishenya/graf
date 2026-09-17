#include "DesktopApiClient.h"

#include "../Storage/Sha256.h"

#include <cctype>
#include <cstdio>
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

std::string DesktopApiClient::formatDisplayMinute(std::uint64_t epochMs, int displayTimezoneOffsetMinutes) noexcept {
    if (epochMs == 0) return {};
    if (displayTimezoneOffsetMinutes < -14 * 60 || displayTimezoneOffsetMinutes > 14 * 60) return {};
    const auto shiftedMs = static_cast<long long>(epochMs) +
        static_cast<long long>(displayTimezoneOffsetMinutes) * 60'000LL;
    if (shiftedMs < 0) return {};
    const auto totalMinutes = static_cast<long long>(shiftedMs / 60'000LL);
    const auto days = totalMinutes / 1440LL;
    const auto minuteOfDay = totalMinutes % 1440LL;
    // Civil date from a day count, so the label depends only on the instant and
    // the offset, never on the locale or time zone of the machine reading it.
    const auto shiftedDays = days + 719468LL;
    const auto era = (shiftedDays >= 0 ? shiftedDays : shiftedDays - 146096LL) / 146097LL;
    const auto dayOfEra = static_cast<unsigned long long>(shiftedDays - era * 146097LL);
    const auto yearOfEra = (dayOfEra - dayOfEra / 1460ULL + dayOfEra / 36524ULL - dayOfEra / 146096ULL) / 365ULL;
    const auto year = static_cast<long long>(yearOfEra) + era * 400LL;
    const auto dayOfYear = dayOfEra - (365ULL * yearOfEra + yearOfEra / 4ULL - yearOfEra / 100ULL);
    const auto monthPrime = (5ULL * dayOfYear + 2ULL) / 153ULL;
    const auto day = dayOfYear - (153ULL * monthPrime + 2ULL) / 5ULL + 1ULL;
    const auto month = monthPrime < 10ULL ? monthPrime + 3ULL : monthPrime - 9ULL;
    const auto civilYear = year + (month <= 2ULL ? 1LL : 0LL);
    if (civilYear < 1970 || civilYear > 9999) return {};
    char buffer[24] = {};
    std::snprintf(buffer, sizeof(buffer), "%04lld-%02llu-%02llu %02lld:%02lld", civilYear, month, day,
                  minuteOfDay / 60LL, minuteOfDay % 60LL);
    return std::string(buffer);
}

std::string DesktopApiClient::formatUtcInstant(std::uint64_t epochMs) noexcept {
    if (epochMs == 0) return {};
    const auto totalSeconds = static_cast<long long>(epochMs / 1000ULL);
    const auto days = totalSeconds / 86400LL;
    const auto secondOfDay = totalSeconds % 86400LL;
    const auto shiftedDays = days + 719468LL;
    const auto era = (shiftedDays >= 0 ? shiftedDays : shiftedDays - 146096LL) / 146097LL;
    const auto dayOfEra = static_cast<unsigned long long>(shiftedDays - era * 146097LL);
    const auto yearOfEra = (dayOfEra - dayOfEra / 1460ULL + dayOfEra / 36524ULL - dayOfEra / 146096ULL) / 365ULL;
    const auto year = static_cast<long long>(yearOfEra) + era * 400LL;
    const auto dayOfYear = dayOfEra - (365ULL * yearOfEra + yearOfEra / 4ULL - yearOfEra / 100ULL);
    const auto monthPrime = (5ULL * dayOfYear + 2ULL) / 153ULL;
    const auto day = dayOfYear - (153ULL * monthPrime + 2ULL) / 5ULL + 1ULL;
    const auto month = monthPrime < 10ULL ? monthPrime + 3ULL : monthPrime - 9ULL;
    const auto civilYear = year + (month <= 2ULL ? 1LL : 0LL);
    if (civilYear < 1970 || civilYear > 9999) return {};
    char buffer[24] = {};
    std::snprintf(buffer, sizeof(buffer), "%04lld-%02llu-%02lluT%02lld:%02lld:%02lldZ", civilYear, month, day,
                  secondOfDay / 3600LL, (secondOfDay % 3600LL) / 60LL, secondOfDay % 60LL);
    return std::string(buffer);
}

std::string DesktopApiClient::createMeetingBody(const CreateMeetingRequest& request) {
    const auto escape = [](std::string_view value) {
        std::string escaped;
        escaped.reserve(value.size());
        for (const char character : value) {
            switch (character) {
            case '\\': escaped += "\\\\"; break;
            case '"': escaped += "\\\""; break;
            case '\n': escaped += "\\n"; break;
            case '\r': escaped += "\\r"; break;
            case '\t': escaped += "\\t"; break;
            default: escaped += character; break;
            }
        }
        return escaped;
    };
    auto body = std::string("{\"local_recording_id\":\"") + escape(request.localRecordingId) +
        "\",\"local_media_revision_id\":\"" + escape(request.localMediaRevisionId) +
        "\",\"source_kind\":\"" + escape(request.sourceKind) +
        "\",\"media_scribe_source_mode\":\"" + escape(request.mediaScribeSourceMode) +
        "\",\"duration_seconds\":" + std::to_string(request.durationSeconds);
    // The timeline is sent only when the package could support it: the server
    // stores what it is given, and a guessed instant is worse than a missing one.
    if (request.hasTimeline() && !request.title.empty() && !request.titleSource.empty()) {
        body += ",\"title\":\"" + escape(request.title) +
            "\",\"title_source\":\"" + escape(request.titleSource) +
            "\",\"started_at\":\"" + escape(request.startedAtIso) +
            "\",\"ended_at\":\"" + escape(request.endedAtIso) +
            "\",\"recording_display_timezone_offset_minutes\":" +
            std::to_string(request.displayTimezoneOffsetMinutes);
    }
    body += "}";
    return body;
}

std::optional<CreateMeetingRequest> DesktopApiClient::createMeetingRequest(
    std::string_view localRecordingId,
    std::string_view localMediaRevisionId,
    std::uint32_t durationSeconds,
    std::uint64_t startedAtMs,
    std::uint64_t stoppedAtMs,
    int displayTimezoneOffsetMinutes) {
    if (!safeIdentity(localRecordingId) || !safeIdentity(localMediaRevisionId) || durationSeconds == 0) {
        return std::nullopt;
    }
    CreateMeetingRequest request;
    request.localRecordingId = std::string(localRecordingId);
    request.localMediaRevisionId = std::string(localMediaRevisionId);
    request.sourceKind = std::string(kV5SourceKind);
    request.mediaScribeSourceMode = std::string(kV5MediaScribeSourceMode);
    request.durationSeconds = durationSeconds;
    // A package without usable bounds is still uploaded; it simply carries no
    // timeline, exactly as before these fields existed.
    if (startedAtMs != 0 && stoppedAtMs >= startedAtMs) {
        const auto label = formatDisplayMinute(startedAtMs, displayTimezoneOffsetMinutes);
        const auto startedAt = formatUtcInstant(startedAtMs);
        const auto endedAt = formatUtcInstant(stoppedAtMs);
        if (!label.empty() && !startedAt.empty() && !endedAt.empty()) {
            request.startedAtIso = startedAt;
            request.endedAtIso = endedAt;
            request.displayTimezoneOffsetMinutes = displayTimezoneOffsetMinutes;
            request.title = "Meeting - " + label;
            request.titleSource = "generic";
        }
    }
    return request;
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

namespace {

// A JSON string value borrowed from jsonObjectFields, unquoted and unescaped.
// An escape sequence is refused instead of decoded: every field this protocol
// reads is an identifier or a server-controlled enum, and a value that needed
// escaping is not one of them.
std::optional<std::string_view> plainString(std::string_view value) noexcept {
    if (value.size() < 2 || value.front() != '"' || value.back() != '"') return std::nullopt;
    value.remove_prefix(1);
    value.remove_suffix(1);
    for (const char character : value) {
        if (character == '\\' || static_cast<unsigned char>(character) < 0x20) return std::nullopt;
    }
    return value;
}

// A JSON integer, accepted only in the canonical form the server serializes:
// no sign, no exponent, no fraction, no leading zero.
std::optional<long long> plainInteger(std::string_view value) noexcept {
    if (value.empty() || value.size() > 18) return std::nullopt;
    long long number = 0;
    for (const char character : value) {
        if (character < '0' || character > '9') return std::nullopt;
        number = number * 10 + (character - '0');
    }
    if (value.size() > 1 && value.front() == '0') return std::nullopt;
    return number;
}

std::string escapeJson(std::string_view value) {
    std::string escaped;
    escaped.reserve(value.size());
    for (const char character : value) {
        switch (character) {
        case '\\': escaped += "\\\\"; break;
        case '"': escaped += "\\\""; break;
        case '\n': escaped += "\\n"; break;
        case '\r': escaped += "\\r"; break;
        case '\t': escaped += "\\t"; break;
        default: escaped += character; break;
        }
    }
    return escaped;
}

// The instant the server serializes for a purge task, in the one shape its own
// encoder produces: date, time, optional fraction, then 'Z' or an offset. The
// client keeps the string as sent, so this only refuses values that are not an
// instant at all.
bool validServerInstant(std::string_view value) noexcept {
    if (value.size() < 20 || value.size() > 40) return false;
    const auto digit = [&](std::size_t index) {
        return value[index] >= '0' && value[index] <= '9';
    };
    for (const std::size_t index : {0U, 1U, 2U, 3U, 5U, 6U, 8U, 9U, 11U, 12U, 14U, 15U, 17U, 18U}) {
        if (!digit(index)) return false;
    }
    if (value[4] != '-' || value[7] != '-' || value[10] != 'T' || value[13] != ':' || value[16] != ':') return false;
    std::size_t cursor = 19;
    if (value[cursor] == '.') {
        ++cursor;
        const auto start = cursor;
        while (cursor < value.size() && digit(cursor)) ++cursor;
        if (cursor == start || cursor - start > 9) return false;
    }
    if (cursor >= value.size()) return false;
    if (value[cursor] == 'Z') return cursor + 1 == value.size();
    if (value[cursor] != '+' && value[cursor] != '-') return false;
    if (cursor + 6 != value.size()) return false;
    return digit(cursor + 1) && digit(cursor + 2) && value[cursor + 3] == ':' &&
        digit(cursor + 4) && digit(cursor + 5);
}

std::optional<LocalPurgeTask> purgeTaskFromFields(
    const std::map<std::string_view, std::string_view>& fields) {
    const auto taskId = fields.find("task_id");
    const auto meetingId = fields.find("meeting_id");
    const auto taskType = fields.find("task_type");
    const auto state = fields.find("state");
    const auto expiresAt = fields.find("expires_at");
    if (taskId == fields.end() || meetingId == fields.end() || taskType == fields.end() ||
        state == fields.end() || expiresAt == fields.end()) return std::nullopt;
    const auto id = plainString(taskId->second);
    const auto meeting = plainString(meetingId->second);
    const auto type = plainString(taskType->second);
    const auto phase = plainString(state->second);
    const auto expiry = plainString(expiresAt->second);
    if (!id || !meeting || !type || !phase || !expiry) return std::nullopt;
    if (!DesktopApiClient::accountId(*id) || !DesktopApiClient::accountId(*meeting)) return std::nullopt;
    if (!validServerInstant(*expiry)) return std::nullopt;
    // Only the task types and states the server can produce. An unknown value is
    // not work this client may carry out or answer for.
    const bool knownType = *type == "purge_local_buffers" || *type == "purge_local_exports" ||
        *type == "confirm_local_expiry";
    const bool knownState = *phase == "pending" || *phase == "claimed" || *phase == "acknowledged" ||
        *phase == "failed" || *phase == "unreachable" || *phase == "expired" ||
        *phase == "local_expiry_relied_upon";
    if (!knownType || !knownState) return std::nullopt;
    LocalPurgeTask task;
    task.taskId = std::string(*id);
    task.meetingId = std::string(*meeting);
    task.taskType = std::string(*type);
    task.state = std::string(*phase);
    task.expiresAt = std::string(*expiry);
    const auto safeReason = fields.find("safe_reason");
    if (safeReason != fields.end() && safeReason->second != "null") {
        const auto reason = plainString(safeReason->second);
        if (!reason || reason->size() > 120) return std::nullopt;
        task.safeReason = std::string(*reason);
    }
    return task;
}

} // namespace

std::string DesktopApiClient::ownOriginDeletionPath(std::string_view directoryId) {
    if (!safeIdentity(directoryId)) return {};
    return std::string(desktopRecordingPrefix) + std::string(directoryId) + std::string(ownOriginDeletionSuffix);
}

std::string DesktopApiClient::meetingDeletionPath(std::string_view meetingId) {
    // A meeting is addressed by UUID, and the server parses that path segment as
    // one. A shorter or differently shaped value would be answered 422 and must
    // never reach the wire as if it identified a meeting.
    if (!accountId(meetingId)) return {};
    return std::string(cabinetMeetingPrefix) + std::string(meetingId) + std::string(ownOriginDeletionSuffix);
}

std::optional<NotificationContext> DesktopApiClient::decodeNotificationContext(std::string_view json) {
    const auto fields = jsonObjectFields(json);
    if (!fields) return std::nullopt;
    const auto user = fields->find("user_id");
    const auto workspace = fields->find("workspace_id");
    const auto version = fields->find("recording_deletion_protocol_version");
    if (user == fields->end() || workspace == fields->end() || version == fields->end()) return std::nullopt;
    const auto userId = plainString(user->second);
    const auto workspaceId = plainString(workspace->second);
    const auto protocolVersion = plainInteger(version->second);
    if (!userId || !workspaceId || !protocolVersion) return std::nullopt;
    if (!accountId(*userId) || !accountId(*workspaceId)) return std::nullopt;
    if (*protocolVersion < 0 || *protocolVersion > 1000) return std::nullopt;
    NotificationContext context;
    context.userId = std::string(*userId);
    context.workspaceId = std::string(*workspaceId);
    context.protocolVersion = static_cast<int>(*protocolVersion);
    return context;
}

std::optional<std::vector<LifecycleEntry>> DesktopApiClient::decodeLifecycleEntries(std::string_view json) {
    const auto values = jsonArrayValues(json);
    if (!values || values->size() > 100) return std::nullopt;
    std::vector<LifecycleEntry> entries;
    entries.reserve(values->size());
    for (const auto value : *values) {
        const auto fields = jsonObjectFields(value);
        if (!fields) return std::nullopt;
        const auto targetType = fields->find("target_type");
        const auto targetId = fields->find("target_id");
        const auto state = fields->find("state");
        if (targetType == fields->end() || targetId == fields->end() || state == fields->end()) return std::nullopt;
        const auto type = plainString(targetType->second);
        const auto id = plainString(targetId->second);
        const auto name = plainString(state->second);
        if (!type || !id || !name || id->empty() || id->size() > 300) return std::nullopt;
        LifecycleEntry entry;
        if (*type == "own_origin") {
            entry.target = DeletionTarget::ownOrigin;
            if (!safeIdentity(*id)) return std::nullopt;
        } else if (*type == "meeting") {
            entry.target = DeletionTarget::meeting;
            if (!accountId(*id)) return std::nullopt;
        } else {
            // A target this client cannot name is not a target it may act on.
            return std::nullopt;
        }
        if (*name == "allowed") {
            entry.state = LifecycleState::allowed;
        } else if (*name == "deletion_accepted") {
            entry.state = LifecycleState::deletionAccepted;
        } else if (*name == "canceled_before_creation") {
            entry.state = LifecycleState::canceledBeforeCreation;
        } else if (*name == "unavailable") {
            entry.state = LifecycleState::unavailable;
        } else {
            return std::nullopt;
        }
        const auto meetingId = fields->find("meeting_id");
        // Absent and null both mean "not linked to a meeting"; a present value
        // has to be a meeting identity or the entry is not trustworthy.
        if (meetingId != fields->end() && meetingId->second != "null") {
            const auto linked = plainString(meetingId->second);
            if (!linked || !accountId(*linked)) return std::nullopt;
            entry.meetingId = std::string(*linked);
        }
        entry.targetId = std::string(*id);
        entries.push_back(std::move(entry));
    }
    return entries;
}

std::optional<DeletionReceipt> DesktopApiClient::decodeDeletionReceipt(std::string_view json) {
    const auto fields = jsonObjectFields(json);
    if (!fields) return std::nullopt;
    const auto type = fields->find("receipt_type");
    const auto requestId = fields->find("request_id");
    const auto phase = fields->find("phase");
    if (type == fields->end() || requestId == fields->end() || phase == fields->end()) return std::nullopt;
    const auto receiptType = plainString(type->second);
    const auto request = plainString(requestId->second);
    const auto state = plainString(phase->second);
    if (!receiptType || !request || !state) return std::nullopt;
    if (!accountId(*request)) return std::nullopt;
    DeletionReceipt receipt;
    receipt.receiptType = std::string(*receiptType);
    receipt.requestId = std::string(*request);
    if (*state != "accepted") return std::nullopt;
    receipt.phase = std::string(*state);
    // The server counts its own deletion attempts; macOS refuses a receipt that
    // reports a negative one, because such a receipt describes no deletion.
    const auto epoch = fields->find("deletion_epoch");
    if (epoch != fields->end() && epoch->second != "null" && !epoch->second.empty() &&
        epoch->second.front() == '-') {
        return std::nullopt;
    }
    // Both identifiers are read for both shapes. A cancellation of a local copy
    // may also name the meeting the server created for it, and that answer is what
    // tells the queue which meeting this recording became.
    const auto meetingId = fields->find("meeting_id");
    if (meetingId != fields->end() && meetingId->second != "null") {
        const auto id = plainString(meetingId->second);
        if (!id || !accountId(*id)) return std::nullopt;
        receipt.meetingId = std::string(*id);
    }
    const auto localId = fields->find("local_recording_id");
    if (localId != fields->end() && localId->second != "null") {
        const auto id = plainString(localId->second);
        if (!id || !safeIdentity(*id)) return std::nullopt;
        receipt.localRecordingId = std::string(*id);
    }
    if (*receiptType == "origin_cancellation") {
        // A cancellation has to name the copy it cancelled.
        if (receipt.localRecordingId.empty()) return std::nullopt;
        return receipt;
    }
    if (*receiptType == "meeting_deletion") {
        // A meeting deletion has to name the meeting it deleted.
        if (receipt.meetingId.empty()) return std::nullopt;
        return receipt;
    }
    // An unknown receipt shape is not a confirmation.
    return std::nullopt;
}

std::string DesktopApiClient::originCancellationBody(std::string_view operationId) {
    // The server validates operation_id as a UUID and the confirmation sentence
    // as one exact literal; a request that sends anything else is refused.
    if (!accountId(operationId)) return {};
    return std::string("{\"operation_id\":\"") + std::string(operationId) +
        "\",\"confirmation_boundary\":\"" + std::string(deletionConfirmationBoundary) + "\"}";
}

std::string DesktopApiClient::meetingDeletionBody() {
    return std::string("{\"confirmation_boundary\":\"") + std::string(deletionConfirmationBoundary) + "\"}";
}

std::string DesktopApiClient::lifecycleBody(const std::vector<std::string>& origins,
                                            const std::vector<std::string>& meetingIds) {
    std::string body = "{\"origins\":[";
    for (std::size_t index = 0; index < origins.size(); ++index) {
        if (index != 0) body += ',';
        body += "\"" + escapeJson(origins[index]) + "\"";
    }
    body += "],\"meeting_ids\":[";
    for (std::size_t index = 0; index < meetingIds.size(); ++index) {
        if (index != 0) body += ',';
        body += "\"" + escapeJson(meetingIds[index]) + "\"";
    }
    return body + "]}";
}

bool DesktopApiClient::validLifecycleSelection(const std::vector<std::string>& origins,
                                               const std::vector<std::string>& meetingIds,
                                               std::size_t maxEntries) noexcept {
    if (origins.size() + meetingIds.size() < 1 || origins.size() + meetingIds.size() > maxEntries) return false;
    for (const auto& origin : origins) {
        if (!safeIdentity(origin)) return false;
    }
    for (const auto& meetingId : meetingIds) {
        if (!accountId(meetingId)) return false;
    }
    return true;
}

std::vector<std::pair<std::string, std::string>> DesktopApiClient::scopedAccountHeaders(
    const DeletionScope& scope) {
    // The server compares this pair with the confirmed session before it changes
    // anything, and macOS sends exactly the same two headers.
    if (!accountId(scope.userId) || !accountId(scope.workspaceId)) return {};
    return {{"X-Graf-Expected-Actor", scope.userId}, {"X-Graf-Expected-Workspace", scope.workspaceId}};
}

std::string DesktopApiClient::deletionOperationId(const DeletionScope& scope, DeletionTarget target,
                                                 std::string_view targetId) {
    if (!accountId(scope.userId) || !accountId(scope.workspaceId)) return {};
    const bool ownOrigin = target == DeletionTarget::ownOrigin;
    if (ownOrigin ? !safeIdentity(targetId) : !accountId(targetId)) return {};
    // The origin is deliberately not part of the name: the same recording on the
    // same account is the same deletion even if the app is pointed at another
    // server later, and the request itself still goes only to the configured one.
    // Qualified on purpose: the class has a private `sha256` predicate, and an
    // unqualified call would silently resolve to it instead of the digest.
    const auto digest = graf::windows::sha256(std::string("graf-deletion-operation\n") + (ownOrigin ? "own_origin\n" : "meeting\n") +
        scope.userId + "\n" + scope.workspaceId + "\n" + std::string(targetId));
    if (digest.size() != 64) return {};
    // Version and variant bits are set so the value is a UUID in the shape the
    // endpoint validates. The remaining nibbles come from the digest.
    std::string id;
    id.reserve(36);
    for (std::size_t index = 0; index < 32; ++index) {
        if (index == 8 || index == 12 || index == 16 || index == 20) id += '-';
        char digit = digest[index];
        if (index == 12) digit = '4';
        if (index == 16) digit = "89ab"[(digest[index] >= '0' && digest[index] <= '9')
            ? (digest[index] - '0') % 4 : (digest[index] - 'a') % 4];
        id += digit;
    }
    return id;
}

std::string DesktopApiClient::localPurgeTaskPath(std::string_view meetingId) {
    // Purge tasks live under the device-facing desktop prefix, while a meeting
    // deletion request is a cabinet route. Mixing them would address an endpoint
    // that does not exist.
    if (!accountId(meetingId)) return {};
    return std::string(desktopMeetingPrefix) + std::string(meetingId) + std::string(purgeTaskSuffix);
}

std::string DesktopApiClient::localPurgeAckPath(std::string_view taskId) {
    if (!accountId(taskId)) return {};
    return std::string(purgeTasksPath) + "/" + std::string(taskId) + std::string(purgeAckSuffix);
}

std::optional<LocalPurgeTask> DesktopApiClient::decodeLocalPurgeTask(std::string_view json) {
    const auto fields = jsonObjectFields(json);
    if (!fields) return std::nullopt;
    return purgeTaskFromFields(*fields);
}

std::optional<std::vector<LocalPurgeTask>> DesktopApiClient::decodeLocalPurgeTaskList(std::string_view json) {
    const auto fields = jsonObjectFields(json);
    if (!fields) return std::nullopt;
    const auto tasks = fields->find("tasks");
    if (tasks == fields->end()) return std::nullopt;
    const auto values = jsonArrayValues(tasks->second);
    if (!values || values->size() > purgeTaskListLimit) return std::nullopt;
    std::vector<LocalPurgeTask> decoded;
    decoded.reserve(values->size());
    for (const auto value : *values) {
        const auto entry = jsonObjectFields(value);
        if (!entry) return std::nullopt;
        auto task = purgeTaskFromFields(*entry);
        // One unusable task rejects the answer: acting on a partial list would
        // leave the device answering for a purge it never saw.
        if (!task) return std::nullopt;
        decoded.push_back(std::move(*task));
    }
    return decoded;
}

std::string_view DesktopApiClient::localPurgeAckStateName(LocalPurgeAckState state) noexcept {
    switch (state) {
    case LocalPurgeAckState::acknowledged: return "acknowledged";
    case LocalPurgeAckState::failed: return "failed";
    case LocalPurgeAckState::localExpiryReliedUpon: return "local_expiry_relied_upon";
    }
    return {};
}

bool DesktopApiClient::validAckReasonCode(std::string_view reasonCode) noexcept {
    // The client only sends codes it owns, and the server bounds the length.
    if (reasonCode.empty() || reasonCode.size() > purgeReasonCodeLimit) return false;
    for (const unsigned char character : reasonCode) {
        if (!(std::islower(character) || std::isdigit(character) || character == '_')) return false;
    }
    return true;
}

std::string DesktopApiClient::localPurgeAckBody(LocalPurgeAckState state, std::string_view reasonCode,
                                               std::string_view clientVersion,
                                               std::string_view completedAtIso) {
    const auto name = localPurgeAckStateName(state);
    if (name.empty() || !validAckReasonCode(reasonCode)) return {};
    if (!completedAtIso.empty() && !validServerInstant(completedAtIso)) return {};
    if (clientVersion.size() > 80) return {};
    std::string body = "{\"state\":\"" + std::string(name) + "\",\"reason_code\":\"" +
        escapeJson(reasonCode) + "\"";
    if (!clientVersion.empty()) body += ",\"client_version\":\"" + escapeJson(clientVersion) + "\"";
    if (!completedAtIso.empty()) body += ",\"completed_at\":\"" + escapeJson(completedAtIso) + "\"";
    return body + "}";
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
