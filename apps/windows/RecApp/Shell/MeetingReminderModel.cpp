#include "MeetingReminderModel.h"
#include "../Storage/Sha256.h"

#include <algorithm>
#include <cctype>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#else
#include <arpa/inet.h>
#endif

namespace graf::windows {
namespace {
std::string normalized(std::string value) {
    for (auto& c : value) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return value;
}
bool parseIpLiteral(int family, const std::string& text, void* address) {
#ifdef _WIN32
    return InetPtonA(family, text.c_str(), address) == 1;
#else
    return inet_pton(family, text.c_str(), address) == 1;
#endif
}
}

NotificationPreferences NotificationPreferenceStore::load(std::string_view owner) const {
    NotificationPreferences result;
    if (owner.empty() || !read) return result;
    const auto bytes = read(sha256(owner));
    if (!bytes || bytes->size() != 8 || bytes->substr(0, 4) != "v1:\n" ||
        ((*bytes)[4] != '0' && (*bytes)[4] != '1') ||
        ((*bytes)[5] != '0' && (*bytes)[5] != '1') ||
        ((*bytes)[6] != '0' && (*bytes)[6] != '1') ||
        ((*bytes)[7] != '0' && (*bytes)[7] != '1' && (*bytes)[7] != '5')) return result;
    result.reminders = (*bytes)[4] == '1'; result.showTitles = (*bytes)[5] == '1';
    result.sound = (*bytes)[6] == '1'; result.offsetMinutes = (*bytes)[7] - '0';
    return result;
}

bool NotificationPreferenceStore::save(const NotificationPreferences& value, std::string_view owner) const {
    if (owner.empty() || !write || (value.offsetMinutes != 0 && value.offsetMinutes != 1 && value.offsetMinutes != 5)) return false;
    std::string bytes = "v1:\n";
    bytes += value.reminders ? '1' : '0'; bytes += value.showTitles ? '1' : '0';
    bytes += value.sound ? '1' : '0'; bytes += static_cast<char>('0' + value.offsetMinutes);
    return write(sha256(owner), bytes);
}

NotificationPreferenceStore NotificationPreferenceStore::native() {
#ifdef _WIN32
    constexpr auto key = L"Software\\GRAF\\Windows\\Notifications";
    return {
        [key](std::string_view owner) -> std::optional<std::string> {
            const std::wstring name(owner.begin(), owner.end());
            char buffer[8]{}; DWORD size = sizeof(buffer);
            if (RegGetValueW(HKEY_CURRENT_USER, key, name.c_str(), RRF_RT_REG_BINARY, nullptr, buffer, &size) != ERROR_SUCCESS || size != 8)
                return std::nullopt;
            return std::string(buffer, size);
        },
        [key](std::string_view owner, std::string_view value) {
            HKEY handle = nullptr;
            if (RegCreateKeyExW(HKEY_CURRENT_USER, key, 0, nullptr, 0, KEY_SET_VALUE, nullptr, &handle, nullptr) != ERROR_SUCCESS) return false;
            const std::wstring name(owner.begin(), owner.end());
            const auto result = RegSetValueExW(handle, name.c_str(), 0, REG_BINARY,
                reinterpret_cast<const BYTE*>(value.data()), static_cast<DWORD>(value.size()));
            RegCloseKey(handle);
            return result == ERROR_SUCCESS;
        }};
#else
    return {};
#endif
}

void MeetingReminderModel::bind(std::string owner, std::string workspace) {
    owner = normalized(std::move(owner)); workspace = normalized(std::move(workspace));
    if (owner == owner_ && workspace == workspace_) return;
    invalidate();
    if (owner.empty() || workspace.empty()) return;
    owner_ = std::move(owner); workspace_ = std::move(workspace);
}
void MeetingReminderModel::invalidate() { ++epoch_; owner_.clear(); workspace_.clear(); clearCalendar(); }
void MeetingReminderModel::clearCalendar() { events_.clear(); }
bool MeetingReminderModel::update(CalendarReminderSnapshot snapshot, std::uint64_t epoch) {
    if (owner_.empty() || epoch != epoch_ || normalized(snapshot.userId) != owner_ || normalized(snapshot.workspaceId) != workspace_) return false;
    events_ = std::move(snapshot.events); return true;
}
double MeetingReminderModel::deadline(const CalendarReminderEvent& event) {
    return std::min({event.endsAt, event.startsAt, event.startsAt - 900 + 120});
}
bool MeetingReminderModel::eligible(const CalendarReminderEvent& event, double now, bool recording) {
    return !recording && event.canSurface && now >= event.startsAt - 900 && now < deadline(event);
}
std::string MeetingReminderModel::dismissalKey(const CalendarReminderEvent& event) const {
    return sha256(owner_ + ":" + workspace_ + ":" + event.eventId);
}
void MeetingReminderModel::dismiss(const CalendarReminderEvent& event) { dismissed_.insert(dismissalKey(event)); }
ReminderActionTarget MeetingReminderModel::actionTarget(const CalendarReminderEvent& event) const {
    return {epoch_, event.eventId, event.startsAt};
}
std::optional<CalendarReminderEvent> MeetingReminderModel::candidate(double now, bool recording) const {
    std::optional<CalendarReminderEvent> result;
    if (owner_.empty()) return result;
    for (const auto& event : events_) {
        if (!eligible(event, now, recording) || dismissed_.count(dismissalKey(event))) continue;
        if (!result || event.startsAt < result->startsAt) result = event;
    }
    return result;
}
std::optional<CalendarReminderEvent> MeetingReminderModel::revalidate(const ReminderActionTarget& target, double now, bool recording) const {
    if (owner_.empty() || target.epoch != epoch_) return std::nullopt;
    for (const auto& event : events_) {
        if (event.eventId == target.eventId && event.startsAt == target.startsAt && eligible(event, now, recording) &&
            !dismissed_.count(dismissalKey(event))) return event;
    }
    return std::nullopt;
}

bool MeetingReminderModel::safeMeetingUrl(std::string_view url) {
    if (url.size() > 4096 || url.size() < 9) return false;
    if (normalized(std::string(url.substr(0, 8))) != "https://" || url.find('#') != std::string_view::npos) return false;
    for (auto c : url) if (static_cast<unsigned char>(c) <= 0x20 || c == '\\' || c == 0x7f) return false;
    const auto end = url.find_first_of("/?", 8);
    auto authority = url.substr(8, end == std::string_view::npos ? url.size() - 8 : end - 8);
    if (authority.empty() || authority.find('@') != std::string_view::npos || authority.find('%') != std::string_view::npos) return false;
    bool ipv6 = authority.front() == '[';
    std::size_t colon;
    if (ipv6) {
        const auto bracket = authority.find(']');
        if (bracket == std::string_view::npos || bracket < 3) return false;
        in6_addr address{};
        if (!parseIpLiteral(AF_INET6, std::string(authority.substr(1, bracket - 1)), &address)) return false;
        if (bracket + 1 < authority.size() && authority[bracket + 1] != ':') return false;
        colon = bracket + 1 < authority.size() ? bracket + 1 : std::string_view::npos;
    } else colon = authority.find(':');
    if (colon != std::string_view::npos) {
        auto port = authority.substr(colon + 1);
        if (port.empty() || port.size() > 5) return false;
        unsigned value = 0;
        for (auto c : port) { if (c < '0' || c > '9') return false; value = value * 10 + (c - '0'); }
        if (value == 0 || value > 65535) return false;
        authority = authority.substr(0, colon);
    }
    if (ipv6) return true;
    auto host = normalized(std::string(authority));
    while (!host.empty() && host.back() == '.') host.pop_back();
    while (!host.empty() && host.front() == '.') host.erase(host.begin());
    if (host.empty() || host == "localhost" || (host.size() > 10 && host.substr(host.size() - 10) == ".localhost")) return false;
    for (auto c : host) if (static_cast<unsigned char>(c) < 0x80 && !std::isalnum(static_cast<unsigned char>(c)) && c != '-' && c != '.') return false;
    in_addr address{};
    if (parseIpLiteral(AF_INET, host, &address)) {
        const auto* bytes = reinterpret_cast<const unsigned char*>(&address.s_addr);
        // Keep canonical decimal spelling even if a platform accepts leading zeroes.
        if (host != std::to_string(bytes[0]) + "." + std::to_string(bytes[1]) + "." +
                    std::to_string(bytes[2]) + "." + std::to_string(bytes[3])) return false;
        return bytes[0] != 10 && bytes[0] != 127 &&
            !(bytes[0] == 172 && bytes[1] >= 16 && bytes[1] <= 31) && !(bytes[0] == 192 && bytes[1] == 168) &&
            (bytes[0] || bytes[1] || bytes[2] || bytes[3]);
    }
    // Do not pass alternative numeric host spellings to ShellExecute's parser.
    const auto lastLabel = host.substr(host.rfind('.') == std::string::npos ? 0 : host.rfind('.') + 1);
    return std::any_of(lastLabel.begin(), lastLabel.end(), [](char c) { return (c >= 'a' && c <= 'z') || static_cast<unsigned char>(c) >= 0x80; }) &&
        lastLabel.rfind("0x", 0) != 0;
}
} // namespace graf::windows
