import TwoBrainRecAppCore

#if canImport(XCTest)
import Foundation
import XCTest

@MainActor
final class AppControlAccessibilityTests: XCTestCase {
    func testDriverSetupButtonsExposeExplicitAccessibilityLabels() {
        XCTAssertEqual(
            DriverSetupView.installButtonAccessibilityLabel,
            "Install audio driver"
        )
        XCTAssertEqual(
            DriverSetupView.repairButtonAccessibilityLabel,
            "Repair audio driver"
        )
    }

    func testRouteVerificationButtonLabelsDoNotImplyRecording() {
        XCTAssertEqual(
            RouteVerificationView.runCheckButtonAccessibilityLabel,
            "Run audio readiness check"
        )
        XCTAssertEqual(
            RouteVerificationView.checkingButtonAccessibilityLabel,
            "Audio readiness check is running"
        )
    }

    func testUninstallResultButtonsExposeExplicitAccessibilityLabels() {
        XCTAssertEqual(
            UninstallResultView.openSoundSettingsAccessibilityLabel,
            "Open Sound Settings"
        )
        XCTAssertEqual(
            UninstallResultView.doneAccessibilityLabel,
            "Close uninstall result"
        )
    }

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
        XCTAssertEqual(DesktopMeetingShellChrome.sidebarWidth, 152)
        XCTAssertEqual(DesktopMeetingShellChrome.collapsedInspectorWidth, 56)
        XCTAssertEqual(DesktopMeetingShellChrome.expandedInspectorWidth, 300)
        XCTAssertEqual(DesktopMeetingShellChrome.shellBackgroundHex, "#191a1c")
        XCTAssertEqual(DesktopMeetingShellChrome.shellSidebarHex, "#202224")
        XCTAssertEqual(DesktopMeetingShellChrome.shellRailHex, "#202224")
        XCTAssertEqual(DesktopMeetingShellChrome.shellSurfaceHex, "#242629")
        XCTAssertEqual(DesktopMeetingShellChrome.webEmbeddedBackgroundHex, DesktopMeetingShellChrome.shellBackgroundHex)
        XCTAssertEqual(DesktopCabinetWorkspaceView.embeddedWorkspaceMaxWidth, 820)
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleHitSize, 44)
        XCTAssertGreaterThanOrEqual(DesktopMeetingShellChrome.inspectorToggleHitSize, 40)
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleCornerRadius, 10)
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleCollapsedSymbol, "chevron.left.2")
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleExpandedSymbol, "chevron.right.2")
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleCollapsedLabel, "Показать панель управления")
        XCTAssertEqual(DesktopMeetingShellChrome.inspectorToggleExpandedLabel, "Скрыть панель управления")
    }

    func testDesktopProfileMenuKeepsExpectedKrispLikeActionsInRussian() {
        let labels = DesktopMeetingShellChrome.profileMenuLabels
        for expected in [
            "Внешний вид",
            "Настройки",
            "Диагностика",
            "Ресурсы",
            "Связаться с поддержкой",
            "Оставить отзыв",
            "Сообщество Slack",
            "Выйти",
            "Закрыть 2brain Rec полностью"
        ] {
            XCTAssertTrue(labels.contains(expected), "Missing profile menu label \(expected)")
        }
    }

    func testDesktopCabinetCopyStaysCleanRoomAndProductFacing() {
        let copy = [
            DesktopCabinetWorkspaceView.workspaceTitle,
            DesktopCabinetWorkspaceView.workspaceAccessibilityLabel,
            DesktopCabinetWorkspaceView.unavailableTitle,
            CaptureControlView.uploadReviewButtonTitle
        ]

        XCTAssertEqual(CaptureControlView.uploadReviewButtonTitle, "Открыть обзор")
        for text in copy {
            XCTAssertFalse(text.localizedCaseInsensitiveContains("krisp"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("webview"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("api"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("route"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("@"))
            XCTAssertFalse(text.localizedCaseInsensitiveContains("/Users/"))
        }
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
        XCTAssertTrue(source.contains("installMainMenu(on: app)"))
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
