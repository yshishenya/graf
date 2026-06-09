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

    func testLegacyDriverRepairActionIsParkedForMVPStatusCopy() {
        let label = AdaptiveStatusText.recoveryActionLabel("install_or_repair_driver")

        XCTAssertTrue(label.localizedCaseInsensitiveContains("parked"))
        XCTAssertTrue(label.localizedCaseInsensitiveContains("MVP recording"))
        XCTAssertFalse(label.localizedCaseInsensitiveContains("run installer"))
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

    func testHealthCanRecordDoesNotRequireVirtualDevicesForSystemAudioMVP() {
        let state = AudioHealthState(
            virtualMicState: .missing,
            virtualSpeakerState: .unavailable,
            microphonePermission: .granted,
            outputPermission: .granted,
            routeVerification: RouteVerificationSnapshot(
                mic: RouteVerification(
                    id: "mic",
                    path: .micToVirtualInput,
                    validationType: .syntheticSignal,
                    target: "Local Microphone",
                    status: .passed,
                    startedAt: Date(timeIntervalSince1970: 1),
                    finishedAt: Date(timeIntervalSince1970: 1)
                ),
                speaker: RouteVerification(
                    id: "system-audio",
                    path: .remoteOutputToVirtualSpeaker,
                    validationType: .syntheticSignal,
                    target: "System Audio",
                    status: .passed,
                    startedAt: Date(timeIntervalSince1970: 1),
                    finishedAt: Date(timeIntervalSince1970: 1)
                )
            ),
            passthroughStatus: .healthy,
            bufferRisk: .healthy
        )

        XCTAssertTrue(state.canRecord)
    }
}
#endif
