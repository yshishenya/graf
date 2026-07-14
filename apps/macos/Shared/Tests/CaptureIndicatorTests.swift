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
            "Идёт запись"
        )
        XCTAssertEqual(
            CaptureStatusItem.accessibilityLabel(for: session),
            "Идёт запись. Кнопка остановки доступна."
        )
    }

    func testNonRecordingReadyLabelDoesNotImplyRecording() {
        let session = makeSession(state: .ready, indicator: .ready, stopAvailable: false)

        XCTAssertEqual(
            CaptureStatusItem.statusLabel(for: session),
            "Готово к записи"
        )
        XCTAssertEqual(
            CaptureStatusItem.accessibilityLabel(for: session),
            "Готово к записи. Активной записи нет."
        )
    }

    func testStoppedSessionAllowsRecordButtonToReturn() {
        let session = makeSession(state: .stopped, indicator: .hidden, stopAvailable: false)

        XCTAssertEqual(CaptureStatusItem.statusLabel(for: session), "Сохранено на Mac")
        XCTAssertFalse(CaptureStatusItem.showsStopButton(for: session))
        XCTAssertTrue(CaptureControlView.shouldShowRecordButton(for: session))
    }

    func testActiveSessionShowsStopInsteadOfRecord() {
        let session = makeSession(state: .active, indicator: .active, stopAvailable: true)

        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: session))
        XCTAssertFalse(CaptureControlView.shouldShowRecordButton(for: session))
    }

    func testPausedRecordingKeepsVisibleIndicatorAndStopAvailable() {
        let session = makeSession(state: .paused, indicator: .paused, stopAvailable: true)

        XCTAssertEqual(CaptureStatusItem.statusLabel(for: session), "Запись на паузе")
        XCTAssertEqual(session.visibleIndicatorState, .paused)
        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: session))
        XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: session, stopDisabled: false))
        XCTAssertTrue(CaptureStatusItem.showsResumeButton(for: session))
        XCTAssertFalse(CaptureStatusItem.showsPauseButton(for: session))
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
