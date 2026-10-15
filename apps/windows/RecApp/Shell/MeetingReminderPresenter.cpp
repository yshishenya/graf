#include "MeetingReminderPresenter.h"
#include <ctime>
#include <algorithm>
#include <cmath>
#include <cwchar>
#include <limits>
#include <utility>
#ifdef _WIN32
#include <windows.h>
#include <winrt/Windows.Globalization.h>
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
std::optional<std::wstring> MeetingReminderPresenter::upcomingTime(double instant,
    std::string_view preferredZone, bool allDay, bool showTime) {
    if (!std::isfinite(instant) || instant < 0 || instant >= 253402300800.0 || preferredZone.size() > 100 ||
        (!preferredZone.empty() && preferredZone != "UTC" && preferredZone.find('/') == std::string_view::npos) ||
        std::any_of(preferredZone.begin(), preferredZone.end(), [](unsigned char c) { return c <= 0x20 || c >= 0x7f; }))
        return std::nullopt;
    if (!showTime) return L"";
    if (allDay) return L"Весь день";
    int hour = 0, minute = 0;
#ifdef _WIN32
    try {
        using namespace winrt::Windows::Globalization;
        Calendar calendar;
        calendar.ChangeCalendarSystem(CalendarIdentifiers::Gregorian());
        calendar.ChangeClock(ClockIdentifiers::TwentyFourHour());
        if (!preferredZone.empty()) calendar.ChangeTimeZone(winrt::to_hstring(preferredZone));
        // HH:mm needs whole seconds. Add the 1601 epoch offset as integers:
        // MSVC's double-sized long double would round across minute boundaries.
        const auto seconds = static_cast<std::int64_t>(std::floor(instant));
        const auto ticks = seconds * 10000000LL + 116444736000000000LL;
        calendar.SetDateTime(winrt::Windows::Foundation::DateTime{winrt::clock::duration{ticks}});
        hour = calendar.Hour(); minute = calendar.Minute();
    } catch (...) { return std::nullopt; }
#else
    // Portable tests may cover UTC/system only, never emulate Windows IANA/DST.
    if (!preferredZone.empty() && preferredZone != "UTC") return std::nullopt;
    if (instant >= static_cast<double>(std::numeric_limits<std::time_t>::max())) return std::nullopt;
    const auto time = static_cast<std::time_t>(instant); std::tm value{};
    if (!(preferredZone.empty() ? localtime_r(&time, &value) : gmtime_r(&time, &value))) return std::nullopt;
    hour = value.tm_hour; minute = value.tm_min;
#endif
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return std::nullopt;
    wchar_t label[6]{};
    if (std::swprintf(label, 6, L"%02d:%02d", hour, minute) != 5) return std::nullopt;
    return std::wstring(label);
}
MeetingReminderPresenter::MeetingReminderPresenter(RecordingNoticePresenter& card, NotificationPreferenceStore store)
    : card_(card), store_(std::move(store)) {}
MeetingReminderPresenter::~MeetingReminderPresenter() { retirePresented(); }
std::optional<RecordingNoticePresenter::Clock::time_point> MeetingReminderPresenter::upcomingExpiry(
    double endsAt, double wallNow, RecordingNoticePresenter::Clock::time_point steadyNow) {
    using Clock = RecordingNoticePresenter::Clock;
    if (!std::isfinite(endsAt) || !std::isfinite(wallNow)) return std::nullopt;
    const auto remaining = endsAt - wallNow;
    if (!std::isfinite(remaining) || remaining <= 0) return std::nullopt;
    const long double ticks = std::floor(static_cast<long double>(remaining) * Clock::period::den / Clock::period::num);
    // MSVC's long double is double: reject its rounded-up signed maximum before casting.
    const auto limit = std::nextafter(static_cast<double>(std::numeric_limits<Clock::duration::rep>::max()), 0.0);
    if (ticks < 1 || ticks > limit) return std::nullopt;
    const Clock::duration duration{static_cast<Clock::duration::rep>(ticks)};
    if (steadyNow > Clock::time_point::max() - duration) return std::nullopt;
    return steadyNow + duration;
}
std::optional<std::vector<UpcomingMeetingRow>> MeetingReminderPresenter::upcomingRows(
    double now, std::string_view preferredZone) const {
    if (!std::isfinite(now)) return std::nullopt;
    const auto snapshot = model_.upcoming();
    if (!snapshot) return std::nullopt;
    std::vector<UpcomingMeetingRow> rows;
    rows.reserve(snapshot->events.size());
    for (auto event : snapshot->events) {
        const auto time = upcomingTime(event.startsAt, preferredZone, event.allDay, snapshot->showUpcomingTime);
        if (!time) return std::nullopt;
        auto title = std::wstring(L"Встреча");
        if (snapshot->showUpcomingTitle && event.titleAvailable && event.title.size() <= 4096) {
            const auto decoded = wide(event.title);
            // Match Mac's whitespace-only empty title without a process-global locale.
            if (event.title.empty() || !decoded.empty()) {
                title = decoded.find_first_not_of(L" \t\r\n\v\f\u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000") == std::wstring::npos
                    ? L"Без названия" : decoded;
            }
        }
        const bool enabled = model_.upcomingCurrent(event, model_.epoch(), now);
        event.title.clear(); event.titleAvailable = false; // Do not duplicate private/display title in the target.
        rows.push_back({std::move(event), model_.epoch(), time->empty() ? std::move(title) : *time + L" · " + title, enabled});
    }
    return rows;
}
void MeetingReminderPresenter::bind(std::string owner, std::string workspace, std::string origin) {
    const auto epoch = model_.epoch(); model_.bind(std::move(owner), std::move(workspace), std::move(origin));
    if (model_.epoch() == epoch) return;
    presented_.reset(); pendingAction_.reset(); failedJoinUntil_.reset(); joinFailure_.clear(); card_.resetContext();
    preferences_ = store_.load(model_.owner()); card_.setQuiet(preferences_.quiet);
}
void MeetingReminderPresenter::invalidate() { model_.invalidate(); presented_.reset(); pendingAction_.reset(); failedJoinUntil_.reset(); joinFailure_.clear(); card_.resetContext(); preferences_ = {}; }
void MeetingReminderPresenter::retirePresented() {
    if (presented_) {
        CalendarReminderEvent event{}; event.eventId = presented_->eventId; event.startsAt = presented_->startsAt;
        model_.dismiss(event);
        if (card_.visible() && card_.kind() == NoticeKind::meeting && card_.id() == model_.dismissalKey(event)) card_.dismiss();
    }
    presented_.reset(); pendingAction_.reset(); failedJoinUntil_.reset(); joinFailure_.clear();
}
void MeetingReminderPresenter::calendarFailed() {
    model_.invalidateUpcoming();
    if (failedJoinUntil_ && RecordingNoticePresenter::Clock::now() < *failedJoinUntil_ &&
        presented_ && card_.visible() && card_.kind() == NoticeKind::meeting) return;
    retirePresented(); model_.clearCalendar();
}
bool MeetingReminderPresenter::update(CalendarReminderSnapshot snapshot, std::uint64_t epoch) {
    bool stillCurrent = !presented_;
    if (presented_) for (const auto& event : snapshot.events) {
        if (sameTarget(model_.actionTarget(event), *presented_) && event.canSurface) stillCurrent = true;
    }
    if (!model_.update(std::move(snapshot), epoch)) return false;
    if (!stillCurrent) retirePresented();
    else { failedJoinUntil_.reset(); joinFailure_.clear(); }
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
            (failedJoinUntil_ && steadyNow >= *failedJoinUntil_) ||
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
    NoticeContent content{NoticeKind::meeting, model_.dismissalKey(*event), std::move(title),
        joinFailure_.empty() ? startText(event->startsAt) : joinFailure_, {}};
    if (event->meetingLinkPresent && MeetingReminderModel::safeMeetingUrl(event->meetingUrl)) {
        content.buttons = {{joinFailure_.empty() ? L"Подключиться" : L"Повторить подключение", NoticeAction::join},
            {L"Подключиться и начать запись", NoticeAction::joinAndRecord}};
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
    if (!pendingActionExpiry(target, action, now, recording)) return std::nullopt;
    const auto event = model_.revalidate(target, now, recording, preferences_.offsetMinutes);
    retirePresented();
    return event;
}
std::optional<RecordingNoticePresenter::Clock::time_point> MeetingReminderPresenter::pendingActionExpiry(
    const ReminderActionTarget& target, NoticeAction action, double now, bool recording) const {
    if (!presented_ || !sameTarget(target, *presented_) || pendingAction_ != action) return std::nullopt;
    const auto event = model_.revalidate(target, now, recording, preferences_.offsetMinutes);
    const bool allowed = event && preferences_.reminders && !preferences_.quiet && now < presentedDeadline_ &&
        RecordingNoticePresenter::Clock::now() < presentedSteadyDeadline_ &&
        (!failedJoinUntil_ || RecordingNoticePresenter::Clock::now() < *failedJoinUntil_) &&
        !card_.automaticPromptActive() &&
        (action == NoticeAction::record ? !card_.visible() :
            card_.visible() && card_.kind() == NoticeKind::meeting && card_.id() == model_.dismissalKey(*event)) &&
        (action == NoticeAction::record || ((action == NoticeAction::join || action == NoticeAction::joinAndRecord) &&
            event->meetingLinkPresent && MeetingReminderModel::safeMeetingUrl(event->meetingUrl)));
    if (!allowed) return std::nullopt;
    return failedJoinUntil_ ? std::min(presentedSteadyDeadline_, *failedJoinUntil_) : presentedSteadyDeadline_;
}
void MeetingReminderPresenter::failAction(const ReminderActionTarget& target, NoticeAction action,
    CalendarJoinReason reason, double now, bool recording) {
    if (!pendingActionExpiry(target, action, now, recording)) return;
    if (reason == CalendarJoinReason::authRequired || reason == CalendarJoinReason::eventUnavailable ||
        reason == CalendarJoinReason::stale || reason == CalendarJoinReason::cancelled) { retirePresented(); return; }
    pendingAction_.reset();
    const auto until = std::min(presentedSteadyDeadline_, RecordingNoticePresenter::Clock::now() + std::chrono::minutes(5));
    failedJoinUntil_ = failedJoinUntil_ ? std::min(*failedJoinUntil_, until) : until;
    joinFailure_ = reason == CalendarJoinReason::busy ? L"Подключение ещё завершается. Повторите после завершения." :
        L"Не удалось подключиться. Повторите подключение или откройте календарь GRAF.";
    reconcile(now, RecordingNoticePresenter::Clock::now(), recording);
}
bool MeetingReminderPresenter::handoffRecordingCurrent(const ReminderActionTarget& target, double now, bool recording) const {
    return !presented_ && !pendingAction_ && !card_.visible() && !card_.automaticPromptActive() &&
        preferences_.reminders && !preferences_.quiet && model_.matchesHandoffTarget(target, now, recording, preferences_.offsetMinutes);
}
} // namespace graf::windows
