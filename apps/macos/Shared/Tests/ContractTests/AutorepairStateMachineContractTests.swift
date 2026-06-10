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
        XCTAssertEqual(AutorepairTimingTier.normal.acceptedRecoverySeconds, 2)
        XCTAssertEqual(AutorepairTimingTier.osDeviceHeavy.acceptedRecoverySeconds, 10)
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
            completedAt: startedAt.addingTimeInterval(1.8),
            freshEvidenceObservedAt: startedAt.addingTimeInterval(1.7)
        )

        XCTAssertTrue(attempt.isAcceptedSuccess)
    }

    func testAcceptedAttemptRejectsTimingBoundaryOverruns() {
        let startedAt = LiveRouteStabilityFixtures.now
        let normalBoundary = AutorepairAttempt(
            attemptId: "repair-normal-boundary",
            trigger: .browserStreamRecreated,
            timingTier: .normal,
            outcome: .succeeded,
            startedAt: startedAt,
            completedAt: startedAt.addingTimeInterval(2.0),
            freshEvidenceObservedAt: startedAt.addingTimeInterval(2.0)
        )
        let normalOverrun = AutorepairAttempt(
            attemptId: "repair-normal-overrun",
            trigger: .browserStreamRecreated,
            timingTier: .normal,
            outcome: .succeeded,
            startedAt: startedAt,
            completedAt: startedAt.addingTimeInterval(2.1),
            freshEvidenceObservedAt: startedAt.addingTimeInterval(2.1)
        )
        let heavyBoundary = AutorepairAttempt(
            attemptId: "repair-heavy-boundary",
            trigger: .sleepWake,
            timingTier: .osDeviceHeavy,
            outcome: .succeeded,
            startedAt: startedAt,
            completedAt: startedAt.addingTimeInterval(10.0),
            freshEvidenceObservedAt: startedAt.addingTimeInterval(10.0)
        )
        let heavyOverrun = AutorepairAttempt(
            attemptId: "repair-heavy-overrun",
            trigger: .sleepWake,
            timingTier: .osDeviceHeavy,
            outcome: .succeeded,
            startedAt: startedAt,
            completedAt: startedAt.addingTimeInterval(10.1),
            freshEvidenceObservedAt: startedAt.addingTimeInterval(10.1)
        )

        XCTAssertTrue(normalBoundary.isAcceptedSuccess)
        XCTAssertFalse(normalOverrun.isAcceptedSuccess)
        XCTAssertTrue(heavyBoundary.isAcceptedSuccess)
        XCTAssertFalse(heavyOverrun.isAcceptedSuccess)
    }
}
#endif
