import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteAutorepairTests: XCTestCase {
    func testRecoverableDisruptionSucceedsOnlyAfterFreshEvidence() {
        let coordinator = LiveRouteAutorepairCoordinator(now: { LiveRouteStabilityFixtures.now })
        let freshActivity = LiveRouteStabilityFixtures.clientActivity()

        let attempt = coordinator.attempt(
            trigger: .coreaudiodRestart,
            timingTier: .normal,
            startedAt: LiveRouteStabilityFixtures.now,
            completedAt: LiveRouteStabilityFixtures.now.addingTimeInterval(1.5),
            clientActivity: freshActivity
        )

        XCTAssertEqual(attempt.outcome, .succeeded)
        XCTAssertTrue(attempt.isAcceptedSuccess)
    }

    func testRecoverableDisruptionOverTimingWindowIsDegraded() {
        let coordinator = LiveRouteAutorepairCoordinator(now: { LiveRouteStabilityFixtures.now })

        let attempt = coordinator.attempt(
            trigger: .coreaudiodRestart,
            timingTier: .normal,
            startedAt: LiveRouteStabilityFixtures.now,
            completedAt: LiveRouteStabilityFixtures.now.addingTimeInterval(2.1),
            clientActivity: LiveRouteStabilityFixtures.clientActivity()
        )

        XCTAssertEqual(attempt.outcome, .degradedSlow)
        XCTAssertFalse(attempt.isAcceptedSuccess)
    }

    func testRecoverableDisruptionWithoutFreshEvidenceIsDegraded() {
        let coordinator = LiveRouteAutorepairCoordinator(now: { LiveRouteStabilityFixtures.now })

        let attempt = coordinator.attempt(
            trigger: .browserStreamRecreated,
            timingTier: .normal,
            startedAt: LiveRouteStabilityFixtures.now,
            completedAt: LiveRouteStabilityFixtures.now.addingTimeInterval(6),
            clientActivity: LiveRouteStabilityFixtures.clientActivity(freshnessMs: 10_000)
        )

        XCTAssertEqual(attempt.outcome, .degradedSlow)
        XCTAssertFalse(attempt.isAcceptedSuccess)
    }
}
#endif
