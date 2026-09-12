import AppKit
import SwiftUI
@testable import TwoBrainRecAppCore
import XCTest

@MainActor
final class NativeSettingsComboBoxTests: XCTestCase {
    private let options = [
        NativeSettingsComboBox.Option(id: "ask", label: "Спрашивать"),
        NativeSettingsComboBox.Option(id: "always", label: "Всегда"),
        NativeSettingsComboBox.Option(id: "never", label: "Никогда"),
    ]

    private func type(_ text: String, in control: NativeSettingsComboBox.Control, coordinator: NativeSettingsComboBox.Coordinator) {
        control.field.stringValue = text
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: control.field))
    }

    func testTypingAndArrowsNeverSaveAndEscapeRestoresSelectedLabel() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        type("ВСЕ", in: control, coordinator: coordinator)
        XCTAssertEqual(coordinator.visibleOptions.map(\.id), ["always"])
        XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.moveDown(_:))))
        XCTAssertEqual(coordinator.activeIndex, 0)
        XCTAssertTrue(saved.isEmpty)
        XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.cancelOperation(_:))))
        XCTAssertEqual(control.field.stringValue, "Спрашивать")
        XCTAssertTrue(saved.isEmpty)
    }

    func testReturnExplicitlySavesHighlightedOptionOnceAndCloses() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        coordinator.open()
        XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.moveDown(_:))))
        XCTAssertEqual(coordinator.activeIndex, 1)
        XCTAssertTrue(saved.isEmpty)
        XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.insertNewline(_:))))
        XCTAssertEqual(saved, ["always"])
        XCTAssertEqual(control.field.stringValue, "Всегда")
        XCTAssertFalse(control.field.isAccessibilityExpanded())
        coordinator.choose(index: 1)
        XCTAssertEqual(saved, ["always"])
    }

    func testOptionClickUsesStableIDWithDuplicateLabelsAndNoMatchCannotSave() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Шаблон", options: [.init(id: "one", label: "Общий"), .init(id: "two", label: "Общий")], selectedID: "one") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        coordinator.open()
        coordinator.choose(index: 1)
        XCTAssertEqual(saved, ["two"])
        type("неизвестное значение", in: control, coordinator: coordinator)
        XCTAssertTrue(coordinator.visibleOptions.isEmpty)
        coordinator.choose(index: 0)
        XCTAssertEqual(saved, ["two"])
    }

    func testCatalogUpdatePreservesInputAndRemovedChoiceCannotSave() {
        var saved: [String] = []
        var owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        type("все", in: control, coordinator: coordinator)
        owner.options.removeAll { $0.id == "always" }
        coordinator.update(owner, control: control, enabled: true)
        XCTAssertEqual(control.field.stringValue, "все")
        XCTAssertTrue(coordinator.visibleOptions.isEmpty)
        coordinator.choose(index: 0)
        XCTAssertTrue(saved.isEmpty)
    }

    func testAppQuerySurvivesBlurAndClearRestoresEntireCatalog() {
        var query = ""
        let owner = NativeSettingsComboBox(title: "Приложения", options: options, filter: Binding(get: { query }, set: { query = $0 }))
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        type("все", in: control, coordinator: coordinator)
        coordinator.controlTextDidEndEditing(Notification(name: NSControl.textDidEndEditingNotification, object: control.field))
        XCTAssertEqual(query, "все")
        XCTAssertEqual(control.field.stringValue, "все")
        type("", in: control, coordinator: coordinator)
        XCTAssertEqual(query, "")
        XCTAssertEqual(coordinator.visibleOptions.count, 3)
    }

    func testDisabledControlCannotConfirmAndOpeningShowsAllOptions() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: false)
        coordinator.open()
        coordinator.choose(index: 1)
        XCTAssertTrue(saved.isEmpty)
        XCTAssertFalse(control.arrow.isEnabled)
        XCTAssertFalse(control.field.isEnabled)
    }

    func testIMEEnterDoesNotConfirmAndTabRestoresWithoutBlockingTraversal() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        let editor = NSTextView()
        coordinator.update(owner, control: control, enabled: true)
        type("все", in: control, coordinator: coordinator)
        editor.setMarkedText("все", selectedRange: NSRange(location: 3, length: 0), replacementRange: NSRange(location: NSNotFound, length: 0))
        XCTAssertFalse(coordinator.control(control.field, textView: editor, doCommandBy: #selector(NSResponder.insertNewline(_:))))
        XCTAssertTrue(saved.isEmpty)
        editor.unmarkText()
        XCTAssertFalse(coordinator.control(control.field, textView: editor, doCommandBy: #selector(NSResponder.insertTab(_:))))
        XCTAssertEqual(control.field.stringValue, "Спрашивать")
        XCTAssertTrue(saved.isEmpty)
    }

    func testAppFilterReturnUsesChosenNameAndExternalCloseRetainsIt() {
        var query = ""
        let owner = NativeSettingsComboBox(title: "Приложения", options: [.init(id: "zoom", label: "Zoom"), .init(id: "rooms", label: "Zoom Rooms")], filter: Binding(get: { query }, set: { query = $0 }))
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        type("zoom", in: control, coordinator: coordinator)
        XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.moveDown(_:))))
        XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.insertNewline(_:))))
        coordinator.close()
        XCTAssertEqual(query, "Zoom")
        XCTAssertEqual(control.field.stringValue, "Zoom")
    }

    func testAccessibilityAndDetachHaveNoContextMenuOrCommitSideEffects() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        XCTAssertEqual(control.field.accessibilityRole(), .comboBox)
        XCTAssertEqual(control.field.accessibilityLabel(), "Правило")
        XCTAssertEqual(control.field.accessibilityLinkedUIElements()?.count, 1)
        type("все", in: control, coordinator: coordinator)
        coordinator.detach()
        XCTAssertNil(control.field.onClick)
        XCTAssertNil(control.field.delegate)
        XCTAssertTrue(saved.isEmpty)
        XCTAssertEqual(control.field.stringValue, "Спрашивать")
    }
    func testRepeatedArrowsTraverseOptionsWithoutSavingOrResettingToCurrentSetting() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        coordinator.open()
        for expected in [1, 2, 2] {
            XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.moveDown(_:))))
            XCTAssertEqual(coordinator.activeIndex, expected)
        }
        XCTAssertTrue(saved.isEmpty)
        XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.insertNewline(_:))))
        XCTAssertEqual(saved, ["never"])
        XCTAssertEqual(control.field.stringValue, "Никогда")
    }

    func testReturnAfterEscapeCannotSaveFirstOption() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "never") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        type("спра", in: control, coordinator: coordinator)
        XCTAssertTrue(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.cancelOperation(_:))))
        XCTAssertFalse(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.insertNewline(_:))))
        XCTAssertEqual(control.field.stringValue, "Никогда")
        XCTAssertTrue(saved.isEmpty)
    }

    func testAccessibleOptionPressUsesStableChoiceAndCannotSaveAfterClose() throws {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        coordinator.open()
        let option = try XCTUnwrap(coordinator.tableView(NSTableView(), viewFor: nil, row: 1))
        XCTAssertEqual(option.accessibilityRole(), .button)
        XCTAssertTrue(option.accessibilityPerformPress())
        XCTAssertEqual(saved, ["always"])
        XCTAssertEqual(control.field.stringValue, "Всегда")
        _ = option.accessibilityPerformPress()
        XCTAssertEqual(saved, ["always"])
    }

    func testBlurRestoresLabelAfterTheCurrentClickWithoutSaving() async {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        type("все", in: control, coordinator: coordinator)
        coordinator.controlTextDidEndEditing(Notification(name: NSControl.textDidEndEditingNotification, object: control.field))
        await withCheckedContinuation { continuation in
            DispatchQueue.main.async { continuation.resume() }
        }
        XCTAssertEqual(control.field.stringValue, "Спрашивать")
        XCTAssertTrue(saved.isEmpty)
    }

    func testActualTableViewportFitsZeroOneThreeEightAndLimitsLongCatalog() {
        for count in [0, 1, 3, 8, 15] {
            let owner = NativeSettingsComboBox(title: "Приложения", options: (0..<count).map { .init(id: "\($0)", label: "Приложение \($0)") })
            let coordinator = owner.makeCoordinator()
            let control = NativeSettingsComboBox.Control(frame: NSRect(x: 0, y: 0, width: 380, height: 32))
            coordinator.update(owner, control: control, enabled: true)
            let rows = coordinator.rowRects
            XCTAssertEqual(rows.count, max(1, count))
            XCTAssertEqual(rows[0].minY, 0, accuracy: 0.01)
            XCTAssertEqual(coordinator.viewport.height, rows[min(rows.count, 8) - 1].maxY, accuracy: 0.01)
            XCTAssertEqual(coordinator.viewport.width, 378, accuracy: 0.01)
            coordinator.detach()
        }
    }

    func testVariableHeightRowsRemainWholeAndFilteringResetsScrolledViewport() {
        let owner = NativeSettingsComboBox(title: "Каталог", options: (0..<12).map {
            .init(id: "\($0)", label: $0 == 2 ? String(repeating: "Длинное название ", count: 8) : "Приложение \($0)")
        })
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control(frame: NSRect(x: 0, y: 0, width: 172, height: 32))
        coordinator.update(owner, control: control, enabled: true)
        XCTAssertGreaterThan(coordinator.rowRects[2].height, 32)
        XCTAssertEqual(coordinator.viewport.height, coordinator.rowRects[7].maxY, accuracy: 0.01)
        coordinator.open()
        for _ in 0..<12 {
            _ = coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.moveDown(_:)))
        }
        XCTAssertGreaterThan(coordinator.viewport.minY, 0)
        type("Длинное", in: control, coordinator: coordinator)
        XCTAssertEqual(coordinator.visibleOptions.count, 1)
        XCTAssertEqual(coordinator.viewport.minY, 0, accuracy: 0.01)
        XCTAssertEqual(coordinator.viewport.height, coordinator.rowRects[0].height, accuracy: 0.01)
        coordinator.detach()
    }

    func testPopupFlipsClampsAndFitsWholeVariableRowsNearScreenEdge() {
        let screen = NSRect(x: 0, y: 0, width: 600, height: 400)
        let frame = NativeSettingsComboBox.popupFrame(anchor: NSRect(x: 450, y: 25, width: 172, height: 32), screen: screen, rowEnds: [32, 80, 112])
        XCTAssertEqual(frame.minY, 61)
        XCTAssertEqual(frame.maxX, 592)
        XCTAssertEqual(frame.height, 114)
        let limited = NativeSettingsComboBox.popupFrame(anchor: NSRect(x: 20, y: 180, width: 172, height: 32), screen: screen, rowEnds: [32, 80, 112, 144, 210, 242, 274, 306])
        XCTAssertEqual(limited.height, 146)
        XCTAssertTrue(screen.insetBy(dx: 8, dy: 8).contains(limited))
        let narrow = NativeSettingsComboBox.popupFrame(anchor: NSRect(x: 0, y: 10, width: 380, height: 32), screen: NSRect(x: 0, y: 0, width: 200, height: 100), rowEnds: [100])
        let offscreen = NativeSettingsComboBox.popupFrame(anchor: NSRect(x: 700, y: 600, width: 172, height: 32), screen: screen, rowEnds: [32, 64, 96])
        XCTAssertTrue(screen.insetBy(dx: 8, dy: 8).contains(offscreen))
        XCTAssertEqual(narrow.width, 184)
        XCTAssertGreaterThan(narrow.height, 0)
        XCTAssertTrue(NSRect(x: 8, y: 8, width: 184, height: 84).contains(narrow))
    }

    func testSavedAccessibilitySelectionDiffersFromActiveAndFilterHasNoSavedChoice() throws {
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask")
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        coordinator.open()
        _ = coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.moveDown(_:)))
        XCTAssertEqual(coordinator.activeIndex, 1)
        XCTAssertTrue(try XCTUnwrap(coordinator.tableView(NSTableView(), viewFor: nil, row: 0)).isAccessibilitySelected())
        XCTAssertFalse(try XCTUnwrap(coordinator.tableView(NSTableView(), viewFor: nil, row: 1)).isAccessibilitySelected())
        XCTAssertTrue(try XCTUnwrap(coordinator.tableView(NSTableView(), rowViewForRow: 0)).isAccessibilitySelected())
        let filterOwner = NativeSettingsComboBox(title: "Приложения", options: options, selectedID: "ask", filter: .constant("Спрашивать"))
        coordinator.update(filterOwner, control: control, enabled: true)
        XCTAssertFalse(try XCTUnwrap(coordinator.tableView(NSTableView(), viewFor: nil, row: 0)).isAccessibilitySelected())
        coordinator.detach()
    }

    func testProgrammaticFocusDoesNotOpenAndInternalFieldHasNoNestedRing() {
        let owner = NativeSettingsComboBox(title: "Правило", options: options)
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        _ = control.field.becomeFirstResponder()
        XCTAssertFalse(control.field.isAccessibilityExpanded())
        XCTAssertEqual(control.field.focusRingType, .none)
        XCTAssertFalse(coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.insertNewline(_:))))
        coordinator.detach()
    }

    func testAccessibilitySharedFocusTracksActiveChoiceAndClearsOnFilterAndClose() throws {
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask")
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control()
        coordinator.update(owner, control: control, enabled: true)
        XCTAssertTrue(control.field.accessibilitySharedFocusElements()?.isEmpty ?? true)
        coordinator.open()
        let initial = try XCTUnwrap(control.field.accessibilitySharedFocusElements()?.first as? NSView)
        XCTAssertEqual(initial.accessibilityLabel(), "Спрашивать")
        XCTAssertTrue(initial.isAccessibilitySelected())
        _ = coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.moveDown(_:)))
        let active = try XCTUnwrap(control.field.accessibilitySharedFocusElements()?.first as? NSView)
        XCTAssertEqual(active.accessibilityLabel(), "Всегда")
        XCTAssertFalse(active.isAccessibilitySelected())
        type("Нет совпадений", in: control, coordinator: coordinator)
        XCTAssertTrue(control.field.accessibilitySharedFocusElements()?.isEmpty ?? true)
        type("Все", in: control, coordinator: coordinator)
        _ = coordinator.control(control.field, textView: NSTextView(), doCommandBy: #selector(NSResponder.moveDown(_:)))
        XCTAssertEqual(control.field.accessibilitySharedFocusElements()?.count, 1)
        coordinator.close()
        XCTAssertTrue(control.field.accessibilitySharedFocusElements()?.isEmpty ?? true)
        coordinator.detach()
    }

    func testOptionHitTargetAcceptsClickWithoutMakingPanelKey() throws {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control(frame: NSRect(x: 0, y: 0, width: 172, height: 32))
        coordinator.update(owner, control: control, enabled: true)
        coordinator.open()
        let table = try XCTUnwrap(coordinator.scroll.documentView as? NSTableView)
        let row = table.rect(ofRow: 1)
        let target = try XCTUnwrap(table.hitTest(NSPoint(x: 80, y: row.midY)))
        XCTAssertTrue(target.acceptsFirstMouse(for: nil))
        XCTAssertFalse(target.needsPanelToBecomeKey)
        let button = try XCTUnwrap(target as? NSButton)
        XCTAssertTrue(button.refusesFirstResponder)
        for x: CGFloat in [10, 80, 160] {
            XCTAssertTrue(table.hitTest(NSPoint(x: x, y: row.midY)) === button)
        }
        // Invoke the native control action directly; no fabricated mouse event.
        XCTAssertTrue(button.sendAction(button.action, to: button.target))
        XCTAssertEqual(saved, ["always"])
        _ = button.sendAction(button.action, to: button.target)
        XCTAssertEqual(saved, ["always"])
        XCTAssertEqual(control.field.stringValue, "Всегда")
        coordinator.detach()
    }

    func testExpandedListIsReachableInFieldAccessibilityChildrenAndDetachesOnClose() throws {
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask")
        let coordinator = owner.makeCoordinator()
        let control = NativeSettingsComboBox.Control(frame: NSRect(x: 0, y: 0, width: 172, height: 32))
        coordinator.update(owner, control: control, enabled: true)
        let table = try XCTUnwrap(coordinator.scroll.documentView as? NSTableView)
        XCTAssertFalse(control.field.accessibilityChildren()?.contains { ($0 as? NSView) === table } ?? false)
        coordinator.open()
        XCTAssertTrue(control.field.accessibilityChildren()?.contains { ($0 as? NSView) === table } ?? false)
        XCTAssertTrue((table.accessibilityParent() as? NSView) === control.field)
        XCTAssertTrue(table.isAccessibilityElement())
        XCTAssertEqual(table.accessibilityRole(), .list)
        func labels(in element: Any, depth: Int = 0) -> [String] {
            guard depth < 8, let element = element as? NSAccessibilityProtocol else { return [] }
            return [element.accessibilityLabel()].compactMap { $0 }
                + (element.accessibilityChildren() ?? []).flatMap { labels(in: $0, depth: depth + 1) }
        }
        XCTAssertTrue(labels(in: control.field).contains("Всегда"))
        let row = try XCTUnwrap(table.view(atColumn: 0, row: 1, makeIfNecessary: true))
        XCTAssertEqual(row.accessibilityLabel(), "Всегда")
        XCTAssertTrue(row.accessibilityPerformPress())
        XCTAssertEqual(control.field.stringValue, "Всегда")
        XCTAssertNil(control.field.optionsList)
        XCTAssertFalse(control.field.accessibilityChildren()?.contains { ($0 as? NSView) === table } ?? false)
        coordinator.detach()
    }

}
