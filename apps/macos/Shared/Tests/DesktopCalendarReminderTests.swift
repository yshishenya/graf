import AppKit
import QuartzCore
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

    func testSelectedJoinChoiceOpensSelectedMeetingURL() async throws {
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
            openURL: { openedURL = $0; return true },
            startRecording: { XCTFail("Join choice must not start recording") },
            dismiss: { dismissedPromptID = $0.id }
        )
        await actions.performPrimaryAction(for: selectedPrompt)

        XCTAssertEqual(openedURL, secondURL)
        XCTAssertEqual(dismissedPromptID, prompt.id)
    }

    func testRecordPromptAtEventStartDoesNotAutoRecord() async throws {
        let event = makeEvent(startsAt: date(120), endsAt: date(300), recordPromptDueAt: date(120))
        var recordStarts = 0
        var dismissedPromptID: String?

        let prompt = try XCTUnwrap(
            DesktopCalendarReminderService.activePrompt(from: [event], now: date(120), isRecordingActive: false)
        )

        XCTAssertEqual(prompt.kind, .record)
        XCTAssertEqual(recordStarts, 0)

        let actions = DesktopCalendarPromptActions(
            openURL: { _ in XCTFail("Record prompt must not open a meeting URL"); return false },
            startRecording: { recordStarts += 1 },
            dismiss: { dismissedPromptID = $0.id }
        )
        await actions.performPrimaryAction(for: prompt)

        XCTAssertEqual(recordStarts, 1)
        XCTAssertEqual(dismissedPromptID, prompt.id)
    }

    // FR-005, FR-015: a synthetic single-event prompt is only a hint; resolve remains automatic.
    func testSingleRecordPromptStartsWithAutomaticIntentAndNoEventID() async throws {
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
            openURL: { _ in XCTFail("Record prompt must not open a meeting URL"); return false },
            startRecording: { intent, eventID in
                receivedIntent = intent
                receivedEventID = eventID
            },
            dismiss: { _ in }
        )

        await actions.performPrimaryAction(for: prompt)

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

    func testOverlapPrimaryActionStartsManualRecordingWithoutSelectingCalendarContext() async throws {
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
            openURL: { openedURL = $0; return true },
            startRecording: { recordStarts += 1 },
            dismiss: { dismissedPromptID = $0.id }
        )

        XCTAssertEqual(recordStarts, 0)
        XCTAssertNil(prompt.eventId)
        XCTAssertTrue(prompt.requiresExplicitCalendarChoice)

        await actions.performPrimaryAction(for: prompt)

        XCTAssertEqual(recordStarts, 1)
        XCTAssertNil(openedURL)
        XCTAssertEqual(dismissedPromptID, prompt.id)
    }

    // FR-014, FR-015, SC-003: only a synthetic explicit overlap choice may carry its event ID.
    func testOverlapRecordChoiceStartsWithUserSelectedIntentAndChosenEventID() async throws {
        var prompt = DesktopCalendarReminderService.overlapRecordPrompt(for: [
            makeEvent(eventId: "synthetic-first", startsAt: date(120), endsAt: date(300)),
            makeEvent(eventId: "synthetic-second", startsAt: date(120), endsAt: date(300))
        ])
        let selectedEventID = try XCTUnwrap(prompt.choices.first?.eventId)
        prompt.eventId = selectedEventID
        var receivedIntent: DesktopCalendarMatchDecisionIntent?
        var receivedEventID: String?
        let actions = DesktopCalendarPromptActions(
            openURL: { _ in XCTFail("Record prompt must not open a meeting URL"); return false },
            startRecording: { intent, eventID in
                receivedIntent = intent
                receivedEventID = eventID
            },
            dismiss: { _ in }
        )

        await actions.performPrimaryAction(for: prompt)

        XCTAssertTrue(prompt.requiresExplicitCalendarChoice)
        XCTAssertEqual(prompt.eventId, "synthetic-first")
        XCTAssertEqual(receivedIntent, .userSelected)
        XCTAssertEqual(receivedEventID, "synthetic-first")
    }

    // FR-014, FR-051, SC-014: start-time decline is explicit and never aliases a later clear.
    func testOverlapRecordWithoutContextStartsWithUserDeclinedIntent() async throws {
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
            openURL: { _ in XCTFail("Record prompt must not open a meeting URL"); return false },
            startRecording: { intent, eventID in
                receivedIntent = intent
                receivedEventID = eventID
            },
            dismiss: { _ in }
        )

        await actions.performPrimaryAction(for: prompt)

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
        var projections: [CalendarProjectionUpdate] = []
        model.onProjection = { projections.append($0) }
        let newest = DesktopCalendarPromptResponse(
            events: [makeEvent(eventId: "new", startsAt: date(120), endsAt: date(180))]
        )

        let first = Task { await model.refresh() }
        await loader.waitForRequestCount(1)
        let second = Task { await model.refresh() }
        await loader.waitForRequestCount(2)

        await loader.complete(
            request: 1,
            with: newest
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
        XCTAssertEqual(projections, [.confirmed(newest)])
    }

    func testCalendarProjectionInvalidationRejectsPendingResponseAndKeepsCaptureState() async {
        let loader = CalendarTrayControlledLoader()
        let model = CalendarTrayModel { try await loader.load() }
        var projections: [CalendarProjectionUpdate] = []
        var invalidations = 0
        model.onProjection = { projections.append($0) }
        model.onAuthInvalidated = { invalidations += 1 }
        model.recordingState = .recording
        let pending = Task { await model.refresh() }
        await loader.waitForRequestCount(1)
        model.invalidate()
        XCTAssertEqual(projections, [.invalidated], "Context invalidation must publish synchronously")
        XCTAssertEqual(invalidations, 1)
        await loader.complete(request: 0, with: DesktopCalendarPromptResponse(
            events: [makeEvent(eventId: "old-account", startsAt: date(120), endsAt: date(180))]
        ))
        await pending.value
        XCTAssertEqual(projections, [.invalidated])
        XCTAssertEqual(invalidations, 1)
        XCTAssertTrue(model.events.isEmpty)
        XCTAssertEqual(model.recordingState, .recording)
    }

    func testTrayAuthInvalidationRejectsPendingProjectionSynchronously() async {
        let loader = CalendarTrayControlledLoader()
        let model = CalendarTrayModel { try await loader.load() }
        let tray = CalendarTrayController(model: model, onOpenSettings: {}, onOpenMeetings: {},
            onStartRecording: {}, onStopRecording: {}, onMuteMicrophone: {},
            onUnmuteMicrophone: {}, onQuit: {})
        var projections: [CalendarProjectionUpdate] = []
        model.onProjection = { projections.append($0) }
        let pending = Task { await model.refresh() }
        await loader.waitForRequestCount(1)
        tray.invalidateAuthContext()
        XCTAssertEqual(projections, [.invalidated], "Invalidation must finish without yielding to queued responses")
        await loader.complete(request: 0, with: DesktopCalendarPromptResponse(
            events: [makeEvent(eventId: "previous-account", startsAt: date(120), endsAt: date(180))]
        ))
        await pending.value
        XCTAssertEqual(projections, [.invalidated], "A response from the previous account must not reach notifications")
        XCTAssertTrue(model.events.isEmpty)
    }

    func testCalendarProjectionClassifiesRetryableHTTPFailuresAsTemporarilyUnavailable() async {
        for status in [408, 429, 500, 503, 599] {
            await assertCalendarFailure(
                DesktopUploadClientError.httpStatus(status, "synthetic_unavailable"),
                projects: .temporarilyUnavailable,
                invalidatesAuth: false,
                context: "HTTP \(status)"
            )
        }
    }

    func testCalendarProjectionClassifiesAllowlistedNetworkFailuresAsTemporarilyUnavailable() async {
        let codes: [URLError.Code] = [
            .timedOut, .notConnectedToInternet, .networkConnectionLost,
            .cannotFindHost, .dnsLookupFailed, .cannotConnectToHost
        ]
        for code in codes {
            await assertCalendarFailure(
                URLError(code), projects: .temporarilyUnavailable, invalidatesAuth: false,
                context: "URLError \(code.rawValue)"
            )
        }
    }

    func testCalendarProjectionAuthClassificationOverridesRetryableStatusAndMisleadingNetworkCode() async {
        for code in ["auth_required", "session_expired", "tenant_context_missing",
                     "tenant_scope_denied", "meeting_scope_denied", "device_scope_denied"] {
            let error = DesktopUploadClientError.httpStatus(500, code)
            XCTAssertEqual(error.failureCategory, .authSession)
            await assertCalendarFailure(
                error, projects: .invalidated, invalidatesAuth: true, context: "HTTP 500 / \(code)"
            )
        }
        for status in [401, 403] {
            for code in ["synthetic_denied", "network_unavailable"] {
                let error = DesktopUploadClientError.httpStatus(status, code)
                if code == "network_unavailable" {
                    XCTAssertEqual(error.failureCategory, .network,
                                   "Exercise the explicit status guard, not only authSession classification")
                }
                await assertCalendarFailure(
                    error, projects: .invalidated, invalidatesAuth: true,
                    context: "HTTP \(status) / \(code)"
                )
            }
        }
    }

    func testCalendarProjectionUnknownMalformedAndCancelledFailuresInvalidateWithoutAuthCallback() async {
        let failures: [(String, any Error)] = [
            ("unknown", CalendarProjectionTestError.unknown),
            ("HTTP 400", DesktopUploadClientError.httpStatus(400, "bad_request")),
            ("HTTP 400 with network code", DesktopUploadClientError.httpStatus(400, "network_unavailable")),
            ("HTTP outside 5xx", DesktopUploadClientError.httpStatus(600, "network_unavailable")),
            ("invalid response", DesktopUploadClientError.invalidResponse),
            ("task cancellation", CancellationError()),
            ("URL cancellation", URLError(.cancelled)),
            ("bad URL", URLError(.badURL)),
            ("TLS failure", URLError(.secureConnectionFailed))
        ]
        for (context, error) in failures {
            await assertCalendarFailure(
                error, projects: .invalidated, invalidatesAuth: false, context: context
            )
        }
    }

    func testCalendarProjectionConfirmedEmptyResponseIsNotAnErrorOrAuthInvalidation() async {
        let loader = CalendarTrayControlledLoader()
        let model = CalendarTrayModel { try await loader.load() }
        var projections: [CalendarProjectionUpdate] = []
        var authInvalidations = 0
        model.onProjection = { projections.append($0) }
        model.onAuthInvalidated = { authInvalidations += 1 }
        let populated = DesktopCalendarPromptResponse(
            events: [makeEvent(startsAt: date(120), endsAt: date(180))]
        )
        let empty = DesktopCalendarPromptResponse(events: [], showUpcomingTime: false, showUpcomingTitle: false)
        for (index, response) in [populated, empty].enumerated() {
            let refresh = Task { await model.refresh() }
            await loader.waitForRequestCount(index + 1)
            await loader.complete(request: index, with: response)
            await refresh.value
        }
        XCTAssertEqual(projections, [.confirmed(populated), .confirmed(empty)])
        XCTAssertTrue(model.events.isEmpty)
        XCTAssertFalse(model.showUpcomingTime)
        XCTAssertFalse(model.showUpcomingTitle)
        XCTAssertEqual(authInvalidations, 0)
    }

    func testCalendarProjectionIgnoresLateFailureAfterNewerSuccessIncludingAuthErrors() async {
        let failures: [any Error] = [
            DesktopUploadClientError.httpStatus(503, "unavailable"),
            URLError(.notConnectedToInternet),
            DesktopUploadClientError.httpStatus(401, "network_unavailable"),
            DesktopUploadClientError.httpStatus(500, "auth_required"),
            CalendarProjectionTestError.unknown
        ]
        for error in failures {
            let loader = CalendarTrayControlledLoader()
            let model = CalendarTrayModel { try await loader.load() }
            var projections: [CalendarProjectionUpdate] = []
            var authInvalidations = 0
            model.onProjection = { projections.append($0) }
            model.onAuthInvalidated = { authInvalidations += 1 }
            model.recordingState = .recording
            let older = Task { await model.refresh() }
            await loader.waitForRequestCount(1)
            let newer = Task { await model.refresh() }
            await loader.waitForRequestCount(2)
            let confirmed = DesktopCalendarPromptResponse(
                events: [makeEvent(eventId: "current", startsAt: date(120), endsAt: date(180))],
                showUpcomingTime: false, showUpcomingTitle: false
            )
            await loader.complete(request: 1, with: confirmed)
            await newer.value
            await loader.fail(request: 0, with: error)
            await older.value

            XCTAssertEqual(projections, [.confirmed(confirmed)], "Late failure: \(error)")
            XCTAssertEqual(model.events, confirmed.events, "Late failure must not clear the newer menu projection")
            XCTAssertFalse(model.showUpcomingTime)
            XCTAssertFalse(model.showUpcomingTitle)
            XCTAssertEqual(authInvalidations, 0, "An obsolete auth failure must not invalidate the current context")
            XCTAssertEqual(model.recordingState, .recording)
        }
    }

    func testCalendarProjectionIgnoresPendingFailureAfterExplicitInvalidation() async {
        let failures: [any Error] = [
            DesktopUploadClientError.httpStatus(503, "unavailable"),
            URLError(.timedOut),
            DesktopUploadClientError.httpStatus(403, "network_unavailable"),
            DesktopUploadClientError.httpStatus(500, "auth_required"),
            DesktopUploadClientError.invalidResponse,
            CancellationError()
        ]
        for error in failures {
            let loader = CalendarTrayControlledLoader()
            let model = CalendarTrayModel { try await loader.load() }
            var projections: [CalendarProjectionUpdate] = []
            var authInvalidations = 0
            model.onProjection = { projections.append($0) }
            model.onAuthInvalidated = { authInvalidations += 1 }
            model.recordingState = .paused
            let pending = Task { await model.refresh() }
            await loader.waitForRequestCount(1)
            model.invalidate()
            XCTAssertEqual(projections, [.invalidated], "Invalidation must be synchronous")
            XCTAssertEqual(authInvalidations, 1)
            await loader.fail(request: 0, with: error)
            await pending.value

            XCTAssertEqual(projections, [.invalidated], "Late failure must not publish after invalidation: \(error)")
            XCTAssertEqual(authInvalidations, 1, "Obsolete failures must not invalidate auth again")
            XCTAssertTrue(model.events.isEmpty)
            XCTAssertEqual(model.recordingState, .paused)
        }
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
        XCTAssertNotEqual(rendered[0], rendered[1], "A large central recording light replaces the equalizer bars")
        XCTAssertEqual(rendered[1], rendered[2], "Mute preserves the same GRAF contour")
    }

    func testRecordingLightStaysVisibleDuringMuteAndStopsMovingForAccessibility() throws {
        let light = GrafRecordingLightView(frame: NSRect(x: 0, y: 0, width: 22, height: 22))
        light.wantsLayer = true
        XCTAssertNil(light.hitTest(NSPoint(x: 11, y: 6)), "The light cannot steal a status-button click")
        for state in [GrafTrayRecordingState.recording, .paused] {
            light.update(state: state, reduceMotion: false)
            XCTAssertFalse(light.isHidden, "Mute still records system audio")
            let pulse = try XCTUnwrap(light.layer?.animation(forKey: "recordingPulse") as? CABasicAnimation)
            XCTAssertEqual(pulse.fromValue as? Double, 1)
            XCTAssertEqual(pulse.toValue as? Double, 0.55)
            XCTAssertEqual(pulse.duration, 0.9)
            XCTAssertTrue(pulse.autoreverses)
            light.update(state: state, reduceMotion: true)
            XCTAssertFalse(light.isHidden)
            XCTAssertNil(light.layer?.animation(forKey: "recordingPulse"))
            XCTAssertEqual(light.layer?.opacity, 1)
        }
        for state in [GrafTrayRecordingState.stopping, .idle, .starting] {
            light.update(state: state, reduceMotion: false)
            XCTAssertEqual(light.isHidden, state != .stopping)
            XCTAssertNil(light.layer?.animation(forKey: "recordingPulse"))
        }
        light.update(state: .recording, reduceMotion: true)
        let bitmap = try XCTUnwrap(light.bitmapImageRepForCachingDisplay(in: light.bounds))
        light.cacheDisplay(in: light.bounds, to: bitmap)
        var redPixels = 0
        for y in 0..<bitmap.pixelsHigh {
            for x in 0..<bitmap.pixelsWide {
                let color = try XCTUnwrap(bitmap.colorAt(x: x, y: y)?.usingColorSpace(.deviceRGB))
                guard color.alphaComponent > 0 else { continue }
                XCTAssertGreaterThan(color.redComponent, color.greenComponent)
                redPixels += 1
                let point = NSPoint(x: CGFloat(x) * 22 / CGFloat(bitmap.pixelsWide),
                                    y: 22 - CGFloat(y) * 22 / CGFloat(bitmap.pixelsHigh))
                XCTAssertTrue(NSRect(x: 5, y: 5, width: 12, height: 12).contains(point), "Red pixels stay inside the logo")
            }
        }
        XCTAssertGreaterThan(redPixels, 40, "The central recording disk must be substantially larger than the old dot")
        let centerX = bitmap.pixelsWide / 2
        let centerY = bitmap.pixelsHigh / 2
        XCTAssertGreaterThan(try XCTUnwrap(bitmap.colorAt(x: centerX, y: centerY)).alphaComponent, 0.9)
        light.update(state: .paused, reduceMotion: true)
        let mutedBitmap = try XCTUnwrap(light.bitmapImageRepForCachingDisplay(in: light.bounds))
        light.cacheDisplay(in: light.bounds, to: mutedBitmap)
        XCTAssertLessThan(try XCTUnwrap(mutedBitmap.colorAt(x: centerX, y: centerY)).alphaComponent, 0.1,
                          "Mute leaves a flat transparent slot inside the still-visible red disk")
    }

    func testCalendarTrayTracksRealCaptureAndPreservesItWhenAnUpdateArrives() {
        let model = CalendarTrayModel { DesktopCalendarPromptResponse(events: []) }
        let tray = CalendarTrayController(model: model, onOpenSettings: {}, onOpenMeetings: {},
                                          onStartRecording: {}, onStopRecording: {},
                                          onMuteMicrophone: {}, onUnmuteMicrophone: {}, onQuit: {})
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
        let update = AppUpdatePresentation(phase: .available, availableVersion: "2026.09.08.1",
                                           isUserInitiated: false, message: nil)
        tray.showUpdate(update, actionEnabled: true)
        XCTAssertEqual(model.recordingState, .recording)
        XCTAssertTrue(tray.statusItemLabel.contains("Идет запись"))
        XCTAssertTrue(tray.statusItemLabel.contains(update.bannerTitle))
        XCTAssertTrue(tray.statusItemLabel.contains("2026.09.08.1"))
        tray.showRecordingState(.idle)
        XCTAssertFalse(tray.statusItemLabel.contains("Идет запись"))
        XCTAssertTrue(tray.statusItemLabel.contains(update.bannerTitle))
    }

    func testNativeTrayMenuCommandsFollowCaptureStateAndRejectStaleActions() throws {
        let model = CalendarTrayModel { DesktopCalendarPromptResponse(events: []) }
        var starts = 0
        var stops = 0
        var settings = 0
        var quits = 0
        var mutes = 0
        var unmutes = 0
        let tray = CalendarTrayController(model: model, onOpenSettings: { settings += 1 }, onOpenMeetings: {},
                                          onStartRecording: { starts += 1 }, onStopRecording: { stops += 1 },
                                          onMuteMicrophone: { mutes += 1 }, onUnmuteMicrophone: { unmutes += 1 },
                                          onQuit: { quits += 1 })
        tray.rebuildMenu()
        XCTAssertEqual(tray.menu.items.filter { !$0.isSeparatorItem }.map(\.title),
                       ["Начать запись", "Перейти к уведомлению", "Последние уведомления",
                        "Открыть GRAF", "Настройки…", "Выйти из GRAF"])
        XCTAssertEqual(tray.menu.minimumWidth, 240)
        XCTAssertTrue(tray.menu.items.allSatisfy { $0.view == nil }, "Native rows retain keyboard, theme and outside-click behavior")
        tray.menu.performActionForItem(at: 0)
        XCTAssertEqual(starts, 1)
        XCTAssertEqual(GrafTrayRecordingState.resolve(sessionState: .starting, writerActive: false,
                                                     stopping: false, starting: true), .starting)
        for (state, title, hasAction) in [(GrafTrayRecordingState.starting, "Начинаем запись…", false),
                                          (.recording, "Остановить запись", true),
                                          (.paused, "Остановить запись", true),
                                          (.stopping, "Завершаем запись…", false)] {
            tray.showRecordingState(state)
            tray.rebuildMenu()
            let first = try XCTUnwrap(tray.menu.items.first)
            XCTAssertEqual(first.title, title)
            XCTAssertEqual(first.action != nil, hasAction)
            if hasAction {
                XCTAssertTrue(first.isEnabled, "Action rows must stay enabled")
            } else {
                XCTAssertFalse(first.isEnabled, "Informational rows must not be actionable")
                XCTAssertNotNil(first.attributedTitle, "Informational rows must keep a readable title")
            }
            tray.startRecording()
            XCTAssertEqual(starts, 1, "A queued stale Start must not invoke capture")
            if hasAction { tray.menu.performActionForItem(at: 0) }
        }
        XCTAssertEqual(stops, 2)
        for state in [GrafTrayRecordingState.idle, .starting, .recording, .paused, .stopping] {
            tray.showRecordingState(state)
            tray.rebuildMenu()
            let mute = tray.menu.items.first { $0.identifier?.rawValue == "graf.menu.mute" }
            let unmute = tray.menu.items.first { $0.identifier?.rawValue == "graf.menu.unmute" }
            XCTAssertEqual(mute != nil, state == .recording)
            XCTAssertEqual(unmute != nil, state == .paused)
            if let mute {
                XCTAssertEqual(mute.title, "Mute микрофона")
                XCTAssertTrue(mute.toolTip?.contains("Системный звук продолжает записываться") == true)
                let index = try XCTUnwrap(tray.menu.items.firstIndex(of: mute))
                tray.menu.performActionForItem(at: index)
            }
            if let unmute {
                XCTAssertEqual(unmute.title, "Включить микрофон")
                let index = try XCTUnwrap(tray.menu.items.firstIndex(of: unmute))
                tray.menu.performActionForItem(at: index)
            }
        }
        XCTAssertEqual(mutes, 1)
        XCTAssertEqual(unmutes, 1)
        tray.showRecordingState(.paused)
        tray.muteMicrophone()
        tray.showRecordingState(.recording)
        tray.unmuteMicrophone()
        tray.showRecordingState(.idle)
        tray.muteMicrophone()
        tray.unmuteMicrophone()
        XCTAssertEqual(mutes, 1, "Stale Mute cannot reverse a newer state")
        XCTAssertEqual(unmutes, 1, "Stale Unmute cannot enable a microphone outside paused capture")
        tray.showRecordingState(.idle)
        tray.stopRecording()
        XCTAssertEqual(stops, 2, "A queued stale Stop must not finalize an idle writer")
        let update = AppUpdatePresentation(phase: .available, availableVersion: "2026.09.08.1",
                                           isUserInitiated: false, message: nil)
        tray.showUpdate(update, actionEnabled: false)
        tray.rebuildMenu()
        let updateItem = try XCTUnwrap(tray.menu.items.first { $0.identifier?.rawValue == "graf.menu.update" })
        XCTAssertEqual(updateItem.title, update.menuItemTitle, "Tray and application menu share one command wording")
        XCTAssertEqual(updateItem.isEnabled, false)
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
                                          onStartRecording: {}, onStopRecording: {},
                                          onMuteMicrophone: {}, onUnmuteMicrophone: {}, onQuit: {})
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
                                          onStartRecording: {}, onStopRecording: {},
                                          onMuteMicrophone: {}, onUnmuteMicrophone: {}, onQuit: {})
            tray.rebuildMenu()
            let header = try XCTUnwrap(tray.menu.items.first { $0.identifier?.rawValue == "graf.menu.upcoming" })
            XCTAssertEqual(header.title, "Ближайшие встречи")
            XCTAssertNil(header.action)
            XCTAssertFalse(header.isEnabled, "A section header must not be actionable")
            XCTAssertEqual(
                try XCTUnwrap(header.attributedTitle).attribute(.foregroundColor, at: 0, effectiveRange: nil) as? NSColor,
                NSColor.secondaryLabelColor
            )
            let events = tray.menu.items.filter { $0.identifier?.rawValue == "graf.menu.event" }
            XCTAssertEqual(events.count, 3)
            XCTAssertEqual(events.map(\.isEnabled), [true, false, false])
            XCTAssertFalse(events.contains { ($0.toolTip ?? "").contains("Must stay private") })
            if showDetails {
                XCTAssertTrue(events[0].title.hasSuffix("…"))
                let truncated = try XCTUnwrap(events[0].title.components(separatedBy: " · ").last)
                let measured = (truncated as NSString).size(withAttributes: [.font: NSFont.menuFont(ofSize: 0)]).width
                XCTAssertLessThanOrEqual(measured, CalendarTrayController.menuTitleMaxWidth)
            } else {
                XCTAssertEqual(events.map(\.title), ["Встреча", "Встреча", "Встреча"])
                XCTAssertEqual(events.map(\.toolTip), ["Встреча", "Встреча", "Встреча"])
            }
        }
    }

    func testNativeTrayTruncatesTitlesByMeasuredWidthAndKeepsFullTextAvailable() async throws {
        let narrow = String(repeating: "i", count: 40)
        let wide = String(repeating: "Ш", count: 30)
        XCTAssertGreaterThan(narrow.count, 36, "A raw character count would have cut this title")
        XCTAssertLessThan(wide.count, 36, "A raw character count would have kept this title")

        let events = [
            makeEvent(eventId: "narrow", startsAt: date(120), endsAt: date(180), title: narrow),
            makeEvent(eventId: "wide", startsAt: date(240), endsAt: date(300), title: wide)
        ]
        let model = CalendarTrayModel {
            DesktopCalendarPromptResponse(
                events: events,
                showUpcomingTime: false,
                showUpcomingTitle: true
            )
        }
        await model.refresh()
        let tray = CalendarTrayController(model: model, onOpenSettings: {}, onOpenMeetings: {},
                                          onStartRecording: {}, onStopRecording: {},
                                          onMuteMicrophone: {}, onUnmuteMicrophone: {}, onQuit: {})
        tray.rebuildMenu()
        let items = tray.menu.items.filter { $0.identifier?.rawValue == "graf.menu.event" }
        XCTAssertEqual(items.count, 2)
        XCTAssertEqual(items[0].title, narrow, "Titles that fit the menu width are not cut")
        XCTAssertEqual(items[0].toolTip, narrow)
        XCTAssertTrue(items[1].title.hasSuffix("…"), "Wide titles are cut by measured width")
        XCTAssertEqual(items[1].toolTip, wide, "The full safe title stays in the tooltip")
        XCTAssertTrue(tray.statusItemLabel.contains(narrow), "The status item exposes the full next meeting title")
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

    private func assertCalendarFailure(
        _ error: any Error,
        projects expected: CalendarProjectionUpdate,
        invalidatesAuth: Bool,
        context: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) async {
        let loader = CalendarTrayControlledLoader()
        let model = CalendarTrayModel { try await loader.load() }
        let tray = CalendarTrayController(
            model: model, onOpenSettings: {}, onOpenMeetings: {},
            onStartRecording: {}, onStopRecording: {}, onMuteMicrophone: {},
            onUnmuteMicrophone: {}, onQuit: {}
        )
        var projections: [CalendarProjectionUpdate] = []
        var authInvalidations = 0
        model.onProjection = { projections.append($0) }
        model.onAuthInvalidated = { authInvalidations += 1 }
        model.recordingState = .recording
        let confirmed = DesktopCalendarPromptResponse(
            events: [makeEvent(eventId: "confirmed-before-error", startsAt: date(120), endsAt: date(180))]
        )
        let success = Task { await model.refresh() }
        await loader.waitForRequestCount(1)
        await loader.complete(request: 0, with: confirmed)
        await success.value
        XCTAssertEqual(projections, [.confirmed(confirmed)], context, file: file, line: line)
        XCTAssertEqual(model.events, confirmed.events, context, file: file, line: line)
        XCTAssertEqual(authInvalidations, 0, context, file: file, line: line)
        tray.rebuildMenu()
        XCTAssertEqual(tray.menu.items.filter { $0.identifier?.rawValue == "graf.menu.event" }.count,
                       1, "\(context): populate the real menu before failing", file: file, line: line)

        let failure = Task { await model.refresh() }
        await loader.waitForRequestCount(2)
        XCTAssertEqual(model.events, confirmed.events, "\(context): refresh has not completed", file: file, line: line)
        await loader.fail(request: 1, with: error)
        await failure.value

        XCTAssertEqual(projections, [.confirmed(confirmed), expected], context, file: file, line: line)
        XCTAssertEqual(authInvalidations, invalidatesAuth ? 1 : 0, context, file: file, line: line)
        XCTAssertTrue(model.events.isEmpty, "\(context): no stale calendar events after any error", file: file, line: line)
        XCTAssertEqual(model.recordingState, .recording, context, file: file, line: line)
        tray.rebuildMenu()
        XCTAssertFalse(tray.menu.items.contains { $0.identifier?.rawValue == "graf.menu.event" },
                       "\(context): no stale event commands in the real menu", file: file, line: line)
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

private enum CalendarProjectionTestError: Error {
    case unknown
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
