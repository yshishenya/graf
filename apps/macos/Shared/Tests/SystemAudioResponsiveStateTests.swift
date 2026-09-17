import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioResponsiveStateTests: XCTestCase {
    func testShortVisibleLabelsFitCompactControls() {
        XCTAssertEqual(SystemAudioStatusLabels.stopButtonTitle, SystemAudioStatusLabels.stopButtonAccessibilityLabel)
        XCTAssertEqual(SystemAudioStatusLabels.stopButtonTitle, "Остановить запись")
        let statusSurface = try? String(
            contentsOf: URL(fileURLWithPath: #filePath)
                .deletingLastPathComponent()
                .appendingPathComponent("../../RecApp/Sources/Capture/CaptureStatusItem.swift")
                .standardizedFileURL,
            encoding: .utf8
        )
        XCTAssertTrue(statusSurface?.contains("Label(SystemAudioStatusLabels.stopButtonTitle, systemImage: \"stop.fill\")") == true)
        XCTAssertTrue(statusSurface?.contains(".fixedSize(horizontal: false, vertical: true)") == true)
        XCTAssertTrue(statusSurface?.contains(".frame(maxWidth: .infinity, minHeight: DesktopMeetingShellChrome.controlHeight)") == true)
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
