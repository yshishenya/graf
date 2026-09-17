import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared
import WebKit
import XCTest

@MainActor
final class DesktopUserTimeContextTests: XCTestCase {
    private let origin = URL(string: "https://graf.example.test/desktop/meetings")!
    private let user = UUID().uuidString
    private let session = UUID().uuidString

    func testPreferenceIsScopedAndColdStartUsesDevice() throws {
        let context = DesktopUserTimeContext()
        XCTAssertNil(context.preference)
        XCTAssertEqual(context.timeZone, .autoupdatingCurrent)
        XCTAssertTrue(context.update(from: payload("Asia/Kathmandu"), origin: origin, expectedRevision: context.revision))
        XCTAssertEqual(context.preference?.userId.uuidString, user)
        XCTAssertEqual(context.preference?.sessionId.uuidString, session)
        XCTAssertEqual(context.preference?.origin, "https://graf.example.test")
        XCTAssertEqual(context.timeZone.identifier, "Asia/Kathmandu")
        let instant = try XCTUnwrap(ISO8601DateFormatter().date(from: "2026-09-05T21:30:00Z"))
        XCTAssertEqual(UserTime.format(instant, timeZone: context.timeZone), "06.09.2026, 03:15")
        XCTAssertTrue(DesktopUploadCustodyCopy.detail(copyKey: "custody.retention_warning", count: 1,
            deadline: instant, timeZone: context.timeZone).contains("06.09.2026, 03:15 (UTC+05:45)"))
        // No network operation mutates this in-process context; a fresh instance never restores it.
        XCTAssertEqual(context.timeZone.identifier, "Asia/Kathmandu")
        XCTAssertNil(DesktopUserTimeContext().preference)
        context.prepareForOrigin(URL(string: "https://GRAF.example.test:443/desktop/settings/account")!)
        XCTAssertNotNil(context.preference)
        context.prepareForOrigin(URL(string: "https://dev.example.test/desktop/meetings")!)
        XCTAssertNil(context.preference)
    }

    func testAuthResetRejectsOldCallbackAndNextUserDoesNotInheritZone() {
        let context = DesktopUserTimeContext()
        XCTAssertTrue(context.update(from: payload("Asia/Yekaterinburg"), origin: origin, expectedRevision: context.revision))
        let oldRevision = context.revision
        context.reset()
        XCTAssertFalse(context.update(from: payload("Asia/Yekaterinburg"), origin: origin, expectedRevision: oldRevision))
        XCTAssertNil(context.preference)
        var nextUser = payload("")
        nextUser["userId"] = UUID().uuidString
        nextUser["sessionId"] = UUID().uuidString
        XCTAssertTrue(context.update(from: nextUser, origin: origin, expectedRevision: context.revision))
        XCTAssertNil(context.preference?.preferredTimeZone)
        XCTAssertEqual(context.timeZone, .autoupdatingCurrent)
    }

    func testInvalidMetadataClearsActiveSelection() {
        let context = DesktopUserTimeContext()
        for invalid in ["../UTC", "wrong/zone", "CST", String(repeating: "x", count: 101)] {
            XCTAssertTrue(context.update(from: payload("Europe/Berlin"), origin: origin, expectedRevision: context.revision))
            XCTAssertFalse(context.update(from: payload(invalid), origin: origin, expectedRevision: context.revision))
            XCTAssertNil(context.preference)
        }
        var anonymous = payload("Europe/Berlin")
        anonymous["userId"] = ""
        XCTAssertFalse(context.update(from: anonymous, origin: origin, expectedRevision: context.revision))
    }

    func testOnlySameOriginAuthenticatedCabinetDocumentsAreEligible() {
        let policy = DesktopCabinetRoutePolicy(baseURL: origin)
        XCTAssertTrue(DesktopUserTimeContext.canRead(from: origin, routePolicy: policy))
        for url in ["https://other.example.test/desktop/meetings", "http://graf.example.test/desktop/meetings",
                    "https://graf.example.test:8443/desktop/meetings", "https://graf.example.test/login",
                    "https://graf.example.test/api/v1/auth/callback/google", "file:///desktop/meetings"] {
            XCTAssertFalse(DesktopUserTimeContext.canRead(from: URL(string: url)!, routePolicy: policy), url)
        }
    }

    func testNativeReaderUsesTopLevelServerMetadataNotIframe() async throws {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        let loaded = expectation(description: "synthetic cabinet loaded")
        let delegate = TimeContextNavigationDelegate(loaded: loaded)
        webView.navigationDelegate = delegate
        webView.loadHTMLString("""
            <html><head><meta name="graf-time-user" content="\(user)">
            <meta name="graf-time-session" content="\(session)">
            <meta name="graf-time-preferred" content="Asia/Kathmandu"></head>
            <body><iframe srcdoc='<meta name="graf-time-preferred" content="Europe/Berlin">'></iframe></body></html>
            """, baseURL: origin)
        await fulfillment(of: [loaded], timeout: 10)
        let fields = try await webView.evaluateJavaScript(DesktopUserTimeContext.documentScript)
        let context = DesktopUserTimeContext()
        XCTAssertTrue(context.update(from: try XCTUnwrap(fields), origin: origin, expectedRevision: context.revision))
        XCTAssertEqual(context.preference?.userId.uuidString, user)
        XCTAssertEqual(context.timeZone.identifier, "Asia/Kathmandu")
        let next = UUID().uuidString
        _ = try await webView.evaluateJavaScript("document.querySelector('meta[name=\"graf-time-user\"]').content='\(next)'; document.querySelector('meta[name=\"graf-time-preferred\"]').content='';")
        let replacement = try await webView.evaluateJavaScript(DesktopUserTimeContext.documentScript)
        context.reset()
        XCTAssertTrue(context.update(from: try XCTUnwrap(replacement), origin: origin, expectedRevision: context.revision))
        XCTAssertEqual(context.preference?.userId.uuidString, next)
        XCTAssertEqual(context.timeZone, .autoupdatingCurrent)
    }

    func testCookieReconciliationResetsAccountBeforeCompletion() async throws {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        let loaded = expectation(description: "cookie test document loaded")
        let delegate = TimeContextNavigationDelegate(loaded: loaded)
        webView.navigationDelegate = delegate
        webView.loadHTMLString("<html></html>", baseURL: origin)
        await fulfillment(of: [loaded], timeout: 10)
        let cookie = try XCTUnwrap(HTTPCookie(properties: [
            .name: DesktopCabinetConfiguration.authSessionCookieName(for: origin),
            .value: UUID().uuidString, .domain: "graf.example.test", .path: "/", .secure: "TRUE",
        ]))
        defer {
            HTTPCookieStorage.shared.deleteCookie(cookie)
            DesktopUserTimeContext.shared.reset()
        }
        await webView.configuration.websiteDataStore.httpCookieStore.setCookie(cookie)
        let context = DesktopUserTimeContext.shared
        XCTAssertTrue(context.update(from: payload("Europe/Berlin"), origin: origin, expectedRevision: context.revision))
        await withCheckedContinuation { continuation in
            DesktopCabinetSessionBridge.syncAuthSessionCookies(from: webView, completion: {
                XCTAssertNil(context.preference)
                continuation.resume()
            })
        }
    }

    private func payload(_ zone: String) -> [String: String] {
        ["userId": user, "sessionId": session, "timeZone": zone]
    }
}

@MainActor
private final class TimeContextNavigationDelegate: NSObject, @preconcurrency WKNavigationDelegate {
    let loaded: XCTestExpectation
    init(loaded: XCTestExpectation) { self.loaded = loaded }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { loaded.fulfill() }
}
