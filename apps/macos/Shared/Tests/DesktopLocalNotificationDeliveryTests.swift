import Foundation
import UserNotifications
import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopLocalNotificationDeliveryTests: XCTestCase {
    private func fixture() throws -> LocalDeliveryFixture {
        let name = "graf-local-delivery-\(UUID())"
        addTeardownBlock { UserDefaults(suiteName: name)?.removePersistentDomain(forName: name) }
        return LocalDeliveryFixture(defaults: try XCTUnwrap(UserDefaults(suiteName: name)))
    }

    func testNotificationTargetIsVisibleEvenWhenAnotherFailureLeadsItsGroup() throws {
        let f = try fixture()
        let items = (0..<12).map { f.item(id: "failure-\($0)") }
        let target = items[11]
        let summaries = DesktopUploadCustodySummary.summaries(for: items, focusedSessionID: target.sessionId)
        XCTAssertEqual(summaries.first?.primaryItem.sessionId, target.sessionId)
        XCTAssertTrue(summaries.first?.affectedItems.allSatisfy { $0.sessionId == target.sessionId } == true)
        XCTAssertFalse(summaries.dropFirst().flatMap(\.affectedItems).contains { $0.sessionId == target.sessionId })
        f.model.showRecording(target.sessionId)
        let request = f.model.recordingNavigationRequest
        f.model.showRecording(target.sessionId)
        XCTAssertGreaterThan(f.model.recordingNavigationRequest, request)
    }

    func testReadyResultsAndTerminalProcessingStayInCabinet() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        var items = (0..<12).map { f.item(id: "ready-\($0)", state: .uploaded) }
        for index in items.indices {
            items[index].serverTruth = .init(meetingId: UUID().uuidString, processingStatus: "processed",
                deletionState: "none", accessState: "owner", reviewAvailable: true,
                summaryStatus: "available", transcriptAvailable: true)
            f.bind(items[index])
        }
        await presenter.updateSnapshot(f.snapshot(items))?.value
        XCTAssertTrue(f.sent.isEmpty)
        items[0].syncConflictState = .processingFailed
        await presenter.updateSnapshot(f.snapshot(items))?.value
        XCTAssertTrue(f.sent.isEmpty)
    }

    func testForeignAndHistoricalIncidentsDoNotHideCurrentOwnedFailureWithoutCalendar() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let foreign = f.item(id: "foreign")
        f.store.bindSession(foreign.sessionId, context: "other:workspace")
        let old = (0..<8).map { f.item(id: "old-\($0)", at: Date().addingTimeInterval(-3600)) }
        let own = f.item(id: "own")
        (old + [own]).forEach(f.bind)
        await presenter.updateSnapshot(f.snapshot([foreign] + old + [own]))?.value
        XCTAssertEqual(f.sent.map(\.identifier), ["graf.local.capture." + own.sessionId])
        await presenter.refreshLocal(f.snapshot([foreign] + old + [own]))
        XCTAssertEqual(f.sent.count, 1)
    }

    func testDeniedPermissionCanReconsiderUnclaimedIncident() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        f.status = .denied
        await presenter.updateSnapshot(f.snapshot([item]))?.value
        XCTAssertTrue(f.sent.isEmpty)
        f.status = .authorized
        await presenter.refreshPermission()
        XCTAssertEqual(f.sent.count, 1)
        await presenter.refreshPermission()
        XCTAssertEqual(f.sent.count, 1)
    }

    func testSnapshotAndCalendarChangesDuringPermissionWaitKeepCurrentIncident() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        let gate = LocalDeliveryGate()
        f.beforeStatus = { await gate.wait() }
        let first = presenter.updateSnapshot(f.snapshot([item]))
        await gate.untilWaiting()
        var latest = f.snapshot([item]); latest.transitioning = true
        let second = presenter.updateSnapshot(latest)
        presenter.clearCalendar()
        gate.release()
        await first?.value; await second?.value
        XCTAssertEqual(f.sent.count, 1)
    }

    func testLogoutDuringPermissionDoesNotConsumeOrDeliverOldOwnerIncident() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        let gate = LocalDeliveryGate()
        f.beforeStatus = { await gate.wait() }
        let delivery = presenter.updateSnapshot(f.snapshot([item]))
        await gate.untilWaiting()
        presenter.invalidate()
        presenter.updateContext(user: "other", workspace: "workspace")
        gate.release()
        await delivery?.value
        XCTAssertTrue(f.sent.isEmpty)
        presenter.updateContext(user: "owner", workspace: "workspace")
        await presenter.refreshLocal(f.snapshot([item]))
        XCTAssertEqual(f.sent.count, 1)
    }

    func testCalendarRefreshDuringSubmitDoesNotRemoveButLogoutDoes() async throws {
        for logout in [false, true] {
            let f = try fixture()
            let presenter = f.presenter()
            let item = f.item()
            f.bind(item)
            let gate = LocalDeliveryGate()
            f.beforeSubmit = { await gate.wait() }
            let delivery = presenter.updateSnapshot(f.snapshot([item]))
            await gate.untilWaiting()
            if logout { presenter.invalidate() } else { presenter.clearCalendar() }
            gate.release()
            await delivery?.value
            let id = try XCTUnwrap(f.sent.first?.identifier)
            XCTAssertEqual(f.removed.contains(id), logout)
        }
    }

    func testClickTargetsItsRecordingAndResolvedOrForeignClickDoesNothing() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        await presenter.updateSnapshot(f.snapshot([item]))?.value
        let id = try XCTUnwrap(f.sent.first?.identifier)
        presenter.openResponse(id, actionIdentifier: UNNotificationDefaultActionIdentifier)
        XCTAssertEqual(f.actions, [.localRecording(item.sessionId)])
        var recovered = item; recovered.state = .queued
        await presenter.updateSnapshot(f.snapshot([recovered]))?.value
        presenter.openResponse(id, actionIdentifier: UNNotificationDefaultActionIdentifier)
        XCTAssertEqual(f.actions.count, 1)
        presenter.invalidate()
        presenter.openResponse(id, actionIdentifier: UNNotificationDefaultActionIdentifier)
        XCTAssertEqual(f.actions.count, 1)
    }
}

@MainActor
private final class LocalDeliveryFixture {
    let context = "owner:workspace"
    let store: DesktopNotificationPreferencesStore
    let model = DesktopControlModel()
    var status: UNAuthorizationStatus = .authorized
    var sent: [UNNotificationRequest] = []
    var removed: [String] = []
    var actions: [DesktopControlAction] = []
    var beforeStatus: (@MainActor () async -> Void)?
    var beforeSubmit: (@MainActor () async -> Void)?
    init(defaults: UserDefaults) { store = .init(defaults: defaults) }
    func bind(_ item: DesktopUploadQueueItem) { store.bindSession(item.sessionId, context: context) }
    func item(id: String = "own", state: UploadItemState = .failed, at: Date = Date()) -> DesktopUploadQueueItem {
        custodyFixtureQueueItem(id: id, state: state, updatedAt: at)
    }
    func snapshot(_ items: [DesktopUploadQueueItem]) -> DesktopControlSnapshot {
        var result = DesktopControlSnapshot(); result.uploadItems = items; return result
    }
    func presenter() -> DesktopNotificationPresenter {
        model.onAction = { self.actions.append($0) }
        let presenter = DesktopNotificationPresenter(store: store, model: model,
            status: { await self.beforeStatus?(); return self.status },
            submit: { request in self.sent.append(request); await self.beforeSubmit?() },
            remove: { ids in self.removed.append(contentsOf: ids ?? self.sent.map(\.identifier)) })
        presenter.updateContext(user: "owner", workspace: "workspace")
        return presenter
    }
}

@MainActor
private final class LocalDeliveryGate {
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
