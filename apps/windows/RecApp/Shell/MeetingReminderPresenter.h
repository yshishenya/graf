#pragma once
#include "MeetingReminderModel.h"
#include "RecordingNoticePresenter.h"
#include "../Web/NativeSettingsBridge.h"

namespace graf::windows {
// UI-thread coordination. AppMain supplies fresh, account-bound calendar reads
// before completing a user action; the model never grants capture authority.
class MeetingReminderPresenter final {
public:
    explicit MeetingReminderPresenter(RecordingNoticePresenter& card,
        NotificationPreferenceStore store = NotificationPreferenceStore::native());
    void bind(std::string owner, std::string workspace);
    void invalidate();
    void calendarFailed();
    [[nodiscard]] bool update(CalendarReminderSnapshot snapshot, std::uint64_t epoch);
    void reconcile(double now, RecordingNoticePresenter::Clock::time_point steadyNow, bool recording);
    [[nodiscard]] std::string settings(const NativeSettingsBridge::NotificationRequest& request,
        double now, RecordingNoticePresenter::Clock::time_point steadyNow, bool recording);
    [[nodiscard]] std::optional<CalendarReminderEvent> completeAction(const ReminderActionTarget& target,
        NoticeAction action, double now, bool recording);
    [[nodiscard]] std::uint64_t epoch() const { return model_.epoch(); }
    [[nodiscard]] const std::string& owner() const { return model_.owner(); }
    [[nodiscard]] const std::string& workspace() const { return model_.workspace(); }
    std::function<void(ReminderActionTarget, NoticeAction)> onActionRequested;
private:
    RecordingNoticePresenter& card_;
    NotificationPreferenceStore store_;
    MeetingReminderModel model_;
    NotificationPreferences preferences_;
    std::optional<ReminderActionTarget> presented_;
};
} // namespace graf::windows
