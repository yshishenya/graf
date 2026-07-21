import Foundation
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

    func testBrowserMetadataRequiresCalendarOrJoinIntent() {
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

    func testNonChromiumBrowserIsManualOnlyWithoutSafeMetadataAdapter() {
        let evidence = BrowserTargetEvidence(
            target: "Firefox",
            metadataAvailable: false,
            failureReason: "non_chromium_metadata_adapter_unavailable",
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
    }

    func testResearchedButUnimplementedBrowserProviderIsNotRuntimeSupport() {
        let evaluation = BrowserMeetingServiceMatcher().evaluate(
            evidence: browserMeetingEvidence(
                serviceFamily: "whereby",
                pageState: .joinedMeeting,
                calendarOrJoinIntentPresent: true
            ),
            registry: Self.browserRegistry()
        )

        XCTAssertEqual(
            evaluation.kind,
            .manualOnly(targetID: nil, reason: "unsupported_browser_service")
        )
        XCTAssertEqual(evaluation.serviceFamily, "whereby")
    }

    func testBrowserTargetEvidenceEncodesOnlyMetadata() throws {
        let evidence = browserMeetingEvidence(
            serviceFamily: "google_meet",
            pageState: .joinedMeeting,
            calendarOrJoinIntentPresent: true
        )

        let encoded = try JSONEncoder().encode(evidence)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])

        XCTAssertEqual(object["target"] as? String, "Chrome")
        XCTAssertEqual(object["serviceFamily"] as? String, "google_meet")
        XCTAssertEqual(object["pageState"] as? String, "joined_meeting")
        XCTAssertNil(object["rawAudio"])
        XCTAssertNil(object["transcriptText"])
        XCTAssertNil(object["meetingContent"])
    }

    private func browserMeetingEvidence(
        serviceFamily: String,
        pageState: BrowserMeetingPageState,
        calendarOrJoinIntentPresent: Bool
    ) -> BrowserTargetEvidence {
        BrowserTargetEvidence(
            target: "Chrome",
            browserBundleID: "com.google.Chrome",
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
