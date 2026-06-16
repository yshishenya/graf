import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class CaptureIndicatorTests: XCTestCase {
    func testActiveRecordingLabelIsExplicitAndAccessible() {
        let session = makeSession(state: .active, indicator: .active, stopAvailable: true)

        XCTAssertEqual(
            CaptureStatusItem.statusLabel(for: session),
            "Recording active"
        )
        XCTAssertEqual(
            CaptureStatusItem.accessibilityLabel(for: session),
            "Recording active. Stop recording is available."
        )
    }

    func testNonRecordingReadyLabelDoesNotImplyRecording() {
        let session = makeSession(state: .ready, indicator: .ready, stopAvailable: false)

        XCTAssertEqual(
            CaptureStatusItem.statusLabel(for: session),
            "Ready to record"
        )
        XCTAssertEqual(
            CaptureStatusItem.accessibilityLabel(for: session),
            "Ready to record. Recording is not active."
        )
    }

    func testStoppedSessionAllowsRecordButtonToReturn() {
        let session = makeSession(state: .stopped, indicator: .hidden, stopAvailable: false)

        XCTAssertFalse(CaptureStatusItem.showsStopButton(for: session))
        XCTAssertTrue(CaptureControlView.shouldShowRecordButton(for: session))
    }

    func testActiveSessionShowsStopInsteadOfRecord() {
        let session = makeSession(state: .active, indicator: .active, stopAvailable: true)

        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: session))
        XCTAssertFalse(CaptureControlView.shouldShowRecordButton(for: session))
    }

    func testRecordButtonCanBeDisabledWhileStartIsInFlight() {
        XCTAssertTrue(CaptureControlView.shouldShowRecordButton(for: nil))
        XCTAssertTrue(CaptureControlView.shouldEnableRecordButton(for: nil, recordDisabled: false))
        XCTAssertFalse(CaptureControlView.shouldEnableRecordButton(for: nil, recordDisabled: true))
    }

    func testStopButtonCanBeDisabledWhileStopIsInFlight() {
        let session = makeSession(state: .active, indicator: .active, stopAvailable: true)

        XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: session, stopDisabled: false))
        XCTAssertFalse(CaptureStatusItem.shouldEnableStopButton(for: session, stopDisabled: true))
    }

    private func makeSession(
        state: CaptureSessionState,
        indicator: VisibleIndicatorState,
        stopAvailable: Bool
    ) -> CaptureSession {
        CaptureSession(
            id: "indicator-session",
            mode: .audioRecording,
            state: state,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "policy",
            triggerEvidence: [:],
            visibleIndicatorState: indicator,
            stopActionAvailable: stopAvailable,
            bufferSummaryId: nil,
            startedAt: nil,
            stoppedAt: nil
        )
    }
}
#endif
