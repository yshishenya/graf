import TwoBrainRecAppCore

#if canImport(XCTest)
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
            [.capture, .meetings, .localAudioReadiness]
        )
        XCTAssertEqual(DesktopCabinetWorkspaceView.embeddedSurfaceHeight, 420)
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
}
#endif
