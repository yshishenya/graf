import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

@MainActor
final class DesktopNotificationLinkPolicyTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 1_000)

    private func event(url: URL?, linkPresent: Bool = true) -> DesktopCalendarPromptEvent {
        DesktopCalendarPromptEvent(eventId: "synthetic-event", startsAt: now,
            endsAt: now.addingTimeInterval(3_600), title: "Синтетическая встреча", titleState: .available,
            meetingLinkPresent: linkPresent, openMeetingURL: url)
    }

    func testPrivateTitleIsHiddenByDefaultAndShownOnlyByPreference() throws {
        let meeting = event(url: URL(string: "https://meet.example.test/room"))
        let zone = try XCTUnwrap(TimeZone(secondsFromGMT: 0))
        var preferences = DesktopNotificationPreferences()
        XCTAssertEqual(DesktopNotificationPresenter.meetingCardContent(event: meeting, preferences: preferences, timeZone: zone),
            .meeting(title: "Встреча в календаре", startText: "Начало в 00:16", hasJoinLink: true))
        preferences.showTitles = true
        XCTAssertEqual(DesktopNotificationPresenter.meetingCardContent(event: meeting, preferences: preferences, timeZone: zone),
            .meeting(title: "Синтетическая встреча", startText: "Начало в 00:16", hasJoinLink: true))
    }

    func testUnsafeLinksAreNeitherOfferedNorResolvedForClick() throws {
        for value in ["http://example.test/room", "file:///tmp/synthetic", "javascript:alert(1)",
                      "https://localhost/room", "https://sub.localhost/room", "https://127.0.0.1/room",
                      "https://10.0.0.1/room", "https://172.16.0.1/room", "https://192.168.0.1/room",
                      "https://169.254.1.1/room", "https://[::1]/room", "https://[fc00::1]/room",
                      "https://[fe80::1]/room", "https://example.test/room#fragment",
                      "https://synthetic@example.test/room"] {
            let meeting = event(url: try XCTUnwrap(URL(string: value)))
            guard case let .meeting(_, _, hasJoinLink) = DesktopNotificationPresenter.meetingCardContent(event: meeting, preferences: .init()) else {
                return XCTFail("Expected calendar content")
            }
            XCTAssertFalse(hasJoinLink, value)
            XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: meeting, events: [meeting], now: now), value)
        }
    }

    func testNoJoinActionWithoutConfirmedLinkEvenIfPayloadContainsURL() {
        let meeting = event(url: URL(string: "https://meet.example.test/room"), linkPresent: false)
        guard case let .meeting(_, _, hasJoinLink) = DesktopNotificationPresenter.meetingCardContent(event: meeting, preferences: .init()) else {
            return XCTFail("Expected calendar content")
        }
        XCTAssertFalse(hasJoinLink)
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: meeting, events: [meeting], now: now))
    }
}
