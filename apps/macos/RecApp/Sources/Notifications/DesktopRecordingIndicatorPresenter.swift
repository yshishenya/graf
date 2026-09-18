import AppKit
import Foundation

/// Состояние, которое показывает индикатор записи поверх других окон.
public enum DesktopRecordingIndicatorState: Equatable, Sendable {
    case recording(elapsed: String)
    case transcribing(elapsed: String)

    public var title: String {
        switch self {
        case .recording: return "Идёт запись"
        case .transcribing: return "Идёт расшифровка"
        }
    }

    public var elapsed: String {
        switch self {
        case let .recording(elapsed), let .transcribing(elapsed): return elapsed
        }
    }

    public var isRecording: Bool {
        if case .recording = self { return true }
        return false
    }
}

/// Компактный индикатор состояния записи в правом верхнем углу рабочей области.
///
/// Наблюдаемый эталон Krisp 3.16.8: отдельное окно поверх других окон с
/// заголовком состояния (`Recording Live` / `Transcribing Live`), узкой полосой
/// сверху и содержимым ниже; окно не забирает клавиатурный фокус
/// (`focusable` выключен). GRAF показывает то же состояние и даёт остановить
/// запись, не открывая главное окно.
@MainActor
public final class DesktopRecordingIndicatorPresenter {
    public static let width: CGFloat = 232
    public static let topInset: CGFloat = 8

    private var panel: NSPanel?
    private var state: DesktopRecordingIndicatorState?
    private var onStop: (() -> Void)?
    private var onOpen: (() -> Void)?
    private var onRefresh: (() -> DesktopRecordingIndicatorState?)?
    private var ticker: Task<Void, Never>?

    public init() {}

    public var isVisible: Bool { panel != nil }
    /// Окно индикатора доступно проверкам: геометрия измеряется на настоящем окне.
    var window: NSWindow? { panel }
    public var presentedState: DesktopRecordingIndicatorState? { state }

    public func show(_ state: DesktopRecordingIndicatorState,
                     onStop: @escaping () -> Void,
                     onOpen: (() -> Void)? = nil,
                     onRefresh: (() -> DesktopRecordingIndicatorState?)? = nil) {
        self.onStop = onStop
        self.onOpen = onOpen
        self.onRefresh = onRefresh
        guard state != self.state || panel == nil else { return }
        self.state = state
        let window = panel ?? makePanel()
        panel = window
        window.contentView = DesktopRecordingIndicatorView(
            state: state,
            onStop: { [weak self] in self?.onStop?() },
            onOpen: { [weak self] in self?.onOpen?() }
        )
        window.setContentSize(NSSize(width: Self.width, height: window.contentView?.fittingSize.height ?? 44))
        position(window)
        window.orderFrontRegardless()
        startTickerIfNeeded()
    }

    public func hide() {
        ticker?.cancel()
        ticker = nil
        onRefresh = nil
        state = nil
        onStop = nil
        onOpen = nil
        panel?.orderOut(nil)
        panel = nil
    }

    /// Длительность должна идти, даже если состояние записи не менялось.
    private func startTickerIfNeeded() {
        guard ticker == nil, onRefresh != nil else { return }
        ticker = Task { [weak self] in
            while !Task.isCancelled {
                do { try await Task.sleep(for: .seconds(1)) } catch { return }
                guard let self, let next = self.onRefresh?() else { return }
                if next != self.state { self.show(next, onStop: self.onStop ?? {}, onOpen: self.onOpen, onRefresh: self.onRefresh) }
            }
        }
    }

    private func makePanel() -> NSPanel {
        let window = DesktopRecordingIndicatorPanel(
            contentRect: NSRect(x: 0, y: 0, width: Self.width, height: 44),
            styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false
        )
        window.level = .statusBar
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .transient]
        window.hidesOnDeactivate = false
        window.isReleasedWhenClosed = false
        window.backgroundColor = .clear
        window.isOpaque = false
        window.hasShadow = false
        window.identifier = NSUserInterfaceItemIdentifier("graf-recording-indicator")
        window.isMovable = false
        return window
    }

    private func position(_ window: NSWindow) {
        let screen = NSScreen.screens.first(where: { $0.frame.contains(NSEvent.mouseLocation) }) ?? NSScreen.main
        guard let screen else { return }
        let visible = screen.visibleFrame
        let x = max(visible.minX, visible.maxX - Self.width)
        let y = max(visible.minY, visible.maxY - window.frame.height - Self.topInset)
        window.setFrameOrigin(NSPoint(x: x, y: y))
    }
}

private final class DesktopRecordingIndicatorPanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

final class DesktopRecordingIndicatorView: NSView {
    private let state: DesktopRecordingIndicatorState
    private let onStop: () -> Void
    private let onOpen: () -> Void

    init(state: DesktopRecordingIndicatorState,
         onStop: @escaping () -> Void,
         onOpen: @escaping () -> Void) {
        self.state = state
        self.onStop = onStop
        self.onOpen = onOpen
        super.init(frame: .zero)
        wantsLayer = true
        build()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }

    private var isDark: Bool {
        effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
    }

    private func build() {
        let card = CardBackgroundView(cornerRadius: DesktopNotificationCardPresenter.cornerRadius)
        card.translatesAutoresizingMaskIntoConstraints = false
        addSubview(card)

        let dot = NSView()
        dot.wantsLayer = true
        dot.translatesAutoresizingMaskIntoConstraints = false
        dot.layer?.backgroundColor = (state.isRecording
            ? NSColor(srgbRed: 0.90, green: 0.22, blue: 0.21, alpha: 1)
            : NSColor(srgbRed: 0.0, green: 0.50, blue: 0.40, alpha: 1)).cgColor
        dot.layer?.cornerRadius = 4

        let title = NSTextField(labelWithString: state.title)
        title.font = .systemFont(ofSize: 13, weight: .semibold)
        title.textColor = DesktopNotificationCardView.primaryText(dark: isDark)
        title.setAccessibilityLabel("\(state.title), \(state.elapsed)")

        let elapsed = NSTextField(labelWithString: state.elapsed)
        elapsed.font = .monospacedDigitSystemFont(ofSize: 13, weight: .regular)
        elapsed.textColor = DesktopNotificationCardView.secondaryText(dark: isDark)

        let stop = NotificationCardButton(title: "Остановить") { [weak self] in self?.onStop() }
        stop.isPrimary = true
        stop.translatesAutoresizingMaskIntoConstraints = false
        stop.heightAnchor.constraint(greaterThanOrEqualToConstant: 28).isActive = true
        stop.setAccessibilityLabel("Остановить запись")

        let stack = NSStackView(views: [dot, title, elapsed, NSView(), stop])
        stack.orientation = .horizontal
        stack.alignment = .centerY
        stack.spacing = 8
        stack.translatesAutoresizingMaskIntoConstraints = false
        card.addSubview(stack)

        let open = NSClickGestureRecognizer(target: self, action: #selector(openTapped))
        title.addGestureRecognizer(open)
        elapsed.addGestureRecognizer(NSClickGestureRecognizer(target: self, action: #selector(openTapped)))

        NSLayoutConstraint.activate([
            card.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 8),
            card.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -8),
            card.topAnchor.constraint(equalTo: topAnchor, constant: 6),
            card.bottomAnchor.constraint(equalTo: bottomAnchor, constant: -6),
            dot.widthAnchor.constraint(equalToConstant: 8),
            dot.heightAnchor.constraint(equalToConstant: 8),
            stack.leadingAnchor.constraint(equalTo: card.leadingAnchor, constant: 12),
            stack.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -10),
            stack.topAnchor.constraint(equalTo: card.topAnchor, constant: 8),
            stack.bottomAnchor.constraint(equalTo: card.bottomAnchor, constant: -8)
        ])
    }

    @objc private func openTapped() { onOpen() }
}
