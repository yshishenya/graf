import Foundation
import WebKit
import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class EmbeddedCabinetRecordingSettingsBridgeTests: XCTestCase {
    private static var retainedViews: [WKWebView] = []

    private func target(_ id: String) -> MeetingTargetRegistryTarget {
        MeetingTargetRegistryTarget(id: id, displayName: "Приложение \(id)", market: .global,
            platform: .macos, targetFamily: .nativeApp, mode: .promptEnabled,
            evidence: .packageVerified, requiredSignals: [.macOSAudioHALAssertion], nativeBundleIds: ["test.\(id)"])
    }

    func testBulkKnownTargetsAndInvalidTargetDoNotChangeOtherSettings() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        _ = try store.update { $0.setRecordingRule(.always, for: "unlisted") }
        let targets = [target("one"), target("two")]
        let bridge = EmbeddedCabinetRecordingSettingsBridge(
            routePolicy: DesktopCabinetRoutePolicy(baseURL: URL(string: "https://graf.test")!), store: store, targets: { targets }
        )
        let result = try bridge.response(to: .init(version: 1, nonce: "test", action: "setAll", targetID: nil, rule: .never))
        XCTAssertEqual((result["targets"] as? [[String: String]])?.map { $0["rule"] }, ["never", "never"])
        XCTAssertEqual(try store.load().recordingRule(for: "unlisted"), .always)
        XCTAssertEqual(try store.load().recordingRule(for: "new"), .ask)
        XCTAssertThrowsError(try bridge.response(to: .init(version: 1, nonce: "test", action: "set", targetID: "invalid", rule: .always)))
        XCTAssertEqual(try store.load().recordingRule(for: "invalid"), .ask)
        try Data("broken".utf8).write(to: root.appendingPathComponent("settings.json"))
        XCTAssertThrowsError(try bridge.response(to: .init(version: 1, nonce: "test", action: "read", targetID: nil, rule: nil)))
    }

    func testSaveFailureReturnsConfirmedRulesAndAnError() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer {
            try? FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: root.path)
            try? FileManager.default.removeItem(at: root)
        }
        let store = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        _ = try store.update { $0.setRecordingRule(.ask, for: "one") }
        let targets = [target("one")]
        let bridge = EmbeddedCabinetRecordingSettingsBridge(
            routePolicy: .init(baseURL: URL(string: "https://graf.test")!), store: store, targets: { targets }
        )
        try FileManager.default.setAttributes([.posixPermissions: 0o500], ofItemAtPath: root.path)
        let result = try bridge.response(to: .init(version: 1, nonce: "test", action: "set", targetID: "one", rule: .always))
        XCTAssertNotNil(result["error"])
        XCTAssertEqual((result["targets"] as? [[String: String]])?.first?["rule"], "ask")
        XCTAssertEqual(try store.load().recordingRule(for: "one"), .ask)
    }

    func testActualWebKitFormSavesAndRefreshesFromNativeNotification() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let store = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        let origin = URL(string: "https://graf.test/desktop/settings/recording")!
        let targets = [target("one"), target("two")]
        let bridge = EmbeddedCabinetRecordingSettingsBridge(routePolicy: .init(baseURL: origin), store: store, targets: { targets })
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        config.userContentController.addScriptMessageHandler(bridge, contentWorld: .page, name: EmbeddedCabinetRecordingSettingsBridge.handlerName)
        let webView = WKWebView(frame: CGRect(x: 0, y: 0, width: 900, height: 700), configuration: config)
        Self.retainedViews.append(webView)
        defer {
            bridge.invalidate()
            config.userContentController.removeScriptMessageHandler(forName: EmbeddedCabinetRecordingSettingsBridge.handlerName, contentWorld: .page)
        }
        let repo = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let cabinet = repo.appendingPathComponent("apps/server/src/twobrain_rec_server/cabinet")
        let template = try String(contentsOf: cabinet.appendingPathComponent("templates/cabinet/pages/settings_recording_content.html"), encoding: .utf8)
        let html = try XCTUnwrap(template.components(separatedBy: "{% if embedded %}").last?.components(separatedBy: "{% else %}").first)
        let script = try String(contentsOf: cabinet.appendingPathComponent("static/cabinet/cabinet.js"), encoding: .utf8)
        webView.loadHTMLString("<!doctype html><html><body>\(html)<script>\(script)</script></body></html>", baseURL: origin)
        try await waitUntil("document.querySelector('[data-recording-settings]')?.dataset.ready === 'true'", in: webView)
        bridge.activate(webView)
        try await waitUntil("document.querySelectorAll('[data-recording-target]').length === 2", in: webView)
        _ = try await evaluate("const s = document.querySelector('[data-recording-target=one]'); s.parentElement.querySelector('input').focus(); s.value = 'always'; s.dispatchEvent(new Event('change', {bubbles:true}));", in: webView)
        try await waitUntil("!document.querySelector('[data-recording-target=one]').disabled", in: webView)
        XCTAssertEqual(try store.load().recordingRule(for: "one"), .always)
        _ = try store.update { $0.setRecordingRule(.never, for: "two") }
        NotificationCenter.default.post(name: .twoBrainRecMeetingDetectionSettingsDidChange, object: nil)
        try await waitUntil("document.querySelector('[data-recording-target=two]').value === 'never'", in: webView)
        let focused = try await evaluate("document.activeElement.parentElement.querySelector('select')?.dataset.recordingTarget", in: webView)
        XCTAssertEqual(focused as? String, "one")
        _ = try await evaluate("const search = document.querySelector('[data-recording-settings-search]'); search.value = 'one'; search.dispatchEvent(new Event('input'));", in: webView)
        let visible = try await evaluate("document.querySelectorAll('[data-recording-settings-targets] label:not([hidden])').length", in: webView)
        XCTAssertEqual(visible as? Int, 1)
        _ = try await evaluate("const all = document.querySelector('[data-recording-settings-all]'); all.value = 'never'; all.dispatchEvent(new Event('change', {bubbles:true}));", in: webView)
        try await waitUntil("!document.querySelector('[data-recording-settings-all]').disabled", in: webView)
        XCTAssertEqual(try store.load().recordingRule(for: "one"), .never)
        XCTAssertEqual(try store.load().recordingRule(for: "two"), .never)
        bridge.invalidate()
        _ = try await evaluate("window.GRAFRecordingSettings.refresh()", in: webView)
        try await waitUntil("!document.querySelector('[data-recording-settings-retry]').hidden", in: webView)
        XCTAssertEqual(try store.load().recordingRule(for: "one"), .never)
    }

    private func waitUntil(_ condition: String, in webView: WKWebView) async throws {
        for _ in 0..<100 {
            if (try? await evaluate(condition, in: webView)) as? Bool == true { return }
            try await Task.sleep(for: .milliseconds(50))
        }
        XCTFail("Condition timed out: \(condition)")
        throw CocoaError(.fileReadUnknown)
    }

    private func evaluate(_ script: String, in webView: WKWebView) async throws -> Any? {
        var result: Any?
        var failure: Error?
        await withCheckedContinuation { continuation in
            webView.evaluateJavaScript(script) { value, error in
                result = value; failure = error; continuation.resume()
            }
        }
        if let failure { throw failure }
        return result
    }

    func testPatchesAcrossStoresPreserveOtherRulesAndPolicyFields() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let first = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        let second = MeetingDetectionSettingsStore(settingsURL: root.appendingPathComponent("settings.json"))
        try first.save(MeetingDetectionSettings(unknownIdentityUploadAllowed: false))
        _ = try first.update { $0.setRecordingRule(.always, for: "one") }
        _ = try second.update { $0.setRecordingRule(.never, for: "two") }
        let saved = try first.load()
        XCTAssertEqual(saved.recordingRule(for: "one"), .always)
        XCTAssertEqual(saved.recordingRule(for: "two"), .never)
        XCTAssertEqual(saved.recordingRule(for: "new"), .ask)
        XCTAssertFalse(saved.unknownIdentityUploadAllowed)
        XCTAssertTrue(saved.allowsDetectorAssistedStart(reason: .savedTargetPolicy, targetID: "one"))
        XCTAssertFalse(saved.allowsDetectorAssistedStart(reason: .savedTargetPolicy, targetID: "two"))
    }

    func testRequestRejectsWrongDocumentFrameOriginRouteAndShape() throws {
        let url = try XCTUnwrap(URL(string: "https://graf.test/desktop/settings/recording"))
        let policy = DesktopCabinetRoutePolicy(baseURL: url)
        let valid: [String: Any] = ["version": 1, "nonce": "current", "action": "set", "targetID": "one", "rule": "always"]
        func accepts(_ body: [String: Any], source: URL? = nil, current: URL? = nil, main: Bool = true, loading: Bool = false) -> Bool {
            EmbeddedCabinetRecordingSettingsBridge.allowedRequest(
                body, sourceURL: source ?? url, currentURL: current ?? url,
                isMainFrame: main, isLoading: loading, nonce: "current", routePolicy: policy
            ) != nil
        }
        XCTAssertTrue(accepts(valid))
        XCTAssertFalse(accepts(valid, main: false))
        XCTAssertFalse(accepts(valid, loading: true))
        XCTAssertFalse(accepts(valid, source: URL(string: "https://evil.test/desktop/settings/recording")))
        XCTAssertFalse(accepts(valid, current: URL(string: "https://graf.test/login")))
        for (key, value) in [("nonce", "old"), ("action", "stop"), ("rule", "invalid"), ("extra", "value")] {
            var body = valid; body[key] = value
            XCTAssertFalse(accepts(body), key)
        }
        var body = valid; body["version"] = true
        XCTAssertFalse(accepts(body))
        body["version"] = 2
        XCTAssertFalse(accepts(body))
    }
}
