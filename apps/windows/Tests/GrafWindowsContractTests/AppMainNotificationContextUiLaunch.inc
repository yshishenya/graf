using namespace graf::windows;
using namespace graf::windows::testing;
auto state = std::make_shared<NotificationContextUiState>();
requireProblemUi(state->release && !std::filesystem::exists(state->root), "context_fresh_root");
Resources().MergedDictionaries().Append(XamlControlsResources());
window_ = Window(); window_.Title(L"GRAF — isolated notification context check");
root_ = Grid(); window_.Content(root_);
cabinet_ = std::make_unique<CabinetWindow>();
capture_ = std::make_unique<NativeCapture>(state->root, AecSelection{std::make_shared<ProblemUiAec>(), false},
    [state](const auto& config, const auto& request) { return state->account(config, request); },
    [](const auto&, const auto&) -> DesktopHttpTransport::ProtectedUploadResponse {
        requireProblemUi(false, "context_no_protected_http"); return {};
    });
reminders_ = std::make_unique<MeetingReminderPresenter>(capture_->notificationCard(), NotificationPreferenceStore{});
const auto read = [this] {
    WebView2Host::NativeSettingsRequest request;
    request.handler = std::string(NativeSettingsBridge::kNotificationSettingsHandler);
    request.notification = NativeSettingsBridge::NotificationRequest{};
    const auto reply = answerNativeSettings(request);
    const auto fields = DesktopApiClient::jsonObjectFields(reply);
    requireProblemUi(fields && fields->count("canEdit"), "context_typed_reply");
    const auto& value = fields->at("canEdit");
    requireProblemUi(value == "true" || value == "false", "context_boolean_reply");
    return value == "true";
};
WebView2SettingsContextFixture::observe(cabinet_->webView(), [this, state, read](std::string_view script) {
    requireProblemUi(script == "window.GRAFNotificationSettings?.refresh()", "context_refresh_api");
    requireProblemUi(++state->refreshes <= 3, "context_no_reentrant_refresh");
    state->lastCanEdit = read(); // Reenters the real bind after markers changed.
});
capture_->setAuthSessionToken("generated-context-token");
NativeCaptureStorageTestPeer::pollAccount(*capture_);
requireProblemUi(!read() && !capture_->currentAccount(), "context_initial_read_completed_false");
state->initialRefreshes = state->refreshes;
requireProblemUi(SetEvent(state->release.get()) != FALSE, "context_release_account");
const auto close = [this, state] {
    if (state->closing) return;
    state->closing = true;
    SetEvent(state->release.get());
    WebView2SettingsContextFixture::detach(cabinet_->webView());
    capture_->setAuthSessionToken({}, true);
    capture_->shutdown();
};
stateTimer_ = root_.DispatcherQueue().CreateTimer();
stateTimer_.Interval(std::chrono::milliseconds(20)); stateTimer_.IsRepeating(true);
stateTimer_.Tick([this, state, read, close](auto const&, auto const&) {
    try {
        NativeCaptureStorageTestPeer::pollAccount(*capture_);
        if (!state->closing) {
            requireProblemUi(GetTickCount64() - state->began < 10000, "context_ui_deadline");
            if (!capture_->currentAccount()) return;
            bindNotificationContext();
            requireProblemUi(state->refreshes == state->initialRefreshes + 1 && state->lastCanEdit,
                "context_confirmed_refresh");
            const auto confirmedRefreshes = state->refreshes;
            bindNotificationContext(); bindNotificationContext();
            requireProblemUi(state->refreshes == confirmedRefreshes, "context_unchanged_no_refresh");
            capture_->setAuthSessionToken({}, true);
            bindNotificationContext();
            requireProblemUi(state->refreshes == confirmedRefreshes + 1 && !state->lastCanEdit && !read(),
                "context_logout_refresh");
            bindNotificationContext();
            requireProblemUi(state->refreshes == confirmedRefreshes + 1, "context_logout_no_repeat");
            close();
        }
    } catch (...) { state->failed = true; close(); }
    if (!state->closing || NativeCaptureStorageTestPeer::accountPending(*capture_)) return;
    reminders_.reset(); capture_.reset(); cabinet_.reset();
    const bool noFiles = !std::filesystem::exists(state->root);
    problemUiResult = !state->failed && noFiles ? 73 : 3;
    std::fprintf(stderr, "CONTEXT_UI terminal=1 refreshes=%u initial=%u no_files=%u worker_drained=1 browser_started=0 exit=%d\n",
        state->refreshes, state->initialRefreshes, unsigned(noFiles), problemUiResult);
    std::fflush(stderr); state->finished = true; stateTimer_.Stop(); window_.Close(); Exit();
});
window_.AppWindow().Closing([state, close](auto const&, auto const& args) {
    if (state->finished) return;
    args.Cancel(true); state->failed = true; close();
});
window_.Activate(); resizeWindowLogical(window_, 480, 240, true); stateTimer_.Start();
