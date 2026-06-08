import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioNoVirtualDeviceCopyTests: XCTestCase {
    func testDriverSetupBoundaryCopySaysVirtualDevicesAreNotRequired() {
        let copy = DriverSetupView.mvpBoundaryCopy

        XCTAssertTrue(copy.contains("does not require"))
        XCTAssertTrue(copy.localizedCaseInsensitiveContains("virtual devices"))
        XCTAssertFalse(copy.localizedCaseInsensitiveContains("before recording"))
        XCTAssertFalse(copy.localizedCaseInsensitiveContains("run check"))
    }

    func testMissingVirtualDeviceCopyDoesNotAskForRepairBeforeRecording() {
        let microphone = DriverSetupView.virtualDeviceText(.missing)
        let speaker = DriverSetupView.virtualDeviceText(.unavailable)
        let driver = DriverSetupView.driverText(.needsRepair)

        XCTAssertTrue(microphone.contains("Not required"))
        XCTAssertTrue(speaker.contains("not blocking recording"))
        XCTAssertFalse(driver.localizedCaseInsensitiveContains("needed"))
        XCTAssertFalse(driver.localizedCaseInsensitiveContains("before recording"))
    }

    func testMVPStatusRefreshCopyDoesNotAskForDriverRepair() {
        let label = AdaptiveStatusText.recoveryActionLabel("refresh_local_audio_status")

        XCTAssertEqual(label, "Refresh local audio status")
        XCTAssertFalse(label.localizedCaseInsensitiveContains("driver"))
        XCTAssertFalse(label.localizedCaseInsensitiveContains("repair"))
    }

    func testAudioEnvironmentRecoveryKeepsDriverDiagnosticsParkedForMVP() {
        let monitor = AudioEnvironmentMonitor(now: { Date(timeIntervalSince1970: 1) })
        let state = monitor.state(from: AudioEnvironmentSnapshot(
            driverState: .notInstalled,
            virtualMicState: .missing,
            virtualSpeakerState: .missing,
            microphonePermission: .granted,
            outputPermission: .granted,
            passthroughStatus: .failed,
            bufferRisk: .healthy
        ))
        let recovery = state.recoveryActions.joined(separator: " ")

        XCTAssertTrue(recovery.localizedCaseInsensitiveContains("parked"))
        XCTAssertTrue(recovery.localizedCaseInsensitiveContains("not required"))
        XCTAssertFalse(recovery.localizedCaseInsensitiveContains("install"))
        XCTAssertFalse(recovery.localizedCaseInsensitiveContains("repair"))
    }
}
#endif
