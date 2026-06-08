import CoreAudio
import AppKit
import SwiftUI
import TwoBrainRecAppCore
import TwoBrainRecShared

@main
private enum TwoBrainRecAppMain {
    @MainActor
    static func main() {
        let app = NSApplication.shared
        let appDelegate = AppLifecycleDelegate()
        app.delegate = appDelegate
        withExtendedLifetime(appDelegate) {
            app.run()
        }
    }
}

private struct ContentView: View {
    @StateObject private var passthroughCoordinator = ExperimentalPassthroughCoordinator(
        logger: AppLog.writeRaw
    )
    @State private var captureController = CaptureSessionController()
    @State private var localRecordingWriter = LocalRecordingWriter()
    @State private var systemAudioCaptureService = SystemAudioCaptureService()
    @State private var microphoneCaptureService = MicrophoneCaptureService()
    @State private var systemAudioPermissionAuthorizer = CoreGraphicsSystemAudioPermissionAuthorizer()
    @State private var systemAudioPermissionGate = SystemAudioPermissionGate()
    @State private var captureScopeApprovalService = CaptureScopeApprovalService()
    @State private var captureSession: CaptureSession?
    @State private var recordingBlocker: String?
    @State private var recordingEvidenceEvents: [RecordingEvidenceEvent] = []
    @State private var localRecordingManifest: LocalRecordingManifest?
    @State private var localRecordingLocation: String?
    @State private var liveRouteSignalLevels = LiveRouteSignalLevels.inactive
    @State private var liveAudioSignalMonitor = LiveAudioSignalMonitor()
    @State private var terminationCleanupInProgress = false

    let snapshot: LocalAudioSnapshot
    let isChecking: Bool
    let onAutoStarted: (LocalAudioSnapshot) -> Void
    let refresh: () -> Void
    let runCheck: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    DriverSetupView(
                        driverState: snapshot.driverState,
                        microphoneState: snapshot.virtualMicrophoneState,
                        speakerState: snapshot.virtualSpeakerState,
                        onInstall: refresh,
                        onRepair: refresh
                    )
                    RouteVerificationView(
                        snapshot: snapshot.routeVerification,
                        canVerify: true,
                        isVerifying: isChecking,
                        onVerify: runCheck
                    )
                    CaptureControlView(
                        session: captureSession,
                        blockedReason: recordingBlocker,
                        localRecordingStatus: localRecordingStatusText,
                        localRecordingLocation: localRecordingLocation,
                        routeSignalLevels: liveRouteSignalLevels,
                        onRecord: {
                            Task { await startManualRecording() }
                        },
                        onStop: {
                            Task { await stopManualRecording() }
                        }
                    )
                    AudioHealthView(state: snapshot.healthState)
                    DiagnosticLogView(
                        path: AppLog.fileURL.path,
                        lastEvent: snapshot.lastEventSummary
                    )
                }
                .padding(18)
            }
        }
        .onAppear {
            passthroughCoordinator.recordLaunchState()
            AppLog.write(event: "app_opened", snapshot: snapshot)
            if !ProcessInfo.processInfo.arguments.contains("--enable-auto-passthrough") {
                AppLog.writeRaw(
                    event: "passthrough_bridge_auto_start_skipped",
                    detail: "automatic non-recording route engine disabled by default for safe launch"
                )
            } else {
                DispatchQueue.global(qos: .userInitiated).async {
                    let preflight = LocalAudioSnapshot.current()
                    AppLog.write(event: "auto_passthrough_preflight", snapshot: preflight)
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        if ProcessInfo.processInfo.arguments.contains("--enforce-low-resource-promotion-gate") {
                            let decision = LowResourcePromotionGate().decision(for: nil)
                            if decision.shouldUseFallback {
                                _ = PassthroughRouteEngine.shared.switchToAccepted005Fallback(
                                    reason: decision.reason,
                                    logger: AppLog.writeRaw
                                )
                            } else {
                                passthroughCoordinator.armAutomaticBridge()
                            }
                        } else {
                            passthroughCoordinator.armAutomaticBridge()
                        }
                        LocalAudioSnapshot.refreshAsync(event: "auto_passthrough_ready") { updated in
                            onAutoStarted(updated)
                        }
                        DispatchQueue.main.asyncAfter(deadline: .now() + 4.5) {
                            LocalAudioSnapshot.refreshAsync(event: "auto_passthrough_active") { updated in
                                onAutoStarted(updated)
                            }
                        }
                    }
                }
            }
            if ProcessInfo.processInfo.arguments.contains("--start-passthrough") {
                DispatchQueue.global(qos: .userInitiated).async {
                    let state = PassthroughRouteEngine.shared.startExperimentalRoute(logger: AppLog.writeRaw)
                    let updated = LocalAudioSnapshot.runReadinessCheck(routeEngineState: state)
                    AppLog.write(event: "explicit_passthrough_ready", snapshot: updated)
                    DispatchQueue.main.async {
                        onAutoStarted(updated)
                    }
                }
            }
        }
        .onReceive(
            Timer.publish(every: 0.2, on: .main, in: .common).autoconnect()
        ) { _ in
            if localRecordingWriter.isRecording {
                let recordingLevels = localRecordingWriter.currentLevels()
                let nextLevels = LiveRouteSignalLevels(
                    isActive: recordingLevels.isRecording,
                    microphoneLevel: recordingLevels.microphoneLevel,
                    speakerLevel: recordingLevels.incomingLevel,
                    microphoneUpdatedAt: recordingLevels.microphoneUpdatedAt,
                    speakerUpdatedAt: recordingLevels.incomingUpdatedAt
                )
                if nextLevels != liveRouteSignalLevels {
                    liveRouteSignalLevels = nextLevels
                }
                return
            }

            let routeActive = PassthroughRouteEngine.shared.nonblockingState == .active
            guard routeActive else {
                if liveRouteSignalLevels != .inactive {
                    liveRouteSignalLevels = .inactive
                }
                return
            }
            let nextLevels = liveAudioSignalMonitor.currentLevels(routeActive: true)
            if nextLevels != liveRouteSignalLevels {
                liveRouteSignalLevels = nextLevels
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .twoBrainRecApplicationShouldTerminate)) { _ in
            guard !terminationCleanupInProgress else { return }
            terminationCleanupInProgress = true
            Task {
                await releaseCaptureResourcesForAppExit()
                await MainActor.run {
                    NotificationCenter.default.post(name: .twoBrainRecApplicationTerminationCleanupFinished, object: nil)
                }
            }
        }
        .onDisappear {
            guard !terminationCleanupInProgress else { return }
            Task { await releaseCaptureResourcesForAppExit() }
        }
    }

    private var header: some View {
        HStack(spacing: 12) {
            Image(systemName: "waveform.badge.mic")
                .font(.system(size: 28, weight: .semibold))
            VStack(alignment: .leading, spacing: 3) {
                Text("2brain Rec")
                    .font(.title2)
                    .fontWeight(.semibold)
                Text(snapshot.summary)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button(action: refresh) {
                Image(systemName: "arrow.clockwise")
            }
            .help("Refresh audio device status")
        }
        .padding(18)
    }

    @MainActor
    private func startManualRecording() async {
        localRecordingManifest = nil
        localRecordingLocation = nil
        let scopeApproval: CaptureScopeApproval
        do {
            scopeApproval = try captureScopeApprovalService.approve(
                scopeKind: .display,
                sourceDisplayName: "Current display/system audio",
                approvalMode: .userConfirmedSuggestedScope,
                eligibleReason: .manualMeetingScope
            )
        } catch {
            recordingBlocker = "Recording blocked: capture scope could not be approved."
            return
        }
        let microphoneSession = await microphoneCaptureService.requestPermissionAndPreflight(
            sessionId: "pending",
            inputDisplayName: "Default Microphone"
        )
        let permissionGate = systemAudioPermissionGate.evaluate(
            microphone: microphoneSession.permissionState,
            systemAudio: systemAudioPermissionAuthorizer.currentPermissionState()
        )
        let prerequisite = RecordingPrerequisiteGate().evaluate(
            RecordingPrerequisiteSnapshot(
                routeState: .inactive,
                routeEvidenceKind: .systemAudioCapture,
                policyAllowsRecording: true,
                microphonePermissionGranted: permissionGate.snapshot.microphone == .granted,
                storageRisk: snapshot.healthState.bufferRisk,
                indicatorAvailable: true,
                sourceAppEligibility: .eligible,
                evaluatedAt: Date()
            )
        )

        do {
            _ = try captureController.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
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
                "routeState": prerequisite.routeState.rawValue,
                "routeEvidenceKind": prerequisite.routeEvidenceKind.rawValue,
                "externalEgressStarted": "false",
                "transcriptionStarted": "false"
            ])
            _ = try captureController.start()
            let active = try captureController.markCapturing()
            _ = try await systemAudioCaptureService.start(
                sessionId: active.id,
                permissionState: permissionGate.snapshot.systemAudio,
                scopeApproval: scopeApproval,
                startedAt: active.startedAt ?? Date()
            )
            let incomingSource = systemAudioCaptureService.incomingSampleSource
            localRecordingWriter = LocalRecordingWriter(
                incomingSampleSourceFactory: { incomingSource },
                recordMicrophone: true
            )
            let directory = try localRecordingWriter.start(
                sessionId: active.id,
                startedAt: active.startedAt ?? Date(),
                scopeApproval: scopeApproval,
                permissions: permissionGate.snapshot
            )
            captureSession = active
            localRecordingLocation = directory.directoryURL.path
            recordingEvidenceEvents.append(
                RecordingEvidenceService().event(
                    for: active,
                    type: .started,
                    initiator: .user,
                    routeState: prerequisite.routeState
                )
            )
            recordingBlocker = nil
            AppLog.writeRaw(
                event: AuditEventName.recordingStarted.rawValue,
                detail: "sessionId=\(active.id) captureSource=system_audio scopeApprovalId=\(scopeApproval.scopeApprovalId) routeState=\(prerequisite.routeState.rawValue) routeEvidenceKind=\(prerequisite.routeEvidenceKind.rawValue) indicator=\(active.visibleIndicatorState.rawValue) localRecordingDirectory=\(directory.directoryId)"
            )
        } catch {
            _ = try? await systemAudioCaptureService.stop()
            if let failed = try? captureController.fail(stopReason: .failed, failureCategory: .storageUnsafe) {
                captureSession = failed
            }
            recordingBlocker = "Recording could not start local file capture: \(error)"
            AppLog.writeRaw(event: AuditEventName.recordingFailed.rawValue, detail: "\(error)")
        }
    }

    @MainActor
    private func stopManualRecording() async {
        do {
            _ = try captureController.requestStop(reason: .userRequested)
            _ = try? await systemAudioCaptureService.stop()
            let manifest = try localRecordingWriter.stop()
            let stopped = try captureController.completeStop()
            captureSession = stopped
            localRecordingManifest = manifest
            recordingEvidenceEvents.append(
                RecordingEvidenceService().event(
                    for: stopped,
                    type: .stopped,
                    initiator: .user,
                    routeState: snapshot.healthState.livePassthroughStatus ?? .inactive
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
            AppLog.writeRaw(
                event: AuditEventName.recordingStopped.rawValue,
                detail: "sessionId=\(stopped.id) reason=\(stopped.stopReason?.rawValue ?? "none") localRecordingStatus=\(manifest.status.rawValue)"
            )
        } catch {
            recordingBlocker = "Recording could not stop: \(error)"
            AppLog.writeRaw(event: AuditEventName.recordingFailed.rawValue, detail: "\(error)")
        }
    }

    @MainActor
    private func releaseCaptureResourcesForAppExit() async {
        _ = await systemAudioCaptureService.releaseForTermination()
        finalizeLocalRecordingForAppExit()
    }

    @MainActor
    private func finalizeLocalRecordingForAppExit() {
        guard localRecordingWriter.isRecording else {
            return
        }
        let recordingDirectory = localRecordingWriter.currentDirectoryURL()
        do {
            let manifest = try localRecordingWriter.stop()
            localRecordingManifest = manifest
            localRecordingLocation = recordingDirectory?.path ?? localRecordingLocation
            AppLog.writeRaw(
                event: AuditEventName.localRecordingDegraded.rawValue,
                detail: "sessionId=\(manifest.sessionId) status=\(manifest.status.rawValue) reason=app_exit_resource_release"
            )
        } catch {
            AppLog.writeRaw(
                event: AuditEventName.recordingFailed.rawValue,
                detail: "app_exit_resource_release_failed error=\(error)"
            )
        }
    }

    private func recordingBlockerText(for snapshot: RecordingPrerequisiteSnapshot) -> String {
        let action = snapshot.recoveryAction ?? "Resolve blocker before recording"
        switch snapshot.blockedReason {
        case .none:
            return ""
        case .routeNotReady, .publicationOnly:
            return "Recording blocked: audio route is not ready. \(action)."
        case .policyDisabled:
            return "Recording blocked by policy. \(action)."
        case .permissionDenied:
            return "Recording blocked: microphone permission is unavailable. \(action)."
        case .storageUnsafe:
            return "Recording blocked: local storage reserve is unsafe. \(action)."
        case .indicatorUnavailable:
            return "Recording blocked: visible indicator is unavailable. \(action)."
        case .sourceAppIneligible:
            return "Recording blocked: target is not approved. \(action)."
        case .alreadyRecording:
            return "Recording already active."
        case .unknown:
            return "Recording blocked: unknown prerequisite failure. \(action)."
        }
    }

    private var localRecordingStatusText: String? {
        guard let manifest = localRecordingManifest else {
            if localRecordingWriter.isRecording {
                return "Local recording in progress"
            }
            return nil
        }
        switch manifest.status {
        case .saved:
            return "Local recording saved"
        case .degraded:
            return "Local recording saved with missing or degraded track"
        case .blocked:
            return "Local recording blocked"
        case .failed:
            return "Local recording failed"
        case .active:
            return "Local recording in progress"
        }
    }
}

@MainActor
private final class AppLifecycleDelegate: NSObject, NSApplicationDelegate {
    private var mainWindow: NSWindow?
    private var terminationReplyPending = false

    override init() {
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
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.logWindowVisibility()
        }
    }

    func applicationShouldHandleReopen(
        _ sender: NSApplication,
        hasVisibleWindows flag: Bool
    ) -> Bool {
        if !flag {
            presentMainWindow(reason: "reopen")
        }
        return true
    }

    func applicationShouldTerminate(_: NSApplication) -> NSApplication.TerminateReply {
        guard !terminationReplyPending else {
            return .terminateLater
        }
        terminationReplyPending = true
        AppLog.writeRaw(
            event: "app_termination_cleanup_requested",
            detail: "reply=terminateLater"
        )
        NotificationCenter.default.post(name: .twoBrainRecApplicationShouldTerminate, object: nil)
        DispatchQueue.main.asyncAfter(deadline: .now() + 10) { [weak self] in
            self?.replyToTerminateIfPending(reason: "timeout")
        }
        return .terminateLater
    }

    func applicationWillTerminate(_: Notification) {
        mainWindow = nil
        _ = PassthroughRouteEngine.shared.stop(logger: AppLog.writeRaw)
    }

    @objc private func applicationTerminationCleanupFinished() {
        replyToTerminateIfPending(reason: "cleanup_finished")
    }

    private func replyToTerminateIfPending(reason: String) {
        guard terminationReplyPending else { return }
        terminationReplyPending = false
        AppLog.writeRaw(
            event: "app_termination_cleanup_completed",
            detail: "reason=\(reason)"
        )
        NSApp.reply(toApplicationShouldTerminate: true)
    }

    private func presentMainWindow(reason: String) {
        if let mainWindow {
            mainWindow.makeKeyAndOrderFront(nil)
            AppLog.writeRaw(
                event: "app_main_window_presented",
                detail: "reason=\(reason) reused=true"
            )
            return
        }

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 760, height: 680),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "2brain Rec"
        window.minSize = NSSize(width: 720, height: 620)
        window.isReleasedWhenClosed = false
        window.isRestorable = false
        window.identifier = NSUserInterfaceItemIdentifier("2brain-rec-main-window")
        window.contentViewController = NSHostingController(
            rootView: AppContentRoot()
        )
        window.center()
        mainWindow = window
        AppLog.writeRaw(
            event: "app_main_window_presented",
            detail: "reason=\(reason) reused=false"
        )
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func logWindowVisibility() {
        let visibleWindowCount = NSApp.windows.filter { $0.isVisible }.count
        AppLog.writeRaw(
            event: "app_window_visibility_checked",
            detail: "visibleWindowCount=\(visibleWindowCount)"
        )
        if visibleWindowCount == 0 {
            presentMainWindow(reason: "visibility_recovery")
        }
    }
}

private extension Notification.Name {
    static let twoBrainRecApplicationShouldTerminate = Notification.Name("pro.2brain.rec.applicationShouldTerminate")
    static let twoBrainRecApplicationTerminationCleanupFinished = Notification.Name("pro.2brain.rec.applicationTerminationCleanupFinished")
}

private struct AppContentRoot: View {
    @State private var snapshot = LocalAudioSnapshot.placeholder()
    @State private var isChecking = false

    var body: some View {
        ContentView(
            snapshot: snapshot,
            isChecking: isChecking,
            onAutoStarted: { updated in
                snapshot = updated
            },
            refresh: {
                LocalAudioSnapshot.refreshAsync(event: "refresh") { updated in
                    snapshot = updated
                }
            },
            runCheck: {
                isChecking = true
                LocalAudioSnapshot.refreshAsync(event: "status_refresh") { updated in
                    snapshot = updated
                    isChecking = false
                }
            }
        )
        .frame(minWidth: 720, minHeight: 620)
    }
}

fileprivate struct LocalAudioSnapshot {
    let driverState: DriverInstallationState
    let virtualMicrophoneState: VirtualDeviceAvailabilityState
    let virtualSpeakerState: VirtualDeviceAvailabilityState
    let routeVerification: RouteVerificationSnapshot?
    let healthState: AudioHealthState
    let defaultInputName: String?
    let defaultOutputName: String?
    let defaultSystemOutputName: String?
    let coreAudioDeviceSummary: String
    let lastEventSummary: String

    var summary: String {
        SystemAudioDriverParkedReadiness(
            driverState: driverState,
            microphoneState: virtualMicrophoneState,
            speakerState: virtualSpeakerState,
            routeVerificationReady: routeVerification?.canShowReady == true
        ).summary
    }

    static func placeholder() -> LocalAudioSnapshot {
        let driverExists = FileManager.default.fileExists(
            atPath: "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"
        )
        let driverState: DriverInstallationState = driverExists ? .installed : .notInstalled
        let health = AudioHealthState(
            driverState: driverState,
            virtualMicState: .requiresRestart,
            virtualSpeakerState: .requiresRestart,
            microphonePermission: .unknown,
            outputPermission: .unknown,
            passthroughStatus: .unknown,
            continuityStatus: "Checking Core Audio in the background",
            bufferRisk: .healthy,
            livePassthroughStatus: .checking,
            recoveryActions: []
        )
        return LocalAudioSnapshot(
            driverState: driverState,
            virtualMicrophoneState: .requiresRestart,
            virtualSpeakerState: .requiresRestart,
            routeVerification: nil,
            healthState: health,
            defaultInputName: nil,
            defaultOutputName: nil,
            defaultSystemOutputName: nil,
            coreAudioDeviceSummary: "pending",
            lastEventSummary: "Opening app"
        )
    }

    static func refreshAsync(
        event: String,
        completion: @escaping @Sendable @MainActor (LocalAudioSnapshot) -> Void
    ) {
        DispatchQueue.global(qos: .userInitiated).async {
            let updated = LocalAudioSnapshot.current()
            AppLog.write(event: event, snapshot: updated)
            Task { @MainActor in
                completion(updated)
            }
        }
    }

    static func current(
        routeEngineState: PassthroughRouteEngineState = PassthroughRouteEngine.shared.state
    ) -> LocalAudioSnapshot {
        makeSnapshot(
            system: CoreAudioSystemSnapshot.current(),
            routeVerification: nil,
            routeEngineState: routeEngineState,
            lastEventSummary: "Status refreshed"
        )
    }

    static func runReadinessCheck(
        routeEngineState: PassthroughRouteEngineState = PassthroughRouteEngine.shared.state
    ) -> LocalAudioSnapshot {
        let system = CoreAudioSystemSnapshot.current()
        return makeSnapshot(
            system: system,
            routeVerification: routeSnapshot(
                system: system,
                checked: true,
                routeEngineState: routeEngineState
            ),
            routeEngineState: routeEngineState,
            lastEventSummary: readinessSummary(system: system, routeEngineState: routeEngineState)
        )
    }

    private static func makeSnapshot(
        system: CoreAudioSystemSnapshot,
        routeVerification: RouteVerificationSnapshot?,
        routeEngineState: PassthroughRouteEngineState,
        lastEventSummary: String
    ) -> LocalAudioSnapshot {
        let hasMic = system.hasVirtualMicrophone
        let hasSpeaker = system.hasVirtualSpeaker
        let driverExists = FileManager.default.fileExists(
            atPath: "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"
        )

        let micState: VirtualDeviceAvailabilityState = hasMic ? .available : (driverExists ? .requiresRestart : .missing)
        let speakerState: VirtualDeviceAvailabilityState = hasSpeaker ? .available : (driverExists ? .requiresRestart : .missing)
        let driverState: DriverInstallationState = driverExists ? .installed : .notInstalled
        let routeSnapshot = routeVerification ?? routeSnapshot(
            system: system,
            checked: false,
            routeEngineState: routeEngineState
        )
        let recoveryActions = recoveryActions(system: system, routeSnapshot: routeSnapshot)
        let routeIsActive = routeEngineState == .active
        let routeIsWaitingForClient = routeEngineState == .armed ||
            routeEngineState == .idleSafe ||
            routeEngineState == .inactive

        let health = AudioHealthState(
            driverState: driverState,
            virtualMicState: micState,
            virtualSpeakerState: speakerState,
            microphonePermission: .unknown,
            outputPermission: .unknown,
            physicalInput: system.defaultInput?.healthSummary(direction: .input),
            physicalOutput: system.defaultOutput?.healthSummary(direction: .output),
            routeVerification: routeSnapshot,
            passthroughStatus: routeIsActive ? .healthy : .unknown,
            continuityStatus: routeIsActive
                ? "Non-recording passthrough is ready for calls."
                : (hasMic && hasSpeaker
                    ? (routeIsWaitingForClient
                        ? "Virtual devices are published. Waiting for meeting audio."
                        : "Virtual devices are published. Live passthrough is waiting for app I/O.")
                    : "System audio recording uses macOS permissions; virtual devices are parked."),
            bufferRisk: .healthy,
            livePassthroughStatus: routeIsActive ? .active : .inactive,
            recoveryActions: recoveryActions
        )

        return LocalAudioSnapshot(
            driverState: driverState,
            virtualMicrophoneState: micState,
            virtualSpeakerState: speakerState,
            routeVerification: routeSnapshot,
            healthState: health,
            defaultInputName: system.defaultInput?.name,
            defaultOutputName: system.defaultOutput?.name,
            defaultSystemOutputName: system.defaultSystemOutput?.name,
            coreAudioDeviceSummary: system.deviceLogSummary,
            lastEventSummary: lastEventSummary
        )
    }

    private static func routeSnapshot(
        system: CoreAudioSystemSnapshot,
        checked: Bool,
        routeEngineState: PassthroughRouteEngineState
    ) -> RouteVerificationSnapshot {
        let now = Date()
        let micResult = micRouteResult(
            system: system,
            checked: checked,
            routeEngineState: routeEngineState
        )
        let speakerResult = speakerRouteResult(
            system: system,
            checked: checked,
            routeEngineState: routeEngineState
        )
        let validationType: RouteValidationType = routeEngineState == .active
            ? .appIOHeartbeat
            : .syntheticSignal
        return RouteVerificationSnapshot(
            mic: RouteVerification(
                id: "local-mic-publication",
                path: .micToVirtualInput,
                validationType: validationType,
                target: "2brain Rec Microphone",
                status: micResult.status,
                failureReason: micResult.reason,
                recoveryAction: micResult.action,
                startedAt: now,
                finishedAt: now
            ),
            speaker: RouteVerification(
                id: "local-speaker-publication",
                path: .remoteOutputToVirtualSpeaker,
                validationType: validationType,
                target: "2brain Rec Speaker",
                status: speakerResult.status,
                failureReason: speakerResult.reason,
                recoveryAction: speakerResult.action,
                startedAt: now,
                finishedAt: now
            )
        )
    }

    private static func micRouteResult(
        system: CoreAudioSystemSnapshot,
        checked: Bool,
        routeEngineState: PassthroughRouteEngineState
    ) -> (status: RouteVerificationStatus, reason: String?, action: String?) {
        guard system.hasVirtualMicrophone else {
            return checked
                ? (.failed, "virtual_microphone_not_visible", "install_or_repair_driver")
                : (.notStarted, nil, "refresh_local_audio_status")
        }
        guard let input = system.defaultInput, input.inputChannels > 0, !input.isTwoBrainVirtual else {
            return checked
                ? (.failed, "physical_microphone_not_selected", "select_physical_microphone")
                : (.notStarted, nil, "refresh_local_audio_status")
        }
        if routeEngineState == .active {
            return (.passed, nil, nil)
        }
        return checked
            ? (.stale, "app_io_heartbeat_missing", "run_readiness_check_again")
            : (.notStarted, nil, "refresh_local_audio_status")
    }

    private static func speakerRouteResult(
        system: CoreAudioSystemSnapshot,
        checked: Bool,
        routeEngineState: PassthroughRouteEngineState
    ) -> (status: RouteVerificationStatus, reason: String?, action: String?) {
        guard system.hasVirtualSpeaker else {
            return checked
                ? (.failed, "virtual_speaker_not_visible", "install_or_repair_driver")
                : (.notStarted, nil, "refresh_local_audio_status")
        }
        guard let output = system.defaultOutput, output.outputChannels > 0, !output.isTwoBrainVirtual else {
            return checked
                ? (.failed, "physical_speaker_not_selected", "select_physical_speaker")
                : (.notStarted, nil, "refresh_local_audio_status")
        }
        if routeEngineState == .active {
            return (.passed, nil, nil)
        }
        return checked
            ? (.stale, "app_io_heartbeat_missing", "run_readiness_check_again")
            : (.notStarted, nil, "refresh_local_audio_status")
    }

    private static func recoveryActions(
        system: CoreAudioSystemSnapshot,
        routeSnapshot: RouteVerificationSnapshot
    ) -> [String] {
        var actions: [String] = []
        if system.defaultInput?.isTwoBrainVirtual == true {
            actions.append("Set macOS input back to a physical microphone while testing")
        }
        if system.defaultOutput?.isTwoBrainVirtual == true {
            actions.append("Set macOS output back to physical speakers")
        }
        if let output = system.defaultOutput,
           let systemOutput = system.defaultSystemOutput,
           output.id != systemOutput.id {
            actions.append("Default output and system output are different: \(output.name) / \(systemOutput.name)")
        }
        return actions
    }

    private static func readinessSummary(
        system: CoreAudioSystemSnapshot,
        routeEngineState: PassthroughRouteEngineState
    ) -> String {
        if !system.hasVirtualMicrophone || !system.hasVirtualSpeaker {
            return "Check failed: virtual devices are missing"
        }
        if system.defaultOutput?.isTwoBrainVirtual == true {
            return "Check failed: macOS output is set to the virtual speaker"
        }
        if routeEngineState == .active {
            return "Check complete: non-recording passthrough is active"
        }
        return "Check complete: devices are visible; app I/O heartbeat is still required"
    }

    var logDescription: String {
        [
            "summary=\(summary)",
            "driver=\(driverState.rawValue)",
            "virtualMic=\(virtualMicrophoneState.rawValue)",
            "virtualSpeaker=\(virtualSpeakerState.rawValue)",
            "defaultInput=\(defaultInputName ?? "none")",
            "defaultOutput=\(defaultOutputName ?? "none")",
            "defaultSystemOutput=\(defaultSystemOutputName ?? "none")",
            "coreAudioDevices=\(coreAudioDeviceSummary)",
            "micRoute=\(routeVerification?.mic.status.rawValue ?? "none")",
            "micReason=\(routeVerification?.mic.failureReason ?? "none")",
            "speakerRoute=\(routeVerification?.speaker.status.rawValue ?? "none")",
            "speakerReason=\(routeVerification?.speaker.failureReason ?? "none")",
            "passthrough=\(healthState.passthroughStatus.rawValue)"
        ].joined(separator: " ")
    }
}

private struct CoreAudioDeviceInfo: Equatable {
    let id: AudioDeviceID
    let name: String
    let inputChannels: Int
    let outputChannels: Int

    var isTwoBrainVirtual: Bool {
        name.localizedCaseInsensitiveContains("2brain Rec")
    }

    func healthSummary(direction: AudioDirection) -> HealthPhysicalDeviceSummary {
        HealthPhysicalDeviceSummary(
            id: String(id),
            displayName: name,
            direction: direction,
            className: isTwoBrainVirtual ? .unknown : .builtIn,
            availabilityState: .available
        )
    }
}

private struct CoreAudioSystemSnapshot {
    let devices: [CoreAudioDeviceInfo]
    let defaultInputID: AudioDeviceID?
    let defaultOutputID: AudioDeviceID?
    let defaultSystemOutputID: AudioDeviceID?

    var hasVirtualMicrophone: Bool {
        devices.contains { $0.name == "2brain Rec Microphone" }
    }

    var hasVirtualSpeaker: Bool {
        devices.contains { $0.name == "2brain Rec Speaker" }
    }

    var deviceLogSummary: String {
        devices
            .map { "\($0.name)[in=\($0.inputChannels),out=\($0.outputChannels)]" }
            .joined(separator: "|")
    }

    var defaultInput: CoreAudioDeviceInfo? {
        device(defaultInputID)
    }

    var defaultOutput: CoreAudioDeviceInfo? {
        device(defaultOutputID)
    }

    var defaultSystemOutput: CoreAudioDeviceInfo? {
        device(defaultSystemOutputID)
    }

    var bridgeInputDevice: CoreAudioDeviceInfo? {
        if let defaultInput, defaultInput.inputChannels > 0, !defaultInput.isTwoBrainVirtual {
            return defaultInput
        }
        return devices.first { $0.inputChannels > 0 && !$0.isTwoBrainVirtual }
    }

    var bridgeOutputDevice: CoreAudioDeviceInfo? {
        if let defaultOutput, defaultOutput.outputChannels > 0, !defaultOutput.isTwoBrainVirtual {
            return defaultOutput
        }
        if let defaultSystemOutput, defaultSystemOutput.outputChannels > 0, !defaultSystemOutput.isTwoBrainVirtual {
            return defaultSystemOutput
        }
        return devices.first { $0.outputChannels > 0 && !$0.isTwoBrainVirtual }
    }

    static func current() -> CoreAudioSystemSnapshot {
        let deviceIDs = readDeviceIDs()
        let devices = deviceIDs.compactMap { id -> CoreAudioDeviceInfo? in
            guard let name = deviceName(id) else {
                return nil
            }
            return CoreAudioDeviceInfo(
                id: id,
                name: name,
                inputChannels: channelCount(id, scope: kAudioDevicePropertyScopeInput),
                outputChannels: channelCount(id, scope: kAudioDevicePropertyScopeOutput)
            )
        }

        return CoreAudioSystemSnapshot(
            devices: devices,
            defaultInputID: defaultDeviceID(kAudioHardwarePropertyDefaultInputDevice),
            defaultOutputID: defaultDeviceID(kAudioHardwarePropertyDefaultOutputDevice),
            defaultSystemOutputID: defaultDeviceID(kAudioHardwarePropertyDefaultSystemOutputDevice)
        )
    }

    private func device(_ id: AudioDeviceID?) -> CoreAudioDeviceInfo? {
        guard let id else {
            return nil
        }
        return devices.first { $0.id == id }
    }

    private static func readDeviceIDs() -> [AudioDeviceID] {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var dataSize: UInt32 = 0
        let sizeStatus = AudioObjectGetPropertyDataSize(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &dataSize
        )
        guard sizeStatus == noErr, dataSize > 0 else {
            return []
        }

        let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var deviceIDs = [AudioDeviceID](repeating: 0, count: count)
        let dataStatus = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &dataSize,
            &deviceIDs
        )
        guard dataStatus == noErr else {
            return []
        }

        return deviceIDs
    }

    private static func defaultDeviceID(_ selector: AudioObjectPropertySelector) -> AudioDeviceID? {
        var address = AudioObjectPropertyAddress(
            mSelector: selector,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var deviceID = AudioDeviceID(kAudioObjectUnknown)
        var dataSize = UInt32(MemoryLayout<AudioDeviceID>.size)
        let status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &dataSize,
            &deviceID
        )
        guard status == noErr, deviceID != kAudioObjectUnknown else {
            return nil
        }
        return deviceID
    }

    private static func deviceName(_ deviceID: AudioDeviceID) -> String? {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioObjectPropertyName,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var name: CFString = "" as CFString
        var dataSize = UInt32(MemoryLayout<CFString>.size)
        let status = withUnsafeMutableBytes(of: &name) { rawName in
            AudioObjectGetPropertyData(
                deviceID,
                &address,
                0,
                nil,
                &dataSize,
                rawName.baseAddress!
            )
        }
        guard status == noErr else {
            return nil
        }
        return name as String
    }

    private static func channelCount(_ deviceID: AudioDeviceID, scope: AudioObjectPropertyScope) -> Int {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyStreamConfiguration,
            mScope: scope,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(deviceID, &address, 0, nil, &dataSize) == noErr,
              dataSize > 0 else {
            return 0
        }

        let raw = UnsafeMutableRawPointer.allocate(
            byteCount: Int(dataSize),
            alignment: MemoryLayout<AudioBufferList>.alignment
        )
        defer { raw.deallocate() }

        guard AudioObjectGetPropertyData(deviceID, &address, 0, nil, &dataSize, raw) == noErr else {
            return 0
        }

        let buffers = UnsafeMutableAudioBufferListPointer(
            raw.bindMemory(to: AudioBufferList.self, capacity: 1)
        )
        return buffers.reduce(0) { $0 + Int($1.mNumberChannels) }
    }
}

private struct DiagnosticLogView: View {
    let path: String
    let lastEvent: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "doc.text.magnifyingglass")
                    .foregroundStyle(.blue)
                Text("Diagnostics")
                    .font(.callout)
                    .fontWeight(.semibold)
            }
            row(label: "Last event", detail: lastEvent)
            row(label: "Log file", detail: path)
        }
        .padding(16)
    }

    private func row(label: String, detail: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(width: 90, alignment: .leading)
            Text(detail)
                .font(.body)
                .lineLimit(2)
                .minimumScaleFactor(0.85)
            Spacer()
        }
        .accessibilityElement(children: .combine)
    }
}

private enum AppLog {
    static let fileURL: URL = {
        let base = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/2brain Rec", isDirectory: true)
        return base.appendingPathComponent("2brain-rec.log")
    }()

    static func write(event: String, snapshot: LocalAudioSnapshot) {
        let line = "\(timestamp()) event=\(event) \(snapshot.logDescription)\n"
        writeLine(line)
    }

    static func writeRaw(event: String, detail: String) {
        let sanitized = detail
            .replacingOccurrences(of: "\n", with: " ")
            .replacingOccurrences(of: "\r", with: " ")
        writeLine("\(timestamp()) event=\(event) detail=\(sanitized)\n")
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
            print("2brain Rec log write failed: \(error)")
        }
    }

    private static func timestamp() -> String {
        ISO8601DateFormatter().string(from: Date())
    }
}
