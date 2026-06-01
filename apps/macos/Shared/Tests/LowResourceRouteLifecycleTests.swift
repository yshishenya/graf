import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourceRouteLifecycleTests: XCTestCase {
    func testIdleSafeDoesNotBecomeReadyFromPublicationOnly() {
        var snapshot = LowResourceTestFixtures.readySnapshot(clientOpen: false)
        snapshot.appBridgeHealth = AppBridgeHealthEvidence(
            heartbeatState: .waitingForApp,
            driverFailClosed: true
        )
        snapshot.resourceState = .idleSafe

        XCTAssertEqual(LowResourceRouteTruthEvaluator.readinessState(for: snapshot), .stale)
    }

    func testActiveRequiresExplicitClientIO() {
        let snapshot = LowResourceTestFixtures.readySnapshot(clientOpen: true)

        XCTAssertEqual(snapshot.clientActivity.source, .driverStartStop)
        XCTAssertTrue(snapshot.clientActivity.hasOpenStream)
        XCTAssertEqual(LowResourceRouteTruthEvaluator.readinessState(for: snapshot), .active)
    }

    func testFallbackStateIsPreserved() {
        var snapshot = LowResourceTestFixtures.readySnapshot(clientOpen: false)
        snapshot.resourceState = .fallback

        XCTAssertEqual(LowResourceRouteTruthEvaluator.readinessState(for: snapshot), .fallback)
    }
}
#endif
