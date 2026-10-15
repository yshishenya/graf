// Body of the test-only OnLaunched adapter. The production problem methods
// below this body remain byte-identical, including their actual catch handlers.
using namespace graf::windows;
using namespace graf::windows::testing;
auto state = std::make_shared<ProblemUiState>();
Resources().MergedDictionaries().Append(XamlControlsResources());
shellIsDark_ = false;
refreshShellPalette(shellIsDark_); // The same production resources required by styleText/styledButton.
for (const auto& entry : shellPaletteEntries())
    requireProblemUi(Resources().HasKey(box_value(entry.key)) &&
        bool(Resources().Lookup(box_value(entry.key)).try_as<Media::Brush>()), "production_palette_ready");
window_ = Window(); window_.Title(L"GRAF synthetic problem UI test");
root_ = Grid(); root_.RequestedTheme(ElementTheme::Light); window_.Content(root_);
selectedRecordingPanel_ = ContentControl(); root_.Children().Append(selectedRecordingPanel_);
problemStore_ = state->store();
stateTimer_ = root_.DispatcherQueue().CreateTimer();
stateTimer_.IsRepeating(true); stateTimer_.Interval(std::chrono::milliseconds(20));
stateTimer_.Tick([this, state](auto const&, auto const&) {
    try {
        if (state->phase != 11 && state->phase != 12 && state->phase != 13)
            requireProblemUi(RecordingNoticePresenter::Clock::now() < state->deadline, "startup_deadline");
        if (state->phase == 0) {
            if (!state->loaded) return;
            if (!state->seed.valid()) { state->startSeed(); return; }
            if (state->seed.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
            state->seed.get();
            capture_ = std::make_unique<NativeCapture>(state->root, AecSelection{std::make_shared<ProblemUiAec>(), false},
                [state](const auto& config, const auto& request) { return state->account(config, request); });
            capture_->startStorageValidation(); state->phase = 1;
        } else if (state->phase == 1) {
            capture_->pollUploads(); // Startup ACK only, before any auth token.
            const auto observation = capture_->localObservation();
            if (!observation.value || !observation.complete) return;
            requireProblemUi(observation.value->items().size() == 2 && !capture_->localQueueComplete(), "adopted_closed_inventory");
            capture_->setAuthSessionToken("generated-problem-ui"); state->phase = 2;
        } else if (state->phase == 2) {
            NativeCaptureStorageTestPeer::pollAccount(*capture_); // No recovery/upload dispatch.
            if (!capture_->currentAccount()) return;
            requireProblemUi(state->loaded && state->accountCalls == 2, "loaded_real_resolver");
            mainWindowHandle_ = nativeWindowHandle(window_);
            requireProblemUi(mainWindowHandle_ != nullptr, "loaded_window_handle");
            tray_ = std::make_unique<WindowsTray>(reinterpret_cast<std::uintptr_t>(mainWindowHandle_), [] {}, [] {}, [] {});
            requireProblemUi(tray_->available(), "actual_tray_available");
            auto& card = capture_->notificationCard();
            card.setDarkTheme(false); // OS text scaling still uses the real read-only Windows setting.
            card.interactionPermitProvider = [this] { return interactionPermit(); };
            reminders_ = std::make_unique<MeetingReminderPresenter>(card, state->store());
            const auto context = capture_->localProblemContext();
            reminders_->bind(context.owner, context.workspace, context.origin);
            state->phase = 3;
        } else if (state->phase == 3) {
            using Clock = RecordingNoticePresenter::Clock;
            const auto now = Clock::now(); const auto context = capture_->localProblemContext();
            const auto permit = interactionPermit();
            requireProblemUi(permit.allowed && permit.epoch != 0, "actual_permit");
            ProblemTarget target{context, "waiting", "capture-problem:waiting", capture_->authGeneration(), reminders_->epoch(),
                permit.epoch, 1000, now + std::chrono::seconds(300)};
            requireProblemUi(problemActionCurrent(target), "positive_action_control");
            auto& card = capture_->notificationCard();
            for (const auto id : {"capture-problem:waiting", "capture-problem:retained"}) {
                requireProblemUi(problemStore_.claimProblem(context.origin, context.owner, context.workspace, id), "generated_claim");
                card.recordProblemHistory(id, target.expires);
            }
            const auto prepareSelection = [&] {
                pendingProblems_.push_back(target); presentedProblem_ = target; selectedRecording_ = target;
                selectedRecordingDisplayKey_ = "generated-selection";
                selectedRecordingPanel_.Content(box_value(L"Synthetic selected recording"));
                selectedRecordingPanel_.Visibility(Visibility::Visible);
            };
            const auto revokedSelection = [&] {
                return pendingProblems_.empty() && !presentedProblem_ && !selectedRecording_ && selectedRecordingDisplayKey_.empty() &&
                    !selectedRecordingPanel_.Content() && selectedRecordingPanel_.Visibility() == Visibility::Collapsed;
            };
            const auto pressure = [&] {
                requireProblemUi(problemActionCurrent(target), "positive_action_before_each_pressure");
                ProblemUiQuota quota;
                bool refused = false;
                try { (void)capture_->recordingProblems(2000); } catch (const std::bad_alloc&) { refused = true; }
                requireProblemUi(refused && !problemActionCurrent(target), "actual_quota_catch_action");
                reconcileRecordingProblems(); // Actual unchanged production function-try-block.
                const auto current = interactionPermit();
                requireProblemUi(current.allowed && current.epoch == permit.epoch && problemContextCurrent(target), "permit_context_not_the_failure");
            };
            unsigned invalidated = 0;
            NoticePresentationHooks hooks; hooks.onInvalidated = [&] { ++invalidated; };
            requireProblemUi(card.present({NoticeKind::problem, target.incidentId, L"Synthetic problem", L"Generated metadata only", {}},
                now, now + std::chrono::seconds(20), {}, {}, std::move(hooks)) && card.visible(), "actual_problem_show");
            prepareSelection();
            const auto preferences = state->preferences; const auto writes = state->writes; const auto history = card.history();
            const auto problemGeneration = card.generation();
            pressure(); // Reservation is released before inspecting or tearing down UI.
            requireProblemUi(revokedSelection() && !card.visible() && card.generation() != problemGeneration && invalidated == 1,
                "problem_ui_revoked");
            requireProblemUi(state->preferences == preferences && state->writes == writes && sameProblemUiHistory(card.history(), history),
                "problem_claims_history_preserved");
            requireProblemUi(problemActionCurrent(target), "action_restored_after_quota");
            for (const auto kind : {NoticeKind::meeting, NoticeKind::recordingPrompt}) {
                const auto stamp = Clock::now();
                const auto id = kind == NoticeKind::meeting ? "synthetic-meeting" : "synthetic-recording-prompt";
                requireProblemUi(card.present({kind, id, L"Synthetic notice", L"Generated metadata only", {}},
                    stamp, stamp + std::chrono::seconds(20)) && card.visible(), "actual_nonproblem_show");
                const auto generation = card.generation(); const auto deadline = card.deadline();
                unsigned shortShown = 0;
                // Native prompt show advances lastTick; never enqueue with its pre-show stamp.
                card.queueShortRecordingDiscarded(Clock::now(), [&] { ++shortShown; });
                const auto unchangedNotice = [&] {
                    return card.visible() && card.kind() == kind && card.id() == id &&
                        card.generation() == generation && card.deadline() == deadline &&
                        card.content().title == L"Synthetic notice" && card.content().body == L"Generated metadata only";
                };
                requireProblemUi(unchangedNotice() && shortShown == 0,
                    kind == NoticeKind::meeting ? "meeting_pre_pressure_control" : "prompt_pre_pressure_control");
                prepareSelection();
                const auto before = card.history();
                pressure();
                requireProblemUi(revokedSelection() && unchangedNotice() && shortShown == 0,
                    kind == NoticeKind::meeting ? "meeting_post_pressure_preserved" : "prompt_post_pressure_preserved");
                requireProblemUi(state->preferences == preferences && state->writes == writes && sameProblemUiHistory(card.history(), before),
                    "nonproblem_claims_history_preserved");
                card.dismiss();
                requireProblemUi(card.presentPendingShort(Clock::now()) && card.visible() && card.kind() == NoticeKind::shortRecording && shortShown == 1,
                    "pending_short_survives_quota_catch");
                card.dismiss();
            }
            state->phase = 4;
        } else if (state->phase == 4 || state->phase == 7) {
            if (state->phase == 7 && state->seed.valid()) {
                if (state->seed.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
                state->seed.get(); // First cancellation did not change protected bytes.
            }
            if (!state->selectionPrepared) {
                const auto context = capture_->localProblemContext();
                const auto permit = interactionPermit();
                ProblemTarget target{context, "waiting", "capture-problem:waiting", capture_->authGeneration(), reminders_->epoch(),
                    permit.epoch, 1000, RecordingNoticePresenter::Clock::now() + std::chrono::seconds(300)};
                requireProblemUi(problemActionCurrent(target) && !pendingLocalRemoval_ && !localActionDialogOpen_, "local_action_positive_target");
                openProblemRecording(target); // Once per case: later ticks wait for the real template/layout.
                state->beforeAction = capture_->localObservation().value;
                requireProblemUi(selectedRecordingPanel_.Visibility() == Visibility::Visible && selectedLocalRecordingId_ == "waiting" &&
                    selectedLocalRemovalAllowed(target, selectedRecordingRevision_, "waiting", state->beforeAction), "local_action_positive_admission");
                state->selectionPrepared = true; return;
            }
            const auto button = problemUiButton(selectedRecordingPanel_, L"Удалить локальную копию…");
            if (!button || !button.IsLoaded() || button.ActualWidth() <= 0 || button.ActualHeight() <= 0) return;
            requireProblemUi(button == selectedLocalRemovalButton_ && selectedRecording_ &&
                selectedLocalRemovalAllowed(*selectedRecording_, selectedRecordingRevision_, "waiting", state->beforeAction), "actual_selected_control");
            invokeProblemUi(button);
            requireProblemUi(!pendingLocalRemoval_, "click_did_not_admit_removal");
            state->selectionPrepared = false;
            state->phase = state->phase == 4 ? 5 : 8;
        } else if (state->phase == 5 || state->phase == 8) {
            for (const auto& popup : Media::VisualTreeHelper::GetOpenPopupsForXamlRoot(root_.XamlRoot())) {
                if (!popup.Child()) continue;
                if (auto dialog = problemUiDialog(popup.Child())) {
                    requireProblemUi(!state->dialog, "single_owned_dialog");
                    state->dialog = dialog;
                }
            }
            if (!state->dialog) return;
            requireProblemUi(localActionDialogOpen_ && !pendingLocalRemoval_, "click_opened_confirmation_only");
            const auto dialog = state->dialog;
            requireProblemUi(dialog.XamlRoot() == root_.XamlRoot() && unbox_value<hstring>(dialog.Title()) == L"Удалить локальную копию?" &&
                dialog.PrimaryButtonText() == L"Переместить в Корзину" && dialog.CloseButtonText() == L"Отмена" &&
                dialog.DefaultButton() == ContentDialogButton::Close, "actual_confirmation_content");
            const auto close = problemUiButton(dialog, L"Отмена");
            const auto primary = problemUiButton(dialog, L"Переместить в Корзину");
            if (!close || !primary) { state->dialog = nullptr; return; } // Wait for the actual template layout.
            dialog.PrimaryButtonClick([state](auto const&, auto const&) { ++state->primaryEvents; });
            dialog.Closed([state](auto const&, auto const&) { ++state->closedEvents; });
            if (state->positive) { invokeProblemUi(primary); state->phase = 14; }
            else if (state->phase == 5) { invokeProblemUi(close); state->phase = 6; }
            else {
                const auto target = *selectedRecording_;
                const auto revision = selectedRecordingRevision_;
                openProblemRecording(target); // Even the same explicit selection revokes the old confirmation.
                requireProblemUi(selectedRecordingRevision_ == revision + 1 && selectedLocalRemovalButton_.IsEnabled() &&
                    !nativeLocalRemovalContextCurrent(target, revision), "actual_reselection_revoked_dialog");
                invokeProblemUi(primary); state->phase = 9;
            }
        } else if (state->phase == 6 || state->phase == 9) {
            if (localActionDialogOpen_) return; // Wait for the production completion, not merely Closed.
            requireProblemUi(state->closedEvents == (state->phase == 6 ? 1U : 2U) &&
                state->primaryEvents == (state->phase == 6 ? 0U : 1U) && !pendingLocalRemoval_ &&
                capture_->localObservation().complete && capture_->localObservation().value == state->beforeAction,
                "cancel_or_stale_completion_without_admission");
            state->dialog = nullptr;
            state->startByteCheck(); state->phase = state->phase == 6 ? 7 : 10;
        } else if (state->phase == 10) {
            if (state->seed.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
            state->seed.get(); // Stale Primary also left the physical protected metadata unchanged.
            state->beforeAction.reset();
            state->positive = true; state->phase = 4; // Same real Button, now accept the current selection.
        } else if (state->phase == 14) {
            if (localActionDialogOpen_) return;
            requireProblemUi(state->closedEvents == 3 && state->primaryEvents == 2 && pendingLocalRemoval_, "positive_native_admission");
            if (!state->removalTicket) state->removalTicket = pendingLocalRemoval_->ticket;
            requireProblemUi(state->removalTicket == pendingLocalRemoval_->ticket &&
                std::holds_alternative<ProblemTarget>(pendingLocalRemoval_->source), "single_native_removal_ticket");
            capture_->pollUploads(); // Existing owner executes intent, Shell recycle and adopted ACK.
            const auto observation = capture_->localObservation();
            if (observation.complete && observation.value && observation.value->items().size() == 1) {
                const auto& retained = observation.value->items().front();
                const auto& previous = state->beforeAction->items();
                const auto found = std::find_if(previous.begin(), previous.end(), [](const auto& row) { return row.localRecordingId == "retained"; });
                requireProblemUi(found != previous.end() && sameProblemUiRow(retained, *found) &&
                    observation.value->deletionOperations().empty() && observation.value->purgeAcknowledgements().empty(),
                    "retained_row_all_fields_no_server_delete");
                requireProblemUi(nativeLocalRemovalContextCurrent(std::get<ProblemTarget>(pendingLocalRemoval_->source),
                    pendingLocalRemoval_->selectionRevision), "completion_current_after_row_gone");
            }
            pollLocalRecordingRemoval(); // Actual production consumption and truthful user result.
            if (pendingLocalRemoval_) return;
            requireProblemUi(observation.complete && observation.value && observation.value->items().size() == 1 &&
                localActionNotice_ == L"Локальная копия больше не хранится в GRAF. Если файл был на диске, он перемещён в Корзину Windows. Запись на сервере не изменена." &&
                !capture_->takeProtectedDeletionCompletion(state->removalTicket) && state->accountCalls == 2,
                "adopted_positive_completion_consumed_once");
            refreshSelectedRecording();
            requireProblemUi(selectedLocalRemovalButton_ && !selectedLocalRemovalButton_.IsEnabled() && selectedLocalRecordingId_.empty(),
                "removed_copy_no_longer_actionable");
            state->afterAction = observation.value; state->beforeAction.reset(); state->dialog = nullptr;
            state->startRemovalCheck(); state->phase = 15;
        } else if (state->phase == 15) {
            if (state->seed.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
            state->seed.get(); // Same directory and protected bytes now in the real Windows Recycle Bin.
            state->passed = true; state->phase = 11; capture_->shutdown();
        } else if (state->phase == 11) {
            if (localActionDialogOpen_) {
                // Click may already have shown the popup before the test adopted
                // its reference, or while its button template was still loading.
                for (const auto& popup : Media::VisualTreeHelper::GetOpenPopupsForXamlRoot(root_.XamlRoot()))
                    if (popup.Child()) if (auto dialog = problemUiDialog(popup.Child())) dialog.Hide();
                return; // The production Completed callback still owns its continuation.
            }
            if (state->seed.valid()) {
                if (state->seed.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
                try { state->seed.get(); } catch (...) { state->failed = true; }
            }
            if (capture_) {
                NativeCaptureStorageTestPeer::pollAccount(*capture_); // Retire a cancelled resolver before actual shutdown/drain.
                capture_->pollUploads(); // A broken stale guard must retire accepted work and FAIL, not hang the test.
                if (!capture_->shutdownWorkDrained()) return;
            }
            reminders_.reset(); tray_.reset(); capture_.reset();
            state->beforeAction.reset(); state->dialog = nullptr;
            state->phase = 12; // A failed dispatch must not launch cleanup again.
            try { state->startCleanup(); } catch (...) { state->failed = true; }
        } else if (state->phase == 12) {
            if (state->cleanup.valid() && state->cleanup.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
            bool unchangedAndRemoved = false;
            if (state->cleanup.valid()) try { unchangedAndRemoved = state->cleanup.get(); } catch (...) { state->failed = true; }
            const bool drained = CustodyOwnedMemory::usedBytes() == state->baseline;
            problemUiResult = state->passed && !state->failed && unchangedAndRemoved && drained ? 73 : 3;
            std::fprintf(stderr, "PROBLEM_UI terminal=1 cases=%u protected_verified=%u owned_baseline=%u exit=%d\n",
                state->passed ? 6U : 0U, unchangedAndRemoved ? 1U : 0U, drained ? 1U : 0U, problemUiResult);
            if (problemUiResult == 73) std::fputs("AppMainProblemUiTests PASS: quota, Cancel, stale Primary and actual local-copy Recycle/adopted completion/cold queue; NOT installed/active-capture proof\n", stderr);
            std::fflush(stderr); state->phase = 13; stateTimer_.Stop(); window_.Close(); Exit();
        }
    } catch (...) {
        std::fprintf(stderr, "PROBLEM_UI exception=1 phase=%u native_hr=0x%08x cleanup_requested=1\n",
            state->phase, static_cast<unsigned>(winrt::to_hresult())); std::fflush(stderr);
        if (state->phase == 12 || state->phase == 13) { problemUiResult = 3; stateTimer_.Stop(); Exit(); return; }
        try { if (state->dialog) state->dialog.Hide(); } catch (...) {}
        state->failed = true; state->phase = 11;
        if (capture_) capture_->shutdown();
    }
});
root_.Loaded([this, state](auto const&, auto const&) { state->loaded = true; stateTimer_.Start(); });
window_.AppWindow().Closing([this, state](auto const&, auto const& args) {
    if (state->phase == 13) return;
    args.Cancel(true); state->failed = true;
    if (state->phase != 11 && state->phase != 12) {
        try { if (state->dialog) state->dialog.Hide(); } catch (...) {}
        state->phase = 11;
        if (capture_) capture_->shutdown();
    }
});
stateTimer_.Start(); // Enforce the startup deadline even if Loaded never arrives.
window_.Activate();
