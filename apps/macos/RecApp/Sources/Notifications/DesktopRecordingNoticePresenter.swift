import AppKit

/// Passive local feedback, independent of system notification permissions.
@MainActor
public final class DesktopRecordingNoticePresenter {
    public static let message = "Запись короче 30 секунд не сохранена"
    private var dismissal: Task<Void, Never>?
    private(set) var panel: NSPanel?

    public init() {}

    public func showShortRecordingDiscarded() {
        dismiss()
        let window = RecordingNoticePanel(
            contentRect: NSRect(x: 0, y: 0, width: 380, height: 64),
            styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false
        )
        window.level = .statusBar
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .transient]
        window.hidesOnDeactivate = false
        window.isReleasedWhenClosed = false
        window.ignoresMouseEvents = true
        window.backgroundColor = .windowBackgroundColor
        window.hasShadow = true
        window.identifier = NSUserInterfaceItemIdentifier("graf-short-recording-notice")
        let label = NSTextField(wrappingLabelWithString: Self.message)
        label.font = .systemFont(ofSize: 14)
        label.textColor = .labelColor
        label.frame = NSRect(x: 16, y: 16, width: 348, height: 36)
        window.contentView?.addSubview(label)
        if let screen = NSScreen.screens.first(where: { $0.frame.contains(NSEvent.mouseLocation) }) ?? NSScreen.main {
            let frame = screen.visibleFrame
            window.setFrameOrigin(NSPoint(x: frame.maxX - 396, y: frame.maxY - 80))
        }
        panel = window
        window.orderFrontRegardless()
        NSAccessibility.post(element: window, notification: .announcementRequested, userInfo: [
            .announcement: Self.message,
            .priority: NSAccessibilityPriorityLevel.high.rawValue
        ])
        dismissal = Task { [weak self] in
            do { try await Task.sleep(for: .seconds(6)) } catch { return }
            self?.dismiss()
        }
    }

    public func dismiss() {
        dismissal?.cancel()
        dismissal = nil
        panel?.orderOut(nil)
        panel = nil
    }
}

private final class RecordingNoticePanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}
