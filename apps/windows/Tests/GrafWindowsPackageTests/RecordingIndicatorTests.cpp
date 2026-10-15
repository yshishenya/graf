#include "../../RecApp/Shell/RecordingIndicator.h"
#include "../../RecApp/Shell/ShellClosePolicy.h"
#include "../../RecApp/Shell/WindowsTray.h"
#include "../../RecApp/Shell/MeetingReminderPresenter.h"
#include "../../RecApp/Core/WindowsDesktopSession.h"
#include "../GrafWindowsCoreTests/AutomaticRecordingTestSupport.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <ctime>
#include <limits>
#include <cmath>
#include <tuple>
#ifdef _WIN32
#include <winrt/base.h>
#include <oleacc.h>
#endif

namespace {

#ifdef _WIN32
// Actual OS menu-loop fixture, using only public tray APIs and our own HWNDs.
// No production seam, direct calendar callback, device read or real target launch.
struct NativeCalendarPopup {
    enum class Case { select, unchanged, replacement, account, time, handler, reentry, destroy, callbackDestroy, disabled };
    inline static NativeCalendarPopup* active = nullptr;
    Case scenario;
    HWND control = nullptr, trayWindow = nullptr;
    WNDPROC originalProcedure = nullptr;
    HMENU menu = nullptr;
    std::unique_ptr<graf::windows::WindowsTray> tray;
    std::vector<graf::windows::UpcomingMeetingRow> rows;
    std::optional<graf::windows::UpcomingMeetingRow> selected;
    unsigned initializations = 0, callbacks = 0, replacements = 0, highlighted = 0, navigationSteps = 0;
    bool timerHandled = false, menuObserved = false, timedOut = false, dispatchFailed = false, navigating = false;

    static LRESULT CALLBACK controlProcedure(HWND window, UINT message, WPARAM wParam, LPARAM lParam) {
        if (message == WM_NCCREATE) SetWindowLongPtrW(window, GWLP_USERDATA,
            reinterpret_cast<LONG_PTR>(reinterpret_cast<CREATESTRUCTW*>(lParam)->lpCreateParams));
        auto* self = reinterpret_cast<NativeCalendarPopup*>(GetWindowLongPtrW(window, GWLP_USERDATA));
        if (self && message == WM_TIMER) {
            if (wParam == 2) { self->timedOut = true; EndMenu(); return 0; }
            try { self->onTimer(); }
            catch (...) { self->dispatchFailed = true; EndMenu(); }
            return 0;
        }
        return DefWindowProcW(window, message, wParam, lParam);
    }
    static LRESULT CALLBACK trayProcedure(HWND window, UINT message, WPARAM wParam, LPARAM lParam) {
        const auto self = active;
        const auto original = self->originalProcedure;
        // TPM_NONOTIFY suppresses WM_INITMENUPOPUP. Owner-drawn menus still
        // supply their real HMENU in DRAWITEMSTRUCT::hwndItem.
        if (message == WM_DRAWITEM && lParam) {
            const auto draw = reinterpret_cast<DRAWITEMSTRUCT*>(lParam);
            if (draw->CtlType == ODT_MENU && (draw->itemState & ODS_SELECTED)) self->highlighted = draw->itemID;
            if (draw->CtlType == ODT_MENU && !self->menu) {
                ++self->initializations;
                self->menu = reinterpret_cast<HMENU>(draw->hwndItem);
                for (unsigned i = 0; i < 12; ++i) {
                    MENUITEMINFOW item{}; item.cbSize = sizeof(item); item.fMask = MIIM_DATA | MIIM_STATE;
                    assert(GetMenuItemInfoW(self->menu, 100 + i, FALSE, &item));
                    const auto name = reinterpret_cast<MSAAMENUINFO*>(item.dwItemData);
                    assert(name && name->dwMSAASignature == MSAA_MENU_SIG);
                    assert(name->cchWText == self->rows[i].label.size());
                    assert(std::wstring(name->pszWText, name->cchWText) == self->rows[i].label);
                    const bool enabled = i == 1 && self->scenario != Case::disabled;
                    assert(((item.fState & MFS_DISABLED) == 0) == enabled);
                }
                MENUITEMINFOW extra{}; extra.cbSize = sizeof(extra); extra.fMask = MIIM_ID;
                assert(!GetMenuItemInfoW(self->menu, 112, FALSE, &extra)); // Real menu prefix, not a projection-only check.
            }
        }
        return CallWindowProcW(original, window, message, wParam, lParam);
    }
    explicit NativeCalendarPopup(Case value) : scenario(value) {
        assert(!active);
        const auto instance = GetModuleHandleW(nullptr);
        assert(LoadIconW(instance, MAKEINTRESOURCEW(1))); // Exactly the production resource, no constructor bypass.
        WNDCLASSW definition{}; definition.hInstance = instance;
        definition.lpfnWndProc = controlProcedure; definition.lpszClassName = L"GRAF.F200.NativePopupTest";
        assert(RegisterClassW(&definition) || GetLastError() == ERROR_CLASS_ALREADY_EXISTS);
        control = CreateWindowExW(WS_EX_TOOLWINDOW, definition.lpszClassName, L"Synthetic popup test",
            WS_POPUP, 0, 0, 0, 0, nullptr, nullptr, instance, this);
        assert(control);
        tray = std::make_unique<graf::windows::WindowsTray>(reinterpret_cast<std::uintptr_t>(control),
            [] {}, [] {}, [] {});
        assert(tray->available() && tray->interactionPermit().allowed);
        assert(EnumThreadWindows(GetCurrentThreadId(), [](HWND window, LPARAM parameter) -> BOOL {
            const auto fixture = reinterpret_cast<NativeCalendarPopup*>(parameter);
            wchar_t name[64]{};
            if (GetClassNameW(window, name, 64) && std::wcscmp(name, L"GRAF.WindowsTray") == 0 &&
                GetWindow(window, GW_OWNER) == fixture->control) fixture->trayWindow = window;
            return TRUE;
        }, reinterpret_cast<LPARAM>(this)) && trayWindow);
        active = this;
        originalProcedure = reinterpret_cast<WNDPROC>(SetWindowLongPtrW(trayWindow, GWLP_WNDPROC,
            reinterpret_cast<LONG_PTR>(trayProcedure)));
        assert(originalProcedure);
        for (unsigned i = 0; i < 13; ++i) {
            char eventId[37]{};
            std::snprintf(eventId, sizeof(eventId), "%08x-1111-4111-8111-000000000000", i + 1);
            rows.push_back({{eventId, 60, 3600, false, false, "", i == 1,
                i == 1 ? "https://meet.example/synthetic" : ""}, 7, L"Synthetic row " + std::to_wstring(i), i == 1});
        }
        rows[1].label = L"10:00 · Synthetic & full accessible title " + std::wstring(4096, L'x');
        if (scenario != Case::disabled) tray->setCalendarHandler([this](auto row) {
            assert(timerHandled && menuObserved && !timedOut && !selected);
            GUITHREADINFO info{}; info.cbSize = sizeof(info);
            assert(GetGUIThreadInfo(GetCurrentThreadId(), &info) && !(info.flags & GUI_INMENUMODE));
            selected = std::move(row); ++callbacks;
            if (scenario == Case::callbackDestroy) tray.reset();
        });
        tray->setCalendarState(rows, 1, 1, true, true);
        tray->setNotificationState(false, std::vector<std::wstring>(51, L"Synthetic neutral history"));
    }
    ~NativeCalendarPopup() {
        KillTimer(control, 1); KillTimer(control, 2);
        tray.reset(); // Fixture and saved WndProc remain alive throughout teardown.
        active = nullptr;
        DestroyWindow(control);
    }
    void selectByKeyboard() {
        // Navigate the real menu, and press Enter only after Windows highlights
        // row101. Disabled rows need not be skipped by the platform.
        navigating = true;
        assert(SetTimer(control, 1, 30, nullptr));
        if (!PostMessageW(trayWindow, WM_KEYDOWN, VK_HOME, 1)) dispatchFailed = true;
    }
    void onTimer() {
        if (!menu) return;
        GUITHREADINFO info{}; info.cbSize = sizeof(info);
        if (!GetGUIThreadInfo(GetCurrentThreadId(), &info) || !(info.flags & GUI_INMENUMODE) ||
            info.hwndMenuOwner != trayWindow) return;
        if (timerHandled) {
            if (!navigating) return;
            MENUITEMINFOW item{}; item.cbSize = sizeof(item); item.fMask = MIIM_STATE;
            assert(GetMenuItemInfoW(menu, 101, FALSE, &item));
            const bool target = (item.fState & MFS_HILITE) != 0;
            assert(++navigationSteps <= 24);
            if (!PostMessageW(trayWindow, WM_KEYDOWN, target ? VK_RETURN : VK_DOWN, 1)) dispatchFailed = true;
            if (target) { navigating = false; KillTimer(control, 1); }
            return;
        }
        menuObserved = true; timerHandled = true; KillTimer(control, 1);
        MONITORINFO monitor{}; monitor.cbSize = sizeof(monitor);
        assert(GetMonitorInfoW(MonitorFromWindow(trayWindow, MONITOR_DEFAULTTONEAREST), &monitor));
        unsigned historyMenus = 0;
        for (int i = 0; i < GetMenuItemCount(menu); ++i) {
            MENUITEMINFOW item{}; item.cbSize = sizeof(item); item.fMask = MIIM_ID | MIIM_SUBMENU;
            assert(GetMenuItemInfoW(menu, static_cast<UINT>(i), TRUE, &item));
            if (item.hSubMenu) { ++historyMenus; assert(GetMenuItemCount(item.hSubMenu) == 50); }
            if (item.wID == 101) {
                RECT bounds{}; assert(GetMenuItemRect(trayWindow, menu, static_cast<UINT>(i), &bounds));
                assert(bounds.right > bounds.left && bounds.right - bounds.left <= monitor.rcWork.right - monitor.rcWork.left);
            }
        }
        assert(historyMenus == 1);
        switch (scenario) {
        case Case::select: case Case::callbackDestroy: selectByKeyboard(); break;
        case Case::unchanged: tray->setCalendarState(rows, 1, 1, true, true); selectByKeyboard(); break;
        case Case::replacement: {
            auto changed = rows; changed[1].event.meetingUrl += "-replacement";
            tray->setCalendarState(std::move(changed), 1, 1, true, true); break;
        }
        case Case::account: tray->setCalendarState(rows, 2, 1, true, true); break;
        case Case::time: tray->setCalendarState(rows, 1, 2, true, true); break;
        case Case::handler: tray->setCalendarHandler([this](auto) { ++replacements; }); break;
        case Case::destroy: tray.reset(); break;
        case Case::reentry:
            SendMessageW(trayWindow, WM_APP + 200, MAKELPARAM(80, 80), MAKELPARAM(WM_CONTEXTMENU, 200));
            assert(initializations == 1); selectByKeyboard(); break;
        case Case::disabled: assert(EndMenu()); break;
        }
    }
    void run() {
        assert(SetTimer(control, 1, 30, nullptr));
        assert(SetTimer(control, 2, 2000, nullptr)); // Test watchdog, never a product operation deadline.
        SendMessageW(trayWindow, WM_APP + 200, MAKELPARAM(80, 80), MAKELPARAM(WM_CONTEXTMENU, 200));
        KillTimer(control, 1); KillTimer(control, 2);
        std::printf("native popup diagnostic case=%u init=%u timer=%u loop=%u timeout=%u dispatch=%u callbacks=%u highlight=%u steps=%u\n",
            static_cast<unsigned>(scenario), initializations, timerHandled, menuObserved, timedOut, dispatchFailed, callbacks, highlighted, navigationSteps);
        std::fflush(stdout);
        assert(initializations == 1 && timerHandled && menuObserved && !timedOut && !dispatchFailed);
        const bool accepts = scenario == Case::select || scenario == Case::unchanged ||
            scenario == Case::reentry || scenario == Case::callbackDestroy;
        assert(callbacks == (accepts ? 1U : 0U) && replacements == 0);
        if (accepts) assert(selected && *selected == rows[1]);
        std::printf("native popup case %u: actual_loop=1 callbacks=%u timeout=0\n", static_cast<unsigned>(scenario), callbacks);
    }
};

void testNativeCalendarPopup() {
    using C = NativeCalendarPopup::Case;
    for (auto scenario : {C::select, C::unchanged, C::replacement, C::account, C::time,
        C::handler, C::reentry, C::destroy, C::callbackDestroy, C::disabled}) {
        NativeCalendarPopup fixture(scenario); fixture.run();
    }
    assert(!NativeCalendarPopup::active);
}
#endif

void testUpcomingUserTimeFormatter() {
    using graf::windows::MeetingReminderPresenter;
    assert(MeetingReminderPresenter::upcomingTime(0, "UTC") == L"00:00");
    assert(MeetingReminderPresenter::upcomingTime(59.9999999, "UTC") == L"00:00");
    assert(MeetingReminderPresenter::upcomingTime(60, "UTC") == L"00:01");
    assert(MeetingReminderPresenter::upcomingTime(std::nextafter(1710054060.0, 0.0), "UTC") == L"07:00");
    assert(MeetingReminderPresenter::upcomingTime(std::nextafter(253402300800.0, 0.0), "UTC") == L"23:59");
    assert(MeetingReminderPresenter::upcomingTime(1710054060, "UTC") == L"07:01");
    assert(MeetingReminderPresenter::upcomingTime(1710054060, "UTC", true) == L"Весь день");
    assert(MeetingReminderPresenter::upcomingTime(1710054060, "UTC", true, false) == L"");
    assert(MeetingReminderPresenter::upcomingTime(1710054060, "UTC", false, false) == L"");
    for (const auto invalid : {-1.0, 253402300800.0, std::numeric_limits<double>::max(),
        std::numeric_limits<double>::infinity(), std::numeric_limits<double>::quiet_NaN()})
        assert(!MeetingReminderPresenter::upcomingTime(invalid, "UTC"));
    for (const auto zone : {"GMT", " UTC", "UTC ", "Asia/\n", "Asia/\x7f", "Asia/\xc0\xaf", "Invalid/NoSuchZone"})
        assert(!MeetingReminderPresenter::upcomingTime(1710054060, zone));
    assert(!MeetingReminderPresenter::upcomingTime(1710054060, std::string(99, 'A') + "/B"));
#ifdef _WIN32
    for (const auto& item : {
        std::make_tuple(1710054060.0, "Asia/Kathmandu", L"12:46"),
        std::make_tuple(1710053940.0, "America/New_York", L"01:59"),
        std::make_tuple(1710054060.0, "America/New_York", L"03:01"),
        std::make_tuple(1705320000.0, "Europe/Berlin", L"13:00"),
        std::make_tuple(1721044800.0, "Europe/Berlin", L"14:00")})
        assert(MeetingReminderPresenter::upcomingTime(std::get<0>(item), std::get<1>(item)) == std::get<2>(item));
    assert(MeetingReminderPresenter::upcomingTime(1710054060)); // Fresh system-zone Calendar, no setting changes.
#else
    // Unsupported named zones never pretend to be native Windows evidence.
    assert(!MeetingReminderPresenter::upcomingTime(1710054060, "Asia/Kathmandu"));
    const std::time_t instant = 1710054060; std::tm local{};
    assert(localtime_r(&instant, &local));
    wchar_t expected[6]{}; assert(std::wcsftime(expected, 6, L"%H:%M", &local));
    assert(MeetingReminderPresenter::upcomingTime(1710054060) == expected);
#endif
}

void testUpcomingMenuRows() {
    using namespace graf::windows;
    RecordingNoticePresenter card;
    std::map<std::string, std::string> saved;
    NotificationPreferenceStore store{
        [&](std::string_view key) -> std::optional<std::string> {
            const auto it = saved.find(std::string(key));
            return it == saved.end() ? std::nullopt : std::optional<std::string>(it->second);
        },
        [&](std::string_view key, std::string_view value) { saved[std::string(key)] = value; return true; }};
    MeetingReminderPresenter presenter(card, store);
    assert(!presenter.upcomingRows(0, "UTC"));
    presenter.bind("synthetic-owner", "synthetic-workspace", "https://calendar.example");
    const auto epoch = presenter.epoch();
    CalendarReminderSnapshot snapshot{presenter.owner(), presenter.workspace(), {}};
    for (int i = 13; i >= 0; --i) {
        const auto id = std::string(i < 10 ? "event-0" : "event-") + std::to_string(i);
        snapshot.events.push_back({id, 60, 3600, false, true, "Синтетическая встреча & обзор",
            true, "https://meet.example/current"});
    }
    assert(presenter.update(snapshot, epoch));
    auto rows = presenter.upcomingRows(0, "UTC");
    assert(rows && rows->size() == 12);
    for (std::size_t i = 0; i < rows->size(); ++i) {
        assert((*rows)[i].event.eventId == snapshot.events[13 - i].eventId);
        assert((*rows)[i].epoch == epoch && (*rows)[i].enabled);
        assert((*rows)[i].label == L"00:01 · Синтетическая встреча & обзор");
        assert((*rows)[i].event.title.empty() && !(*rows)[i].event.titleAvailable);
    }
    const auto now = RecordingNoticePresenter::Clock::now();
    for (const auto field : {"quiet", "reminders", "showTitles"}) {
        const bool value = std::string_view(field) == "quiet";
        (void)presenter.settings({NativeSettingsBridge::NotificationAction::set, field, value, 1}, 0, now, true);
    }
    presenter.reconcile(0, now, true);
    assert(!card.visible());
    assert(presenter.upcomingRows(0, "UTC")->at(0).label == rows->at(0).label);
    assert(presenter.upcomingRows(3600, "UTC")->size() == 12);
    assert(!presenter.upcomingRows(3600, "UTC")->at(0).enabled);

    snapshot.events.resize(5);
    snapshot.events[0].startsAt = 0; snapshot.events[0].titleAvailable = false;
    snapshot.events[0].title = "SYNTHETIC-PRIVATE-TITLE";
    snapshot.events[1].startsAt = 1; snapshot.events[1].title = " \r\n\t";
    snapshot.events[1].meetingLinkPresent = false;
    snapshot.events[2].startsAt = 2; snapshot.events[2].title = ""; snapshot.events[2].allDay = true;
    snapshot.events[2].meetingUrl = "javascript:synthetic";
    snapshot.events[3].startsAt = 3; snapshot.events[3].title = "\xc0\xaf"; // Invalid UTF-8.
    snapshot.events[4].startsAt = 4; snapshot.events[4].title = std::string(4096, 'x');
    assert(presenter.update(snapshot, epoch));
    rows = presenter.upcomingRows(0, "UTC");
    assert(rows && rows->size() == 5);
    assert(rows->at(0).label == L"00:00 · Встреча" && rows->at(0).enabled);
    assert(rows->at(1).label == L"00:00 · Без названия" && !rows->at(1).enabled);
    assert(rows->at(2).label == L"Весь день · Без названия" && !rows->at(2).enabled);
    assert(rows->at(3).label == L"00:00 · Встреча");
    assert(rows->at(4).label == L"00:00 · " + std::wstring(4096, L'x'));
    for (const auto& row : *rows) assert(row.event.title.empty() && !row.event.titleAvailable);
    snapshot.events[4].title = "\xc2\xa0\xe2\x80\x89\xe3\x80\x80"; // Unicode whitespace, same as Mac.
    assert(presenter.update(snapshot, epoch));
    assert(presenter.upcomingRows(0, "UTC")->at(4).label == L"00:00 · Без названия");
    assert(!presenter.upcomingRows(0, "Invalid/NoSuchZone"));
    for (const auto invalid : {std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity()})
        assert(!presenter.upcomingRows(invalid, "UTC"));
    snapshot.showUpcomingTime = false; snapshot.showUpcomingTitle = false;
    assert(presenter.update(snapshot, epoch));
    rows = presenter.upcomingRows(0, "UTC");
    for (const auto& row : *rows) assert(row.label == L"Встреча");
    presenter.calendarFailed();
    assert(!presenter.upcomingRows(0, "UTC"));
    assert(!presenter.upcomingCurrent(rows->at(0).event, epoch, 0));
    assert(presenter.update(snapshot, epoch));
    presenter.bind("new-owner", "synthetic-workspace", "https://calendar.example");
    assert(!presenter.upcomingRows(0, "UTC"));
    assert(!presenter.upcomingCurrent(rows->at(0).event, epoch, 0));
    assert(!presenter.update(snapshot, epoch));
    snapshot = {presenter.owner(), presenter.workspace(), {}};
    assert(presenter.update(snapshot, presenter.epoch()));
    assert(presenter.upcomingRows(0, "UTC")->empty());
}

void testUpcomingMenuIdentityAndExpiry() {
    using namespace graf::windows;
    const UpcomingMeetingRow row{{"event", 60, 3600, false, false, "", true, "https://meet.example/current"},
        7, L"00:01 · Встреча", true};
    assert(row == row);
    for (int field = 0; field < 8; ++field) {
        auto changed = row;
        switch (field) {
        case 0: changed.event.eventId += "-other"; break;
        case 1: changed.event.startsAt++; break;
        case 2: changed.event.endsAt++; break;
        case 3: changed.event.meetingLinkPresent = false; break;
        case 4: changed.event.meetingUrl += "/other"; break;
        case 5: changed.epoch++; break;
        case 6: changed.label += L" other"; break;
        case 7: changed.enabled = false; break;
        }
        assert(!(row == changed));
    }
    auto presentationOnly = row;
    presentationOnly.event.canSurface = true;
    assert(row == presentationOnly); // Card eligibility is not menu identity.
    using Clock = RecordingNoticePresenter::Clock;
    const auto now = Clock::time_point{} + std::chrono::seconds(100);
    const auto expiry = MeetingReminderPresenter::upcomingExpiry(3600, 60, now);
    assert(expiry && *expiry == now + std::chrono::seconds(3540));
    assert(!MeetingReminderPresenter::upcomingExpiry(60, 60, now));
    assert(!MeetingReminderPresenter::upcomingExpiry(59, 60, now));
    for (const auto invalid : {std::numeric_limits<double>::infinity(), std::numeric_limits<double>::quiet_NaN()}) {
        assert(!MeetingReminderPresenter::upcomingExpiry(invalid, 0, now));
        assert(!MeetingReminderPresenter::upcomingExpiry(3600, invalid, now));
    }
    assert(!MeetingReminderPresenter::upcomingExpiry(std::numeric_limits<double>::max(), 0, now));
    assert(!MeetingReminderPresenter::upcomingExpiry(3600, 60, Clock::time_point::max()));
    assert(!MeetingReminderPresenter::upcomingExpiry(1e-12, 0, now));
    assert(MeetingReminderPresenter::upcomingExpiry(1, 0, Clock::time_point::max() - std::chrono::seconds(1)) == Clock::time_point::max());
    assert(*expiry == now + std::chrono::seconds(3540)); // Frozen value, never a later clock conversion.
}

std::string source(const char* relative) {
    const auto root = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path();
    std::ifstream file(root / "RecApp" / relative);
    assert(file.is_open());
    return {std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
}

std::string section(const std::string& text, const char* begin, const char* end) {
    const auto first = text.find(begin);
    assert(first != std::string::npos);
    const auto last = text.find(end, first + std::string(begin).size());
    assert(last != std::string::npos);
    return text.substr(first, last - first);
}

void expectBefore(const std::string& text, const char* first, const char* second) {
    const auto a = text.find(first);
    const auto b = text.find(second);
    if (a == std::string::npos || b == std::string::npos || a >= b)
        std::fprintf(stderr, "Expected source order: %s before %s\n", first, second);
    assert(a != std::string::npos && b != std::string::npos && a < b);
}

void testSelectedLocalRemovalSourceWiring() {
    // Source wiring only: an installed Click/dialog/focus test remains required.
    const auto app = source("AppMain.cpp");
    const auto panel = section(app, "    void refreshSelectedRecording()", "    bool calendarAuthCurrent(");
    assert(panel.find("styledButton(L\"Удалить локальную копию…\")") != std::string::npos);
    assert(panel.find("selectedLocalRemovalButton_.Click(") != std::string::npos);
    assert(panel.find("removeSelectedLocalCopy(target, revision, localId)") != std::string::npos);
    assert(panel.find("selectedLocalRemovalButton_.IsEnabled(") != std::string::npos);
    assert(panel.find("setAccessible(selectedLocalRemovalButton_") != std::string::npos);
    assert(panel.find("if (key == selectedRecordingDisplayKey_) return") == std::string::npos);
    assert(panel.find("if (key != selectedRecordingDisplayKey_)") != std::string::npos);
    assert(panel.find("if (!observation.complete && !selectedRecordingDisplayKey_.empty()) localId = selectedLocalRecordingId_") != std::string::npos);
    assert(panel.find("if (selectedRecordingStatus_.Text() != detail)") != std::string::npos);
    assert(panel.find("nativeLocalRemovalContextCurrent(*selectedRecording_, selectedRecordingRevision_)") != std::string::npos);
    assert(panel.find("problemContextCurrent(*selectedRecording_)") == std::string::npos);
    const auto context = section(app, "    [[nodiscard]] bool nativeLocalRemovalContextCurrent(",
        "    [[nodiscard]] bool selectedLocalRemovalAllowed(");
    for (const auto guard : {"selectedRecordingRevision_", "authGeneration()", "currentAccount()", "authSessionToken().empty()",
                            "interactionPermit()", "updateAdmissionBlocked()", "contextEpoch", "permit.epoch"})
        assert(context.find(guard) != std::string::npos);
    // Receipt currency must survive its own successful row removal.
    for (const auto forbidden : {"ownsRecordingSession(", "problemContextCurrent(", "problemActionCurrent(", "localObservation("})
        assert(context.find(forbidden) == std::string::npos);
    const auto allowed = section(app, "    [[nodiscard]] bool selectedLocalRemovalAllowed(",
        "    void removeSelectedLocalCopy(");
    for (const auto guard : {"nativeLocalRemovalContextCurrent(", "selectedRecording_", "observation.complete", "observation.value != snapshot",
                            "localRecordingId", "sessionId", "ownerUserId", "ownerWorkspaceId", "canLocalRemoval(", "matches == 1"})
        assert(allowed.find(guard) != std::string::npos);
    const auto action = section(app, "    void removeSelectedLocalCopy(", "    void refreshSelectedRecording()");
    expectBefore(action, "selectedLocalRemovalAllowed(", "confirmLocalAction(");
    const auto confirmed = action.substr(action.find("snapshot = observation.value"));
    expectBefore(confirmed, "selectedLocalRemovalAllowed(", "PendingLocalAction pending");
    expectBefore(confirmed, "PendingLocalAction pending", "requestProtectedLocalRemoval(");
    assert(confirmed.find("pendingLocalRemoval_ = std::move(pending)") != std::string::npos);
    for (const auto forbidden : {"handleLocalRecording(", "documentNonce", "requestProtectedDeletionSelection(", "handleDeletionSelection("})
        assert(action.find(forbidden) == std::string::npos);
    const auto poll = section(app, "    void pollLocalRecordingRemoval()", "    void handleDeletionSelection(");
    assert(poll.find("std::get_if<ProblemTarget>") != std::string::npos);
    assert(poll.find("nativeLocalRemovalContextCurrent(") != std::string::npos);
    expectBefore(poll, "takeProtectedDeletionCompletion(", "pendingLocalRemoval_.reset()");
    const auto selection = section(app, "    void openProblemRecording(", "    void reconcileRecordingProblems()");
    assert(selection.find("++selectedRecordingRevision_") != std::string::npos);
    expectBefore(selection, "++selectedRecordingRevision_", "selectedRecording_ = target");
    assert(panel.find("++selectedRecordingRevision_") == std::string::npos);
}

void testClosePolicy() {
    using namespace graf::windows;
    for (const auto state : {SessionState::idle, SessionState::starting, SessionState::recording,
                            SessionState::paused, SessionState::degraded, SessionState::stopping,
                            SessionState::finalizing, SessionState::savedLocal, SessionState::failed}) {
        // Hiding/reopening owns no capture transition. Repeat X is still a hide;
        // loss of either recovery or the active Stop surface keeps the shell.
        assert(shellCloseAction(ShellCloseIntent::window, state, true, true, false) == ShellCloseAction::hide);
        assert(shellCloseAction(ShellCloseIntent::window, state, false, true, false) == ShellCloseAction::keepVisible);
        assert(shellCloseAction(ShellCloseIntent::window, state, true, false, false) ==
               (isCaptureState(state) ? ShellCloseAction::keepVisible : ShellCloseAction::hide));
        const auto firstQuit = shellCloseAction(ShellCloseIntent::quit, state, false, false, false);
        const auto repeatedQuit = shellCloseAction(ShellCloseIntent::quit, state, true, true, true);
        if (!isCaptureState(state)) {
            assert(firstQuit == ShellCloseAction::close);
            assert(repeatedQuit == ShellCloseAction::close);
        } else {
            assert(firstQuit == (state == SessionState::stopping || state == SessionState::finalizing
                ? ShellCloseAction::wait : ShellCloseAction::stopAndWait));
            assert(repeatedQuit == ShellCloseAction::wait);
            assert(shellCloseAction(ShellCloseIntent::window, state, true, true, true) == ShellCloseAction::wait);
        }
    }
}

void testCloseKeepsTheSessionAndAutomaticTracking() {
    using namespace graf::windows;
    WindowsDesktopSession session("same-session-after-tray-reopen");
    assert(session.beginReadinessCheck().accepted());
    assert(session.markReady().accepted());
    assert(session.beginStart().accepted());
    const auto hideAndReopen = [&] {
        const auto before = session.state();
        for (unsigned repeat = 0; repeat < 3; ++repeat)
            assert(shellCloseAction(ShellCloseIntent::window, session.state(), true, true, false) == ShellCloseAction::hide);
        assert(session.state() == before);
        assert(session.sessionId() == "same-session-after-tray-reopen");
        // Hiding does not release the actual process-wide active-session lease.
        WindowsDesktopSession other("must-not-start");
        const auto blocked = other.beginReadinessCheck();
        assert(!blocked.accepted() && blocked.reason == ReasonCode::activeSessionExists);
    };
    hideAndReopen();
    assert(session.startRecording().accepted());
    hideAndReopen();
    assert(session.pause().accepted());
    hideAndReopen();
    assert(shellCloseAction(ShellCloseIntent::quit, session.state(), true, true, false) == ShellCloseAction::stopAndWait);
    assert(session.stop().accepted());
    assert(shellCloseAction(ShellCloseIntent::quit, session.state(), true, true, true) == ShellCloseAction::wait);
    assert(session.beginFinalizing().accepted());
    hideAndReopen();
    assert(shellCloseAction(ShellCloseIntent::window, session.state(), false, false, true) == ShellCloseAction::wait);
    assert(session.saveLocal().accepted());
    assert(shellCloseAction(ShellCloseIntent::quit, session.state(), false, false, true) == ShellCloseAction::close);

    using namespace graf::windows::testing;
    VerifiedTargetRegistry registry;
    assert(registry.registerTarget(target()));
    Preferences preferences;
    AutomaticRecordingPolicy policy(registry, preferences.store());
    assert(policy.setPreference(target(), AutomaticRecordingPreference::always));
    assert(observeFor(policy, 0, 5).shouldStart);
    policy.captureAccepted();
    assert(shellCloseAction(ShellCloseIntent::window, SessionState::recording, true, true, false) == ShellCloseAction::hide);
    assert(!policy.shouldStopCapture(snapshot(at(6s)), true, at(6s)));
    // The same tracked meeting still ends automatically after hiding/reopening.
    for (int second = 7; second <= 22; ++second) {
        const auto now = at(std::chrono::seconds(second));
        auto absent = snapshot(now);
        absent.observations.clear();
        assert(policy.shouldStopCapture(absent, true, now) == (second == 22));
    }
}

void testCloseSourceWiring() {
    // Source checks complement the executable policy, not Windows UI evidence.
    const auto app = source("AppMain.cpp");
    const auto closing = section(app, "window_.AppWindow().Closing(", "window_.Closed(");
    assert(closing.find("shellCloseAction(ShellCloseIntent::window") != std::string::npos);
    assert(closing.find("tray_->available()") != std::string::npos);
    assert(closing.find("requestExit()") == std::string::npos);
    assert(closing.find("capture_->stop") == std::string::npos);
    assert(closing.find("automaticPolicy_.cancel()") == std::string::npos);
    assert(closing.find("args.Cancel(true)") != std::string::npos);
    expectBefore(closing, "beginExit()", "exitWorkDrained()");
    const auto exitJobs = section(app, "    [[nodiscard]] bool shellExitJobsDrained()", "    void requestExit()");
    for (const auto field : {"deletionSelectionsInFlight_ == 0", "shellMutations_ == 0",
                            "!calendarResolverThread_.joinable()", "!calendarCalling_", "capture_->shutdownWorkDrained()"})
        assert(exitJobs.find(field) != std::string::npos);
    expectBefore(exitJobs, "exitRequested_ = true", "capture_->requestShutdown()");
    expectBefore(exitJobs, "capture_->requestShutdown()", "capture_->shutdown()");
    const auto quit = section(app, "    void requestExit()", "    bool ensureRecordingIndicator(");
    expectBefore(quit, "beginExit()", "exitWorkDrained()");
    expectBefore(quit, "exitWorkDrained()", "window_.Close()");
    const auto refresh = section(app, "    void refreshNativeState()", "        const CustodyMutationScope mutation(shellMutations_)");
    expectBefore(refresh, "capture_->pollHealth()", "capture_->pollUploads()");
    expectBefore(refresh, "capture_->pollUploads()", "exitWorkDrained()");
    expectBefore(refresh, "exitWorkDrained()", "window_.Close()");
    const auto capture = source("Recording/NativeCapture.h");
    const auto purge = section(app, "    void startLocalPurgePass()", "    void pollDeletionSelection()");
    assert(purge.find("beginProtectedLocalPurgePass()") != std::string::npos && purge.find(".detach()") == std::string::npos);
    assert(app.find("localPurgeInFlight_") == std::string::npos && app.find("prepareLocalPurgeAnswers") == std::string::npos);
    const auto drain = section(capture, "    [[nodiscard]] bool updateWorkDrained()", "    [[nodiscard]] bool shutdownWorkDrained()");
    assert(drain.find("if (deletionContinuationId_) return false") != std::string::npos);
    const auto shutdown = section(capture, "    void requestShutdown()", "    [[nodiscard]] graf::windows::TransitionResult pause()");
    expectBefore(shutdown, "exitAdmissionBlocked_ = true", "RecordingStopReason::interruption");
    expectBefore(shutdown, "protectedRecoveryEpoch_.reset()", "RecordingStopReason::interruption");
    const auto storagePoll = section(capture, "    void pollStorageStartup(bool allowDisplay)", "    void stopStorageStartup()");
    assert(storagePoll.find("if (allowDisplay && retired") != std::string::npos);
    assert(capture.find("pollStorageStartup(!pendingRecovery_)") != std::string::npos);
    expectBefore(storagePoll, "!shuttingDown_ && !exitAdmissionBlocked_ && !updateAdmissionBlocked_",
                 "StorageCommand::recovery");
    const auto confirmation = section(app, "    void confirmLocalAction(", "    void showCabinetFallback(");
    expectBefore(confirmation, "exitRequested_ || !capture_", "dialog.ShowAsync()");
    const auto primary = confirmation.substr(confirmation.find("ContentDialogResult::Primary"));
    expectBefore(primary, "exitRequested_ || !capture_", "confirmed()");
    assert(capture.find("bool sendLocalRecording(") == std::string::npos && capture.find("bool assignLocalOwner(") == std::string::npos);
    const auto send = section(app, "    void handleLocalRecording(", "    void pollLocalRecordingSend()");
    assert(send.find("localQueueComplete()") == std::string::npos);
    expectBefore(send, "playbackDocumentCurrent(request, epoch)", "requestProtectedManualSend(");
    expectBefore(send, "PendingLocalAction pending{request, epoch, 0}", "requestProtectedManualSend(");
    assert(send.find("requestProtectedManualSend(observation.value, id, epoch, false)") != std::string::npos &&
        send.find("Сохраняем запрос отправки") != std::string::npos);
    assert(send.find("Подтвердить и отправить") == std::string::npos); // Unowned rows remain hidden, no unreachable confirmation.
    const auto sendPoll = section(app, "    void pollLocalRecordingSend()", "    void handleDeletionSelection(");
    expectBefore(sendPoll, "playbackDocumentCurrent(", "protectedManualSendTicket(");
    expectBefore(sendPoll, "QueueTicketState::pending", "QueueTicketState::committed");
    const auto staleSend = section(sendPoll, "if (!request || !playbackDocumentCurrent(", "        const auto ticket =");
    expectBefore(staleSend, "localActionNotice_ ==", "localActionNotice_.clear()");
    expectBefore(staleSend, "localActionNotice_.clear()", "pendingManualSend_.reset()");
    assert(staleSend.find("Сохраняем запрос отправки… Запись остаётся на этом компьютере.") != std::string::npos);
    for (const auto signature : {"    [[nodiscard]] std::optional<QueueMutationTicket> requestProtectedManualSend(",
                                "    [[nodiscard]] std::optional<QueueMutationTicket> requestProtectedDeletionSelection("}) {
        const auto start = capture.find(signature);
        assert(start != std::string::npos);
        const auto body = capture.substr(start, capture.find("\n    }", start) - start);
        assert(body.find("exitAdmissionBlocked_") != std::string::npos);
    }
    assert(capture.find("LocalCopyRemovalResult removeLocalCopy(") == std::string::npos &&
        capture.find("void finishPendingLocalDeletions(") == std::string::npos && capture.find(" localItem(") == std::string::npos);
    const auto removal = section(send, "        if (action == \"delete\")", "\n    }");
    const auto confirmedRemoval = removal.substr(removal.find("[this, request, epoch, snapshot = observation.value]"));
    expectBefore(confirmedRemoval, "playbackDocumentCurrent(request, epoch)", "requestProtectedLocalRemoval(");
    expectBefore(confirmedRemoval, "PendingLocalAction pending{request, epoch, 0}", "requestProtectedLocalRemoval(");
    assert(confirmedRemoval.find("pendingLocalRemoval_ = std::move(pending)") != std::string::npos);
    expectBefore(confirmedRemoval, "localRecordingActionAllowed(\"delete\", request.id)", "requestProtectedLocalRemoval(");
    assert(confirmedRemoval.find("requestProtectedLocalRemoval(snapshot, request.id, epoch)") != std::string::npos);
    const auto removalPoll = section(app, "    void pollLocalRecordingRemoval()", "    void handleDeletionSelection(");
    expectBefore(removalPoll, "takeProtectedDeletionCompletion(", "pendingLocalRemoval_.reset()");
    expectBefore(removalPoll, "pendingLocalRemoval_.reset()", "if (current) localActionNotice_");
    expectBefore(removalPoll, "result->unknown", "!result->saved");
    expectBefore(removalPoll, "!result->saved", "Намерение сохранено");
    expectBefore(removalPoll, "result->accepted == 1", "Локальная копия больше не хранится");
    assert(removalPoll.find("if (!current) return") == std::string::npos);
    assert(removalPoll.find("localActionNotice_.clear()") != std::string::npos);
    assert(app.find("std::is_nothrow_move_constructible_v<PendingLocalAction>") != std::string::npos);
    const auto nativeRemoval = section(capture, "    [[nodiscard]] std::optional<QueueMutationTicket> requestProtectedLocalRemoval(",
        "    [[nodiscard]] std::optional<QueueMutationTicket> beginProtectedDeletionSelection(");
    assert(nativeRemoval.find("exitAdmissionBlocked_") != std::string::npos && nativeRemoval.find("epoch != authGeneration_") != std::string::npos);
    const auto tray = source("Shell/WindowsTray.cpp");
    const auto restart = section(tray, "if (message == self->taskbarCreated)", "if (message == kTrayMessage)");
    expectBefore(restart, "self->registered = false", "self->addIcon()");
    const auto add = section(tray, "    bool addIcon()", "\n};");
    // A state tick may restore the icon before the queued TaskbarCreated
    // broadcast arrives. NIM_ADD can then fail for our already-present icon.
    assert(add.find("NIM_MODIFY") != std::string::npos);
    expectBefore(add, "NIM_ADD", "NIM_SETVERSION");
    expectBefore(add, "NIM_SETVERSION", "registered = true");
    assert(add.find("removeIcon()") != std::string::npos);
    const auto update = section(tray, "    void updateIcon()", "    bool addIcon()");
    const auto modification = update.find("NIM_MODIFY");
    assert(modification != std::string::npos);
    expectBefore(update.substr(modification), "registered = false", "addIcon()");
    const auto available = section(tray, "bool WindowsTray::available()", "void WindowsTray::setTheme(");
    assert(available.find("updateIcon()") != std::string::npos);
    assert(available.find("impl_->registered") != std::string::npos);
    const auto fallback = section(app, "    void refreshTrayAvailability()", "    void buildShell()");
    assert(fallback.find("tray_->available()") != std::string::npos);
    assert(fallback.find("window_.AppWindow().Show(false)") != std::string::npos);
    assert(app.find("trayExitButton_.Click([this](auto const&, auto const&) { requestExit(); })") != std::string::npos);
    const auto startup = section(app, "    void showStartupError(", "    static double reminderWallTime()");
    assert(startup.find("requestExit()") != std::string::npos);
}

void testBackgroundSurfaceWiring() {
    const auto app = source("AppMain.cpp");
    const auto prompt = section(app, "    void updateAutomaticPrompt()", "    void showPermissionOnboarding()");
    assert(app.find("automaticPromptWindow_") == std::string::npos);
    assert(prompt.find("NoticeKind::recordingPrompt") != std::string::npos);
    assert(prompt.find("notificationCard().present(") != std::string::npos);
    assert(prompt.find("hooks.onPresented") != std::string::npos);
    assert(prompt.find("automaticPolicy_.confirmPromptPresented(") != std::string::npos);
    assert(prompt.find("notificationCard().deadline() - std::chrono::seconds(8)") != std::string::npos);
    assert(prompt.find("automaticPolicy_.cancel()") != std::string::npos);
    const auto indicator = section(app, "    bool ensureRecordingIndicator(", "    void pauseResumeCapture()");
    assert(indicator.find("indicatorWindow_.Activate()") == std::string::npos);
    assert(indicator.find("indicatorWindow_.AppWindow().Show(false)") != std::string::npos);
    assert(indicator.find("if (!recordingIndicatorAvailable())") != std::string::npos);
    const auto automaticStart = section(app, "    void startAutomaticRecording(", "    bool closeAutomaticPrompt(");
    expectBefore(automaticStart, "!ensureRecordingIndicator()", "capture_->record(");
    const auto manualStart = section(app, "    void recordCapture(", "    void stopCapture()");
    expectBefore(manualStart, "!ensureRecordingIndicator()", "capture_->record()");
    const auto indicatorCreated = manualStart.find("!ensureRecordingIndicator()");
    expectBefore(manualStart.substr(indicatorCreated), "current && !current()", "capture_->record()");
    const auto keyboard = section(app, "    bool focusBackgroundSurface()", "    void refreshTrayAvailability()");
    assert(keyboard.find("NoticeKind::recordingPrompt") != std::string::npos);
    assert(keyboard.find("notificationCard().focus()") != std::string::npos);
    assert(keyboard.find("indicatorStop_.Focus(FocusState::Keyboard)") != std::string::npos);
    assert(app.find("VirtualKey::F6 && focusBackgroundSurface()") != std::string::npos);
}

void testTrayActionWiring() {
    const auto tray = source("Shell/WindowsTray.cpp");
    const auto append = section(tray, "    void addItem(", "    void measureItem(");
    assert(append.find("MF_DISABLED") != std::string::npos);
    assert(append.find("MF_SEPARATOR") != std::string::npos);
    assert(append.find("MSAA_MENU_SIG") != std::string::npos);
    assert(append.find("accessibility.pszWText = item->text.data()") != std::string::npos);
    expectBefore(append, "menuItems.push_back", "AppendMenuW("); // Allocation must precede submenu attachment.
    assert(tray.find("L\"Начать запись\", kStartCommand") != std::string::npos);
    assert(tray.find("L\"Настройки\", kSettingsCommand") != std::string::npos);
    assert(tray.find("L\"Перейти к уведомлению\", kFocusNotificationCommand") != std::string::npos);
    assert(tray.find("L\"История уведомлений\"") != std::string::npos);
    assert(tray.find("history.size() > 50") != std::string::npos);
    assert(tray.find("if (self->actions.start) handler = self->startHandler") != std::string::npos);
    assert(tray.find("if (self->actions.settings) handler = self->settingsHandler") != std::string::npos);
    const auto menu = section(tray, "    void showMenu(", "    NOTIFYICONDATAW iconData()");
    expectBefore(menu, "invalidateMenu()", "popupToken = token"); // A finishing selection cannot survive a new popup.
    expectBefore(menu, "popupToken = token", "prepareMenuStyle(");
    expectBefore(menu, "const auto rows = calendarRows", "TrackPopupMenuEx(");
    expectBefore(menu, "const auto calendar = calendarHandler", "TrackPopupMenuEx(");
    expectBefore(menu, "auto menuLifetime = std::move(menuItems)", "SetForegroundWindow(");
    assert(menu.find("!row.enabled || !calendar || !actions.settings") != std::string::npos);
    const auto returned = menu.substr(menu.find("TrackPopupMenuEx("));
    expectBefore(returned, "token->current && IsWindow(menuWindow)", "calendar(row)");
    assert(returned.find("(*rows)[command - kCalendarCommand]") != std::string::npos);
    assert(returned.find("calendarRows") == std::string::npos);
    assert(returned.find("calendarHandler") == std::string::npos);
    assert(returned.find("calendar(row); // no access to Impl") != std::string::npos);
    const auto projection = section(tray, "void WindowsTray::setCalendarState(", "} // namespace graf::windows");
    for (const auto field : {"calendarRows != rows", "calendarAuthGeneration != authGeneration",
        "calendarTimeRevision != timeRevision", "calendarShowTime != showTime", "calendarShowTitle != showTitle"})
        assert(projection.find(field) != std::string::npos);
    assert(projection.find("impl_->invalidateMenu()") != std::string::npos);
    assert(tray.find("DT_END_ELLIPSIS | DT_NOPREFIX") != std::string::npos);
    assert(tray.find("SPI_GETNONCLIENTMETRICS") != std::string::npos);
    assert(tray.find("COLOR_HIGHLIGHTTEXT") != std::string::npos);
    const auto app = source("AppMain.cpp");
    assert(app.find("[this] { recordCapture(); }") != std::string::npos);
    assert(app.find("[this] { openAccountSettings(); }") != std::string::npos);
    const auto start = section(app, "    void recordCapture(", "    void stopCapture()");
    expectBefore(start, "if (!capture_->localQueueComplete())", "capture_->refreshReadiness()");
    const auto unavailable = section(start, "        if (!capture_->localQueueComplete()) {", "        // A tray command");
    assert(unavailable.find("localActionNotice_ = capture_->custodySummary()") != std::string::npos);
    assert(unavailable.find("return;") != std::string::npos);
    assert(unavailable.find("refreshNativeState()") == std::string::npos);
    expectBefore(start, "capture_->refreshReadiness()", "!canStartRecording()");
    expectBefore(start, "!canStartRecording()", "capture_->record()");
    assert(app.find("tray_->setState(snapshot, canStartRecording(), exitRequested_, capture_->privacyPending())") != std::string::npos);
    const auto settings = section(app, "    void openAccountSettings()", "    bool focusBackgroundSurface()");
    assert(settings.find("/desktop/settings/account") != std::string::npos);
    assert(settings.find("trustedOrigin()") != std::string::npos);
    assert(settings.find("openMainWindow()") != std::string::npos);
    assert(settings.find("openNativeSettings()") == std::string::npos);
    assert(app.find("settingsButton.Click([this](auto const&, auto const&) { openAccountSettings(); })") != std::string::npos);
    assert(app.find("RecordingNoticePresenter::historyMessage(entry.kind)") != std::string::npos);
    assert(app.find("protectedFramesProvider = [this] { return notificationProtectedFrames(); }") != std::string::npos);
}

void testTrayActionAvailability() {
    using namespace graf::windows;
    RecordingIndicator indicator;
    for (const auto state : {SessionState::idle, SessionState::ready, SessionState::blocked,
                            SessionState::starting, SessionState::recording, SessionState::paused,
                            SessionState::degraded, SessionState::stopping, SessionState::finalizing,
                            SessionState::savedLocal, SessionState::failed}) {
        indicator.publish(state);
        for (bool ready : {false, true}) {
            for (bool exiting : {false, true}) {
                const auto actions = WindowsTray::menuAvailability(indicator.snapshot(), ready, exiting);
                assert(actions.start == (ready && !isCaptureState(state) && !exiting));
                assert(actions.pauseResume == (!exiting && (state == SessionState::recording || state == SessionState::paused)));
                assert(actions.stop == isCaptureState(state));
                assert(actions.settings == !exiting);
                const auto pending = WindowsTray::menuAvailability(indicator.snapshot(), ready, exiting, true);
                assert(!pending.pauseResume && pending.stop == actions.stop);
                assert(pending.start == actions.start && pending.settings == actions.settings);
            }
        }
    }
}

void testCalendarJoinOwnerSourceWiring() {
    // Wiring regression only, not evidence of actual UI/worker/SDK completion.
    const auto app = source("AppMain.cpp");
    const auto owner = section(app, "    bool calendarAuthCurrent(", "    void refreshMeetingReminders()");
    for (const auto field : {"context.owner", "context.workspace", "context.authGeneration", "context.sessionToken",
        "context.actionExpiresAt", "calendarJoinCurrent", "pendingActionExpiry"})
        assert(owner.find(field) != std::string::npos);
    assert(owner.find("ShellExecute") == std::string::npos);
    assert(owner.find(".detach()") == std::string::npos);
    const auto poll = section(app, "    void pollCalendarJoin()", "    void refreshMeetingReminders()");
    assert(poll.find("future_status::ready") == std::string::npos);
    assert(poll.find("if (!calendarCurrent() && !calendarRetryCurrent()) cancelCalendarJoin();") != std::string::npos);
    assert(poll.find("const bool failedMenu") == std::string::npos);
    expectBefore(poll, "WaitForSingleObject", "calendarResolverThread_.join()");
    expectBefore(poll, "status == WAIT_OBJECT_0", "calendarResolverThread_.join()");
    expectBefore(poll, "calendarResolverThread_.join()", "calendarResolverFuture_.get()");
    expectBefore(poll, "calendarResolverFuture_.get()", "calendarJoin_.complete(ticket");
    const auto handedOff = poll.substr(poll.find("CalendarLauncherOutcome::launched"));
    expectBefore(handedOff, "CalendarJoinState::handedOff", "reminders_->completeAction(");
    expectBefore(handedOff, "reminders_->completeAction(", "recordCapture(");
    assert(handedOff.find("calendarAuthCurrent(context, epoch)") != std::string::npos);
    assert(handedOff.find("handoffRecordingCurrent(target") != std::string::npos);
    const auto refresh = section(app, "    void refreshNativeState()", "    TextBlock privacyNotice_");
    expectBefore(refresh, "pollCalendarJoin()", "if (!capture_ || shuttingDown_)");
    assert(app.find("host.setCalendarJoinHandlers(") != std::string::npos);
    const auto admission = section(app, "    void beginMenuCalendarJoin(", "    void startCalendarResolver(");
    expectBefore(admission, "upcomingCurrent(menu->event", "calendarJoin_.begin(");
    expectBefore(admission, "upcomingExpiry(menu->event.endsAt", "calendarJoin_.begin(");
    assert(admission.find("flight.menu = menu") != std::string::npos);
    assert(admission.find("context.sourceEpoch = menu->epoch") != std::string::npos);
    assert(admission.find("event = menu->event.eventId") != std::string::npos);
    assert(admission.find("std::chrono::steady_clock::now(), menu.has_value()") != std::string::npos);
    const auto applicability = section(app, "    bool calendarSourceCurrent()", "    void cancelCalendarJoin()");
    assert(applicability.find("upcomingCurrent(flight.menu->event, flight.menu->epoch") != std::string::npos);
    assert(applicability.find("std::chrono::steady_clock::now() < context.actionExpiresAt") != std::string::npos);
    assert(applicability.find("upcomingExpiry") == std::string::npos); // Never extend admitted expiry on refresh.
    const auto dialog = section(app, "    void offerCalendarDialog(bool retry)", "    void pollCalendarJoin()");
    assert(dialog.find("calendarJoin_.retryDialog(") != std::string::npos);
    assert(dialog.find("calendarJoin_.confirmRetry(ticket") != std::string::npos);
    assert(dialog.find("calendarFlight_->hideRequested") != std::string::npos);
    assert(dialog.find("calendarCalling_") != std::string::npos);
    assert(dialog.find("Повторить подключение") != std::string::npos);
    assert(dialog.find("calendarFlight_->retryOffered = true") != std::string::npos);
    const auto retry = section(poll, "                        if (calendarFlight_->retryDialog)",
        "                        } else if (applicable && calendarCurrent())");
    for (const auto field : {"ContentDialogResult::Primary", "confirmedAt", "!calendarFlight_->hideRequested",
        "calendarRetryCurrent()", "calendarJoin_.retry(", "newSessionId()", "calendarFlight_->id = resolver->operationId"})
        assert(retry.find(field) != std::string::npos);
    assert(retry.find(".begin(") == std::string::npos && retry.find("upcomingExpiry") == std::string::npos);
    expectBefore(poll.substr(poll.find("calendarDialogOperation_.Status()")), "calendarJoin_.complete(ticket", "calendarJoin_.retry(");
    assert(poll.find("const CustodyMutationScope call(calendarCalling_)") != std::string::npos);
    const auto failureUi = section(poll, "        if (calendarJoin_.result().state == CalendarJoinState::failed",
        "        if (!calendarJoin_.busy()");
    for (const auto fence : {"!calendarFlight_->retryOffered", "!calendarFlight_->work", "!calendarResolverThread_.joinable()",
        "!calendarLauncher_.busy()", "!calendarDialogOperation_", "calendarRetryCurrent()"})
        expectBefore(failureUi, fence, "offerCalendarDialog(true)");
    assert(refresh.find("tray_->setCalendarState(") != std::string::npos);
    assert(refresh.find("upcomingRows(reminderWallTime(), zone)") != std::string::npos);
    assert(refresh.find("userTimeRevision()") != std::string::npos);
    assert(app.find("if (alive->load()) beginMenuCalendarJoin(std::move(row))") != std::string::npos);
}

void testLocalNotificationSettingsWiring() {
    // Source wiring only: native control layout/focus still requires a live
    // installed Windows run. The model/bridge suites exercise persistence.
    const auto app = source("AppMain.cpp");
    const auto settings = section(app, "    void openNativeSettings()", "    void bindNotificationContext()");
    for (const auto field : {"reminders", "showTitles", "sound", "quiet", "offsetMinutes"})
        assert(settings.find(std::string("\"") + field + "\"") != std::string::npos);
    assert(settings.find("NotificationAction::test") != std::string::npos);
    assert(settings.find("AutomationLiveSetting::Polite") != std::string::npos);
    assert(settings.find("ms-settings:notifications") == std::string::npos);
    const auto bind = section(app, "    void bindNotificationContext()", "    void refreshLocalNotificationSettings()");
    assert(bind.find("capture_->currentAccount()") != std::string::npos);
    assert(bind.find("DesktopHttpConfig{}.baseOrigin") != std::string::npos);
    const auto save = section(app, "    void applyLocalNotificationSetting(", "    ComboBox automaticPreferencePicker(");
    expectBefore(save, "bindNotificationContext()", "displayedEpoch != reminders_->epoch()");
    expectBefore(save, "displayedEpoch != reminders_->epoch()", "reminders_->settings(");
    assert(save.find("refreshNativeSettings()") != std::string::npos);
    assert(save.find("refreshLocalNotificationSettings()") != std::string::npos);
    const auto refresh = section(app, "    void refreshLocalNotificationSettings()", "    void applyLocalNotificationSetting(");
    assert(refresh.find("reminders_->preferences()") != std::string::npos);
    assert(refresh.find("toggle.IsEnabled(editable)") != std::string::npos);
    assert(refresh.find("localNotificationOffset_.IsEnabled(editable && preferences.reminders)") != std::string::npos);
    assert(refresh.find("localNotificationTest_.IsEnabled(editable)") != std::string::npos);
    const auto answer = section(app, "    std::string answerNativeSettings(", "    const graf::windows::VerifiedTargetIdentity*");
    assert(answer.find("refreshLocalNotificationSettings()") != std::string::npos);
    const auto status = section(app, "    void setLocalNotificationStatus(", "    void refreshLocalNotificationSettings()");
    expectBefore(status, "localNotificationStatus_.Text() == text", "RaiseAutomationEvent(");
    assert(status.find("AutomationEvents::LiveRegionChanged") != std::string::npos);
}

void testSystemThemeRefreshWiring() {
    const auto app = source("AppMain.cpp");
    const auto appearance = section(app, "    void applyCabinetAppearance(", "    void handleLocalRecording(");
    assert(appearance.find("if (theme == announcedAppearance_)") == std::string::npos);
    assert(appearance.find("notificationCard().setDarkTheme(isDark)") != std::string::npos);
    const auto refresh = section(app, "    void refreshNativeState()", "    TextBlock privacyNotice_");
    assert(refresh.find("announcedAppearance_ == \"system\" && systemThemeIsDark() != shellIsDark_") != std::string::npos);
    assert(refresh.find("applyCabinetAppearance(\"system\")") != std::string::npos);
}

void testInteractionLifecycle() {
    using namespace graf::windows;
    InteractionPermitState guard;
    assert(!guard.permit().allowed);
    const InteractionSample ready{true, true, true, true};
    auto permit = guard.observe(ready, 100);
    assert(permit.allowed && permit.epoch != 0);
    const auto initial = permit.epoch;
    std::uint64_t sampleTime = 100;
    for (int missing = 0; missing != 4; ++missing) {
        auto sample = ready;
        if (missing == 0) sample.subscriptionsReady = false;
        if (missing == 1) sample.sessionActive = false;
        if (missing == 2) sample.sessionUnlocked = false;
        if (missing == 3) sample.inputDesktop = false;
        const auto before = guard.permit().epoch;
        assert(!guard.observe(sample, ++sampleTime).allowed);
        assert(guard.permit().epoch != before);
        assert(guard.observe(ready, ++sampleTime).allowed);
    }
    assert(guard.permit().epoch != initial);
    for (const auto event : {InteractionEvent::sessionUnavailable, InteractionEvent::suspend}) {
        const auto before = guard.permit().epoch;
        guard.event(event);
        assert(!guard.permit().allowed && guard.permit().epoch != before);
        assert(!guard.observe(ready, 200).allowed); // positive probe cannot undo a latched event
        guard.event(InteractionEvent::resumeAutomatic);
        assert(!guard.observe(ready, 201).allowed);
        guard.event(InteractionEvent::sessionAvailable);
        assert(!guard.permit().allowed); // event is not positive evidence
        assert(guard.observe(ready, 202).allowed);
        assert(guard.permit().epoch != before); // an old worker token never revives
    }
    guard.event(InteractionEvent::suspend);
    guard.event(InteractionEvent::resumeInteractive);
    assert(guard.observe(ready, 203).allowed);
    const auto beforeSwitch = guard.permit().epoch;
    guard.event(InteractionEvent::desktopSwitch);
    assert(!guard.permit().allowed);
    assert(guard.observe(ready, 204).allowed && guard.permit().epoch != beforeSwitch);
    const auto beforeGap = guard.permit().epoch;
    assert(guard.observe(ready, 4000).allowed && guard.permit().epoch != beforeGap);
    const auto beforeRollback = guard.permit().epoch;
    assert(guard.observe(ready, 3000).allowed && guard.permit().epoch != beforeRollback);
    guard.event(InteractionEvent::shutdown);
    guard.event(InteractionEvent::sessionAvailable);
    assert(!guard.observe(ready, 4001).allowed);
    assert(!guard.retrySubscriptionsDue(4001));
    InteractionPermitState retry;
    assert(retry.retrySubscriptionsDue(0));
    assert(!retry.retrySubscriptionsDue(999));
    for (const std::uint64_t at : {1000, 3000, 7000, 15000}) {
        assert(!retry.retrySubscriptionsDue(at - 1));
        assert(retry.retrySubscriptionsDue(at));
        assert(!retry.retrySubscriptionsDue(at));
    }
    assert(!retry.retrySubscriptionsDue(31000));
    // A late positive prerequisite query may allow NEW work, not the token
    // captured before the gap. The final guard must compare the fresh epoch.
    InteractionPermitState pending;
    const auto token = pending.observe(ready, 100);
    const auto latePositive = pending.observe(ready, 2601);
    assert(latePositive.allowed && latePositive.epoch == token.epoch + 1);
    const auto finalPermit = pending.observe(ready, 2602);
    assert(!(finalPermit.allowed && finalPermit.epoch == token.epoch));
    // A slow native sample is not fresh evidence, even if all facts are true.
    // Recovery requires another bounded query and cannot revive its old token.
    for (const bool rollback : {false, true}) {
        InteractionPermitState sampling;
        const auto old = sampling.observe(ready, 100);
        const std::uint64_t finishedAt = rollback ? 99 : 2601;
        const auto stale = sampling.observe(ready, 100, finishedAt);
        assert(!stale.allowed && stale.epoch != old.epoch);
        const auto fresh = sampling.observe(ready, finishedAt + 1, finishedAt + 2);
        assert(fresh.allowed && fresh.epoch != old.epoch);
    }
    InteractionPermitState boundary;
    assert(boundary.observe(ready, 100, 2600).allowed);
#ifndef _WIN32
    WindowsTray unsupported(0, {}, {}, {});
    assert(!unsupported.interactionPermit().allowed);
#endif
    // Source wiring, not live WTS/power/secure-desktop evidence.
    const auto tray = source("Shell/WindowsTray.cpp");
    for (const auto api : {"WTSRegisterSessionNotification", "NOTIFY_FOR_THIS_SESSION",
                          "WTSQuerySessionInformationW", "WTSSessionInfoEx", "WTSFreeMemory",
                          "WTS_SESSIONSTATE_UNLOCK", "GetThreadDesktop", "UOI_IO",
                          "RegisterSuspendResumeNotification", "DEVICE_NOTIFY_WINDOW_HANDLE",
                          "EVENT_SYSTEM_DESKTOPSWITCH", "WINEVENT_OUTOFCONTEXT",
                          "WM_WTSSESSION_CHANGE", "WM_POWERBROADCAST",
                          "WTSUnRegisterSessionNotification", "UnregisterSuspendResumeNotification", "UnhookWinEvent"})
        assert(tray.find(api) != std::string::npos);
    assert(tray.find("interaction.retrySubscriptionsDue(now)") != std::string::npos);
    const auto probe = section(tray, "    InteractionPermit checkInteraction()", "    void cleanupInteraction()");
    assert(probe.find("interaction.observe") != std::string::npos);
    expectBefore(probe, "WTSQuerySessionInformationW(", "const auto finishedAt = GetTickCount64()");
    expectBefore(probe, "GetUserObjectInformationW(", "const auto finishedAt = GetTickCount64()");
    expectBefore(probe, "const auto finishedAt = GetTickCount64()", "interaction.observe(sample, now, finishedAt)");
    assert(probe.find("registered") == std::string::npos); // independent of Explorer icon availability
    assert(probe.find("invalidationHandler()") == std::string::npos); // no callback during a card probe
    const auto lifecycle = section(tray, "    void interactionEvent(", "    // Тема");
    assert(lifecycle.find("capture_") == std::string::npos);
    assert(lifecycle.find("SetForegroundWindow") == std::string::npos);
    const auto app = source("AppMain.cpp");
    assert(app.find("interactionPermitProvider = [this] { return interactionPermit(); }") != std::string::npos);
    const auto start = section(app, "    void startAutomaticRecording(", "    bool closeAutomaticPrompt(");
    expectBefore(start, "interactionEpoch = permit.epoch", "if (!permit.allowed || permit.epoch != interactionEpoch)");
    expectBefore(start, "if (!permit.allowed || permit.epoch != interactionEpoch)", "automaticPolicy_.acceptStart(");
    const auto finalGuard = section(start,
        "prerequisites.oneActionStopAvailable = prerequisites.visibleIndicatorAvailable;",
        "return automaticPolicy_.acceptStart(");
    expectBefore(finalGuard, " = interactionPermit();", ".epoch != interactionEpoch");
    assert(finalGuard.find(".allowed") != std::string::npos);
    const auto refresh = section(app, "    void refreshNativeState()", "    TextBlock privacyNotice_");
    // The exit-only branch polls completion, never automatic start or notices.
    // Keep the original interaction-before-start assertions on the normal path.
    const auto normalAt = refresh.find("        const CustodyMutationScope mutation(shellMutations_)");
    assert(normalAt != std::string::npos);
    const auto normalRefresh = refresh.substr(normalAt);
    expectBefore(normalRefresh, "refreshNotificationInteraction()", "capture_->pollHealth()");
    expectBefore(normalRefresh, "capture_->pollUploads()", "notificationCard().presentPendingShort(");
    expectBefore(normalRefresh, "notificationCard().presentPendingShort(", "refreshMeetingReminders()");
    const auto invalidate = section(app, "    void invalidateNotificationInteraction()", "    void refreshNotificationInteraction()");
    expectBefore(invalidate, "!capture_->indicator().visible || capture_->indicator().state == graf::windows::SessionState::starting",
                 "automaticPolicy_.cancel()");
    assert(invalidate.find("notificationCard().invalidatePresentation()") != std::string::npos);
    assert(invalidate.find("resetContext()") == std::string::npos);
    assert(invalidate.find("Hide()") == std::string::npos);
    assert(invalidate.find("capture_->stop") == std::string::npos);
}

void testRecordingProblemAndShortSourceWiring() {
    // These assertions keep the tested model connected to the WinUI shell;
    // they supplement, not replace, native compilation and interaction tests.
    const auto app = source("AppMain.cpp");
    const auto capture = source("Recording/NativeCapture.h");
    const auto projection = section(capture,
        "    [[nodiscard]] graf::windows::CustodyVector<graf::windows::ProtectedLocalProblemProjection> recordingProblems(",
        "    [[nodiscard]] const auto& custodyRoot()");
    assert(projection.find("const bool blocker = !deliberateShort") != std::string::npos);
    assert(projection.find("state.state == State::blocked && state.reason != graf::windows::ReasonCode::none") != std::string::npos);
    assert(projection.find("const auto observation = localObservation()") != std::string::npos);
    assert(projection.find("projectProtectedLocalRecordingProblems(") != std::string::npos);
    assert(projection.find("observation.value ? observation.value->items() : noRows, observation.complete") != std::string::npos);
    assert(projection.find("queue_.items()") == std::string::npos);
    // Protected V5 publishes only discard intent. Until the separate purge and
    // OS-absence ACK is connected (T120), no short notice/removal may be emitted.
    const auto storage = section(capture, "    static unsigned __stdcall runStorageStartup(",
        "    void pollStorageStartup(bool allowDisplay)");
    assert(storage.find("!recordingResult->shortRecordingDiscarded") != std::string::npos);
    assert(storage.find("durable && keepable") != std::string::npos);
    assert(storage.find("recording->terminal = true") != std::string::npos);
    assert(capture.find("queueShortRecordingDiscarded(") == std::string::npos);
    assert(capture.find("showShortRecordingDiscarded(") == std::string::npos);
    const auto completion = section(capture, "    void createRecordingPipeline()", "public:");
    expectBefore(completion, "recordingWork_->epoch != authGeneration_", "result.savedLocal = false");
    assert(app.find("PendingShortNotice") == std::string::npos); // one presenter-owned pending short
    const auto reconcile = section(app, "    void reconcileRecordingProblems()", "    void refreshSelectedRecording()");
    expectBefore(reconcile, "const auto problems = capture_->recordingProblems(", "problemStore_.resolveProblem(");
    expectBefore(reconcile, "LocalProblemState::positivelyResolved", "problemStore_.resolveProblem(");
    expectBefore(reconcile, "problemStore_.claimProblem(", "card.recordProblemHistory(");
    expectBefore(reconcile, "card.recordProblemHistory(", "if (reminders_->preferences().quiet)");
    assert(reconcile.find("pendingProblems_.size() >= 256") != std::string::npos);
    const auto failureAt = reconcile.find("catch (const std::bad_alloc&)");
    assert(failureAt != std::string::npos);
    const auto failure = reconcile.substr(failureAt);
    for (const auto required : {"pendingProblems_.clear()", "presentedProblem_.reset()", "selectedRecording_.reset()",
            "selectedRecordingDisplayKey_.clear()", "card.kind() == graf::windows::NoticeKind::problem", "card.invalidate()", "refreshSelectedRecording()"})
        assert(failure.find(required) != std::string::npos);
    for (const auto forbidden : {"resolveProblem(", "resetContext(", "invalidateNotificationInteraction(",
            "invalidatePresentation(", "automaticPolicy_", "capture_->stop(", "recordingProblems("})
        assert(failure.find(forbidden) == std::string::npos);
    const auto action = section(app, "    [[nodiscard]] bool problemActionCurrent(", "    void openProblemRecording(");
    assert(action.find("catch (const std::bad_alloc&)") != std::string::npos);
    expectBefore(action, "catch (const std::bad_alloc&)", "return false;\n    }");
    const auto open = section(app, "    void openProblemRecording(", "    void reconcileRecordingProblems()");
    expectBefore(open, "if (!problemActionCurrent(target)) return", "selectedRecording_ = target");
    assert(open.find("StartBringIntoView()") != std::string::npos);
    assert(open.find("Focus(FocusState::Programmatic)") != std::string::npos);
    assert(open.find("ShellExecute") == std::string::npos); // inspect this session, never launch its M4A
    const auto context = section(app, "    void bindNotificationContext()", "    void setLocalNotificationStatus(");
    assert(context.find("pendingProblems_.clear()") != std::string::npos);
    assert(context.find("selectedRecording_.reset()") != std::string::npos);
    const auto refresh = section(app, "    void refreshNativeState()", "    TextBlock privacyNotice_");
    expectBefore(refresh, "capture_->pollUploads()", "reconcileRecordingProblems()");
    expectBefore(refresh, "reconcileRecordingProblems()", "notificationCard().presentPendingShort(");
    expectBefore(refresh, "notificationCard().presentPendingShort(", "refreshMeetingReminders()");
}

} // namespace

int main() {
#ifdef _WIN32
    winrt::init_apartment(winrt::apartment_type::single_threaded);
#endif
    using namespace graf::windows;
    testUpcomingUserTimeFormatter();
    testUpcomingMenuRows();
    testUpcomingMenuIdentityAndExpiry();
    testClosePolicy();
    testCloseKeepsTheSessionAndAutomaticTracking();
    testCloseSourceWiring();
    testSelectedLocalRemovalSourceWiring();
    testBackgroundSurfaceWiring();
    testTrayActionWiring();
    testTrayActionAvailability();
    testCalendarJoinOwnerSourceWiring();
#ifdef _WIN32
    testNativeCalendarPopup();
#endif
    testLocalNotificationSettingsWiring();
    testSystemThemeRefreshWiring();
    testInteractionLifecycle();
    testRecordingProblemAndShortSourceWiring();
#ifndef _WIN32
    WindowsTray unsupported(0, {}, {}, {});
    assert(!unsupported.available()); // A portable stub never claims a real tray.
#endif
    RecordingIndicator indicator;
    indicator.publish(SessionState::degraded, ReasonCode::clockDiscontinuity);
    assert(indicator.snapshot().visible && indicator.snapshot().stopAvailable);
    assert(indicator.snapshot().statusText == "Запись ограничена");
    indicator.publish(SessionState::failed, ReasonCode::microphoneEndpointUnavailable);
    assert(indicator.snapshot().state == SessionState::failed);
    assert(indicator.snapshot().reason == ReasonCode::microphoneEndpointUnavailable);
    assert(indicator.snapshot().statusText == "Запись завершилась с ошибкой");
    assert(!indicator.snapshot().visible && !indicator.snapshot().stopAvailable);
#ifdef _WIN32
    winrt::uninit_apartment();
#endif
    return 0;
}
