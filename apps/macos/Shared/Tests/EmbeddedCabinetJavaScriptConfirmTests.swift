import AppKit
import Network
import SwiftUI
import WebKit
import XCTest
@testable import TwoBrainRecAppCore

@MainActor
final class EmbeddedCabinetJavaScriptConfirmTests: XCTestCase {
    private let origin = URL(string: "https://cabinet.graf.test")!
    private static var retainedWebViews: [WKWebView] = []

    func testConfirmationTrustBoundary() {
        let policy = DesktopCabinetRoutePolicy(baseURL: origin)
        let account = origin.appendingPathComponent("desktop/settings/account")
        for path in ["desktop/meetings", "desktop/settings/summaries", "desktop/settings/account", "billing/usage"] {
            let url = origin.appendingPathComponent(path)
            XCTAssertTrue(EmbeddedCabinetWebView.allowsJavaScriptConfirm(
                webViewURL: url, frameURL: url, frameIsMainFrame: true, routePolicy: policy
            ))
        }
        for source in [
            nil, URL(string: "https://foreign.test/desktop/settings/account"),
            URL(string: "https://user@cabinet.graf.test/desktop/settings/account"),
            origin.appendingPathComponent("login"), origin.appendingPathComponent("unknown"),
            URL(string: "file:///desktop/settings/account"), URL(string: "about:blank")
        ] {
            XCTAssertFalse(EmbeddedCabinetWebView.allowsJavaScriptConfirm(
                webViewURL: account, frameURL: source, frameIsMainFrame: true, routePolicy: policy
            ))
            XCTAssertFalse(EmbeddedCabinetWebView.allowsJavaScriptConfirm(
                webViewURL: source, frameURL: account, frameIsMainFrame: true, routePolicy: policy
            ))
        }
        XCTAssertFalse(EmbeddedCabinetWebView.allowsJavaScriptConfirm(
            webViewURL: account, frameURL: account, frameIsMainFrame: false, routePolicy: policy
        ))
    }

    func testRealJavaScriptCancelAndKeyboardNeverRunProtectedAction() async throws {
        // An HTTP document supplies a real WKFrameInfo URL; loadHTMLString does not.
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        let listening = expectation(description: "loopback fixture ready")
        listener.stateUpdateHandler = { state in
            if case .ready = state { listening.fulfill() }
        }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .global())
            connection.receive(minimumIncompleteLength: 1, maximumLength: 4096) { _, _, _, _ in
                let html = "<!doctype html><title>Synthetic confirmation</title><p>GRAF test</p>"
                let response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: \(html.utf8.count)\r\nConnection: close\r\n\r\n\(html)"
                connection.send(content: Data(response.utf8), completion: .contentProcessed { _ in connection.cancel() })
            }
        }
        listener.start(queue: .global())
        defer { listener.cancel() }
        await fulfillment(of: [listening], timeout: 5)
        let port = try XCTUnwrap(listener.port)
        let localOrigin = try XCTUnwrap(URL(string: "http://127.0.0.1:\(port.rawValue)"))
        let (view, window, coordinator) = makeCabinet(realDocument: true, baseURL: localOrigin)
        defer {
            coordinator.detachNavigationController(from: view)
            view.navigationDelegate = nil
            view.uiDelegate = nil
            window.close()
        }
        view.navigationDelegate = coordinator
        view.uiDelegate = coordinator
        let documentURL = localOrigin.appendingPathComponent("desktop/settings/account")
        view.load(URLRequest(url: documentURL))
        for _ in 0..<100 {
            if !view.isLoading && view.url == documentURL { break }
            try await Task.sleep(for: .milliseconds(30))
        }
        XCTAssertEqual(view.url, documentURL)
        for key in ["\r", "\u{1b}"] {
            let replied = expectation(description: "real JavaScript completes after cancellation")
            view.evaluateJavaScript("window.protectedAction = false; if (confirm('Synthetic action')) window.protectedAction = true; window.protectedAction") { result, error in
                XCTAssertNil(error)
                XCTAssertEqual(result as? Bool, false)
                replied.fulfill()
            }
            for _ in 0..<100 {
                if coordinator.pendingConfirmation != nil { break }
                try await Task.sleep(for: .milliseconds(30))
            }
            let alert = try XCTUnwrap(coordinator.pendingConfirmation?.alert)
            try await Task.sleep(for: .milliseconds(400))
            let event = try XCTUnwrap(NSEvent.keyEvent(
                with: .keyDown, location: .zero, modifierFlags: [], timestamp: 0,
                windowNumber: alert.window.windowNumber, context: nil,
                characters: key, charactersIgnoringModifiers: key, isARepeat: false,
                keyCode: key == "\r" ? 36 : 53
            ))
            if key == "\r" {
                XCTAssertTrue(alert.window.performKeyEquivalent(with: event))
            } else {
                NSApp.sendEvent(event)
            }
            await fulfillment(of: [replied], timeout: 3)
            XCTAssertNil(coordinator.pendingConfirmation, "key=\(key.debugDescription)")
        }
    }

    func testNativeButtonsCancelByDefaultAndContinueExplicitly() async throws {
        let (view, window, coordinator) = makeCabinet()
        defer { coordinator.detachNavigationController(from: view); window.close() }
        for (index, expected) in [(0, false), (1, true)] {
            let replied = expectation(description: "native button reply")
            request(coordinator, view: view) { answer in
                XCTAssertEqual(answer, expected)
                replied.fulfill()
            }
            let alert = try XCTUnwrap(coordinator.pendingConfirmation?.alert)
            XCTAssertTrue(alert.window.defaultButtonCell === alert.buttons[0].cell)
            XCTAssertEqual(alert.buttons[0].keyEquivalent, "\r")
            XCTAssertEqual(alert.buttons[1].keyEquivalent, "")
            alert.buttons[index].performClick(nil)
            await fulfillment(of: [replied], timeout: 3)
            XCTAssertNil(coordinator.pendingConfirmation)
        }
    }

    func testDuplicateAndLateCompletionCannotResolveNewRequest() async throws {
        let (view, window, coordinator) = makeCabinet()
        defer { coordinator.detachNavigationController(from: view); window.close() }
        var replies: [Bool] = []
        request(coordinator, view: view) { replies.append($0) }
        let first = try XCTUnwrap(coordinator.pendingConfirmation?.id)
        request(coordinator, view: view) { replies.append($0) }
        XCTAssertEqual(replies, [false])
        XCTAssertEqual(coordinator.pendingConfirmation?.id, first)
        coordinator.cancelJavaScriptConfirmation()
        XCTAssertEqual(replies, [false, false])
        // Let AppKit finish dismissing the old sheet before another request.
        try await Task.sleep(for: .milliseconds(100))
        request(coordinator, view: view) { replies.append($0) }
        let second = try XCTUnwrap(coordinator.pendingConfirmation?.id)
        coordinator.finishJavaScriptConfirmation(id: first, confirmed: true)
        XCTAssertEqual(coordinator.pendingConfirmation?.id, second)
        XCTAssertEqual(replies, [false, false])
        coordinator.cancelJavaScriptConfirmation()
        coordinator.cancelJavaScriptConfirmation()
        XCTAssertEqual(replies, [false, false, false])
    }

    func testUnavailableWindowsAndSubframesCancel() {
        let (view, window, coordinator) = makeCabinet()
        defer { coordinator.detachNavigationController(from: view); window.close() }
        var replies: [Bool] = []
        coordinator.requestJavaScriptConfirmation(
            in: view, message: "Synthetic", frameURL: view.url, frameIsMainFrame: false
        ) { replies.append($0) }
        let occupied = NSWindow(contentRect: .zero, styleMask: .titled, backing: .buffered, defer: false)
        window.beginSheet(occupied)
        request(coordinator, view: view) { replies.append($0) }
        window.endSheet(occupied)
        window.orderOut(nil)
        request(coordinator, view: view) { replies.append($0) }
        view.removeFromSuperview()
        request(coordinator, view: view) { replies.append($0) }
        XCTAssertEqual(replies, [false, false, false, false])
        XCTAssertNil(coordinator.pendingConfirmation)
    }

    func testLifecycleCancelsExactlyOnceAndProcessExitRejectsOldDocument() throws {
        for reason in ["navigation", "detach", "close", "process"] {
            let (view, window, coordinator) = makeCabinet()
            var replies: [Bool] = []
            request(coordinator, view: view) { replies.append($0) }
            let id = try XCTUnwrap(coordinator.pendingConfirmation?.id)
            switch reason {
            case "navigation":
                let navigation = view.loadHTMLString("<p>Synthetic navigation</p>", baseURL: view.url)
                coordinator.webView(view, didStartProvisionalNavigation: navigation)
            case "detach": coordinator.detachNavigationController(from: view)
            case "close": window.close()
            default: coordinator.webViewWebContentProcessDidTerminate(view)
            }
            coordinator.finishJavaScriptConfirmation(id: id, confirmed: true)
            XCTAssertEqual(replies, [false], reason)
            request(coordinator, view: view) { replies.append($0) }
            XCTAssertEqual(replies, [false, false], reason)
            coordinator.detachNavigationController(from: view)
            window.close()
        }
    }

    private func makeCabinet(realDocument: Bool = false, baseURL: URL? = nil) -> (WKWebView, NSWindow, EmbeddedCabinetWebView.Coordinator) {
        _ = NSApplication.shared
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = realDocument ? WKWebView(frame: .zero, configuration: configuration)
            : ConfirmationTestWebView(frame: .zero, configuration: configuration)
        let origin = baseURL ?? origin
        let documentURL = origin.appendingPathComponent("desktop/settings/account")
        (view as? ConfirmationTestWebView)?.documentURL = documentURL
        Self.retainedWebViews.append(view)
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 480),
                              styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = view
        window.orderFront(nil)
        let policy = DesktopCabinetRoutePolicy(baseURL: origin)
        let navigation = EmbeddedCabinetNavigationController()
        let request = URLRequest(url: documentURL)
        navigation.attach(webView: view, routePolicy: policy, fallbackRequest: request,
                          initialRequest: request, sessionExpired: false)
        let coordinator = EmbeddedCabinetWebView.Coordinator(
            routePolicy: policy, desktopHeaders: [:], cabinetState: .constant(.ready),
            currentRoute: .constant(view.url), navigationEventLogger: nil,
            showsAppUpdateBadge: false, onCheckForUpdates: {},
            onOpenMeetingDetectionSettings: {}, supportIncidentBridge: nil,
            navigationController: navigation
        )
        if !realDocument { coordinator.webView(view, didFinish: nil) }
        return (view, window, coordinator)
    }

    private func request(_ coordinator: EmbeddedCabinetWebView.Coordinator, view: WKWebView,
                         reply: @escaping (Bool) -> Void) {
        coordinator.requestJavaScriptConfirmation(
            in: view, message: "Синтетическое подтверждение", frameURL: view.url,
            frameIsMainFrame: true, completionHandler: reply
        )
    }
}

@MainActor
private final class ConfirmationTestWebView: WKWebView {
    var documentURL: URL?
    override var url: URL? { documentURL }
}
