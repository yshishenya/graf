import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingPrerequisiteGateTests: XCTestCase {
    func testValidSnapshotAllowsRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(validSnapshot())

        XCTAssertTrue(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .none)
    }

    func testPublicationOnlyRouteBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(routeEvidenceKind: .publicationOnly)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .publicationOnly)
        XCTAssertEqual(decision.recoveryAction, "Run route readiness before recording")
    }

    func testStaleRouteBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(routeState: .stale, routeEvidenceKind: .stale)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .routeNotReady)
    }

    func testUnknownRouteEvidenceBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(routeEvidenceKind: .unknown)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .routeNotReady)
        XCTAssertEqual(decision.recoveryAction, "Confirm audio route evidence before recording")
    }

    func testSystemAudioCaptureDoesNotRequireLiveRouteState() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(routeState: .inactive, routeEvidenceKind: .systemAudioCapture)
        )

        XCTAssertTrue(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .none)
    }

    func testPolicyDisabledBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(policyAllowsRecording: false)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .policyDisabled)
    }

    func testPermissionDeniedBlocksRecordingStart() {
        let decision = RecordingPrerequisiteGate().evaluate(
            validSnapshot(microphonePermissionGranted: false)
        )

        XCTAssertFalse(decision.allowsRecording)
        XCTAssertEqual(decision.blockedReason, .permissionDenied)
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
        routeState: LivePassthroughStatus = .ready,
        routeEvidenceKind: RecordingRouteEvidenceKind = .lowResourceTruth,
        policyAllowsRecording: Bool = true,
        microphonePermissionGranted: Bool = true,
        storageRisk: LocalBufferRiskState = .healthy,
        indicatorAvailable: Bool = true,
        sourceAppEligibility: SourceAppEligibility = .eligible
    ) -> RecordingPrerequisiteSnapshot {
        RecordingPrerequisiteSnapshot(
            routeState: routeState,
            routeEvidenceKind: routeEvidenceKind,
            policyAllowsRecording: policyAllowsRecording,
            microphonePermissionGranted: microphonePermissionGranted,
            storageRisk: storageRisk,
            indicatorAvailable: indicatorAvailable,
            sourceAppEligibility: sourceAppEligibility,
            evaluatedAt: Date(timeIntervalSince1970: 1_777_777_777)
        )
    }
}
#endif
