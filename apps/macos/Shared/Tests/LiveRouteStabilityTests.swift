import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteStabilityTests: XCTestCase {
    func testThirtyMinuteSimulatedActiveClientWindowHasNoUnexpectedReleaseDecision() {
        let policy = PassthroughAutoIdlePolicy(releaseAfterIdleTicks: 300)
        let activity = LiveRouteStabilityFixtures.clientActivity(freshnessMs: 1_000)
        var releaseCount = 0

        for tick in 0..<(30 * 60) {
            if policy.shouldReleasePhysicalRoute(
                bridgeActive: true,
                clientActivity: activity,
                consecutiveIdleTicks: tick
            ) {
                releaseCount += 1
            }
        }

        XCTAssertEqual(releaseCount, 0)
    }
}
#endif
