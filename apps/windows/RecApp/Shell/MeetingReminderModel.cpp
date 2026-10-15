#include "MeetingReminderModel.h"
#include "CalendarMeetingOpener.h"
#include "../Storage/Sha256.h"
#include "../Upload/DesktopUploadQueueService.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <set>

#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {
namespace {
std::string normalized(std::string value) {
    for (auto& c : value) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return value;
}
bool validOffset(int value) { return value == 0 || value == 1 || value == 5; }
std::string instant(double value) {
    std::ostringstream text; text.imbue(std::locale::classic());
    text << std::setprecision(std::numeric_limits<double>::max_digits10) << value;
    return text.str();
}
bool digestKey(std::string_view value) {
    return value.size() == 64 && value.find_first_not_of("0123456789abcdef") == std::string_view::npos;
}
std::string receiptKey(std::string_view context, const CalendarReminderEvent& event) {
    return sha256(std::string(context) + ":" + sha256(event.eventId) + ":" + instant(event.startsAt));
}
constexpr std::size_t maxReceipts = 1024, maxStoreBytes = 128 * 1024;
using Receipts = std::map<std::string, double>;
std::optional<Receipts> readReceipts(const NotificationPreferenceStore& store, std::string_view context, double now) {
    if (!digestKey(context) || !std::isfinite(now) || !store.read || !store.write) return std::nullopt;
    const auto bytes = store.read(std::string(context) + ".meetings");
    Receipts result;
    if (!bytes) return result;
    if (bytes->size() > maxStoreBytes || bytes->substr(0, 12) != "receipts-v1\n" || bytes->back() != '\n') return std::nullopt;
    std::istringstream input(bytes->substr(12)); input.imbue(std::locale::classic());
    std::string line;
    std::size_t count = 0;
    while (std::getline(input, line)) {
        if (++count > maxReceipts) return std::nullopt;
        std::istringstream row(line); row.imbue(std::locale::classic());
        std::string key; double expires;
        if (!(row >> key >> expires) || !digestKey(key) || !std::isfinite(expires) || expires <= 0 ||
            !(row >> std::ws).eof() || result.count(key)) return std::nullopt;
        result.emplace(std::move(key), expires);
    }
    for (auto it = result.begin(); it != result.end();) {
        if (it->second <= now) it = result.erase(it); else ++it;
    }
    return result;
}
bool writeReceipts(const NotificationPreferenceStore& store, std::string_view context, const Receipts& receipts) {
    std::string bytes = "receipts-v1\n";
    for (const auto& [key, expires] : receipts) bytes += key + " " + instant(expires) + "\n";
    const auto key = std::string(context) + ".meetings";
    const auto previous = store.read(key);
    if ((!previous && receipts.empty()) || previous == bytes) return true;
    return store.write(key, bytes) && store.read(key) == bytes;
}
bool updateProblemClaim(const NotificationPreferenceStore& store, std::string_view origin,
    std::string_view owner, std::string_view workspace, std::string_view incident, bool resolved) {
    // Serialized by the native UI owner, just like preferences and meeting claims.
    // The store does not infer recovery from snapshots, elapsed time or logout.
    if (!store.read || !store.write || incident.empty() || incident.size() > 4096) return false;
    try {
        MeetingReminderModel context;
        context.bind(std::string(owner), std::string(workspace), std::string(origin));
        const auto contextKey = context.contextKey();
        if (contextKey.empty()) return false;
        const auto key = contextKey + ".problems";
        const auto previous = store.read(key);
        constexpr std::string_view header = "problems-v1\n";
        std::set<std::string> claims;
        if (previous) {
            if (previous->size() > maxStoreBytes || previous->substr(0, header.size()) != header ||
                previous->back() != '\n') return false;
            std::istringstream input(previous->substr(header.size()));
            std::string digest;
            while (std::getline(input, digest)) {
                if (!digestKey(digest) || claims.size() >= maxReceipts || !claims.insert(digest).second) return false;
            }
        }
        const auto digest = sha256(incident);
        if (resolved) {
            if (!claims.erase(digest)) return true; // already absent; no write or broad cleanup
        } else {
            if (claims.count(digest) || claims.size() >= maxReceipts) return false;
            claims.insert(digest);
        }
        std::string bytes(header);
        for (const auto& claim : claims) bytes += claim + "\n";
        return store.write(key, bytes) && store.read(key) == bytes;
    } catch (...) {
        // Native read errors use the malformed sentinel; injected stores may throw.
        // Neither authorizes notification or reports an unverified resolution.
        return false;
    }
}
}

namespace {
template<class Result, class Items>
Result projectRecordingProblems(
    const LocalProblemContext& currentContext, const LocalProblemContext& queueContext,
    const Items& items, bool queueComplete,
    const std::optional<CurrentCaptureProblem>& capture, std::uint64_t nowMs) {
    const auto owns = [&](const LocalProblemContext& context) {
        return !currentContext.origin.empty() && !currentContext.owner.empty() && !currentContext.workspace.empty() &&
            context.origin == currentContext.origin && context.owner == currentContext.owner &&
            context.workspace == currentContext.workspace;
    };
    struct Session {
        bool owned = true, hasRows = false, allUploaded = true, problem = false, fresh = false;
        std::uint64_t occurredAtMs = 0;
    };
    // Borrow only for this call; the result below owns its identities. Rebind
    // from the output allocator so protected intermediates share its quota.
    using Entry = std::pair<const std::string_view, Session>;
    using Allocator = typename std::allocator_traits<typename Result::allocator_type>::template rebind_alloc<Entry>;
    std::map<std::string_view, Session, std::less<std::string_view>, Allocator> sessions(
        std::less<std::string_view>{}, Allocator{});
    const bool queueOwned = owns(queueContext);
    for (const auto& item : items) {
        if (item.sessionId.empty()) continue; // no stable incident to identify
        auto& session = sessions[std::string_view(item.sessionId)];
        session.hasRows = true;
        session.owned = session.owned && queueOwned && !item.localRecordingId.empty() &&
            std::string_view(item.ownerUserId) == currentContext.owner &&
            std::string_view(item.ownerWorkspaceId) == currentContext.workspace;
        session.allUploaded = session.allUploaded && item.status == UploadQueueStatus::uploaded;
        const bool problem = item.status == UploadQueueStatus::needsAuth ||
            item.status == UploadQueueStatus::quarantined || item.status == UploadQueueStatus::blocked ||
            (item.status == UploadQueueStatus::retry && item.safeReason == "retry_budget_exhausted");
        session.problem = session.problem || problem;
        if (item.updatedAtMs > 0 && item.updatedAtMs <= nowMs) {
            if (!session.occurredAtMs || item.updatedAtMs < session.occurredAtMs) session.occurredAtMs = item.updatedAtMs;
            session.fresh = session.fresh || (problem && nowMs - item.updatedAtMs < 300'000);
        }
    }
    if (capture && !capture->sessionId.empty()) {
        auto& session = sessions[capture->sessionId];
        session.owned = session.owned && owns(capture->frozenContext);
        session.problem = session.problem || capture->blocker;
        session.fresh = session.fresh || capture->blocker;
        if (!session.occurredAtMs) session.occurredAtMs = nowMs;
    }
    Result result;
    result.reserve(sessions.size());
    for (const auto& [id, session] : sessions) {
        auto state = LocalProblemState::unknown;
        if (session.owned) {
            if (session.problem) state = LocalProblemState::problem;
            else if (queueComplete && session.hasRows && session.allUploaded) state = LocalProblemState::positivelyResolved;
        }
        using String = decltype(typename Result::value_type{}.sessionId);
        String incident("capture-problem:");
        incident.append(id.data(), id.size());
        result.push_back({String(id.data(), id.size()), std::move(incident), state,
            state == LocalProblemState::problem && session.fresh, session.occurredAtMs});
    }
    return result; // stable session order, independent of row/attempt ordering
}
}

std::vector<LocalProblemProjection> projectLocalRecordingProblems(
    const LocalProblemContext& currentContext, const LocalProblemContext& queueContext,
    const std::vector<UploadCustodyItem>& items, bool queueComplete,
    const std::optional<CurrentCaptureProblem>& capture, std::uint64_t nowMs) {
    return projectRecordingProblems<std::vector<LocalProblemProjection>>(
        currentContext, queueContext, items, queueComplete, capture, nowMs);
}

CustodyVector<ProtectedLocalProblemProjection> projectProtectedLocalRecordingProblems(
    const LocalProblemContext& currentContext, const LocalProblemContext& queueContext,
    const CustodyVector<BasicUploadCustodyItem<CustodyString, CustodyString>>& items, bool queueComplete,
    const std::optional<CurrentCaptureProblem>& capture, std::uint64_t nowMs) {
    return projectRecordingProblems<CustodyVector<ProtectedLocalProblemProjection>>(
        currentContext, queueContext, items, queueComplete, capture, nowMs);
}

NotificationPreferences NotificationPreferenceStore::load(std::string_view owner) const {
    NotificationPreferences result;
    if (owner.empty() || !read) return result;
    const auto bytes = read(sha256(owner));
    if (!bytes || !((bytes->size() == 8 && bytes->substr(0, 4) == "v1:\n") ||
                    (bytes->size() == 9 && bytes->substr(0, 4) == "v2:\n" && ((*bytes)[8] == '0' || (*bytes)[8] == '1'))) ||
        ((*bytes)[4] != '0' && (*bytes)[4] != '1') ||
        ((*bytes)[5] != '0' && (*bytes)[5] != '1') ||
        ((*bytes)[6] != '0' && (*bytes)[6] != '1') ||
        ((*bytes)[7] != '0' && (*bytes)[7] != '1' && (*bytes)[7] != '5')) return result;
    result.reminders = (*bytes)[4] == '1'; result.showTitles = (*bytes)[5] == '1';
    result.sound = (*bytes)[6] == '1'; result.offsetMinutes = (*bytes)[7] - '0';
    result.quiet = bytes->size() == 9 && (*bytes)[8] == '1';
    return result;
}

bool NotificationPreferenceStore::save(const NotificationPreferences& value, std::string_view owner) const {
    if (owner.empty() || !read || !write || !validOffset(value.offsetMinutes)) return false;
    std::string bytes = "v2:\n";
    bytes += value.reminders ? '1' : '0'; bytes += value.showTitles ? '1' : '0';
    bytes += value.sound ? '1' : '0'; bytes += static_cast<char>('0' + value.offsetMinutes);
    bytes += value.quiet ? '1' : '0';
    const auto key = sha256(owner);
    return write(key, bytes) && read(key) == bytes;
}

bool NotificationPreferenceStore::claimMeeting(std::string_view context, const CalendarReminderEvent& event, double now) const {
    if (event.eventId.empty() || !std::isfinite(event.startsAt) || !std::isfinite(event.endsAt) ||
        event.endsAt <= now || event.startsAt + 120 <= now) return false;
    auto receipts = readReceipts(*this, context, now);
    if (!receipts) return false;
    const auto key = receiptKey(context, event);
    const bool alreadyClaimed = receipts->count(key) != 0;
    if (!alreadyClaimed) {
        if (receipts->size() >= maxReceipts) return false; // Never evict a live deny marker.
        receipts->emplace(key, event.startsAt + 120);
    }
    return writeReceipts(*this, context, *receipts) && !alreadyClaimed;
}
bool NotificationPreferenceStore::pruneMeetingReceipts(std::string_view context, double now) const {
    const auto receipts = readReceipts(*this, context, now);
    return receipts && writeReceipts(*this, context, *receipts);
}

bool NotificationPreferenceStore::claimProblem(std::string_view origin, std::string_view owner,
    std::string_view workspace, std::string_view incidentIdentity) const {
    return updateProblemClaim(*this, origin, owner, workspace, incidentIdentity, false);
}
bool NotificationPreferenceStore::resolveProblem(std::string_view origin, std::string_view owner,
    std::string_view workspace, std::string_view incidentIdentity) const {
    return updateProblemClaim(*this, origin, owner, workspace, incidentIdentity, true);
}

NotificationPreferenceStore NotificationPreferenceStore::native() {
#ifdef _WIN32
    constexpr auto key = L"Software\\GRAF\\Windows\\Notifications";
    return {
        [key](std::string_view owner) -> std::optional<std::string> {
            const std::wstring name(owner.begin(), owner.end());
            DWORD size = 0;
            auto result = RegGetValueW(HKEY_CURRENT_USER, key, name.c_str(), RRF_RT_REG_BINARY, nullptr, nullptr, &size);
            if (result == ERROR_FILE_NOT_FOUND || result == ERROR_PATH_NOT_FOUND) return std::nullopt;
            if (result != ERROR_SUCCESS || size == 0 || size > maxStoreBytes) return std::string{};
            std::string buffer(size, '\0');
            result = RegGetValueW(HKEY_CURRENT_USER, key, name.c_str(), RRF_RT_REG_BINARY, nullptr, buffer.data(), &size);
            if (result != ERROR_SUCCESS || size != buffer.size()) return std::string{};
            return buffer;
        },
        [key](std::string_view owner, std::string_view value) {
            if (value.size() > maxStoreBytes) return false;
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

void MeetingReminderModel::bind(std::string owner, std::string workspace, std::string origin) {
    owner = normalized(std::move(owner)); workspace = normalized(std::move(workspace));
    origin = normalized(std::move(origin));
    if (!origin.empty() && origin.back() == '/') origin.pop_back();
    const auto scheme = origin.rfind("https://", 0) == 0 ? 8u : origin.rfind("http://", 0) == 0 ? 7u : 0u;
    if (!scheme || origin.size() <= scheme || origin.find_first_of("/?#@\\", scheme) != std::string::npos ||
        std::any_of(origin.begin(), origin.end(), [](unsigned char c) { return c <= 0x20 || c == 0x7f; })) origin.clear();
    const std::string_view defaultPort = scheme == 8 ? ":443" : ":80";
    if (origin.size() > scheme + defaultPort.size() && origin.compare(origin.size() - defaultPort.size(), defaultPort.size(), defaultPort) == 0)
        origin.resize(origin.size() - defaultPort.size());
    if (owner == owner_ && workspace == workspace_ && origin == origin_) return;
    invalidate();
    if (owner.empty() || workspace.empty() || origin.empty()) return;
    owner_ = std::move(owner); workspace_ = std::move(workspace); origin_ = std::move(origin);
}
void MeetingReminderModel::invalidate() { ++epoch_; owner_.clear(); workspace_.clear(); origin_.clear(); dismissed_.clear(); clearCalendar(); }
void MeetingReminderModel::clearCalendar() { events_.clear(); invalidateUpcoming(); }
bool MeetingReminderModel::update(CalendarReminderSnapshot snapshot, std::uint64_t epoch) {
    if (owner_.empty() || epoch != epoch_ || normalized(snapshot.userId) != owner_ || normalized(snapshot.workspaceId) != workspace_) return false;
    // The API decoder validates dates; also keep internal typed callers from
    // passing NaN into the menu sort or retaining an invalid menu source.
    upcomingAvailable_ = std::all_of(snapshot.events.begin(), snapshot.events.end(), [](const auto& event) {
        return std::isfinite(event.startsAt) && std::isfinite(event.endsAt) && event.endsAt > event.startsAt;
    });
    showUpcomingTime_ = snapshot.showUpcomingTime; showUpcomingTitle_ = snapshot.showUpcomingTitle;
    events_ = std::move(snapshot.events); return true;
}
std::optional<CalendarReminderSnapshot> MeetingReminderModel::upcoming() const {
    if (!upcomingAvailable_) return std::nullopt;
    CalendarReminderSnapshot result{owner_, workspace_, events_, showUpcomingTime_, showUpcomingTitle_};
    std::sort(result.events.begin(), result.events.end(), [](const auto& left, const auto& right) {
        return left.startsAt < right.startsAt || (left.startsAt == right.startsAt && left.eventId < right.eventId);
    });
    if (result.events.size() > 12) result.events.resize(12);
    return result;
}
bool MeetingReminderModel::upcomingCurrent(const CalendarReminderEvent& target, std::uint64_t epoch, double now) const {
    if (!upcomingAvailable_ || epoch != epoch_ || !std::isfinite(now) || target.eventId.empty() ||
        !std::isfinite(target.startsAt) || !std::isfinite(target.endsAt) || target.endsAt <= target.startsAt ||
        now >= target.endsAt || !target.meetingLinkPresent || !safeMeetingUrl(target.meetingUrl)) return false;
    return std::any_of(events_.begin(), events_.end(), [&](const auto& event) {
        return event.eventId == target.eventId && event.startsAt == target.startsAt && event.endsAt == target.endsAt &&
            event.meetingLinkPresent == target.meetingLinkPresent && event.meetingUrl == target.meetingUrl;
    });
}
double MeetingReminderModel::deadline(const CalendarReminderEvent& event, int offsetMinutes) {
    return std::min(event.endsAt, event.startsAt - offsetMinutes * 60.0 + 120);
}
bool MeetingReminderModel::eligible(const CalendarReminderEvent& event, double now, bool recording, int offsetMinutes) {
    return validOffset(offsetMinutes) && std::isfinite(now) && std::isfinite(event.startsAt) && std::isfinite(event.endsAt) &&
        !event.eventId.empty() && event.endsAt > event.startsAt && !recording && event.canSurface &&
        now >= event.startsAt - offsetMinutes * 60.0 && now < deadline(event, offsetMinutes);
}
std::string MeetingReminderModel::contextKey() const {
    return owner_.empty() ? std::string{} : sha256(sha256(origin_) + sha256(owner_) + sha256(workspace_));
}
std::string MeetingReminderModel::dismissalKey(const CalendarReminderEvent& event) const {
    return receiptKey(contextKey(), event);
}
void MeetingReminderModel::dismiss(const CalendarReminderEvent& event) { dismissed_[dismissalKey(event)] = event.startsAt + 120; }
ReminderActionTarget MeetingReminderModel::actionTarget(const CalendarReminderEvent& event) const {
    return {epoch_, event.eventId, event.startsAt, event.meetingUrl, event.meetingLinkPresent};
}
std::optional<CalendarReminderEvent> MeetingReminderModel::candidate(double now, bool recording, int offsetMinutes) const {
    std::optional<CalendarReminderEvent> result;
    if (owner_.empty()) return result;
    for (auto it = dismissed_.begin(); it != dismissed_.end();) {
        if (it->second <= now) it = dismissed_.erase(it); else ++it;
    }
    for (const auto& event : events_) {
        if (!eligible(event, now, recording, offsetMinutes) || dismissed_.count(dismissalKey(event))) continue;
        if (!result || event.startsAt < result->startsAt || (event.startsAt == result->startsAt && event.eventId < result->eventId)) result = event;
    }
    return result;
}
std::optional<CalendarReminderEvent> MeetingReminderModel::revalidate(const ReminderActionTarget& target, double now, bool recording, int offsetMinutes) const {
    const auto event = currentEvent(target, now, recording, offsetMinutes);
    if (!event || dismissed_.count(dismissalKey(*event))) return std::nullopt;
    return *event;
}
bool MeetingReminderModel::matchesHandoffTarget(const ReminderActionTarget& target, double now, bool recording, int offsetMinutes) const {
    return currentEvent(target, now, recording, offsetMinutes) != nullptr;
}
const CalendarReminderEvent* MeetingReminderModel::currentEvent(const ReminderActionTarget& target, double now, bool recording, int offsetMinutes) const {
    if (owner_.empty() || target.epoch != epoch_) return nullptr;
    for (const auto& event : events_) {
        if (event.eventId == target.eventId && event.startsAt == target.startsAt &&
            event.meetingUrl == target.meetingUrl && event.meetingLinkPresent == target.meetingLinkPresent &&
            eligible(event, now, recording, offsetMinutes)) return &event;
    }
    return nullptr;
}

bool MeetingReminderModel::safeMeetingUrl(std::string_view url) {
    return CalendarMeetingOpener::validatedHTTPS(url).has_value();
}
} // namespace graf::windows
