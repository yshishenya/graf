import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioResponsiveStateTests: XCTestCase {
    func testLongRecordingLocationAccessibilityKeepsFullPath() {
        let path = "/Users/example/Library/Application Support/2brain Rec/Recordings/2026-06-08/a-very-long-meeting-session-directory-name/manifest.json"

        let label = SystemAudioStatusLabels.localRecordingLocationAccessibilityLabel(path)

        XCTAssertTrue(label.hasPrefix("Local recording location:"))
        XCTAssertTrue(label.contains("a-very-long-meeting-session-directory-name"))
        XCTAssertTrue(label.contains("manifest.json"))
    }

    func testShortVisibleLabelsFitCompactControls() {
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.stopButtonTitle.count, 12)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.activeState.count, 12)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.silentState.count, 12)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.microphoneTitle.count, 16)
        XCTAssertLessThanOrEqual(SystemAudioStatusLabels.incomingTitle.count, 16)
    }

    func testWaitingAndBlockedCopyAvoidsOverSpecificDeviceInstructions() {
        let waiting = SystemAudioStatusLabels.waitingForRecordingAudio
        let noIncoming = SystemAudioStatusLabels.incomingDetail(routeIsActive: true, incomingIsLive: false)

        XCTAssertFalse(waiting.localizedCaseInsensitiveContains("select"))
        XCTAssertFalse(noIncoming.localizedCaseInsensitiveContains("speaker device"))
        XCTAssertFalse(noIncoming.localizedCaseInsensitiveContains("driver"))
    }
}
#endif
