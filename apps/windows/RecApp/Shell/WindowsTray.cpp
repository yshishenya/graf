#include "WindowsTray.h"

#ifdef _WIN32

#include <windows.h>
#include <shellapi.h>

#include <string>

namespace graf::windows {

struct WindowsTray::Impl {
    static constexpr UINT kTrayMessage = WM_APP + 200;
    static constexpr UINT kOpenCommand = 1;
    static constexpr UINT kStopCommand = 2;
    static constexpr UINT kQuitCommand = 3;

    HWND owner = nullptr;
    HWND window = nullptr;
    HICON icon = nullptr;
    Handler openHandler;
    Handler stopHandler;
    Handler quitHandler;
    bool recording = false;

    static LRESULT CALLBACK windowProc(HWND window, UINT message, WPARAM wParam, LPARAM lParam) {
        auto* self = reinterpret_cast<Impl*>(GetWindowLongPtrW(window, GWLP_USERDATA));
        if (message == WM_NCCREATE) {
            const auto* create = reinterpret_cast<const CREATESTRUCTW*>(lParam);
            self = static_cast<Impl*>(create->lpCreateParams);
            SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
            self->window = window;
        }
        if (self == nullptr) return DefWindowProcW(window, message, wParam, lParam);
        if (message == kTrayMessage) {
            if (lParam == WM_LBUTTONUP && self->openHandler) self->openHandler();
            if (lParam == WM_RBUTTONUP) self->showMenu();
            return 0;
        }
        if (message == WM_COMMAND) {
            switch (LOWORD(wParam)) {
            case kOpenCommand:
                if (self->openHandler) self->openHandler();
                break;
            case kStopCommand:
                if (self->recording && self->stopHandler) self->stopHandler();
                break;
            case kQuitCommand:
                if (self->quitHandler) self->quitHandler();
                break;
            default:
                break;
            }
            return 0;
        }
        if (message == WM_DESTROY) {
            self->removeIcon();
            return 0;
        }
        return DefWindowProcW(window, message, wParam, lParam);
    }

    void showMenu() {
        POINT point{};
        GetCursorPos(&point);
        const auto menu = CreatePopupMenu();
        if (!menu) return;
        AppendMenuW(menu, MF_STRING, kOpenCommand, L"Открыть GRAF");
        AppendMenuW(menu, recording ? MF_STRING : MF_STRING | MF_GRAYED, kStopCommand, L"Остановить запись");
        AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
        AppendMenuW(menu, MF_STRING, kQuitCommand, L"Выйти из GRAF");
        SetForegroundWindow(window);
        TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_BOTTOMALIGN, point.x, point.y, 0, window, nullptr);
        DestroyMenu(menu);
    }

    void removeIcon() noexcept {
        if (!window) return;
        NOTIFYICONDATAW data{};
        data.cbSize = sizeof(data);
        data.hWnd = window;
        data.uID = 200;
        Shell_NotifyIconW(NIM_DELETE, &data);
    }

    void updateIcon() noexcept {
        if (!window) return;
        NOTIFYICONDATAW data{};
        data.cbSize = sizeof(data);
        data.hWnd = window;
        data.uID = 200;
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP;
        data.uCallbackMessage = kTrayMessage;
        data.hIcon = icon;
        wcsncpy_s(data.szTip, recording ? L"GRAF — идёт запись" : L"GRAF", _TRUNCATE);
        Shell_NotifyIconW(NIM_MODIFY, &data);
    }

    void addIcon() noexcept {
        if (!window) return;
        NOTIFYICONDATAW data{};
        data.cbSize = sizeof(data);
        data.hWnd = window;
        data.uID = 200;
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP;
        data.uCallbackMessage = kTrayMessage;
        data.hIcon = icon;
        wcsncpy_s(data.szTip, L"GRAF", _TRUNCATE);
        Shell_NotifyIconW(NIM_ADD, &data);
    }
};

WindowsTray::WindowsTray(std::uintptr_t ownerWindow, Handler openHandler, Handler stopHandler, Handler quitHandler)
    : impl_(std::make_unique<Impl>()) {
    impl_->owner = reinterpret_cast<HWND>(ownerWindow);
    impl_->openHandler = std::move(openHandler);
    impl_->stopHandler = std::move(stopHandler);
    impl_->quitHandler = std::move(quitHandler);
    const auto instance = GetModuleHandleW(nullptr);
    static const wchar_t className[] = L"GRAF.WindowsTray";
    WNDCLASSW windowClass{};
    windowClass.lpfnWndProc = &Impl::windowProc;
    windowClass.hInstance = instance;
    windowClass.lpszClassName = className;
    windowClass.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    RegisterClassW(&windowClass);
    impl_->window = CreateWindowExW(0, className, L"GRAF", 0, 0, 0, 0, 0, HWND_MESSAGE, nullptr, instance, impl_.get());
    impl_->icon = LoadIconW(nullptr, IDI_APPLICATION);
    impl_->addIcon();
}

WindowsTray::~WindowsTray() {
    if (!impl_) return;
    if (impl_->window) DestroyWindow(impl_->window);
}

void WindowsTray::setRecording(bool active) noexcept {
    if (!impl_) return;
    impl_->recording = active;
    impl_->updateIcon();
}

} // namespace graf::windows

#else

namespace graf::windows {

struct WindowsTray::Impl {};

WindowsTray::WindowsTray(std::uintptr_t, Handler, Handler, Handler)
    : impl_(std::make_unique<Impl>()) {}

WindowsTray::~WindowsTray() = default;

void WindowsTray::setRecording(bool) noexcept {}

} // namespace graf::windows

#endif
