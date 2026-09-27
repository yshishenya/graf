import Foundation
import WebKit
import XCTest
@testable import TwoBrainRecAppCore

@MainActor
final class EmbeddedCabinetNotificationSettingsBridgeTests: XCTestCase {
    private static var retainedViews: [WKWebView] = []

    func testNativeFallbackKeepsTheFivePreferenceContractWithoutSystemPermissionUI() throws {
        let repo = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let source = try String(contentsOf: repo.appendingPathComponent("apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift"), encoding: .utf8)
        let declaration = try XCTUnwrap(source.range(of: "public struct DesktopNotificationsSettingsView: View"))
        let fallback = String(source[declaration.lowerBound...])
        for field in ["reminders", "offsetMinutes", "showTitles", "sound", "quiet"] {
            XCTAssertTrue(fallback.contains(".\(field)"), "Native fallback must expose \(field)")
        }
        for label in ["Тихий режим", "Проверить уведомление", "Когда напоминать"] {
            XCTAssertTrue(fallback.contains(label), "Native fallback must retain \(label)")
        }
        for api in ["saveDraft", "testNotification", "canEdit"] {
            XCTAssertTrue(fallback.contains(api), "Native fallback must use \(api)")
        }
        for retired in ["permissionText", "canRequestPermission", "refreshPermission", "requestPermission", "openSystemSettings", "x-apple.systempreferences", "Timer.publish"] {
            XCTAssertFalse(fallback.contains(retired), "Retired permission UI/polling: \(retired)")
        }
    }

    func testActualWebKitEditsConfirmedFieldsAndClearsOnAccountChange() async throws {
        let suite = "F260-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel())
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
        // Template rendering is covered by the browser suite; this fixture exercises the real WK bridge.
        let html = """
        <div data-local-notification-settings>
          <fieldset data-local-notification-controls disabled>
            <input type="checkbox" data-local-notification-field="reminders">
            <select data-settings-combobox aria-label="Когда напоминать" data-local-notification-field="offsetMinutes"><option value="0">Сейчас</option><option value="1">За минуту</option><option value="5">За 5 минут</option></select>
            <input type="checkbox" data-local-notification-field="showTitles">
            <input type="checkbox" data-local-notification-field="sound">
            <input type="checkbox" data-local-notification-field="quiet">
            <button data-local-notification-action="test">Проверить уведомление</button>
          </fieldset>
          <p data-local-notification-status></p><button data-local-notification-retry></button><a data-local-notification-reload></a>
        </div>
        """
        let script = try String(contentsOf: base.appendingPathComponent("static/cabinet/cabinet.js"), encoding: .utf8)
        let autosave = try String(contentsOf: base.appendingPathComponent("static/cabinet/settings-autosave.js"), encoding: .utf8)
        web.loadHTMLString("<!doctype html><body>\(html)<meta name='graf-time-user' content='a'><meta name='graf-workspace' content='w'><script>\(autosave)</script><script>\(script)</script></body>", baseURL: url)
        try await wait("document.querySelector('[data-local-notification-settings]')?.dataset.ready === 'true'", web)
        bridge.activate(web)
        try await wait("!document.querySelector('[data-local-notification-controls]').disabled", web)
        _ = try await web.evaluateJavaScript("const sound=document.querySelector('[data-local-notification-field=sound]');sound.focus();sound.checked=true;sound.dispatchEvent(new Event('change',{bubbles:true}));")
        try await wait("!document.querySelector('[data-local-notification-controls]').disabled", web)
        let flushed = try await web.callAsyncJavaScript("return await GRAFSettings.flushAll()", arguments: [:], in: nil, contentWorld: .page)
        XCTAssertEqual(flushed as? Bool, true)
        XCTAssertTrue(presenter.preferences.sound)
        XCTAssertFalse(presenter.preferences.showTitles)
        _ = try await web.evaluateJavaScript("const quiet=document.querySelector('[data-local-notification-field=quiet]');quiet.checked=true;quiet.dispatchEvent(new Event('change',{bubbles:true}));")
        let quietFlushed = try await web.callAsyncJavaScript("return await GRAFSettings.flushAll()", arguments: [:], in: nil, contentWorld: .page)
        XCTAssertEqual(quietFlushed as? Bool, true)
        let snapshot = try await bridge.response(to: .init(version: 2, nonce: "n", action: "read", field: nil, value: nil), epoch: presenter.authEpoch)
        XCTAssertEqual((snapshot["preferences"] as? [String: Any])?["quiet"] as? Bool, true)
        var value = presenter.preferences; value.showTitles = true; presenter.draft = value
        XCTAssertTrue(presenter.saveDraft())
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
            contextProvider: {
                await gate.wait()
                return DesktopNotificationContext(user_id: user, workspace_id: workspace, recording_deletion_protocol_version: nil)
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

    func testSettingsExitFlushesTheBrowserQueueAndKeepsFailedDraftUntilDiscarded() async throws {
        let config = WKWebViewConfiguration(); config.websiteDataStore = .nonPersistent()
        let web = WKWebView(frame: .zero, configuration: config)
        Self.retainedViews.append(web)
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let script = try String(contentsOf: root.appendingPathComponent("apps/server/src/twobrain_rec_server/cabinet/static/cabinet/settings-autosave.js"), encoding: .utf8)
        web.loadHTMLString("<meta name='graf-time-user' content='a'><meta name='graf-workspace' content='w'><script>\(script)</script>", baseURL: URL(string: "https://graf.test/desktop/settings/account"))
        try await wait("typeof window.GRAFSettings === 'object'", web)
        _ = try await web.evaluateJavaScript("""
          window.saved='old'; window.fail=false;
          window.queue=GRAFSettings.create('test', {initial:{name:'old'},
            async save(fields){await new Promise(r=>setTimeout(r,30));if(window.fail)throw Error('offline');window.saved=fields.name;return {saved:true,actor:'a',workspace:'w',values:fields};},
            async load(){return {values:{name:window.saved}};}
          });queue.edit({name:'new'},500); true;
        """)
        let flushed = await EmbeddedCabinetWebView.prepareSettingsToLeave(in: web)
        XCTAssertTrue(flushed)
        let saved = try await web.evaluateJavaScript("window.saved")
        XCTAssertEqual(saved as? String, "new")
        _ = try await web.evaluateJavaScript("window.fail=true;window.confirm=()=>false;queue.edit({name:'draft'}); true;")
        let retained = await EmbeddedCabinetWebView.prepareSettingsToLeave(in: web)
        XCTAssertFalse(retained)
        let pending = try await web.evaluateJavaScript("GRAFSettings.pending()")
        XCTAssertEqual(pending as? Bool, true)
        _ = try await web.evaluateJavaScript("window.confirm=()=>true;true;")
        let discarded = await EmbeddedCabinetWebView.prepareSettingsToLeave(in: web)
        XCTAssertTrue(discarded)
    }

    private func wait(_ condition: String, _ web: WKWebView) async throws {
        var lastJSError: (domain: String, code: Int)?
        var lastBooleanResult: Bool?
        var lastIsLoading = web.isLoading
        for _ in 0..<100 {
            do {
                lastBooleanResult = try await web.evaluateJavaScript(condition) as? Bool
                if lastBooleanResult == true { return }
            } catch {
                let jsError = error as NSError
                lastJSError = (domain: jsError.domain, code: jsError.code)
            }
            lastIsLoading = web.isLoading
            try await Task.sleep(for: .milliseconds(50))
        }
        let jsErrorSummary = lastJSError.map { "domain=\($0.domain), code=\($0.code)" } ?? "none"
        let booleanSummary = lastBooleanResult.map { String($0) } ?? "nil"
        // XCTUnwrap records one failure and aborts the test with XCTest's own error.
        _ = try XCTUnwrap(nil as Bool?, "Condition timed out after 100 attempts at 50 ms: \(condition); lastJSError=\(jsErrorSummary); lastBooleanResult=\(booleanSummary); isLoading=\(lastIsLoading)")
    }

    func testBoundaryRejectsUntrustedDocumentsAndMalformedPatches() {
        let url = URL(string: "https://graf.test/desktop/settings/notifications")!
        let policy = DesktopCabinetRoutePolicy(baseURL: url)
        let valid: [String: Any] = ["version": 2, "nonce": "current", "action": "set", "field": "sound", "value": true]
        func allowed(_ body: [String: Any], _ source: URL? = nil, _ main: Bool = true, _ loading: Bool = false, _ nonce: String? = "current") -> Bool {
            EmbeddedCabinetNotificationSettingsBridge.allowedRequest(body, sourceURL: source ?? url, currentURL: url, isMainFrame: main, isLoading: loading, nonce: nonce, routePolicy: policy) != nil
        }
        XCTAssertTrue(allowed(valid))
        for path in ["http://graf.test/desktop/settings/notifications", "https://other.test/desktop/settings/notifications", "https://graf.test:444/desktop/settings/notifications", "https://graf.test/desktop/settings/notifications?x=1", "https://graf.test/desktop/settings/notifications#x", "https://graf.test/desktop/settings/%6Eotifications", "https://graf.test/desktop/settings/account"] {
            XCTAssertFalse(allowed(valid, URL(string: path)), path)
        }
        XCTAssertFalse(allowed(valid, nil, false)); XCTAssertFalse(allowed(valid, nil, true, true)); XCTAssertFalse(allowed(valid, nil, true, false, "old"))
        for patch in [["value": "true"], ["value": 1], ["field": "owner"], ["extra": true], ["version": true], ["version": 1], ["version": 3], ["field": "offsetMinutes", "value": 2], ["field": "offsetMinutes", "value": true]] as [[String: Any]] {
            XCTAssertFalse(allowed(valid.merging(patch) { _, new in new }))
        }
        for field in ["reminders", "showTitles", "sound", "quiet"] {
            for value in [true, false] {
                XCTAssertTrue(allowed(valid.merging(["field": field, "value": value]) { _, new in new }))
            }
        }
        for minutes in [0, 1, 5] {
            XCTAssertTrue(allowed(valid.merging(["field": "offsetMinutes", "value": minutes]) { _, new in new }))
        }
        for action in ["read", "test"] {
            let request: [String: Any] = ["version": 2, "nonce": "current", "action": action]
            XCTAssertTrue(allowed(request))
            for extra in [["field": "quiet"], ["value": false], ["extra": NSNull()]] as [[String: Any]] {
                XCTAssertFalse(allowed(request.merging(extra) { _, new in new }), "\(action) rejects extra fields")
            }
        }
        for action in ["requestPermission", "openSystemSettings", "permission", "unknown"] {
            XCTAssertFalse(allowed(["version": 2, "nonce": "current", "action": action]))
        }
        XCTAssertNil(EmbeddedCabinetNotificationSettingsBridge.allowedRequest(valid, sourceURL: url,
            currentURL: URL(string: "https://other.test/desktop/settings/notifications"), isMainFrame: true,
            isLoading: false, nonce: "current", routePolicy: policy))
        XCTAssertFalse(allowed(valid, nil, true, false, nil))
    }

    func testPatchUsesCurrentPreferencesAndRejectsOldAuthEpoch() async throws {
        let suite = "F260-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel())
        presenter.updateContext(user: "a", workspace: "w")
        let epoch = presenter.authEpoch
        let bridge = EmbeddedCabinetNotificationSettingsBridge(routePolicy: .init(baseURL: URL(string: "https://graf.test")!), presenter: presenter)
        var value = presenter.preferences; value.showTitles = true
        presenter.draft = value
        XCTAssertTrue(presenter.saveDraft())
        let request = EmbeddedCabinetNotificationSettingsBridge.Request(version: 2, nonce: "n", action: "set", field: "sound", value: .bool(false))
        _ = try await bridge.response(to: request, epoch: epoch)
        XCTAssertTrue(presenter.preferences.showTitles); XCTAssertFalse(presenter.preferences.sound)
        let quiet = EmbeddedCabinetNotificationSettingsBridge.Request(version: 2, nonce: "n", action: "set", field: "quiet", value: .bool(true))
        _ = try await bridge.response(to: quiet, epoch: epoch)
        XCTAssertTrue(presenter.preferences.quiet)
        XCTAssertTrue(presenter.preferences.showTitles)
        for minutes in [0, 1, 5] {
            let offset = EmbeddedCabinetNotificationSettingsBridge.Request(version: 2, nonce: "n", action: "set", field: "offsetMinutes", value: .minutes(minutes))
            _ = try await bridge.response(to: offset, epoch: epoch)
            XCTAssertEqual(presenter.preferences.offsetMinutes, minutes)
            XCTAssertTrue(presenter.preferences.quiet)
        }
        presenter.updateContext(user: "b", workspace: "w"); presenter.updateContext(user: "a", workspace: "w")
        do { _ = try await bridge.response(to: request, epoch: epoch); XCTFail("Old epoch accepted") } catch {}
        XCTAssertTrue(presenter.preferences.quiet, "The current owner retains its saved preference")
        presenter.invalidate()
        presenter.draft = value
        XCTAssertFalse(presenter.saveDraft())
    }

    func testPreviewUsesTheRealCardWithoutChangingPreferencesAndLogoutRemovesIt() async throws {
        let suite = "F277-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel())
        presenter.updateContext(user: "a", workspace: "w")
        defer { presenter.invalidate() }
        let bridge = EmbeddedCabinetNotificationSettingsBridge(routePolicy: .init(baseURL: URL(string: "https://graf.test")!), presenter: presenter)
        let before = presenter.preferences
        let result = try await bridge.response(to: .init(version: 2, nonce: "n", action: "test", field: nil, value: nil), epoch: presenter.authEpoch)
        XCTAssertTrue(presenter.card.isVisible, "Preview must use the actual notification component")
        XCTAssertEqual(presenter.preferences, before)
        XCTAssertFalse((result["message"] as? String ?? "").isEmpty)
        presenter.invalidate()
        XCTAssertFalse(presenter.card.isVisible)
    }

    func testVersionTwoResponseHasFivePreferencesAndNoSystemPermissionState() async throws {
        let suite = "F277-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel())
        presenter.updateContext(user: "a", workspace: "w")
        let bridge = EmbeddedCabinetNotificationSettingsBridge(routePolicy: .init(baseURL: URL(string: "https://graf.test")!), presenter: presenter)
        let read = EmbeddedCabinetNotificationSettingsBridge.Request(version: 2, nonce: "n", action: "read", field: nil, value: nil)
        let result = try await bridge.response(to: read, epoch: presenter.authEpoch)
        XCTAssertEqual(result["version"] as? Int, 2)
        XCTAssertEqual(Set(result.keys), ["version", "preferences", "canEdit", "message"])
        let prefs = try XCTUnwrap(result["preferences"] as? [String: Any])
        XCTAssertEqual(Set(prefs.keys), ["reminders", "offsetMinutes", "showTitles", "sound", "quiet"])
        XCTAssertEqual(prefs["quiet"] as? Bool, false)
        XCTAssertEqual(result["canEdit"] as? Bool, true)
        XCTAssertNotNil(result["message"] as? String)
        let before = presenter.preferences
        for action in ["set", "test"] {
            let old = EmbeddedCabinetNotificationSettingsBridge.Request(version: 1, nonce: "n", action: action, field: action == "set" ? "sound" : nil, value: action == "set" ? .bool(true) : nil)
            do { _ = try await bridge.response(to: old, epoch: presenter.authEpoch); XCTFail("Version 1 accepted") } catch {}
            XCTAssertEqual(presenter.preferences, before)
            XCTAssertFalse(presenter.card.isVisible)
        }
        let preview = EmbeddedCabinetNotificationSettingsBridge.Request(version: 2, nonce: "n", action: "test", field: nil, value: nil)
        do { _ = try await bridge.response(to: preview, epoch: presenter.authEpoch, isCurrent: { false }); XCTFail("Old document accepted") } catch {}
        XCTAssertFalse(presenter.card.isVisible)
        let epoch = presenter.authEpoch
        presenter.invalidate()
        do { _ = try await bridge.response(to: preview, epoch: epoch); XCTFail("Old epoch accepted") } catch {}
        let unavailable = try await bridge.response(to: read, epoch: presenter.authEpoch)
        XCTAssertEqual(unavailable["canEdit"] as? Bool, false)
        let save = EmbeddedCabinetNotificationSettingsBridge.Request(version: 2, nonce: "n", action: "set", field: "quiet", value: .bool(true))
        let failed = try await bridge.response(to: save, epoch: presenter.authEpoch)
        XCTAssertFalse((failed["error"] as? String ?? "").isEmpty, "Unavailable save must not claim success")
        XCTAssertFalse(presenter.card.isVisible)
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
