import AppKit
import SwiftUI
import TwoBrainRecShared
import XCTest
@testable import TwoBrainRecAppCore

@MainActor
final class DesktopNotificationProtectedConsumerTests: XCTestCase {
    func testCompactRailRegistersActualVisibleStopFrame() async throws {
        try await assertShellStopIsProtected(inTitlebar: false)
    }

    func testTitlebarHUDRegistersActualVisibleStopFrame() async throws {
        try await assertShellStopIsProtected(inTitlebar: true)
    }

    func testExpandedCaptureStatusRegistersActualVisibleStopFrame() async throws {
        try await assertShellStopIsProtected(inTitlebar: false, expanded: true)
    }

    private func assertShellStopIsProtected(inTitlebar: Bool, expanded: Bool = false) async throws {
        try F277CardTestSupport.requireScreen()
        let screen = try XCTUnwrap(NSScreen.main)
        // Only inject the owner. The real consumers must install their own markers.
        // The application singleton also retires OS notifications, which requires
        // an application bundle and is not the subject of this XCTest fixture.
        let fixture = F277CardFixture()
        fixture.screens = [.init(id: 1, frame: screen.frame, visibleFrame: screen.visibleFrame, isMain: true)]
        fixture.pointer = NSPoint(x: screen.visibleFrame.midX, y: screen.visibleFrame.midY)
        let card = fixture.presenter()
        var stopActions = 0
        let session = CaptureSession(
            id: "f277-protected-consumer",
            mode: .audioRecording,
            state: .active,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "synthetic-policy",
            triggerEvidence: [:],
            visibleIndicatorState: .active,
            stopActionAvailable: true,
            bufferSummaryId: nil,
            startedAt: Date(),
            stoppedAt: nil
        )
        let shell = DesktopMeetingShellView(
            session: session,
            uploadQueueItems: [],
            cabinetConfigured: true,
            cabinetState: .ready,
            hasActionableCaptureProblem: expanded,
            onStopRecording: { stopActions += 1 },
            captureControls: { CaptureStatusItem(session: session, onStop: { stopActions += 1 })
                .environment(\.accessibilityEnabled, true) },
            meetingsWorkspace: { Color.clear }
        )
        let host = NSHostingView(rootView: AnyView(shell.environment(\.desktopNotificationCard, card)
            .environment(\.accessibilityEnabled, true)))
        let window = NSWindow(
            contentRect: NSRect(x: screen.visibleFrame.minX + 20,
                                y: screen.visibleFrame.minY + 20,
                                width: min(960, screen.visibleFrame.width - 40),
                                height: min(600, screen.visibleFrame.height - 100)),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.isReleasedWhenClosed = false
        defer {
            card.dismiss()
            // Dismantle the real accessory anchor as well as the content host.
            host.rootView = AnyView(EmptyView())
            host.layoutSubtreeIfNeeded()
            window.contentView = nil
            while !window.titlebarAccessoryViewControllers.isEmpty {
                window.removeTitlebarAccessoryViewController(at: 0)
            }
            window.orderOut(nil)
            window.close()
        }
        window.contentView = host
        window.orderFrontRegardless()
        _ = try await F277CardTestSupport.awaitAppKitState({ false }, timeout: 0.15)

        // Await real layout/accessibility publication, not a synthetic notification.
        // The bounded wait only prepares the fixture; missing AX controls fail below.
        var matches: [NSObject] = []
        var controlNodes: [NSObject] = []
        var accessibleHosts = Set<ObjectIdentifier>()
        for _ in 0..<30 {
            host.layoutSubtreeIfNeeded()
            for accessory in window.titlebarAccessoryViewControllers {
                if let accessoryHost = accessory.view as? NSHostingView<AnyView>,
                   accessibleHosts.insert(ObjectIdentifier(accessoryHost)).inserted {
                    accessoryHost.rootView = AnyView(accessoryHost.rootView.environment(\.accessibilityEnabled, true))
                }
                accessory.view.layoutSubtreeIfNeeded()
            }
            window.displayIfNeeded()
            if inTitlebar {
                let roots = window.titlebarAccessoryViewControllers.map { $0.view as NSObject }
                let hud = accessibilityNodes(roots).filter {
                    identifier($0) == "systemAudio.titlebarRecordingHUD"
                }
                controlNodes = accessibilityNodes(hud)
                matches = controlNodes.filter {
                    role($0) == NSAccessibility.Role.button.rawValue
                        && label($0) == SystemAudioStatusLabels.stopButtonAccessibilityLabel
                }
            } else {
                controlNodes = accessibilityNodes([host] + scrollContentElements(in: host))
                matches = controlNodes.filter {
                    label($0) == SystemAudioStatusLabels.stopButtonAccessibilityLabel
                        && role($0) == NSAccessibility.Role.button.rawValue
                }
            }
            if matches.count == 1, let frame = frame(matches[0]), !frame.isEmpty { break }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        XCTAssertTrue(window.isVisible, "Fixture window must actually be visible")
        XCTAssertTrue(window.isOnActiveSpace, "Fixture must be on the active Space")
        XCTAssertEqual(matches.count, 1, "Expected one actual SwiftUI Stop AX element")
        let stop = try XCTUnwrap(matches.first, "Missing Stop is a fixture/AX failure, not protection RED")
        var stopFrame = try XCTUnwrap(frame(stop), "Actual Stop must expose its screen frame")
        XCTAssertFalse(stopFrame.isEmpty)
        XCTAssertTrue([stopFrame.minX, stopFrame.minY, stopFrame.width, stopFrame.height].allSatisfy { $0.isFinite })
        XCTAssertTrue(window.frame.contains(stopFrame), "Stop must be inside the visible fixture window")
        if inTitlebar {
            let accessory = try XCTUnwrap(window.titlebarAccessoryViewControllers.first)
            XCTAssertEqual(accessory.view.bounds.height, DesktopMeetingShellChrome.recordingStripHeight,
                           accuracy: 0.5, "AppKit must preserve the declared recording strip height")
            let oldWidth = accessory.view.bounds.width
            var resized = window.frame
            resized.size.width -= 80
            window.setFrame(resized, display: true)
            let followedWindow = try await F277CardTestSupport.awaitAppKitState {
                abs(accessory.view.bounds.width - (oldWidth - 80)) < 1
                    && abs(accessory.view.bounds.height - DesktopMeetingShellChrome.recordingStripHeight) < 0.5
            }
            XCTAssertTrue(followedWindow, "Titlebar must preserve its height while following window width")
            stopFrame = try XCTUnwrap(frame(stop))
            XCTAssertTrue(window.frame.contains(stopFrame))
        }
        // Allow pending registration work after layout; never supply an obstacle here.
        await Task.yield()
        let protectedFrames = card.protectedFrames
        let indicators = controlNodes.filter { node in
            if inTitlebar {
                return role(node) == NSAccessibility.Role.staticText.rawValue
                    && stringValue(node) == CaptureStatusItem.statusLabel(for: session)
            }
            if expanded {
                return role(node) == NSAccessibility.Role.staticText.rawValue
                    && stringValue(node) == CaptureStatusItem.accessibilityLabel(for: session)
            }
            return label(node) == "\(DesktopMeetingShellChrome.compactRailLabels[0]): \(CaptureStatusItem.statusLabel(for: session))"
        }
        XCTAssertEqual(indicators.count, 1, "Measure the real recording indicator independently of the markers")
        let indicator = try XCTUnwrap(indicators.first)
        let indicatorFrame = try XCTUnwrap(frame(indicator))
        XCTAssertFalse(indicatorFrame.isEmpty)
        XCTAssertTrue(protectedFrames.contains { $0.insetBy(dx: -1, dy: -1).contains(indicatorFrame) },
                      "Actual indicator \(indicatorFrame) must also be protected")
        XCTAssertTrue(
            protectedFrames.contains { $0.insetBy(dx: -1, dy: -1).contains(stopFrame) },
            "Actual \(inTitlebar ? "titlebar HUD" : "compact rail") Stop \(stopFrame) is not protected: \(protectedFrames)"
        )
        XCTAssertEqual(protectedFrames.count, expanded ? 2 : 3,
                       "Protect expanded status + HUD, or compact indicator + Stop + HUD")
        let region = try XCTUnwrap(protectedFrames.first { $0.insetBy(dx: -1, dy: -1).contains(stopFrame) })
        if !inTitlebar, !expanded {
            XCTAssertEqual(region.width, stopFrame.width, accuracy: 1)
            XCTAssertEqual(region.height, stopFrame.height, accuracy: 1)
        } else {
            XCTAssertLessThan(region.width, window.frame.width)
            XCTAssertLessThan(region.height, 200, "Empty inspector/hosting space must not be protected")
        }

        // Start with a real card, then move the actual Stop into its old frame.
        // No supplied obstacle rectangles: only production consumer registrations.
        let notice = DesktopNotificationCardContent.problem(title: "Проверка размещения",
            message: Array(repeating: "Синтетическая строка проверки", count: 12).joined(separator: "\n"),
            actionTitle: "Открыть", sessionID: "synthetic")
        XCTAssertTrue(card.present(notice, onAction: { _ in }))
        let panel = try XCTUnwrap(card.window)
        let originalPanelFrame = panel.frame
        let deadline = card.deadline
        window.setFrameOrigin(NSPoint(x: window.frame.minX + originalPanelFrame.midX - stopFrame.midX,
            y: window.frame.minY + originalPanelFrame.midY - stopFrame.midY))
        host.layoutSubtreeIfNeeded()
        for accessory in window.titlebarAccessoryViewControllers { accessory.view.layoutSubtreeIfNeeded() }
        let avoided = try await F277CardTestSupport.awaitAppKitState {
            !card.protectedFrames.isEmpty && card.protectedFrames.allSatisfy { !panel.frame.intersects($0) }
                && panel.frame != originalPanelFrame
        }
        XCTAssertTrue(avoided, "Moving a real Stop into the notification must trigger relocation")
        let movedStop = try XCTUnwrap(frame(stop))
        XCTAssertTrue(originalPanelFrame.intersects(movedStop), "Fixture must arrange a genuine collision: panel=\(originalPanelFrame), stop=\(movedStop), regions=\(card.protectedFrames), window=\(window.frame)")
        XCTAssertFalse(panel.frame.intersects(movedStop))
        for protected in card.protectedFrames where panel.frame.maxX > protected.minX && panel.frame.minX < protected.maxX {
            XCTAssertLessThanOrEqual(panel.frame.maxY, protected.minY - 8)
        }
        XCTAssertTrue(card.window === panel)
        XCTAssertEqual(card.deadline, deadline)
        XCTAssertEqual((stop as AnyObject).accessibilityPerformPress?(), true)
        XCTAssertEqual(stopActions, 1, "Actual Stop callback remains reachable and runs once")

        if !inTitlebar, !expanded {
            for (disclosureLabel, expectedRegions) in [
                (DesktopMeetingShellChrome.inspectorToggleCollapsedLabel, 2),
                (DesktopMeetingShellChrome.inspectorToggleExpandedLabel, 3)
            ] {
                let disclosure = try XCTUnwrap(accessibilityNodes([host]).first {
                    role($0) == NSAccessibility.Role.button.rawValue && label($0) == disclosureLabel
                })
                XCTAssertEqual((disclosure as AnyObject).accessibilityPerformPress?(), true)
                let switched = try await F277CardTestSupport.awaitAppKitState {
                    card.protectedFrames.count == expectedRegions
                        && card.protectedFrames.allSatisfy { !panel.frame.intersects($0) }
                }
                XCTAssertTrue(switched, "Real inspector transition must replace its live regions")
                let currentStop = try XCTUnwrap(accessibilityNodes([host] + scrollContentElements(in: host)).first {
                    role($0) == NSAccessibility.Role.button.rawValue
                        && label($0) == SystemAudioStatusLabels.stopButtonAccessibilityLabel
                })
                let currentFrame = try XCTUnwrap(frame(currentStop))
                XCTAssertTrue(card.protectedFrames.contains { $0.insetBy(dx: -1, dy: -1).contains(currentFrame) })
                XCTAssertFalse(panel.frame.intersects(currentFrame))
                XCTAssertTrue(card.window === panel)
                XCTAssertEqual(card.deadline, deadline)
            }
        }

        let idleShell = DesktopMeetingShellView(session: nil, uploadQueueItems: [],
            cabinetConfigured: true, cabinetState: .ready,
            captureControls: { CaptureStatusItem(session: nil, onStop: {}) },
            meetingsWorkspace: { Color.clear })
        host.rootView = AnyView(idleShell.environment(\.desktopNotificationCard, card)
            .environment(\.accessibilityEnabled, true))
        host.layoutSubtreeIfNeeded()
        let cleared = try await F277CardTestSupport.awaitAppKitState {
            card.protectedFrames.isEmpty && window.titlebarAccessoryViewControllers.isEmpty
                && panel.frame == originalPanelFrame
        }
        XCTAssertTrue(cleared, "Ending capture removes its regions/HUD and restores placement")
        XCTAssertTrue(card.window === panel)
        XCTAssertEqual(card.deadline, deadline)
    }

    // SwiftUI's scroll content can vend its virtual elements on AX hit testing
    // without enumerating them as children of the AppKit scroll wrapper. Query
    // the real viewport, independently of notification markers or Stop frames.
    private func scrollContentElements(in host: NSView) -> [NSObject] {
        guard let window = host.window else { return [] }
        return F277CardTestSupport.descendants(host).compactMap { $0 as? NSScrollView }.flatMap { scroll in
            let rect = window.convertToScreen(scroll.convert(scroll.visibleRect.intersection(scroll.bounds), to: nil))
            return stride(from: rect.minY + 1, to: rect.maxY, by: 8).compactMap { y in
                host.accessibilityHitTest(NSPoint(x: rect.midX, y: y)) as? NSObject
            }
        }
    }

    // SwiftUI exposes virtual AX objects, not necessarily NSViews. Traverse both
    // AX child lists; NSView children only bridge through ignored hosting wrappers.
    private func accessibilityNodes(_ roots: [NSObject]) -> [NSObject] {
        var pending = roots
        var seen = Set<ObjectIdentifier>()
        var result: [NSObject] = []
        while let node = pending.popLast() {
            guard seen.insert(ObjectIdentifier(node)).inserted else { continue }
            guard seen.count <= 4096 else {
                XCTFail("Unexpectedly large accessibility tree")
                break
            }
            result.append(node)
            let ax: AnyObject = node
            let children = ax.accessibilityChildren?() ?? []
            pending.append(contentsOf: children.compactMap { $0 as? NSObject })
            pending.append(contentsOf: (ax.accessibilityChildrenInNavigationOrder?() ?? [])
                .compactMap { $0 as? NSObject })
            if let view = node as? NSView { pending.append(contentsOf: view.subviews) }
        }
        return result
    }

    private func identifier(_ node: NSObject) -> String? {
        (node as AnyObject).accessibilityIdentifier?()
    }

    private func label(_ node: NSObject) -> String? {
        (node as AnyObject).accessibilityLabel?()
    }

    private func role(_ node: NSObject) -> String? {
        (node as AnyObject).accessibilityRole?()?.rawValue
    }

    private func frame(_ node: NSObject) -> NSRect? {
        // AX frames are already screen coordinates: do not convert them again.
        (node as AnyObject).accessibilityFrame?()
    }

    private func stringValue(_ node: NSObject) -> String? {
        let selector = #selector(NSAccessibilityProtocol.accessibilityValue)
        guard node.responds(to: selector) else { return nil }
        return node.perform(selector)?.takeUnretainedValue() as? String
    }
}
