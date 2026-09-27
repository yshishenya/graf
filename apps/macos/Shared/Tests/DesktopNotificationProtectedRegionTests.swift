import AppKit
import SwiftUI
import XCTest
@testable import TwoBrainRecAppCore

final class DesktopNotificationProtectedRegionTests: XCTestCase {
    @MainActor
    func testMarkerTracksOnlyVisibleOwnControlsAsTheWindowMoves() async throws {
        _ = NSApplication.shared
        let screen = try XCTUnwrap(NSScreen.main)
        let card = DesktopNotificationCardPresenter()
        let window = NSWindow(contentRect: NSRect(x: screen.visibleFrame.minX + 30,
            y: screen.visibleFrame.minY + 40, width: 160, height: 70),
            styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(rootView: DesktopNotificationProtectedRegion(card: card)
            .frame(width: 160, height: 70))
        defer { card.dismiss(); window.orderOut(nil) }
        window.orderFrontRegardless()
        window.contentView?.layoutSubtreeIfNeeded()
        await Task.yield()
        let initial = try XCTUnwrap(card.protectedFramesProvider().first)
        XCTAssertEqual(initial.width, 160, accuracy: 1)
        XCTAssertEqual(initial.height, 70, accuracy: 1)
        window.setFrameOrigin(NSPoint(x: window.frame.minX + 30, y: window.frame.minY + 20))
        let moved = try XCTUnwrap(card.protectedFramesProvider().first)
        XCTAssertEqual(moved.minX - initial.minX, 30, accuracy: 1)
        XCTAssertEqual(moved.minY - initial.minY, 20, accuracy: 1)
        window.orderOut(nil)
        XCTAssertTrue(card.protectedFramesProvider().isEmpty)
    }
}
