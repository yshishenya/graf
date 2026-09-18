import AppKit
import Foundation
import UserNotifications
import XCTest
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

@MainActor
final class DesktopNotificationCardTests: XCTestCase {
    private func event(startsIn offset: TimeInterval,
                       duration: TimeInterval = 1_800,
                       link: String? = "https://example.test/meeting",
                       title: String = "Встреча команды") -> DesktopCalendarPromptEvent {
        let now = Date()
        var value = DesktopCalendarPromptEvent(
            eventId: "event-\(offset)",
            startsAt: now.addingTimeInterval(offset),
            endsAt: now.addingTimeInterval(offset + duration),
            title: title,
            titleState: .available,
            meetingLinkPresent: link != nil,
            joinPromptState: .notDue,
            recordPromptState: .notDue,
            openMeetingURL: link.flatMap(URL.init(string:))
        )
        value.joinPromptDueAt = value.startsAt.addingTimeInterval(-900)
        return value
    }

    // Наблюдаемый эталон: карточка показывается за 15 минут и держится до
    // начала встречи, но не дольше 120 секунд показа.
    func testCardWindowMatchesObservedReference() {
        let now = Date()
        let far = event(startsIn: 40 * 60)
        XCTAssertFalse(DesktopNotificationPresenter.shouldPresentCard(far, snapshot: .init(), now: now))

        let inside = event(startsIn: 10 * 60)
        XCTAssertTrue(DesktopNotificationPresenter.shouldPresentCard(inside, snapshot: .init(), now: now))

        let justStarted = event(startsIn: -30)
        XCTAssertTrue(DesktopNotificationPresenter.shouldPresentCard(justStarted, snapshot: .init(), now: now))

        let past = event(startsIn: -180)
        XCTAssertFalse(DesktopNotificationPresenter.shouldPresentCard(past, snapshot: .init(), now: now))
    }

    func testCardNeverOffersRecordingDuringActiveMeeting() {
        var snapshot = DesktopControlSnapshot()
        snapshot.session = CaptureSession(
            id: "active", mode: .audioRecording, state: .active,
            sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
            visibleIndicatorState: .active, stopActionAvailable: true,
            bufferSummaryId: nil, startedAt: Date(), stoppedAt: nil
        )
        let running = event(startsIn: 5 * 60)
        snapshot.calendarContextEventID = running.eventId
        XCTAssertFalse(DesktopNotificationPresenter.shouldPresentCard(running, snapshot: snapshot, now: Date()))
    }

    func testMeetingCardContentFollowsTitlePreferenceAndLink() {
        let linked = event(startsIn: 5 * 60)
        var preferences = DesktopNotificationPreferences()
        XCTAssertEqual(DesktopNotificationPresenter.meetingCardContent(event: linked, preferences: preferences),
                       .meeting(title: "Встреча в календаре", startText: startText(linked), hasJoinLink: true))
        preferences.showTitles = true
        XCTAssertEqual(DesktopNotificationPresenter.meetingCardContent(event: linked, preferences: preferences),
                       .meeting(title: "Встреча команды", startText: startText(linked), hasJoinLink: true))

        let withoutLink = event(startsIn: 5 * 60, link: nil)
        XCTAssertEqual(DesktopNotificationPresenter.meetingCardContent(event: withoutLink, preferences: preferences),
                       .meeting(title: "Встреча команды", startText: startText(withoutLink), hasJoinLink: false))
    }

    // Опасная схема ссылки не даёт кнопки подключения.
    func testUnsafeMeetingLinkIsNotOffered() {
        let unsafe = event(startsIn: 5 * 60, link: "http://example.test/meeting")
        let content = DesktopNotificationPresenter.meetingCardContent(event: unsafe, preferences: .init())
        XCTAssertEqual(content, .meeting(title: "Встреча в календаре",
                                        startText: startText(unsafe), hasJoinLink: false))
    }

    func testCardContentIsAccessibleAndIdentified() {
        let meeting = DesktopNotificationCardContent.meeting(title: "Встреча команды",
                                                             startText: "Начало в 10:00",
                                                             hasJoinLink: true)
        XCTAssertTrue(meeting.accessibilitySummary.contains("Встреча команды"))
        XCTAssertTrue(meeting.accessibilitySummary.contains("10:00"))
        XCTAssertEqual(meeting.identifier, "graf.card.meeting")
        XCTAssertEqual(DesktopNotificationCardContent.notice(title: "Запись началась",
                                                             message: "Остановить запись можно в строке меню",
                                                             actionTitle: nil).accessibilitySummary,
                       "Запись началась. Остановить запись можно в строке меню.")
        XCTAssertEqual(DesktopNotificationCardContent.notice(title: "Проверка",
                                                             message: "Так выглядит напоминание",
                                                             actionTitle: "Открыть").accessibilitySummary,
                       "Проверка. Так выглядит напоминание. Действие: Открыть.")
    }

    func testDismissalKeyIsStablePerOccurrence() {
        let first = event(startsIn: 5 * 60)
        var moved = first
        moved.startsAt = first.startsAt.addingTimeInterval(600)
        XCTAssertEqual(DesktopNotificationPresenter.cardDismissalKey(first, context: "owner"),
                       DesktopNotificationPresenter.cardDismissalKey(moved, context: "owner"))
        XCTAssertNotEqual(DesktopNotificationPresenter.cardDismissalKey(first, context: "owner"),
                          DesktopNotificationPresenter.cardDismissalKey(first, context: "other"))
    }

    // Состояние записи сообщается один раз на переход, отдельного окна нет.
    func testRecordingNoticeStatesCarryTruthfulText() {
        var recording = DesktopControlSnapshot()
        recording.session = CaptureSession(
            id: "active", mode: .audioRecording, state: .active,
            sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
            visibleIndicatorState: .active, stopActionAvailable: true,
            bufferSummaryId: nil, startedAt: Date(), stoppedAt: nil
        )
        XCTAssertEqual(DesktopNotificationPresenter.RecordingNoticeState(snapshot: recording), .recording)
        var stopping = recording
        stopping.stopping = true
        XCTAssertEqual(DesktopNotificationPresenter.RecordingNoticeState(snapshot: stopping), .transcribing)
        XCTAssertEqual(DesktopNotificationPresenter.RecordingNoticeState(snapshot: recording)?.title,
                       "Запись началась")
        XCTAssertEqual(DesktopNotificationPresenter.RecordingNoticeState(snapshot: stopping)?.title,
                       "Расшифровка началась")
        XCTAssertNil(DesktopNotificationPresenter.RecordingNoticeState(snapshot: DesktopControlSnapshot()))
    }

    // Карточка не должна забирать клавиатурный фокус у приложения со встречей.
    func testCardPanelNeverBecomesKeyWindow() {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.notice(title: "Запись началась",
                                  message: "Остановить запись можно в строке меню.",
                                  actionTitle: nil), onAction: { _ in })
        defer { presenter.dismiss() }
        XCTAssertTrue(presenter.isVisible)
        let panel = presenter.window
        XCTAssertNotNil(panel)
        XCTAssertFalse(panel?.canBecomeKey ?? true)
        XCTAssertFalse(panel?.canBecomeMain ?? true)
        XCTAssertEqual(panel?.level, .statusBar)
        XCTAssertTrue(panel?.collectionBehavior.contains(.canJoinAllSpaces) ?? false)
        XCTAssertEqual(panel?.frame.width, DesktopNotificationCardPresenter.windowWidth)
    }

    func testDismissRemovesCardAndContent() {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.notice(title: "Запись началась",
                                  message: "Остановить запись можно в строке меню.",
                                  actionTitle: nil), onAction: { _ in })
        XCTAssertNotNil(presenter.presentedContent)
        presenter.dismiss()
        XCTAssertFalse(presenter.isVisible)
        XCTAssertNil(presenter.presentedContent)
    }

    func testPositionKeepsCardInsideVisibleFrameBelowMenuBar() {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.notice(title: "Запись началась",
                                  message: "Остановить запись можно в строке меню.",
                                  actionTitle: nil), onAction: { _ in })
        defer { presenter.dismiss() }
        guard let panel = presenter.window,
              let screen = panel.screen ?? NSScreen.main else { return XCTFail("нет окна карточки") }
        let visible = screen.visibleFrame
        XCTAssertGreaterThanOrEqual(panel.frame.minX, visible.minX)
        XCTAssertLessThanOrEqual(panel.frame.maxX, visible.maxX)
        XCTAssertLessThanOrEqual(panel.frame.maxY, visible.maxY)
        XCTAssertGreaterThanOrEqual(panel.frame.minY, visible.minY)
    }

    func testRefreshKeepsCardWhileContentIsCurrent() {
        let presenter = DesktopNotificationCardPresenter()
        var ticks = 0
        presenter.present(.notice(title: "Запись началась",
                                  message: "Остановить запись можно в строке меню.",
                                  actionTitle: nil),
                          dismissAfter: Date().addingTimeInterval(60),
                          onAction: { _ in },
                          onTick: {
                              ticks += 1
                              return .notice(title: "Запись началась",
                                             message: "Остановить запись можно в строке меню.",
                                             actionTitle: nil)
                          })
        defer { presenter.dismiss() }
        presenter.refresh()
        XCTAssertEqual(presenter.presentedContent, .notice(title: "Запись началась",
                                                            message: "Остановить запись можно в строке меню.",
                                                            actionTitle: nil))
        XCTAssertEqual(ticks, 1)
    }

    // Геометрия карточки измеряется на настоящем окне и совпадает с наблюдаемым
    // эталоном: 420 точек внутри окна 448, высота 82, поля 10, радиус 16.
    func testCardWithOneActionMatchesReferenceGeometry() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.meeting(title: "Встреча команды", startText: "Начало в 10:00", hasJoinLink: false),
                          onAction: { _ in })
        defer { presenter.dismiss() }
        let (panel, view) = try fitted(presenter)
        let card = try XCTUnwrap(view.subviews.compactMap { $0 as? CardBackgroundView }.first)
        card.layoutSubtreeIfNeeded()

        XCTAssertEqual(view.frame.width, DesktopNotificationCardPresenter.windowWidth)
        XCTAssertEqual(view.frame.height, DesktopNotificationCardPresenter.windowHeight, accuracy: 1)
        XCTAssertEqual(card.frame.width, DesktopNotificationCardPresenter.cardWidth)
        XCTAssertEqual(card.frame.height, DesktopNotificationCardPresenter.cardHeight, accuracy: 1)
        XCTAssertEqual(card.frame.minX, DesktopNotificationCardPresenter.horizontalMargin)
        XCTAssertEqual(card.frame.minY, DesktopNotificationCardPresenter.bottomPadding, accuracy: 1)
        XCTAssertEqual(card.layer?.cornerRadius, DesktopNotificationCardPresenter.cornerRadius)

        let buttons = descendants(of: view).compactMap { $0 as? NotificationCardButton }
        XCTAssertEqual(buttons.count, 1, "одно действие в карточке без ссылки")
        for button in buttons {
            XCTAssertGreaterThanOrEqual(button.frame.height, DesktopNotificationCardPresenter.buttonHeight)
            XCTAssertEqual(button.layer?.cornerRadius, 10)
            XCTAssertFalse(button.isBordered)
        }

        // Одна строка: значок, текст и действие.
        let stacks = card.subviews.compactMap { $0 as? NSStackView }
        XCTAssertEqual(stacks.count, 1, "карточка с одним действием собрана в одну строку")
        let row = try XCTUnwrap(stacks.first)
        XCTAssertEqual(row.frame.midY, card.frame.height / 2, accuracy: 1)
        let title = try XCTUnwrap(descendants(of: row).compactMap { $0 as? NSTextField }
            .first { $0.stringValue == "Встреча команды" })
        let buttonFrame = try XCTUnwrap(buttons.first).convert(buttons[0].bounds, to: card)
        XCTAssertGreaterThan(buttonFrame.minX, title.convert(title.bounds, to: card).maxX)
        XCTAssertLessThanOrEqual(buttonFrame.maxX, card.frame.width - 20)

        let close = try XCTUnwrap(view.subviews.compactMap { $0 as? NSButton }
            .first { $0.accessibilityLabel() == "Закрыть уведомление" })
        XCTAssertLessThanOrEqual(close.frame.width, 28)
        XCTAssertLessThanOrEqual(close.frame.height, 28)
        // Знак закрытия стоит в верхнем правом углу карточки.
        XCTAssertEqual(close.frame.midX, card.frame.maxX - 24, accuracy: 3)
        XCTAssertEqual(close.frame.midY, card.frame.maxY - 22, accuracy: 4)
        _ = panel
    }

    // Двум действиям нужна отдельная строка: подписи эталона длиннее латинских.
    func testCardWithTwoActionsKeepsBothActionsInsideCard() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.meeting(title: "Встреча команды", startText: "Начало в 10:00", hasJoinLink: true),
                          onAction: { _ in })
        defer { presenter.dismiss() }
        let (_, view) = try fitted(presenter)
        let card = try XCTUnwrap(view.subviews.compactMap { $0 as? CardBackgroundView }.first)
        card.layoutSubtreeIfNeeded()

        XCTAssertEqual(card.frame.width, DesktopNotificationCardPresenter.cardWidth)
        XCTAssertGreaterThan(card.frame.height, DesktopNotificationCardPresenter.cardHeight,
                             "двум действиям нужна вторая строка")
        let buttons = descendants(of: view).compactMap { $0 as? NotificationCardButton }
        XCTAssertEqual(buttons.count, 2)
        XCTAssertEqual(buttons.filter { $0.isPrimary }.count, 1)
        for button in buttons {
            let frame = button.convert(button.bounds, to: card)
            XCTAssertGreaterThanOrEqual(frame.minX, 8)
            XCTAssertLessThanOrEqual(frame.maxX, card.frame.width - 8)
            XCTAssertGreaterThanOrEqual(frame.height, DesktopNotificationCardPresenter.buttonHeight)
        }
    }

    // Карточка показывается поверх других окон и на всех рабочих столах, но не
    // забирает клавиатурный фокус.
    func testCardWindowFloatsAboveOtherWindowsWithoutFocus() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.meeting(title: "Встреча команды", startText: "Начало в 10:00", hasJoinLink: true),
                          onAction: { _ in })
        defer { presenter.dismiss() }
        let panel = try XCTUnwrap(presenter.window)
        XCTAssertEqual(panel.level, .statusBar)
        XCTAssertTrue(panel.collectionBehavior.contains(.canJoinAllSpaces))
        XCTAssertTrue(panel.collectionBehavior.contains(.fullScreenAuxiliary))
        XCTAssertFalse(panel.canBecomeKey)
        XCTAssertFalse(panel.isOpaque)
        XCTAssertFalse(panel.hasShadow)
        XCTAssertTrue(panel.styleMask.contains(.nonactivatingPanel))
    }

    // Положение: правый край рабочей области без отступа, верх ниже строки меню.
    func testCardPositionKeepsRightEdgeAndMenuBarInset() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.meeting(title: "Встреча команды", startText: "Начало в 10:00", hasJoinLink: true),
                          onAction: { _ in })
        defer { presenter.dismiss() }
        let panel = try XCTUnwrap(presenter.window)
        let screen = try XCTUnwrap(panel.screen ?? NSScreen.main)
        let visible = screen.visibleFrame
        XCTAssertEqual(panel.frame.maxX, visible.maxX, accuracy: 1)
        XCTAssertEqual(visible.maxY - panel.frame.maxY, DesktopNotificationCardPresenter.topInset, accuracy: 1.5)
    }

    private func fitted(_ presenter: DesktopNotificationCardPresenter) throws -> (NSWindow, NSView) {
        let panel = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(panel.contentView)
        for _ in 0..<3 {
            view.layoutSubtreeIfNeeded()
            panel.setContentSize(NSSize(width: DesktopNotificationCardPresenter.windowWidth,
                                        height: view.fittingSize.height))
        }
        view.layoutSubtreeIfNeeded()
        view.displayIfNeeded()
        return (panel, view)
    }

    // Служебное сообщение показывается одной строкой: текст и знак закрытия.
    func testNoticeCardKeepsSingleRowGeometry() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.presentNotice(title: "Запись началась",
                                message: "Остановить запись можно в строке меню.")
        defer { presenter.dismiss() }
        let panel = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(panel.contentView)
        panel.setContentSize(NSSize(width: DesktopNotificationCardPresenter.windowWidth,
                                    height: DesktopNotificationCardPresenter.windowHeight))
        view.layoutSubtreeIfNeeded()
        view.displayIfNeeded()
        let card = try XCTUnwrap(view.subviews.compactMap { $0 as? CardBackgroundView }.first)
        card.layoutSubtreeIfNeeded()
        XCTAssertEqual(card.frame.width, DesktopNotificationCardPresenter.cardWidth)
        XCTAssertEqual(card.frame.height, DesktopNotificationCardPresenter.cardHeight, accuracy: 1)
        XCTAssertEqual(card.subviews.compactMap { $0 as? NSStackView }.count, 1)
    }


    // Согласователь карточки: показ, закрытие и отсутствие дублирования баннером.
    func testPresenterShowsCardForUpcomingMeetingAndSuppressesBanner() async throws {
        let harness = CardHarness()
        defer { harness.finish() }
        let event = harness.event(startsIn: 10 * 60)
        await harness.updateCalendar([event])
        XCTAssertEqual(harness.presenter.card.presentedContent,
                       .meeting(title: "Встреча команды", startText: harness.startText(event), hasJoinLink: true))
        XCTAssertTrue(harness.presenter.card.isVisible)

        // Карточка видна: системный баннер не дублирует событие.
        XCTAssertTrue(harness.presenter.presentationOptions(for: harness.reminderID(event)).isEmpty)
    }

    func testPresenterDoesNotRestoreDismissedCardAndKeepsBannerFallback() async throws {
        let harness = CardHarness()
        defer { harness.finish() }
        let event = harness.event(startsIn: 10 * 60)
        await harness.updateCalendar([event])
        let id = harness.reminderID(event)
        harness.presenter.dismissCard(eventID: event.eventId)
        XCTAssertFalse(harness.presenter.card.isVisible)
        // Карточка закрыта: баннер остаётся резервным напоминанием.
        XCTAssertFalse(harness.presenter.presentationOptions(for: id).isEmpty)

        await harness.updateCalendar([event])
        XCTAssertFalse(harness.presenter.card.isVisible, "закрытая карточка не возвращается")
    }

    func testPresenterHidesCardWhenRemindersAreTurnedOff() async throws {
        let harness = CardHarness()
        defer { harness.finish() }
        await harness.updateCalendar([harness.event(startsIn: 10 * 60)])
        XCTAssertTrue(harness.presenter.card.isVisible)
        harness.presenter.draft.reminders = false
        _ = harness.presenter.save(harness.presenter.draft)
        XCTAssertFalse(harness.presenter.card.isVisible)
    }

    func testPresenterHidesCardOnSignOut() async throws {
        let harness = CardHarness()
        defer { harness.finish() }
        await harness.updateCalendar([harness.event(startsIn: 10 * 60)])
        XCTAssertTrue(harness.presenter.card.isVisible)
        harness.presenter.invalidate()
        XCTAssertFalse(harness.presenter.card.isVisible)
    }

    func testPresenterIgnoresDistantMeeting() async throws {
        let harness = CardHarness()
        defer { harness.finish() }
        await harness.updateCalendar([harness.event(startsIn: 40 * 60)])
        XCTAssertFalse(harness.presenter.card.isVisible)
    }

    // Состояние записи сообщается один раз на переход: «Запись началась»,
    // затем «Расшифровка началась», затем «Запись остановлена». Постоянного
    // окна поверх других окон нет.
    func testPresenterAnnouncesRecordingStatesOncePerTransition() {
        let harness = CardHarness()
        defer { harness.finish() }
        var snapshot = DesktopControlSnapshot()
        snapshot.session = CaptureSession(
            id: "active", mode: .audioRecording, state: .active,
            sourceAppEligibility: .eligible, policySnapshotRef: "policy", triggerEvidence: [:],
            visibleIndicatorState: .active, stopActionAvailable: true,
            bufferSummaryId: nil, startedAt: Date(), stoppedAt: nil
        )
        harness.presenter.updateRecordingIndicator(snapshot, elapsed: "0:05")
        XCTAssertEqual(harness.presenter.card.presentedContent,
                       .notice(title: "Запись началась",
                               message: "Остановить запись можно в строке меню.",
                               actionTitle: nil))

        // Повторное то же состояние ничего не показывает заново.
        harness.presenter.card.dismiss()
        harness.presenter.updateRecordingIndicator(snapshot, elapsed: "0:07")
        XCTAssertFalse(harness.presenter.card.isVisible)

        snapshot.stopping = true
        harness.presenter.updateRecordingIndicator(snapshot, elapsed: "0:07")
        XCTAssertEqual(harness.presenter.card.presentedContent,
                       .notice(title: "Расшифровка началась",
                               message: "Запись сохраняется и уходит на расшифровку.",
                               actionTitle: nil))

        snapshot.stopping = false
        snapshot.session?.state = .stopped
        harness.presenter.updateRecordingIndicator(snapshot, elapsed: "0:07")
        XCTAssertEqual(harness.presenter.card.presentedContent,
                       .notice(title: "Запись остановлена",
                               message: "Запись сохранена на этом Mac.",
                               actionTitle: nil))
    }

    // Карточку можно закрыть мышью: окно принимает нажатия, а точка знака
    // закрытия действительно приходится на кнопку.
    func testCardCloseButtonReceivesMouseClicks() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.presentNotice(title: "Проверка уведомлений GRAF",
                                message: "Так выглядит напоминание о встрече.")
        defer { presenter.dismiss() }
        let panel = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(panel.contentView)
        view.layoutSubtreeIfNeeded()
        XCTAssertFalse(panel.ignoresMouseEvents, "окно карточки не должно пропускать нажатия")
        let close = try XCTUnwrap(view.subviews.compactMap { $0 as? NSButton }
            .first { $0.accessibilityLabel() == "Закрыть уведомление" })
        let inWindow = close.convert(close.bounds, to: nil)
        let point = NSPoint(x: inWindow.midX, y: inWindow.midY)
        let hit = view.hitTest(view.convert(point, from: nil))
        XCTAssertTrue(hit === close, "нажатие в углу карточки должно попадать в знак закрытия")
        // Нажатие закрывает карточку и убирает окно.
        close.performClick(nil)
        XCTAssertFalse(presenter.isVisible)
    }

    // Сторож нажатий закрывает карточку по нажатию в знак закрытия и не
    // трогает нажатия мимо него.
    func testClickMonitorClosesCardOnlyOnTheCloseControl() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.presentNotice(title: "Проверка уведомлений GRAF",
                                message: "Так выглядит напоминание о встрече.")
        let panel = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(panel.contentView as? DesktopNotificationCardView)
        let close = try XCTUnwrap(view.closeButton)
        let inWindow = close.convert(close.bounds, to: nil)
        // Нажатие мимо знака закрытия карточку не закрывает.
        XCTAssertFalse(presenter.handleCardClick(at: NSPoint(x: inWindow.minX - 120, y: inWindow.midY)))
        XCTAssertTrue(presenter.isVisible)
        // Нажатие в знак закрытия закрывает карточку и убирает окно.
        XCTAssertTrue(presenter.handleCardClick(at: NSPoint(x: inWindow.midX, y: inWindow.midY)))
        XCTAssertFalse(presenter.isVisible)
        XCTAssertNil(presenter.window)
    }

    // Сторож нажатий получает настоящее событие мыши этого окна: синтетическое
    // событие с номером окна карточки он обязан закрыть карточку и не пропустить
    // событие дальше.
    func testClickMonitorHandlesSyntheticMouseDown() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.presentNotice(title: "Проверка уведомлений GRAF",
                                message: "Так выглядит напоминание о встрече.")
        let panel = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(panel.contentView as? DesktopNotificationCardView)
        let close = try XCTUnwrap(view.closeButton)
        let inWindow = close.convert(close.bounds, to: nil)
        let point = NSPoint(x: inWindow.midX, y: inWindow.midY)
        let event = try XCTUnwrap(NSEvent.mouseEvent(with: .leftMouseDown,
                                                    location: point,
                                                    modifierFlags: [],
                                                    timestamp: ProcessInfo.processInfo.systemUptime,
                                                    windowNumber: panel.windowNumber,
                                                    context: nil,
                                                    eventNumber: 0,
                                                    clickCount: 1,
                                                    pressure: 1))
        XCTAssertTrue(event.window === panel, "событие должно принадлежать окну карточки")
        XCTAssertTrue(presenter.handleCardClick(at: event.locationInWindow),
                      "сторож обязан принять нажатие в знак закрытия")
        XCTAssertFalse(presenter.isVisible, "нажатие в знак закрытия убирает карточку")
    }

    // Приложение может быть неактивным. Пока GRAF не впереди, система отдаёт
    // первое нажатие активации, поэтому окно нажатие не получает: карточку
    // закрывает сторож нажатий. Здесь проверяется, что окно нажатия принимает,
    // фокус не забирает и знак закрытия доступен сторожу.
    func testCardWindowAcceptsClicksWhileAppIsInactive() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.presentNotice(title: "Проверка уведомлений GRAF",
                                message: "Так выглядит напоминание о встрече.")
        defer { presenter.dismiss() }
        let panel = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(panel.contentView as? DesktopNotificationCardView)
        XCTAssertFalse(panel.ignoresMouseEvents)
        XCTAssertFalse(panel.canBecomeMain, "карточка не забирает главное окно")
        XCTAssertFalse(panel.hidesOnDeactivate)
        XCTAssertTrue(panel.styleMask.contains(.nonactivatingPanel))
        XCTAssertFalse(panel.isKeyWindow, "карточка не забирает клавиатурный фокус")
        let close = try XCTUnwrap(view.closeButton)
        let inWindow = close.convert(close.bounds, to: nil)
        let hit = view.hitTest(view.convert(NSPoint(x: inWindow.midX, y: inWindow.midY), from: nil))
        XCTAssertTrue(hit === close, "сторож нажатий должен находить знак закрытия")
    }

    // Сообщение исчезает само: иначе окно остаётся поверх чужих приложений.
    func testNoticeDisappearsAfterItsLifetime() async throws {
        let presenter = DesktopNotificationCardPresenter()
        defer { presenter.dismiss() }
        presenter.presentNotice(title: "Запись началась",
                                message: "Остановить запись можно в строке меню.",
                                duration: 1)
        XCTAssertTrue(presenter.isVisible)
        try await Task.sleep(for: .seconds(3))
        XCTAssertFalse(presenter.isVisible, "сообщение обязано исчезнуть само")
        XCTAssertNil(presenter.presentedContent)
    }

    // Снимок поверхности для ручной сверки с эталоном. Пишется только когда
    // задан GRAF_CARD_SNAPSHOT_DIR: обычный прогон тестов ничего не сохраняет.
    func testCardSurfacesCanBeCapturedForReferenceComparison() throws {
        guard let directory = ProcessInfo.processInfo.environment["GRAF_CARD_SNAPSHOT_DIR"], !directory.isEmpty else {
            throw XCTSkip("снимок не запрашивался")
        }
        let target = URL(fileURLWithPath: directory, isDirectory: true)
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)

        let card = DesktopNotificationCardPresenter()
        defer { card.dismiss() }
        card.present(.meeting(title: "Встреча команды", startText: "Начало в 14:30", hasJoinLink: true), onAction: { _ in })
        try write(card.window, to: target.appendingPathComponent("card-meeting.png"))

        card.present(.meeting(title: "Встреча в календаре", startText: "Начало в 14:30", hasJoinLink: false), onAction: { _ in })
        try write(card.window, to: target.appendingPathComponent("card-meeting-no-link.png"))

        card.present(.problem(title: "Запись требует вашего внимания",
                              message: "Откройте запись в GRAF, чтобы проверить ее сохранность и отправку.",
                              actionTitle: "Открыть запись",
                              sessionID: "session"), onAction: { _ in })
        try write(card.window, to: target.appendingPathComponent("card-problem.png"))

        card.presentNotice(title: "Запись началась",
                           message: "Остановить запись можно в строке меню.")
        try write(card.window, to: target.appendingPathComponent("notice-recording.png"))
        card.presentNotice(title: "Запись не сохранена",
                           message: "Запись короче 30 секунд не сохранена.")
        try write(card.window, to: target.appendingPathComponent("notice-short-recording.png"))
        card.dismiss()
    }

    private func write(_ window: NSWindow?, to url: URL) throws {
        let view = try XCTUnwrap(window?.contentView)
        let size = try XCTUnwrap(window?.contentView?.bounds.size)
        view.layoutSubtreeIfNeeded()
        view.displayIfNeeded()
        let representation = try XCTUnwrap(view.bitmapImageRepForCachingDisplay(in: view.bounds))
        view.cacheDisplay(in: view.bounds, to: representation)
        XCTAssertEqual(representation.pixelsWide, Int(size.width * (window?.backingScaleFactor ?? 1)))
        let png = try XCTUnwrap(representation.representation(using: .png, properties: [:]))
        try png.write(to: url)
    }

    private func descendants(of view: NSView) -> [NSView] {
        view.subviews.flatMap { [$0] + descendants(of: $0) }
    }

    private func startText(_ event: DesktopCalendarPromptEvent) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.dateFormat = "HH:mm"
        return "Начало в \(formatter.string(from: event.startsAt))"
    }
}

/// Стенд согласователя: временные настройки, подставной центр уведомлений и
/// календарь без сети.
@MainActor
private final class CardHarness {
    let presenter: DesktopNotificationPresenter
    private let defaults: UserDefaults
    private let name: String
    private(set) var sent: [UNNotificationRequest] = []

    init() {
        name = "graf-card-\(UUID())"
        defaults = UserDefaults(suiteName: name) ?? .standard
        var preferences = DesktopNotificationPreferences()
        preferences.reminders = true
        preferences.showTitles = true
        try? DesktopNotificationPreferencesStore(defaults: defaults).save(preferences, owner: "owner")
        let created = DesktopNotificationPresenter(
            store: .init(defaults: defaults),
            model: DesktopControlModel(),
            status: { .authorized },
            submit: { _ in },
            remove: { _ in },
            requestPermission: { true }
        )
        presenter = created
        presenter.updateContext(user: "owner", workspace: "workspace")
        presenter.draft.reminders = true
        presenter.draft.showTitles = true
        _ = presenter.save(presenter.draft)
    }

    func finish() {
        presenter.invalidate()
        defaults.removePersistentDomain(forName: name)
    }

    func event(startsIn offset: TimeInterval) -> DesktopCalendarPromptEvent {
        var value = DesktopCalendarPromptEvent(
            eventId: "event-\(Int(offset))",
            startsAt: Date().addingTimeInterval(offset),
            endsAt: Date().addingTimeInterval(offset + 1_800),
            title: "Встреча команды",
            titleState: .available,
            meetingLinkPresent: true,
            joinPromptState: .notDue,
            recordPromptState: .notDue,
            openMeetingURL: URL(string: "https://example.test/meeting")
        )
        value.joinPromptDueAt = value.startsAt.addingTimeInterval(-900)
        return value
    }

    func startText(_ event: DesktopCalendarPromptEvent) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.dateFormat = "HH:mm"
        return "Начало в \(formatter.string(from: event.startsAt))"
    }

    func reminderID(_ event: DesktopCalendarPromptEvent) -> String {
        DesktopNotificationPresenter.reminderID(event, context: "owner:workspace")
    }

    func updateCalendar(_ events: [DesktopCalendarPromptEvent]) async {
        var response = DesktopCalendarPromptResponse(events: events, showUpcomingTitle: true)
        response.notificationOwnerID = "owner"
        response.notificationWorkspaceID = "workspace"
        presenter.updateCalendar(response)
        // Планирование напоминаний идёт отдельной задачей: ждём её, чтобы
        // проверять согласованное состояние.
        await presenter.updateSnapshot(DesktopControlSnapshot())?.value
        try? await Task.sleep(for: .milliseconds(60))
    }
}
