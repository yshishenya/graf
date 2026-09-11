import AppKit
import SwiftUI

/// The field's query is separate from the stored setting. Only an explicit
/// selection invokes onSelect; application filters intentionally retain text.
struct NativeSettingsComboBox: NSViewRepresentable {
    struct Option: Equatable {
        let id: String
        let label: String
    }

    let title: String
    var options: [Option]
    var selectedID: String? = nil
    var placeholder = "Выберите или начните вводить"
    var filter: Binding<String>? = nil
    var onSelect: (String) -> Void = { _ in }
    @Environment(\.isEnabled) private var isEnabled

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeNSView(context: Context) -> NSComboBox {
        let control = NSComboBox()
        control.isEditable = true
        control.completes = false
        control.hasVerticalScroller = true
        control.numberOfVisibleItems = 8
        control.controlSize = .regular
        control.setContentHuggingPriority(.defaultLow, for: .horizontal)
        context.coordinator.update(self, control: control, enabled: isEnabled)
        return control
    }

    func updateNSView(_ control: NSComboBox, context: Context) {
        context.coordinator.update(self, control: control, enabled: isEnabled)
    }

    @MainActor
    final class Coordinator: NSObject, NSComboBoxDelegate, NSComboBoxDataSource {
        private var owner: NativeSettingsComboBox
        private var query = ""
        private var isEditing = false
        private var isUpdating = false
        private var isExpanded = false
        private var isPopupInteraction = false
        private var didConfirmInPopup = false
        private(set) var visibleOptions: [Option] = []

        init(_ owner: NativeSettingsComboBox) { self.owner = owner }

        func update(_ owner: NativeSettingsComboBox, control: NSComboBox, enabled: Bool) {
            self.owner = owner
            control.usesDataSource = true
            control.dataSource = self
            control.delegate = self
            control.target = self
            control.action = #selector(selected(_:))
            control.isEnabled = enabled
            control.placeholderString = owner.placeholder
            control.setAccessibilityLabel(owner.title)
            control.setAccessibilityHelp("Выберите вариант или введите текст, чтобы сократить список.")
            refresh(control)
            if !isEditing || !enabled { restore(control) }
        }

        private func refresh(_ control: NSComboBox) {
            let activeID = visibleOptions.indices.contains(control.indexOfSelectedItem)
                ? visibleOptions[control.indexOfSelectedItem].id : nil
            visibleOptions = owner.options.filter { query.isEmpty || $0.label.localizedStandardContains(query) || $0.id.localizedStandardContains(query) }
            isUpdating = true
            // Reloading the catalog must not replace an in-progress query or
            // move the field editor's insertion point.
            let text = control.stringValue
            let range = control.currentEditor()?.selectedRange
            control.reloadData()
            if let activeID, let index = visibleOptions.firstIndex(where: { $0.id == activeID }) {
                control.selectItem(at: index)
            } else if control.indexOfSelectedItem >= 0 {
                control.deselectItem(at: control.indexOfSelectedItem)
            }
            control.stringValue = text
            if let range { control.currentEditor()?.selectedRange = range }
            isUpdating = false
        }

        func numberOfItems(in comboBox: NSComboBox) -> Int { max(1, visibleOptions.count) }

        func comboBox(_ comboBox: NSComboBox, objectValueForItemAt index: Int) -> Any? {
            if visibleOptions.isEmpty { return owner.options.isEmpty ? "Список пока недоступен" : "Ничего не найдено" }
            return visibleOptions.indices.contains(index) ? visibleOptions[index].label : nil
        }

        func comboBoxWillPopUp(_ notification: Notification) {
            guard let control = notification.object as? NSComboBox else { return }
            isExpanded = true
            isPopupInteraction = true
            didConfirmInPopup = false
            if !isEditing { query = "" }
            refresh(control)
        }

        func comboBoxWillDismiss(_ notification: Notification) {
            isExpanded = false
            guard let control = notification.object as? NSComboBox else { return }
            // Dismissal itself is not confirmation (Escape, Tab, outside click).
            // Let AppKit deliver a click/Return action before restoring text.
            DispatchQueue.main.async { [weak self, weak control] in
                guard let self, let control, !self.isExpanded else { return }
                self.isPopupInteraction = false
                if !self.didConfirmInPopup { self.restore(control) }
            }
        }

        func controlTextDidBeginEditing(_ notification: Notification) {
            guard let control = notification.object as? NSComboBox else { return }
            // The cell owns AXShowMenu; NSControl.performClick only sends the
            // target action and does not open an NSComboBox popup.
            DispatchQueue.main.async { [weak self, weak control] in
                guard let self, let control, control.isEnabled,
                      control.currentEditor() != nil, !self.isExpanded else { return }
                control.cell?.accessibilityPerformShowMenu()
            }
        }

        func controlTextDidChange(_ notification: Notification) {
            guard !isUpdating, let control = notification.object as? NSComboBox, control.isEnabled else { return }
            isEditing = true
            query = control.stringValue
            owner.filter?.wrappedValue = query
            isUpdating = true
            if control.indexOfSelectedItem >= 0 { control.deselectItem(at: control.indexOfSelectedItem) }
            control.stringValue = query
            isUpdating = false
            refresh(control)
            controlTextDidBeginEditing(notification)
        }

        func comboBoxSelectionDidChange(_ notification: Notification) {
            // AppKit distinguishes the completed popup choice (DidChange)
            // from highlighted rows (IsChanging). Programmatic selectItem also
            // sends DidChange, so exclude all refresh/restore operations.
            guard !isUpdating, isPopupInteraction,
                  let control = notification.object as? NSComboBox else { return }
            confirmSelection(in: control)
        }

        func comboBoxSelectionIsChanging(_ notification: Notification) {
            // Highlighting alone never changes the stored setting.
        }

        @objc private func selected(_ control: NSComboBox) {
            handleSelectionAction(in: control, event: NSApp.currentEvent)
        }

        func handleSelectionAction(in control: NSComboBox, event: NSEvent?) {
            // Combo box actions can also follow arrow navigation. Only Return
            // confirms a keyboard action; mouse and accessibility actions do.
            if let event, event.type == .keyDown || event.type == .keyUp,
               event.keyCode != 36 && event.keyCode != 76 { return }
            confirmSelection(in: control)
        }

        func confirmSelection(in control: NSComboBox) {
            guard !isUpdating, !(isPopupInteraction && didConfirmInPopup), control.isEnabled,
                  (control.currentEditor() as? NSTextView)?.hasMarkedText() != true else { return }
            let index = control.indexOfSelectedItem >= 0 ? control.indexOfSelectedItem : (isEditing ? 0 : -1)
            guard visibleOptions.indices.contains(index) else { return }
            let option = visibleOptions[index]
            guard owner.options.contains(where: { $0.id == option.id }) else { return }
            didConfirmInPopup = true
            isEditing = false
            query = ""
            control.stringValue = option.label
            if let filter = owner.filter { filter.wrappedValue = option.label }
            else if option.id != owner.selectedID { owner.onSelect(option.id) }
        }

        func control(_ control: NSControl, textView: NSTextView, doCommandBy commandSelector: Selector) -> Bool {
            guard let combo = control as? NSComboBox, !textView.hasMarkedText() else { return false }
            if commandSelector == #selector(NSResponder.cancelOperation(_:)) {
                restore(combo)
            }
            // AppKit must handle Return/Escape to dismiss its popup. Return
            // confirms through the target/action path, never twice here. Tab
            // follows the normal key-view loop; end-editing restores.
            return false
        }

        func controlTextDidEndEditing(_ notification: Notification) {
            guard let control = notification.object as? NSComboBox else { return }
            restore(control)
        }

        private func restore(_ control: NSComboBox) {
            isEditing = false
            query = ""
            refresh(control)
            isUpdating = true
            if let index = visibleOptions.firstIndex(where: { $0.id == owner.selectedID }) {
                control.selectItem(at: index)
            } else if control.indexOfSelectedItem >= 0 {
                control.deselectItem(at: control.indexOfSelectedItem)
            }
            control.stringValue = owner.filter?.wrappedValue ?? owner.options.first(where: { $0.id == owner.selectedID })?.label ?? ""
            isUpdating = false
        }
    }
}
