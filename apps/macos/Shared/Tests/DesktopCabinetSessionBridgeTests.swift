import Foundation
@testable import TwoBrainRecAppCore
import WebKit
import XCTest

@MainActor
final class DesktopCabinetSessionBridgeTests: XCTestCase {
    private let origin = URL(string: "https://renewal.example.test/api/v1/desktop/notification-context")!
    private let now = Date(timeIntervalSince1970: 1_800_000_000)

    func testRenewalAcceptsOnlySuccessfulSameOriginIntegerFutureExpiry() throws {
        var request = URLRequest(url: origin)
        request.setValue("synthetic-session", forHTTPHeaderField: "X-Auth-Session")
        let future = String(Int(now.timeIntervalSince1970 + 30 * 86400))
        for status in [200, 204, 304] {
            XCTAssertNotNil(DesktopCabinetSessionBridge.renewalExpiry(request: request, response: response(status: status, expiry: future), now: now))
        }
        for status in [301, 400, 401, 403, 500] {
            XCTAssertNil(DesktopCabinetSessionBridge.renewalExpiry(request: request, response: response(status: status, expiry: future), now: now))
        }
        for value in ["", "invalid", "1800000000", "1799999999", "1800000100.5", "-1", "+1800000100", "999999999999999999999", "999999999999"] {
            XCTAssertNil(DesktopCabinetSessionBridge.renewalExpiry(request: request, response: response(expiry: value), now: now), value)
        }
        for url in ["https://other.example.test", "http://renewal.example.test", "https://renewal.example.test:8443"] {
            XCTAssertNil(DesktopCabinetSessionBridge.renewalExpiry(request: request, response: response(url: URL(string: url)!, expiry: future), now: now))
        }
        XCTAssertNotNil(DesktopCabinetSessionBridge.renewalExpiry(request: request, response: response(url: URL(string: "https://RENEWAL.example.test:443/next")!, expiry: future), now: now))
        request.setValue(nil, forHTTPHeaderField: "X-Auth-Session")
        XCTAssertNil(DesktopCabinetSessionBridge.renewalExpiry(request: request, response: response(expiry: future), now: now))
    }

    func testRenewalOnlyExtendsExistingMatchingCookiesAndPreservesSecurity() throws {
        let old = try cookie(expiry: now.addingTimeInterval(100))
        let expiry = now.addingTimeInterval(30 * 86400)
        let pair = try XCTUnwrap(DesktopCabinetSessionBridge.renewalCookies(webCookies: [old], nativeCookies: [old], originURL: origin, token: old.value, expiresAt: expiry, now: now))
        for renewed in [try XCTUnwrap(pair.web), try XCTUnwrap(pair.native)] {
            XCTAssertEqual(renewed.expiresDate, expiry)
            XCTAssertEqual(renewed.value, old.value)
            XCTAssertEqual(renewed.name, old.name)
            XCTAssertEqual(renewed.domain, old.domain)
            XCTAssertEqual(renewed.path, old.path)
            XCTAssertEqual(renewed.isSecure, old.isSecure)
            XCTAssertEqual(renewed.isHTTPOnly, old.isHTTPOnly)
            XCTAssertEqual(renewed.properties?[HTTPCookiePropertyKey("SameSite")] as? String, old.properties?[HTTPCookiePropertyKey("SameSite")] as? String)
        }
        let unchanged = try XCTUnwrap(DesktopCabinetSessionBridge.renewalCookies(webCookies: [old], nativeCookies: [old], originURL: origin, token: old.value, expiresAt: now.addingTimeInterval(50), now: now))
        XCTAssertNil(unchanged.web)
        XCTAssertNil(unchanged.native)
        let other = try cookie(value: "other-account", expiry: expiry)
        let expired = try cookie(expiry: now)
        for (web, native) in [([], [old]), ([old], []), ([other], [old]), ([old], [other]), ([expired], [old]), ([old], [expired])] {
            XCTAssertNil(DesktopCabinetSessionBridge.renewalCookies(webCookies: web, nativeCookies: native, originURL: origin, token: old.value, expiresAt: expiry, now: now))
        }
    }

    func testLocalDevRenewalPreservesInsecureLoopbackCookie() throws {
        let url = URL(string: "http://127.0.0.1:8081/api/v1/desktop/notification-context")!
        let old = try XCTUnwrap(HTTPCookie(properties: [.name: DesktopUploadClient.localOwnerSessionCookieName,
            .value: "synthetic-local", .domain: "127.0.0.1", .path: "/", .expires: now.addingTimeInterval(100)]))
        let pair = try XCTUnwrap(DesktopCabinetSessionBridge.renewalCookies(webCookies: [old], nativeCookies: [old], originURL: url,
            token: old.value, expiresAt: now.addingTimeInterval(30 * 86400), now: now))
        XCTAssertFalse(try XCTUnwrap(pair.web).isSecure)
        XCTAssertFalse(try XCTUnwrap(pair.native).isSecure)
        XCTAssertEqual(pair.web?.name, DesktopUploadClient.localOwnerSessionCookieName)
    }

    func testExpiryOnlyReconciliationDoesNotChangeAuthentication() throws {
        let old = try cookie(expiry: now.addingTimeInterval(100))
        let renewed = try cookie(expiry: now.addingTimeInterval(30 * 86400))
        let plan = DesktopCabinetSessionBridge.reconciliation(webCookies: [renewed], nativeCookies: [old], originURL: origin, now: now)
        XCTAssertFalse(plan.authenticationChanged)
        XCTAssertEqual(plan.cookiesToSet.first?.expiresDate, renewed.expiresDate)
        let staleSnapshot = DesktopCabinetSessionBridge.reconciliation(webCookies: [old], nativeCookies: [renewed], originURL: origin, now: now)
        XCTAssertTrue(staleSnapshot.cookiesToSet.isEmpty)
        XCTAssertFalse(staleSnapshot.authenticationChanged)
        let changed = try cookie(value: "other-account", expiry: renewed.expiresDate!)
        XCTAssertTrue(DesktopCabinetSessionBridge.reconciliation(webCookies: [changed], nativeCookies: [old], originURL: origin, now: now).authenticationChanged)
        XCTAssertTrue(DesktopCabinetSessionBridge.reconciliation(webCookies: [], nativeCookies: [old], originURL: origin, now: now).authenticationChanged)
    }

    func testRealWebKitAndNativeStoresRenewAndRejectLogoutAccountAndStaleGeneration() async throws {
        let storage = HTTPCookieStorage.sharedCookieStorage(forGroupContainerIdentifier: "test.graf.renewal.\(UUID())")
        let dataStore = WKWebsiteDataStore.nonPersistent()
        let store = dataStore.httpCookieStore
        defer { withExtendedLifetime(dataStore) {} }
        let old = try cookie(expiry: Date().addingTimeInterval(3600))
        let expiry = String(Int(Date().addingTimeInterval(30 * 86400).timeIntervalSince1970))
        var request = URLRequest(url: origin)
        request.setValue(old.value, forHTTPHeaderField: "X-Auth-Session")
        storage.setCookie(old)
        await store.setCookie(old)
        defer { for cookie in storage.cookies ?? [] { storage.deleteCookie(cookie) } }
        let generation = DesktopCabinetSessionBridge.generation
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response(status: 304, expiry: expiry), expectedGeneration: generation, storage: storage, cookieStore: store)
        XCTAssertEqual(storage.cookies?.first?.expiresDate?.timeIntervalSince1970, Double(expiry))
        let web = await store.allCookies()
        XCTAssertEqual(web.first?.expiresDate?.timeIntervalSince1970, Double(expiry))

        // Logout after request dispatch, before the response arrives.
        storage.deleteCookie(old)
        await store.deleteCookie(old)
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response(expiry: expiry), expectedGeneration: generation, storage: storage, cookieStore: store)
        XCTAssertTrue(storage.cookies?.isEmpty ?? true)
        let loggedOut = await store.allCookies()
        XCTAssertTrue(loggedOut.isEmpty)

        let other = try cookie(value: "other-account", expiry: Date().addingTimeInterval(3600))
        storage.setCookie(other)
        await store.setCookie(other)
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response(expiry: expiry), expectedGeneration: generation, storage: storage, cookieStore: store)
        XCTAssertEqual(storage.cookies?.first?.value, other.value)
        XCTAssertEqual(storage.cookies?.first?.expiresDate, other.expiresDate)

        storage.setCookie(old)
        await store.setCookie(old)
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response(expiry: expiry), expectedGeneration: generation &- 1, storage: storage, cookieStore: store)
        XCTAssertEqual(storage.cookies?.first?.expiresDate, old.expiresDate)
    }

    func testWebKitExpirySyncDoesNotPostAuthChangeOrResetAccount() async throws {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        let loaded = expectation(description: "synthetic document")
        let delegate = RenewalNavigationDelegate(loaded: loaded)
        webView.navigationDelegate = delegate
        webView.loadHTMLString("<html></html>", baseURL: origin)
        await fulfillment(of: [loaded], timeout: 10)
        let old = try cookie(expiry: Date().addingTimeInterval(3600))
        let renewed = try cookie(expiry: Date().addingTimeInterval(30 * 86400))
        HTTPCookieStorage.shared.setCookie(old)
        defer { HTTPCookieStorage.shared.deleteCookie(old) }
        await configuration.websiteDataStore.httpCookieStore.setCookie(renewed)
        let notification = expectation(description: "no auth change for expiry")
        notification.isInverted = true
        let observer = NotificationCenter.default.addObserver(forName: .twoBrainRecDesktopAuthSessionDidChange, object: nil, queue: .main) { _ in notification.fulfill() }
        defer { NotificationCenter.default.removeObserver(observer) }
        let generation = DesktopCabinetSessionBridge.generation
        let revision = DesktopUserTimeContext.shared.revision
        await withCheckedContinuation { continuation in
            DesktopCabinetSessionBridge.syncAuthSessionCookies(from: webView, completion: { continuation.resume() })
        }
        XCTAssertEqual(DesktopCabinetSessionBridge.generation, generation)
        XCTAssertEqual(DesktopUserTimeContext.shared.revision, revision)
        XCTAssertEqual(HTTPCookieStorage.shared.cookies(for: origin)?.first(where: { $0.name == old.name })?.expiresDate, renewed.expiresDate)
        await fulfillment(of: [notification], timeout: 0.1)
    }

    func testRegistry304AndGenericRequestDeliverRenewal() async throws {
        let recorder = RenewalRecorder()
        let client = DesktopUploadClient(baseURL: origin, headers: [:], partSizeBytes: DesktopUploadClient.defaultPartSizeBytes, authSessionTokenProvider: { _ in "synthetic-session" }, requestExecutor: { request in
            let registry = request.url!.path.hasSuffix("target-registry")
            return (Data("{}".utf8), HTTPURLResponse(url: request.url!, statusCode: registry ? 304 : 200, httpVersion: nil, headerFields: ["X-GRAF-Auth-Expires-At": "1800000000"])!)
        }, sessionRenewalHandler: { request, response, _ in
            await recorder.record(request: request, response: response)
        })
        let first = try await client.fetchMeetingDetectionTargetRegistry(ifNoneMatch: "synthetic-etag")
        let second = try await client.fetchMeetingDetectionTargetRegistry(ifNoneMatch: "synthetic-etag")
        XCTAssertTrue(first.notModified && second.notModified)
        // A malformed body still reached authenticated transport before decoding.
        do { _ = try await client.notificationContext() } catch is DecodingError { }
        let statuses = await recorder.statuses
        XCTAssertEqual(statuses, [304, 304, 200])
    }

    private func response(url: URL? = nil, status: Int = 200, expiry: String) -> HTTPURLResponse {
        HTTPURLResponse(url: url ?? origin, statusCode: status, httpVersion: nil, headerFields: ["X-GRAF-Auth-Expires-At": expiry])!
    }

    private func cookie(value: String = "synthetic-session", expiry: Date) throws -> HTTPCookie {
        try XCTUnwrap(HTTPCookie(properties: [.name: DesktopCabinetSessionBridge.authSessionCookieName, .value: value,
            .domain: origin.host!, .path: "/", .secure: "TRUE", .expires: expiry,
            HTTPCookiePropertyKey("HttpOnly"): "TRUE", HTTPCookiePropertyKey("SameSite"): "Lax"]))
    }
}

private actor RenewalRecorder {
    var statuses: [Int] = []
    func record(request: URLRequest, response: URLResponse) {
        statuses.append((response as! HTTPURLResponse).statusCode)
    }
}

@MainActor
private final class RenewalNavigationDelegate: NSObject, WKNavigationDelegate {
    let loaded: XCTestExpectation
    init(loaded: XCTestExpectation) { self.loaded = loaded }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { loaded.fulfill() }
}
