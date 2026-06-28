import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioLocalizationTests: XCTestCase {
    func testStateLabelsComeFromSharedLabelModel() {
        XCTAssertEqual(SystemAudioStatusLabels.recordingIdle, "Запись не идет")
        XCTAssertEqual(SystemAudioStatusLabels.recordButtonTitle, "Начать запись")
        XCTAssertEqual(SystemAudioStatusLabels.stopButtonTitle, "Остановить")
        XCTAssertEqual(SystemAudioStatusLabels.pauseButtonTitle, "Пауза")
        XCTAssertEqual(SystemAudioStatusLabels.resumeButtonTitle, "Продолжить")
        XCTAssertEqual(SystemAudioStatusLabels.activeState, "Есть звук")
        XCTAssertEqual(SystemAudioStatusLabels.silentState, "Тихо")
        XCTAssertEqual(
            SystemAudioStatusLabels.localAudioRouteActiveNotRecording,
            "Локальный аудиомаршрут активен; запись начинается только вручную"
        )
    }

    func testLiveSummaryLabelsCoverAllMeterStatesWithoutDriverLanguage() {
        let summaries = [
            SystemAudioStatusLabels.liveSummary(routeIsActive: false, microphoneIsLive: false, incomingIsLive: false),
            SystemAudioStatusLabels.liveSummary(routeIsActive: true, microphoneIsLive: true, incomingIsLive: true),
            SystemAudioStatusLabels.liveSummary(routeIsActive: true, microphoneIsLive: true, incomingIsLive: false),
            SystemAudioStatusLabels.liveSummary(routeIsActive: true, microphoneIsLive: false, incomingIsLive: true),
            SystemAudioStatusLabels.liveSummary(routeIsActive: true, microphoneIsLive: false, incomingIsLive: false)
        ]

        XCTAssertEqual(Set(summaries).count, 5)
        for summary in summaries {
            XCTAssertFalse(summary.localizedCaseInsensitiveContains("driver"))
            XCTAssertFalse(summary.localizedCaseInsensitiveContains("virtual"))
            XCTAssertFalse(summary.localizedCaseInsensitiveContains("run check"))
        }
        XCTAssertFalse(SystemAudioStatusLabels.localAudioRouteActiveNotRecording.localizedCaseInsensitiveContains("passthrough"))
        XCTAssertFalse(SystemAudioStatusLabels.localAudioRouteActiveNotRecording.localizedCaseInsensitiveContains("virtual"))
    }

    func testMeterDetailLabelsAreStableForPermissionAndRecordingStates() {
        XCTAssertEqual(
            SystemAudioStatusLabels.microphoneDetail(routeIsActive: false, microphoneIsLive: false),
            SystemAudioStatusLabels.waitingForRecordingAudio
        )
        XCTAssertEqual(
            SystemAudioStatusLabels.incomingDetail(routeIsActive: true, incomingIsLive: true),
            "Звук встречи поступает в запись."
        )
        XCTAssertEqual(SystemAudioStatusLabels.meterState(isLive: true), SystemAudioStatusLabels.activeState)
        XCTAssertEqual(SystemAudioStatusLabels.meterState(isLive: false), SystemAudioStatusLabels.silentState)
    }

    func testRecordingMeterFreshnessAllowsBatchedSystemAudioDelivery() {
        XCTAssertGreaterThanOrEqual(SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds, 1.5)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds, 2.0)
    }

    func testMuteTruthLimitationCopyDoesNotClaimMeetingAppMuteSupport() {
        XCTAssertEqual(
            SystemAudioStatusLabels.meetingMuteTruthLimitationCopy,
            "GRAF не может проверить mute в этой встрече. Чтобы локальная речь не попала в запись, используйте Паузу или Остановить в GRAF."
        )
        XCTAssertTrue(SystemAudioStatusLabels.meetingMuteTruthLimitationCopy.contains("Паузу или Остановить"))
        XCTAssertTrue(SystemAudioStatusLabels.meetingMuteTruthLimitationCopy.contains("не может проверить"))
        XCTAssertFalse(SystemAudioStatusLabels.meetingMuteTruthLimitationCopy.localizedCaseInsensitiveContains("mute-respecting"))
        XCTAssertFalse(SystemAudioStatusLabels.meetingMuteTruthLimitationCopy.localizedCaseInsensitiveContains("guarantee"))
    }
}
#endif
