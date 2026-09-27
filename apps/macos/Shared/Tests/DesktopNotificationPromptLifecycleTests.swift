import AppKit
import XCTest
@testable import TwoBrainRecAppCore

@MainActor
final class DesktopNotificationPromptLifecycleTests: XCTestCase {
    func testInformationalHoverHoldPreservesRemainingTimeForAllThreeFamilies() throws {
        try F277CardTestSupport.requireScreen()
        let cases: [(DesktopNotificationCardContent, TimeInterval)] = [
            (.preview(title: "Проверка", message: "Сообщение"), 6),
            (.shortRecording, 20),
            (.problem(title: "Проверка", message: "Сообщение", actionTitle: "Открыть", sessionID: "synthetic"), 20)
        ]
        for (content, duration) in cases {
            let fixture = F277CardFixture()
            let presenter = fixture.presenter()
            defer { presenter.dismiss() }
            var expired = 0
            let initialDeadline = fixture.now.addingTimeInterval(duration)
            XCTAssertTrue(presenter.present(content, dismissAfter: initialDeadline,
                onAction: { _ in XCTFail("Hold не выполняет действие") }, onExpire: { expired += 1 }))
            presenter.setHovered(false)
            fixture.now.addTimeInterval(2)
            presenter.setHovered(true)
            fixture.now.addTimeInterval(30)
            presenter.refresh()
            XCTAssertEqual(expired, 0)
            XCTAssertTrue(presenter.isVisible)
            presenter.setHovered(false)
            XCTAssertEqual(presenter.deadline, initialDeadline.addingTimeInterval(30))
            fixture.now.addTimeInterval(duration - 3)
            presenter.refresh()
            XCTAssertEqual(expired, 0, "После hold остаётся исходный остаток, не новый полный срок")
            fixture.now.addTimeInterval(1)
            presenter.refresh()
            presenter.refresh()
            XCTAssertEqual(expired, 1)
            XCTAssertFalse(presenter.isVisible)
        }
    }

    func testKeyFocusHoldAndHoverOverlapResumeOnlyAfterBothEnd() async throws {
        try F277CardTestSupport.requireScreen()
        try await F277CardTestSupport.requireFocusHost()
        let fixture = F277CardFixture()
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        var expired = 0
        let initialDeadline = fixture.now.addingTimeInterval(20)
        XCTAssertTrue(presenter.present(.shortRecording, dismissAfter: initialDeadline,
            onAction: { _ in }, onExpire: { expired += 1 }))
        presenter.setHovered(false)
        fixture.now.addTimeInterval(5)
        try await F277CardTestSupport.requestFocus(presenter)
        let window = try XCTUnwrap(presenter.window)
        fixture.now.addTimeInterval(30)
        presenter.refresh()
        XCTAssertEqual(expired, 0)
        presenter.setHovered(true)
        window.resignKey()
        fixture.now.addTimeInterval(10)
        presenter.refresh()
        XCTAssertEqual(expired, 0)
        presenter.setHovered(false)
        XCTAssertEqual(presenter.deadline, initialDeadline.addingTimeInterval(40))
        fixture.now.addTimeInterval(14)
        presenter.refresh()
        XCTAssertEqual(expired, 0)
        fixture.now.addTimeInterval(1)
        presenter.refresh()
        XCTAssertEqual(expired, 1)
    }

    func testPromptAndMeetingDeadlinesIgnoreHoverAndKeyFocus() async throws {
        try F277CardTestSupport.requireScreen()
        try await F277CardTestSupport.requireFocusHost()
        let cases: [(DesktopNotificationCardContent, Int)] = [
            (F277CardTestSupport.prompt(), 8),
            (.meeting(title: "Встреча", startText: "10:00", hasJoinLink: true), 120)
        ]
        for (content, duration) in cases {
            let fixture = F277CardFixture()
            let presenter = fixture.presenter()
            defer { presenter.dismiss() }
            var expired = 0
            let deadline = fixture.now.addingTimeInterval(TimeInterval(duration))
            XCTAssertTrue(presenter.present(content, dismissAfter: deadline,
                onAction: { _ in }, onExpire: { expired += 1 }, onInvalidated: { XCTFail("Обычные тики допустимы") }))
            presenter.setHovered(true)
            try await F277CardTestSupport.requestFocus(presenter)
            for _ in 1..<duration {
                fixture.now.addTimeInterval(1)
                presenter.refresh()
                XCTAssertEqual(expired, 0)
                XCTAssertEqual(presenter.deadline, deadline)
            }
            fixture.now.addTimeInterval(1)
            presenter.refresh()
            XCTAssertEqual(expired, 1)
            XCTAssertFalse(presenter.isVisible)
        }
    }

    func testDelayedOrBackwardsPromptTickInvalidatesBeforeExpiryForEitherCheckboxValue() throws {
        try F277CardTestSupport.requireScreen()
        for remember in [false, true] {
            for gap in [TimeInterval(3), 9, -1] {
                let fixture = F277CardFixture()
                let presenter = fixture.presenter()
                defer { presenter.dismiss() }
                var invalidated = 0
                XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(remember: remember),
                    dismissAfter: fixture.now.addingTimeInterval(8),
                    onAction: { _ in XCTFail("Задержанный вопрос не выполняет действие") },
                    onExpire: { XCTFail("Задержанный tick не может запустить запись") },
                    onClose: { XCTFail("Invalidation не является close") },
                    onInvalidated: {
                        invalidated += 1
                        XCTAssertFalse(presenter.isVisible)
                        XCTAssertNil(presenter.presentedContent)
                        XCTAssertNil(presenter.deadline)
                    }))
                fixture.now.addTimeInterval(gap)
                presenter.refresh()
                fixture.now.addTimeInterval(30)
                presenter.refresh()
                presenter.invalidate()
                XCTAssertEqual(invalidated, 1)
            }
        }
    }

    func testHiddenPanelInvalidatesBeforeDueTickAndCannotFireHeldButton() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        var invalidated = 0
        XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(),
            dismissAfter: fixture.now.addingTimeInterval(1),
            onAction: { _ in XCTFail("Скрытый вопрос не выполняет действие") },
            onExpire: { XCTFail("Невидимая панель не запускает запись") },
            onInvalidated: { invalidated += 1 }))
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let button = try XCTUnwrap(F277CardTestSupport.actions(view).last)
        try XCTUnwrap(presenter.window).orderOut(nil)
        fixture.now.addTimeInterval(1)
        presenter.refresh()
        button.performClick(nil)
        presenter.refresh()
        XCTAssertEqual(invalidated, 1)
        XCTAssertNil(presenter.window)
        XCTAssertNil(presenter.deadline)
        XCTAssertNil(presenter.presentedContent)
    }

    func testInvalidationClearsBeforeCallbackAndDoesNotInvalidateReplacement() throws {
        try F277CardTestSupport.requireScreen()
        let fixture = F277CardFixture()
        let presenter = fixture.presenter()
        defer { presenter.dismiss() }
        let next = DesktopNotificationCardContent.preview(title: "Следующее", message: "Сообщение")
        var invalidated = 0
        XCTAssertTrue(presenter.present(F277CardTestSupport.prompt(),
            dismissAfter: fixture.now.addingTimeInterval(8), onAction: { _ in },
            onInvalidated: {
                invalidated += 1
                XCTAssertNil(presenter.window)
                XCTAssertNil(presenter.presentedContent)
                XCTAssertTrue(presenter.present(next, onAction: { _ in }))
            }))
        fixture.now.addTimeInterval(9)
        presenter.refresh()
        presenter.refresh()
        XCTAssertEqual(invalidated, 1)
        XCTAssertEqual(presenter.presentedContent, next)
        XCTAssertTrue(presenter.isVisible)
    }

    func testCountdownRefreshKeepsWindowCheckboxButtonsAndFirstResponder() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.present(F277CardTestSupport.prompt(), dismissAfter: Date().addingTimeInterval(8),
                          onAction: { _ in }, onTick: { F277CardTestSupport.prompt(seconds: 7) })
        let window = try XCTUnwrap(presenter.window)
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let checkbox = try F277CardTestSupport.checkbox(view)
        let buttons = F277CardTestSupport.actions(view)
        XCTAssertTrue(window.makeFirstResponder(checkbox))
        presenter.refresh()
        let (updatedView, _) = try F277CardTestSupport.fitted(presenter)
        XCTAssertTrue(presenter.window === window)
        XCTAssertTrue(updatedView === view)
        XCTAssertTrue(try F277CardTestSupport.checkbox(updatedView) === checkbox)
        XCTAssertEqual(F277CardTestSupport.actions(updatedView).map(ObjectIdentifier.init), buttons.map(ObjectIdentifier.init))
        XCTAssertTrue(presenter.window?.firstResponder === checkbox)
        XCTAssertEqual(presenter.presentedContent, F277CardTestSupport.prompt(seconds: 7))
    }

    func testCloseClearsOldStateBeforeReentrantPresentation() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        let next = DesktopNotificationCardContent.preview(title: "Следующее", message: "Сообщение")
        var closed = 0
        presenter.present(F277CardTestSupport.prompt(), onAction: { _ in XCTFail("Close не является start/skip") },
                          onClose: {
                              closed += 1
                              XCTAssertFalse(presenter.isVisible)
                              XCTAssertNil(presenter.presentedContent)
                              presenter.present(next, onAction: { _ in })
                          })
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let oldClose = try F277CardTestSupport.close(view)
        oldClose.performClick(nil)
        XCTAssertEqual(closed, 1)
        XCTAssertTrue(presenter.isVisible)
        XCTAssertEqual(presenter.presentedContent, next)
        oldClose.performClick(nil)
        XCTAssertEqual(closed, 1, "Удержанная старая кнопка не завершает новое событие")
        XCTAssertEqual(presenter.presentedContent, next)
    }

    func testTerminalButtonsClearBeforeCallbackAndCannotActTwice() throws {
        try F277CardTestSupport.requireScreen()
        for remember in [false, true] {
            for expected in [DesktopNotificationCardAction.record, .skipRecordingPrompt] {
                let presenter = DesktopNotificationCardPresenter()
                defer { presenter.dismiss() }
                var received: [DesktopNotificationCardAction] = []
                let next = DesktopNotificationCardContent.preview(title: "Следующее", message: "Сообщение")
                presenter.present(F277CardTestSupport.prompt(remember: remember), onAction: { action in
                    received.append(action)
                    XCTAssertFalse(presenter.isVisible)
                    XCTAssertNil(presenter.presentedContent)
                    presenter.present(next, onAction: { _ in XCTFail("Старый control вызвал новый callback") })
                })
                let (view, _) = try F277CardTestSupport.fitted(presenter)
                let button = try XCTUnwrap(F277CardTestSupport.actions(view)
                    .first { $0.title == (expected == .record ? "Записать" : "Не записывать") })
                button.performClick(nil)
                button.performClick(nil)
                XCTAssertEqual(received, [expected])
                XCTAssertEqual(presenter.presentedContent, next)
            }
        }
    }

    func testCheckboxIsNonterminalAndUpdatesCurrentContentBeforeCallback() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        var changes: [DesktopNotificationCardAction] = []
        presenter.present(F277CardTestSupport.prompt(), onAction: { action in
            changes.append(action)
            XCTAssertTrue(presenter.isVisible)
            XCTAssertEqual(presenter.presentedContent, F277CardTestSupport.prompt(remember: true))
        })
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let checkbox = try F277CardTestSupport.checkbox(view)
        checkbox.performClick(nil)
        XCTAssertEqual(changes, [.toggleRecordingPromptRemember(true)])
        XCTAssertEqual(checkbox.state, .on)
        XCTAssertTrue(presenter.window?.contentView === view)
    }

    func testCloseWithEitherCheckboxValueNeverDispatchesARecordingAction() throws {
        try F277CardTestSupport.requireScreen()
        for remember in [false, true] {
            let presenter = DesktopNotificationCardPresenter()
            defer { presenter.dismiss() }
            var closes = 0
            presenter.present(F277CardTestSupport.prompt(remember: remember),
                              onAction: { _ in XCTFail("Close не сохраняет правило") },
                              onExpire: { XCTFail("Close не запускает запись") }, onClose: { closes += 1 })
            let (view, _) = try F277CardTestSupport.fitted(presenter)
            try F277CardTestSupport.close(view).performClick(nil)
            presenter.refresh()
            XCTAssertEqual(closes, 1)
            XCTAssertFalse(presenter.isVisible)
        }
    }

    func testDismissedViewCannotInvokeItsCapturedAction() throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        var actions = 0
        presenter.present(F277CardTestSupport.prompt(), onAction: { _ in actions += 1 })
        let (view, _) = try F277CardTestSupport.fitted(presenter)
        let oldButton = try XCTUnwrap(F277CardTestSupport.actions(view).first { $0.title == "Записать" })
        presenter.dismiss()
        oldButton.performClick(nil)
        presenter.refresh()
        XCTAssertEqual(actions, 0)
        XCTAssertNil(presenter.presentedContent)
    }

    func testExpiryClearsBeforeCallbackAndDoesNotDismissReplacement() async throws {
        try F277CardTestSupport.requireScreen()
        for remember in [false, true] {
            let presenter = DesktopNotificationCardPresenter()
            defer { presenter.dismiss() }
            var expired = 0
            let next = DesktopNotificationCardContent.preview(title: "Следующее", message: "Сообщение")
            presenter.present(F277CardTestSupport.prompt(remember: remember),
                              dismissAfter: Date().addingTimeInterval(0.02),
                              onAction: { _ in XCTFail("Expiry не является явным start/skip") },
                              onExpire: {
                                  expired += 1
                                  XCTAssertFalse(presenter.isVisible)
                                  XCTAssertNil(presenter.presentedContent)
                                  presenter.present(next, onAction: { _ in })
                              }, onClose: { XCTFail("Expiry не является close") })
            try await Task.sleep(for: .milliseconds(60))
            presenter.refresh()
            presenter.refresh()
            XCTAssertEqual(expired, 1)
            XCTAssertEqual(presenter.presentedContent, next)
        }
    }

    func testTickAndCheckboxContentRefreshCannotExtendOriginalDeadline() async throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        var expired = 0
        var remember = false
        presenter.present(F277CardTestSupport.prompt(), dismissAfter: Date().addingTimeInterval(0.02),
                          onAction: { _ in },
                          onTick: { F277CardTestSupport.prompt(seconds: 7, remember: remember) },
                          onExpire: { expired += 1 })
        remember = true
        presenter.refresh()
        try await Task.sleep(for: .milliseconds(60))
        presenter.refresh()
        XCTAssertEqual(expired, 1)
        XCTAssertFalse(presenter.isVisible)
    }

    func testDismissBeforeDeadlinePreventsLateExpiry() async throws {
        try F277CardTestSupport.requireScreen()
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        var expired = 0
        presenter.present(F277CardTestSupport.prompt(), dismissAfter: Date().addingTimeInterval(0.02),
                          onAction: { _ in XCTFail("Отменённый вопрос не выполняет действие") },
                          onExpire: { expired += 1 })
        presenter.dismiss()
        try await Task.sleep(for: .milliseconds(60))
        presenter.refresh()
        XCTAssertEqual(expired, 0)
        XCTAssertFalse(presenter.isVisible)
    }
}
