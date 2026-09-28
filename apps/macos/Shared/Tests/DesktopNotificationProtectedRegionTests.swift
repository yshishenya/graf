import AppKit
import SwiftUI
import XCTest
@testable import TwoBrainRecAppCore

final class DesktopNotificationProtectedRegionTests: XCTestCase {
    @MainActor
    func testDetachedHierarchyAndItsPresenterAreReleased() async throws {
        try F277CardTestSupport.requireScreen()
        weak var releasedCard: DesktopNotificationCardPresenter?
        weak var releasedMarker: NSView?
        autoreleasepool {
            let card = DesktopNotificationCardPresenter()
            let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 160, height: 70),
                styleMask: [.borderless], backing: .buffered, defer: false)
            window.isReleasedWhenClosed = false
            let host = NSHostingView(rootView: AnyView(DesktopNotificationProtectedRegion(card: card)))
            window.contentView = host
            window.orderFrontRegardless()
            host.layoutSubtreeIfNeeded()
            releasedCard = card
            releasedMarker = F277CardTestSupport.descendants(host).first {
                String(describing: type(of: $0)) == "CaptureRegionMarker"
            }
            XCTAssertNotNil(releasedMarker)
            XCTAssertEqual(card.protectedFrames.count, 1)
            host.rootView = AnyView(EmptyView())
            host.layoutSubtreeIfNeeded()
            window.contentView = nil
            window.orderOut(nil)
            window.close()
        }
        await Task.yield()
        let released = try await F277CardTestSupport.awaitAppKitState {
            releasedCard == nil && releasedMarker == nil
        }
        XCTAssertTrue(released, "Registry/observers must not retain a detached control or its owner")
    }

    @MainActor
    func testActualProtectedViewRejectsImpossiblePromptWithoutLateStart() async throws {
        try F277CardTestSupport.requireScreen()
        let screen = try XCTUnwrap(NSScreen.main)
        let area = NSRect(x: screen.visibleFrame.minX + 40, y: screen.visibleFrame.minY + 40,
                          width: 400, height: 240)
        let fixture = try notificationFixture(self)
        let presenter = fixture.presenter(screens: [.init(id: 1, frame: area, visibleFrame: area, isMain: true)])
        // First prove the available screen itself fits this exact prompt.
        XCTAssertTrue(fixture.prompt(presenter))
        presenter.dismissAllCards()
        let window = NSWindow(contentRect: area, styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(rootView: DesktopNotificationProtectedRegion(card: presenter.card))
        window.orderFrontRegardless()
        window.contentView?.layoutSubtreeIfNeeded()
        defer { window.contentView = nil; window.orderOut(nil); window.close(); presenter.dismissAllCards() }
        await Task.yield()
        XCTAssertEqual(presenter.card.protectedFrames.count, 1)
        var starts = 0
        var invalidations = 0
        XCTAssertFalse(presenter.presentRecordingPrompt(displayName: "Synthetic meeting",
            onStart: { starts += 1 }, onDismiss: {}, onRememberChoiceChanged: { _ in },
            onExpire: { starts += 1 }, onInvalidated: { invalidations += 1 }))
        XCTAssertFalse(presenter.card.isVisible)
        XCTAssertEqual(invalidations, 1)
        window.orderOut(nil)
        fixture.now.addTimeInterval(9)
        presenter.card.refresh()
        Self.drainTrackingEvents()
        XCTAssertEqual(starts, 0)
        XCTAssertFalse(presenter.card.isVisible, "Freed space must not replay a rejected recording proposal")
    }

    @MainActor
    func testWindowResizeMiniaturizeRestoreAndCloseUpdateLiveRegions() async throws {
        try F277CardTestSupport.requireScreen()
        let screen = try XCTUnwrap(NSScreen.main)
        let card = DesktopNotificationCardPresenter()
        let window = NSWindow(contentRect: NSRect(x: screen.visibleFrame.minX + 50,
            y: screen.visibleFrame.minY + 50, width: 240, height: 100),
            styleMask: [.titled, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        let host = NSHostingView(rootView: DesktopNotificationProtectedRegion(card: card))
        window.contentView = host
        window.orderFrontRegardless()
        host.layoutSubtreeIfNeeded()
        defer { window.contentView = nil; window.orderOut(nil); window.close(); card.dismiss() }
        await Task.yield()
        XCTAssertEqual(try XCTUnwrap(card.protectedFrames.first).width, 240, accuracy: 1)
        window.setContentSize(NSSize(width: 300, height: 130))
        host.layoutSubtreeIfNeeded()
        XCTAssertEqual(try XCTUnwrap(card.protectedFrames.first).width, 300, accuracy: 1)
        XCTAssertEqual(try XCTUnwrap(card.protectedFrames.first).height, 130, accuracy: 1)
        window.miniaturize(nil)
        let miniaturized = try await F277CardTestSupport.awaitAppKitState { window.isMiniaturized }
        XCTAssertTrue(miniaturized, "AppKit must actually miniaturize the test window")
        XCTAssertTrue(card.protectedFrames.isEmpty)
        window.deminiaturize(nil)
        let restored = try await F277CardTestSupport.awaitAppKitState {
            !window.isMiniaturized && card.protectedFrames.count == 1
        }
        XCTAssertTrue(restored)
        window.close()
        XCTAssertTrue(card.protectedFrames.isEmpty)
    }

    @MainActor
    func testMarkerReparentingOwnerChangeAndDismantleLeaveNoStaleRegion() async throws {
        try F277CardTestSupport.requireScreen()
        let screen = try XCTUnwrap(NSScreen.main)
        let firstCard = DesktopNotificationCardPresenter()
        let secondCard = DesktopNotificationCardPresenter()
        let host = NSHostingView(rootView: AnyView(DesktopNotificationProtectedRegion(card: firstCard)
            .frame(width: 160, height: 70)))
        let windows = (0..<2).map { index in
            let window = NSWindow(contentRect: NSRect(x: screen.visibleFrame.minX + 30 + CGFloat(index) * 200,
                y: screen.visibleFrame.minY + 40, width: 160, height: 70),
                styleMask: [.borderless], backing: .buffered, defer: false)
            window.isReleasedWhenClosed = false
            window.orderFrontRegardless()
            return window
        }
        defer {
            windows.forEach { $0.contentView = nil; $0.orderOut(nil); $0.close() }
            firstCard.dismiss(); secondCard.dismiss()
        }
        windows[0].contentView = host
        host.layoutSubtreeIfNeeded()
        await Task.yield()
        XCTAssertEqual(firstCard.protectedFrames.count, 1)
        windows[0].contentView = nil
        XCTAssertTrue(firstCard.protectedFrames.isEmpty)
        windows[1].contentView = host
        host.layoutSubtreeIfNeeded()
        await Task.yield()
        XCTAssertEqual(firstCard.protectedFrames.count, 1)
        XCTAssertEqual(try XCTUnwrap(firstCard.protectedFrames.first).minX, windows[1].frame.minX, accuracy: 1)
        host.rootView = AnyView(DesktopNotificationProtectedRegion(card: secondCard).frame(width: 160, height: 70))
        host.layoutSubtreeIfNeeded()
        await Task.yield()
        XCTAssertTrue(firstCard.protectedFrames.isEmpty)
        XCTAssertEqual(secondCard.protectedFrames.count, 1)
        // The marker never intercepts the actual button's mouse events.
        let marker = try XCTUnwrap(F277CardTestSupport.descendants(host).first {
            String(describing: type(of: $0)) == "CaptureRegionMarker"
        })
        XCTAssertNil(marker.hitTest(NSPoint(x: marker.bounds.midX, y: marker.bounds.midY)))
        host.rootView = AnyView(EmptyView())
        host.layoutSubtreeIfNeeded()
        await Task.yield()
        XCTAssertTrue(secondCard.protectedFrames.isEmpty)
    }

    @MainActor
    func testClippingScrollAndHiddenAncestorRepositionDuringTrackingWithoutExtendingDeadline() async throws {
        try F277CardTestSupport.requireScreen()
        let screen = try XCTUnwrap(NSScreen.main)
        let fixture = F277CardFixture()
        fixture.screens = [.init(id: 1, frame: screen.frame, visibleFrame: screen.visibleFrame, isMain: true)]
        fixture.pointer = NSPoint(x: screen.visibleFrame.midX, y: screen.visibleFrame.midY)
        let card = fixture.presenter()
        let window = NSWindow(contentRect: NSRect(x: screen.visibleFrame.maxX - 210,
            y: screen.visibleFrame.maxY - 150, width: 180, height: 140),
            styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        let scroll = NSScrollView(frame: NSRect(x: 0, y: 0, width: 180, height: 140))
        let document = NSView(frame: NSRect(x: 0, y: 0, width: 180, height: 500))
        let host = NSHostingView(rootView: DesktopNotificationProtectedRegion(card: card).frame(width: 160, height: 70))
        host.frame = NSRect(x: 0, y: 400, width: 160, height: 70)
        document.addSubview(host)
        scroll.documentView = document
        window.contentView = scroll
        window.orderFrontRegardless()
        scroll.contentView.scroll(to: NSPoint(x: 0, y: 360))
        window.contentView?.layoutSubtreeIfNeeded()
        defer { card.dismiss(); window.contentView = nil; window.orderOut(nil) }
        await Task.yield()
        let fullRegion = try XCTUnwrap(card.protectedFrames.first)
        XCTAssertEqual(fullRegion.height, 70, accuracy: 1)
        XCTAssertTrue(card.present(F277CardTestSupport.prompt(), onAction: { _ in }))
        let panel = try XCTUnwrap(card.window)
        let expiry = card.deadline
        XCTAssertLessThanOrEqual(panel.frame.maxY, fullRegion.minY - 8)

        // Real AppKit bounds changes, while running the tracking mode only.
        // No fake notification, card.reposition(), tick or updateWindows().
        scroll.contentView.scroll(to: NSPoint(x: 0, y: 440))
        Self.drainTrackingEvents()
        let partialRegion = try XCTUnwrap(card.protectedFrames.first)
        XCTAssertEqual(partialRegion.height, 30, accuracy: 1)
        XCTAssertLessThanOrEqual(panel.frame.maxY, partialRegion.minY - 8)

        scroll.contentView.scroll(to: .zero)
        Self.drainTrackingEvents()
        XCTAssertTrue(card.protectedFrames.isEmpty)
        XCTAssertEqual(panel.frame.maxY, screen.visibleFrame.maxY - 8, accuracy: 1)

        scroll.contentView.scroll(to: NSPoint(x: 0, y: 360))
        Self.drainTrackingEvents()
        XCTAssertLessThanOrEqual(panel.frame.maxY, fullRegion.minY - 8)
        document.isHidden = true
        Self.drainTrackingEvents()
        XCTAssertTrue(card.protectedFrames.isEmpty)
        XCTAssertEqual(panel.frame.maxY, screen.visibleFrame.maxY - 8, accuracy: 1)
        document.isHidden = false
        Self.drainTrackingEvents()
        XCTAssertLessThanOrEqual(panel.frame.maxY, fullRegion.minY - 8)
        window.orderOut(nil)
        let hiddenWindow = try await F277CardTestSupport.awaitAppKitState {
            panel.frame.maxY == screen.visibleFrame.maxY - 8
        }
        XCTAssertTrue(hiddenWindow)
        XCTAssertTrue(card.protectedFrames.isEmpty)
        window.orderFrontRegardless()
        let shownWindow = try await F277CardTestSupport.awaitAppKitState {
            panel.frame.maxY <= fullRegion.minY - 8
        }
        XCTAssertTrue(shownWindow)
        XCTAssertTrue(card.window === panel)
        XCTAssertEqual(card.deadline, expiry)
    }

    @MainActor
    private static func drainTrackingEvents() {
        for _ in 0..<5 {
            _ = RunLoop.main.run(mode: .eventTracking, before: Date().addingTimeInterval(0.01))
        }
    }

    @MainActor
    func testSeveralMarkersRemainProtectedWhenNewestIsDetached() async throws {
        try await assertRemainingMarkerAfterDetaching(index: 1)
        try await assertRemainingMarkerAfterDetaching(index: 0)
    }

    @MainActor
    private func assertRemainingMarkerAfterDetaching(index: Int) async throws {
        try F277CardTestSupport.requireScreen()
        let screen = try XCTUnwrap(NSScreen.main)
        let card = DesktopNotificationCardPresenter()
        let windows = (0..<2).map { index in
            let window = NSWindow(contentRect: NSRect(x: screen.visibleFrame.minX + 30 + CGFloat(index) * 200,
                y: screen.visibleFrame.minY + 40, width: 160, height: 70),
                styleMask: [.borderless], backing: .buffered, defer: false)
            window.isReleasedWhenClosed = false
            window.contentView = NSHostingView(rootView: DesktopNotificationProtectedRegion(card: card)
                .frame(width: 160, height: 70))
            window.orderFrontRegardless()
            window.contentView?.layoutSubtreeIfNeeded()
            return window
        }
        defer { card.dismiss(); windows.forEach { $0.orderOut(nil) } }
        await Task.yield()
        XCTAssertEqual(card.protectedFrames.count, 2)
        windows[index].contentView = nil
        await Task.yield()
        XCTAssertEqual(card.protectedFrames.count, 1)
        let remaining = try XCTUnwrap(card.protectedFrames.first)
        XCTAssertEqual(remaining.minX, windows[1 - index].frame.minX, accuracy: 1)
    }

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
        let initial = try XCTUnwrap(card.protectedFrames.first)
        XCTAssertEqual(initial.width, 160, accuracy: 1)
        XCTAssertEqual(initial.height, 70, accuracy: 1)
        window.setFrameOrigin(NSPoint(x: window.frame.minX + 30, y: window.frame.minY + 20))
        let moved = try XCTUnwrap(card.protectedFrames.first)
        XCTAssertEqual(moved.minX - initial.minX, 30, accuracy: 1)
        XCTAssertEqual(moved.minY - initial.minY, 20, accuracy: 1)
        window.orderOut(nil)
        XCTAssertTrue(card.protectedFrames.isEmpty)
    }
}
