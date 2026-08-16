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

    func testKnownRecordingSourceIsReadFromCurrentSessionEvidence() {
        let session = makeSession(
            state: .active,
            indicator: .active,
            stopAvailable: true,
            triggerEvidence: ["sourceDisplayName": "Zoom"]
        )

        XCTAssertEqual(CaptureStatusItem.sourceDisplayName(for: session), "Zoom")
        XCTAssertEqual(
            CaptureStatusItem.sourceAccessibilityLabel(for: session),
            "Источник: Zoom"
        )
    }

    func testKnownRecordingSourceRemainsVisibleAcrossActiveLifecycleStates() {
        for state in [
            CaptureSessionState.detecting,
            .ready,
            .starting,
            .active,
            .paused,
            .degraded,
            .stopping
        ] {
            let session = makeSession(
                state: state,
                indicator: .active,
                stopAvailable: state != .detecting && state != .ready,
                triggerEvidence: ["sourceDisplayName": "Telemost"]
            )

            XCTAssertEqual(CaptureStatusItem.sourceDisplayName(for: session), "Telemost")
        }
    }

    func testManualAndUnknownRecordingSourcesUseTruthfulFallbacks() {
        let manual = makeSession(
            state: .active,
            indicator: .active,
            stopAvailable: true,
            triggerEvidence: ["sourceDisplayName": "Current display/system audio"]
        )
        let blank = makeSession(
            state: .active,
            indicator: .active,
            stopAvailable: true,
            triggerEvidence: ["sourceDisplayName": "  "]
        )
        let missing = makeSession(state: .active, indicator: .active, stopAvailable: true)
        let stopped = makeSession(
            state: .stopped,
            indicator: .hidden,
            stopAvailable: false,
            triggerEvidence: ["sourceDisplayName": "Zoom"]
        )

        XCTAssertEqual(
            CaptureStatusItem.sourceDisplayName(for: manual),
            SystemAudioStatusLabels.recordingSourceSystemAudio
        )
        XCTAssertEqual(
            CaptureStatusItem.sourceDisplayName(for: blank),
            SystemAudioStatusLabels.recordingSourceUnknown
        )
        XCTAssertEqual(
            CaptureStatusItem.sourceDisplayName(for: missing),
            SystemAudioStatusLabels.recordingSourceUnknown
        )
        XCTAssertNil(CaptureStatusItem.sourceDisplayName(for: stopped))
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

    func testDegradedSourceKeepsTruthfulStatusRecoveryAndStop() {
        var session = makeSession(state: .degraded, indicator: .degraded, stopAvailable: true)
        session.triggerEvidence["degradedSource"] = "microphone"
        session.triggerEvidence["recoveryAction"] = "Подключите микрофон или остановите запись."

        XCTAssertEqual(CaptureStatusItem.statusLabel(for: session), "Запись с ограничением")
        XCTAssertEqual(
            CaptureControlView.degradedSourceRecovery(for: session),
            "Микрофон недоступен. Подключите микрофон или остановите запись."
        )
        XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: session, stopDisabled: false))
    }

    func testDegradedSessionWithoutSourceEvidenceStillOffersBoundedRecovery() {
        let session = makeSession(state: .degraded, indicator: .degraded, stopAvailable: true)

        XCTAssertEqual(
            CaptureControlView.degradedSourceRecovery(for: session),
            "Один из источников недоступен. Остановите запись и проверьте источник."
        )
        XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: session, stopDisabled: false))
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
        stopAvailable: Bool,
        triggerEvidence: [String: String] = [:]
    ) -> CaptureSession {
        CaptureSession(
            id: "indicator-session",
            mode: .audioRecording,
            state: state,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "policy",
            triggerEvidence: triggerEvidence,
            visibleIndicatorState: indicator,
            stopActionAvailable: stopAvailable,
            bufferSummaryId: nil,
            startedAt: nil,
            stoppedAt: nil
        )
    }
}
#endif
