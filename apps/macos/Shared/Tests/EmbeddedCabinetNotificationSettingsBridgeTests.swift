import Foundation
import WebKit
import UserNotifications
import XCTest
@testable import TwoBrainRecAppCore

@MainActor
final class EmbeddedCabinetNotificationSettingsBridgeTests: XCTestCase {
    private static var retainedViews: [WKWebView] = []

    func testActualWebKitEditsConfirmedFieldsAndClearsOnAccountChange() async throws {
        let suite = "F260-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel(), status: { .denied })
        presenter.updateContext(user: "a", workspace: "w")
        let url = URL(string: "https://graf.test/desktop/settings/notifications")!
        let bridge = EmbeddedCabinetNotificationSettingsBridge(routePolicy: .init(baseURL: url), presenter: presenter)
        let config = WKWebViewConfiguration(); config.websiteDataStore = .nonPersistent()
        config.userContentController.addScriptMessageHandler(bridge, contentWorld: .page, name: EmbeddedCabinetNotificationSettingsBridge.handlerName)
        let web = WKWebView(frame: CGRect(x: 0, y: 0, width: 820, height: 600), configuration: config)
        Self.retainedViews.append(web)
        defer { bridge.invalidate(); config.userContentController.removeScriptMessageHandler(forName: EmbeddedCabinetNotificationSettingsBridge.handlerName, contentWorld: .page) }
        let repo = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let base = repo.appendingPathComponent("apps/server/src/twobrain_rec_server/cabinet")
        let template = try String(contentsOf: base.appendingPathComponent("templates/cabinet/pages/settings_notifications_content.html"), encoding: .utf8)
        let html = try XCTUnwrap(template.components(separatedBy: "{% if embedded %}").last?.components(separatedBy: "{% else %}").first)
        let script = try String(contentsOf: base.appendingPathComponent("static/cabinet/cabinet.js"), encoding: .utf8)
        web.loadHTMLString("<!doctype html><body>\(html)<script>\(script)</script></body>", baseURL: url)
        try await wait("document.querySelector('[data-local-notification-settings]')?.dataset.ready === 'true'", web)
        bridge.activate(web)
        try await wait("!document.querySelector('[data-local-notification-controls]').disabled", web)
        _ = try await web.evaluateJavaScript("const sound=document.querySelector('[data-local-notification-field=sound]');sound.focus();sound.checked=true;sound.dispatchEvent(new Event('change',{bubbles:true}));")
        try await wait("!document.querySelector('[data-local-notification-controls]').disabled", web)
        XCTAssertTrue(presenter.preferences.sound)
        XCTAssertFalse(presenter.preferences.showTitles)
        var value = presenter.preferences; value.showTitles = true; presenter.save(value)
        try await wait("document.querySelector('[data-local-notification-field=showTitles]').checked", web)
        let focus = try await web.evaluateJavaScript("document.activeElement.dataset.localNotificationField")
        XCTAssertEqual(focus as? String, "sound")
        presenter.updateContext(user: "b", workspace: "w")
        try await wait("document.querySelector('[data-local-notification-controls]').disabled && !document.querySelector('[data-local-notification-field=sound]').checked", web)
        XCTAssertFalse(presenter.preferences.sound)
    }

    func testAccountChangeWhileActivationWaitsCannotReconnectOldDocument() async throws {
        let suite = "F260-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let gate = NotificationSettingsGate()
        let user = UUID(), workspace = UUID()
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel(),
            status: { .denied }, contextProvider: {
                await gate.wait()
                return DesktopNotificationContext(user_id: user, workspace_id: workspace)
            })
        let url = URL(string: "https://graf.test/desktop/settings/notifications")!
        let bridge = EmbeddedCabinetNotificationSettingsBridge(routePolicy: .init(baseURL: url), presenter: presenter)
        let configuration = WKWebViewConfiguration(); configuration.websiteDataStore = .nonPersistent()
        let web = WKWebView(frame: .zero, configuration: configuration)
        Self.retainedViews.append(web)
        defer { bridge.invalidate() }
        web.loadHTMLString("<script>window.connections=0;window.GRAFNotificationSettings={connect(){connections++},disconnect(){}};</script>", baseURL: url)
        try await wait("typeof window.connections === 'number'", web)
        let epoch = presenter.authEpoch
        let pending = Task { await bridge.activateAfterRefreshingContext(web, expectedAuthEpoch: epoch, isCurrentDocument: { true }) }
        await gate.untilWaiting()
        presenter.invalidate()
        presenter.updateContext(user: UUID().uuidString, workspace: workspace.uuidString)
        gate.release(); await pending.value
        let connections = try await web.evaluateJavaScript("connections")
        XCTAssertEqual(connections as? Int, 0)
        // A fresh document may establish its initial owner during refresh.
        let currentEpoch = presenter.authEpoch
        let fresh = Task { await bridge.activateAfterRefreshingContext(web, expectedAuthEpoch: currentEpoch, isCurrentDocument: { true }) }
        await gate.untilWaiting(); gate.release(); await fresh.value
        try await wait("connections === 1", web)
        XCTAssertEqual(presenter.owner, user.uuidString.lowercased())
        // A task queued before an auth change must not start a new request either.
        await bridge.activateAfterRefreshingContext(web, expectedAuthEpoch: epoch, isCurrentDocument: { true })
        XCTAssertNil(gate.waiting)
    }

    private func wait(_ condition: String, _ web: WKWebView) async throws {
        for _ in 0..<100 {
            if (try? await web.evaluateJavaScript(condition)) as? Bool == true { return }
            try await Task.sleep(for: .milliseconds(50))
        }
        XCTFail("Condition timed out: \(condition)")
        throw CocoaError(.fileReadUnknown)
    }

    func testBoundaryRejectsUntrustedDocumentsAndMalformedPatches() {
        let url = URL(string: "https://graf.test/desktop/settings/notifications")!
        let policy = DesktopCabinetRoutePolicy(baseURL: url)
        let valid: [String: Any] = ["version": 1, "nonce": "current", "action": "set", "field": "sound", "value": true]
        func allowed(_ body: [String: Any], _ source: URL? = nil, _ main: Bool = true, _ loading: Bool = false, _ nonce: String? = "current") -> Bool {
            EmbeddedCabinetNotificationSettingsBridge.allowedRequest(body, sourceURL: source ?? url, currentURL: url, isMainFrame: main, isLoading: loading, nonce: nonce, routePolicy: policy) != nil
        }
        XCTAssertTrue(allowed(valid))
        for path in ["http://graf.test/desktop/settings/notifications", "https://other.test/desktop/settings/notifications", "https://graf.test:444/desktop/settings/notifications", "https://graf.test/desktop/settings/notifications?x=1", "https://graf.test/desktop/settings/notifications#x", "https://graf.test/desktop/settings/%6Eotifications", "https://graf.test/desktop/settings/account"] {
            XCTAssertFalse(allowed(valid, URL(string: path)), path)
        }
        XCTAssertFalse(allowed(valid, nil, false)); XCTAssertFalse(allowed(valid, nil, true, true)); XCTAssertFalse(allowed(valid, nil, true, false, "old"))
        for patch in [["value": "true"], ["value": 1], ["field": "owner"], ["extra": true], ["version": true], ["field": "offsetMinutes", "value": 2], ["field": "offsetMinutes", "value": true]] as [[String: Any]] {
            XCTAssertFalse(allowed(valid.merging(patch) { _, new in new }))
        }
        XCTAssertTrue(allowed(valid.merging(["field": "offsetMinutes", "value": 5]) { _, new in new }))
    }

    func testPatchUsesCurrentPreferencesAndRejectsOldAuthEpoch() async throws {
        let suite = "F260-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel(), status: { .denied })
        presenter.updateContext(user: "a", workspace: "w")
        let epoch = presenter.authEpoch
        let bridge = EmbeddedCabinetNotificationSettingsBridge(routePolicy: .init(baseURL: URL(string: "https://graf.test")!), presenter: presenter)
        var value = presenter.preferences; value.showTitles = true
        XCTAssertTrue(presenter.save(value))
        let request = EmbeddedCabinetNotificationSettingsBridge.Request(version: 1, nonce: "n", action: "set", field: "sound", value: .bool(false))
        _ = try await bridge.response(to: request, epoch: epoch)
        XCTAssertTrue(presenter.preferences.showTitles); XCTAssertFalse(presenter.preferences.sound)
        presenter.updateContext(user: "b", workspace: "w"); presenter.updateContext(user: "a", workspace: "w")
        do { _ = try await bridge.response(to: request, epoch: epoch); XCTFail("Old epoch accepted") } catch {}
        presenter.invalidate()
        XCTAssertFalse(presenter.save(value))
    }

    func testLogoutWhilePermissionOrTestIsPendingHasNoLateEffects() async throws {
        for action in ["permission", "test"] {
            let suite = "F260-\(UUID().uuidString)"
            let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
            defer { defaults.removePersistentDomain(forName: suite) }
            let gate = NotificationSettingsGate()
            var sent: [String] = [], removed: [String] = []
            let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel(), status: { .authorized },
                submit: { request in sent.append(request.identifier); await gate.wait() },
                remove: { removed.append(contentsOf: $0 ?? sent) },
                requestPermission: { await gate.wait(); return true })
            presenter.updateContext(user: "a", workspace: "w")
            let task = Task { if action == "test" { await presenter.test() } else { await presenter.enable() } }
            await gate.untilWaiting()
            presenter.invalidate(); gate.release(); await task.value
            XCTAssertEqual(presenter.message, "")
            XCTAssertTrue(sent.allSatisfy { removed.contains($0) })
        }
    }
}

@MainActor
private final class NotificationSettingsGate {
    var waiting: CheckedContinuation<Void, Never>?
    var entered: CheckedContinuation<Void, Never>?
    func wait() async { await withCheckedContinuation { waiting = $0; entered?.resume(); entered = nil } }
    func untilWaiting() async { if waiting == nil { await withCheckedContinuation { entered = $0 } } }
    func release() { waiting?.resume(); waiting = nil }
}
