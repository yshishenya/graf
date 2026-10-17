#include "RecordingNoticePresenter.h"
#include <algorithm>
#include <utility>

#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {
RecordingNoticePresenter::~RecordingNoticePresenter() { dismiss(); }

bool RecordingNoticePresenter::present(NoticeContent content, Clock::time_point now, Clock::time_point deadline,
    std::function<void(NoticeAction)> onAction, std::function<void()> onClose) {
    if (deadline <= now) return false;
    tick(now);
    if (automaticPromptActive() && static_cast<int>(content.kind) <= static_cast<int>(NoticeKind::shortRecording)) return false;
    if (visible_ && !(content.kind == content_.kind && content.id == content_.id) &&
        static_cast<int>(content.kind) <= static_cast<int>(content_.kind)) return false;
    const bool unchanged = visible_ && content.kind == content_.kind && content.id == content_.id &&
        content.title == content_.title && content.body == content_.body && content.buttons.size() == content_.buttons.size();
    if (!unchanged) dismiss();
    content_ = std::move(content); deadline_ = deadline;
    onAction_ = std::move(onAction); onClose_ = std::move(onClose);
    if (unchanged) return true;
#ifdef _WIN32
    visible_ = createWindow();
#else
    visible_ = true; // portable state checks are not evidence of a Windows window
#endif
    if (visible_ && automaticPromptActive()) {
        const auto generation = *automaticPromptGeneration_;
        // Keep the callback alive if synchronous Closed clears the stored one.
        auto replaced = onAutomaticPromptReplaced_;
        if (!replaced || !replaced()) { dismiss(); return false; }
        releaseAutomaticPrompt(generation);
    }
    return visible_;
}
bool RecordingNoticePresenter::acquireAutomaticPrompt(std::uint64_t generation, Clock::time_point now,
    std::function<bool()> onReplaced) {
    if (!generation || !onReplaced) return false;
    tick(now);
    if (automaticPromptActive()) return *automaticPromptGeneration_ == generation;
    if (visible_ && static_cast<int>(content_.kind) >= static_cast<int>(NoticeKind::shortRecording)) return false;
    dismiss();
    automaticPromptGeneration_ = generation;
    onAutomaticPromptReplaced_ = std::move(onReplaced);
    return true;
}
void RecordingNoticePresenter::releaseAutomaticPrompt(std::uint64_t generation) {
    if (automaticPromptGeneration_ != generation) return;
    automaticPromptGeneration_.reset(); onAutomaticPromptReplaced_ = {};
}
void RecordingNoticePresenter::showShortRecordingDiscarded(Clock::time_point now) {
    (void)present({NoticeKind::shortRecording, "short-recording", L"Запись слишком короткая", std::wstring(message()), {}},
                  now, now + std::chrono::milliseconds(durationMilliseconds));
}
void RecordingNoticePresenter::tick(Clock::time_point now) { if (expired(now)) dismiss(); }
void RecordingNoticePresenter::dismiss() {
    visible_ = false; onClose_ = {}; onAction_ = {};
#ifdef _WIN32
    destroyWindow();
#endif
}
void RecordingNoticePresenter::close() {
    auto callback = onClose_; dismiss(); if (callback) callback();
}
void RecordingNoticePresenter::invoke(NoticeAction action) {
    if (!visible_ || expired(Clock::now())) return;
    const bool offered = std::any_of(content_.buttons.begin(), content_.buttons.end(), [action](const auto& b) { return b.action == action; });
    auto callback = onAction_; if (offered && callback) callback(action);
}
void RecordingNoticePresenter::focus() {
#ifdef _WIN32
    if (!window_ || !visible_) return;
    auto window = static_cast<HWND>(window_);
    SetForegroundWindow(window); SetFocus(GetNextDlgTabItem(window, nullptr, FALSE));
#endif
}

#ifdef _WIN32
namespace {
constexpr wchar_t kClass[] = L"GrafNotificationCard";
constexpr wchar_t kButtonProc[] = L"GrafNotificationButtonProc";

LRESULT CALLBACK buttonProc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    auto old = reinterpret_cast<WNDPROC>(GetPropW(window, kButtonProc));
    if (message == WM_KEYDOWN && (wparam == VK_TAB || wparam == VK_ESCAPE)) {
        if (wparam == VK_ESCAPE) SendMessageW(GetParent(window), WM_CLOSE, 0, 0);
        else SetFocus(GetNextDlgTabItem(GetParent(window), window, GetKeyState(VK_SHIFT) < 0));
        return 0;
    }
    return CallWindowProcW(old, window, message, wparam, lparam);
}
LRESULT CALLBACK cardProc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    auto* presenter = reinterpret_cast<RecordingNoticePresenter*>(GetWindowLongPtrW(window, GWLP_USERDATA));
    if (message == WM_NCCREATE) {
        presenter = static_cast<RecordingNoticePresenter*>(reinterpret_cast<CREATESTRUCTW*>(lparam)->lpCreateParams);
        SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(presenter));
    }
    if (message == WM_MOUSEACTIVATE) return MA_NOACTIVATE;
    if (presenter && message == WM_CLOSE) { presenter->close(); return 0; }
    if (presenter && message == WM_COMMAND && HIWORD(wparam) == BN_CLICKED) {
        const auto id = LOWORD(wparam);
        if (id == 100) presenter->close();
        else if (id >= 101 && id <= 103) presenter->invoke(static_cast<NoticeAction>(id - 101));
        return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}
}

bool RecordingNoticePresenter::createWindow() {
    WNDCLASSEXW cls{}; cls.cbSize = sizeof(cls); cls.lpfnWndProc = cardProc;
    cls.hInstance = GetModuleHandleW(nullptr); cls.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    cls.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1); cls.lpszClassName = kClass;
    if (!RegisterClassExW(&cls) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS) return false;
    POINT cursor{}; GetCursorPos(&cursor);
    MONITORINFO monitor{}; monitor.cbSize = sizeof(monitor);
    if (!GetMonitorInfoW(MonitorFromPoint(cursor, MONITOR_DEFAULTTONEAREST), &monitor)) return false;
    auto window = CreateWindowExW(WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_CONTROLPARENT,
        kClass, content_.title.c_str(), WS_POPUP | WS_BORDER, monitor.rcWork.right - 1, monitor.rcWork.top,
        1, 1, nullptr, nullptr, cls.hInstance, this);
    if (!window) return false;
    window_ = window;
    const UINT dpi = GetDpiForWindow(window);
    const auto scale = [dpi](int value) { return MulDiv(value, static_cast<int>(dpi ? dpi : 96), 96); };
    const int margin = scale(16);
    const int width = std::min(scale(448), static_cast<int>(monitor.rcWork.right - monitor.rcWork.left) - 2 * margin);
    const int buttonHeight = scale(40), textHeight = scale(72);
    const int height = margin * 2 + textHeight + static_cast<int>(content_.buttons.size()) * (buttonHeight + scale(8));
    NONCLIENTMETRICSW metrics{}; metrics.cbSize = sizeof(metrics);
    if (SystemParametersInfoForDpi(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, 0, dpi))
        font_ = CreateFontIndirectW(&metrics.lfMessageFont);
    const auto control = [&](const wchar_t* type, const std::wstring& text, DWORD style, int x, int y, int w, int h, int id) {
        auto child = CreateWindowExW(0, type, text.c_str(), WS_CHILD | WS_VISIBLE | style, x, y, w, h, window,
            reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), cls.hInstance, nullptr);
        if (child && font_) SendMessageW(child, WM_SETFONT, reinterpret_cast<WPARAM>(font_), TRUE);
        if (child && (style & WS_TABSTOP)) {
            auto old = GetWindowLongPtrW(child, GWLP_WNDPROC);
            if (!SetPropW(child, kButtonProc, reinterpret_cast<HANDLE>(old))) { DestroyWindow(child); return static_cast<HWND>(nullptr); }
            SetWindowLongPtrW(child, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(buttonProc));
        }
        return child;
    };
    if (!control(L"STATIC", content_.title + L"\r\n" + content_.body, SS_LEFT | SS_ENDELLIPSIS, margin, margin,
                 width - 2 * margin - scale(100), textHeight, 0) ||
        !control(L"BUTTON", L"Закрыть", WS_TABSTOP | BS_PUSHBUTTON, width - margin - scale(96), margin, scale(96), buttonHeight, 100)) {
        destroyWindow(); return false;
    }
    int y = margin + textHeight;
    for (const auto& button : content_.buttons) {
        if (!control(L"BUTTON", button.title, WS_TABSTOP | BS_PUSHBUTTON, margin, y, width - 2 * margin, buttonHeight,
                     101 + static_cast<int>(button.action))) { destroyWindow(); return false; }
        y += buttonHeight + scale(8);
    }
    SetWindowPos(window, HWND_TOPMOST, monitor.rcWork.right - width - margin, monitor.rcWork.top + scale(39),
                 width, height, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    ShowWindow(window, SW_SHOWNOACTIVATE);
    NotifyWinEvent(EVENT_SYSTEM_ALERT, window, OBJID_CLIENT, CHILDID_SELF);
    return IsWindowVisible(window) != FALSE;
}
void RecordingNoticePresenter::destroyWindow() {
    if (window_) DestroyWindow(static_cast<HWND>(window_));
    window_ = nullptr;
    if (font_) DeleteObject(static_cast<HFONT>(font_));
    font_ = nullptr;
}
#endif
} // namespace graf::windows
