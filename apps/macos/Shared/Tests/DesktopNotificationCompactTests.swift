import AppKit
import XCTest
@testable import TwoBrainRecAppCore

/// Shared synthetic fixtures for geometry, lifecycle and accessibility checks.
@MainActor
enum F277CardTestSupport {
    private static var preparedApplication = false
    static func prompt(seconds: Int = 8, remember: Bool = false) -> DesktopNotificationCardContent {
        .recordingPrompt(displayName: "Zoom", remainingSeconds: seconds, rememberChoice: remember)
    }

    static var shortRecording: DesktopNotificationCardContent {
        .shortRecording
    }

    static func requireScreen() throws {
        let app = NSApplication.shared
        try XCTSkipIf(NSScreen.screens.isEmpty, "Нужен экран для измерения настоящей AppKit-панели")
        // swift test is a command-line host, not the launched GRAF app. Set up
        // AppKit here rather than depending on another suite's WebKit/windows.
        // Never activate here: only the production focus() command may do that.
        if app.activationPolicy() == .prohibited {
            XCTAssertTrue(app.setActivationPolicy(.regular), "Тестовому GUI-host нужна разрешённая активация")
        }
        if !preparedApplication {
            if !NSRunningApplication.current.isFinishedLaunching { app.finishLaunching() }
            preparedApplication = true
        }
        XCTAssertNotEqual(app.activationPolicy(), .prohibited)
    }

    static func descendants(_ view: NSView) -> [NSView] {
        view.subviews.flatMap { [$0] + descendants($0) }
    }

    /// XCTest does not run NSApplication's event loop. Host a bounded real loop
    /// for activation/key-window assertions. The timer only ends this test loop;
    /// production focus is notification-driven and has no state polling.
    /// Never call becomeKey(), fake notifications or substitute a result.
    static func awaitAppKitState(_ condition: @escaping @MainActor () -> Bool,
                                timeout: TimeInterval = 2,
                                perform: (@MainActor () -> Void)? = nil) async throws -> Bool {
        if !NSApp.isRunning, !condition() || perform != nil {
            let deadline = Date().addingTimeInterval(timeout)
            var performed = false
            let timer = Timer.scheduledTimer(withTimeInterval: 0.01, repeats: true) { _ in
                MainActor.assumeIsolated {
                    if !performed { performed = true; perform?() }
                    if condition() || Date() >= deadline {
                        NSApp.stop(nil)
                        if let wake = NSEvent.otherEvent(with: .applicationDefined, location: .zero,
                            modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil,
                            subtype: 0, data1: 0, data2: 0) { NSApp.postEvent(wake, atStart: false) }
                    }
                }
            }
            NSApp.run()
            timer.invalidate()
            return condition()
        }
        perform?()
        let deadline = Date().addingTimeInterval(timeout)
        while !condition(), Date() < deadline {
            for _ in 0..<100 {
                guard let event = NSApp.nextEvent(matching: .any, until: Date(),
                    inMode: .default, dequeue: true) else { break }
                NSApp.sendEvent(event)
            }
            if condition() { break }
            try await Task.sleep(for: .milliseconds(10))
        }
        return condition()
    }

    static func requestFocus(_ presenter: DesktopNotificationCardPresenter,
                             file: StaticString = #filePath, line: UInt = #line) async throws {
        let launched = try await awaitAppKitState { NSRunningApplication.current.isFinishedLaunching }
        XCTAssertTrue(launched, "AppKit launch must complete before an explicit user command", file: file, line: line)
        let window = try XCTUnwrap(presenter.window, file: file, line: line)
        let focused = try await awaitAppKitState({ NSApp.isActive && window.isKeyWindow }, timeout: 3, perform: {
            XCTAssertTrue(presenter.focus(), "Запрос фокуса должен быть принят", file: file, line: line)
        })
        XCTAssertTrue(focused, "Ожидается настоящий key window: active=\(NSApp.isActive), running=\(NSApp.isRunning), policy=\(NSApp.activationPolicy().rawValue), canKey=\(window.canBecomeKey)", file: file, line: line)
    }

    /// Prepare a visible, inactive host before creating the card under test.
    /// AppKit owns deactivation; hiding then unhiding without activation avoids
    /// relying on deactivate() across bounded NSApplication event-loop runs.
    static func requireInactiveHost(file: StaticString = #filePath, line: UInt = #line) async throws {
        defer { if NSApp.isHidden { NSApp.unhideWithoutActivation() } }
        let hidden = try await awaitAppKitState({ !NSApp.isActive && NSApp.isHidden }, perform: {
            NSApp.hide(nil)
        })
        guard hidden else {
            XCTFail("Could not hide and deactivate the AppKit test host", file: file, line: line)
            throw CocoaError(.validationMissingMandatoryProperty)
        }
        let visibleInactive = try await awaitAppKitState({ !NSApp.isActive && !NSApp.isHidden }, perform: {
            NSApp.unhideWithoutActivation()
        })
        guard visibleInactive else {
            XCTFail("Could not restore a visible inactive AppKit test host", file: file, line: line)
            throw CocoaError(.validationMissingMandatoryProperty)
        }
    }

    /// Probe the test host independently of notification code. macOS may deny
    /// cooperative activation even to a normal window in an unbundled XCTest
    /// process. A skip here is missing GUI evidence, never product acceptance.
    /// Once the probe succeeds, failures of the actual card remain failures.
    static func requireFocusHost(file: StaticString = #filePath, line: UInt = #line) async throws {
        let launched = try await awaitAppKitState { NSRunningApplication.current.isFinishedLaunching }
        guard launched else {
            XCTFail("AppKit test host did not finish launching", file: file, line: line)
            throw CocoaError(.validationMissingMandatoryProperty)
        }
        try await requireInactiveHost(file: file, line: line)
        let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 240, height: 120),
            styleMask: [.titled], backing: .buffered, defer: false)
        defer { window.orderOut(nil) }
        let focused = try await awaitAppKitState({ NSApp.isActive && window.isKeyWindow }, perform: {
            NSApp.activate()
            window.makeKeyAndOrderFront(nil)
        })
        window.orderOut(nil)
        try XCTSkipIf(!focused,
            "Тестовая среда не подтвердила фокус обычного AppKit-окна без карточки; причина требует проверки в GRAF Dev",
            file: file, line: line)
        try await requireInactiveHost(file: file, line: line)
    }

    static func fitted(_ presenter: DesktopNotificationCardPresenter) throws -> (NSView, CardBackgroundView) {
        let window = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(window.contentView)
        view.layoutSubtreeIfNeeded()
        let card = try XCTUnwrap(descendants(view).compactMap { $0 as? CardBackgroundView }.first)
        card.layoutSubtreeIfNeeded()
        return (view, card)
    }

    static func labels(_ view: NSView) -> [NSTextField] {
        // NSButton/NSScrollView may install private text fields, including an
        // empty default 13pt field. Measure the two semantic card labels only.
        let identifiers = ["graf.notification.title", "graf.notification.message"]
        return descendants(view).compactMap { $0 as? NSTextField }.filter {
            identifiers.contains($0.identifier?.rawValue ?? "") && !$0.isHiddenOrHasHiddenAncestor
        }
    }

    static func actions(_ view: NSView) -> [NotificationCardButton] {
        descendants(view).compactMap { $0 as? NotificationCardButton }
    }

    static func close(_ view: NSView) throws -> NSButton {
        try XCTUnwrap(descendants(view).compactMap { $0 as? NSButton }
            .first { $0.accessibilityLabel() == "Закрыть уведомление" })
    }

    static func checkbox(_ view: NSView) throws -> NSButton {
        try XCTUnwrap(descendants(view).compactMap { $0 as? NSButton }
            .first { $0.title.hasPrefix("Запомнить выбор") })
    }

    /// Coordinates increase downwards independently of the implementation's isFlipped.
    static func verticalInterval(_ element: NSView, in card: NSView) -> (top: CGFloat, bottom: CGFloat) {
        let frame = element.convert(element.bounds, to: card)
        return card.isFlipped ? (frame.minY, frame.maxY) : (-frame.maxY, -frame.minY)
    }
}

@MainActor
final class F277CardFixture {
    var now = Date(timeIntervalSince1970: 2_000_000_000)
    var pointer = NSPoint(x: 100, y: 100)
    var screens = [NotificationCardScreen(id: 1, frame: NSRect(x: 0, y: 0, width: 1440, height: 900),
                                         visibleFrame: NSRect(x: 0, y: 0, width: 1440, height: 875), isMain: true)]
    var announcements: [String] = []

    func presenter(scale: CGFloat = 1) -> DesktopNotificationCardPresenter {
        var environment = NotificationCardEnvironment()
        environment.now = { self.now }
        environment.screens = { self.screens }
        environment.mouseLocation = { self.pointer }
        environment.announce = { _, text in self.announcements.append(text) }
        environment.automaticallyTicks = false
        environment.fontScale = scale
        return DesktopNotificationCardPresenter(environment: environment)
    }
}

@MainActor
final class DesktopNotificationCompactTests: XCTestCase {
    func testFiveFamiliesHave380PointVisibleWidthAnd12PointCorners() throws {
        try F277CardTestSupport.requireScreen()
        let contents: [DesktopNotificationCardContent] = [
            .meeting(title: "Встреча", startText: "Начало в 10:00", hasJoinLink: true),
            F277CardTestSupport.prompt(),
            .problem(title: "Нужна проверка", message: "Откройте запись", actionTitle: "Открыть запись", sessionID: "synthetic"),
            F277CardTestSupport.shortRecording,
            .preview(title: "Проверка", message: "Проверочное сообщение")
        ]
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        for content in contents {
            presenter.present(content, onAction: { _ in })
            let (_, card) = try F277CardTestSupport.fitted(presenter)
            XCTAssertEqual(card.bounds.width, 380, accuracy: 0.5, content.identifier)
            XCTAssertEqual(try XCTUnwrap(card.layer).cornerRadius, 12, accuracy: 0.5)
        }
    }

    func testShortRecordingHasOneFixedMessageNoActionsAndCompactHeight() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(F277CardTestSupport.shortRecording, onAction: { _ in })
        let (view, card) = try F277CardTestSupport.fitted(presenter)
        XCTAssertEqual(F277CardTestSupport.labels(view).map(\.stringValue),
                       ["Запись не сохранена — короче 30 секунд"])
        XCTAssertTrue(F277CardTestSupport.actions(view).isEmpty)
        XCTAssertGreaterThanOrEqual(card.bounds.height, 44)
        XCTAssertLessThanOrEqual(card.bounds.height, 52)
    }

    func testAbsentTitleDoesNotLeaveAnEmptyLabelOrReservedRow() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(.preview(title: "", message: "Короткое сообщение"), onAction: { _ in })
        let (view, card) = try F277CardTestSupport.fitted(presenter)
        XCTAssertEqual(F277CardTestSupport.labels(view).map(\.stringValue), ["Короткое сообщение"])
        let withoutTitle = card.bounds.height
        presenter.present(.preview(title: "Заголовок", message: "Короткое сообщение"), onAction: { _ in })
        let (_, titledCard) = try F277CardTestSupport.fitted(presenter)
        XCTAssertGreaterThan(titledCard.bounds.height, withoutTitle)
    }

    func testCloseHitAreaOverlaysTopLeftAndDoesNotReserveTextColumn() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(.preview(title: "Проверка", message: "Сообщение"), onAction: { _ in })
        let (view, card) = try F277CardTestSupport.fitted(presenter)
        let close = try F277CardTestSupport.close(view)
        let closeFrame = close.convert(close.bounds, to: card)
        XCTAssertGreaterThanOrEqual(closeFrame.width, 28)
        XCTAssertGreaterThanOrEqual(closeFrame.height, 28)
        XCTAssertEqual(closeFrame.midX, card.bounds.minX, accuracy: 1)
        XCTAssertEqual(closeFrame.midY, card.isFlipped ? card.bounds.minY : card.bounds.maxY, accuracy: 1)
        let title = try XCTUnwrap(F277CardTestSupport.labels(view).first { $0.stringValue == "Проверка" })
        let textFrame = title.convert(title.bounds, to: card)
        XCTAssertLessThanOrEqual(textFrame.minX, 12 + 18 + 8 + 1)
        XCTAssertFalse(closeFrame.intersects(textFrame))
    }

    func testActionsAlwaysFollowTextSecondaryBeforePrimary() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        for content in [F277CardTestSupport.prompt(),
                        .meeting(title: "Встреча", startText: "10:00", hasJoinLink: true),
                        .problem(title: "Ошибка", message: "Проверка", actionTitle: "Открыть", sessionID: "synthetic")] {
            presenter.present(content, onAction: { _ in })
            let (view, card) = try F277CardTestSupport.fitted(presenter)
            let actions = F277CardTestSupport.actions(view)
            let textBottom = try XCTUnwrap(F277CardTestSupport.labels(view)
                .map { F277CardTestSupport.verticalInterval($0, in: card).bottom }.max())
            for button in actions {
                XCTAssertGreaterThanOrEqual(F277CardTestSupport.verticalInterval(button, in: card).top, textBottom + 7)
                XCTAssertGreaterThanOrEqual(button.bounds.height, 32)
            }
            if actions.count == 2 {
                let visualOrder = actions.sorted {
                    let left = F277CardTestSupport.verticalInterval($0, in: card).top
                    let right = F277CardTestSupport.verticalInterval($1, in: card).top
                    return abs(left - right) > 1 ? left < right
                        : $0.convert($0.bounds, to: card).minX < $1.convert($1.bounds, to: card).minX
                }
                XCTAssertFalse(visualOrder[0].isPrimary)
                XCTAssertTrue(visualOrder[1].isPrimary)
            }
        }
    }

    func testPromptCheckboxIsSeparateRowAndCountdownHasNoPercent() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(F277CardTestSupport.prompt(seconds: 7), onAction: { _ in })
        let (view, card) = try F277CardTestSupport.fitted(presenter)
        let checkbox = try F277CardTestSupport.checkbox(view)
        XCTAssertEqual(checkbox.title, "Запомнить выбор для Zoom")
        XCTAssertEqual(checkbox.state, .off)
        let checkboxBottom = F277CardTestSupport.verticalInterval(checkbox, in: card).bottom
        for button in F277CardTestSupport.actions(view) {
            XCTAssertGreaterThanOrEqual(F277CardTestSupport.verticalInterval(button, in: card).top, checkboxBottom + 7)
        }
        let labels = F277CardTestSupport.labels(view).map(\.stringValue)
        XCTAssertTrue(labels.contains("Встреча в Zoom"))
        XCTAssertTrue(labels.contains("Запись начнётся через 7 секунд"))
        XCTAssertFalse(labels.joined().contains("%"))
    }

    func testLargePromptAllocatesAndExposesEveryCountdownLineInBothThemes() throws {
        try F277CardTestSupport.requireScreen()
        for appearance in [NSAppearance.Name.aqua, .darkAqua] {
            let presenter = F277CardFixture().presenter(scale: 1.6)
            defer { presenter.dismiss() }
            XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(seconds: 7), onAction: { _ in }))
            try XCTUnwrap(presenter.window).appearance = NSAppearance(named: appearance)
            let (view, card) = try F277CardTestSupport.fitted(presenter)
            let label = try XCTUnwrap(F277CardTestSupport.labels(view).first {
                $0.identifier?.rawValue == "graf.notification.message"
            })
            XCTAssertEqual(label.stringValue, "Запись начнётся через 7 секунд")
            let font = try XCTUnwrap(label.font)
            XCTAssertGreaterThanOrEqual(font.pointSize, 22.4)
            let cell = try XCTUnwrap(label.cell)
            // Query the actual displayed cell, not the presenter's measuring helper.
            let required = ceil(cell.cellSize(forBounds: NSRect(x: 0, y: 0,
                width: label.bounds.width, height: .greatestFiniteMagnitude)).height)
            let oneLine = ceil(font.ascender - font.descender + font.leading)
            XCTAssertGreaterThan(required, oneLine, "При 380pt и large счётчик должен занимать две строки")
            XCTAssertGreaterThanOrEqual(label.bounds.height, required)
            XCTAssertGreaterThanOrEqual(label.visibleRect.height + 0.5, required,
                "Наличие полного stringValue не доказывает видимость хвоста «7 секунд»")
            let labelBottom = F277CardTestSupport.verticalInterval(label, in: card).bottom
            let checkbox = try F277CardTestSupport.checkbox(view)
            XCTAssertGreaterThanOrEqual(F277CardTestSupport.verticalInterval(checkbox, in: card).top, labelBottom + 7)
            let scroll = try XCTUnwrap(F277CardTestSupport.descendants(view).compactMap { $0 as? NSScrollView }.first)
            XCTAssertFalse(scroll.hasVerticalScroller, "Обычный экран должен вместить обе строки без прокрутки")
        }
    }
}
