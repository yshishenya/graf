#include "WindowsTray.h"

#ifdef _WIN32

#include "ShellPalette.h"

#include <windows.h>
#include <windowsx.h>
#include <shellapi.h>
#include <oleacc.h>
#include <wtsapi32.h>
#ifdef _MSC_VER
#pragma comment(lib, "Wtsapi32.lib")
#endif

#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace graf::windows {

struct WindowsTray::Impl {
    static constexpr UINT kTrayMessage = WM_APP + 200;
    static constexpr UINT kIconId = 200;
    static constexpr UINT kOpenCommand = 1;
    static constexpr UINT kStopCommand = 2;
    static constexpr UINT kQuitCommand = 3;
    static constexpr UINT kPauseResumeCommand = 4;
    static constexpr UINT kStartCommand = 5;
    static constexpr UINT kSettingsCommand = 6;
    static constexpr UINT kFocusNotificationCommand = 7;
    static constexpr UINT kUpdateCommand = 8;
    static constexpr UINT kInteractionInvalidated = WM_APP + 201;
    static constexpr UINT_PTR kInteractionTimer = 201;

    struct MenuItem {
        // Win32 exposes owner-drawn names to screen readers through this first
        // member; the backing text remains alive throughout the nested menu loop.
        MSAAMENUINFO accessibility{};
        std::wstring text;
        bool separator = false;
        bool disabled = false;
    };

    HWND window = nullptr;
    HICON icon = nullptr;
    UINT taskbarCreated = 0;
    bool registered = false;
    InteractionPermitState interaction;
    Handler invalidationHandler;
    DWORD shellThreadId = 0, sessionId = 0;
    bool sessionIdKnown = false, sessionSubscribed = false, interactionTimer = false;
    bool queryingInteraction = false, invalidationPending = false, interactionStopped = false;
    HPOWERNOTIFY powerSubscription = nullptr;
    HWINEVENTHOOK desktopSubscription = nullptr;
    // Routing only, on the subscribing UI thread. No allocation/global input hook.
    inline static thread_local Impl* firstDesktopHook = nullptr;
    Impl* nextDesktopHook = nullptr;

    void deliverInvalidation() noexcept {
        if (!invalidationPending || queryingInteraction || interactionStopped) return;
        invalidationPending = false;
        try {
            const auto handler = invalidationHandler;
            if (handler) handler(); // may destroy this tray; never touch self after it
        } catch (...) {} // no exception may cross WindowProc/WinEventProc
    }
    void queueInvalidation() noexcept {
        if (invalidationPending || interactionStopped) return;
        invalidationPending = true;
        (void)PostMessageW(window, kInteractionInvalidated, 0, 0);
        // A failed post is retried by the lifecycle timer, never by a card query.
    }
    void interactionEvent(InteractionEvent event) noexcept {
        if (interactionStopped) return;
        interaction.event(event);
        if (queryingInteraction) { queueInvalidation(); return; }
        invalidationPending = true;
        deliverInvalidation(); // synchronous event path; no access to self afterwards
    }
    static void CALLBACK desktopChanged(HWINEVENTHOOK hook, DWORD, HWND, LONG, LONG, DWORD, DWORD) noexcept {
        for (auto* owner = firstDesktopHook; owner; owner = owner->nextDesktopHook) {
            if (owner->desktopSubscription != hook) continue;
            owner->interactionEvent(InteractionEvent::desktopSwitch);
            return; // callback may have unlinked and destroyed owner
        }
    }
    void retryInteractionSubscriptions(ULONGLONG now) noexcept {
        if (interactionStopped || !window) return;
        if (sessionIdKnown && sessionSubscribed && powerSubscription && desktopSubscription && interactionTimer) return;
        if (!interaction.retrySubscriptionsDue(now)) return;
        if (!sessionIdKnown) sessionIdKnown = ProcessIdToSessionId(GetCurrentProcessId(), &sessionId) != FALSE;
        if (!sessionSubscribed) sessionSubscribed = WTSRegisterSessionNotification(window, NOTIFY_FOR_THIS_SESSION) != FALSE;
        if (!powerSubscription) powerSubscription = RegisterSuspendResumeNotification(window, DEVICE_NOTIFY_WINDOW_HANDLE);
        if (!desktopSubscription) {
            desktopSubscription = SetWinEventHook(EVENT_SYSTEM_DESKTOPSWITCH, EVENT_SYSTEM_DESKTOPSWITCH,
                nullptr, &Impl::desktopChanged, 0, 0, WINEVENT_OUTOFCONTEXT);
            if (desktopSubscription) {
                nextDesktopHook = firstDesktopHook;
                firstDesktopHook = this;
            }
        }
        if (!interactionTimer) interactionTimer = SetTimer(window, kInteractionTimer, 250, nullptr) != 0;
    }
    InteractionPermit checkInteraction() noexcept {
        if (interactionStopped || GetCurrentThreadId() != shellThreadId) return {};
        if (queryingInteraction) return {false, interaction.permit().epoch};
        queryingInteraction = true;
        struct QueryScope { bool& value; ~QueryScope() { value = false; } } scope{queryingInteraction};
        const auto before = interaction.permit().epoch;
        const auto now = GetTickCount64();
        retryInteractionSubscriptions(now);
        InteractionSample sample;
        sample.subscriptionsReady = sessionIdKnown && sessionSubscribed && powerSubscription && desktopSubscription && interactionTimer;
        LPWSTR buffer = nullptr;
        DWORD bytes = 0;
        if (WTSQuerySessionInformationW(WTS_CURRENT_SERVER_HANDLE, WTS_CURRENT_SESSION,
                                       WTSSessionInfoEx, &buffer, &bytes) && buffer && bytes >= sizeof(WTSINFOEXW)) {
            const auto* info = reinterpret_cast<const WTSINFOEXW*>(buffer);
            if (info->Level == 1 && sessionIdKnown && info->Data.WTSInfoExLevel1.SessionId == sessionId) {
                sample.sessionActive = info->Data.WTSInfoExLevel1.SessionState == WTSActive;
                sample.sessionUnlocked = info->Data.WTSInfoExLevel1.SessionFlags == WTS_SESSIONSTATE_UNLOCK;
            }
        }
        if (buffer) WTSFreeMemory(buffer);
        // Check OUR desktop, not just OpenInputDesktop (which can succeed in a
        // disconnected session). This borrowed handle must not be CloseDesktop'd.
        const auto desktop = GetThreadDesktop(shellThreadId);
        BOOL input = FALSE;
        DWORD needed = 0;
        sample.inputDesktop = desktop && GetUserObjectInformationW(desktop, UOI_IO, &input, sizeof(input), &needed) &&
            needed == sizeof(input) && input == TRUE;
        const auto finishedAt = GetTickCount64();
        const auto permit = interaction.observe(sample, now, finishedAt);
        if (permit.epoch != before) queueInvalidation();
        return permit; // no external handler, message pumping or capture mutation
    }
    void cleanupInteraction() noexcept {
        if (interactionStopped) return;
        interactionStopped = true;
        interaction.event(InteractionEvent::shutdown);
        invalidationPending = false;
        invalidationHandler = {};
        if (interactionTimer && window) KillTimer(window, kInteractionTimer);
        interactionTimer = false;
        if (sessionSubscribed && window) WTSUnRegisterSessionNotification(window);
        sessionSubscribed = false;
        if (powerSubscription) UnregisterSuspendResumeNotification(powerSubscription);
        powerSubscription = nullptr;
        if (desktopSubscription) {
            for (auto** link = &firstDesktopHook; *link; link = &(*link)->nextDesktopHook) {
                if (*link != this) continue;
                *link = nextDesktopHook;
                break;
            }
            UnhookWinEvent(desktopSubscription);
        }
        desktopSubscription = nullptr;
        nextDesktopHook = nullptr;
    }
    ~Impl() { cleanupInteraction(); }
    // Тема приходит из оболочки: меню рисуется её кистями, а не системными.
    bool isDark = true;
    std::vector<std::unique_ptr<MenuItem>> menuItems;
    Handler openHandler;
    Handler stopHandler;
    Handler quitHandler;
    Handler pauseResumeHandler;
    Handler startHandler;
    Handler settingsHandler;
    Handler updateHandler;
    Handler focusNotificationHandler;
    bool notificationVisible = false;
    std::vector<std::wstring> notificationHistory;
    RecordingIndicatorSnapshot snapshot;
    MenuAvailability actions{false, false, false, true};

    static LRESULT CALLBACK windowProc(HWND window, UINT message, WPARAM wParam, LPARAM lParam) {
        auto* self = reinterpret_cast<Impl*>(GetWindowLongPtrW(window, GWLP_USERDATA));
        if (message == WM_NCCREATE) {
            const auto* create = reinterpret_cast<const CREATESTRUCTW*>(lParam);
            self = static_cast<Impl*>(create->lpCreateParams);
            SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
            self->window = window;
        }
        if (self == nullptr) return DefWindowProcW(window, message, wParam, lParam);
        if (message == WM_WTSSESSION_CHANGE) {
            if (!self->sessionIdKnown || static_cast<DWORD>(lParam) != self->sessionId) return 0;
            switch (wParam) {
            case WTS_SESSION_LOCK:
            case WTS_CONSOLE_DISCONNECT:
            case WTS_REMOTE_DISCONNECT:
            case WTS_SESSION_LOGOFF:
                self->interactionEvent(InteractionEvent::sessionUnavailable); break;
            case WTS_SESSION_UNLOCK:
            case WTS_CONSOLE_CONNECT:
            case WTS_REMOTE_CONNECT:
            case WTS_SESSION_LOGON:
                self->interactionEvent(InteractionEvent::sessionAvailable); break;
            default: break;
            }
            return 0;
        }
        if (message == WM_POWERBROADCAST) {
            switch (wParam) {
            case PBT_APMSUSPEND: self->interactionEvent(InteractionEvent::suspend); break;
            case PBT_APMRESUMEAUTOMATIC: self->interactionEvent(InteractionEvent::resumeAutomatic); break;
            case PBT_APMRESUMESUSPEND: self->interactionEvent(InteractionEvent::resumeInteractive); break;
            default: break;
            }
            return TRUE;
        }
        if (message == kInteractionInvalidated) {
            self->deliverInvalidation();
            return 0;
        }
        if (message == WM_TIMER && wParam == kInteractionTimer) {
            (void)self->checkInteraction();
            self->deliverInvalidation();
            return 0;
        }
        if (message == self->taskbarCreated) {
            self->registered = false;
            (void)self->addIcon();
            return 0;
        }
        if (message == kTrayMessage) {
            // VERSION4 packs the event/id in lParam and signed coordinates in wParam.
            if (HIWORD(lParam) != kIconId) return 0;
            switch (LOWORD(lParam)) {
            case NIN_SELECT:
            case NIN_KEYSELECT: {
                const auto handler = self->openHandler;
                if (handler) handler();
                break;
            }
            case WM_CONTEXTMENU:
                self->showMenu({GET_X_LPARAM(wParam), GET_Y_LPARAM(wParam)});
                break;
            default:
                break;
            }
            return 0;
        }
        if (message == WM_COMMAND) {
            Handler handler;
            switch (LOWORD(wParam)) {
            case kOpenCommand:
                handler = self->openHandler;
                break;
            case kStopCommand:
                if (self->actions.stop) handler = self->stopHandler;
                break;
            case kPauseResumeCommand:
                if (self->actions.pauseResume) handler = self->pauseResumeHandler;
                break;
            case kStartCommand:
                if (self->actions.start) handler = self->startHandler;
                break;
            case kSettingsCommand:
                if (self->actions.settings) handler = self->settingsHandler;
                break;
            case kUpdateCommand:
                if (self->actions.settings) handler = self->updateHandler;
                break;
            case kFocusNotificationCommand:
                if (self->actions.settings && self->notificationVisible) handler = self->focusNotificationHandler;
                break;
            case kQuitCommand:
                handler = self->quitHandler;
                break;
            default:
                break;
            }
            // A handler may destroy the shell and this tray; do not access self afterwards.
            if (handler) handler();
            return 0;
        }
        if (message == WM_MEASUREITEM) {
            self->measureItem(reinterpret_cast<MEASUREITEMSTRUCT*>(lParam));
            return TRUE;
        }
        if (message == WM_DRAWITEM) {
            self->drawItem(reinterpret_cast<const DRAWITEMSTRUCT*>(lParam));
            return TRUE;
        }
        if (message == WM_DESTROY) {
            self->cleanupInteraction();
            self->removeIcon();
            return 0;
        }
        if (message == WM_NCDESTROY) {
            SetWindowLongPtrW(window, GWLP_USERDATA, 0);
            self->window = nullptr;
        }
        return DefWindowProcW(window, message, wParam, lParam);
    }


    // Кисти берутся из палитры оболочки: меню обязано совпадать с окном.
    COLORREF colorOf(const wchar_t* key, COLORREF fallback) const {
        for (const auto& entry : shellPaletteEntries()) {
            if (std::wcscmp(entry.key, key) != 0) continue;
            const auto value = shellPaletteColor(entry, isDark);
            return RGB((value.rgb >> 16) & 0xFF, (value.rgb >> 8) & 0xFF, value.rgb & 0xFF);
        }
        return fallback;
    }

    HBRUSH backgroundBrush() const {
        return CreateSolidBrush(colorOf(L"GrafPanelBrush", isDark ? RGB(29, 31, 35) : RGB(255, 255, 255)));
    }

    void addItem(HMENU menu, const std::wstring& text, UINT_PTR id, bool separator, bool disabled = false, bool submenu = false) {
        auto item = std::make_unique<MenuItem>();
        item->text = text;
        item->accessibility.dwMSAASignature = MSAA_MENU_SIG;
        item->accessibility.cchWText = static_cast<DWORD>(item->text.size());
        item->accessibility.pszWText = item->text.data();
        item->separator = separator;
        item->disabled = disabled;
        // Для MF_OWNERDRAW данные пункта передаются в параметре строки.
        const UINT flags = MF_OWNERDRAW | (separator ? MF_SEPARATOR : 0U) | (submenu ? MF_POPUP : 0U) |
            (disabled || separator ? MF_DISABLED | MF_GRAYED : MF_ENABLED);
        AppendMenuW(menu, flags, id, reinterpret_cast<LPCWSTR>(item.get()));
        menuItems.push_back(std::move(item));
    }

    void measureItem(MEASUREITEMSTRUCT* measure) const {
        const auto* item = reinterpret_cast<const MenuItem*>(measure->itemData);
        if (item == nullptr) return;
        measure->itemHeight = item->separator ? 9 : 30;
        if (item->separator) {
            measure->itemWidth = 220;
            return;
        }
        const auto dc = GetDC(window);
        if (dc == nullptr) {
            measure->itemWidth = 260;
            return;
        }
        // Ширина по самой длинной строке плюс поля, как у системного меню.
        auto font = static_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));
        const auto previous = SelectObject(dc, font);
        SIZE size{};
        GetTextExtentPoint32W(dc, item->text.c_str(), static_cast<int>(item->text.size()), &size);
        SelectObject(dc, previous);
        ReleaseDC(window, dc);
        measure->itemWidth = static_cast<UINT>(size.cx) + 64;
    }

    void drawItem(const DRAWITEMSTRUCT* draw) const {
        const auto* item = reinterpret_cast<const MenuItem*>(draw->itemData);
        if (item == nullptr) return;
        const bool selected = (draw->itemState & ODS_SELECTED) != 0 && !item->disabled;
        if (item->separator) {
            const auto background = CreateSolidBrush(colorOf(L"GrafPanelBrush", RGB(29, 31, 35)));
            FillRect(draw->hDC, &draw->rcItem, background);
            DeleteObject(background);
            const auto line = CreateSolidBrush(colorOf(L"GrafLineSoftBrush", RGB(70, 74, 84)));
            RECT rule = draw->rcItem;
            rule.top += 4;
            rule.bottom = rule.top + 1;
            rule.left += 12;
            rule.right -= 12;
            FillRect(draw->hDC, &rule, line);
            DeleteObject(line);
            return;
        }
        const auto background = CreateSolidBrush(selected
            ? colorOf(L"GrafAccentSolidBrush", RGB(112, 86, 233))
            : colorOf(L"GrafPanelBrush", RGB(29, 31, 35)));
        FillRect(draw->hDC, &draw->rcItem, background);
        DeleteObject(background);
        SetBkMode(draw->hDC, TRANSPARENT);
        const COLORREF text = selected ? RGB(255, 255, 255)
                                       : item->disabled ? colorOf(L"GrafMutedTextBrush", RGB(173, 178, 188))
                                                        : colorOf(L"GrafTextBrush", RGB(240, 241, 244));
        SetTextColor(draw->hDC, text);
        auto font = static_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));
        const auto previous = SelectObject(draw->hDC, font);
        RECT text_rect = draw->rcItem;
        text_rect.left += 16;
        text_rect.right -= 12;
        DrawTextW(draw->hDC, item->text.c_str(), static_cast<int>(item->text.size()), &text_rect,
                  DT_SINGLELINE | DT_VCENTER | DT_LEFT | DT_END_ELLIPSIS);
        SelectObject(draw->hDC, previous);
    }

    void showMenu(POINT point) {
        if (point.x == -1 && point.y == -1) {
            NOTIFYICONIDENTIFIER identifier{};
            identifier.cbSize = sizeof(identifier);
            identifier.hWnd = window;
            identifier.uID = kIconId;
            RECT bounds{};
            if (SUCCEEDED(Shell_NotifyIconGetRect(&identifier, &bounds))) {
                point = {bounds.left, bounds.bottom};
            } else {
                GetCursorPos(&point);
            }
        }
        const auto menu = CreatePopupMenu();
        if (!menu) return;
        auto data = iconData();
        // Пункты рисуются сами: системное меню берёт цвета у Windows и на
        // тёмном окне GRAF выглядит светлым чужеродным пятном.
        addItem(menu, data.szTip, 0, false, true);
        addItem(menu, L"", 0, true);
        addItem(menu, L"Открыть GRAF", kOpenCommand, false);
        SetMenuDefaultItem(menu, kOpenCommand, FALSE);
        addItem(menu, L"Начать запись", kStartCommand, false, !actions.start || !startHandler);
        if (pauseResumeHandler && (snapshot.state == SessionState::recording || snapshot.state == SessionState::paused)) {
            addItem(menu, snapshot.state == SessionState::paused ? L"Продолжить запись микрофона" : L"Пауза микрофона",
                    kPauseResumeCommand, false, !actions.pauseResume);
        }
        addItem(menu, L"Остановить запись", kStopCommand, false, !actions.stop || !stopHandler);
        addItem(menu, L"", 0, true);
        addItem(menu, L"Настройки", kSettingsCommand, false, !actions.settings || !settingsHandler);
        addItem(menu, L"Проверить обновления…", kUpdateCommand, false, !actions.settings || !updateHandler);
        addItem(menu, L"Перейти к уведомлению", kFocusNotificationCommand, false,
                !actions.settings || !notificationVisible || !focusNotificationHandler);
        const auto historyMenu = CreatePopupMenu();
        if (historyMenu) {
            if (notificationHistory.empty()) addItem(historyMenu, L"Уведомлений пока нет", 0, false, true);
            else for (const auto& entry : notificationHistory) addItem(historyMenu, entry, 0, false, true);
            addItem(menu, L"История уведомлений", reinterpret_cast<UINT_PTR>(historyMenu), false, false, true);
        }
        addItem(menu, L"Закрыть GRAF", kQuitCommand, false);
        MENUINFO info{};
        info.cbSize = sizeof(info);
        info.fMask = MIM_BACKGROUND | MIM_APPLYTOSUBMENUS;
        info.hbrBack = backgroundBrush();
        SetMenuInfo(menu, &info);
        const auto menuWindow = window;
        // The nested loop can process Quit and destroy this Impl. Item data
        // and the brush must outlive that loop without accessing this afterwards.
        auto menuLifetime = std::move(menuItems);
        SetForegroundWindow(menuWindow);
        const auto command = TrackPopupMenuEx(menu, TPM_RETURNCMD | TPM_NONOTIFY | TPM_RIGHTBUTTON,
                                             point.x, point.y, menuWindow, nullptr);
        // The nested menu loop may close the owner. Use only local handles from here.
        DestroyMenu(menu);
        menuLifetime.clear();
        DeleteObject(info.hbrBack);
        if (IsWindow(menuWindow)) {
            PostMessageW(menuWindow, WM_NULL, 0, 0);
            Shell_NotifyIconW(NIM_SETFOCUS, &data);
            if (command) PostMessageW(menuWindow, WM_COMMAND, command, 0);
        }
    }

    NOTIFYICONDATAW iconData() const noexcept {
        NOTIFYICONDATAW data{};
        data.cbSize = sizeof(data);
        data.hWnd = window;
        data.uID = kIconId;
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_SHOWTIP;
        data.uCallbackMessage = kTrayMessage;
        data.hIcon = icon;
        if (snapshot.state == SessionState::paused) {
            wcsncpy_s(data.szTip, L"GRAF — Микрофон на паузе; системный звук записывается", _TRUNCATE);
        } else if (snapshot.statusText.empty()) {
            wcsncpy_s(data.szTip, L"GRAF", _TRUNCATE);
        } else {
            wchar_t status[128]{};
            if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, snapshot.statusText.c_str(), -1,
                                    status, static_cast<int>(_countof(status))) == 0) {
                wcsncpy_s(status, L"Статус недоступен", _TRUNCATE);
            }
            wcscpy_s(data.szTip, L"GRAF — ");
            wcsncat_s(data.szTip, status, _TRUNCATE);
        }
        return data;
    }

    void removeIcon() noexcept {
        registered = false;
        if (!window) return;
        auto data = iconData();
        Shell_NotifyIconW(NIM_DELETE, &data);
    }

    void updateIcon() noexcept {
        if (!window || !IsWindow(window)) { registered = false; return; }
        auto data = iconData();
        if (registered && Shell_NotifyIconW(NIM_MODIFY, &data)) return;
        registered = false;
        (void)addIcon();
    }

    bool addIcon() noexcept {
        registered = false;
        if (!window || !icon) return false;
        auto data = iconData();
        // A periodic recovery can beat the queued TaskbarCreated broadcast.
        // Accept our existing HWND/id only after MODIFY and SETVERSION succeed.
        if (!Shell_NotifyIconW(NIM_ADD, &data) && !Shell_NotifyIconW(NIM_MODIFY, &data)) return false;
        data.uVersion = NOTIFYICON_VERSION_4;
        if (Shell_NotifyIconW(NIM_SETVERSION, &data)) {
            registered = true;
            return true;
        }
        removeIcon();
        return false;
    }
};

WindowsTray::WindowsTray(std::uintptr_t ownerWindow, Handler openHandler, Handler stopHandler,
                         Handler quitHandler, Handler pauseResumeHandler, Handler startHandler, Handler settingsHandler,
                         Handler focusNotificationHandler, Handler interactionInvalidated)
    : impl_(std::make_unique<Impl>()) {
    impl_->openHandler = std::move(openHandler);
    impl_->stopHandler = std::move(stopHandler);
    impl_->quitHandler = std::move(quitHandler);
    impl_->pauseResumeHandler = std::move(pauseResumeHandler);
    impl_->startHandler = std::move(startHandler);
    impl_->settingsHandler = std::move(settingsHandler);
    impl_->focusNotificationHandler = std::move(focusNotificationHandler);
    impl_->invalidationHandler = std::move(interactionInvalidated);
    impl_->shellThreadId = GetCurrentThreadId();
    const auto instance = GetModuleHandleW(nullptr);
    impl_->icon = LoadIconW(instance, MAKEINTRESOURCEW(1));
    if (!impl_->icon) throw std::runtime_error("GRAF tray icon resource 1 is unavailable");
    impl_->taskbarCreated = RegisterWindowMessageW(L"TaskbarCreated");
    if (!impl_->taskbarCreated) throw std::runtime_error("GRAF tray recovery message registration failed");
    static const wchar_t className[] = L"GRAF.WindowsTray";
    WNDCLASSW windowClass{};
    windowClass.lpfnWndProc = &Impl::windowProc;
    windowClass.hInstance = instance;
    windowClass.lpszClassName = className;
    windowClass.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    if (!RegisterClassW(&windowClass) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS) {
        throw std::runtime_error("GRAF tray window registration failed");
    }
    // TaskbarCreated is broadcast only to top-level windows, not HWND_MESSAGE.
    impl_->window = CreateWindowExW(WS_EX_TOOLWINDOW, className, L"GRAF", WS_POPUP, 0, 0, 0, 0,
                                    reinterpret_cast<HWND>(ownerWindow), nullptr, instance, impl_.get());
    if (!impl_->window) throw std::runtime_error("GRAF tray window creation failed");
    // Keep the recovery window if Explorer is temporarily unavailable. The
    // shell stays visible; TaskbarCreated and subsequent state ticks retry.
    (void)impl_->addIcon();
    (void)impl_->checkInteraction();
}

WindowsTray::~WindowsTray() {
    if (!impl_) return;
    impl_->cleanupInteraction();
    if (impl_->window) DestroyWindow(impl_->window);
}

void WindowsTray::setState(const RecordingIndicatorSnapshot& snapshot, bool recordingReady, bool exiting) {
    if (!impl_) return;
    impl_->snapshot = snapshot;
    impl_->actions = menuAvailability(snapshot, recordingReady, exiting);
    impl_->updateIcon();
}

bool WindowsTray::available() noexcept {
    if (!impl_) return false;
    impl_->updateIcon();
    return impl_->registered;
}

InteractionPermit WindowsTray::interactionPermit() noexcept {
    return impl_ ? impl_->checkInteraction() : InteractionPermit{};
}

void WindowsTray::setTheme(bool isDark) {
    if (!impl_) return;
    impl_->isDark = isDark;
}

void WindowsTray::setUpdateHandler(Handler handler) {
    if (impl_) impl_->updateHandler = std::move(handler);
}

void WindowsTray::setNotificationState(bool visible, std::vector<std::wstring> history) {
    if (!impl_) return;
    impl_->notificationVisible = visible;
    if (history.size() > 50) history.resize(50);
    impl_->notificationHistory = std::move(history);
}

} // namespace graf::windows

#else

namespace graf::windows {

struct WindowsTray::Impl {};

WindowsTray::WindowsTray(std::uintptr_t, Handler, Handler, Handler, Handler, Handler, Handler, Handler, Handler)
    : impl_(std::make_unique<Impl>()) {}

WindowsTray::~WindowsTray() = default;

void WindowsTray::setState(const RecordingIndicatorSnapshot&, bool, bool) {}

bool WindowsTray::available() noexcept { return false; }

InteractionPermit WindowsTray::interactionPermit() noexcept { return {}; }

void WindowsTray::setTheme(bool) {}
void WindowsTray::setUpdateHandler(Handler) {}

void WindowsTray::setNotificationState(bool, std::vector<std::wstring>) {}

} // namespace graf::windows

#endif
