import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteIdleRegressionTests: XCTestCase {
    func testObservedThreeHundredTickPatternDoesNotReleaseFreshClientEvidence() {
        let policy = PassthroughAutoIdlePolicy(releaseAfterIdleTicks: 300)

        XCTAssertFalse(policy.shouldReleasePhysicalRoute(
            bridgeActive: true,
            clientActivity: LiveRouteStabilityFixtures.clientActivity(),
            consecutiveIdleTicks: 300
        ))
    }
}
#endif
