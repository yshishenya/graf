import AppKit
import Foundation

public enum DesktopNotificationCardAction: Equatable, Sendable {
    case join, joinAndRecord, record
    case openRecording(String)
    case skipRecordingPrompt
    case toggleRecordingPromptRemember(Bool)
}

/// Semantic content only. Decisions, event identity and priority belong to the owner.
public enum DesktopNotificationCardContent: Equatable, Sendable {
    case meeting(title: String, startText: String, hasJoinLink: Bool)
    case recordingPrompt(displayName: String, remainingSeconds: Int, rememberChoice: Bool)
    case problem(title: String, message: String, actionTitle: String, sessionID: String?)
    case preview(title: String, message: String)
    case shortRecording

    public var identifier: String {
        switch self {
        case .meeting: return "graf.card.meeting"
        case .recordingPrompt: return "graf.card.recording-prompt"
        case .problem: return "graf.card.problem"
        case .preview: return "graf.card.preview"
        case .shortRecording: return "graf.card.short-recording"
        }
    }
    fileprivate var text: (title: String, message: String) {
        switch self {
        case let .meeting(title, startText, _): return (title, startText)
        case let .recordingPrompt(name, seconds, _):
            let count = max(0, seconds)
            let ending: String
            if (11...14).contains(count % 100) { ending = "секунд" }
            else if count % 10 == 1 { ending = "секунду" }
            else if (2...4).contains(count % 10) { ending = "секунды" }
            else { ending = "секунд" }
            return ("Встреча в \(name)", "Запись начнётся через \(count) \(ending)")
        case let .problem(title, message, _, _), let .preview(title, message): return (title, message)
        case .shortRecording: return ("", "Запись не сохранена — короче 30 секунд")
        }
    }
    public var accessibilitySummary: String {
        [text.title, text.message].filter { !$0.isEmpty }
            .map { $0.hasSuffix(".") ? $0 : $0 + "." }.joined(separator: " ")
    }
    fileprivate var actions: [(title: String, action: DesktopNotificationCardAction, primary: Bool)] {
        switch self {
        case let .meeting(_, _, linked):
            return linked ? [("Подключиться", .join, false), ("Подключиться и начать запись", .joinAndRecord, true)]
                : [("Начать запись", .record, true)]
        case .recordingPrompt: return [("Не записывать", .skipRecordingPrompt, false), ("Записать", .record, true)]
        case let .problem(_, _, title, session):
            guard !title.isEmpty, let session else { return [] }
            return [(title, .openRecording(session), true)]
        case .preview, .shortRecording: return []
        }
    }
    fileprivate var checkboxTitle: String? {
        if case let .recordingPrompt(name, _, _) = self { return "Запомнить выбор для \(name)" }
        return nil
    }
    fileprivate var remembers: Bool {
        if case let .recordingPrompt(_, _, value) = self { return value }
        return false
    }
    fileprivate var allowsHold: Bool {
        switch self {
        case .preview, .problem, .shortRecording: return true
        case .meeting, .recordingPrompt: return false
        }
    }
    fileprivate var iconName: String? {
        switch self {
        case .meeting: return "calendar"
        case .recordingPrompt: return "record.circle"
        case .problem: return "exclamationmark.triangle"
        case .preview: return "bell"
        case .shortRecording: return nil
        }
    }
}

struct NotificationCardScreen: Equatable {
    var id: UInt32
    var frame: NSRect
    var visibleFrame: NSRect
    var isMain: Bool = false
}

@MainActor
struct NotificationCardEnvironment {
    var now: () -> Date = Date.init
    var screens: () -> [NotificationCardScreen] = {
        NSScreen.screens.compactMap { screen in
            guard let id = screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber else { return nil }
            return NotificationCardScreen(id: id.uint32Value, frame: screen.frame,
                                          visibleFrame: screen.visibleFrame, isMain: screen === NSScreen.main)
        }
    }
    var mouseLocation: () -> NSPoint = { NSEvent.mouseLocation }
    // AppKit may complete, delay, or deny an explicit activation request.
    // Keep that OS boundary injectable without substituting key-window state.
    var requestActivation: () -> Void = { NSApp.activate() }
    var requestKeyWindow: (NSWindow) -> Void = { $0.makeKeyAndOrderFront(nil) }
    var announce: (NSWindow, String) -> Void = { window, text in
        NSAccessibility.post(element: window, notification: .announcementRequested,
                             userInfo: [.announcement: text, .priority: NSAccessibilityPriorityLevel.high.rawValue])
    }
    var automaticallyTicks = true
    var fontScale: CGFloat = 1
}

/// Owns exactly one panel and ticker. Never starts recording or requests permissions.
@MainActor
public final class DesktopNotificationCardPresenter {
    public static let cardWidth: CGFloat = 380
    public static let horizontalMargin: CGFloat = 14
    public static let topPadding: CGFloat = 14
    public static let bottomPadding: CGFloat = 14
    public static let previewDisplayDuration: TimeInterval = 6
    public static let recordingPromptDisplayDuration: TimeInterval = 8
    public static let noticeDisplayDuration: TimeInterval = 20

    /// Visible GRAF controls, in global screen coordinates. No foreign-window discovery.
    public var protectedFramesProvider: () -> [NSRect] = { [] }
    public var isVisible: Bool { panel?.isVisible == true }
    public private(set) var presentedContent: DesktopNotificationCardContent?
    var window: NSWindow? { panel }
    private(set) var selectedScreenID: UInt32?
    private(set) var deadline: Date?

    private let environment: NotificationCardEnvironment
    private var panel: DesktopNotificationCardPanel?
    private var ticker: Task<Void, Never>?
    private var generation = 0
    private var onAction: ((DesktopNotificationCardAction) -> Void)?
    private var onTick: (() -> DesktopNotificationCardContent?)?
    private var onExpire: (() -> Void)?
    private var onClose: (() -> Void)?
    private var onInvalidated: (() -> Void)?
    private var hovered = false
    private var focused = false
    private var holdStarted: Date?
    private var lastTickAt: Date?
    private weak var previousKeyWindow: NSWindow?
    private var previousApplication: NSRunningApplication?
    private var observations: NotificationCardObservations?
    private var focusRequestID = 0
    private var pendingFocus: (generation: Int, requestID: Int)?
    private var focusObservations: NotificationCardObservations?
    private var focusTimeout: DispatchWorkItem?

    public convenience init() { self.init(environment: .init()) }
    init(environment: NotificationCardEnvironment) { self.environment = environment }
    deinit { ticker?.cancel() }

    @discardableResult
    public func present(_ content: DesktopNotificationCardContent,
                        dismissAfter: Date? = nil,
                        onAction: @escaping (DesktopNotificationCardAction) -> Void,
                        onTick: (() -> DesktopNotificationCardContent?)? = nil,
                        onExpire: (() -> Void)? = nil,
                        onClose: (() -> Void)? = nil,
                        onInvalidated: (() -> Void)? = nil) -> Bool {
        let requestedAt = environment.now()
        guard dismissAfter.map({ $0 > requestedAt }) ?? true,
              let screen = initialScreen(), let placement = placement(content, screen: screen) else { return false }
        if panel != nil {
            invalidate()
            // A callback may have installed another event; never dismiss its window.
            guard panel == nil else { return false }
        }
        generation += 1
        let token = generation
        let window = DesktopNotificationCardPanel(contentRect: placement.frame,
            styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        window.level = .statusBar
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .transient]
        window.hidesOnDeactivate = false
        window.isReleasedWhenClosed = false
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = true
        window.isMovable = false
        window.becomesKeyOnlyIfNeeded = true
        window.autorecalculatesKeyViewLoop = false
        window.identifier = NSUserInterfaceItemIdentifier("graf-notification-card")
        let view = DesktopNotificationCardView(content: content, width: placement.width,
            height: placement.height, scale: environment.fontScale,
            onAction: { [weak self] action in self?.act(action, token: token) },
            onClose: { [weak self] in self?.close(token: token) },
            onHover: { [weak self] value in self?.setHovered(value, token: token) })
        window.contentView = view
        window.closeAction = { [weak self] in self?.close(token: token) }
        window.focusChanged = { [weak self] value in self?.setFocused(value, token: token) }
        self.onAction = onAction; self.onTick = onTick; self.onExpire = onExpire
        self.onClose = onClose; self.onInvalidated = onInvalidated
        presentedContent = content
        selectedScreenID = screen.id
        panel = window
        window.setFrame(placement.frame, display: false)
        view.layoutSubtreeIfNeeded()
        window.orderFrontRegardless()
        guard window.isVisible else { clear(); return false }
        view.configureKeyLoop()
        // The prompt's budget starts only when the panel is actually visible.
        if case .recordingPrompt = content, let dismissAfter {
            deadline = environment.now().addingTimeInterval(dismissAfter.timeIntervalSince(requestedAt))
        } else { deadline = dismissAfter }
        lastTickAt = environment.now()
        reconcileHold()
        observeLifecycle(token: token)
        environment.announce(window, content.accessibilitySummary)
        startTicker(token: token)
        return true
    }

    /// Update the same event only. Changes of domain identity require explicit invalidation.
    @discardableResult
    public func update(_ content: DesktopNotificationCardContent) -> Bool {
        guard let old = presentedContent, old.identifier == content.identifier,
              let view = panel?.contentView as? DesktopNotificationCardView else { return false }
        guard let screen = currentScreen(), let placement = placement(content, screen: screen) else {
            invalidate(); return false
        }
        presentedContent = content
        selectedScreenID = screen.id
        view.update(content, width: placement.width, height: placement.height)
        panel?.setFrame(placement.frame, display: true)
        return true
    }

    public func dismiss() { clear() }

    public func invalidate() {
        guard panel != nil else { return }
        let callback = onInvalidated
        clear()
        callback?()
    }

    /// Call after the registered Stop marker or its window changes frame/visibility.
    public func reposition() {
        guard let content = presentedContent else { return }
        _ = update(content)
    }

    /// Accepts an explicit focus request. Activation is asynchronous: true does
    /// not guarantee that macOS has already made the panel key (or will allow it).
    @discardableResult
    public func focus() -> Bool {
        guard let panel, panel.isVisible, NSApp.activationPolicy() != .prohibited else { return false }
        if !panel.explicitFocus {
            previousKeyWindow = NSApp.keyWindow
            previousApplication = NSWorkspace.shared.frontmostApplication
        }
        cancelPendingFocus()
        panel.explicitFocus = true
        focusRequestID += 1
        let requestID = focusRequestID
        let token = generation
        pendingFocus = (token, requestID)
        let observer = NotificationCardObservations()
        observer.add(NotificationCenter.default, name: NSApplication.didBecomeActiveNotification) { [weak self] in
            self?.completeFocus(token: token, requestID: requestID)
        }
        focusObservations = observer
        // Denied activation must not leave a request that steals focus on an
        // unrelated later activation. This is a one-shot cancellation, not polling.
        let timeout = DispatchWorkItem { [weak self] in
            MainActor.assumeIsolated {
                guard let self, self.pendingFocus?.generation == token,
                      self.pendingFocus?.requestID == requestID else { return }
                self.cancelPendingFocus()
            }
        }
        focusTimeout = timeout
        DispatchQueue.main.asyncAfter(deadline: .now() + 2, execute: timeout)
        if !NSApp.isActive { environment.requestActivation() }
        // Selecting the eligible panel can itself complete AppKit activation.
        // Do not make isActive a prerequisite: that creates a circular wait for
        // apps whose only visible window is this nonactivating panel.
        completeFocus(token: token, requestID: requestID)
        // One deferred attempt also covers an already-active app while its tray
        // menu is unwinding. All later activation work is notification-driven.
        DispatchQueue.main.async { [weak self] in self?.completeFocus(token: token, requestID: requestID) }
        return true
    }

    private func completeFocus(token: Int, requestID: Int) {
        guard generation == token, pendingFocus?.generation == token,
              pendingFocus?.requestID == requestID else { return }
        guard let panel, panel.isVisible, panel.explicitFocus,
              let view = panel.contentView as? DesktopNotificationCardView else {
            cancelPendingFocus(); return
        }
        view.configureKeyLoop()
        environment.requestKeyWindow(panel)
        guard generation == token, self.panel === panel, panel.isKeyWindow else { return }
        view.configureKeyLoop()
        guard panel.makeFirstResponder(view.closeButton) else { cancelPendingFocus(); return }
        cancelPendingFocus()
        setFocused(true, token: token)
    }

    private func cancelPendingFocus() {
        pendingFocus = nil
        focusObservations = nil
        focusTimeout?.cancel(); focusTimeout = nil
        if panel?.isKeyWindow != true { panel?.explicitFocus = false }
    }

    public func refresh() {
        guard panel != nil else { return }
        guard panel?.isVisible == true else { invalidate(); return }
        let token = generation
        let now = environment.now()
        if case .recordingPrompt? = presentedContent, let lastTickAt {
            let gap = now.timeIntervalSince(lastTickAt)
            // A delayed tick after sleep/lock must not win a race with the lifecycle observer.
            guard gap >= 0, gap <= 2.5 else { invalidate(); return }
        }
        lastTickAt = now
        if holdStarted == nil, let deadline, environment.now() >= deadline {
            let callback = onExpire
            clear()
            callback?()
            return
        }
        guard let onTick else { return }
        let next = onTick()
        guard generation == token, panel != nil else { return }
        guard let next else { invalidate(); return }
        _ = update(next)
    }

    private func act(_ action: DesktopNotificationCardAction, token: Int) {
        guard token == generation, panel != nil else { return }
        if case let .toggleRecordingPromptRemember(value) = action {
            guard case let .recordingPrompt(name, seconds, _)? = presentedContent else { return }
            guard update(.recordingPrompt(displayName: name, remainingSeconds: seconds, rememberChoice: value)) else { return }
            onAction?(action)
            return
        }
        let callback = onAction
        clear()
        callback?(action)
    }

    private func close(token: Int) {
        guard generation == token, panel != nil else { return }
        let callback = onClose
        clear()
        callback?()
    }

    private func clear() {
        let old = panel
        let restore = old?.isKeyWindow == true && old?.explicitFocus == true
        let previousWindow = previousKeyWindow
        let previousApp = previousApplication
        cancelPendingFocus()
        generation += 1
        let clearedGeneration = generation
        ticker?.cancel(); ticker = nil
        observations = nil
        panel = nil; presentedContent = nil; selectedScreenID = nil; deadline = nil
        onAction = nil; onTick = nil; onExpire = nil; onClose = nil; onInvalidated = nil
        hovered = false; focused = false; holdStarted = nil; lastTickAt = nil
        previousKeyWindow = nil; previousApplication = nil
        old?.closeAction = nil; old?.focusChanged = nil
        // A card's native window is single-use. Clear its full-screen behavior
        // before close() orders it out; clearing after orderOut() can leave the
        // native panel retained. The next card keeps its own Spaces settings.
        old?.collectionBehavior = []
        old?.close()
        old?.contentView = nil
        // A native willClose observer may have installed (and even dismissed)
        // another card. Never restore an older focus context across that event.
        if restore, generation == clearedGeneration, panel == nil {
            if let previousWindow, previousWindow.isVisible { previousWindow.makeKey() }
            else if let previousApp, previousApp.processIdentifier != ProcessInfo.processInfo.processIdentifier {
                previousApp.activate(options: [])
            }
        }
    }

    private func startTicker(token: Int) {
        guard environment.automaticallyTicks, deadline != nil || onTick != nil else { return }
        ticker = Task { [weak self] in
            while !Task.isCancelled {
                do { try await Task.sleep(for: .seconds(1)) } catch { return }
                guard let self, self.generation == token else { return }
                self.refresh()
            }
        }
    }
    func setHovered(_ value: Bool) { setHovered(value, token: generation) }
    private func setHovered(_ value: Bool, token: Int) {
        guard generation == token, panel != nil else { return }
        hovered = value; reconcileHold()
    }
    private func setFocused(_ value: Bool, token: Int) {
        guard generation == token, panel != nil else { return }
        focused = value; reconcileHold()
    }
    private func reconcileHold() {
        guard presentedContent?.allowsHold == true, let deadline else { return }
        let now = environment.now()
        if hovered || focused {
            if holdStarted == nil {
                if now >= deadline { refresh() }
                else { holdStarted = now }
            }
        } else if let started = holdStarted {
            self.deadline = deadline.addingTimeInterval(max(0, now.timeIntervalSince(started)))
            holdStarted = nil
        }
    }

    private func initialScreen() -> NotificationCardScreen? {
        let screens = environment.screens()
        return screens.first { $0.frame.contains(environment.mouseLocation()) } ?? screens.first { $0.isMain } ?? screens.first
    }
    private func currentScreen() -> NotificationCardScreen? {
        let screens = environment.screens()
        return screens.first { $0.id == selectedScreenID } ?? screens.first { $0.isMain } ?? screens.first
    }
    private struct Placement { var frame: NSRect; var width: CGFloat; var height: CGFloat }
    private func placement(_ content: DesktopNotificationCardContent, screen: NotificationCardScreen) -> Placement? {
        let allowed = screen.visibleFrame.insetBy(dx: 8, dy: 8)
        let width = min(Self.cardWidth, allowed.width - Self.horizontalMargin * 2)
        guard width >= 220 else { return nil }
        let layout = DesktopNotificationCardView.measure(content, width: width, scale: environment.fontScale)
        let surfaceWidth = width + Self.horizontalMargin * 2
        let x = allowed.maxX - surfaceWidth
        var top = allowed.maxY
        let protected = protectedFramesProvider().filter { !$0.isEmpty }
        for _ in 0...protected.count {
            let available = top - allowed.minY - Self.topPadding - Self.bottomPadding
            guard available >= layout.minimumHeight else { return nil }
            let height = min(layout.height, available)
            let frame = NSRect(x: x, y: top - height - Self.topPadding - Self.bottomPadding,
                               width: surfaceWidth, height: height + Self.topPadding + Self.bottomPadding)
            if let collision = protected.filter({ frame.intersects($0) }).min(by: { $0.minY < $1.minY }) {
                top = min(top, collision.minY - 8)
                continue
            }
            guard allowed.contains(frame) else { return nil }
            return Placement(frame: frame, width: width, height: height)
        }
        return nil
    }

    private func observeLifecycle(token: Int) {
        let observations = NotificationCardObservations()
        observations.add(NotificationCenter.default, name: NSApplication.didChangeScreenParametersNotification) { [weak self] in
            guard let self, self.generation == token else { return }
            self.reposition()
        }
        observations.add(NSWorkspace.shared.notificationCenter, name: NSWorkspace.willSleepNotification) { [weak self] in
            guard let self, self.generation == token else { return }
            self.invalidate()
        }
        observations.add(NSWorkspace.shared.notificationCenter, name: NSWorkspace.sessionDidResignActiveNotification) { [weak self] in
            guard let self, self.generation == token else { return }
            self.invalidate()
        }
        self.observations = observations
    }

}

private final class NotificationCardObservations {
    private var tokens: [(NotificationCenter, NSObjectProtocol)] = []
    @MainActor func add(_ center: NotificationCenter, name: Notification.Name,
                        handler: @escaping @MainActor @Sendable () -> Void) {
        let token = center.addObserver(forName: name, object: nil, queue: .main) { _ in
            MainActor.assumeIsolated { handler() }
        }
        tokens.append((center, token))
    }
    deinit { for (center, token) in tokens { center.removeObserver(token) } }
}

private final class DesktopNotificationCardPanel: NSPanel {
    var explicitFocus = false
    var closeAction: (() -> Void)?
    var focusChanged: ((Bool) -> Void)?
    override var canBecomeKey: Bool { explicitFocus }
    override var canBecomeMain: Bool { false }
    override func becomeKey() { super.becomeKey(); focusChanged?(true) }
    override func resignKey() { super.resignKey(); focusChanged?(false) }
    override func cancelOperation(_ sender: Any?) { if isKeyWindow { closeAction?() } }
    override func selectNextKeyView(_ sender: Any?) {
        guard explicitFocus, let current = firstResponder as? NSView,
              let view = contentView as? DesktopNotificationCardView,
              let next = view.keyView(relativeTo: current, backwards: false) else { super.selectNextKeyView(sender); return }
        makeFirstResponder(next)
    }
    override func selectPreviousKeyView(_ sender: Any?) {
        guard explicitFocus, let current = firstResponder as? NSView,
              let view = contentView as? DesktopNotificationCardView,
              let previous = view.keyView(relativeTo: current, backwards: true) else { super.selectPreviousKeyView(sender); return }
        makeFirstResponder(previous)
    }
    override func sendEvent(_ event: NSEvent) {
        // Keep the card's explicit keyboard contract independent of the user's
        // system-wide Full Keyboard Access preference and NSButton cell handling.
        if isKeyWindow, event.type == .keyDown,
           event.modifierFlags.intersection([.command, .control, .option]).isEmpty,
           [48, 53, 36, 76, 49].contains(event.keyCode) {
            keyDown(with: event)
            return
        }
        super.sendEvent(event)
    }
    override func keyDown(with event: NSEvent) {
        guard isKeyWindow else { return }
        if event.keyCode == 53 { closeAction?(); return }
        if event.keyCode == 48 {
            if event.modifierFlags.contains(.shift) { selectPreviousKeyView(nil) }
            else { selectNextKeyView(nil) }
            return
        }
        if [36, 76, 49].contains(event.keyCode), let button = firstResponder as? NSButton {
            button.performClick(nil); return
        }
        super.keyDown(with: event)
    }
}

/// Frame-based layout preserves the native controls and their AX identity across ticks.
public final class DesktopNotificationCardView: NSView {
    private let card = CardBackgroundView(cornerRadius: 12)
    private let close = NotificationCardCloseButton()
    private let textScroll = NotificationCardScrollView()
    private let textDocument = NotificationCardFlippedView()
    private let icon = NSImageView()
    private let titleLabel = NSTextField(wrappingLabelWithString: "")
    private let messageLabel = NSTextField(wrappingLabelWithString: "")
    private let remember = NotificationCardCheckbox(checkboxWithTitle: "", target: nil, action: nil)
    private var actionButtons: [NotificationCardButton] = []
    private var content: DesktopNotificationCardContent
    private let scale: CGFloat
    private let onAction: (DesktopNotificationCardAction) -> Void
    private let onClose: () -> Void
    private let onHover: (Bool) -> Void
    private var tracking: NSTrackingArea?
    var closeButton: NSButton? { close }
    override public var isFlipped: Bool { true }

    init(content: DesktopNotificationCardContent, width: CGFloat, height: CGFloat, scale: CGFloat,
         onAction: @escaping (DesktopNotificationCardAction) -> Void,
         onClose: @escaping () -> Void, onHover: @escaping (Bool) -> Void) {
        self.content = content; self.scale = scale
        self.onAction = onAction; self.onClose = onClose; self.onHover = onHover
        super.init(frame: NSRect(x: 0, y: 0, width: width + 28, height: height + 28))
        addSubview(card); addSubview(close)
        close.target = self; close.action = #selector(closeTapped)
        textScroll.drawsBackground = false
        textScroll.borderType = .noBorder
        textScroll.autohidesScrollers = true
        textScroll.documentView = textDocument
        card.addSubview(textScroll); card.addSubview(remember)
        remember.target = self; remember.action = #selector(rememberChanged)
        remember.setAccessibilityElement(true)
        remember.setAccessibilityRole(.checkBox)
        textDocument.addSubview(icon); textDocument.addSubview(titleLabel); textDocument.addSubview(messageLabel)
        titleLabel.identifier = NSUserInterfaceItemIdentifier("graf.notification.title")
        messageLabel.identifier = NSUserInterfaceItemIdentifier("graf.notification.message")
        for label in [titleLabel, messageLabel] {
            label.isSelectable = false
            label.usesSingleLineMode = false
            label.maximumNumberOfLines = 0
            label.lineBreakMode = .byWordWrapping
        }
        update(content, width: width, height: height)
    }
    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }

    struct Measurement {
        var height: CGFloat
        var textHeight: CGFloat
        var checkboxHeight: CGFloat
        var buttonHeights: [CGFloat]
        var verticalActions: Bool
        var controlsHeight: CGFloat
        var minimumHeight: CGFloat { 24 + min(textHeight, 40) + controlsHeight }
    }
    static func titleFont() -> NSFont { .systemFont(ofSize: max(14, NSFont.preferredFont(forTextStyle: .headline).pointSize), weight: .semibold) }
    static func messageFont() -> NSFont { .systemFont(ofSize: max(14, NSFont.preferredFont(forTextStyle: .body).pointSize)) }
    static func actionFont(weight: NSFont.Weight) -> NSFont { .systemFont(ofSize: max(13, NSFont.preferredFont(forTextStyle: .callout).pointSize), weight: weight) }
    static func scaled(_ font: NSFont, by scale: CGFloat) -> NSFont {
        NSFontManager.shared.convert(font, toSize: font.pointSize * max(1, scale))
    }
    static func measuredHeight(_ text: String, font: NSFont, width: CGFloat) -> CGFloat {
        guard !text.isEmpty else { return 0 }
        let paragraph = NSMutableParagraphStyle(); paragraph.lineBreakMode = .byWordWrapping
        let rect = (text as NSString).boundingRect(with: NSSize(width: max(1, width), height: .greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin, .usesFontLeading], attributes: [.font: font, .paragraphStyle: paragraph])
        return max(ceil(rect.height), ceil(font.ascender - font.descender + font.leading))
    }
    static func labelHeight(_ text: String, font: NSFont, width: CGFloat) -> CGFloat {
        guard !text.isEmpty else { return 0 }
        // Measure the same AppKit cell that draws the label. NSString's bounding
        // rect has no NSTextFieldCell insets; at a wrap boundary it can report
        // one line where the actual cell needs two (large prompt countdown).
        let label = NSTextField(wrappingLabelWithString: text)
        label.font = font
        label.isSelectable = false
        label.usesSingleLineMode = false
        label.maximumNumberOfLines = 0
        label.lineBreakMode = .byWordWrapping
        let cellHeight = label.cell?.cellSize(forBounds: NSRect(x: 0, y: 0,
            width: max(1, width), height: .greatestFiniteMagnitude)).height ?? 0
        return max(ceil(cellHeight), ceil(font.ascender - font.descender + font.leading))
    }
    static func measure(_ content: DesktopNotificationCardContent, width: CGFloat, scale: CGFloat) -> Measurement {
        // Keep even iconless text outside the 28pt corner hit region.
        let textWidth = width - 24 - (content.iconName == nil ? 4 : 26)
        let values = content.text
        let title = labelHeight(values.title, font: scaled(titleFont(), by: scale), width: textWidth)
        let message = labelHeight(values.message, font: scaled(messageFont(), by: scale), width: textWidth)
        let textHeight = max(content.iconName == nil ? 0 : 22, title + message + (title > 0 && message > 0 ? 2 : 0))
        let checkboxHeight = content.checkboxTitle.map {
            max(20, measuredHeight($0, font: scaled(actionFont(weight: .regular), by: scale), width: width - 48))
        } ?? 0
        let font = scaled(actionFont(weight: .semibold), by: scale)
        let widths = content.actions.map { ceil(($0.title as NSString).size(withAttributes: [.font: font]).width) + 24 }
        let vertical = widths.reduce(0, +) + CGFloat(max(0, widths.count - 1)) * 8 > width - 24
        let heights = content.actions.enumerated().map { index, item in
            max(32, measuredHeight(item.title, font: font, width: (vertical ? width - 24 : widths[index]) - 24) + 12)
        }
        let actionsHeight = vertical ? heights.reduce(0, +) + CGFloat(max(0, heights.count - 1)) * 8 : heights.max() ?? 0
        let controls = (checkboxHeight > 0 ? 8 + checkboxHeight : 0) + (actionsHeight > 0 ? 8 + actionsHeight : 0)
        return Measurement(height: max(44, 24 + textHeight + controls), textHeight: textHeight,
            checkboxHeight: checkboxHeight, buttonHeights: heights, verticalActions: vertical, controlsHeight: controls)
    }

    func update(_ next: DesktopNotificationCardContent, width: CGFloat, height: CGFloat) {
        let changedActions = content.actions.map(\.action) != next.actions.map(\.action)
            || content.actions.map(\.title) != next.actions.map(\.title)
        content = next
        let measured = Self.measure(next, width: width, scale: scale)
        frame.size = NSSize(width: width + 28, height: height + 28)
        card.frame = NSRect(x: 14, y: 14, width: width, height: height)
        close.frame = NSRect(x: 0, y: 0, width: 28, height: 28)
        let visibleTextHeight = max(1, height - 24 - measured.controlsHeight)
        let scrolls = measured.textHeight > visibleTextHeight + 0.5
        textScroll.frame = NSRect(x: 12, y: 12, width: width - 24, height: visibleTextHeight)
        textScroll.hasVerticalScroller = scrolls
        textScroll.scrollerStyle = .overlay
        textScroll.setAccessibilityLabel("Текст уведомления")
        let documentWidth = width - 24 - (scrolls ? 16 : 0)
        let textX: CGFloat = next.iconName == nil ? 4 : 26
        let values = next.text
        let titleFont = Self.scaled(Self.titleFont(), by: scale)
        let messageFont = Self.scaled(Self.messageFont(), by: scale)
        let titleHeight = Self.labelHeight(values.title, font: titleFont, width: documentWidth - textX)
        let bodyHeight = Self.labelHeight(values.message, font: messageFont, width: documentWidth - textX)
        let bodyY = titleHeight + (titleHeight > 0 && bodyHeight > 0 ? 2 : 0)
        textDocument.frame = NSRect(x: 0, y: 0, width: documentWidth, height: max(visibleTextHeight, bodyY + bodyHeight))
        titleLabel.stringValue = values.title; titleLabel.font = titleFont; titleLabel.isHidden = values.title.isEmpty
        messageLabel.stringValue = values.message; messageLabel.font = messageFont; messageLabel.isHidden = values.message.isEmpty
        titleLabel.frame = NSRect(x: textX, y: 0, width: documentWidth - textX, height: titleHeight)
        messageLabel.frame = NSRect(x: textX, y: bodyY, width: documentWidth - textX, height: bodyHeight)
        icon.isHidden = next.iconName == nil
        icon.image = next.iconName.flatMap { NSImage(systemSymbolName: $0, accessibilityDescription: nil) }
        icon.symbolConfiguration = .init(pointSize: 18, weight: .medium)
        icon.frame = NSRect(x: 0, y: 4, width: 18, height: 18)
        icon.setAccessibilityElement(false)
        var y = 12 + visibleTextHeight
        remember.isHidden = next.checkboxTitle == nil
        remember.title = next.checkboxTitle ?? ""
        remember.font = Self.scaled(Self.actionFont(weight: .regular), by: scale)
        remember.cell?.wraps = true; remember.cell?.lineBreakMode = .byWordWrapping
        remember.setAccessibilityLabel(next.checkboxTitle)
        remember.state = next.remembers ? .on : .off
        remember.setAccessibilityValue(NSNumber(value: next.remembers))
        if measured.checkboxHeight > 0 {
            y += 8
            remember.frame = NSRect(x: 12, y: y, width: width - 24, height: measured.checkboxHeight)
            y += measured.checkboxHeight
        }
        if changedActions || actionButtons.count != next.actions.count {
            for button in actionButtons { button.removeFromSuperview() }
            actionButtons = next.actions.map { item in
                let button = NotificationCardButton(title: item.title) { [weak self] in self?.onAction(item.action) }
                button.isPrimary = item.primary
                card.addSubview(button)
                return button
            }
        }
        if !actionButtons.isEmpty {
            y += 8
            let font = Self.scaled(Self.actionFont(weight: .semibold), by: scale)
            let widths = next.actions.map { ceil(($0.title as NSString).size(withAttributes: [.font: font]).width) + 24 }
            var x = width - 12 - widths.reduce(0, +) - CGFloat(max(0, widths.count - 1)) * 8
            for (index, button) in actionButtons.enumerated() {
                button.fontScale = scale
                let buttonHeight = measured.verticalActions ? measured.buttonHeights[index] : measured.buttonHeights.max() ?? 32
                button.frame = NSRect(x: measured.verticalActions ? 12 : x, y: y,
                    width: measured.verticalActions ? width - 24 : widths[index], height: buttonHeight)
                if measured.verticalActions { y += buttonHeight + 8 } else { x += widths[index] + 8 }
            }
        }
        configureKeyLoop()
        applyStyle()
        needsLayout = true
    }
    // AppKit can reset nextKeyView while installing a content view. Reapply only
    // links after attachment/layout; never replace controls or the first responder.
    private var keyboardControls: [NSView] {
        var controls: [NSView] = [close]
        if textScroll.hasVerticalScroller { controls.append(textScroll) }
        if !remember.isHidden { controls.append(remember) }
        controls.append(contentsOf: actionButtons)
        return controls
    }
    // NSScrollView inserts its clip view into nextKeyView. Use the same semantic
    // order for explicit Tab navigation, without focusing noninteractive internals.
    func keyView(relativeTo current: NSView, backwards: Bool) -> NSView? {
        let controls = keyboardControls
        guard let index = controls.firstIndex(where: { $0 === current }) else { return nil }
        return controls[(index + (backwards ? controls.count - 1 : 1)) % controls.count]
    }
    func configureKeyLoop() {
        let controls = keyboardControls
        for (index, control) in controls.enumerated() { control.nextKeyView = controls[(index + 1) % controls.count] }
    }
    override public func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        configureKeyLoop()
    }
    override public func layout() {
        super.layout()
        configureKeyLoop()
    }
    override public func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let tracking { removeTrackingArea(tracking) }
        let area = NSTrackingArea(rect: .zero, options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect], owner: self, userInfo: nil)
        addTrackingArea(area); tracking = area
    }
    override public func mouseEntered(with event: NSEvent) { onHover(true) }
    override public func mouseExited(with event: NSEvent) { onHover(false) }
    override public func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); applyStyle() }
    private func applyStyle() {
        let dark = effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
        titleLabel.textColor = Self.primaryText(dark: dark)
        messageLabel.textColor = Self.secondaryText(dark: dark)
        icon.contentTintColor = Self.primaryText(dark: dark)
    }
    public static func cardBackground(dark: Bool) -> NSColor { dark ? NSColor(white: 0.12, alpha: 1) : .white }
    public static func cardBorder(dark: Bool) -> NSColor { NSColor(white: dark ? 0.58 : 0.45, alpha: 1) }
    public static func primaryText(dark: Bool) -> NSColor { NSColor(white: dark ? 0.98 : 0.12, alpha: 1) }
    public static func secondaryText(dark: Bool) -> NSColor { NSColor(white: dark ? 0.80 : 0.36, alpha: 1) }
    public static func accent(dark: Bool) -> NSColor { NSColor(srgbRed: 0.38, green: 0.30, blue: 0.90, alpha: 1) }
    @objc private func closeTapped() { onClose() }
    @objc private func rememberChanged() { onAction(.toggleRecordingPromptRemember(remember.state == .on)) }
}

private final class NotificationCardFlippedView: NSView { override var isFlipped: Bool { true } }

private final class NotificationCardScrollView: NSScrollView {
    override var acceptsFirstResponder: Bool { true }
    // Own keyboard scrolling here: NSScrollView's default focus handoff to the
    // non-editable document can leave the panel itself as first responder.
    override func becomeFirstResponder() -> Bool { true }
    override func keyDown(with event: NSEvent) {
        let step: CGFloat
        switch event.keyCode {
        case 125: step = 24
        case 126: step = -24
        case 121: step = contentView.bounds.height
        case 116: step = -contentView.bounds.height
        default: super.keyDown(with: event); return
        }
        let limit = max(0, (documentView?.bounds.height ?? 0) - contentView.bounds.height)
        contentView.scroll(to: NSPoint(x: 0, y: min(limit, max(0, contentView.bounds.minY + step))))
        reflectScrolledClipView(contentView)
    }
}

final class CardBackgroundView: NSView {
    private let cornerRadius: CGFloat
    override var isFlipped: Bool { true }
    init(cornerRadius: CGFloat) {
        self.cornerRadius = cornerRadius
        super.init(frame: .zero)
        wantsLayer = true
        applyStyle()
    }
    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }
    override func updateLayer() { applyStyle() }
    override func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); applyStyle() }
    private func applyStyle() {
        let dark = effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
        // Always opaque: reduced transparency requires no additional material.
        layer?.backgroundColor = DesktopNotificationCardView.cardBackground(dark: dark).cgColor
        layer?.borderColor = DesktopNotificationCardView.cardBorder(dark: dark).cgColor
        layer?.borderWidth = 1; layer?.cornerRadius = cornerRadius
    }
}

final class NotificationCardCheckbox: NSButton {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var acceptsFirstResponder: Bool { true }
    override var needsPanelToBecomeKey: Bool { false }
    var indicatorFrame: NSRect { cell?.imageRect(forBounds: bounds) ?? .zero }
    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        guard state == .off, !indicatorFrame.isEmpty else { return }
        // Keep the native switch cell, title, state, hit target and AX behavior.
        // Its unselected fill alone is too close to the card in both themes.
        let dark = effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
        let outline = NSBezierPath(roundedRect: indicatorFrame.insetBy(dx: 0.75, dy: 0.75),
                                  xRadius: 4, yRadius: 4)
        DesktopNotificationCardView.cardBorder(dark: dark).setStroke()
        outline.lineWidth = 1.5
        outline.stroke()
    }
    override func viewDidChangeEffectiveAppearance() {
        super.viewDidChangeEffectiveAppearance()
        needsDisplay = true
    }
}

private final class NotificationCardCloseButton: NSButton {
    init() {
        super.init(frame: .zero)
        isBordered = false
        imagePosition = .imageOnly
        image = NSImage(systemSymbolName: "xmark", accessibilityDescription: nil)?
            .withSymbolConfiguration(.init(pointSize: 9, weight: .semibold))
        setAccessibilityLabel("Закрыть уведомление")
        setAccessibilityElement(true)
        setAccessibilityRole(.button)
        toolTip = "Закрыть уведомление"
        focusRingType = .exterior
    }
    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var acceptsFirstResponder: Bool { true }
    override var needsPanelToBecomeKey: Bool { false }
    override func draw(_ dirtyRect: NSRect) {
        let dark = effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
        let circle = NSBezierPath(ovalIn: bounds.insetBy(dx: 5, dy: 5))
        DesktopNotificationCardView.cardBackground(dark: dark).setFill(); circle.fill()
        DesktopNotificationCardView.cardBorder(dark: dark).setStroke(); circle.lineWidth = 1; circle.stroke()
        super.draw(dirtyRect)
    }
}

final class NotificationCardButton: NSButton {
    var isPrimary = false { didSet { applyStyle() } }
    var fontScale: CGFloat = 1 { didSet { applyStyle() } }
    private let handler: () -> Void
    init(title: String, handler: @escaping () -> Void) {
        self.handler = handler
        super.init(frame: .zero)
        self.title = title; target = self; action = #selector(fire)
        bezelStyle = .regularSquare; isBordered = false; wantsLayer = true
        focusRingType = .exterior
        cell?.wraps = true; cell?.lineBreakMode = .byWordWrapping
        setAccessibilityLabel(title)
        setAccessibilityElement(true)
        setAccessibilityRole(.button)
        applyStyle()
    }
    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var acceptsFirstResponder: Bool { true }
    override var needsPanelToBecomeKey: Bool { false }
    override func updateLayer() { applyStyle() }
    override func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); applyStyle() }
    private func applyStyle() {
        let dark = effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
        layer?.cornerRadius = 8
        layer?.borderWidth = 1
        layer?.backgroundColor = (isPrimary ? DesktopNotificationCardView.accent(dark: dark) : DesktopNotificationCardView.cardBackground(dark: dark)).cgColor
        layer?.borderColor = (isPrimary ? DesktopNotificationCardView.accent(dark: dark) : DesktopNotificationCardView.cardBorder(dark: dark)).cgColor
        let paragraph = NSMutableParagraphStyle(); paragraph.alignment = .center; paragraph.lineBreakMode = .byWordWrapping
        let font = DesktopNotificationCardView.scaled(DesktopNotificationCardView.actionFont(weight: .semibold), by: fontScale)
        self.font = font
        attributedTitle = NSAttributedString(string: title, attributes: [
            .font: font, .foregroundColor: isPrimary ? NSColor.white : DesktopNotificationCardView.primaryText(dark: dark),
            .paragraphStyle: paragraph
        ])
    }
    @objc private func fire() { handler() }
}
