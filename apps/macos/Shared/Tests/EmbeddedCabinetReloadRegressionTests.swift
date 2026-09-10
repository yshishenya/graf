import AppKit
import Combine
import Foundation
import Network
import SwiftUI
@testable import TwoBrainRecAppCore
import WebKit
import XCTest

@MainActor
final class EmbeddedCabinetReloadRegressionTests: XCTestCase {
    func testControllerReloadReachesServerAfterButtonsBecomeDisabled() async throws {
        _ = NSApplication.shared
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        let ready = expectation(description: "synthetic server listening")
        let requests = expectation(description: "initial GET and explicit reload GET")
        requests.expectedFulfillmentCount = 2
        listener.stateUpdateHandler = { if case .ready = $0 { ready.fulfill() } }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .global())
            connection.receive(minimumIncompleteLength: 1, maximumLength: 16384) { data, _, _, _ in
                guard let data, let text = String(data: data, encoding: .utf8),
                      text.hasPrefix("GET /desktop/meetings ") else {
                    connection.cancel(); return
                }
                requests.fulfill()
                let html = "<!doctype html><title>Synthetic reload</title><p>Reload test</p>"
                let reply = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nCache-Control: private, no-store\r\nContent-Length: \(html.utf8.count)\r\nConnection: close\r\n\r\n\(html)"
                connection.send(content: Data(reply.utf8), completion: .contentProcessed { _ in connection.cancel() })
            }
        }
        listener.start(queue: .global())
        defer { listener.cancel() }
        await fulfillment(of: [ready], timeout: 5)
        let port = try XCTUnwrap(listener.port)
        let origin = try XCTUnwrap(URL(string: "http://127.0.0.1:\(port.rawValue)"))
        let request = URLRequest(url: origin.appendingPathComponent("desktop/meetings"))
        let controller = EmbeddedCabinetNavigationController()
        let view = EmbeddedCabinetWebView(request: request,
            routePolicy: DesktopCabinetRoutePolicy(baseURL: origin), cabinetState: .constant(.ready),
            fallbackRequest: request,
            notificationPresenter: DesktopNotificationPresenter(
                store: .init(defaults: UserDefaults(suiteName: UUID().uuidString)!),
                model: DesktopControlModel(), status: { .denied }), navigationController: controller)
        let host = NSHostingView(rootView: view)
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 480),
            styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = host
        host.layoutSubtreeIfNeeded()
        defer { window.close() }
        let deadline = Date().addingTimeInterval(10)
        while !controller.canReload && Date() < deadline {
            try await Task.sleep(for: .milliseconds(40))
        }
        XCTAssertTrue(controller.canReload, "Initial document must be fully loaded")
        controller.reload()
        XCTAssertFalse(controller.canReload, "Controls are disabled while the requested reload is pending")
        await fulfillment(of: [requests], timeout: 5)
    }
}
