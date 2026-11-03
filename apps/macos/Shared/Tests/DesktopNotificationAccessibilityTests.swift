import AppKit
import XCTest
@testable import TwoBrainRecAppCore

@MainActor
final class DesktopNotificationAccessibilityTests: XCTestCase {
    func testCountdownSummaryUsesExactRussianSecondFormsFromZeroThroughEight() {
        let expected = ["0 секунд", "1 секунду", "2 секунды", "3 секунды", "4 секунды",
                        "5 секунд", "6 секунд", "7 секунд", "8 секунд"]
        for (seconds, phrase) in expected.enumerated() {
            XCTAssertEqual(F277CardTestSupport.prompt(seconds: seconds).accessibilitySummary,
                "Встреча в Zoom. Запись начнётся через \(phrase).")
        }
        for (seconds, phrase) in [(11, "11 секунд"), (14, "14 секунд"), (20, "20 секунд"),
                                  (21, "21 секунду"), (22, "22 секунды"), (25, "25 секунд")] {
            XCTAssertEqual(F277CardTestSupport.prompt(seconds: seconds).accessibilitySummary,
                "Встреча в Zoom. Запись начнётся через \(phrase).")
        }
    }

    func testPromptSummaryNeverClaimsChoiceAlreadySavedOrAnnouncesPercent() {
        for remember in [false, true] {
            let summary = F277CardTestSupport.prompt(seconds: 7, remember: remember).accessibilitySummary.lowercased()
            XCTAssertTrue(summary.contains("zoom"))
            XCTAssertTrue(summary.contains("7 секунд"))
            XCTAssertFalse(summary.contains("процент"))
            XCTAssertFalse(summary.contains("%"))
            XCTAssertFalse(summary.contains("выбор сохранён"), "Флажок ещё не является сохранением правила")
        }
    }

    func testCheckboxExposesAppScopedLabelAndState() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(F277CardTestSupport.prompt(remember: true), onAction: { _ in })
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let checkbox = try F277CardTestSupport.checkbox(view)
        XCTAssertEqual(checkbox.accessibilityRole(), .checkBox)
        XCTAssertEqual(checkbox.accessibilityLabel(), "Запомнить выбор для Zoom")
        XCTAssertEqual(checkbox.state, .on)
        XCTAssertEqual(checkbox.accessibilityValue() as? NSNumber, NSNumber(value: true))
        XCTAssertEqual(try F277CardTestSupport.close(view).accessibilityRole(), .button)
        for action in F277CardTestSupport.actions(view) {
            XCTAssertEqual(action.accessibilityRole(), .button)
            XCTAssertEqual(action.accessibilityLabel(), action.title)
        }
        checkbox.performClick(nil)
        XCTAssertEqual(checkbox.state, .off)
        XCTAssertEqual(checkbox.accessibilityValue() as? NSNumber, NSNumber(value: false))
    }

    func testEveryControlAcceptsFirstClickWithoutActivatingTheApp() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        let activeBefore = NSApp.isActive
        presenter.present(F277CardTestSupport.prompt(), onAction: { _ in })
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        XCTAssertEqual(NSApp.isActive, activeBefore)
        XCTAssertFalse(try XCTUnwrap(presenter.window).isKeyWindow)
        for button in F277CardTestSupport.descendants(view).compactMap({ $0 as? NSButton }) {
            XCTAssertTrue(button.acceptsFirstMouse(for: nil), button.title)
        }
    }

    func testSurfaceIncludingCloseHitRegionHasEightPointScreenMargin() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(F277CardTestSupport.prompt(), onAction: { _ in })
        let window = try XCTUnwrap(presenter.window)
        let screen = try XCTUnwrap(window.screen)
        let allowed = screen.visibleFrame.insetBy(dx: 8, dy: 8)
        XCTAssertTrue(allowed.contains(window.frame), "Вся панель, включая close hit region, должна помещаться с запасом")
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let close = try F277CardTestSupport.close(view)
        XCTAssertTrue(view.bounds.contains(close.convert(close.bounds, to: view)))
    }

    func testTextAndPrimaryActionContrastInBothThemes() throws {
        for dark in [false, true] {
            let background = DesktopNotificationCardView.cardBackground(dark: dark)
            XCTAssertGreaterThanOrEqual(try contrast(DesktopNotificationCardView.primaryText(dark: dark), background), 4.5)
            XCTAssertGreaterThanOrEqual(try contrast(DesktopNotificationCardView.secondaryText(dark: dark), background), 4.5)
            XCTAssertGreaterThanOrEqual(try contrast(.white, DesktopNotificationCardView.accent(dark: dark)), 4.5)
            XCTAssertGreaterThanOrEqual(try contrast(DesktopNotificationCardView.cardBorder(dark: dark), background), 3)
        }
    }

    func testUncheckedCheckboxRendersContrastingBoundaryInBothThemesAndTextSizes() throws {
        try F277CardTestSupport.requireScreen()
        for scale in [CGFloat(1), CGFloat(1.6)] {
            for (appearance, dark) in [(NSAppearance.Name.aqua, false), (.darkAqua, true)] {
                let presenter = F277CardFixture().presenter(scale: scale)
                defer { presenter.dismiss() }
                XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(), onAction: { _ in }))
                try XCTUnwrap(presenter.window).appearance = NSAppearance(named: appearance)
                let (view, _) = try F277CardTestSupport.fitted(presenter)
                let checkbox = try XCTUnwrap(F277CardTestSupport.checkbox(view) as? NotificationCardCheckbox)
                checkbox.appearance = NSAppearance(named: appearance)
                checkbox.displayIfNeeded()
                let glyph = checkbox.indicatorFrame
                XCTAssertFalse(glyph.isEmpty, "Нужна геометрия настоящего native switch cell")
                XCTAssertTrue(checkbox.bounds.contains(glyph))
                let bitmap = try XCTUnwrap(checkbox.bitmapImageRepForCachingDisplay(in: checkbox.bounds))
                checkbox.cacheDisplay(in: checkbox.bounds, to: bitmap)
                let sx = CGFloat(bitmap.pixelsWide) / checkbox.bounds.width
                let sy = CGFloat(bitmap.pixelsHigh) / checkbox.bounds.height
                let background = DesktopNotificationCardView.cardBackground(dark: dark)
                var contrastingPixels = 0
                // Restrict to the switch glyph: label glyphs must not make this pass.
                // Bitmap rows run top-to-bottom; NSButton's bounds are unflipped.
                let minY = checkbox.isFlipped ? glyph.minY : checkbox.bounds.height - glyph.maxY
                let maxY = minY + glyph.height
                for y in max(0, Int(ceil(minY * sy)))..<min(bitmap.pixelsHigh, Int(floor(maxY * sy))) {
                    for x in max(0, Int(ceil(glyph.minX * sx)))..<min(bitmap.pixelsWide, Int(floor(glyph.maxX * sx))) {
                        if let color = bitmap.colorAt(x: x, y: y), color.alphaComponent >= 0.95,
                           try contrast(color, background) >= 3 {
                            contrastingPixels += 1
                        }
                    }
                }
                XCTAssertGreaterThan(contrastingPixels, Int((glyph.width + glyph.height) * min(sx, sy)),
                    "Нужна видимая граница ≥3:1 в самом bitmap, не только контраст цветового token")
                XCTAssertEqual(checkbox.state, .off)
                XCTAssertEqual(checkbox.accessibilityRole(), .checkBox)
                checkbox.performClick(nil)
                XCTAssertEqual(checkbox.state, .on, "Обводка не должна менять native toggle")
            }
        }
    }

    func testTickAndCheckboxUpdateAnnounceOnlyInitialContent() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        presenter.present(F277CardTestSupport.prompt(), dismissAfter: fixture.now.addingTimeInterval(8),
                          onAction: { _ in }, onTick: { F277CardTestSupport.prompt(seconds: 7) })
        let originalWindow = presenter.window
        fixture.now.addTimeInterval(1)
        presenter.refresh()
        XCTAssertTrue(presenter.update(F277CardTestSupport.prompt(seconds: 7, remember: true)))
        XCTAssertEqual(fixture.announcements.count, 1)
        XCTAssertTrue(presenter.window === originalWindow)
    }

    func testExplicitFocusAndKeyLoopReachCloseCheckboxAndActions() async throws {
        try F277CardTestSupport.requireScreen()
        try await F277CardTestSupport.requireFocusHost()
        let presenter = F277CardFixture().presenter()
        defer { presenter.dismiss() }
        XCTAssertFalse(presenter.focus())
        presenter.present(F277CardTestSupport.prompt(), onAction: { _ in })
        let window = try XCTUnwrap(presenter.window)
        XCTAssertFalse(window.isKeyWindow)
        try await F277CardTestSupport.requestFocus(presenter)
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let close = try F277CardTestSupport.close(view)
        let checkbox = try F277CardTestSupport.checkbox(view)
        let actions = F277CardTestSupport.actions(view)
        XCTAssertTrue(window.firstResponder === close)
        XCTAssertTrue(close.nextKeyView === checkbox)
        XCTAssertTrue(checkbox.nextKeyView === actions.first)
        XCTAssertTrue(actions.last?.nextKeyView === close)
        window.selectNextKeyView(nil)
        XCTAssertTrue(window.firstResponder === checkbox)
        window.selectPreviousKeyView(nil)
        XCTAssertTrue(window.firstResponder === close)
    }

    func testExplicitFocusFromInactiveAppDoesNotDependOnAnotherSuiteActivation() async throws {
        try F277CardTestSupport.requireScreen()
        try await F277CardTestSupport.requireFocusHost()
        let launched = try await F277CardTestSupport.awaitAppKitState { NSRunningApplication.current.isFinishedLaunching }
        XCTAssertTrue(launched)
        let presenter = F277CardFixture().presenter()
        defer { presenter.dismiss() }
        try await F277CardTestSupport.requireInactiveHost()
        XCTAssertFalse(NSApp.isActive, "Начальное состояние должно быть действительно неактивным")
        var policyBeforeFocus: NSApplication.ActivationPolicy?
        XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(), onAction: { _ in }))
        let window = try XCTUnwrap(presenter.window)
        // Let pending AppKit events run; automatic show must still not activate.
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertFalse(NSApp.isActive, "Автоматический показ не активирует GRAF")
        XCTAssertFalse(window.isKeyWindow)
        let pumped = try await F277CardTestSupport.awaitAppKitState({ NSApp.isActive && window.isKeyWindow }, timeout: 3, perform: {
            XCTAssertFalse(NSApp.isActive, "Приложение не должно активироваться до явной команды")
            XCTAssertFalse(NSApp.isHidden, "Проверяется видимое, а не скрытое приложение")
            XCTAssertTrue(window.isVisible)
            XCTAssertFalse(window.isKeyWindow, "Панель не должна получать фокус до явной команды")
            policyBeforeFocus = NSApp.activationPolicy()
            XCTAssertNotEqual(policyBeforeFocus, .prohibited, "Тестовый процесс должен разрешать активацию перед командой")
            XCTAssertTrue(presenter.focus(), "Явная команда должна передать фокус настоящей панели")
        })
        XCTAssertTrue(pumped)
        XCTAssertTrue(NSApp.isActive)
        XCTAssertTrue(window.isKeyWindow)
        XCTAssertEqual(NSApp.activationPolicy(), try XCTUnwrap(policyBeforeFocus), "Production не меняет activationPolicy")
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        XCTAssertTrue(window.firstResponder === (try F277CardTestSupport.close(view)))
        window.selectNextKeyView(nil)
        XCTAssertTrue(window.firstResponder === (try F277CardTestSupport.checkbox(view)))
    }

    func testDismissCancelsPendingFocusBeforeActivationAndCannotFocusReplacement() async throws {
        try F277CardTestSupport.requireScreen()
        var requests: [NSWindow] = []
        var environment = NotificationCardEnvironment()
        environment.automaticallyTicks = false
        environment.announce = { _, _ in }
        environment.requestActivation = {}
        environment.requestKeyWindow = { requests.append($0) }
        let presenter = DesktopNotificationCardPresenter(environment: environment)
        defer { presenter.dismiss() }
        XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(), onAction: { _ in }))
        let old = try XCTUnwrap(presenter.window)
        // Model delayed/denied OS activation explicitly. AppKit is otherwise
        // allowed to grant focus synchronously, even in an inactive test host.
        XCTAssertTrue(presenter.focus())
        XCTAssertTrue(old.canBecomeKey)
        XCTAssertFalse(old.isKeyWindow)
        XCTAssertEqual(requests.count, 1)
        presenter.dismiss()
        XCTAssertTrue(presenter.present(.preview(title: "Следующее", message: "Сообщение"), onAction: { _ in }))
        let replacement = try XCTUnwrap(presenter.window)
        // A simulated late system signal and the real queued continuation must
        // not issue another focus request for either the old or replacement card.
        NotificationCenter.default.post(name: NSApplication.didBecomeActiveNotification, object: NSApp)
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertEqual(requests.count, 1)
        XCTAssertTrue(requests.first === old)
        XCTAssertFalse(old.isVisible)
        XCTAssertFalse(old.isKeyWindow)
        XCTAssertFalse(replacement.canBecomeKey)
        XCTAssertFalse(replacement.isKeyWindow)
        XCTAssertTrue(presenter.window === replacement)
    }

    func testUncompletedFocusRequestExpiresAndDoesNotStealLaterActivation() async throws {
        try F277CardTestSupport.requireScreen()
        // A preceding keyboard test may leave AppKit active. Establish the
        // denied-activation scenario before exposing an eligible key panel.
        try await F277CardTestSupport.requireInactiveHost()
        var requests = 0
        var environment = NotificationCardEnvironment()
        environment.automaticallyTicks = false
        environment.announce = { _, _ in }
        environment.requestActivation = {}
        environment.requestKeyWindow = { _ in requests += 1 }
        let presenter = DesktopNotificationCardPresenter(environment: environment)
        defer { presenter.dismiss() }
        XCTAssertTrue(presenter.present(.shortRecording, onAction: { _ in }))
        let window = try XCTUnwrap(presenter.window)
        XCTAssertTrue(presenter.focus())
        XCTAssertFalse(window.isKeyWindow, "Проверка требует ещё не завершённой активации")
        XCTAssertTrue(window.canBecomeKey)
        // Exercise the actual one-shot expiry while the OS boundary declines
        // both immediate and deferred focus attempts.
        try await Task.sleep(for: .milliseconds(2100))
        XCTAssertFalse(window.canBecomeKey)
        let completedRequests = requests
        XCTAssertGreaterThanOrEqual(completedRequests, 1)
        NotificationCenter.default.post(name: NSApplication.didBecomeActiveNotification, object: NSApp)
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertEqual(requests, completedRequests, "Истёкший запрос не реагирует на позднюю активацию")
        XCTAssertFalse(window.isKeyWindow)
        XCTAssertTrue(window.isVisible, "Отказ в фокусе не удаляет само уведомление")
    }

    func testFocusedKeyboardEventsToggleActAndCloseWithoutGlobalEscape() async throws {
        try F277CardTestSupport.requireScreen()
        try await F277CardTestSupport.requireFocusHost()
        let presenter = F277CardFixture().presenter()
        defer { presenter.dismiss() }
        var received: [DesktopNotificationCardAction] = []
        var closed = 0
        XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(),
            onAction: { received.append($0) }, onClose: { closed += 1 }))
        let window = try XCTUnwrap(presenter.window)
        // An unfocused card must not consume Escape from another context.
        window.keyDown(with: try key(window, code: 53, text: "\u{1b}"))
        XCTAssertTrue(presenter.isVisible)
        XCTAssertEqual(closed, 0)
        try await F277CardTestSupport.requestFocus(presenter)
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let checkbox = try F277CardTestSupport.checkbox(view)
        let close = try F277CardTestSupport.close(view)
        window.sendEvent(try key(window, code: 48, text: "\t"))
        XCTAssertTrue(window.firstResponder === checkbox)
        window.sendEvent(try key(window, code: 49, text: " "))
        XCTAssertEqual(received, [.toggleRecordingPromptRemember(true)])
        XCTAssertTrue(window.firstResponder === checkbox)
        window.sendEvent(try key(window, code: 48, text: "\t", modifiers: .shift))
        XCTAssertTrue(window.firstResponder === close)
        let record = try XCTUnwrap(F277CardTestSupport.actions(view).first { $0.title == "Записать" })
        XCTAssertTrue(window.makeFirstResponder(record))
        window.sendEvent(try key(window, code: 36, text: "\r"))
        XCTAssertEqual(received, [.toggleRecordingPromptRemember(true), .record])
        XCTAssertFalse(presenter.isVisible)
        XCTAssertEqual(closed, 0)

        XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(),
            onAction: { _ in XCTFail("Escape не является start/skip") }, onClose: { closed += 1 }))
        try await F277CardTestSupport.requestFocus(presenter)
        let nextWindow = try XCTUnwrap(presenter.window)
        nextWindow.sendEvent(try key(nextWindow, code: 53, text: "\u{1b}"))
        XCTAssertEqual(closed, 1)
        XCTAssertFalse(presenter.isVisible)
    }

    func testScreenSelectionStaysStableUntilSelectedDisplayIsRemoved() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        fixture.screens.append(NotificationCardScreen(id: 2,
            frame: NSRect(x: 1440, y: 0, width: 1024, height: 768),
            visibleFrame: NSRect(x: 1440, y: 0, width: 1024, height: 744)))
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        let expiry = fixture.now.addingTimeInterval(120)
        presenter.present(.meeting(title: "Встреча", startText: "14:30", hasJoinLink: false),
                          dismissAfter: expiry, onAction: { _ in })
        let originalWindow = presenter.window
        let initialFrame = try XCTUnwrap(originalWindow).frame
        fixture.pointer = NSPoint(x: 1500, y: 100)
        presenter.reposition()
        XCTAssertEqual(presenter.selectedScreenID, 1)
        XCTAssertEqual(presenter.window?.frame, initialFrame)
        fixture.screens.removeFirst()
        fixture.screens[0].isMain = true
        NotificationCenter.default.post(name: NSApplication.didChangeScreenParametersNotification, object: NSApp)
        XCTAssertEqual(presenter.selectedScreenID, 2)
        XCTAssertTrue(presenter.window === originalWindow)
        XCTAssertEqual(presenter.deadline, expiry)
        XCTAssertTrue(fixture.screens[0].visibleFrame.insetBy(dx: 8, dy: 8).contains(try XCTUnwrap(presenter.window).frame))
    }

    func testProtectedRegionMovesPanelDownWithoutResetAndImpossiblePlacementInvalidates() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        var invalidated = 0
        presenter.present(F277CardTestSupport.prompt(), dismissAfter: fixture.now.addingTimeInterval(8),
                          onAction: { _ in }, onInvalidated: { invalidated += 1 })
        let deadline = presenter.deadline
        let window = try XCTUnwrap(presenter.window)
        let obstacle = NSRect(x: window.frame.minX, y: 760, width: window.frame.width, height: 100)
        let regionID = UUID()
        presenter.registerProtectedRegion(id: regionID) { obstacle }
        presenter.reposition()
        XCTAssertTrue(presenter.window === window)
        XCTAssertLessThanOrEqual(window.frame.maxY, obstacle.minY - 8)
        XCTAssertEqual(presenter.deadline, deadline)
        presenter.registerProtectedRegion(id: regionID) { fixture.screens[0].visibleFrame }
        presenter.reposition()
        presenter.reposition()
        XCTAssertEqual(invalidated, 1)
        XCTAssertFalse(presenter.isVisible)
    }

    func testNarrowShortScreenScrollsTextButKeepsControlsReachable() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        fixture.screens = [NotificationCardScreen(id: 1,
            frame: NSRect(x: 0, y: 0, width: 300, height: 350),
            visibleFrame: NSRect(x: 0, y: 0, width: 300, height: 350), isMain: true)]
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        let content = DesktopNotificationCardContent.problem(title: "Проверка",
            message: String(repeating: "Длинный доступный текст. ", count: 70),
            actionTitle: "Открыть запись для проверки сохранности", sessionID: "synthetic")
        XCTAssertTrue(presenter.present(content, onAction: { _ in }))
        let (view, card) = try F277CardTestSupport.fitted(presenter)
        XCTAssertLessThan(card.bounds.width, 380)
        XCTAssertGreaterThanOrEqual(card.bounds.width, 220)
        let scroll = try XCTUnwrap(F277CardTestSupport.descendants(view).compactMap { $0 as? NSScrollView }.first)
        XCTAssertTrue(scroll.hasVerticalScroller)
        XCTAssertTrue(scroll.acceptsFirstResponder)
        XCTAssertGreaterThan(try XCTUnwrap(scroll.documentView).bounds.height, scroll.contentView.bounds.height)
        for button in F277CardTestSupport.actions(view) {
            XCTAssertTrue(card.bounds.contains(button.convert(button.bounds, to: card)))
            XCTAssertGreaterThanOrEqual(try XCTUnwrap(button.font).pointSize, 13)
        }
    }

    func testUnavailableScreenOrInsufficientControlsSpaceRejectsPrompt() throws {
        _ = NSApplication.shared
        let fixture = F277CardFixture()
        fixture.screens = []
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        var expiry = 0
        XCTAssertFalse(presenter.present(F277CardTestSupport.prompt(),
            dismissAfter: fixture.now.addingTimeInterval(8), onAction: { _ in }, onExpire: { expiry += 1 }))
        XCTAssertNil(presenter.deadline)
        fixture.screens = [NotificationCardScreen(id: 1,
            frame: NSRect(x: 0, y: 0, width: 300, height: 90),
            visibleFrame: NSRect(x: 0, y: 0, width: 300, height: 90), isMain: true)]
        XCTAssertFalse(presenter.present(F277CardTestSupport.prompt(),
            dismissAfter: fixture.now.addingTimeInterval(8), onAction: { _ in }, onExpire: { expiry += 1 }))
        fixture.now.addTimeInterval(20)
        presenter.refresh()
        presenter.reposition()
        XCTAssertFalse(presenter.isVisible)
        XCTAssertEqual(expiry, 0)
        XCTAssertTrue(fixture.announcements.isEmpty)
    }

    func testKeyboardScrollSurvivesTickAndTabReachesAction() async throws {
        try F277CardTestSupport.requireScreen()
        try await F277CardTestSupport.requireFocusHost()
        let fixture = F277CardFixture()
        fixture.screens = [NotificationCardScreen(id: 1,
            frame: NSRect(x: 0, y: 0, width: 300, height: 350),
            visibleFrame: NSRect(x: 0, y: 0, width: 300, height: 350), isMain: true)]
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        let content = DesktopNotificationCardContent.problem(title: "Проверка",
            message: String(repeating: "Длинный доступный текст. ", count: 70),
            actionTitle: "Открыть запись", sessionID: "synthetic")
        let updated = DesktopNotificationCardContent.problem(title: "Обновлено",
            message: String(repeating: "Длинный доступный текст. ", count: 70),
            actionTitle: "Открыть запись", sessionID: "synthetic")
        XCTAssertTrue(presenter.present(content, onAction: { _ in }, onTick: { updated }))
        try await F277CardTestSupport.requestFocus(presenter)
        let window = try XCTUnwrap(presenter.window)
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let scroll = try XCTUnwrap(F277CardTestSupport.descendants(view).compactMap { $0 as? NSScrollView }.first)
        XCTAssertTrue(scroll.hasVerticalScroller)
        XCTAssertTrue(window.firstResponder === (try F277CardTestSupport.close(view)))
        window.sendEvent(try key(window, code: 48, text: "\t"))
        XCTAssertTrue(window.firstResponder === scroll,
            "Tab must focus scroll, got \(String(describing: window.firstResponder))")
        let initialY = scroll.contentView.bounds.minY
        window.sendEvent(try key(window, code: 125, text: "\u{f701}", modifiers: .function))
        let lineY = scroll.contentView.bounds.minY
        XCTAssertGreaterThan(lineY, initialY)
        window.sendEvent(try key(window, code: 121, text: "\u{f72d}", modifiers: .function))
        let pageY = scroll.contentView.bounds.minY
        XCTAssertGreaterThan(pageY, lineY)
        fixture.now.addTimeInterval(1); presenter.refresh()
        let title = try XCTUnwrap(F277CardTestSupport.descendants(view).compactMap { $0 as? NSTextField }
            .first { $0.identifier?.rawValue == "graf.notification.title" })
        XCTAssertEqual(title.stringValue, "Обновлено")
        XCTAssertTrue(presenter.window === window)
        XCTAssertTrue(window.isKeyWindow)
        XCTAssertTrue(window.firstResponder === scroll)
        XCTAssertEqual(scroll.contentView.bounds.minY, pageY, accuracy: 0.5)
        let expectedAction = try XCTUnwrap(F277CardTestSupport.actions(view).first)
        window.sendEvent(try key(window, code: 48, text: "\t"))
        XCTAssertTrue(window.firstResponder === expectedAction,
            "Tab must leave scroll for action; got \(String(describing: window.firstResponder)), next=\(String(describing: scroll.nextKeyView))")
        window.sendEvent(try key(window, code: 48, text: "\t", modifiers: .shift))
        XCTAssertTrue(window.firstResponder === scroll)
        window.sendEvent(try key(window, code: 48, text: "\t", modifiers: .shift))
        XCTAssertTrue(window.firstResponder === (try F277CardTestSupport.close(view)))
    }

    func testEscapeRestoresPreviousWindowAndCallbackReplacementKeepsItsFocus() async throws {
        try F277CardTestSupport.requireScreen()
        try await F277CardTestSupport.requireFocusHost()
        let previous = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 240, height: 120),
            styleMask: [.titled], backing: .buffered, defer: false)
        defer { previous.orderOut(nil) }
        let previousFocused = try await F277CardTestSupport.awaitAppKitState({ NSApp.isActive && previous.isKeyWindow }, perform: {
            NSApp.activate(); previous.makeKeyAndOrderFront(nil)
        })
        XCTAssertTrue(previousFocused)
        let presenter = F277CardFixture().presenter()
        defer { presenter.dismiss() }
        var closes = 0
        XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(), onAction: { _ in }, onClose: { closes += 1 }))
        try await F277CardTestSupport.requestFocus(presenter)
        let first = try XCTUnwrap(presenter.window)
        XCTAssertFalse(previous.isKeyWindow)
        first.sendEvent(try key(first, code: 53, text: "\u{1b}"))
        let restored = try await F277CardTestSupport.awaitAppKitState { previous.isKeyWindow && NSApp.keyWindow === previous }
        XCTAssertTrue(restored)
        XCTAssertEqual(closes, 1)
        XCTAssertNil(presenter.window)

        XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(), onAction: { _ in }, onClose: {
            closes += 1
            XCTAssertTrue(presenter.present(.preview(title: "Следующее", message: "Сообщение"), onAction: { _ in }))
            XCTAssertTrue(presenter.focus())
        }))
        try await F277CardTestSupport.requestFocus(presenter)
        let old = try XCTUnwrap(presenter.window)
        old.sendEvent(try key(old, code: 53, text: "\u{1b}"))
        let replacement = try XCTUnwrap(presenter.window)
        XCTAssertFalse(old === replacement)
        let focused = try await F277CardTestSupport.awaitAppKitState { replacement.isKeyWindow && NSApp.keyWindow === replacement }
        XCTAssertTrue(focused)
        try await Task.sleep(for: .milliseconds(30))
        XCTAssertTrue(replacement.isKeyWindow)
        XCTAssertFalse(previous.isKeyWindow)
        XCTAssertEqual(closes, 2)
        let (replacementView, _) = try F277CardTestSupport.fitted(presenter)
        XCTAssertTrue(replacement.firstResponder === (try F277CardTestSupport.close(replacementView)))
    }

    private func key(_ window: NSWindow, code: UInt16, text: String,
                     modifiers: NSEvent.ModifierFlags = []) throws -> NSEvent {
        try XCTUnwrap(NSEvent.keyEvent(with: .keyDown, location: .zero,
            modifierFlags: modifiers, timestamp: 0, windowNumber: window.windowNumber,
            context: nil, characters: text, charactersIgnoringModifiers: text,
            isARepeat: false, keyCode: code))
    }

    private func contrast(_ first: NSColor, _ second: NSColor) throws -> CGFloat {
        func luminance(_ color: NSColor) throws -> CGFloat {
            let rgb = try XCTUnwrap(color.usingColorSpace(.sRGB))
            func linear(_ value: CGFloat) -> CGFloat {
                value <= 0.04045 ? value / 12.92 : pow((value + 0.055) / 1.055, 2.4)
            }
            return 0.2126 * linear(rgb.redComponent) + 0.7152 * linear(rgb.greenComponent) + 0.0722 * linear(rgb.blueComponent)
        }
        let a = try luminance(first), b = try luminance(second)
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)
    }
}
