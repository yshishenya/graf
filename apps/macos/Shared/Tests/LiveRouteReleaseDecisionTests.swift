import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteReleaseDecisionTests: XCTestCase {
    func testReleaseDeniedForActiveAmbiguousAndStaleEvidence() {
        let policy = LiveRouteReleasePolicy()
        let now = LiveRouteStabilityFixtures.now

        XCTAssertEqual(policy.decision(for: LiveRouteStabilityFixtures.clientActivity(), requestedReason: .meetingClientClosed, decidedAt: now).outcome, .keepActive)
        XCTAssertEqual(policy.decision(for: nil, requestedReason: .meetingClientClosed, decidedAt: now).reason, .deniedAmbiguousEvidence)
        XCTAssertEqual(policy.decision(for: LiveRouteStabilityFixtures.clientActivity(freshnessMs: 9_000), requestedReason: .meetingClientClosed, decidedAt: now).reason, .deniedStaleEvidence)
    }

    func testReleaseAllowedOnlyAfterClientClosedEvidence() {
        let snapshot = ClientActivitySnapshot(
            source: .validationFixture,
            microphoneOpen: false,
            microphoneRunning: false,
            speakerOpen: false,
            speakerRunning: false,
            stillUsesVirtualMicrophone: false,
            stillUsesVirtualSpeaker: false,
            freshnessMs: 100,
            naturalSilenceAllowed: false
        )

        let decision = LiveRouteReleasePolicy().decision(
            for: snapshot,
            requestedReason: .meetingClientClosed,
            decidedAt: LiveRouteStabilityFixtures.now
        )

        XCTAssertEqual(decision.outcome, .released)
        XCTAssertEqual(decision.reason, .meetingClientClosed)
    }
}
#endif
