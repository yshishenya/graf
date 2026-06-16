import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioAccessibilityTests: XCTestCase {
    func testRecordingControlsExposeStableAccessibilityIdentifiers() {
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.captureControls, "systemAudio.capture.controls")
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.recordButton, "systemAudio.record.button")
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.stopButton, "systemAudio.stop.button")
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.microphoneMeter, "systemAudio.meter.microphone")
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.incomingMeter, "systemAudio.meter.incoming")
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.blockerBanner, "systemAudio.blocker.banner")
    }

    func testPrimaryControlLabelsAreExplicitForAssistiveTech() {
        XCTAssertEqual(SystemAudioStatusLabels.captureRegion, "Управление записью")
        XCTAssertEqual(SystemAudioStatusLabels.recordButtonAccessibilityLabel, "Начать запись системного звука")
        XCTAssertEqual(SystemAudioStatusLabels.stopButtonAccessibilityLabel, "Остановить запись")
        XCTAssertEqual(
            SystemAudioStatusLabels.meterAccessibilityLabel(
                title: SystemAudioStatusLabels.incomingTitle,
                detail: "Звук встречи поступает в запись."
            ),
            "Встреча: Звук встречи поступает в запись."
        )
    }
}
#endif
