// The cabinet's settings pages ask the app the way macOS lets them ask it, and the
// page validates every answer before it shows or saves anything. These checks hold
// the two ends of that agreement: what the app accepts as a request, and what it
// sends back.
#include "../../RecApp/Web/NativeSettingsBridge.h"
#include "../../RecApp/Shell/MeetingReminderModel.h"
#include "../../RecApp/Shell/RecordingNoticePresenter.h"
#include "../../RecApp/Shell/MeetingReminderPresenter.h"

#ifdef NDEBUG
#undef NDEBUG
#endif

#include <cassert>
#include <cstdio>
#include <string>

using graf::windows::NativeSettingsBridge::Action;
using graf::windows::NativeSettingsBridge::Target;

namespace {

void testOnlyTheSettingsPageMayUseTheBridge() {
    // The route macOS bridges: the recording settings page, addressed plainly.
    assert(graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording"));
    assert(graf::windows::NativeSettingsBridge::isSettingsRoute(
        "http://127.0.0.1:8080/desktop/settings/recording"));
    // The notification settings page is also a supported native bridge route;
    // a query, a fragment and a look-alike path are not.
    assert(graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording?next=/desktop/meetings"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording#section"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(
        "https://rec.2brain.pro/desktop/settings/recording/extra"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute("/desktop/settings/recording"));
    assert(!graf::windows::NativeSettingsBridge::isSettingsRoute(""));
}

void testTheRequestVocabularyIsThePagesOwn() {
    using namespace graf::windows::NativeSettingsBridge;
    assert(actionFromToken("read") == Action::read);
    assert(actionFromToken("set") == Action::set);
    assert(actionFromToken("setAll") == Action::setAll);
    // Unknown, differently cased and empty actions are not actions.
    assert(!actionFromToken("write"));
    assert(!actionFromToken("SET"));
    assert(!actionFromToken(""));
    assert(actionToken(Action::read) == "read");
    assert(actionToken(Action::set) == "set");
    assert(actionToken(Action::setAll) == "setAll");

    // The stored preference and the page's select share these three words.
    assert(isRule("always"));
    assert(isRule("ask"));
    assert(isRule("never"));
    assert(!isRule("Always"));
    assert(!isRule("sometimes"));
    assert(!isRule(""));
}

void testTheReplyCarriesWhatThePageValidates() {
    using namespace graf::windows::NativeSettingsBridge;
    const std::vector<Target> targets{
        {"yandex-telemost", "Яндекс Телемост", "always"},
        {"zoom", "Zoom Workplace", "never"},
    };
    const auto reply = settingsReply(targets);
    // The page reads `version`, `targets[].id`, `targets[].name` and `targets[].rule`.
    assert(reply.find("\"version\":1") != std::string::npos);
    assert(reply.find("{\"id\":\"yandex-telemost\",\"name\":\"Яндекс Телемост\",\"rule\":\"always\"}") != std::string::npos);
    assert(reply.find("{\"id\":\"zoom\",\"name\":\"Zoom Workplace\",\"rule\":\"never\"}") != std::string::npos);
    // Russian text is sent as UTF-8; it is not escaped into something else.
    assert(reply.find("Яндекс") != std::string::npos);
}

void testATargetThatWouldBreakTheReplyIsLeftOut() {
    using namespace graf::windows::NativeSettingsBridge;
    // The page refuses the whole reply over one unusable row, and then it would
    // show nothing at all: a row that cannot be answered is dropped instead.
    const std::vector<Target> targets{
        {"", "Без ключа", "always"},
        {"broken-rule", "Сломанное правило", "sometimes"},
        {"good", "Рабочее приложение", "ask"},
    };
    const auto reply = settingsReply(targets);
    assert(reply.find("Без ключа") == std::string::npos);
    assert(reply.find("Сломанное правило") == std::string::npos);
    assert(reply.find("good") != std::string::npos);
    assert(reply.find("always") == std::string::npos);
    // Exactly one target, so exactly one comma-free object after the colon.
    assert(reply.find(",\"name\"") != std::string::npos);
}

void testQuotesAndControlCharactersCannotLeaveTheJson() {
    using namespace graf::windows::NativeSettingsBridge;
    const std::vector<Target> targets{{"we\"ird", "Имя \"в кавычках\"\nи перенос", "ask"}};
    const auto reply = settingsReply(targets);
    // A name that would otherwise end the string early is escaped.
    assert(reply.find("Имя \\\"в кавычках\\\"\\nи перенос") != std::string::npos);
    assert(reply.find("we\\\"ird") != std::string::npos);
    // No raw newline survived: the page parses this as one JSON document.
    assert(reply.find('\n') == std::string::npos);
}

void testARefusalIsStillAnAnswer() {
    using namespace graf::windows::NativeSettingsBridge;
    const auto reply = failureReply("Настройки не сохранены.");
    // The page checks the version before it believes anything, including a refusal.
    assert(reply.find("\"version\":1") != std::string::npos);
    assert(reply.find("\"error\":\"Настройки не сохранены.\"") != std::string::npos);
    // An empty message is never sent as an empty reason.
    const auto blank = failureReply("");
    assert(blank.find("\"error\":\"\"") == std::string::npos);
}

void testEachSettingsPageHasItsOwnRoute() {
    using namespace graf::windows::NativeSettingsBridge;
    assert(isRecordingSettingsRoute("https://rec.2brain.pro/desktop/settings/recording"));
    assert(isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    // Neither page answers for the other, and the general check accepts both.
    assert(!isRecordingSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/recording"));
    assert(isSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings/notifications?tab=1"));
    assert(!isNotificationSettingsRoute("https://rec.2brain.pro/desktop/settings"));
}

void testTheNotificationReplyIsThePlatformTruth() {
    using namespace graf::windows::NativeSettingsBridge;
    const auto reply = notificationSettingsReply({}, true);
    // The page refuses a reply that misses one of these, and then it would show
    // nothing at all, so the shape is checked here.
    assert(reply.find("\"version\":1") != std::string::npos);
    assert(reply.find("\"preferences\":{\"reminders\":true,\"showTitles\":false,\"sound\":false,\"offsetMinutes\":1}") != std::string::npos);
    assert(reply.find("\"canEdit\":true") != std::string::npos);
    assert(reply.find("\"canRequestPermission\":false") != std::string::npos);
    assert(reply.find("\"permission\":\"Windows") != std::string::npos);
    // A reason given by the app is used as it is.
    assert(notificationSettingsReply({}, false).find("\"canEdit\":false") != std::string::npos);
}

void testNotificationRequestsAndOwnerPersistence() {
    using namespace graf::windows;
    using namespace NativeSettingsBridge;
    const auto parse = [](std::string fields) {
        return parseNotificationRequest("{\"version\":1,\"nonce\":\"current\"," + fields + "}", "current");
    };
    assert(parse("\"action\":\"read\""));
    assert(parse("\"action\":\"test\""));
    assert(parse("\"action\":\"requestPermission\"")); // explicit unsupported reply
    assert(!parse("\"action\":\"read\",\"value\":true"));
    assert(!parse("\"action\":\"set\",\"field\":\"sound\",\"value\":1"));
    assert(!parse("\"action\":\"set\",\"field\":\"offsetMinutes\",\"value\":1.0"));
    assert(!parse("\"action\":\"set\",\"field\":\"offsetMinutes\",\"value\":2"));
    assert(!parse("\"action\":\"set\",\"field\":\"sound\",\"value\":true,\"extra\":0"));
    assert(!parseNotificationRequest(R"({"version":1,"nonce":"old","action":"test"})", "current"));
    assert(!parse("\"action\":\"test\",\"action\":\"read\""));
    const auto payload = [](std::string id, std::string extra = "") {
        return "{\"handler\":\"grafNotificationSettings\",\"requestId\":" + id +
            ",\"request\":{\"version\":1,\"nonce\":\"current\",\"action\":\"test\"}" + extra + "}";
    };
    assert(parseNotificationPayload(payload("1"), "current"));
    assert(!parseNotificationPayload(payload("0"), "current"));
    assert(!parseNotificationPayload(payload("1.0"), "current"));
    assert(!parseNotificationPayload(payload("-1"), "current"));
    assert(!parseNotificationPayload(payload("9007199254740992"), "current"));
    assert(!parseNotificationPayload(payload("1", ",\"extra\":true"), "current"));
    assert(!parseNotificationPayload(payload("1", ",\"requestId\":2"), "current"));
    assert(!parseNotificationPayload(payload("1"), "old"));
    std::map<std::string, std::string> saved;
    bool writes = true;
    NotificationPreferenceStore store{
        [&](std::string_view key) -> std::optional<std::string> {
            auto it = saved.find(std::string(key));
            return it == saved.end() ? std::nullopt : std::optional<std::string>(it->second);
        },
        [&](std::string_view key, std::string_view value) {
            if (!writes) return false;
            saved[std::string(key)] = value; return true;
        }};
    NotificationPreferences preferences;
    const auto edit = parse("\"action\":\"set\",\"field\":\"showTitles\",\"value\":true");
    assert(edit && applyNotificationSetting(preferences, *edit));
    assert(preferences.showTitles && preferences.offsetMinutes == 1);
    assert(!store.save(preferences, ""));
    assert(store.save(preferences, "owner-a"));
    assert(store.load("owner-a").showTitles);
    assert(!store.load("owner-b").showTitles);
    writes = false;
    preferences.showTitles = false;
    assert(!store.save(preferences, "owner-a"));
    assert(store.load("owner-a").showTitles);
    assert(saved.begin()->first.find("owner-a") == std::string::npos);
}

void testFixedReminderWindowAndRevalidation() {
    using namespace graf::windows;
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    assert(MeetingReminderModel::deadline(event) == 9'220);
    assert(!MeetingReminderModel::eligible(event, 9'099, false));
    assert(MeetingReminderModel::eligible(event, 9'100, false));
    assert(MeetingReminderModel::eligible(event, 9'219, false));
    assert(!MeetingReminderModel::eligible(event, 9'220, false));
    assert(!MeetingReminderModel::eligible(event, 9'101, true));
    MeetingReminderModel model;
    model.bind("a", "w");
    const auto epoch = model.epoch();
    assert(model.update({"a", "w", {event}}, epoch));
    auto selected = model.candidate(9'101, false);
    assert(selected && selected->eventId == "event");
    auto earlier = event; earlier.eventId = "earlier"; earlier.startsAt = 9'990;
    assert(model.update({"a", "w", {event, earlier}}, epoch));
    assert(model.candidate(9'101, false)->eventId == "earlier");
    model.dismiss(event);
    event.startsAt += 10; // moving a dismissed occurrence does not undismiss it
    assert(model.update({"a", "w", {event}}, epoch));
    assert(!model.candidate(9'120, false));
    model.bind("b", "w");
    assert(!model.update({"a", "w", {event}}, epoch));
    assert(!model.candidate(9'120, false));
    assert(model.update({"b", "w", {event}}, model.epoch()));
    assert(model.candidate(9'120, false));
    const auto target = model.actionTarget(event);
    event.startsAt += 1;
    assert(model.update({"b", "w", {event}}, model.epoch()));
    assert(!model.revalidate(target, 9'120, false)); // a stale click cannot follow a moved occurrence
    auto current = model.actionTarget(event);
    assert(model.revalidate(current, 9'120, false));
    assert(!model.revalidate(current, 9'120, true));
    event.canSurface = false;
    assert(model.update({"b", "w", {event}}, model.epoch()));
    assert(!model.revalidate(current, 9'120, false));
    model.clearCalendar();
    assert(!model.revalidate(current, 9'120, false));
    model.invalidate();
    assert(model.owner().empty());
    assert(!model.update({"b", "w", {event}}, epoch));
    // A restart during/after the expired fixed window never grants a new 120s.
    MeetingReminderModel restarted;
    restarted.bind("b", "w"); event.canSurface = true;
    assert(restarted.update({"b", "w", {event}}, restarted.epoch()));
    assert(!restarted.candidate(9'300, false));
}

void testSharedCardPriorityAndManualClose() {
    using namespace graf::windows;
    RecordingNoticePresenter presenter;
    const auto now = std::chrono::steady_clock::now();
    int closed = 0;
    assert(presenter.present({NoticeKind::preview, "preview", L"Проверка", L"", {}}, now, now + std::chrono::seconds(6)));
    assert(presenter.present({NoticeKind::meeting, "a", L"Встреча", L"", {}}, now, now + std::chrono::seconds(90), {}, [&] { ++closed; }));
    assert(!presenter.present({NoticeKind::preview, "preview", L"Проверка", L"", {}}, now, now + std::chrono::seconds(6)));
    assert(!presenter.present({NoticeKind::meeting, "b", L"Встреча", L"", {}}, now, now + std::chrono::seconds(90)));
    presenter.showShortRecordingDiscarded(now);
    assert(presenter.kind() == NoticeKind::shortRecording);
    assert(closed == 0); // replacement/expiry must not dismiss the real event
    presenter.tick(now + std::chrono::seconds(20));
    assert(!presenter.visible());
    assert(presenter.present({NoticeKind::meeting, "a", L"Встреча", L"", {}}, now, now + std::chrono::seconds(90), {}, [&] { ++closed; }));
    presenter.close();
    assert(!presenter.visible() && closed == 1);
    assert(presenter.present({NoticeKind::preview, "preview", L"Проверка", L"", {}}, now, now + std::chrono::seconds(6)));
    presenter.tick(now + std::chrono::milliseconds(5999)); assert(presenter.visible());
    presenter.tick(now + std::chrono::seconds(6)); assert(!presenter.visible());
}

void testCalendarSchemaAndSafeJoin() {
    using namespace graf::windows;
    const std::string response = R"({"notification_owner_id":"11111111-1111-4111-8111-111111111111","notification_workspace_id":"22222222-2222-4222-8222-222222222222","events":[{"event_id":"33333333-3333-4333-8333-333333333333","starts_at":"2026-09-26T12:00:00.125+03:00","ends_at":"2026-09-26T10:00:00Z","join_prompt_state":"not_due","title_state":"available","title":"Test \u0412\u0441\u0442\u0440\u0435\u0447\u0430","meeting_link_present":true,"open_meeting_url":"https://meet.example.com/room"}]})";
    const auto result = DesktopApiClient::decodeCalendarReminders(response);
    assert(result && result->events.size() == 1);
    assert(result->events[0].title == "Test Встреча");
    assert(result->events[0].canSurface);
    assert(DesktopApiClient::formatUtcInstant(static_cast<std::uint64_t>(result->events[0].startsAt * 1000)) == "2026-09-26T09:00:00Z");
    auto invalid = response;
    invalid.replace(invalid.find("2026-09-26T12"), 10, "2026-02-30");
    assert(!DesktopApiClient::decodeCalendarReminders(invalid));
    assert(!DesktopApiClient::decodeCalendarReminders(R"({"events":[]})"));
    assert(!DesktopApiClient::decodeCalendarReminders(R"({"notification_owner_id":null,"notification_workspace_id":null,"events":[]})"));
    for (const auto url : {"http://meet.example.com", "https://user@meet.example.com", "https://localhost/x", "https://127.0.0.1/x", "https://10.1.2.3/x", "https://meet.example.com/#secret", "https://meet.example.com\\evil", "https://2130706433/x"})
        assert(!MeetingReminderModel::safeMeetingUrl(url));
    assert(MeetingReminderModel::safeMeetingUrl("https://meet.example.com/room"));
    assert(MeetingReminderModel::safeMeetingUrl("https://abc.de/room"));
    assert(MeetingReminderModel::safeMeetingUrl("https://[2001:db8::1]/room"));
    assert(!MeetingReminderModel::safeMeetingUrl("https://[2001:::1]/room"));
    assert(!MeetingReminderModel::safeMeetingUrl("https://0177.0.0.1/room"));
    assert(!MeetingReminderModel::safeMeetingUrl("https://.localhost/room"));
}

void testAutomaticPromptSharesCardPriority() {
    using namespace graf::windows;
    RecordingNoticePresenter card;
    const auto now = RecordingNoticePresenter::Clock::now();
    int replaced = 0, dismissed = 0;
    assert(card.present({NoticeKind::meeting, "event", L"", L"", {}}, now,
        now + std::chrono::seconds(90), {}, [&] { ++dismissed; }));
    assert(card.acquireAutomaticPrompt(1, now, [&] { ++replaced; card.releaseAutomaticPrompt(1); return true; }));
    assert(!card.visible() && card.occupied() && card.automaticPromptActive());
    assert(dismissed == 0); // Preemption is not a dismissal of the meeting.
    assert(card.acquireAutomaticPrompt(1, now, [] { return true; }));
    assert(!card.acquireAutomaticPrompt(2, now, [] { return true; }));
    assert(!card.present({NoticeKind::preview, "preview", L"", L"", {}}, now, now + std::chrono::seconds(6)));
    assert(!card.present({NoticeKind::meeting, "event", L"", L"", {}}, now, now + std::chrono::seconds(90)));
    card.showShortRecordingDiscarded(now);
    assert(!card.visible() && card.automaticPromptActive());
    card.dismiss(); // Dismissing the native card does not release the external window.
    card.releaseAutomaticPrompt(2);
    assert(card.automaticPromptActive());
    assert(card.present({NoticeKind::problem, "problem", L"", L"", {}}, now, now + std::chrono::seconds(20)));
    assert(replaced == 1 && !card.automaticPromptActive() && card.visible());
    assert(!card.acquireAutomaticPrompt(2, now, [] { return true; }));
    card.dismiss();
    card.showShortRecordingDiscarded(now);
    assert(!card.acquireAutomaticPrompt(2, now, [] { return true; }));
    assert(card.acquireAutomaticPrompt(2, now + std::chrono::seconds(20), [] { return true; }));
    card.releaseAutomaticPrompt(1); // A late Closed event belongs to the old window.
    assert(card.automaticPromptActive());
    card.releaseAutomaticPrompt(2);
    assert(!card.occupied());
    assert(!card.acquireAutomaticPrompt(3, now, {})); // A preemptible window needs a close callback.

    MeetingReminderPresenter reminders(card, {});
    reminders.bind("owner", "workspace");
    CalendarReminderEvent event{"event", 10'000, 11'000, true, false, "", false, ""};
    assert(reminders.update({"owner", "workspace", {event}}, reminders.epoch()));
    assert(card.acquireAutomaticPrompt(3, now, [] { return true; }));
    reminders.reconcile(9'100, now, false);
    const auto reply = reminders.settings({NativeSettingsBridge::NotificationAction::test, {}, false, 1}, 9'100, now, false);
    assert(reply.find("важное сообщение") != std::string::npos && reply.find("\"error\"") == std::string::npos);
    assert(!reminders.completeAction({reminders.epoch(), "event", event.startsAt}, NoticeAction::record, 9'100, false));
    card.releaseAutomaticPrompt(3);
    reminders.reconcile(9'101, now, false);
    assert(card.visible() && card.kind() == NoticeKind::meeting); // Not consumed by the prompt.
    card.showShortRecordingDiscarded(now);
    assert(!reminders.completeAction({reminders.epoch(), "event", event.startsAt}, NoticeAction::record, 9'101, false));
    assert(card.visible() && card.kind() == NoticeKind::shortRecording);
    assert(card.present({NoticeKind::problem, "problem", L"", L"", {}}, now, now + std::chrono::seconds(20)));
    assert(!reminders.completeAction({reminders.epoch(), "event", event.startsAt}, NoticeAction::record, 9'101, false));
    assert(card.visible() && card.kind() == NoticeKind::problem);
}

void testAutomaticPromptReplacementAcknowledgement() {
    using namespace graf::windows;
    RecordingNoticePresenter card;
    const auto now = RecordingNoticePresenter::Clock::now();
    const NoticeContent problem{NoticeKind::problem, "problem", L"", L"", {}};
    int calls = 0, dismissed = 0;
    bool hidden = false;
    assert(card.acquireAutomaticPrompt(10, now, [&] {
        ++calls;
        assert(card.visible() && card.kind() == NoticeKind::problem); // Create before requesting acknowledgement.
        assert(card.automaticPromptActive()); // Lease is held until acknowledgement.
        return hidden;
    }));
    assert(!card.present(problem, now, now + std::chrono::seconds(20), {}, [&] { ++dismissed; }));
    assert(calls == 1 && dismissed == 0 && !card.visible() && card.automaticPromptActive());
    assert(!card.acquireAutomaticPrompt(11, now, [] { return true; }));
    assert(!card.present({NoticeKind::preview, "preview", L"", L"", {}}, now, now + std::chrono::seconds(6)));
    hidden = true;
    assert(card.present(problem, now, now + std::chrono::seconds(20)));
    assert(calls == 2 && card.visible() && !card.automaticPromptActive()); // Same callback survived failure.
    card.dismiss();

    assert(card.acquireAutomaticPrompt(11, now, [&] {
        card.releaseAutomaticPrompt(11); // Synchronous Closed already released this generation.
        return true;
    }));
    assert(card.present(problem, now, now + std::chrono::seconds(20)));
    assert(card.visible() && !card.automaticPromptActive());
    card.dismiss();

    int newerCalls = 0;
    assert(card.acquireAutomaticPrompt(12, now, [&] {
        card.releaseAutomaticPrompt(12);
        card.dismiss(); // Reentrant UI removes the replacement before opening a newer prompt.
        assert(card.acquireAutomaticPrompt(13, now, [&] { ++newerCalls; return false; }));
        return true;
    }));
    assert(!card.present(problem, now, now + std::chrono::seconds(20)));
    card.releaseAutomaticPrompt(12);
    assert(card.automaticPromptActive());
    assert(!card.present(problem, now, now + std::chrono::seconds(20)));
    assert(newerCalls == 1 && card.automaticPromptActive() && !card.visible());
    card.releaseAutomaticPrompt(13);
}

void testReminderAuthExpiryPropagation() {
    using namespace graf::windows;
    for (const auto invalid : {"", "-1", "+1", " 123", "123 ", "1.2", "1e9", "9223372036854775808", "9999999999999999999", "12345678901234567890"})
        assert(!DesktopApiClient::calendarAuthExpiryFromHeader(invalid));
    assert(DesktopApiClient::calendarAuthExpiryFromHeader("1800000000") == 1'800'000'000);
    assert(DesktopApiClient::calendarAuthExpiryFromHeader("9223372036854775807") == INT64_MAX);
    CalendarReminderResponse response{200, std::nullopt};
    response.inheritAuthExpiry(2000);
    assert(response.renewedSessionExpiry(1000) == 2000);
    response.authExpiresAt = 3000;
    response.inheritAuthExpiry(4000); // The later calendar response owns its header.
    assert(response.renewedSessionExpiry(1000) == 3000);
    assert(!response.renewedSessionExpiry(3000));
    for (auto status : {0u, 429u, 503u}) {
        response = {status, std::nullopt};
        response.inheritAuthExpiry(2000); // A valid context header survives a calendar failure.
        assert(response.renewedSessionExpiry(1000) == 2000);
    }
    for (auto status : {401u, 403u}) {
        response = {status, std::nullopt, 3000};
        response.inheritAuthExpiry(2000);
        assert(!response.renewedSessionExpiry(1000));
    }
    ReminderRequestIdentity request{7, 11, "synthetic-session"};
    assert(request.matches(7, 11, "synthetic-session"));
    assert(!request.matches(8, 11, "synthetic-session"));
    assert(!request.matches(7, 12, "synthetic-session"));
    assert(!request.matches(7, 11, "replacement-session"));
    assert(!request.matches(7, 11, ""));
    request = {};
    assert(!request.matches(0, 0, ""));
}

void testMeetingUrlIpLiteralSyntax() {
    using graf::windows::MeetingReminderModel;
    for (const auto url : {
        "https://[2001::db8:]/room", "https://[:2001::db8]/room",
        "https://[2001::db8::1]/room", "https://[2001:db8:0:0:0:0:1]/room",
        "https://[2001:db8:0:0:0:0:0:0:1]/room", "https://[2001:db8::12345]/room",
        "https://[2001:db8::gg]/room", "https://[::ffff:192.0.2.999]/room",
        "https://[2001:db8::1]extra/room", "https://[2001:db8::1]:0/room",
        "https://[2001:db8::1]:65536/room", "https://[fe80::1%25en0]/room",
        "https://127.0.0.1/room", "https://10.255.255.255/room",
        "https://172.16.0.1/room", "https://172.31.255.255/room",
        "https://192.168.1.1/room", "https://0.0.0.0/room",
        "https://192.000.2.1/room", "https://256.0.2.1/room",
        "https://192.0.2/room", "https://3221225985/room",
        "https://0xc0000201/room", "https://0xc0.0.2.1/room"}) {
        assert(!MeetingReminderModel::safeMeetingUrl(url));
    }
    for (const auto url : {
        "https://[2001:db8::1]/room", "https://[2001:DB8:0:0:0:0:0:1]:443/room",
        "https://[2001:db8::]/room", "https://[::ffff:192.0.2.1]/room",
        "https://[2001:db8::192.0.2.1]:65535/room",
        "https://192.0.2.1/room", "https://172.15.255.255/room",
        "https://172.32.0.1/room", "https://192.169.0.1:443/room"}) {
        assert(MeetingReminderModel::safeMeetingUrl(url));
    }
}

void testReminderPresenterNeverConsumesRealEventsForPreview() {
    using namespace graf::windows;
    using namespace NativeSettingsBridge;
    std::map<std::string, std::string> disk;
    bool writeAllowed = true;
    NotificationPreferenceStore store{
        [&](std::string_view key) -> std::optional<std::string> { auto it = disk.find(std::string(key)); return it == disk.end() ? std::nullopt : std::optional<std::string>(it->second); },
        [&](std::string_view key, std::string_view value) { if (!writeAllowed) return false; disk[std::string(key)] = value; return true; }};
    RecordingNoticePresenter card;
    MeetingReminderPresenter presenter(card, store);
    auto now = RecordingNoticePresenter::Clock::now();
    const NotificationRequest preview{NotificationAction::test, {}, false, 1};
    assert(presenter.settings(preview, 9'100, now, false).find("\"error\"") != std::string::npos);
    assert(!card.visible());
    presenter.bind("a", "w");
    CalendarReminderEvent event{"event", 10'000, 11'000, true, true, "Синтетическая встреча", true, "https://meet.example.com/current"};
    assert(presenter.update({"a", "w", {event}}, presenter.epoch()));
    (void)presenter.settings(preview, 9'099, now, false);
    assert(card.visible() && card.kind() == NoticeKind::preview);
    presenter.reconcile(9'100, now, false);
    assert(card.kind() == NoticeKind::meeting && card.content().title == L"Встреча в календаре");
    (void)presenter.settings(preview, 9'100, now, false);
    assert(card.kind() == NoticeKind::meeting);
    auto edit = NotificationRequest{NotificationAction::set, "showTitles", true, 1};
    assert(presenter.settings(edit, 9'100, now, false).find("\"error\"") == std::string::npos);
    assert(card.content().title == L"Синтетическая встреча");
    writeAllowed = false; edit.booleanValue = false;
    assert(presenter.settings(edit, 9'100, now, false).find("\"error\"") != std::string::npos);
    assert(card.content().title == L"Синтетическая встреча");
    std::optional<ReminderActionTarget> clicked;
    presenter.onActionRequested = [&](auto target, auto action) { assert(action == NoticeAction::join); clicked = target; };
    card.invoke(NoticeAction::join); assert(clicked);
    // Fresh response changes the URL; only that URL is allowed on completion.
    event.meetingUrl = "https://meet.example.com/revalidated";
    assert(presenter.update({"a", "w", {event}}, presenter.epoch()));
    const auto allowed = presenter.completeAction(*clicked, NoticeAction::join, 9'101, false);
    assert(allowed && allowed->meetingUrl == event.meetingUrl);
    assert(!presenter.completeAction(*clicked, NoticeAction::join, 9'101, false));
    presenter.reconcile(9'102, now, false); assert(!card.visible());
    // Preview does not clear dismissal, nor refresh the calendar, nor alter settings.
    (void)presenter.settings(preview, 9'102, now, false);
    presenter.reconcile(9'108, now + std::chrono::seconds(6), false); assert(!card.visible());
    presenter.invalidate(); presenter.bind("a", "w");
    assert(presenter.update({"a", "w", {event}}, presenter.epoch()));
    presenter.reconcile(9'109, now, false); assert(!card.visible());
    presenter.bind("b", "w");
    assert(presenter.update({"b", "w", {event}}, presenter.epoch()));
    presenter.reconcile(9'109, now, false); assert(card.visible());
    presenter.calendarFailed(); assert(!card.visible());
    assert(!presenter.completeAction(*clicked, NoticeAction::record, 9'110, false));
    // Test remains six seconds even when meeting reminders are disabled.
    writeAllowed = true;
    (void)presenter.settings({NotificationAction::set, "reminders", false, 1}, 9'110, now, false);
    (void)presenter.settings(preview, 9'110, now, false);
    presenter.reconcile(9'115, now + std::chrono::seconds(5), false); assert(card.visible());
    presenter.reconcile(9'116, now + std::chrono::seconds(6), false); assert(!card.visible());
    presenter.invalidate(); assert(!card.visible());
    // A restarted presenter reloads persisted preferences but never old calendar data.
    MeetingReminderPresenter restarted(card, store); restarted.bind("a", "w");
    assert(restarted.settings({}, 9'110, now, false).find("\"showTitles\":true") != std::string::npos);
    restarted.reconcile(9'110, now, false); assert(!card.visible());
}

void testTheShimAsksOnlyWhatTheAppCanAnswer() {
    const auto script = std::string(graf::windows::NativeSettingsBridge::documentScript());
    // The page calls exactly this handler and awaits the promise the shim returns.
    assert(script.find("window.webkit.messageHandlers.grafRecordingSettings") != std::string::npos);
    assert(script.find("graf:native-settings") != std::string::npos);
    assert(script.find("graf:native-settings-reply") != std::string::npos);
    assert(script.find("__grafNativeSettingsInstalled") != std::string::npos);
    // Both settings pages the app can answer are advertised, and only those.
    assert(script.find("window.webkit.messageHandlers.grafNotificationSettings") != std::string::npos);
    // Installing it twice would replace a page's own pending requests.
    assert(script.find("if (window.__grafNativeSettingsInstalled) return;") != std::string::npos);
}

void testTheSharedSettingsPageStopsClaimingToBeAMac() {
    const auto script = std::string(graf::windows::NativeSettingsBridge::documentScript());
    // Общая серверная страница написана для macOS. На Windows это неправда, и
    // оболочка приводит слова и кнопку в порядок, не трогая общую страницу.
    assert(script.find("platformWords") != std::string::npos);
    assert(script.find("['На этом Mac', 'На этом компьютере']") != std::string::npos);
    assert(script.find("['Настройки macOS', 'Настройки Windows']") != std::string::npos);
    assert(script.find("['разрешение macOS', 'разрешение Windows']") != std::string::npos);
    assert(script.find("'настройки этого компьютера'") != std::string::npos);
    // Живая проверка 2026-09-19: заголовок страницы «На этом Mac» стоит вне формы
    // настроек, поэтому обход идёт по всему документу — иначе заголовок, легенда
    // раздела, карточка навигации и примечание для страниц без скриптов остаются
    // маковскими.
    assert(script.find("const root = document.body;") != std::string::npos);
    assert(script.find("['Правила автозаписи на Mac', 'Правила автозаписи в Windows']") != std::string::npos);
    assert(script.find("['Уведомления на этом Mac', 'Уведомления на этом компьютере']") != std::string::npos);
    assert(script.find("['изменить уведомления Mac', 'изменить уведомления в приложении']") != std::string::npos);
    // System permission is not needed; the local test is now functional.
    assert(script.find("[data-local-notification-action=\"openSystemSettings\"]") != std::string::npos);
    assert(script.find("[data-local-notification-action=\"test\"]") == std::string::npos);
    assert(script.find("button.hidden = true") != std::string::npos);
    // Живая проверка 2026-09-19 (раунд 52) показала, что одной подписки на события
    // мало: оболочка ставится, когда документ уже идёт. Поэтому правка запускается
    // сразу, на событии документа, на подстановке и ещё дважды по времени.
    assert(script.find("const runAdaptation = () => {") != std::string::npos);
    assert(script.find("document.addEventListener('DOMContentLoaded', runAdaptation)") != std::string::npos);
    assert(script.find("document.addEventListener('htmx:afterSwap', adaptPlatformWords)") != std::string::npos);
    assert(script.find("setTimeout(adaptPlatformWords, 120)") != std::string::npos);
    assert(script.find("setTimeout(adaptPlatformWords, 600)") != std::string::npos);
    assert(script.find("action: 'diag_'") == std::string::npos);
    assert(script.find("window.dispatchEvent(new CustomEvent('graf:native-settings'") != std::string::npos);
}

} // namespace

int main() {
    testOnlyTheSettingsPageMayUseTheBridge();
    testTheRequestVocabularyIsThePagesOwn();
    testTheReplyCarriesWhatThePageValidates();
    testATargetThatWouldBreakTheReplyIsLeftOut();
    testQuotesAndControlCharactersCannotLeaveTheJson();
    testARefusalIsStillAnAnswer();
    testEachSettingsPageHasItsOwnRoute();
    testTheSharedSettingsPageStopsClaimingToBeAMac();
    testTheNotificationReplyIsThePlatformTruth();
    testNotificationRequestsAndOwnerPersistence();
    testFixedReminderWindowAndRevalidation();
    testSharedCardPriorityAndManualClose();
    testCalendarSchemaAndSafeJoin();
    testMeetingUrlIpLiteralSyntax();
    testAutomaticPromptSharesCardPriority();
    testAutomaticPromptReplacementAcknowledgement();
    testReminderAuthExpiryPropagation();
    testReminderPresenterNeverConsumesRealEventsForPreview();
    testTheShimAsksOnlyWhatTheAppCanAnswer();
    std::puts("NativeSettingsBridgeTests passed");
    return 0;
}
