import AppKit
import Foundation
import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopLocalNotificationDeliveryTests: XCTestCase {
    func testF277CalendarRecoveryKeepsDeadlineAndEarlyEventEndWins() async throws {
        for offset in [0, 1, 5] {
            let f = try notificationFixture(self)
            let p = f.presenter()
            defer { p.dismissAllCards() }
            var prefs = p.preferences; prefs.offsetMinutes = offset; prefs.sound = true
            XCTAssertTrue(p.save(prefs))
            // End wins at offsets0/1; due+120 wins at offset5.
            let early = f.event(start: f.now.addingTimeInterval(Double(offset * 60)), duration: 30)
            let (tray, loader) = calendarPipeline(f, p, [early])
            await tray.refresh()
            let window = try XCTUnwrap(p.card.window)
            let deadline = try XCTUnwrap(p.card.deadline)
            XCTAssertEqual(deadline, min(f.now.addingTimeInterval(120), early.endsAt))
            f.now.addTimeInterval(5)
            await loader.setFailure(URLError(.timedOut)); await tray.refresh()
            XCTAssertTrue(p.card.window === window)
            var updated = early; updated.title = "Changed synthetic title"
            let future = f.event(id: "future", start: f.now.addingTimeInterval(Double(offset * 60) + 240))
            await loader.setResponse(f.calendar([updated, future])); await tray.refresh()
            XCTAssertTrue(p.card.window === window)
            XCTAssertEqual(p.card.deadline, deadline)
            XCTAssertFalse(p.card.presentedContent?.accessibilitySummary.contains("Changed synthetic") ?? true)
            XCTAssertEqual(f.sounds, 1)
            f.now = deadline; p.card.refresh()
            XCTAssertFalse(p.card.isVisible)
            XCTAssertTrue(f.actions.isEmpty)
            XCTAssertEqual(p.calendarEvents.count, 2, "A confirmed replacement is no longer retained error data")
            f.now = future.startsAt.addingTimeInterval(-Double(offset * 60))
            p.reconcileCard(now: f.now)
            XCTAssertTrue(p.card.isVisible, "Fresh future candidates must survive retirement of the old card")
        }
    }

    func testF277TemporaryCalendarFailureDropsUnshownAndQueuedCandidates() async throws {
        for behindPrompt in [false, true] {
            let f = try notificationFixture(self)
            let p = f.presenter()
            defer { p.dismissAllCards() }
            if behindPrompt { XCTAssertTrue(f.prompt(p)) }
            let event = f.event(start: f.now.addingTimeInterval(behindPrompt ? 60 : 120))
            let (tray, loader) = calendarPipeline(f, p, [event])
            await tray.refresh()
            await loader.setFailure(URLError(.notConnectedToInternet)); await tray.refresh()
            if behindPrompt { try notificationClose(p) }
            f.now.addTimeInterval(61); p.reconcileCard(now: f.now)
            XCTAssertFalse(p.card.isVisible, "No new reminder may come from the failed projection")
            XCTAssertTrue(f.actions.isEmpty)
        }
    }

    func testF277RetainedCalendarCardStillHonorsInvalidationAndNeverReplays() async throws {
        for reason in ["close", "preempt", "empty", "move", "link", "policy", "auth", "forbidden",
                       "unknown", "logout", "workspace", "quiet", "disabled", "recording", "lock"] {
            let f = try notificationFixture(self)
            let p = f.presenter()
            defer { p.dismissAllCards() }
            let event = f.event(start: f.now.addingTimeInterval(60))
            let (tray, loader) = calendarPipeline(f, p, [event])
            await tray.refresh()
            await loader.setFailure(URLError(.networkConnectionLost)); await tray.refresh()
            XCTAssertTrue(p.card.isVisible, reason)
            switch reason {
            case "close": try notificationClose(p)
            case "preempt":
                XCTAssertTrue(f.prompt(p)); try notificationClose(p)
            case "empty":
                await loader.setResponse(f.calendar([])); await tray.refresh()
            case "move":
                var moved = event; moved.startsAt.addTimeInterval(3600); moved.endsAt.addTimeInterval(3600)
                await loader.setResponse(f.calendar([moved])); await tray.refresh()
            case "link":
                var changed = event; changed.openMeetingURL = URL(string: "https://example.test/changed")
                await loader.setResponse(f.calendar([changed])); await tray.refresh()
            case "policy":
                var blocked = event; blocked.joinPromptState = .blockedByPolicy
                await loader.setResponse(f.calendar([blocked])); await tray.refresh()
            case "auth", "forbidden":
                await loader.setFailure(DesktopUploadClientError.httpStatus(reason == "auth" ? 401 : 403, "denied"))
                await tray.refresh(); XCTAssertTrue(p.owner.isEmpty)
            case "unknown":
                await loader.setFailure(DesktopUploadClientError.invalidResponse); await tray.refresh()
            case "logout": tray.invalidate()
            case "workspace": p.updateContext(user: "owner", workspace: "other")
            case "quiet": var prefs = p.preferences; prefs.quiet = true; XCTAssertTrue(p.save(prefs))
            case "disabled": var prefs = p.preferences; prefs.reminders = false; XCTAssertTrue(p.save(prefs))
            case "recording":
                var snapshot = DesktopControlSnapshot()
                snapshot.session = CaptureSession(id: "synthetic-active", mode: .audioRecording, state: .active,
                    sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
                    visibleIndicatorState: .active, stopActionAvailable: true,
                    bufferSummaryId: nil, startedAt: f.now, stoppedAt: nil)
                await p.updateSnapshot(snapshot)?.value
            case "lock": p.setPresentationBlocked(.lock, blocked: true)
            default: XCTFail("Uncovered reason")
            }
            XCTAssertFalse(p.card.isVisible, reason)
            if !["move", "link", "policy"].contains(reason) {
                XCTAssertTrue(p.calendarEvents.isEmpty, "Retained calendar data must be released on terminal state: \(reason)")
            }
            await loader.setFailure(URLError(.timedOut)); await tray.refresh()
            if reason == "lock" { p.setPresentationBlocked(.lock, blocked: false) }
            XCTAssertFalse(p.card.isVisible, reason)
            if !["logout", "workspace", "auth", "forbidden"].contains(reason) {
                await loader.setResponse(f.calendar([event])); await tray.refresh()
                XCTAssertFalse(p.card.isVisible, "Terminal occurrence cannot replay: \(reason)")
            }
            XCTAssertTrue(f.actions.isEmpty)
        }
    }

    func testF279NotificationJoinRetainsFailureAndRetriesWithoutStartingRecording() async throws {
        for joinAndRecord in [false, true] {
            let f = try notificationFixture(self)
            let p = f.presenter()
            defer { p.dismissAllCards() }
            let event = f.event(id: UUID().uuidString, start: f.now.addingTimeInterval(60))
            var pending: CheckedContinuation<Bool, Never>?
            var attempts = 0
            f.joinHandler = { id, current in
                XCTAssertEqual(id, event.eventId)
                attempts += 1
                let result = await withCheckedContinuation { pending = $0 }
                return current() && result
            }
            p.updateCalendar(f.calendar([event]))
            let title = joinAndRecord ? "Подключиться и начать запись" : "Подключиться"
            let button = try XCTUnwrap(notificationButtons(p.card.window?.contentView).first { $0.title == title })
            let deadline = p.card.deadline
            button.performClick(nil); button.performClick(nil)
            for _ in 0..<100 where pending == nil { await Task.yield() }
            XCTAssertNotNil(pending)
            XCTAssertEqual(attempts, 1)
            XCTAssertTrue(p.card.isVisible)
            XCTAssertTrue(f.actions.isEmpty)
            p.updateCalendar(f.calendar([event]))
            XCTAssertTrue(p.card.presentedContent?.accessibilitySummary.contains("Открываем") == true)
            XCTAssertEqual(p.card.deadline, deadline)
            pending?.resume(returning: false); pending = nil
            for _ in 0..<100 { await Task.yield() }
            XCTAssertTrue(p.card.isVisible)
            p.updateCalendar(f.calendar([event]))
            XCTAssertTrue(p.card.presentedContent?.accessibilitySummary.contains("Не удалось") == true)
            XCTAssertTrue(f.actions.isEmpty)
            let retry = try XCTUnwrap(notificationButtons(p.card.window?.contentView).first {
                $0.title == (joinAndRecord ? title : "Повторить подключение")
            })
            retry.performClick(nil)
            for _ in 0..<100 where pending == nil { await Task.yield() }
            XCTAssertNotNil(pending)
            pending?.resume(returning: true); pending = nil
            for _ in 0..<100 { await Task.yield() }
            XCTAssertEqual(attempts, 2)
            XCTAssertFalse(p.card.isVisible)
            XCTAssertEqual(f.actions, joinAndRecord ? [.start] : [])
        }
    }

    func testF279PendingNotificationJoinCancelsBeforeHandoffWhenCardBecomesStale() async throws {
        for reason in ["close", "deadline", "auth", "link", "cancelled", "lock", "superseded"] {
            let f = try notificationFixture(self)
            let p = f.presenter()
            defer { p.dismissAllCards() }
            var event = f.event(id: UUID().uuidString, start: f.now.addingTimeInterval(60))
            var pending: CheckedContinuation<Void, Never>?
            var handoffs = 0
            f.joinHandler = { id, current in
                await CalendarMeetingOpener.resolveAndOpen(eventID: UUID(uuidString: id)!, resolve: { _ in
                    await withCheckedContinuation { pending = $0 }
                    return URL(string: "https://meet.google.com/fresh")!
                }, isCurrent: current, open: { _ in handoffs += 1; return true })
            }
            p.updateCalendar(f.calendar([event]))
            let button = try XCTUnwrap(notificationButtons(p.card.window?.contentView).first { $0.title == "Подключиться и начать запись" })
            button.performClick(nil)
            for _ in 0..<100 where pending == nil { await Task.yield() }
            XCTAssertNotNil(pending)
            switch reason {
            case "close": try notificationClose(p)
            case "deadline": f.now = try XCTUnwrap(p.card.deadline); p.reconcileCard(now: f.now)
            case "auth": p.invalidate()
            case "link": event.openMeetingURL = nil; event.meetingLinkPresent = false; p.updateCalendar(f.calendar([event]))
            case "cancelled": p.updateCalendar(f.calendar([]))
            case "lock": p.setPresentationBlocked(.lock, blocked: true)
            default: _ = p.presentRecordingPrompt(displayName: "Synthetic", onStart: {}, onDismiss: {}, onRememberChoiceChanged: { _ in })
            }
            pending?.resume(); pending = nil
            for _ in 0..<100 { await Task.yield() }
            XCTAssertEqual(handoffs, 0, reason)
            XCTAssertTrue(f.actions.isEmpty, reason)
        }
    }

    func testF277RetainedCalendarActionsAreSingleUseAndRejectStaleButtons() async throws {
        for title in ["Подключиться", "Подключиться и начать запись", "Начать запись"] {
            for invalidation in ["none", "deadline", "context", "link"] {
                let f = try notificationFixture(self)
                let p = f.presenter()
                defer { p.dismissAllCards() }
                var event = f.event(start: f.now.addingTimeInterval(60))
                if title == "Начать запись" { event.meetingLinkPresent = false; event.openMeetingURL = nil }
                let (tray, loader) = calendarPipeline(f, p, [event])
                await tray.refresh()
                let button = try XCTUnwrap(notificationButtons(p.card.window?.contentView).first { $0.title == title })
                let deadline = try XCTUnwrap(p.card.deadline)
                await loader.setFailure(URLError(.timedOut)); await tray.refresh()
                XCTAssertTrue(p.card.isVisible)
                switch invalidation {
                case "deadline": f.now = deadline
                case "context": p.invalidate()
                case "link":
                    var changed = event; changed.openMeetingURL = URL(string: "javascript:alert(1)")
                    await loader.setResponse(f.calendar([changed])); await tray.refresh()
                default: f.now = deadline.addingTimeInterval(-0.001)
                }
                button.performClick(nil); button.performClick(nil)
                for _ in 0..<20 { await Task.yield() }
                if invalidation != "link" {
                    XCTAssertTrue(p.calendarEvents.isEmpty, "Retained data must be released after action or expiry")
                }
                XCTAssertEqual(f.actions, invalidation == "none" && title != "Подключиться" ? [.start] : [])
                XCTAssertEqual(f.openedEventIDs, invalidation == "none" && title != "Начать запись" ? [event.eventId] : [])
                XCTAssertFalse(p.card.isVisible)
            }
        }
    }

    func testF277TemporaryCalendarFailureKeepsVisibleCardUntilOriginalDeadline() async throws {
        for offset in [0, 1, 5] {
            let f = try notificationFixture(self)
            let p = f.presenter()
            defer { p.dismissAllCards() }
            var prefs = p.preferences; prefs.offsetMinutes = offset; prefs.sound = true
            XCTAssertTrue(p.save(prefs))
            let event = f.event(start: f.now.addingTimeInterval(Double(offset * 60)))
            let loader = NotificationCalendarLoader(response: f.calendar([event]))
            let tray = CalendarTrayModel { try await loader.load() }
            tray.onProjection = { p.updateCalendarProjection($0) }
            await tray.refresh()
            let window = try XCTUnwrap(p.card.window)
            let deadline = try XCTUnwrap(p.card.deadline)
            XCTAssertEqual(deadline, f.now.addingTimeInterval(120))
            for error in [DesktopUploadClientError.httpStatus(503, "unavailable") as any Error,
                          URLError(.notConnectedToInternet)] {
                f.now.addTimeInterval(10)
                await loader.setFailure(error)
                await tray.refresh()
                XCTAssertTrue(tray.events.isEmpty)
                XCTAssertTrue(p.card.isVisible, "A temporary fetch failure must preserve the visible reminder")
                XCTAssertTrue(p.card.window === window)
                XCTAssertEqual(p.card.deadline, deadline)
                XCTAssertEqual(f.sounds, 1)
            }
            f.now = deadline.addingTimeInterval(-0.001)
            p.card.refresh()
            XCTAssertTrue(p.card.isVisible)
            f.now = deadline
            p.card.refresh()
            XCTAssertFalse(p.card.isVisible)
            XCTAssertTrue(p.calendarEvents.isEmpty, "Do not retain failed-refresh data beyond the original deadline")
            await loader.setResponse(f.calendar([event]))
            await tray.refresh()
            XCTAssertFalse(p.card.isVisible)
            XCTAssertEqual(f.sounds, 1)
            XCTAssertTrue(f.actions.isEmpty)
        }
    }

    func testOwnedFreshServerAcceptedItemsStaySilentAndLocalBlockedActionOnlyOpensRecording() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var prefs = p.preferences; prefs.sound = true
        XCTAssertTrue(p.save(prefs))
        let retentionDeadline = f.now.addingTimeInterval(7 * 86_400)
        let accepted = custodyFixtureQueueItem(id: "accepted", state: .uploaded, retryMode: .terminal,
            meetingId: "server-accepted", retentionDeadline: retentionDeadline, updatedAt: f.now)
        let processed = custodyFixtureQueueItem(id: "processed", state: .uploaded, retryMode: .terminal,
            serverTruth: ServerTruthFingerprint(meetingId: "server-processed", processingStatus: "processed",
                finalizedAt: f.now), retentionDeadline: retentionDeadline, updatedAt: f.now)
        var blocked = custodyFixtureQueueItem(id: "blocked-local", state: .blocked, retryMode: .manualOnly,
            failureCategory: .localResource, failureReason: "local_recording_package_not_uploadable",
            retentionDeadline: retentionDeadline, updatedAt: f.now)
        blocked.artifactProfile = custodyFixtureProfile(uploadable: false)
        let custody = DesktopUploadCustodyProjection(item: blocked, now: f.now)
        XCTAssertEqual(custody.custodyState, .cannotSend)
        XCTAssertTrue(custody.requiresUserAttention)
        let items = [accepted, processed, blocked]
        XCTAssertEqual(Set(items.map(\.sessionId)).count, 3)
        for item in items {
            f.bind(item)
            XCTAssertTrue(f.store.ownsSession(item.sessionId, context: "owner:workspace"))
            XCTAssertEqual(item.updatedAt, f.now, "Silence must not depend on stale or foreign items")
            XCTAssertGreaterThan(item.retentionDeadline, f.now, "This is not a retention-expiry incident")
        }

        let serverOnly = f.snapshot([accepted, processed])
        f.model.update(serverOnly)
        await p.updateSnapshot(serverOnly)?.value
        XCTAssertNil(p.card.presentedContent)
        XCTAssertTrue(p.history.isEmpty)
        XCTAssertEqual(f.sounds, 0)
        XCTAssertTrue(f.actions.isEmpty)
        XCTAssertEqual(f.model.snapshot, serverOnly)

        let mixed = f.snapshot(items)
        f.model.update(mixed)
        await p.updateSnapshot(mixed)?.value
        guard case let .problem(_, _, _, sessionID) = p.card.presentedContent else {
            return XCTFail("The fresh owned local package failure must produce a real problem card")
        }
        XCTAssertEqual(sessionID, blocked.sessionId)
        XCTAssertEqual(p.history.map(\.kind), [.problem])
        XCTAssertEqual(f.sounds, 1)
        XCTAssertEqual(f.model.snapshot, mixed)
        let button = try XCTUnwrap(notificationButtons(p.card.window?.contentView)
            .first { $0.title == "Открыть запись" })
        button.performClick(nil)
        XCTAssertEqual(f.actions, [.localRecording(blocked.sessionId)],
                       "Navigation must not send start/stop or another capture command")
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(p.history.map(\.kind), [.problem])
        XCTAssertEqual(f.sounds, 1)
        XCTAssertEqual(f.model.snapshot, mixed, "Opening the recording must not mutate capture state")
    }

    func testF277MeetingReceiptTTLEndExtensionAfterCloseDoesNotRepeatInSamePresenter() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var prefs = p.preferences; prefs.offsetMinutes = 0; prefs.sound = true
        XCTAssertTrue(p.save(prefs))
        var event = f.event(start: f.now, duration: 30)
        p.updateCalendar(f.calendar([event]))
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.meeting")
        XCTAssertEqual(f.sounds, 1)
        try notificationClose(p)
        XCTAssertNil(p.card.presentedContent)

        f.now = event.startsAt.addingTimeInterval(40)
        event.endsAt = event.startsAt.addingTimeInterval(3600)
        p.updateCalendar(f.calendar([event]))
        XCTAssertNil(p.card.presentedContent, "Extending only endsAt cannot revive the closed occurrence")
        XCTAssertEqual(f.sounds, 1, "The receipt must outlive the original short meeting end")
    }

    func testF277MeetingReceiptTTLEndExtensionAfterCloseDoesNotRepeatAfterRestart() throws {
        let f = try notificationFixture(self)
        var first: DesktopNotificationPresenter? = f.presenter()
        var prefs = try XCTUnwrap(first).preferences; prefs.offsetMinutes = 0; prefs.sound = true
        XCTAssertTrue(try XCTUnwrap(first).save(prefs))
        var event = f.event(start: f.now, duration: 30)
        first?.updateCalendar(f.calendar([event]))
        XCTAssertEqual(first?.card.presentedContent?.identifier, "graf.card.meeting")
        XCTAssertEqual(f.sounds, 1)
        try notificationClose(XCTUnwrap(first))
        XCTAssertNil(first?.card.presentedContent)
        first = nil

        f.now = event.startsAt.addingTimeInterval(40)
        event.endsAt = event.startsAt.addingTimeInterval(3600)
        let restored = f.presenter(restoredStore: true)
        defer { restored.dismissAllCards() }
        restored.updateCalendar(f.calendar([event]))
        XCTAssertNil(restored.card.presentedContent, "Restart and an extended end keep the same event/start consumed")
        XCTAssertEqual(f.sounds, 1, "The persisted receipt must outlive the original short meeting end")
    }

    func testF277MeetingClaimCloseThenRestartDoesNotShowOrSoundAgain() throws {
        let f = try notificationFixture(self)
        let first = f.presenter()
        let event = f.event(start: f.now.addingTimeInterval(60))
        var prefs = first.preferences; prefs.sound = true
        XCTAssertTrue(first.save(prefs))
        first.updateCalendar(f.calendar([event]))
        XCTAssertEqual(first.card.presentedContent?.identifier, "graf.card.meeting")
        XCTAssertEqual(f.sounds, 1)
        try notificationClose(first)
        let restored = f.presenter(restoredStore: true)
        defer { first.dismissAllCards(); restored.dismissAllCards() }
        restored.updateCalendar(f.calendar([event]))
        XCTAssertNil(restored.card.presentedContent, "Closing survives a new presenter and preferences store")
        XCTAssertEqual(f.sounds, 1, "A consumed occurrence cannot sound after restart")
    }

    func testF277MeetingClaimRestartWhileOpenDoesNotShowOrSoundAgain() throws {
        let f = try notificationFixture(self)
        var first: DesktopNotificationPresenter? = f.presenter()
        let event = f.event(start: f.now.addingTimeInterval(60))
        var prefs = try XCTUnwrap(first).preferences; prefs.sound = true
        XCTAssertTrue(try XCTUnwrap(first).save(prefs))
        first?.updateCalendar(f.calendar([event]))
        XCTAssertEqual(first?.card.presentedContent?.identifier, "graf.card.meeting")
        XCTAssertEqual(f.sounds, 1)
        // Tear down the native surface without a close/expire/terminal callback.
        // A receipt written only by retire() would miss this restart.
        first?.card.dismiss()
        first = nil
        let restored = f.presenter(restoredStore: true)
        defer { restored.dismissAllCards() }
        restored.updateCalendar(f.calendar([event]))
        XCTAssertNil(restored.card.presentedContent)
        XCTAssertEqual(f.sounds, 1)
    }

    func testF277MeetingClaimDeliveredLegacyStableAndStartAliasPreventPopup() throws {
        for includesStart in [false, true] {
            for hasPastReservation in [false, true] {
                let f = try notificationFixture(self)
                let event = f.event(start: f.now.addingTimeInterval(60))
                let digest = f.legacyMeetingDigest(event, includesStart: includesStart)
                f.seedLegacyMeetingClaim(digest,
                    scheduledFor: hasPastReservation ? f.now.addingTimeInterval(-1) : nil)
                var prefs = DesktopNotificationPreferences(); prefs.sound = true
                try f.store.save(prefs, owner: "owner")
                let restored = f.presenter(restoredStore: true)
                defer { restored.dismissAllCards() }
                restored.updateCalendar(f.calendar([event]))
                XCTAssertNil(restored.card.presentedContent,
                             "Delivered legacy claim must suppress before showing; includesStart=\(includesStart)")
                XCTAssertEqual(f.sounds, 0)
                restored.dismissAllCards()
                let second = f.presenter(restoredStore: true)
                defer { second.dismissAllCards() }
                second.updateCalendar(f.calendar([event]))
                XCTAssertNil(second.card.presentedContent, "One-way migration must survive another restart")
                XCTAssertEqual(f.sounds, 0)
            }
        }
    }

    func testF277MeetingClaimCancelledFutureReservationRemainsEligibleAfterItsOldDueTime() throws {
        let f = try notificationFixture(self)
        let retiredAt = f.now
        let event = f.event(start: retiredAt.addingTimeInterval(60))
        let oldDue = event.startsAt // Previous offset zero; current setting is one minute.
        for includesStart in [false, true] {
            f.seedLegacyMeetingClaim(f.legacyMeetingDigest(event, includesStart: includesStart), scheduledFor: oldDue)
        }
        var prefs = DesktopNotificationPreferences(); prefs.sound = true
        try f.store.save(prefs, owner: "owner")
        // First upgrade retires OS scheduling, but the calendar arrives later.
        let initial = f.presenter()
        initial.dismissAllCards()
        f.now = retiredAt.addingTimeInterval(70)
        let restored = f.presenter(restoredStore: true)
        defer { restored.dismissAllCards() }
        restored.updateCalendar(f.calendar([event]))
        XCTAssertEqual(restored.card.presentedContent?.identifier, "graf.card.meeting",
                       "Compare reservation due with retirement time, not delayed calendar arrival")
        XCTAssertEqual(f.sounds, 1)
        f.now = retiredAt.addingTimeInterval(120)
        restored.reconcileCard(now: f.now)
        XCTAssertNil(restored.card.presentedContent, "Migration cannot reset the absolute deadline")
    }

    func testF277MeetingClaimDeliveredAliasDominatesFutureReservationForOtherAlias() throws {
        let f = try notificationFixture(self)
        let event = f.event(start: f.now.addingTimeInterval(60))
        f.seedLegacyMeetingClaim(f.legacyMeetingDigest(event, includesStart: false),
                                 scheduledFor: event.startsAt)
        f.seedLegacyMeetingClaim(f.legacyMeetingDigest(event, includesStart: true), scheduledFor: nil)
        let restored = f.presenter()
        defer { restored.dismissAllCards() }
        restored.updateCalendar(f.calendar([event]))
        XCTAssertNil(restored.card.presentedContent,
                     "A future reservation cannot override another consumed legacy key")
        XCTAssertEqual(f.sounds, 0)
    }

    func testMeetingMigrationCutoverPrecedesDelayedOwnerAndCalendar() throws {
        let f = try notificationFixture(self)
        let event = f.event(start: f.now.addingTimeInterval(60))
        f.seedLegacyMeetingClaim(f.legacyMeetingDigest(event, includesStart: false), scheduledFor: event.startsAt)
        let p = f.presenter(user: "", workspace: "")
        defer { p.dismissAllCards() }
        f.now = f.now.addingTimeInterval(70)
        p.updateContext(user: "owner", workspace: "workspace")
        p.updateCalendar(f.calendar([event]))
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.meeting",
                       "Use initialization/OS-retirement time, not the first confirmed owner")
    }

    func testF277MeetingClaimReservationDueExactlyAtRetirementIsAlreadyConsumed() throws {
        let f = try notificationFixture(self)
        let event = f.event(start: f.now.addingTimeInterval(60))
        f.seedLegacyMeetingClaim(f.legacyMeetingDigest(event, includesStart: false), scheduledFor: f.now)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        p.updateCalendar(f.calendar([event]))
        XCTAssertNil(p.card.presentedContent, "Only scheduledFor strictly after retirement is an unused reservation")
        XCTAssertEqual(f.sounds, 0)
    }

    func testF277MeetingClaimContextIsolationAndReturnToOriginalContext() throws {
        let f = try notificationFixture(self)
        let event = f.event(start: f.now.addingTimeInterval(60))
        for (user, workspace, origin) in [
            ("owner", "workspace", "https://one.test"),
            ("owner", "different-workspace", "https://one.test"),
            ("different-owner", "workspace", "https://one.test"),
            ("owner", "workspace", "https://two.test")
        ] {
            let p = f.presenter(restoredStore: true, user: user, workspace: workspace, serverOrigin: origin)
            defer { p.dismissAllCards() }
            var response = f.calendar([event])
            response.notificationOwnerID = user; response.notificationWorkspaceID = workspace
            p.updateCalendar(response)
            XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.meeting",
                           "Claims must be isolated by account, workspace and server origin")
            try notificationClose(p)
        }
        let original = f.presenter(restoredStore: true, serverOrigin: "https://one.test")
        defer { original.dismissAllCards() }
        original.updateCalendar(f.calendar([event]))
        XCTAssertNil(original.card.presentedContent, "Returning to the consumed context does not forget its claim")
    }

    func testF277MeetingClaimNewStartIsNewOccurrenceButOriginalStaysConsumed() throws {
        let f = try notificationFixture(self)
        let originalEvent = f.event(start: f.now.addingTimeInterval(60))
        let first = f.presenter()
        first.updateCalendar(f.calendar([originalEvent]))
        try notificationClose(first)
        var moved = originalEvent
        moved.startsAt = originalEvent.startsAt.addingTimeInterval(30)
        moved.endsAt = originalEvent.endsAt.addingTimeInterval(30)
        f.now = f.now.addingTimeInterval(30)
        let restored = f.presenter(restoredStore: true)
        defer { first.dismissAllCards(); restored.dismissAllCards() }
        restored.updateCalendar(f.calendar([moved]))
        XCTAssertEqual(restored.card.presentedContent?.identifier, "graf.card.meeting")
        try notificationClose(restored)
        let third = f.presenter(restoredStore: true)
        defer { third.dismissAllCards() }
        third.updateCalendar(f.calendar([originalEvent]))
        XCTAssertNil(third.card.presentedContent)
        third.updateCalendar(f.calendar([moved]))
        XCTAssertNil(third.card.presentedContent)
    }

    func testF277SelectedOffsetsDriveTheCustomCardAndAbsoluteDeadline() throws {
        for offset in [0, 1, 5] {
            let f = try notificationFixture(self)
            let presenter = f.presenter()
            defer { presenter.dismissAllCards() }
            var prefs = presenter.preferences; prefs.offsetMinutes = offset
            XCTAssertTrue(presenter.save(prefs))
            let due = f.now.addingTimeInterval(600)
            let event = f.event(start: due.addingTimeInterval(Double(offset * 60)))
            presenter.updateCalendar(f.calendar([event]))
            f.now = due.addingTimeInterval(-1); presenter.reconcileCard(now: f.now)
            XCTAssertNil(presenter.card.presentedContent)
            f.now = due; presenter.reconcileCard(now: f.now)
            XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.meeting")
            let window = presenter.card.window
            f.now = due.addingTimeInterval(119)
            presenter.updateCalendar(f.calendar([event]))
            XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.meeting")
            XCTAssertTrue(presenter.card.window === window)
            f.now = due.addingTimeInterval(120); presenter.reconcileCard(now: f.now)
            XCTAssertNil(presenter.card.presentedContent)
        }
    }

    func testF277MeetingEndCapsTheSelectedOffsetWindow() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var prefs = p.preferences; prefs.offsetMinutes = 0
        XCTAssertTrue(p.save(prefs))
        let event = f.event(start: f.now, duration: 30)
        p.updateCalendar(f.calendar([event]))
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.meeting")
        f.now = event.endsAt; p.reconcileCard(now: f.now)
        XCTAssertNil(p.card.presentedContent)
    }

    func testF277ProblemCannotDisplaceRecordingPromptAndWinsAfterPromptCloses() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        XCTAssertTrue(f.prompt(p))
        let panel = p.card.window
        let item = f.item(); f.bind(item)
        await p.updateSnapshot(f.snapshot([item]))?.value
        p.updateCalendar(f.calendar([f.event(start: f.now.addingTimeInterval(60))]))
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.recording-prompt")
        XCTAssertTrue(p.card.window === panel)
        XCTAssertFalse(p.presentPreview(title: "Проверка", message: "Проверка"))
        try notificationClose(p)
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.problem")
        try notificationClose(p)
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.meeting")
    }

    func testF277RecordingPromptCanDisplaceProblemWithoutResurrectingIt() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let item = f.item(); f.bind(item)
        await p.updateSnapshot(f.snapshot([item]))?.value
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.problem")
        XCTAssertTrue(f.prompt(p))
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.recording-prompt")
        try notificationClose(p)
        await p.refreshLocal(f.snapshot([item]))
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(p.history.map(\.kind), [.problem])
    }

    func testF277ClaimedIncidentIsRejectedBeforeAnyCardAppears() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let item = f.item(); f.bind(item)
        let snapshot = f.snapshot([item])
        let incident = try XCTUnwrap(DesktopLocalNotificationIncident.incidents(in: snapshot, now: f.now).first)
        XCTAssertTrue(f.store.claimLocalIncident(incident, owner: "owner", now: f.now))
        await p.updateSnapshot(snapshot)?.value
        XCTAssertNil(p.card.presentedContent)
        XCTAssertTrue(p.history.isEmpty)
        XCTAssertEqual(f.sounds, 0)
    }

    func testF277SamePriorityDifferentProblemDoesNotReplaceVisibleOne() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let first = f.item(id: "first"), second = f.item(id: "second")
        f.bind(first); f.bind(second)
        await p.updateSnapshot(f.snapshot([first]))?.value
        let content = try XCTUnwrap(p.card.presentedContent)
        let panel = p.card.window
        await p.updateSnapshot(f.snapshot([second, first]))?.value
        XCTAssertEqual(p.card.presentedContent, content)
        XCTAssertTrue(p.card.window === panel)
        try notificationClose(p)
        guard case let .problem(_, _, _, sessionID) = p.card.presentedContent else { return XCTFail("Next problem missing") }
        XCTAssertEqual(sessionID, second.sessionId)
    }

    func testF277QuietSuppressesOptionalProblemButKeepsRecordingPrompt() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var prefs = p.preferences; prefs.quiet = true; prefs.sound = true
        XCTAssertTrue(p.save(prefs))
        let item = f.item(); f.bind(item)
        await p.updateSnapshot(f.snapshot([item]))?.value
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(p.history.map(\.kind), [.problem])
        XCTAssertTrue(f.prompt(p))
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.recording-prompt")
        XCTAssertEqual(f.sounds, 0)
    }

    func testOnlyNewestShortResultWaitsBehindPromptAndAllResultsEnterHistory() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        XCTAssertTrue(f.prompt(p))
        XCTAssertFalse(p.presentShortRecording())
        f.now = f.now.addingTimeInterval(1)
        XCTAssertFalse(p.presentShortRecording())
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.recording-prompt")
        try notificationClose(p)
        XCTAssertEqual(p.card.presentedContent, .shortRecording)
        f.now = f.now.addingTimeInterval(19.999); p.card.refresh()
        XCTAssertEqual(p.card.presentedContent, .shortRecording)
        f.now = f.now.addingTimeInterval(0.001); p.card.refresh()
        XCTAssertNil(p.card.presentedContent)
        p.reconcileCard(now: f.now)
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(p.history.count, 2)
    }

    func testNewestShortSurvivesOlderCandidatesWaitingDeadlineAndDoesNotReplay() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let arrival = f.now
        let problem = f.item(); f.bind(problem)
        await p.updateSnapshot(f.snapshot([problem]))?.value
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.problem")
        XCTAssertFalse(p.presentShortRecording())
        f.now = arrival.addingTimeInterval(1)
        XCTAssertFalse(p.presentShortRecording())
        // The first result's waiting window has ended; only the second is fresh.
        f.now = arrival.addingTimeInterval(20.5)
        p.card.refresh()
        XCTAssertEqual(p.card.presentedContent, .shortRecording)
        try notificationClose(p)
        p.reconcileCard(now: f.now)
        XCTAssertNil(p.card.presentedContent)
        f.now = arrival.addingTimeInterval(60); p.card.refresh(); p.reconcileCard(now: f.now)
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(p.history.map(\.kind), [.shortRecording, .shortRecording, .problem])
    }

    func testPendingShortReconciliationDoesNotExtendOriginalWaitingWindow() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let arrival = f.now
        let problem = f.item(); f.bind(problem)
        await p.updateSnapshot(f.snapshot([problem]))?.value
        XCTAssertFalse(p.presentShortRecording())
        for second in 1...19 {
            f.now = arrival.addingTimeInterval(Double(second))
            p.reconcileCard(now: f.now)
            XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.problem")
        }
        f.now = arrival.addingTimeInterval(20); p.card.refresh()
        XCTAssertNil(p.card.presentedContent)
        p.reconcileCard(now: f.now)
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(p.history.map(\.kind), [.shortRecording, .problem])
    }

    func testPreviewExpiresAtSixSecondsWithoutHistoryOrReplay() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let arrival = f.now
        XCTAssertTrue(p.presentPreview(title: "Проверка", message: "Сообщение"))
        f.now = arrival.addingTimeInterval(5.999); p.card.refresh()
        XCTAssertEqual(p.card.presentedContent, .preview(title: "Проверка", message: "Сообщение"))
        f.now = arrival.addingTimeInterval(6); p.card.refresh()
        XCTAssertNil(p.card.presentedContent)
        p.reconcileCard(now: f.now)
        XCTAssertNil(p.card.presentedContent)
        XCTAssertTrue(p.history.isEmpty)
    }

    func testUnshownShortExpiresTwentySecondsAfterArrival() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        XCTAssertTrue(f.prompt(p))
        XCTAssertFalse(p.presentShortRecording())
        f.now = f.now.addingTimeInterval(20)
        p.reconcileCard(now: f.now)
        try notificationClose(p)
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(p.history.count, 1)
    }

    func testDisplacedMeetingDoesNotReturnAfterProblemOrOffsetChange() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let event = f.event(start: f.now.addingTimeInterval(60))
        p.updateCalendar(f.calendar([event]))
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.meeting")
        let item = f.item(); f.bind(item)
        await p.updateSnapshot(f.snapshot([item]))?.value
        XCTAssertEqual(p.card.presentedContent?.identifier, "graf.card.problem")
        try notificationClose(p)
        p.updateCalendar(f.calendar([event]))
        XCTAssertNil(p.card.presentedContent)
        var prefs = p.preferences; prefs.offsetMinutes = 0
        XCTAssertTrue(p.save(prefs))
        f.now = event.startsAt; p.reconcileCard(now: f.now)
        XCTAssertNil(p.card.presentedContent)
    }

    func testFreshProblemsUseEventTimeThenStableIdentityOrder() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        XCTAssertTrue(f.prompt(p))
        let late = f.item(id: "a", at: f.now), early = f.item(id: "z", at: f.now.addingTimeInterval(-10))
        f.bind(late); f.bind(early)
        await p.updateSnapshot(f.snapshot([late, early]))?.value
        try notificationClose(p)
        guard case let .problem(_, _, _, id) = p.card.presentedContent else { return XCTFail("Missing problem") }
        XCTAssertEqual(id, early.sessionId)
    }

    func testSoundOnlyOncePerActualOptionalPresentation() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var prefs = p.preferences; prefs.sound = true
        XCTAssertTrue(p.save(prefs))
        let event = f.event(start: f.now.addingTimeInterval(60))
        p.updateCalendar(f.calendar([event]))
        XCTAssertEqual(f.sounds, 1)
        for _ in 0..<4 { p.updateCalendar(f.calendar([event])); p.card.refresh() }
        XCTAssertEqual(f.sounds, 1)
        try notificationClose(p)
        await p.testNotification()
        XCTAssertEqual(f.sounds, 1)
        XCTAssertTrue(p.history.isEmpty)
    }

    func testMissingScreenFailsPromptAndCancelsWithoutInvisibleExpiry() throws {
        let f = try notificationFixture(self, requiresScreen: false)
        let p = f.presenter(screens: [])
        var expired = 0, invalidated = 0
        XCTAssertFalse(p.presentRecordingPrompt(displayName: "Zoom",
            onStart: { XCTFail("Invisible start") }, onDismiss: {}, onRememberChoiceChanged: { _ in },
            onExpire: { expired += 1 }, onInvalidated: { invalidated += 1 }))
        f.now = f.now.addingTimeInterval(9); p.card.refresh()
        XCTAssertEqual(expired, 0); XCTAssertEqual(invalidated, 1)
        XCTAssertNil(p.card.presentedContent)
    }

    func testLifecycleBlocksAreIndependentAndCancelBeforeCallback() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var cancelled = 0, expired = 0
        XCTAssertTrue(p.presentRecordingPrompt(displayName: "Zoom",
            onStart: {}, onDismiss: {}, onRememberChoiceChanged: { _ in }, onExpire: { expired += 1 },
            onInvalidated: {
                cancelled += 1
                XCTAssertFalse(p.isPresentationAvailable)
                XCTAssertFalse(f.prompt(p))
            }))
        let epoch = p.presentationEpoch
        p.setPresentationBlocked(.sleep, blocked: true)
        p.setPresentationBlocked(.lock, blocked: true)
        XCTAssertGreaterThan(p.presentationEpoch, epoch)
        XCTAssertEqual(cancelled, 1)
        p.setPresentationBlocked(.sleep, blocked: false)
        XCTAssertFalse(p.isPresentationAvailable)
        f.now = f.now.addingTimeInterval(60); p.card.refresh()
        p.setPresentationBlocked(.lock, blocked: false)
        XCTAssertTrue(p.isPresentationAvailable)
        XCTAssertNil(p.card.presentedContent)
        XCTAssertEqual(expired, 0)
    }

    func testLongGapInvalidatesPromptWithoutExpiry() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var invalidated = 0, expires = 0
        XCTAssertTrue(p.presentRecordingPrompt(displayName: "Zoom",
            onStart: {}, onDismiss: {}, onRememberChoiceChanged: { _ in },
            onExpire: { expires += 1 }, onInvalidated: { invalidated += 1 }))
        f.now = f.now.addingTimeInterval(60); p.card.refresh()
        XCTAssertEqual(invalidated, 1); XCTAssertEqual(expires, 0)
        XCTAssertNil(p.card.presentedContent)
    }

    func testPromptExpiresOnceAfterEightVisibleTicksAndNeverRemembersOnTimeout() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var expires = 0, remembers = 0, skips = 0
        XCTAssertTrue(p.presentRecordingPrompt(displayName: "Zoom", rememberChoice: true,
            onStart: { XCTFail("Explicit start") }, onDismiss: {}, onRememberChoiceChanged: { _ in remembers += 1 },
            onExpire: { expires += 1 }, onSkip: { _ in skips += 1 }))
        for _ in 1...9 { f.now = f.now.addingTimeInterval(1); p.card.refresh() }
        XCTAssertEqual(expires, 1); XCTAssertEqual(remembers, 0); XCTAssertEqual(skips, 0)
        XCTAssertNil(p.card.presentedContent)
    }

    func testCurrentCheckboxValueReachesSkipButCloseNeverSaves() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var choices: [Bool] = [], skips: [Bool] = [], closes = 0
        XCTAssertTrue(p.presentRecordingPrompt(displayName: "Zoom",
            onStart: {}, onDismiss: { closes += 1 }, onRememberChoiceChanged: { choices.append($0) },
            onSkip: { skips.append($0) }))
        let checkbox = try XCTUnwrap(notificationButtons(p.card.window?.contentView).first { $0.title.contains("Запомнить") })
        checkbox.performClick(nil)
        let skip = try XCTUnwrap(notificationButtons(p.card.window?.contentView).first { $0.title == "Не записывать" })
        skip.performClick(nil); skip.performClick(nil)
        XCTAssertEqual(choices, [true]); XCTAssertEqual(skips, [true]); XCTAssertEqual(closes, 0)
        XCTAssertTrue(p.presentRecordingPrompt(displayName: "Zoom", rememberChoice: true,
            onStart: {}, onDismiss: { closes += 1 }, onRememberChoiceChanged: { choices.append($0) },
            onSkip: { skips.append($0) }))
        try notificationClose(p)
        XCTAssertEqual(closes, 1); XCTAssertEqual(skips, [true])
    }

    func testChangedLinkAndContextMakeRetainedOldButtonsHarmless() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var event = f.event(start: f.now.addingTimeInterval(60))
        p.updateCalendar(f.calendar([event]))
        let oldButtons = notificationButtons(p.card.window?.contentView)
        event.openMeetingURL = URL(string: "https://example.test/changed")
        p.updateCalendar(f.calendar([event]))
        for button in oldButtons { button.performClick(nil) }
        XCTAssertTrue(f.actions.isEmpty)
        let epoch = p.presentationEpoch
        p.updateContext(user: "other", workspace: "workspace")
        XCTAssertGreaterThan(p.presentationEpoch, epoch)
        for button in oldButtons { button.performClick(nil) }
        XCTAssertTrue(f.actions.isEmpty)
    }

    func testForeignAndHistoricalProblemsNeverHideCurrentOwnedFailure() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let foreign = f.item(id: "foreign"), old = f.item(id: "old", at: f.now.addingTimeInterval(-3600)), own = f.item()
        f.store.bindSession(foreign.sessionId, context: "other:workspace")
        f.bind(old); f.bind(own)
        await p.updateSnapshot(f.snapshot([foreign, old, own]))?.value
        guard case let .problem(_, _, _, id) = p.card.presentedContent else { return XCTFail("Missing current problem") }
        XCTAssertEqual(id, own.sessionId)
        XCTAssertEqual(p.history.count, 1)
    }

    func testLogoutInvalidatesQueuedRefreshAndRetainedPromptButtons() async throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var starts = 0, cancelled = 0
        XCTAssertTrue(p.presentRecordingPrompt(displayName: "Zoom",
            onStart: { starts += 1 }, onDismiss: {}, onRememberChoiceChanged: { _ in },
            onInvalidated: { cancelled += 1 }))
        let buttons = notificationButtons(p.card.window?.contentView)
        let item = f.item(); f.bind(item)
        let refresh = p.updateSnapshot(f.snapshot([item]))
        p.invalidate()
        await refresh?.value
        for button in buttons { button.performClick(nil) }
        XCTAssertEqual(starts, 0); XCTAssertEqual(cancelled, 1)
        XCTAssertNil(p.card.presentedContent); XCTAssertTrue(p.history.isEmpty)
    }
}

@MainActor
private func calendarPipeline(_ fixture: NotificationTestFixture, _ presenter: DesktopNotificationPresenter,
                              _ events: [DesktopCalendarPromptEvent]) -> (CalendarTrayModel, NotificationCalendarLoader) {
    let loader = NotificationCalendarLoader(response: fixture.calendar(events))
    let model = CalendarTrayModel { try await loader.load() }
    model.onProjection = { presenter.updateCalendarProjection($0) }
    model.onAuthInvalidated = { presenter.invalidate() }
    return (model, loader)
}

private actor NotificationCalendarLoader {
    var response: DesktopCalendarPromptResponse
    var failure: (any Error)?
    init(response: DesktopCalendarPromptResponse) { self.response = response }
    func load() throws -> DesktopCalendarPromptResponse {
        if let failure { throw failure }
        return response
    }
    func setFailure(_ failure: any Error) { self.failure = failure }
    func setResponse(_ response: DesktopCalendarPromptResponse) {
        self.response = response; failure = nil
    }
}

@MainActor
func notificationFixture(_ test: XCTestCase, requiresScreen: Bool = true) throws -> NotificationTestFixture {
    _ = NSApplication.shared
    if requiresScreen && NSScreen.screens.isEmpty { throw XCTSkip("WindowServer screen is required for actual card delivery") }
    let suite = "graf-f277-delivery-\(UUID())"
    test.addTeardownBlock { UserDefaults(suiteName: suite)?.removePersistentDomain(forName: suite) }
    return NotificationTestFixture(defaults: try XCTUnwrap(UserDefaults(suiteName: suite)))
}

@MainActor
final class NotificationTestFixture {
    var now = Date()
    var sounds = 0
    var openedEventIDs: [String] = []
    var joinHandler: (@MainActor (String, @escaping () -> Bool) async -> Bool)?
    var actions: [DesktopControlAction] = []
    let store: DesktopNotificationPreferencesStore
    let defaults: UserDefaults
    let model = DesktopControlModel()
    init(defaults: UserDefaults) { self.defaults = defaults; store = .init(defaults: defaults) }
    func presenter(screens: [NotificationCardScreen]? = nil, restoredStore: Bool = false,
                   user: String = "owner", workspace: String = "workspace",
                   serverOrigin: String = "", initialPlacementDelay: TimeInterval = 0) -> DesktopNotificationPresenter {
        var environment = NotificationCardEnvironment()
        environment.now = { self.now }; environment.automaticallyTicks = false
        environment.announce = { _, _ in }
        if let screens { environment.screens = { screens } }
        let currentScreens = environment.screens
        var pendingPlacementDelay = initialPlacementDelay
        environment.screens = {
            self.now.addTimeInterval(pendingPlacementDelay)
            pendingPlacementDelay = 0
            return currentScreens()
        }
        model.onAction = { [weak self] in self?.actions.append($0) }
        let result = DesktopNotificationPresenter(
            store: restoredStore ? DesktopNotificationPreferencesStore(defaults: defaults) : store,
            model: model, clock: { self.now }, playSound: { self.sounds += 1 },
            openMeetingEvent: { id, current in
                if let handler = self.joinHandler { return await handler(id, current) }
                guard current() else { return false }
                self.openedEventIDs.append(id); return true
            }, serverOrigin: serverOrigin,
            card: DesktopNotificationCardPresenter(environment: environment))
        result.updateContext(user: user, workspace: workspace)
        return result
    }
    func legacyMeetingDigest(_ event: DesktopCalendarPromptEvent, includesStart: Bool) -> String {
        let raw = "owner:workspace:" + event.eventId
            + (includesStart ? ":" + String(event.startsAt.timeIntervalSince1970) : "")
        let identifier = "graf.local.reminder." + DesktopNotificationPreferencesStore.digest(raw)
        return DesktopNotificationPreferencesStore.digest(identifier)
    }
    func seedLegacyMeetingClaim(_ digest: String, scheduledFor: Date?) {
        let root = "graf.notifications." + DesktopNotificationPreferencesStore.digest("owner")
        var attempts = defaults.dictionary(forKey: root + ".attempts") ?? [:]
        attempts[digest] = Date.distantFuture.timeIntervalSince1970
        defaults.set(attempts, forKey: root + ".attempts")
        if let scheduledFor {
            var reservations = defaults.dictionary(forKey: root + ".attempts.reservations") ?? [:]
            reservations[digest] = ["expires": Date.distantFuture.timeIntervalSince1970,
                                    "scheduledFor": scheduledFor.timeIntervalSince1970]
            defaults.set(reservations, forKey: root + ".attempts.reservations")
        }
    }
    func prompt(_ p: DesktopNotificationPresenter) -> Bool {
        p.presentRecordingPrompt(displayName: "Zoom",
            onStart: {}, onDismiss: {}, onRememberChoiceChanged: { _ in })
    }
    func bind(_ item: DesktopUploadQueueItem) { store.bindSession(item.sessionId, context: "owner:workspace") }
    func item(id: String = "own", state: UploadItemState = .failed, at: Date? = nil) -> DesktopUploadQueueItem {
        custodyFixtureQueueItem(id: id, state: state, updatedAt: at ?? now)
    }
    func snapshot(_ items: [DesktopUploadQueueItem]) -> DesktopControlSnapshot {
        var value = DesktopControlSnapshot(); value.uploadItems = items; return value
    }
    func event(id: String = "meeting", start: Date, duration: TimeInterval = 3600) -> DesktopCalendarPromptEvent {
        DesktopCalendarPromptEvent(eventId: id, startsAt: start, endsAt: start.addingTimeInterval(duration),
            title: "Private meeting title", titleState: .available, meetingLinkPresent: true,
            openMeetingURL: URL(string: "https://example.test/meeting"))
    }
    func calendar(_ events: [DesktopCalendarPromptEvent]) -> DesktopCalendarPromptResponse {
        var response = DesktopCalendarPromptResponse(events: events, showUpcomingTitle: false)
        response.notificationOwnerID = "owner"; response.notificationWorkspaceID = "workspace"
        return response
    }
}

@MainActor
func notificationButtons(_ view: NSView?) -> [NSButton] {
    guard let view else { return [] }
    return (view as? NSButton).map { [$0] } ?? view.subviews.flatMap { notificationButtons($0) }
}

@MainActor
func notificationClose(_ presenter: DesktopNotificationPresenter) throws {
    let button = try XCTUnwrap(notificationButtons(presenter.card.window?.contentView)
        .first { $0.toolTip == "Закрыть уведомление" })
    button.performClick(nil)
}
