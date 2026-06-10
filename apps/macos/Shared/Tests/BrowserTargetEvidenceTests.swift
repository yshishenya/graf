import Foundation
import TwoBrainRecAppCore
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

    func testBrowserTargetEvidenceTravelsThroughAudioEnvironmentState() {
        let evidence = BrowserTargetEvidence(
            target: "chrome",
            status: .passed,
            microphoneSelected: "2brain Rec Microphone",
            speakerSelected: "2brain Rec Speaker",
            localSpeechUsable: true,
            remoteAudioUsable: true,
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )
        let monitor = AudioEnvironmentMonitor()
        let (_, state) = monitor.refresh(with: AudioEnvironmentSnapshot(
            driverState: .installed,
            virtualMicState: .available,
            virtualSpeakerState: .available,
            microphonePermission: .granted,
            outputPermission: .granted,
            passthroughStatus: .healthy,
            bufferRisk: .healthy,
            browserTargetEvidence: [evidence]
        ))

        XCTAssertEqual(state.browserTargetEvidence, [evidence])
    }

    func testBrowserTargetEvidenceBundleIsMetadataOnly() throws {
        let evidence = BrowserTargetEvidence(
            target: "opera",
            status: .blocked,
            microphoneSelected: "2brain Rec Microphone",
            speakerSelected: "2brain Rec Speaker",
            localSpeechUsable: false,
            remoteAudioUsable: false,
            failureReason: "manual_validation_unavailable",
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )

        let bundle = try DiagnosticBundleService().buildBrowserTargetEvidenceBundle(evidence: [evidence])

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertNotNil(bundle.manifest["browserTargetEvidence"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
    }

    func testPassthroughBrowserEvidenceRequiresConcreteBlockedReason() {
        let evidence = PassthroughBrowserCallEvidence(
            targetName: "Yandex Telemost",
            targetVersion: "browser",
            selectedMicrophone: "2brain Rec Microphone",
            selectedSpeaker: "2brain Rec Speaker",
            localSpeechUsable: false,
            remoteAudioUsable: false,
            status: .notAccepted,
            failureReason: "manual_validation_unavailable",
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )

        XCTAssertEqual(evidence.status, .notAccepted)
        XCTAssertFalse(evidence.failureReason?.isEmpty ?? true)
    }

    func testPassthroughBrowserEvidenceTravelsThroughAudioEnvironmentState() {
        let evidence = PassthroughBrowserCallEvidence(
            targetName: "Chrome",
            targetVersion: "125",
            selectedMicrophone: "2brain Rec Microphone",
            selectedSpeaker: "2brain Rec Speaker",
            localSpeechUsable: true,
            remoteAudioUsable: true,
            status: .passed,
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )
        let monitor = AudioEnvironmentMonitor()
        let (_, state) = monitor.refresh(with: AudioEnvironmentSnapshot(
            driverState: .installed,
            virtualMicState: .available,
            virtualSpeakerState: .available,
            microphonePermission: .granted,
            outputPermission: .granted,
            passthroughStatus: .healthy,
            bufferRisk: .healthy,
            livePassthroughStatus: .active,
            passthroughBrowserEvidence: [evidence]
        ))

        XCTAssertEqual(state.livePassthroughStatus, .active)
        XCTAssertEqual(state.passthroughBrowserEvidence, [evidence])
    }
}
#endif
