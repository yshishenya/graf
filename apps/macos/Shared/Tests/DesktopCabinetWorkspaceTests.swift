import Foundation
import Combine
import AppKit
import Network
import SwiftUI
import WebKit
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopCabinetWorkspaceTests: XCTestCase {
    func testDesktopUserAgentOnlyIncludesValidatedVersion() {
        XCTAssertEqual(DesktopCabinetConfiguration.applicationNameForUserAgent(version: "2026.09.06.1"), "GRAFDesktop/2026.09.06.1")
        for value in [nil, "", "local", "2026.02.29.1", "2026.09.06.+1", "2026.09.06.1\r\nPrivate: name", "MacBook of Someone"] {
            XCTAssertEqual(DesktopCabinetConfiguration.applicationNameForUserAgent(version: value), "GRAFDesktop/unknown")
        }
    }

    @MainActor
    func testRealCabinetUserAgentSurvivesFormPostAndRedirect() async throws {
        _ = NSApplication.shared
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        let listening = expectation(description: "synthetic auth server ready")
        let get = expectation(description: "initial GET identifies app")
        let post = expectation(description: "form POST identifies app")
        let redirect = expectation(description: "redirect GET identifies app")
        let marker = DesktopCabinetConfiguration.applicationNameForUserAgent()
        listener.stateUpdateHandler = { state in
            if case .ready = state { listening.fulfill() }
        }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .global())
            Self.receiveAuthFixtureRequest(connection, marker: marker, get: get, post: post, redirect: redirect)
        }
        listener.start(queue: .global())
        defer { listener.cancel() }
        await fulfillment(of: [listening], timeout: 5)
        let port = try XCTUnwrap(listener.port)
        let origin = try XCTUnwrap(URL(string: "http://127.0.0.1:\(port.rawValue)"))
        let request = URLRequest(url: origin.appendingPathComponent("login"))
        let cabinet = EmbeddedCabinetWebView(
            request: request, routePolicy: DesktopCabinetRoutePolicy(baseURL: origin),
            cabinetState: .constant(.expiredSession), fallbackRequest: request,
            notificationPresenter: DesktopNotificationPresenter(
                store: .init(defaults: UserDefaults(suiteName: UUID().uuidString)!),
                model: DesktopControlModel()),
            navigationController: EmbeddedCabinetNavigationController()
        )
        let host = NSHostingView(rootView: cabinet)
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 480),
                              styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = host
        window.orderFront(nil)
        defer { window.close() }
        await fulfillment(of: [get], timeout: 10)
        await fulfillment(of: [post, redirect], timeout: 10)
    }

    private nonisolated static func receiveAuthFixtureRequest(
        _ connection: NWConnection, buffered: Data = Data(), marker: String,
        get: XCTestExpectation, post: XCTestExpectation, redirect: XCTestExpectation
    ) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16_384) { data, _, complete, error in
            var received = buffered
            received.append(data ?? Data())
            if received.isEmpty, complete || error != nil { connection.cancel(); return }
            guard let request = String(data: received, encoding: .utf8), request.contains("\r\n\r\n") else {
                guard !complete, error == nil, received.count < 32_768 else {
                    XCTFail("Incomplete synthetic HTTP request"); connection.cancel(); return
                }
                receiveAuthFixtureRequest(connection, buffered: received, marker: marker, get: get, post: post, redirect: redirect)
                return
            }
            let userAgent = request.components(separatedBy: "\r\n").first { $0.lowercased().hasPrefix("user-agent:") } ?? ""
            XCTAssertTrue(userAgent.contains("AppleWebKit/"), "Keep WebKit's base User-Agent")
            XCTAssertTrue(userAgent.contains(marker), "All HTTP steps must identify the application")
            let status: String
            let html: String
            if request.hasPrefix("GET /login ") {
                get.fulfill()
                status = "200 OK"
                html = "<!doctype html><form method='post' action='/login/email/start'><input name='synthetic' value='yes'></form><script>document.forms[0].submit()</script>"
            } else if request.hasPrefix("POST /login/email/start ") {
                post.fulfill()
                status = "303 See Other\r\nLocation: /desktop/settings/account"
                html = ""
            } else if request.hasPrefix("GET /desktop/settings/account ") {
                redirect.fulfill()
                status = "200 OK"
                html = "<!doctype html><title>Synthetic account</title><p>Signed in</p>"
            } else {
                XCTFail("Unexpected synthetic auth route")
                status = "404 Not Found"
                html = ""
            }
            let response = "HTTP/1.1 \(status)\r\nContent-Type: text/html\r\nContent-Length: \(html.utf8.count)\r\nConnection: close\r\n\r\n\(html)"
            connection.send(content: Data(response.utf8), completion: .contentProcessed { _ in connection.cancel() })
        }
    }

    @MainActor
    func testSessionBoundaryOrdinaryGetKeepsWebView() async throws {
        try await checkSessionBoundary(method: "GET")
    }

    @MainActor
    func testSessionBoundarySettingsPostKeepsWebView() async throws {
        try await checkSessionBoundary(method: "POST")
    }

    @MainActor
    func testSessionBoundarySettingsPostRedirectKeepsWebView() async throws {
        try await checkSessionBoundary(method: "POST", redirect: true)
    }

    @MainActor
    func testSessionBoundaryNewFormSupersedesPendingFormWithoutRemount() async throws {
        try await checkSessionBoundary(method: "POST", supersedesPendingForm: true)
    }

    @MainActor
    func testSessionBoundarySettingsPostErrorKeepsWebView() async throws {
        try await checkSessionBoundary(method: "POST", status: "503 Service Unavailable")
    }

    @MainActor
    func testSessionBoundarySettingsPostCancellationKeepsWebView() async throws {
        try await checkSessionBoundary(method: "POST", cancel: true, probeStaleCallbacks: true)
    }

    @MainActor
    func testSessionBoundarySettingsPostNetworkFailureKeepsSafeGet() async throws {
        try await checkSessionBoundary(method: "POST", networkFailure: true)
    }

    @MainActor
    func testSessionBoundaryCommittedPostCancellationRemainsUnsafe() async throws {
        try await checkSessionBoundary(method: "POST", cancel: true, committedCancellation: true)
    }

    @MainActor
    func testSessionBoundaryLoginCommitsFinalDocumentBeforeRemount() async throws {
        try await checkSessionBoundary(method: "GET", initialPath: "/login", changesSession: true)
    }

    @MainActor
    func testSessionBoundaryLogoutRemovesProtectedHistory() async throws {
        try await checkSessionBoundary(method: "GET", targetPath: "/login", changesSession: true)
    }

    @MainActor
    func testSessionBoundaryTrailingSlashLoginRemovesProtectedHistory() async throws {
        try await checkSessionBoundary(method: "GET", targetPath: "/login/", changesSession: true)
    }

    @MainActor
    func testSessionBoundaryTrailingSlashSignupRemovesProtectedHistory() async throws {
        try await checkSessionBoundary(method: "GET", targetPath: "/sign-up/", changesSession: true)
    }

    @MainActor
    func testSessionBoundaryExpiredSessionImmediatelyDisablesProtectedCommands() async throws {
        try await checkSessionBoundary(method: "GET", status: "401 Unauthorized", changesSession: true)
    }

    @MainActor
    func testSessionBoundaryReselectionImmediatelyDisablesProtectedCommands() async throws {
        try await checkSessionBoundary(method: "GET", status: "403 Forbidden", reselect: true, changesSession: true)
    }

    @MainActor
    func testNewGetAfterPostRestoresHistoryWithoutReplayingOldPost() async throws {
        _ = NSApplication.shared
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        let listening = expectation(description: "history fixture listening")
        let requests = SessionBoundaryRequests()
        defer { requests.cancelHeldConnection() }
        listener.stateUpdateHandler = { if case .ready = $0 { listening.fulfill() } }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .global())
            Self.receiveHistoryFixtureRequest(connection, requests: requests)
        }
        listener.start(queue: .global())
        defer { listener.cancel() }
        await fulfillment(of: [listening], timeout: 5)
        let origin = try XCTUnwrap(URL(string: "http://127.0.0.1:\(try XCTUnwrap(listener.port).rawValue)"))
        let sameURL = origin.appendingPathComponent("desktop/settings/account")
        let nextURL = origin.appendingPathComponent("desktop/settings/integrations/calendar")
        let controller = EmbeddedCabinetNavigationController()
        let document = SessionBoundaryDocument(state: .ready)
        let presenter = DesktopNotificationPresenter(
            store: .init(defaults: UserDefaults(suiteName: UUID().uuidString)!), model: DesktopControlModel())
        let host = NSHostingView(rootView: SessionBoundaryFixture(request: URLRequest(url: sameURL),
            origin: origin, controller: controller, document: document, presenter: presenter))
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 480),
            styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = host
        host.layoutSubtreeIfNeeded()
        defer { window.close() }
        let web = try XCTUnwrap(Self.sessionFixtureWebView(host))
        func waitForDocument(_ marker: String, reloadFinished: Bool = false) async throws {
            for _ in 0..<250 {
                if !controller.isLoading, !web.isLoading, (!reloadFinished || controller.canReload),
                   (try? await web.evaluateJavaScript("document.body.dataset.result")) as? String == marker { return }
                try await Task.sleep(for: .milliseconds(20))
            }
            XCTFail("History fixture did not settle at \(marker)")
        }
        try await waitForDocument("GET /desktop/settings/account")
        XCTAssertTrue(controller.canReload)
        _ = try await web.evaluateJavaScript("document.forms[0].submit(); true")
        try await waitForDocument("POST /desktop/settings/account")
        let postItem = try XCTUnwrap(web.backForwardList.currentItem)
        XCTAssertFalse(controller.canReload, "Synthetic finish GET cannot rehabilitate a POST entry")
        _ = web.load(URLRequest(url: nextURL))
        try await waitForDocument("GET /desktop/settings/integrations/calendar")
        _ = web.load(URLRequest(url: sameURL))
        try await waitForDocument("GET /desktop/settings/account")
        let getItem = try XCTUnwrap(web.backForwardList.currentItem)
        XCTAssertFalse(getItem === postItem, "WebKit must retain distinct entries for POST and a new GET at one URL")
        XCTAssertTrue(controller.canReload, "A real new GET must restore Reload despite the old POST at this URL")
        guard controller.canReload else { return }
        controller.reload()
        try await waitForDocument("GET /desktop/settings/account", reloadFinished: true)
        _ = web.load(URLRequest(url: nextURL))
        try await waitForDocument("GET /desktop/settings/integrations/calendar")
        XCTAssertTrue(controller.canGoBack, "Safe GET history remains useful")
        controller.goBack()
        try await waitForDocument("GET /desktop/settings/account")
        XCTAssertTrue(controller.canReload)
        XCTAssertTrue(controller.canGoForward)
        controller.goForward()
        try await waitForDocument("GET /desktop/settings/integrations/calendar")
        controller.goBack()
        try await waitForDocument("GET /desktop/settings/account")
        controller.goBack()
        try await waitForDocument("GET /desktop/settings/integrations/calendar")
        controller.goBack()
        try await waitForDocument("GET /desktop/settings/account")
        XCTAssertFalse(web.backForwardList.currentItem === postItem, "Native Back skips the old POST entry, rather than selecting it and stalling")
        controller.goForward()
        try await waitForDocument("GET /desktop/settings/integrations/calendar")
        controller.goForward()
        try await waitForDocument("GET /desktop/settings/account")
        controller.goForward()
        try await waitForDocument("GET /desktop/settings/integrations/calendar")
        // Exercise WebKit's own history path, including a POST entry whose URL
        // is identical to the later, explicitly loaded safe GET entry.
        let coordinator = try XCTUnwrap(web.navigationDelegate as? EmbeddedCabinetWebView.Coordinator)
        let historyDecision = expectation(description: "real coordinator rejects old POST history")
        let probe = HistoryPolicyProbe(coordinator: coordinator, decision: historyDecision)
        web.navigationDelegate = probe
        _ = web.go(to: postItem)
        await fulfillment(of: [historyDecision], timeout: 5)
        web.navigationDelegate = coordinator
        XCTAssertEqual(probe.policy, .cancel, "The actual coordinator must reject the old entry before dispatch")
        XCTAssertEqual(probe.method, "POST")
        for _ in 0..<250 {
            if web.backForwardList.currentItem !== postItem, !web.isLoading { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertEqual(web.url, nextURL, "An old POST entry cannot become navigable because another entry used GET")
        XCTAssertFalse(web.backForwardList.currentItem === postItem)
        XCTAssertEqual(requests.count("POST /desktop/settings/account"), 1, "Neither native navigation nor WebKit history may resubmit the form")
        XCTAssertTrue(Self.sessionFixtureWebView(host) === web, "Ordinary requests preserve the live WebView")

        // A superseded safe request followed by a failed download does not
        // finish a new document or rehabilitate the preceding POST entry.
        let source = origin.appendingPathComponent("desktop/meetings/history-source")
        _ = web.load(URLRequest(url: source))
        try await waitForDocument("GET /desktop/meetings/history-source")
        _ = try await web.evaluateJavaScript("document.forms[0].submit(); true")
        try await waitForDocument("POST /desktop/meetings/history-source")
        let sourcePost = try XCTUnwrap(web.backForwardList.currentItem)
        XCTAssertFalse(controller.canReload)
        _ = web.load(URLRequest(url: origin.appendingPathComponent("desktop/meetings/history-pending")))
        for _ in 0..<250 {
            if requests.count("GET /desktop/meetings/history-pending") == 1 { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertEqual(requests.count("GET /desktop/meetings/history-pending"), 1)
        XCTAssertTrue(controller.isLoading)
        _ = try await web.evaluateJavaScript("location.href='/api/v1/cabinet/meetings/history-source/downloads/summary'; true")
        for _ in 0..<250 {
            if requests.count("GET /api/v1/cabinet/meetings/history-source/downloads/summary") == 1,
               !controller.isLoading, !web.isLoading { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertEqual(requests.count("GET /api/v1/cabinet/meetings/history-source/downloads/summary"), 1)
        XCTAssertFalse(controller.isLoading)
        XCTAssertTrue(web.backForwardList.currentItem === sourcePost, "A resource result leaves the POST document unchanged")
        XCTAssertFalse(controller.canReload, "An excluded resource cannot certify a document GET or make a POST replayable")
        requests.cancelHeldConnection()
    }

    private nonisolated static func receiveHistoryFixtureRequest(
        _ connection: NWConnection, buffered: Data = Data(), requests: SessionBoundaryRequests
    ) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16_384) { data, _, complete, error in
            var received = buffered; received.append(data ?? Data())
            if received.isEmpty, complete || error != nil { connection.cancel(); return }
            guard let request = String(data: received, encoding: .utf8), request.contains("\r\n\r\n") else {
                guard !complete, error == nil, received.count < 32_768 else {
                    XCTFail("Incomplete synthetic history request"); connection.cancel(); return
                }
                receiveHistoryFixtureRequest(connection, buffered: received, requests: requests)
                return
            }
            let key = request.components(separatedBy: "\r\n")[0].split(separator: " ").prefix(2).joined(separator: " ")
            guard ["GET /desktop/settings/account", "POST /desktop/settings/account", "GET /desktop/settings/integrations/calendar",
                   "GET /desktop/meetings/history-source", "POST /desktop/meetings/history-source",
                   "GET /desktop/meetings/history-pending", "GET /api/v1/cabinet/meetings/history-source/downloads/summary"].contains(key) else {
                XCTFail("Unexpected synthetic history route"); connection.cancel(); return
            }
            _ = requests.record(key)
            if key == "GET /desktop/meetings/history-pending" { requests.hold(connection); return }
            let path = key.split(separator: " ").last!
            let html = "<!doctype html><body data-result='\(key)'><form method='post' action='\(path)'><input name='synthetic' value='yes'></form></body>"
            let status = key.contains("/downloads/") ? "404 Not Found" : "200 OK"
            let response = "HTTP/1.1 \(status)\r\nContent-Type: text/html\r\nCache-Control: no-store\r\nContent-Length: \(html.utf8.count)\r\nConnection: close\r\n\r\n\(html)"
            connection.send(content: Data(response.utf8), completion: .contentProcessed { _ in connection.cancel() })
        }
    }

    @MainActor
    func testRealWorkspaceRetainsFinishedDocumentAfterProvisionalCancellation() async throws {
        try await checkRealWorkspaceCancellation()
    }

    @MainActor
    func testRealWorkspaceRestoresRouteAfterDifferentGetCancellation() async throws {
        try await checkRealWorkspaceCancellation(differentGet: true)
    }

    @MainActor
    func testRealWorkspaceRestoresNotificationSettingsAfterProvisionalCancellation() async throws {
        try await checkRealWorkspaceCancellation(notifications: true)
    }

    @MainActor
    func testRealWorkspaceInitialCancellationDoesNotBecomeReady() async throws {
        try await checkRealWorkspaceCancellation(holdInitial: true)
    }

    @MainActor
    func testRealWorkspaceCommittedPostCancellationDoesNotBecomeReady() async throws {
        try await checkRealWorkspaceCancellation(committed: true)
    }

    @MainActor
    private func checkRealWorkspaceCancellation(holdInitial: Bool = false, committed: Bool = false, notifications: Bool = false, differentGet: Bool = false) async throws {
        _ = NSApplication.shared
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        let listening = expectation(description: "real workspace fixture listening")
        let initial = expectation(description: "initial workspace request")
        let submitted = expectation(description: "one explicit request")
        let result = expectation(description: "held response")
        if holdInitial { submitted.isInverted = true; result.isInverted = true }
        let requests = SessionBoundaryRequests()
        let path = notifications ? "/desktop/settings/notifications" : "/desktop/settings/recording"
        let targetPath = differentGet ? "/desktop/settings/account" : path
        let connectionCount = notifications ? "window.notificationConnections" : "window.recordingConnections"
        listener.stateUpdateHandler = { if case .ready = $0 { listening.fulfill() } }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .global())
            Self.receiveSessionFixtureRequest(connection, initialPath: path, targetPath: targetPath,
                method: differentGet ? "GET" : "POST", status: "200 OK", cancel: true, reselect: false, redirect: false,
                initial: initial, submitted: submitted, result: result, requests: requests, resultCount: 1,
                committedCancellation: committed, holdInitial: holdInitial)
        }
        listener.start(queue: .global())
        defer { requests.cancelHeldConnection(); listener.cancel() }
        await fulfillment(of: [listening], timeout: 5)
        let origin = try XCTUnwrap(URL(string: "http://127.0.0.1:\(try XCTUnwrap(listener.port).rawValue)"))
        let url = origin.appendingPathComponent(path)
        let document = SessionBoundaryDocument(state: .loading)
        let suite = "F136-workspace-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let user = UUID(), workspace = UUID()
        let presenter = DesktopNotificationPresenter(store: .init(defaults: defaults), model: DesktopControlModel(),
            contextProvider: { DesktopNotificationContext(user_id: user, workspace_id: workspace, recording_deletion_protocol_version: nil) })
        let host = NSHostingView(rootView: RealWorkspaceFixture(configuration: .init(baseURL: origin),
            initialRoute: url, document: document, presenter: presenter))
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 800, height: 600),
            styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = host
        host.layoutSubtreeIfNeeded()
        defer { window.close() }
        await fulfillment(of: [initial], timeout: 10)
        let web = try XCTUnwrap(Self.sessionFixtureWebView(host))
        if !holdInitial {
            for _ in 0..<250 {
                if document.state == .ready, !web.isLoading,
                   (try? await web.evaluateJavaScript(connectionCount)) as? Int == 1 { break }
                try await Task.sleep(for: .milliseconds(20))
            }
            XCTAssertEqual(document.state, .ready)
            let connections = try await web.evaluateJavaScript(connectionCount)
            XCTAssertEqual(connections as? Int, 1)
        }
        let initialNonce = notifications ? try await web.evaluateJavaScript("window.notificationNonce") as? String : nil
        let item = web.backForwardList.currentItem
        var probe: CommittedNavigationProbe?
        if committed {
            let coordinator = try XCTUnwrap(web.navigationDelegate as? EmbeddedCabinetWebView.Coordinator)
            probe = CommittedNavigationProbe(coordinator: coordinator,
                committed: expectation(description: "actual POST commit"))
            web.navigationDelegate = probe
        }
        if !holdInitial {
            _ = try await web.evaluateJavaScript("document.forms[0].submit(); true")
            await fulfillment(of: [submitted, result], timeout: 10)
        }
        if let probe {
            await fulfillment(of: [probe.committed], timeout: 5)
            for _ in 0..<250 {
                if requests.count("GET /f136-held-resource") == 1 { break }
                try await Task.sleep(for: .milliseconds(20))
            }
            XCTAssertEqual(requests.count("GET /f136-held-resource"), 1)
            XCTAssertFalse(web.backForwardList.currentItem === item)
            XCTAssertEqual(probe.finishCount, 0)
        }
        XCTAssertEqual(document.state, .loading)
        web.stopLoading()
        for _ in 0..<250 {
            if document.state != .loading { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        // Let SwiftUI reconcile the production visibility branch, then search
        // the actual view tree; a retained local reference alone proves nothing.
        for _ in 0..<10 {
            host.layoutSubtreeIfNeeded()
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertEqual(requests.count("GET \(path)"), 1)
        XCTAssertEqual(requests.count("POST \(path)"), holdInitial || differentGet ? 0 : 1)
        if differentGet { XCTAssertEqual(requests.count("GET \(targetPath)?result=yes"), 1) }
        if holdInitial || committed {
            if holdInitial { await fulfillment(of: [submitted, result], timeout: 0.1) }
            XCTAssertEqual(document.state, .malformedResponse)
            XCTAssertNil(Self.sessionFixtureWebView(host), "An unconfirmed document must not be restored as ready")
            return
        }
        XCTAssertEqual(document.state, .ready, "Expected provisional cancellation preserves the finished document")
        guard let visibleWeb = Self.sessionFixtureWebView(host) else {
            XCTFail("The actual workspace removed its finished document after cancellation")
            return
        }
        XCTAssertTrue(visibleWeb === web)
        XCTAssertTrue(visibleWeb.window === window)
        XCTAssertTrue(visibleWeb.backForwardList.currentItem === item)
        XCTAssertEqual(document.route?.path, path)
        let container = try XCTUnwrap(visibleWeb.superview as? EmbeddedCabinetWebView.WebViewContainer)
        XCTAssertEqual(container.lastLoadedRequestIdentity, EmbeddedCabinetWebView.loadIdentity(url: url))
        let dom = try await visibleWeb.evaluateJavaScript("Boolean(document.forms[0])")
        XCTAssertEqual(dom as? Bool, true)
        for _ in 0..<250 {
            if (try? await visibleWeb.evaluateJavaScript(connectionCount)) as? Int == 2 { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        let connections = try await visibleWeb.evaluateJavaScript(connectionCount)
        XCTAssertEqual(connections as? Int, 2, "Retained settings need a new bridge activation")
        if notifications {
            let nonceValue = try await visibleWeb.evaluateJavaScript("window.notificationNonce")
            let nonce = try XCTUnwrap(nonceValue as? String)
            XCTAssertNotEqual(nonce, initialNonce, "A retained document needs a new notification nonce")
            let canEdit = try await visibleWeb.callAsyncJavaScript("""
                const result = await window.webkit.messageHandlers.grafNotificationSettings.postMessage({version:2,nonce:window.notificationNonce,action:'read'});
                return result.canEdit;
                """, arguments: [:], in: nil, contentWorld: .page)
            XCTAssertEqual(canEdit as? Bool, true)
            let oldRejected = try await visibleWeb.callAsyncJavaScript("""
                try { await window.webkit.messageHandlers.grafNotificationSettings.postMessage({version:2,nonce:oldNonce,action:'read'}); return false; }
                catch { return true; }
                """, arguments: ["oldNonce": try XCTUnwrap(initialNonce)], in: nil, contentWorld: .page)
            XCTAssertEqual(oldRejected as? Bool, true, "The pre-navigation connection remains revoked")
        }
        _ = try await visibleWeb.evaluateJavaScript("window.domStillWorks = 42; true")
        let domValue = try await visibleWeb.evaluateJavaScript("window.domStillWorks")
        XCTAssertEqual(domValue as? Int, 42)
        _ = visibleWeb.reload()
        for _ in 0..<250 {
            if requests.count("GET \(path)") == 2, document.state == .ready, !visibleWeb.isLoading { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertEqual(requests.count("GET \(path)"), 2)
        XCTAssertEqual(requests.count("POST \(path)"), differentGet ? 0 : 1, "Reload cannot replay the cancelled form")
        if differentGet { XCTAssertEqual(requests.count("GET \(targetPath)?result=yes"), 1, "Reconciliation and Reload cannot retry the cancelled destination") }
    }

    @MainActor
    private func checkSessionBoundary(
        method: String, initialPath: String = "/desktop/settings/account",
        targetPath: String = "/desktop/settings/account", status: String = "200 OK",
        cancel: Bool = false, reselect: Bool = false, changesSession: Bool = false, redirect: Bool = false,
        supersedesPendingForm: Bool = false, networkFailure: Bool = false,
        committedCancellation: Bool = false, probeStaleCallbacks: Bool = false
    ) async throws {
        let trace = { (phase: String) in
            FileHandle.standardError.write(Data("F136_NATIVE_SESSION \(phase) method=\(method) status=\(status)\n".utf8))
        }
        trace("start")
        _ = NSApplication.shared
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        let listening = expectation(description: "session fixture listening")
        let submitted = expectation(description: "one explicit form submission")
        let initial = expectation(description: "initial document")
        let requests = SessionBoundaryRequests()
        defer { requests.cancelHeldConnection() }
        let result = expectation(description: "result request and only the permitted session remount")
        result.expectedFulfillmentCount = changesSession ? 2 : 1
        listener.stateUpdateHandler = { if case .ready = $0 { listening.fulfill() } }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .global())
            Self.receiveSessionFixtureRequest(connection, initialPath: initialPath, targetPath: targetPath,
                method: method, status: status, cancel: cancel, reselect: reselect, redirect: redirect,
                initial: initial, submitted: submitted, result: result, requests: requests, resultCount: changesSession ? 2 : 1,
                supersedesPendingForm: supersedesPendingForm, networkFailure: networkFailure,
                committedCancellation: committedCancellation)
        }
        listener.start(queue: .global())
        defer { listener.cancel() }
        await fulfillment(of: [listening], timeout: 5)
        trace("listener-ready")
        if method == "GET", !changesSession {
            // WebKit may close a speculative connection without sending HTTP.
            let unusedClosed = expectation(description: "unused connection closed")
            let unused = NWConnection(host: "127.0.0.1", port: try XCTUnwrap(listener.port), using: .tcp)
            unused.start(queue: .global())
            unused.send(content: nil, contentContext: .finalMessage, isComplete: true, completion: .contentProcessed { error in
                XCTAssertNil(error)
            })
            unused.receive(minimumIncompleteLength: 1, maximumLength: 1) { _, _, complete, error in
                XCTAssertTrue(complete || error != nil)
                unused.cancel()
                unusedClosed.fulfill()
            }
            await fulfillment(of: [unusedClosed], timeout: 5)
        }
        let origin = try XCTUnwrap(URL(string: "http://127.0.0.1:\(try XCTUnwrap(listener.port).rawValue)"))
        let request = URLRequest(url: origin.appendingPathComponent(initialPath))
        let controller = EmbeddedCabinetNavigationController()
        let document = SessionBoundaryDocument(state: initialPath == "/login" ? .expiredSession : .ready)
        let presenter = DesktopNotificationPresenter(
            store: .init(defaults: UserDefaults(suiteName: UUID().uuidString)!), model: DesktopControlModel())
        let host = NSHostingView(rootView: SessionBoundaryFixture(
            request: request, origin: origin, controller: controller, document: document, presenter: presenter))
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 480),
            styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = host
        trace("host-attached")
        host.layoutSubtreeIfNeeded()
        trace("host-laid-out")
        defer { window.close() }
        await fulfillment(of: [initial], timeout: 10)
        for _ in 0..<250 {
            if controller.canReload { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        trace("initial-loaded")
        XCTAssertTrue(controller.canReload, "Initial stable document must finish")
        let boundary = controller.sessionBoundaryID
        let webView = try XCTUnwrap(Self.sessionFixtureWebView(host))
        let coordinator = try XCTUnwrap(webView.navigationDelegate as? EmbeddedCabinetWebView.Coordinator)
        func waitForDocument(at url: URL) async throws {
            for _ in 0..<250 {
                if webView.url == url, !controller.isLoading, !webView.isLoading { return }
                try await Task.sleep(for: .milliseconds(20))
            }
            XCTFail("Navigation did not finish at the expected synthetic document")
        }
        var staleNavigation: WKNavigation?
        if probeStaleCallbacks {
            staleNavigation = try XCTUnwrap(webView.reload())
            for _ in 0..<250 {
                if requests.count("GET \(initialPath)") == 2, !controller.isLoading, !webView.isLoading { break }
                try await Task.sleep(for: .milliseconds(20))
            }
            XCTAssertEqual(requests.count("GET \(initialPath)"), 2)
            XCTAssertTrue(controller.canReload)
        }
        let initialItem = try XCTUnwrap(webView.backForwardList.currentItem)
        var probe: CommittedNavigationProbe?
        if committedCancellation {
            probe = CommittedNavigationProbe(coordinator: coordinator,
                committed: expectation(description: "real POST document committed before cancellation"))
            webView.navigationDelegate = probe
        }
        var boundaryCount = 0
        let observation = controller.$sessionBoundaryID.dropFirst().sink { _ in
            boundaryCount += 1
            if changesSession, status == "200 OK" {
                XCTAssertEqual(document.route?.path, URL(string: targetPath)?.path, "Final route precedes the successful session boundary")
                XCTAssertEqual(document.state, ["/login", "/login/", "/sign-up/"].contains(targetPath) ? .expiredSession : .ready,
                    "Final state precedes the successful session boundary")
            }
        }
        defer { observation.cancel() }
        _ = try await webView.evaluateJavaScript("document.forms[0].submit(); true")
        await fulfillment(of: [submitted], timeout: 10)
        if supersedesPendingForm {
            XCTAssertTrue(controller.isLoading, "First form is waiting for its server response")
            XCTAssertEqual(controller.sessionBoundaryID, boundary)
            // Keep native WebKit callbacks: the second explicit submission must
            // cancel the provisional first one, even for the same URL and body.
            _ = try await webView.evaluateJavaScript("document.forms[0].submit(); true")
        }
        if let staleNavigation {
            coordinator.webView(webView, didCommit: staleNavigation)
            coordinator.webView(webView, didFinish: staleNavigation)
            coordinator.webView(webView, didFail: staleNavigation, withError: URLError(.cancelled))
            XCTAssertTrue(controller.isLoading, "Stale callbacks must not retire the pending form")
            XCTAssertTrue(webView.backForwardList.currentItem === initialItem)
        }
        if committedCancellation {
            let probe = try XCTUnwrap(probe)
            await fulfillment(of: [probe.committed], timeout: 5)
            for _ in 0..<250 {
                if requests.count("GET /f136-held-resource") == 1 { break }
                try await Task.sleep(for: .milliseconds(20))
            }
            XCTAssertEqual(requests.count("GET /f136-held-resource"), 1)
            XCTAssertFalse(webView.backForwardList.currentItem === initialItem)
            XCTAssertTrue(webView.isLoading, "The committed document is waiting for its held resource")
            XCTAssertEqual(probe.finishCount, 0, "Cancellation must occur before didFinish")
        }
        if cancel { webView.stopLoading() }
        await fulfillment(of: [result], timeout: 10)
        for _ in 0..<250 {
            if !controller.isLoading, document.state != .loading { break }
            try await Task.sleep(for: .milliseconds(20))
        }
        trace("terminal-callback")
        XCTAssertFalse(controller.isLoading, "Terminal callback must release navigation")
        XCTAssertNotEqual(document.state, .loading)
        if cancel { XCTAssertEqual(document.state, committedCancellation ? .malformedResponse : .ready) }
        XCTAssertEqual(controller.sessionBoundaryID == boundary, !changesSession)
        XCTAssertEqual(boundaryCount, changesSession ? 1 : 0)
        let initialGetCount = probeStaleCallbacks ? 2 : 1
        XCTAssertEqual(requests.count("GET \(initialPath)"), initialGetCount, "The initial document must not be reloaded after a form")
        XCTAssertEqual(requests.count("\(method) \(targetPath)" + (method == "GET" ? "?result=yes" : "")),
            changesSession || supersedesPendingForm ? 2 : 1)
        if redirect { XCTAssertEqual(requests.count("GET \(targetPath)?result=yes"), 1) }
        let currentWebView = try XCTUnwrap(Self.sessionFixtureWebView(host))
        if !changesSession {
            XCTAssertTrue(currentWebView === webView, "Ordinary form results/errors/cancellation keep the live WebView")
        } else {
            XCTAssertFalse(controller.canGoBack, "Previous session history must be inaccessible")
            XCTAssertFalse(controller.canGoForward)
            if status != "200 OK" || ["/login", "/login/", "/sign-up/"].contains(targetPath) {
                XCTAssertFalse(controller.canGoHome, "An expired session cannot navigate to protected home")
            }
        }
        if committedCancellation {
            XCTAssertFalse(controller.canReload, "A committed POST stays unsafe even without didFinish")
            let postItem = try XCTUnwrap(webView.backForwardList.currentItem)
            let postCount = requests.count("POST \(targetPath)")
            controller.reload()
            XCTAssertEqual(requests.count("POST \(targetPath)"), postCount)
            XCTAssertEqual(try XCTUnwrap(probe).finishCount, 0)
            webView.navigationDelegate = coordinator
            let next = origin.appendingPathComponent("desktop/settings/integrations/calendar")
            _ = webView.load(URLRequest(url: next))
            try await waitForDocument(at: next)
            _ = webView.load(request)
            try await waitForDocument(at: try XCTUnwrap(request.url))
            XCTAssertTrue(controller.canReload, "A new completed GET can certify its own entry")
            controller.goBack()
            try await waitForDocument(at: next)
            controller.goBack()
            try await waitForDocument(at: try XCTUnwrap(request.url))
            XCTAssertFalse(webView.backForwardList.currentItem === postItem, "Back skips the committed but unfinished POST")
            XCTAssertEqual(requests.count("POST \(targetPath)"), postCount)
        } else if method == "POST", !changesSession, cancel || networkFailure || status != "200 OK" {
            XCTAssertTrue(webView.backForwardList.currentItem === initialItem, "An uncommitted form preserves the GET document")
            XCTAssertTrue(controller.canReload, "A failed provisional POST must not poison the preceding GET")
            if controller.canReload {
                controller.reload()
                for _ in 0..<250 {
                    if requests.count("GET \(initialPath)") == initialGetCount + 1, !controller.isLoading, !webView.isLoading { break }
                    try await Task.sleep(for: .milliseconds(20))
                }
                XCTAssertEqual(requests.count("GET \(initialPath)"), initialGetCount + 1)
                XCTAssertEqual(requests.count("POST \(targetPath)"), 1, "Reload must issue GET, never replay the form")
                XCTAssertTrue(controller.canReload)
                XCTAssertEqual(controller.sessionBoundaryID, boundary)
                let next = origin.appendingPathComponent("desktop/settings/integrations/calendar")
                _ = webView.load(URLRequest(url: next))
                try await waitForDocument(at: next)
                XCTAssertTrue(controller.canGoBack)
                controller.goBack()
                try await waitForDocument(at: try XCTUnwrap(request.url))
                XCTAssertEqual(webView.url, request.url)
                XCTAssertTrue(controller.canReload)
                XCTAssertTrue(controller.canGoForward)
                controller.goForward()
                try await waitForDocument(at: next)
                XCTAssertEqual(webView.url, next)
                XCTAssertEqual(requests.count("POST \(targetPath)"), 1)
            }
        }
        if status == "200 OK", !cancel, !networkFailure {
            XCTAssertEqual(document.route?.path, URL(string: targetPath)?.path)
            let loaded = try await currentWebView.evaluateJavaScript("Boolean(document.getElementById('result'))")
            XCTAssertEqual(loaded as? Bool, true, "Keep the actual form result after SwiftUI reconciliation")
        }
    }

    @MainActor
    private static func sessionFixtureWebView(_ view: NSView) -> WKWebView? {
        if let web = view as? WKWebView { return web }
        return view.subviews.lazy.compactMap { sessionFixtureWebView($0) }.first
    }

    private nonisolated static func receiveSessionFixtureRequest(
        _ connection: NWConnection, data: Data = Data(), initialPath: String, targetPath: String,
        method: String, status: String, cancel: Bool, reselect: Bool, redirect: Bool,
        initial: XCTestExpectation, submitted: XCTestExpectation, result: XCTestExpectation,
        requests: SessionBoundaryRequests, resultCount: Int, supersedesPendingForm: Bool = false,
        networkFailure: Bool = false, committedCancellation: Bool = false, holdInitial: Bool = false
    ) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16_384) { chunk, _, complete, error in
            var bytes = data; bytes.append(chunk ?? Data())
            if bytes.isEmpty, complete || error != nil { connection.cancel(); return }
            guard let request = String(data: bytes, encoding: .utf8), request.contains("\r\n\r\n") else {
                guard !complete, error == nil, bytes.count < 32_768 else {
                    XCTFail("Incomplete synthetic session request"); connection.cancel(); return
                }
                receiveSessionFixtureRequest(connection, data: bytes, initialPath: initialPath,
                    targetPath: targetPath, method: method, status: status, cancel: cancel, reselect: reselect, redirect: redirect,
                    initial: initial, submitted: submitted, result: result, requests: requests, resultCount: resultCount,
                    supersedesPendingForm: supersedesPendingForm, networkFailure: networkFailure,
                    committedCancellation: committedCancellation, holdInitial: holdInitial)
                return
            }
            let key = request.components(separatedBy: "\r\n")[0].split(separator: " ").prefix(2).joined(separator: " ")
            let count = requests.record(key)
            if committedCancellation, key == "GET /f136-held-resource" {
                requests.hold(connection)
                return
            }
            let isPost = request.hasPrefix("POST \(targetPath) ")
            let isResult = isPost || request.hasPrefix("GET \(targetPath)?result=yes ")
            let html: String
            let replyStatus: String
            if isResult {
                if supersedesPendingForm, isPost, count == 1 {
                    requests.hold(connection)
                    submitted.fulfill()
                    return
                }
                if count == 1, isPost || method == "GET" { submitted.fulfill() }
                if (supersedesPendingForm ? count == 2 : count <= resultCount), !redirect || !isPost { result.fulfill() }
                if supersedesPendingForm { requests.attemptHeldRedirect() }
                html = "<!doctype html><title>Synthetic result</title><p id='result'>Result</p>"
                    + (committedCancellation && isPost ? "<img src='/f136-held-resource'>" : "")
                replyStatus = redirect && isPost ? "303 See Other\r\nLocation: \(targetPath)?result=yes" : status
            } else if key == "GET /desktop/settings/integrations/calendar" {
                html = "<!doctype html><title>Next safe document</title>"
                replyStatus = "200 OK"
            } else if request.hasPrefix("GET \(initialPath) ") {
                if count == 1 { initial.fulfill() }
                if holdInitial { requests.hold(connection); return }
                html = "<!doctype html><title>Synthetic form</title><form method='\(method.lowercased())' action='\(targetPath)'><input name='result' value='yes'></form><script>window.recordingConnections=0;window.GRAFRecordingSettings={connect(){recordingConnections++}};window.notificationConnections=0;window.GRAFNotificationSettings={connect(nonce){notificationConnections++;window.notificationNonce=nonce},disconnect(){window.notificationNonce=null}};</script>"
                replyStatus = "200 OK"
            } else {
                XCTFail("Unexpected synthetic session route"); connection.cancel(); return
            }
            let recovery = reselect && isResult ? "X-GRAF-Cabinet-Recovery: reselect-space\r\n" : ""
            let length = html.utf8.count
            let response = "HTTP/1.1 \(replyStatus)\r\nContent-Type: text/html\r\nCache-Control: no-store\r\n\(recovery)Content-Length: \(length)\r\nConnection: close\r\n\r\n\(html)"
            if networkFailure && isResult {
                connection.cancel()
            } else if cancel && isResult && !committedCancellation {
                requests.hold(connection)
            } else {
                connection.send(content: Data(response.utf8), completion: .contentProcessed { _ in connection.cancel() })
            }
        }
    }

    func testDefaultWorkspaceOpensMeetingsList() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))

        XCTAssertEqual(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).absoluteString, "https://rec.2brain.dev/desktop/meetings")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.workspace, "desktop-cabinet-workspace")
        XCTAssertFalse(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).path.localizedCaseInsensitiveContains("diagnostic"))
        XCTAssertFalse(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).path.localizedCaseInsensitiveContains("settings"))
    }

    func testCabinetUrlRequestKeepsDesktopHeadersOnSameOriginOnly() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [
                "Authorization": "Bearer SECRET",
                "X-Workspace-Id": "workspace-033",
                "X-Device-Id": "device-033",
                "X-User-Id": "user-033",
                "X-Organization-Id": "organization-033"
            ]
        ))

        let sameOriginRequest = configuration.urlRequest(
            for: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings"))
        )
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "Authorization"), "Bearer SECRET")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-Device-Id"), "device-033")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-User-Id"), "user-033")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-Organization-Id"), "organization-033")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-GRAF-Client"), "desktop")

        for externalURL in [
            "https://attacker.example/oauth/authorize?state=state",
            "http://rec.2brain.dev/desktop/meetings",
            "https://rec.2brain.dev:8443/desktop/meetings",
            "https://sub.rec.2brain.dev/desktop/meetings"
        ] {
            let externalProviderRequest = configuration.urlRequest(
                for: try XCTUnwrap(URL(string: externalURL))
            )
            for header in [
                "Authorization",
                "X-Workspace-Id",
                "X-Device-Id",
                "X-User-Id",
                "X-Organization-Id"
            ] {
                XCTAssertNil(externalProviderRequest.value(forHTTPHeaderField: header), externalURL)
            }
            XCTAssertNil(externalProviderRequest.value(forHTTPHeaderField: "X-GRAF-Client"), externalURL)
        }
    }

    func testWorkspaceOpensMeetingDetailDestination() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))

        XCTAssertEqual(
            DesktopCabinetWorkspace.detailRoute(meetingId: "meeting-033", configuration: configuration).absoluteString,
            "https://rec.2brain.dev/desktop/meetings/meeting-033"
        )
    }

    func testMeetingDetailBackReturnsToListWhenWebHistoryIsNotAUsableMeetingRoute() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let detail = configuration.meetingDetailURL(meetingId: "meeting-033")
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        let external = try XCTUnwrap(URL(string: "https://accounts.example/login"))

        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: detail,
                backURL: login,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy
            ),
            .meetingsList
        )
        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: detail,
                backURL: external,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy
            ),
            .meetingsList
        )
    }

    func testMeetingDetailBackPreservesSafeMeetingHistoryAndListBackDisablesWithoutHistory() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let detail = configuration.meetingDetailURL(meetingId: "meeting-033")

        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: detail,
                backURL: configuration.meetingsURL(),
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy
            ),
            .history
        )
        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: configuration.meetingsURL(),
                backURL: nil,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy
            ),
            .unavailable
        )
    }

    func testHistorySelectionSkipsCurrentDuplicatesForBackAndForward() throws {
        struct HistoryCandidate {
            let id: String
            let url: URL
        }

        let current = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/settings/integrations/calendar"))
        let previous = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/settings/recording"))
        let next = try XCTUnwrap(URL(string: "https://rec.2brain.dev/billing"))
        let external = try XCTUnwrap(URL(string: "https://accounts.example/login"))
        let candidates = [
            HistoryCandidate(id: "current-duplicate", url: current),
            HistoryCandidate(id: "unsafe", url: external)
        ]
        let allowedURLs: Set<URL> = [previous, next]

        let backTarget = EmbeddedCabinetNavigationPolicy.nearestDistinctHistoryItem(
            currentURL: current,
            candidates: candidates + [HistoryCandidate(id: "previous", url: previous)],
            url: { $0.url },
            isAllowed: allowedURLs.contains
        )
        XCTAssertEqual(backTarget?.id, "previous")

        let forwardTarget = EmbeddedCabinetNavigationPolicy.nearestDistinctHistoryItem(
            currentURL: current,
            candidates: candidates + [HistoryCandidate(id: "next", url: next)],
            url: { $0.url },
            isAllowed: allowedURLs.contains
        )
        XCTAssertEqual(forwardTarget?.id, "next")

        XCTAssertNil(
            EmbeddedCabinetNavigationPolicy.nearestDistinctHistoryItem(
                currentURL: current,
                candidates: candidates,
                url: { $0.url },
                isAllowed: allowedURLs.contains
            )
        )
    }

    func testExpiredSessionBackCannotRestoreProtectedCabinetDocument() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        let detail = configuration.meetingDetailURL(meetingId: "meeting-033")

        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: login,
                backURL: detail,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy,
                sessionExpired: true
            ),
            .unavailable
        )
    }

    func testOnlySafeGetDocumentsCanEnterNativeHistory() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let list = configuration.meetingsURL()
        var getRequest = URLRequest(url: list)
        getRequest.httpMethod = "GET"
        var postRequest = URLRequest(url: list)
        postRequest.httpMethod = "POST"

        XCTAssertTrue(EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(getRequest, routePolicy: policy))
        XCTAssertFalse(EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(postRequest, routePolicy: policy))
    }

    func testAuthCallbackCannotEnterNativeHistoryOrBackStack() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let callback = try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/auth/callback/yandex?code=one-time-code"))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        var callbackRequest = URLRequest(url: callback)
        callbackRequest.httpMethod = "GET"

        XCTAssertFalse(EmbeddedCabinetNavigationPolicy.isSafeDocument(callback, routePolicy: policy))
        XCTAssertFalse(EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(callbackRequest, routePolicy: policy))
        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: login,
                backURL: callback,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy,
                sessionExpired: true
            ),
            .unavailable
        )
    }

    func testOnlyRootAuthDocumentsCanEnterHistoryAndSwiftUIRecovery() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        for (path, isStable) in [
            ("/login", true),
            ("/login/?next=%2Fdesktop%2Fmeetings", true),
            ("/sign-up", true),
            ("/sign-up/?next=%2Fdesktop%2Fmeetings", true),
            ("/login/vk/start", false),
            ("/login/yandex/start/?next=%2Fdesktop%2Fmeetings", false),
            ("/sign-up/vk/start", false),
            ("/sign-up/yandex/start", false),
            ("/login/email/start", false),
            ("/login/email/verify", false),
            ("/sign-up/email/start", false),
            ("/sign-up/email/verify", false)
        ] {
            let url = try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
            let decision = policy.decision(for: url)
            // These actions remain available to the live WebKit navigation.
            XCTAssertEqual(decision.decision, .allow, path)
            XCTAssertEqual(EmbeddedCabinetNavigationPolicy.isSafeDocument(url, routePolicy: policy), isStable, path)
            let request = URLRequest(url: url)
            XCTAssertEqual(EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(request, routePolicy: policy), isStable, path)
            XCTAssertEqual(EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(for: decision.route.kind, url: url), isStable, path)
            XCTAssertEqual(EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(for: decision.route.kind, request: request), isStable, path)
            XCTAssertEqual(
                EmbeddedCabinetNavigationPolicy.backDecision(
                    currentURL: configuration.baseURL.appendingPathComponent("login"),
                    backURL: url,
                    fallbackURL: configuration.meetingsURL(),
                    routePolicy: policy
                ),
                isStable ? .history : .unavailable,
                path
            )
            var post = request
            post.httpMethod = "POST"
            XCTAssertFalse(EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(post, routePolicy: policy), path)
            XCTAssertFalse(EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(for: decision.route.kind, request: post), path)
        }
    }

    func testEmailFormResponsesDoNotBecomeSwiftUIOwnedGetRoutes() throws {
        for path in [
            "/login/email/start",
            "/login/email/verify",
            "/sign-up/email/start",
            "/sign-up/email/verify",
            "/desktop/settings/account/email-link/start",
            "/desktop/settings/account/email-link/verify"
        ] {
            XCTAssertFalse(
                EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(
                    for: .authLogin,
                    url: try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
                ),
                path
            )
        }

        let settings = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/settings/account"))
        var postRequest = URLRequest(url: settings)
        postRequest.httpMethod = "POST"
        XCTAssertFalse(
            EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(
                for: .settings,
                request: postRequest
            )
        )
        XCTAssertTrue(
            EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(
                for: .settings,
                request: URLRequest(url: settings)
            )
        )
        XCTAssertTrue(
            EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(
                for: .authLogin,
                url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/login"))
            )
        )
        XCTAssertTrue(
            EmbeddedCabinetWebView.shouldTrackSwiftUIRequestIdentity(
                for: .meetingList,
                url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings"))
            )
        )
    }

    func testNativeNavigationControlsExposeStableAccessibilityIdentifiers() {
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.navigationBack, "desktop-cabinet-navigation-back")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.navigationForward, "desktop-cabinet-navigation-forward")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.navigationReload, "desktop-cabinet-navigation-reload")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.navigationHome, "desktop-cabinet-navigation-home")
    }

    func testNativeNavigationHintsShowHumanReadableShortcutCombinations() throws {
        XCTAssertEqual(DesktopCabinetNavigationShortcut.hint(for: KeyEquivalent("0")), "⌘0")
        XCTAssertEqual(DesktopCabinetNavigationShortcut.hint(for: KeyEquivalent("[")), "⌘[")
        XCTAssertEqual(DesktopCabinetNavigationShortcut.hint(for: KeyEquivalent("]")), "⌘]")
        XCTAssertEqual(DesktopCabinetNavigationShortcut.hint(for: KeyEquivalent("r")), "⌘R")
        XCTAssertFalse(DesktopCabinetNavigationShortcut.hint(for: KeyEquivalent("r")).contains("KeyEquivalent"))

        let source = try String(
            contentsOf: Self.repositoryRoot().appendingPathComponent(
                "apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift"
            ),
            encoding: .utf8
        )
        XCTAssertFalse(source.contains("String(describing: shortcut)"), "No service text in user-facing hints")
    }

    func testSharedNavigationContractCoversEveryCabinetSection() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let paths = [
            "/desktop/meetings",
            "/desktop/settings",
            "/desktop/settings/recording",
            "/desktop/settings/summaries",
            "/desktop/settings/integrations/calendar",
            "/desktop/settings/workspace",
            "/desktop/settings/account",
            "/desktop/settings/notifications",
            "/billing"
        ]

        for path in paths {
            let url = try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
            XCTAssertTrue(EmbeddedCabinetNavigationPolicy.isSafeDocument(url, routePolicy: policy), path)
        }

        let identifiers = [
            DesktopCabinetAccessibilityIdentifier.navigationHome,
            DesktopCabinetAccessibilityIdentifier.navigationBack,
            DesktopCabinetAccessibilityIdentifier.navigationForward,
            DesktopCabinetAccessibilityIdentifier.navigationReload
        ]
        XCTAssertEqual(Set(identifiers).count, 4)
        XCTAssertTrue(identifiers.allSatisfy { $0.hasPrefix("desktop-cabinet-navigation-") })
    }

    @MainActor
    func testEmbeddedWebViewDoesNotReloadInitialRouteAfterInPageNavigation() throws {
        let initial = URLRequest(url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings")))
        let detail = URLRequest(url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033")))
        let lastLoadedInitialRoute = EmbeddedCabinetWebView.loadIdentity(for: initial)

        XCTAssertFalse(
            EmbeddedCabinetWebView.shouldLoad(
                request: initial,
                lastLoadedRequestIdentity: lastLoadedInitialRoute
            )
        )
        XCTAssertTrue(
            EmbeddedCabinetWebView.shouldLoad(
                request: detail,
                lastLoadedRequestIdentity: lastLoadedInitialRoute
            )
        )
        XCTAssertFalse(
            EmbeddedCabinetWebView.shouldLoad(
                request: detail,
                lastLoadedRequestIdentity: lastLoadedInitialRoute,
                requestIsAlreadyNavigating: true
            )
        )
    }

    func testEmbeddedWebViewTracksMainFrameRouteChangesForNativeNavigation() throws {
        let list = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings"))
        let detail = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033"))

        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: nil, loaded: list), list)
        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: list, loaded: detail), detail)
        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: detail, loaded: detail), detail)
    }

    func testSuccessfulLoginPageLoadDoesNotMarkCabinetReady() {
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .meetingList), .ready)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .meetingDetail), .ready)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .settings), .ready)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .calendarSettings), .ready)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .billing), .ready)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authLogin), .expiredSession)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authSignup), .expiredSession)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authProvider), .expiredSession)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authCallback), .expiredSession)
    }

    func testExpiredSessionRecoveryUsesEmbeddedLoginForDesktopMeetings() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: ["X-Workspace-Id": "workspace-033"]
        ))

        let route = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(for: .expiredSession, configuration: configuration),
            .embedded(route)
        )
        let components = try XCTUnwrap(URLComponents(url: route, resolvingAgainstBaseURL: false))
        let query = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).compactMap { item in
            item.value.map { (item.name, $0) }
        })

        XCTAssertEqual(route.path, "/login")
        XCTAssertEqual(query["next"], "/desktop/meetings")
        XCTAssertEqual(query["workspace_id"], "workspace-033")
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(for: .offline, configuration: configuration),
            .embedded(configuration.meetingsURL())
        )
    }

    func testLocalUnavailableRecoveryUsesInAppLoginForAllUnauthenticatedStates() throws {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: "DesktopCabinetWorkspaceTests.local-profile"))
        defaults.removePersistentDomain(forName: "DesktopCabinetWorkspaceTests.local-profile")
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration.configured(
            from: [
                DesktopCabinetConfiguration.localAppEnvironmentKey: "1",
                DesktopCabinetConfiguration.requireExplicitBaseURLEnvironmentKey: "1",
                DesktopCabinetConfiguration.baseURLEnvironmentKey: "http://127.0.0.1:8081"
            ],
            defaults: defaults
        ))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)

        for state in [DesktopCabinetState.offline, .timeout, .expiredSession, .malformedResponse] {
            XCTAssertEqual(
                DesktopCabinetWorkspace.recoveryTarget(
                    for: state,
                    currentRoute: configuration.meetingsURL(),
                    initialRoute: nil,
                    configuration: configuration
                ),
                .embedded(login),
                "state=\(state)"
            )
            XCTAssertTrue(
                DesktopCabinetWorkspace.shouldUseLocalLoginRecovery(for: state, configuration: configuration),
                "state=\(state)"
            )
        }

        XCTAssertFalse(
            DesktopCabinetWorkspace.shouldUseLocalLoginRecovery(
                for: .accessDenied,
                configuration: configuration
            )
        )
    }

    func testRecoveryKeepsLastDocumentRouteAfterResourceFailure() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let detail = configuration.meetingDetailURL(meetingId: "meeting-033")
        let artifact = try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/cabinet/meetings/meeting-033/downloads/audio"))

        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .blockedRoute,
                currentRoute: detail,
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(detail)
        )
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .blockedRoute,
                currentRoute: artifact,
                initialRoute: detail,
                configuration: configuration
            ),
            .embedded(detail)
        )
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .accessDenied,
                currentRoute: detail,
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(configuration.meetingsURL())
        )
    }

    func testRecoveryKeepsTheBillingRouteSoPaymentStateStaysVisible() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let checkoutReturn = try XCTUnwrap(URL(string: "https://rec.2brain.dev/billing/checkout/return"))
        let billing = try XCTUnwrap(URL(string: "https://rec.2brain.dev/billing"))

        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .blockedRoute,
                currentRoute: checkoutReturn,
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(checkoutReturn)
        )
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .offline,
                currentRoute: billing,
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(billing)
        )
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .blockedRoute,
                currentRoute: try XCTUnwrap(URL(string: "https://yookassa.ru/checkout/abc")),
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(configuration.meetingsURL()),
            "A provider page must never become the recovered cabinet document"
        )
        XCTAssertEqual(
            EmbeddedCabinetWebView.finishedState(for: .billing),
            .ready,
            "The cabinet reports the current subscription state after payment"
        )
    }

    func testRecoveryKeepsCalendarSettingsRouteAcrossAuthAndBlockedStates() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let settings = configuration.calendarSettingsURL()

        guard case let .embedded(login)? = DesktopCabinetWorkspace.recoveryTarget(
            for: .expiredSession,
            currentRoute: settings,
            initialRoute: nil,
            configuration: configuration
        ) else {
            return XCTFail("Expected embedded login recovery")
        }
        let loginComponents = try XCTUnwrap(URLComponents(url: login, resolvingAgainstBaseURL: false))
        XCTAssertEqual(
            loginComponents.queryItems?.first(where: { $0.name == "next" })?.value,
            settings.path
        )
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .blockedRoute,
                currentRoute: settings,
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(settings)
        )
    }

    func testExpiredSessionKeepsEmbeddedLoginSurfaceVisible() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        let provider = try XCTUnwrap(URL(string: "https://oauth.yandex.ru/authorize?state=state"))
        let futureProvider = try XCTUnwrap(URL(string: "https://id.future-provider.example/authorize?state=state"))
        let callback = try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/auth/callback/yandex?state=state&code=code"))

        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: provider,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: futureProvider,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: callback,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertFalse(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: configuration.meetingsURL(),
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertFalse(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .offline,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
    }

    func testUnavailableWorkspaceStatesStayNativeAndExposeOnlySafeRecoveryActions() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let unavailableStates: [DesktopCabinetState] = [
            .notConfigured,
            .offline,
            .timeout,
            .accessDenied,
            .notFound,
            .malformedResponse,
            .blockedRoute
        ]

        for state in unavailableStates {
            XCTAssertFalse(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
                for: state,
                currentRoute: configuration.meetingsURL(),
                initialRoute: nil,
                configuration: configuration
            ), "\(state)")
            if [.offline, .timeout, .malformedResponse, .accessDenied, .notFound, .blockedRoute].contains(state) {
                XCTAssertEqual(
                    DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration),
                    .embedded(configuration.meetingsURL()),
                    "\(state)"
                )
                if [.offline, .timeout, .malformedResponse].contains(state) {
                    XCTAssertEqual(state.recoveryActionTitle, "Повторить", "\(state)")
                    XCTAssertEqual(state.recoverySystemImage, "arrow.clockwise", "\(state)")
                } else {
                    XCTAssertEqual(state.recoveryActionTitle, "К списку встреч", "\(state)")
                    XCTAssertEqual(state.recoverySystemImage, "arrow.left", "\(state)")
                }
            } else {
                XCTAssertNil(DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration), "\(state)")
                XCTAssertNil(state.recoveryActionTitle, "\(state)")
            }
            XCTAssertNotEqual(
                DesktopMeetingShellCabinetStatusPresentation.resolved(
                    cabinetConfigured: true,
                    cabinetState: state
                ).tileTitle,
                "Сервер доступен",
                "\(state)"
            )
        }
    }

    func testExpiredSessionCanShowOnlyAuthRecoveryInsideEmbeddedSurface() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: ["X-Workspace-Id": "workspace-033"]
        ))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)

        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(for: .expiredSession, configuration: configuration),
            .embedded(login)
        )
        XCTAssertNotEqual(
            DesktopMeetingShellCabinetStatusPresentation.resolved(
                cabinetConfigured: true,
                cabinetState: .expiredSession
            ).tileTitle,
            "Сервер доступен"
        )
    }

    func testShellInvariantKeepsStopReachableDuringActiveRecordingForEveryCabinetState() {
        for state in DesktopCabinetState.allCases {
            let invariant = NativeShellInvariant(
                recordVisible: true,
                stopVisible: true,
                uploadTruthVisible: true,
                focusCanReachStop: true,
                embeddedSurfaceLoaded: state == .ready
            )

            XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: state), "\(state)")
        }
    }

    func testActiveRecordingInvariantFailsWhenStopIsHiddenOrFocusTrapped() {
        let hiddenRecord = NativeShellInvariant(
            recordVisible: false,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true
        )
        let hiddenStop = NativeShellInvariant(
            recordVisible: true,
            stopVisible: false,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true
        )
        let focusTrap = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: false,
            embeddedSurfaceLoaded: true
        )

        XCTAssertFalse(hiddenRecord.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertFalse(hiddenStop.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertFalse(focusTrap.satisfiesActiveRecordingSafety(cabinetState: .ready))
    }

    func testNativeAndEmbeddedRegionsHaveStableAccessibilityBoundaries() {
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.captureRegion, "desktop-native-capture-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.uploadTruthRegion, "desktop-native-upload-truth-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.nativeShellRegion, "desktop-native-shell-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.embeddedSurface, "desktop-cabinet-embedded-surface")
    }

    func testWorkspaceZoomDoesNotScaleNativeShellControls() {
        let safe = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true,
            workspaceZoomApplied: WorkspaceZoomPreference(value: 1.3),
            nativeShellScaledByWorkspaceZoom: false
        )
        let unsafe = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true,
            workspaceZoomApplied: WorkspaceZoomPreference(value: 1.3),
            nativeShellScaledByWorkspaceZoom: true
        )

        XCTAssertTrue(safe.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertFalse(unsafe.satisfiesActiveRecordingSafety(cabinetState: .ready))
    }

    func testUnavailableStatesHaveBoundedMessages() {
        let states: [DesktopCabinetState] = [.notConfigured, .offline, .timeout, .expiredSession, .accessDenied, .notFound, .malformedResponse, .blockedRoute]

        for state in states {
            XCTAssertFalse(state.unavailableTitle.isEmpty, "\(state)")
            XCTAssertFalse(state.unavailableSystemImage.isEmpty, "\(state)")
            XCTAssertFalse(state.userMessage.isEmpty, "\(state)")
            XCTAssertLessThanOrEqual(state.userMessage.count, 180, "\(state)")
            XCTAssertFalse(state.userMessage.contains("/Users/"), "\(state)")
        }
    }

    func testMissingOwnerSessionHasLoginRecoveryAction() {
        XCTAssertEqual(DesktopCabinetState.expiredSession.unavailableTitle, "Нужно войти")
        XCTAssertEqual(DesktopCabinetState.expiredSession.recoveryActionTitle, "Войти в кабинет")
        XCTAssertEqual(DesktopCabinetState.expiredSession.recoverySystemImage, "person.crop.circle")
        XCTAssertTrue(DesktopCabinetState.expiredSession.unavailableSystemImage.contains("person"))
        XCTAssertFalse(DesktopCabinetState.expiredSession.shouldShowEmbeddedSurface)
    }

    func test052ExpiredOwnerSessionKeepsNativeShellTruthVisible() {
        let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .expiredSession
        )
        let invariant = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: false
        )

        XCTAssertEqual(presentation.tileTitle, "Нужен вход")
        XCTAssertEqual(presentation.tileDetail, "Откройте кабинет заново")
        XCTAssertEqual(presentation.tone, .warning)
        XCTAssertFalse(DesktopCabinetState.expiredSession.shouldShowEmbeddedSurface)
        XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: .expiredSession))
    }

    func testDeniedStateOffersSafeReturnWithoutPretendingToGrantAccess() {
        XCTAssertEqual(DesktopCabinetState.accessDenied.unavailableTitle, "Нет доступа к встречам")
        XCTAssertEqual(DesktopCabinetState.accessDenied.recoveryActionTitle, "К списку встреч")
        XCTAssertEqual(DesktopCabinetState.accessDenied.recoverySystemImage, "arrow.left")
        XCTAssertFalse(DesktopCabinetState.accessDenied.shouldShowEmbeddedSurface)
    }

    func testBlockedAndMissingRoutesOfferReturnToMeetings() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))

        for state in [DesktopCabinetState.blockedRoute, .notFound] {
            XCTAssertEqual(state.recoveryActionTitle, "К списку встреч", "\(state)")
            XCTAssertEqual(state.recoverySystemImage, "arrow.left", "\(state)")
            XCTAssertEqual(
                DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration),
                .embedded(configuration.meetingsURL()),
                "\(state)"
            )
        }
    }

    func testDeniedAndNotFoundStatesDoNotConfirmMeetingExistence() {
        for state in [DesktopCabinetState.accessDenied, .notFound] {
            XCTAssertFalse(state.userMessage.localizedCaseInsensitiveContains("this meeting"), "\(state)")
            XCTAssertFalse(state.userMessage.localizedCaseInsensitiveContains("meeting exists"), "\(state)")
            XCTAssertTrue(
                state.userMessage.localizedCaseInsensitiveContains("доступ") ||
                    state.userMessage.localizedCaseInsensitiveContains("недоступна"),
                "\(state)"
            )
        }
    }

    func testProductWorkspaceLayoutKeepsMeetingsBeforeDiagnostics() {
        let order = DesktopCabinetLayoutPolicy.defaultSectionOrder

        XCTAssertEqual(order.first, .meetings)
        XCTAssertTrue(order.contains(.capture))
        XCTAssertTrue(order.contains(.localAudioReadiness))
        XCTAssertLessThan(
            try XCTUnwrap(order.firstIndex(of: .meetings)),
            try XCTUnwrap(order.firstIndex(of: .localAudioReadiness))
        )
    }

    func testInstalledRuntimeEvidenceUsesApplicationsBundlePath() {
        let acceptedRuntimePath = "/Applications/GRAF.app"

        XCTAssertEqual(acceptedRuntimePath, "/Applications/GRAF.app")
        XCTAssertFalse(acceptedRuntimePath.hasPrefix("/Users/"))
        XCTAssertTrue(acceptedRuntimePath.hasSuffix("GRAF.app"))
    }

    func testConfiguredCabinetDoesNotShowHealthyShellStatusBeforeRuntimeProof() {
        let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .loading
        )

        XCTAssertEqual(presentation.tileTitle, "Проверяем сервер")
        XCTAssertEqual(presentation.systemImage, "clock")
        XCTAssertEqual(presentation.tone, .neutral)
        XCTAssertFalse(presentation.tileTitle.localizedCaseInsensitiveContains("задан"))
        XCTAssertNotEqual(presentation.systemImage, "checkmark.circle")
    }

    func testShellShowsServerUnavailableWhenCabinetNavigationFails() {
        for state in [DesktopCabinetState.offline, .timeout] {
            let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
                cabinetConfigured: true,
                cabinetState: state
            )

            XCTAssertEqual(presentation.tileTitle, "Сервер недоступен", "\(state)")
            XCTAssertEqual(presentation.tileDetail, "Записи остаются на этом Mac", "\(state)")
            XCTAssertEqual(presentation.systemImage, "wifi.slash", "\(state)")
            XCTAssertEqual(presentation.tone, .error, "\(state)")
        }
    }

    func testShellShowsSuccessOnlyAfterCabinetReadyState() {
        let ready = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .ready
        )
        let expired = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .expiredSession
        )

        XCTAssertEqual(ready.tileTitle, "Сервер доступен")
        XCTAssertEqual(ready.systemImage, "checkmark.circle")
        XCTAssertEqual(ready.tone, .success)
        XCTAssertEqual(expired.tileTitle, "Нужен вход")
        XCTAssertEqual(expired.systemImage, "person.crop.circle.badge.exclamationmark")
        XCTAssertEqual(expired.tone, .warning)
    }

    func testShellNeverCarriesCachedReadyAcrossAuthOrServerFailureStates() {
        let nonReadyStates: [DesktopCabinetState] = [
            .loading,
            .offline,
            .timeout,
            .expiredSession,
            .accessDenied,
            .notFound,
            .malformedResponse,
            .blockedRoute,
        ]

        for state in nonReadyStates {
            let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
                cabinetConfigured: true,
                cabinetState: state
            )

            XCTAssertNotEqual(presentation.tileTitle, "Сервер доступен", "\(state)")
            XCTAssertNotEqual(presentation.systemImage, "checkmark.circle", "\(state)")
            XCTAssertNotEqual(presentation.tone, .success, "\(state)")
        }
    }

    func testHTTPStatusMappingPreventsFalseGreenCabinetState() {
        XCTAssertNil(DesktopCabinetState.state(forHTTPStatus: 200))
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 401), .expiredSession)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 403), .accessDenied)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 404), .notFound)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 504), .timeout)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 503), .offline)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 429), .malformedResponse)
    }

    func testRevokedEmbeddedWorkspaceRequiresExplicitReauthenticationAndReselection() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let response = try XCTUnwrap(HTTPURLResponse(
            url: configuration.meetingsURL(),
            statusCode: 403,
            httpVersion: nil,
            headerFields: ["X-GRAF-Cabinet-Recovery": "reselect-space"]
        ))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)

        XCTAssertEqual(DesktopCabinetState.state(forHTTPResponse: response), .workspaceReselectionRequired)
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(for: .workspaceReselectionRequired, configuration: configuration),
            .embedded(login)
        )
        XCTAssertEqual(DesktopCabinetState.workspaceReselectionRequired.recoveryActionTitle, "Войти и выбрать пространство")
        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .workspaceReselectionRequired,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertFalse(DesktopCabinetState.workspaceReselectionRequired.shouldShowEmbeddedSurface)
    }

    func testOwnerReviewDetailRouteUsesServerOwnedDesktopCabinetOnlyWhenReady() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let route = DesktopCabinetWorkspace.detailRoute(meetingId: "meeting-051", configuration: configuration)
        let loading = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .loading
        )
        let ready = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .ready
        )

        XCTAssertEqual(route.path, "/desktop/meetings/meeting-051")
        XCTAssertNil(route.fragment)
        XCTAssertNotEqual(loading.tileTitle, "Сервер доступен")
        XCTAssertEqual(ready.tileTitle, "Сервер доступен")
        XCTAssertEqual(ready.systemImage, "checkmark.circle")
    }

    func testUnavailableStatesUseHumanCopyAndKeepNativeRecordingIndependent() {
        let unavailableStates: [DesktopCabinetState] = [
            .notConfigured,
            .offline,
            .timeout,
            .expiredSession,
            .accessDenied,
            .notFound,
            .malformedResponse,
            .blockedRoute
        ]

        for state in unavailableStates {
            let message = state.userMessage
            let invariant = NativeShellInvariant(
                recordVisible: true,
                stopVisible: true,
                uploadTruthVisible: true,
                focusCanReachStop: true,
                embeddedSurfaceLoaded: false
            )

            XCTAssertFalse(message.localizedCaseInsensitiveContains("сервером rec"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("пароли календаря"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("token"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("password"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("app password"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("refresh"), "\(state)")
            XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: state), "\(state)")
        }

        for state in [DesktopCabinetState.notConfigured, .offline, .timeout, .expiredSession, .malformedResponse] {
            XCTAssertTrue(state.userMessage.contains("Запись на этом Mac остается доступна"), "\(state)")
        }
    }

    func testCalendarSettingsExpiredSessionRecoveryReturnsToEmbeddedSettings() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: ["X-Workspace-Id": "workspace-063"]
        ))
        let target = DesktopCabinetWorkspace.calendarSettingsRecoveryTarget(
            for: .expiredSession,
            configuration: configuration
        )
        guard case let .embedded(route)? = target else {
            XCTFail("Expected embedded calendar settings login recovery target")
            return
        }
        let components = try XCTUnwrap(URLComponents(url: route, resolvingAgainstBaseURL: false))
        let query = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).compactMap { item in
            item.value.map { (item.name, $0) }
        })

        XCTAssertEqual(route.path, "/login")
        XCTAssertEqual(query["next"], "/desktop/settings/integrations/calendar")
        XCTAssertEqual(query["workspace_id"], "workspace-063")
        XCTAssertEqual(
            DesktopCabinetWorkspace.calendarSettingsRecoveryTarget(
                for: .offline,
                configuration: configuration
            ),
            .embedded(configuration.calendarSettingsURL())
        )
    }

    func testLocalRecordingLifecycleStaysUsableBeforeServerIdentityExists() {
        let localOnly = DesktopUploadCustodyProjection(
            item: custodyFixtureQueueItem(id: "local-only", state: .queued)
        )
        let uploading = DesktopUploadCustodyProjection(
            item: custodyFixtureQueueItem(id: "uploading", state: .uploading)
        )

        XCTAssertEqual(localOnly.custodyState, .serverUnknownLocalSaved)
        XCTAssertEqual(localOnly.uploadState, .notStarted)
        XCTAssertNil(localOnly.serverMeetingId)
        XCTAssertFalse(localOnly.reviewAvailable)
        XCTAssertEqual(uploading.custodyState, .partialUploaded)
        XCTAssertEqual(uploading.uploadState, .partialUploaded)
        XCTAssertNil(uploading.serverMeetingId)
        XCTAssertFalse(uploading.reviewAvailable)
    }

    func testServerProcessingAndReadyLifecycleDoNotOverwriteLocalCustodyTruth() {
        let processing = DesktopUploadCustodyProjection(
            item: custodyFixtureQueueItem(
                id: "server-processing",
                state: .uploaded,
                serverTruth: ServerTruthFingerprint(
                    meetingId: "meeting-processing",
                    mediaRevisionId: "revision-processing",
                    processingStatus: "pending_processing",
                    finalizedAt: Date(timeIntervalSince1970: 200)
                )
            )
        )
        let ready = DesktopUploadCustodyProjection(
            item: custodyFixtureQueueItem(
                id: "server-ready",
                state: .uploaded,
                serverTruth: ServerTruthFingerprint(
                    meetingId: "meeting-ready",
                    mediaRevisionId: "revision-ready",
                    processingStatus: "processed",
                    finalizedAt: Date(timeIntervalSince1970: 200)
                )
            )
        )

        XCTAssertEqual(processing.custodyState, .processing)
        XCTAssertEqual(processing.uploadState, .finalized)
        XCTAssertFalse(processing.reviewAvailable)
        XCTAssertEqual(ready.custodyState, .delivered)
        XCTAssertEqual(ready.uploadState, .finalized)
        XCTAssertTrue(ready.reviewAvailable)
        XCTAssertEqual(ready.normalUserAction, .openReview)
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let marker = candidate.appendingPathComponent("apps/macos/Package.swift")
            if FileManager.default.fileExists(atPath: marker.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "DesktopCabinetWorkspaceTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
@MainActor
private final class CommittedNavigationProbe: NSObject, @preconcurrency WKNavigationDelegate {
    let coordinator: EmbeddedCabinetWebView.Coordinator
    let committed: XCTestExpectation
    var finishCount = 0
    init(coordinator: EmbeddedCabinetWebView.Coordinator, committed: XCTestExpectation) {
        self.coordinator = coordinator; self.committed = committed
    }
    override func responds(to selector: Selector!) -> Bool {
        super.responds(to: selector) || coordinator.responds(to: selector)
    }
    override func forwardingTarget(for selector: Selector!) -> Any? { coordinator }
    func webView(_ webView: WKWebView, didCommit navigation: WKNavigation!) {
        coordinator.webView(webView, didCommit: navigation)
        committed.fulfill()
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        finishCount += 1
        coordinator.webView(webView, didFinish: navigation)
    }
}

@MainActor
private final class HistoryPolicyProbe: NSObject, @preconcurrency WKNavigationDelegate {
    let coordinator: EmbeddedCabinetWebView.Coordinator
    let decision: XCTestExpectation
    var policy: WKNavigationActionPolicy?
    var method: String?
    init(coordinator: EmbeddedCabinetWebView.Coordinator, decision: XCTestExpectation) {
        self.coordinator = coordinator; self.decision = decision
    }
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping EmbeddedCabinetNavigationDecisionHandler) {
        coordinator.webView(webView, decidePolicyFor: navigationAction) { policy in
            self.method = navigationAction.request.httpMethod
            self.policy = policy
            decisionHandler(policy)
            self.decision.fulfill()
        }
    }
}

private final class SessionBoundaryRequests: @unchecked Sendable {
    private let lock = NSLock()
    private var counts: [String: Int] = [:]
    private var heldConnection: NWConnection?
    func record(_ key: String) -> Int {
        lock.withLock { counts[key, default: 0] += 1; return counts[key]! }
    }
    func count(_ key: String) -> Int { lock.withLock { counts[key, default: 0] } }
    func hold(_ connection: NWConnection) { lock.withLock { heldConnection = connection } }
    func cancelHeldConnection() {
        lock.withLock { heldConnection?.cancel(); heldConnection = nil }
    }
    func attemptHeldRedirect() {
        let connection = lock.withLock { let value = heldConnection; heldConnection = nil; return value }
        guard let connection else { XCTFail("Missing first provisional form"); return }
        let response = "HTTP/1.1 303 See Other\r\nLocation: /login\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
        connection.send(content: Data(response.utf8), completion: .contentProcessed { error in
            // A send attempt cannot establish that the cancelled WebKit load
            // received this response. Record that limit instead of claiming it.
            print("F136_NATIVE_OVERLAP old_response_send=\(error == nil ? "written" : "failed")")
            connection.cancel()
        })
    }
}

@MainActor
private final class SessionBoundaryDocument: ObservableObject {
    @Published var state: DesktopCabinetState
    @Published var route: URL?
    init(state: DesktopCabinetState) { self.state = state }
}

@MainActor
private struct RealWorkspaceFixture: View {
    let configuration: DesktopCabinetConfiguration
    let initialRoute: URL
    @ObservedObject var document: SessionBoundaryDocument
    let presenter: DesktopNotificationPresenter
    var body: some View {
        DesktopCabinetWorkspaceView(configuration: configuration, initialRoute: initialRoute,
            currentRoute: $document.route, cabinetState: $document.state, presentation: .shell,
            notificationPresenter: presenter)
    }
}

@MainActor
private struct SessionBoundaryFixture: View {
    let request: URLRequest
    let origin: URL
    @ObservedObject var controller: EmbeddedCabinetNavigationController
    @ObservedObject var document: SessionBoundaryDocument
    let presenter: DesktopNotificationPresenter
    var body: some View {
        EmbeddedCabinetWebView(request: URLRequest(url: document.route ?? request.url!),
            routePolicy: DesktopCabinetRoutePolicy(baseURL: origin), cabinetState: $document.state,
            currentRoute: $document.route, fallbackRequest: URLRequest(url: origin.appendingPathComponent("desktop/meetings")),
            notificationPresenter: presenter, navigationController: controller)
            .id(controller.sessionBoundaryID)
    }
}

#endif
