import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioResponsiveStateTests: XCTestCase {
    func testShortVisibleLabelsFitCompactControls() {
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.stopButtonTitle.count, 12)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.activeState.count, 12)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.silentState.count, 12)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.microphoneTitle.count, 16)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.incomingTitle.count, 16)
    }

    func testWaitingAndBlockedCopyAvoidsOverSpecificDeviceInstructions() {
        let waiting = SystemAudioStatusLabels.waitingForRecordingAudio
        let noIncoming = SystemAudioStatusLabels.incomingDetail(recordingIsActive: true, incomingIsLive: false)

        XCTAssertFalse(waiting.localizedCaseInsensitiveContains("select"))
        XCTAssertFalse(noIncoming.localizedCaseInsensitiveContains("speaker device"))
        XCTAssertFalse(noIncoming.localizedCaseInsensitiveContains("driver"))
    }

    func testPendingRecordingStatusCopyPointsToRecordInsteadOfRunCheck() {
        XCTAssertEqual(SystemAudioStatusLabels.microphonePendingStatus, "Проверим доступ при старте записи")
        XCTAssertEqual(SystemAudioStatusLabels.speakerPendingStatus, "Проверим звук при старте записи")
        XCTAssertFalse(SystemAudioStatusLabels.microphonePendingStatus.localizedCaseInsensitiveContains("not checked"))
        XCTAssertFalse(SystemAudioStatusLabels.speakerPendingStatus.localizedCaseInsensitiveContains("not checked"))
        XCTAssertFalse(SystemAudioStatusLabels.speakerPendingStatus.localizedCaseInsensitiveContains("driver"))
    }
}
#endif
