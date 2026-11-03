using namespace graf::windows;
using namespace graf::windows::testing;
using namespace winrt::Microsoft::Web::WebView2::Core;
auto state = std::make_shared<SettingsUiState>();
Resources().MergedDictionaries().Append(XamlControlsResources());
shellIsDark_ = false; refreshShellPalette(false);
window_ = Window(); window_.Title(L"GRAF — isolated native settings check");
root_ = Grid(); root_.RequestedTheme(ElementTheme::Light);
buildShell();
// This fixture cannot start recording; capture readiness is deliberately false.
recordButton_.IsEnabled(false); compactRecordButton_.IsEnabled(false);
problemStore_ = NotificationPreferenceStore{};
capture_ = std::make_unique<NativeCapture>(state->root, AecSelection{std::make_shared<ProblemUiAec>(), false},
    [state](const auto& config, const auto& request) { return state->account(config, request); },
    [](const auto&, const auto&) -> DesktopHttpTransport::ProtectedUploadResponse {
        requireProblemUi(false, "no_settings_protected_http"); return {};
    });
capture_->setAuthSessionToken("generated-settings-ui");
reminders_ = std::make_unique<MeetingReminderPresenter>(capture_->notificationCard());
const auto closeFixture = [this, state] {
    if (state->closing) return;
    state->closing = true; state->closingAt = GetTickCount64();
    if (cabinet_) cabinet_->webView().close();
    if (capture_) capture_->shutdown();
};
stateTimer_ = root_.DispatcherQueue().CreateTimer();
stateTimer_.Interval(std::chrono::milliseconds(100)); stateTimer_.IsRepeating(true);
stateTimer_.Tick([this, state, closeFixture](auto const&, auto const&) {
    try {
        if (state->finished) return;
        if (state->closing) {
            if (state->environment && !state->browserExited.load() && GetTickCount64() - state->closingAt < 10000) return;
            const bool browserStopped = !state->environment || state->browserExited.load();
            reminders_.reset(); tray_.reset(); capture_.reset();
            const bool cleaned = state->clearPreference();
            state->environment = nullptr; state->profilePin.close();
            std::error_code error;
            if (browserStopped) std::filesystem::remove_all(state->parent, error);
            const bool passed = !state->failed && browserStopped && cleaned && !error && state->sawQuiet && state->sawRestore &&
                state->sawPreview && state->returnedWhileQuiet && state->settingsLoads >= 2 && state->meetingsLoads >= 1;
            problemUiResult = passed ? 73 : 3;
            std::fprintf(stderr, "SETTINGS_UI terminal=1 quiet=%u restored=%u preview=%u settings_loads=%u meetings_loads=%u browser_stopped=%u registry_cleaned=%u profile_cleaned=%u exit=%d\n",
                unsigned(state->sawQuiet), unsigned(state->sawRestore), unsigned(state->sawPreview), state->settingsLoads,
                state->meetingsLoads, unsigned(browserStopped), unsigned(cleaned), unsigned(browserStopped && !error && !std::filesystem::exists(state->parent)), problemUiResult);
            std::fflush(stderr); state->finished = true; stateTimer_.Stop(); window_.Close(); Exit(); return;
        }
        requireProblemUi(!state->failed, "settings_async_failure");
        if (std::filesystem::exists(state->stage / "close.request")) { closeFixture(); return; }
        requireProblemUi(GetTickCount64() - state->began < 600000, "settings_ui_deadline");
        if (!state->loaded) return;
        NativeCaptureStorageTestPeer::pollAccount(*capture_);
        if (!capture_->currentAccount()) return;
        if (!state->initializing) {
            state->initializing = true;
            mainWindowHandle_ = nativeWindowHandle(window_);
            tray_ = std::make_unique<WindowsTray>(reinterpret_cast<std::uintptr_t>(mainWindowHandle_), [] {}, [] {}, [] {});
            requireProblemUi(tray_->available(), "settings_actual_tray");
            capture_->notificationCard().interactionPermitProvider = [this] { return interactionPermit(); };
            configureCabinet(); bindNotificationContext();
            const auto home = cabinet_->openCabinet();
            requireProblemUi(home.decision == RouteDecision::allow && home.kind == RouteKind::meetings &&
                home.normalizedUrl == state->origin + "/desktop/meetings", "settings_home_origin_binding");
            // A process failure ends this test; recreation must never select the installed profile.
            cabinet_->webView().setRecreateHandler([state, closeFixture] { state->failed = true; closeFixture(); });
            requireProblemUi(cabinet_->webView().routePolicy().trustedOrigin() == state->origin, "settings_test_origin_binding");
            (void)cabinet_->open(state->origin + "/desktop/settings/notifications");
            webView_.CoreWebView2Initialized([this, state](auto const& sender, auto const& event) {
                try {
                    requireProblemUi(SUCCEEDED(event.Exception()) && sender.CoreWebView2(), "settings_core");
                    const auto core = sender.CoreWebView2();
                    requireProblemUi(state->starts == 0 && state->profileMatches(core.Environment().UserDataFolder().c_str()), "settings_profile_before_navigation");
                    std::fputs("SETTINGS_UI profile_verified=1 starts_before_check=0\n", stderr); std::fflush(stderr);
                    core.NavigationStarting([state](auto const&, auto const& args) {
                        ++state->starts; state->completedAt = 0;
                        std::fprintf(stderr, "SETTINGS_UI navigation=%s redirected=%u\n", state->pageName(args.Uri().c_str()), unsigned(args.IsRedirected()));
                        std::fflush(stderr);
                    });
                    core.NavigationCompleted([state](auto const& view, auto const& completed) {
                        if (!completed.IsSuccess()) {
                            using Error = CoreWebView2WebErrorStatus;
                            const auto error = completed.WebErrorStatus();
                            const bool certificate = error == Error::CertificateCommonNameIsIncorrect ||
                                error == Error::CertificateExpired || error == Error::ClientCertificateContainsErrors ||
                                error == Error::CertificateRevoked || error == Error::CertificateIsInvalid;
                            std::fprintf(stderr, "SETTINGS_UI tls_rejected=%u web_error=%d page=%s\n", unsigned(certificate), int(error), state->pageName(view.Source().c_str()));
                            std::fflush(stderr); return;
                        }
                        state->completedAt = GetTickCount64();
                        const auto url = view.Source();
                        if (url == winrt::to_hstring(state->origin + "/desktop/settings/notifications")) {
                            ++state->settingsLoads;
                            const bool quiet = NotificationPreferenceStore::native().load(state->owner).quiet;
                            state->returnedWhileQuiet = state->returnedWhileQuiet || (state->meetingsAfterQuiet && quiet);
                            std::fprintf(stderr, "SETTINGS_UI page=settings native_quiet=%u returned_quiet=%u\n", unsigned(quiet), unsigned(state->returnedWhileQuiet));
                        }
                        if (url == winrt::to_hstring(state->origin + "/desktop/meetings")) {
                            ++state->meetingsLoads;
                            state->meetingsAfterQuiet = state->sawQuiet && !state->sawRestore;
                            std::fputs("SETTINGS_UI page=meetings\n", stderr);
                        }
                        std::fflush(stderr);
                    });
                    core.WebResourceResponseReceived([this, state](auto const&, auto const& args) {
                        try {
                            const auto request = args.Request();
                            if (std::string_view(state->pageName(request.Uri().c_str())) == "other") return;
                            const auto headers = request.Headers();
                            const auto response = args.Response();
                            const auto responseHeaders = response.Headers();
                            const bool tag = headers.Contains(L"X-GRAF-Desktop-Navigation");
                            const auto generation = cabinet_->webView().documentGeneration();
                            std::fprintf(stderr, "SETTINGS_UI response=1 get=%u status=%d html=%u dest_present=%u dest=%u mode_present=%u mode=%u tag=%u tag_current=%u generation=%llu elapsed_ms=%llu after_completion_ms=%lld\n",
                                unsigned(request.Method() == L"GET"), response.StatusCode(),
                                unsigned(responseHeaders.Contains(L"Content-Type") && responseHeaders.GetHeader(L"Content-Type") == L"text/html; charset=utf-8"),
                                unsigned(headers.Contains(L"Sec-Fetch-Dest")), unsigned(headers.Contains(L"Sec-Fetch-Dest") && headers.GetHeader(L"Sec-Fetch-Dest") == L"document"),
                                unsigned(headers.Contains(L"Sec-Fetch-Mode")), unsigned(headers.Contains(L"Sec-Fetch-Mode") && headers.GetHeader(L"Sec-Fetch-Mode") == L"navigate"), unsigned(tag),
                                unsigned(tag && headers.GetHeader(L"X-GRAF-Desktop-Navigation") == winrt::to_hstring(std::to_string(generation))),
                                static_cast<unsigned long long>(generation), GetTickCount64() - state->began,
                                state->completedAt ? static_cast<long long>(GetTickCount64() - state->completedAt) : -1LL);
                            std::fflush(stderr);
                        } catch (...) { std::fputs("SETTINGS_UI metadata_observer_failed=1\n", stderr); std::fflush(stderr); }
                    });
                    core.AddWebResourceRequestedFilter(L"*", CoreWebView2WebResourceContext::All, CoreWebView2WebResourceRequestSourceKinds::All);
                    core.WebResourceRequested([state](auto const& view, auto const& args) {
                        if (args.Response()) return;
                        const std::wstring url(args.Request().Uri());
                        const auto origin = winrt::to_hstring(state->origin);
                        if (!state->closing && url.rfind(origin.c_str(), 0) == 0 && url.size() > origin.size() &&
                            url[origin.size()] == L'/' && args.Request().Method() == L"GET") {
                            auto path = url.substr(origin.size());
                            path.resize(path.find(L'?') == std::wstring::npos ? path.size() : path.find(L'?'));
                            const bool allowed = path == L"/desktop/settings" || state->resources.count(path);
                            if (args.ResourceContext() == CoreWebView2WebResourceContext::Document) {
                                std::fprintf(stderr, "SETTINGS_UI document=%s allowed=%u path_sha256=%s\n", state->pageName(url), unsigned(allowed), sha256(winrt::to_string(path)).c_str());
                                std::fflush(stderr);
                            }
                            if (allowed) return; // Real HTTPS; the production tagger runs next.
                        }
                        args.Response(view.Environment().CreateWebResourceResponse(nullptr, 403, L"Loopback fixture only", L"Content-Length: 0"));
                    });
                    core.PermissionRequested([](auto const&, auto const& args) { args.State(CoreWebView2PermissionState::Deny); });
                    const auto manager = core.CookieManager();
                    auto cookie = manager.CreateCookie(L"__Host-twobrain_rec_owner_session", L"generated-settings-ui", L"localhost", L"/");
                    cookie.IsSecure(true); cookie.IsHttpOnly(true); manager.AddOrUpdateCookie(cookie);
                } catch (...) { state->failed = true; try { sender.Close(); } catch (...) {} }
            });
            CoreWebView2EnvironmentOptions options; options.AdditionalBrowserArguments(L"--disable-background-networking --no-proxy-server");
            const auto dispatcher = root_.DispatcherQueue();
            CoreWebView2Environment::CreateWithOptionsAsync({}, state->profile.native(), options).Completed(
                [this, state, dispatcher](auto const& operation, auto const&) {
                    dispatcher.TryEnqueue([this, state, operation] {
                        try {
                            if (state->closing) return;
                            state->environment = operation.GetResults();
                            requireProblemUi(state->profileMatches(state->environment.UserDataFolder().c_str()), "settings_environment_profile");
                            state->environment.BrowserProcessExited([state](auto const&, auto const&) { state->browserExited.store(true); });
                            cabinet_->webView().attach(webView_, state->environment);
                            state->attached = true;
                        } catch (...) { state->failed = true; }
                    });
                });
        }
        if (state->attached && cabinet_->webView().runtimeState() == WebRuntimeState::unavailable) {
            std::fprintf(stderr, "SETTINGS_UI host_failure=%s\n", cabinet_->webView().failureDetail().c_str()); std::fflush(stderr);
            requireProblemUi(false, "settings_runtime_unavailable");
        }
        const auto store = NotificationPreferenceStore::native();
        const auto bytes = store.read(state->preferenceKey);
        const auto current = bytes.value_or("absent");
        if (current != state->observed) {
            const bool quiet = store.load(state->owner).quiet;
            state->sawQuiet = state->sawQuiet || quiet;
            state->sawRestore = state->sawRestore || state->sawQuiet && !quiet && bytes.has_value();
            state->observed = current;
            std::fprintf(stderr, "SETTINGS_UI native_read present=%u quiet=%u\n", unsigned(bytes.has_value()), unsigned(quiet)); std::fflush(stderr);
        }
        if (capture_->notificationCard().visible() && capture_->notificationCard().kind() == NoticeKind::preview) state->sawPreview = true;
    } catch (...) { state->failed = true; closeFixture(); }
});
root_.Loaded([state](auto const&, auto const&) { state->loaded = true; });
window_.AppWindow().Closing([state, closeFixture](auto const&, auto const& args) {
    if (state->finished) return;
    args.Cancel(true);
    closeFixture();
});
window_.Activate(); resizeWindowLogical(window_, 1080, 620, true); stateTimer_.Start();
