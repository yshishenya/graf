#pragma once

#include "../Upload/DesktopApiClient.h"
#include <functional>
#include <map>

namespace graf::windows {

struct UploadCustodyItem;

// Trusted native identities, already canonicalized by their owner. Comparison
// is exact; this projection never adopts an unowned recording into an account.
struct LocalProblemContext {
    std::string origin, owner, workspace;
};
struct CurrentCaptureProblem {
    std::string sessionId;
    LocalProblemContext frozenContext; // captured at recording start, not refresh
    bool blocker = false;
};
enum class LocalProblemState { unknown, problem, positivelyResolved };
struct LocalProblemProjection {
    std::string sessionId;
    std::string incidentId; // one capture-problem identity per session, not reason/attempt
    LocalProblemState state = LocalProblemState::unknown;
    bool fresh = false; // problem updated in [now-300s, now], with strict age <300s
    std::uint64_t occurredAtMs = 0; // oldest known non-future row time; capture-only: now
};

// Pure, no claims/history/UI. Caller supplies only current-generation native
// observations; queueContext binds their origin, absent from UploadCustodyItem.
// queueComplete=false allows known problems, NEVER positive resolution. Failed
// reads supply no rows; absence from the returned vector is always unknown.
// Resolution requires a nonempty, fully owned, all-uploaded session in a complete
// queue, with no current capture blocker. Retry/auth recovery alone is unknown.
[[nodiscard]] std::vector<LocalProblemProjection> projectLocalRecordingProblems(
    const LocalProblemContext& currentContext, const LocalProblemContext& queueContext,
    const std::vector<UploadCustodyItem>& items, bool queueComplete,
    const std::optional<CurrentCaptureProblem>& capture, std::uint64_t nowMs);

struct NotificationPreferences {
    bool reminders = true;
    bool showTitles = false;
    bool sound = false;
    int offsetMinutes = 1;
    bool quiet = false;
};

struct NotificationPreferenceStore {
    std::function<std::optional<std::string>(std::string_view)> read;
    std::function<bool(std::string_view, std::string_view)> write;
    [[nodiscard]] NotificationPreferences load(std::string_view owner) const;
    [[nodiscard]] bool save(const NotificationPreferences& value, std::string_view owner) const;
    // One UI-thread owner. Missing storage is not a successful claim. Reads
    // return nullopt only for an absent value; malformed/error data fail closed.
    [[nodiscard]] bool claimMeeting(std::string_view contextKey, const CalendarReminderEvent& event, double now) const;
    [[nodiscard]] bool pruneMeetingReceipts(std::string_view contextKey, double now) const;
    // A stable native incident identity (recording + problem kind), never UI text.
    // True claims the first notification; false always forbids a new notification.
    [[nodiscard]] bool claimProblem(std::string_view origin, std::string_view owner,
        std::string_view workspace, std::string_view incidentIdentity) const;
    // Call only for a positively confirmed resolution in the current native
    // context. Absence from a partial snapshot is NOT confirmation. No bulk reset
    // or expiry exists; true means the removal/absence was verified.
    [[nodiscard]] bool resolveProblem(std::string_view origin, std::string_view owner,
        std::string_view workspace, std::string_view incidentIdentity) const;
    [[nodiscard]] static NotificationPreferenceStore native();
};

struct ReminderActionTarget {
    std::uint64_t epoch = 0;
    std::string eventId;
    double startsAt = 0;
    std::string meetingUrl{};
    bool meetingLinkPresent = false;
};

// Ephemeral dispatch identity. Never persist or log the session token.
struct ReminderRequestIdentity {
    std::uint64_t authGeneration = 0;
    std::uint64_t epoch = 0;
    std::string sessionToken;
    [[nodiscard]] bool matches(std::uint64_t currentGeneration, std::uint64_t currentEpoch,
        std::string_view currentToken) const {
        return !sessionToken.empty() && authGeneration == currentGeneration && epoch == currentEpoch && sessionToken == currentToken;
    }
};

// UI-thread owner. A response may only update the context captured at dispatch.
class MeetingReminderModel final {
public:
    // origin must come from the trusted native account context, never the page.
    // Missing origin deliberately leaves reminders unavailable until integration.
    void bind(std::string owner, std::string workspace, std::string origin = {});
    void invalidate();
    void clearCalendar();
    [[nodiscard]] bool update(CalendarReminderSnapshot snapshot, std::uint64_t epoch);
    [[nodiscard]] std::optional<CalendarReminderEvent> candidate(double now, bool recording, int offsetMinutes = 1) const;
    [[nodiscard]] std::optional<CalendarReminderEvent> revalidate(const ReminderActionTarget& target,
                                                                double now, bool recording, int offsetMinutes = 1) const;
    [[nodiscard]] ReminderActionTarget actionTarget(const CalendarReminderEvent& event) const;
    void dismiss(const CalendarReminderEvent& event);
    [[nodiscard]] std::string dismissalKey(const CalendarReminderEvent& event) const;
    [[nodiscard]] const std::string& owner() const { return owner_; }
    [[nodiscard]] const std::string& workspace() const { return workspace_; }
    [[nodiscard]] const std::string& origin() const { return origin_; }
    [[nodiscard]] std::string contextKey() const;
    [[nodiscard]] std::uint64_t epoch() const { return epoch_; }
    [[nodiscard]] static double deadline(const CalendarReminderEvent& event, int offsetMinutes = 1);
    [[nodiscard]] static bool eligible(const CalendarReminderEvent& event, double now, bool recording, int offsetMinutes = 1);
    [[nodiscard]] static bool safeMeetingUrl(std::string_view url);
private:
    std::string owner_, workspace_, origin_;
    std::uint64_t epoch_ = 0;
    std::vector<CalendarReminderEvent> events_;
    // Active-context terminal events; durable receipts survive context changes.
    mutable std::map<std::string, double> dismissed_;
};
} // namespace graf::windows
