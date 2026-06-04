import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class AutorepairStateMachineContractTests: XCTestCase {
    func testAutorepairAllowsFreshEvidenceBeforeHealthyState() {
        let machine = AutorepairStateMachine()

        XCTAssertTrue(machine.canTransition(from: .recovering, to: .verifyingFreshEvidence))
        XCTAssertTrue(machine.canTransition(from: .verifyingFreshEvidence, to: .healthyAfterFreshEvidence))
        XCTAssertFalse(machine.canTransition(from: .recovering, to: .healthyAfterFreshEvidence))
    }

    func testTimingTiersMatchAcceptedWindows() {
        XCTAssertEqual(AutorepairTimingTier.normal.acceptedRecoverySeconds, 10)
        XCTAssertEqual(AutorepairTimingTier.osDeviceHeavy.acceptedRecoverySeconds, 30)
    }

    func testNonRecoverableReasonsCoverBlockedOutcomes() {
        XCTAssertEqual(
            Set(AutorepairNonRecoverableReason.allCases),
            [
                .permissionDenied,
                .unsupportedPhysicalRoute,
                .missingVirtualDevice,
                .missingPhysicalDevice,
                .meetingDeviceChangedAwayFromVirtual,
                .recordingIndicatorUnavailable
            ]
        )
    }

    func testAcceptedAttemptRequiresFreshEvidenceAndTimingWindow() {
        let startedAt = LiveRouteStabilityFixtures.now
        let attempt = AutorepairAttempt(
            attemptId: "repair-1",
            trigger: .coreaudiodRestart,
            timingTier: .normal,
            outcome: .succeeded,
            startedAt: startedAt,
            completedAt: startedAt.addingTimeInterval(8),
            freshEvidenceObservedAt: startedAt.addingTimeInterval(7)
        )

        XCTAssertTrue(attempt.isAcceptedSuccess)
    }
}
#endif
