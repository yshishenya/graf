import Foundation
import UserNotifications
import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopRecapDeliveryTests: XCTestCase {
    private func fixture() throws -> RecapDeliveryFixture {
        let name = "graf-recap-delivery-\(UUID())"
        addTeardownBlock { UserDefaults(suiteName: name)?.removePersistentDomain(forName: name) }
        return RecapDeliveryFixture(defaults: try XCTUnwrap(UserDefaults(suiteName: name)))
    }

    func testSuccessfulProcessingIsNotALocalIncidentAndRecapsAreOptIn() async throws {
        let f = try fixture()
        let presenter = try f.presenter(recaps: false)
        let ready = f.item()
        f.bind(ready)
        presenter.updateSnapshot(f.snapshot([ready]))
        await presenter.notifyReady()
        XCTAssertTrue(DesktopLocalNotificationIncident.incidents(in: f.snapshot([ready]), now: Date()).isEmpty)
        XCTAssertTrue(f.sent.isEmpty)
        var preferences = presenter.preferences
        preferences.recaps = true
        presenter.save(preferences)
        await presenter.notifyReady()
        XCTAssertEqual(f.sent.count, 1)
        XCTAssertTrue(f.sent.allSatisfy { $0.identifier.hasPrefix("graf.local.ready.") })
        var failed = ready
        failed.syncConflictState = .processingFailed
        XCTAssertTrue(DesktopLocalNotificationIncident.incidents(in: f.snapshot([failed]), now: Date()).isEmpty)
    }

    func testForeignFirstAndHistoricalBacklogDoNotHideFreshOwnedEvent() async throws {
        let f = try fixture()
        let presenter = try f.presenter()
        let foreign = f.item(id: "foreign")
        f.store.bindSession(foreign.sessionId, context: "other:workspace")
        let old = (0..<8).map { f.item(id: "old-\($0)", at: Date().addingTimeInterval(-3600)) }
        let own = f.item(id: "own")
        (old + [own]).forEach(f.bind)
        presenter.updateSnapshot(f.snapshot([foreign] + old + [own]))
        await presenter.notifyReady()
        XCTAssertEqual(f.sent.map(\.identifier), [DesktopNotificationPresenter.recapID(own, context: f.context)])
    }

    func testFailureThenSuccessAndNewVersionHaveSeparateDurableClaims() async throws {
        let f = try fixture()
        let presenter = try f.presenter()
        var item = f.item(status: "failed")
        f.bind(item)
        presenter.updateSnapshot(f.snapshot([item]))
        await presenter.notifyReady()
        await presenter.notifyReady()
        XCTAssertEqual(f.sent.count, 1)
        XCTAssertEqual(f.sent.first?.content.title, "Расшифровка готова")
        item.serverTruth.summaryStatus = "generating"
        item.serverTruth.summaryEventId = nil
        presenter.updateSnapshot(f.snapshot([item]))
        await presenter.notifyReady()
        item.serverTruth.summaryStatus = "available"
        item.serverTruth.summaryEventId = UUID().uuidString
        presenter.updateSnapshot(f.snapshot([item]))
        await presenter.notifyReady()
        XCTAssertEqual(f.sent.count, 2)
        let restarted = try f.presenter()
        restarted.updateSnapshot(f.snapshot([item]))
        await restarted.notifyReady()
        XCTAssertEqual(f.sent.count, 2)
        item.serverTruth.summaryEventId = UUID().uuidString
        restarted.updateSnapshot(f.snapshot([item]))
        await restarted.notifyReady()
        XCTAssertEqual(f.sent.count, 3)
        XCTAssertEqual(Set(f.sent.map(\.identifier)).count, 3)
    }

    func testDeniedPermissionDoesNotConsumeFreshEventAndGrantReconsidersIt() async throws {
        let f = try fixture()
        let presenter = try f.presenter()
        await presenter.refreshPermission()
        f.status = .denied
        let item = f.item()
        f.bind(item)
        let delivery = presenter.updateSnapshot(f.snapshot([item]))
        await delivery?.value
        XCTAssertTrue(f.sent.isEmpty)
        f.status = .authorized
        await presenter.refreshPermission()
        XCTAssertEqual(f.sent.count, 1)
    }

    func testSnapshotAndCalendarChangesWhilePermissionAwaitsDoNotLoseRecap() async throws {
        let f = try fixture()
        let presenter = try f.presenter()
        let item = f.item()
        f.bind(item)
        let gate = RecapTestGate()
        f.beforeStatus = { await gate.wait() }
        presenter.updateSnapshot(f.snapshot([item]))
        await gate.untilWaiting()
        var snapshot = f.snapshot([item])
        snapshot.microphone = "Доступ разрешён"
        presenter.updateSnapshot(snapshot)
        presenter.clearCalendar()
        gate.release()
        await presenter.notifyReady()
        XCTAssertEqual(f.sent.count, 1)
    }

    func testCalendarChangesDuringSubmissionDoNotRemoveOrRepeatRecap() async throws {
        let f = try fixture()
        let presenter = try f.presenter()
        let item = f.item()
        f.bind(item)
        let gate = RecapTestGate()
        f.beforeSubmit = { await gate.wait() }
        let delivery = presenter.updateSnapshot(f.snapshot([item]))
        await gate.untilWaiting()
        presenter.clearCalendar()
        gate.release()
        await delivery?.value
        await presenter.notifyReady()
        let id = try XCTUnwrap(f.sent.first?.identifier)
        XCTAssertEqual(f.sent.count, 1)
        XCTAssertFalse(f.removed.contains(id))
    }

    func testLogoutDuringPermissionWaitCannotClaimOrDeliverToNewOwner() async throws {
        let f = try fixture()
        let presenter = try f.presenter()
        let item = f.item()
        f.bind(item)
        let gate = RecapTestGate()
        f.beforeStatus = { await gate.wait() }
        let delivery = presenter.updateSnapshot(f.snapshot([item]))
        await gate.untilWaiting()
        presenter.invalidate()
        presenter.updateContext(user: "other", workspace: "workspace")
        gate.release()
        await delivery?.value
        await presenter.notifyReady()
        XCTAssertTrue(f.sent.isEmpty)
        presenter.updateContext(user: "owner", workspace: "workspace")
        await presenter.notifyReady()
        XCTAssertEqual(f.sent.count, 1, "An invalidated permission lookup must not consume the event")
    }

    func testLogoutDuringSubmissionRemovesOldOwnerRequest() async throws {
        let f = try fixture()
        let presenter = try f.presenter()
        let item = f.item()
        f.bind(item)
        let gate = RecapTestGate()
        f.beforeSubmit = { await gate.wait() }
        let delivery = presenter.updateSnapshot(f.snapshot([item]))
        await gate.untilWaiting()
        presenter.invalidate()
        gate.release()
        // Wait for the held submit to complete and its post-await scope check.
        await delivery?.value
        XCTAssertTrue(f.removed.contains(try XCTUnwrap(f.sent.first?.identifier)))
    }

    func testRecapClickSurvivesCalendarRefreshButNotLogoutOrAccessRevocation() async throws {
        for change in ["calendar", "logout", "revoke", "revision"] {
            let f = try fixture()
            let presenter = try f.presenter()
            let item = f.item()
            f.bind(item)
            presenter.updateSnapshot(f.snapshot([item]))
            await presenter.notifyReady()
            let id = try XCTUnwrap(f.sent.first?.identifier)
            let gate = RecapTestGate()
            f.beforeReconcile = { await gate.wait() }
            var opened: [UUID] = []
            presenter.onOpenMeeting = { opened.append($0) }
            let click = Task { await presenter.openResponse(id) }
            await gate.untilWaiting()
            if change == "logout" { presenter.invalidate() }
            else if change == "revoke" { f.access = "revoked" }
            else if change == "revision" { f.revision = "replacement" }
            else { presenter.clearCalendar() }
            gate.release()
            await click.value
            XCTAssertEqual(opened.count, change == "calendar" ? 1 : 0, change)
        }
    }

    func testFreshnessAllowsBoundedClockSkewAndRejectsUnknownOrHistoricalMetadata() {
        let now = Date()
        let f = RecapDeliveryFixture(defaults: .standard) // Pure metadata checks; no store writes.
        for (offset, eligible) in [(-300.0, false), (-299.0, true), (60.0, true), (61.0, false)] {
            let item = f.item(at: now.addingTimeInterval(offset))
            XCTAssertEqual(DesktopNotificationPresenter.freshRecapID(item, context: f.context, now: now) != nil, eligible)
        }
        var item = f.item()
        item.serverTruth.summaryUpdatedAt = nil
        XCTAssertNil(DesktopNotificationPresenter.freshRecapID(item, context: f.context, now: now))
        item.serverTruth.summaryUpdatedAt = now
        item.serverTruth.transcriptAvailable = false
        XCTAssertNil(DesktopNotificationPresenter.freshRecapID(item, context: f.context, now: now))
        item.serverTruth.transcriptAvailable = true
        item.serverTruth.summaryEventId = "not-an-event-id"
        XCTAssertNil(DesktopNotificationPresenter.freshRecapID(item, context: f.context, now: now))
    }

    func testWidgetUsesTranscriptTruthNotReviewPageAccess() {
        let f = RecapDeliveryFixture(defaults: .standard)
        var item = f.item()
        var snapshot = f.snapshot([item])
        snapshot.session = CaptureSession(id: item.sessionId, mode: .audioRecording, state: .stopped,
            sourceAppEligibility: .eligible, policySnapshotRef: "fixture", triggerEvidence: [:],
            visibleIndicatorState: .hidden, stopActionAvailable: false, bufferSummaryId: nil,
            startedAt: Date(), stoppedAt: Date())
        for status in ["not_requested", "queued", "generating", "blocked_dependency", "failed", "available"] {
            item.serverTruth.summaryStatus = status
            item.serverTruth.transcriptAvailable = false
            snapshot.uploadItems = [item]
            XCTAssertEqual(snapshot.progressText, "Готовим расшифровку")
            item.serverTruth.transcriptAvailable = nil
            snapshot.uploadItems = [item]
            XCTAssertEqual(snapshot.progressText, "Проверяем готовность расшифровки")
        }
        item.serverTruth.transcriptAvailable = true
        item.serverTruth.summaryStatus = "queued"
        snapshot.uploadItems = [item]
        XCTAssertEqual(snapshot.progressText, "Расшифровка готова. Готовим итоги")
    }
}

@MainActor
private final class RecapDeliveryFixture {
    let context = "owner:workspace"
    let store: DesktopNotificationPreferencesStore
    var status: UNAuthorizationStatus = .authorized
    var sent: [UNNotificationRequest] = []
    var removed: [String] = []
    var beforeStatus: (@MainActor () async -> Void)?
    var beforeSubmit: (@MainActor () async -> Void)?
    var beforeReconcile: (@MainActor () async -> Void)?
    var access = "owner"
    var revision: String?

    init(defaults: UserDefaults) { store = .init(defaults: defaults) }
    func bind(_ item: DesktopUploadQueueItem) { store.bindSession(item.sessionId, context: context) }
    func item(id: String = "own", status: String = "available", at: Date = Date()) -> DesktopUploadQueueItem {
        custodyFixtureQueueItem(id: id, state: .uploaded,
            serverTruth: .init(meetingId: UUID().uuidString, mediaRevisionId: "revision", processingStatus: "processed",
                deletionState: "none", accessState: "owner", reviewAvailable: true, summaryStatus: status,
                transcriptAvailable: true, summaryEventId: UUID().uuidString, summaryUpdatedAt: at), updatedAt: Date())
    }
    func snapshot(_ items: [DesktopUploadQueueItem]) -> DesktopControlSnapshot {
        var result = DesktopControlSnapshot(); result.uploadItems = items; return result
    }
    func presenter(recaps: Bool = true) throws -> DesktopNotificationPresenter {
        var preferences = DesktopNotificationPreferences()
        preferences.recaps = recaps
        preferences.reminders = false
        try store.save(preferences, owner: "owner")
        let presenter = DesktopNotificationPresenter(store: store, model: DesktopControlModel(),
            status: { await self.beforeStatus?(); return self.status },
            submit: { request in self.sent.append(request); await self.beforeSubmit?() },
            remove: { ids in self.removed.append(contentsOf: ids ?? self.sent.map(\.identifier)) },
            reconcile: { item in
                await self.beforeReconcile?()
                var truth = item.serverTruth
                truth.accessState = self.access
                truth.mediaRevisionId = self.revision ?? truth.mediaRevisionId
                return DesktopUploadReconciliation(serverTruth: truth, conflictState: .none, conflictReason: nil, nextAction: nil)
            })
        presenter.updateContext(user: "owner", workspace: "workspace")
        return presenter
    }
}

@MainActor
private final class RecapTestGate {
    private var released = false
    private var waiting: [CheckedContinuation<Void, Never>] = []
    private var entered: CheckedContinuation<Void, Never>?
    func wait() async {
        guard !released else { return }
        await withCheckedContinuation { waiting.append($0); entered?.resume(); entered = nil }
    }
    func untilWaiting() async {
        guard waiting.isEmpty else { return }
        await withCheckedContinuation { entered = $0 }
    }
    func release() {
        released = true
        waiting.forEach { $0.resume() }; waiting.removeAll()
    }
}
