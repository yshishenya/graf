import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingTimelineEvidenceContractTests: XCTestCase {
    func testTimelineAlignmentBandsMatchContractThresholds() {
        XCTAssertEqual(RecordingTimelineIntegrityEvidence.band(forDurationDifferenceSeconds: 3), .accepted)
        XCTAssertEqual(RecordingTimelineIntegrityEvidence.band(forDurationDifferenceSeconds: 3.1), .degradedWarning)
        XCTAssertEqual(RecordingTimelineIntegrityEvidence.band(forDurationDifferenceSeconds: 10.1), .failed)
    }

    func testRecordingTimelineEvidenceCarriesRouteCorrelation() {
        let evidence = RecordingTimelineIntegrityEvidence(
            routeSessionId: "route-session-019",
            autorepairAttemptIds: ["repair-1"],
            micDurationSeconds: 1_800,
            incomingDurationSeconds: 1_798,
            interruptionCategory: .autorepairCovered
        )

        XCTAssertEqual(evidence.routeSessionId, "route-session-019")
        XCTAssertEqual(evidence.autorepairAttemptIds, ["repair-1"])
        XCTAssertEqual(evidence.durationDifferenceSeconds, 2)
        XCTAssertEqual(evidence.alignmentBand, .accepted)
        XCTAssertEqual(evidence.interruptionCategory, .autorepairCovered)
    }
}
#endif
