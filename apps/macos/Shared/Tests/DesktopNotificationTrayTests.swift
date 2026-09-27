import AppKit
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class DesktopNotificationTrayTests: XCTestCase {
    @MainActor
    func testHistoryUsesOnlyNeutralEntriesAndFocusIsExplicit() throws {
        var entries = (0..<60).map { index in
            DesktopNotificationHistoryEntry(id: UUID(), occurredAt: Date(timeIntervalSince1970: Double(index)), kind: .shortRecording)
        }
        var visible = false
        var focused = 0
        let tray = CalendarTrayController(
            model: CalendarTrayModel { DesktopCalendarPromptResponse(events: []) },
            onOpenSettings: {}, onOpenMeetings: {}, onStartRecording: {}, onStopRecording: {},
            onMuteMicrophone: {}, onUnmuteMicrophone: {}, onQuit: {},
            notificationHistory: { entries }, canFocusNotification: { visible },
            onFocusNotification: { focused += 1 }
        )
        tray.rebuildMenu()
        let focus = try XCTUnwrap(tray.menu.items.first { $0.identifier?.rawValue == "graf.menu.notification-focus" })
        XCTAssertFalse(focus.isEnabled)
        let history = try XCTUnwrap(tray.menu.items.first { $0.identifier?.rawValue == "graf.menu.notification-history" }?.submenu)
        XCTAssertEqual(history.items.count, 50)
        XCTAssertTrue(history.items.allSatisfy { $0.action == nil && $0.representedObject == nil })
        XCTAssertTrue(history.items.allSatisfy { $0.toolTip?.contains("Запись") == true })
        XCTAssertEqual(focused, 0)
        tray.invalidateNotificationHistory()
        XCTAssertTrue(history.items.isEmpty, "An already-open submenu cannot retain the previous context")
        visible = true
        entries = []
        tray.rebuildMenu()
        let index = try XCTUnwrap(tray.menu.items.firstIndex { $0.identifier?.rawValue == "graf.menu.notification-focus" })
        XCTAssertTrue(tray.menu.items[index].isEnabled)
        tray.menu.performActionForItem(at: index)
        XCTAssertEqual(focused, 1)
        let cleared = try XCTUnwrap(tray.menu.items.first { $0.identifier?.rawValue == "graf.menu.notification-history" }?.submenu)
        XCTAssertEqual(cleared.items.map(\.title), ["Пока нет уведомлений"])
    }
}
