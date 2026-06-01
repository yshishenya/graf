import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class CaptureSessionSafetyTests: XCTestCase {
    func testStartingRecordingRequiresVisibleStop() {
        let session = makeSession(
            state: .starting,
            visibleIndicatorState: .hidden,
            stopActionAvailable: true
        )

        XCTAssertFalse(CaptureSessionSafetyValidator.validate(session))
    }

    func testActiveRecordingRejectsErrorIndicator() {
        let session = makeSession(
            state: .active,
            visibleIndicatorState: .error,
            stopActionAvailable: true
        )

        XCTAssertFalse(CaptureSessionSafetyValidator.validate(session))
    }

    func testStoppingRecordingRequiresStopActionUntilClosed() {
        let session = makeSession(
            state: .stopping,
            visibleIndicatorState: .degraded,
            stopActionAvailable: false
        )

        XCTAssertFalse(CaptureSessionSafetyValidator.validate(session))
    }

    func testActiveRecordingWithIndicatorAndStopIsValid() {
        let session = makeSession(
            state: .active,
            visibleIndicatorState: .active,
            stopActionAvailable: true
        )

        XCTAssertTrue(CaptureSessionSafetyValidator.validate(session))
    }

    func testStoppedRecordingMayHideIndicator() {
        let session = makeSession(
            state: .stopped,
            visibleIndicatorState: .hidden,
            stopActionAvailable: false
        )

        XCTAssertTrue(CaptureSessionSafetyValidator.validate(session))
    }

    private func makeSession(
        state: CaptureSessionState,
        visibleIndicatorState: VisibleIndicatorState,
        stopActionAvailable: Bool
    ) -> CaptureSession {
        CaptureSession(
            id: "safety-session",
            mode: .audioRecording,
            state: state,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "policy",
            triggerEvidence: [:],
            visibleIndicatorState: visibleIndicatorState,
            stopActionAvailable: stopActionAvailable,
            bufferSummaryId: nil,
            startedAt: nil,
            stoppedAt: nil
        )
    }
}
#endif
