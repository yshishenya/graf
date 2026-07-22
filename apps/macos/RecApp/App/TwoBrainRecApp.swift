import AppKit
import Network
import SwiftUI
import TwoBrainRecAppCore
import TwoBrainRecShared

@main
private enum TwoBrainRecAppMain {
    @MainActor
    static func main() {
        let app = NSApplication.shared
        let appDelegate = AppLifecycleDelegate()
        installMainMenu(on: app, zoomTarget: appDelegate)
        app.delegate = appDelegate
        withExtendedLifetime(appDelegate) {
            app.run()
        }
    }

    @MainActor
    private static func installMainMenu(on app: NSApplication, zoomTarget: AnyObject) {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu(title: "GRAF")
        appMenuItem.submenu = appMenu
        appMenu.addItem(
            withTitle: "About GRAF",
            action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)),
            keyEquivalent: ""
        )
        let updateItem = appMenu.addItem(
            withTitle: "Check for Updates…",
            action: #selector(AppLifecycleDelegate.checkForUpdates(_:)),
            keyEquivalent: ""
        )
        updateItem.target = zoomTarget
        appMenu.addItem(NSMenuItem.separator())
        let settingsItem = appMenu.addItem(
            withTitle: "Settings...",
            action: #selector(AppLifecycleDelegate.openSettings(_:)),
            keyEquivalent: ","
        )
        settingsItem.target = zoomTarget
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(
            withTitle: "Hide GRAF",
            action: #selector(NSApplication.hide(_:)),
            keyEquivalent: "h"
        )
        let hideOthersItem = appMenu.addItem(
            withTitle: "Hide Others",
            action: #selector(NSApplication.hideOtherApplications(_:)),
            keyEquivalent: "h"
        )
        hideOthersItem.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(
            withTitle: "Show All",
            action: #selector(NSApplication.unhideAllApplications(_:)),
            keyEquivalent: ""
        )
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(
            withTitle: "Quit GRAF",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q"
        )

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "Edit")
        editMenuItem.submenu = editMenu
        editMenu.addItem(withTitle: "Undo", action: NSSelectorFromString("undo:"), keyEquivalent: "z")
        let redoItem = editMenu.addItem(
            withTitle: "Redo",
            action: NSSelectorFromString("redo:"),
            keyEquivalent: "z"
        )
        redoItem.keyEquivalentModifierMask = [.command, .shift]
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        let pasteAndMatchItem = editMenu.addItem(
            withTitle: "Paste and Match Style",
            action: #selector(NSTextView.pasteAsPlainText(_:)),
            keyEquivalent: "v"
        )
        pasteAndMatchItem.keyEquivalentModifierMask = [.command, .option, .shift]
        editMenu.addItem(withTitle: "Delete", action: #selector(NSText.delete(_:)), keyEquivalent: "")
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")

        let viewMenuItem = NSMenuItem()
        mainMenu.addItem(viewMenuItem)
        let viewMenu = NSMenu(title: "View")
        viewMenuItem.submenu = viewMenu
        for item in WorkspaceZoomMenu.items {
            let menuItem = NSMenuItem(
                title: item.title,
                action: selector(for: item.command),
                keyEquivalent: item.keyEquivalent
            )
            menuItem.target = zoomTarget
            viewMenu.addItem(menuItem)
        }

        let windowMenuItem = NSMenuItem()
        mainMenu.addItem(windowMenuItem)
        let windowMenu = NSMenu(title: "Window")
        windowMenuItem.submenu = windowMenu
        windowMenu.addItem(
            withTitle: "Minimize",
            action: #selector(NSWindow.miniaturize(_:)),
            keyEquivalent: "m"
        )
        windowMenu.addItem(
            withTitle: "Zoom",
            action: #selector(NSWindow.zoom(_:)),
            keyEquivalent: ""
        )

        app.windowsMenu = windowMenu
        app.mainMenu = mainMenu
    }

    private static func selector(for command: WorkspaceZoomCommand) -> Selector {
        switch command {
        case .increase:
            return #selector(AppLifecycleDelegate.increaseWorkspaceZoom(_:))
        case .decrease:
            return #selector(AppLifecycleDelegate.decreaseWorkspaceZoom(_:))
        case .reset:
            return #selector(AppLifecycleDelegate.resetWorkspaceZoom(_:))
        }
    }
}

private struct ContentView: View {
    private let meetingDetectionRegistryRefreshIntervalNanoseconds: UInt64 = 3_600_000_000_000
    private static let meetingDetectionPromptWindowSize = NSSize(width: 360, height: 286)
    private static let meetingDetectionPromptVisibleMargin: CGFloat = 22

    @ObservedObject private var appUpdateController: AppUpdateController
    @State private var captureController = CaptureSessionController()
    @State private var localRecordingWriter = LocalRecordingWriter()
    @State private var systemAudioCaptureService = SystemAudioCaptureService(
        runtimeStartFailureLogger: { detail in
            AppLog.writeRaw(event: "system_audio.runtime_start_failed", detail: detail)
        }
    )
    @State private var microphoneCaptureService = MicrophoneCaptureService()
    @State private var systemAudioPermissionAuthorizer = CoreGraphicsSystemAudioPermissionAuthorizer()
    @State private var systemAudioPermissionGate = SystemAudioPermissionGate()
    @State private var captureScopeApprovalService = CaptureScopeApprovalService()
    @State private var meetingMuteTruthService = MeetingMuteTruthService()
    @State private var captureSession: CaptureSession?
    @State private var recordingBlocker: String?
    @State private var recordingEvidenceEvents: [RecordingEvidenceEvent] = []
    @State private var localRecordingManifest: LocalRecordingManifest?
    @State private var selectedRecordingMicrophoneDeviceId: String?
    @State private var recordingMicrophoneSelection: RecordingMicrophoneSelection?
    @State private var activeMicrophoneSampleSource: AppOwnedMicrophoneSampleSource?
    @State private var desktopUploadQueueService = DesktopUploadQueueService()
    @State private var uploadQueueItems: [DesktopUploadQueueItem] = []
    @State private var desktopCalendarReminderService = DesktopCalendarReminderService()
    @State private var desktopCalendarPrompt: DesktopCalendarPrompt?
    @State private var desktopCalendarRefreshInProgress = false
    @State private var activeCalendarContextEventId: String?
    @State private var activeCalendarMatchAttemptId: String?
    @State private var activeCalendarMatchLocalRecordingId: String?
    @State private var meetingDetectionSettingsStore = MeetingDetectionSettingsStore()
    @State private var meetingDetectionSettings = MeetingDetectionSettings()
    @State private var meetingDetectionRegistryStore: MeetingTargetRegistryStore?
    @State private var meetingDetectionRegistry: MeetingTargetRegistryDocument?
    @State private var meetingDetectionDetector = MacOSMeetingActivityDetector()
    @State private var meetingDetectionRollupStore = MeetingDetectionTelemetryRollupStore()
    @State private var meetingDetectionTelemetryUploader: MeetingDetectionTelemetryUploader?
    @State private var meetingDetectionLogStream: MacOSAudioOwnershipLogStream?
    @State private var meetingDetectionTask: Task<Void, Never>?
    @State private var meetingDetectionAdvanceTask: Task<Void, Never>?
    @State private var meetingDetectionStatus = "Ожидает запуск"
    @State private var meetingDetectionPrompt: MeetingDetectionPrompt?
    @State private var meetingDetectionPromptWindow: NSWindow?
    @State private var liveRecordingLevels = LiveRecordingLevels.inactive
    @State private var localRecordingActive = false
    @State private var levelsPollInProgress = false
    @State private var uploadQueueRefreshInProgress = false
    @State private var uploadQueueFollowUpScheduled = false
    @State private var uploadQueueNetworkMonitor: NWPathMonitor?
    @State private var uploadQueueNetworkWasSatisfied = false
    @State private var terminationCleanupInProgress = false
    @State private var recordingStartInProgress = false
    @State private var recordingStopInProgress = false
    @State private var desktopCabinetConfiguration = DesktopCabinetConfiguration.configuredFromEnvironment()
    @State private var desktopCabinetState: DesktopCabinetState = DesktopCabinetConfiguration.configuredFromEnvironment() == nil ? .notConfigured : .loading
    @State private var selectedCabinetRoute: URL?
    @State private var supportIncidentBridge = EmbeddedCabinetSupportIncidentBridge()
    @State private var permissionOnboardingStatus = DesktopPermissionOnboardingStatus.unknown
    @State private var permissionOnboardingPresented = false
    @State private var permissionOnboardingRequestInProgress = false

    let workspaceZoom: WorkspaceZoomPreference

    init(
        appUpdateController: AppUpdateController,
        workspaceZoom: WorkspaceZoomPreference
    ) {
        _appUpdateController = ObservedObject(wrappedValue: appUpdateController)
        self.workspaceZoom = workspaceZoom
    }

    var body: some View {
        DesktopMeetingShellView(
            session: captureSession,
            uploadQueueItems: uploadQueueItems,
            cabinetConfigured: desktopCabinetConfiguration != nil,
            cabinetState: desktopCabinetState,
            startRecordingAvailable: CaptureControlView.shouldShowDirectRecordButton(
                for: captureSession,
                calendarPrompt: desktopCalendarPrompt
            ) && permissionOnboardingStatus.isReady && !recordingStartInProgress && !recordingStopInProgress,
            recordingTransitionInProgress: recordingStartInProgress || recordingStopInProgress,
            hasActionableCaptureProblem: CaptureControlView.hasActionableProblem(
                blockedReason: recordingBlocker
            ) || !permissionOnboardingStatus.isReady || desktopCalendarPrompt?.kind == .record,
            showsAppUpdateBadge: appUpdateController.presentation.showsSidebarBadge,
            onStartRecording: {
                Task { await startManualRecording() }
            },
            onStopRecording: {
                Task { await stopManualRecording() }
            },
            onPauseRecording: {
                Task { await pauseManualRecording() }
            },
            onResumeRecording: {
                Task { await resumeManualRecording() }
            },
            onOpenSettings: {
                (NSApp.delegate as? AppLifecycleDelegate)?.openSettings(nil)
            },
            onCheckForUpdates: {
                (NSApp.delegate as? AppLifecycleDelegate)?.checkForUpdates(nil)
            },
            onSupportIncidentReport: { itemIds in
                try await submitSupportIncidentReport(itemIds: itemIds)
            },
            onSupportIncidentSync: { itemIds in
                try await syncSupportIncident(itemIds: itemIds)
            },
            onCopySupportIncidentReport: { itemIds in
                try copySupportIncidentReport(itemIds: itemIds)
            },
            onOpenSupportSignIn: {
                openSupportSignIn()
            }
        ) {
            CaptureControlView(
                session: captureSession,
                blockedReason: recordingBlocker,
                localRecordingStatus: localRecordingStatusText,
                muteTruthWarning: meetingMuteTruthWarningText,
                recordingMicrophoneSelection: recordingMicrophoneSelection,
                recordingMicrophoneInputs: microphoneCaptureService.availableRecordingMicrophoneInputs(),
                selectedRecordingMicrophoneDeviceId: selectedRecordingMicrophoneDeviceId,
                calendarPrompt: desktopCalendarPrompt,
                meetingDetectionStatus: meetingDetectionStatus,
                readinessStatus: permissionOnboardingStatus,
                recordingLevels: liveRecordingLevels,
                recordDisabled: !permissionOnboardingStatus.isReady || recordingStartInProgress || recordingStopInProgress,
                stopDisabled: recordingStartInProgress || recordingStopInProgress,
                pauseDisabled: recordingStartInProgress || recordingStopInProgress,
                onRecord: {
                    Task { await startManualRecording() }
                },
                onStop: {
                    Task { await stopManualRecording() }
                },
                onPause: {
                    Task { await pauseManualRecording() }
                },
                onResume: {
                    Task { await resumeManualRecording() }
                },
                onSelectRecordingMicrophone: { inputDeviceId in
                    selectedRecordingMicrophoneDeviceId = inputDeviceId
                    recordingMicrophoneSelection = microphoneCaptureService.resolveRecordingMicrophoneSelection(
                        selectedInputDeviceId: inputDeviceId
                    )
                },
                onCalendarPromptPrimary: { prompt in
                    handleCalendarPromptPrimary(prompt)
                },
                onCalendarPromptDismiss: { prompt in
                    dismissCalendarPrompt(prompt)
                },
                onMeetingDetectionSettings: {
                    (NSApp.delegate as? AppLifecycleDelegate)?.openSettings(nil)
                },
                onPermissionRecovery: {
                    refreshPermissionOnboarding(reason: "capture_permission_recovery", presentIfNeeded: false)
                    permissionOnboardingPresented = true
                }
            )
            .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.captureRegion)
        } meetingsWorkspace: {
            DesktopCabinetWorkspaceView(
                configuration: desktopCabinetConfiguration,
                initialRoute: selectedCabinetRoute,
                currentRoute: $selectedCabinetRoute,
                cabinetState: $desktopCabinetState,
                presentation: .shell,
                workspaceZoom: workspaceZoom,
                navigationEventLogger: { event, detail in
                    AppLog.writeRaw(event: event, detail: detail)
                },
                showsAppUpdateBadge: appUpdateController.presentation.showsSidebarBadge,
                onCheckForUpdates: {
                    (NSApp.delegate as? AppLifecycleDelegate)?.checkForUpdates(nil)
                },
                supportIncidentBridge: supportIncidentBridge
            )
        }
        .sheet(isPresented: $permissionOnboardingPresented) {
            DesktopPermissionOnboardingView(
                status: permissionOnboardingStatus,
                isRequesting: permissionOnboardingRequestInProgress,
                onRequestMicrophone: {
                    Task { await requestStartupMicrophonePermission() }
                },
                onRequestSystemAudio: {
                    Task { await requestStartupSystemAudioPermission() }
                },
                onOpenMicrophoneSettings: {
                    openPermissionSettings(DesktopPermissionOnboardingSettings.microphoneURL)
                },
                onOpenSystemAudioSettings: {
                    openPermissionSettings(DesktopPermissionOnboardingSettings.screenAndSystemAudioURL)
                },
                onDismiss: {
                    permissionOnboardingPresented = false
                },
                onFinish: {
                    permissionOnboardingPresented = false
                }
            )
        }
        .onAppear {
            AppLog.writeRaw(
                event: "app_opened",
                detail: "capture=app_owned_system_audio microphone=app_owned"
            )
            refreshPermissionOnboarding(reason: "app_appeared", presentIfNeeded: true)
            refreshUploadQueueAndProcess(reason: "app_appeared")
            startUploadQueueNetworkMonitorIfNeeded()
            startMeetingDetectionIfNeeded()
            appUpdateController.updateProtectedWork(protectedUpdateWork)
        }
        .onChange(of: protectedUpdateWork) { _, work in
            appUpdateController.updateProtectedWork(work)
        }
        .onReceive(NotificationCenter.default.publisher(for: .twoBrainRecMeetingDetectionSettingsDidChange)) { _ in
            reloadMeetingDetectionSettings()
        }
        .task {
            while !Task.isCancelled {
                await refreshCalendarReminder(reason: "calendar_poll")
                try? await Task.sleep(nanoseconds: 30_000_000_000)
            }
        }
        .task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: meetingDetectionRegistryRefreshIntervalNanoseconds)
                await refreshMeetingDetectionRegistry(reason: "periodic_registry_refresh")
            }
        }
        .task(id: localRecordingActive) {
            guard localRecordingActive else { return }
            while !Task.isCancelled {
                pollRecordingLevelsIfNeeded()
                try? await Task.sleep(nanoseconds: 200_000_000)
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .twoBrainRecApplicationShouldTerminate)) { _ in
            permissionOnboardingPresented = false
            permissionOnboardingRequestInProgress = false
            dismissMeetingDetectionPrompt()
            guard !terminationCleanupInProgress else { return }
            terminationCleanupInProgress = true
            Task {
                await releaseCaptureResourcesForAppExit()
                await MainActor.run {
                    NotificationCenter.default.post(name: .twoBrainRecApplicationTerminationCleanupFinished, object: nil)
                }
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .twoBrainRecDesktopAuthSessionDidChange)) { _ in
            refreshUploadQueueAndProcess(reason: "desktop_auth_session_changed")
            Task { await refreshCalendarReminder(reason: "desktop_auth_session_changed") }
            Task { await refreshMeetingDetectionRegistry(reason: "desktop_auth_session_changed") }
        }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
            refreshPermissionOnboarding(reason: "app_became_active", presentIfNeeded: false)
            refreshUploadQueueAndProcess(reason: "app_became_active")
            Task { await refreshCalendarReminder(reason: "app_became_active") }
            Task { await refreshMeetingDetectionRegistry(reason: "app_became_active") }
        }
        .onReceive(NSWorkspace.shared.notificationCenter.publisher(for: NSWorkspace.didWakeNotification)) { _ in
            refreshUploadQueueAndProcess(reason: "system_wake")
            Task { await refreshCalendarReminder(reason: "system_wake") }
            Task { await refreshMeetingDetectionRegistry(reason: "system_wake") }
            Task { await uploadMeetingDetectionTelemetry(reason: "system_wake") }
        }
        .onDisappear {
            guard !terminationCleanupInProgress else { return }
            stopMeetingDetection()
            Task { await releaseCaptureResourcesForAppExit() }
        }
    }

    private var protectedUpdateWork: ProtectedUpdateWork {
        ProtectedUpdateWork(
            captureActive: captureSession.map { CaptureStatusItem.showsStopButton(for: $0) } == true || localRecordingActive,
            captureTransitioning: recordingStartInProgress || recordingStopInProgress,
            recordingFinalizing: recordingStopInProgress,
            terminationCleanupPending: terminationCleanupInProgress
        )
    }

    @MainActor
    private func refreshPermissionOnboarding(reason: String, presentIfNeeded: Bool) {
        let status = DesktopPermissionOnboardingStatus(
            microphone: microphoneCaptureService.preflight(
                sessionId: "startup-permission-onboarding"
            ).permissionState,
            systemAudio: systemAudioPermissionAuthorizer.currentPermissionState()
        )
        permissionOnboardingStatus = status

        if status.isReady {
            permissionOnboardingPresented = false
        } else {
            if presentIfNeeded {
                permissionOnboardingPresented = true
            }
        }

        AppLog.writeRaw(
            event: "desktop.permission_onboarding_checked",
            detail: "reason=\(reason) microphone=\(status.microphone.rawValue) systemAudio=\(status.systemAudio.rawValue) ready=\(status.isReady)"
        )
    }

    @MainActor
    private func requestStartupMicrophonePermission() async {
        guard !permissionOnboardingRequestInProgress else { return }
        permissionOnboardingRequestInProgress = true
        defer { permissionOnboardingRequestInProgress = false }

        let selection = microphoneCaptureService.resolveRecordingMicrophoneSelection(
            selectedInputDeviceId: selectedRecordingMicrophoneDeviceId
        )
        recordingMicrophoneSelection = selection
        _ = await microphoneCaptureService.requestPermissionAndPreflight(
            sessionId: "startup-permission-onboarding",
            inputDeviceId: selection.inputDeviceId,
            inputDisplayName: selection.inputDisplayName ?? "Default Microphone"
        )
        refreshPermissionOnboarding(reason: "microphone_permission_requested", presentIfNeeded: false)
    }

    @MainActor
    private func requestStartupSystemAudioPermission() async {
        guard !permissionOnboardingRequestInProgress else { return }
        permissionOnboardingRequestInProgress = true
        defer { permissionOnboardingRequestInProgress = false }

        _ = await systemAudioPermissionAuthorizer.requestPermission()
        refreshPermissionOnboarding(reason: "system_audio_permission_requested", presentIfNeeded: false)
    }

    @MainActor
    private func openPermissionSettings(_ url: URL) {
        NSWorkspace.shared.open(url)
    }

    @MainActor
    private func refreshCalendarReminder(reason: String) async {
        guard !desktopCalendarRefreshInProgress else { return }
        guard let client = DesktopUploadClient.configuredFromEnvironment() else {
            desktopCalendarPrompt = nil
            return
        }

        desktopCalendarRefreshInProgress = true
        defer { desktopCalendarRefreshInProgress = false }

        do {
            let response = try await client.listDesktopCalendarUpcoming()
            desktopCalendarPrompt = desktopCalendarReminderService.activePrompt(
                from: response.events,
                now: Date(),
                isRecordingActive: calendarPromptRecordingIsActive
            )
        } catch {
            desktopCalendarPrompt = nil
            AppLog.writeRaw(
                event: "calendar.prompt_unavailable",
                detail: "reason=\(reason) error=calendar_unavailable"
            )
        }
    }

    @MainActor
    private func handleCalendarPromptPrimary(_ prompt: DesktopCalendarPrompt) {
        let actions = DesktopCalendarPromptActions(
            openURL: { url in
                NSWorkspace.shared.open(url)
            },
            startRecording: { decisionIntent, eventId in
                Task {
                    await startManualRecording(
                        calendarContextEventId: eventId,
                        calendarMatchDecisionIntent: decisionIntent
                    )
                }
            },
            dismiss: { dismissed in
                dismissCalendarPrompt(dismissed)
            }
        )
        actions.performPrimaryAction(for: prompt)
    }

    @MainActor
    private func dismissCalendarPrompt(_ prompt: DesktopCalendarPrompt) {
        desktopCalendarReminderService.dismiss(prompt)
        if desktopCalendarPrompt?.id == prompt.id {
            desktopCalendarPrompt = nil
        }
    }

    private var calendarPromptRecordingIsActive: Bool {
        localRecordingActive ||
            recordingStartInProgress ||
            recordingStopInProgress ||
            captureSession.map { CaptureStatusItem.showsStopButton(for: $0) } == true
    }

    @MainActor
    private func reloadMeetingDetectionSettings() {
        do {
            let previousMode = meetingDetectionSettings.detectionMode
            meetingDetectionSettings = try meetingDetectionSettingsStore.load()
            if previousMode == .detectAndAsk,
               meetingDetectionSettings.detectionMode != .detectAndAsk {
                dismissMeetingDetectionPrompt()
            }
            startMeetingDetectionIfNeeded()
            meetingDetectionStatus = meetingDetectionStatusText()
        } catch {
            AppLog.writeRaw(event: "meeting_detection.settings_reload_failed", detail: "error=settings_unavailable")
        }
    }

    @MainActor
    private func startMeetingDetectionIfNeeded() {
        guard meetingDetectionTask == nil else { return }
        do {
            meetingDetectionSettings = try meetingDetectionSettingsStore.load()
        } catch {
            meetingDetectionStatus = "Недоступно"
            AppLog.writeRaw(event: "meeting_detection.start_failed", detail: "error=settings_unavailable")
            return
        }
        meetingDetectionRegistryStore = buildMeetingDetectionRegistryStore()
        if (try? resolveMeetingDetectionRegistry(remoteData: nil, remoteETag: nil)) == nil {
            meetingDetectionRegistry = nil
            AppLog.writeRaw(
                event: "meeting_detection.registry_cache_unavailable",
                detail: "awaitingRemote=true"
            )
        }
        configureMeetingDetectionUploaderIfNeeded()
        meetingDetectionStatus = meetingDetectionStatusText()

        let logStream = MacOSAudioOwnershipLogStream()
        meetingDetectionLogStream = logStream
        meetingDetectionTask = Task {
            for await event in logStream.events() {
                await handleMeetingDetectionAudioOwnershipEvent(event)
            }
        }
        meetingDetectionAdvanceTask = Task {
            while !Task.isCancelled {
                await advanceMeetingDetection(reason: "timer")
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }
        }
        Task {
            await refreshMeetingDetectionRegistry(reason: "startup")
            await uploadMeetingDetectionTelemetry(reason: "startup")
        }
        AppLog.writeRaw(event: "meeting_detection.started", detail: "mode=\(meetingDetectionSettings.detectionMode.rawValue)")
    }

    @MainActor
    private func stopMeetingDetection() {
        meetingDetectionAdvanceTask?.cancel()
        meetingDetectionAdvanceTask = nil
        meetingDetectionTask?.cancel()
        meetingDetectionTask = nil
        meetingDetectionLogStream?.stop()
        meetingDetectionLogStream = nil
    }

    private func buildMeetingDetectionRegistryStore() -> MeetingTargetRegistryStore {
        MeetingTargetRegistryStore(cacheURL: MeetingDetectionAppModule.targetRegistryCacheURL())
    }

    @MainActor
    private func resolveMeetingDetectionRegistry(remoteData: Data?, remoteETag: String?) throws {
        let store: MeetingTargetRegistryStore
        if let existing = meetingDetectionRegistryStore {
            store = existing
        } else {
            store = buildMeetingDetectionRegistryStore()
            meetingDetectionRegistryStore = store
        }
        let resolution = try store.resolve(remoteData: remoteData, remoteETag: remoteETag)
        meetingDetectionRegistry = resolution.document
        AppLog.writeRaw(
            event: "meeting_detection.registry_resolved",
            detail: "version=\(resolution.document.registryVersion) source=\(resolution.source.rawValue)"
        )
        NotificationCenter.default.post(name: .twoBrainRecMeetingTargetRegistryDidChange, object: nil)
    }

    @MainActor
    private func configureMeetingDetectionUploaderIfNeeded() {
        guard meetingDetectionTelemetryUploader == nil,
              let client = DesktopUploadClient.configuredFromEnvironment()
        else {
            return
        }
        meetingDetectionTelemetryUploader = MeetingDetectionTelemetryUploader(
            rollupStore: meetingDetectionRollupStore,
            settingsStore: meetingDetectionSettingsStore,
            transport: client,
            stateURL: MeetingDetectionAppModule.telemetryUploaderStateURL()
        )
    }

    @MainActor
    private func refreshMeetingDetectionRegistry(reason: String) async {
        guard let client = DesktopUploadClient.configuredFromEnvironment() else {
            meetingDetectionStatus = meetingDetectionStatusText()
            return
        }
        do {
            let etag = meetingDetectionRegistry?.etag
            let fetched = try await client.fetchMeetingDetectionTargetRegistry(ifNoneMatch: etag)
            if let registry = fetched.registry {
                let data = try MeetingDetectionCoding.encoder().encode(registry)
                try resolveMeetingDetectionRegistry(remoteData: data, remoteETag: fetched.etag)
            }
            meetingDetectionStatus = meetingDetectionStatusText()
        } catch let refreshError {
            var fallbackErrorCode: String?
            do {
                try resolveMeetingDetectionRegistry(remoteData: nil, remoteETag: nil)
            } catch let fallbackError {
                fallbackErrorCode = safeMeetingDetectionRegistryRefreshErrorCode(fallbackError)
                meetingDetectionRegistry = nil
            }
            meetingDetectionStatus = meetingDetectionStatusText()
            let fallbackDetail = fallbackErrorCode.map { " fallback=\($0)" } ?? ""
            AppLog.writeRaw(
                event: "meeting_detection.registry_refresh_failed",
                detail: "reason=\(reason) error=\(safeMeetingDetectionRegistryRefreshErrorCode(refreshError))\(fallbackDetail)"
            )
        }
    }

    private func safeMeetingDetectionRegistryRefreshErrorCode(_ error: Error) -> String {
        if case DesktopUploadClientError.httpStatus(let status, let code) = error {
            return "http_status_\(status):\(code)"
        }
        if let registryError = error as? MeetingTargetRegistryError {
            return "registry_\(registryError.description)"
        }
        if let decodingError = error as? DecodingError {
            return safeRegistryDecodingErrorCode(decodingError)
        }
        return "registry_unavailable"
    }

    private func safeRegistryDecodingErrorCode(_ error: DecodingError) -> String {
        func path(_ context: DecodingError.Context) -> String {
            let value = context.codingPath.map(\.stringValue).joined(separator: ".")
            return value.isEmpty ? "root" : value
        }
        func detail(_ context: DecodingError.Context) -> String {
            context.debugDescription
                .replacingOccurrences(of: " ", with: "_")
                .replacingOccurrences(of: "\n", with: "_")
                .prefix(160)
                .description
        }
        switch error {
        case .dataCorrupted(let context):
            return "registry_decode_data_corrupted:\(path(context)):\(detail(context))"
        case .keyNotFound(let key, let context):
            let parent = path(context)
            return "registry_decode_key_not_found:\(parent).\(key.stringValue):\(detail(context))"
        case .typeMismatch(_, let context):
            return "registry_decode_type_mismatch:\(path(context)):\(detail(context))"
        case .valueNotFound(_, let context):
            return "registry_decode_value_not_found:\(path(context)):\(detail(context))"
        @unknown default:
            return "registry_decode_failed"
        }
    }

    @MainActor
    private func handleMeetingDetectionAudioOwnershipEvent(_ event: MacOSAudioOwnershipEvent) async {
        guard let registry = meetingDetectionRegistry else { return }
        let outputs = meetingDetectionDetector.handle(
            event: event,
            registry: registry,
            settings: meetingDetectionSettings,
            prerequisites: meetingDetectionPrerequisites()
        )
        processMeetingDetectionOutputs(outputs, registry: registry)
        await advanceMeetingDetection(reason: "mic_event")
    }

    @MainActor
    private func advanceMeetingDetection(reason _: String) async {
        guard let registry = meetingDetectionRegistry else { return }
        let outputs = meetingDetectionDetector.advance(
            registry: registry,
            settings: meetingDetectionSettings,
            prerequisites: meetingDetectionPrerequisites()
        )
        processMeetingDetectionOutputs(outputs, registry: registry)
    }

    @MainActor
    private func processMeetingDetectionOutputs(
        _ outputs: [MacOSMeetingActivityDetectorOutput],
        registry: MeetingTargetRegistryDocument
    ) {
        for output in outputs {
            switch output {
            case .promptEligible(let targetID, let bundleID):
                guard !calendarPromptRecordingIsActive else { continue }
                let displayName = registry.targets.first { $0.id == targetID }?.displayName ?? bundleID
                let prerequisites = meetingDetectionPrerequisites()
                let prompt = MeetingDetectionPrompt(
                    targetID: targetID,
                    bundleID: bundleID,
                    displayName: displayName,
                    captureMode: "Режим: аудиозапись встречи",
                    captureSources: "Источники: системный звук и микрофон",
                    workspacePolicyState: meetingDetectionPolicyStateText(for: prerequisites),
                    detectorReason: "Сигнал: приложение использует аудио встречи"
                )
                meetingDetectionPrompt = prompt
                presentMeetingDetectionPrompt(prompt)
                meetingDetectionStatus = "Найдена встреча: \(displayName)"
            case .candidateObserved(
                bundleID: _,
                score: _,
                observation: let observation,
                decision: let decision
            ):
                do {
                    _ = try meetingDetectionRollupStore.recordObservation(
                        observation,
                        decision: decision,
                        registryVersion: registry.registryVersion,
                        settings: meetingDetectionSettings
                    )
                    Task { await uploadMeetingDetectionTelemetry(reason: "candidate_observed") }
                    meetingDetectionStatus = "Найден кандидат для проверки"
                } catch {
                    AppLog.writeRaw(event: "meeting_detection.rollup_failed", detail: "error=local_rollup_unavailable")
                }
            case .suppressed:
                meetingDetectionStatus = meetingDetectionStatusText()
            case .ended(let bundleID):
                if meetingDetectionPrompt?.bundleID == bundleID {
                    dismissMeetingDetectionPrompt()
                }
                stopMeetingDetectionRecordingIfNeeded(bundleID: bundleID)
                meetingDetectionStatus = meetingDetectionStatusText()
            }
        }
    }

    @MainActor
    private func stopMeetingDetectionRecordingIfNeeded(bundleID: String) {
        guard let session = captureSession,
              session.triggerEvidence["meetingDetectionBundleId"] == bundleID,
              CaptureStatusItem.showsStopButton(for: session)
        else {
            return
        }
        AppLog.writeRaw(
            event: "meeting_detection.recording_stop_requested",
            detail: "sessionId=\(session.id) bundleID=\(bundleID) reason=meeting_ended"
        )
        Task {
            await stopManualRecording(
                reason: .meetingEnded,
                evidenceInitiator: .systemFailClosed,
                enqueueReason: "meeting_detection_target_ended"
            )
        }
    }

    @MainActor
    private func uploadMeetingDetectionTelemetry(reason: String) async {
        configureMeetingDetectionUploaderIfNeeded()
        guard let uploader = meetingDetectionTelemetryUploader else { return }
        do {
            let outcome = try await uploader.uploadPending()
            AppLog.writeRaw(
                event: "meeting_detection.telemetry_upload_completed",
                detail: "reason=\(reason) uploadedCount=\(outcome.uploadedCount) skipped=\(outcome.skippedReason != nil)"
            )
        } catch {
            AppLog.writeRaw(event: "meeting_detection.telemetry_upload_failed", detail: "reason=\(reason) error=upload_unavailable")
        }
    }

    @MainActor
    private func meetingDetectionPrerequisites() -> MeetingDetectionCapturePrerequisites {
        let currentMicrophone = microphoneCaptureService.preflight(sessionId: "meeting-detection-preflight")
        let currentSystemAudio = systemAudioPermissionAuthorizer.currentPermissionState()
        let permissionGate = systemAudioPermissionGate.evaluate(
            microphone: currentMicrophone.permissionState,
            systemAudio: currentSystemAudio
        )
        let prerequisite = evaluatedMeetingDetectionRecordingPrerequisite(
            permissions: permissionGate.snapshot
        )
        return MeetingDetectionCapturePrerequisites(
            recordingAlreadyActive: calendarPromptRecordingIsActive,
            visibleRecordingStateAvailable: prerequisite.indicatorAvailable,
            oneActionStopAvailable: meetingDetectionOneActionStopAvailable,
            captureRouteReady: !recordingStartInProgress && !recordingStopInProgress,
            recordingPrerequisite: prerequisite
        )
    }

    @MainActor
    private var meetingDetectionOneActionStopAvailable: Bool {
        !recordingStartInProgress && !recordingStopInProgress
    }

    @MainActor
    private var meetingDetectionVisibleIndicatorAvailable: Bool {
        guard let captureSession else { return true }
        return captureSession.visibleIndicatorState != .hidden ||
            CaptureControlView.shouldShowRecordButton(for: captureSession)
    }

    @MainActor
    private var meetingDetectionWorkspacePolicyAllowsRecording: Bool {
        captureSession?.sourceAppEligibility != .policyBlocked
    }

    @MainActor
    private func evaluatedMeetingDetectionRecordingPrerequisite(
        permissions: SystemAudioPermissionSnapshot
    ) -> RecordingPrerequisiteSnapshot {
        RecordingPrerequisiteGate().evaluate(
            RecordingPrerequisiteSnapshot(
                policyAllowsRecording: meetingDetectionWorkspacePolicyAllowsRecording,
                microphonePermissionGranted: permissions.microphone == .granted,
                systemAudioPermissionGranted: permissions.systemAudio == .granted,
                storageRisk: .healthy,
                indicatorAvailable: meetingDetectionVisibleIndicatorAvailable,
                sourceAppEligibility: meetingDetectionWorkspacePolicyAllowsRecording ? .eligible : .policyBlocked,
                evaluatedAt: Date()
            )
        )
    }

    @MainActor
    private func meetingDetectionPolicyStateText(
        for prerequisites: MeetingDetectionCapturePrerequisites
    ) -> String {
        guard let prerequisite = prerequisites.recordingPrerequisite else {
            return "Политика: проверяется"
        }
        if prerequisite.policyAllowsRecording, prerequisite.blockedReason != .policyDisabled {
            return "Политика: запись разрешена"
        }
        return "Политика: запись недоступна"
    }

    @MainActor
    private func meetingDetectionStatusText() -> String {
        switch meetingDetectionSettings.detectionMode {
        case .detectOnly:
            return "Запрос записи отключен"
        case .detectAndAsk:
            return "Запрашивать запись включено"
        }
    }

    @MainActor
    private func presentMeetingDetectionPrompt(_ prompt: MeetingDetectionPrompt) {
        dismissMeetingDetectionPromptWindow()
        let promptWindowSize = Self.meetingDetectionPromptWindowSize

        let window = NSPanel(
            contentRect: NSRect(origin: .zero, size: promptWindowSize),
            styleMask: [.borderless, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.level = .statusBar
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .transient]
        window.backgroundColor = .clear
        window.isOpaque = false
        window.hasShadow = true
        window.hidesOnDeactivate = false
        window.isReleasedWhenClosed = false
        window.isMovableByWindowBackground = true
        window.identifier = NSUserInterfaceItemIdentifier("graf-meeting-detection-prompt")
        let hostingController = NSHostingController(
            rootView: MeetingDetectionPromptView(
                prompt: prompt,
                isStartDisabled: recordingStartInProgress || recordingStopInProgress || calendarPromptRecordingIsActive,
                onStart: {
                    acceptMeetingDetectionPrompt(prompt)
                },
                onDismiss: {
                    dismissMeetingDetectionPrompt()
                }
            )
            .frame(width: promptWindowSize.width, height: promptWindowSize.height)
        )
        hostingController.view.frame = NSRect(origin: .zero, size: promptWindowSize)
        window.contentViewController = hostingController
        window.minSize = promptWindowSize
        window.maxSize = promptWindowSize
        window.setContentSize(promptWindowSize)
        positionMeetingDetectionPromptWindow(window)
        meetingDetectionPromptWindow = window
        AppLog.writeRaw(
            event: "meeting_detection.prompt_presented",
            detail: "targetId=\(prompt.targetID) bundleID=\(prompt.bundleID)"
        )
        window.orderFrontRegardless()
        window.contentView?.layoutSubtreeIfNeeded()
        window.setContentSize(promptWindowSize)
        positionMeetingDetectionPromptWindow(window)
        Task { @MainActor [weak window] in
            guard let window, window.isVisible else { return }
            window.contentView?.layoutSubtreeIfNeeded()
            window.setContentSize(Self.meetingDetectionPromptWindowSize)
            positionMeetingDetectionPromptWindow(window)
        }
    }

    @MainActor
    private func dismissMeetingDetectionPrompt() {
        if let meetingDetectionPrompt {
            AppLog.writeRaw(
                event: "meeting_detection.prompt_dismissed",
                detail: "targetId=\(meetingDetectionPrompt.targetID) bundleID=\(meetingDetectionPrompt.bundleID)"
            )
        }
        meetingDetectionPrompt = nil
        dismissMeetingDetectionPromptWindow()
    }

    @MainActor
    private func dismissMeetingDetectionPromptWindow() {
        meetingDetectionPromptWindow?.close()
        meetingDetectionPromptWindow = nil
    }

    @MainActor
    private func positionMeetingDetectionPromptWindow(_ window: NSWindow) {
        guard let screen = meetingDetectionPromptScreen() else {
            window.center()
            return
        }
        let frame = meetingDetectionPromptFrame(
            windowSize: Self.meetingDetectionPromptWindowSize,
            visibleFrame: screen.visibleFrame
        )
        window.setFrame(frame, display: true)
    }

    @MainActor
    private func meetingDetectionPromptScreen() -> NSScreen? {
        let mouseLocation = NSEvent.mouseLocation
        if let screen = NSScreen.screens.first(where: { NSMouseInRect(mouseLocation, $0.frame, false) }) {
            return screen
        }
        return NSApp.keyWindow?.screen
            ?? NSApp.mainWindow?.screen
            ?? NSScreen.main
            ?? NSScreen.screens.first
    }

    private func meetingDetectionPromptFrame(windowSize: NSSize, visibleFrame: NSRect) -> NSRect {
        let margin = Self.meetingDetectionPromptVisibleMargin
        let horizontalMargin = min(margin, max(0, visibleFrame.width / 2 - 1))
        let verticalMargin = min(margin, max(0, visibleFrame.height / 2 - 1))
        let safeFrame = visibleFrame.insetBy(dx: horizontalMargin, dy: verticalMargin)
        let width = min(windowSize.width, max(1, safeFrame.width))
        let height = min(windowSize.height, max(1, safeFrame.height))
        let maxX = safeFrame.maxX - width
        let maxY = safeFrame.maxY - height
        return NSRect(
            x: clamp(safeFrame.midX - width / 2, lower: safeFrame.minX, upper: maxX),
            y: clamp(safeFrame.maxY - height, lower: safeFrame.minY, upper: maxY),
            width: width,
            height: height
        )
    }

    private func clamp(_ value: CGFloat, lower: CGFloat, upper: CGFloat) -> CGFloat {
        guard upper >= lower else { return lower }
        return min(max(value, lower), upper)
    }

    @MainActor
    private func acceptMeetingDetectionPrompt(_ prompt: MeetingDetectionPrompt) {
        AppLog.writeRaw(
            event: "meeting_detection.prompt_accepted",
            detail: "targetId=\(prompt.targetID) bundleID=\(prompt.bundleID)"
        )
        dismissMeetingDetectionPrompt()
        Task {
            await startManualRecording(
                meetingDetectionTarget: MeetingDetectionRecordingTarget(
                    targetID: prompt.targetID,
                    bundleID: prompt.bundleID,
                    displayName: prompt.displayName
                )
            )
        }
    }

    @MainActor
    private func startManualRecording(
        calendarContextEventId: String? = nil,
        calendarMatchDecisionIntent: DesktopCalendarMatchDecisionIntent = .automatic,
        meetingDetectionTarget: MeetingDetectionRecordingTarget? = nil
    ) async {
        guard !recordingStartInProgress, !recordingStopInProgress else { return }
        if let captureSession, CaptureStatusItem.showsStopButton(for: captureSession) {
            return
        }
        activeCalendarContextEventId = calendarContextEventId
        activeCalendarMatchAttemptId = nil
        activeCalendarMatchLocalRecordingId = nil
        recordingStartInProgress = true
        defer { recordingStartInProgress = false }

        localRecordingManifest = nil
        recordingBlocker = nil
        let scopeApproval: CaptureScopeApproval
        do {
            if let meetingDetectionTarget {
                scopeApproval = try captureScopeApprovalService.approveDetectorAssistedMeetingTarget(
                    sourceDisplayName: meetingDetectionTarget.displayName
                )
            } else {
                scopeApproval = try captureScopeApprovalService.approve(
                    scopeKind: .display,
                    sourceDisplayName: "Current display/system audio",
                    approvalMode: .userConfirmedSuggestedScope,
                    eligibleReason: .manualMeetingScope
                )
            }
        } catch {
            recordingBlocker = "Запись не началась: не удалось подтвердить область записи."
            return
        }
        do {
            let preparing = if let meetingDetectionTarget {
                try captureController.beginDetectorAssistedPreparing(
                    targetID: meetingDetectionTarget.targetID,
                    bundleID: meetingDetectionTarget.bundleID,
                    displayName: meetingDetectionTarget.displayName
                )
            } else {
                try captureController.beginPreparing(
                    mode: .audioRecording,
                    sourceAppEligibility: .eligible
                )
            }
            captureSession = preparing
        } catch {
            recordingBlocker = "Запись не началась: \(recordingStartFailureMessage(for: error))"
            return
        }
        let resolvedMicrophoneSelection = microphoneCaptureService.resolveRecordingMicrophoneSelection(
            selectedInputDeviceId: selectedRecordingMicrophoneDeviceId
        )
        recordingMicrophoneSelection = resolvedMicrophoneSelection
        guard resolvedMicrophoneSelection.isAccepted else {
            let recoveryCopy = CaptureControlView.recordingMicrophoneRecoveryCopy(
                for: resolvedMicrophoneSelection
            ) ?? "Выберите другой микрофон записи."
            if let blocked = try? captureController.blockStart(
                reason: .captureFailed,
                recoveryAction: recoveryCopy
            ) {
                captureSession = blocked
            }
            recordingBlocker = "Запись не началась: \(recoveryCopy)"
            return
        }
        let microphoneSession = await microphoneCaptureService.requestPermissionAndPreflight(
            sessionId: "pending",
            inputDeviceId: resolvedMicrophoneSelection.inputDeviceId,
            inputDisplayName: resolvedMicrophoneSelection.inputDisplayName ?? "Default Microphone"
        )
        let systemAudioPermissionState = await systemAudioPermissionAuthorizer.requestPermission()
        let permissionGate = systemAudioPermissionGate.evaluate(
            microphone: microphoneSession.permissionState,
            systemAudio: systemAudioPermissionState
        )
        let prerequisite = evaluatedMeetingDetectionRecordingPrerequisite(
            permissions: permissionGate.snapshot
        )

        do {
            guard prerequisite.allowsRecording && permissionGate.allowsAcceptedRecording else {
                let blocked = try captureController.blockStart(
                    reason: permissionGate.allowsAcceptedRecording ? prerequisite.blockedReason : .permissionDenied,
                    recoveryAction: permissionGate.presentation?.message ??
                        prerequisite.recoveryAction ??
                        "Resolve recording blocker"
                )
                captureSession = blocked
                recordingEvidenceEvents.append(
                    RecordingEvidenceService().startBlocked(session: blocked, prerequisite: prerequisite)
                )
                recordingBlocker = permissionGate.presentation.map {
                    "\($0.title). \($0.message)"
                } ?? recordingBlockerText(for: prerequisite)
                AppLog.writeRaw(
                    event: AuditEventName.recordingStartBlocked.rawValue,
                    detail: "reason=\(permissionGate.allowsAcceptedRecording ? prerequisite.blockedReason.rawValue : RecordingStartBlocker.permissionDenied.rawValue) microphonePermission=\(permissionGate.snapshot.microphone.rawValue) systemAudioPermission=\(permissionGate.snapshot.systemAudio.rawValue) action=\(permissionGate.presentation?.recoveryAction.rawValue ?? prerequisite.recoveryAction ?? "none")"
                )
                return
            }

            _ = try captureController.markReady(triggerEvidence: [
                "captureSource": "system_audio",
                "scopeApprovalId": scopeApproval.scopeApprovalId,
                "scopeKind": scopeApproval.scopeKind.rawValue,
                "sourceDisplayName": scopeApproval.sourceDisplayName,
                "microphonePermissionState": permissionGate.snapshot.microphone.rawValue,
                "systemAudioPermissionState": permissionGate.snapshot.systemAudio.rawValue,
                "recordingMicrophoneMode": resolvedMicrophoneSelection.mode.rawValue,
                "recordingMicrophoneSelectionResult": resolvedMicrophoneSelection.selectionResult.rawValue,
                "recordingMicrophoneInputDeviceId": resolvedMicrophoneSelection.inputDeviceId ?? "none",
                "recordingMicrophoneInputDisplayName": resolvedMicrophoneSelection.inputDisplayName ?? "unknown",
                "captureArchitecture": "app_owned_system_audio_and_microphone",
                "recordingStartKind": meetingDetectionTarget == nil ? "manual" : "meeting_detection",
                "meetingDetectionTargetId": meetingDetectionTarget?.targetID ?? "none",
                "meetingDetectionBundleId": meetingDetectionTarget?.bundleID ?? "none",
                "externalEgressStarted": "false",
                "transcriptionStarted": "false"
            ])
            let starting = try captureController.start()
            captureSession = starting
            let targetMuteCapability = meetingMuteTruthService.capability(for: scopeApproval.sourceDisplayName)
            let targetMuteEvidence = meetingMuteTruthService.evidence(
                sessionId: starting.id,
                capability: targetMuteCapability,
                limitationCopyShown: true,
                recordedAt: Date()
            )
            let limitationCopyShownAt = Date()
            let recordingStartedAt = Date()
            _ = try await systemAudioCaptureService.start(
                sessionId: starting.id,
                permissionState: permissionGate.snapshot.systemAudio,
                scopeApproval: scopeApproval,
                startedAt: recordingStartedAt
            )
            let incomingSource = systemAudioCaptureService.incomingSampleSource
            let microphoneSource = try microphoneCaptureService.startAppOwnedMicrophoneSampleSource(
                for: resolvedMicrophoneSelection
            )
            activeMicrophoneSampleSource = microphoneSource
            localRecordingWriter = LocalRecordingWriter(
                microphoneSampleSourceFactory: { microphoneSource },
                incomingSampleSourceFactory: { incomingSource },
                recordMicrophone: true
            )
            let directory = try await localRecordingWriter.startAsync(
                sessionId: starting.id,
                startedAt: recordingStartedAt,
                scopeApproval: scopeApproval,
                permissions: permissionGate.snapshot,
                microphoneSelection: resolvedMicrophoneSelection,
                targetMuteCapability: targetMuteCapability,
                meetingMuteTruthEvidence: [targetMuteEvidence],
                limitationCopyShownAt: limitationCopyShownAt
            )
            localRecordingActive = true
            let active = try captureController.markCapturing()
            captureSession = active
            if let command = DesktopCalendarResolvePolicy.commandAfterCaptureStarted(
                localRecordingActive: localRecordingActive,
                localRecordingId: directory.directoryId,
                recordingStartedAt: recordingStartedAt,
                decisionIntent: calendarMatchDecisionIntent,
                eventId: calendarContextEventId
            ) {
                activeCalendarMatchLocalRecordingId = command.localRecordingId
                Task {
                    await resolveCalendarContextAfterCaptureStarted(
                        localRecordingId: command.localRecordingId,
                        recordingStartedAt: command.recordingStartedAt,
                        decisionIntent: command.decisionIntent,
                        eventId: command.eventId
                    )
                }
            }
            recordingEvidenceEvents.append(
                RecordingEvidenceService().event(
                    for: active,
                    type: .started,
                    initiator: .user
                )
            )
            recordingBlocker = nil
            AppLog.writeRaw(
                event: AuditEventName.recordingStarted.rawValue,
                detail: "sessionId=\(active.id) captureSource=system_audio microphoneSource=app_owned scopeApprovalId=\(scopeApproval.scopeApprovalId) indicator=\(active.visibleIndicatorState.rawValue) localRecordingDirectory=\(directory.directoryId)"
            )
        } catch {
            localRecordingActive = false
            liveRecordingLevels = .inactive
            activeMicrophoneSampleSource?.stop()
            activeMicrophoneSampleSource = nil
            let releasedSystemAudioSession = try? await systemAudioCaptureService.stop()
            await finalizeLocalRecordingForFailure(
                reason: "start_failure_cleanup",
                failureReason: releasedSystemAudioSession?.failureReason ?? .none
            )
            clearActiveCalendarMatchState()
            let failureCategory = recordingStartFailureCategory(for: error)
            if let failed = try? captureController.fail(stopReason: .failed, failureCategory: failureCategory) {
                captureSession = failed
            }
            recordingBlocker = "Запись не началась: \(recordingStartFailureMessage(for: error))"
            AppLog.writeRaw(
                event: AuditEventName.recordingFailed.rawValue,
                detail: "category=\(failureCategory.rawValue) error=\(error)"
            )
        }
    }

    @MainActor
    private func resolveCalendarContextAfterCaptureStarted(
        localRecordingId: String,
        recordingStartedAt: Date,
        decisionIntent: DesktopCalendarMatchDecisionIntent,
        eventId: String?
    ) async {
        defer {
            let queueHasRecording = (try? desktopUploadQueueService.loadItems().contains {
                $0.directoryId == localRecordingId
            }) == true
            if DesktopCalendarResolvePolicy.shouldProcessQueuedRecording(
                queueHasRecording: queueHasRecording
            ) {
                refreshUploadQueueAndProcess(reason: "calendar_context_resolve_completed")
            }
        }

        guard let client = DesktopUploadClient.configuredFromEnvironment() else {
            AppLog.writeRaw(
                event: "calendar.context_resolve_unavailable",
                detail: "localRecordingId=\(localRecordingId) reason=client_not_configured"
            )
            return
        }

        do {
            let response = try await client.resolveCalendarContext(
                localRecordingId: localRecordingId,
                request: DesktopCalendarContextResolveRequest(
                    recordingStartedAt: recordingStartedAt,
                    decisionIntent: decisionIntent,
                    eventId: eventId
                )
            )
            let attemptId = response.attemptId.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !attemptId.isEmpty else { return }

            if activeCalendarMatchLocalRecordingId == localRecordingId {
                activeCalendarMatchAttemptId = attemptId
            }
            _ = try desktopUploadQueueService.persistCalendarMatchAttempt(
                localRecordingId: localRecordingId,
                attemptId: attemptId
            )
            AppLog.writeRaw(
                event: "calendar.context_resolved",
                detail: "localRecordingId=\(localRecordingId) state=\(response.contextState.rawValue)"
            )
        } catch {
            AppLog.writeRaw(
                event: "calendar.context_resolve_unavailable",
                detail: "localRecordingId=\(localRecordingId) reason=calendar_unavailable"
            )
        }
    }

    @MainActor
    private func clearActiveCalendarMatchState() {
        activeCalendarContextEventId = nil
        activeCalendarMatchAttemptId = nil
        activeCalendarMatchLocalRecordingId = nil
    }

    @MainActor
    private func finalizeLocalRecordingForFailure(
        reason: String,
        failureReason: LocalRecordingFailureReason = .none
    ) async {
        guard await localRecordingWriter.isRecordingAsync() else {
            return
        }
        activeMicrophoneSampleSource?.stop()
        activeMicrophoneSampleSource = nil
        let recordingDirectory = await localRecordingWriter.currentDirectoryURLAsync()
        do {
            let manifest = try await localRecordingWriter.stopAsync(failureReason: failureReason)
            localRecordingManifest = manifest
            enqueueLocalRecordingForUpload(
                manifest: manifest,
                directoryURL: recordingDirectory,
                reason: reason,
                calendarContextEventId: activeCalendarContextEventId,
                calendarMatchAttemptId: activeCalendarMatchAttemptId
            )
            clearActiveCalendarMatchState()
            AppLog.writeRaw(
                event: AuditEventName.localRecordingDegraded.rawValue,
                detail: "sessionId=\(manifest.sessionId) status=\(manifest.status.rawValue) reason=\(reason) failureReason=\(manifest.failureReason.rawValue)"
            )
        } catch {
            AppLog.writeRaw(
                event: AuditEventName.recordingFailed.rawValue,
                detail: "\(reason)_failed error=\(error)"
            )
        }
    }

    private func recordingStartFailureCategory(for error: Error) -> RecordingStartBlocker {
        if let writerError = error as? LocalRecordingWriterError {
            switch writerError {
            case .alreadyRecording:
                return .alreadyRecording
            case .directoryUnavailable:
                return .storageUnsafe
            case .notRecording:
                return .unknown
            }
        }
        if let captureError = error as? SystemAudioCaptureServiceError {
            switch captureError {
            case .permissionDenied:
                return .permissionDenied
            case .alreadyRunning:
                return .alreadyRecording
            case .runtimeStartFailed, .scopeNotApproved, .screenCaptureKitUnavailable, .noShareableDisplay:
                return .captureFailed
            case .notRunning:
                return .unknown
            }
        }
        if let microphoneError = error as? RecordingMicrophoneSampleSourceError {
            switch microphoneError {
            case .selectionNotAccepted:
                return .captureFailed
            case .runtimeUnavailable, .runtimeStartFailed:
                return .captureFailed
            }
        }
        return .unknown
    }

    private func recordingStartFailureMessage(for error: Error) -> String {
        if let writerError = error as? LocalRecordingWriterError {
            switch writerError {
            case .alreadyRecording:
                return "запись уже идет."
            case .directoryUnavailable:
                return "локальное хранилище недоступно."
            case .notRecording:
                return "активной записи нет."
            }
        }
        if let captureError = error as? SystemAudioCaptureServiceError {
            switch captureError {
            case .permissionDenied:
                return "нужен доступ к записи системного звука."
            case .alreadyRunning:
                return "запись системного звука уже идет."
            case .scopeNotApproved:
                return "область записи не подтверждена."
            case .runtimeStartFailed:
                return "macOS не запустила запись системного звука."
            case .screenCaptureKitUnavailable:
                return "запись системного звука недоступна на этом Mac."
            case .noShareableDisplay:
                return "нет доступного экрана для записи системного звука."
            case .notRunning:
                return "запись системного звука не была активна."
            }
        }
        if let microphoneError = error as? RecordingMicrophoneSampleSourceError {
            switch microphoneError {
            case .selectionNotAccepted:
                return "выбранный микрофон записи не принят."
            case .runtimeUnavailable:
                return "macOS не дала доступ к потоку микрофона."
            case .runtimeStartFailed:
                return "macOS не запустила поток микрофона."
            }
        }
        return "нужна повторная попытка."
    }

    @MainActor
    private func pauseManualRecording() async {
        guard !recordingStartInProgress, !recordingStopInProgress else { return }
        guard captureSession?.state == .active else { return }

        do {
            let pausedAt = Date()
            try await localRecordingWriter.pausePrivacyAsync(startedAt: pausedAt)
            let paused = try captureController.pause()
            captureSession = paused
            recordingBlocker = nil
            AppLog.writeRaw(
                event: "recording.pause_requested",
                detail: "sessionId=\(paused.id) localMicTreatment=silenced stopAvailable=\(paused.stopActionAvailable)"
            )
        } catch {
            recordingBlocker = "Не удалось поставить запись на паузу. Запись продолжается; попробуйте ещё раз."
            AppLog.writeRaw(
                event: AuditEventName.recordingFailed.rawValue,
                detail: "pause_failed error=\(error)"
            )
        }
    }

    @MainActor
    private func resumeManualRecording() async {
        guard !recordingStartInProgress, !recordingStopInProgress else { return }
        guard captureSession?.state == .paused else { return }

        do {
            let resumedAt = Date()
            try await localRecordingWriter.resumePrivacyAsync(endedAt: resumedAt)
            let active = try captureController.resume()
            captureSession = active
            recordingBlocker = nil
            AppLog.writeRaw(
                event: "recording.resume_requested",
                detail: "sessionId=\(active.id) localMicTreatment=capturing stopAvailable=\(active.stopActionAvailable)"
            )
        } catch {
            recordingBlocker = "Не удалось продолжить запись. Она остаётся на паузе; попробуйте ещё раз или остановите её."
            AppLog.writeRaw(
                event: AuditEventName.recordingFailed.rawValue,
                detail: "resume_failed error=\(error)"
            )
        }
    }

    @MainActor
    private func stopManualRecording(
        reason: RecordingStopReason = .userRequested,
        evidenceInitiator: RecordingEvidenceInitiator = .user,
        enqueueReason: String = "manual_stop_finalized"
    ) async {
        guard !recordingStartInProgress, !recordingStopInProgress else { return }
        recordingStopInProgress = true
        localRecordingActive = false
        liveRecordingLevels = .inactive
        defer { recordingStopInProgress = false }

        do {
            _ = try captureController.requestStop(reason: reason)
            let recordingDirectory = await localRecordingWriter.currentDirectoryURLAsync()
            let systemAudioSession = try await systemAudioCaptureService.stop()
            activeMicrophoneSampleSource?.stop()
            activeMicrophoneSampleSource = nil
            let manifest = try await localRecordingWriter.stopAsync(
                failureReason: systemAudioSession.failureReason
            )
            let stopped = try captureController.completeStop()
            captureSession = stopped
            localRecordingManifest = manifest
            recordingEvidenceEvents.append(
                RecordingEvidenceService().event(
                    for: stopped,
                    type: .stopped,
                    initiator: evidenceInitiator
                )
            )
            recordingBlocker = nil
            let localEvent: AuditEventName = switch manifest.status {
            case .saved:
                .localRecordingSaved
            case .degraded:
                .localRecordingDegraded
            case .blocked, .failed, .active:
                .localRecordingFailed
            }
            AppLog.writeRaw(
                event: localEvent.rawValue,
                detail: "sessionId=\(stopped.id) status=\(manifest.status.rawValue) directoryId=\(manifest.directoryId)"
            )
            enqueueLocalRecordingForUpload(
                manifest: manifest,
                directoryURL: recordingDirectory,
                reason: enqueueReason,
                calendarContextEventId: activeCalendarContextEventId,
                calendarMatchAttemptId: activeCalendarMatchAttemptId
            )
            clearActiveCalendarMatchState()
            AppLog.writeRaw(
                event: AuditEventName.recordingStopped.rawValue,
                detail: "sessionId=\(stopped.id) reason=\(stopped.stopReason?.rawValue ?? "none") localRecordingStatus=\(manifest.status.rawValue)"
            )
        } catch {
            let failureCategory = recordingStopFailureCategory(for: error)
            if let failed = try? captureController.fail(stopReason: .failed, failureCategory: failureCategory) {
                captureSession = failed
            }
            let releasedSystemAudioSession = await systemAudioCaptureService.releaseForTermination()
            activeMicrophoneSampleSource?.stop()
            activeMicrophoneSampleSource = nil
            await finalizeLocalRecordingForFailure(
                reason: "stop_failure_cleanup",
                failureReason: releasedSystemAudioSession?.failureReason ?? .none
            )
            clearActiveCalendarMatchState()
            localRecordingActive = false
            liveRecordingLevels = .inactive
            recordingBlocker = "Не удалось завершить запись. Проверьте локальную копию в списке записей."
            AppLog.writeRaw(
                event: AuditEventName.recordingFailed.rawValue,
                detail: "category=\(failureCategory.rawValue) error=\(error)"
            )
        }
    }

    private func recordingStopFailureCategory(for error: Error) -> RecordingStartBlocker {
        if error is LocalRecordingWriterError {
            return .storageUnsafe
        }
        if error is SystemAudioCaptureServiceError || error is CaptureSessionControllerError {
            return .captureFailed
        }
        return .unknown
    }

    @MainActor
    private func releaseCaptureResourcesForAppExit() async {
        stopMeetingDetection()
        let releasedSystemAudioSession = await systemAudioCaptureService.releaseForTermination()
        await finalizeLocalRecordingForAppExit(
            failureReason: releasedSystemAudioSession?.failureReason ?? .none
        )
    }

    @MainActor
    private func finalizeLocalRecordingForAppExit(
        failureReason: LocalRecordingFailureReason = .none
    ) async {
        guard await localRecordingWriter.isRecordingAsync() else {
            return
        }
        let recordingDirectory = await localRecordingWriter.currentDirectoryURLAsync()
        localRecordingActive = false
        liveRecordingLevels = .inactive
        activeMicrophoneSampleSource?.stop()
        activeMicrophoneSampleSource = nil
        do {
            let manifest = try await localRecordingWriter.stopAsync(failureReason: failureReason)
            localRecordingManifest = manifest
            enqueueLocalRecordingForUpload(
                manifest: manifest,
                directoryURL: recordingDirectory,
                reason: "app_exit_resource_release",
                calendarContextEventId: activeCalendarContextEventId,
                calendarMatchAttemptId: activeCalendarMatchAttemptId
            )
            clearActiveCalendarMatchState()
            AppLog.writeRaw(
                event: AuditEventName.localRecordingDegraded.rawValue,
                detail: "sessionId=\(manifest.sessionId) status=\(manifest.status.rawValue) reason=app_exit_resource_release failureReason=\(manifest.failureReason.rawValue)"
            )
        } catch {
            AppLog.writeRaw(
                event: AuditEventName.recordingFailed.rawValue,
                detail: "app_exit_resource_release_failed error=\(error)"
            )
        }
    }

    @MainActor
    private func refreshUploadQueueAndProcess(reason: String) {
        guard !uploadQueueRefreshInProgress else { return }
        uploadQueueRefreshInProgress = true
        let service = desktopUploadQueueService
        Task {
            do {
                _ = try service.scanAndEnqueueCompletedRecordings()
                _ = try service.applyRetentionExpiry()
                var items = try await service.processDueItems { progressItems in
                    await MainActor.run {
                        uploadQueueItems = progressItems
                    }
                }
                var shouldRetryLocalPurgeAcknowledgement = false
                do {
                    _ = try await service.acknowledgePendingLocalPurgeTasks()
                    items = try service.loadItems()
                } catch {
                    shouldRetryLocalPurgeAcknowledgement = true
                    items = (try? service.loadItems()) ?? items
                    AppLog.writeRaw(
                        event: AuditEventName.localPurgeAcknowledged.rawValue,
                        detail: "reason=\(reason) failed=true error=\(error)"
                    )
                }
                await MainActor.run {
                    uploadQueueItems = items
                    uploadQueueRefreshInProgress = false
                    scheduleUploadQueueFollowUpIfNeeded(
                        items: items,
                        reason: reason,
                        shouldRetryLocalPurgeAcknowledgement: shouldRetryLocalPurgeAcknowledgement
                    )
                    AppLog.writeRaw(
                        event: "upload.queue_refreshed",
                        detail: "reason=\(reason) total=\(items.count) pending=\(items.filter { !$0.state.isTerminal }.count)"
                    )
                }
            } catch {
                await MainActor.run {
                    uploadQueueRefreshInProgress = false
                    AppLog.writeRaw(
                        event: AuditEventName.uploadFailed.rawValue,
                        detail: "reason=\(reason) error=\(error)"
                    )
                }
            }
        }
    }

    @MainActor
    private func submitSupportIncidentReport(itemIds: [String]) async throws -> DesktopSupportIncidentResponse {
        let service = desktopUploadQueueService
        do {
            let response = try await service.submitSupportIncident(
                itemIds: itemIds,
                using: supportIncidentBridge
            )
            uploadQueueItems = try service.loadItems()
            AppLog.writeRaw(
                event: "support_incident.submitted",
                detail: "incident=\(response.incidentId) status=\(response.incidentStatus)"
            )
            return response
        } catch {
            uploadQueueItems = (try? service.loadItems()) ?? uploadQueueItems
            AppLog.writeRaw(
                event: "support_incident.failed",
                detail: "code=\(safeSupportIncidentErrorCode(error))"
            )
            throw error
        }
    }

    @MainActor
    private func syncSupportIncident(itemIds: [String]) async throws -> DesktopSupportIncidentResponse {
        let service = desktopUploadQueueService
        do {
            let response = try await service.syncSupportIncident(
                itemIds: itemIds,
                using: supportIncidentBridge
            )
            uploadQueueItems = try service.loadItems()
            AppLog.writeRaw(
                event: "support_incident.sync_checked",
                detail: "incident=\(response.incidentId) status=\(response.incidentStatus)"
            )
            return response
        } catch {
            uploadQueueItems = (try? service.loadItems()) ?? uploadQueueItems
            AppLog.writeRaw(
                event: "support_incident.sync_failed",
                detail: "code=\(safeSupportIncidentErrorCode(error))"
            )
            throw error
        }
    }

    private func copySupportIncidentReport(itemIds: [String]) throws -> String? {
        try desktopUploadQueueService.supportIncidentReportText(itemIds: itemIds)
    }

    @MainActor
    private func openSupportSignIn() {
        guard let configuration = desktopCabinetConfiguration else { return }
        selectedCabinetRoute = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        desktopCabinetState = .loading
    }

    private func safeSupportIncidentErrorCode(_ error: Error) -> String {
        if case DesktopUploadClientError.httpStatus(_, let code) = error {
            return code
        }
        if error is DesktopUploadQueueServiceError {
            return "support_incident.local_queue_unavailable"
        }
        return "support_incident.unavailable"
    }

    @MainActor
    private func scheduleUploadQueueFollowUpIfNeeded(
        items: [DesktopUploadQueueItem],
        reason: String,
        shouldRetryLocalPurgeAcknowledgement: Bool = false
    ) {
        guard !uploadQueueFollowUpScheduled else { return }
        let now = Date()
        let needsProcessingFollowUp = items.contains(where: { DesktopUploadQueueService.needsProcessingFollowUp($0, now: now) })
        let nextRetryDate = DesktopUploadQueueService.nextScheduledRetryDate(for: items, now: now)
        guard needsProcessingFollowUp || nextRetryDate != nil || shouldRetryLocalPurgeAcknowledgement else { return }
        uploadQueueFollowUpScheduled = true
        let followUpReason: String
        let delay: TimeInterval
        if shouldRetryLocalPurgeAcknowledgement {
            followUpReason = "local_purge_ack_retry_after_\(reason)"
            delay = 60
        } else if needsProcessingFollowUp {
            followUpReason = reason.hasPrefix("processing_follow_up") ? "processing_follow_up" : "processing_follow_up_after_\(reason)"
            delay = 10
        } else {
            followUpReason = "scheduled_retry_after_\(reason)"
            delay = max(1, min(nextRetryDate?.timeIntervalSince(now) ?? 10, 60 * 60))
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
            uploadQueueFollowUpScheduled = false
            refreshUploadQueueAndProcess(reason: followUpReason)
        }
    }

    @MainActor
    private func startUploadQueueNetworkMonitorIfNeeded() {
        guard uploadQueueNetworkMonitor == nil else { return }
        let monitor = NWPathMonitor()
        let queue = DispatchQueue(label: "pro.2brain.graf.upload-network-monitor", qos: .utility)
        monitor.pathUpdateHandler = { path in
            Task { @MainActor in
                let isSatisfied = path.status == .satisfied
                defer { uploadQueueNetworkWasSatisfied = isSatisfied }
                guard isSatisfied, !uploadQueueNetworkWasSatisfied else { return }
                refreshUploadQueueAndProcess(reason: "network_recovered")
            }
        }
        uploadQueueNetworkMonitor = monitor
        monitor.start(queue: queue)
    }

    @MainActor
    private func enqueueLocalRecordingForUpload(
        manifest: LocalRecordingManifest,
        directoryURL: URL?,
        reason: String,
        calendarContextEventId: String? = nil,
        calendarMatchAttemptId: String? = nil
    ) {
        guard let directoryURL else { return }
        do {
            let item = try desktopUploadQueueService.enqueue(
                manifest: manifest,
                directoryURL: directoryURL,
                reason: reason,
                calendarContextEventId: calendarContextEventId,
                calendarMatchAttemptId: calendarMatchAttemptId
            )
            uploadQueueItems = try desktopUploadQueueService.loadItems()
            let event: AuditEventName = switch item.state {
            case .queued, .uploading:
                .uploadQueued
            case .retrying:
                .uploadRetrying
            case .uploaded:
                .uploadUploaded
            case .degraded, .blocked:
                .uploadBlocked
            case .failed, .terminalDeleted:
                .uploadFailed
            }
            AppLog.writeRaw(
                event: event.rawValue,
                detail: "queueId=\(item.id) directoryId=\(item.directoryId) state=\(item.state.rawValue) retryMode=\(item.retryMode.rawValue) failureCategory=\(item.failureCategory.rawValue)"
            )
            refreshUploadQueueAndProcess(reason: "enqueue_\(reason)")
        } catch {
            AppLog.writeRaw(
                event: AuditEventName.uploadFailed.rawValue,
                detail: "reason=enqueue_\(reason) sessionId=\(manifest.sessionId) directoryId=\(manifest.directoryId) error=\(error)"
            )
        }
    }

    private func recordingBlockerText(for snapshot: RecordingPrerequisiteSnapshot) -> String {
        let action = snapshot.recoveryAction.map(recoveryActionText) ?? "Проверьте состояние перед записью"
        switch snapshot.blockedReason {
        case .none:
            return ""
        case .captureUnavailable:
            return "Запись не началась: источник записи занят или недоступен. \(action)."
        case .policyDisabled:
            return "Запись отключена политикой. \(action)."
        case .permissionDenied:
            return "Запись не началась: нужен доступ к микрофону или системному звуку. \(action)."
        case .storageUnsafe:
            return "Запись не началась: недостаточно безопасного места для локальной копии. \(action)."
        case .indicatorUnavailable:
            return "Запись не началась: локальный индикатор недоступен. \(action)."
        case .sourceAppIneligible:
            return "Запись не началась: источник не подтверждён. \(action)."
        case .alreadyRecording:
            return "Запись уже идёт."
        case .captureFailed:
            return "Запись не началась: системный звук не запустился. \(action)."
        case .unknown:
            return "Запись не началась: нужна повторная проверка. \(action)."
        }
    }

    private func recoveryActionText(_ action: String) -> String {
        switch action {
        case "refresh_local_audio_status":
            return "Обновите состояние звука"
        case "select_physical_microphone":
            return "Выберите физический микрофон"
        case "select_physical_speaker":
            return "Выберите физические динамики"
        case "grant_microphone":
            return "Разрешите доступ к микрофону"
        case "grant_system_audio":
            return "Разрешите запись системного звука"
        case "Review workspace recording policy":
            return "Проверьте политику записи рабочего пространства"
        case "Use an approved meeting target":
            return "Откройте поддерживаемое приложение встречи"
        case "Enable recording policy before starting":
            return "Разрешите запись в настройках рабочего пространства"
        case "Grant microphone permission in System Settings":
            return "Разрешите доступ к микрофону в Системных настройках"
        case "Grant Screen & System Audio permission in System Settings":
            return "Разрешите запись экрана и системного звука в Системных настройках"
        case "Free local storage or reduce retention before recording":
            return "Освободите место на Mac"
        case "Restore visible capture indicator before recording":
            return "Перезапустите GRAF и повторите попытку"
        default:
            return "Проверьте настройки записи"
        }
    }

    private var localRecordingStatusText: String? {
        guard let manifest = localRecordingManifest else {
            if localRecordingActive {
                if captureSession?.state == .paused {
                    return SystemAudioStatusLabels.localRecordingPausedStatus
                }
                return "Локальная запись идет"
            }
            return nil
        }
        switch manifest.status {
        case .saved:
            return "Локальная запись сохранена"
        case .degraded:
            return "Локальная запись сохранена с ограничениями"
        case .blocked:
            return "Локальная запись заблокирована"
        case .failed:
            return "Локальная запись не сохранена"
        case .active:
            return "Локальная запись идёт"
        }
    }

    private var meetingMuteTruthWarningText: String? {
        guard localRecordingActive || localRecordingManifest?.meetingMuteTruth != nil else {
            return nil
        }
        return SystemAudioStatusLabels.meetingMuteTruthLimitationCopy
    }

    @MainActor
    private func pollRecordingLevelsIfNeeded() {
        guard localRecordingActive, !recordingStartInProgress, !recordingStopInProgress else {
            if liveRecordingLevels != .inactive {
                liveRecordingLevels = .inactive
            }
            return
        }
        guard !levelsPollInProgress else { return }

        levelsPollInProgress = true
        let writer = localRecordingWriter
        Task {
            let recordingLevels = await writer.currentLevelsAsync()
            await MainActor.run {
                levelsPollInProgress = false
                guard writer === localRecordingWriter,
                      localRecordingActive,
                      !recordingStartInProgress,
                      !recordingStopInProgress else {
                    if liveRecordingLevels != .inactive {
                        liveRecordingLevels = .inactive
                    }
                    return
                }
                if recordingLevels != liveRecordingLevels {
                    liveRecordingLevels = recordingLevels
                }
            }
        }
    }
}

private struct MeetingDetectionRecordingTarget: Equatable, Sendable {
    let targetID: String
    let bundleID: String
    let displayName: String
}

private struct MeetingDetectionPrompt: Identifiable, Equatable {
    let id: String
    let targetID: String
    let bundleID: String
    let displayName: String
    let captureMode: String
    let captureSources: String
    let workspacePolicyState: String
    let detectorReason: String

    init(
        targetID: String,
        bundleID: String,
        displayName: String,
        captureMode: String,
        captureSources: String,
        workspacePolicyState: String,
        detectorReason: String
    ) {
        self.targetID = targetID
        self.bundleID = bundleID
        self.displayName = displayName
        self.captureMode = captureMode
        self.captureSources = captureSources
        self.workspacePolicyState = workspacePolicyState
        self.detectorReason = detectorReason
        id = "\(targetID):\(bundleID)"
    }
}

private struct MeetingDetectionPromptView: View {
    let prompt: MeetingDetectionPrompt
    let isStartDisabled: Bool
    let onStart: () -> Void
    let onDismiss: () -> Void

    @State private var didResolve = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "video.badge.checkmark")
                    .font(.title3)
                    .foregroundStyle(.blue)
                    .frame(width: 24)
                VStack(alignment: .leading, spacing: 4) {
                    Text(prompt.displayName)
                        .font(.headline)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                    Text("Начать запись?")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(prompt.captureMode)
                        Text(prompt.captureSources)
                        Text(prompt.workspacePolicyState)
                        Text(prompt.detectorReason)
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.9)
                }
            }

            VStack(spacing: 8) {
                Button("Начать") {
                    resolveStart()
                }
                .buttonStyle(.borderedProminent)
                .disabled(isStartDisabled)
                .keyboardShortcut(.defaultAction)
                .frame(maxWidth: .infinity)

                Button("Не сейчас") {
                    resolveDismiss()
                }
                .buttonStyle(.plain)
                .keyboardShortcut(.cancelAction)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity)
            }
        }
        .padding(18)
        .frame(width: 360)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 10))
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(.quaternary, lineWidth: 1)
        )
    }

    private func resolveStart() {
        guard !didResolve, !isStartDisabled else { return }
        didResolve = true
        onStart()
    }

    private func resolveDismiss() {
        guard !didResolve else { return }
        didResolve = true
        onDismiss()
    }
}

@MainActor
private final class AppLifecycleDelegate: NSObject, NSApplicationDelegate, NSMenuItemValidation {
    private var mainWindow: NSWindow?
    private var settingsWindow: NSWindow?
    private let workspaceZoomStore = WorkspaceZoomStore()
    private let appUpdateController: AppUpdateController
    private var terminationReplyPending = false

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
        appUpdateController.start()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.logWindowVisibility()
        }
    }

    func applicationShouldHandleReopen(
        _ sender: NSApplication,
        hasVisibleWindows flag: Bool
    ) -> Bool {
        presentMainWindow(reason: flag ? "reopen_visible" : "reopen")
        return true
    }

    func applicationDidBecomeActive(_: Notification) {
        guard mainWindow?.isVisible != true else { return }
        presentMainWindow(reason: "became_active_recovery")
    }

    func applicationShouldTerminate(_: NSApplication) -> NSApplication.TerminateReply {
        guard !terminationReplyPending else {
            return .terminateLater
        }
        terminationReplyPending = true
        appUpdateController.updateProtectedWork(
            ProtectedUpdateWork(terminationCleanupPending: true)
        )
        AppLog.writeRaw(
            event: "app_termination_cleanup_requested",
            detail: "reply=terminateLater"
        )
        dismissModalWindowsForTermination()
        NotificationCenter.default.post(name: .twoBrainRecApplicationShouldTerminate, object: nil)
        DispatchQueue.main.asyncAfter(deadline: .now() + 10) { [weak self] in
            self?.replyToTerminateIfPending(reason: "timeout")
        }
        return .terminateLater
    }

    func applicationWillTerminate(_: Notification) {
        mainWindow = nil
        settingsWindow = nil
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
        for window in NSApp.windows {
            if let attachedSheet = window.attachedSheet {
                window.endSheet(attachedSheet)
            }
            if window.isSheet, let sheetParent = window.sheetParent {
                sheetParent.endSheet(window)
            }
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
            AppLog.writeRaw(
                event: "app_main_window_presented",
                detail: "reason=\(reason) reused=true"
            )
            return
        }

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 760),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "GRAF"
        window.minSize = NSSize(width: 1040, height: 680)
        window.isReleasedWhenClosed = false
        window.isRestorable = false
        window.identifier = NSUserInterfaceItemIdentifier("graf-main-window")
        configureMainWindowCollectionBehavior(window)
        window.contentViewController = NSHostingController(
            rootView: AppContentRoot(
                workspaceZoomStore: workspaceZoomStore,
                appUpdateController: appUpdateController
            )
        )
        window.center()
        mainWindow = window
        AppLog.writeRaw(
            event: "app_main_window_presented",
            detail: "reason=\(reason) reused=false"
        )
        window.makeKeyAndOrderFront(nil)
        window.orderFrontRegardless()
        NSApp.activate(ignoringOtherApps: true)
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
        } else if mainWindow?.isKeyWindow != true || !NSApp.isActive {
            presentMainWindow(reason: "activation_recovery")
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

    @objc func openSettings(_: Any?) {
        presentSettingsWindow(reason: "menu")
    }

    @objc func checkForUpdates(_ sender: Any?) {
        guard appUpdateController.checkForUpdates(sender) else {
            let alert = NSAlert()
            alert.alertStyle = .informational
            alert.messageText = "Проверка обновлений недоступна"
            alert.informativeText = appUpdateController.presentation.message
                ?? "Эта сборка GRAF не содержит полной доверенной конфигурации обновлений."
            alert.addButton(withTitle: "ОК")
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
        guard menuItem.action == #selector(checkForUpdates(_:)) else { return true }
        return appUpdateController.isManualCheckActionEnabled
    }

    private func presentSettingsWindow(reason: String) {
        if let settingsWindow {
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
            contentRect: NSRect(x: 0, y: 0, width: 720, height: 480),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = MeetingDetectionSettingsView.windowTitle
        window.minSize = NSSize(width: 680, height: 440)
        window.isReleasedWhenClosed = false
        window.isRestorable = false
        window.identifier = NSUserInterfaceItemIdentifier("graf-settings-window")
        window.contentViewController = NSHostingController(rootView: MeetingDetectionSettingsView())
        window.center()
        settingsWindow = window
        AppLog.writeRaw(
            event: "app_settings_window_presented",
            detail: "reason=\(reason) reused=false"
        )
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}

private extension Notification.Name {
    static let twoBrainRecApplicationShouldTerminate = Notification.Name("pro.2brain.graf.applicationShouldTerminate")
    static let twoBrainRecApplicationTerminationCleanupFinished = Notification.Name("pro.2brain.graf.applicationTerminationCleanupFinished")
}

private struct AppContentRoot: View {
    @ObservedObject private var workspaceZoomStore: WorkspaceZoomStore
    @ObservedObject private var appUpdateController: AppUpdateController

    init(
        workspaceZoomStore: WorkspaceZoomStore,
        appUpdateController: AppUpdateController
    ) {
        self.workspaceZoomStore = workspaceZoomStore
        self.appUpdateController = appUpdateController
    }

    var body: some View {
        ContentView(
            appUpdateController: appUpdateController,
            workspaceZoom: workspaceZoomStore.preference
        )
        .frame(minWidth: 1040, minHeight: 680)
    }
}

private enum AppLog {
    static let fileURL: URL = {
        let base = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/GRAF", isDirectory: true)
        return base.appendingPathComponent("graf.log")
    }()

    static func writeRaw(event: String, detail: String) {
        writeLine("\(timestamp()) event=\(event) detail=\(sanitize(detail))\n")
    }

    private static func sanitize(_ detail: String) -> String {
        detail
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "\r", with: " ")
            .split(separator: " ")
            .map { token in
                let value = String(token)
                let lowered = value.lowercased()
                if value.hasPrefix("/") || value.contains("=/") || value.contains("file://") {
                    return "<redacted-path>"
                }
                if lowered.hasPrefix("authorization=") ||
                    lowered.hasPrefix("cookie=") ||
                    lowered.hasPrefix("token=") ||
                    lowered.contains("bearer ") {
                    return "<redacted-secret>"
                }
                return value
            }
            .joined(separator: " ")
    }

    private static func writeLine(_ line: String) {
        do {
            try FileManager.default.createDirectory(
                at: fileURL.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            if FileManager.default.fileExists(atPath: fileURL.path),
               let handle = try? FileHandle(forWritingTo: fileURL) {
                try handle.seekToEnd()
                if let data = line.data(using: .utf8) {
                    try handle.write(contentsOf: data)
                }
                try handle.close()
            } else {
                try line.write(to: fileURL, atomically: true, encoding: .utf8)
            }
        } catch {
            print("GRAF log write failed: \(error)")
        }
    }

    private static func timestamp() -> String {
        ISO8601DateFormatter().string(from: Date())
    }
}
