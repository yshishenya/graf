using namespace graf::windows;
using namespace graf::windows::testing;
using namespace winrt::Microsoft::UI::Xaml;
auto state = std::make_shared<SettingsAccountAbcState>();
Resources().MergedDictionaries().Append(XamlControlsResources());
shellIsDark_ = false; refreshShellPalette(false);
window_ = Window(); window_.Title(L"GRAF — sequential synthetic account check");
root_ = Controls::Grid(); root_.RequestedTheme(ElementTheme::Light);
buildShell();
recordButton_.IsEnabled(false); compactRecordButton_.IsEnabled(false);
problemStore_ = NotificationPreferenceStore{};
capture_ = std::make_unique<NativeCapture>(state->root, AecSelection{std::make_shared<ProblemUiAec>(), false},
    [state](const auto& config, const auto& request) { return state->account(config, request); },
    [state](const auto&, const auto&) -> DesktopHttpTransport::ProtectedUploadResponse {
        ++state->unexpectedNative; state->failed.store(true); return {403, {}};
    });
reminders_ = std::make_unique<MeetingReminderPresenter>(capture_->notificationCard(), NotificationPreferenceStore{});
const auto gate = [this] { return WebView2AccountStorageFixture::read(cabinet_->webView()); };
// Explicit R2 wiring; one derivative-only call precedes the original recreate attach.
settingsAccountAbcObserver = [state, gate](auto const& control) {
    try {
        requireProblemUi(!state->closing && !state->failed.load(), "abc_observer_live");
        state->observe(control, gate);
    } catch (...) {
        state->failed.store(true); state->unknown.store(true);
        throw; // Abort recreate before product attach; timer closes/retains safely.
    }
};
state->observe(webView_, gate);
receiveAuthSession(SettingsAccountAbcState::token, true);
const auto closeFixture = [this, state] {
    if (state->closing) return;
    state->closing = true; state->closingAt = GetTickCount64();
    try { if (cabinet_) cabinet_->webView().close(); } catch (...) { state->unknown.store(true); }
    try { if (capture_) capture_->shutdown(); } catch (...) { state->unknown.store(true); }
};
stateTimer_ = root_.DispatcherQueue().CreateTimer();
stateTimer_.Interval(std::chrono::milliseconds(50)); stateTimer_.IsRepeating(true);
stateTimer_.Tick([this, state, gate, closeFixture](auto const&, auto const&) {
    try {
        if (state->finished) return;
        if (GetTickCount64() - state->began >= 280000) { state->failed.store(true); closeFixture(); }
        if (!state->closing) {
            if (state->failed.load() || std::filesystem::exists(state->stage / L"close.request")) {
                state->failed.store(true); closeFixture(); return;
            }
            if (!state->loaded) return;
            NativeCaptureStorageTestPeer::pollAccount(*capture_);
            if (state->attached && cabinet_->webView().runtimeState() == WebRuntimeState::unavailable) {
                std::fprintf(stderr, "T088_ABC host_unavailable site=pre-bind state=%u elapsed_ms=%llu detail=%s\n",
                    static_cast<unsigned>(cabinet_->webView().runtimeState()),
                    static_cast<unsigned long long>(GetTickCount64() - state->began), cabinet_->webView().failureDetail().c_str());
                std::fflush(stderr);
            }
            if (state->attached)
                requireProblemUi(cabinet_->webView().runtimeState() != WebRuntimeState::unavailable, "abc_host_available");
            if (!state->matches(capture_->currentAccount())) return;
            if (!state->attached) {
                configureCabinet(); bindNotificationContext();
                requireProblemUi(cabinet_->webView().routePolicy().trustedOrigin() == SettingsAccountAbcState::origin,
                    "abc_fixed_product_origin");
                requireProblemUi(cabinet_->openCabinet().decision == RouteDecision::allow, "abc_initial_cabinet_route");
                cabinet_->attach(webView_); state->attached = true;
            } else bindNotificationContext();
            if (cabinet_->webView().runtimeState() == WebRuntimeState::unavailable) {
                std::fprintf(stderr, "T088_ABC host_unavailable site=post-bind state=%u elapsed_ms=%llu detail=%s\n",
                    static_cast<unsigned>(cabinet_->webView().runtimeState()),
                    static_cast<unsigned long long>(GetTickCount64() - state->began), cabinet_->webView().failureDetail().c_str());
                std::fflush(stderr);
            }
            requireProblemUi(cabinet_->webView().runtimeState() != WebRuntimeState::unavailable, "abc_host_available");
            const auto slot = state->target.load();
            if (!state->inspected[slot] || state->scripts.load() ||
                NativeCaptureStorageTestPeer::accountPending(*capture_) ||
                cabinet_->webView().runtimeState() != WebRuntimeState::ready) return;
            if (!state->settled[slot]) {
                if (GetTickCount64() - state->completedAt[slot] >= 200) {
                    const auto current = state->controls[slot].get();
                    requireProblemUi(bool(current) && current.CoreWebView2(), "abc_live_current_control");
                    state->script(current.CoreWebView2(), slot, false);
                }
                return;
            }
            if (slot > 0 && !state->cookieInspected[slot]) {
                if (!state->cookieStarted[slot]) {
                    const auto current = state->controls[slot].get();
                    requireProblemUi(bool(current) && current.CoreWebView2(), "abc_cookie_live_current_control");
                    state->readCookie(current.CoreWebView2(), slot);
                }
                return;
            }
            if (state->cookieReads.load()) return;
            const auto s = gate();
            requireProblemUi(!s.pending && !s.inFlight && !s.failed && s.requested == slot && s.running == slot,
                "abc_sequential_drain_before_next_account");
            if (slot < 2) {
                state->target.store(slot + 1);
                std::fprintf(stderr, "T088_ABC requesting=%u previous_drained=1 native_calls=%u\n", slot + 1, state->nativeCalls.load());
                // Same cookie, changed native-confirmed user/workspace; no DOM identity.
                receiveAuthSession(SettingsAccountAbcState::token, true);
            } else closeFixture();
        }
        if (!state->closing) return;
        NativeCaptureStorageTestPeer::pollAccount(*capture_);
        if (GetTickCount64() - state->closingAt < 12000 &&
            (!state->processStopped() || state->scripts.load() || state->cookieReads.load() || NativeCaptureStorageTestPeer::accountPending(*capture_))) return;
        const bool drained = state->processStopped() && !state->scripts.load() && !state->cookieReads.load() &&
            !NativeCaptureStorageTestPeer::accountPending(*capture_);
        if (!drained) state->unknown.store(true);
        bool cleaned = false;
        try { if (drained) cleaned = state->cleanupOwnedProfile(); }
        catch (...) { state->unknown.store(true); }
        if (!cleaned) state->unknown.store(true);
        const bool passed = !state->failed.load() && !state->unknown.load() && cleaned &&
            state->watched == 3 && state->cores == 3 && state->allowed == 3 &&
            state->settled[0] && state->settled[1] && state->settled[2] &&
            state->cookieInspected[1] && state->cookieInspected[2] && !state->cookieReads.load() &&
            state->unexpectedNative.load() == 0 &&
            SettingsAccountAbcState::absent(state->root);
        problemUiResult = passed ? 73 : 3;
        std::fprintf(stderr, "T088_ABC terminal=1 sequential_only=1 cores=%u allowed=%u denied=%u native_calls=%u unexpected_native=%u browser_stopped=%u scripts_drained=%u cookies_drained=%u cookies_b_c=%u owned_udf_cleaned=%u retained=%u unknown=%u full_product_acceptance=0 exit=%d\n",
            state->cores, state->allowed, state->denied, state->nativeCalls.load(), state->unexpectedNative.load(),
            unsigned(state->processStopped()), unsigned(!state->scripts.load()), unsigned(!state->cookieReads.load()),
            unsigned(state->cookieInspected[1] && state->cookieInspected[2]), unsigned(cleaned),
            unsigned(state->owned), unsigned(state->unknown.load()), problemUiResult);
        std::fflush(stderr);
        settingsAccountAbcObserver = {};
        state->finished = true; stateTimer_.Stop(); window_.Close(); Exit();
    } catch (...) { state->failed.store(true); state->unknown.store(true); closeFixture(); }
});
root_.Loaded([state](auto const&, auto const&) { state->loaded = true; });
window_.AppWindow().Closing([state, closeFixture](auto const&, auto const& event) {
    if (state->finished) return;
    event.Cancel(true); state->failed.store(true); closeFixture();
});
window_.Activate(); resizeWindowLogical(window_, 1080, 620, true); stateTimer_.Start();
