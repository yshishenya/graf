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
// Run on the actual OnLaunched stack before partial startup. No profile, real
// WebView, storage validation, device probes or network worker is started here.
{
    requireProblemUi(!capture_ && !cabinet_ && !attribution_ && !webViewAttached_ && !webView_ &&
        !std::filesystem::exists(shellClose->root), "shared_activation_prestartup_empty");
    {
        std::lock_guard<std::mutex> lock(activationMutex);
        requireProblemUi(!pendingActivation.closed && !pendingActivation.sharedRoute, "shared_activation_initial_empty");
    }
    const std::string workspace = "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF";
    const std::string version = "0123456789abcdef01234567";
    const auto publicA = "grafrec://shared-meeting?v=1&workspace_id=" + workspace +
        "&share_token=" + std::string(43, 'a') + "&tab=recording&position_ms=0014&media_version=" + version;
    const auto publicB = "grafrec://shared-meeting?v=1&workspace_id=" + workspace +
        "&share_token=" + std::string(43, 'b') + "&tab=outcomes";
    const auto routeA = WebViewRoutePolicy::sharedMeetingRoute(publicA);
    const auto routeB = WebViewRoutePolicy::sharedMeetingRoute(publicB);
    requireProblemUi(routeA && routeB &&
        *routeA == "/api/v1/cabinet/public-shares/" + std::string(43, 'a') +
            "?workspace_id=abcdefab-cdef-4abc-8def-abcdefabcdef&media_version=" + version + "#recording?position_ms=14" &&
        *routeB == "/api/v1/cabinet/public-shares/" + std::string(43, 'b') +
            "?workspace_id=abcdefab-cdef-4abc-8def-abcdefabcdef#outcomes", "shared_activation_generated_intents");
    const auto pending = [] {
        std::lock_guard<std::mutex> lock(activationMutex);
        return pendingActivation.sharedRoute;
    };
    const auto revision = [] {
        std::lock_guard<std::mutex> lock(activationMutex);
        return pendingActivation.sharedRevision;
    };
    requireProblemUi(receiveProtocolActivation("grafrec://attribution?utm_source=generated-shared-check"),
        "shared_activation_existing_attribution_received");
    requireProblemUi(receiveProtocolActivation(publicA) && receiveProtocolActivation(publicB),
        "shared_activation_latest_valid_received");
    const auto beforeInvalid = revision();
    requireProblemUi(!receiveProtocolActivation(publicA + "&next=/desktop/meetings") &&
        !receiveProtocolActivation(std::string(16385, 'x')) &&
        !receiveProtocolActivation(std::wstring(16385, L'x')) &&
        !receiveProtocolActivation(std::wstring(6000, L'\u4e00')) &&
        revision() == beforeInvalid && pending() == routeB, "shared_activation_invalid_preserves_latest");
    applyPendingActivation(false);
    requireProblemUi(!cabinet_ && pending() == routeB && attributionSignInRequested_,
        "shared_activation_cold_retained_before_cabinet");
    configureCabinet(); // Production helper applies before any attach/navigation startup.
    const auto origin = cabinet_->webView().routePolicy().trustedOrigin();
    requireProblemUi(cabinet_->webView().safeRecoveryUrl() == origin + *routeB &&
        !pending() && !attributionSignInRequested_ && !webViewAttached_ && !webView_ &&
        !cabinet_->webView().routePolicy().allowsNativeBridge(origin + *routeB) &&
        cabinet_->webView().currentUrl().empty() && cabinet_->webView().runtimeState() != WebRuntimeState::ready,
        "shared_activation_configure_adopts_reader_before_old_login_without_bridge");
    unsigned navigations = 0;
    bool injectNewer = false;
    cabinet_->webView().setNavigationHandler([&](RouteEvaluation evaluation) {
        requireProblemUi(evaluation.decision == RouteDecision::allow, "shared_activation_open_allowed");
        ++navigations;
        if (injectNewer) {
            injectNewer = false;
            requireProblemUi(receiveProtocolActivation(publicB), "shared_activation_B_during_open_A");
        }
    });
    applyPendingActivation(false);
    requireProblemUi(navigations == 0, "shared_activation_cold_ack_once");
    requireProblemUi(receiveProtocolActivation(publicA), "shared_activation_warm_A_received");
    injectNewer = true;
    applyPendingActivation(false);
    requireProblemUi(navigations == 1 && pending() == routeB &&
        cabinet_->webView().safeRecoveryUrl() == origin + *routeA, "shared_activation_old_ack_cannot_clear_new_B");
    applyPendingActivation(false);
    applyPendingActivation(false);
    requireProblemUi(navigations == 2 && !pending() && cabinet_->webView().safeRecoveryUrl() == origin + *routeB,
        "shared_activation_new_B_ack_exactly_once");
    requireProblemUi(receiveProtocolActivation(publicA), "shared_activation_before_replacement_checks");
    RouteEvaluation replacement;
    replacement.decision = RouteDecision::allow;
    replacement.kind = RouteKind::meetingDetail;
    handleCabinetNavigation(replacement);
    requireProblemUi(pending() == routeA, "shared_activation_automatic_callback_does_not_cancel");
    replacement.userInitiated = true;
    replacement.decision = RouteDecision::deny;
    handleCabinetNavigation(replacement);
    requireProblemUi(pending() == routeA, "shared_activation_denied_user_callback_does_not_cancel");
    replacement.decision = RouteDecision::allow;
    handleCabinetNavigation(replacement);
    requireProblemUi(!pending(), "shared_activation_accepted_user_callback_cancels");
    capture_ = std::make_unique<NativeCapture>(shellClose->root,
        AecSelection{std::make_shared<ProblemUiAec>(), false});
    capture_->setUpdateAdmissionBlocked(true);
    requireProblemUi(receiveProtocolActivation(publicA), "shared_activation_during_update_received");
    applyPendingActivation(false);
    requireProblemUi(navigations == 2 && pending() == routeA, "shared_activation_update_pause_retains");
    capture_->setUpdateAdmissionBlocked(false);
    applyPendingActivation(false);
    requireProblemUi(navigations == 3 && !pending(), "shared_activation_update_resume_ack");
    cabinet_->webView().close();
    requireProblemUi(receiveProtocolActivation(publicB), "shared_activation_closed_host_received");
    applyPendingActivation(false);
    requireProblemUi(navigations == 3 && pending() == routeB, "shared_activation_closed_host_not_ack");
    cabinet_.reset();
    configureCabinet();
    requireProblemUi(!pending() && cabinet_->webView().safeRecoveryUrl() == origin + *routeB,
        "shared_activation_reconfigured_host_ack");
    receiveAuthSession("generated-session-A", true);
    requireProblemUi(receiveProtocolActivation(publicA), "shared_activation_for_session_checks");
    const auto beforeRevalidation = revision();
    receiveAuthSession({}, false); // Unknown is not a logout.
    receiveAuthSession("generated-session-A", true); // Same cookie, fresh server revalidation.
    requireProblemUi(pending() == routeA && revision() == beforeRevalidation,
        "shared_activation_unknown_and_same_cookie_do_not_cancel");
    receiveAuthSession("generated-session-B", true);
    requireProblemUi(!pending(), "shared_activation_confirmed_token_change_cancels");
    requireProblemUi(receiveProtocolActivation(publicA), "shared_activation_before_logout");
    receiveAuthSession({}, true);
    requireProblemUi(!pending(), "shared_activation_confirmed_logout_cancels");
    requireProblemUi(receiveProtocolActivation(publicB), "shared_activation_new_public_after_logout");
    applyPendingActivation(false);
    requireProblemUi(!pending() && cabinet_->webView().safeRecoveryUrl() == origin + *routeB,
        "shared_activation_signed_out_public_allowed_without_authority");
    requireProblemUi(!NativeCaptureStorageTestPeer::accountPending(*capture_) &&
        capture_->indicator().state == SessionState::idle && !std::filesystem::exists(shellClose->root) &&
        !webView_ && !webViewAttached_ && !attribution_, "shared_activation_no_profile_root_web_or_account_worker");
    cabinet_.reset();
    capture_.reset();
    observedAuthGeneration_.reset();
    observedNetworkAccount_ = false;
    sharedActivationAccount_.reset();
    requireProblemUi(receiveProtocolActivation(publicA) && pending() == routeA,
        "shared_activation_pending_until_actual_shell_exit");
    window_.Closed([shellClose, publicA](auto const&, auto const&) {
        bool cancelled = false;
        {
            std::lock_guard<std::mutex> lock(activationMutex);
            cancelled = pendingActivation.closed && !pendingActivation.sharedRoute;
        }
        const bool rejected = !receiveProtocolActivation(publicA);
        if (!cancelled || !rejected) shellClose->failed = true;
        std::fprintf(stderr, "SHARED_ACTIVATION closed=1 cancelled=%u rejected_after_exit=%u\n",
            unsigned(cancelled), unsigned(rejected));
        std::fflush(stderr);
    });
    std::fputs("SHARED_ACTIVATION prephase=PASS native_webview=0 profile=0 root=0 account_worker=0\n", stderr);
    std::fflush(stderr);
}
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
