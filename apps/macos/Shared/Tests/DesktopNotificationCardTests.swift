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
        XCTAssertEqual(DesktopNotificationCardContent.recording(elapsed: "1:05").accessibilitySummary,
                       "Идёт запись. Длительность 1:05.")
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

    func testIndicatorStatesCarryElapsedAndTruthfulTitle() {
        XCTAssertEqual(DesktopRecordingIndicatorState.recording(elapsed: "0:42").title, "Идёт запись")
        XCTAssertEqual(DesktopRecordingIndicatorState.transcribing(elapsed: "0:42").title, "Идёт расшифровка")
        XCTAssertTrue(DesktopRecordingIndicatorState.recording(elapsed: "0:42").isRecording)
        XCTAssertFalse(DesktopRecordingIndicatorState.transcribing(elapsed: "0:42").isRecording)
        XCTAssertEqual(DesktopRecordingIndicatorState.recording(elapsed: "0:42").elapsed, "0:42")
    }

    // Карточка не должна забирать клавиатурный фокус у приложения со встречей.
    func testCardPanelNeverBecomesKeyWindow() {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.recording(elapsed: "0:10"), onAction: { _ in })
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
        presenter.present(.recording(elapsed: "0:10"), onAction: { _ in })
        XCTAssertNotNil(presenter.presentedContent)
        presenter.dismiss()
        XCTAssertFalse(presenter.isVisible)
        XCTAssertNil(presenter.presentedContent)
    }

    func testPositionKeepsCardInsideVisibleFrameBelowMenuBar() {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.recording(elapsed: "0:10"), onAction: { _ in })
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
        presenter.present(.recording(elapsed: "0:10"),
                          dismissAfter: Date().addingTimeInterval(60),
                          onAction: { _ in },
                          onTick: {
                              ticks += 1
                              return .recording(elapsed: "0:11")
                          })
        defer { presenter.dismiss() }
        presenter.refresh()
        XCTAssertEqual(presenter.presentedContent, .recording(elapsed: "0:11"))
        XCTAssertEqual(ticks, 1)
    }

    // Геометрия карточки измеряется на настоящем окне: ширина, поля, радиусы и
    // высота кнопок совпадают с наблюдаемым эталоном.
    func testMeetingCardGeometryMatchesReference() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.meeting(title: "Встреча команды", startText: "Начало в 10:00", hasJoinLink: true),
                          onAction: { _ in })
        defer { presenter.dismiss() }
        let panel = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(panel.contentView)
        panel.setContentSize(NSSize(width: DesktopNotificationCardPresenter.windowWidth, height: 132))
        view.layoutSubtreeIfNeeded()
        view.displayIfNeeded()

        let card = try XCTUnwrap(view.subviews.compactMap { $0 as? CardBackgroundView }.first)
        card.layoutSubtreeIfNeeded()
        XCTAssertEqual(view.frame.width, DesktopNotificationCardPresenter.windowWidth)
        XCTAssertEqual(card.frame.width, DesktopNotificationCardPresenter.cardWidth)
        XCTAssertEqual(card.frame.minX, DesktopNotificationCardPresenter.horizontalMargin)
        XCTAssertEqual(card.frame.minY, DesktopNotificationCardPresenter.bottomPadding)
        XCTAssertEqual(card.layer?.cornerRadius, DesktopNotificationCardPresenter.cornerRadius)

        let buttons = descendants(of: view).compactMap { $0 as? NotificationCardButton }
        XCTAssertEqual(buttons.filter { $0.isPrimary }.count, 1, "в карточке ровно одно главное действие")
        for button in buttons {
            XCTAssertGreaterThanOrEqual(button.frame.height, 40)
            XCTAssertEqual(button.layer?.cornerRadius, 10)
            XCTAssertFalse(button.isBordered)
        }
        XCTAssertTrue(buttons.contains { $0.isPrimary })

        // Действия не выходят за карточку и стоят ниже строки заголовка.
        let stacks = card.subviews.compactMap { $0 as? NSStackView }
        XCTAssertEqual(stacks.count, 2, "строка заголовка и строка действий")
        let header = try XCTUnwrap(stacks.first { stack in
            descendants(of: stack).contains { ($0 as? NSTextField)?.stringValue == "Встреча команды" }
        })
        let actions = try XCTUnwrap(stacks.first { $0 !== header })
        print("ORDER", "header", header.frame, "actions", actions.frame)
        XCTAssertLessThanOrEqual(actions.frame.maxY, header.frame.minY)
        for button in buttons {
            let frame = button.convert(button.bounds, to: view)
            XCTAssertLessThanOrEqual(frame.maxX, card.frame.maxX - 8)
            XCTAssertGreaterThanOrEqual(frame.minX, card.frame.minX + 8)
        }

        let close = try XCTUnwrap(view.subviews.compactMap { $0 as? NSButton }.first { $0.accessibilityLabel() == "Закрыть уведомление" })
        XCTAssertLessThanOrEqual(close.frame.width, 24)
        XCTAssertLessThanOrEqual(close.frame.height, 24)
        XCTAssertEqual(close.frame.midX, card.frame.maxX - 14, accuracy: 3)
        XCTAssertEqual(close.frame.midY, card.frame.maxY - 14, accuracy: 3)
    }

    func testIndicatorCardKeepsSingleRowGeometry() throws {
        let presenter = DesktopNotificationCardPresenter()
        presenter.present(.recording(elapsed: "0:42"), onAction: { _ in })
        defer { presenter.dismiss() }
        let panel = try XCTUnwrap(presenter.window)
        let view = try XCTUnwrap(panel.contentView)
        panel.setContentSize(NSSize(width: DesktopNotificationCardPresenter.windowWidth, height: 104))
        view.layoutSubtreeIfNeeded()
        view.displayIfNeeded()
        let card = try XCTUnwrap(view.subviews.compactMap { $0 as? CardBackgroundView }.first)
        card.layoutSubtreeIfNeeded()
        XCTAssertEqual(card.frame.width, DesktopNotificationCardPresenter.cardWidth)
        // Индикатор занимает одну строку и ниже карточки встречи.
        XCTAssertEqual(card.frame.height, 64, accuracy: 1, "индикатор записи — одна строка")
        XCTAssertLessThan(card.frame.height, 110, "индикатор записи ниже карточки встречи")
    }

    // Индикатор обновляет длительность сам, не дожидаясь смены состояния записи.
    func testIndicatorTicksElapsedTimeWithoutStateChange() async throws {
        let indicator = DesktopRecordingIndicatorPresenter()
        defer { indicator.hide() }
        var elapsed = "0:01"
        indicator.show(.recording(elapsed: elapsed),
                       onStop: {},
                       onOpen: {},
                       onRefresh: { .recording(elapsed: elapsed) })
        XCTAssertEqual(indicator.presentedState, .recording(elapsed: "0:01"))
        elapsed = "0:03"
        try await Task.sleep(for: .seconds(2.2))
        XCTAssertEqual(indicator.presentedState, .recording(elapsed: "0:03"))
    }

    func testIndicatorWithoutRefreshStaysOnGivenState() {
        let indicator = DesktopRecordingIndicatorPresenter()
        defer { indicator.hide() }
        indicator.show(.transcribing(elapsed: "0:20"), onStop: {}, onOpen: nil)
        XCTAssertEqual(indicator.presentedState, .transcribing(elapsed: "0:20"))
        XCTAssertTrue(indicator.isVisible)
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
        XCTAssertFalse(harness.presenter.indicator.isVisible)
    }

    func testPresenterIgnoresDistantMeeting() async throws {
        let harness = CardHarness()
        defer { harness.finish() }
        await harness.updateCalendar([harness.event(startsIn: 40 * 60)])
        XCTAssertFalse(harness.presenter.card.isVisible)
    }

    func testPresenterShowsRecordingIndicatorWhileRecording() {
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
        XCTAssertEqual(harness.presenter.indicator.presentedState, .recording(elapsed: "0:05"))

        snapshot.stopping = true
        harness.presenter.updateRecordingIndicator(snapshot, elapsed: "0:05")
        XCTAssertEqual(harness.presenter.indicator.presentedState, .transcribing(elapsed: "0:05"))

        harness.presenter.updateRecordingIndicator(DesktopControlSnapshot(), elapsed: "0:05")
        XCTAssertFalse(harness.presenter.indicator.isVisible)
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
