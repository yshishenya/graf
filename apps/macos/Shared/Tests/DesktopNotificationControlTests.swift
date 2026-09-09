import AppKit
import Foundation
import XCTest
import UserNotifications
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopNotificationControlTests: XCTestCase {
    func testIncidentRecursOnlyAfterObservedRecovery() throws {
        let name = "graf-incident-recovery-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        let now = Date()
        let incident = DesktopLocalNotificationIncident(sessionID: "session", itemIDs: ["item"], expires: now.addingTimeInterval(300), fresh: true)
        store.reconcileIncidents([incident], knownSessions: ["session"], owner: "owner")
        XCTAssertTrue(store.claimLocalIncident(incident, owner: "owner", now: now))
        store.reconcileIncidents([incident], knownSessions: ["session"], owner: "owner")
        XCTAssertFalse(store.claimLocalIncident(incident, owner: "owner", now: now))
        store.reconcileIncidents([], knownSessions: [], owner: "owner")
        XCTAssertFalse(store.claimLocalIncident(incident, owner: "owner", now: now))
        store.reconcileIncidents([], knownSessions: ["session"], owner: "owner")
        XCTAssertTrue(store.claimLocalIncident(incident, owner: "owner", now: now))
    }

    func testEveryFailedRecordingHasFreshIncidentEvenAfterRetention() {
        let now = Date()
        var snapshot = DesktopControlSnapshot()
        snapshot.uploadItems = (0..<8).map { index in
            custodyFixtureQueueItem(id: "failure-\(index)", state: .failed,
                retentionDeadline: now.addingTimeInterval(-1), updatedAt: now)
        }
        let incidents = DesktopLocalNotificationIncident.incidents(in: snapshot, now: now)
        XCTAssertEqual(incidents.count, 8)
        XCTAssertTrue(incidents.allSatisfy { $0.fresh && $0.expires > now })
    }

    func testUnreadyDispatcherRejectsWithoutDeferringStart() {
        let model = DesktopControlModel()
        XCTAssertFalse(model.send(.start))
        var actions: [DesktopControlAction] = []
        model.onAction = { actions.append($0) }
        XCTAssertTrue(actions.isEmpty)
        XCTAssertTrue(model.send(.start))
        XCTAssertEqual(actions, [.start])
    }

    func testPermissionRecoveryDoesNotOpenHistoricalRecording() {
        var snapshot = DesktopControlSnapshot()
        snapshot.session = CaptureSession(
            id: "completed", mode: .audioRecording, state: .stopped,
            sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
            visibleIndicatorState: .hidden, stopActionAvailable: false,
            bufferSummaryId: nil, startedAt: Date(), stoppedAt: Date()
        )
        XCTAssertEqual(snapshot.recoveryAction, .localRecordings)
        snapshot.permissionBlocker = true
        XCTAssertEqual(snapshot.recoveryAction, .permissions)
    }

    func testDeviceNavigationDoesNotMutateCapture() {
        let model = DesktopControlModel()
        var actions: [DesktopControlAction] = []
        model.onAction = { actions.append($0) }
        let snapshot = model.snapshot
        model.send(.localRecordings)
        XCTAssertEqual(model.snapshot, snapshot)
        XCTAssertEqual(actions, [.localRecordings])
    }

    func testSharedControlDispatcherForwardsAllCaptureActions() {
        let model = DesktopControlModel()
        var actions: [DesktopControlAction] = []
        model.onAction = { actions.append($0) }

        for action in [DesktopControlAction.start, .stop, .pause, .resume] {
            model.send(action)
        }

        XCTAssertEqual(actions, [.start, .stop, .pause, .resume])
    }

    func testElapsedContinuesDuringMicrophonePauseAndFreezesOnlyAfterStop() {
        let start = Date(timeIntervalSince1970: 1_000)
        let model = DesktopControlModel()
        var snapshot = DesktopControlSnapshot()
        snapshot.session = CaptureSession(
            id: "timer", mode: .audioRecording, state: .active,
            sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
            visibleIndicatorState: .active, stopActionAvailable: true,
            bufferSummaryId: nil, startedAt: start, stoppedAt: nil
        )
        model.update(snapshot)
        XCTAssertEqual(model.elapsed(now: start.addingTimeInterval(5)), "0:05")
        snapshot.session?.state = .paused
        model.update(snapshot)
        XCTAssertEqual(model.elapsed(now: start.addingTimeInterval(15)), "0:15")
        XCTAssertEqual(model.elapsed(now: start.addingTimeInterval(25)), "0:25")
        XCTAssertTrue(model.snapshot.active)
        snapshot.session?.state = .active
        model.update(snapshot)
        XCTAssertEqual(model.elapsed(now: start.addingTimeInterval(65)), "1:05")
        snapshot.session?.state = .stopped
        snapshot.session?.stoppedAt = start.addingTimeInterval(70)
        model.update(snapshot)
        XCTAssertEqual(model.elapsed(now: start.addingTimeInterval(90)), "1:10")
        XCTAssertFalse(model.snapshot.active)
    }

    func testPermissionDefaultsAndOwnerIsolation() throws {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: "graf-notification-test-\(UUID())"))
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        var preferences = store.load(owner: "owner-a")
        XCTAssertFalse(preferences.showTitles)
        XCTAssertFalse(preferences.sound)
        preferences.showTitles = true
        try store.save(preferences, owner: "owner-a")
        XCTAssertTrue(store.load(owner: "owner-a").showTitles)
        XCTAssertFalse(store.load(owner: "owner-b").showTitles)
        XCTAssertThrowsError(try store.save(preferences, owner: ""))
    }

    func testSessionOwnerCannotChangeAfterLoginSwitchOrRestart() throws {
        let name = "graf-notification-owner-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        store.bindSession("capture-1", context: "owner-a:workspace-a")
        let restored = DesktopNotificationPreferencesStore(defaults: defaults)
        restored.bindSession("capture-1", context: "owner-b:workspace-b")
        XCTAssertTrue(restored.ownsSession("capture-1", context: "owner-a:workspace-a"))
        XCTAssertFalse(restored.ownsSession("capture-1", context: "owner-b:workspace-b"))
        XCTAssertFalse(restored.ownsSession("capture-1", context: "owner-a:workspace-b"))
        restored.bindSession("offline-capture", context: "")
        restored.bindSession("offline-capture", context: "owner-a:workspace-a")
        XCTAssertFalse(restored.ownsSession("offline-capture", context: "owner-a:workspace-a"))
    }

    func testNotificationClaimSurvivesRestartAndRejectsExpiredEvent() throws {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: "graf-notification-claim-\(UUID())"))
        let now = Date()
        let first = DesktopNotificationPreferencesStore(defaults: defaults)
        XCTAssertTrue(first.claim(id: "incident-1", owner: "a", expires: now.addingTimeInterval(30), now: now))
        XCTAssertFalse(DesktopNotificationPreferencesStore(defaults: defaults).claim(id: "incident-1", owner: "a", expires: now.addingTimeInterval(30), now: now))
        XCTAssertFalse(first.claim(id: "old", owner: "a", expires: now.addingTimeInterval(-1), now: now))
    }
    func testCancelledFutureReservationCanBeRestoredButDueAttemptCannotRepeat() throws {
        let name = "graf-notification-reservation-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let now = Date(timeIntervalSince1970: 1000)
        let due = now.addingTimeInterval(120)
        let expiry = due.addingTimeInterval(300)
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        XCTAssertTrue(store.claim(id: "reminder", owner: "a", expires: expiry, scheduledFor: due, now: now))
        let legacyLedger = try XCTUnwrap(defaults.dictionaryRepresentation().first { $0.key.hasSuffix(".attempts") }?.value as? [String: Double])
        XCTAssertEqual(legacyLedger.count, 1, "Rollback must still read the old numeric deny ledger")
        let restored = DesktopNotificationPreferencesStore(defaults: defaults)
        XCTAssertTrue(restored.claim(id: "reminder", owner: "a", expires: expiry, scheduledFor: due, now: now.addingTimeInterval(60)))
        XCTAssertFalse(restored.claim(id: "reminder", owner: "a", expires: expiry, scheduledFor: due.addingTimeInterval(60), now: due))
        XCTAssertTrue(store.claim(id: "immediate", owner: "a", expires: expiry, now: now))
        XCTAssertFalse(restored.claim(id: "immediate", owner: "a", expires: expiry, scheduledFor: due, now: now))
        XCTAssertTrue(store.claim(id: "moved", owner: "a", expires: expiry, scheduledFor: due, now: now))
        XCTAssertTrue(store.claim(id: "moved", owner: "a", expires: expiry, scheduledFor: now, now: now))
        XCTAssertFalse(restored.claim(id: "moved", owner: "a", expires: expiry, scheduledFor: due, now: now.addingTimeInterval(1)))
    }

    func testNotificationClickUsesCurrentPermittedUnexpiredMeetingURL() {
        let now = Date(timeIntervalSince1970: 1000)
        let old = DesktopCalendarPromptEvent(eventId: "event", startsAt: now, endsAt: now.addingTimeInterval(3600), openMeetingURL: URL(string: "https://example.test/old"))
        var current = old
        current.openMeetingURL = URL(string: "https://example.test/current")
        XCTAssertEqual(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [current], now: now), current.openMeetingURL)
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [], now: now))
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [current], now: now.addingTimeInterval(300)))
        current.joinPromptState = .blockedByPolicy
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [current], now: now))
        current.joinPromptState = .notDue
        current.openMeetingURL = URL(string: "http://example.test/current")
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [current], now: now))
    }

    func testFailedSessionKeepsIndicatorUntilStopCleanupFinishes() {
        var snapshot = DesktopControlSnapshot()
        XCTAssertEqual(snapshot.recoveryAction, .permissions)
        snapshot.session = CaptureSession(id: "stop", mode: .audioRecording, state: .failed,
            sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
            visibleIndicatorState: .error, stopActionAvailable: false,
            bufferSummaryId: nil, startedAt: Date(), stoppedAt: nil)
        snapshot.stopping = true
        XCTAssertTrue(snapshot.active)
        XCTAssertFalse(snapshot.completedRecording)
        snapshot.stopping = false
        XCTAssertFalse(snapshot.active)
        XCTAssertTrue(snapshot.completedRecording)
        XCTAssertEqual(snapshot.recoveryAction, .localRecordings)
    }

    func testNotificationWithoutLinkStillResolvesOnlyCurrentPermittedEvent() {
        let now = Date(timeIntervalSince1970: 1000)
        let event = DesktopCalendarPromptEvent(eventId: "no-link", startsAt: now, endsAt: now.addingTimeInterval(3600))
        XCTAssertEqual(DesktopNotificationPresenter.currentMeeting(for: event, events: [event], now: now)?.eventId, event.eventId)
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: event, events: [event], now: now))
        XCTAssertNil(DesktopNotificationPresenter.currentMeeting(for: event, events: [], now: now))
        XCTAssertNil(DesktopNotificationPresenter.currentMeeting(for: event, events: [event], now: now.addingTimeInterval(300)))
        var moved = event
        moved.startsAt = now.addingTimeInterval(60)
        XCTAssertNil(DesktopNotificationPresenter.currentMeeting(for: event, events: [moved], now: now))
        var blocked = event
        blocked.joinPromptState = .blockedByPolicy
        XCTAssertNil(DesktopNotificationPresenter.currentMeeting(for: event, events: [blocked], now: now))
    }

    func testMovingReminderKeepsClaimAfterOriginalTimeAndAcrossRestart() throws {
        let name = "graf-moving-reminder-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        let now = Date(timeIntervalSince1970: 1000)
        var event = DesktopCalendarPromptEvent(eventId: "occurrence", startsAt: now.addingTimeInterval(60), endsAt: now.addingTimeInterval(3600))
        let id = DesktopNotificationPresenter.reminderID(event, context: "owner:workspace")
        XCTAssertTrue(store.claim(id: id, owner: "owner", expires: .distantFuture, scheduledFor: now, now: now))
        event.startsAt = now.addingTimeInterval(86400)
        let movedID = DesktopNotificationPresenter.reminderID(event, context: "owner:workspace")
        XCTAssertEqual(movedID, id)
        let restored = DesktopNotificationPreferencesStore(defaults: defaults)
        XCTAssertFalse(restored.claim(id: movedID, owner: "owner", expires: .distantFuture,
            scheduledFor: event.startsAt, now: now.addingTimeInterval(7200)))
        event.eventId = "next-occurrence"
        XCTAssertNotEqual(DesktopNotificationPresenter.reminderID(event, context: "owner:workspace"), id)
    }

    func testLegacyReminderAttemptIsNotRepeatedOnUpgrade() throws {
        let name = "graf-old-reminder-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        let now = Date(timeIntervalSince1970: 1000)
        let event = DesktopCalendarPromptEvent(eventId: "event", startsAt: now, endsAt: now.addingTimeInterval(3600))
        let legacy = DesktopNotificationPresenter.legacyReminderID(event, context: "owner:workspace")
        XCTAssertTrue(store.claim(id: legacy, owner: "owner", expires: now.addingTimeInterval(300), now: now))
        XCTAssertFalse(store.claim(id: DesktopNotificationPresenter.reminderID(event, context: "owner:workspace"),
            aliases: [legacy], owner: "owner", expires: .distantFuture, scheduledFor: now, now: now))
        var moved = event; moved.startsAt = now.addingTimeInterval(86400)
        XCTAssertFalse(store.claim(id: DesktopNotificationPresenter.reminderID(moved, context: "owner:workspace"),
            aliases: [DesktopNotificationPresenter.legacyReminderID(moved, context: "owner:workspace")],
            owner: "owner", expires: .distantFuture, scheduledFor: moved.startsAt, now: now.addingTimeInterval(7200)))
    }

    func testRecordingSuppressesOnlyItsCalendarOccurrence() {
        let now = Date(timeIntervalSince1970: 1000)
        let event = DesktopCalendarPromptEvent(eventId: "other-meeting", startsAt: now, endsAt: now.addingTimeInterval(3600))
        var snapshot = DesktopControlSnapshot()
        snapshot.stopping = true
        XCTAssertTrue(DesktopNotificationPresenter.shouldRemind(event, snapshot: snapshot, now: now), "Manual recording keeps calendar reminders")
        snapshot.calendarContextEventID = "recorded-meeting"
        XCTAssertTrue(DesktopNotificationPresenter.shouldRemind(event, snapshot: snapshot, now: now))
        snapshot.calendarContextEventID = event.eventId
        XCTAssertFalse(DesktopNotificationPresenter.shouldRemind(event, snapshot: snapshot, now: now))
        snapshot.stopping = false
        XCTAssertTrue(DesktopNotificationPresenter.shouldRemind(event, snapshot: snapshot, now: now))
        XCTAssertFalse(DesktopNotificationPresenter.shouldRemind(event, snapshot: snapshot, now: now.addingTimeInterval(300)))
    }

    func testReminderContentUsesAbsoluteTimePrivateDefaultsAndOptionalJoin() {
        let now = Date(timeIntervalSince1970: 0)
        var event = DesktopCalendarPromptEvent(eventId: "event", startsAt: now, endsAt: now.addingTimeInterval(3600))
        let hidden = DesktopNotificationPresenter.reminderContent(event: event, preferences: .init(), recording: false, timeZone: TimeZone(secondsFromGMT: 0)!)
        XCTAssertEqual(hidden.title, "Встреча в календаре")
        XCTAssertEqual(hidden.body, "Начало в 00:00. Запись ещё не начата.")
        XCTAssertNil(hidden.sound)
        let categories = DesktopNotificationPresenter.notificationCategories
        XCTAssertFalse(categories.first { $0.identifier == hidden.categoryIdentifier }!.actions.contains { $0.identifier == "graf.join" })
        event.openMeetingURL = URL(string: "https://example.test/meeting")
        var preferences = DesktopNotificationPreferences()
        preferences.sound = true
        let linked = DesktopNotificationPresenter.reminderContent(event: event, preferences: preferences, recording: true)
        XCTAssertNil(linked.sound)
        XCTAssertEqual(categories.first { $0.identifier == linked.categoryIdentifier }!.actions.map(\.identifier), ["graf.join", "graf.settings"])
    }

    func testNotificationActionsNeverImplicitlyJoinOrCapture() {
        XCTAssertEqual(DesktopNotificationPresenter.responseAction(UNNotificationDefaultActionIdentifier, calendar: true), .calendar)
        XCTAssertEqual(DesktopNotificationPresenter.responseAction("graf.join", calendar: true), .join)
        XCTAssertEqual(DesktopNotificationPresenter.responseAction("graf.settings", calendar: true), .settings)
        XCTAssertEqual(DesktopNotificationPresenter.responseAction(UNNotificationDefaultActionIdentifier, calendar: false), .localRecording)
        XCTAssertEqual(DesktopNotificationPresenter.responseAction("graf.openRecording", calendar: false), .localRecording)
        for action in [UNNotificationDismissActionIdentifier, "unknown", "graf.start", "graf.join"] {
            XCTAssertNil(DesktopNotificationPresenter.responseAction(action, calendar: false))
        }
    }

    func testStopAndUploadFailureBecomeOneSessionIncident() {
        let now = Date()
        let item = custodyFixtureQueueItem(id: "stopped", state: .failed,
            retentionDeadline: now.addingTimeInterval(3600), updatedAt: now)
        var snapshot = DesktopControlSnapshot()
        snapshot.uploadItems = [item]
        snapshot.session = CaptureSession(id: item.sessionId, mode: .audioRecording, state: .failed,
            sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
            visibleIndicatorState: .error, stopActionAvailable: false,
            bufferSummaryId: nil, startedAt: now.addingTimeInterval(-60), stoppedAt: now)
        snapshot.blocker = "Не удалось завершить запись"
        let incidents = DesktopLocalNotificationIncident.incidents(in: snapshot, now: now)
        XCTAssertEqual(incidents.count, 1)
        XCTAssertEqual(incidents.first?.sessionID, item.sessionId)
        XCTAssertEqual(incidents.first?.itemIDs, [item.id])
        XCTAssertEqual(incidents.first?.fresh, true)
    }

    func testLegacyClaimsPreventDuplicateAfterUpgradeAndRollback() throws {
        let now = Date()
        let incident = DesktopLocalNotificationIncident(sessionID: "session", itemIDs: ["item"],
            expires: now.addingTimeInterval(3600), fresh: true)
        for legacyID in ["graf.local.capture.session", "graf.local.incident.item"] {
            let name = "graf-notification-upgrade-\(UUID())"
            let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
            defer { defaults.removePersistentDomain(forName: name) }
            let store = DesktopNotificationPreferencesStore(defaults: defaults)
            XCTAssertTrue(store.claim(id: legacyID, owner: "owner", expires: incident.expires, now: now))
            XCTAssertFalse(store.claimLocalIncident(incident, owner: "owner", now: now))
            let restored = DesktopNotificationPreferencesStore(defaults: defaults)
            XCTAssertFalse(restored.claim(id: "graf.local.capture.session", owner: "owner", expires: incident.expires, now: now))
            XCTAssertFalse(restored.claim(id: "graf.local.incident.item", owner: "owner", expires: incident.expires, now: now))
            XCTAssertFalse(restored.claimLocalIncident(incident, owner: "owner", now: now))
        }
    }



}
