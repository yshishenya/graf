import AppKit
import Foundation
import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopNotificationControlTests: XCTestCase {
    func testF277MeetingClaimMigrationPreservesUnrelatedAndIncidentEvidence() throws {
        let f = try notificationFixture(self, requiresScreen: false)
        let root = "graf.notifications." + DesktopNotificationPreferencesStore.digest("owner")
        let event = f.event(start: f.now.addingTimeInterval(60))
        f.seedLegacyMeetingClaim(f.legacyMeetingDigest(event, includesStart: false), scheduledFor: nil)
        let incidentKey = DesktopNotificationPreferencesStore.digest("graf.local.incident.previous-item")
        var attempts = try XCTUnwrap(f.defaults.dictionary(forKey: root + ".attempts"))
        attempts[incidentKey] = Date.distantFuture.timeIntervalSince1970
        attempts["unknown-entry"] = ["opaque": "keep"]
        f.defaults.set(attempts, forKey: root + ".attempts")
        f.defaults.set(["session": ["previous-item"]], forKey: root + ".activeIncidents")
        f.store.bindSession("session", context: "owner:workspace")
        let p = f.presenter(screens: [])
        defer { p.dismissAllCards() }
        p.updateCalendar(f.calendar([event]))
        let remaining = try XCTUnwrap(f.defaults.dictionary(forKey: root + ".attempts"))
        XCTAssertNil(remaining[f.legacyMeetingDigest(event, includesStart: false)])
        XCTAssertEqual(f.defaults.dictionary(forKey: root + ".meetingReceipts")?.count, 1)
        XCTAssertEqual(remaining["unknown-entry"] as? [String: String], ["opaque": "keep"])
        XCTAssertEqual(remaining[incidentKey] as? Double, Date.distantFuture.timeIntervalSince1970)
        XCTAssertTrue(f.store.ownsSession("session", context: "owner:workspace"))
        let current = DesktopLocalNotificationIncident(sessionID: "session", itemIDs: ["current-item"],
            expires: f.now.addingTimeInterval(300), fresh: true)
        f.store.reconcileIncidents([current], knownSessions: ["session"], owner: "owner")
        XCTAssertFalse(f.store.claimLocalIncident(current, owner: "owner", now: f.now),
                       "Calendar migration cannot lose a previous-item incident marker")
    }

    func testMigrationReadsPersistedPreviousItemsBeforePartialSnapshotReplacesThem() throws {
        let name = "graf-f277-migration-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        let root = "graf.notifications." + DesktopNotificationPreferencesStore.digest("owner")
        let oldItem = DesktopNotificationPreferencesStore.digest("graf.local.incident.old-item")
        let unrelated = "unknown-entry"
        let now = Date()
        defaults.set([oldItem: Date.distantFuture.timeIntervalSince1970, unrelated: 42.0], forKey: root + ".attempts")
        defaults.set(["session": ["old-item"]], forKey: root + ".activeIncidents")
        let incident = DesktopLocalNotificationIncident(sessionID: "session", itemIDs: ["new-item"],
            expires: now.addingTimeInterval(300), fresh: true)
        store.reconcileIncidents([incident], knownSessions: ["session"], owner: "owner")
        XCTAssertFalse(store.claimLocalIncident(incident, owner: "owner", now: now))
        XCTAssertNil(defaults.dictionary(forKey: root + ".attempts")?[oldItem])
        XCTAssertEqual(defaults.dictionary(forKey: root + ".attempts")?[unrelated] as? Double, 42)
        XCTAssertFalse(DesktopNotificationPreferencesStore(defaults: defaults)
            .claimLocalIncident(incident, owner: "owner", now: now))
        store.reconcileIncidents([], knownSessions: ["session"], owner: "owner")
        XCTAssertTrue(store.claimLocalIncident(incident, owner: "owner", now: now))
    }

    func testMigrationAcceptsEachKnownLegacyClaimWithoutWritingLegacyAliases() throws {
        for oldID in ["graf.local.capture.session", "graf.local.incident.item"] {
            let name = "graf-f277-migration-\(UUID())"
            let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
            defer { defaults.removePersistentDomain(forName: name) }
            let root = "graf.notifications." + DesktopNotificationPreferencesStore.digest("owner")
            defaults.set([DesktopNotificationPreferencesStore.digest(oldID): Date.distantFuture.timeIntervalSince1970],
                         forKey: root + ".attempts")
            let store = DesktopNotificationPreferencesStore(defaults: defaults)
            let incident = DesktopLocalNotificationIncident(sessionID: "session", itemIDs: ["item"],
                expires: Date().addingTimeInterval(300), fresh: true)
            XCTAssertFalse(store.claimLocalIncident(incident, owner: "owner", now: Date()))
            XCTAssertTrue(defaults.dictionary(forKey: root + ".attempts")?.isEmpty == true)
            XCTAssertEqual(defaults.dictionary(forKey: root + ".incidentClaims")?.count, 1)
        }
    }

    func testRetirementPreservesUnmatchedMigrationEvidenceAndOriginalCutover() throws {
        let name = "graf-f277-retire-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let root = "graf.notifications." + DesktopNotificationPreferencesStore.digest("owner")
        defaults.set(["unknown": ["value": "keep"]], forKey: root + ".attempts")
        defaults.set(["calendar": ["scheduledFor": 1000]], forKey: root + ".attempts.reservations")
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        store.bindSession("session", context: "owner:workspace")
        var prefs = DesktopNotificationPreferences(); prefs.offsetMinutes = 5; prefs.sound = true
        try store.save(prefs, owner: "owner")
        store.beginCalendarRetirement(at: Date(timeIntervalSince1970: 900))
        store.beginCalendarRetirement(at: Date(timeIntervalSince1970: 1100))
        XCTAssertEqual(defaults.double(forKey: "graf.notifications.calendarRetiredAt"), 900)
        XCTAssertEqual(defaults.dictionary(forKey: root + ".attempts.reservations")?["calendar"] as? [String: Int],
                       ["scheduledFor": 1000], "No known event yet: retain migration evidence, not an active scheduler")
        XCTAssertNotNil(defaults.dictionary(forKey: root + ".attempts")?["unknown"])
        XCTAssertTrue(store.ownsSession("session", context: "owner:workspace"))
        XCTAssertEqual(store.load(owner: "owner"), prefs)
        var pending = 0, delivered = 0
        DesktopNotificationRetirement.cleanup(removePending: { pending += 1 }, removeDelivered: { delivered += 1 })
        DesktopNotificationRetirement.cleanup(removePending: { pending += 1 }, removeDelivered: { delivered += 1 })
        XCTAssertEqual(pending, 2); XCTAssertEqual(delivered, 2)
    }

    func testMeetingReceiptsHaveFiniteUnextendedExpiryAndPruneExpiredOccurrences() throws {
        let f = try notificationFixture(self, requiresScreen: false)
        let root = "graf.notifications." + DesktopNotificationPreferencesStore.digest("owner")
        let start = f.now.addingTimeInterval(60)
        f.store.beginCalendarRetirement(at: f.now)
        XCTAssertTrue(f.store.claimMeeting(eventID: "meeting", startsAt: start, endsAt: start.addingTimeInterval(3600),
            owner: "owner", context: "https://one.test|owner:workspace", legacyContext: "owner:workspace", now: f.now))
        let receipts = try XCTUnwrap(f.defaults.dictionary(forKey: root + ".meetingReceipts") as? [String: Double])
        XCTAssertEqual(Array(receipts.values), [start.addingTimeInterval(120).timeIntervalSince1970])
        XCTAssertFalse(f.store.claimMeeting(eventID: "meeting", startsAt: start, endsAt: start.addingTimeInterval(7200),
            owner: "owner", context: "https://one.test|owner:workspace", legacyContext: "owner:workspace",
            now: f.now.addingTimeInterval(30)))
        XCTAssertEqual(f.defaults.dictionary(forKey: root + ".meetingReceipts") as? [String: Double], receipts)
        f.now = start.addingTimeInterval(121)
        XCTAssertTrue(f.store.claimMeeting(eventID: "next", startsAt: f.now, endsAt: f.now.addingTimeInterval(30),
            owner: "owner", context: "https://one.test|owner:workspace", legacyContext: "owner:workspace", now: f.now))
        let remaining = try XCTUnwrap(f.defaults.dictionary(forKey: root + ".meetingReceipts") as? [String: Double])
        XCTAssertEqual(remaining.count, 1)
        XCTAssertEqual(Array(remaining.values), [f.now.addingTimeInterval(120).timeIntervalSince1970])
        XCTAssertTrue(Set(receipts.keys).isDisjoint(with: Set(remaining.keys)))
    }

    func testUntrustedOffsetFailsDecodeAndSaveWithoutReplacingGoodPreferences() throws {
        XCTAssertThrowsError(try JSONDecoder().decode(DesktopNotificationPreferences.self,
            from: Data(#"{"offsetMinutes":15}"#.utf8)))
        let name = "graf-f277-invalid-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        let good = DesktopNotificationPreferences()
        try store.save(good, owner: "owner")
        var bad = good; bad.offsetMinutes = 15
        XCTAssertThrowsError(try store.save(bad, owner: "owner"))
        XCTAssertEqual(store.load(owner: "owner"), good)
    }

    func testLegacySessionOwnershipIsAdoptedOnlyOnceByConfirmedOrigin() throws {
        let name = "graf-f277-origin-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        store.bindSession("session", context: "owner:workspace")
        store.adoptLegacySession("session", context: "https://one.test|owner:workspace", legacyContext: "owner:workspace")
        store.adoptLegacySession("session", context: "https://two.test|owner:workspace", legacyContext: "owner:workspace")
        XCTAssertTrue(store.ownsSession("session", context: "https://one.test|owner:workspace"))
        XCTAssertFalse(store.ownsSession("session", context: "https://two.test|owner:workspace"))
        store.bindSession("unknown", context: "")
        store.adoptLegacySession("unknown", context: "https://one.test|owner:workspace", legacyContext: "owner:workspace")
        XCTAssertFalse(store.ownsSession("unknown", context: "https://one.test|owner:workspace"))
    }

    // F277 RED: exercise the existing public API before replacing the transport.
    func testF277OldPreferencesDecodeQuietAsFalseWithoutLosingValues() throws {
        let data = Data(#"{"reminders":false,"offsetMinutes":5,"showTitles":true,"sound":true}"#.utf8)
        let value = try JSONDecoder().decode(DesktopNotificationPreferences.self, from: data)
        XCTAssertFalse(value.reminders)
        XCTAssertEqual(value.offsetMinutes, 5)
        XCTAssertTrue(value.showTitles)
        XCTAssertTrue(value.sound)
        let encoded = try JSONEncoder().encode(value)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        XCTAssertEqual(object["quiet"] as? Bool, false,
                       "Missing legacy quiet must decode to false and become part of current preferences")
    }

    func testF277QuietPreferenceSurvivesDecodeAndSave() throws {
        let name = "graf-f277-quiet-\(UUID())"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let store = DesktopNotificationPreferencesStore(defaults: defaults)
        let data = Data(#"{"reminders":true,"offsetMinutes":0,"showTitles":false,"sound":false,"quiet":true}"#.utf8)
        let value = try JSONDecoder().decode(DesktopNotificationPreferences.self, from: data)
        try store.save(value, owner: "owner")
        let restored = try JSONEncoder().encode(store.load(owner: "owner"))
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: restored) as? [String: Any])
        XCTAssertEqual(object["quiet"] as? Bool, true)
    }

    func testF277MovedOccurrenceHasNewIdentityAndContextIsIsolated() {
        let start = Date(timeIntervalSince1970: 1_000)
        var event = DesktopCalendarPromptEvent(eventId: "occurrence", startsAt: start,
                                               endsAt: start.addingTimeInterval(3_600))
        let first = DesktopNotificationPresenter.reminderID(event, context: "owner:workspace")
        XCTAssertEqual(first, DesktopNotificationPresenter.reminderID(event, context: "owner:workspace"))
        XCTAssertNotEqual(first, DesktopNotificationPresenter.reminderID(event, context: "other:workspace"))
        event.startsAt = start.addingTimeInterval(60)
        XCTAssertNotEqual(first, DesktopNotificationPresenter.reminderID(event, context: "owner:workspace"),
                          "Occurrence identity contains both event ID and start time")
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

    func testUnreadyDispatcherRejectsWithoutDeferringStart() {
        let model = DesktopControlModel()
        XCTAssertFalse(model.send(.start))
        var actions: [DesktopControlAction] = []
        model.onAction = { actions.append($0) }
        XCTAssertTrue(actions.isEmpty)
        XCTAssertTrue(model.send(.start))
        XCTAssertEqual(actions, [.start])
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


    func testNotificationClickUsesCurrentPermittedUnexpiredMeetingURL() {
        let now = Date(timeIntervalSince1970: 1000)
        let old = DesktopCalendarPromptEvent(eventId: "event", startsAt: now, endsAt: now.addingTimeInterval(3600), meetingLinkPresent: true, openMeetingURL: URL(string: "https://example.test/old"))
        var current = old
        current.openMeetingURL = URL(string: "https://example.test/current")
        XCTAssertEqual(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [current], now: now), current.openMeetingURL)
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [], now: now))
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [current], now: now.addingTimeInterval(3_600)))
        current.joinPromptState = .blockedByPolicy
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [current], now: now))
        current.joinPromptState = .notDue
        current.openMeetingURL = URL(string: "http://example.test/current")
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: old, events: [current], now: now))
    }

    func testFailedSessionKeepsIndicatorUntilStopCleanupFinishes() {
        var snapshot = DesktopControlSnapshot()
        snapshot.session = CaptureSession(id: "stop", mode: .audioRecording, state: .failed,
            sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
            visibleIndicatorState: .error, stopActionAvailable: false,
            bufferSummaryId: nil, startedAt: Date(), stoppedAt: nil)
        snapshot.stopping = true
        XCTAssertTrue(snapshot.active)
        snapshot.stopping = false
        XCTAssertFalse(snapshot.active)
    }

    func testNotificationWithoutLinkStillResolvesOnlyCurrentPermittedEvent() {
        let now = Date(timeIntervalSince1970: 1000)
        let event = DesktopCalendarPromptEvent(eventId: "no-link", startsAt: now, endsAt: now.addingTimeInterval(3600))
        XCTAssertEqual(DesktopNotificationPresenter.currentMeeting(for: event, events: [event], now: now)?.eventId, event.eventId)
        XCTAssertNil(DesktopNotificationPresenter.currentMeetingURL(for: event, events: [event], now: now))
        XCTAssertNil(DesktopNotificationPresenter.currentMeeting(for: event, events: [], now: now))
        XCTAssertNil(DesktopNotificationPresenter.currentMeeting(for: event, events: [event], now: now.addingTimeInterval(3_600)))
        var moved = event
        moved.startsAt = now.addingTimeInterval(60)
        XCTAssertNil(DesktopNotificationPresenter.currentMeeting(for: event, events: [moved], now: now))
        var blocked = event
        blocked.joinPromptState = .blockedByPolicy
        XCTAssertNil(DesktopNotificationPresenter.currentMeeting(for: event, events: [blocked], now: now))
    }



    func testRecordingSuppressesEveryCalendarOccurrence() {
        let now = Date(timeIntervalSince1970: 1000)
        let event = DesktopCalendarPromptEvent(eventId: "other-meeting", startsAt: now, endsAt: now.addingTimeInterval(3600))
        var snapshot = DesktopControlSnapshot()
        snapshot.stopping = true
        XCTAssertFalse(DesktopNotificationPresenter.shouldRemind(event, snapshot: snapshot, now: now), "переход записи не должен предлагать вторую запись")
        snapshot.stopping = false
        XCTAssertTrue(DesktopNotificationPresenter.shouldRemind(event, snapshot: snapshot, now: now))
        XCTAssertFalse(DesktopNotificationPresenter.shouldRemind(event, snapshot: snapshot, now: now.addingTimeInterval(3_600)))
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




}
