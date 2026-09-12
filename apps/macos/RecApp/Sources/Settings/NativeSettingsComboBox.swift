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
        var onClick: ((NSTextView) -> Void)?
        weak var optionsList: NSView?
        override func accessibilityChildren() -> [Any]? {
            let children = super.accessibilityChildren() ?? []
            return children + (optionsList.map { [$0] } ?? [])
        }
        override func becomeFirstResponder() -> Bool {
            let accepted = super.becomeFirstResponder()
            if accepted { superview?.needsDisplay = true }
            return accepted
        }
        override func mouseDown(with event: NSEvent) {
            super.mouseDown(with: event)
            if let editor = currentEditor() as? NSTextView { onClick?(editor) }
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
            field.focusRingType = .none
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
        override func draw(_ dirtyRect: NSRect) {
            super.draw(dirtyRect)
            if field.currentEditor() != nil, window?.isKeyWindow == true {
                NSGraphicsContext.saveGraphicsState()
                NSFocusRingPlacement.only.set()
                NSBezierPath(roundedRect: bounds, xRadius: 5, yRadius: 5).fill()
                NSGraphicsContext.restoreGraphicsState()
            }
        }
        override var intrinsicContentSize: NSSize { NSSize(width: 160, height: 32) }
        override func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); updateColors() }
        private func updateColors() {
            effectiveAppearance.performAsCurrentDrawingAppearance {
                layer?.backgroundColor = NSColor.controlBackgroundColor.cgColor
                layer?.borderColor = NSColor.separatorColor.cgColor
            }
        }
    }

    private final class ControlBackground: NSView {
        override init(frame: NSRect) {
            super.init(frame: frame)
            wantsLayer = true
            layer?.cornerRadius = 6
            layer?.borderWidth = 1
            layer?.masksToBounds = true
            updateColors()
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
        override func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); updateColors() }
        private func updateColors() {
            effectiveAppearance.performAsCurrentDrawingAppearance {
                layer?.backgroundColor = NSColor.controlBackgroundColor.cgColor
                layer?.borderColor = NSColor.separatorColor.cgColor
            }
        }
    }

    private final class OptionCell: NSButton {
        override init(frame: NSRect) {
            super.init(frame: frame)
            title = ""
            isBordered = false
            setButtonType(.momentaryChange)
            refusesFirstResponder = true
            focusRingType = .none
            target = self
            action = #selector(choose)
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
        // Labels must not request keyboard focus from the non-key popup panel.
        override func hitTest(_ point: NSPoint) -> NSView? { super.hitTest(point) == nil ? nil : self }
        override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
        override var needsPanelToBecomeKey: Bool { false }
        @objc private func choose() { onChoose?() }
        var onChoose: (() -> Void)?
        var savedSelection = false
        override func isAccessibilitySelected() -> Bool { savedSelection }
        override func accessibilityPerformPress() -> Bool {
            guard let onChoose else { return false }
            onChoose()
            return true
        }
    }

    private final class OptionRow: NSTableRowView {
        var active = false { didSet { needsDisplay = true } }
        var savedSelection = false
        override func isAccessibilitySelected() -> Bool { savedSelection }
        override func drawBackground(in dirtyRect: NSRect) {
            if active {
                NSColor.unemphasizedSelectedContentBackgroundColor.setFill()
                bounds.fill()
            }
        }
    }

    private final class OptionsPanel: NSPanel {
        override var canBecomeKey: Bool { false }
        override var canBecomeMain: Bool { false }
    }

    /// Geometry uses actual table row ends, including variable-height labels.
    static func popupFrame(anchor: NSRect, screen: NSRect, rowEnds: [CGFloat]) -> NSRect {
        let available = screen.insetBy(dx: 8, dy: 8)
        let below = min(available.height, max(0, anchor.minY - 4 - available.minY))
        let above = min(available.height, max(0, available.maxY - anchor.maxY - 4))
        let desired = (rowEnds.prefix(8).last ?? 32) + 2
        let opensAbove = below < desired && above > below
        let room = opensAbove ? above : below
        let fullHeight = rowEnds.prefix(8).last(where: { $0 + 2 <= room }).map { $0 + 2 }
        // Only a screen shorter than one row requires a partially visible row.
        let height = min(room, fullHeight ?? desired)
        let width = min(anchor.width, max(0, available.width))
        let y = opensAbove ? anchor.maxY + 4 : anchor.minY - 4 - height
        return NSRect(x: min(max(anchor.minX, available.minX), available.maxX - width),
                      y: min(max(y, available.minY), available.maxY - height),
                      width: width, height: height)
    }

    private final class OptionsTable: NSTableView {
        override func accessibilityChildren() -> [Any]? {
            (0..<numberOfRows).compactMap { view(atColumn: 0, row: $0, makeIfNecessary: true) }
        }
        // Arrow/Return handling belongs to the one text field, not the popup.
        override var acceptsFirstResponder: Bool { false }
    }

    @MainActor
    final class Coordinator: NSObject, NSTextFieldDelegate, NSTableViewDataSource, NSTableViewDelegate {
        private var owner: NativeSettingsComboBox
        private weak var control: Control?
        private var query = ""
        private var isEditing = false
        private var isOpen = false
        private var isCommitting = false
        private var isPresenting = false
        private var mouseMonitor: Any?
        private var observers: [NSObjectProtocol] = []
        private let panel = OptionsPanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: true)
        let scroll = NSScrollView()
        private let surface = ControlBackground()
        private var contentWidth: CGFloat = 158
        private let table = OptionsTable()
        var rowRects: [NSRect] { (0..<table.numberOfRows).map { table.rect(ofRow: $0) } }
        var viewport: NSRect { scroll.contentView.bounds }
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
            table.style = .plain
            table.intercellSpacing = .zero
            table.selectionHighlightStyle = .none
            table.backgroundColor = .clear
            table.dataSource = self
            table.delegate = self
            table.setAccessibilityElement(true)
            table.setAccessibilityRole(.list)
            scroll.hasVerticalScroller = true
            scroll.drawsBackground = false
            scroll.documentView = table
            scroll.borderType = .noBorder
            scroll.scrollerStyle = .overlay
            scroll.automaticallyAdjustsContentInsets = false
            scroll.contentInsets = NSEdgeInsetsZero
            scroll.autoresizingMask = [.width, .height]
            surface.addSubview(scroll)
            panel.contentView = surface
            panel.isOpaque = false
            panel.backgroundColor = .clear
            panel.hasShadow = true
            panel.hidesOnDeactivate = true
            panel.isReleasedWhenClosed = false
        }

        func update(_ owner: NativeSettingsComboBox, control: Control, enabled: Bool) {
            self.owner = owner
            self.control = control
            control.field.delegate = self
            control.field.onClick = { [weak self] editor in
                guard let self else { return }
                // AppKit places the caret during mouseDown; replace the saved label on typing.
                if !self.isEditing, self.owner.filter == nil, !editor.hasMarkedText(),
                   self.owner.options.contains(where: { $0.id == self.owner.selectedID && $0.label == editor.string }) {
                    editor.selectAll(nil)
                }
                self.scheduleOpen()
            }
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
            visibleOptions = owner.options.filter { query.isEmpty || $0.label.localizedStandardContains(query) || (owner.filter == nil && $0.id.localizedStandardContains(query)) }
            activeIndex = activeID.flatMap { id in visibleOptions.firstIndex { $0.id == id } }
            layoutOptions()
            updateHighlight()
            if panel.isVisible && visibleOptions.isEmpty {
                NSAccessibility.post(element: table, notification: .announcementRequested, userInfo: [.announcement: emptyMessage, .priority: NSAccessibilityPriorityLevel.medium.rawValue])
            }
        }

        private var emptyMessage: String { owner.options.isEmpty ? "Список пока недоступен" : "Ничего не найдено" }

        private func scheduleOpen() {
            DispatchQueue.main.async { [weak self] in
                guard let self, self.control?.field.currentEditor() != nil else { return }
                self.open()
            }
        }

        func open() {
            guard let control, control.field.isEnabled else { return }
            if !isOpen && !isEditing {
                query = owner.filter?.wrappedValue ?? ""
                refresh()
                activeIndex = visibleOptions.firstIndex { $0.id == owner.selectedID }
                updateHighlight()
            }
            isOpen = true
            control.field.optionsList = table
            table.setAccessibilityParent(control.field)
            NSAccessibility.post(element: control.field, notification: .layoutChanged)
            updateHighlight()
            guard !panel.isVisible, let parent = control.window, parent.isVisible else { return }
            isPresenting = true
            layoutOptions()
            updateHighlight()
            parent.addChildWindow(panel, ordered: .above)
            panel.orderFront(nil)
            control.field.setAccessibilityExpanded(true)
            control.window?.makeKey()
            control.window?.makeFirstResponder(control.field)
            isPresenting = false
            // Outside clicks or scrolling cancel; keyboard input stays with the field.
            mouseMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown, .scrollWheel]) { [weak self] event in
                guard let self, let control = self.control else { return event }
                if event.window === self.panel { return event }
                if event.type != .scrollWheel && event.window === control.window && control.bounds.contains(control.convert(event.locationInWindow, from: nil)) { return event }
                self.close()
                return event
            }
            for name in [NSWindow.didMoveNotification, NSWindow.didResizeNotification,
                         NSWindow.willCloseNotification, NSWindow.didMiniaturizeNotification,
                         NSWindow.didResignKeyNotification] {
                observe(name, object: parent)
            }
            observe(NSApplication.didResignActiveNotification, object: nil)
        }

        @objc private func toggleOptions(_ sender: NSButton) {
            if panel.isVisible { close(); return }
            control?.window?.makeFirstResponder(control?.field)
            open()
        }

        func controlTextDidBeginEditing(_ notification: Notification) { control?.needsDisplay = true }

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
            control?.needsDisplay = true
            guard !isPresenting, !isCommitting, notification.object as? NSTextField === control?.field else { return }
            // Let an option's mouse/AX action finish before cancelling a blur.
            DispatchQueue.main.async { [weak self] in
                guard let self, self.control?.field.currentEditor() == nil else { return }
                self.close()
            }
        }

        private func updateHighlight() {
            for row in 0..<table.numberOfRows {
                (table.rowView(atRow: row, makeIfNecessary: false) as? OptionRow)?.active = row == activeIndex
            }
            if isOpen, let index = activeIndex, visibleOptions.indices.contains(index) {
                table.scrollRowToVisible(index)
                let active = table.view(atColumn: 0, row: index, makeIfNecessary: true)
                control?.field.setAccessibilitySharedFocusElements(active.map { [$0] } ?? [])
            } else {
                control?.field.setAccessibilitySharedFocusElements([])
            }
        }

        private func observe(_ name: Notification.Name, object: Any?) {
            observers.append(NotificationCenter.default.addObserver(forName: name, object: object, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.close() }
            })
        }

        func layoutOptions() {
            let anchor = control.flatMap { view in view.window.map { $0.convertToScreen(view.convert(view.bounds, to: nil)) } }
                ?? NSRect(x: 0, y: 400, width: max(120, control?.bounds.width ?? 160), height: 32)
            let screen = control?.window?.screen?.visibleFrame ?? NSRect(x: -1000, y: -1000, width: 3000, height: 3000)
            contentWidth = max(1, min(anchor.width, screen.width - 16) - 2)
            table.frame.size.width = contentWidth
            table.tableColumns.first?.width = contentWidth
            table.reloadData()
            table.layoutSubtreeIfNeeded()
            let frame = NativeSettingsComboBox.popupFrame(anchor: anchor, screen: screen, rowEnds: rowRects.map(\.maxY))
            panel.setFrame(frame, display: false)
            scroll.frame = NSRect(origin: NSPoint(x: 1, y: 1), size: NSSize(width: contentWidth, height: max(0, frame.height - 2)))
            scroll.tile()
            // A new query must start at its first result, even after scrolling the old catalog.
            scroll.contentView.scroll(to: .zero)
            scroll.reflectScrolledClipView(scroll.contentView)
        }

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
            control.window?.makeKey()
            control.window?.makeFirstResponder(control.field)
        }

        func close() {
            isOpen = false
            activeIndex = nil
            panel.parent?.removeChildWindow(panel)
            panel.orderOut(nil)
            stopObserving()
            control?.field.optionsList = nil
            table.setAccessibilityParent(nil)
            control?.field.setAccessibilitySharedFocusElements([])
            control?.field.setAccessibilityExpanded(false)
            if let field = control?.field { NSAccessibility.post(element: field, notification: .layoutChanged) }
            control?.needsDisplay = true
            if !isCommitting { restoreLabel() }
        }

        private func restoreLabel() {
            isEditing = false
            query = owner.filter?.wrappedValue ?? ""
            activeIndex = nil
            control?.field.stringValue = owner.filter?.wrappedValue ?? owner.options.first(where: { $0.id == owner.selectedID })?.label ?? ""
        }

        private func stopObserving() {
            if let mouseMonitor { NSEvent.removeMonitor(mouseMonitor); self.mouseMonitor = nil }
            observers.forEach(NotificationCenter.default.removeObserver)
            observers.removeAll()
        }

        func detach() {
            close()
            control?.field.onClick = nil
            control?.field.delegate = nil
            control = nil
        }

        func numberOfRows(in tableView: NSTableView) -> Int { max(1, visibleOptions.count) }
        func tableView(_ tableView: NSTableView, shouldSelectRow row: Int) -> Bool { visibleOptions.indices.contains(row) }
        func tableView(_ tableView: NSTableView, heightOfRow row: Int) -> CGFloat { rowHeight(row, width: contentWidth) }
        private func rowHeight(_ row: Int, width: CGFloat) -> CGFloat {
            let label = visibleOptions.indices.contains(row) ? visibleOptions[row].label : emptyMessage
            return max(32, ceil((label as NSString).boundingRect(with: NSSize(width: max(1, width - (owner.filter == nil ? 44 : 20)), height: .greatestFiniteMagnitude), options: [.usesLineFragmentOrigin], attributes: [.font: NSFont.systemFont(ofSize: 13)]).height) + 12)
        }
        func tableView(_ tableView: NSTableView, rowViewForRow row: Int) -> NSTableRowView? {
            let view = OptionRow()
            view.active = row == activeIndex
            view.savedSelection = isSaved(row)
            return view
        }

        private func isSaved(_ row: Int) -> Bool {
            owner.filter == nil && visibleOptions.indices.contains(row) && visibleOptions[row].id == owner.selectedID
        }

        func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
            let label = NSTextField(wrappingLabelWithString: visibleOptions.indices.contains(row) ? visibleOptions[row].label : emptyMessage)
            label.font = .systemFont(ofSize: 13)
            label.textColor = visibleOptions.isEmpty ? .secondaryLabelColor : .labelColor
            let cell = OptionCell()
            cell.savedSelection = isSaved(row)
            let check = NSTextField(labelWithString: isSaved(row) ? "✓" : "")
            check.font = .systemFont(ofSize: 13)
            check.setAccessibilityElement(false)
            check.translatesAutoresizingMaskIntoConstraints = false
            cell.addSubview(check)
            cell.setAccessibilityElement(true)
            cell.setAccessibilityParent(table)
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
                check.leadingAnchor.constraint(equalTo: cell.leadingAnchor, constant: 10),
                check.widthAnchor.constraint(equalToConstant: 14),
                check.centerYAnchor.constraint(equalTo: cell.centerYAnchor),
                label.leadingAnchor.constraint(equalTo: cell.leadingAnchor, constant: owner.filter == nil ? 34 : 10),
                label.trailingAnchor.constraint(equalTo: cell.trailingAnchor, constant: -10),
                label.centerYAnchor.constraint(equalTo: cell.centerYAnchor),
            ])
            return cell
        }
    }
}
