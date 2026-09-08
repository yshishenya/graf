import AppKit
import Foundation
@testable import TwoBrainRecAppCore
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

    func testExplicitHiddenStateRespectedAndOwnerTitlePreserved() throws {
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
        XCTAssertEqual(unsafePrompt.title, unsafeEvent.title)
        XCTAssertTrue(unsafePrompt.accessibilityLabel.contains("alice@example.test"))
        XCTAssertTrue(unsafePrompt.accessibilityLabel.localizedCaseInsensitiveContains("passcode"))
    }

    func testProviderAuthorizedLinksRemainInOwnerPromptTitles() throws {
        let googleMeetEvent = makeEvent(
            eventId: "google-meet",
            startsAt: date(120),
            endsAt: date(300),
            title: "meet.google.com/abc-defg-hij?token=attacker-secret",
            titleState: .available,
            joinPromptDueAt: date(60),
            openMeetingURL: try XCTUnwrap(URL(string: "https://meet.google.com/abc-defg-hij"))
        )
        let teamsEvent = makeEvent(
            eventId: "teams",
            startsAt: date(120),
            endsAt: date(300),
            title: "teams.microsoft.com/l/meetup-join/19%3ameeting-secret-thread",
            titleState: .available,
            joinPromptDueAt: date(60),
            openMeetingURL: try XCTUnwrap(URL(string: "https://teams.microsoft.com/l/meetup-join/example"))
        )

        let googlePrompt = DesktopCalendarReminderService.joinPrompt(for: googleMeetEvent)
        let overlapPrompt = DesktopCalendarReminderService.overlapJoinPrompt(for: [googleMeetEvent, teamsEvent])

        XCTAssertEqual(googlePrompt.title, googleMeetEvent.title)
        XCTAssertTrue(googlePrompt.accessibilityLabel.contains("meet.google.com"))
        XCTAssertEqual(overlapPrompt.choices.map(\.title), [
            googleMeetEvent.title!,
            teamsEvent.title!
        ])
    }

    func testMissingOwnerTitleAndVerbatimWhitespace() {
        let missing = makeEvent(startsAt: date(120), endsAt: date(300), title: nil, titleState: .available)
        XCTAssertEqual(missing.safeDisplayTitle(), "Без названия")
        let verbatim = makeEvent(startsAt: date(120), endsAt: date(300), title: "  alice@example.test https://example.test/?password=synthetic  ")
        XCTAssertEqual(verbatim.safeDisplayTitle(), verbatim.title)
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
          "show_upcoming_time": false,
          "show_upcoming_title": false,
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
        XCTAssertFalse(response.showUpcomingTime)
        XCTAssertFalse(response.showUpcomingTitle)
        XCTAssertEqual(response.events[0].titleState, .freeBusyOnly)
        XCTAssertEqual(response.events[0].openMeetingURL?.host, "meet.example.test")
    }

    @MainActor
    func testCalendarTrayModelSortsEventsAndKeepsSafeProjection() async {
        let later = makeEvent(
            eventId: "later",
            startsAt: date(300),
            endsAt: date(360),
            title: "Later meeting"
        )
        let earlier = makeEvent(
            eventId: "earlier",
            startsAt: date(120),
            endsAt: date(180),
            title: "Earlier meeting"
        )
        let model = CalendarTrayModel {
            DesktopCalendarPromptResponse(
                events: [later, earlier],
                showUpcomingTime: false,
                showUpcomingTitle: false
            )
        }

        await model.refresh()

        XCTAssertEqual(model.events.map(\.eventId), ["earlier", "later"])
        XCTAssertEqual(model.events[0].safeDisplayTitle(), "Earlier meeting")
        XCTAssertFalse(model.showUpcomingTime)
        XCTAssertFalse(model.showUpcomingTitle)
    }

    func testCalendarTrayModelIgnoresAnOlderRefreshThatFinishesLast() async {
        let loader = CalendarTrayControlledLoader()
        let model = CalendarTrayModel { try await loader.load() }

        let first = Task { await model.refresh() }
        await loader.waitForRequestCount(1)
        let second = Task { await model.refresh() }
        await loader.waitForRequestCount(2)

        await loader.complete(
            request: 1,
            with: DesktopCalendarPromptResponse(
                events: [makeEvent(eventId: "new", startsAt: date(120), endsAt: date(180))]
            )
        )
        await second.value
        await loader.complete(
            request: 0,
            with: DesktopCalendarPromptResponse(
                events: [makeEvent(eventId: "old", startsAt: date(60), endsAt: date(90))]
            )
        )
        await first.value

        XCTAssertEqual(model.events.map(\.eventId), ["new"])
    }

    func testCalendarTrayStaysCompactWithoutConfirmedEventsAndRecoversAfterFailures() async {
        let loader = CalendarTrayControlledLoader()
        let model = CalendarTrayModel { try await loader.load() }
        let first = Task { await model.refresh() }
        await loader.waitForRequestCount(1)
        await loader.complete(request: 0, with: DesktopCalendarPromptResponse(events: []))
        await first.value

        let failures: [any Error] = [
            DesktopUploadClientError.httpStatus(401, "auth_required"),
            DesktopUploadClientError.httpStatus(503, "unavailable"),
            URLError(.notConnectedToInternet)
        ]
        for (index, error) in failures.enumerated() {
            let success = Task { await model.refresh() }
            await loader.waitForRequestCount(index * 2 + 2)
            await loader.complete(request: index * 2 + 1, with: DesktopCalendarPromptResponse(
                events: [makeEvent(startsAt: date(120), endsAt: date(180))]
            ))
            await success.value
            XCTAssertEqual(model.events.count, 1)

            let failure = Task { await model.refresh() }
            await loader.waitForRequestCount(index * 2 + 3)
            XCTAssertEqual(model.events.count, 1, "Background refresh keeps useful content until it finishes")
            await loader.fail(request: index * 2 + 2, with: error)
            await failure.value
            XCTAssertTrue(model.events.isEmpty, "Do not expose outdated or signed-out calendar data")
        }
        model.appUpdatePresentation = AppUpdatePresentation(
            phase: .available, availableVersion: "2026.09.08.1", isUserInitiated: false, message: nil
        )
    }

    func testCalendarTrayVectorIsMonochromeTransparentAndHasDistinctRecordingMarks() throws {
        var rendered: [Data] = []
        for state in [GrafTrayRecordingState.idle, .recording, .paused] {
            let image = CalendarTrayController.statusIcon(recordingState: state)
            XCTAssertTrue(image.isTemplate, "macOS supplies light/dark/selected menu-bar contrast")
            XCTAssertEqual(image.size, NSSize(width: 22, height: 22), "Capture must not resize or displace the menu-bar anchor")
            let data = try XCTUnwrap(image.tiffRepresentation)
            rendered.append(data)
            let bitmap = try XCTUnwrap(NSBitmapImageRep(data: data))
            XCTAssertEqual(bitmap.colorAt(x: 0, y: 0)?.alphaComponent, 0)
            XCTAssertEqual(bitmap.colorAt(x: 20, y: 2)?.alphaComponent, 0,
                           "No separate mark outside the GRAF silhouette")
            var inkPixels = 0
            for y in 0..<bitmap.pixelsHigh {
                for x in 0..<bitmap.pixelsWide {
                    let color = try XCTUnwrap(bitmap.colorAt(x: x, y: y)?.usingColorSpace(.deviceRGB))
                    guard color.alphaComponent > 0 else { continue }
                    inkPixels += 1
                    XCTAssertEqual(color.redComponent, color.greenComponent, accuracy: 0.001)
                    XCTAssertEqual(color.greenComponent, color.blueComponent, accuracy: 0.001)
                }
            }
            XCTAssertGreaterThan(inkPixels, 60, "The vector must render, not just reserve a canvas")
            XCTAssertLessThan(inkPixels, bitmap.pixelsWide * bitmap.pixelsHigh / 2, "No opaque app-icon background")
        }
        XCTAssertNotEqual(rendered[0], rendered[1])
        XCTAssertEqual(rendered[1], rendered[2], "A microphone pause still records system audio")
    }

    func testCalendarTrayTracksRealCaptureAndPreservesItWhenAnUpdateArrives() {
        let model = CalendarTrayModel { DesktopCalendarPromptResponse(events: []) }
        let tray = CalendarTrayController(model: model, onOpenSettings: {}, onOpenMeetings: {},
                                          onStartRecording: {}, onStopRecording: {}, onQuit: {})
        let transitions: [(CaptureSessionState?, Bool, Bool, GrafTrayRecordingState)] = [
            (nil, false, false, .idle), (.starting, false, false, .idle),
            (.failed, false, false, .idle), (.active, true, false, .recording),
            (.paused, true, false, .paused), (.active, true, false, .recording),
            (.degraded, true, false, .recording), (.active, false, true, .stopping),
            (.stopped, false, false, .idle), (.finalized, false, false, .idle)
        ]
        for (session, active, stopping, expected) in transitions {
            let state = GrafTrayRecordingState.resolve(sessionState: session, writerActive: active, stopping: stopping)
            XCTAssertEqual(state, expected)
            tray.showRecordingState(state)
            XCTAssertEqual(model.recordingState, expected)
            XCTAssertEqual(tray.statusItemLabel, expected.label.map { "GRAF — \($0)" } ?? "GRAF")
        }
        tray.showRecordingState(.recording)
        tray.showUpdate(AppUpdatePresentation(phase: .available, availableVersion: "2026.09.08.1",
                                             isUserInitiated: false, message: nil), actionEnabled: true)
        XCTAssertEqual(model.recordingState, .recording)
        XCTAssertTrue(tray.statusItemLabel.contains("Идёт запись"))
        XCTAssertTrue(tray.statusItemLabel.contains("2026.09.08.1"))
        tray.showRecordingState(.idle)
        XCTAssertFalse(tray.statusItemLabel.contains("Идёт запись"))
        XCTAssertTrue(tray.statusItemLabel.contains("2026.09.08.1"))
    }

    func testNativeTrayMenuCommandsFollowCaptureStateAndRejectStaleActions() throws {
        let model = CalendarTrayModel { DesktopCalendarPromptResponse(events: []) }
        var starts = 0
        var stops = 0
        var settings = 0
        var quits = 0
        let tray = CalendarTrayController(model: model, onOpenSettings: { settings += 1 }, onOpenMeetings: {},
                                          onStartRecording: { starts += 1 }, onStopRecording: { stops += 1 },
                                          onQuit: { quits += 1 })
        tray.rebuildMenu()
        XCTAssertEqual(tray.menu.items.filter { !$0.isSeparatorItem }.map(\.title),
                       ["Начать запись", "Открыть GRAF", "Настройки…", "Выйти из GRAF"])
        XCTAssertEqual(tray.menu.minimumWidth, 240)
        XCTAssertTrue(tray.menu.items.allSatisfy { $0.view == nil }, "Native rows retain keyboard, theme and outside-click behavior")
        tray.menu.performActionForItem(at: 0)
        XCTAssertEqual(starts, 1)
        XCTAssertEqual(GrafTrayRecordingState.resolve(sessionState: .starting, writerActive: false,
                                                     stopping: false, starting: true), .starting)
        for (state, title, enabled) in [(GrafTrayRecordingState.starting, "Начинаем запись…", false),
                                       (.recording, "Остановить запись", true),
                                       (.paused, "Остановить запись", true),
                                       (.stopping, "Завершаем запись…", false)] {
            tray.showRecordingState(state)
            tray.rebuildMenu()
            let first = try XCTUnwrap(tray.menu.items.first)
            XCTAssertEqual(first.title, title)
            XCTAssertEqual(first.isEnabled, enabled)
            tray.startRecording()
            XCTAssertEqual(starts, 1, "A queued stale Start must not invoke capture")
            if enabled { tray.menu.performActionForItem(at: 0) }
        }
        XCTAssertEqual(stops, 2)
        tray.showRecordingState(.idle)
        tray.stopRecording()
        XCTAssertEqual(stops, 2, "A queued stale Stop must not finalize an idle writer")
        tray.showUpdate(AppUpdatePresentation(phase: .available, availableVersion: "2026.09.08.1",
                                             isUserInitiated: false, message: nil), actionEnabled: false)
        tray.rebuildMenu()
        XCTAssertEqual(tray.menu.items.first { $0.identifier?.rawValue == "graf.menu.update" }?.isEnabled, false)
        let settingsIndex = try XCTUnwrap(tray.menu.items.firstIndex { $0.identifier?.rawValue == "graf.menu.settings" })
        tray.menu.performActionForItem(at: settingsIndex)
        tray.menu.performActionForItem(at: tray.menu.numberOfItems - 1)
        XCTAssertEqual(settings, 1)
        XCTAssertEqual(quits, 1)
        XCTAssertEqual(starts, 1, "Settings and Quit never invoke recording")
        XCTAssertEqual(tray.menu.items.first?.title, "Начать запись")
    }

    func testNativeMenuDismissesAppWindowsButKeepsItsOwnSurfaceAndReleasesMonitors() {
        let window = NSWindow()
        for (level, outside) in [(NSWindow.Level.normal, true), (.floating, true),
                                 (.mainMenu, false), (.statusBar, false), (.popUpMenu, false)] {
            window.level = level
            XCTAssertEqual(CalendarTrayController.isOutsideMenuWindow(window), outside)
        }
        XCTAssertFalse(CalendarTrayController.isOutsideMenuWindow(nil))
        let model = CalendarTrayModel { DesktopCalendarPromptResponse(events: []) }
        let tray = CalendarTrayController(model: model, onOpenSettings: {}, onOpenMeetings: {},
                                          onStartRecording: {}, onStopRecording: {}, onQuit: {})
        for _ in 0..<2 {
            XCTAssertFalse(tray.hasMouseMonitors)
            tray.menuWillOpen(tray.menu)
            tray.menuWillOpen(tray.menu)
            XCTAssertTrue(tray.hasMouseMonitors)
            tray.menuDidClose(tray.menu)
            XCTAssertFalse(tray.hasMouseMonitors)
        }
    }

    func testNativeTrayCalendarRespectsPrivacyAndOnlyEnablesSafeMeetingLinks() async throws {
        let safe = makeEvent(eventId: "safe", startsAt: date(120), endsAt: date(180),
                             title: String(repeating: "Long title ", count: 12), meetingLinkPresent: true,
                             openMeetingURL: URL(string: "https://example.com/meeting"))
        let unsafe = makeEvent(eventId: "unsafe", startsAt: date(240), endsAt: date(300),
                               meetingLinkPresent: true, openMeetingURL: URL(string: "http://example.com/meeting"))
        let privateEvent = makeEvent(eventId: "private", startsAt: date(360), endsAt: date(420),
                                     title: "Must stay private", titleState: .privateRedacted)
        for showDetails in [false, true] {
            let model = CalendarTrayModel {
                DesktopCalendarPromptResponse(events: [safe, unsafe, privateEvent],
                                              showUpcomingTime: showDetails, showUpcomingTitle: showDetails)
            }
            await model.refresh()
            let tray = CalendarTrayController(model: model, onOpenSettings: {}, onOpenMeetings: {},
                                          onStartRecording: {}, onStopRecording: {}, onQuit: {})
            tray.rebuildMenu()
            let events = tray.menu.items.filter { $0.identifier?.rawValue == "graf.menu.event" }
            XCTAssertEqual(events.count, 3)
            XCTAssertEqual(events.map(\.isEnabled), [true, false, false])
            XCTAssertFalse(events.contains { ($0.toolTip ?? "").contains("Must stay private") })
            if showDetails {
                XCTAssertTrue(events[0].title.hasSuffix("…"))
                XCTAssertLessThan(events[0].title.count, 50)
            } else {
                XCTAssertEqual(events.map(\.title), ["Встреча", "Встреча", "Встреча"])
                XCTAssertEqual(events.map(\.toolTip), ["Встреча", "Встреча", "Встреча"])
            }
        }
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

private actor CalendarTrayControlledLoader {
    private var continuations: [CheckedContinuation<DesktopCalendarPromptResponse, Error>] = []

    func load() async throws -> DesktopCalendarPromptResponse {
        try await withCheckedThrowingContinuation { continuation in
            continuations.append(continuation)
        }
    }

    func waitForRequestCount(_ count: Int) async {
        while continuations.count < count {
            await Task.yield()
        }
    }

    func fail(request index: Int, with error: any Error) {
        continuations[index].resume(throwing: error)
    }

    func complete(request index: Int, with response: DesktopCalendarPromptResponse) {
        continuations[index].resume(returning: response)
    }
}
#endif
