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
        XCTAssertEqual(DesktopMeetingShellChrome.shellBackgroundHex, "#191a1c")
        XCTAssertEqual(DesktopMeetingShellChrome.shellRailHex, "#202224")
        XCTAssertEqual(DesktopMeetingShellChrome.shellSurfaceHex, "#242629")
        XCTAssertEqual(DesktopMeetingShellChrome.recordingStripHex, "#342087")
        XCTAssertEqual(DesktopMeetingShellChrome.shellAccentHex, "#8c73ff")
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
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleCornerRadius, 10)
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
        XCTAssertFalse(source.contains(".accessibilityElement(children: .combine)"))
    }

    func testDesktopCaptureChromeUsesFeature104DensityAndContrastContracts() throws {
        XCTAssertEqual(DesktopMeetingShellChrome.spacingSmall, 8)
        XCTAssertEqual(DesktopMeetingShellChrome.spacingMedium, 12)
        XCTAssertEqual(DesktopMeetingShellChrome.spacingLarge, 16)
        XCTAssertEqual(DesktopMeetingShellChrome.spacingXLarge, 24)
        XCTAssertEqual(DesktopMeetingShellChrome.controlHeight, 36)
        XCTAssertEqual(DesktopMeetingShellChrome.minimumInteractiveTarget, 40)

        let root = try Self.repositoryRoot()
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        let captureSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Capture/CaptureControlView.swift"),
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
    }

    func testDesktopCabinetCopyStaysCleanRoomAndProductFacing() {
        let copy = [
            DesktopCabinetWorkspaceView.workspaceTitle,
            DesktopCabinetWorkspaceView.workspaceAccessibilityLabel,
            DesktopCabinetWorkspaceView.unavailableTitle,
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
        XCTAssertTrue(DesktopPermissionOnboardingView.systemAudioStepDetail.contains("перезапуск GRAF"))
        XCTAssertTrue(DesktopPermissionOnboardingView.startStepDetail.contains("кнопку записи"))
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
        XCTAssertTrue(source.contains("systemAudioPermissionAuthorizer.requestPermission()"))
        XCTAssertTrue(source.contains("if status.isReady {\n            permissionOnboardingPresented = false"))
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
