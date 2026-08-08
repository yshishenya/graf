import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class DesktopCalendarReminderTests: XCTestCase {
    func testMeetingDetectionJoinIntentHintUsesServiceFamilyWithoutRawURL() throws {
        let event = makeEvent(
            startsAt: date(120),
            endsAt: date(300),
            title: "Private browser call",
            titleState: .privateRedacted,
            meetingLinkPresent: true,
            joinPromptDueAt: date(60),
            openMeetingURL: try XCTUnwrap(URL(string: "https://telemost.yandex.ru/j/browser-room"))
        )

        let hint = try XCTUnwrap(
            DesktopCalendarReminderService.meetingDetectionJoinIntentHint(
                from: [event],
                now: date(60),
                isRecordingActive: false
            )
        )

        XCTAssertEqual(hint.serviceFamily, "yandex_telemost")
        XCTAssertEqual(hint.source, .calendarJoinPrompt)
        XCTAssertEqual(hint.matchingEventCount, 1)
        XCTAssertFalse(hint.isAmbiguous)
    }

    func testMeetingDetectionJoinIntentHintFailsClosedForOverlap() throws {
        let firstURL = try XCTUnwrap(URL(string: "https://telemost.yandex.ru/j/first"))
        let secondURL = try XCTUnwrap(URL(string: "https://meet.google.com/abc-defg-hij"))
        let events = [
            makeEvent(
                eventId: "first",
                startsAt: date(120),
                endsAt: date(300),
                meetingLinkPresent: true,
                joinPromptDueAt: date(60),
                openMeetingURL: firstURL
            ),
            makeEvent(
                eventId: "second",
                startsAt: date(120),
                endsAt: date(300),
                meetingLinkPresent: true,
                joinPromptDueAt: date(60),
                openMeetingURL: secondURL
            )
        ]

        XCTAssertNil(
            DesktopCalendarReminderService.meetingDetectionJoinIntentHint(
                from: events,
                now: date(60),
                isRecordingActive: false
            )
        )
    }

    func testMeetingDetectionJoinIntentHintRequiresSafeKnownMeetingURL() throws {
        let unknownURL = try XCTUnwrap(URL(string: "https://example.test/standup"))
        let event = makeEvent(
            startsAt: date(120),
            endsAt: date(300),
            meetingLinkPresent: true,
            joinPromptDueAt: date(60),
            openMeetingURL: unknownURL
        )

        XCTAssertNil(
            DesktopCalendarReminderService.meetingDetectionJoinIntentHint(
                from: [event],
                now: date(60),
                isRecordingActive: false
            )
        )
    }

    func testMeetingDetectionRecordOverlapHintUsesCurrentSingleMeetingLinkOnly() throws {
        let event = makeEvent(
            startsAt: date(100),
            endsAt: date(300),
            meetingLinkPresent: true,
            recordPromptDueAt: date(100),
            openMeetingURL: try XCTUnwrap(URL(string: "https://meet.google.com/abc-defg-hij"))
        )

        let hint = try XCTUnwrap(
            DesktopCalendarReminderService.meetingDetectionJoinIntentHint(
                from: [event],
                now: date(160),
                isRecordingActive: false
            )
        )

        XCTAssertEqual(hint.serviceFamily, "google_meet")
        XCTAssertEqual(hint.source, .calendarRecordPrompt)
        XCTAssertEqual(hint.matchingEventCount, 1)
    }

    func testJoinPromptIsDueOneMinuteBeforeStart() throws {
        let event = makeEvent(
            startsAt: date(120),
            endsAt: date(300),
            title: "Product sync",
            titleState: .available,
            meetingLinkPresent: true,
            joinPromptDueAt: date(60),
            openMeetingURL: try XCTUnwrap(URL(string: "https://meet.example.test/room"))
        )

        XCTAssertNil(DesktopCalendarReminderService.activePrompt(from: [event], now: date(59), isRecordingActive: false))

        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: [event], now: date(60), isRecordingActive: false)
        )
        XCTAssertEqual(prompt.kind, .join)
        XCTAssertEqual(prompt.eventId, event.eventId)
        XCTAssertEqual(prompt.title, "Product sync")
        XCTAssertEqual(prompt.openMeetingURL?.absoluteString, "https://meet.example.test/room")
    }

    func testOverlappingJoinPromptsRequireChoice() throws {
        let firstURL = try XCTUnwrap(URL(string: "https://meet.example.test/first"))
        let secondURL = try XCTUnwrap(URL(string: "https://meet.example.test/second"))
        let events = [
            makeEvent(
                eventId: "first",
                startsAt: date(120),
                endsAt: date(300),
                title: "First",
                meetingLinkPresent: true,
                joinPromptDueAt: date(60),
                openMeetingURL: firstURL
            ),
            makeEvent(
                eventId: "second",
                startsAt: date(120),
                endsAt: date(300),
                title: "Second",
                meetingLinkPresent: true,
                joinPromptDueAt: date(60),
                openMeetingURL: secondURL
            )
        ]

        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: events, now: date(60), isRecordingActive: false)
        )

        XCTAssertEqual(prompt.kind, .join)
        XCTAssertNil(prompt.eventId)
        XCTAssertEqual(prompt.message, SystemAudioStatusLabels.calendarJoinOverlapPromptMessage)
        XCTAssertEqual(prompt.choices.map(\.eventId), ["first", "second"])
        XCTAssertEqual(prompt.choices.map(\.openMeetingURL), [firstURL, secondURL])
    }

    func testDismissedOverlappingJoinPromptDoesNotFallBackToSingleMeeting() throws {
        let firstURL = try XCTUnwrap(URL(string: "https://meet.example.test/first"))
        let secondURL = try XCTUnwrap(URL(string: "https://meet.example.test/second"))
        let events = [
            makeEvent(
                eventId: "first",
                startsAt: date(120),
                endsAt: date(300),
                meetingLinkPresent: true,
                joinPromptDueAt: date(60),
                openMeetingURL: firstURL
            ),
            makeEvent(
                eventId: "second",
                startsAt: date(120),
                endsAt: date(300),
                meetingLinkPresent: true,
                joinPromptDueAt: date(60),
                openMeetingURL: secondURL
            )
        ]
        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: events, now: date(60), isRecordingActive: false)
        )

        XCTAssertNil(
            DesktopCalendarReminderService.activePrompt(
                from: events,
                now: date(60),
                isRecordingActive: false,
                dismissedPromptIDs: [prompt.id]
            )
        )
    }

    func testSelectedJoinChoiceOpensSelectedMeetingURL() throws {
        let firstURL = try XCTUnwrap(URL(string: "https://meet.example.test/first"))
        let secondURL = try XCTUnwrap(URL(string: "https://meet.example.test/second"))
        let prompt = DesktopCalendarReminderService.overlapJoinPrompt(for: [
            makeEvent(eventId: "first", startsAt: date(120), endsAt: date(300), title: "First", openMeetingURL: firstURL),
            makeEvent(eventId: "second", startsAt: date(120), endsAt: date(300), title: "Second", openMeetingURL: secondURL)
        ])
        var selectedPrompt = prompt
        selectedPrompt.eventId = prompt.choices[1].eventId
        selectedPrompt.openMeetingURL = prompt.choices[1].openMeetingURL
        var openedURL: URL?
        var dismissedPromptID: String?

        let actions = DesktopCalendarPromptActions(
            openURL: { openedURL = $0 },
            startRecording: { XCTFail("Join choice must not start recording") },
            dismiss: { dismissedPromptID = $0.id }
        )
        actions.performPrimaryAction(for: selectedPrompt)

        XCTAssertEqual(openedURL, secondURL)
        XCTAssertEqual(dismissedPromptID, prompt.id)
    }

    func testRecordPromptAtEventStartDoesNotAutoRecord() throws {
        let event = makeEvent(startsAt: date(120), endsAt: date(300), recordPromptDueAt: date(120))
        var recordStarts = 0
        var dismissedPromptID: String?

        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: [event], now: date(120), isRecordingActive: false)
        )

        XCTAssertEqual(prompt.kind, .record)
        XCTAssertEqual(recordStarts, 0)

        let actions = DesktopCalendarPromptActions(
            openURL: { _ in XCTFail("Record prompt must not open a meeting URL") },
            startRecording: { recordStarts += 1 },
            dismiss: { dismissedPromptID = $0.id }
        )
        actions.performPrimaryAction(for: prompt)

        XCTAssertEqual(recordStarts, 1)
        XCTAssertEqual(dismissedPromptID, prompt.id)
    }

    // FR-005, FR-015: a synthetic single-event prompt is only a hint; resolve remains automatic.
    func testSingleRecordPromptStartsWithAutomaticIntentAndNoEventID() throws {
        let event = makeEvent(
            eventId: "synthetic-single-event",
            startsAt: date(120),
            endsAt: date(300),
            recordPromptDueAt: date(120)
        )
        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(
                from: [event],
                now: date(120),
                isRecordingActive: false
            )
        )
        var receivedIntent: DesktopCalendarMatchDecisionIntent?
        var receivedEventID: String?
        let actions = DesktopCalendarPromptActions(
            openURL: { _ in XCTFail("Record prompt must not open a meeting URL") },
            startRecording: { intent, eventID in
                receivedIntent = intent
                receivedEventID = eventID
            },
            dismiss: { _ in }
        )

        actions.performPrimaryAction(for: prompt)

        XCTAssertEqual(prompt.eventId, "synthetic-single-event")
        XCTAssertFalse(prompt.requiresExplicitCalendarChoice)
        XCTAssertEqual(receivedIntent, .automatic)
        XCTAssertNil(receivedEventID)
    }

    func testActiveRecordingSuppressesRecordPrompt() {
        let event = makeEvent(startsAt: date(120), endsAt: date(300), recordPromptDueAt: date(120))

        XCTAssertNil(
            DesktopCalendarReminderService.activePrompt(from: [event], now: date(121), isRecordingActive: true)
        )
    }

    func testPrivateAndUnsafeTitlesUseGenericCopy() throws {
        let privateEvent = makeEvent(
            startsAt: date(120),
            endsAt: date(300),
            title: "Board plan",
            titleState: .privateRedacted,
            recordPromptDueAt: date(120)
        )
        let unsafeEvent = makeEvent(
            eventId: "unsafe",
            startsAt: date(500),
            endsAt: date(700),
            title: "alice@example.test passcode 123",
            titleState: .available,
            recordPromptDueAt: date(500)
        )

        let privatePrompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: [privateEvent], now: date(121), isRecordingActive: false)
        )
        let unsafePrompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: [unsafeEvent], now: date(501), isRecordingActive: false)
        )

        XCTAssertEqual(privatePrompt.title, SystemAudioStatusLabels.calendarGenericMeetingTitle)
        XCTAssertEqual(unsafePrompt.title, SystemAudioStatusLabels.calendarGenericMeetingTitle)
        XCTAssertFalse(unsafePrompt.accessibilityLabel.contains("alice@example.test"))
        XCTAssertFalse(unsafePrompt.accessibilityLabel.localizedCaseInsensitiveContains("passcode"))
    }

    func testOverlappingCurrentEventsFallBackToGenericRecordPrompt() throws {
        let events = [
            makeEvent(eventId: "first", startsAt: date(120), endsAt: date(300), title: "First", recordPromptDueAt: date(120)),
            makeEvent(eventId: "second", startsAt: date(150), endsAt: date(330), title: "Second", recordPromptDueAt: date(150))
        ]

        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: events, now: date(160), isRecordingActive: false)
        )

        XCTAssertEqual(prompt.kind, .record)
        XCTAssertNil(prompt.eventId)
        XCTAssertEqual(prompt.title, SystemAudioStatusLabels.calendarGenericMeetingTitle)
        XCTAssertEqual(prompt.message, SystemAudioStatusLabels.calendarOverlapPromptMessage)
        XCTAssertTrue(prompt.requiresExplicitCalendarChoice)
        XCTAssertEqual(prompt.primaryActionTitle, SystemAudioStatusLabels.calendarPromptRecordWithoutContextActionTitle)
        XCTAssertEqual(prompt.choices.compactMap(\.eventId), ["first", "second"])
        XCTAssertNil(prompt.choices.last?.eventId)
    }

    func testOverlapPrimaryActionStartsManualRecordingWithoutSelectingCalendarContext() throws {
        let now = date(160)
        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(
                from: CalendarSettingsFixtures.overlappingPromptEvents(now: now),
                now: now,
                isRecordingActive: false
            )
        )
        var recordStarts = 0
        var openedURL: URL?
        var dismissedPromptID: String?

        let actions = DesktopCalendarPromptActions(
            openURL: { openedURL = $0 },
            startRecording: { recordStarts += 1 },
            dismiss: { dismissedPromptID = $0.id }
        )

        XCTAssertEqual(recordStarts, 0)
        XCTAssertNil(prompt.eventId)
        XCTAssertTrue(prompt.requiresExplicitCalendarChoice)

        actions.performPrimaryAction(for: prompt)

        XCTAssertEqual(recordStarts, 1)
        XCTAssertNil(openedURL)
        XCTAssertEqual(dismissedPromptID, prompt.id)
    }

    // FR-014, FR-015, SC-003: only a synthetic explicit overlap choice may carry its event ID.
    func testOverlapRecordChoiceStartsWithUserSelectedIntentAndChosenEventID() throws {
        var prompt = DesktopCalendarReminderService.overlapRecordPrompt(for: [
            makeEvent(eventId: "synthetic-first", startsAt: date(120), endsAt: date(300)),
            makeEvent(eventId: "synthetic-second", startsAt: date(120), endsAt: date(300))
        ])
        let selectedEventID = try XCTUnwrap(prompt.choices.first?.eventId)
        prompt.eventId = selectedEventID
        var receivedIntent: DesktopCalendarMatchDecisionIntent?
        var receivedEventID: String?
        let actions = DesktopCalendarPromptActions(
            openURL: { _ in XCTFail("Record prompt must not open a meeting URL") },
            startRecording: { intent, eventID in
                receivedIntent = intent
                receivedEventID = eventID
            },
            dismiss: { _ in }
        )

        actions.performPrimaryAction(for: prompt)

        XCTAssertTrue(prompt.requiresExplicitCalendarChoice)
        XCTAssertEqual(prompt.eventId, "synthetic-first")
        XCTAssertEqual(receivedIntent, .userSelected)
        XCTAssertEqual(receivedEventID, "synthetic-first")
    }

    // FR-014, FR-051, SC-014: start-time decline is explicit and never aliases a later clear.
    func testOverlapRecordWithoutContextStartsWithUserDeclinedIntent() throws {
        var prompt = DesktopCalendarReminderService.overlapRecordPrompt(for: [
            makeEvent(eventId: "synthetic-first", startsAt: date(120), endsAt: date(300)),
            makeEvent(eventId: "synthetic-second", startsAt: date(120), endsAt: date(300))
        ])
        let withoutContextChoice = try XCTUnwrap(
            prompt.choices.first { $0.id == "without-calendar-context" }
        )
        prompt.eventId = withoutContextChoice.eventId
        var receivedIntent: DesktopCalendarMatchDecisionIntent?
        var receivedEventID: String?
        let actions = DesktopCalendarPromptActions(
            openURL: { _ in XCTFail("Record prompt must not open a meeting URL") },
            startRecording: { intent, eventID in
                receivedIntent = intent
                receivedEventID = eventID
            },
            dismiss: { _ in }
        )

        actions.performPrimaryAction(for: prompt)

        XCTAssertTrue(prompt.requiresExplicitCalendarChoice)
        XCTAssertNil(prompt.eventId)
        XCTAssertEqual(DesktopCalendarMatchDecisionIntent.userDeclined.rawValue, "user_declined")
        XCTAssertNotEqual(DesktopCalendarMatchDecisionIntent.userDeclined.rawValue, "cleared_by_user")
        XCTAssertEqual(receivedIntent, .userDeclined)
        XCTAssertNil(receivedEventID)
    }

    func testActiveRecordingDoesNotSwitchCalendarContextWhenOverlapAppears() {
        let now = date(160)

        XCTAssertNil(
            DesktopCalendarReminderService.activePrompt(
                from: CalendarSettingsFixtures.overlappingPromptEvents(now: now),
                now: now,
                isRecordingActive: true
            )
        )
    }

    func testDismissedPromptDoesNotReturn() throws {
        var service = DesktopCalendarReminderService()
        let event = makeEvent(startsAt: date(120), endsAt: date(300), recordPromptDueAt: date(120))
        let prompt = try XCTUnwrap(service.activePrompt(from: [event], now: date(120), isRecordingActive: false))

        service.dismiss(prompt)

        XCTAssertNil(service.activePrompt(from: [event], now: date(121), isRecordingActive: false))
    }

    func testDesktopUpcomingResponseDecodesEndpointShape() throws {
        let json = """
        {
          "events": [{
            "event_id": "00000000-0000-0000-0000-000000000060",
            "provider_family": "caldav_yandex",
            "starts_at": "2026-06-27T10:00:00Z",
            "ends_at": "2026-06-27T11:00:00Z",
            "title": null,
            "title_state": "free_busy_only",
            "meeting_link_present": true,
            "attendee_count": 3,
            "privacy_class": "private",
            "join_prompt_due_at": "2026-06-27T09:59:00Z",
            "record_prompt_due_at": "2026-06-27T10:00:00Z",
            "join_prompt_state": "not_due",
            "record_prompt_state": "not_due",
            "open_meeting_url": "https://meet.example.test/authorized"
          }]
        }
        """

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let response = try decoder.decode(DesktopCalendarPromptResponse.self, from: Data(json.utf8))

        XCTAssertEqual(response.events.count, 1)
        XCTAssertEqual(response.events[0].titleState, .freeBusyOnly)
        XCTAssertEqual(response.events[0].openMeetingURL?.host, "meet.example.test")
    }

    func testPromptAccessibilityCopyNamesManualAction() throws {
        let event = makeEvent(startsAt: date(120), endsAt: date(300), recordPromptDueAt: date(120))
        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: [event], now: date(120), isRecordingActive: false)
        )

        XCTAssertTrue(prompt.accessibilityLabel.contains(SystemAudioStatusLabels.calendarPromptRecordActionTitle))
        XCTAssertTrue(prompt.accessibilityLabel.contains("Запись не начинается автоматически"))
        XCTAssertEqual(SystemAudioAccessibilityIdentifier.calendarPrompt, "systemAudio.calendar.prompt")
    }

    private func makeEvent(
        eventId: String = "event",
        startsAt: Date,
        endsAt: Date,
        title: String? = "Calendar meeting",
        titleState: CalendarEventTitleState = .available,
        meetingLinkPresent: Bool = false,
        joinPromptDueAt: Date? = nil,
        recordPromptDueAt: Date? = nil,
        openMeetingURL: URL? = nil
    ) -> DesktopCalendarPromptEvent {
        DesktopCalendarPromptEvent(
            eventId: eventId,
            startsAt: startsAt,
            endsAt: endsAt,
            title: title,
            titleState: titleState,
            meetingLinkPresent: meetingLinkPresent,
            joinPromptDueAt: joinPromptDueAt,
            recordPromptDueAt: recordPromptDueAt,
            openMeetingURL: openMeetingURL
        )
    }

    private func date(_ seconds: TimeInterval) -> Date {
        Date(timeIntervalSince1970: seconds)
    }

}
#endif
