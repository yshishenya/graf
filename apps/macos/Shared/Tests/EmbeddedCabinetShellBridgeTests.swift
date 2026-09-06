import Foundation
import XCTest
import AppKit
import Network
import WebKit
import SwiftUI
@testable import TwoBrainRecAppCore

@MainActor
final class EmbeddedCabinetShellBridgeTests: XCTestCase {
    private let url = URL(string: "https://rec.example.test/desktop/settings/account")!
    private var payload: [String: Any] {
        ["version": "desktop-shell/v1", "generation": "document-1", "theme": "system", "name": "Синтетический профиль",
         "commands": ["account", "settings", "theme", "logout", "quit"],
         "items": [["id": "settings", "label": "Настройки", "route": "/desktop/settings", "group": "main", "selected": true],
                   ["id": "account", "label": "Аккаунт", "route": "/desktop/settings/account", "group": "settings", "selected": true]]]
    }
    private func parse(_ body: [String: Any], source: URL? = nil, main: Bool = true, generation: String = "document-1") -> EmbeddedCabinetShellSnapshot? {
        EmbeddedCabinetShellSnapshot.parse(body, sourceURL: source ?? url, documentURL: url, isMainFrame: main,
                                          generation: generation, routePolicy: DesktopCabinetRoutePolicy(baseURL: URL(string: "https://rec.example.test")!))
    }
    func testSnapshotAcceptsSelectedParentAndCategoryWithoutCopyingHistory() throws {
        let snapshot = try XCTUnwrap(parse(payload))
        XCTAssertEqual(snapshot.items.count, 2)
        XCTAssertEqual(snapshot.theme, "system")
        XCTAssertEqual(snapshot.items.last?.url.path, "/desktop/settings/account")
    }
    func testRejectsWrongDocumentFrameGenerationAndVersion() {
        XCTAssertNil(parse(payload, main: false))
        XCTAssertNil(parse(payload, source: URL(string: "https://other.test/desktop/settings/account")))
        XCTAssertNil(parse(payload, source: URL(string: "https://rec.example.test/login")))
        XCTAssertNil(parse(payload, generation: "next-document"))
        var body = payload; body["version"] = "desktop-shell/v2"; XCTAssertNil(parse(body))
    }
    func testRejectsUnsafeRoutesDuplicateIDsAndAmbiguousSelection() {
        for route in ["javascript:alert(1)", "https://other.test/desktop/settings", "/logout", "/login", "//other.test/desktop/settings"] {
            var body = payload
            body["items"] = [["id": "route", "label": "Ссылка", "route": route, "group": "main", "selected": false]]
            XCTAssertNil(parse(body), route)
        }
        var body = payload
        let item = (payload["items"] as! [[String: Any]])[0]
        body["items"] = [item, item]; XCTAssertNil(parse(body))
        var second = item; second["id"] = "other"
        body["items"] = [item, second]; XCTAssertNil(parse(body))
    }
    func testRejectsOversizeMalformedFieldsAndUnknownCommands() {
        var body = payload; body["name"] = String(repeating: "x", count: 257); XCTAssertNil(parse(body))
        body = payload; body["commands"] = ["evaluateJavaScript"]; XCTAssertNil(parse(body))
        body = payload; body["theme"] = "glass"; XCTAssertNil(parse(body))
        body = payload; body["extra"] = String(repeating: "x", count: 32769); XCTAssertNil(parse(body))
        body = payload; body["items"] = [["id": "invalid id", "label": "\n", "route": "/desktop/settings", "group": "main", "selected": true]]; XCTAssertNil(parse(body))
    }
    private static var retainedWebViews: [WKWebView] = []

    func testRealDocumentHandoffThemeAndStaleSessionFallback() async throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let javascript = try String(contentsOf: root.appendingPathComponent("apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"), encoding: .utf8)
        let html = """
        <!doctype html><html lang="ru"><body>
        <div class="app-shell desktop-embedded" data-cabinet-shell>
          <aside data-cabinet-navigation><a href="/desktop/meetings" data-shell-item="meetings" data-shell-group="main" aria-label="Мои встречи" aria-current="page">Мои встречи</a>
          <strong class="sidebar-profile__name">Synthetic</strong>
          <form data-account-preferences data-account-preferences-auto-save="true" method="post" action="/desktop/settings/account/preferences">
            <input type="hidden" name="csrf_token" value="synthetic-csrf">
            <input type="radio" name="theme" value="system" checked>
            <input type="radio" name="theme" value="light"><input type="radio" name="theme" value="dark">
          </form></aside><main>Test document</main>
        </div><script>\(javascript)</script></body></html>
        """
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        let ready = expectation(description: "loopback ready")
        listener.stateUpdateHandler = { if case .ready = $0 { ready.fulfill() } }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .global())
            connection.receive(minimumIncompleteLength: 1, maximumLength: 4096) { data, _, _, _ in
                let request = String(decoding: data ?? Data(), as: UTF8.self)
                let response: String
                if request.hasPrefix("POST /desktop/settings/account/preferences ") {
                    response = "HTTP/1.1 303 See Other\r\nLocation: /desktop/settings/account?preferences=saved\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
                } else if request.hasPrefix("POST /desktop/settings/fail/preferences ") {
                    response = "HTTP/1.1 503 Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
                } else {
                    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: \(html.utf8.count)\r\nConnection: close\r\n\r\n\(html)"
                }
                connection.send(content: Data(response.utf8), completion: .contentProcessed { _ in connection.cancel() })
            }
        }
        listener.start(queue: .global())
        defer { listener.cancel() }
        await fulfillment(of: [ready], timeout: 5)
        let origin = try XCTUnwrap(URL(string: "http://127.0.0.1:\(try XCTUnwrap(listener.port).rawValue)"))
        let documentURL = origin.appendingPathComponent("desktop/meetings")
        let policy = DesktopCabinetRoutePolicy(baseURL: origin)
        let bridge = EmbeddedCabinetShellBridge()
        let controller = EmbeddedCabinetNavigationController()
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let web = WKWebView(frame: .zero, configuration: configuration)
        Self.retainedWebViews.append(web)
        let coordinator = EmbeddedCabinetWebView.Coordinator(routePolicy: policy, desktopHeaders: [:], cabinetState: .constant(.ready),
            currentRoute: .constant(documentURL), navigationEventLogger: nil, showsAppUpdateBadge: false, onCheckForUpdates: {},
            onOpenMeetingDetectionSettings: {}, supportIncidentBridge: nil, navigationController: controller, shellBridge: bridge)
        configuration.userContentController.add(coordinator, name: EmbeddedCabinetShellBridge.messageHandlerName)
        controller.attach(webView: web, routePolicy: policy, fallbackRequest: URLRequest(url: documentURL), initialRequest: URLRequest(url: documentURL), sessionExpired: false)
        web.navigationDelegate = coordinator
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 800, height: 600), styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = web
        defer { bridge.invalidate(); web.navigationDelegate = nil; configuration.userContentController.removeAllScriptMessageHandlers(); window.close() }
        web.load(URLRequest(url: documentURL))
        for _ in 0..<150 {
            if bridge.snapshot != nil { break }
            try await Task.sleep(for: .milliseconds(30))
        }
        let snapshot = try XCTUnwrap(bridge.snapshot)
        let hidden = try await web.evaluateJavaScript("document.querySelector('[data-cabinet-navigation]').hidden")
        XCTAssertEqual(hidden as? Bool, true)
        var stale = payload; stale["generation"] = "previous-document"
        bridge.receive(stale, sourceURL: documentURL, isMainFrame: true, sessionBoundaryID: controller.sessionBoundaryID)
        XCTAssertEqual(bridge.snapshot, snapshot, "Late messages must not clear a newer menu")
        _ = try await web.evaluateJavaScript("window.shellIdentity = 'preserved'")
        _ = try await web.evaluateJavaScript("history.replaceState(null, '', '?q=synthetic#summary')")
        bridge.perform("theme", value: "light")
        for _ in 0..<100 {
            if bridge.snapshot?.theme == "light",
               (try? await web.evaluateJavaScript("!document.querySelector('input[name=theme]').disabled")) as? Bool == true { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertEqual(web.url?.path, documentURL.path, "Saving the theme must not take the user to account settings")
        XCTAssertEqual(web.url?.fragment, "summary")
        _ = try await web.evaluateJavaScript("document.querySelector('form').action = '/desktop/settings/fail/preferences'")
        bridge.perform("theme", value: "dark")
        for _ in 0..<100 {
            if (try? await web.evaluateJavaScript("!!document.getElementById('cabinet-theme-feedback')")) as? Bool == true { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        let errorVisible = try await web.evaluateJavaScript("document.getElementById('cabinet-theme-feedback')?.getAttribute('role')")
        XCTAssertEqual(errorVisible as? String, "alert")
        for _ in 0..<100 {
            if bridge.snapshot?.theme == "light" { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertEqual(bridge.snapshot?.theme, "light")
        let identity = try await web.evaluateJavaScript("window.shellIdentity")
        XCTAssertEqual(identity as? String, "preserved")
        bridge.invalidate()
        XCTAssertNil(bridge.snapshot)
        let visible = try await web.evaluateJavaScript("!document.querySelector('[data-cabinet-navigation]').hidden")
        XCTAssertEqual(visible as? Bool, true)
        bridge.receive(payload, sourceURL: documentURL, isMainFrame: true, sessionBoundaryID: UUID())
        XCTAssertNil(bridge.snapshot)

        // Exercise the real SwiftUI hierarchy, not only the document bridge.
        let workspace = DesktopCabinetWorkspaceView(
            configuration: DesktopCabinetConfiguration(baseURL: origin), presentation: .shell)
        let host = NSHostingController(rootView: workspace)
        let workspaceWindow = NSWindow(contentViewController: host)
        workspaceWindow.isReleasedWhenClosed = false
        workspaceWindow.setContentSize(NSSize(width: 1040, height: 680))
        workspaceWindow.contentView?.layoutSubtreeIfNeeded()
        defer { workspaceWindow.close() }
        func descendants<T: NSView>(_ view: NSView, of type: T.Type) -> [T] {
            (view as? T).map { [$0] } ?? view.subviews.flatMap { descendants($0, of: type) }
        }
        var hostedWeb: WKWebView?
        for _ in 0..<150 {
            hostedWeb = descendants(host.view, of: WKWebView.self).first
            if let hostedWeb, !hostedWeb.isLoading,
               (try? await hostedWeb.evaluateJavaScript("document.querySelector('[data-cabinet-navigation]')?.hidden")) as? Bool == true { break }
            try await Task.sleep(for: .milliseconds(30))
        }
        let stableWeb = try XCTUnwrap(hostedWeb)
        Self.retainedWebViews.append(stableWeb)
        let adopted = try await stableWeb.evaluateJavaScript("document.querySelector('[data-cabinet-navigation]').hidden")
        XCTAssertEqual(adopted as? Bool, true)
        _ = try await stableWeb.evaluateJavaScript("window.shellIdentity = 'workspace-preserved'")
        let split = try XCTUnwrap(descendants(host.view, of: NSSplitView.self).first)
        let splitController = try XCTUnwrap(split.delegate as? NSSplitViewController)
        let sidebar = try XCTUnwrap(splitController.splitViewItems.first)
        for collapsed in [true, false] {
            sidebar.isCollapsed = collapsed
            workspaceWindow.setContentSize(NSSize(width: collapsed ? 1200 : 1040, height: 680))
            _ = try await stableWeb.evaluateJavaScript("document.documentElement.dataset.theme = '\(collapsed ? "light" : "dark")'; window.grafDesktopShell.publish()")
            try await Task.sleep(for: .milliseconds(150))
            host.view.layoutSubtreeIfNeeded()
            XCTAssertTrue(descendants(host.view, of: WKWebView.self).first === stableWeb)
            XCTAssertEqual(descendants(host.view, of: WKWebView.self).count, 1)
            let marker = try await stableWeb.evaluateJavaScript("window.shellIdentity")
            XCTAssertEqual(marker as? String, "workspace-preserved")
        }
    }

}
