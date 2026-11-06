// Inserted into the original OnLaunched after window_.Content(root_).
// Production Closing/Closed, exit methods and stateTimer remain unchanged.
using namespace graf::windows;
using namespace graf::windows::testing;
struct StartupExitState {
    std::shared_ptr<NativeCaptureStorageTestPeer::StartupHold> hold;
    winrt::Microsoft::UI::Dispatching::DispatcherQueueTimer observer{nullptr};
    std::filesystem::path root = std::filesystem::temp_directory_path() /
        ("graf-startup-exit-" + native_capture_detail::newSessionId());
    ULONGLONG began = GetTickCount64(), firstQuit = 0;
    unsigned invocations = 0, heldTicks = 0;
    bool failed = false, released = false;
};
auto startupExit = std::make_shared<StartupExitState>();
problemStore_ = NotificationPreferenceStore{};
startupExit->observer = root_.DispatcherQueue().CreateTimer();
startupExit->observer.Interval(std::chrono::milliseconds(100));
startupExit->observer.Tick([this, startupExit](auto const&, auto const&) {
    try {
        const auto now = GetTickCount64();
        if (!startupExit->invocations) {
            requireProblemUi(now - startupExit->began < 5000, "startup_error_button_deadline");
            const auto button = problemUiButton(root_, L"Закрыть GRAF");
            if (!button || !button.IsLoaded() || button.ActualWidth() <= 0) return;
            requireProblemUi(capture_ && startupExit->hold && !tray_ && !reminders_, "partial_startup_isolated");
            ++startupExit->invocations; startupExit->firstQuit = now;
            invokeProblemUi(button);
            requireProblemUi(exitRequested_ && !exitWorkDrained() && !shuttingDown_, "first_quit_held");
            std::fputs("STARTUP_EXIT first_quit=1 held=1\n", stderr); std::fflush(stderr);
        } else if (!startupExit->released) {
            requireProblemUi(!exitWorkDrained() && !shuttingDown_, "held_worker_keeps_window");
            ++startupExit->heldTicks;
            if (now - startupExit->firstQuit >= 500 && startupExit->heldTicks >= 2) {
                requireProblemUi(SetEvent(startupExit->hold->release.get()) != FALSE, "release_startup_worker");
                startupExit->released = true;
            }
        } else if (now - startupExit->firstQuit >= 3000) {
            throw std::runtime_error("startup_exit_not_drained");
        }
    } catch (...) {
        startupExit->failed = true;
        std::fputs("STARTUP_EXIT failure=1 rescue_quit=1\n", stderr); std::fflush(stderr);
        if (startupExit->hold) SetEvent(startupExit->hold->release.get());
        // A rescue can close a broken derivative but can never produce PASS.
        ++startupExit->invocations; requestExit();
    }
});
window_.Closed([this, startupExit](auto const&, auto const&) {
    startupExit->observer.Stop();
    if (startupExit->hold) SetEvent(startupExit->hold->release.get());
    const bool workerReleased = startupExit->hold && startupExit->hold->released.load();
    const bool noFiles = !std::filesystem::exists(startupExit->root);
    problemUiResult = !startupExit->failed && startupExit->invocations == 1 &&
        startupExit->heldTicks >= 2 && startupExit->released && workerReleased &&
        exitWorkDrained() && noFiles ? 73 : 3;
    std::fprintf(stderr, "STARTUP_EXIT terminal=1 invocations=%u held_ticks=%u worker_released=%u drained=%u no_files=%u exit=%d\n",
        startupExit->invocations, startupExit->heldTicks, unsigned(workerReleased), unsigned(exitWorkDrained()),
        unsigned(noFiles), problemUiResult);
    std::fflush(stderr);
});
startupExit->observer.Start();
