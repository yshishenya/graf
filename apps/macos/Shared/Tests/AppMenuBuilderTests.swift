import AppKit
import XCTest
@testable import TwoBrainRecAppCore

@MainActor
final class AppMenuBuilderTests: XCTestCase {
    func testMenuIsRussianAndHasUniqueShortcuts() throws {
        let menu = AppMenuBuilder.makeMenu(zoomTarget: NSObject())
        let titles = allTitles(in: menu)
        for forbidden in ["About", "Hide", "Quit", "Edit", "View", "Window", "Minimize", "Zoom In", "Zoom Out", "Actual Size"] {
            XCTAssertFalse(titles.contains(forbidden), "unexpected English menu title: \(forbidden)")
        }
        XCTAssertTrue(titles.contains("Остановить запись"))
        XCTAssertTrue(titles.contains("Настройки…"))
        XCTAssertTrue(titles.contains("Увеличить масштаб кабинета"))

        var seen: [String: String] = [:]
        for item in allItems(in: menu) where !item.keyEquivalent.isEmpty {
            let key = "\(item.keyEquivalentModifierMask.rawValue):\(item.keyEquivalent)"
            if let previous = seen[key] {
                XCTFail("duplicate shortcut \(key): \(previous) and \(item.title)")
            }
            seen[key] = item.title
        }
    }

    func testStopIsAvailableFromApplicationMenuWithShiftCommandS() throws {
        let menu = AppMenuBuilder.makeMenu(zoomTarget: NSObject())
        let item = try XCTUnwrap(allItems(in: menu).first { $0.title == "Остановить запись" })
        XCTAssertEqual(item.keyEquivalent, "s")
        XCTAssertEqual(item.keyEquivalentModifierMask, [.command, .shift])
        XCTAssertEqual(item.action, #selector(AppLifecycleDelegate.stopRecordingFromMenu(_:)))
    }

    func testZoomMenuHasOneVisibleIncreaseAndZeroConflict() throws {
        let menu = AppMenuBuilder.makeMenu(zoomTarget: NSObject())
        let viewItems = try XCTUnwrap(menu.items.first { $0.submenu?.title == "Вид" }?.submenu?.items)
        XCTAssertEqual(viewItems.filter { $0.title == "Увеличить масштаб кабинета" }.count, 1)
        XCTAssertEqual(viewItems.filter { $0.keyEquivalent == "0" }.map(\.title), ["Сбросить масштаб кабинета"])
        XCTAssertFalse(viewItems.contains { $0.keyEquivalent == "0" && $0.title != "Сбросить масштаб кабинета" })
    }

    private func allItems(in menu: NSMenu) -> [NSMenuItem] {
        menu.items + menu.items.flatMap { item in item.submenu.map(allItems(in:)) ?? [] }
    }

    private func allTitles(in menu: NSMenu) -> Set<String> {
        Set(allItems(in: menu).map(\.title))
    }
}
