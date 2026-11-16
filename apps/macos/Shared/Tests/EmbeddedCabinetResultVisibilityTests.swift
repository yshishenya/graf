import AppKit
import Foundation
import WebKit
import XCTest
@testable import TwoBrainRecAppCore

@MainActor
final class EmbeddedCabinetResultVisibilityTests: XCTestCase {
    private let url = URL(string: "https://graf.test/desktop/meetings/00000000-0000-0000-0000-000000000010")!
    private static var retainedViews: [WKWebView] = []

    func testOnlyCanonicalOwnDetailRouteIsAllowed() {
        let policy = DesktopCabinetRoutePolicy(baseURL: url)
        XCTAssertTrue(EmbeddedCabinetResultVisibilityBridge.isDetailURL(url, policy: policy))
        XCTAssertTrue(EmbeddedCabinetResultVisibilityBridge.isDetailURL(URL(string: url.absoluteString + "?summary_format=synthetic#recording"), policy: policy))
        for path in [
            "http://graf.test/desktop/meetings/00000000-0000-0000-0000-000000000010",
            "https://other.test" + url.path, "https://graf.test:444" + url.path,
            "https://graf.test/desktop/shared-meetings/00000000-0000-0000-0000-000000000010",
            "https://graf.test/desktop/meetings/not-a-uuid", url.absoluteString + "/",
            url.absoluteString + "/deletion-requests", url.absoluteString + "/calendar-context",
            "https://graf.test/desktop/%6Deetings/00000000-0000-0000-0000-000000000010",
            "https://graf.test/desktop/settings/notifications", "https://graf.test/meetings/00000000-0000-0000-0000-000000000010",
        ] {
            XCTAssertFalse(EmbeddedCabinetResultVisibilityBridge.isDetailURL(URL(string: path), policy: policy), path)
        }
    }

    func testBoundaryRejectsOtherDocumentsFramesAndMalformedRequests() {
        let policy = DesktopCabinetRoutePolicy(baseURL: url)
        let valid: [String: Any] = ["version": 1, "nonce": "current"]
        func allows(_ body: [String: Any], source: URL? = nil, current: URL? = nil,
                    main: Bool = true, loading: Bool = false, nonce: String? = "current") -> Bool {
            EmbeddedCabinetResultVisibilityBridge.allowedRequest(body, sourceURL: source ?? url,
                currentURL: current ?? url, isMainFrame: main, isLoading: loading, nonce: nonce, routePolicy: policy)
        }
        XCTAssertTrue(allows(valid))
        XCTAssertFalse(allows(valid, main: false)); XCTAssertFalse(allows(valid, loading: true))
        XCTAssertFalse(allows(valid, nonce: nil)); XCTAssertFalse(allows(valid, nonce: "old"))
        XCTAssertFalse(allows(valid, source: URL(string: "https://other.test" + url.path)))
        XCTAssertFalse(allows(valid, current: URL(string: "https://other.test" + url.path)))
        XCTAssertFalse(allows(valid, source: URL(string: url.absoluteString.replacingOccurrences(of: "0010", with: "0011"))))
        for patch in [["version": true], ["version": 2], ["version": "1"], ["nonce": 1],
                      ["extra": true], ["proof": "synthetic"], ["meetingId": "synthetic"]] as [[String: Any]] {
            XCTAssertFalse(allows(valid.merging(patch) { _, new in new }))
        }
        XCTAssertFalse(allows(["version": 1])); XCTAssertFalse(allows(["nonce": "current"]))
    }

    func testEachForegroundConditionIsRequired() {
        XCTAssertTrue(EmbeddedCabinetResultVisibilityBridge.foregroundReady(
            applicationActive: true, viewVisible: true, windowVisible: true, miniaturized: false, occlusionVisible: true))
        for blocked in 0..<5 {
            XCTAssertFalse(EmbeddedCabinetResultVisibilityBridge.foregroundReady(
                applicationActive: blocked != 0, viewVisible: blocked != 1, windowVisible: blocked != 2,
                miniaturized: blocked == 3, occlusionVisible: blocked != 4))
        }
    }

    func testRealWKReplyIsReadOnlyAndInvalidatesOldNonceAndSession() async throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: url)
        let bridge = EmbeddedCabinetResultVisibilityBridge(routePolicy: policy)
        let config = WKWebViewConfiguration(); config.websiteDataStore = .nonPersistent()
        config.userContentController.addScriptMessageHandler(bridge, contentWorld: .page, name: EmbeddedCabinetResultVisibilityBridge.handlerName)
        let web = WKWebView(frame: .zero, configuration: config)
        Self.retainedViews.append(web)
        defer { bridge.invalidate(); config.userContentController.removeScriptMessageHandler(forName: EmbeddedCabinetResultVisibilityBridge.handlerName, contentWorld: .page) }
        web.loadHTMLString("<script>window.connections=0;window.nonce=null;window.GRAFResultVisibility={connect(value){connections++;nonce=value},disconnect(){nonce=null},refresh(){}};</script>", baseURL: url)
        try await wait("document.readyState === 'complete' && typeof connections === 'number'", web)
        let barrier = DesktopCabinetSessionBridge.beginNavigation()
        bridge.activate(web, isCurrentDocument: { true })
        let blockedConnections = try await web.evaluateJavaScript("connections")
        XCTAssertEqual(blockedConnections as? Int, 0)
        DesktopCabinetSessionBridge.endNavigation(barrier)
        var currentDocument = true
        bridge.activate(web, isCurrentDocument: { currentDocument })
        try await wait("connections === 1 && typeof nonce === 'string'", web)
        let result = try await web.callAsyncJavaScript(
            "return await window.webkit.messageHandlers.grafResultVisibility.postMessage({version:1,nonce})",
            arguments: [:], in: nil, contentWorld: .page)
        let fields = try XCTUnwrap(result as? [String: Any])
        XCTAssertEqual(Set(fields.keys), ["version", "ready"])
        XCTAssertEqual(fields["version"] as? Int, 1)
        XCTAssertEqual(fields["ready"] as? Bool, false, "Detached WKWebView cannot prove foreground")
        currentDocument = false
        let rejected = try await web.callAsyncJavaScript(
            "try {await window.webkit.messageHandlers.grafResultVisibility.postMessage({version:1,nonce});return false} catch {return true}",
            arguments: [:], in: nil, contentWorld: .page)
        XCTAssertEqual(rejected as? Bool, true)
        currentDocument = true
        let changed = DesktopCabinetSessionBridge.beginNavigation()
        defer { DesktopCabinetSessionBridge.endNavigation(changed) }
        let stale = try await web.callAsyncJavaScript(
            "try {await window.webkit.messageHandlers.grafResultVisibility.postMessage({version:1,nonce});return false} catch {return true}",
            arguments: [:], in: nil, contentWorld: .page)
        XCTAssertEqual(stale as? Bool, true)
        bridge.invalidate()
        try await wait("nonce === null", web)
    }

    func testCoordinatorConnectsAfterReconciliationAndInvalidatesEveryDocumentExit() async throws {
        let suite = "F273-result-visibility-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        for interruption in ["navigation", "termination", "detach"] {
            let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel())
            defer { presenter.invalidate() }
            let policy = DesktopCabinetRoutePolicy(baseURL: url)
            let config = WKWebViewConfiguration(); config.websiteDataStore = .nonPersistent()
            let web = WKWebView(frame: .zero, configuration: config)
            Self.retainedViews.append(web)
            web.loadHTMLString("<script>window.connections=0;window.nonce=null;window.GRAFResultVisibility={connect(value){connections++;nonce=value},disconnect(){nonce=null},refresh(){}};</script>", baseURL: url)
            try await wait("document.readyState === 'complete' && typeof connections === 'number'", web)
            let navigation = EmbeddedCabinetNavigationController()
            let request = URLRequest(url: url)
            navigation.attach(webView: web, routePolicy: policy, fallbackRequest: request, initialRequest: request, sessionExpired: false)
            let coordinator = EmbeddedCabinetWebView.Coordinator(routePolicy: policy, desktopHeaders: [:],
                cabinetState: .constant(.ready), currentRoute: .constant(url), navigationEventLogger: nil,
                showsAppUpdateBadge: false, onCheckForUpdates: {}, onOpenMeetingDetectionSettings: {},
                supportIncidentBridge: nil, notificationPresenter: presenter, navigationController: navigation)
            let dispatched = expectation(description: "Synthetic auth navigation dispatched")
            coordinator.dispatchAuthNavigation(in: web, targetURL: url,
                decisionHandler: { _ in XCTFail("Current navigation cancelled") }, dispatch: { dispatched.fulfill() })
            await fulfillment(of: [dispatched], timeout: 5)
            XCTAssertFalse(DesktopCabinetSessionBridge.isCurrentSession(DesktopCabinetSessionBridge.generation))
            let before = try await web.evaluateJavaScript("connections")
            XCTAssertEqual(before as? Int, 0)
            coordinator.webView(web, didFinish: nil)
            try await wait("connections === 1 && typeof nonce === 'string'", web)
            XCTAssertTrue(DesktopCabinetSessionBridge.isCurrentSession(DesktopCabinetSessionBridge.generation))
            switch interruption {
            case "navigation": coordinator.webView(web, didStartProvisionalNavigation: nil)
            case "termination": coordinator.webViewWebContentProcessDidTerminate(web)
            default: await coordinator.detachNavigationController(from: web)?.value
            }
            try await wait("nonce === null", web)
            await coordinator.detachNavigationController(from: web)?.value
        }
    }

    private func wait(_ condition: String, _ web: WKWebView) async throws {
        for _ in 0..<100 {
            if try await web.evaluateJavaScript(condition) as? Bool == true { return }
            try await Task.sleep(for: .milliseconds(50))
        }
        _ = try XCTUnwrap(nil as Bool?, "Synthetic WK condition did not become true")
    }
}
