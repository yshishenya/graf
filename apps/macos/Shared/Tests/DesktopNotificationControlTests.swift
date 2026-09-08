import AppKit
import Foundation
import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopNotificationControlTests: XCTestCase {
    func testOlderPreferencesKeepExplicitFalseAndDoNotEnableRecaps() throws {
        let data = Data(#"{"reminders":false,"offsetMinutes":5,"showTitles":false,"sound":false}"#.utf8)
        let value = try JSONDecoder().decode(DesktopNotificationPreferences.self, from: data)
        XCTAssertFalse(value.reminders)
        XCTAssertFalse(value.sound)
        XCTAssertFalse(value.showTitles)
        XCTAssertFalse(value.recaps)
        XCTAssertEqual(value.offsetMinutes, 5)
    }

    func testRecapRequiresFreshServerEventNotAnAdjacentSnapshotTransition() {
        var pending = custodyFixtureQueueItem(id: "recap", state: .uploaded)
        pending.serverTruth = ServerTruthFingerprint(meetingId: UUID().uuidString, mediaRevisionId: "revision",
            deletionState: "none", accessState: "owner", reviewAvailable: true, summaryStatus: "generating")
        var ready = pending
        ready.serverTruth.summaryStatus = "available"
        let now = Date()
        XCTAssertNil(DesktopNotificationPresenter.freshRecapID(ready, context: "owner", now: now))
        ready.serverTruth.transcriptAvailable = true
        ready.serverTruth.summaryEventId = UUID().uuidString
        ready.serverTruth.summaryUpdatedAt = now
        XCTAssertNotNil(DesktopNotificationPresenter.freshRecapID(ready, context: "owner", now: now))
        XCTAssertNil(DesktopNotificationPresenter.freshRecapID(ready, context: "owner", now: now.addingTimeInterval(300)))
        ready.serverTruth.accessState = "revoked"
        XCTAssertNil(DesktopNotificationPresenter.freshRecapID(ready, context: "owner", now: now))
    }

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

    func testPanelFitsShortAndNegativeOriginScreens() {
        for bounds in [NSRect(x: 0, y: 24, width: 1440, height: 876),
                       NSRect(x: -1280, y: -320, width: 1280, height: 480)] {
            for candidate in [NSRect(x: 3000, y: 900, width: 290, height: 320),
                              NSRect(x: -3000, y: -1200, width: 2000, height: 1200)] {
                let placed = DesktopPanelPlacement.frame(candidate, within: bounds)
                XCTAssertTrue(bounds.contains(placed))
                XCTAssertEqual(DesktopPanelPlacement.frame(placed, within: bounds), placed)
            }
        }
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

    func testLateReminderDoesNotPromiseOriginalFiveMinutes() {
        let start = Date(timeIntervalSince1970: 1000)
        let due = start.addingTimeInterval(-300)
        XCTAssertTrue(DesktopNotificationPresenter.reminderBody(startsAt: start, due: due, offsetMinutes: 5, now: due).contains("через 5 мин"))
        XCTAssertTrue(DesktopNotificationPresenter.reminderBody(startsAt: start, due: due, offsetMinutes: 5, now: start.addingTimeInterval(-30)).contains("скоро"))
        XCTAssertTrue(DesktopNotificationPresenter.reminderBody(startsAt: start, due: due, offsetMinutes: 5, now: start).contains("уже началась"))
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

    func testVisibleStopResultConsumesOnlyItsIncidentWithoutLosingOtherRecording() throws {
        let name = "graf-notification-visible-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        let now = Date()
        let shown = DesktopLocalNotificationIncident(sessionID: "shown", itemIDs: ["a"],
            expires: now.addingTimeInterval(3600), fresh: true)
        let other = DesktopLocalNotificationIncident(sessionID: "other", itemIDs: ["b"],
            expires: now.addingTimeInterval(3600), fresh: true)
        let model = DesktopControlModel()
        model.setVisibleResultSessionID("shown")
        XCTAssertFalse(shown.claimForDelivery(store: store, owner: "owner",
            visibleResultSessionID: model.visibleResultSessionID, now: now))
        XCTAssertTrue(other.claimForDelivery(store: store, owner: "owner",
            visibleResultSessionID: model.visibleResultSessionID, now: now))
        model.setVisibleResultSessionID(nil)
        XCTAssertFalse(shown.claimForDelivery(store: store, owner: "owner",
            visibleResultSessionID: model.visibleResultSessionID, now: now.addingTimeInterval(8)))
        XCTAssertFalse(other.claimForDelivery(store: store, owner: "owner",
            visibleResultSessionID: model.visibleResultSessionID, now: now.addingTimeInterval(8)))
        XCTAssertFalse(other.claimForDelivery(store: store, owner: "owner",
            visibleResultSessionID: nil, now: now.addingTimeInterval(9)))
    }

}
