import Foundation
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

#if canImport(WebKit) && canImport(XCTest)
import XCTest
import WebKit

final class EmbeddedCabinetSupportIncidentBridgeTests: XCTestCase {
    @MainActor
    func testRequestScriptChecksDocumentIdentityBeforeFetch() async throws {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        let loaded = expectation(description: "synthetic support document loaded")
        let delegate = SupportNavigationDelegate(loaded: loaded)
        webView.navigationDelegate = delegate
        webView.loadHTMLString("""
            <html><head><meta name="graf-time-user" content="actor">
            <meta name="graf-workspace" content="workspace">
            <meta name="graf-time-session" content="session">
            <meta name="csrf-token" content="synthetic-csrf"></head></html>
            """, baseURL: URL(string: "https://graf.invalid/desktop/meetings")!)
        await fulfillment(of: [loaded], timeout: 10)
        let documentOrigin = try await webView.evaluateJavaScript("location.origin")
        XCTAssertEqual(documentOrigin as? String, "https://graf.invalid")
        _ = try await webView.evaluateJavaScript("""
            window.calls = [];
            window.fetch = async (path, options) => {
              calls.push({path, options});
              return {status: 202, text: async () => '{}'};
            };
            true;
            """)
        let request: [String: Any] = [
            "origin": "https://graf.invalid", "actor": "actor", "workspace": "workspace", "session": "session",
            "path": EmbeddedCabinetSupportIncidentBridge.intakePath, "hasBody": true,
            "body": "{}", "idempotencyKey": "synthetic-key"
        ]
        for field in ["origin", "actor", "workspace", "session"] {
            var stale = request
            stale[field] = "different"
            let raw = try await webView.callAsyncJavaScript(
                EmbeddedCabinetSupportIncidentBridge.requestScript, arguments: ["request": stale], in: nil, contentWorld: .page
            )
            let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(XCTUnwrap(raw))
            XCTAssertEqual(result.status, 409, field)
            XCTAssertEqual(result.body, "{\"code\":\"recording_scope_changed\"}", field)
        }
        let blockedCalls = try await webView.evaluateJavaScript("calls.length")
        XCTAssertEqual(blockedCalls as? Int, 0)
        let raw = try await webView.callAsyncJavaScript(
            EmbeddedCabinetSupportIncidentBridge.requestScript, arguments: ["request": request], in: nil, contentWorld: .page
        )
        XCTAssertEqual(try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(XCTUnwrap(raw)).status, 202)
        let call = try await webView.evaluateJavaScript("calls[0]") as? [String: Any]
        XCTAssertEqual(call?["path"] as? String, EmbeddedCabinetSupportIncidentBridge.intakePath)
        let options = call?["options"] as? [String: Any]
        XCTAssertEqual(options?["credentials"] as? String, "same-origin")
        XCTAssertEqual(options?["body"] as? String, "{}")
        let headers = options?["headers"] as? [String: String]
        XCTAssertEqual(headers?["X-Graf-Expected-Actor"], "actor")
        XCTAssertEqual(headers?["X-Graf-Expected-Workspace"], "workspace")
        XCTAssertEqual(headers?["X-CSRF-Token"], "synthetic-csrf")
        XCTAssertEqual(headers?["Idempotency-Key"], "synthetic-key")
    }

    @MainActor
    func testNativeBridgeRejectsSessionChangeBeforeDispatchAndAfterAwait() async throws {
        let origin = URL(string: "https://graf.invalid")!
        let actor = UUID().uuidString.lowercased()
        let session = UUID().uuidString.lowercased()
        let scope = try RecordingDeletionScope(serverOrigin: origin.absoluteString, workspaceID: "workspace", actorUserID: actor)
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let started = expectation(description: "synthetic fetch started")
        let loaded = expectation(description: "synthetic cabinet loaded")
        let delegate = SupportNavigationDelegate(loaded: loaded, started: started)
        configuration.userContentController.add(delegate, name: "supportFetch")
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = delegate
        webView.loadHTMLString("""
            <html><head><meta name="graf-time-user" content="\(actor)">
            <meta name="graf-workspace" content="workspace"><meta name="graf-time-session" content="\(session)">
            <meta name="csrf-token" content="synthetic-csrf"></head></html>
            """, baseURL: origin.appendingPathComponent("desktop/meetings"))
        await fulfillment(of: [loaded], timeout: 10)
        let time = DesktopUserTimeContext.shared
        defer { time.reset(); configuration.userContentController.removeScriptMessageHandler(forName: "supportFetch") }
        XCTAssertTrue(time.update(from: ["userId": actor, "sessionId": session, "timeZone": ""], origin: origin, expectedRevision: time.revision))
        let bridge = EmbeddedCabinetSupportIncidentBridge()
        bridge.attach(webView: webView, routePolicy: DesktopCabinetRoutePolicy(baseURL: origin))
        _ = try await webView.evaluateJavaScript("""
            window.calls = 0;
            window.fetch = () => {
              calls++;
              window.webkit.messageHandlers.supportFetch.postMessage('started');
              return new Promise(resolve => { window.finishSupport = () => resolve({status: 200, text: async () => '{}'}); });
            };
            true;
            """)
        let stale = DesktopSupportIncidentRequestContext(scope: scope, sessionGeneration: DesktopCabinetSessionBridge.generation, validateScope: {})
        let barrier = DesktopCabinetSessionBridge.beginNavigation()
        DesktopCabinetSessionBridge.endNavigation(barrier)
        do {
            _ = try await bridge.syncSupportIncident(incidentID: "CUST-TEST", context: stale)
            XCTFail("Stale session must be cancelled before fetch")
        } catch is CancellationError {}
        let blockedCalls = try await webView.evaluateJavaScript("calls")
        XCTAssertEqual(blockedCalls as? Int, 0)
        let current = DesktopSupportIncidentRequestContext(scope: scope, sessionGeneration: DesktopCabinetSessionBridge.generation, validateScope: {})
        let task = Task { try await bridge.syncSupportIncident(incidentID: "CUST-TEST", context: current) }
        await fulfillment(of: [started], timeout: 10)
        let nextBarrier = DesktopCabinetSessionBridge.beginNavigation()
        DesktopCabinetSessionBridge.endNavigation(nextBarrier)
        _ = try await webView.evaluateJavaScript("finishSupport(); true;")
        do {
            _ = try await task.value
            XCTFail("Late session response must be cancelled before decoding")
        } catch is CancellationError {}
    }

    @MainActor
    func testBridgeUsesFixedSameOriginFetchWithoutCookieOrTokenExtraction() {
        let script = EmbeddedCabinetSupportIncidentBridge.requestScript

        XCTAssertEqual(
            EmbeddedCabinetSupportIncidentBridge.intakePath,
            "/api/v1/desktop/support-incidents"
        )
        XCTAssertTrue(script.contains("fetch(request.path"))
        XCTAssertTrue(script.contains("credentials: \"same-origin\""))
        XCTAssertTrue(script.contains("X-CSRF-Token"))
        XCTAssertTrue(script.contains("return JSON.stringify([response.status, await response.text()])"))
        XCTAssertTrue(script.contains("request.path"))
        XCTAssertFalse(script.contains("arguments.request"))
        XCTAssertFalse(script.contains("(async () =>"))
        XCTAssertFalse(script.localizedCaseInsensitiveContains("document.cookie"))
        XCTAssertFalse(script.localizedCaseInsensitiveContains("authorization"))
        XCTAssertFalse(script.localizedCaseInsensitiveContains("x-auth-session"))
        XCTAssertFalse(script.localizedCaseInsensitiveContains("cookie"))
    }

    func testBridgeOnlyUsesAnAllowedAuthenticatedCabinetDocument() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.pro"))
        )

        XCTAssertTrue(
            EmbeddedCabinetSupportIncidentBridge.isAllowedCabinetDocument(
                try XCTUnwrap(URL(string: "https://rec.2brain.pro/desktop/meetings")),
                routePolicy: policy
            )
        )
        XCTAssertFalse(
            EmbeddedCabinetSupportIncidentBridge.isAllowedCabinetDocument(
                try XCTUnwrap(URL(string: "https://rec.2brain.pro/login")),
                routePolicy: policy
            )
        )
        XCTAssertFalse(
            EmbeddedCabinetSupportIncidentBridge.isAllowedCabinetDocument(
                try XCTUnwrap(URL(string: "https://example.test/desktop/meetings")),
                routePolicy: policy
            )
        )
    }

    @MainActor
    func testBridgeDecodesWebKitObjectResult() throws {
        let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(
            [
                "status": 202,
                "body": "{\"incident_id\":\"CUST-ABC123\"}"
            ]
        )

        XCTAssertEqual(
            result,
            EmbeddedCabinetSupportIncidentBridge.JavaScriptResult(
                status: 202,
                body: "{\"incident_id\":\"CUST-ABC123\"}"
            )
        )
    }

    @MainActor
    func testBridgeKeepsStringResultCompatibility() throws {
        let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(
            "{\"status\":200,\"body\":\"{}\"}"
        )

        XCTAssertEqual(result.status, 200)
        XCTAssertEqual(result.body, "{}")
    }

    @MainActor
    func testBridgeDecodesWebKitArrayResult() throws {
        let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(
            [202, "{\"incident_id\":\"CUST-ARRAY123\"}"]
        )

        XCTAssertEqual(result.status, 202)
        XCTAssertEqual(result.body, "{\"incident_id\":\"CUST-ARRAY123\"}")
    }

    @MainActor
    func testBridgeDecodesStringifiedWebKitArrayResult() throws {
        let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(
            "[202, \"{\\\"incident_id\\\":\\\"CUST-STRING123\\\"}\"]"
        )

        XCTAssertEqual(result.status, 202)
        XCTAssertEqual(result.body, "{\"incident_id\":\"CUST-STRING123\"}")
    }
}

@MainActor
private final class SupportNavigationDelegate: NSObject, @preconcurrency WKNavigationDelegate, WKScriptMessageHandler {
    let loaded: XCTestExpectation
    let started: XCTestExpectation?
    init(loaded: XCTestExpectation, started: XCTestExpectation? = nil) {
        self.loaded = loaded
        self.started = started
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { loaded.fulfill() }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) { started?.fulfill() }
}
#endif
