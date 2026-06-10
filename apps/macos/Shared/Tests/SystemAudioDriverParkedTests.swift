import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioDriverParkedTests: XCTestCase {
    func testMVPReadinessIgnoresUnavailableDriverDiagnostics() {
        let readiness = SystemAudioDriverParkedReadiness(
            driverState: .notInstalled,
            microphoneState: .missing,
            speakerState: .missing,
            routeVerificationReady: false
        )

        XCTAssertTrue(readiness.mvpRecordingIgnoresDriverDiagnostics)
        XCTAssertTrue(readiness.summary.contains("Record"))
        XCTAssertFalse(readiness.summary.localizedCaseInsensitiveContains("install"))
        XCTAssertFalse(readiness.summary.localizedCaseInsensitiveContains("repair"))
        XCTAssertFalse(readiness.summary.localizedCaseInsensitiveContains("restart"))
    }

    func testDriverDiagnosticSummaryDoesNotBlockSystemAudioMVP() {
        let absent = SystemAudioDriverParkedReadiness(
            driverState: .uninstalled,
            microphoneState: .unavailable,
            speakerState: .unavailable,
            routeVerificationReady: false
        )
        let maintenance = SystemAudioDriverParkedReadiness(
            driverState: .needsRepair,
            microphoneState: .requiresRestart,
            speakerState: .requiresRestart,
            routeVerificationReady: false
        )

        XCTAssertTrue(absent.driverDiagnosticSummary.contains("can still use macOS capture permissions"))
        XCTAssertTrue(maintenance.driverDiagnosticSummary.contains("parked"))
        XCTAssertTrue(absent.virtualDeviceDiagnosticSummary.contains("not an MVP recording prerequisite"))
    }
}
#endif
