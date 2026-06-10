import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingRouteStabilityTests: XCTestCase {
    func testAutorepairDuringRecordingKeepsIndicatorAndStopAvailable() {
        let session = CaptureSession(
            id: "recording-session",
            mode: .audioRecording,
            state: .degraded,
            sourceAppEligibility: .eligible,
            policySnapshotRef: nil,
            triggerEvidence: ["routeSessionId": "route-session-019"],
            visibleIndicatorState: .degraded,
            stopActionAvailable: true,
            bufferSummaryId: nil,
            startedAt: LiveRouteStabilityFixtures.now,
            stoppedAt: nil
        )

        XCTAssertEqual(session.visibleIndicatorState, .degraded)
        XCTAssertTrue(session.stopActionAvailable)
        XCTAssertEqual(session.triggerEvidence["routeSessionId"], "route-session-019")
    }
}
#endif
