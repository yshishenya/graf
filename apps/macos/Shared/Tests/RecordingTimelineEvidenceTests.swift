import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingTimelineEvidenceTests: XCTestCase {
    func testAcceptedDegradedAndFailedAlignmentBands() {
        let builder = RecordingTimelineEvidenceBuilder()

        XCTAssertEqual(builder.evidence(routeSessionId: "route", microphoneDurationMs: 10_000, incomingDurationMs: 7_000, interruptionCategory: .none).alignmentBand, .accepted)
        XCTAssertEqual(builder.evidence(routeSessionId: "route", microphoneDurationMs: 10_000, incomingDurationMs: 6_900, interruptionCategory: .routeGap).alignmentBand, .degradedWarning)
        XCTAssertEqual(builder.evidence(routeSessionId: "route", microphoneDurationMs: 10_000, incomingDurationMs: 0, interruptionCategory: .trackGap).alignmentBand, .degradedWarning)
        XCTAssertEqual(builder.evidence(routeSessionId: "route", microphoneDurationMs: 20_000, incomingDurationMs: 0, interruptionCategory: .trackGap).alignmentBand, .failed)
    }
}
#endif
