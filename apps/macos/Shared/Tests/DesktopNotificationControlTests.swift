import Foundation
import XCTest
import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopNotificationControlTests: XCTestCase {
    func testDeviceNavigationDoesNotMutateCapture() {
        let model = DesktopControlModel()
        var actions: [DesktopControlAction] = []
        model.onAction = { actions.append($0) }
        let snapshot = model.snapshot
        model.send(.localRecordings)
        XCTAssertEqual(model.snapshot, snapshot)
        XCTAssertEqual(actions, [.localRecordings])
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
}
