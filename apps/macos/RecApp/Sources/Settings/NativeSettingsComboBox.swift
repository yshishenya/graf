import AppKit
import SwiftUI

/// One editable field; the query never becomes a stored setting without a choice.
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

    func makeNSView(context: Context) -> Control {
        let control = Control()
        context.coordinator.update(self, control: control, enabled: isEnabled)
        return control
    }

    func updateNSView(_ control: Control, context: Context) {
        context.coordinator.update(self, control: control, enabled: isEnabled)
    }

    static func dismantleNSView(_ control: Control, coordinator: Coordinator) {
        coordinator.detach()
    }

    final class Field: NSTextField {
        var onFocus: (() -> Void)?
        override func becomeFirstResponder() -> Bool {
            let accepted = super.becomeFirstResponder()
            if accepted { onFocus?() }
            return accepted
        }
        override func mouseDown(with event: NSEvent) {
            super.mouseDown(with: event)
            onFocus?()
        }
    }

    final class Control: NSView {
        let field = Field()
        let arrow = NSButton(image: NSImage(systemSymbolName: "chevron.down", accessibilityDescription: nil)!, target: nil, action: nil)

        override init(frame: NSRect) {
            super.init(frame: frame)
            wantsLayer = true
            layer?.cornerRadius = 5
            layer?.borderWidth = 1
            field.isBezeled = false
            field.drawsBackground = false
            field.focusRingType = .exterior
            field.lineBreakMode = .byTruncatingTail
            field.setAccessibilityRole(.comboBox)
            field.setContentHuggingPriority(.defaultLow, for: .horizontal)
            arrow.isBordered = false
            arrow.refusesFirstResponder = true
            arrow.setAccessibilityLabel("Показать варианты")
            for view in [field, arrow] {
                view.translatesAutoresizingMaskIntoConstraints = false
                addSubview(view)
            }
            NSLayoutConstraint.activate([
                field.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 8),
                field.centerYAnchor.constraint(equalTo: centerYAnchor),
                field.trailingAnchor.constraint(equalTo: arrow.leadingAnchor, constant: -4),
                arrow.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -4),
                arrow.centerYAnchor.constraint(equalTo: centerYAnchor),
                arrow.widthAnchor.constraint(equalToConstant: 22),
                arrow.heightAnchor.constraint(equalToConstant: 24),
            ])
            updateColors()
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
        override var intrinsicContentSize: NSSize { NSSize(width: 160, height: 32) }
        override func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); updateColors() }
        private func updateColors() {
            effectiveAppearance.performAsCurrentDrawingAppearance {
                layer?.backgroundColor = NSColor.controlBackgroundColor.cgColor
                layer?.borderColor = NSColor.separatorColor.cgColor
            }
        }
    }

    private final class OptionCell: NSTableCellView {
        var onChoose: (() -> Void)?
        override func accessibilityPerformPress() -> Bool {
            guard let onChoose else { return false }
            onChoose()
            return true
        }
    }

    private final class OptionsTable: NSTableView {
        // Arrow/Return handling belongs to the one text field, not the popup.
        override var acceptsFirstResponder: Bool { false }
    }

    @MainActor
    final class Coordinator: NSObject, NSTextFieldDelegate, NSTableViewDataSource, NSTableViewDelegate, NSPopoverDelegate {
        private var owner: NativeSettingsComboBox
        private weak var control: Control?
        private var query = ""
        private var isEditing = false
        private var isOpen = false
        private var suppressFocus = false
        private var isCommitting = false
        private var isPresenting = false
        private var mouseMonitor: Any?
        private var activationObserver: NSObjectProtocol?
        private let popover = NSPopover()
        private let table = OptionsTable()
        private(set) var visibleOptions: [Option] = []
        private(set) var activeIndex: Int?

        init(_ owner: NativeSettingsComboBox) {
            self.owner = owner
            super.init()
            let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("option"))
            table.addTableColumn(column)
            table.headerView = nil
            table.autoresizingMask = [.width]
            table.columnAutoresizingStyle = .uniformColumnAutoresizingStyle
            table.intercellSpacing = .zero
            table.backgroundColor = .clear
            table.dataSource = self
            table.delegate = self
            table.target = self
            table.action = #selector(clickedOption(_:))
            table.setAccessibilityRole(.list)
            let scroll = NSScrollView()
            scroll.hasVerticalScroller = true
            scroll.drawsBackground = false
            scroll.documentView = table
            let content = NSViewController()
            content.view = scroll
            popover.contentViewController = content
            // Typing in the anchor field must not dismiss a transient popup.
            popover.behavior = .applicationDefined
            popover.animates = false
            popover.delegate = self
        }

        func update(_ owner: NativeSettingsComboBox, control: Control, enabled: Bool) {
            self.owner = owner
            self.control = control
            control.field.delegate = self
            control.field.onFocus = { [weak self] in self?.scheduleOpen() }
            control.arrow.target = self
            control.arrow.action = #selector(toggleOptions(_:))
            control.field.isEnabled = enabled
            control.arrow.isEnabled = enabled
            control.field.placeholderString = owner.placeholder
            control.field.setAccessibilityLabel(owner.title)
            control.field.setAccessibilityHelp("Введите текст для фильтрации. Стрелки выбирают вариант, Return подтверждает, Escape отменяет.")
            control.field.setAccessibilityLinkedUIElements([table])
            table.setAccessibilityLabel("Варианты: " + owner.title)
            if !enabled { close() }
            if !isEditing && !isOpen { restoreLabel() }
            refresh()
        }

        private func refresh() {
            let activeID = activeIndex.flatMap { visibleOptions.indices.contains($0) ? visibleOptions[$0].id : nil }
            visibleOptions = owner.options.filter { query.isEmpty || $0.label.localizedStandardContains(query) || $0.id.localizedStandardContains(query) }
            activeIndex = activeID.flatMap { id in visibleOptions.firstIndex { $0.id == id } }
            table.reloadData()
            updateHighlight()
            if let control {
                let width = max(120, control.bounds.width)
                table.frame.size.width = width
                popover.contentSize = NSSize(width: width, height: min(256, (0..<max(1, visibleOptions.count)).reduce(0) { $0 + rowHeight($1, width: width) }))
            }
            if popover.isShown && visibleOptions.isEmpty {
                NSAccessibility.post(element: table, notification: .announcementRequested, userInfo: [.announcement: emptyMessage, .priority: NSAccessibilityPriorityLevel.medium.rawValue])
            }
        }

        private var emptyMessage: String { owner.options.isEmpty ? "Список пока недоступен" : "Ничего не найдено" }

        private func scheduleOpen() {
            guard !suppressFocus else { return }
            DispatchQueue.main.async { [weak self] in
                guard let self, !self.suppressFocus, self.control?.field.currentEditor() != nil else { return }
                self.open()
            }
        }

        func open() {
            guard let control, control.field.isEnabled else { return }
            if !isOpen && !isEditing {
                query = ""
                refresh()
                activeIndex = visibleOptions.firstIndex { $0.id == owner.selectedID }
                updateHighlight()
            }
            isOpen = true
            guard !popover.isShown, control.window?.isVisible == true else { return }
            isPresenting = true
            popover.show(relativeTo: control.bounds, of: control, preferredEdge: .minY)
            control.field.setAccessibilityExpanded(true)
            suppressFocus = true
            control.window?.makeKey()
            control.window?.makeFirstResponder(control.field)
            suppressFocus = false
            isPresenting = false
            // Observe only clicks; keyboard input remains with the anchor field.
            mouseMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] event in
                guard let self, let control = self.control else { return event }
                if event.window === self.popover.contentViewController?.view.window { return event }
                if event.window === control.window && control.bounds.contains(control.convert(event.locationInWindow, from: nil)) { return event }
                self.close()
                return event
            }
            activationObserver = NotificationCenter.default.addObserver(forName: NSApplication.didResignActiveNotification, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.close() }
            }
        }

        @objc private func toggleOptions(_ sender: NSButton) {
            if popover.isShown { close(); return }
            suppressFocus = true
            control?.window?.makeFirstResponder(control?.field)
            suppressFocus = false
            open()
        }

        func controlTextDidChange(_ notification: Notification) {
            guard let control, control.field.isEnabled, notification.object as? NSTextField === control.field else { return }
            isEditing = true
            query = control.field.stringValue
            owner.filter?.wrappedValue = query
            activeIndex = nil
            refresh()
            open()
        }

        func control(_ field: NSControl, textView: NSTextView, doCommandBy commandSelector: Selector) -> Bool {
            guard control?.field === field, !textView.hasMarkedText() else { return false }
            switch commandSelector {
            case #selector(NSResponder.moveDown(_:)), #selector(NSResponder.moveUp(_:)):
                open()
                guard !visibleOptions.isEmpty else { return true }
                let direction = commandSelector == #selector(NSResponder.moveDown(_:)) ? 1 : -1
                activeIndex = min(visibleOptions.count - 1, max(0, (activeIndex ?? (direction > 0 ? -1 : visibleOptions.count)) + direction))
                updateHighlight()
                if let activeIndex, let field = control?.field {
                    NSAccessibility.post(element: field, notification: .announcementRequested, userInfo: [.announcement: visibleOptions[activeIndex].label, .priority: NSAccessibilityPriorityLevel.medium.rawValue])
                }
                return true
            case #selector(NSResponder.insertNewline(_:)):
                guard isOpen else { return false }
                choose(index: activeIndex ?? 0)
                return true
            case #selector(NSResponder.cancelOperation(_:)):
                close()
                return true
            case #selector(NSResponder.insertTab(_:)), #selector(NSResponder.insertBacktab(_:)):
                close()
                return false
            default: return false
            }
        }

        func controlTextDidEndEditing(_ notification: Notification) {
            guard !isPresenting, !isCommitting, notification.object as? NSTextField === control?.field else { return }
            // Let an option's mouse/AX action finish before cancelling a blur.
            DispatchQueue.main.async { [weak self] in
                guard let self, self.control?.field.currentEditor() == nil else { return }
                self.close()
            }
        }

        private func updateHighlight() {
            if let index = activeIndex, visibleOptions.indices.contains(index) {
                table.selectRowIndexes(IndexSet(integer: index), byExtendingSelection: false)
                table.scrollRowToVisible(index)
            } else { table.deselectAll(nil) }
        }

        @objc private func clickedOption(_ sender: NSTableView) { choose(index: sender.clickedRow) }

        func choose(index: Int) {
            guard isOpen, let control, control.field.isEnabled,
                  (control.field.currentEditor() as? NSTextView)?.hasMarkedText() != true,
                  visibleOptions.indices.contains(index) else { return }
            let option = visibleOptions[index]
            guard owner.options.contains(where: { $0.id == option.id }) else { return }
            isCommitting = true
            isEditing = false
            query = ""
            control.field.stringValue = option.label
            if let filter = owner.filter { filter.wrappedValue = option.label }
            else if option.id != owner.selectedID {
                owner.selectedID = option.id
                owner.onSelect(option.id)
            }
            close()
            isCommitting = false
            suppressFocus = true
            control.window?.makeKey()
            control.window?.makeFirstResponder(control.field)
            suppressFocus = false
        }

        func close() {
            isOpen = false
            activeIndex = nil
            if popover.isShown { popover.performClose(nil) }
            stopObserving()
            control?.field.setAccessibilityExpanded(false)
            if !isCommitting { restoreLabel() }
        }

        func popoverDidClose(_ notification: Notification) { close() }

        private func restoreLabel() {
            isEditing = false
            query = ""
            activeIndex = nil
            control?.field.stringValue = owner.filter?.wrappedValue ?? owner.options.first(where: { $0.id == owner.selectedID })?.label ?? ""
        }

        private func stopObserving() {
            if let mouseMonitor { NSEvent.removeMonitor(mouseMonitor); self.mouseMonitor = nil }
            if let activationObserver { NotificationCenter.default.removeObserver(activationObserver); self.activationObserver = nil }
        }

        func detach() {
            close()
            control?.field.onFocus = nil
            control?.field.delegate = nil
            control = nil
        }

        func numberOfRows(in tableView: NSTableView) -> Int { max(1, visibleOptions.count) }
        func tableView(_ tableView: NSTableView, shouldSelectRow row: Int) -> Bool { visibleOptions.indices.contains(row) }
        func tableView(_ tableView: NSTableView, heightOfRow row: Int) -> CGFloat { rowHeight(row, width: popover.contentSize.width) }
        private func rowHeight(_ row: Int, width: CGFloat) -> CGFloat {
            let label = visibleOptions.indices.contains(row) ? visibleOptions[row].label : emptyMessage
            return max(32, ceil((label as NSString).boundingRect(with: NSSize(width: max(80, width - 24), height: .greatestFiniteMagnitude), options: [.usesLineFragmentOrigin], attributes: [.font: NSFont.systemFont(ofSize: 13)]).height) + 12)
        }
        func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
            let label = NSTextField(wrappingLabelWithString: visibleOptions.indices.contains(row) ? visibleOptions[row].label : emptyMessage)
            label.font = .systemFont(ofSize: 13)
            label.textColor = visibleOptions.isEmpty ? .secondaryLabelColor : .labelColor
            let cell = OptionCell()
            cell.setAccessibilityElement(true)
            cell.setAccessibilityLabel(label.stringValue)
            if visibleOptions.indices.contains(row) {
                let id = visibleOptions[row].id
                cell.setAccessibilityRole(.button)
                cell.onChoose = { [weak self] in
                    guard let self, let index = self.visibleOptions.firstIndex(where: { $0.id == id }) else { return }
                    self.choose(index: index)
                }
            } else {
                cell.setAccessibilityRole(.staticText)
            }
            label.setAccessibilityElement(false)
            label.translatesAutoresizingMaskIntoConstraints = false
            cell.addSubview(label)
            NSLayoutConstraint.activate([
                label.leadingAnchor.constraint(equalTo: cell.leadingAnchor, constant: 10),
                label.trailingAnchor.constraint(equalTo: cell.trailingAnchor, constant: -10),
                label.centerYAnchor.constraint(equalTo: cell.centerYAnchor),
            ])
            cell.textField = label
            return cell
        }
    }
}
