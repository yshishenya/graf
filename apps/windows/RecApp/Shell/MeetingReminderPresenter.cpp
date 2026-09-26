#include "MeetingReminderPresenter.h"
#include <ctime>
#include <utility>
#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {
namespace {
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
void MeetingReminderPresenter::bind(std::string owner, std::string workspace) {
    const auto epoch = model_.epoch(); model_.bind(std::move(owner), std::move(workspace));
    if (model_.epoch() == epoch) return;
    card_.dismiss(); presented_.reset(); preferences_ = store_.load(model_.owner());
}
void MeetingReminderPresenter::invalidate() { model_.invalidate(); card_.dismiss(); presented_.reset(); preferences_ = {}; }
void MeetingReminderPresenter::calendarFailed() {
    model_.clearCalendar(); presented_.reset();
    if (card_.visible() && card_.kind() == NoticeKind::meeting) card_.dismiss();
}
bool MeetingReminderPresenter::update(CalendarReminderSnapshot snapshot, std::uint64_t epoch) {
    return model_.update(std::move(snapshot), epoch);
}
void MeetingReminderPresenter::reconcile(double now, RecordingNoticePresenter::Clock::time_point steadyNow, bool recording) {
    card_.tick(steadyNow);
    if (model_.owner().empty() || !preferences_.reminders) {
        if (card_.visible() && card_.kind() == NoticeKind::meeting) card_.dismiss();
        presented_.reset(); return;
    }
    if (card_.visible() && card_.kind() == NoticeKind::meeting &&
        (!presented_ || !model_.revalidate(*presented_, now, recording))) { card_.dismiss(); presented_.reset(); }
    const auto event = model_.candidate(now, recording);
    if (!event) return;
    auto title = std::wstring(L"Встреча в календаре");
    if (preferences_.showTitles && event->titleAvailable) {
        title = wide(event->title);
        if (title.find_first_not_of(L" \r\n\t") == std::wstring::npos) title = L"Без названия";
    }
    NoticeContent content{NoticeKind::meeting, model_.dismissalKey(*event), std::move(title), startText(event->startsAt), {}};
    if (MeetingReminderModel::safeMeetingUrl(event->meetingUrl)) {
        content.buttons = {{L"Подключиться и начать запись", NoticeAction::joinAndRecord}, {L"Подключиться", NoticeAction::join}};
    } else content.buttons = {{L"Начать запись", NoticeAction::record}};
    const auto target = model_.actionTarget(*event);
    const auto deadline = steadyNow + std::chrono::duration_cast<RecordingNoticePresenter::Clock::duration>(
        std::chrono::duration<double>(MeetingReminderModel::deadline(*event) - now));
    if (card_.present(std::move(content), steadyNow, deadline,
        [this, target](NoticeAction action) { if (onActionRequested) onActionRequested(target, action); },
        [this, event = *event] { model_.dismiss(event); presented_.reset(); })) presented_ = target;
}
std::string MeetingReminderPresenter::settings(const NativeSettingsBridge::NotificationRequest& request,
    double now, RecordingNoticePresenter::Clock::time_point steadyNow, bool recording) {
    using namespace NativeSettingsBridge;
    std::string message, error;
    const bool editable = !model_.owner().empty();
    if (request.action == NotificationAction::requestPermission || request.action == NotificationAction::openSystemSettings)
        error = "Системное разрешение для карточек GRAF не требуется.";
    else if (!editable && request.action != NotificationAction::read) error = "Войдите в GRAF, чтобы изменить настройки уведомлений.";
    else if (request.action == NotificationAction::set) {
        auto next = preferences_;
        if (!applyNotificationSetting(next, request) || !store_.save(next, model_.owner())) error = "Не сохранено. Действуют прежние настройки.";
        else { preferences_ = next; message = "Сохранено на этом компьютере"; reconcile(now, steadyNow, recording); }
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
    if (!preferences_.reminders || card_.automaticPromptActive() ||
        (card_.visible() && static_cast<int>(card_.kind()) > static_cast<int>(NoticeKind::meeting))) return std::nullopt;
    const auto event = model_.revalidate(target, now, recording);
    if (!event || (action != NoticeAction::record && (!event->meetingLinkPresent || !MeetingReminderModel::safeMeetingUrl(event->meetingUrl)))) return std::nullopt;
    model_.dismiss(*event); card_.dismiss(); presented_.reset(); return event;
}
} // namespace graf::windows
