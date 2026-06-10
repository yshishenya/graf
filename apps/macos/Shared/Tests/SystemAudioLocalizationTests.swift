import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioLocalizationTests: XCTestCase {
    func testStateLabelsComeFromSharedLabelModel() {
        XCTAssertEqual(SystemAudioStatusLabels.recordingIdle, "Recording idle")
        XCTAssertEqual(SystemAudioStatusLabels.recordButtonTitle, "Record System Audio")
        XCTAssertEqual(SystemAudioStatusLabels.stopButtonTitle, "Stop")
        XCTAssertEqual(SystemAudioStatusLabels.activeState, "Active")
        XCTAssertEqual(SystemAudioStatusLabels.silentState, "Silent")
        XCTAssertEqual(
            SystemAudioStatusLabels.localAudioRouteActiveNotRecording,
            "Local audio route is active; recording still starts only from Record"
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
            "System audio is reaching the recorder."
        )
        XCTAssertEqual(SystemAudioStatusLabels.meterState(isLive: true), SystemAudioStatusLabels.activeState)
        XCTAssertEqual(SystemAudioStatusLabels.meterState(isLive: false), SystemAudioStatusLabels.silentState)
    }

    func testRecordingMeterFreshnessAllowsBatchedSystemAudioDelivery() {
        XCTAssertGreaterThanOrEqual(SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds, 1.5)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds, 2.0)
    }
}
#endif
