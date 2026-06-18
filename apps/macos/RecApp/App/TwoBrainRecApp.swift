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
        let appMenu = NSMenu(title: "2brain Rec")
        appMenuItem.submenu = appMenu
        appMenu.addItem(
            withTitle: "About 2brain Rec",
            action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)),
            keyEquivalent: ""
        )
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(
            withTitle: "Hide 2brain Rec",
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
            withTitle: "Quit 2brain Rec",
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
    @State private var meetingMuteTruthService = MeetingMuteTruthService()
    @State private var captureSession: CaptureSession?
    @State private var recordingBlocker: String?
    @State private var recordingEvidenceEvents: [RecordingEvidenceEvent] = []
    @State private var localRecordingManifest: LocalRecordingManifest?
    @State private var localRecordingLocation: String?
    @State private var desktopUploadQueueService = DesktopUploadQueueService()
    @State private var uploadQueueItems: [DesktopUploadQueueItem] = []
    @State private var liveRouteSignalLevels = LiveRouteSignalLevels.inactive
    @State private var localRecordingActive = false
    @State private var levelsPollInProgress = false
    @State private var uploadQueueRefreshInProgress = false
    @State private var terminationCleanupInProgress = false
    @State private var recordingStartInProgress = false
    @State private var recordingStopInProgress = false
    @State private var desktopCabinetConfiguration = DesktopCabinetConfiguration.configuredFromEnvironment()
    @State private var selectedCabinetRoute: URL?

    let snapshot: LocalAudioSnapshot
    let isChecking: Bool
    let workspaceZoom: WorkspaceZoomPreference
    let onAutoStarted: (LocalAudioSnapshot) -> Void
    let refresh: () -> Void
    let runCheck: () -> Void

    var body: some View {
        DesktopMeetingShellView(
            session: captureSession,
            uploadQueueItems: uploadQueueItems,
            pendingUploadCount: uploadQueueItems.filter { !$0.state.isTerminal }.count,
            cabinetConfigured: desktopCabinetConfiguration != nil,
            statusSummary: snapshot.summary,
            lastEventSummary: snapshot.lastEventSummary,
            isChecking: isChecking,
            onRefresh: refresh,
            onRunCheck: runCheck,
            onOpenMeetingsList: {
                selectedCabinetRoute = desktopCabinetConfiguration.map {
                    DesktopCabinetWorkspace.defaultRoute(configuration: $0)
                }
            }
        ) {
            CaptureControlView(
                session: captureSession,
                blockedReason: recordingBlocker,
                localRecordingStatus: localRecordingStatusText,
                localRecordingLocation: localRecordingLocation,
                muteTruthWarning: meetingMuteTruthWarningText,
                uploadQueueItems: uploadQueueItems,
                cabinetConfiguration: desktopCabinetConfiguration,
                routeSignalLevels: liveRouteSignalLevels,
                recordDisabled: recordingStartInProgress || recordingStopInProgress,
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
                onUploadRetry: { itemId in
                    retryUpload(itemId: itemId)
                },
                onUploadStopRetry: { itemId in
                    stopUploadRetry(itemId: itemId)
                },
                onUploadReview: { route in
                    selectedCabinetRoute = route
                }
            )
            .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.captureRegion)
        } meetingsWorkspace: {
            DesktopCabinetWorkspaceView(
                configuration: desktopCabinetConfiguration,
                initialRoute: selectedCabinetRoute,
                currentRoute: $selectedCabinetRoute,
                presentation: .shell,
                workspaceZoom: workspaceZoom
            )
        } diagnosticsContent: {
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
                AudioHealthView(state: snapshot.healthState)
                DiagnosticLogView(
                    path: AppLog.fileURL.path,
                    lastEvent: snapshot.lastEventSummary
                )
            }
            .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.nativeShellRegion)
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
            refreshUploadQueueAndProcess(reason: "app_appeared")
        }
        .task(id: localRecordingActive) {
            guard localRecordingActive else { return }
            while !Task.isCancelled {
                pollRecordingLevelsIfNeeded()
                try? await Task.sleep(nanoseconds: 200_000_000)
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
        .onReceive(NotificationCenter.default.publisher(for: .twoBrainRecDesktopAuthSessionDidChange)) { _ in
            refreshUploadQueueAndProcess(reason: "desktop_auth_session_changed")
        }
        .onDisappear {
            guard !terminationCleanupInProgress else { return }
            Task { await releaseCaptureResourcesForAppExit() }
        }
    }

    @MainActor
    private func startManualRecording() async {
        guard !recordingStartInProgress, !recordingStopInProgress else { return }
        if let captureSession, CaptureStatusItem.showsStopButton(for: captureSession) {
            return
        }
        recordingStartInProgress = true
        defer { recordingStartInProgress = false }

        localRecordingManifest = nil
        localRecordingLocation = nil
        recordingBlocker = nil
        let scopeApproval: CaptureScopeApproval
        do {
            scopeApproval = try captureScopeApprovalService.approve(
                scopeKind: .display,
                sourceDisplayName: "Current display/system audio",
                approvalMode: .userConfirmedSuggestedScope,
                eligibleReason: .manualMeetingScope
            )
        } catch {
            recordingBlocker = "Запись не началась: не удалось подтвердить область записи."
            return
        }
        do {
            let preparing = try captureController.beginPreparing(
                mode: .audioRecording,
                sourceAppEligibility: .eligible
            )
            captureSession = preparing
        } catch {
            recordingBlocker = "Запись не началась: \(recordingStartFailureMessage(for: error))"
            return
        }
        let microphoneSession = await microphoneCaptureService.requestPermissionAndPreflight(
            sessionId: "pending",
            inputDisplayName: "Default Microphone"
        )
        let systemAudioPermissionState = await systemAudioPermissionAuthorizer.requestPermission()
        let permissionGate = systemAudioPermissionGate.evaluate(
            microphone: microphoneSession.permissionState,
            systemAudio: systemAudioPermissionState
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
            _ = try await systemAudioCaptureService.start(
                sessionId: starting.id,
                permissionState: permissionGate.snapshot.systemAudio,
                scopeApproval: scopeApproval,
                startedAt: Date()
            )
            let incomingSource = systemAudioCaptureService.incomingSampleSource
            localRecordingWriter = LocalRecordingWriter(
                incomingSampleSourceFactory: { incomingSource },
                recordMicrophone: true
            )
            let directory = try await localRecordingWriter.startAsync(
                sessionId: starting.id,
                startedAt: Date(),
                scopeApproval: scopeApproval,
                permissions: permissionGate.snapshot,
                targetMuteCapability: targetMuteCapability,
                meetingMuteTruthEvidence: [targetMuteEvidence],
                limitationCopyShownAt: limitationCopyShownAt
            )
            localRecordingActive = true
            let active = try captureController.markCapturing()
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
            localRecordingActive = false
            liveRouteSignalLevels = .inactive
            let releasedSystemAudioSession = try? await systemAudioCaptureService.stop()
            await finalizeLocalRecordingForFailure(
                reason: "start_failure_cleanup",
                failureReason: releasedSystemAudioSession?.failureReason ?? .none
            )
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
    private func finalizeLocalRecordingForFailure(
        reason: String,
        failureReason: LocalRecordingFailureReason = .none
    ) async {
        guard await localRecordingWriter.isRecordingAsync() else {
            return
        }
        let recordingDirectory = await localRecordingWriter.currentDirectoryURLAsync()
        do {
            let manifest = try await localRecordingWriter.stopAsync(failureReason: failureReason)
            localRecordingManifest = manifest
            localRecordingLocation = recordingDirectory?.path ?? localRecordingLocation
            enqueueLocalRecordingForUpload(
                manifest: manifest,
                directoryURL: recordingDirectory,
                reason: reason
            )
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
            recordingBlocker = "Не удалось поставить запись на паузу: \(error)"
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
            recordingBlocker = "Не удалось продолжить запись: \(error)"
            AppLog.writeRaw(
                event: AuditEventName.recordingFailed.rawValue,
                detail: "resume_failed error=\(error)"
            )
        }
    }

    @MainActor
    private func stopManualRecording() async {
        guard !recordingStartInProgress, !recordingStopInProgress else { return }
        recordingStopInProgress = true
        localRecordingActive = false
        liveRouteSignalLevels = .inactive
        defer { recordingStopInProgress = false }

        do {
            _ = try captureController.requestStop(reason: .userRequested)
            let recordingDirectory = await localRecordingWriter.currentDirectoryURLAsync()
            let systemAudioSession = try await systemAudioCaptureService.stop()
            let manifest = try await localRecordingWriter.stopAsync(
                failureReason: systemAudioSession.failureReason
            )
            let stopped = try captureController.completeStop()
            captureSession = stopped
            localRecordingManifest = manifest
            localRecordingLocation = recordingDirectory?.path ?? localRecordingLocation
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
            enqueueLocalRecordingForUpload(
                manifest: manifest,
                directoryURL: recordingDirectory,
                reason: "manual_stop_finalized"
            )
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
            await finalizeLocalRecordingForFailure(
                reason: "stop_failure_cleanup",
                failureReason: releasedSystemAudioSession?.failureReason ?? .none
            )
            localRecordingActive = false
            liveRouteSignalLevels = .inactive
            recordingBlocker = "Не удалось остановить запись: \(error)"
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
        liveRouteSignalLevels = .inactive
        do {
            let manifest = try await localRecordingWriter.stopAsync(failureReason: failureReason)
            localRecordingManifest = manifest
            localRecordingLocation = recordingDirectory?.path ?? localRecordingLocation
            enqueueLocalRecordingForUpload(
                manifest: manifest,
                directoryURL: recordingDirectory,
                reason: "app_exit_resource_release"
            )
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
                let items = try await service.processDueItems()
                await MainActor.run {
                    uploadQueueItems = items
                    uploadQueueRefreshInProgress = false
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
    private func enqueueLocalRecordingForUpload(
        manifest: LocalRecordingManifest,
        directoryURL: URL?,
        reason: String
    ) {
        guard let directoryURL else { return }
        do {
            let item = try desktopUploadQueueService.enqueue(
                manifest: manifest,
                directoryURL: directoryURL,
                reason: reason
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

    @MainActor
    private func retryUpload(itemId: String) {
        do {
            _ = try desktopUploadQueueService.retry(itemId: itemId)
            uploadQueueItems = try desktopUploadQueueService.loadItems()
            AppLog.writeRaw(
                event: AuditEventName.uploadRetrying.rawValue,
                detail: "queueId=\(itemId) reason=manual_retry_requested"
            )
            refreshUploadQueueAndProcess(reason: "manual_retry")
        } catch {
            AppLog.writeRaw(
                event: AuditEventName.uploadFailed.rawValue,
                detail: "queueId=\(itemId) reason=manual_retry_failed error=\(error)"
            )
        }
    }

    @MainActor
    private func stopUploadRetry(itemId: String) {
        do {
            let item = try desktopUploadQueueService.stopRetry(itemId: itemId)
            uploadQueueItems = try desktopUploadQueueService.loadItems()
            AppLog.writeRaw(
                event: AuditEventName.uploadBlocked.rawValue,
                detail: "queueId=\(itemId) state=\(item.state.rawValue) reason=automatic_retry_stopped"
            )
        } catch {
            AppLog.writeRaw(
                event: AuditEventName.uploadFailed.rawValue,
                detail: "queueId=\(itemId) reason=stop_retry_failed error=\(error)"
            )
        }
    }

    private func recordingBlockerText(for snapshot: RecordingPrerequisiteSnapshot) -> String {
        let action = snapshot.recoveryAction.map(recoveryActionText) ?? "Проверьте состояние перед записью"
        switch snapshot.blockedReason {
        case .none:
            return ""
        case .routeNotReady, .publicationOnly:
            return "Запись не началась: звук еще не готов. \(action)."
        case .policyDisabled:
            return "Запись отключена политикой. \(action)."
        case .permissionDenied:
            return "Запись не началась: нужен доступ к микрофону или системному звуку. \(action)."
        case .storageUnsafe:
            return "Запись не началась: недостаточно безопасного места для локальной копии. \(action)."
        case .indicatorUnavailable:
            return "Запись не началась: локальный индикатор недоступен. \(action)."
        case .sourceAppIneligible:
            return "Запись не началась: источник не подтвержден. \(action)."
        case .alreadyRecording:
            return "Запись уже идет."
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
        default:
            return action
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
            return "Локальная запись идет"
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
            if liveRouteSignalLevels != .inactive {
                liveRouteSignalLevels = .inactive
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
                    if liveRouteSignalLevels != .inactive {
                        liveRouteSignalLevels = .inactive
                    }
                    return
                }
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
            }
        }
    }
}

@MainActor
private final class AppLifecycleDelegate: NSObject, NSApplicationDelegate {
    private var mainWindow: NSWindow?
    private let workspaceZoomStore = WorkspaceZoomStore()
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
        window.title = "2brain Rec"
        window.minSize = NSSize(width: 1040, height: 680)
        window.isReleasedWhenClosed = false
        window.isRestorable = false
        window.identifier = NSUserInterfaceItemIdentifier("2brain-rec-main-window")
        configureMainWindowCollectionBehavior(window)
        window.contentViewController = NSHostingController(
            rootView: AppContentRoot(workspaceZoomStore: workspaceZoomStore)
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
}

private extension Notification.Name {
    static let twoBrainRecApplicationShouldTerminate = Notification.Name("pro.2brain.rec.applicationShouldTerminate")
    static let twoBrainRecApplicationTerminationCleanupFinished = Notification.Name("pro.2brain.rec.applicationTerminationCleanupFinished")
}

private struct AppContentRoot: View {
    @ObservedObject private var workspaceZoomStore: WorkspaceZoomStore
    @State private var snapshot = LocalAudioSnapshot.placeholder()
    @State private var isChecking = false

    init(workspaceZoomStore: WorkspaceZoomStore) {
        self.workspaceZoomStore = workspaceZoomStore
    }

    var body: some View {
        ContentView(
            snapshot: snapshot,
            isChecking: isChecking,
            workspaceZoom: workspaceZoomStore.preference,
            onAutoStarted: { updated in
                snapshot = updated
            },
            refresh: {
                snapshot = LocalAudioSnapshot.placeholder(lastEventSummary: "Состояние обновлено")
                AppLog.write(event: "refresh", snapshot: snapshot)
            },
            runCheck: {
                isChecking = true
                snapshot = LocalAudioSnapshot.placeholder(lastEventSummary: "Права проверяются при старте записи")
                AppLog.write(event: "status_refresh", snapshot: snapshot)
                isChecking = false
            }
        )
        .frame(minWidth: 1040, minHeight: 680)
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

    static func placeholder(lastEventSummary: String = "Приложение открыто") -> LocalAudioSnapshot {
        let driverExists = FileManager.default.fileExists(
            atPath: "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"
        )
        let driverState: DriverInstallationState = driverExists ? .installed : .notInstalled
        let virtualDeviceState: VirtualDeviceAvailabilityState = driverExists ? .requiresRestart : .missing
        let health = AudioHealthState(
            driverState: driverState,
            virtualMicState: virtualDeviceState,
            virtualSpeakerState: virtualDeviceState,
            microphonePermission: .unknown,
            outputPermission: .unknown,
            passthroughStatus: .unknown,
            continuityStatus: "Запись системного звука использует права macOS.",
            bufferRisk: .healthy,
            livePassthroughStatus: .inactive,
            recoveryActions: []
        )
        return LocalAudioSnapshot(
            driverState: driverState,
            virtualMicrophoneState: virtualDeviceState,
            virtualSpeakerState: virtualDeviceState,
            routeVerification: nil,
            healthState: health,
            defaultInputName: nil,
            defaultOutputName: nil,
            defaultSystemOutputName: nil,
            coreAudioDeviceSummary: "pending",
            lastEventSummary: lastEventSummary
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
            lastEventSummary: "Состояние обновлено"
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
                ? "Локальный аудиомаршрут активен; запись начинается вручную."
                : (hasMic && hasSpeaker
                    ? "Виртуальные устройства видны для диагностики; запись использует права macOS."
                    : "Запись системного звука использует права macOS."),
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
                id: "local-mic-recording-status",
                path: .micToVirtualInput,
                validationType: validationType,
                target: "Local Microphone",
                status: micResult.status,
                failureReason: micResult.reason,
                recoveryAction: micResult.action,
                startedAt: now,
                finishedAt: now
            ),
            speaker: RouteVerification(
                id: "system-audio-recording-status",
                path: .remoteOutputToVirtualSpeaker,
                validationType: validationType,
                target: "System Audio",
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
        guard let input = system.defaultInput, input.inputChannels > 0, !input.isTwoBrainVirtual else {
            return checked
                ? (.failed, "physical_microphone_not_selected", "select_physical_microphone")
                : (.notStarted, nil, "refresh_local_audio_status")
        }
        if routeEngineState == .active {
            return (.passed, nil, nil)
        }
        return checked ? (.passed, nil, nil) : (.notStarted, nil, "refresh_local_audio_status")
    }

    private static func speakerRouteResult(
        system: CoreAudioSystemSnapshot,
        checked: Bool,
        routeEngineState: PassthroughRouteEngineState
    ) -> (status: RouteVerificationStatus, reason: String?, action: String?) {
        let output = system.defaultOutput?.usablePhysicalOutput ??
            system.defaultSystemOutput?.usablePhysicalOutput
        guard output != nil else {
            return checked
                ? (.failed, "physical_speaker_not_selected", "select_physical_speaker")
                : (.notStarted, nil, "refresh_local_audio_status")
        }
        if routeEngineState == .active {
            return (.passed, nil, nil)
        }
        return checked ? (.passed, nil, nil) : (.notStarted, nil, "refresh_local_audio_status")
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
        guard let input = system.defaultInput, input.inputChannels > 0, !input.isTwoBrainVirtual else {
            return "Check failed: select a physical microphone"
        }
        guard system.defaultOutput?.usablePhysicalOutput != nil ||
              system.defaultSystemOutput?.usablePhysicalOutput != nil else {
            return "Check failed: select a physical speaker or output"
        }
        if routeEngineState == .active {
            return "Check complete: \(SystemAudioStatusLabels.localAudioRouteActiveNotRecording)"
        }
        return "Check complete: local audio status refreshed; recording permissions are checked when you press Record"
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

    var usablePhysicalOutput: CoreAudioDeviceInfo? {
        outputChannels > 0 && !isTwoBrainVirtual ? self : nil
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
