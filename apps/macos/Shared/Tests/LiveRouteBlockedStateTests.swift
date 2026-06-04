import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteBlockedStateTests: XCTestCase {
    func testNonRecoverableReasonsProduceBlockedAttempts() {
        let coordinator = LiveRouteAutorepairCoordinator(now: { LiveRouteStabilityFixtures.now })

        for reason in AutorepairNonRecoverableReason.allCases {
            let attempt = coordinator.blockedAttempt(trigger: .unknownExternalDisruption, reason: reason)
            XCTAssertEqual(attempt.outcome, .blockedNonRecoverable)
            XCTAssertEqual(attempt.nonRecoverableReason, reason)
        }
    }
}
#endif
