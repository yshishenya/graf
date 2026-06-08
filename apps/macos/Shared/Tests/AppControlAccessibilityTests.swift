import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

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
}
#endif
