#include "RecordingNoticePresenter.h"

#include <utility>

#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {

#ifdef _WIN32
namespace {

constexpr wchar_t kNoticeWindowClass[] = L"GrafRecordingNoticeWindow";
constexpr int kNoticeBaseWidth = 380;
constexpr int kNoticeBaseHeight = 64;
constexpr int kNoticeMargin = 16;

UINT windowDpi(HWND window) {
    const auto user32 = GetModuleHandleW(L"user32.dll");
    if (user32 != nullptr) {
        using GetDpiForWindowFn = UINT(WINAPI*)(HWND);
        const auto getDpiForWindow =
            reinterpret_cast<GetDpiForWindowFn>(GetProcAddress(user32, "GetDpiForWindow"));
        if (getDpiForWindow != nullptr) {
            const auto dpi = getDpiForWindow(window);
            if (dpi != 0) return dpi;
        }
    }
    return 96;
}

int scaled(int value, UINT dpi) {
    return MulDiv(value, static_cast<int>(dpi), 96);
}

bool ensureWindowClass() {
    static bool registered = false;
    if (registered) return true;
    WNDCLASSEXW definition{};
    definition.cbSize = sizeof(definition);
    definition.lpfnWndProc = DefWindowProcW;
    definition.hInstance = GetModuleHandleW(nullptr);
    definition.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    definition.lpszClassName = kNoticeWindowClass;
    // A notice must be able to repaint itself after the owner redraws; window
    // background comes from system colours so High Contrast stays truthful.
    definition.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1);
    if (RegisterClassExW(&definition) == 0 && GetLastError() != ERROR_CLASS_ALREADY_EXISTS) return false;
    registered = true;
    return true;
}

} // namespace
#endif

RecordingNoticePresenter::~RecordingNoticePresenter() {
    dismiss();
}

void RecordingNoticePresenter::showShortRecordingDiscarded(std::chrono::steady_clock::time_point now) {
    // A repeat replaces the previous notice instead of stacking a second one.
    dismiss();
    visible_ = true;
    shownAt_ = now;
#ifdef _WIN32
    createWindow();
#endif
}

void RecordingNoticePresenter::tick(std::chrono::steady_clock::time_point now) {
    if (!visible_) return;
    if (expired(now)) dismiss();
}

void RecordingNoticePresenter::dismiss() {
    visible_ = false;
#ifdef _WIN32
    destroyWindow();
#endif
}

#ifdef _WIN32

void RecordingNoticePresenter::createWindow() {
    if (!ensureWindowClass()) return;
    const auto module = GetModuleHandleW(nullptr);
    const auto instance = reinterpret_cast<HINSTANCE>(module);
    auto* ownerWindow = static_cast<HWND>(owner_);
    // WS_EX_NOACTIVATE plus SW_SHOWNOACTIVATE keeps the user's meeting window in
    // front. WS_EX_TRANSPARENT means the notice never intercepts input.
    const auto window = CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT,
        kNoticeWindowClass, message().data(), WS_POPUP,
        0, 0, kNoticeBaseWidth, kNoticeBaseHeight,
        ownerWindow, nullptr, instance, nullptr);
    if (window == nullptr) return;
    window_ = window;

    const auto dpi = windowDpi(window);
    const auto width = scaled(kNoticeBaseWidth, dpi);
    const auto height = scaled(kNoticeBaseHeight, dpi);
    const auto margin = scaled(kNoticeMargin, dpi);
    const auto label = CreateWindowExW(
        0, L"STATIC", message().data(),
        WS_CHILD | WS_VISIBLE | SS_CENTER | SS_CENTERIMAGE | SS_LEFTNOWORDWRAP,
        margin, margin, width - 2 * margin, height - 2 * margin,
        window, nullptr, instance, nullptr);
    if (label == nullptr) {
        DestroyWindow(window);
        window_ = nullptr;
        return;
    }
    label_ = label;
    // Use the operating-system message font so text follows the user's size,
    // font and accessibility preferences instead of a hardcoded face.
    NONCLIENTMETRICSW metrics{};
    metrics.cbSize = sizeof(metrics);
    if (SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, 0)) {
        const auto font = CreateFontIndirectW(&metrics.lfMessageFont);
        if (font != nullptr) SendMessageW(static_cast<HWND>(label), WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
    }

    // Place the notice on the monitor that owns the cursor, inside the work
    // area, so it cannot be hidden behind the taskbar.
    POINT cursor{};
    GetCursorPos(&cursor);
    const auto monitor = MonitorFromPoint(cursor, MONITOR_DEFAULTTONEAREST);
    MONITORINFO monitorInfo{};
    monitorInfo.cbSize = sizeof(monitorInfo);
    RECT workArea{};
    if (monitor != nullptr && GetMonitorInfoW(monitor, &monitorInfo)) {
        workArea = monitorInfo.rcWork;
    } else {
        SystemParametersInfoW(SPI_GETWORKAREA, 0, &workArea, 0);
    }
    const auto x = workArea.right - width - margin;
    const auto y = workArea.bottom - height - margin;
    SetWindowPos(window, HWND_TOPMOST, x, y, width, height, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    ShowWindow(window, SW_SHOWNOACTIVATE);
    // Ask assistive technology to read the notice without focusing it.
    NotifyWinEvent(EVENT_SYSTEM_ALERT, window, OBJID_CLIENT, CHILDID_SELF);
}

void RecordingNoticePresenter::destroyWindow() {
    if (window_ != nullptr) {
        DestroyWindow(static_cast<HWND>(window_));
        window_ = nullptr;
    }
    label_ = nullptr;
}

#endif

} // namespace graf::windows
