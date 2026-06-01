import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class CaptureControlTests: XCTestCase {
    func testActiveCaptureKeepsVisibleIndicatorAndStopAvailable() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 10) },
            idFactory: { "capture-test-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        let active = try controller.markCapturing()

        XCTAssertEqual(active.visibleIndicatorState, .active)
        XCTAssertTrue(active.stopActionAvailable)
    }

    func testTrackEvidenceUsesCurrentSession() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 10) },
            idFactory: { "track-test-id" },
            policySnapshotProvider: { "policy-test" }
        )

        let session = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        let track = try controller.makeTrackEvidence(role: .localMic)

        XCTAssertEqual(track.sessionId, session.id)
        XCTAssertEqual(track.role, .localMic)
        XCTAssertEqual(track.state, .capturing)
    }
}
#endif
