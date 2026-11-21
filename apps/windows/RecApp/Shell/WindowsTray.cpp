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
#include <algorithm>
#include <cstdlib>
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
    static constexpr UINT kCalendarCommand = 100;
    static constexpr UINT kInteractionInvalidated = WM_APP + 201;
    static constexpr UINT_PTR kInteractionTimer = 201;

    struct MenuStyle {
        std::shared_ptr<void> font;
        int dpi = 96, maxWidth = 640;
        COLORREF background = 0, text = 0, muted = 0, selected = 0, selectedText = 0, line = 0;
        int scale(int value) const noexcept { return MulDiv(value, dpi, 96); }
    };
    struct PopupToken { bool current = true, preparing = true, tracking = false; };
    struct MenuItem {
        // Win32 exposes owner-drawn names to screen readers through this first
        // member; the backing text remains alive throughout the nested menu loop.
        MSAAMENUINFO accessibility{};
        std::wstring text;
        std::shared_ptr<MenuStyle> style;
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
    std::shared_ptr<PopupToken> popupToken;
    void invalidateMenu() noexcept {
        if (!popupToken) return;
        popupToken->current = false;
        if (popupToken->tracking) EndMenu();
    }
    HPOWERNOTIFY powerSubscription = nullptr;
    HWINEVENTHOOK desktopSubscription = nullptr;
    // Routing only, on the subscribing UI thread. No allocation/global input hook.
    inline static thread_local Impl* firstDesktopHook = nullptr;
    Impl* nextDesktopHook = nullptr;

    void deliverInvalidation() noexcept {
        if (!invalidationPending || queryingInteraction || interactionStopped) return;
        invalidationPending = false;
        invalidateMenu();
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
        invalidateMenu();
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
        if (permit.epoch != before) { invalidateMenu(); queueInvalidation(); }
        return permit; // no external handler, message pumping or capture mutation
    }
    void cleanupInteraction() noexcept {
        invalidateMenu();
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
    std::shared_ptr<MenuStyle> menuStyle;
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
    CalendarHandler calendarHandler;
    std::optional<std::vector<UpcomingMeetingRow>> calendarRows;
    std::uint64_t calendarAuthGeneration = 0, calendarTimeRevision = 0;
    bool calendarShowTime = true, calendarShowTitle = true;
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
        if (message == WM_TIMECHANGE || message == WM_SETTINGCHANGE || message == WM_DISPLAYCHANGE ||
            (message == WM_DPICHANGED && (!self->popupToken || !self->popupToken->preparing))) {
            self->invalidateMenu(); // presentation only, never cancel an admitted Join
        }
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
            self->invalidateMenu();
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
                try { self->showMenu({GET_X_LPARAM(wParam), GET_Y_LPARAM(wParam)}); }
                catch (...) {} // allocation/presentation failure must not cross WindowProc
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
    static COLORREF colorOf(const wchar_t* key, COLORREF fallback, bool dark) {
        for (const auto& entry : shellPaletteEntries()) {
            if (std::wcscmp(entry.key, key) != 0) continue;
            const auto value = shellPaletteColor(entry, dark);
            return RGB((value.rgb >> 16) & 0xFF, (value.rgb >> 8) & 0xFF, value.rgb & 0xFF);
        }
        return fallback;
    }

    static std::shared_ptr<MenuStyle> prepareMenuStyle(POINT point, HWND menuWindow, bool dark,
                                                     const std::shared_ptr<PopupToken>& token) {
        MONITORINFO monitor{}; monitor.cbSize = sizeof(monitor);
        if (!GetMonitorInfoW(MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST), &monitor)) return {};
        // As in RecordingNoticePresenter, associate the invisible window with
        // the popup's monitor before asking Windows for its font/DPI metrics.
        if (!SetWindowPos(menuWindow, nullptr, monitor.rcWork.left, monitor.rcWork.top, 1, 1,
                          SWP_NOACTIVATE | SWP_NOZORDER) || !token->current || !IsWindow(menuWindow)) return {};
        auto style = std::make_shared<MenuStyle>();
        const auto dpi = GetDpiForWindow(menuWindow);
        style->dpi = static_cast<int>(dpi ? dpi : 96);
        style->maxWidth = (std::min)(style->scale(640),
            static_cast<int>(monitor.rcWork.right - monitor.rcWork.left) - style->scale(32));
        if (style->maxWidth <= style->scale(64)) return {};
        NONCLIENTMETRICSW metrics{}; metrics.cbSize = sizeof(metrics);
        if (!SystemParametersInfoForDpi(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, 0,
                                        static_cast<UINT>(style->dpi))) return {};
        DWORD textScale = 100, bytes = sizeof(textScale);
        if (RegGetValueW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Accessibility", L"TextScaleFactor",
            RRF_RT_REG_DWORD, nullptr, &textScale, &bytes) != ERROR_SUCCESS) textScale = 100;
        textScale = std::clamp<DWORD>(textScale, 100, 225);
        metrics.lfMenuFont.lfHeight = -(std::max)(std::abs(static_cast<int>(metrics.lfMenuFont.lfHeight)),
            MulDiv(style->scale(14), static_cast<int>(textScale), 100));
        const auto font = CreateFontIndirectW(&metrics.lfMenuFont);
        if (!font) return {};
        style->font = std::shared_ptr<void>(font, [](void* value) { DeleteObject(static_cast<HFONT>(value)); });
        HIGHCONTRASTW contrast{}; contrast.cbSize = sizeof(contrast);
        if (!SystemParametersInfoW(SPI_GETHIGHCONTRAST, sizeof(contrast), &contrast, 0)) return {};
        const bool highContrast = (contrast.dwFlags & HCF_HIGHCONTRASTON) != 0;
        style->background = highContrast ? GetSysColor(COLOR_MENU) : colorOf(L"GrafPanelBrush", RGB(29, 31, 35), dark);
        style->text = highContrast ? GetSysColor(COLOR_MENUTEXT) : colorOf(L"GrafTextBrush", RGB(240, 241, 244), dark);
        style->muted = highContrast ? GetSysColor(COLOR_GRAYTEXT) : colorOf(L"GrafMutedTextBrush", RGB(173, 178, 188), dark);
        style->selected = highContrast ? GetSysColor(COLOR_HIGHLIGHT) : colorOf(L"GrafAccentSolidBrush", RGB(112, 86, 233), dark);
        style->selectedText = highContrast ? GetSysColor(COLOR_HIGHLIGHTTEXT) : RGB(255, 255, 255);
        style->line = highContrast ? GetSysColor(COLOR_MENUTEXT) : colorOf(L"GrafLineSoftBrush", RGB(70, 74, 84), dark);
        return style;
    }

    void addItem(HMENU menu, const std::wstring& text, UINT_PTR id, bool separator, bool disabled = false, bool submenu = false) {
        auto item = std::make_unique<MenuItem>();
        item->text = text;
        item->style = menuStyle;
        item->accessibility.dwMSAASignature = MSAA_MENU_SIG;
        item->accessibility.cchWText = static_cast<DWORD>(item->text.size());
        item->accessibility.pszWText = item->text.data();
        item->separator = separator;
        item->disabled = disabled;
        // Для MF_OWNERDRAW данные пункта передаются в параметре строки.
        const UINT flags = MF_OWNERDRAW | (separator ? MF_SEPARATOR : 0U) | (submenu ? MF_POPUP : 0U) |
            (disabled || separator ? MF_DISABLED | MF_GRAYED : MF_ENABLED);
        const auto data = item.get();
        menuItems.push_back(std::move(item)); // Allocate before transferring a submenu to its parent.
        if (!AppendMenuW(menu, flags, id, reinterpret_cast<LPCWSTR>(data))) {
            menuItems.pop_back();
            throw std::runtime_error("GRAF tray menu item unavailable");
        }
    }

    void measureItem(MEASUREITEMSTRUCT* measure) const {
        const auto* item = reinterpret_cast<const MenuItem*>(measure->itemData);
        if (item == nullptr || !item->style) return;
        const auto& style = *item->style;
        measure->itemHeight = static_cast<UINT>(item->separator ? style.scale(9) : style.scale(30));
        if (item->separator) {
            measure->itemWidth = static_cast<UINT>((std::min)(style.scale(220), style.maxWidth));
            return;
        }
        const auto dc = GetDC(window);
        if (dc == nullptr) {
            measure->itemWidth = static_cast<UINT>((std::min)(style.scale(260), style.maxWidth));
            return;
        }
        // Ширина по самой длинной строке плюс поля, как у системного меню.
        auto font = static_cast<HFONT>(style.font.get());
        const auto previous = SelectObject(dc, font);
        SIZE size{};
        GetTextExtentPoint32W(dc, item->text.c_str(), static_cast<int>(item->text.size()), &size);
        TEXTMETRICW textMetrics{};
        if (GetTextMetricsW(dc, &textMetrics))
            measure->itemHeight = static_cast<UINT>((std::max)(style.scale(30),
                static_cast<int>(textMetrics.tmHeight) + style.scale(12)));
        SelectObject(dc, previous);
        ReleaseDC(window, dc);
        measure->itemWidth = static_cast<UINT>((std::min)(style.maxWidth,
            (std::max)(style.scale(220), static_cast<int>(size.cx) + style.scale(64))));
    }

    void drawItem(const DRAWITEMSTRUCT* draw) const {
        const auto* item = reinterpret_cast<const MenuItem*>(draw->itemData);
        if (item == nullptr || !item->style) return;
        const auto& style = *item->style;
        const bool selected = (draw->itemState & ODS_SELECTED) != 0 && !item->disabled;
        if (item->separator) {
            const auto background = CreateSolidBrush(style.background);
            FillRect(draw->hDC, &draw->rcItem, background);
            DeleteObject(background);
            const auto line = CreateSolidBrush(style.line);
            RECT rule = draw->rcItem;
            rule.top += style.scale(4);
            rule.bottom = rule.top + 1;
            rule.left += style.scale(12);
            rule.right -= style.scale(12);
            FillRect(draw->hDC, &rule, line);
            DeleteObject(line);
            return;
        }
        const auto background = CreateSolidBrush(selected ? style.selected : style.background);
        FillRect(draw->hDC, &draw->rcItem, background);
        DeleteObject(background);
        SetBkMode(draw->hDC, TRANSPARENT);
        const COLORREF text = selected ? style.selectedText : item->disabled ? style.muted : style.text;
        SetTextColor(draw->hDC, text);
        auto font = static_cast<HFONT>(style.font.get());
        const auto previous = SelectObject(draw->hDC, font);
        RECT text_rect = draw->rcItem;
        text_rect.left += style.scale(16);
        text_rect.right -= style.scale(12);
        DrawTextW(draw->hDC, item->text.c_str(), static_cast<int>(item->text.size()), &text_rect,
                  DT_SINGLELINE | DT_VCENTER | DT_LEFT | DT_END_ELLIPSIS | DT_NOPREFIX);
        SelectObject(draw->hDC, previous);
    }

    void showMenu(POINT point) {
        if (popupToken && (popupToken->preparing || popupToken->tracking)) return;
        invalidateMenu(); // Reentry after tracking must revoke the previous, still-finishing selection.
        const auto menuWindow = window;
        const auto dark = isDark;
        const auto token = std::make_shared<PopupToken>();
        popupToken = token;
        struct PopupScope {
            std::shared_ptr<PopupToken> token;
            ~PopupScope() { token->preparing = false; token->tracking = false; }
        } popupScope{token};
        if (point.x == -1 && point.y == -1) {
            NOTIFYICONIDENTIFIER identifier{};
            identifier.cbSize = sizeof(identifier);
            identifier.hWnd = menuWindow;
            identifier.uID = kIconId;
            RECT bounds{};
            if (SUCCEEDED(Shell_NotifyIconGetRect(&identifier, &bounds))) {
                point = {bounds.left, bounds.bottom};
            } else {
                GetCursorPos(&point);
            }
        }
        if (!token->current || !IsWindow(menuWindow)) return;
        // This static preparation never accesses Impl across native calls.
        // WM_DPICHANGED during placement is expected: metrics are read afterwards.
        auto style = prepareMenuStyle(point, menuWindow, dark, token);
        if (!style || !token->current || !IsWindow(menuWindow)) return;
        menuStyle = std::move(style);
        menuItems.clear();
        struct MenuScope {
            HMENU menu = nullptr;
            HBRUSH background = nullptr;
            ~MenuScope() { if (menu) DestroyMenu(menu); if (background) DeleteObject(background); }
        } scope{CreatePopupMenu(), CreateSolidBrush(menuStyle->background)};
        const auto menu = scope.menu;
        if (!scope.background) return;
        if (!menu) return;
        const auto rows = calendarRows;
        const auto calendar = calendarHandler;
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
        if (rows) {
            addItem(menu, L"", 0, true);
            addItem(menu, L"Ближайшие встречи", 0, false, true);
            for (std::size_t index = 0; index < rows->size(); ++index) {
                const auto& row = (*rows)[index];
                addItem(menu, row.label, kCalendarCommand + index, false, !row.enabled || !calendar || !actions.settings);
            }
        }
        addItem(menu, L"", 0, true);
        addItem(menu, L"Настройки", kSettingsCommand, false, !actions.settings || !settingsHandler);
        addItem(menu, L"Проверить обновления…", kUpdateCommand, false, !actions.settings || !updateHandler);
        addItem(menu, L"Перейти к уведомлению", kFocusNotificationCommand, false,
                !actions.settings || !notificationVisible || !focusNotificationHandler);
        MenuScope historyScope{CreatePopupMenu(), nullptr};
        const auto historyMenu = historyScope.menu;
        if (historyMenu) {
            if (notificationHistory.empty()) addItem(historyMenu, L"Уведомлений пока нет", 0, false, true);
            else for (const auto& entry : notificationHistory) addItem(historyMenu, entry, 0, false, true);
            addItem(menu, L"История уведомлений", reinterpret_cast<UINT_PTR>(historyMenu), false, false, true);
            historyScope.menu = nullptr; // the parent menu now owns this submenu
        }
        addItem(menu, L"Закрыть GRAF", kQuitCommand, false);
        MENUINFO info{};
        info.cbSize = sizeof(info);
        info.fMask = MIM_BACKGROUND | MIM_APPLYTOSUBMENUS;
        info.hbrBack = scope.background;
        SetMenuInfo(menu, &info);
        // The nested loop can process Quit and destroy this Impl. Item data
        // and the brush must outlive that loop without accessing this afterwards.
        auto menuLifetime = std::move(menuItems);
        token->preparing = false;
        token->tracking = true;
        SetForegroundWindow(menuWindow);
        const auto command = token->current && IsWindow(menuWindow)
            ? TrackPopupMenuEx(menu, TPM_RETURNCMD | TPM_NONOTIFY | TPM_RIGHTBUTTON,
                              point.x, point.y, menuWindow, nullptr) : 0U;
        token->tracking = false;
        // The nested menu loop may close the owner. Use only local handles from here.
        DestroyMenu(menu);
        scope.menu = nullptr;
        menuLifetime.clear();
        DeleteObject(info.hbrBack);
        scope.background = nullptr;
        if (token->current && IsWindow(menuWindow)) {
            PostMessageW(menuWindow, WM_NULL, 0, 0);
            Shell_NotifyIconW(NIM_SETFOCUS, &data);
            if (!token->current || !IsWindow(menuWindow)) return;
            if (command >= kCalendarCommand && rows && command - kCalendarCommand < rows->size()) {
                const auto& row = (*rows)[command - kCalendarCommand];
                if (row.enabled && calendar) calendar(row); // no access to Impl, including after the callback
                return;
            }
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

void WindowsTray::setState(const RecordingIndicatorSnapshot& snapshot, bool recordingReady, bool exiting, bool privacyPending) {
    if (!impl_) return;
    const auto actions = menuAvailability(snapshot, recordingReady, exiting, privacyPending);
    const auto& old = impl_->snapshot;
    if (old.visible != snapshot.visible || old.stopAvailable != snapshot.stopAvailable || old.state != snapshot.state ||
        old.reason != snapshot.reason || old.accessibleName != snapshot.accessibleName || old.statusText != snapshot.statusText ||
        impl_->actions.start != actions.start || impl_->actions.pauseResume != actions.pauseResume ||
        impl_->actions.stop != actions.stop || impl_->actions.settings != actions.settings) impl_->invalidateMenu();
    impl_->snapshot = snapshot;
    impl_->actions = actions;
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
    if (impl_->isDark != isDark) impl_->invalidateMenu();
    impl_->isDark = isDark;
}

void WindowsTray::setUpdateHandler(Handler handler) {
    if (!impl_) return;
    impl_->invalidateMenu();
    impl_->updateHandler = std::move(handler);
}

void WindowsTray::setNotificationState(bool visible, std::vector<std::wstring> history) {
    if (!impl_) return;
    if (history.size() > 50) history.resize(50);
    if (impl_->notificationVisible != visible || impl_->notificationHistory != history) impl_->invalidateMenu();
    impl_->notificationVisible = visible;
    impl_->notificationHistory = std::move(history);
}

void WindowsTray::setCalendarHandler(CalendarHandler handler) {
    if (!impl_) return;
    impl_->invalidateMenu();
    impl_->calendarHandler = std::move(handler);
}

void WindowsTray::setCalendarState(std::optional<std::vector<UpcomingMeetingRow>> rows,
    std::uint64_t authGeneration, std::uint64_t timeRevision, bool showTime, bool showTitle) {
    if (!impl_) return;
    if (rows && rows->size() > 12) rows->resize(12);
    if (impl_->calendarRows != rows || impl_->calendarAuthGeneration != authGeneration ||
        impl_->calendarTimeRevision != timeRevision || impl_->calendarShowTime != showTime ||
        impl_->calendarShowTitle != showTitle) impl_->invalidateMenu();
    impl_->calendarRows = std::move(rows);
    impl_->calendarAuthGeneration = authGeneration;
    impl_->calendarTimeRevision = timeRevision;
    impl_->calendarShowTime = showTime;
    impl_->calendarShowTitle = showTitle;
}

} // namespace graf::windows

#else

namespace graf::windows {

struct WindowsTray::Impl {};

WindowsTray::WindowsTray(std::uintptr_t, Handler, Handler, Handler, Handler, Handler, Handler, Handler, Handler)
    : impl_(std::make_unique<Impl>()) {}

WindowsTray::~WindowsTray() = default;

void WindowsTray::setState(const RecordingIndicatorSnapshot&, bool, bool, bool) {}

bool WindowsTray::available() noexcept { return false; }

InteractionPermit WindowsTray::interactionPermit() noexcept { return {}; }

void WindowsTray::setTheme(bool) {}
void WindowsTray::setUpdateHandler(Handler) {}

void WindowsTray::setNotificationState(bool, std::vector<std::wstring>) {}
void WindowsTray::setCalendarHandler(CalendarHandler) {}
void WindowsTray::setCalendarState(std::optional<std::vector<UpcomingMeetingRow>>, std::uint64_t,
                                   std::uint64_t, bool, bool) {}

} // namespace graf::windows

#endif
