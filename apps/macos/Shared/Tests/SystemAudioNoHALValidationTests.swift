import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioNoHALValidationTests: XCTestCase {
    func testEvidencePassesWhenMVPDoesNotDependOnHALOrVirtualDevices() {
        let evidence = SystemAudioNoHALEvidence(
            halRuntimeProbeExecuted: false,
            virtualDeviceSelectionRequired: false,
            driverRepairRequired: false,
            coreAudioRestartRequired: false,
            recordingUsedVirtualDevice: false
        )

        XCTAssertTrue(evidence.passesMVPBoundary)
    }

    func testEvidenceFailsWhenHALRuntimeProbeIsObserved() {
        let evidence = SystemAudioNoHALEvidence(
            halRuntimeProbeExecuted: true,
            virtualDeviceSelectionRequired: false,
            driverRepairRequired: false,
            coreAudioRestartRequired: false,
            recordingUsedVirtualDevice: false,
            gateStatus: .failed,
            failureReason: .halProbeObserved
        )

        XCTAssertFalse(evidence.passesMVPBoundary)
        XCTAssertEqual(evidence.failureReason, .halProbeObserved)
    }

    func testEvidenceFailsWhenVirtualDeviceOrDriverRepairIsRequired() {
        let virtualDeviceEvidence = SystemAudioNoHALEvidence(
            halRuntimeProbeExecuted: false,
            virtualDeviceSelectionRequired: true,
            driverRepairRequired: false,
            coreAudioRestartRequired: false,
            recordingUsedVirtualDevice: true,
            gateStatus: .failed,
            failureReason: .legacyNotReady
        )
        let driverRepairEvidence = SystemAudioNoHALEvidence(
            halRuntimeProbeExecuted: false,
            virtualDeviceSelectionRequired: false,
            driverRepairRequired: true,
            coreAudioRestartRequired: true,
            recordingUsedVirtualDevice: false,
            gateStatus: .failed,
            failureReason: .legacyNotReady
        )

        XCTAssertFalse(virtualDeviceEvidence.passesMVPBoundary)
        XCTAssertFalse(driverRepairEvidence.passesMVPBoundary)
    }
}
#endif
