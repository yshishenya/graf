import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteClientActivityTests: XCTestCase {
    func testFreshVirtualClientActivityIsIndependentFromAudioEnergy() {
        let snapshot = ClientActivitySnapshot(
            source: .validationFixture,
            microphoneOpen: true,
            microphoneRunning: false,
            speakerOpen: true,
            speakerRunning: false,
            stillUsesVirtualMicrophone: true,
            stillUsesVirtualSpeaker: true,
            freshnessMs: 250,
            naturalSilenceAllowed: true
        )

        XCTAssertEqual(LiveRouteClientActivityPolicy().status(for: snapshot), .active)
        XCTAssertTrue(LiveRouteClientActivityPolicy().shouldPreserveRoute(for: snapshot))
    }

    func testOneSidedActivityPreservesRoute() {
        let snapshot = ClientActivitySnapshot(
            source: .validationFixture,
            microphoneOpen: true,
            microphoneRunning: false,
            speakerOpen: false,
            speakerRunning: false,
            stillUsesVirtualMicrophone: true,
            stillUsesVirtualSpeaker: true,
            freshnessMs: 250,
            naturalSilenceAllowed: true
        )

        XCTAssertEqual(LiveRouteClientActivityPolicy().status(for: snapshot), .oneSided)
        XCTAssertTrue(LiveRouteClientActivityPolicy().shouldPreserveRoute(for: snapshot))
    }

    func testStaleClientActivityDoesNotClaimPreservation() {
        let snapshot = LiveRouteStabilityFixtures.clientActivity(freshnessMs: 8_000)

        XCTAssertEqual(LiveRouteClientActivityPolicy().status(for: snapshot), .stale)
        XCTAssertFalse(LiveRouteClientActivityPolicy().shouldPreserveRoute(for: snapshot))
    }
}
#endif
