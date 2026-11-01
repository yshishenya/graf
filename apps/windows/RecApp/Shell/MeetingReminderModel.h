#pragma once

#include "../Upload/DesktopApiClient.h"
#include <functional>
#include <set>

namespace graf::windows {

struct NotificationPreferences {
    bool reminders = true;
    bool showTitles = false;
    bool sound = false;
    int offsetMinutes = 1;
};

struct NotificationPreferenceStore {
    std::function<std::optional<std::string>(std::string_view)> read;
    std::function<bool(std::string_view, std::string_view)> write;
    [[nodiscard]] NotificationPreferences load(std::string_view owner) const;
    [[nodiscard]] bool save(const NotificationPreferences& value, std::string_view owner) const;
    [[nodiscard]] static NotificationPreferenceStore native();
};

struct ReminderActionTarget {
    std::uint64_t epoch = 0;
    std::string eventId;
    double startsAt = 0;
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
    void bind(std::string owner, std::string workspace);
    void invalidate();
    void clearCalendar();
    [[nodiscard]] bool update(CalendarReminderSnapshot snapshot, std::uint64_t epoch);
    [[nodiscard]] std::optional<CalendarReminderEvent> candidate(double now, bool recording) const;
    [[nodiscard]] std::optional<CalendarReminderEvent> revalidate(const ReminderActionTarget& target,
                                                                double now, bool recording) const;
    [[nodiscard]] ReminderActionTarget actionTarget(const CalendarReminderEvent& event) const;
    void dismiss(const CalendarReminderEvent& event);
    [[nodiscard]] std::string dismissalKey(const CalendarReminderEvent& event) const;
    [[nodiscard]] const std::string& owner() const { return owner_; }
    [[nodiscard]] const std::string& workspace() const { return workspace_; }
    [[nodiscard]] std::uint64_t epoch() const { return epoch_; }
    [[nodiscard]] static double deadline(const CalendarReminderEvent& event);
    [[nodiscard]] static bool eligible(const CalendarReminderEvent& event, double now, bool recording);
    [[nodiscard]] static bool safeMeetingUrl(std::string_view url);
private:
    std::string owner_, workspace_;
    std::uint64_t epoch_ = 0;
    std::vector<CalendarReminderEvent> events_;
    // Mac's stable occurrence key survives account invalidation in this process.
    // Only hashes survive: a different account/workspace never inherits dismissal.
    std::set<std::string> dismissed_;
};
} // namespace graf::windows
