import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingPrerequisiteGateTests: XCTestCase {
    func testCurrentCapturePrerequisitesAllowRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(validSnapshot())

        XCTAssertTrue(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .none)
        XCTAssertNil(decision.recoveryAction)
    }

    func testPolicyDisabledBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(policyAllowsRecording: false)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .policyDisabled)
    }

    func testMicrophonePermissionDeniedBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(microphonePermissionGranted: false)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .permissionDenied)
        XCTAssertEqual(decision.recoveryAction, "Grant microphone permission in System Settings")
    }

    func testSystemAudioPermissionDeniedBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(systemAudioPermissionGranted: false)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .permissionDenied)
        XCTAssertEqual(decision.recoveryAction, "Grant Screen & System Audio permission in System Settings")
    }

    func testUnsafeStorageBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(storageRisk: .critical)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .storageUnsafe)
    }

    func testMissingIndicatorBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(indicatorAvailable: false)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .indicatorUnavailable)
    }

    func testIneligibleSourceAppBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(sourceAppEligibility: .ineligible)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .sourceAppIneligible)
    }

    private func validSnapshot(
        policyAllowsRecording: Bool = true,
        microphonePermissionGranted: Bool = true,
        systemAudioPermissionGranted: Bool = true,
        storageRisk: LocalBufferRiskState = .healthy,
        indicatorAvailable: Bool = true,
        sourceAppEligibility: SourceAppEligibility = .eligible
    ) -> RecordingPrerequisiteSnapshot {
        RecordingPrerequisiteSnapshot(
            policyAllowsRecording: policyAllowsRecording,
            microphonePermissionGranted: microphonePermissionGranted,
            systemAudioPermissionGranted: systemAudioPermissionGranted,
            storageRisk: storageRisk,
            indicatorAvailable: indicatorAvailable,
            sourceAppEligibility: sourceAppEligibility,
            evaluatedAt: Date(timeIntervalSince1970: 1_777_777_777)
        )
    }
}
#endif
