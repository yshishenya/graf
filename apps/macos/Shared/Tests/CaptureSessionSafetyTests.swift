import Foundation
import TwoBrainRecAppCore
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

    func testAppOwnedMicrophoneSampleSourceStopIsIdempotentBeforeStart() {
        let source = AppOwnedMicrophoneSampleSource()
        let scratch = UnsafeMutablePointer<Float>.allocate(capacity: 8)
        defer { scratch.deallocate() }

        source.stop()
        source.stop()

        XCTAssertEqual(source.readSamples(into: scratch, capacity: 8), 0)
    }

    func testAppleCandidateFailureCannotHideActiveCaptureOrRemoveStop() {
        let hiddenIndicator = makeSession(
            state: .active,
            visibleIndicatorState: .hidden,
            stopActionAvailable: true
        )
        let missingStop = makeSession(
            state: .active,
            visibleIndicatorState: .degraded,
            stopActionAvailable: false
        )
        let visibleStop = makeSession(
            state: .active,
            visibleIndicatorState: .degraded,
            stopActionAvailable: true
        )

        XCTAssertFalse(CaptureSessionSafetyValidator.validate(hiddenIndicator))
        XCTAssertFalse(CaptureSessionSafetyValidator.validate(missingStop))
        XCTAssertTrue(CaptureSessionSafetyValidator.validate(visibleStop))
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
