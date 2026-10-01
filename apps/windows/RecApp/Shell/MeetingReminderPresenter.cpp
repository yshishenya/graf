#include "MeetingReminderPresenter.h"
#include <ctime>
#include <utility>
#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {
namespace {
bool sameTarget(const ReminderActionTarget& left, const ReminderActionTarget& right) {
    return left.epoch == right.epoch && left.eventId == right.eventId && left.startsAt == right.startsAt &&
        left.meetingUrl == right.meetingUrl && left.meetingLinkPresent == right.meetingLinkPresent;
}
std::wstring wide(std::string_view value) {
#ifdef _WIN32
    const auto size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0);
    if (size <= 0) return {};
    std::wstring result(size, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), result.data(), size);
    return result;
#else
    std::wstring result;
    for (std::size_t i = 0; i < value.size();) {
        unsigned cp = static_cast<unsigned char>(value[i++]);
        unsigned count = 0, minimum = 0;
        if (cp >= 0xf0 && cp <= 0xf4) { cp &= 7; count = 3; minimum = 0x10000; }
        else if (cp >= 0xe0 && cp <= 0xef) { cp &= 15; count = 2; minimum = 0x800; }
        else if (cp >= 0xc2 && cp <= 0xdf) { cp &= 31; count = 1; minimum = 0x80; }
        else if (cp >= 0x80) return {};
        while (count--) {
            if (i == value.size()) return {};
            const auto next = static_cast<unsigned char>(value[i++]);
            if ((next & 0xc0) != 0x80) return {};
            cp = (cp << 6) | (next & 63);
        }
        if (cp < minimum || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) return {};
        result += static_cast<wchar_t>(cp);
    }
    return result;
#endif
}
std::wstring startText(double instant) {
    const auto time = static_cast<std::time_t>(instant); std::tm local{};
#ifdef _WIN32
    if (localtime_s(&local, &time) != 0) return L"Встреча скоро начнётся";
#else
    if (!localtime_r(&time, &local)) return L"Встреча скоро начнётся";
#endif
    wchar_t formatted[32]{};
    std::wcsftime(formatted, 32, L"Начало в %H:%M", &local);
    return formatted;
}
}
MeetingReminderPresenter::MeetingReminderPresenter(RecordingNoticePresenter& card, NotificationPreferenceStore store)
    : card_(card), store_(std::move(store)) {}
MeetingReminderPresenter::~MeetingReminderPresenter() { retirePresented(); }
void MeetingReminderPresenter::bind(std::string owner, std::string workspace, std::string origin) {
    const auto epoch = model_.epoch(); model_.bind(std::move(owner), std::move(workspace), std::move(origin));
    if (model_.epoch() == epoch) return;
    presented_.reset(); pendingAction_.reset(); card_.resetContext();
    preferences_ = store_.load(model_.owner()); card_.setQuiet(preferences_.quiet);
}
void MeetingReminderPresenter::invalidate() { model_.invalidate(); presented_.reset(); pendingAction_.reset(); card_.resetContext(); preferences_ = {}; }
void MeetingReminderPresenter::retirePresented() {
    if (presented_) {
        CalendarReminderEvent event{}; event.eventId = presented_->eventId; event.startsAt = presented_->startsAt;
        model_.dismiss(event);
        if (card_.visible() && card_.kind() == NoticeKind::meeting && card_.id() == model_.dismissalKey(event)) card_.dismiss();
    }
    presented_.reset(); pendingAction_.reset();
}
void MeetingReminderPresenter::calendarFailed() {
    retirePresented(); model_.clearCalendar();
}
bool MeetingReminderPresenter::update(CalendarReminderSnapshot snapshot, std::uint64_t epoch) {
    bool stillCurrent = !presented_;
    if (presented_) for (const auto& event : snapshot.events) {
        if (sameTarget(model_.actionTarget(event), *presented_) && event.canSurface) stillCurrent = true;
    }
    if (!model_.update(std::move(snapshot), epoch)) return false;
    if (!stillCurrent) retirePresented();
    return true;
}
void MeetingReminderPresenter::reconcile(double now, RecordingNoticePresenter::Clock::time_point steadyNow, bool recording) {
    card_.tick(steadyNow);
    if (model_.owner().empty()) return;
    if (!store_.pruneMeetingReceipts(model_.contextKey(), now) || !preferences_.reminders || preferences_.quiet) {
        retirePresented(); return;
    }
    std::optional<CalendarReminderEvent> event;
    if (presented_) {
        event = model_.revalidate(*presented_, now, recording, preferences_.offsetMinutes);
        const bool sameCard = card_.visible() && card_.kind() == NoticeKind::meeting &&
            event && card_.id() == model_.dismissalKey(*event);
        if (!event || now >= presentedDeadline_ || steadyNow >= presentedSteadyDeadline_ ||
            card_.automaticPromptActive() || (!sameCard && (card_.visible() || !pendingAction_))) {
            retirePresented(); event.reset();
        } else if (pendingAction_) return;
    }
    const bool updating = event.has_value();
    if (!updating) {
        if (card_.automaticPromptActive() || (card_.visible() && card_.kind() != NoticeKind::preview)) return;
        event = model_.candidate(now, recording, preferences_.offsetMinutes);
    }
    if (!event) return;
    auto title = std::wstring(L"Встреча в календаре");
    if (preferences_.showTitles && event->titleAvailable) {
        title = wide(event->title);
        if (title.find_first_not_of(L" \r\n\t") == std::wstring::npos) title = L"Без названия";
    }
    NoticeContent content{NoticeKind::meeting, model_.dismissalKey(*event), std::move(title), startText(event->startsAt), {}};
    if (event->meetingLinkPresent && MeetingReminderModel::safeMeetingUrl(event->meetingUrl)) {
        content.buttons = {{L"Подключиться", NoticeAction::join}, {L"Подключиться и начать запись", NoticeAction::joinAndRecord}};
    } else content.buttons = {{L"Начать запись", NoticeAction::record}};
    const auto target = model_.actionTarget(*event);
    const auto deadline = MeetingReminderModel::deadline(*event, preferences_.offsetMinutes);
    const auto steadyDeadline = steadyNow + std::chrono::duration_cast<RecordingNoticePresenter::Clock::duration>(
        std::chrono::duration<double>(deadline - now));
    if (!updating) { presentedDeadline_ = deadline; presentedSteadyDeadline_ = steadyDeadline; }
    else { // An end/offset change may shorten, never restart an already visible card.
        presentedDeadline_ = std::min(presentedDeadline_, deadline);
        presentedSteadyDeadline_ = std::min(presentedSteadyDeadline_, steadyDeadline);
    }
    presented_ = target;
    NoticePresentationHooks hooks;
    hooks.beforeFirstShow = [this, target, event = *event, now] {
        return presented_ && sameTarget(target, *presented_) && !preferences_.quiet && preferences_.reminders &&
            store_.claimMeeting(model_.contextKey(), event, now);
    };
    hooks.onPresented = [this, target] {
        if (presented_ && sameTarget(target, *presented_) && preferences_.sound && !preferences_.quiet && onMeetingPresented)
            onMeetingPresented();
    };
    hooks.onInvalidated = [this, target] { if (presented_ && sameTarget(target, *presented_)) retirePresented(); };
    hooks.onExpired = hooks.onInvalidated;
    if (!card_.present(std::move(content), steadyNow, presentedSteadyDeadline_,
        [this, target](NoticeAction action) {
            if (!presented_ || !sameTarget(target, *presented_) || pendingAction_) return;
            pendingAction_ = action;
            if (onActionRequested) onActionRequested(target, action);
        },
        [this, target] { if (presented_ && sameTarget(target, *presented_)) retirePresented(); }, std::move(hooks))) {
        if (presented_ && sameTarget(target, *presented_)) retirePresented();
    }
}
std::string MeetingReminderPresenter::settings(const NativeSettingsBridge::NotificationRequest& request,
    double now, RecordingNoticePresenter::Clock::time_point steadyNow, bool recording) {
    using namespace NativeSettingsBridge;
    std::string message, error;
    const bool editable = !model_.owner().empty();
    if (!editable && request.action != NotificationAction::read) error = "Войдите в GRAF, чтобы изменить настройки уведомлений.";
    else if (request.action == NotificationAction::set) {
        auto next = preferences_;
        if (!applyNotificationSetting(next, request) || !store_.save(next, model_.owner())) error = "Не сохранено. Действуют прежние настройки.";
        else { preferences_ = next; card_.setQuiet(preferences_.quiet); message = "Сохранено на этом компьютере"; reconcile(now, steadyNow, recording); }
    } else if (request.action == NotificationAction::test) {
        if (card_.present({NoticeKind::preview, "preview", L"Проверка уведомлений GRAF", L"Так выглядит напоминание о встрече.", {}},
            steadyNow, steadyNow + std::chrono::seconds(6))) message = "Проверочное уведомление показано в правом верхнем углу.";
        else if (card_.occupied()) message = "Проверочное уведомление не заменило уже показанное важное сообщение.";
        else error = "Не удалось показать карточку. Повторите проверку уведомлений.";
    }
    return notificationSettingsReply(preferences_, editable, message, error);
}
std::optional<CalendarReminderEvent> MeetingReminderPresenter::completeAction(const ReminderActionTarget& target,
    NoticeAction action, double now, bool recording) {
    if (!presented_ || !sameTarget(target, *presented_) || pendingAction_ != action) return std::nullopt;
    const auto event = model_.revalidate(target, now, recording, preferences_.offsetMinutes);
    const bool allowed = event && preferences_.reminders && !preferences_.quiet && now < presentedDeadline_ &&
        RecordingNoticePresenter::Clock::now() < presentedSteadyDeadline_ &&
        !card_.automaticPromptActive() && (!card_.visible() || card_.kind() == NoticeKind::meeting) &&
        (action == NoticeAction::record || ((action == NoticeAction::join || action == NoticeAction::joinAndRecord) &&
            event->meetingLinkPresent && MeetingReminderModel::safeMeetingUrl(event->meetingUrl)));
    retirePresented();
    return allowed ? event : std::nullopt;
}
} // namespace graf::windows
