import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class BrowserTargetEvidenceTests: XCTestCase {
    func testBrowserMeetingMetadataClassifiesJoinedTelemostWithCalendarIntent() throws {
        let evidence = browserMeetingEvidence(
            serviceFamily: "yandex_telemost",
            pageState: .joinedMeeting,
            calendarOrJoinIntentPresent: true
        )
        let evaluation = BrowserMeetingServiceMatcher().evaluate(
            evidence: evidence,
            registry: Self.browserRegistry()
        )

        XCTAssertEqual(
            evaluation.kind,
            .safeJoinedTarget(targetID: "yandex_telemost_web", mode: .promptEnabled)
        )
        XCTAssertEqual(evaluation.serviceFamily, "yandex_telemost")
        XCTAssertEqual(evaluation.signals, [.browserMetadata, .calendarOrJoinIntent])

        let encoded = try JSONEncoder().encode(evidence)
        let payload = String(decoding: encoded, as: UTF8.self)
        XCTAssertFalse(payload.contains("https://"))
        XCTAssertFalse(payload.localizedCaseInsensitiveContains("passcode"))
    }

    func testBrowserServiceLandingAndUtilityPagesRemainManualOnly() {
        let closedStates: [BrowserMeetingPageState] = [
            .landingPage,
            .newMeeting,
            .joinPage,
            .settings,
            .deviceTest,
            .mediaPlayback,
            .voiceSearch
        ]

        for state in closedStates {
            let evaluation = BrowserMeetingServiceMatcher().evaluate(
                evidence: browserMeetingEvidence(
                    serviceFamily: "google_meet",
                    pageState: state,
                    calendarOrJoinIntentPresent: true
                ),
                registry: Self.browserRegistry()
            )

            XCTAssertEqual(
                evaluation.kind,
                .manualOnly(targetID: "google_meet_web", reason: "unsupported_browser_metadata"),
                "Expected \(state.rawValue) to fail closed"
            )
        }
    }

    func testBrowserMetadataRequiresCalendarOrJoinIntentForPromptQualityEvidence() {
        let evaluation = BrowserMeetingServiceMatcher().evaluate(
            evidence: browserMeetingEvidence(
                serviceFamily: "google_meet",
                pageState: .joinedMeeting,
                calendarOrJoinIntentPresent: false
            ),
            registry: Self.browserRegistry()
        )

        XCTAssertEqual(
            evaluation.kind,
            .manualOnly(targetID: "google_meet_web", reason: "calendar_or_join_intent_missing")
        )
        XCTAssertEqual(evaluation.signals, [.browserMetadata])
    }

    func testUnavailableBrowserMetadataFailsClosedWithoutTargetIdentity() {
        let evidence = BrowserTargetEvidence(
            target: "Chrome",
            status: .passed,
            microphoneSelected: "browser-default",
            speakerSelected: "system-default",
            localSpeechUsable: true,
            remoteAudioUsable: true,
            metadataAvailable: false,
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )

        let evaluation = BrowserMeetingServiceMatcher().evaluate(
            evidence: evidence,
            registry: Self.browserRegistry()
        )

        XCTAssertEqual(
            evaluation.kind,
            .manualOnly(targetID: nil, reason: "browser_metadata_unavailable")
        )
        XCTAssertTrue(evaluation.signals.isEmpty)
    }

    func testBrowserTargetEvidenceEncodesMetadataOnlyContract() throws {
        let evidence = BrowserTargetEvidence(
            target: "chrome",
            status: .passed,
            microphoneSelected: "GRAF Microphone",
            speakerSelected: "GRAF Speaker",
            localSpeechUsable: true,
            remoteAudioUsable: true,
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )

        let encoded = try JSONEncoder().encode(evidence)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["target"] as? String, "chrome")
        XCTAssertEqual(object["status"] as? String, "passed")
        XCTAssertEqual(object["microphoneSelected"] as? String, "GRAF Microphone")
        XCTAssertNil(object["rawAudio"])
        XCTAssertNil(object["transcriptText"])
        XCTAssertNil(object["meetingContent"])
    }

    func testBlockedBrowserTargetRequiresFailureReasonInPolicy() {
        let evidence = BrowserTargetEvidence(
            target: "yandex_telemost_browser",
            status: .blocked,
            microphoneSelected: "GRAF Microphone",
            speakerSelected: "GRAF Speaker",
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
            microphoneSelected: "GRAF Microphone",
            speakerSelected: "GRAF Speaker",
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
            microphoneSelected: "GRAF Microphone",
            speakerSelected: "GRAF Speaker",
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
            selectedMicrophone: "GRAF Microphone",
            selectedSpeaker: "GRAF Speaker",
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
            selectedMicrophone: "GRAF Microphone",
            selectedSpeaker: "GRAF Speaker",
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

    private func browserMeetingEvidence(
        serviceFamily: String,
        pageState: BrowserMeetingPageState,
        calendarOrJoinIntentPresent: Bool
    ) -> BrowserTargetEvidence {
        BrowserTargetEvidence(
            target: "Chrome",
            status: .passed,
            microphoneSelected: "browser-default",
            speakerSelected: "system-default",
            localSpeechUsable: true,
            remoteAudioUsable: true,
            serviceFamily: serviceFamily,
            hostCategory: "first_party",
            patternClass: pageState == .joinedMeeting ? "meeting_room" : pageState.rawValue,
            pageState: pageState,
            metadataAvailable: true,
            calendarOrJoinIntentPresent: calendarOrJoinIntentPresent,
            checkedAt: Date(timeIntervalSince1970: 1_779_887_120)
        )
    }

    private static func browserRegistry() -> MeetingTargetRegistryDocument {
        MeetingTargetRegistryDocument(
            registryVersion: "browser-test",
            generatedAt: Date(timeIntervalSince1970: 1_779_887_120),
            targets: [
                MeetingTargetRegistryTarget(
                    id: "yandex_telemost_web",
                    displayName: "Yandex Telemost web",
                    market: .russia,
                    platform: .browser,
                    targetFamily: .browserMeeting,
                    mode: .promptEnabled,
                    evidence: .seed,
                    requiredSignals: [.browserMetadata, .calendarOrJoinIntent],
                    browserServicePatterns: [
                        MeetingTargetBrowserServicePattern(
                            serviceFamily: "yandex_telemost",
                            hostCategory: "first_party",
                            patternClass: "meeting_room"
                        )
                    ]
                ),
                MeetingTargetRegistryTarget(
                    id: "google_meet_web",
                    displayName: "Google Meet web",
                    market: .global,
                    platform: .browser,
                    targetFamily: .browserMeeting,
                    mode: .promptEnabled,
                    evidence: .seed,
                    requiredSignals: [.browserMetadata, .calendarOrJoinIntent],
                    browserServicePatterns: [
                        MeetingTargetBrowserServicePattern(
                            serviceFamily: "google_meet",
                            hostCategory: "first_party",
                            patternClass: "meeting_room"
                        )
                    ]
                )
            ]
        )
    }
}
#endif
