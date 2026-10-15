#pragma once
#include "MeetingReminderModel.h"
#include "RecordingNoticePresenter.h"
#include "../Web/NativeSettingsBridge.h"
#include "CalendarJoinOperation.h"

namespace graf::windows {
// Ephemeral safe menu text plus frozen target, never a cached launch grant.
struct UpcomingMeetingRow {
    CalendarReminderEvent event;
    std::uint64_t epoch = 0;
    std::wstring label;
    bool enabled = false;
    friend bool operator==(const UpcomingMeetingRow& a, const UpcomingMeetingRow& b) {
        return a.event.eventId == b.event.eventId && a.event.startsAt == b.event.startsAt &&
            a.event.endsAt == b.event.endsAt && a.event.meetingLinkPresent == b.event.meetingLinkPresent &&
            a.event.meetingUrl == b.event.meetingUrl && a.epoch == b.epoch &&
            a.label == b.label && a.enabled == b.enabled;
    }
};
// UI-thread coordination. AppMain supplies fresh, account-bound calendar reads
// before completing a user action; the model never grants capture authority.
class MeetingReminderPresenter final {
public:
    explicit MeetingReminderPresenter(RecordingNoticePresenter& card,
        NotificationPreferenceStore store = NotificationPreferenceStore::native());
    ~MeetingReminderPresenter();
    void bind(std::string owner, std::string workspace, std::string origin = {});
    void invalidate();
    void calendarFailed();
    [[nodiscard]] bool update(CalendarReminderSnapshot snapshot, std::uint64_t epoch);
    [[nodiscard]] std::optional<CalendarReminderSnapshot> upcoming() const { return model_.upcoming(); }
    [[nodiscard]] std::optional<std::vector<UpcomingMeetingRow>> upcomingRows(
        double now, std::string_view preferredZone = {}) const;
    [[nodiscard]] static std::optional<RecordingNoticePresenter::Clock::time_point> upcomingExpiry(
        double endsAt, double wallNow, RecordingNoticePresenter::Clock::time_point steadyNow);
    // Presentation only: the caller supplies an accepted account-bound zone.
    // Empty zone uses the current OS zone; failure never invents a time label.
    [[nodiscard]] static std::optional<std::wstring> upcomingTime(double instant,
        std::string_view preferredZone = {}, bool allDay = false, bool showTime = true);
    [[nodiscard]] bool upcomingCurrent(const CalendarReminderEvent& event, std::uint64_t epoch, double now) const {
        return model_.upcomingCurrent(event, epoch, now);
    }
    void reconcile(double now, RecordingNoticePresenter::Clock::time_point steadyNow, bool recording);
    [[nodiscard]] std::string settings(const NativeSettingsBridge::NotificationRequest& request,
        double now, RecordingNoticePresenter::Clock::time_point steadyNow, bool recording);
    [[nodiscard]] std::optional<CalendarReminderEvent> completeAction(const ReminderActionTarget& target,
        NoticeAction action, double now, bool recording);
    // Native applicability only, no URL/launch authority or worker completion.
    [[nodiscard]] std::optional<RecordingNoticePresenter::Clock::time_point> pendingActionExpiry(
        const ReminderActionTarget&, NoticeAction, double now, bool recording) const;
    void failAction(const ReminderActionTarget&, NoticeAction, CalendarJoinReason, double now, bool recording);
    [[nodiscard]] bool handoffRecordingCurrent(const ReminderActionTarget&, double now, bool recording) const;
    [[nodiscard]] std::uint64_t epoch() const { return model_.epoch(); }
    [[nodiscard]] const std::string& owner() const { return model_.owner(); }
    [[nodiscard]] const std::string& workspace() const { return model_.workspace(); }
    [[nodiscard]] const std::string& origin() const { return model_.origin(); }
    [[nodiscard]] const NotificationPreferences& preferences() const { return preferences_; }
    std::function<void(ReminderActionTarget, NoticeAction)> onActionRequested;
    // Native integration plays one optional sound here; never called for a
    // refresh, preview, quiet mode, blocked surface or active capture.
    std::function<void()> onMeetingPresented;
private:
    void retirePresented();
    RecordingNoticePresenter& card_;
    NotificationPreferenceStore store_;
    MeetingReminderModel model_;
    NotificationPreferences preferences_;
    std::optional<ReminderActionTarget> presented_;
    std::optional<NoticeAction> pendingAction_;
    double presentedDeadline_ = 0;
    RecordingNoticePresenter::Clock::time_point presentedSteadyDeadline_{};
    std::optional<RecordingNoticePresenter::Clock::time_point> failedJoinUntil_;
    std::wstring joinFailure_;
};
} // namespace graf::windows
