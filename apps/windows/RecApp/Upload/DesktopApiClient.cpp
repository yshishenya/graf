#include "DesktopApiClient.h"
#include "DesktopHttpTransport.h"

#include "../Storage/Sha256.h"
#include "../Contracts/JsonString.h"
#include "../Contracts/JsonReader.h"

#include <cctype>
#include <charconv>
#include <cstdio>
#include <set>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <memory>

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#endif

namespace graf::windows {
namespace {

std::optional<std::string> calendarString(
    std::string_view raw, std::size_t maxRawBytes = 16384, bool allowNul = false);

using JsonReader = json_detail::JsonReader<>;
template<class String> using ProtocolJsonReader = std::conditional_t<std::is_same_v<String, CustodyString>,
    json_detail::JsonReader<CustodyAllocator, String>, json_detail::JsonReader<std::allocator, String>>;

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

template<class String>
String DesktopApiClient::formatDisplayMinute(std::uint64_t epochMs, int displayTimezoneOffsetMinutes) noexcept(std::is_same_v<String, std::string>) {
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
    return String(buffer);
}

template<class String>
String DesktopApiClient::formatUtcInstant(std::uint64_t epochMs) noexcept(std::is_same_v<String, std::string>) {
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
    return String(buffer);
}

template<class String>
String DesktopApiClient::createMeetingBody(const BasicCreateMeetingRequest<String>& request) {
    const auto escape = [](String& body, std::string_view value) {
        for (const char character : value) {
            switch (character) {
            case '\\': body += "\\\\"; break;
            case '"': body += "\\\""; break;
            case '\n': body += "\\n"; break;
            case '\r': body += "\\r"; break;
            case '\t': body += "\\t"; break;
            default: body += character; break;
            }
        }
    };
    const auto number = [](String& body, auto value) {
        char digits[24];
        const auto end = std::to_chars(std::begin(digits), std::end(digits), value);
        body.append(digits, static_cast<std::size_t>(end.ptr - digits));
    };
    String body("{\"local_recording_id\":\"");
    escape(body, request.localRecordingId);
    body += "\",\"local_media_revision_id\":\""; escape(body, request.localMediaRevisionId);
    body += "\",\"source_kind\":\""; escape(body, request.sourceKind);
    body += "\",\"media_scribe_source_mode\":\""; escape(body, request.mediaScribeSourceMode);
    body += "\",\"duration_seconds\":"; number(body, request.durationSeconds);
    // The timeline is sent only when the package could support it: the server
    // stores what it is given, and a guessed instant is worse than a missing one.
    if (request.hasTimeline() && !request.title.empty() && !request.titleSource.empty()) {
        body += ",\"title\":\""; escape(body, request.title);
        body += "\",\"title_source\":\""; escape(body, request.titleSource);
        body += "\",\"started_at\":\""; escape(body, request.startedAtIso);
        body += "\",\"ended_at\":\""; escape(body, request.endedAtIso);
        body += "\",\"recording_display_timezone_offset_minutes\":";
        number(body, request.displayTimezoneOffsetMinutes);
    }
    body += "}";
    return body;
}

template<class String>
std::optional<BasicCreateMeetingRequest<String>> DesktopApiClient::createMeetingRequest(
    std::string_view localRecordingId,
    std::string_view localMediaRevisionId,
    std::uint32_t durationSeconds,
    std::uint64_t startedAtMs,
    std::uint64_t stoppedAtMs,
    int displayTimezoneOffsetMinutes) {
    if (!safeIdentity(localRecordingId) || !safeIdentity(localMediaRevisionId) || durationSeconds == 0) {
        return std::nullopt;
    }
    BasicCreateMeetingRequest<String> request;
    request.localRecordingId.assign(localRecordingId.data(), localRecordingId.size());
    request.localMediaRevisionId.assign(localMediaRevisionId.data(), localMediaRevisionId.size());
    request.sourceKind.assign(kV5SourceKind.data(), kV5SourceKind.size());
    request.mediaScribeSourceMode.assign(kV5MediaScribeSourceMode.data(), kV5MediaScribeSourceMode.size());
    request.durationSeconds = durationSeconds;
    // A package without usable bounds is still uploaded; it simply carries no
    // timeline, exactly as before these fields existed.
    if (startedAtMs != 0 && stoppedAtMs >= startedAtMs) {
        const auto label = formatDisplayMinute<String>(startedAtMs, displayTimezoneOffsetMinutes);
        const auto startedAt = formatUtcInstant<String>(startedAtMs);
        const auto endedAt = formatUtcInstant<String>(stoppedAtMs);
        if (!label.empty() && !startedAt.empty() && !endedAt.empty()) {
            request.startedAtIso = startedAt;
            request.endedAtIso = endedAt;
            request.displayTimezoneOffsetMinutes = displayTimezoneOffsetMinutes;
            request.title = "Meeting - "; request.title += label;
            request.titleSource = "generic";
        }
    }
    return request;
}

template<class String>
std::optional<BasicUploadSessionRequest<String>> DesktopApiClient::uploadSessionRequest(
    const std::array<std::uint64_t, 3>& expectedTrackSizes,
    std::string_view manifestSha256) {
    if (!sha256(manifestSha256)) {
        return std::nullopt;
    }
    return BasicUploadSessionRequest<String>{kV5WireRoles, expectedTrackSizes, String(manifestSha256)};
}

template<class String>
String DesktopApiClient::idempotencyKey(
    std::string_view scope,
    std::string_view directoryId,
    std::string_view sessionId) {
    if (!safeIdentity(scope) || !safeIdentity(directoryId) || !safeIdentity(sessionId)) {
        return {};
    }
    String key("desktop-upload:");
    key.append(scope.data(), scope.size()); key += ':';
    key.append(directoryId.data(), directoryId.size()); key += ':';
    key.append(sessionId.data(), sessionId.size());
    return key;
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

template<class String = std::string> String escapeJson(std::string_view value) {
    String escaped;
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

template<class String>
std::optional<BasicLocalPurgeTask<String>> purgeTaskFromFields(
    const typename ProtocolJsonReader<String>::Fields& fields) {
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
    BasicLocalPurgeTask<String> task;
    task.taskId = *id;
    task.meetingId = *meeting;
    task.taskType = *type;
    task.state = *phase;
    task.expiresAt = *expiry;
    const auto safeReason = fields.find("safe_reason");
    if (safeReason != fields.end() && safeReason->second != "null") {
        const auto reason = plainString(safeReason->second);
        if (!reason || reason->size() > 120) return std::nullopt;
        task.safeReason = *reason;
    }
    return task;
}

} // namespace

template<class String> String DesktopApiClient::ownOriginDeletionPath(std::string_view directoryId) {
    if (!safeIdentity(directoryId)) return {};
    String path(desktopRecordingPrefix); path += directoryId; path += ownOriginDeletionSuffix; return path;
}

template<class String> String DesktopApiClient::meetingDeletionPath(std::string_view meetingId) {
    // A meeting is addressed by UUID, and the server parses that path segment as
    // one. A shorter or differently shaped value would be answered 422 and must
    // never reach the wire as if it identified a meeting.
    if (!accountId(meetingId)) return {};
    String path(cabinetMeetingPrefix); path += meetingId; path += ownOriginDeletionSuffix; return path;
}

namespace {
// Calendar strings may contain JSON Unicode escapes. Upload decoding is unchanged.
std::optional<std::string> calendarString(std::string_view raw, std::size_t maxRawBytes, bool allowNul) {
    std::string result;
    if (!json_detail::decodeString(raw, maxRawBytes, allowNul, [&](char byte) { result += byte; })) return std::nullopt;
    return result;
}

std::optional<std::string> calendarEventId(std::string_view raw) {
    if (raw.size() != 36) return std::nullopt;
    std::string id(raw);
    for (auto& c : id) if (c >= 'A' && c <= 'F') c = static_cast<char>(c + ('a' - 'A'));
    // Calendar IDs are UUID syntax, not account authority (which excludes nil).
    if (!DesktopApiClient::accountId(id) && id != "00000000-0000-0000-0000-000000000000") return std::nullopt;
    return id;
}

std::optional<double> calendarInstant(std::string_view raw) {
    const auto text = calendarString(raw);
    if (!text || text->size() < 20 || text->size() > 40) return std::nullopt;
    const auto& s = *text;
    const auto number = [&](std::size_t pos, std::size_t count) -> int {
        int result = 0;
        for (std::size_t i = pos; i < pos + count; ++i) {
            if (s[i] < '0' || s[i] > '9') return -1;
            result = result * 10 + s[i] - '0';
        }
        return result;
    };
    if (s[4] != '-' || s[7] != '-' || s[10] != 'T' || s[13] != ':' || s[16] != ':') return std::nullopt;
    const int y = number(0, 4), m = number(5, 2), d = number(8, 2);
    const int h = number(11, 2), minute = number(14, 2), second = number(17, 2);
    if (y < 1970 || m < 1 || m > 12 || h < 0 || h > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) return std::nullopt;
    const int days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    const int maxDay = days[m - 1] + (m == 2 && y % 4 == 0 && (y % 100 != 0 || y % 400 == 0) ? 1 : 0);
    if (d < 1 || d > maxDay) return std::nullopt;
    std::size_t i = 19; double fraction = 0;
    if (s[i] == '.') {
        double place = 0.1; const auto first = ++i;
        while (i < s.size() && s[i] >= '0' && s[i] <= '9') { fraction += (s[i++] - '0') * place; place *= 0.1; }
        if (i == first || i - first > 9) return std::nullopt;
    }
    int offset = 0;
    if (i < s.size() && s[i] == 'Z' && i + 1 == s.size()) {}
    else if (i + 6 == s.size() && (s[i] == '+' || s[i] == '-') && s[i + 3] == ':') {
        const auto oh = number(i + 1, 2), om = number(i + 4, 2);
        if (oh < 0 || oh > 14 || om < 0 || om > 59 || (oh == 14 && om != 0)) return std::nullopt;
        offset = (oh * 60 + om) * (s[i] == '+' ? 1 : -1);
    } else return std::nullopt;
    const auto year = y - (m <= 2 ? 1 : 0);
    const auto era = year / 400, yoe = year - era * 400;
    const auto doy = (153 * (m > 2 ? m - 3 : m + 9) + 2) / 5 + d - 1;
    const auto dayCount = era * 146097LL + yoe * 365 + yoe / 4 - yoe / 100 + doy - 719468;
    return static_cast<double>(dayCount * 86400 + h * 3600 + minute * 60 + second - offset * 60) + fraction;
}
}

std::string DesktopApiClient::calendarJoinTargetPath(std::string_view eventId) {
    const auto id = calendarEventId(eventId);
    return id ? "/api/v1/calendar/events/" + *id + "/join-target" : std::string{};
}

std::optional<CalendarJoinTarget> DesktopApiClient::decodeCalendarJoinTarget(
    std::string_view json, std::string_view expectedEventId) {
    const auto expected = calendarEventId(expectedEventId);
    if (!expected || json.size() > 65536) return std::nullopt;
    JsonReader reader(json, 8, true);
    const auto fields = reader.read();
    if (!fields) return std::nullopt;
    const auto field = [&](std::string_view key) -> std::optional<std::string> {
        const auto it = fields->find(key);
        return it == fields->end() ? std::nullopt : calendarString(it->second, 65536);
    };
    const auto idText = field("event_id"), family = field("provider_family"), url = field("https_url");
    const auto id = idText ? calendarEventId(*idText) : std::nullopt;
    if (!id || *id != *expected || !family || family->size() > 64 || !url || url->size() > 8192) return std::nullopt;
    return CalendarJoinTarget{*id, *family, *url};
}

std::optional<CalendarJoinIntent> DesktopApiClient::decodeCalendarJoinIntent(
    std::string_view payload, std::string_view command) {
    const bool join = command == "calendar_join";
    if ((!join && command != "calendar_join_cancel") || payload.size() > kBridgeMaxSerializedBytes)
        return std::nullopt;
    JsonReader reader(payload, kBridgeMaxPayloadDepth, true);
    const auto fields = reader.read();
    if (!fields || fields->size() != (join ? 3U : 2U)) return std::nullopt;
    const auto text = [&](std::string_view key) -> std::optional<std::string> {
        const auto it = fields->find(key);
        return it == fields->end() ? std::nullopt : calendarString(it->second, kBridgeMaxSerializedBytes);
    };
    if (join && text("action") != "joinCalendarEvent") return std::nullopt;
    const auto eventText = text("eventId"), requestText = text("requestId");
    const auto event = eventText ? calendarEventId(*eventText) : std::nullopt;
    const auto request = requestText ? calendarEventId(*requestText) : std::nullopt;
    if (!event || !request) return std::nullopt;
    return CalendarJoinIntent{*event, *request};
}

std::optional<UserTimeMetadata> DesktopApiClient::decodeUserTimeMetadata(std::string_view json) {
    if (json.size() > 2048) return std::nullopt;
    JsonReader reader(json, 1, true);
    const auto fields = reader.read();
    if (!fields || fields->size() != 5) return std::nullopt;
    const auto text = [&](std::string_view key) -> std::optional<std::string> {
        const auto it = fields->find(key);
        return it == fields->end() ? std::nullopt : calendarString(it->second, 2048);
    };
    const auto user = text("userId"), workspace = text("workspaceId"), session = text("sessionId"),
        zone = text("timeZone"), url = text("documentURL");
    if (!user || !workspace || !session || !zone || !url ||
        !accountId(*user) || !accountId(*workspace) || !accountId(*session) ||
        zone->size() > 100 || url->empty() || url->size() > 1024) return std::nullopt;
    if ((!zone->empty() && *zone != "UTC" && zone->find('/') == std::string::npos) ||
        std::any_of(zone->begin(), zone->end(), [](unsigned char c) { return c <= 0x20 || c >= 0x7f; }) ||
        std::any_of(url->begin(), url->end(), [](unsigned char c) { return c <= 0x20 || c == 0x7f; }))
        return std::nullopt;
    return UserTimeMetadata{*user, *workspace, *session, *zone, *url};
}

std::optional<std::string> DesktopApiClient::calendarJoinEnvelopePayload(
    std::string_view json, std::string_view command) {
    if ((command != "calendar_join" && command != "calendar_join_cancel") ||
        json.size() > kBridgeMaxSerializedBytes) return std::nullopt;
    // Envelope contributes a root level; payload limits are checked separately.
    JsonReader reader(json, kBridgeMaxPayloadDepth + 1, true);
    const auto fields = reader.read();
    if (!fields) return std::nullopt;
    const auto rawCommand = fields->find("command"), payload = fields->find("payload");
    if (rawCommand == fields->end() || payload == fields->end() ||
        calendarString(rawCommand->second, kBridgeMaxSerializedBytes) != command ||
        !decodeCalendarJoinIntent(payload->second, command)) return std::nullopt;
    return std::string(payload->second);
}

std::optional<CalendarReminderSnapshot> DesktopApiClient::decodeCalendarReminders(std::string_view json) {
    if (json.size() > 1024 * 1024) return std::nullopt;
    const auto root = jsonObjectFields(json); if (!root) return std::nullopt;
    const auto field = [](const auto& fields, std::string_view key) -> std::string_view {
        auto it = fields.find(key); return it == fields.end() ? std::string_view{} : it->second;
    };
    const auto owner = calendarString(field(*root, "notification_owner_id"));
    const auto workspace = calendarString(field(*root, "notification_workspace_id"));
    const auto events = jsonArrayValues(field(*root, "events"));
    if (!owner || !workspace || !accountId(*owner) || !accountId(*workspace) || !events || events->size() > 50) return std::nullopt;
    const auto presentationBoolean = [](std::string_view raw, bool defaultValue) -> std::optional<bool> {
        if (raw.empty() || raw == "null") return defaultValue;
        if (raw == "true") return true;
        if (raw == "false") return false;
        return std::nullopt;
    };
    const auto showTime = presentationBoolean(field(*root, "show_upcoming_time"), true);
    const auto showTitle = presentationBoolean(field(*root, "show_upcoming_title"), true);
    if (!showTime || !showTitle) return std::nullopt;
    CalendarReminderSnapshot result{*owner, *workspace, {}};
    result.showUpcomingTime = *showTime;
    result.showUpcomingTitle = *showTitle;
    std::set<std::string> ids;
    for (const auto raw : *events) {
        const auto fields = jsonObjectFields(raw); if (!fields) return std::nullopt;
        auto id = calendarString(field(*fields, "event_id"));
        auto start = calendarInstant(field(*fields, "starts_at")), end = calendarInstant(field(*fields, "ends_at"));
        auto state = calendarString(field(*fields, "join_prompt_state"));
        auto titleState = calendarString(field(*fields, "title_state"));
        auto link = field(*fields, "meeting_link_present");
        if (!id || !accountId(*id) || !ids.insert(*id).second || !start || !end || *end <= *start ||
            !state || !titleState || (link != "true" && link != "false")) return std::nullopt;
        CalendarReminderEvent event{*id, *start, *end, *state == "not_due" || *state == "shown", *titleState == "available", "", link == "true", ""};
        const auto allDay = presentationBoolean(field(*fields, "all_day"), false);
        if (!allDay) return std::nullopt;
        event.allDay = *allDay;
        auto title = field(*fields, "title");
        if (!title.empty() && title != "null") {
            auto decoded = calendarString(title); if (!decoded || decoded->size() > 4096) return std::nullopt;
            if (event.titleAvailable) event.title = std::move(*decoded);
        }
        auto url = field(*fields, "open_meeting_url");
        if (!url.empty() && url != "null") {
            auto decoded = calendarString(url); if (!decoded || decoded->size() > 4096) return std::nullopt;
            event.meetingUrl = std::move(*decoded);
        }
        result.events.push_back(std::move(event));
    }
    return result;
}

void CalendarReminderResponse::inheritAuthExpiry(std::optional<std::int64_t> contextExpiry) {
    if (status == 401 || status == 403) { authExpiresAt.reset(); return; }
    if (!authExpiresAt) authExpiresAt = contextExpiry;
}

std::optional<std::int64_t> CalendarReminderResponse::renewedSessionExpiry(std::int64_t now) const {
    if (status == 401 || status == 403 || !authExpiresAt || *authExpiresAt <= 0 || *authExpiresAt <= now) return std::nullopt;
    return authExpiresAt;
}

std::optional<std::int64_t> DesktopApiClient::calendarAuthExpiryFromHeader(std::string_view raw) {
    if (raw.empty() || raw.size() > 19 || raw.front() < '0' || raw.front() > '9') return std::nullopt;
    std::int64_t value = 0;
    const auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != raw.data() + raw.size()) return std::nullopt;
    return value;
}

CalendarReminderResponse DesktopApiClient::calendarReminders(const DesktopHttpConfig& config) {
    CalendarReminderResponse result;
#ifdef _WIN32
    const auto cancelled = [&] { return config.cancellation && config.cancellation->load(); };
    if (cancelled() || !config.confirmedIdentity || !accountId(config.confirmedIdentity->userId) ||
        !accountId(config.workspaceId) || config.confirmedIdentity->workspaceId != config.workspaceId ||
        config.sessionToken.empty() || config.sessionToken.size() > 4096) return result;
    for (const auto c : config.sessionToken) if (static_cast<unsigned char>(c) < 0x21 || static_cast<unsigned char>(c) > 0x7e) return result;
    // Configuration is native-owned; userinfo/path/query/fragment cannot become
    // an alternative authenticated destination. The request path is constant.
    if (config.baseOrigin.size() > 2048 || config.baseOrigin.find_first_of("\r\n\t @?#") != std::string::npos) return result;
    const auto scheme = config.baseOrigin.find("://");
    if (scheme == std::string::npos || config.baseOrigin.find('/', scheme + 3) != std::string::npos) return result;
    const std::wstring origin(config.baseOrigin.begin(), config.baseOrigin.end());
    URL_COMPONENTS components{}; components.dwStructSize = sizeof(components);
    components.dwSchemeLength = static_cast<DWORD>(-1); components.dwHostNameLength = static_cast<DWORD>(-1);
    if (!WinHttpCrackUrl(origin.c_str(), 0, 0, &components) || components.nScheme != INTERNET_SCHEME_HTTPS || !components.dwHostNameLength) return result;
    using Handle = std::unique_ptr<void, decltype(&WinHttpCloseHandle)>;
    Handle session(WinHttpOpen(L"GRAF/Feature200", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0), WinHttpCloseHandle);
    if (!session || !WinHttpSetTimeouts(session.get(), 5000, 5000, 5000, 5000)) return result;
    const std::wstring host(components.lpszHostName, components.dwHostNameLength);
    Handle connection(WinHttpConnect(session.get(), host.c_str(), components.nPort, 0), WinHttpCloseHandle);
    if (!connection) return result;
    const std::wstring path(calendarUpcomingPath.begin(), calendarUpcomingPath.end());
    Handle request(WinHttpOpenRequest(connection.get(), L"GET", path.c_str(), nullptr, WINHTTP_NO_REFERER,
                                      WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE), WinHttpCloseHandle);
    if (!request) return result;
    DWORD disabled = WINHTTP_DISABLE_REDIRECTS | WINHTTP_DISABLE_COOKIES;
    if (!WinHttpSetOption(request.get(), WINHTTP_OPTION_DISABLE_FEATURE, &disabled, sizeof(disabled))) return result;
    const std::string headers = "Accept: application/json\r\nX-Auth-Session: " + config.sessionToken +
        "\r\nX-Workspace-Id: " + config.workspaceId + "\r\nX-Graf-Expected-Actor: " + config.confirmedIdentity->userId +
        "\r\nX-Graf-Expected-Workspace: " + config.workspaceId + "\r\n";
    const std::wstring wide(headers.begin(), headers.end());
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(15);
    if (cancelled() || !WinHttpSendRequest(request.get(), wide.c_str(), static_cast<DWORD>(wide.size()),
        WINHTTP_NO_REQUEST_DATA, 0, 0, 0) || cancelled() || !WinHttpReceiveResponse(request.get(), nullptr)) return result;
    DWORD status = 0, bytes = sizeof(status);
    if (!WinHttpQueryHeaders(request.get(), WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
        WINHTTP_HEADER_NAME_BY_INDEX, &status, &bytes, WINHTTP_NO_HEADER_INDEX)) return result;
    result.status = status;
    // Fixed-size header read: at most 19 ASCII digits plus the terminator.
    wchar_t expiry[20]{}; DWORD expiryBytes = sizeof(expiry);
    if (WinHttpQueryHeaders(request.get(), WINHTTP_QUERY_CUSTOM, L"X-GRAF-Auth-Expires-At",
        expiry, &expiryBytes, WINHTTP_NO_HEADER_INDEX)) {
        std::string raw;
        for (const auto c : expiry) {
            if (!c) break;
            if (c < L'0' || c > L'9') { raw.clear(); break; }
            raw += static_cast<char>(c);
        }
        result.authExpiresAt = calendarAuthExpiryFromHeader(raw);
    }
    if (status != 200) return result;
    std::string body;
    for (;;) {
        if (cancelled() || std::chrono::steady_clock::now() >= deadline) return result;
        char buffer[8192]; DWORD read = 0;
        if (!WinHttpReadData(request.get(), buffer, sizeof(buffer), &read)) return result;
        if (!read) break;
        if (body.size() + read > 1024 * 1024) return result;
        body.append(buffer, read);
    }
    if (!cancelled()) result.snapshot = decodeCalendarReminders(body);
#else
    (void)config;
#endif
    return result;
}

template<class String>
std::optional<BasicNotificationContext<String>> DesktopApiClient::decodeNotificationContext(
    std::string_view json, const std::atomic<bool>* cancellation) {
    json_detail::checkCancellation(cancellation);
    const auto fields = ProtocolJsonReader<String>(json, 32, false, cancellation).read();
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
    BasicNotificationContext<String> context;
    context.userId = *userId;
    context.workspaceId = *workspaceId;
    context.protocolVersion = static_cast<int>(*protocolVersion);
    json_detail::checkCancellation(cancellation);
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

template<class String>
std::optional<BasicDeletionReceipt<String>> DesktopApiClient::decodeDeletionReceipt(
    std::string_view json, const std::atomic<bool>* cancellation) {
    json_detail::checkCancellation(cancellation);
    const auto fields = ProtocolJsonReader<String>(json, 32, false, cancellation).read();
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
    BasicDeletionReceipt<String> receipt;
    receipt.receiptType = *receiptType;
    receipt.requestId = *request;
    if (*state != "accepted") return std::nullopt;
    receipt.phase = *state;
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
        receipt.meetingId = *id;
    }
    const auto localId = fields->find("local_recording_id");
    if (localId != fields->end() && localId->second != "null") {
        const auto id = plainString(localId->second);
        if (!id || !safeIdentity(*id)) return std::nullopt;
        receipt.localRecordingId = *id;
    }
    json_detail::checkCancellation(cancellation);
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

template<class String> String DesktopApiClient::originCancellationBody(std::string_view operationId) {
    // The server validates operation_id as a UUID and the confirmation sentence
    // as one exact literal; a request that sends anything else is refused.
    if (!accountId(operationId)) return {};
    String body("{\"operation_id\":\""); body += operationId;
    body += "\",\"confirmation_boundary\":\""; body += deletionConfirmationBoundary; body += "\"}"; return body;
}

template<class String> String DesktopApiClient::meetingDeletionBody() {
    String body("{\"confirmation_boundary\":\""); body += deletionConfirmationBoundary; body += "\"}"; return body;
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

template<class String>
std::optional<std::array<std::pair<std::string_view, std::string_view>, 2>> DesktopApiClient::scopedAccountHeaders(
    const BasicDeletionScope<String>& scope) {
    // The server compares this pair with the confirmed session before it changes
    // anything, and macOS sends exactly the same two headers.
    if (!accountId(scope.userId) || !accountId(scope.workspaceId)) return {};
    return std::array<std::pair<std::string_view, std::string_view>, 2>{{
        {"X-Graf-Expected-Actor", scope.userId}, {"X-Graf-Expected-Workspace", scope.workspaceId}}};
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

template<class String> String DesktopApiClient::localPurgeTaskPath(std::string_view meetingId) {
    // Purge tasks live under the device-facing desktop prefix, while a meeting
    // deletion request is a cabinet route. Mixing them would address an endpoint
    // that does not exist.
    if (!accountId(meetingId)) return {};
    String path(desktopMeetingPrefix); path += meetingId; path += purgeTaskSuffix; return path;
}

template<class String> String DesktopApiClient::localPurgeAckPath(std::string_view taskId) {
    if (!accountId(taskId)) return {};
    String path(purgeTasksPath); path += '/'; path += taskId; path += purgeAckSuffix; return path;
}

template<class String>
std::optional<BasicLocalPurgeTask<String>> DesktopApiClient::decodeLocalPurgeTask(
    std::string_view json, const std::atomic<bool>* cancellation) {
    json_detail::checkCancellation(cancellation);
    const auto fields = ProtocolJsonReader<String>(json, 32, false, cancellation).read();
    if (!fields) return std::nullopt;
    auto task = purgeTaskFromFields<String>(*fields);
    json_detail::checkCancellation(cancellation);
    return task;
}

template<class String>
std::optional<BasicLocalPurgeTasks<String>> DesktopApiClient::decodeLocalPurgeTaskList(
    std::string_view json, const std::atomic<bool>* cancellation) {
    json_detail::checkCancellation(cancellation);
    const auto fields = ProtocolJsonReader<String>(json, 32, false, cancellation).read();
    if (!fields) return std::nullopt;
    const auto tasks = fields->find("tasks");
    if (tasks == fields->end()) return std::nullopt;
    const auto values = ProtocolJsonReader<String>(tasks->second, 32, false, cancellation).readArray();
    if (!values || values->size() > purgeTaskListLimit) return std::nullopt;
    BasicLocalPurgeTasks<String> decoded;
    decoded.reserve(values->size());
    for (const auto value : *values) {
        auto task = decodeLocalPurgeTask<String>(value, cancellation);
        // One unusable task rejects the answer: acting on a partial list would
        // leave the device answering for a purge it never saw.
        if (!task) return std::nullopt;
        decoded.push_back(std::move(*task));
    }
    json_detail::checkCancellation(cancellation);
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

template<class String> String DesktopApiClient::localPurgeAckBody(LocalPurgeAckState state, std::string_view reasonCode,
                                               std::string_view clientVersion,
                                               std::string_view completedAtIso) {
    const auto name = localPurgeAckStateName(state);
    if (name.empty() || !validAckReasonCode(reasonCode)) return {};
    if (!completedAtIso.empty() && !validServerInstant(completedAtIso)) return {};
    if (clientVersion.size() > 80) return {};
    String body("{\"state\":\""); body += name; body += "\",\"reason_code\":\"";
    body += escapeJson<String>(reasonCode); body += '"';
    if (!clientVersion.empty()) { body += ",\"client_version\":\""; body += escapeJson<String>(clientVersion); body += '"'; }
    if (!completedAtIso.empty()) { body += ",\"completed_at\":\""; body += escapeJson<String>(completedAtIso); body += '"'; }
    body += '}'; return body;
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

// Both representations share one serializer and validation algorithm.
template std::optional<BasicCreateMeetingRequest<std::string>> DesktopApiClient::createMeetingRequest<std::string>(std::string_view, std::string_view, std::uint32_t, std::uint64_t, std::uint64_t, int);
template std::optional<BasicCreateMeetingRequest<CustodyString>> DesktopApiClient::createMeetingRequest<CustodyString>(std::string_view, std::string_view, std::uint32_t, std::uint64_t, std::uint64_t, int);
template std::string DesktopApiClient::formatDisplayMinute<std::string>(std::uint64_t, int) noexcept;
template CustodyString DesktopApiClient::formatDisplayMinute<CustodyString>(std::uint64_t, int);
template std::string DesktopApiClient::formatUtcInstant<std::string>(std::uint64_t) noexcept;
template CustodyString DesktopApiClient::formatUtcInstant<CustodyString>(std::uint64_t);
template std::string DesktopApiClient::createMeetingBody<std::string>(const BasicCreateMeetingRequest<std::string>&);
template CustodyString DesktopApiClient::createMeetingBody<CustodyString>(const BasicCreateMeetingRequest<CustodyString>&);
template std::optional<BasicUploadSessionRequest<std::string>> DesktopApiClient::uploadSessionRequest<std::string>(const std::array<std::uint64_t, 3>&, std::string_view);
template std::optional<BasicUploadSessionRequest<CustodyString>> DesktopApiClient::uploadSessionRequest<CustodyString>(const std::array<std::uint64_t, 3>&, std::string_view);
template std::string DesktopApiClient::idempotencyKey<std::string>(std::string_view, std::string_view, std::string_view);
template CustodyString DesktopApiClient::idempotencyKey<CustodyString>(std::string_view, std::string_view, std::string_view);
template std::optional<std::array<std::pair<std::string_view, std::string_view>, 2>> DesktopApiClient::scopedAccountHeaders<std::string>(const BasicDeletionScope<std::string>&);
template std::optional<std::array<std::pair<std::string_view, std::string_view>, 2>> DesktopApiClient::scopedAccountHeaders<CustodyString>(const BasicDeletionScope<CustodyString>&);
template std::optional<BasicDeletionReceipt<std::string>> DesktopApiClient::decodeDeletionReceipt<std::string>(std::string_view, const std::atomic<bool>*);
template std::optional<BasicNotificationContext<std::string>> DesktopApiClient::decodeNotificationContext<std::string>(std::string_view, const std::atomic<bool>*);
template std::optional<BasicNotificationContext<CustodyString>> DesktopApiClient::decodeNotificationContext<CustodyString>(std::string_view, const std::atomic<bool>*);
template std::optional<BasicDeletionReceipt<CustodyString>> DesktopApiClient::decodeDeletionReceipt<CustodyString>(std::string_view, const std::atomic<bool>*);
template std::string DesktopApiClient::ownOriginDeletionPath<std::string>(std::string_view);
template CustodyString DesktopApiClient::ownOriginDeletionPath<CustodyString>(std::string_view);
template std::string DesktopApiClient::meetingDeletionPath<std::string>(std::string_view);
template CustodyString DesktopApiClient::meetingDeletionPath<CustodyString>(std::string_view);
template std::string DesktopApiClient::originCancellationBody<std::string>(std::string_view);
template CustodyString DesktopApiClient::originCancellationBody<CustodyString>(std::string_view);
template std::string DesktopApiClient::meetingDeletionBody<std::string>();
template CustodyString DesktopApiClient::meetingDeletionBody<CustodyString>();
template std::string DesktopApiClient::localPurgeTaskPath<std::string>(std::string_view);
template CustodyString DesktopApiClient::localPurgeTaskPath<CustodyString>(std::string_view);
template std::string DesktopApiClient::localPurgeAckPath<std::string>(std::string_view);
template CustodyString DesktopApiClient::localPurgeAckPath<CustodyString>(std::string_view);
template std::optional<LocalPurgeTask> DesktopApiClient::decodeLocalPurgeTask<std::string>(std::string_view, const std::atomic<bool>*);
template std::optional<BasicLocalPurgeTask<CustodyString>> DesktopApiClient::decodeLocalPurgeTask<CustodyString>(std::string_view, const std::atomic<bool>*);
template std::optional<BasicLocalPurgeTasks<std::string>> DesktopApiClient::decodeLocalPurgeTaskList<std::string>(std::string_view, const std::atomic<bool>*);
template std::optional<BasicLocalPurgeTasks<CustodyString>> DesktopApiClient::decodeLocalPurgeTaskList<CustodyString>(std::string_view, const std::atomic<bool>*);
template std::string DesktopApiClient::localPurgeAckBody<std::string>(LocalPurgeAckState, std::string_view, std::string_view, std::string_view);
template CustodyString DesktopApiClient::localPurgeAckBody<CustodyString>(LocalPurgeAckState, std::string_view, std::string_view, std::string_view);

} // namespace graf::windows
