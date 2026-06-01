import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class ShortSmokeEvidenceTests: XCTestCase {
    func testShortSmokeEvidenceCannotRepresentRecordingAcceptance() {
        let evidence = ShortSmokeEvidence(
            targetApp: "Chrome",
            selectedInput: "2brain Rec Microphone",
            selectedOutput: "2brain Rec Speaker",
            localSpeechObserved: true,
            remoteAudioObserved: true,
            loopbackObserved: false,
            recordingStarted: false,
            result: .passed
        )

        XCTAssertEqual(evidence.result, .passed)
        XCTAssertFalse(evidence.recordingStarted)
        XCTAssertEqual(evidence.targetApp, "Chrome")
    }

    func testBlockedShortSmokeEvidenceCanRepresentUnknownAudioObservation() {
        let evidence = ShortSmokeEvidence(
            targetApp: "Opera",
            selectedInput: "2brain Rec Microphone",
            selectedOutput: "2brain Rec Speaker",
            localSpeechObserved: nil,
            remoteAudioObserved: nil,
            loopbackObserved: nil,
            recordingStarted: false,
            result: .blocked
        )

        XCTAssertNil(evidence.localSpeechObserved)
        XCTAssertNil(evidence.remoteAudioObserved)
        XCTAssertNil(evidence.loopbackObserved)
        XCTAssertFalse(evidence.recordingStarted)
        XCTAssertEqual(evidence.result, .blocked)
    }
}
#endif
