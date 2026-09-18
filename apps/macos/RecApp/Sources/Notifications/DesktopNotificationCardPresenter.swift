import AppKit
import Foundation

/// Собственная карточка GRAF поверх других окон.
///
/// Наблюдаемый эталон: карточка-напоминание Krisp 3.16.8 шириной 448 точек в
/// правом верхнем углу рабочей области, содержимое 420 точек со скруглением 16,
/// заголовок 14/20 полужирным, пояснение 14/20 обычным, кнопка действия высотой
/// не меньше 40 точек со скруглением 10, кнопка закрытия 20x20 со скруглением 10
/// со смещением 2 точки. Карточка не зависит от разрешения
/// `UNUserNotificationCenter` и от режима «Не беспокоить».
public enum DesktopNotificationCardAction: Equatable, Sendable {
    case join
    case joinAndRecord
    case record
    case openCalendar
    case openSettings
    case stopRecording
    case openRecording(String)
}

/// Содержимое карточки без AppKit: пригодно для проверок логики показа.
public enum DesktopNotificationCardContent: Equatable, Sendable {
    case meeting(title: String, startText: String, hasJoinLink: Bool)
    case recording(elapsed: String)
    case transcribing(elapsed: String)
    case problem(title: String, message: String, actionTitle: String, sessionID: String?)

    public var accessibilitySummary: String {
        switch self {
        case let .meeting(title, startText, hasJoinLink):
            let join = hasJoinLink ? "Есть ссылка на встречу." : "Ссылки на встречу нет."
            return "Напоминание о встрече. \(title). Начало \(startText). \(join)"
        case let .recording(elapsed):
            return "Идёт запись. Длительность \(elapsed)."
        case let .transcribing(elapsed):
            return "Идёт расшифровка. Длительность \(elapsed)."
        case let .problem(title, message, actionTitle, _):
            return "\(title). \(message). Действие: \(actionTitle)."
        }
    }

    public var identifier: String {
        switch self {
        case .meeting: return "graf.card.meeting"
        case .recording: return "graf.card.recording"
        case .transcribing: return "graf.card.transcribing"
        case .problem: return "graf.card.problem"
        }
    }
}

/// Показ карточки в окне поверх других окон. Все побочные эффекты снимаются
/// вместе с окном, поэтому остановка и выход из аккаунта не оставляют карточек.
@MainActor
public final class DesktopNotificationCardPresenter {
    public static let cardWidth: CGFloat = 420
    public static let windowWidth: CGFloat = 448
    public static let horizontalMargin: CGFloat = 10
    public static let topInset: CGFloat = 39
    public static let bottomPadding: CGFloat = 12
    public static let cornerRadius: CGFloat = 16

    private var panel: NSPanel?
    private var ticker: Task<Void, Never>?
    private var content: DesktopNotificationCardContent?
    private var onAction: ((DesktopNotificationCardAction) -> Void)?
    private var onTick: (() -> DesktopNotificationCardContent?)?
    private var dismissAfter: Date?
    private var screenObserver: NSObjectProtocol?

    public init() {}

    public var isVisible: Bool { panel != nil }
    public var presentedContent: DesktopNotificationCardContent? { content }

    /// Показывает карточку. Повторный вызов с другим содержимым заменяет его,
    /// не создавая второго окна.
    public func present(_ content: DesktopNotificationCardContent,
                        dismissAfter: Date? = nil,
                        onAction: @escaping (DesktopNotificationCardAction) -> Void,
                        onTick: (() -> DesktopNotificationCardContent?)? = nil) {
        self.onAction = onAction
        self.onTick = onTick
        self.dismissAfter = dismissAfter
        self.content = content
        let window = panel ?? makePanel()
        panel = window
        window.contentView = DesktopNotificationCardView(
            content: content,
            onAction: { [weak self] action in self?.onAction?(action) },
            onClose: { [weak self] in self?.dismiss() }
        )
        // Высота окна равна высоте содержимого: карточка не растягивается на
        // остаток прежнего кадра.
        if let view = window.contentView {
            view.layoutSubtreeIfNeeded()
            let height = view.fittingSize.height
            if height > 0 { window.setContentSize(NSSize(width: Self.windowWidth, height: height)) }
        }
        position(window)
        window.orderFrontRegardless()
        announce(content.accessibilitySummary)
        startTickerIfNeeded()
    }

    public func dismiss() {
        ticker?.cancel()
        ticker = nil
        onTick = nil
        dismissAfter = nil
        content = nil
        panel?.orderOut(nil)
        panel = nil
    }

    /// Показанное окно карточки: нужно для измерений и проверок поверхности.
    var window: NSWindow? { panel }

    /// Обновляет показанное содержимое без пересоздания окна.
    public func refresh() {
        guard let onTick else {
            if dismissAfter != nil { dismiss() }
            return
        }
        guard let next = onTick() else {
            if dismissAfter != nil { dismiss() }
            return
        }
        guard next != content else { return }
        present(next, dismissAfter: dismissAfter, onAction: onAction ?? { _ in }, onTick: onTick)
    }

    private func startTickerIfNeeded() {
        guard ticker == nil, onTick != nil || dismissAfter != nil else { return }
        ticker = Task { [weak self] in
            while !Task.isCancelled {
                do { try await Task.sleep(for: .seconds(1)) } catch { return }
                guard let self else { return }
                if let deadline = self.dismissAfter, Date() >= deadline {
                    self.dismiss()
                    return
                }
                self.refresh()
            }
        }
    }

    private func makePanel() -> NSPanel {
        let window = DesktopNotificationCardPanel(
            contentRect: NSRect(x: 0, y: 0, width: Self.windowWidth, height: 104),
            styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false
        )
        window.level = .statusBar
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .transient]
        window.hidesOnDeactivate = false
        window.isReleasedWhenClosed = false
        window.backgroundColor = .clear
        window.isOpaque = false
        window.hasShadow = false
        window.identifier = NSUserInterfaceItemIdentifier("graf-notification-card")
        window.isMovable = false
        return window
    }

    /// Держит карточку в рабочей области выбранного экрана и не перекрывает
    /// строку меню: правый край с отступом 0 точек, верх — на `topInset` ниже
    /// рабочей области (наблюдаемые координаты эталона: ширина экрана минус 448).
    func position(_ window: NSWindow) {
        let screen = NSScreen.screens.first(where: { $0.frame.contains(NSEvent.mouseLocation) }) ?? NSScreen.main
        guard let screen else { return }
        let visible = screen.visibleFrame
        let height = max(window.frame.height, 64)
        let x = max(visible.minX, visible.maxX - Self.windowWidth)
        let y = max(visible.minY, visible.maxY - height - Self.topInset)
        window.setFrame(NSRect(x: x, y: y, width: Self.windowWidth, height: height), display: true)
    }

    private func announce(_ text: String) {
        guard let panel else { return }
        NSAccessibility.post(element: panel, notification: .announcementRequested, userInfo: [
            .announcement: text,
            .priority: NSAccessibilityPriorityLevel.high.rawValue
        ])
    }
}

private final class DesktopNotificationCardPanel: NSPanel {
    // Карточка не должна забирать фокус у приложения, где идёт встреча.
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

/// Содержимое карточки. Рисуется кодом GRAF: чужие ресурсы не используются.
final class DesktopNotificationCardView: NSView {
    private let content: DesktopNotificationCardContent
    private let onAction: (DesktopNotificationCardAction) -> Void
    private let onClose: () -> Void
    private var buttons: [(NSButton, DesktopNotificationCardAction)] = []

    init(content: DesktopNotificationCardContent,
         onAction: @escaping (DesktopNotificationCardAction) -> Void,
         onClose: @escaping () -> Void) {
        self.content = content
        self.onAction = onAction
        self.onClose = onClose
        super.init(frame: .zero)
        wantsLayer = true
        build()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }

    static func cardBackground(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 28/255, green: 31/255, blue: 32/255, alpha: 0.92)
             : NSColor(srgbRed: 254/255, green: 254/255, blue: 254/255, alpha: 0.97)
    }

    static func cardBorder(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 71/255, green: 74/255, blue: 76/255, alpha: 1)
             : NSColor(srgbRed: 210/255, green: 211/255, blue: 212/255, alpha: 1)
    }

    static func primaryText(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 254/255, green: 254/255, blue: 254/255, alpha: 1)
             : NSColor(srgbRed: 36/255, green: 39/255, blue: 41/255, alpha: 1)
    }

    static func secondaryText(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 190/255, green: 192/255, blue: 194/255, alpha: 1)
             : NSColor(srgbRed: 108/255, green: 110/255, blue: 112/255, alpha: 1)
    }

    static func accent(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 97/255, green: 78/255, blue: 250/255, alpha: 1)
             : NSColor(srgbRed: 97/255, green: 78/255, blue: 250/255, alpha: 1)
    }

    private var isDark: Bool {
        effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
    }

    /// Карточка встречи и карточка проблемы складываются из строки с текстом и
    /// отдельной строки действий: так ширина остаётся наблюдаемыми 420 точками.
    private var usesStackedLayout: Bool {
        switch content {
        case .meeting, .problem: return true
        case .recording, .transcribing: return false
        }
    }

    private func build() {
        let card = CardBackgroundView(cornerRadius: DesktopNotificationCardPresenter.cornerRadius)
        card.translatesAutoresizingMaskIntoConstraints = false
        // Ширина карточки наблюдаемая: 420 точек внутри окна 448 точек.
        card.widthAnchor.constraint(equalToConstant: DesktopNotificationCardPresenter.cardWidth).isActive = true
        addSubview(card)

        let close = NSButton(title: "", target: self, action: #selector(closeTapped))
        close.isBordered = false
        close.bezelStyle = .regularSquare
        close.image = NSImage(systemSymbolName: "xmark", accessibilityDescription: "Закрыть уведомление")
        close.imagePosition = .imageOnly
        close.contentTintColor = Self.secondaryText(dark: isDark)
        close.translatesAutoresizingMaskIntoConstraints = false
        close.toolTip = "Закрыть уведомление"
        close.setAccessibilityLabel("Закрыть уведомление")
        addSubview(close)

        let header = NSStackView()
        header.orientation = .horizontal
        header.alignment = .centerY
        header.spacing = 12
        header.translatesAutoresizingMaskIntoConstraints = false
        card.addSubview(header)

        let icon = NSImageView()
        icon.image = NSImage(systemSymbolName: iconName, accessibilityDescription: nil)
        icon.contentTintColor = Self.accent(dark: isDark)
        icon.symbolConfiguration = .init(pointSize: 20, weight: .medium)
        icon.translatesAutoresizingMaskIntoConstraints = false
        icon.widthAnchor.constraint(equalToConstant: 24).isActive = true

        let text = NSStackView()
        text.orientation = .vertical
        text.alignment = .leading
        text.spacing = 2
        text.translatesAutoresizingMaskIntoConstraints = false
        let titleLabel = label(title, font: .systemFont(ofSize: 14, weight: .semibold),
                               color: Self.primaryText(dark: isDark))
        let messageLabel = label(message, font: .systemFont(ofSize: 14),
                                 color: Self.secondaryText(dark: isDark))
        text.addArrangedSubview(titleLabel)
        text.addArrangedSubview(messageLabel)

        header.addArrangedSubview(icon)
        header.addArrangedSubview(text)
        header.addArrangedSubview(NSView())

        var constraints: [NSLayoutConstraint] = [
            card.leadingAnchor.constraint(equalTo: leadingAnchor, constant: DesktopNotificationCardPresenter.horizontalMargin),
            card.trailingAnchor.constraint(equalTo: leadingAnchor,
                                           constant: DesktopNotificationCardPresenter.horizontalMargin
                                               + DesktopNotificationCardPresenter.cardWidth),
            card.topAnchor.constraint(greaterThanOrEqualTo: topAnchor, constant: 10),
            // Высота карточки определяется содержимым, а не остатком окна.
            card.bottomAnchor.constraint(lessThanOrEqualTo: bottomAnchor,
                                         constant: -DesktopNotificationCardPresenter.bottomPadding),
            close.topAnchor.constraint(equalTo: topAnchor, constant: 12),
            close.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -4),
            close.widthAnchor.constraint(equalToConstant: 20),
            close.heightAnchor.constraint(equalToConstant: 20),
            header.leadingAnchor.constraint(equalTo: card.leadingAnchor, constant: 14),
            header.topAnchor.constraint(equalTo: card.topAnchor, constant: 12),
            // Текст не заходит под кнопку закрытия и не расширяет окно.
            header.trailingAnchor.constraint(lessThanOrEqualTo: card.trailingAnchor, constant: -34),
            titleLabel.widthAnchor.constraint(lessThanOrEqualToConstant: DesktopNotificationCardPresenter.cardWidth - 96),
            messageLabel.widthAnchor.constraint(lessThanOrEqualToConstant: DesktopNotificationCardPresenter.cardWidth - 96)
        ]

        if usesStackedLayout {
            let actions = NSStackView()
            actions.orientation = .horizontal
            actions.alignment = .centerY
            actions.spacing = 8
            actions.translatesAutoresizingMaskIntoConstraints = false
            card.addSubview(actions)
            for (buttonTitle, action, isPrimary) in actionButtons {
                let button = NotificationCardButton(title: buttonTitle) { [weak self] in self?.onAction(action) }
                button.isPrimary = isPrimary
                button.translatesAutoresizingMaskIntoConstraints = false
                button.heightAnchor.constraint(greaterThanOrEqualToConstant: 40).isActive = true
                actions.addArrangedSubview(button)
                buttons.append((button, action))
            }
            actions.addArrangedSubview(NSView())
            constraints += [
                actions.leadingAnchor.constraint(equalTo: card.leadingAnchor, constant: 14),
                actions.trailingAnchor.constraint(lessThanOrEqualTo: card.trailingAnchor, constant: -14),
                actions.topAnchor.constraint(equalTo: header.bottomAnchor, constant: 10),
                actions.bottomAnchor.constraint(equalTo: card.bottomAnchor, constant: -12)
            ]
            // Нижняя граница карточки задаётся строкой действий.
            card.bottomAnchor.constraint(equalTo: actions.bottomAnchor, constant: 12).isActive = true
        } else {
            for (buttonTitle, action, isPrimary) in actionButtons {
                let button = NotificationCardButton(title: buttonTitle) { [weak self] in self?.onAction(action) }
                button.isPrimary = isPrimary
                button.translatesAutoresizingMaskIntoConstraints = false
                button.heightAnchor.constraint(greaterThanOrEqualToConstant: 40).isActive = true
                header.addArrangedSubview(button)
                buttons.append((button, action))
            }
            constraints += [
                header.bottomAnchor.constraint(equalTo: card.bottomAnchor, constant: -12)
            ]
        }

        NSLayoutConstraint.activate(constraints)
    }

    private var iconName: String {
        switch content {
        case .meeting: return "calendar"
        case .recording: return "record.circle"
        case .transcribing: return "waveform"
        case .problem: return "exclamationmark.triangle"
        }
    }

    private var title: String {
        switch content {
        case let .meeting(title, _, _): return title
        case .recording: return "Идёт запись"
        case .transcribing: return "Идёт расшифровка"
        case let .problem(title, _, _, _): return title
        }
    }

    private var message: String {
        switch content {
        case let .meeting(_, startText, _): return startText
        case let .recording(elapsed), let .transcribing(elapsed): return elapsed
        case let .problem(_, message, _, _): return message
        }
    }

    private var actionButtons: [(String, DesktopNotificationCardAction, Bool)] {
        switch content {
        case let .meeting(_, _, hasJoinLink):
            var items: [(String, DesktopNotificationCardAction, Bool)] = []
            if hasJoinLink {
                items.append(("Подключиться и начать запись", .joinAndRecord, true))
                items.append(("Подключиться", .join, false))
            } else {
                items.append(("Начать запись", .record, true))
            }
            return items
        case .recording, .transcribing:
            return [("Остановить запись", .stopRecording, true)]
        case let .problem(_, _, actionTitle, sessionID):
            return [(actionTitle, sessionID.map { .openRecording($0) } ?? .openCalendar, true)]
        }
    }

    private func label(_ text: String, font: NSFont, color: NSColor) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.font = font
        field.textColor = color
        field.lineBreakMode = .byTruncatingTail
        field.maximumNumberOfLines = 2
        return field
    }

    @objc private func closeTapped() { onClose() }
}

final class CardBackgroundView: NSView {
    private let cornerRadius: CGFloat
    init(cornerRadius: CGFloat) {
        self.cornerRadius = cornerRadius
        super.init(frame: .zero)
        wantsLayer = true
        // Слой настраивается сразу: карточка может быть измерена до первого показа.
        applyStyle()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }

    override func updateLayer() { applyStyle() }

    override func viewDidChangeEffectiveAppearance() {
        super.viewDidChangeEffectiveAppearance()
        applyStyle()
    }

    private func applyStyle() {
        let dark = effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
        layer?.backgroundColor = DesktopNotificationCardView.cardBackground(dark: dark).cgColor
        layer?.borderColor = DesktopNotificationCardView.cardBorder(dark: dark).cgColor
        layer?.borderWidth = 1
        layer?.cornerRadius = cornerRadius
        layer?.masksToBounds = true
    }
}

final class NotificationCardButton: NSButton {
    var isPrimary = false {
        didSet { applyStyle() }
    }
    private let handler: () -> Void

    init(title: String, handler: @escaping () -> Void) {
        self.handler = handler
        super.init(frame: .zero)
        self.title = title
        self.target = self
        self.action = #selector(fire)
        bezelStyle = .regularSquare
        isBordered = false
        wantsLayer = true
        font = .systemFont(ofSize: 13, weight: .semibold)
        setAccessibilityLabel(title)
        applyStyle()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }

    override func updateLayer() { applyStyle() }

    private func applyStyle() {
        let dark = effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
        layer?.cornerRadius = 10
        layer?.borderWidth = 1
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = .center
        if isPrimary {
            layer?.backgroundColor = DesktopNotificationCardView.accent(dark: dark).cgColor
            layer?.borderColor = NSColor.clear.cgColor
            attributedTitle = NSAttributedString(string: title, attributes: [
                .foregroundColor: NSColor.white,
                .font: NSFont.systemFont(ofSize: 13, weight: .semibold),
                .paragraphStyle: paragraph
            ])
        } else {
            layer?.backgroundColor = NSColor.clear.cgColor
            layer?.borderColor = DesktopNotificationCardView.cardBorder(dark: dark).cgColor
            attributedTitle = NSAttributedString(string: title, attributes: [
                .foregroundColor: DesktopNotificationCardView.primaryText(dark: dark),
                .font: NSFont.systemFont(ofSize: 13, weight: .medium),
                .paragraphStyle: paragraph
            ])
        }
        // Наблюдаемый эталон: поля кнопки 15 точек по бокам вокруг текста.
        widthConstraint?.isActive = false
        let text = (title as NSString).size(withAttributes: [.font: NSFont.systemFont(ofSize: 13, weight: .semibold)]).width
        let width = widthAnchor.constraint(equalToConstant: ceil(text) + 30)
        width.isActive = true
        widthConstraint = width
    }

    private var widthConstraint: NSLayoutConstraint?

    @objc private func fire() { handler() }
}
