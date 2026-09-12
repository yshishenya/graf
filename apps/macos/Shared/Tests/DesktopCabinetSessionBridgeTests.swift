import Foundation
import SwiftUI
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

    func testNavigationDrainsSubmittedWriteBeforeAccountChangeOrLogout() async throws {
        for logout in [false, true] {
            let storage = HTTPCookieStorage.sharedCookieStorage(forGroupContainerIdentifier: "test.graf.barrier.\(UUID())")
            defer { for cookie in storage.cookies ?? [] { storage.deleteCookie(cookie) } }
            let old = try cookie(expiry: Date().addingTimeInterval(3600))
            let other = try cookie(value: "synthetic-other-account", expiry: Date().addingTimeInterval(3600))
            storage.setCookie(old)
            var web = [old]
            var writes = 0
            var request = URLRequest(url: origin)
            request.setValue(old.value, forHTTPHeaderField: "X-Auth-Session")
            let response = response(expiry: String(Int(Date().addingTimeInterval(86400).timeIntervalSince1970)))
            let started = expectation(description: "WebKit write submitted")
            let write = RenewalSuspension(entered: started)
            let beforeNavigation = DesktopCabinetSessionBridge.generation
            let renewal = Task {
                await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response,
                    expectedGeneration: beforeNavigation, storage: storage, readCookies: { web }, writeCookie: { cookie in
                        writes += 1
                        await write.wait()
                        web = [cookie]
                    })
            }
            await fulfillment(of: [started], timeout: 5)
            let barrier = DesktopCabinetSessionBridge.beginNavigation()
            defer { DesktopCabinetSessionBridge.endNavigation(barrier) }
            let duringNavigation = DesktopCabinetSessionBridge.generation
            let draining = expectation(description: "navigation reached drain")
            var dispatched = false
            let navigation = Task {
                draining.fulfill()
                await DesktopCabinetSessionBridge.drainRenewal()
                dispatched = true
                web = logout ? [] : [other]
            }
            await fulfillment(of: [draining], timeout: 5)
            XCTAssertFalse(dispatched)
            // Even a response whose generation was captured during navigation is denied.
            await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response,
                expectedGeneration: duringNavigation, storage: storage, readCookies: {
                    XCTFail("renewal read during navigation")
                    return web
                }, writeCookie: { _ in XCTFail("renewal write during navigation") })
            write.resume()
            await renewal.value
            await navigation.value
            XCTAssertTrue(dispatched)
            XCTAssertEqual(writes, 1)
            XCTAssertEqual(storage.cookies?.first?.expiresDate, old.expiresDate)
            let plan = DesktopCabinetSessionBridge.reconciliation(webCookies: web, nativeCookies: storage.cookies ?? [], originURL: origin)
            for cookie in plan.cookiesToDelete { storage.deleteCookie(cookie) }
            for cookie in plan.cookiesToSet { storage.setCookie(cookie) }
            DesktopCabinetSessionBridge.endNavigation(barrier)
            for staleGeneration in [beforeNavigation, duringNavigation] {
                await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response,
                    expectedGeneration: staleGeneration, storage: storage, readCookies: { web },
                    writeCookie: { _ in XCTFail("late response overwrote navigation") })
            }
            XCTAssertEqual(web.map(\.value), logout ? [] : [other.value])
            XCTAssertEqual((storage.cookies ?? []).map(\.value), logout ? [] : [other.value])
        }
    }

    func testNavigationOwnersCannotReleaseEachOtherAndRenewalResumesAfterLastOwner() async throws {
        let first = DesktopCabinetSessionBridge.beginNavigation()
        let second = DesktopCabinetSessionBridge.beginNavigation()
        defer {
            DesktopCabinetSessionBridge.endNavigation(first)
            DesktopCabinetSessionBridge.endNavigation(second)
        }
        DesktopCabinetSessionBridge.endNavigation(first)
        DesktopCabinetSessionBridge.endNavigation(first) // stale completion is harmless
        let storage = HTTPCookieStorage.sharedCookieStorage(forGroupContainerIdentifier: "test.graf.owners.\(UUID())")
        let old = try cookie(expiry: Date().addingTimeInterval(3600))
        storage.setCookie(old)
        defer { for cookie in storage.cookies ?? [] { storage.deleteCookie(cookie) } }
        var web = [old]
        var request = URLRequest(url: origin)
        request.setValue(old.value, forHTTPHeaderField: "X-Auth-Session")
        let response = response(expiry: String(Int(Date().addingTimeInterval(86400).timeIntervalSince1970)))
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response,
            expectedGeneration: DesktopCabinetSessionBridge.generation, storage: storage,
            readCookies: { XCTFail("second owner is still navigating"); return web }, writeCookie: { _ in XCTFail() })
        DesktopCabinetSessionBridge.endNavigation(second)
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: response,
            expectedGeneration: DesktopCabinetSessionBridge.generation, storage: storage,
            readCookies: { web }, writeCookie: { web = [$0] })
        XCTAssertGreaterThan(try XCTUnwrap(web.first?.expiresDate), try XCTUnwrap(old.expiresDate))
        XCTAssertEqual(storage.cookies?.first?.expiresDate, web.first?.expiresDate)
    }

    func testCoordinatorWaitsBeforeDispatchAndKeepsBarrierUntilFreshReconciliation() async throws {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = RenewalTestWebView(frame: .zero, configuration: configuration)
        let previousURL = origin.deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("desktop/meetings")
        let nextURL = origin.deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("desktop/settings/account")
        view.documentURL = previousURL
        let coordinator = makeCoordinator(view: view)
        let storage = HTTPCookieStorage.shared
        let store = configuration.websiteDataStore.httpCookieStore
        let old = try cookie(expiry: Date().addingTimeInterval(3600))
        let other = try cookie(value: "synthetic-account-B", expiry: Date().addingTimeInterval(3600))
        storage.setCookie(old)
        await store.setCookie(old)
        defer { coordinator.detachNavigationController(from: view); storage.deleteCookie(old) }
        var request = URLRequest(url: origin)
        request.setValue(old.value, forHTTPHeaderField: "X-Auth-Session")
        let reply = response(expiry: String(Int(Date().addingTimeInterval(86400).timeIntervalSince1970)))
        let started = expectation(description: "submitted real WebKit write")
        let gate = RenewalSuspension(entered: started)
        let before = DesktopCabinetSessionBridge.generation
        let pending = Task {
            await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: reply,
                expectedGeneration: before, storage: storage, readCookies: { await store.allCookies() }, writeCookie: {
                    await gate.wait()
                    await store.setCookie($0)
                })
        }
        await fulfillment(of: [started], timeout: 5)
        let dispatched = expectation(description: "navigation dispatch")
        var didDispatch = false
        coordinator.dispatchAuthNavigation(in: view, targetURL: nextURL,
            decisionHandler: { _ in XCTFail("current navigation was cancelled") }) {
                didDispatch = true
                dispatched.fulfill()
            }
        XCTAssertNotEqual(DesktopCabinetSessionBridge.generation, before)
        XCTAssertFalse(didDispatch)
        // A terminal callback for the preceding document cannot release the new owner.
        coordinator.finishAuthNavigation(in: view, expectedURL: previousURL)
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: reply,
            expectedGeneration: DesktopCabinetSessionBridge.generation, storage: storage,
            readCookies: { XCTFail("renewal before dispatch"); return [] }, writeCookie: { _ in XCTFail() })
        gate.resume()
        await pending.value
        await fulfillment(of: [dispatched], timeout: 5)
        await store.setCookie(other) // login/space-switch response after dispatch
        coordinator.finishAuthNavigation(in: view, expectedURL: previousURL)
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: reply,
            expectedGeneration: DesktopCabinetSessionBridge.generation, storage: storage,
            readCookies: { XCTFail("stale completion released barrier"); return [] }, writeCookie: { _ in XCTFail() })
        let reconciled = expectation(description: "fresh account reconciliation")
        let observer = NotificationCenter.default.addObserver(forName: .twoBrainRecDesktopAuthSessionDidChange,
            object: nil, queue: .main) { _ in reconciled.fulfill() }
        defer { NotificationCenter.default.removeObserver(observer) }
        view.documentURL = nextURL
        coordinator.finishAuthNavigation(in: view, expectedURL: nextURL)
        await fulfillment(of: [reconciled], timeout: 5)
        request.setValue(other.value, forHTTPHeaderField: "X-Auth-Session")
        var renewedAfterFinish = false
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: reply,
            expectedGeneration: DesktopCabinetSessionBridge.generation, storage: storage,
            readCookies: { await store.allCookies() }, writeCookie: {
                renewedAfterFinish = true
                await store.setCookie($0)
            })
        XCTAssertTrue(renewedAfterFinish)
        XCTAssertEqual(DesktopUploadClient.authSessionToken(from: storage.cookies ?? [], origin), other.value)
    }

    func testSameURLFormRejectsPreviousNavigationFinishBeforeNewStart() async throws {
        for logsOut in [false, true] {
            let configuration = WKWebViewConfiguration()
            configuration.websiteDataStore = .nonPersistent()
            let view = RenewalTestWebView(frame: .zero, configuration: configuration)
            let url = URL(string: "https://renewal.example.test/desktop/meetings")!
            view.documentURL = url
            let navigation = EmbeddedCabinetNavigationController()
            let coordinator = makeCoordinator(view: view, navigation: navigation)
            let store = configuration.websiteDataStore.httpCookieStore
            let storage = HTTPCookieStorage.shared
            let old = try cookie(expiry: Date().addingTimeInterval(3600))
            let other = try cookie(value: "synthetic-account-B", expiry: Date().addingTimeInterval(3600))
            storage.setCookie(old)
            await store.setCookie(old)
            let previous = try XCTUnwrap(view.loadHTMLString("<html></html>", baseURL: url))
            coordinator.webView(view, didStartProvisionalNavigation: previous)
            let allowed = expectation(description: "same URL form allowed")
            let action = try await navigationAction(url: url, submitsForm: true)
            coordinator.webView(view, decidePolicyFor: action) { policy in
                XCTAssertEqual(policy, .allow)
                allowed.fulfill()
            }
            await fulfillment(of: [allowed], timeout: 5)
            coordinator.webView(view, didFinish: previous)
            XCTAssertTrue(navigation.isLoading, "previous terminal callback must not finish the new form")
            var request = URLRequest(url: origin)
            request.setValue(old.value, forHTTPHeaderField: "X-Auth-Session")
            let reply = response(expiry: String(Int(Date().addingTimeInterval(86400).timeIntervalSince1970)))
            await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: reply,
                expectedGeneration: DesktopCabinetSessionBridge.generation, storage: storage,
                readCookies: { XCTFail("old same-URL finish released the new barrier"); return [] }, writeCookie: { _ in XCTFail() })
            let current = try XCTUnwrap(view.loadHTMLString("<html></html>", baseURL: url))
            coordinator.webView(view, didStartProvisionalNavigation: current)
            if logsOut { await store.deleteCookie(old) } else { await store.setCookie(other) }
            let reconciled = expectation(description: "form cookie reconciled")
            let observer = NotificationCenter.default.addObserver(forName: .twoBrainRecDesktopAuthSessionDidChange,
                object: nil, queue: .main) { _ in reconciled.fulfill() }
            coordinator.webView(view, didFinish: current)
            await fulfillment(of: [reconciled], timeout: 5)
            NotificationCenter.default.removeObserver(observer)
            XCTAssertEqual(DesktopUploadClient.authSessionToken(from: storage.cookies ?? [], origin), logsOut ? nil : other.value)
            let cleanup = coordinator.detachNavigationController(from: view)
            await cleanup?.value
            storage.deleteCookie(old)
        }
    }

    func testBlockedActionStopsDispatchedNavigationBeforeReleasingBarrier() async throws {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = RenewalTestWebView(frame: .zero, configuration: configuration)
        let url = URL(string: "https://renewal.example.test/desktop/meetings")!
        view.documentURL = url
        let coordinator = makeCoordinator(view: view)
        let storage = HTTPCookieStorage.shared
        let old = try cookie(expiry: Date().addingTimeInterval(3600))
        storage.setCookie(old)
        defer { storage.deleteCookie(old) }
        let allowed = expectation(description: "navigation dispatched")
        let action = try await navigationAction(url: url, submitsForm: true)
        coordinator.webView(view, decidePolicyFor: action) { policy in
            XCTAssertEqual(policy, .allow)
            allowed.fulfill()
        }
        await fulfillment(of: [allowed], timeout: 5)
        let reconciled = expectation(description: "cancelled navigation cookie reconciled")
        let observer = NotificationCenter.default.addObserver(forName: .twoBrainRecDesktopAuthSessionDidChange,
            object: nil, queue: .main) { _ in
                MainActor.assumeIsolated { XCTAssertEqual(view.stopLoadingCount, 1) }
                reconciled.fulfill()
            }
        defer { NotificationCenter.default.removeObserver(observer) }
        let cancelled = expectation(description: "blocked action cancelled")
        let blockedAction = try await navigationAction(
            url: URL(string: "https://renewal.example.test/not-a-cabinet-route")!, submitsForm: false)
        coordinator.webView(view, decidePolicyFor: blockedAction) { policy in
            XCTAssertEqual(policy, .cancel)
            XCTAssertEqual(view.stopLoadingCount, 1)
            cancelled.fulfill()
        }
        await fulfillment(of: [cancelled, reconciled], timeout: 5)
        let newCookie = try cookie(value: "synthetic-new-login", expiry: Date().addingTimeInterval(3600))
        storage.setCookie(newCookie)
        var request = URLRequest(url: origin)
        request.setValue(newCookie.value, forHTTPHeaderField: "X-Auth-Session")
        var renewed = false
        await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request,
            response: response(expiry: String(Int(Date().addingTimeInterval(86400).timeIntervalSince1970))),
            expectedGeneration: DesktopCabinetSessionBridge.generation, storage: storage,
            readCookies: { [newCookie] }, writeCookie: { _ in renewed = true })
        XCTAssertTrue(renewed)
        let cleanup = coordinator.detachNavigationController(from: view)
        await cleanup?.value
    }

    func testDetachedCoordinatorCancelsPendingDispatchAfterDrainingWrite() async throws {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = RenewalTestWebView(frame: .zero, configuration: configuration)
        view.documentURL = origin
        let coordinator = makeCoordinator(view: view)
        let storage = HTTPCookieStorage.sharedCookieStorage(forGroupContainerIdentifier: "test.graf.detach.\(UUID())")
        let old = try cookie(expiry: Date().addingTimeInterval(3600))
        storage.setCookie(old)
        defer { storage.deleteCookie(old) }
        var request = URLRequest(url: origin)
        request.setValue(old.value, forHTTPHeaderField: "X-Auth-Session")
        let started = expectation(description: "write before detach")
        let gate = RenewalSuspension(entered: started)
        let reply = response(expiry: String(Int(Date().addingTimeInterval(86400).timeIntervalSince1970)))
        let before = DesktopCabinetSessionBridge.generation
        let pending = Task {
            await DesktopCabinetSessionBridge.renewAuthSessionCookies(request: request, response: reply,
                expectedGeneration: before, storage: storage, readCookies: { [old] }, writeCookie: { _ in await gate.wait() })
        }
        await fulfillment(of: [started], timeout: 5)
        let cancelled = expectation(description: "detached policy cancelled")
        coordinator.dispatchAuthNavigation(in: view, targetURL: origin, decisionHandler: { policy in
            XCTAssertEqual(policy, .cancel)
            cancelled.fulfill()
        }, dispatch: { XCTFail("detached view dispatched navigation") })
        let detached = coordinator.detachNavigationController(from: view)
        gate.resume()
        await pending.value
        await fulfillment(of: [cancelled], timeout: 5)
        await detached?.value
    }

    private func navigationAction(url: URL, submitsForm: Bool) async throws -> WKNavigationAction {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: .zero, configuration: configuration)
        let loaded = expectation(description: "action source document loaded")
        let captured = expectation(description: "WebKit action captured without dispatch")
        let delegate = RenewalActionCapture(loaded: loaded, captured: captured, target: url)
        view.navigationDelegate = delegate
        view.loadHTMLString("<form method='post' action='\(url.absoluteString)'></form><a href='\(url.absoluteString)'>Open</a>",
            baseURL: URL(string: "https://renewal.example.test/desktop/settings/account")!)
        await fulfillment(of: [loaded], timeout: 10)
        _ = try await view.evaluateJavaScript(submitsForm ? "document.forms[0].submit()" : "document.querySelector('a').click()")
        await fulfillment(of: [captured], timeout: 5)
        let action = try XCTUnwrap(delegate.action)
        XCTAssertEqual(action.navigationType, submitsForm ? .formSubmitted : .linkActivated)
        return action
    }

    private func makeCoordinator(view: WKWebView, navigation: EmbeddedCabinetNavigationController = .init()) -> EmbeddedCabinetWebView.Coordinator {
        let policy = DesktopCabinetRoutePolicy(baseURL: origin)
        let request = URLRequest(url: view.url!)
        navigation.attach(webView: view, routePolicy: policy, fallbackRequest: request, initialRequest: request, sessionExpired: false)
        return EmbeddedCabinetWebView.Coordinator(routePolicy: policy, desktopHeaders: [:],
            cabinetState: .constant(.ready), currentRoute: .constant(view.url), navigationEventLogger: nil,
            showsAppUpdateBadge: false, onCheckForUpdates: {}, onOpenMeetingDetectionSettings: {},
            supportIncidentBridge: nil, notificationPresenter: DesktopNotificationPresenter(
                store: .init(defaults: UserDefaults(suiteName: UUID().uuidString)!),
                model: DesktopControlModel(), status: { .denied }), navigationController: navigation)
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

@MainActor
private final class RenewalSuspension {
    let entered: XCTestExpectation
    private var continuation: CheckedContinuation<Void, Never>?
    init(entered: XCTestExpectation) { self.entered = entered }
    func wait() async {
        await withCheckedContinuation {
            continuation = $0
            entered.fulfill()
        }
    }
    func resume() {
        let pending = continuation
        continuation = nil
        pending?.resume()
    }
}

@MainActor
private final class RenewalTestWebView: WKWebView {
    var documentURL: URL?
    override var url: URL? { documentURL }
    var stopLoadingCount = 0
    override func stopLoading() { stopLoadingCount += 1 }
}

@MainActor
private final class RenewalActionCapture: NSObject, WKNavigationDelegate {
    let loaded: XCTestExpectation
    let captured: XCTestExpectation
    let target: URL
    var action: WKNavigationAction?
    init(loaded: XCTestExpectation, captured: XCTestExpectation, target: URL) {
        self.loaded = loaded
        self.captured = captured
        self.target = target
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { loaded.fulfill() }
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping EmbeddedCabinetNavigationDecisionHandler) {
        if navigationAction.request.url == target {
            action = navigationAction
            decisionHandler(.cancel)
            captured.fulfill()
        } else { decisionHandler(.allow) }
    }
}
