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
        XCTAssertNil(control.field.onFocus)
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

}
