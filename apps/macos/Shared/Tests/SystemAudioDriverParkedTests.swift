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
        XCTAssertTrue(readiness.summary.contains("записи"))
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

        XCTAssertTrue(absent.driverDiagnosticSummary.contains("права macOS"))
        XCTAssertTrue(maintenance.driverDiagnosticSummary.contains("отложено"))
        XCTAssertTrue(absent.virtualDeviceDiagnosticSummary.contains("не обязательны"))
    }
}
#endif
