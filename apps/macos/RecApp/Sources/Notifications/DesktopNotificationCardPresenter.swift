import AppKit
import Foundation

/// Собственная карточка GRAF поверх других окон: единая поверхность для всех
/// коротких сообщений — напоминания о встрече, состояния записи, проблемы с
/// локальной записью и служебных подсказок.
///
/// Наблюдаемый эталон: карточка-напоминание Krisp 3.16.8 шириной 448 точек в
/// правом верхнем углу рабочей области, содержимое 420 точек со скруглением 16,
/// заголовок 14/20 полужирным, пояснение 14/20 обычным, кнопка действия высотой
/// не меньше 40 точек со скруглением 10. Карточка не зависит от разрешения
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
    case problem(title: String, message: String, actionTitle: String, sessionID: String?)
    /// Служебное сообщение без действия или с одним действием.
    case notice(title: String, message: String, actionTitle: String?)

    public var accessibilitySummary: String {
        switch self {
        case let .meeting(title, startText, hasJoinLink):
            let join = hasJoinLink ? "Есть ссылка на встречу." : "Ссылки на встречу нет."
            return "Напоминание о встрече. \(title). Начало \(startText). \(join)"
        case let .problem(title, message, actionTitle, _):
            return "\(title). \(message). Действие: \(actionTitle)."
        case let .notice(title, message, actionTitle):
            // Точка в конце сообщения не удваивается.
            let body = message.hasSuffix(".") ? message : message + "."
            return actionTitle.map { "\(title). \(body) Действие: \($0)." } ?? "\(title). \(body)"
        }
    }

    public var identifier: String {
        switch self {
        case .meeting: return "graf.card.meeting"
        case .problem: return "graf.card.problem"
        case .notice: return "graf.card.notice"
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
    /// Высота кнопки действия: карточка эталона 82 точки при полях 10 и тексте
    /// в две строки по 20 точек.
    public static let buttonHeight: CGFloat = 40
    /// Поле карточки сверху.
    public static let topPadding: CGFloat = 10
    /// Поле карточки слева и справа внутри окна.
    public static let contentInset: CGFloat = 16
    /// Наблюдаемая высота карточки эталона.
    public static let cardHeight: CGFloat = 82
    /// Наблюдаемая высота окна карточки эталона.
    public static let windowHeight: CGFloat = 104
    /// Сколько живёт служебное сообщение, если не задано иное.
    public static let noticeDisplayDuration: TimeInterval = 20

    private var panel: NSPanel?
    private var ticker: Task<Void, Never>?
    private var onExpire: (() -> Void)?
    /// Знак закрытия показанной карточки и сторож нажатий: пока приложение не
    /// впереди, первое нажатие до окна не доходит.
    private weak var closeControl: NSButton?
    private var clickMonitor: Any?
    private var content: DesktopNotificationCardContent?
    private var onAction: ((DesktopNotificationCardAction) -> Void)?
    private var onTick: (() -> DesktopNotificationCardContent?)?
    private var dismissAfter: Date?
    private var screenObserver: NSObjectProtocol?

    public init() {}

    public var isVisible: Bool { panel != nil }
    public var presentedContent: DesktopNotificationCardContent? { content }

    /// Высота окна: наблюдаемая для одной строки действий, больше — когда
    /// действия вынесены во вторую строку.
    static func windowHeight(for content: DesktopNotificationCardContent) -> CGFloat {
        surfaceHeight(for: content)
    }

    /// Высота карточки внутри поверхности. Одна строка действий — наблюдаемые
    /// 82 точки. Две строки — строка текста, зазор и строка действий.
    static func rootHeight(for content: DesktopNotificationCardContent) -> CGFloat {
        guard DesktopNotificationCardView.rowCount(for: content) > 1 else { return cardHeight }
        return cardHeight + buttonHeight + 14
    }

    /// Полная высота поверхности: карточка плюс наблюдаемые поля.
    static func surfaceHeight(for content: DesktopNotificationCardContent) -> CGFloat {
        rootHeight(for: content) + topPadding + bottomPadding
    }

    /// Служебное сообщение: короткая подсказка без действия или с одним
    /// действием. Живёт ограниченное время и заменяет предыдущее сообщение.
    public func presentNotice(title: String,
                              message: String,
                              actionTitle: String? = nil,
                              onAction: ((DesktopNotificationCardAction) -> Void)? = nil,
                              duration: TimeInterval = DesktopNotificationCardPresenter.noticeDisplayDuration,
                              onExpire: (() -> Void)? = nil) {
        present(.notice(title: title, message: message, actionTitle: actionTitle),
                dismissAfter: Date().addingTimeInterval(duration),
                onAction: onAction ?? { _ in },
                onExpire: onExpire)
    }

    /// Показывает карточку. Повторный вызов с другим содержимым заменяет его,
    /// не создавая второго окна.
    public func present(_ content: DesktopNotificationCardContent,
                        dismissAfter: Date? = nil,
                        onAction: @escaping (DesktopNotificationCardAction) -> Void,
                        onTick: (() -> DesktopNotificationCardContent?)? = nil,
                        onExpire: (() -> Void)? = nil) {
        self.onAction = onAction
        self.onTick = onTick
        self.onExpire = onExpire
        self.dismissAfter = dismissAfter
        self.content = content
        // Окно создаётся заново под новое содержимое: размер окна не зависит от
        // кадра предыдущего сообщения. Одновременно на экране всегда ровно одно
        // окно уведомления GRAF.
        stopClickMonitor()
        panel?.orderOut(nil)
        let surface = NSSize(width: Self.windowWidth, height: Self.surfaceHeight(for: content))
        let window = makePanel(surface: surface)
        panel = window
        let view = DesktopNotificationCardView(
            content: content,
            rootHeight: Self.rootHeight(for: content),
            onAction: { [weak self] action in self?.onAction?(action) },
            onClose: { [weak self] in self?.dismiss() }
        )
        window.contentView = view
        closeControl = view.closeButton
        window.contentView?.frame = NSRect(origin: .zero, size: surface)
        window.orderFrontRegardless()
        position(window)
        window.contentView?.layoutSubtreeIfNeeded()
        startClickMonitor(for: window)
        announce(content.accessibilitySummary)
        startTickerIfNeeded()
    }

    /// Убирает карточку. Срок, истёкший сам, сообщается отдельно: показ
    /// следующего сообщения не должен зависеть от того, кто закрыл окно.
    public func dismiss() {
        let expired = dismissAfter != nil && (dismissAfter.map { Date() >= $0 } ?? false)
        stopClickMonitor()
        closeControl = nil
        ticker?.cancel()
        ticker = nil
        onTick = nil
        let expire = onExpire
        onExpire = nil
        dismissAfter = nil
        content = nil
        panel?.orderOut(nil)
        panel = nil
        if expired { expire?() }
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
        present(next, dismissAfter: dismissAfter, onAction: onAction ?? { _ in },
                onTick: onTick, onExpire: onExpire)
    }

    /// Нажатие на знак закрытия, пока приложение не впереди, окно не получает:
    /// система отдаёт первое нажатие активации. Сторож перехватывает его и
    /// передаёт знаку закрытия, иначе карточку нельзя закрыть мышью.
    private func startClickMonitor(for window: NSWindow) {
        stopClickMonitor()
        clickMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown]) { [weak self, weak window] event in
            guard let self, let window, event.window === window,
                  let close = self.closeControl else { return event }
            let point = window.contentView?.convert(event.locationInWindow, from: nil) ?? .zero
            guard let hit = window.contentView?.hitTest(point), hit === close || hit.isDescendant(of: close) else {
                return event
            }
            close.performClick(nil)
            return nil
        }
    }

    private func stopClickMonitor() {
        if let clickMonitor { NSEvent.removeMonitor(clickMonitor) }
        clickMonitor = nil
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

    private func makePanel(surface: NSSize) -> NSPanel {
        let window = DesktopNotificationCardPanel(
            contentRect: NSRect(origin: .zero, size: surface),
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

/// Знак закрытия: собственный размер 20 на 20 точек. Обычная кнопка AppKit
/// растягивается по высоте строки, поэтому размер задаётся здесь.
private final class NotificationCardCloseButton: NSButton {
    private static let side: CGFloat = 20

    override var intrinsicContentSize: NSSize {
        NSSize(width: Self.side, height: Self.side)
    }
}

private final class DesktopNotificationCardPanel: NSPanel {
    // Карточка не должна забирать фокус у приложения, где идёт встреча.
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

/// Содержимое карточки. Рисуется кодом GRAF: чужие ресурсы не используются.
/// Поверхность открыта приложению: вопрос о записи показывается той же
/// карточкой, чтобы все сообщения выглядели одинаково.
public final class DesktopNotificationCardView: NSView {
    /// Знак закрытия: нужен сторожу нажатий, пока приложение не впереди.
    var closeButton: NSButton? { close }
    private var close: NSButton?

    private let content: DesktopNotificationCardContent
    private let rootHeight: CGFloat
    private let onAction: (DesktopNotificationCardAction) -> Void
    private let onClose: () -> Void
    private var buttons: [(NSButton, DesktopNotificationCardAction)] = []

    init(content: DesktopNotificationCardContent,
         rootHeight: CGFloat,
         onAction: @escaping (DesktopNotificationCardAction) -> Void,
         onClose: @escaping () -> Void) {
        self.content = content
        self.rootHeight = rootHeight
        self.onAction = onAction
        self.onClose = onClose
        super.init(frame: .zero)
        wantsLayer = true
        build()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) не поддерживается") }

    /// Сколько строк нужно содержимому: две, когда действий больше одного.
    static func rowCount(for content: DesktopNotificationCardContent) -> Int {
        switch content {
        case let .meeting(_, _, hasJoinLink): return hasJoinLink ? 2 : 1
        case .problem, .notice: return 1
        }
    }

    public static func cardBackground(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 28/255, green: 31/255, blue: 32/255, alpha: 0.92)
             : NSColor(srgbRed: 254/255, green: 254/255, blue: 254/255, alpha: 0.97)
    }

    public static func cardBorder(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 71/255, green: 74/255, blue: 76/255, alpha: 1)
             : NSColor(srgbRed: 210/255, green: 211/255, blue: 212/255, alpha: 1)
    }

    public static func primaryText(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 254/255, green: 254/255, blue: 254/255, alpha: 1)
             : NSColor(srgbRed: 36/255, green: 39/255, blue: 41/255, alpha: 1)
    }

    public static func secondaryText(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 190/255, green: 192/255, blue: 194/255, alpha: 1)
             : NSColor(srgbRed: 108/255, green: 110/255, blue: 112/255, alpha: 1)
    }

    public static func accent(dark: Bool) -> NSColor {
        dark ? NSColor(srgbRed: 97/255, green: 78/255, blue: 250/255, alpha: 1)
             : NSColor(srgbRed: 97/255, green: 78/255, blue: 250/255, alpha: 1)
    }

    private var isDark: Bool {
        effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
    }

    private func build() {
        let card = CardBackgroundView(cornerRadius: DesktopNotificationCardPresenter.cornerRadius)
        card.translatesAutoresizingMaskIntoConstraints = false
        // Ширина карточки наблюдаемая: 420 точек внутри окна 448 точек.
        card.widthAnchor.constraint(equalToConstant: DesktopNotificationCardPresenter.cardWidth).isActive = true
        addSubview(card)

        let close = NotificationCardCloseButton(title: "", target: self, action: #selector(closeTapped))
        self.close = close
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
        header.spacing = 8
        header.translatesAutoresizingMaskIntoConstraints = false
        // Строка не сжимается по высоте: карточка держит наблюдаемые размеры.
        header.setContentCompressionResistancePriority(.required, for: .vertical)
        header.setContentHuggingPriority(.required, for: .vertical)
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
        // Текст уступает место действиям лишь настолько, насколько нужно:
        // сообщение не обрезается многоточием.
        text.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        text.setContentHuggingPriority(.defaultLow, for: .horizontal)

        header.addArrangedSubview(icon)
        header.addArrangedSubview(text)

        // Строка действий. С одним действием она помещается рядом с текстом,
        // как в наблюдаемом эталоне. Двум действиям нужна отдельная строка:
        // подписи эталона длиннее латинских, а ширина карточки наблюдаемая —
        // 420 точек.
        let actions = NSStackView()
        actions.orientation = .horizontal
        actions.alignment = .centerY
        actions.spacing = 8
        actions.translatesAutoresizingMaskIntoConstraints = false
        actions.setContentCompressionResistancePriority(.required, for: .vertical)
        actions.setContentHuggingPriority(.required, for: .vertical)
        // Одно действие или ни одного: строка помещается рядом с текстом.
        if actionButtons.count <= 1 {
            header.addArrangedSubview(actions)
        } else {
            card.addSubview(actions)
        }
        for (buttonTitle, action, isPrimary) in actionButtons {
            let button = NotificationCardButton(title: buttonTitle) { [weak self] in self?.onAction(action) }
            button.isPrimary = isPrimary
            button.translatesAutoresizingMaskIntoConstraints = false
            button.heightAnchor.constraint(greaterThanOrEqualToConstant: DesktopNotificationCardPresenter.buttonHeight).isActive = true
            actions.addArrangedSubview(button)
            buttons.append((button, action))
        }
        let usesSecondRow = actionButtons.count > 1

        // Наблюдаемый эталон: одна строка со значком, текстом и действиями,
        // поля карточки 10 точек сверху и снизу, 14 точек по бокам.
        let constraints: [NSLayoutConstraint] = [
            card.leadingAnchor.constraint(equalTo: leadingAnchor, constant: DesktopNotificationCardPresenter.horizontalMargin),
            card.trailingAnchor.constraint(equalTo: leadingAnchor,
                                           constant: DesktopNotificationCardPresenter.horizontalMargin
                                               + DesktopNotificationCardPresenter.cardWidth),
            heightAnchor.constraint(equalToConstant: rootHeight
                + DesktopNotificationCardPresenter.topPadding
                + DesktopNotificationCardPresenter.bottomPadding),
            card.topAnchor.constraint(equalTo: topAnchor, constant: DesktopNotificationCardPresenter.topPadding),
            // Ниже карточки остаётся наблюдаемый запас: окно 104 точки при
            // карточке 82 точки.
            card.bottomAnchor.constraint(equalTo: bottomAnchor,
                                         constant: -DesktopNotificationCardPresenter.bottomPadding),
            // Наблюдаемое положение: знак закрытия у верхнего правого угла.
            // Знак закрытия прижат к верхнему правому углу: 20 на 20 точек.
            close.topAnchor.constraint(equalTo: card.topAnchor, constant: 12),
            close.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -14),
            header.leadingAnchor.constraint(equalTo: card.leadingAnchor, constant: 14),
            // Действия не заходят под кнопку закрытия.
            header.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -34),
            // Знак закрытия занимает 14 + 20 точек справа: текст не заходит под него.
            titleLabel.widthAnchor.constraint(lessThanOrEqualToConstant: DesktopNotificationCardPresenter.cardWidth - 90),
            messageLabel.widthAnchor.constraint(lessThanOrEqualToConstant: DesktopNotificationCardPresenter.cardWidth - 90),
            text.widthAnchor.constraint(greaterThanOrEqualToConstant: 104)
        ]

        var all = constraints
        if usesSecondRow {
            // Первая строка: значок и текст. Вторая строка: действия.
            all += [
                header.topAnchor.constraint(equalTo: card.topAnchor, constant: DesktopNotificationCardPresenter.contentInset),
                actions.leadingAnchor.constraint(equalTo: card.leadingAnchor, constant: DesktopNotificationCardPresenter.contentInset),
                actions.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -DesktopNotificationCardPresenter.contentInset),
                actions.topAnchor.constraint(equalTo: header.bottomAnchor, constant: 10),
                actions.bottomAnchor.constraint(equalTo: card.bottomAnchor, constant: -DesktopNotificationCardPresenter.contentInset)
            ]
        } else {
            // Одно действие: наблюдаемые размеры карточки эталона и строка по центру.
            all += [
                card.heightAnchor.constraint(equalToConstant: DesktopNotificationCardPresenter.cardHeight),
                header.centerYAnchor.constraint(equalTo: card.centerYAnchor),
                actions.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -DesktopNotificationCardPresenter.contentInset)
            ]
        }
        NSLayoutConstraint.activate(all)
    }

    private var iconName: String {
        switch content {
        case .meeting: return "calendar"
        case .problem: return "exclamationmark.triangle"
        case .notice: return "bell"
        }
    }

    private var title: String {
        switch content {
        case let .meeting(title, _, _): return title
        case let .problem(title, _, _, _): return title
        case let .notice(title, _, _): return title
        }
    }

    private var message: String {
        switch content {
        case let .meeting(_, startText, _): return startText
        case let .problem(_, message, _, _): return message
        case let .notice(_, message, _): return message
        }
    }

    private var actionButtons: [(String, DesktopNotificationCardAction, Bool)] {
        switch content {
        case let .meeting(_, _, hasJoinLink):
            var items: [(String, DesktopNotificationCardAction, Bool)] = []
            // Подписи короткие: две длинные русские подписи выдавливают текст
            // встречи из строки шириной 420 точек.
            if hasJoinLink {
                items.append(("Записать", .joinAndRecord, true))
                items.append(("Подключиться", .join, false))
            } else {
                items.append(("Записать", .record, true))
            }
            return items
        case let .problem(_, _, actionTitle, sessionID):
            return [(actionTitle, sessionID.map { .openRecording($0) } ?? .openCalendar, true)]
        case let .notice(_, _, actionTitle):
            return actionTitle.map { [($0, .openCalendar, false)] } ?? []
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
