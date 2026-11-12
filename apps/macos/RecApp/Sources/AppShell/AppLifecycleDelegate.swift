import AppKit
import Combine
import SwiftUI
import TwoBrainRecShared

@MainActor
final class AppLifecycleDelegate: NSObject, NSApplicationDelegate, NSMenuItemValidation, NSWindowDelegate {
    private var mainWindow: NSWindow?
    private var settingsWindow: NSWindow?
    private var calendarTrayController: CalendarTrayController?
    private var trayRecordingState: GrafTrayRecordingState = .idle
    private let workspaceZoomStore = WorkspaceZoomStore()
    private let interfacePreferences = InterfacePreferencesStore()
    private let appUpdateController: AppUpdateController
    private var appUpdateSubscription: AnyCancellable?
    private var notificationContextSubscription: AnyCancellable?
    private var terminationReplyPending = false
    private var settingsExitPending = false
    private var relaunchAfterTermination = false

    override init() {
        appUpdateController = AppUpdateController { event, detail in
            AppLog.writeRaw(event: event, detail: detail)
        }
        super.init()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(applicationTerminationCleanupFinished),
            name: .twoBrainRecApplicationTerminationCleanupFinished,
            object: nil
        )
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    func updateTrayRecordingState(_ state: GrafTrayRecordingState) {
        trayRecordingState = state
        calendarTrayController?.showRecordingState(state)
    }

    func applicationWillFinishLaunching(_: Notification) {
        UserDefaults.standard.register(defaults: [
            "ApplePersistenceIgnoreState": true,
            "NSQuitAlwaysKeepsWindows": false
        ])
        UserDefaults.standard.set(true, forKey: "ApplePersistenceIgnoreState")
        UserDefaults.standard.set(false, forKey: "NSQuitAlwaysKeepsWindows")
        NSApp.setActivationPolicy(.regular)
    }

    func application(
        _: NSApplication,
        shouldSaveApplicationState _: NSCoder
    ) -> Bool {
        false
    }

    func application(
        _: NSApplication,
        shouldRestoreApplicationState _: NSCoder
    ) -> Bool {
        false
    }

    func applicationDidFinishLaunching(_: Notification) {
        AppLog.writeRaw(
            event: "app_launch_finished",
            detail: "activationPolicy=regular"
        )
        NSApp.activate(ignoringOtherApps: true)
        presentMainWindow(reason: "launch")
        let trayModel = CalendarTrayModel {
            guard let client = DesktopUploadClient.configuredFromEnvironment() else {
                throw DesktopUploadClientError.invalidBaseURL
            }
            return try await client.listDesktopCalendarUpcoming(beforeMinutes: 15, afterMinutes: 1_440)
        }
        calendarTrayController = CalendarTrayController(
            model: trayModel,
            onOpenSettings: { [weak self] in self?.openSettings(nil) },
            onOpenMeetings: { [weak self] in self?.openMeetingsFromTray() },
            onStartRecording: { [weak self] in self?.captureCommandFromTray(.start) },
            onStopRecording: { [weak self] in self?.captureCommandFromTray(.stop) },
            onMuteMicrophone: { [weak self] in self?.captureCommandFromTray(.pause) },
            onUnmuteMicrophone: { [weak self] in self?.captureCommandFromTray(.resume) },
            onQuit: { NSApp.terminate(nil) },
            onUpdate: { [weak self] in self?.checkForUpdates(nil) },
            notificationHistory: { DesktopNotificationPresenter.shared.history },
            canFocusNotification: { DesktopNotificationPresenter.shared.card.isVisible },
            onFocusNotification: { DesktopNotificationPresenter.shared.focusCurrentNotification() }
        )
        notificationContextSubscription = DesktopNotificationPresenter.shared.$authEpoch.dropFirst()
            .sink { [weak self] _ in self?.calendarTrayController?.invalidateNotificationHistory() }
        trayModel.onAuthInvalidated = { DesktopNotificationPresenter.shared.invalidate() }
        trayModel.onProjection = { DesktopNotificationPresenter.shared.updateCalendarProjection($0) }
        calendarTrayController?.start()
        calendarTrayController?.showRecordingState(trayRecordingState)
        appUpdateSubscription = appUpdateController.$presentation
            .combineLatest(appUpdateController.$isManualCheckActionEnabled)
            .sink { [weak self] presentation, enabled in
                self?.calendarTrayController?.showUpdate(presentation, actionEnabled: enabled)
            }
        appUpdateController.start()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.logWindowVisibility()
        }
    }

    func applicationShouldHandleReopen(
        _ sender: NSApplication,
        hasVisibleWindows flag: Bool
    ) -> Bool {
        // A notification may already have opened its target before macOS sends reopen.
        if !flag { presentMainWindow(reason: "reopen") }
        return true
    }

    /// Ссылка со страницы загрузки: метки кампании попадают в приложение (FR-022).
    func application(_: NSApplication, open urls: [URL]) {
        for url in urls {
            if SharedMeetingHandoffInbox.shared.receive(url) {
                presentMainWindow(reason: "shared_meeting_handoff")
                NotificationCenter.default.post(name: .grafSharedMeetingHandoffDidArrive, object: nil)
                continue
            }
            let store = ProductAttributionHandoffStore()
            // Разбор и запись живут в хранилище, поэтому тот же путь проверяем
            // тестом; здесь остаются только журнал и показ окна.
            guard let handoff = store.handleOpenURL(url) else {
                AppLog.writeRaw(event: "attribution.handoff_rejected", detail: "scheme=\(url.scheme ?? "unknown")")
                continue
            }
            AppLog.writeRaw(
                event: "attribution.handoff_received",
                detail: "scheme=\(handoff.bridgeID != nil ? "bridge" : "labels_only") campaignKnown=\(handoff.campaignKnown)"
            )
            presentMainWindow(reason: "attribution_handoff")
            NotificationCenter.default.post(
                name: .twoBrainRecDesktopAttributionHandoffDidArrive,
                object: nil
            )
        }
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        // Карточка не должна переживать закрытие окна GRAF: она принадлежит
        // текущему процессу и не может оставаться самостоятельным баннером.
        DesktopNotificationPresenter.shared.dismissAllCards()
        NotificationCenter.default.post(name: .twoBrainRecDismissMeetingDetectionPrompt, object: nil)
        guard !settingsExitPending else { return false }
        settingsExitPending = true
        Task { [weak self, weak sender] in
            let allowed = await EmbeddedCabinetWebView.prepareSettingsToLeave(in: sender?.contentView)
            self?.settingsExitPending = false
            if allowed { sender?.close() }
        }
        return false
    }

    func windowDidMove(_ notification: Notification) {
        saveMainWindowFrame(from: notification)
    }

    func windowDidResize(_ notification: Notification) {
        saveMainWindowFrame(from: notification)
    }

    private func saveMainWindowFrame(from notification: Notification) {
        guard let window = notification.object as? NSWindow, window === mainWindow else { return }
        interfacePreferences.saveWindowFrame(window.frame)
    }

    func applicationShouldTerminate(_: NSApplication) -> NSApplication.TerminateReply {
        // Карточка живёт в отдельной панели и иначе остаётся поверх экрана,
        // пока асинхронное завершение приложения ещё не закончено.
        DesktopNotificationPresenter.shared.dismissAllCards()
        NotificationCenter.default.post(name: .twoBrainRecDismissMeetingDetectionPrompt, object: nil)
        guard !terminationReplyPending else { return .terminateLater }
        guard !settingsExitPending else { return .terminateCancel }
        terminationReplyPending = true
        settingsExitPending = true
        Task { [weak self] in
            guard let self else { return }
            let allowed = await EmbeddedCabinetWebView.prepareSettingsToLeave(in: self.mainWindow?.contentView)
            self.settingsExitPending = false
            guard allowed else {
                self.terminationReplyPending = false
                self.relaunchAfterTermination = false
                NSApp.reply(toApplicationShouldTerminate: false)
                return
            }
            self.appUpdateController.updateProtectedWork(
                ProtectedUpdateWork(terminationCleanupPending: true)
            )
            AppLog.writeRaw(
                event: "app_termination_cleanup_requested",
                detail: "reply=terminateLater"
            )
            self.dismissModalWindowsForTermination()
            NotificationCenter.default.post(name: .twoBrainRecApplicationShouldTerminate, object: nil)
            DispatchQueue.main.asyncAfter(deadline: .now() + 10) { [weak self] in
                self?.replyToTerminateIfPending(reason: "timeout")
            }
        }
        return .terminateLater
    }

    func applicationWillTerminate(_: Notification) {
        AppLog.flush()
        if relaunchAfterTermination {
            relaunchAfterTermination = false
            let configuration = NSWorkspace.OpenConfiguration()
            configuration.activates = true
            configuration.createsNewApplicationInstance = true
            NSWorkspace.shared.openApplication(
                at: Bundle.main.bundleURL,
                configuration: configuration
            )
        }
        mainWindow = nil
        settingsWindow = nil
    }

    func requestRelaunch() {
        guard !terminationReplyPending else { return }
        relaunchAfterTermination = true
        NSApp.terminate(nil)
    }

    @objc private func applicationTerminationCleanupFinished() {
        replyToTerminateIfPending(reason: "cleanup_finished")
    }

    private func replyToTerminateIfPending(reason: String) {
        guard terminationReplyPending else { return }
        terminationReplyPending = false
        appUpdateController.updateProtectedWork(.idle)
        AppLog.writeRaw(
            event: "app_termination_cleanup_completed",
            detail: "reason=\(reason)"
        )
        NSApp.reply(toApplicationShouldTerminate: true)
    }

    private func dismissModalWindowsForTermination() {
        if NSApp.modalWindow != nil {
            NSApp.abortModal()
        }

        for window in NSApp.windows {
            if let attachedSheet = window.attachedSheet {
                window.endSheet(attachedSheet)
            }
            if window.isSheet, let sheetParent = window.sheetParent {
                sheetParent.endSheet(window)
            }
        }

        for window in NSApp.windows {
            if let mainWindow, window === mainWindow {
                continue
            }
            guard window.isVisible else { continue }
            window.orderOut(nil)
            window.close()
        }
    }

    private func presentMainWindow(reason: String) {
        if let mainWindow {
            if mainWindow.isMiniaturized {
                mainWindow.deminiaturize(nil)
            }
            configureMainWindowCollectionBehavior(mainWindow)
            mainWindow.setIsVisible(true)
            mainWindow.makeKeyAndOrderFront(nil)
            mainWindow.orderFrontRegardless()
            NSApp.activate(ignoringOtherApps: true)
            logMainWindowPresented(reason: reason, window: mainWindow, reused: true)
            return
        }

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 760),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = GrafAppChannel.current.displayName
        window.minSize = NSSize(width: 1040, height: 680)
        window.isReleasedWhenClosed = false
        window.isRestorable = false
        window.identifier = NSUserInterfaceItemIdentifier("graf-main-window")
        window.delegate = self
        configureMainWindowCollectionBehavior(window)
        window.contentViewController = NSHostingController(
            rootView: AppContentRoot(
                workspaceZoomStore: workspaceZoomStore,
                appUpdateController: appUpdateController
            )
        )
        if let frame = interfacePreferences.windowFrame,
           let screen = NSScreen.screens.first(where: { $0.visibleFrame.intersects(frame) }) ?? NSScreen.main {
            window.setFrame(InterfacePreferencesStore.clampedFrame(frame, to: screen.visibleFrame), display: false)
        } else {
            window.center()
        }
        mainWindow = window
        window.makeKeyAndOrderFront(nil)
        window.orderFrontRegardless()
        NSApp.activate(ignoringOtherApps: true)
        logMainWindowPresented(reason: reason, window: window, reused: false)
    }

    private func logMainWindowPresented(reason: String, window: NSWindow, reused: Bool) {
        guard window.isVisible else {
            AppLog.writeRaw(
                event: "app_main_window_presentation_failed",
                detail: "reason=\(reason) reused=\(reused) visible=false"
            )
            return
        }
        AppLog.writeRaw(
            event: "app_main_window_presented",
            detail: "reason=\(reason) reused=\(reused) visible=true"
        )
    }

    private func configureMainWindowCollectionBehavior(_ window: NSWindow) {
        window.collectionBehavior = [
            .managed,
            .moveToActiveSpace,
            .fullScreenAuxiliary
        ]
    }

    private func logWindowVisibility() {
        let visibleWindowCount = NSApp.windows.filter { $0.isVisible }.count
        let mainWindowState = mainWindow.map {
            "mainWindowVisible=\($0.isVisible) key=\($0.isKeyWindow) miniaturized=\($0.isMiniaturized) activeSpace=\($0.isOnActiveSpace) occlusion=\($0.occlusionState.rawValue)"
        } ?? "mainWindowVisible=false key=false miniaturized=false activeSpace=false occlusion=0"
        AppLog.writeRaw(
            event: "app_window_visibility_checked",
            detail: "visibleWindowCount=\(visibleWindowCount) \(mainWindowState)"
        )
        if visibleWindowCount == 0 {
            presentMainWindow(reason: "visibility_recovery")
        }
    }

    @objc func increaseWorkspaceZoom(_: Any?) {
        workspaceZoomStore.apply(.increase)
    }

    @objc func decreaseWorkspaceZoom(_: Any?) {
        workspaceZoomStore.apply(.decrease)
    }

    @objc func resetWorkspaceZoom(_: Any?) {
        workspaceZoomStore.apply(.reset)
    }

    @objc func openSettings(_: Any?) { openSettingsSection("account") }

    private func openSettingsSection(_ section: String, retry: Bool = false) {
        presentMainWindow(reason: "settings")
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .twoBrainRecOpenSettings, object: nil, userInfo: ["section": section, "retry": retry])
        }
    }

    func openLocalRecordingSettings() { openSettingsSection("recording") }
    func closeSettingsFallback() { settingsWindow?.close() }
    func presentSettingsFallback(section: String) {
        presentSettingsWindow(reason: "cabinet_unavailable", section: section)
    }

    @objc func stopRecordingFromMenu(_: Any?) {
        let snapshot = DesktopControlModel.shared.snapshot
        guard !snapshot.stopping, snapshot.active || snapshot.transitioning else { return }
        AppLog.writeRaw(event: "capture_control.action_dispatched", detail: "source=application_menu action=stop")
        _ = DesktopControlModel.shared.send(.stop)
    }

    @objc func openGrafMenu(_: Any?) {
        calendarTrayController?.showMenu()
    }

    @objc func focusNotification(_: Any?) {
        DesktopNotificationPresenter.shared.focusCurrentNotification()
    }

    private func captureCommandFromTray(_ action: DesktopControlAction) {
        AppLog.writeRaw(event: "capture_control.action_dispatched", detail: "source=tray action=\(action)")
        guard DesktopControlModel.shared.send(action) else {
            // Never queue a Start that might unexpectedly run after initialization.
            presentMainWindow(reason: "capture_control_unavailable")
            let alert = NSAlert()
            alert.messageText = "Управление записью еще не готово"
            alert.informativeText = "Команда не выполнена. Повторите попытку, когда GRAF откроется."
            alert.addButton(withTitle: "Понятно")
            if let mainWindow { alert.beginSheetModal(for: mainWindow) }
            return
        }
    }

    func openMeetingsFromTray() {
        presentMainWindow(reason: "calendar_tray")
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .twoBrainRecOpenMeetingsFromTray, object: nil)
        }
    }

    @objc func checkForUpdates(_ sender: Any?) {
        guard appUpdateController.checkForUpdates(sender) else {
            presentMainWindow(reason: "update_check_unavailable")
            let alert = NSAlert()
            alert.alertStyle = .informational
            alert.messageText = "Проверка обновлений недоступна"
            alert.informativeText = appUpdateController.presentation.message
                ?? "Эта сборка GRAF не содержит полной доверенной конфигурации обновлений."
            alert.addButton(withTitle: "Понятно")
            if let mainWindow {
                alert.beginSheetModal(for: mainWindow)
            } else {
                alert.runModal()
            }
            return
        }
        NSApp.activate(ignoringOtherApps: true)
    }

    func validateMenuItem(_ menuItem: NSMenuItem) -> Bool {
        if menuItem.action == #selector(focusNotification(_:)) {
            return DesktopNotificationPresenter.shared.card.isVisible
        }
        if menuItem.action == #selector(stopRecordingFromMenu(_:)) {
            let snapshot = DesktopControlModel.shared.snapshot
            return !snapshot.stopping && (snapshot.active || snapshot.transitioning)
        }
        guard menuItem.action == #selector(checkForUpdates(_:)) else { return true }
        menuItem.title = appUpdateController.presentation.menuItemTitle
        return appUpdateController.isManualCheckActionEnabled
    }

    private func presentSettingsWindow(reason: String, section: String) {
        Task { await DesktopNotificationPresenter.shared.refreshContext() }
        if let settingsWindow {
            let frame = settingsWindow.frame
            settingsWindow.contentViewController = NSHostingController(rootView: LocalSettingsFallbackView(section: section, onOpenAll: { [weak self] in self?.openSettingsSection("account", retry: true) }))
            settingsWindow.setFrame(frame, display: false)
            if settingsWindow.isMiniaturized {
                settingsWindow.deminiaturize(nil)
            }
            settingsWindow.setIsVisible(true)
            settingsWindow.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            AppLog.writeRaw(
                event: "app_settings_window_presented",
                detail: "reason=\(reason) reused=true"
            )
            return
        }

        let window = NSWindow(
            contentRect: NSRect(origin: .zero, size: MeetingDetectionSettingsView.windowSize),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = MeetingDetectionSettingsView.windowTitle
        window.minSize = NSSize(width: 820, height: 680)
        window.isReleasedWhenClosed = false
        window.isRestorable = false
        window.identifier = NSUserInterfaceItemIdentifier("graf-settings-window")
        window.contentViewController = NSHostingController(rootView: LocalSettingsFallbackView(
            section: section, onOpenAll: { [weak self] in self?.openSettingsSection("account", retry: true) }
        ))
        window.setContentSize(MeetingDetectionSettingsView.windowSize)
        window.center()
        if let screen = window.screen ?? NSScreen.main {
            let available = screen.visibleFrame.insetBy(dx: 16, dy: 16)
            var frame = window.frame
            frame.size.width = min(frame.width, available.width)
            frame.size.height = min(frame.height, available.height)
            frame.origin = NSPoint(x: available.midX - frame.width / 2, y: available.midY - frame.height / 2)
            window.minSize = NSSize(width: min(window.minSize.width, frame.width), height: min(window.minSize.height, frame.height))
            window.setFrame(frame, display: false)
        }
        settingsWindow = window
        AppLog.writeRaw(
            event: "app_settings_window_presented",
            detail: "reason=\(reason) reused=false"
        )
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}

extension Notification.Name {
    static let twoBrainRecDismissMeetingDetectionPrompt = Notification.Name("pro.2brain.graf.dismissMeetingDetectionPrompt")
    static let twoBrainRecApplicationShouldTerminate = Notification.Name("pro.2brain.graf.applicationShouldTerminate")
    static let twoBrainRecApplicationTerminationCleanupFinished = Notification.Name("pro.2brain.graf.applicationTerminationCleanupFinished")
    static let twoBrainRecOpenSettings = Notification.Name("pro.2brain.graf.openSettings")
    static let twoBrainRecOpenMeetingsFromTray = Notification.Name("pro.2brain.graf.openMeetingsFromTray")
}
