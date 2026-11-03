#include "RecordingNoticePresenter.h"
#include <algorithm>
#include <cstdlib>
#include <utility>

#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {
RecordingNoticePresenter::~RecordingNoticePresenter() { dismiss(); }

namespace {
std::size_t identity(const NoticeContent& content) { return std::hash<std::string>{}(content.id); }
bool significant(NoticeKind kind) { return kind == NoticeKind::shortRecording || kind == NoticeKind::problem; }
}

void RecordingNoticePresenter::recordHistory(const NoticeContent& content, Clock::time_point until) {
    const auto key = identity(content);
    if (std::any_of(seen_.begin(), seen_.end(), [&](const auto& entry) { return entry.identity == key && entry.kind == content.kind; })) return;
    bool recorded = false, consumed = false;
    for (std::size_t i = 0; i < history_.size(); ++i)
        if (history_[i].kind == content.kind && historyIdentities_[i] && historyIdentities_[i]->identity == key) {
            recorded = true;
            consumed = historyIdentities_[i]->consumed;
        }
    if (significant(content.kind) && !recorded) {
        history_.insert(history_.begin(), {++historySequence_, std::chrono::system_clock::now(), content.kind});
        historyIdentities_.insert(historyIdentities_.begin(), HistoryIdentity{key, false});
        if (history_.size() > 50) { history_.pop_back(); historyIdentities_.pop_back(); }
    }
    // Bounded deduplication; if flooded, refuse new presentation until expiry.
    if (seen_.size() >= 256) return;
    seen_.push_back({key, content.kind, until, consumed});
}

void RecordingNoticePresenter::recordProblemHistory(const std::string& id, Clock::time_point until) {
    const auto now = Clock::now();
    if (id.empty() || id.size() > 1024 || until <= now) return;
    until = std::min(until, now + std::chrono::seconds(300));
    recordHistory({NoticeKind::problem, id, L"", L"", {}}, until);
    const auto key = std::hash<std::string>{}(id);
    for (auto& entry : seen_)
        if (entry.kind == NoticeKind::problem && entry.identity == key && !entry.shown)
            entry.until = std::max(entry.until, until);
}

void RecordingNoticePresenter::markConsumed(const NoticeContent& content) {
    const auto key = identity(content);
    for (auto& entry : seen_)
        if (entry.identity == key && entry.kind == content.kind) entry.shown = true;
    for (std::size_t i = 0; i < history_.size(); ++i)
        if (history_[i].kind == content.kind && historyIdentities_[i] && historyIdentities_[i]->identity == key)
            historyIdentities_[i]->consumed = true;
}

InteractionPermit RecordingNoticePresenter::readInteractionPermit() const noexcept {
    try {
        if (interactionPermitProvider) return interactionPermitProvider();
    } catch (...) { return {}; }
#ifdef _WIN32
    return {};
#else
    return {true, 1}; // deterministic portable seam, never native visibility evidence
#endif
}

bool RecordingNoticePresenter::requireInteraction() {
    const auto token = generation_;
    const auto permit = readInteractionPermit();
    if (token != generation_) return false;
    if (permit.allowed && permit.epoch != 0 && permit.epoch == interactionEpoch_) return true;
    invalidatePresentation();
    return false;
}

std::wstring_view RecordingNoticePresenter::historyMessage(NoticeKind kind) noexcept {
    if (kind == NoticeKind::shortRecording) return message();
    if (kind == NoticeKind::problem) return L"Возникла проблема с записью. Проверьте её состояние в GRAF.";
    return {};
}

bool RecordingNoticePresenter::present(NoticeContent content, Clock::time_point now, Clock::time_point deadline,
    std::function<void(NoticeAction)> onAction, std::function<void()> onClose, NoticePresentationHooks hooks) {
    if (preparing_) return false; // a claim cannot overwrite an owned, still-hidden HWND
    if (deadline <= now || content.id.empty() || content.buttons.size() > 3 || content.id.size() > 1024 ||
        content.title.size() > 4096 || content.body.size() > 4096 || content.checkboxTitle.size() > 1024 ||
        static_cast<int>(content.kind) < 0 || static_cast<int>(content.kind) > 4) return false;
    for (std::size_t i = 0; i < content.buttons.size(); ++i) {
        const auto& button = content.buttons[i];
        if (button.title.empty() || button.title.size() > 1024 || static_cast<int>(button.action) < 0 || static_cast<int>(button.action) > 4) return false;
        for (std::size_t j = 0; j < i; ++j) if (content.buttons[j].action == button.action) return false;
    }
    tick(now);
    if (content.kind == NoticeKind::preview && occupied()) return false;
    if (content.kind == NoticeKind::shortRecording) {
        content.title.clear(); content.body = message(); content.buttons.clear(); content.checkboxTitle.clear();
    }
    std::stable_sort(content.buttons.begin(), content.buttons.end(), [](const auto& a, const auto& b) {
        const auto primary = [](NoticeAction action) { return action == NoticeAction::record || action == NoticeAction::joinAndRecord || action == NoticeAction::openRecording; };
        return primary(a.action) < primary(b.action);
    });
    const bool same = visible_ && content.kind == content_.kind && content.id == content_.id;
    if (same) {
        // Controls and callbacks update; the original deadline/generation/focus do not.
        content_ = std::move(content);
        actionPending_ = false;
        if (content_.kind == NoticeKind::meeting) deadline_ = std::min(deadline_, deadline);
        onAction_ = std::move(onAction); onClose_ = std::move(onClose);
        hooks_.onExpired = std::move(hooks.onExpired); hooks_.onInvalidated = std::move(hooks.onInvalidated);
        hooks_.onRememberChanged = std::move(hooks.onRememberChanged);
#ifdef _WIN32
        try { if (!updateWindow()) { invalidate(); return false; } }
        catch (...) { invalidate(); return false; }
#endif
        return visible_ && requireInteraction();
    }
    if (content.kind == NoticeKind::recordingPrompt) content.rememberChoice = false;
    else content.checkboxTitle.clear();
    if (content.kind == NoticeKind::preview) deadline = std::min(deadline, now + std::chrono::seconds(6));
    if (significant(content.kind)) deadline = std::min(deadline, now + std::chrono::seconds(20));
    if (content.kind != NoticeKind::preview) recordHistory(content, deadline);
    const auto key = identity(content);
    const auto seen = std::find_if(seen_.begin(), seen_.end(), [&](const auto& e) { return e.identity == key && e.kind == content.kind; });
    if (quiet_ && content.kind != NoticeKind::recordingPrompt && content.kind != NoticeKind::preview) {
        markConsumed(content);
        return false;
    }
    if (content.kind != NoticeKind::preview && (seen == seen_.end() || seen->shown)) return false;
    const auto permit = readInteractionPermit();
    if (!permit.allowed || permit.epoch == 0) return false;
    if (visible_ && static_cast<int>(content.kind) <= static_cast<int>(content_.kind)) {
        if (content.kind == NoticeKind::shortRecording && (!pendingShort_ || pendingShort_->content.id != content.id))
            pendingShort_ = PendingShort{std::move(content), std::min(deadline, now + std::chrono::seconds(20)),
                std::move(onAction), std::move(onClose), std::move(hooks), permit.epoch};
        return false;
    }
    const auto beforeDismiss = generation_;
    if (visible_) invalidate();
    // An invalidation callback may have installed or cancelled another event.
    if (visible_ || generation_ > beforeDismiss + 1) return false;
    content_ = std::move(content);
    deadline_ = deadline; lastTick_ = now; holdStarted_.reset(); actionPending_ = false;
    ++generation_;
    const auto token = generation_;
    onAction_ = std::move(onAction); onClose_ = std::move(onClose);
    hooks_ = std::move(hooks);
    interactionEpoch_ = permit.epoch;
    const auto preparedAt = Clock::now();
    preparing_ = true;
    struct Preparing { bool& value; ~Preparing() { value = false; } } preparing{preparing_};
    try {
#ifdef _WIN32
        if (!createWindow()) { dismiss(); return false; }
#endif
        if (!requireInteraction()) return false;
        auto claim = hooks_.beforeFirstShow;
        if (claim && !claim()) { if (token == generation_) dismiss(); return false; }
        if (token != generation_) return false;
        if (!requireInteraction()) return false;
        // Do not show a meeting whose claim consumed its remaining hard deadline.
        const auto elapsed = Clock::now() - preparedAt;
        if (content_.kind == NoticeKind::meeting && now + elapsed >= deadline_) { dismiss(); return false; }
#ifdef _WIN32
        visible_ = showWindow();
#else
        visible_ = true; // portable model only, not evidence of a native window
#endif
        if (!visible_) { if (token == generation_) dismiss(); return false; }
        if (!requireInteraction()) return false;
        if (content_.kind == NoticeKind::meeting && now + (Clock::now() - preparedAt) >= deadline_) {
            dismiss(); return false;
        }
        if (content_.kind == NoticeKind::recordingPrompt) {
            const auto shownAfter = Clock::now() - preparedAt;
            deadline_ = now + shownAfter + std::chrono::seconds(8);
            lastTick_ = now + shownAfter;
        }
        markConsumed(content_);
        preparing_ = false;
        auto presented = hooks_.onPresented;
        if (presented) presented();
        return token == generation_ && visible_;
    } catch (...) {
        if (token == generation_) dismiss();
        return false;
    }
}
void RecordingNoticePresenter::showShortRecordingDiscarded(Clock::time_point now, std::function<void()> onPresented) {
    NoticePresentationHooks hooks;
    hooks.onPresented = std::move(onPresented);
    (void)present({NoticeKind::shortRecording, "short-recording-" + std::to_string(++shortSequence_), L"", std::wstring(message()), {}},
                  now, now + std::chrono::milliseconds(durationMilliseconds), {}, {}, std::move(hooks));
}
void RecordingNoticePresenter::queueShortRecordingDiscarded(Clock::time_point now, std::function<void()> onPresented) {
    tick(now);
    NoticeContent content{NoticeKind::shortRecording, "short-recording-" + std::to_string(++shortSequence_),
                          L"", std::wstring(message()), {}};
    const auto until = now + std::chrono::milliseconds(durationMilliseconds);
    recordHistory(content, until);
    pendingShort_.reset();
    if (quiet_) { markConsumed(content); return; }
    const auto permit = readInteractionPermit();
    if (!permit.allowed || permit.epoch == 0) return;
    NoticePresentationHooks hooks;
    hooks.onPresented = std::move(onPresented);
    pendingShort_ = PendingShort{std::move(content), until, {}, {}, std::move(hooks), permit.epoch};
}
bool RecordingNoticePresenter::allowsHold() const noexcept {
    return content_.kind == NoticeKind::preview || significant(content_.kind);
}
void RecordingNoticePresenter::setInteraction(bool hovered, bool focused, Clock::time_point now) {
    if (!visible_ || !allowsHold()) return;
    if (hovered || focused) {
        if (expired(now)) return;
        if (!holdStarted_) holdStarted_ = now;
    } else if (holdStarted_) {
        deadline_ += std::max(Clock::duration::zero(), now - *holdStarted_);
        holdStarted_.reset();
    }
}
void RecordingNoticePresenter::tick(Clock::time_point now) {
    if (visible_ && !requireInteraction()) return;
    seen_.erase(std::remove_if(seen_.begin(), seen_.end(), [&](const auto& e) {
        return e.until <= now && !(visible_ && e.kind == content_.kind && e.identity == identity(content_));
    }), seen_.end());
#ifdef _WIN32
    if (visible_) {
        auto window = static_cast<HWND>(window_);
        if (!window || !IsWindowVisible(window) || IsIconic(window)) { invalidatePresentation(); return; }
        RECT rect{}; POINT point{};
        const bool hovered = GetWindowRect(window, &rect) && GetCursorPos(&point) && PtInRect(&rect, point);
        const auto focused = GetFocus();
        setInteraction(hovered, focused == window || IsChild(window, focused), now);
    }
#endif
    if (visible_ && content_.kind == NoticeKind::recordingPrompt &&
        (now < lastTick_ || now - lastTick_ > std::chrono::milliseconds(2500))) { invalidatePresentation(); return; }
    lastTick_ = now;
    if (expired(now)) {
        auto expiredCallback = hooks_.onExpired;
        dismiss();
        if (expiredCallback) expiredCallback();
    }
    if (pendingShort_ && now >= pendingShort_->until) pendingShort_.reset();
}
bool RecordingNoticePresenter::presentPendingShort(Clock::time_point now) {
    if (pendingShort_ && now >= pendingShort_->until) pendingShort_.reset();
    if (pendingShort_) {
        const auto permit = readInteractionPermit();
        if (!permit.allowed || permit.epoch != pendingShort_->interactionEpoch) {
            invalidatePresentation();
            return false;
        }
    }
    if (quiet_ || (visible_ && content_.kind >= NoticeKind::shortRecording) || !pendingShort_) return false;
    auto pending = std::move(*pendingShort_); pendingShort_.reset();
    return present(std::move(pending.content), now, now + std::chrono::seconds(20),
        std::move(pending.onAction), std::move(pending.onClose), std::move(pending.hooks));
}
void RecordingNoticePresenter::finish(bool invalidated) {
    auto callback = invalidated ? std::move(hooks_.onInvalidated) : std::function<void()>{};
    visible_ = false; ++generation_; holdStarted_.reset(); actionPending_ = false;
    interactionEpoch_ = 0;
    onClose_ = {}; onAction_ = {}; hooks_ = {};
#ifdef _WIN32
    destroyWindow();
#endif
    if (callback) callback();
}
void RecordingNoticePresenter::dismiss() { finish(false); }
void RecordingNoticePresenter::invalidate() { finish(true); }
void RecordingNoticePresenter::invalidatePresentation() {
    pendingShort_.reset();
    content_.rememberChoice = false;
#ifdef _WIN32
    explicitFocus_ = false; // lock/desktop/sleep is not an explicit close gesture
#endif
    invalidate();
}
void RecordingNoticePresenter::setQuiet(bool quiet) {
    quiet_ = quiet;
    if (quiet) {
        pendingShort_.reset();
        if (visible_ && content_.kind != NoticeKind::recordingPrompt && content_.kind != NoticeKind::preview) invalidate();
    }
}
void RecordingNoticePresenter::resetContext() {
    pendingShort_.reset();
    auto invalidated = hooks_.onInvalidated;
    dismiss(); content_ = {}; history_.clear(); historyIdentities_.clear(); seen_.clear(); quiet_ = false;
    if (invalidated) invalidated();
}
void RecordingNoticePresenter::resolveProblem(const std::string& id) {
    const auto key = std::hash<std::string>{}(id);
    seen_.erase(std::remove_if(seen_.begin(), seen_.end(), [&](const auto& e) {
        return e.kind == NoticeKind::problem && e.identity == key;
    }), seen_.end());
    for (std::size_t i = 0; i < history_.size(); ++i)
        if (history_[i].kind == NoticeKind::problem && historyIdentities_[i] && historyIdentities_[i]->identity == key)
            historyIdentities_[i].reset();
    if (visible_ && content_.kind == NoticeKind::problem && content_.id == id) invalidate();
}
void RecordingNoticePresenter::close() { close(generation_); }
void RecordingNoticePresenter::close(std::uint64_t token) {
    if (!visible_ || token != generation_) return;
    if (!requireInteraction()) return;
    auto callback = onClose_; dismiss(); if (callback) callback();
}
void RecordingNoticePresenter::invoke(NoticeAction action) { invoke(action, generation_, Clock::now()); }
void RecordingNoticePresenter::invoke(NoticeAction action, std::uint64_t token, Clock::time_point now) {
    if (!visible_ || token != generation_ || actionPending_) return;
    if (!requireInteraction() || expired(now)) return;
    if (content_.kind == NoticeKind::recordingPrompt &&
        (now < lastTick_ || now - lastTick_ > std::chrono::milliseconds(2500))) { invalidatePresentation(); return; }
    const bool offered = std::any_of(content_.buttons.begin(), content_.buttons.end(), [action](const auto& b) { return b.action == action; });
    if (!offered) return;
    auto callback = onAction_;
    if (content_.kind == NoticeKind::meeting && (action == NoticeAction::join || action == NoticeAction::joinAndRecord)) {
        // A click is not handoff. Keep close/expiry available, block every action
        // before native layout/callback can reenter, and preserve this deadline.
        actionPending_ = true;
        content_.body += L"\nОткрываем…";
#ifdef _WIN32
        try { if (!updateWindow()) { invalidate(); return; } }
        catch (...) { invalidate(); return; }
#endif
        if (!visible_ || token != generation_ || !requireInteraction()) return;
    } else dismiss(); // Record/skip/problem actions remain terminal before callback.
    if (callback) callback(action);
}
void RecordingNoticePresenter::setRememberChoice(bool value) {
    if (!visible_ || content_.kind != NoticeKind::recordingPrompt) return;
    if (!requireInteraction()) return;
    content_.rememberChoice = value;
#ifdef _WIN32
    if (window_) {
        auto checkbox = GetDlgItem(static_cast<HWND>(window_), 201);
        SendMessageW(checkbox, BM_SETCHECK, value ? BST_CHECKED : BST_UNCHECKED, 0);
        InvalidateRect(checkbox, nullptr, FALSE);
    }
#endif
    auto callback = hooks_.onRememberChanged;
    if (callback) callback(value);
}
void RecordingNoticePresenter::setDarkTheme(bool dark) {
    if (themeExplicit_ && dark_ == dark) return;
    themeExplicit_ = true;
    dark_ = dark;
    reposition();
}
void RecordingNoticePresenter::reposition() {
    if (visible_ && !requireInteraction()) return;
#ifdef _WIN32
    if (visible_) {
        try { if (!updateWindow()) invalidate(); }
        catch (...) { invalidate(); }
    }
#endif
}
void RecordingNoticePresenter::focus() {
    if (!visible_ || !requireInteraction()) return;
#ifdef _WIN32
    if (!window_ || !visible_) return;
    auto window = static_cast<HWND>(window_);
    if (!explicitFocus_) previousForeground_ = GetForegroundWindow();
    if (SetForegroundWindow(window)) {
        explicitFocus_ = true;
        SetFocus(GetNextDlgTabItem(window, nullptr, FALSE));
    }
#endif
}

std::optional<NoticePlacement> RecordingNoticePresenter::place(NoticeRect work, int desiredHeight,
    int minimumHeight, const std::vector<NoticeRect>& protectedFrames, int dpi) {
    if (dpi <= 0 || dpi > 960 || desiredHeight < minimumHeight || minimumHeight <= 0) return std::nullopt;
    const auto scale = [dpi](int dip) { return (dip * dpi + 48) / 96; };
    const int edge = scale(8), inset = scale(14);
    const int width = std::min(scale(380), work.width - 2 * edge - 2 * inset);
    if (width < scale(220)) return std::nullopt;
    int y = work.y + edge;
    for (std::size_t attempt = 0; attempt <= protectedFrames.size(); ++attempt) {
        const int height = std::min(desiredHeight, work.y + work.height - edge - y - 2 * inset);
        if (height < minimumHeight) return std::nullopt;
        NoticeRect frame{work.x + work.width - edge - width - 2 * inset, y, width + 2 * inset, height + 2 * inset};
        int nextY = y;
        for (const auto& r : protectedFrames) {
            if (r.width > 0 && r.height > 0 && frame.x < r.x + r.width && r.x < frame.x + frame.width &&
                frame.y < r.y + r.height && r.y < frame.y + frame.height) nextY = std::max(nextY, r.y + r.height + edge);
        }
        if (nextY == y) return NoticePlacement{frame, width, height};
        y = nextY;
    }
    return std::nullopt;
}

#ifdef _WIN32
namespace {
constexpr wchar_t kClass[] = L"GrafNotificationCard";
constexpr wchar_t kButtonProc[] = L"GrafNotificationButtonProc";
constexpr wchar_t kDark[] = L"GrafNotificationDark";
constexpr wchar_t kBrush[] = L"GrafNotificationBrush";
constexpr UINT_PTR kTick = 1;

bool highContrast() {
    HIGHCONTRASTW value{}; value.cbSize = sizeof(value);
    return SystemParametersInfoW(SPI_GETHIGHCONTRAST, sizeof(value), &value, 0) &&
        (value.dwFlags & HCF_HIGHCONTRASTON);
}
COLORREF background(HWND window) {
    return highContrast() ? GetSysColor(COLOR_WINDOW) : GetPropW(window, kDark) ? RGB(31, 31, 31) : RGB(255, 255, 255);
}
COLORREF foreground(HWND window) {
    return highContrast() ? GetSysColor(COLOR_WINDOWTEXT) : GetPropW(window, kDark) ? RGB(250, 250, 250) : RGB(31, 31, 31);
}
COLORREF border(HWND window) {
    return highContrast() ? GetSysColor(COLOR_WINDOWTEXT) : GetPropW(window, kDark) ? RGB(148, 148, 148) : RGB(115, 115, 115);
}
void interaction(HWND window, RecordingNoticePresenter& presenter) {
    RECT rect{}; POINT point{};
    const bool hover = GetWindowRect(window, &rect) && GetCursorPos(&point) && PtInRect(&rect, point);
    auto focus = GetFocus();
    presenter.setInteraction(hover, focus == window || IsChild(window, focus), RecordingNoticePresenter::Clock::now());
}
LRESULT CALLBACK buttonProc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    auto old = reinterpret_cast<WNDPROC>(GetPropW(window, kButtonProc));
    if (message == WM_PAINT && GetDlgCtrlID(window) == 201) {
        // Preserve the native BUTTON/BS_AUTOCHECKBOX role, check state and input;
        // paint its label explicitly so the dark card never gets black theme text.
        const auto parent = GetParent(window);
        PAINTSTRUCT paint{}; const auto dc = BeginPaint(window, &paint);
        RECT rect{}; GetClientRect(window, &rect);
        auto brush = CreateSolidBrush(background(parent)); FillRect(dc, &rect, brush); DeleteObject(brush);
        const int box = MulDiv(18, static_cast<int>(GetDpiForWindow(window)), 96);
        RECT mark{0, 0, box, box};
        DrawFrameControl(dc, &mark, DFC_BUTTON, DFCS_BUTTONCHECK |
            (SendMessageW(window, BM_GETCHECK, 0, 0) == BST_CHECKED ? DFCS_CHECKED : 0));
        auto font = reinterpret_cast<HFONT>(SendMessageW(window, WM_GETFONT, 0, 0));
        auto oldFont = SelectObject(dc, font);
        wchar_t text[1025]{}; GetWindowTextW(window, text, 1025);
        rect.left = box + MulDiv(6, static_cast<int>(GetDpiForWindow(window)), 96);
        SetBkMode(dc, TRANSPARENT); SetTextColor(dc, foreground(parent));
        DrawTextW(dc, text, -1, &rect, DT_WORDBREAK | DT_NOPREFIX);
        if (GetFocus() == window) DrawFocusRect(dc, &rect);
        SelectObject(dc, oldFont); EndPaint(window, &paint); return 0;
    }
    if (message == WM_GETDLGCODE) return DLGC_WANTALLKEYS;
    if (message == WM_KEYDOWN) {
        const auto parent = GetParent(window);
        if (wparam == VK_ESCAPE) { SendMessageW(parent, WM_CLOSE, 0, 0); return 0; }
        if (wparam == VK_TAB) {
            SetFocus(GetNextDlgTabItem(parent, window, GetKeyState(VK_SHIFT) < 0)); return 0;
        }
        if ((wparam == VK_RETURN || wparam == VK_SPACE) && GetDlgCtrlID(window) != 200) {
            SendMessageW(window, BM_CLICK, 0, 0); return 0;
        }
    }
    // BM_CLICK on keydown is terminal; swallow keyup to avoid a second activation.
    if (message == WM_KEYUP && (wparam == VK_RETURN || wparam == VK_SPACE) && GetDlgCtrlID(window) != 200) return 0;
    const auto result = CallWindowProcW(old, window, message, wparam, lparam);
    if (message == WM_SETFOCUS || message == WM_KILLFOCUS || message == WM_MOUSEMOVE) {
        auto parent = GetParent(window);
        auto* presenter = reinterpret_cast<RecordingNoticePresenter*>(GetWindowLongPtrW(parent, GWLP_USERDATA));
        if (presenter) interaction(parent, *presenter);
    }
    return result;
}
LRESULT CALLBACK cardProc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    auto* presenter = reinterpret_cast<RecordingNoticePresenter*>(GetWindowLongPtrW(window, GWLP_USERDATA));
    try {
    if (message == WM_NCCREATE) {
        presenter = static_cast<RecordingNoticePresenter*>(reinterpret_cast<CREATESTRUCTW*>(lparam)->lpCreateParams);
        SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(presenter));
    }
    if (message == WM_MOUSEACTIVATE) return MA_NOACTIVATE; // first click still delivered
    if (presenter && message == WM_CLOSE) { presenter->close(); return 0; }
    if (presenter && message == WM_COMMAND && HIWORD(wparam) == BN_CLICKED) {
        const auto id = LOWORD(wparam);
        if (reinterpret_cast<HWND>(lparam) != GetDlgItem(window, id)) return 0;
        if (id == 100) presenter->close();
        else if (id == 201) presenter->setRememberChoice(SendMessageW(GetDlgItem(window, 201), BM_GETCHECK, 0, 0) == BST_CHECKED);
        else if (id >= 101 && id <= 105) presenter->invoke(static_cast<NoticeAction>(id - 101));
        return 0;
    }
    if (presenter && message == WM_TIMER && wparam == kTick) { presenter->tick(RecordingNoticePresenter::Clock::now()); return 0; }
    if (presenter && message == WM_DPICHANGED) {
        PostMessageW(window, WM_APP + 74, 0, 0); return 0;
    }
    if (presenter && (message == WM_DISPLAYCHANGE || message == WM_SETTINGCHANGE || message == WM_APP + 74)) {
        presenter->reposition(); return 0;
    }
    if (presenter && message == WM_MOUSEMOVE) interaction(window, *presenter);
    if (message == WM_ERASEBKGND) return 1;
    if (message == WM_CTLCOLORSTATIC || message == WM_CTLCOLOREDIT || message == WM_CTLCOLORBTN) {
        const auto dc = reinterpret_cast<HDC>(wparam);
        SetTextColor(dc, foreground(window)); SetBkColor(dc, background(window));
        return reinterpret_cast<LRESULT>(GetPropW(window, kBrush));
    }
    if (message == WM_PAINT) {
        PAINTSTRUCT paint{}; const auto dc = BeginPaint(window, &paint);
        RECT area{}; GetClientRect(window, &area);
        const auto dpi = GetDpiForWindow(window);
        const auto scale = [dpi](int value) { return MulDiv(value, static_cast<int>(dpi ? dpi : 96), 96); };
        auto brush = CreateSolidBrush(background(window));
        auto pen = CreatePen(PS_SOLID, 1, border(window));
        auto oldBrush = SelectObject(dc, brush); auto oldPen = SelectObject(dc, pen);
        RoundRect(dc, scale(14), scale(14), area.right - scale(14), area.bottom - scale(14), scale(24), scale(24));
        SelectObject(dc, oldPen); SelectObject(dc, oldBrush);
        DeleteObject(pen); DeleteObject(brush); EndPaint(window, &paint); return 0;
    }
    if (message == WM_DRAWITEM) {
        const auto* item = reinterpret_cast<DRAWITEMSTRUCT*>(lparam);
        if (item->CtlType != ODT_BUTTON) return FALSE;
        auto rect = item->rcItem;
        const auto dpi = GetDpiForWindow(window);
        const auto scale = [dpi](int value) { return MulDiv(value, static_cast<int>(dpi ? dpi : 96), 96); };
        const bool primary = item->CtlID == 101 || item->CtlID == 103 || item->CtlID == 105;
        const auto fill = primary ? (highContrast() ? GetSysColor(COLOR_HIGHLIGHT) : RGB(97, 77, 230)) : background(window);
        const auto ink = primary ? (highContrast() ? GetSysColor(COLOR_HIGHLIGHTTEXT) : RGB(255, 255, 255)) : foreground(window);
        auto brush = CreateSolidBrush(fill); auto pen = CreatePen(PS_SOLID, scale(1), border(window));
        FillRect(item->hDC, &item->rcItem, brush);
        auto oldBrush = SelectObject(item->hDC, brush); auto oldPen = SelectObject(item->hDC, pen);
        if (item->CtlID == 100) {
            InflateRect(&rect, -scale(5), -scale(5)); // 18 DIP circle inside 28 DIP hit
            Ellipse(item->hDC, rect.left, rect.top, rect.right, rect.bottom);
            auto glyphPen = CreatePen(PS_SOLID, std::max(1, scale(1)), ink);
            SelectObject(item->hDC, glyphPen);
            const int a = scale(10), b = scale(18);
            MoveToEx(item->hDC, a, a, nullptr); LineTo(item->hDC, b, b);
            MoveToEx(item->hDC, b, a, nullptr); LineTo(item->hDC, a, b);
            SelectObject(item->hDC, pen); DeleteObject(glyphPen);
        } else {
            RoundRect(item->hDC, rect.left, rect.top, rect.right, rect.bottom, scale(8), scale(8));
            wchar_t label[1025]{};
            GetWindowTextW(item->hwndItem, label, 1025);
            auto font = reinterpret_cast<HFONT>(SendMessageW(item->hwndItem, WM_GETFONT, 0, 0));
            auto oldFont = SelectObject(item->hDC, font);
            SetBkMode(item->hDC, TRANSPARENT); SetTextColor(item->hDC, ink);
            InflateRect(&rect, -scale(12), -scale(6));
            DrawTextW(item->hDC, label, -1, &rect, DT_CENTER | DT_WORDBREAK | DT_NOPREFIX);
            SelectObject(item->hDC, oldFont);
        }
        if ((item->itemState & ODS_FOCUS) || GetFocus() == item->hwndItem) {
            auto focusRect = item->rcItem;
            InflateRect(&focusRect, -scale(2), -scale(2));
            DrawFocusRect(item->hDC, &focusRect);
        }
        SelectObject(item->hDC, oldPen); SelectObject(item->hDC, oldBrush);
        DeleteObject(pen); DeleteObject(brush); return TRUE;
    }
    if (message == WM_DESTROY) KillTimer(window, kTick);
    return DefWindowProcW(window, message, wparam, lparam);
    } catch (...) {
        // No C++ exception may cross the native window-procedure boundary.
        if (presenter) presenter->dismiss();
        return 0;
    }
}
bool wireControl(HWND child) {
    const auto old = GetWindowLongPtrW(child, GWLP_WNDPROC);
    if (!SetPropW(child, kButtonProc, reinterpret_cast<HANDLE>(old))) return false;
    SetLastError(ERROR_SUCCESS);
    return SetWindowLongPtrW(child, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(buttonProc)) != 0 || GetLastError() == ERROR_SUCCESS;
}
bool setTextIfChanged(HWND control, const std::wstring& text) {
    const auto length = GetWindowTextLengthW(control);
    std::wstring previous(static_cast<std::size_t>(length) + 1, L'\0');
    GetWindowTextW(control, previous.data(), length + 1); previous.resize(static_cast<std::size_t>(length));
    return previous == text || SetWindowTextW(control, text.c_str()) != FALSE;
}
}

bool RecordingNoticePresenter::createWindow() {
    WNDCLASSEXW cls{}; cls.cbSize = sizeof(cls); cls.lpfnWndProc = cardProc;
    cls.hInstance = GetModuleHandleW(nullptr); cls.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    cls.lpszClassName = kClass;
    if (!RegisterClassExW(&cls) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS) return false;
    POINT cursor{};
    auto monitor = GetCursorPos(&cursor) ? MonitorFromPoint(cursor, MONITOR_DEFAULTTONULL) : nullptr;
    if (!monitor) monitor = MonitorFromPoint(POINT{0, 0}, MONITOR_DEFAULTTOPRIMARY);
    MONITORINFO info{}; info.cbSize = sizeof(info);
    if (!monitor || !GetMonitorInfoW(monitor, &info)) return false;
    selectedMonitor_ = monitor;
    auto window = CreateWindowExW(WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_CONTROLPARENT,
        kClass, L"Уведомление GRAF", WS_POPUP | WS_CLIPCHILDREN, info.rcWork.left, info.rcWork.top,
        1, 1, nullptr, nullptr, cls.hInstance, this);
    if (!window) return false;
    window_ = window;
    const auto control = [&](const wchar_t* type, const wchar_t* text, DWORD style, int id) {
        auto child = CreateWindowExW(0, type, text, WS_CHILD | style, 0, 0, 1, 1, window,
            reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), cls.hInstance, nullptr);
        return child && wireControl(child);
    };
    // Create once, initially hidden. Native controls retain accessible names,
    // roles, checkbox state, selection and keyboard scroll support.
    bool ok = control(L"BUTTON", L"Закрыть уведомление", WS_TABSTOP | BS_OWNERDRAW, 100) &&
        control(L"EDIT", L"", WS_TABSTOP | ES_READONLY | ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL, 200) &&
        control(L"BUTTON", L"", WS_TABSTOP | BS_AUTOCHECKBOX | BS_MULTILINE, 201);
    for (int id = 101; ok && id <= 105; ++id) ok = control(L"BUTTON", L"", WS_TABSTOP | BS_OWNERDRAW, id);
    if (!ok || !updateWindow()) { destroyWindow(); return false; }
    return true;
}

bool RecordingNoticePresenter::updateWindow() {
    if (updatingWindow_) return true;
    updatingWindow_ = true;
    struct Updating { bool& value; ~Updating() { value = false; } } updating{updatingWindow_};
    auto window = static_cast<HWND>(window_);
    if (!window || !IsWindow(window)) return false;
    // Call user/domain providers before acquiring GDI resources; an exception
    // is a presentation failure, not a leak or permission to overlap Stop.
    auto protectedFrames = protectedFramesProvider ? protectedFramesProvider() : std::vector<NoticeRect>{};
    if (protectedFrames.size() > 64) return false;
    MONITORINFO info{}; info.cbSize = sizeof(info);
    auto monitor = static_cast<HMONITOR>(selectedMonitor_);
    if (!monitor || !GetMonitorInfoW(monitor, &info)) {
        monitor = MonitorFromPoint(POINT{0, 0}, MONITOR_DEFAULTTOPRIMARY);
        if (!monitor || !GetMonitorInfoW(monitor, &info)) return false;
        selectedMonitor_ = monitor;
    }
    // The first invisible placement associates the window with the chosen monitor.
    if (!IsWindowVisible(window)) {
        if (!SetWindowPos(window, nullptr, info.rcWork.left, info.rcWork.top, 1, 1, SWP_NOACTIVATE | SWP_NOZORDER)) return false;
    }
    const auto dpi = GetDpiForWindow(window);
    const auto scale = [dpi](int value) { return MulDiv(value, static_cast<int>(dpi ? dpi : 96), 96); };
    NONCLIENTMETRICSW metrics{}; metrics.cbSize = sizeof(metrics);
    if (!SystemParametersInfoForDpi(SPI_GETNONCLIENTMETRICS, sizeof(metrics), &metrics, 0, dpi ? dpi : 96)) return false;
    DWORD textScale = 100, bytes = sizeof(textScale);
    if (RegGetValueW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Accessibility", L"TextScaleFactor",
        RRF_RT_REG_DWORD, nullptr, &textScale, &bytes) != ERROR_SUCCESS) textScale = 100;
    textScale = std::clamp<DWORD>(textScale, 100, 225);
    const int fontHeight = std::max(static_cast<int>(std::abs(metrics.lfMessageFont.lfHeight)), MulDiv(scale(14), static_cast<int>(textScale), 100));
    metrics.lfMessageFont.lfHeight = -fontHeight;
    auto font = CreateFontIndirectW(&metrics.lfMessageFont);
    if (!font) return false;
    auto oldFont = static_cast<HFONT>(font_); font_ = font;
    if (!themeExplicit_) {
        DWORD light = 1, size = sizeof(light);
        if (RegGetValueW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
            L"AppsUseLightTheme", RRF_RT_REG_DWORD, nullptr, &light, &size) == ERROR_SUCCESS) dark_ = light == 0;
    }
    if (dark_) SetPropW(window, kDark, reinterpret_cast<HANDLE>(1)); else RemovePropW(window, kDark);
    auto brush = CreateSolidBrush(background(window));
    if (!brush) { font_ = oldFont; DeleteObject(font); return false; }
    auto oldBrush = static_cast<HBRUSH>(background_);
    if (!SetPropW(window, kBrush, brush)) { font_ = oldFont; DeleteObject(font); DeleteObject(brush); return false; }
    background_ = brush;
    for (int id : {100, 200, 201, 101, 102, 103, 104, 105})
        SendMessageW(GetDlgItem(window, id), WM_SETFONT, reinterpret_cast<WPARAM>(font), FALSE);
    const NoticeRect work{info.rcWork.left, info.rcWork.top,
        info.rcWork.right - info.rcWork.left, info.rcWork.bottom - info.rcWork.top};
    const int width = std::min(scale(380), work.width - scale(44));
    const int padding = scale(12), gap = scale(8), inset = scale(14);
    const auto dc = GetDC(window);
    if (!dc) { if (oldFont) DeleteObject(oldFont); if (oldBrush) DeleteObject(oldBrush); return false; }
    const auto savedFont = SelectObject(dc, font);
    const auto measure = [&](const std::wstring& text, int available) {
        if (text.empty()) return 0;
        RECT rect{0, 0, std::max(1, available), 0};
        DrawTextW(dc, text.c_str(), -1, &rect, DT_CALCRECT | DT_WORDBREAK | DT_NOPREFIX | DT_EDITCONTROL);
        return static_cast<int>(rect.bottom);
    };
    const auto body = content_.title.empty() ? content_.body :
        content_.body.empty() ? content_.title : content_.title + L"\r\n" + content_.body;
    const int textWidth = width - 2 * padding - scale(4);
    int textHeight = measure(body, textWidth);
    const int checkboxHeight = content_.checkboxTitle.empty() ? 0 : std::max(scale(24), measure(content_.checkboxTitle, width - 2 * padding - scale(24)));
    std::vector<int> buttonWidths, buttonHeights;
    int totalWidth = 0;
    for (const auto& button : content_.buttons) {
        SIZE size{};
        GetTextExtentPoint32W(dc, button.title.c_str(), static_cast<int>(button.title.size()), &size);
        buttonWidths.push_back(static_cast<int>(size.cx) + 2 * padding);
        totalWidth += buttonWidths.back();
    }
    if (!buttonWidths.empty()) totalWidth += static_cast<int>(buttonWidths.size() - 1) * gap;
    const bool vertical = totalWidth > width - 2 * padding;
    int actionsHeight = 0;
    for (std::size_t i = 0; i < content_.buttons.size(); ++i) {
        const int h = std::max(scale(32), measure(content_.buttons[i].title,
            (vertical ? width - 2 * padding : buttonWidths[i]) - 2 * padding) + scale(12));
        buttonHeights.push_back(h);
        actionsHeight = vertical ? actionsHeight + h + (i ? gap : 0) : std::max(actionsHeight, h);
    }
    const int controlsHeight = (checkboxHeight ? gap + checkboxHeight : 0) + (actionsHeight ? gap + actionsHeight : 0);
    const int desired = std::max(scale(44), 2 * padding + textHeight + controlsHeight);
    const int minimum = 2 * padding + std::min(textHeight, fontHeight + scale(4)) + controlsHeight;
    auto placement = place(work, desired, std::max(scale(44), minimum), protectedFrames, static_cast<int>(dpi ? dpi : 96));
    SelectObject(dc, savedFont); ReleaseDC(window, dc);
    if (!placement) { if (oldFont) DeleteObject(oldFont); if (oldBrush) DeleteObject(oldBrush); return false; }
    const int visibleTextHeight = placement->cardHeight - 2 * padding - controlsHeight;
    const bool scrolls = textHeight > visibleTextHeight;
    const auto layout = [&](int id, int x, int y, int w, int h, bool show) {
        auto child = GetDlgItem(window, id);
        SendMessageW(child, WM_SETFONT, reinterpret_cast<WPARAM>(font), FALSE);
        return SetWindowPos(child, nullptr, x, y, w, h, SWP_NOACTIVATE | SWP_NOZORDER |
            (show ? SWP_SHOWWINDOW : SWP_HIDEWINDOW)) != FALSE;
    };
    bool ok = setTextIfChanged(GetDlgItem(window, 200), body);
    auto textStyle = GetWindowLongPtrW(GetDlgItem(window, 200), GWL_STYLE);
    SetWindowLongPtrW(GetDlgItem(window, 200), GWL_STYLE, scrolls ? textStyle | WS_TABSTOP : textStyle & ~WS_TABSTOP);
    ShowScrollBar(GetDlgItem(window, 200), SB_VERT, scrolls);
    ok = layout(100, 0, 0, scale(28), scale(28), true) &&
        layout(200, inset + padding + scale(4), inset + padding, textWidth, visibleTextHeight, !body.empty()) && ok;
    ok = setTextIfChanged(GetDlgItem(window, 201), content_.checkboxTitle) && ok;
    SendMessageW(GetDlgItem(window, 201), BM_SETCHECK, content_.rememberChoice ? BST_CHECKED : BST_UNCHECKED, 0);
    int y = inset + padding + visibleTextHeight;
    if (checkboxHeight) y += gap;
    ok = layout(201, inset + padding, y, width - 2 * padding, std::max(1, checkboxHeight), checkboxHeight != 0) && ok;
    y += checkboxHeight;
    if (actionsHeight) y += gap;
    int x = inset + width - padding - totalWidth;
    // Z-order defines native Tab order: close, text, checkbox, secondary, primary.
    HWND previousControl = HWND_TOP;
    for (int id : {100, 200, 201}) {
        auto control = GetDlgItem(window, id);
        ok = SetWindowPos(control, previousControl, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE) && ok;
        previousControl = control;
    }
    HWND previous = GetDlgItem(window, 201);
    for (int id = 101; id <= 105; ++id) {
        const bool offered = std::any_of(content_.buttons.begin(), content_.buttons.end(), [id](const auto& button) {
            return 101 + static_cast<int>(button.action) == id;
        });
        if (!offered) ShowWindow(GetDlgItem(window, id), SW_HIDE);
    }
    for (std::size_t i = 0; i < content_.buttons.size(); ++i) {
        const auto& button = content_.buttons[i];
        auto child = GetDlgItem(window, 101 + static_cast<int>(button.action));
        EnableWindow(child, !actionPending_);
        ok = setTextIfChanged(child, button.title) && ok;
        const int h = vertical ? buttonHeights[i] : actionsHeight;
        ok = layout(101 + static_cast<int>(button.action), vertical ? inset + padding : x, y,
            vertical ? width - 2 * padding : buttonWidths[i], h, true) && ok;
        ok = SetWindowPos(child, previous, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE) && ok;
        previous = child;
        if (vertical) y += h + gap; else x += buttonWidths[i] + gap;
    }
    // Rounded card plus separate 28-DIP close hit region, both inside outer inset.
    auto region = CreateRoundRectRgn(inset, inset, inset + width + 1, inset + placement->cardHeight + 1, scale(24), scale(24));
    auto closeRegion = CreateEllipticRgn(0, 0, scale(28) + 1, scale(28) + 1);
    if (!region || !closeRegion) ok = false;
    else {
        if (CombineRgn(region, region, closeRegion, RGN_OR) == ERROR) ok = false;
        if (!SetWindowRgn(window, region, FALSE)) { DeleteObject(region); ok = false; }
        region = nullptr; // window owns a successfully installed region
    }
    if (region) DeleteObject(region);
    if (closeRegion) DeleteObject(closeRegion);
    const auto& frame = placement->frame;
    ok = SetWindowPos(window, HWND_TOPMOST, frame.x, frame.y, frame.width, frame.height, SWP_NOACTIVATE) && ok;
    if (oldFont) DeleteObject(oldFont);
    if (oldBrush) DeleteObject(oldBrush);
    RedrawWindow(window, nullptr, nullptr, RDW_INVALIDATE | RDW_ALLCHILDREN);
    return ok;
}
bool RecordingNoticePresenter::showWindow() {
    auto window = static_cast<HWND>(window_);
    if (!window) return false;
    // Claim may have moved Stop or changed the work area. Revalidate while hidden.
    if (!updateWindow()) return false;
    if (!requireInteraction()) return false;
    ShowWindow(window, SW_SHOWNOACTIVATE);
    if (!IsWindowVisible(window) || IsIconic(window)) return false;
    if (!requireInteraction()) return false;
    if (!SetTimer(window, kTick, 100, nullptr)) return false;
    NotifyWinEvent(EVENT_SYSTEM_ALERT, window, OBJID_CLIENT, CHILDID_SELF);
    return true;
}
void RecordingNoticePresenter::destroyWindow() {
    auto window = static_cast<HWND>(window_);
    auto previous = static_cast<HWND>(previousForeground_);
    const bool restore = explicitFocus_ && window && GetForegroundWindow() == window;
    window_ = nullptr; selectedMonitor_ = nullptr; previousForeground_ = nullptr; explicitFocus_ = false;
    if (window) {
        SetWindowLongPtrW(window, GWLP_USERDATA, 0);
        KillTimer(window, kTick);
        ShowWindow(window, SW_HIDE);
        DestroyWindow(window);
    }
    if (font_) DeleteObject(static_cast<HFONT>(font_));
    if (background_) DeleteObject(static_cast<HBRUSH>(background_));
    font_ = nullptr; background_ = nullptr;
    if (restore && previous && IsWindow(previous)) SetForegroundWindow(previous);
}
#endif
} // namespace graf::windows
