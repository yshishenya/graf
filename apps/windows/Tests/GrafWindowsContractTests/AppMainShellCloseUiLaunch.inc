// Observe the original Closing/Closed path in an isolated partial-startup shell.
// Actual WM_CLOSE and native tray registration; no device, writer or web startup.
using namespace graf::windows;
using namespace graf::windows::testing;
struct ShellCloseState {
    winrt::Microsoft::UI::Dispatching::DispatcherQueueTimer observer{nullptr};
    std::filesystem::path root = std::filesystem::temp_directory_path() /
        ("graf-shell-close-" + native_capture_detail::newSessionId());
    WindowsCaptureSessionController* controller = nullptr;
    HWND window = nullptr;
    std::string session;
    ULONGLONG began = GetTickCount64();
    unsigned phase = 0, closes = 0, reopens = 0, quitInvocations = 0;
    bool failed = false;
};
auto shellClose = std::make_shared<ShellCloseState>();
problemStore_ = NotificationPreferenceStore{};
shellClose->observer = root_.DispatcherQueue().CreateTimer();
shellClose->observer.Interval(std::chrono::milliseconds(100));
shellClose->observer.Tick([this, shellClose](auto const&, auto const&) {
    try {
        requireProblemUi(GetTickCount64() - shellClose->began < 8000, "shell_close_deadline");
        const auto visible = [&] { return window_.AppWindow().IsVisible() && IsWindowVisible(mainWindowHandle_); };
        const auto close = [&] {
            requireProblemUi(PostMessageW(mainWindowHandle_, WM_CLOSE, 0, 0) != FALSE, "post_native_close");
            ++shellClose->closes;
        };
        const auto tray = [&] {
            tray_ = std::make_unique<WindowsTray>(reinterpret_cast<std::uintptr_t>(mainWindowHandle_),
                [this] { openMainWindow(); }, [this] { stopCapture(); }, [this] { requestExit(); });
            requireProblemUi(tray_->available(), "actual_tray_registered");
        };
        const auto same = [&] {
            requireProblemUi(!exitRequested_ && !shuttingDown_ && mainWindowHandle_ == shellClose->window &&
                &NativeCaptureStorageTestPeer::controller(*capture_) == shellClose->controller, "same_native_window_controller");
            requireProblemUi(!shellClose->session.empty() && shellClose->controller->session().sessionId() == shellClose->session &&
                capture_->indicator().state == SessionState::starting &&
                CaptureSessionTestPeer::deviceFreeReservation(*shellClose->controller), "same_starting_reservation_no_devices");
            WindowsDesktopSession other("generated-shell-close-contender");
            const auto blocked = other.beginReadinessCheck();
            requireProblemUi(!blocked.accepted() && blocked.reason == ReasonCode::activeSessionExists, "same_exclusive_lease");
        };
        switch (shellClose->phase) {
        case 0: {
            const auto button = problemUiButton(root_, L"Закрыть GRAF");
            if (!button || !button.IsLoaded() || button.ActualWidth() <= 0) return;
            // Production initializes this after the early startup-error return.
            // Use the HWND of this very WinUI window, with no title-based lookup.
            mainWindowHandle_ = nativeWindowHandle(window_);
            requireProblemUi(mainWindowHandle_ && capture_ && !reminders_ && visible(), "partial_shell_visible");
            shellClose->window = mainWindowHandle_;
            requireProblemUi(capture_->indicator().state == SessionState::idle, "idle_before_close");
            tray(); close(); break;
        }
        case 1:
            requireProblemUi(!visible() && !exitRequested_ && capture_->indicator().state == SessionState::idle, "idle_hidden");
            openMainWindow(); ++shellClose->reopens; break;
        case 2:
            requireProblemUi(visible() && mainWindowHandle_ == shellClose->window && !exitRequested_, "idle_reopened");
            tray_.reset(); refreshTrayAvailability(); close(); break;
        case 3:
            requireProblemUi(visible() && !tray_ && !exitRequested_ && capture_->indicator().state == SessionState::idle, "idle_no_tray_kept");
            tray();
            shellClose->controller = &NativeCaptureStorageTestPeer::controller(*capture_);
            requireProblemUi(CaptureSessionTestPeer::reserve(*shellClose->controller), "real_start_reservation");
            shellClose->session = shellClose->controller->session().sessionId();
            same();
            requireProblemUi(ensureRecordingIndicator() && recordingIndicatorAvailable(), "actual_starting_stop_visible");
            close(); break;
        case 4:
            same(); requireProblemUi(!visible() && recordingIndicatorAvailable(), "starting_hidden_stop_visible");
            close(); break; // Repeated WM_CLOSE must leave the same reservation alone.
        case 5:
            same(); requireProblemUi(!visible() && recordingIndicatorAvailable(), "repeat_close_same_start");
            openMainWindow(); ++shellClose->reopens; break;
        case 6:
            same(); requireProblemUi(visible(), "starting_reopened");
            indicatorWindow_.AppWindow().Hide();
            requireProblemUi(!recordingIndicatorAvailable(), "indicator_unavailable");
            close(); break;
        case 7:
            same(); requireProblemUi(visible() && tray_ && tray_->available(), "no_indicator_kept");
            requireProblemUi(ensureRecordingIndicator() && recordingIndicatorAvailable(), "stop_restored");
            tray_.reset(); refreshTrayAvailability(); close(); break;
        case 8: {
            same(); requireProblemUi(visible() && !tray_ && recordingIndicatorAvailable(), "starting_no_tray_kept_stop_visible");
            ++shellClose->quitInvocations;
            ++shellClose->phase; // Closed can run synchronously inside the actual button event.
            invokeProblemUi(problemUiButton(root_, L"Закрыть GRAF"));
            return;
        }
        default: return; // Only the production drain may close after Quit.
        }
        std::fprintf(stderr, "SHELL_CLOSE phase=%u pass=1\n", shellClose->phase);
        std::fflush(stderr);
        ++shellClose->phase;
    } catch (...) {
        shellClose->failed = true;
        std::fputs("SHELL_CLOSE failure=1 rescue_quit=1\n", stderr); std::fflush(stderr);
        ++shellClose->quitInvocations; requestExit();
    }
});
window_.Closed([this, shellClose](auto const&, auto const&) {
    shellClose->observer.Stop();
    WindowsDesktopSession other("generated-shell-close-released");
    const auto released = other.beginReadinessCheck().accepted();
    const bool noFiles = !std::filesystem::exists(shellClose->root);
    problemUiResult = !shellClose->failed && shellClose->phase == 9 && shellClose->closes == 6 &&
        shellClose->reopens == 2 && shellClose->quitInvocations == 1 &&
        exitWorkDrained() && released && noFiles ? 73 : 3;
    std::fprintf(stderr, "SHELL_CLOSE terminal=1 phases=%u closes=%u reopens=%u quit=%u drained=%u lease_released=%u no_files=%u exit=%d\n",
        shellClose->phase, shellClose->closes, shellClose->reopens, shellClose->quitInvocations,
        unsigned(exitWorkDrained()), unsigned(released), unsigned(noFiles), problemUiResult);
    std::fflush(stderr);
});
shellClose->observer.Start();
