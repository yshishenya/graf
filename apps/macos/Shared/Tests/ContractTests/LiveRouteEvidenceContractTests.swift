import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteEvidenceContractTests: XCTestCase {
    func testRouteEvidenceIncludesAllRequiredFamilies() {
        XCTAssertEqual(
            Set(RouteEvidenceFamily.allCases),
            [
                .routeLifecycle,
                .clientActivity,
                .defaultRoute,
                .frameContinuity,
                .autorepair,
                .releaseDecision,
                .recordingTimeline,
                .validationRun,
                .userAction
            ]
        )
    }

    func testRouteEvidenceSerializesRequiredMetadataFields() throws {
        let event = LiveRouteStabilityFixtures.routeEvent()
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: event.jsonData()) as? [String: Any])

        XCTAssertEqual(object["eventId"] as? String, "evt-019")
        XCTAssertEqual(object["sessionId"] as? String, "route-session-019")
        XCTAssertEqual(object["family"] as? String, "client_activity")
        XCTAssertEqual(object["name"] as? String, "client_activity.fresh")
        XCTAssertEqual(object["source"] as? String, "validation_script")
        XCTAssertEqual(object["redactionState"] as? String, "redacted")
        XCTAssertNil(object["rawAudio"])
        XCTAssertNil(object["transcriptText"])
        XCTAssertNil(object["meetingContent"])
    }
}
#endif
