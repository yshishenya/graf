#include "../../RecApp/Shell/RecordingIndicator.h"
#include "../../RecApp/Shell/ShellClosePolicy.h"
#include "../../RecApp/Shell/WindowsTray.h"
#include "../../RecApp/Core/WindowsDesktopSession.h"
#include "../GrafWindowsCoreTests/AutomaticRecordingTestSupport.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>

namespace {

std::string source(const char* relative) {
    const auto root = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path();
    std::ifstream file(root / "RecApp" / relative);
    assert(file.is_open());
    return {std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
}

std::string section(const std::string& text, const char* begin, const char* end) {
    const auto first = text.find(begin);
    assert(first != std::string::npos);
    const auto last = text.find(end, first + std::string(begin).size());
    assert(last != std::string::npos);
    return text.substr(first, last - first);
}

void expectBefore(const std::string& text, const char* first, const char* second) {
    const auto a = text.find(first);
    const auto b = text.find(second);
    if (a == std::string::npos || b == std::string::npos || a >= b)
        std::fprintf(stderr, "Expected source order: %s before %s\n", first, second);
    assert(a != std::string::npos && b != std::string::npos && a < b);
}

void testClosePolicy() {
    using namespace graf::windows;
    for (const auto state : {SessionState::idle, SessionState::starting, SessionState::recording,
                            SessionState::paused, SessionState::degraded, SessionState::stopping,
                            SessionState::finalizing, SessionState::savedLocal, SessionState::failed}) {
        // Hiding/reopening owns no capture transition. Repeat X is still a hide;
        // loss of either recovery or the active Stop surface keeps the shell.
        assert(shellCloseAction(ShellCloseIntent::window, state, true, true, false) == ShellCloseAction::hide);
        assert(shellCloseAction(ShellCloseIntent::window, state, false, true, false) == ShellCloseAction::keepVisible);
        assert(shellCloseAction(ShellCloseIntent::window, state, true, false, false) ==
               (isCaptureState(state) ? ShellCloseAction::keepVisible : ShellCloseAction::hide));
        const auto firstQuit = shellCloseAction(ShellCloseIntent::quit, state, false, false, false);
        const auto repeatedQuit = shellCloseAction(ShellCloseIntent::quit, state, true, true, true);
        if (!isCaptureState(state)) {
            assert(firstQuit == ShellCloseAction::close);
            assert(repeatedQuit == ShellCloseAction::close);
        } else {
            assert(firstQuit == (state == SessionState::stopping || state == SessionState::finalizing
                ? ShellCloseAction::wait : ShellCloseAction::stopAndWait));
            assert(repeatedQuit == ShellCloseAction::wait);
            assert(shellCloseAction(ShellCloseIntent::window, state, true, true, true) == ShellCloseAction::wait);
        }
    }
}

void testCloseKeepsTheSessionAndAutomaticTracking() {
    using namespace graf::windows;
    WindowsDesktopSession session("same-session-after-tray-reopen");
    assert(session.beginReadinessCheck().accepted());
    assert(session.markReady().accepted());
    assert(session.beginStart().accepted());
    const auto hideAndReopen = [&] {
        const auto before = session.state();
        for (unsigned repeat = 0; repeat < 3; ++repeat)
            assert(shellCloseAction(ShellCloseIntent::window, session.state(), true, true, false) == ShellCloseAction::hide);
        assert(session.state() == before);
        assert(session.sessionId() == "same-session-after-tray-reopen");
        // Hiding does not release the actual process-wide active-session lease.
        WindowsDesktopSession other("must-not-start");
        const auto blocked = other.beginReadinessCheck();
        assert(!blocked.accepted() && blocked.reason == ReasonCode::activeSessionExists);
    };
    hideAndReopen();
    assert(session.startRecording().accepted());
    hideAndReopen();
    assert(session.pause().accepted());
    hideAndReopen();
    assert(shellCloseAction(ShellCloseIntent::quit, session.state(), true, true, false) == ShellCloseAction::stopAndWait);
    assert(session.stop().accepted());
    assert(shellCloseAction(ShellCloseIntent::quit, session.state(), true, true, true) == ShellCloseAction::wait);
    assert(session.beginFinalizing().accepted());
    hideAndReopen();
    assert(shellCloseAction(ShellCloseIntent::window, session.state(), false, false, true) == ShellCloseAction::wait);
    assert(session.saveLocal().accepted());
    assert(shellCloseAction(ShellCloseIntent::quit, session.state(), false, false, true) == ShellCloseAction::close);

    using namespace graf::windows::testing;
    VerifiedTargetRegistry registry;
    assert(registry.registerTarget(target()));
    Preferences preferences;
    AutomaticRecordingPolicy policy(registry, preferences.store());
    assert(policy.setPreference(target(), AutomaticRecordingPreference::always));
    assert(observeFor(policy, 0, 5).shouldStart);
    policy.captureAccepted();
    assert(shellCloseAction(ShellCloseIntent::window, SessionState::recording, true, true, false) == ShellCloseAction::hide);
    assert(!policy.shouldStopCapture(snapshot(at(6s)), true, at(6s)));
    // The same tracked meeting still ends automatically after hiding/reopening.
    for (int second = 7; second <= 22; ++second) {
        const auto now = at(std::chrono::seconds(second));
        auto absent = snapshot(now);
        absent.observations.clear();
        assert(policy.shouldStopCapture(absent, true, now) == (second == 22));
    }
}

void testCloseSourceWiring() {
    // Source checks complement the executable policy, not Windows UI evidence.
    const auto app = source("AppMain.cpp");
    const auto closing = section(app, "window_.AppWindow().Closing(", "window_.Closed(");
    assert(closing.find("shellCloseAction(ShellCloseIntent::window") != std::string::npos);
    assert(closing.find("tray_->available()") != std::string::npos);
    assert(closing.find("requestExit()") == std::string::npos);
    assert(closing.find("capture_->stop") == std::string::npos);
    assert(closing.find("automaticPolicy_.cancel()") == std::string::npos);
    assert(closing.find("args.Cancel(true)") != std::string::npos);
    const auto quit = section(app, "    void requestExit()", "    bool ensureRecordingIndicator(");
    assert(quit.find("shellCloseAction(ShellCloseIntent::quit") != std::string::npos);
    expectBefore(quit, "exitRequested_ = true", "window_.Close()");
    assert(quit.find("action == ShellCloseAction::stopAndWait") != std::string::npos);
    assert(quit.find("RecordingStopReason::interruption") != std::string::npos);
    const auto tray = source("Shell/WindowsTray.cpp");
    const auto restart = section(tray, "if (message == self->taskbarCreated)", "if (message == kTrayMessage)");
    expectBefore(restart, "self->registered = false", "self->addIcon()");
    const auto add = section(tray, "    bool addIcon()", "\n};");
    // A state tick may restore the icon before the queued TaskbarCreated
    // broadcast arrives. NIM_ADD can then fail for our already-present icon.
    assert(add.find("NIM_MODIFY") != std::string::npos);
    expectBefore(add, "NIM_ADD", "NIM_SETVERSION");
    expectBefore(add, "NIM_SETVERSION", "registered = true");
    assert(add.find("removeIcon()") != std::string::npos);
    const auto update = section(tray, "    void updateIcon()", "    bool addIcon()");
    const auto modification = update.find("NIM_MODIFY");
    assert(modification != std::string::npos);
    expectBefore(update.substr(modification), "registered = false", "addIcon()");
    const auto available = section(tray, "bool WindowsTray::available()", "void WindowsTray::setTheme(");
    assert(available.find("updateIcon()") != std::string::npos);
    assert(available.find("impl_->registered") != std::string::npos);
    const auto fallback = section(app, "    void refreshTrayAvailability()", "    void buildShell()");
    assert(fallback.find("tray_->available()") != std::string::npos);
    assert(fallback.find("window_.AppWindow().Show(false)") != std::string::npos);
    assert(app.find("trayExitButton_.Click([this](auto const&, auto const&) { requestExit(); })") != std::string::npos);
    const auto startup = section(app, "    void showStartupError(", "    static double reminderWallTime()");
    assert(startup.find("requestExit()") != std::string::npos);
}

void testBackgroundSurfaceWiring() {
    const auto app = source("AppMain.cpp");
    const auto prompt = section(app, "    void updateAutomaticPrompt()", "    void showPermissionOnboarding()");
    assert(app.find("automaticPromptWindow_") == std::string::npos);
    assert(prompt.find("NoticeKind::recordingPrompt") != std::string::npos);
    assert(prompt.find("notificationCard().present(") != std::string::npos);
    assert(prompt.find("hooks.onPresented") != std::string::npos);
    assert(prompt.find("automaticPolicy_.confirmPromptPresented(") != std::string::npos);
    assert(prompt.find("notificationCard().deadline() - std::chrono::seconds(8)") != std::string::npos);
    assert(prompt.find("automaticPolicy_.cancel()") != std::string::npos);
    const auto indicator = section(app, "    bool ensureRecordingIndicator(", "    void pauseResumeCapture()");
    assert(indicator.find("indicatorWindow_.Activate()") == std::string::npos);
    assert(indicator.find("indicatorWindow_.AppWindow().Show(false)") != std::string::npos);
    assert(indicator.find("if (!recordingIndicatorAvailable())") != std::string::npos);
    const auto automaticStart = section(app, "    void startAutomaticRecording(", "    bool closeAutomaticPrompt(");
    expectBefore(automaticStart, "!ensureRecordingIndicator()", "capture_->record(");
    const auto manualStart = section(app, "    void recordCapture()", "    void stopCapture()");
    expectBefore(manualStart, "!ensureRecordingIndicator()", "capture_->record()");
    const auto keyboard = section(app, "    bool focusBackgroundSurface()", "    void refreshTrayAvailability()");
    assert(keyboard.find("NoticeKind::recordingPrompt") != std::string::npos);
    assert(keyboard.find("notificationCard().focus()") != std::string::npos);
    assert(keyboard.find("indicatorStop_.Focus(FocusState::Keyboard)") != std::string::npos);
    assert(app.find("VirtualKey::F6 && focusBackgroundSurface()") != std::string::npos);
}

void testTrayActionWiring() {
    const auto tray = source("Shell/WindowsTray.cpp");
    const auto append = section(tray, "    void addItem(", "    void measureItem(");
    assert(append.find("MF_DISABLED") != std::string::npos);
    assert(append.find("MF_SEPARATOR") != std::string::npos);
    assert(append.find("MSAA_MENU_SIG") != std::string::npos);
    assert(append.find("accessibility.pszWText = item->text.data()") != std::string::npos);
    assert(tray.find("L\"Начать запись\", kStartCommand") != std::string::npos);
    assert(tray.find("L\"Настройки\", kSettingsCommand") != std::string::npos);
    assert(tray.find("L\"Перейти к уведомлению\", kFocusNotificationCommand") != std::string::npos);
    assert(tray.find("L\"История уведомлений\"") != std::string::npos);
    assert(tray.find("history.size() > 50") != std::string::npos);
    assert(tray.find("if (self->actions.start) handler = self->startHandler") != std::string::npos);
    assert(tray.find("if (self->actions.settings) handler = self->settingsHandler") != std::string::npos);
    const auto app = source("AppMain.cpp");
    assert(app.find("[this] { recordCapture(); }") != std::string::npos);
    assert(app.find("[this] { openAccountSettings(); }") != std::string::npos);
    const auto start = section(app, "    void recordCapture()", "    void stopCapture()");
    expectBefore(start, "capture_->refreshReadiness()", "!canStartRecording()");
    expectBefore(start, "!canStartRecording()", "capture_->record()");
    assert(app.find("tray_->setState(snapshot, canStartRecording(), exitRequested_)") != std::string::npos);
    const auto settings = section(app, "    void openAccountSettings()", "    bool focusBackgroundSurface()");
    assert(settings.find("/desktop/settings/account") != std::string::npos);
    assert(settings.find("trustedOrigin()") != std::string::npos);
    assert(settings.find("openMainWindow()") != std::string::npos);
    assert(settings.find("openNativeSettings()") == std::string::npos);
    assert(app.find("settingsButton.Click([this](auto const&, auto const&) { openAccountSettings(); })") != std::string::npos);
    assert(app.find("RecordingNoticePresenter::historyMessage(entry.kind)") != std::string::npos);
    assert(app.find("protectedFramesProvider = [this] { return notificationProtectedFrames(); }") != std::string::npos);
}

void testTrayActionAvailability() {
    using namespace graf::windows;
    RecordingIndicator indicator;
    for (const auto state : {SessionState::idle, SessionState::ready, SessionState::blocked,
                            SessionState::starting, SessionState::recording, SessionState::paused,
                            SessionState::degraded, SessionState::stopping, SessionState::finalizing,
                            SessionState::savedLocal, SessionState::failed}) {
        indicator.publish(state);
        for (bool ready : {false, true}) {
            for (bool exiting : {false, true}) {
                const auto actions = WindowsTray::menuAvailability(indicator.snapshot(), ready, exiting);
                assert(actions.start == (ready && !isCaptureState(state) && !exiting));
                assert(actions.pauseResume == (!exiting && (state == SessionState::recording || state == SessionState::paused)));
                assert(actions.stop == isCaptureState(state));
                assert(actions.settings == !exiting);
            }
        }
    }
}

void testLocalNotificationSettingsWiring() {
    // Source wiring only: native control layout/focus still requires a live
    // installed Windows run. The model/bridge suites exercise persistence.
    const auto app = source("AppMain.cpp");
    const auto settings = section(app, "    void openNativeSettings()", "    void bindNotificationContext()");
    for (const auto field : {"reminders", "showTitles", "sound", "quiet", "offsetMinutes"})
        assert(settings.find(std::string("\"") + field + "\"") != std::string::npos);
    assert(settings.find("NotificationAction::test") != std::string::npos);
    assert(settings.find("AutomationLiveSetting::Polite") != std::string::npos);
    assert(settings.find("ms-settings:notifications") == std::string::npos);
    const auto bind = section(app, "    void bindNotificationContext()", "    void refreshLocalNotificationSettings()");
    assert(bind.find("capture_->currentAccount()") != std::string::npos);
    assert(bind.find("DesktopHttpConfig{}.baseOrigin") != std::string::npos);
    const auto save = section(app, "    void applyLocalNotificationSetting(", "    ComboBox automaticPreferencePicker(");
    expectBefore(save, "bindNotificationContext()", "displayedEpoch != reminders_->epoch()");
    expectBefore(save, "displayedEpoch != reminders_->epoch()", "reminders_->settings(");
    assert(save.find("refreshNativeSettings()") != std::string::npos);
    assert(save.find("refreshLocalNotificationSettings()") != std::string::npos);
    const auto refresh = section(app, "    void refreshLocalNotificationSettings()", "    void applyLocalNotificationSetting(");
    assert(refresh.find("reminders_->preferences()") != std::string::npos);
    assert(refresh.find("toggle.IsEnabled(editable)") != std::string::npos);
    assert(refresh.find("localNotificationOffset_.IsEnabled(editable && preferences.reminders)") != std::string::npos);
    assert(refresh.find("localNotificationTest_.IsEnabled(editable)") != std::string::npos);
    const auto answer = section(app, "    std::string answerNativeSettings(", "    const graf::windows::VerifiedTargetIdentity*");
    assert(answer.find("refreshLocalNotificationSettings()") != std::string::npos);
    const auto status = section(app, "    void setLocalNotificationStatus(", "    void refreshLocalNotificationSettings()");
    expectBefore(status, "localNotificationStatus_.Text() == text", "RaiseAutomationEvent(");
    assert(status.find("AutomationEvents::LiveRegionChanged") != std::string::npos);
}

void testSystemThemeRefreshWiring() {
    const auto app = source("AppMain.cpp");
    const auto appearance = section(app, "    void applyCabinetAppearance(", "    // The names the cabinet prints");
    assert(appearance.find("if (theme == announcedAppearance_)") == std::string::npos);
    assert(appearance.find("notificationCard().setDarkTheme(isDark)") != std::string::npos);
    const auto refresh = section(app, "    void refreshNativeState()", "    TextBlock privacyNotice_");
    assert(refresh.find("announcedAppearance_ == \"system\" && systemThemeIsDark() != shellIsDark_") != std::string::npos);
    assert(refresh.find("applyCabinetAppearance(\"system\")") != std::string::npos);
}

void testInteractionLifecycle() {
    using namespace graf::windows;
    InteractionPermitState guard;
    assert(!guard.permit().allowed);
    const InteractionSample ready{true, true, true, true};
    auto permit = guard.observe(ready, 100);
    assert(permit.allowed && permit.epoch != 0);
    const auto initial = permit.epoch;
    std::uint64_t sampleTime = 100;
    for (int missing = 0; missing != 4; ++missing) {
        auto sample = ready;
        if (missing == 0) sample.subscriptionsReady = false;
        if (missing == 1) sample.sessionActive = false;
        if (missing == 2) sample.sessionUnlocked = false;
        if (missing == 3) sample.inputDesktop = false;
        const auto before = guard.permit().epoch;
        assert(!guard.observe(sample, ++sampleTime).allowed);
        assert(guard.permit().epoch != before);
        assert(guard.observe(ready, ++sampleTime).allowed);
    }
    assert(guard.permit().epoch != initial);
    for (const auto event : {InteractionEvent::sessionUnavailable, InteractionEvent::suspend}) {
        const auto before = guard.permit().epoch;
        guard.event(event);
        assert(!guard.permit().allowed && guard.permit().epoch != before);
        assert(!guard.observe(ready, 200).allowed); // positive probe cannot undo a latched event
        guard.event(InteractionEvent::resumeAutomatic);
        assert(!guard.observe(ready, 201).allowed);
        guard.event(InteractionEvent::sessionAvailable);
        assert(!guard.permit().allowed); // event is not positive evidence
        assert(guard.observe(ready, 202).allowed);
        assert(guard.permit().epoch != before); // an old worker token never revives
    }
    guard.event(InteractionEvent::suspend);
    guard.event(InteractionEvent::resumeInteractive);
    assert(guard.observe(ready, 203).allowed);
    const auto beforeSwitch = guard.permit().epoch;
    guard.event(InteractionEvent::desktopSwitch);
    assert(!guard.permit().allowed);
    assert(guard.observe(ready, 204).allowed && guard.permit().epoch != beforeSwitch);
    const auto beforeGap = guard.permit().epoch;
    assert(guard.observe(ready, 4000).allowed && guard.permit().epoch != beforeGap);
    const auto beforeRollback = guard.permit().epoch;
    assert(guard.observe(ready, 3000).allowed && guard.permit().epoch != beforeRollback);
    guard.event(InteractionEvent::shutdown);
    guard.event(InteractionEvent::sessionAvailable);
    assert(!guard.observe(ready, 4001).allowed);
    assert(!guard.retrySubscriptionsDue(4001));
    InteractionPermitState retry;
    assert(retry.retrySubscriptionsDue(0));
    assert(!retry.retrySubscriptionsDue(999));
    for (const std::uint64_t at : {1000, 3000, 7000, 15000}) {
        assert(!retry.retrySubscriptionsDue(at - 1));
        assert(retry.retrySubscriptionsDue(at));
        assert(!retry.retrySubscriptionsDue(at));
    }
    assert(!retry.retrySubscriptionsDue(31000));
    // A late positive prerequisite query may allow NEW work, not the token
    // captured before the gap. The final guard must compare the fresh epoch.
    InteractionPermitState pending;
    const auto token = pending.observe(ready, 100);
    const auto latePositive = pending.observe(ready, 2601);
    assert(latePositive.allowed && latePositive.epoch == token.epoch + 1);
    const auto finalPermit = pending.observe(ready, 2602);
    assert(!(finalPermit.allowed && finalPermit.epoch == token.epoch));
    // A slow native sample is not fresh evidence, even if all facts are true.
    // Recovery requires another bounded query and cannot revive its old token.
    for (const bool rollback : {false, true}) {
        InteractionPermitState sampling;
        const auto old = sampling.observe(ready, 100);
        const std::uint64_t finishedAt = rollback ? 99 : 2601;
        const auto stale = sampling.observe(ready, 100, finishedAt);
        assert(!stale.allowed && stale.epoch != old.epoch);
        const auto fresh = sampling.observe(ready, finishedAt + 1, finishedAt + 2);
        assert(fresh.allowed && fresh.epoch != old.epoch);
    }
    InteractionPermitState boundary;
    assert(boundary.observe(ready, 100, 2600).allowed);
#ifndef _WIN32
    WindowsTray unsupported(0, {}, {}, {});
    assert(!unsupported.interactionPermit().allowed);
#endif
    // Source wiring, not live WTS/power/secure-desktop evidence.
    const auto tray = source("Shell/WindowsTray.cpp");
    for (const auto api : {"WTSRegisterSessionNotification", "NOTIFY_FOR_THIS_SESSION",
                          "WTSQuerySessionInformationW", "WTSSessionInfoEx", "WTSFreeMemory",
                          "WTS_SESSIONSTATE_UNLOCK", "GetThreadDesktop", "UOI_IO",
                          "RegisterSuspendResumeNotification", "DEVICE_NOTIFY_WINDOW_HANDLE",
                          "EVENT_SYSTEM_DESKTOPSWITCH", "WINEVENT_OUTOFCONTEXT",
                          "WM_WTSSESSION_CHANGE", "WM_POWERBROADCAST",
                          "WTSUnRegisterSessionNotification", "UnregisterSuspendResumeNotification", "UnhookWinEvent"})
        assert(tray.find(api) != std::string::npos);
    assert(tray.find("interaction.retrySubscriptionsDue(now)") != std::string::npos);
    const auto probe = section(tray, "    InteractionPermit checkInteraction()", "    void cleanupInteraction()");
    assert(probe.find("interaction.observe") != std::string::npos);
    expectBefore(probe, "WTSQuerySessionInformationW(", "const auto finishedAt = GetTickCount64()");
    expectBefore(probe, "GetUserObjectInformationW(", "const auto finishedAt = GetTickCount64()");
    expectBefore(probe, "const auto finishedAt = GetTickCount64()", "interaction.observe(sample, now, finishedAt)");
    assert(probe.find("registered") == std::string::npos); // independent of Explorer icon availability
    assert(probe.find("invalidationHandler()") == std::string::npos); // no callback during a card probe
    const auto lifecycle = section(tray, "    void interactionEvent(", "    // Тема");
    assert(lifecycle.find("capture_") == std::string::npos);
    assert(lifecycle.find("SetForegroundWindow") == std::string::npos);
    const auto app = source("AppMain.cpp");
    assert(app.find("interactionPermitProvider = [this] { return interactionPermit(); }") != std::string::npos);
    const auto start = section(app, "    void startAutomaticRecording(", "    bool closeAutomaticPrompt(");
    expectBefore(start, "interactionEpoch = permit.epoch", "if (!permit.allowed || permit.epoch != interactionEpoch)");
    expectBefore(start, "if (!permit.allowed || permit.epoch != interactionEpoch)", "automaticPolicy_.acceptStart(");
    const auto finalGuard = section(start,
        "prerequisites.oneActionStopAvailable = prerequisites.visibleIndicatorAvailable;",
        "return automaticPolicy_.acceptStart(");
    expectBefore(finalGuard, " = interactionPermit();", ".epoch != interactionEpoch");
    assert(finalGuard.find(".allowed") != std::string::npos);
    const auto refresh = section(app, "    void refreshNativeState()", "    TextBlock privacyNotice_");
    expectBefore(refresh, "refreshNotificationInteraction()", "capture_->pollHealth()");
    expectBefore(refresh, "capture_->pollUploads()", "notificationCard().presentPendingShort(");
    expectBefore(refresh, "notificationCard().presentPendingShort(", "refreshMeetingReminders()");
    const auto invalidate = section(app, "    void invalidateNotificationInteraction()", "    void refreshNotificationInteraction()");
    expectBefore(invalidate, "!capture_->indicator().visible || capture_->indicator().state == graf::windows::SessionState::starting",
                 "automaticPolicy_.cancel()");
    assert(invalidate.find("notificationCard().invalidatePresentation()") != std::string::npos);
    assert(invalidate.find("resetContext()") == std::string::npos);
    assert(invalidate.find("Hide()") == std::string::npos);
    assert(invalidate.find("capture_->stop") == std::string::npos);
}

void testRecordingProblemAndShortSourceWiring() {
    // These assertions keep the tested model connected to the WinUI shell;
    // they supplement, not replace, native compilation and interaction tests.
    const auto app = source("AppMain.cpp");
    const auto projection = section(app,
        "    [[nodiscard]] std::vector<graf::windows::LocalProblemProjection> recordingProblems(",
        "    [[nodiscard]] const auto& custodyRoot()");
    assert(projection.find("const bool blocker = !deliberateShort") != std::string::npos);
    assert(projection.find("state.state == State::blocked && state.reason != graf::windows::ReasonCode::none") != std::string::npos);
    assert(projection.find("complete ? queue_.items() : noRows") != std::string::npos);
    const auto shortResult = section(app, "                if (result.shortRecordingDiscarded)",
        "                if (!result.normalPackage())");
    expectBefore(shortResult, "recordingAuthGeneration_ == authGeneration_ && sameOwner",
        "noticePresenter_.queueShortRecordingDiscarded(");
    assert(shortResult.find("showShortRecordingDiscarded(") == std::string::npos);
    assert(app.find("PendingShortNotice") == std::string::npos); // one presenter-owned pending short
    const auto reconcile = section(app, "    void reconcileRecordingProblems()", "    void refreshSelectedRecording()");
    expectBefore(reconcile, "LocalProblemState::positivelyResolved", "problemStore_.resolveProblem(");
    expectBefore(reconcile, "problemStore_.claimProblem(", "card.recordProblemHistory(");
    expectBefore(reconcile, "card.recordProblemHistory(", "if (reminders_->preferences().quiet)");
    assert(reconcile.find("pendingProblems_.size() >= 256") != std::string::npos);
    const auto open = section(app, "    void openProblemRecording(", "    void reconcileRecordingProblems()");
    expectBefore(open, "if (!problemActionCurrent(target)) return", "selectedRecording_ = target");
    assert(open.find("StartBringIntoView()") != std::string::npos);
    assert(open.find("Focus(FocusState::Programmatic)") != std::string::npos);
    assert(open.find("ShellExecute") == std::string::npos); // inspect this session, never launch its M4A
    const auto context = section(app, "    void bindNotificationContext()", "    void setLocalNotificationStatus(");
    assert(context.find("pendingProblems_.clear()") != std::string::npos);
    assert(context.find("selectedRecording_.reset()") != std::string::npos);
    const auto refresh = section(app, "    void refreshNativeState()", "    TextBlock privacyNotice_");
    expectBefore(refresh, "capture_->pollUploads()", "reconcileRecordingProblems()");
    expectBefore(refresh, "reconcileRecordingProblems()", "notificationCard().presentPendingShort(");
    expectBefore(refresh, "notificationCard().presentPendingShort(", "refreshMeetingReminders()");
}

} // namespace

int main() {
    using namespace graf::windows;
    testClosePolicy();
    testCloseKeepsTheSessionAndAutomaticTracking();
    testCloseSourceWiring();
    testBackgroundSurfaceWiring();
    testTrayActionWiring();
    testTrayActionAvailability();
    testLocalNotificationSettingsWiring();
    testSystemThemeRefreshWiring();
    testInteractionLifecycle();
    testRecordingProblemAndShortSourceWiring();
#ifndef _WIN32
    WindowsTray unsupported(0, {}, {}, {});
    assert(!unsupported.available()); // A portable stub never claims a real tray.
#endif
    RecordingIndicator indicator;
    indicator.publish(SessionState::degraded, ReasonCode::clockDiscontinuity);
    assert(indicator.snapshot().visible && indicator.snapshot().stopAvailable);
    assert(indicator.snapshot().statusText == "Запись ограничена");
    return 0;
}
