// Derivative OnLaunched only. Real shell/refresh/AX, synthetic last-query and
// session UI inputs. No audio devices, writer, account, WebView Core or TLS.
using namespace graf::windows;
using namespace graf::windows::testing;
using namespace winrt::Microsoft::UI::Xaml::Automation;
struct StorageUiCase {
    const char* label;
    SessionState state;
    bool complete;
    unsigned pressure;
    const wchar_t* expected;
    bool expanded;
    unsigned action = 0; // 1: real collapse button; 2: real compact attention.
    CustodyFileError error = CustodyFileError::none;
    std::uint32_t nativeError = 0;
    bool privacyPending = false, privacyError = false;
};
struct StorageUiRun {
    std::filesystem::path parent, root;
    winrt::file_handle parentHandle;
    winrt::Windows::Foundation::IInspectable focused{nullptr};
    std::vector<StorageUiCase> cases;
    std::size_t next = 0, passed = 0, baseline = CustodyOwnedMemory::usedBytes();
    ULONGLONG began = GetTickCount64(), closingAt = 0;
    bool loaded = false, started = false, observing = false, closing = false, finished = false;
    std::atomic<bool> failed{false};
    bool manualGate = false, automaticGate = false;
};
auto state = std::make_shared<StorageUiRun>();
const auto idle = L"Микрофон не найден или недоступен"; // No device probe/ready injection.
const auto pending = L"Микрофон не найден или недоступен\nПроверяем место на диске…";
const auto warning = L"Микрофон не найден или недоступен\nМало места для локальных записей. Проверьте свободное место на диске";
const auto recording = L"Общий системный звук и локальный микрофон";
const auto recordingWarning = L"Общий системный звук и локальный микрофон\nМало места для локальных записей. Проверьте свободное место на диске";
const auto paused = L"Микрофон на паузе. Системный звук продолжает записываться.";
const auto pausedWarning = L"Микрофон на паузе. Системный звук продолжает записываться.\nМало места для локальных записей. Проверьте свободное место на диске";
state->cases = {
    {"idle_pending", SessionState::idle, false, 0, pending, true},
    {"idle_79", SessionState::idle, true, 79, idle, false},
    {"idle_80", SessionState::idle, true, 80, warning, true},
    {"idle_95", SessionState::idle, true, 95, warning, true},
    {"idle_recovered", SessionState::idle, true, 79, idle, false},
    {"idle_disk_full", SessionState::idle, true, 0,
        L"Микрофон не найден или недоступен\nПри последней проверке было недостаточно места для сохранения. Проверьте свободное место на диске",
        true, 0, CustodyFileError::ioFailed, ERROR_DISK_FULL},
    {"idle_query_error", SessionState::idle, true, 0,
        L"Микрофон не найден или недоступен\nНе удалось проверить место на диске",
        true, 0, CustodyFileError::ioFailed, ERROR_ACCESS_DENIED},
    {"idle_error_recovered", SessionState::idle, true, 79, idle, false},
    {"attention_80", SessionState::idle, true, 80, warning, true},
    {"actual_manual_collapse", SessionState::idle, true, 80, warning, false, 1},
    {"dismissal_survives_refresh", SessionState::idle, true, 80, warning, false},
    {"actual_attention_reopen", SessionState::idle, true, 80, warning, true, 2},
    {"collapse_again", SessionState::idle, true, 80, warning, false, 1},
    {"dismissal_clears_below_80", SessionState::idle, true, 79, idle, false},
    {"new_attention_after_recovery", SessionState::idle, true, 80, warning, true},
    {"recording_79", SessionState::recording, true, 79, recording, false},
    {"recording_80", SessionState::recording, true, 80, recordingWarning, true},
    {"recording_recovered", SessionState::recording, true, 79, recording, false},
    {"paused_80", SessionState::paused, true, 80, pausedWarning, true},
    {"paused_recovered", SessionState::paused, true, 79, paused, false},
    {"privacy_pending_priority", SessionState::recording, true, 80,
        L"Сохраняем изменение записи микрофона…", true, 0, CustodyFileError::none, 0, true},
    {"privacy_error_priority", SessionState::recording, true, 80,
        L"Не удалось изменить паузу микрофона. Проверьте состояние записи и повторите действие.",
        true, 0, CustodyFileError::none, 0, false, true},
    {"privacy_cleared", SessionState::recording, true, 80, recordingWarning, true},
    {"microphone_loss_priority", SessionState::degraded, true, 80,
        L"Микрофон отключён. Продолжается только системный звук. Запись будет сохранена с ограничением.", true},
    {"write_failure_display_priority", SessionState::failed, true, 80, idle, true}
};
GUID id{}; requireProblemUi(CoCreateGuid(&id) == S_OK, "storage_ui_guid");
wchar_t leaf[40]{}; requireProblemUi(StringFromGUID2(id, leaf, 40) != 0, "storage_ui_leaf");
const auto temporary = std::filesystem::temp_directory_path();
wchar_t expandedTemporary[32768]{};
const auto temporaryLength = GetLongPathNameW(temporary.c_str(), expandedTemporary, 32768);
requireProblemUi(temporaryLength && temporaryLength < 32768, "storage_ui_long_temp_namespace");
state->parent = std::filesystem::path(expandedTemporary) / (std::wstring(L"graf-storage-ui-") + leaf);
state->root = state->parent / L"recordings";
requireProblemUi(CreateDirectoryW(state->parent.c_str(), nullptr) != FALSE, "storage_ui_exclusive_parent");
state->parentHandle.attach(CreateFileW(state->parent.c_str(), FILE_READ_ATTRIBUTES,
    FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING,
    FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
FILE_ATTRIBUTE_TAG_INFO attributes{};
requireProblemUi(state->parentHandle && GetFileInformationByHandleEx(state->parentHandle.get(),
    FileAttributeTagInfo, &attributes, sizeof(attributes)) &&
    !(attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) && !std::filesystem::exists(state->root),
    "storage_ui_private_absent_root");
// Retain this small generated store, including on unknown termination. No delete
// API or user profile cleanup is part of this diagnostic.
std::fprintf(stderr, "STORAGE_UI owned_leaf=%s scratch_retained=1\n",
    winrt::to_string(state->parent.filename().native()).c_str());
Resources().MergedDictionaries().Append(XamlControlsResources());
shellIsDark_ = false; announcedAppearance_ = "light"; shellHighContrast_ = shellHighContrast();
refreshShellPalette(false);
window_ = Window(); window_.Title(L"GRAF — synthetic storage warning UI check");
root_ = Grid(); root_.RequestedTheme(ElementTheme::Light);
buildShell();
// The native shell is real. Remove the unloaded browser before activation;
// no Core/profile/environment is created for an unrelated storage UI test.
requireProblemUi(!webView_.CoreWebView2(), "storage_ui_no_core");
std::uint32_t browserIndex = 0;
requireProblemUi(meetingsSurface_.Children().IndexOf(webView_, browserIndex), "storage_ui_unloaded_browser");
meetingsSurface_.Children().RemoveAt(browserIndex); webView_.Close(); webView_ = nullptr;
problemStore_ = NotificationPreferenceStore{};
capture_ = std::make_unique<NativeCapture>(state->root, AecSelection{std::make_shared<ProblemUiAec>(), false},
    [state](const auto&, const auto&) -> DesktopHttpTransport::UploadResponse {
        state->failed = true; throw std::runtime_error("storage_ui_unexpected_http");
    }, [state](const auto&, const auto&) -> DesktopHttpTransport::ProtectedUploadResponse {
        state->failed = true; throw std::runtime_error("storage_ui_unexpected_protected_http");
    });
const auto beginClose = [this, state] {
    if (state->closing) return;
    state->closing = true; state->closingAt = GetTickCount64();
    shuttingDown_ = true;
    capture_->shutdown(); // Real worker/handle completion is still required.
};
window_.AppWindow().Closing([state, beginClose](auto const&, auto const& args) {
    if (!state->finished) { args.Cancel(true); state->failed = true; beginClose(); }
});
root_.Loaded([this, state](auto const&, auto const&) {
    state->loaded = true; mainWindowHandle_ = nativeWindowHandle(window_);
});
stateTimer_ = root_.DispatcherQueue().CreateTimer();
stateTimer_.Interval(std::chrono::milliseconds(25)); stateTimer_.IsRepeating(true);
stateTimer_.Tick([this, state, beginClose](auto const&, auto const&) {
    try {
        if (state->finished) return;
        if (GetTickCount64() - state->began >= 180000) { state->failed = true; beginClose(); }
        if (state->closing) {
            capture_->pollHealth(); capture_->pollUploads();
            if (!capture_->shutdownWorkDrained()) {
                if (GetTickCount64() - state->closingAt >= 10000) {
                    std::fputs("STORAGE_UI terminal=UNKNOWN drained=0 scratch_retained=1\n", stderr);
                    std::fflush(stderr); TerminateProcess(GetCurrentProcess(), 2);
                }
                return;
            }
            requireProblemUi(NativeCaptureStorageTestPeer::storageUiNoCaptureOrNetwork(*capture_) &&
                CaptureSessionTestPeer::storageUiDeviceFree(NativeCaptureStorageTestPeer::controller(*capture_)) &&
                !capture_->finalization().savedLocal, "storage_ui_terminal_no_capture_or_saved_claim");
            capture_.reset(); tray_.reset(); state->parentHandle.close();
            requireProblemUi(CustodyOwnedMemory::usedBytes() == state->baseline, "storage_ui_charged_memory_released");
            state->finished = true; stateTimer_.Stop();
            problemUiResult = !state->failed && state->passed == state->cases.size() ? 73 : 2;
            std::fprintf(stderr, "STORAGE_UI terminal=%s cases=%zu/%zu drained=1 scratch_retained=1 installed=0 actual_audio=0 permission_denied=NOT_RUN\n",
                problemUiResult == 73 ? "PASS" : "FAIL", state->passed, state->cases.size());
            std::fflush(stderr);
            if (indicatorWindow_) indicatorWindow_.Close();
            window_.Close(); Application::Current().Exit(); return;
        }
        if (state->failed) { beginClose(); return; }
        if (!state->loaded) return;
        if (!state->started) {
            requireProblemUi(mainWindowHandle_ != nullptr, "storage_ui_hwnd");
            tray_ = std::make_unique<WindowsTray>(reinterpret_cast<std::uintptr_t>(mainWindowHandle_),
                [] {}, [] {}, [] {});
            requireProblemUi(tray_->available(), "storage_ui_actual_tray_required");
            requireProblemUi(ensureRecordingIndicator(false), "storage_ui_prepare_indicator_hidden");
            capture_->refreshPermission();
            requireProblemUi(capture_->microphonePermissionGranted(), "storage_ui_BLOCKED_actual_microphone_permission");
            capture_->startStorageValidation(); state->started = true; return;
        }
        capture_->pollUploads(); // Genuine empty owner/queue adoption, never fabricated READY/context.
        if (state->next == 0 && !state->observing && !NativeCaptureStorageTestPeer::storageUiReady(*capture_)) return;
        requireProblemUi(tray_ && tray_->available() && !cabinet_ && !webView_ &&
            NativeCaptureStorageTestPeer::storageUiNoCaptureOrNetwork(*capture_) &&
            CaptureSessionTestPeer::storageUiDeviceFree(NativeCaptureStorageTestPeer::controller(*capture_)),
            "storage_ui_no_unrelated_work");
        const auto& test = state->cases.at(state->next);
        if (!state->observing) {
            CaptureSessionTestPeer::storageUiState(NativeCaptureStorageTestPeer::controller(*capture_), test.state);
            CaptureSessionTestPeer::storageUiPrivacy(NativeCaptureStorageTestPeer::controller(*capture_),
                test.privacyPending, test.privacyError);
            state->manualGate = canStartRecording(); state->automaticGate = automaticPrerequisites().allowsStart();
            requireProblemUi(backButton_.Focus(FocusState::Programmatic), "storage_ui_focus_control");
            state->focused = Input::FocusManager::GetFocusedElement(root_.XamlRoot());
            requireProblemUi(bool(state->focused), "storage_ui_actual_focus");
            NativeCaptureStorageTestPeer::storageUiObservation(*capture_, test.complete, test.pressure, test.error, test.nativeError);
            if (test.action == 1) invokeProblemUi(expandedInspectorToggle_);
            if (test.action == 2) invokeProblemUi(compactAttentionButton_);
            // Isolate this UI projection from unrelated scheduler/device probes.
            // No claim about production observation cadence is made here.
            const auto now = GetTickCount64();
            lastStateTick_ = lastUploadRecovery_ = lastLocalPurge_ = lastReadinessCheck_ = now;
            lastDetectionRequest_ = DetectionClock::now();
            refreshNativeState(); root_.UpdateLayout();
            requireProblemUi(capture_->microphonePermissionGranted(), "storage_ui_permission_remains_actual");
            requireProblemUi(canStartRecording() == state->manualGate &&
                automaticPrerequisites().allowsStart() == state->automaticGate,
                "storage_ui_warning_does_not_change_start_gates");
            state->observing = true; return; // Observe on a later dispatcher tick after layout.
        }
        root_.UpdateLayout();
        requireProblemUi(std::wstring(readinessText_.Text().c_str()) == test.expected, "storage_ui_exact_visible_text");
        const auto textPeer = Peers::TextBlockAutomationPeer(readinessText_);
        requireProblemUi(std::wstring(textPeer.GetName().c_str()) == test.expected, "storage_ui_actual_peer_name");
        requireProblemUi((expandedInspector_.Visibility() == Visibility::Visible) == test.expanded &&
            (compactInspector_.Visibility() == Visibility::Visible) != test.expanded &&
            inspectorColumn_.Width().Value == (test.expanded ? 308.0 : 52.0), "storage_ui_disclosure_layout");
        const auto bounds = textPeer.GetBoundingRectangle();
        requireProblemUi(test.expanded ? (!textPeer.IsOffscreen() && bounds.Width > 0 && bounds.Height > 0) :
            textPeer.IsOffscreen(), "storage_ui_actual_text_visibility");
        requireProblemUi(Input::FocusManager::GetFocusedElement(root_.XamlRoot()) == state->focused &&
            !permissionDialogOpen_ && !localActionDialogOpen_ && !problemUiDialog(root_), "storage_ui_focus_no_modal");
        const bool active = test.state == SessionState::recording || test.state == SessionState::paused || test.state == SessionState::degraded;
        requireProblemUi((recordingStrip_.Visibility() == Visibility::Visible) == active &&
            (stopButton_.Visibility() == Visibility::Visible) == active &&
            recordButton_.IsEnabled() == state->manualGate && compactRecordButton_.IsEnabled() == state->manualGate,
            "storage_ui_existing_controls");
        if (active) {
            requireProblemUi(recordingIndicatorAvailable() && indicatorStop_.IsEnabled() &&
                recordingStripStop_.IsEnabled() && stopButton_.IsEnabled(), "storage_ui_active_stop_preserved");
            for (const auto& button : {recordingStripStop_, indicatorStop_, stopButton_}) {
                const auto peer = Peers::ButtonAutomationPeer(button);
                requireProblemUi(!peer.GetName().empty() && bool(peer.GetPattern(Peers::PatternInterface::Invoke)
                    .try_as<Provider::IInvokeProvider>()), "storage_ui_actual_stop_provider");
            }
        } else requireProblemUi(!indicatorWindow_.AppWindow().IsVisible(), "storage_ui_no_false_active_indicator");
        if (!test.expanded && test.complete && test.pressure >= 80)
            requireProblemUi(compactAttentionButton_.Visibility() == Visibility::Visible &&
                !Peers::ButtonAutomationPeer(compactAttentionButton_).IsOffscreen(), "storage_ui_compact_attention_visible");
        if (test.state == SessionState::failed)
            requireProblemUi(captureOutcomeText_.Text() == L"Не хватает места для записи. Освободите место на диске и повторите попытку." &&
                captureOutcomeText_.Visibility() == Visibility::Visible, "storage_ui_write_failure_display");
        requireProblemUi(capture_->custodyAttentionCount() == 0 && localActionNotice_.empty(),
            "storage_ui_no_other_custody_attention");
        std::fprintf(stderr, "STORAGE_UI case=%s PASS peer=1 focus_preserved=1 synthetic_state=1\n", test.label);
        std::fflush(stderr); ++state->passed; ++state->next; state->observing = false;
        if (state->next == state->cases.size()) beginClose();
    } catch (...) {
        state->failed = true;
        std::fprintf(stderr, "STORAGE_UI failure_at_case=%zu scratch_retained=1\n", state->next);
        std::fflush(stderr);
        if (state->closing) { TerminateProcess(GetCurrentProcess(), 2); return; }
        beginClose();
    }
});
resizeWindowLogical(window_, 1080, 900, true);
stateTimer_.Start(); window_.Activate();
