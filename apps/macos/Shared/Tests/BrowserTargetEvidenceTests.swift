import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class BrowserTargetEvidenceTests: XCTestCase {
    func testBrowserTargetEvidenceEncodesMetadataOnlyContract() throws {
        let evidence = BrowserTargetEvidence(
            target: "chrome",
            status: .passed,
            microphoneSelected: "2brain Rec Microphone",
            speakerSelected: "2brain Rec Speaker",
            localSpeechUsable: true,
            remoteAudioUsable: true,
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )

        let encoded = try JSONEncoder().encode(evidence)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["target"] as? String, "chrome")
        XCTAssertEqual(object["status"] as? String, "passed")
        XCTAssertEqual(object["microphoneSelected"] as? String, "2brain Rec Microphone")
        XCTAssertNil(object["rawAudio"])
        XCTAssertNil(object["transcriptText"])
        XCTAssertNil(object["meetingContent"])
    }

    func testBlockedBrowserTargetRequiresFailureReasonInPolicy() {
        let evidence = BrowserTargetEvidence(
            target: "yandex_telemost_browser",
            status: .blocked,
            microphoneSelected: "2brain Rec Microphone",
            speakerSelected: "2brain Rec Speaker",
            localSpeechUsable: false,
            remoteAudioUsable: false,
            failureReason: "target_does_not_expose_device_selection",
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )

        XCTAssertEqual(evidence.status, .blocked)
        XCTAssertFalse(evidence.failureReason?.isEmpty ?? true)
    }
}
#endif
