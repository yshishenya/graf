import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import Foundation
import XCTest

@MainActor
final class AppControlAccessibilityTests: XCTestCase {
    func testDesktopCabinetWorkspaceUsesProductLabelsNotImplementationLabels() {
        XCTAssertEqual(DesktopCabinetWorkspaceView.workspaceTitle, "Встречи")
        XCTAssertEqual(
            DesktopCabinetWorkspaceView.workspaceAccessibilityLabel,
            "Встречи и обзор записей"
        )
        XCTAssertFalse(DesktopCabinetWorkspaceView.workspaceAccessibilityLabel.localizedCaseInsensitiveContains("webview"))
        XCTAssertFalse(DesktopCabinetWorkspaceView.workspaceAccessibilityLabel.localizedCaseInsensitiveContains("api"))
    }

    func testDesktopCabinetLayoutStartsWithNativeCaptureThenMeetings() {
        XCTAssertEqual(
            DesktopCabinetLayoutPolicy.defaultSectionOrder,
            [.meetings, .capture, .localAudioReadiness]
        )
        XCTAssertEqual(DesktopCabinetWorkspaceView.embeddedSurfaceHeight, 420)
        XCTAssertGreaterThanOrEqual(DesktopCabinetWorkspaceView.shellEmbeddedSurfaceMinHeight, 520)
        XCTAssertEqual(DesktopMeetingShellChrome.collapsedInspectorWidth, 52)
        XCTAssertEqual(DesktopMeetingShellChrome.expandedInspectorWidth, 308)
        XCTAssertEqual(DesktopMeetingShellChrome.shellBackgroundHex, "#0a0a0b")
        XCTAssertEqual(DesktopMeetingShellChrome.shellRailHex, "#121214")
        XCTAssertEqual(DesktopMeetingShellChrome.shellSurfaceHex, "#1c1c1f")
        XCTAssertEqual(DesktopMeetingShellChrome.recordingStripHex, "#342087")
        XCTAssertEqual(DesktopMeetingShellChrome.shellAccentHex, "#8c73ff")
        XCTAssertEqual(DesktopMeetingShellChrome.webButtonHeight, 32)
        XCTAssertEqual(DesktopMeetingShellChrome.webButtonCornerRadius, 7)
        XCTAssertEqual(DesktopMeetingShellChrome.webButtonHorizontalPadding, 12)
        XCTAssertEqual(DesktopMeetingShellChrome.webButtonPrimaryHex, "#8c73ff")
        XCTAssertEqual(DesktopMeetingShellChrome.webButtonSecondaryDarkHex, "#26282c")
        XCTAssertEqual(DesktopMeetingShellChrome.webButtonBorderDarkHex, "#30343a")
        XCTAssertEqual(DesktopMeetingShellChrome.webEmbeddedBackgroundHex, DesktopMeetingShellChrome.shellBackgroundHex)
        XCTAssertEqual(DesktopMeetingShellChrome.fontStackDescription, "SF Pro Text / system")
        XCTAssertEqual(DesktopMeetingShellChrome.compactRailLabels, ["Статус записи", "Локальная сохранность"])
        XCTAssertEqual(DesktopCabinetWorkspaceView.embeddedWorkspaceMaxWidth, 1120)
        XCTAssertFalse(DesktopMeetingShellChrome.idleShowsNativeTopBar)
        XCTAssertEqual(DesktopMeetingShellChrome.recordingStripHeight, 44)
        XCTAssertGreaterThanOrEqual(
            DesktopMeetingShellChrome.recordingStripHeight,
            DesktopMeetingShellChrome.inspectorToggleHitSize
        )
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleHitSize, 44)
        XCTAssertGreaterThanOrEqual(DesktopMeetingShellChrome.inspectorToggleHitSize, 40)
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleCornerRadius, 12)
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleTopInset, 10)
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleTrailingInset, 4)
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleCollapsedSymbol, "chevron.left.2")
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleExpandedSymbol, "chevron.right.2")
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleCollapsedLabel, "Показать панель управления")
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleExpandedLabel, "Скрыть панель управления")
        XCTAssertEqual(DesktopMeetingShellChrome.compactRailStartLabel, "Начать запись")
        XCTAssertEqual(DesktopMeetingShellChrome.compactRailStopLabel, "Остановить запись")
        XCTAssertEqual(DesktopMeetingShellChrome.compactRailActionHitSize, 40)
        XCTAssertGreaterThanOrEqual(DesktopMeetingShellChrome.compactRailActionHitSize, 40)
        XCTAssertEqual(DesktopMeetingShellChrome.recordingTitle(for: .audioRecording), "Запись аудио")
        XCTAssertEqual(DesktopMeetingShellChrome.recordingTitle(for: .transcriptOnly), "Транскрибация")
    }

    func testInspectorDisclosureKeepsAccessibilityContract() {
        XCTAssertEqual(
            DesktopMeetingShellChrome.inspectorToggleLabel(isExpanded: false),
            "Показать панель управления"
        )
        XCTAssertEqual(
            DesktopMeetingShellChrome.inspectorToggleHint(isExpanded: false),
            "Раскрывает правую панель"
        )
        XCTAssertEqual(
            DesktopMeetingShellChrome.inspectorToggleLabel(isExpanded: true),
            "Скрыть панель управления"
        )
        XCTAssertEqual(
            DesktopMeetingShellChrome.inspectorToggleHint(isExpanded: true),
            "Сворачивает правую панель"
        )
    }

    func testDesktopInspectorExpansionStaysStableAndOpensOnlyForIntentOrActionableProblem() {
        XCTAssertFalse(
            DesktopMeetingShellChrome.shouldShowExpandedInspector(
                manualExpanded: false,
                hasActionableProblem: false
            )
        )
        XCTAssertTrue(
            DesktopMeetingShellChrome.shouldShowExpandedInspector(
                manualExpanded: true,
                hasActionableProblem: false
            )
        )
        XCTAssertTrue(
            DesktopMeetingShellChrome.shouldShowExpandedInspector(
                manualExpanded: false,
                hasActionableProblem: true
            )
        )
        XCTAssertTrue(
            DesktopMeetingShellChrome.shouldShowExpandedInspector(
                manualExpanded: true,
                hasActionableProblem: true
            )
        )
    }

    func testDesktopCaptureRailUsesDirectAccessibleActionsAndHonorsReduceMotion() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("@Environment(\\.accessibilityReduceMotion)"))
        XCTAssertTrue(source.contains("accessibilityReduceMotion ? nil : .easeInOut"))
        XCTAssertTrue(source.contains("DesktopMeetingShellChrome.compactRailActionHitSize"))
        XCTAssertTrue(source.contains("desktop-meeting-shell-start-recording-button"))
        XCTAssertTrue(source.contains("desktop-meeting-shell-stop-recording-button"))
        XCTAssertTrue(source.contains("DesktopMeetingShellChrome.compactRailStartLabel"))
        XCTAssertTrue(source.contains("DesktopMeetingShellChrome.compactRailStopLabel"))
    }

    func testCaptureStatusKeepsPauseResumeAndStopAsSeparateAccessibilityActions() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains(".accessibilityElement(children: .contain)"))
        XCTAssertTrue(source.contains(".accessibilityElement(children: .combine)"))
        XCTAssertTrue(source.contains(".accessibilityIdentifier(SystemAudioAccessibilityIdentifier.statusSurface)"))
        XCTAssertTrue(source.contains("SystemAudioAccessibilityIdentifier.recordingSource"))
        XCTAssertTrue(source.contains("sourceAccessibilityLabel(for: session)"))
        XCTAssertTrue(source.contains(".help(Self.sourceAccessibilityLabel(for: session)"))
        XCTAssertTrue(source.contains(".lineLimit(1)"))
        XCTAssertTrue(source.contains(".accessibilityRemoveTraits(.isSelected)"))
        XCTAssertTrue(source.contains("VStack(alignment: .leading, spacing: 8)"))
        XCTAssertGreaterThanOrEqual(
            source.components(
                separatedBy: ".frame(maxWidth: .infinity, minHeight: DesktopMeetingShellChrome.controlHeight)"
            ).count - 1,
            3
        )
        XCTAssertTrue(source.contains("checkmark.circle.fill"))
        XCTAssertTrue(source.contains("session.state == .stopped || session.state == .finalized"))
        XCTAssertFalse(source.contains(".keyboardShortcut(.escape, modifiers: [])"))
    }

    func testRecordingSourceUsesSharedAccessibilityContract() {
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.recordingSource, "systemAudio.status.source")
        XCTAssertEqual(SystemAudioStatusLabels.recordingSourceTitle, "Источник")
        XCTAssertEqual(SystemAudioStatusLabels.recordingSourceSystemAudio, "Системный звук")
        XCTAssertEqual(SystemAudioStatusLabels.recordingSourceUnknown, "Источник не определён")
        XCTAssertEqual(
            SystemAudioStatusLabels.recordingSourceAccessibilityLabel("Zoom"),
            "Источник: Zoom"
        )
    }

    func testDesktopCaptureChromeUsesFeature104DensityAndContrastContracts() throws {
        XCTAssertEqual(DesktopMeetingShellChrome.spacingSmall, 8)
        XCTAssertEqual(DesktopMeetingShellChrome.spacingMedium, 16)
        XCTAssertEqual(DesktopMeetingShellChrome.spacingLarge, 16)
        XCTAssertEqual(DesktopMeetingShellChrome.spacingXLarge, 24)
        XCTAssertEqual(DesktopMeetingShellChrome.controlHeight, 32)
        XCTAssertEqual(DesktopMeetingShellChrome.minimumInteractiveTarget, 40)

        let root = try Self.repositoryRoot()
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        let captureSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift"),
            encoding: .utf8
        )
        let settingsSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(shellSource.contains("@Environment(\\.colorSchemeContrast)"))
        XCTAssertTrue(captureSource.contains("@Environment(\\.colorSchemeContrast)"))
        XCTAssertTrue(shellSource.contains("colorSchemeContrast == .increased"))
        XCTAssertTrue(captureSource.contains("colorSchemeContrast == .increased"))
        XCTAssertTrue(shellSource.contains("DesktopMeetingShellChrome.spacingSmall"))
        XCTAssertTrue(shellSource.contains("DesktopMeetingShellChrome.spacingMedium"))
        XCTAssertTrue(captureSource.contains("DesktopMeetingShellChrome.spacingMedium"))
        XCTAssertTrue(shellSource.contains(".contentShape(Rectangle())"))
        XCTAssertTrue(shellSource.contains("DesktopWebButtonStyle"))
        XCTAssertTrue(shellSource.contains(".tint(DesktopMeetingShellChrome.shellAccentColor)"))
        XCTAssertFalse(shellSource.contains("buttonStyle(.borderedProminent)"))
        XCTAssertFalse(captureSource.contains("buttonStyle(.borderedProminent)"))
        XCTAssertTrue(settingsSource.contains(".tint(DesktopMeetingShellChrome.shellAccentColor)"))
    }

    func testFeature191NativeProductAccentsUseSharedVioletToken() throws {
        let root = try Self.repositoryRoot()
        let paths = [
            "apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift",
            "apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift",
            "apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift",
            "apps/macos/RecApp/App/TwoBrainRecApp.swift",
        ]

        for path in paths {
            let source = try String(
                contentsOf: root.appendingPathComponent(path),
                encoding: .utf8
            )
            XCTAssertTrue(source.contains("DesktopMeetingShellChrome.shellAccentColor"), path)
            XCTAssertFalse(source.contains(".blue"), path)
        }
    }

    func testFeature121NarrowKeyboardContrastAndMotionContract() throws {
        let root = try Self.repositoryRoot()
        let shellSource = try String(
            contentsOf: root.appendingPathComponent(
                "apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"
            ),
            encoding: .utf8
        )
        let captureSource = try String(
            contentsOf: root.appendingPathComponent(
                "apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift"
            ),
            encoding: .utf8
        )

        XCTAssertLessThan(
            DesktopMeetingShellChrome.collapsedInspectorWidth,
            DesktopMeetingShellChrome.expandedInspectorWidth
        )
        XCTAssertGreaterThanOrEqual(
            DesktopMeetingShellChrome.compactRailActionHitSize,
            DesktopMeetingShellChrome.minimumInteractiveTarget
        )
        XCTAssertTrue(shellSource.contains(".frame(maxWidth: .infinity, maxHeight: .infinity"))
        XCTAssertTrue(shellSource.contains("compactInspector"))
        XCTAssertTrue(shellSource.contains(".keyboardShortcut(\"r\", modifiers: [.command, .shift])"))
        XCTAssertTrue(captureSource.contains(".keyboardShortcut(\"r\", modifiers: [.command, .shift])"))
        XCTAssertFalse(shellSource.contains(".keyboardShortcut(.escape, modifiers: [])"))
        XCTAssertFalse(captureSource.contains(".keyboardShortcut(.escape, modifiers: [])"))
        XCTAssertTrue(shellSource.contains("@Environment(\\.accessibilityReduceMotion)"))
        XCTAssertTrue(shellSource.contains("accessibilityReduceMotion ? nil : .easeInOut"))
        XCTAssertTrue(shellSource.contains("@Environment(\\.colorSchemeContrast)"))
        XCTAssertTrue(captureSource.contains("@Environment(\\.colorSchemeContrast)"))
        XCTAssertTrue(shellSource.contains("colorSchemeContrast == .increased"))
        XCTAssertTrue(captureSource.contains("colorSchemeContrast == .increased"))
        let joinPrompt = DesktopCalendarPrompt(
            id: "join-prompt",
            kind: .join,
            eventId: "event",
            title: "Встреча началась",
            message: "Открыть встречу?",
            primaryActionTitle: "Открыть встречу",
            accessibilityLabel: "Встреча началась"
        )
        XCTAssertTrue(
            CaptureControlView.shouldShowDirectRecordButton(
                for: nil,
                calendarPrompt: joinPrompt
            )
        )
    }

    func testDesktopCabinetCopyStaysCleanRoomAndProductFacing() {
        let copy = [
            DesktopCabinetWorkspaceView.workspaceTitle,
            DesktopCabinetWorkspaceView.workspaceAccessibilityLabel,
            DesktopCabinetState.offline.unavailableTitle,
            DesktopCabinetState.offline.userMessage,
            DesktopMeetingShellChrome.compactRailStartLabel,
            DesktopMeetingShellChrome.compactRailStopLabel
        ]

        for text in copy {
            XCTAssertFalse(text.localizedCaseInsensitiveContains("krisp"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("webview"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("api"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("route"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("@"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("/Users/"))
        }
    }

    func testUnavailableWorkspaceCentersHumanRecoveryAtShellSize() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("VStack(alignment: .center"))
        XCTAssertTrue(source.contains(".multilineTextAlignment(.center)"))
        XCTAssertTrue(source.contains("maxHeight: presentation == .shell ? .infinity : nil"))
        XCTAssertTrue(source.contains("DesktopMeetingShellChrome.minimumInteractiveTarget"))
        XCTAssertTrue(source.contains("activeCabinetState.recoverySystemImage"))
        XCTAssertTrue(source.contains("accessibilityElement(children: recoveryTarget == nil ? .combine : .contain)"))
        XCTAssertTrue(source.contains(".accessibilityLabel(title)"))
        XCTAssertEqual(DesktopCabinetState.offline.recoveryActionTitle, "Повторить")
        XCTAssertFalse(DesktopCabinetState.offline.userMessage.localizedCaseInsensitiveContains("сервером rec"))
        XCTAssertFalse(DesktopCabinetState.offline.userMessage.localizedCaseInsensitiveContains("пароли календаря"))
    }

    func testStartupPermissionOnboardingTracksBothMacPermissions() {
        XCTAssertTrue(
            DesktopPermissionOnboardingStatus(
                microphone: .granted,
                systemAudio: .granted
            ).isReady
        )
        XCTAssertFalse(
            DesktopPermissionOnboardingStatus(
                microphone: .granted,
                systemAudio: .unknown
            ).isReady
        )
        XCTAssertEqual(
            DesktopPermissionOnboardingSettings.microphoneURL.scheme,
            "x-apple.systempreferences"
        )
        XCTAssertEqual(
            DesktopPermissionOnboardingSettings.screenAndSystemAudioURL.scheme,
            "x-apple.systempreferences"
        )
        XCTAssertEqual(
            DesktopPermissionOnboardingAccessibilityIdentifier.sheet,
            "desktop.permissionOnboarding.sheet"
        )
    }

    func testStartupPermissionOnboardingCopyKeepsManualRecordingBoundary() {
        let copy = [
            DesktopPermissionOnboardingView.title,
            DesktopPermissionOnboardingView.subtitle,
            DesktopPermissionOnboardingView.systemAudioStepDetail,
            DesktopPermissionOnboardingView.startStepTitle,
            DesktopPermissionOnboardingView.startStepDetail
        ]

        XCTAssertTrue(DesktopPermissionOnboardingView.subtitle.contains("Запись не начнется"))
        XCTAssertTrue(DesktopPermissionOnboardingView.systemAudioStepDetail.contains("проверьте снова"))
        XCTAssertTrue(DesktopPermissionOnboardingView.restartDetail.contains("Не сбрасывайте все разрешения"))
        XCTAssertTrue(DesktopPermissionOnboardingView.startStepDetail.contains("кнопку записи"))
        XCTAssertEqual(DesktopPermissionOnboardingView.openSettingsTitle, "Открыть настройки macOS")
        XCTAssertEqual(DesktopPermissionOnboardingView.retryTitle, "Проверить снова")
        XCTAssertEqual(DesktopPermissionOnboardingView.restartTitle, "Перезапустить GRAF")
        XCTAssertTrue(DesktopPermissionOnboardingView.microphoneDeniedDetail.contains("Откройте настройки"))
        XCTAssertEqual(
            DesktopPermissionOnboardingAccessibilityIdentifier.restartButton,
            "desktop.permissionOnboarding.restart"
        )
        for text in copy {
            XCTAssertFalse(text.localizedCaseInsensitiveContains("krisp"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("api"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("@"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("/Users/"))
        }
    }

    func testDesktopAppPresentsStartupPermissionOnboardingWithoutStartingRecording() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains(".sheet(isPresented: $permissionOnboardingPresented)"))
        XCTAssertTrue(source.contains("refreshPermissionOnboarding(reason: \"app_appeared\", presentIfNeeded: true)"))
        XCTAssertTrue(source.contains("refreshPermissionOnboarding(reason: \"app_became_active\", presentIfNeeded: false)"))
        XCTAssertTrue(source.contains("microphoneCaptureService.preflight("))
        XCTAssertTrue(source.contains("sessionId: \"startup-permission-onboarding\""))
        XCTAssertTrue(source.contains("microphoneCaptureService.requestPermissionAndPreflight("))
        XCTAssertTrue(source.contains("openMicrophonePermissionSettings()"))
        XCTAssertTrue(source.contains("microphoneCaptureService.requestPermissionForSettings()"))
        XCTAssertTrue(source.contains("systemAudioPermissionAuthorizer.requestPermission()"))
        XCTAssertTrue(source.contains("systemAudioPermissionAuthorizer.verifyCurrentPermission()"))
        XCTAssertTrue(source.contains("refreshPermissionOnboardingWithFunctionalProbe"))
        XCTAssertTrue(source.contains("permissionFunctionalProbeInProgress"))
        XCTAssertTrue(source.contains("lastObservedSystemAudioPermission"))
        XCTAssertTrue(source.contains("systemAudioPermissionTransitionRequiresRestart"))
        XCTAssertTrue(source.contains("observeSystemAudioPermission"))
        XCTAssertTrue(source.contains("effectiveSystemAudioPermissionState"))
        XCTAssertTrue(source.contains("permissionOnboardingPresented = true"))
        XCTAssertTrue(source.contains("if status.isReady && !permissionRestartRequired {\n            permissionOnboardingPresented = false"))
        XCTAssertTrue(source.contains("restartRequired: permissionRestartRequired"))
        XCTAssertTrue(source.contains("status: effectivePermissionOnboardingStatus"))
        XCTAssertTrue(source.contains("applicationName: currentApplicationDisplayName"))
        XCTAssertTrue(source.contains("Bundle.main.bundleIdentifier"))
        XCTAssertTrue(source.contains("currentApplicationIdentityDetail"))
        XCTAssertTrue(source.contains("let previousPermissionState = permissionOnboardingStatus.systemAudio"))
        XCTAssertTrue(source.contains("onRestart: {"))
        XCTAssertTrue(source.contains("effectivePermissionOnboardingStatus"))
        XCTAssertTrue(source.contains("presentPermissionRecoveryAfterSystemAudioRuntimeFailure"))
        XCTAssertTrue(source.contains("captureError == .runtimeStartFailed"))
        XCTAssertTrue(source.contains("systemAudioPermissionAuthorizer.currentPermissionState() == .granted"))
        XCTAssertTrue(source.contains("permissionRestartRequired = true"))
        XCTAssertTrue(source.contains("appDelegate.requestRelaunch()"))
        XCTAssertTrue(source.contains("relaunchAfterTermination"))
        XCTAssertTrue(source.contains("configuration.createsNewApplicationInstance = true"))
        XCTAssertTrue(source.contains("NSWorkspace.shared.openApplication("))
        XCTAssertFalse(source.contains("requestStartupMicrophonePermission() async {\n        await startManualRecording"))
        XCTAssertFalse(source.contains("requestStartupSystemAudioPermission() async {\n        await startManualRecording"))
    }

    func testDesktopAppDismissesPermissionSheetsBeforeTerminationCleanup() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("permissionOnboardingPresented = false"))
        XCTAssertTrue(source.contains("permissionOnboardingRequestInProgress = false"))
        XCTAssertTrue(source.contains("dismissMeetingDetectionPrompt()"))
        XCTAssertTrue(source.contains("dismissModalWindowsForTermination()"))
        XCTAssertTrue(source.contains("window.endSheet(attachedSheet)"))
        XCTAssertTrue(source.contains("sheetParent.endSheet(window)"))
        XCTAssertTrue(source.contains("NSApp.modalWindow"))
        XCTAssertTrue(source.contains("NSApp.abortModal()"))
        XCTAssertTrue(source.contains("window.orderOut(nil)"))
        XCTAssertTrue(source.contains("window.close()"))
    }

    func testDesktopAppDoesNotRequestPermissionsDuringTerminationCleanup() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )
        let terminationBlock = try XCTUnwrap(
            source.range(of: ".onReceive(NotificationCenter.default.publisher(for: .twoBrainRecApplicationShouldTerminate))")
        )
        let nextReceive = try XCTUnwrap(
            source[terminationBlock.upperBound...].range(of: ".onReceive(NotificationCenter.default.publisher(for: .twoBrainRecDesktopAuthSessionDidChange))")
        )
        let block = source[terminationBlock.lowerBound..<nextReceive.lowerBound]

        XCTAssertFalse(block.contains("requestStartupMicrophonePermission"))
        XCTAssertFalse(block.contains("requestStartupSystemAudioPermission"))
        XCTAssertFalse(block.contains("openPermissionSettings"))
        XCTAssertTrue(block.contains("releaseCaptureResourcesForAppExit()"))
    }

    func testCalendarPromptAccessibilityCopyPreservesManualRecordingBoundary() {
        let label = SystemAudioStatusLabels.calendarPromptAccessibilityLabel(
            title: SystemAudioStatusLabels.calendarGenericMeetingTitle,
            action: SystemAudioStatusLabels.calendarPromptRecordActionTitle
        )

        XCTAssertEqual(SystemAudioAccessibilityIdentifier.calendarPrompt, "systemAudio.calendar.prompt")
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.calendarPromptPrimaryButton, "systemAudio.calendar.prompt.primary")
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.calendarPromptDismissButton, "systemAudio.calendar.prompt.dismiss")
        XCTAssertTrue(label.contains("Запись не начинается автоматически"))
        XCTAssertFalse(label.localizedCaseInsensitiveContains("@"))
        XCTAssertFalse(label.localizedCaseInsensitiveContains("http"))
    }

    func testMeetingDetectionAccessibilityCopyDoesNotMentionRawLogsOrSecrets() {
        let label = SystemAudioStatusLabels.meetingDetectionAccessibilityLabel(
            status: "Определение включено",
            health: "Работает в фоне"
        )

        XCTAssertTrue(label.contains(SystemAudioStatusLabels.meetingDetectionSettingsTitle))
        XCTAssertFalse(label.localizedCaseInsensitiveContains("raw"))
        XCTAssertFalse(label.localizedCaseInsensitiveContains("log"))
        XCTAssertFalse(label.localizedCaseInsensitiveContains("token"))
        XCTAssertFalse(label.localizedCaseInsensitiveContains("@"))
    }

    func testMeetingDetectionSettingsExposeDetectAndAskAndAutoRecordList() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent(
                    "apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift"
                ),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("ScrollView"))
        XCTAssertTrue(source.contains("Запрашивать запись"))
        XCTAssertTrue(source.contains("Автозапись"))
        XCTAssertTrue(source.contains("ForEach(promptCapableTargets"))
        XCTAssertTrue(source.contains("Всегда писать") || source.contains("autoRecordSectionDetail"))
        XCTAssertTrue(source.contains("autoRecordDisabledSectionDetail"))
        XCTAssertTrue(source.contains("settings.detectionMode == .detectAndAsk"))
        XCTAssertTrue(source.contains("selectAllAutoRecordTargets"))
        XCTAssertTrue(source.contains("clearAutoRecordTargets"))
        XCTAssertTrue(source.contains("MeetingTargetRegistryStore"))
        XCTAssertTrue(source.contains("twoBrainRecMeetingTargetRegistryDidChange"))
        XCTAssertFalse(source.localizedCaseInsensitiveContains("diagnostic"))
    }

    func testEmbeddedSettingsRouteOpensNativeMeetingDetectionWindow() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent(
                    "apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift"
                ),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("decision.route.kind == .meetingDetectionSettings"))
        XCTAssertTrue(source.contains("navigationController.cancelPendingNavigation(webView: webView)"))
        XCTAssertTrue(source.contains("onOpenMeetingDetectionSettings()"))
        XCTAssertTrue(source.contains("decisionHandler(.cancel)"))
    }

    func testDesktopAppInstallsStandardEditMenuCommandsForEmbeddedCabinetFields() throws {
        let source = try String(
            contentsOf: Self.repositoryRoot()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        for command in [
            "#selector(NSText.cut(_:))",
            "#selector(NSText.copy(_:))",
            "#selector(NSText.paste(_:))",
            "#selector(NSText.selectAll(_:))"
        ] {
            XCTAssertTrue(source.contains(command), "Missing edit command \(command)")
        }
        XCTAssertTrue(source.contains("installMainMenu(on: app, zoomTarget: appDelegate)"))
        XCTAssertTrue(source.contains("withTitle: \"Settings...\""))
        XCTAssertTrue(source.contains("#selector(AppLifecycleDelegate.openSettings(_:))"))
        XCTAssertTrue(source.contains("MeetingDetectionSettingsView()"))
        XCTAssertTrue(source.contains("WorkspaceZoomMenu.items"))
        XCTAssertTrue(source.contains("increaseWorkspaceZoom"))
        XCTAssertTrue(source.contains("decreaseWorkspaceZoom"))
        XCTAssertTrue(source.contains("resetWorkspaceZoom"))
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let appSourceURL = candidate.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift")
            if FileManager.default.fileExists(atPath: appSourceURL.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "AppControlAccessibilityTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
