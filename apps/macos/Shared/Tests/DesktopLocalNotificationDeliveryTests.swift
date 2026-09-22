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

    // Проверка из настроек показывает ту же карточку, что и настоящее
    // напоминание, но остаётся безопасным предпросмотром без побочных эффектов.
    func testGeneratedTestNotificationShowsTheCardAndOpensSettings() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        var preferences = presenter.preferences; preferences.sound = true
        XCTAssertTrue(presenter.save(preferences))
        var settingsOpened = 0
        presenter.onOpenSettings = { settingsOpened += 1 }
        defer { presenter.card.dismiss() }
        await presenter.test()
        XCTAssertTrue(presenter.card.isVisible, "проверка обязана показать карточку")
        XCTAssertEqual(presenter.card.presentedContent,
                       .preview(title: "Проверка уведомлений GRAF",
                                message: "Так выглядит напоминание о встрече."))
        XCTAssertTrue(f.sent.isEmpty, "предпросмотр не отправляет системный запрос")
        XCTAssertTrue(f.removed.isEmpty, "предпросмотр не удаляет системные запросы")
        let panel = try XCTUnwrap(presenter.card.window)
        XCTAssertEqual(panel.identifier?.rawValue, "graf-notification-card")
        XCTAssertEqual(panel.frame.width, DesktopNotificationCardPresenter.windowWidth)
        XCTAssertFalse(panel.canBecomeKey)
        // Системный баннер не отправляется: проверка показывает поверхность GRAF.
        XCTAssertNil(f.sent.last?.identifier)
        XCTAssertTrue(DesktopNotificationPresenter.isTestNotification("graf.local.test"))
        XCTAssertEqual(settingsOpened, 0)
    }

    func testProblemIncidentUsesCardWithoutSystemSubmission() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        let task = presenter.updateSnapshot(f.snapshot([item]))
        await task?.value
        XCTAssertTrue(f.sent.isEmpty, "проблема показывается карточкой без системного баннера")
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")
    }

    func testCardBrokerKeepsHigherPriorityProblemAndDoesNotConsumeHiddenIncident() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        await presenter.updateSnapshot(f.snapshot([item]))?.value
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")

        XCTAssertFalse(presenter.presentPreview(title: "Проверка", message: "Предпросмотр"),
                       "предпросмотр не должен молча заменять проблему записи")
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")
    }

    func testShortRecordingNoticeUsesTheSameBrokerAsOtherCards() throws {
        let f = try fixture()
        let presenter = f.presenter()
        let notice = DesktopRecordingNoticePresenter(presenter: presenter)
        notice.showShortRecordingDiscarded()
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.short-recording")
        XCTAssertFalse(presenter.presentPreview(title: "Проверка", message: "Предпросмотр"),
                       "предпросмотр не должен заменять важное сообщение")
        XCTAssertEqual(notice.presentedContent?.identifier, "graf.card.short-recording")
        notice.dismiss()
        XCTAssertNil(presenter.card.presentedContent)
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
        for item in old + [own] { f.bind(item) }
        await presenter.updateSnapshot(f.snapshot([foreign] + old + [own]))?.value
        XCTAssertTrue(f.sent.isEmpty)
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")
        await presenter.refreshLocal(f.snapshot([foreign] + old + [own]))
        XCTAssertTrue(f.sent.isEmpty)
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")
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
        await presenter.refreshLocal(f.snapshot([item]))
        XCTAssertTrue(f.sent.isEmpty)
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")
        await presenter.refreshLocal(f.snapshot([item]))
        XCTAssertTrue(f.sent.isEmpty)
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")
    }

    func testSnapshotAndCalendarChangesKeepCurrentIncident() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        let first = presenter.updateSnapshot(f.snapshot([item]))
        var latest = f.snapshot([item]); latest.transitioning = true
        let second = presenter.updateSnapshot(latest)
        presenter.clearCalendar()
        _ = await first?.value
        _ = await second?.value
        XCTAssertTrue(f.sent.isEmpty)
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")
    }

    func testLogoutDoesNotConsumeOrDeliverOldOwnerIncident() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        let delivery = presenter.updateSnapshot(f.snapshot([item]))
        presenter.invalidate()
        _ = await delivery?.value
        XCTAssertTrue(f.sent.isEmpty)
        XCTAssertNil(presenter.card.presentedContent)
        presenter.updateContext(user: "other", workspace: "workspace")
        await presenter.refreshLocal(f.snapshot([item]))
        XCTAssertTrue(f.sent.isEmpty)
        XCTAssertNil(presenter.card.presentedContent)
    }

    func testCalendarRefreshAndLogoutDoNotCreateSystemIncidentRequests() async throws {
        for logout in [false, true] {
            let f = try fixture()
            let presenter = f.presenter()
            let item = f.item()
            f.bind(item)
            let delivery = presenter.updateSnapshot(f.snapshot([item]))
            if logout {
                presenter.invalidate()
            } else {
                presenter.clearCalendar()
            }
            await delivery?.value
            XCTAssertTrue(f.sent.isEmpty)
            XCTAssertTrue(f.removed.isEmpty)
            if logout {
                XCTAssertFalse(presenter.card.isVisible)
            }
        }
    }

    func testClickTargetsItsRecordingAndResolvedOrForeignClickDoesNothing() async throws {
        let f = try fixture()
        let presenter = f.presenter()
        let item = f.item()
        f.bind(item)
        await presenter.updateSnapshot(f.snapshot([item]))?.value
        XCTAssertTrue(f.sent.isEmpty)
        XCTAssertEqual(presenter.card.presentedContent?.identifier, "graf.card.problem")
        presenter.openResponse("graf.local.capture.\(item.sessionId)", actionIdentifier: UNNotificationDefaultActionIdentifier)
        XCTAssertEqual(f.actions, [.localRecording(item.sessionId)])
        var recovered = item; recovered.state = .queued
        await presenter.updateSnapshot(f.snapshot([recovered]))?.value
        presenter.openResponse("graf.local.capture.\(item.sessionId)", actionIdentifier: UNNotificationDefaultActionIdentifier)
        XCTAssertEqual(f.actions.count, 1)
        presenter.invalidate()
        presenter.openResponse("graf.local.capture.\(item.sessionId)", actionIdentifier: UNNotificationDefaultActionIdentifier)
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
