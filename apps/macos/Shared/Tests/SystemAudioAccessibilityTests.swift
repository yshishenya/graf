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
        XCTAssertEqual(SystemAudioStatusLabels.captureRegion, "System audio recording controls")
        XCTAssertEqual(SystemAudioStatusLabels.recordButtonAccessibilityLabel, "Start system audio recording")
        XCTAssertEqual(SystemAudioStatusLabels.stopButtonAccessibilityLabel, "Stop recording")
        XCTAssertEqual(
            SystemAudioStatusLabels.meterAccessibilityLabel(
                title: SystemAudioStatusLabels.incomingTitle,
                detail: "System audio is reaching the recorder."
            ),
            "Incoming: System audio is reaching the recorder."
        )
    }
}
#endif
