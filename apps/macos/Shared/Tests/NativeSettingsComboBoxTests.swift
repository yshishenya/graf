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

    func testTypingAndArrowSelectionNeverSaveAndBlurRestoresSelectedLabel() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: true)
        combo.stringValue = "ВСЕ"
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        XCTAssertEqual(coordinator.visibleOptions.map(\.id), ["always"])
        combo.selectItem(at: 0)
        coordinator.comboBoxSelectionDidChange(Notification(name: NSComboBox.selectionDidChangeNotification, object: combo))
        XCTAssertEqual(saved, [])
        coordinator.controlTextDidEndEditing(Notification(name: NSControl.textDidEndEditingNotification, object: combo))
        XCTAssertEqual(combo.stringValue, "Спрашивать")
        XCTAssertEqual(saved, [])
    }

    func testExplicitChoiceUsesStableIDAndNoMatchCannotSave() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: true)
        combo.stringValue = "все"
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        coordinator.confirmSelection(in: combo)
        XCTAssertEqual(saved, ["always"])
        combo.stringValue = "произвольное значение"
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        coordinator.confirmSelection(in: combo)
        XCTAssertEqual(saved, ["always"])
        XCTAssertEqual(coordinator.numberOfItems(in: combo), 1)
        XCTAssertEqual(coordinator.comboBox(combo, objectValueForItemAt: 0) as? String, "Ничего не найдено")
    }

    func testCatalogUpdateKeepsInputAndRemovedChoiceCannotSave() {
        var saved: [String] = []
        var owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: true)
        combo.stringValue = "все"
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        owner.options.removeAll { $0.id == "always" }
        coordinator.update(owner, control: combo, enabled: true)
        XCTAssertEqual(combo.stringValue, "все")
        XCTAssertTrue(coordinator.visibleOptions.isEmpty)
        coordinator.confirmSelection(in: combo)
        XCTAssertTrue(saved.isEmpty)
    }

    func testAppQuerySurvivesBlurAndClearRestoresEntireCatalog() {
        var query = ""
        let binding = Binding(get: { query }, set: { query = $0 })
        let owner = NativeSettingsComboBox(title: "Приложения", options: options, filter: binding)
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: true)
        combo.stringValue = "все"
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        coordinator.controlTextDidEndEditing(Notification(name: NSControl.textDidEndEditingNotification, object: combo))
        XCTAssertEqual(query, "все")
        XCTAssertEqual(combo.stringValue, "все")
        combo.stringValue = ""
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        XCTAssertEqual(query, "")
        XCTAssertEqual(coordinator.visibleOptions.count, 3)
    }

    func testDisabledControlCannotConfirmAndOpeningShowsAllOptions() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: false)
        coordinator.comboBoxWillPopUp(Notification(name: NSComboBox.willPopUpNotification, object: combo))
        XCTAssertEqual(coordinator.visibleOptions.count, 3)
        coordinator.confirmSelection(in: combo)
        XCTAssertTrue(saved.isEmpty)
    }
    func testArrowAndTabActionsDoNotSaveButReturnConfirms() throws {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: true)
        combo.selectItem(at: 1)
        for keyCode: UInt16 in [125, 126, 48, 53] {
            for type: NSEvent.EventType in [.keyDown, .keyUp] {
                let event = try XCTUnwrap(NSEvent.keyEvent(with: type, location: .zero, modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil, characters: "", charactersIgnoringModifiers: "", isARepeat: false, keyCode: keyCode))
                coordinator.handleSelectionAction(in: combo, event: event)
            }
        }
        XCTAssertTrue(saved.isEmpty)
        let enter = try XCTUnwrap(NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil, characters: "\r", charactersIgnoringModifiers: "\r", isARepeat: false, keyCode: 36))
        coordinator.handleSelectionAction(in: combo, event: enter)
        XCTAssertEqual(saved, ["always"])
    }

    func testEscapeRestoresSettingAndIMEEnterDoesNotConfirm() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        let editor = NSTextView()
        coordinator.update(owner, control: combo, enabled: true)
        combo.stringValue = "все"
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        editor.setMarkedText("все", selectedRange: NSRange(location: 3, length: 0), replacementRange: NSRange(location: NSNotFound, length: 0))
        XCTAssertFalse(coordinator.control(combo, textView: editor, doCommandBy: #selector(NSResponder.insertNewline(_:))))
        XCTAssertTrue(saved.isEmpty)
        editor.unmarkText()
        XCTAssertFalse(coordinator.control(combo, textView: editor, doCommandBy: #selector(NSResponder.cancelOperation(_:))))
        XCTAssertEqual(combo.stringValue, "Спрашивать")
        XCTAssertTrue(saved.isEmpty)
    }

    func testReturnLeavesDismissalToAppKitAndOnlyItsActionConfirms() throws {
        var query = ""
        let owner = NativeSettingsComboBox(
            title: "Приложения",
            options: [.init(id: "zoom", label: "Zoom"), .init(id: "zoom-room", label: "Zoom Rooms")],
            filter: Binding(get: { query }, set: { query = $0 })
        )
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: true)
        combo.stringValue = "zoom"
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        coordinator.comboBoxWillPopUp(Notification(name: NSComboBox.willPopUpNotification, object: combo))
        combo.delegate = nil
        combo.selectItem(at: 0)
        combo.delegate = coordinator
        coordinator.comboBoxSelectionIsChanging(Notification(name: NSComboBox.selectionIsChangingNotification, object: combo))
        XCTAssertFalse(coordinator.control(combo, textView: NSTextView(), doCommandBy: #selector(NSResponder.insertNewline(_:))))
        XCTAssertEqual(query, "zoom", "The delegate must not update SwiftUI while AppKit still handles Return")
        let enter = try XCTUnwrap(NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil, characters: "\r", charactersIgnoringModifiers: "\r", isARepeat: false, keyCode: 36))
        coordinator.handleSelectionAction(in: combo, event: enter)
        coordinator.comboBoxWillDismiss(Notification(name: NSComboBox.willDismissNotification, object: combo))
        XCTAssertEqual(query, "Zoom")
        XCTAssertEqual(combo.stringValue, "Zoom")
    }

    func testTabLeavesKeyViewTraversalToAppKitAndMouseStillConfirms() throws {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: true)
        combo.stringValue = "все"
        coordinator.controlTextDidChange(Notification(name: NSControl.textDidChangeNotification, object: combo))
        XCTAssertFalse(coordinator.control(combo, textView: NSTextView(), doCommandBy: #selector(NSResponder.insertTab(_:))))
        coordinator.controlTextDidEndEditing(Notification(name: NSControl.textDidEndEditingNotification, object: combo))
        XCTAssertEqual(combo.stringValue, "Спрашивать")
        XCTAssertTrue(saved.isEmpty)
        combo.selectItem(at: 1)
        let mouse = try XCTUnwrap(NSEvent.mouseEvent(with: .leftMouseUp, location: .zero, modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil, eventNumber: 0, clickCount: 1, pressure: 0))
        coordinator.handleSelectionAction(in: combo, event: mouse)
        XCTAssertEqual(saved, ["always"])
    }

    func testPopupFinalSelectionSavesWithoutTargetActionAndIgnoresRefresh() {
        var saved: [String] = []
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask") { saved.append($0) }
        let coordinator = owner.makeCoordinator()
        let combo = NSComboBox()
        coordinator.update(owner, control: combo, enabled: true)
        coordinator.comboBoxWillPopUp(Notification(name: NSComboBox.willPopUpNotification, object: combo))
        coordinator.update(owner, control: combo, enabled: true)
        XCTAssertTrue(saved.isEmpty, "Programmatic selectItem during refresh must not save")
        combo.delegate = nil
        combo.selectItem(at: 1)
        combo.delegate = coordinator
        coordinator.comboBoxSelectionIsChanging(Notification(name: NSComboBox.selectionIsChangingNotification, object: combo))
        XCTAssertTrue(saved.isEmpty, "A highlight is not a choice")
        // AppKit may announce dismissal before the final selection notification.
        coordinator.comboBoxWillDismiss(Notification(name: NSComboBox.willDismissNotification, object: combo))
        coordinator.comboBoxSelectionDidChange(Notification(name: NSComboBox.selectionDidChangeNotification, object: combo))
        XCTAssertEqual(saved, ["always"])
        coordinator.handleSelectionAction(in: combo, event: nil)
        XCTAssertEqual(saved, ["always"], "An optional target action must not duplicate the completed choice")
    }

    func testFocusOpensTheNativeCellMenuWithoutSendingASelectionAction() async {
        let owner = NativeSettingsComboBox(title: "Правило", options: options, selectedID: "ask")
        let coordinator = owner.makeCoordinator()
        let combo = EditingComboBox()
        let cell = ShowMenuCell()
        combo.cell = cell
        coordinator.update(owner, control: combo, enabled: true)
        coordinator.controlTextDidBeginEditing(Notification(name: NSControl.textDidBeginEditingNotification, object: combo))
        await withCheckedContinuation { continuation in
            DispatchQueue.main.async { continuation.resume() }
        }
        XCTAssertEqual(cell.showMenuCalls, 1)
    }

    private final class EditingComboBox: NSComboBox {
        let editor = NSTextView()
        override func currentEditor() -> NSText? { editor }
    }

    private final class ShowMenuCell: NSComboBoxCell {
        var showMenuCalls = 0
        override func accessibilityPerformShowMenu() -> Bool {
            showMenuCalls += 1
            return true
        }
    }

}
