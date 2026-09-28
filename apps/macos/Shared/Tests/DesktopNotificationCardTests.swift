import AppKit
import XCTest
@testable import TwoBrainRecAppCore

/// Card surface regressions. Scheduling, URL policy and owner isolation live in
/// DesktopLocalNotificationDeliveryTests, not a second notification-centre harness.
@MainActor
final class DesktopNotificationCardTests: XCTestCase {
    private var families: [(String, DesktopNotificationCardContent)] {
        [
            ("meeting", .meeting(title: "Встреча команды", startText: "Начало в 14:30", hasJoinLink: true)),
            ("prompt", F277CardTestSupport.prompt(seconds: 7)),
            ("problem", .problem(title: "Запись требует вашего внимания",
                                 message: "Откройте запись в GRAF, чтобы проверить её сохранность и отправку.",
                                 actionTitle: "Открыть запись", sessionID: "synthetic-session")),
            ("short", .shortRecording),
            ("preview", .preview(title: "Проверка уведомлений GRAF", message: "Так выглядит напоминание о встрече."))
        ]
    }

    func testAutomaticPanelDoesNotTakeKeyOrMainFocus() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        XCTAssertTrue(presenter.present(.preview(title: "Проверка", message: "Сообщение"), onAction: { _ in }))
        let panel = try XCTUnwrap(presenter.window)
        XCTAssertFalse(panel.canBecomeKey)
        XCTAssertFalse(panel.canBecomeMain)
        XCTAssertFalse(panel.isKeyWindow)
        XCTAssertEqual(panel.level, .statusBar)
        XCTAssertTrue(panel.styleMask.contains(.nonactivatingPanel))
        XCTAssertTrue(panel.collectionBehavior.contains(.canJoinAllSpaces))
        XCTAssertTrue(panel.collectionBehavior.contains(.fullScreenAuxiliary))
        XCTAssertFalse(panel.hidesOnDeactivate)
        XCTAssertFalse(panel.ignoresMouseEvents)
    }

    func testDismissClearsSurfaceContentDeadlineAndScreen() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        let presenter = fixture.presenter()
        XCTAssertTrue(presenter.present(.shortRecording, dismissAfter: fixture.now.addingTimeInterval(20), onAction: { _ in }))
        presenter.dismiss()
        XCTAssertFalse(presenter.isVisible)
        XCTAssertNil(presenter.window)
        XCTAssertNil(presenter.presentedContent)
        XCTAssertNil(presenter.deadline)
        XCTAssertNil(presenter.selectedScreenID)
    }

    func testDismissClosesTheRetiredNativeWindowExactlyOnce() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = F277CardFixture().presenter()
        defer { presenter.dismiss() }
        XCTAssertTrue(presenter.present(.shortRecording, onAction: { _ in }))
        let window = try XCTUnwrap(presenter.window)
        let closed = expectation(description: "Retired notification window closes")
        closed.assertForOverFulfill = true
        let token = NotificationCenter.default.addObserver(forName: NSWindow.willCloseNotification,
            object: window, queue: .main) { _ in closed.fulfill() }
        defer { NotificationCenter.default.removeObserver(token) }
        presenter.dismiss()
        presenter.dismiss()
        wait(for: [closed], timeout: 0.2)
        XCTAssertNil(presenter.window)
        XCTAssertFalse(window.isVisible)
    }

    func testDismissReleasesNativePanelAndContentForEveryFamily() async throws {
        try F277CardTestSupport.requireScreen()
        // Automatic cards start without activating their host; do not inherit
        // an earlier keyboard test's activation and pending AppKit events.
        try await F277CardTestSupport.requireInactiveHost()
        for (name, content) in families {
            weak var retiredWindow: NSWindow?
            weak var retiredPresenter: DesktopNotificationCardPresenter?
            weak var retiredView: NSView?
            try autoreleasepool {
                let presenter = F277CardFixture().presenter()
                retiredPresenter = presenter
                XCTAssertTrue(presenter.present(content, onAction: { _ in }), name)
                retiredWindow = try XCTUnwrap(presenter.window)
                retiredView = presenter.window?.contentView
                presenter.dismiss()
            }
            // AppKit may finish releasing the native window on a subsequent
            // event-loop turn after activation. Bound that teardown without
            // running/stopping NSApplication or changing the retired window.
            for _ in 0..<20 {
                if retiredWindow == nil { break }
                try await Task.sleep(for: .milliseconds(10))
            }
            XCTAssertNil(retiredPresenter, name)
            XCTAssertNil(retiredWindow, "A completed \(name) card must release its native window")
            XCTAssertNil(retiredView, name)
        }
    }

    func testReplacementAndExpiryCloseNativeWindowWithoutUserCloseAction() throws {
        try F277CardTestSupport.requireScreen()
        for expires in [false, true] {
            let fixture = F277CardFixture()
            let presenter = fixture.presenter()
            defer { presenter.dismiss() }
            var expiries = 0
            XCTAssertTrue(presenter.present(.shortRecording,
                dismissAfter: fixture.now.addingTimeInterval(1), onAction: { _ in XCTFail("No user action") },
                onExpire: { expiries += 1 }, onClose: { XCTFail("Resource closure is not a user close") }))
            let window = try XCTUnwrap(presenter.window)
            let closed = expectation(description: expires ? "Expired window closes" : "Replaced window closes")
            closed.assertForOverFulfill = true
            let token = NotificationCenter.default.addObserver(forName: NSWindow.willCloseNotification,
                object: window, queue: .main) { _ in closed.fulfill() }
            defer { NotificationCenter.default.removeObserver(token) }
            if expires {
                fixture.now.addTimeInterval(1)
                presenter.refresh()
                presenter.refresh()
            } else {
                XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(), onAction: { _ in }))
            }
            wait(for: [closed], timeout: 0.2)
            XCTAssertEqual(expiries, expires ? 1 : 0)
            XCTAssertFalse(window.isVisible)
            if expires { XCTAssertNil(presenter.window) }
            else { XCTAssertEqual(presenter.presentedContent, F277CardTestSupport.prompt()) }
        }
    }

    func testNativeWindowCloseObserverCanInstallANewCardWithoutLosingIt() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = F277CardFixture().presenter()
        defer { presenter.dismiss() }
        XCTAssertTrue(presenter.present(.shortRecording, onAction: { _ in XCTFail("No old action") },
            onClose: { XCTFail("Dismiss is not a user close") }))
        let window = try XCTUnwrap(presenter.window)
        let next = DesktopNotificationCardContent.preview(title: "Следующее", message: "Сообщение")
        let closed = expectation(description: "A native close observer installs the next card")
        closed.assertForOverFulfill = true
        let token = NotificationCenter.default.addObserver(forName: NSWindow.willCloseNotification,
            object: window, queue: .main) { _ in
                MainActor.assumeIsolated {
                    XCTAssertNil(presenter.window)
                    XCTAssertNil(presenter.presentedContent)
                    XCTAssertTrue(presenter.present(next, onAction: { _ in }))
                    closed.fulfill()
                }
            }
        defer { NotificationCenter.default.removeObserver(token) }
        presenter.dismiss()
        wait(for: [closed], timeout: 0.2)
        XCTAssertEqual(presenter.presentedContent, next)
        XCTAssertTrue(presenter.isVisible)
        XCTAssertFalse(presenter.window === window)
        XCTAssertEqual(presenter.window?.collectionBehavior,
            [.canJoinAllSpaces, .fullScreenAuxiliary, .transient],
            "Retiring the old panel must not change the new card's Spaces behavior")
    }

    func testSameEventUpdateKeepsSurfaceAndDeadline() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        let deadline = fixture.now.addingTimeInterval(120)
        XCTAssertTrue(presenter.present(.meeting(title: "Встреча", startText: "14:30", hasJoinLink: false),
                                        dismissAfter: deadline, onAction: { _ in }))
        let window = presenter.window
        XCTAssertTrue(presenter.update(.meeting(title: "Длинное название встречи", startText: "14:30", hasJoinLink: false)))
        XCTAssertTrue(presenter.window === window)
        XCTAssertEqual(presenter.deadline, deadline)
        XCTAssertFalse(presenter.update(.shortRecording), "Другая семья требует нового показа")
    }

    func testContentIdentifiersAndDisplayDurations() {
        XCTAssertEqual(Set(families.map { $0.1.identifier }).count, 5)
        XCTAssertEqual(DesktopNotificationCardPresenter.previewDisplayDuration, 6)
        XCTAssertEqual(DesktopNotificationCardPresenter.recordingPromptDisplayDuration, 8)
        XCTAssertEqual(DesktopNotificationCardPresenter.noticeDisplayDuration, 20)
        XCTAssertEqual(DesktopNotificationCardContent.shortRecording.accessibilitySummary,
                       "Запись не сохранена — короче 30 секунд.")
        XCTAssertEqual(DesktopNotificationCardContent.preview(title: "Проверка", message: "Сообщение.").accessibilitySummary,
                       "Проверка. Сообщение.")
    }

    func testCloseIsHitTestableAndAcceptsFirstClickWithoutAProductionClickAdapter() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(.preview(title: "Проверка", message: "Сообщение"), onAction: { _ in })
        let window = try XCTUnwrap(presenter.window)
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let close = try F277CardTestSupport.close(view)
        let rect = close.convert(close.bounds, to: nil)
        let parent = try XCTUnwrap(view.superview)
        let outside = parent.convert(NSPoint(x: rect.minX - 100, y: rect.midY), from: nil)
        XCTAssertNil(view.hitTest(outside))
        let event = try XCTUnwrap(NSEvent.mouseEvent(with: .leftMouseDown,
            location: NSPoint(x: rect.midX, y: rect.midY), modifierFlags: [], timestamp: 0,
            windowNumber: window.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 1))
        XCTAssertTrue(event.window === window)
        // NSView.hitTest consumes a point in its superview's coordinate system.
        let hit = try XCTUnwrap(view.hitTest(parent.convert(event.locationInWindow, from: nil)) as? NSButton)
        XCTAssertTrue(hit === close)
        XCTAssertTrue(hit.acceptsFirstMouse(for: event))
        hit.performClick(nil)
        XCTAssertFalse(presenter.isVisible)
    }

    func testProblemWithoutSessionOrActionTitleHasNoActionButton() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = F277CardFixture().presenter()
        defer { presenter.dismiss() }
        for (title, session) in [("Открыть запись", Optional<String>.none), ("", Optional("synthetic"))] {
            XCTAssertTrue(presenter.present(.problem(title: "Проверка", message: "Сообщение",
                actionTitle: title, sessionID: session), onAction: { _ in XCTFail("Нет действия без цели") }))
            let (view, _) = try F277CardTestSupport.fitted(presenter)
            XCTAssertTrue(F277CardTestSupport.actions(view).isEmpty)
        }
    }

    func testAllVisibleControlsAndTextFitSurfaceInBothThemesAndFontSizes() throws {
        try F277CardTestSupport.requireScreen()
        for scale in [CGFloat(1), CGFloat(1.6)] {
            for appearance in [NSAppearance.Name.aqua, .darkAqua] {
                let presenter = F277CardFixture().presenter(scale: scale)
                defer { presenter.dismiss() }
                for (name, content) in families {
                    XCTAssertTrue(presenter.present(content, onAction: { _ in }), name)
                    let window = try XCTUnwrap(presenter.window)
                    window.appearance = NSAppearance(named: appearance)
                    let (view, card) = try F277CardTestSupport.fitted(presenter)
                    XCTAssertEqual(card.bounds.width, 380, accuracy: 0.5)
                    for button in F277CardTestSupport.descendants(view).compactMap({ $0 as? NSButton })
                    where !button.isHiddenOrHasHiddenAncestor {
                        XCTAssertTrue(view.bounds.contains(button.convert(button.bounds, to: view)), "\(name): \(button.title)")
                    }
                    let labels = F277CardTestSupport.labels(view)
                    XCTAssertEqual(labels.count, content == .shortRecording ? 1 : 2, name)
                    for label in labels {
                        XCTAssertTrue(card.bounds.contains(label.convert(label.bounds, to: card)), "\(name): текст")
                        XCTAssertEqual(label.maximumNumberOfLines, 0)
                        XCTAssertEqual(label.lineBreakMode, .byWordWrapping)
                        XCTAssertGreaterThanOrEqual(try XCTUnwrap(label.font).pointSize, 14 * scale)
                        let cell = try XCTUnwrap(label.cell)
                        let required = ceil(cell.cellSize(forBounds: NSRect(x: 0, y: 0,
                            width: label.bounds.width, height: .greatestFiniteMagnitude)).height)
                        XCTAssertGreaterThanOrEqual(label.bounds.height, required,
                            "\(name): недостаточно высоты для всех строк \(label.stringValue)")
                        XCTAssertGreaterThanOrEqual(label.visibleRect.height + 0.5, required,
                            "\(name): контейнер обрезает текст \(label.stringValue)")
                    }
                }
            }
        }
    }

    func testLongRussianTextRaisesHeightWithoutShrinkingFont() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(.preview(title: "Проверка", message: "Короткий текст"), onAction: { _ in })
        let (_, short) = try F277CardTestSupport.fitted(presenter)
        let initialHeight = short.bounds.height
        presenter.update(.preview(title: "Проверка", message: String(repeating: "Длинное проверочное сообщение. ", count: 12)))
        let (view, long) = try F277CardTestSupport.fitted(presenter)
        XCTAssertGreaterThan(long.bounds.height, initialHeight)
        XCTAssertTrue(F277CardTestSupport.labels(view).allSatisfy { ($0.font?.pointSize ?? 0) >= 14 })
    }

    func testInformationalExpiryAndExplicitDismissAreDistinct() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        var expiries = 0
        for (_, content) in families.filter({ ["short", "preview", "problem"].contains($0.0) }) {
            let expiry = fixture.now.addingTimeInterval(20)
            presenter.present(content, dismissAfter: expiry, onAction: { _ in }, onExpire: { expiries += 1 })
            presenter.setHovered(false)
            fixture.now = expiry.addingTimeInterval(-1)
            presenter.refresh()
            XCTAssertTrue(presenter.isVisible)
            fixture.now = expiry
            presenter.refresh()
            XCTAssertFalse(presenter.isVisible)
        }
        XCTAssertEqual(expiries, 3)
        presenter.present(.shortRecording, dismissAfter: fixture.now.addingTimeInterval(20),
                          onAction: { _ in }, onExpire: { expiries += 1 })
        presenter.dismiss()
        fixture.now.addTimeInterval(30)
        presenter.refresh()
        XCTAssertEqual(expiries, 3)
    }

    /// Optional unit-render evidence, not GRAF Dev runtime or VoiceOver acceptance.
    /// Five semantic families × two appearances × standard/large text = 20 PNG files.
    func testCardSurfacesCanBeCapturedForReferenceComparison() throws {
        guard let directory = ProcessInfo.processInfo.environment["GRAF_CARD_SNAPSHOT_DIR"], !directory.isEmpty else {
            throw XCTSkip("GRAF_CARD_SNAPSHOT_DIR not set: unit-render export not requested")
        }
        try F277CardTestSupport.requireScreen()
        let target = URL(fileURLWithPath: directory, isDirectory: true)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        for (fontName, scale) in [("standard", CGFloat(1)), ("large", CGFloat(1.6))] {
            for (themeName, appearance) in [("light", NSAppearance.Name.aqua), ("dark", .darkAqua)] {
                var environment = NotificationCardEnvironment()
                environment.fontScale = scale
                environment.automaticallyTicks = false
                environment.announce = { _, _ in }
                let presenter = DesktopNotificationCardPresenter(environment: environment)
                defer { presenter.dismiss() }
                for (name, content) in families {
                    XCTAssertTrue(presenter.present(content, onAction: { _ in }))
                    let window = try XCTUnwrap(presenter.window)
                    window.appearance = NSAppearance(named: appearance)
                    let view = try XCTUnwrap(window.contentView)
                    view.appearance = NSAppearance(named: appearance)
                    view.layoutSubtreeIfNeeded()
                    view.displayIfNeeded()
                    let image = try XCTUnwrap(view.bitmapImageRepForCachingDisplay(in: view.bounds))
                    view.cacheDisplay(in: view.bounds, to: image)
                    XCTAssertEqual(image.pixelsWide, Int(view.bounds.width * window.backingScaleFactor))
                    let data = try XCTUnwrap(image.representation(using: .png, properties: [:]))
                    try data.write(to: target.appendingPathComponent("card-\(name)-\(themeName)-\(fontName).png"))
                }
            }
        }
    }
}
