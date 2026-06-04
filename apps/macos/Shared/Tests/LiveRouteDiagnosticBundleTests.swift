import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteDiagnosticBundleTests: XCTestCase {
    func testRouteEvidenceBundleIsLocalMetadataOnlyAndRedactsForbiddenContent() throws {
        let event = RouteEvidenceEvent(
            eventId: "evt",
            sessionId: "route-session",
            family: .validationRun,
            name: "validation.accepted",
            observedAt: LiveRouteStabilityFixtures.now,
            source: .validationScript,
            validationRun: LiveRouteStabilityFixtures.validationRun()
        )

        let bundle = try DiagnosticBundleService().buildRouteEvidenceBundle(
            events: [event],
            manifestOverrides: [
                "meetingContent": .string("forbidden")
            ]
        )

        XCTAssertNotNil(bundle.manifest["routeEvidenceEvents"])
        XCTAssertNotNil(bundle.manifest["validationRunEvidence"])
        XCTAssertNil(bundle.manifest["meetingContent"])
        XCTAssertTrue(bundle.removedFields.contains("meetingContent"))
    }
}
#endif
