#include "WindowsTray.h"

#ifdef _WIN32

#include "ShellPalette.h"

#include <windows.h>
#include <windowsx.h>
#include <shellapi.h>

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

    struct MenuItem {
        std::wstring text;
        bool separator = false;
        bool disabled = false;
    };

    HWND window = nullptr;
    HICON icon = nullptr;
    UINT taskbarCreated = 0;
    // Тема приходит из оболочки: меню рисуется её кистями, а не системными.
    bool isDark = true;
    std::vector<std::unique_ptr<MenuItem>> menuItems;
    Handler openHandler;
    Handler stopHandler;
    Handler quitHandler;
    Handler pauseResumeHandler;
    RecordingIndicatorSnapshot snapshot;

    static LRESULT CALLBACK windowProc(HWND window, UINT message, WPARAM wParam, LPARAM lParam) {
        auto* self = reinterpret_cast<Impl*>(GetWindowLongPtrW(window, GWLP_USERDATA));
        if (message == WM_NCCREATE) {
            const auto* create = reinterpret_cast<const CREATESTRUCTW*>(lParam);
            self = static_cast<Impl*>(create->lpCreateParams);
            SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
            self->window = window;
        }
        if (self == nullptr) return DefWindowProcW(window, message, wParam, lParam);
        if (message == self->taskbarCreated) {
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
                if (self->snapshot.stopAvailable) handler = self->stopHandler;
                break;
            case kPauseResumeCommand:
                if (self->snapshot.state == SessionState::recording || self->snapshot.state == SessionState::paused) {
                    handler = self->pauseResumeHandler;
                }
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

    void addItem(HMENU menu, const std::wstring& text, UINT id, bool separator, bool disabled = false) {
        auto item = std::make_unique<MenuItem>();
        item->text = text;
        item->separator = separator;
        item->disabled = disabled;
        // Для MF_OWNERDRAW данные пункта передаются в параметре строки.
        AppendMenuW(menu, MF_OWNERDRAW, id, reinterpret_cast<LPCWSTR>(item.get()));
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
        if (pauseResumeHandler && (snapshot.state == SessionState::recording || snapshot.state == SessionState::paused)) {
            addItem(menu, snapshot.state == SessionState::paused ? L"Продолжить запись микрофона" : L"Пауза микрофона",
                    kPauseResumeCommand, false);
        }
        addItem(menu, L"Остановить запись", kStopCommand, false, !snapshot.stopAvailable);
        addItem(menu, L"", 0, true);
        addItem(menu, L"Закрыть GRAF", kQuitCommand, false);
        MENUINFO info{};
        info.cbSize = sizeof(info);
        info.fMask = MIM_BACKGROUND | MIM_APPLYTOSUBMENUS;
        info.hbrBack = backgroundBrush();
        SetMenuInfo(menu, &info);
        const auto menuWindow = window;
        SetForegroundWindow(menuWindow);
        const auto command = TrackPopupMenuEx(menu, TPM_RETURNCMD | TPM_NONOTIFY | TPM_RIGHTBUTTON,
                                             point.x, point.y, menuWindow, nullptr);
        // The nested menu loop may close the owner. Use only local handles from here.
        DestroyMenu(menu);
        menuItems.clear();
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
        if (!window) return;
        auto data = iconData();
        Shell_NotifyIconW(NIM_DELETE, &data);
    }

    void updateIcon() noexcept {
        if (!window) return;
        auto data = iconData();
        if (!Shell_NotifyIconW(NIM_MODIFY, &data)) (void)addIcon();
    }

    bool addIcon() noexcept {
        if (!window || !icon) return false;
        auto data = iconData();
        if (!Shell_NotifyIconW(NIM_ADD, &data)) return false;
        data.uVersion = NOTIFYICON_VERSION_4;
        if (Shell_NotifyIconW(NIM_SETVERSION, &data)) return true;
        removeIcon();
        return false;
    }
};

WindowsTray::WindowsTray(std::uintptr_t ownerWindow, Handler openHandler, Handler stopHandler,
                         Handler quitHandler, Handler pauseResumeHandler)
    : impl_(std::make_unique<Impl>()) {
    impl_->openHandler = std::move(openHandler);
    impl_->stopHandler = std::move(stopHandler);
    impl_->quitHandler = std::move(quitHandler);
    impl_->pauseResumeHandler = std::move(pauseResumeHandler);
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
    if (!impl_->addIcon()) {
        DestroyWindow(impl_->window);
        throw std::runtime_error("GRAF tray icon installation failed");
    }
}

WindowsTray::~WindowsTray() {
    if (!impl_) return;
    if (impl_->window) DestroyWindow(impl_->window);
}

void WindowsTray::setState(const RecordingIndicatorSnapshot& snapshot) {
    if (!impl_) return;
    impl_->snapshot = snapshot;
    impl_->updateIcon();
}

void WindowsTray::setTheme(bool isDark) {
    if (!impl_) return;
    impl_->isDark = isDark;
}

} // namespace graf::windows

#else

namespace graf::windows {

struct WindowsTray::Impl {};

WindowsTray::WindowsTray(std::uintptr_t, Handler, Handler, Handler, Handler)
    : impl_(std::make_unique<Impl>()) {}

WindowsTray::~WindowsTray() = default;

void WindowsTray::setState(const RecordingIndicatorSnapshot&) {}

void WindowsTray::setTheme(bool) {}

} // namespace graf::windows

#endif
