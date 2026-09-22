import AppKit
import Foundation

/// Собственная карточка GRAF поверх других окон: единая поверхность для
/// напоминания о встрече, вопроса о записи, проблемы сохранения или отправки,
/// короткой записи и безопасного предпросмотра из настроек.
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
    case skipRecordingPrompt
    case toggleRecordingPromptRemember(Bool)
}

/// Содержимое карточки без AppKit: пригодно для проверок логики показа.
public enum DesktopNotificationCardContent: Equatable, Sendable {
    case meeting(title: String, startText: String, hasJoinLink: Bool)
    case recordingPrompt(displayName: String, remainingSeconds: Int, progress: Double, rememberChoice: Bool)
    case problem(title: String, message: String, actionTitle: String, sessionID: String?)
    /// Безопасное предварительное сообщение из настроек, не являющееся реальным событием.
    case preview(title: String, message: String)
    case shortRecording(title: String, message: String)

    public var accessibilitySummary: String {
        switch self {
        case let .meeting(title, startText, hasJoinLink):
            let join = hasJoinLink ? "Есть ссылка на встречу." : "Ссылки на встречу нет."
            return "Напоминание о встрече. \(title). Начало \(startText). \(join)"
        case let .recordingPrompt(displayName, remainingSeconds, progress, rememberChoice):
            let remember = rememberChoice ? "Выбор сохранён." : "Выбор не сохранён."
            let remainingPercent = Int(((1 - min(max(progress, 0), 1)) * 100).rounded())
            return "Вопрос о записи. Встреча в \(displayName). Записать через \(remainingSeconds) секунд. Осталось \(remainingPercent) процентов. \(remember)"
        case let .problem(title, message, actionTitle, _):
            return "\(title). \(message). Действие: \(actionTitle)."
        case let .preview(title, message), let .shortRecording(title, message):
            // Точка в конце сообщения не удваивается.
            let body = message.hasSuffix(".") ? message : message + "."
            return "\(title). \(body)"
        }
    }

    public var identifier: String {
        switch self {
        case .meeting: return "graf.card.meeting"
        case .recordingPrompt: return "graf.card.recording-prompt"
        case .problem: return "graf.card.problem"
        case .preview: return "graf.card.preview"
        case .shortRecording: return "graf.card.short-recording"
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
    /// Предпросмотр из настроек живёт шесть секунд.
    public static let previewDisplayDuration: TimeInterval = 6
    /// Вопрос о записи живёт восемь секунд.
    public static let recordingPromptDisplayDuration: TimeInterval = 8
    /// Проблема сохранения и короткая запись живут двадцать секунд.
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
    private var onCloseAction: (() -> Void)?
    private var dismissAfter: Date?
    private var expiryGeneration = 0
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
        DesktopNotificationCardView.measuredRootHeight(for: content)
    }

    /// Полная высота поверхности: карточка плюс наблюдаемые поля.
    static func surfaceHeight(for content: DesktopNotificationCardContent) -> CGFloat {
        rootHeight(for: content) + topPadding + bottomPadding
    }

    /// Безопасный предварительный просмотр карточки без привязки к реальному
    /// событию и без изменения состояния согласователя.
    public func presentPreview(title: String,
                               message: String,
                               duration: TimeInterval = DesktopNotificationCardPresenter.previewDisplayDuration,
                               onExpire: (() -> Void)? = nil) {
        present(.preview(title: title, message: message),
                dismissAfter: Date().addingTimeInterval(duration),
                onAction: { _ in },
                onExpire: onExpire)
    }

    public func presentPreview(title: String,
                               message: String,
                               expiresAt: Date,
                               onExpire: (() -> Void)? = nil) {
        present(.preview(title: title, message: message),
                dismissAfter: expiresAt,
                onAction: { _ in },
                onExpire: onExpire)
    }

    public func presentShortRecording(title: String,
                                      message: String,
                                      duration: TimeInterval = DesktopRecordingNoticePresenter.displayDuration,
                                      onExpire: (() -> Void)? = nil) {
        present(.shortRecording(title: title, message: message),
                dismissAfter: Date().addingTimeInterval(duration),
                onAction: { _ in },
                onExpire: onExpire)
    }

    public func presentRecordingPrompt(
        displayName: String,
        remainingSeconds: Int,
        progress: Double,
        rememberChoice: Bool = false,
        duration: TimeInterval = DesktopNotificationCardPresenter.recordingPromptDisplayDuration,
        onStart: @escaping () -> Void,
        onDismiss: @escaping () -> Void,
        onRememberChoiceChanged: @escaping (Bool) -> Void,
        onTick: (() -> DesktopNotificationCardContent?)? = nil,
        onExpire: (() -> Void)? = nil,
        onSkip: ((Bool) -> Void)? = nil
    ) {
        present(
            .recordingPrompt(
                displayName: displayName,
                remainingSeconds: remainingSeconds,
                progress: progress,
                rememberChoice: rememberChoice
            ),
            dismissAfter: Date().addingTimeInterval(duration),
            onAction: { action in
                switch action {
                case .joinAndRecord, .record: onStart()
                case .skipRecordingPrompt: onSkip?(rememberChoice)
                case .toggleRecordingPromptRemember(let value): onRememberChoiceChanged(value)
                default: break
                }
            },
            onTick: onTick,
            onExpire: onExpire,
            onClose: onDismiss
        )
    }

    /// Показывает карточку. Повторный вызов с другим содержимым заменяет его,
    /// не создавая второго окна.
    public func present(_ content: DesktopNotificationCardContent,
                        dismissAfter: Date? = nil,
                        onAction: @escaping (DesktopNotificationCardAction) -> Void,
                        onTick: (() -> DesktopNotificationCardContent?)? = nil,
                        onExpire: (() -> Void)? = nil,
                        onClose: (() -> Void)? = nil) {
        ticker?.cancel()
        ticker = nil
        expiryGeneration += 1
        self.onAction = onAction
        self.onTick = onTick
        self.onExpire = onExpire
        self.onCloseAction = onClose
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
            onClose: { [weak self] in self?.onCloseAction?(); self?.dismiss() }
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

    /// Убирает карточку без применения автоматического решения. Это путь для
    /// закрытия пользователем, выхода из аккаунта и замены карточки.
    public func dismiss() {
        clearCard()
    }

    /// Завершает карточку по её сроку и ровно один раз вызывает `onExpire`.
    private func expire() {
        guard let deadline = dismissAfter, Date() >= deadline else {
            dismiss()
            return
        }
        let callback = onExpire
        clearCard()
        callback?()
    }

    private func clearCard() {
        stopClickMonitor()
        closeControl = nil
        ticker?.cancel()
        ticker = nil
        onTick = nil
        onExpire = nil
        expiryGeneration += 1
        onCloseAction = nil
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
            if let deadline = dismissAfter, Date() >= deadline {
                expire()
            }
            return
        }
        guard let next = onTick() else {
            if dismissAfter != nil { dismiss() }
            return
        }
        guard next != content else { return }
        present(next, dismissAfter: dismissAfter, onAction: onAction ?? { _ in },
                onTick: onTick, onExpire: onExpire, onClose: onCloseAction)
    }

    /// Нажатие на знак закрытия, пока приложение не впереди, окно не получает:
    /// система отдаёт первое нажатие активации. Сторож перехватывает его и
    /// передаёт знаку закрытия, иначе карточку нельзя закрыть мышью.
    private func startClickMonitor(for window: NSWindow) {
        stopClickMonitor()
        clickMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown]) { [weak self, weak window] event in
            guard let self, let window, event.window === window else { return event }
            return self.handleCardClick(at: event.locationInWindow) ? nil : event
        }
    }

    /// Нажатие в области знака закрытия закрывает карточку и не передаётся
    /// дальше. Нажатие мимо знака остаётся обычным нажатием окна.
    @discardableResult
    func handleCardClick(at pointInWindow: NSPoint) -> Bool {
        guard let close = closeControl,
              let content = panel?.contentView else { return false }
        let point = content.convert(pointInWindow, from: nil)
        guard let hit = content.hitTest(point), hit === close || hit.isDescendant(of: close) else {
            return false
        }
        close.performClick(nil)
        return true
    }

    private func stopClickMonitor() {
        if let clickMonitor { NSEvent.removeMonitor(clickMonitor) }
        clickMonitor = nil
    }

    private func startTickerIfNeeded() {
        guard ticker == nil, onTick != nil || dismissAfter != nil else { return }
        let generation = expiryGeneration
        ticker = Task { [weak self] in
            while !Task.isCancelled {
                do { try await Task.sleep(for: .seconds(1)) } catch { return }
                guard let self, self.expiryGeneration == generation else { return }
                if let deadline = self.dismissAfter, Date() >= deadline {
                    self.expire()
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

    private static let closeLeading: CGFloat = 14
    private static let headerLeading: CGFloat = 50
    private static let headerTrailing: CGFloat = 14
    private static let iconWidth: CGFloat = 24
    private static let headerSpacing: CGFloat = 8
    private static let rowSpacing: CGFloat = 10
    private static let verticalInset: CGFloat = 16

    static func titleFont() -> NSFont {
        let preferred = NSFont.preferredFont(forTextStyle: .headline)
        return .systemFont(ofSize: max(14, preferred.pointSize), weight: .semibold)
    }

    static func messageFont() -> NSFont {
        let preferred = NSFont.preferredFont(forTextStyle: .body)
        return .systemFont(ofSize: max(14, preferred.pointSize))
    }

    static func actionFont(weight: NSFont.Weight) -> NSFont {
        let preferred = NSFont.preferredFont(forTextStyle: .callout)
        return .systemFont(ofSize: max(13, preferred.pointSize), weight: weight)
    }

    private static func text(for content: DesktopNotificationCardContent) -> (title: String, message: String) {
        switch content {
        case let .meeting(title, startText, _): return (title, startText)
        case let .recordingPrompt(displayName, remainingSeconds, progress, _):
            let percent = Int((min(max(progress, 0), 1) * 100).rounded())
            return ("Записать встречу?", "Встреча в \(displayName) · Записать через \(remainingSeconds) с · \(percent)%")
        case let .problem(title, message, _, _): return (title, message)
        case let .preview(title, message), let .shortRecording(title, message): return (title, message)
        }
    }

    private static func actionTitles(for content: DesktopNotificationCardContent) -> [String] {
        switch content {
        case let .meeting(_, _, hasJoinLink):
            return hasJoinLink ? ["Подключиться и начать запись", "Подключиться"] : ["Начать запись"]
        case .recordingPrompt: return ["Записать", "Не записывать"]
        case let .problem(_, _, actionTitle, _): return [actionTitle]
        case .preview, .shortRecording: return []
        }
    }

    private static func measuredWidth(_ text: String, font: NSFont) -> CGFloat {
        ceil((text as NSString).size(withAttributes: [.font: font]).width)
    }

    static func measuredHeight(_ text: String, font: NSFont, width: CGFloat) -> CGFloat {
        let rect = (text as NSString).boundingRect(
            with: NSSize(width: max(1, width), height: .greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin, .usesFontLeading],
            attributes: [.font: font]
        )
        return max(ceil(rect.height), ceil(font.pointSize * 1.35))
    }

    private static var baseTextWidth: CGFloat {
        DesktopNotificationCardPresenter.cardWidth - headerLeading - headerTrailing - iconWidth - headerSpacing
    }

    static func textWidth(for content: DesktopNotificationCardContent, secondRow: Bool) -> CGFloat {
        let base = baseTextWidth
        guard !secondRow, let action = actionTitles(for: content).first else { return base }
        let actionWidth = measuredWidth(action, font: actionFont(weight: .semibold)) + 30
        return max(104, base - actionWidth - headerSpacing)
    }

    static func usesSecondRow(for content: DesktopNotificationCardContent) -> Bool {
        let actions = actionTitles(for: content)
        guard !actions.isEmpty else { return false }
        guard actions.count <= 1 else { return true }
        let width = textWidth(for: content, secondRow: false)
        let values = text(for: content)
        return measuredWidth(values.title, font: titleFont()) > width
            || measuredWidth(values.message, font: messageFont()) > width
    }

    static func rowCount(for content: DesktopNotificationCardContent) -> Int {
        usesSecondRow(for: content) ? 2 : 1
    }

    static func headerHeight(for content: DesktopNotificationCardContent, secondRow: Bool) -> CGFloat {
        let width = textWidth(for: content, secondRow: secondRow)
        let values = text(for: content)
        let textHeight = measuredHeight(values.title, font: titleFont(), width: width)
            + 2
            + measuredHeight(values.message, font: messageFont(), width: width)
        return max(iconWidth, textHeight)
    }

    static func measuredRootHeight(for content: DesktopNotificationCardContent) -> CGFloat {
        let secondRow = usesSecondRow(for: content)
        let header = headerHeight(for: content, secondRow: secondRow)
        guard secondRow else {
            return max(DesktopNotificationCardPresenter.cardHeight, header + 24)
        }
        return verticalInset + header + rowSpacing + DesktopNotificationCardPresenter.buttonHeight + verticalInset
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
        icon.heightAnchor.constraint(equalToConstant: 24).isActive = true

        let text = NSStackView()
        text.orientation = .vertical
        text.alignment = .leading
        text.spacing = 2
        text.translatesAutoresizingMaskIntoConstraints = false
        let titleLabel = label(title, font: Self.titleFont(),
                               color: Self.primaryText(dark: isDark))
        let messageLabel = label(message, font: Self.messageFont(),
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
        let usesSecondRow = Self.usesSecondRow(for: content)
        // Одно действие или ни одного: строка помещается рядом с текстом, если
        // текст помещается. Длинное содержимое получает отдельную строку.
        if !usesSecondRow {
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
        if case let .recordingPrompt(_, _, _, rememberChoice) = content {
            let remember = NSButton(checkboxWithTitle: "Запомнить выбор", target: self,
                                    action: #selector(rememberChoiceChanged(_:)))
            remember.state = rememberChoice ? .on : .off
            remember.font = Self.actionFont(weight: .regular)
            remember.setAccessibilityLabel("Запомнить выбор")
            remember.translatesAutoresizingMaskIntoConstraints = false
            actions.addArrangedSubview(remember)
        }

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
            // Крестик стандартного уведомления находится в левом верхнем углу;
            // содержимое начинается после его зоны и не пересекается с ней.
            close.topAnchor.constraint(equalTo: card.topAnchor, constant: 12),
            close.leadingAnchor.constraint(equalTo: card.leadingAnchor, constant: Self.closeLeading),
            header.leadingAnchor.constraint(equalTo: card.leadingAnchor, constant: Self.headerLeading),
            header.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -Self.headerTrailing),
            text.widthAnchor.constraint(equalToConstant: Self.textWidth(for: content, secondRow: usesSecondRow)),
            titleLabel.widthAnchor.constraint(equalToConstant: Self.textWidth(for: content, secondRow: usesSecondRow)),
            messageLabel.widthAnchor.constraint(equalToConstant: Self.textWidth(for: content, secondRow: usesSecondRow)),
            titleLabel.heightAnchor.constraint(equalToConstant: Self.measuredHeight(title, font: Self.titleFont(), width: Self.textWidth(for: content, secondRow: usesSecondRow))),
            messageLabel.heightAnchor.constraint(equalToConstant: Self.measuredHeight(message, font: Self.messageFont(), width: Self.textWidth(for: content, secondRow: usesSecondRow))),
            header.heightAnchor.constraint(equalToConstant: Self.headerHeight(for: content, secondRow: usesSecondRow)),
            card.heightAnchor.constraint(equalToConstant: rootHeight)
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
                header.centerYAnchor.constraint(equalTo: card.centerYAnchor),
                actions.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -20)
            ]
        }
        NSLayoutConstraint.activate(all)
    }

    private var iconName: String {
        switch content {
        case .meeting: return "calendar"
        case .recordingPrompt: return "record.circle"
        case .problem: return "exclamationmark.triangle"
        case .preview: return "bell"
        case .shortRecording: return "exclamationmark.triangle"
        }
    }

    private var title: String {
        switch content {
        case let .meeting(title, _, _): return title
        case .recordingPrompt: return "Записать встречу?"
        case let .problem(title, _, _, _): return title
        case let .preview(title, _), let .shortRecording(title, _): return title
        }
    }

    private var message: String {
        switch content {
        case let .meeting(_, startText, _): return startText
        case let .recordingPrompt(displayName, remainingSeconds, progress, _):
            let percent = Int((min(max(progress, 0), 1) * 100).rounded())
            return "Встреча в \(displayName) · Записать через \(remainingSeconds) с · \(percent)%"
        case let .problem(_, message, _, _): return message
        case let .preview(_, message), let .shortRecording(_, message): return message
        }
    }

    private var actionButtons: [(String, DesktopNotificationCardAction, Bool)] {
        switch content {
        case let .meeting(_, _, hasJoinLink):
            var items: [(String, DesktopNotificationCardAction, Bool)] = []
            // Подписи короткие: две длинные русские подписи выдавливают текст
            // встречи из строки шириной 420 точек.
            if hasJoinLink {
                items.append(("Подключиться и начать запись", .joinAndRecord, true))
                items.append(("Подключиться", .join, false))
            } else {
                items.append(("Начать запись", .record, true))
            }
            return items
        case .recordingPrompt:
            return [
                ("Записать", .record, true),
                ("Не записывать", .skipRecordingPrompt, false)
            ]
        case let .problem(_, _, actionTitle, sessionID):
            return [(actionTitle, sessionID.map { .openRecording($0) } ?? .openCalendar, true)]
        case .preview, .shortRecording:
            return []
        }
    }

    private func label(_ text: String, font: NSFont, color: NSColor) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.font = font
        field.textColor = color
        field.translatesAutoresizingMaskIntoConstraints = false
        field.usesSingleLineMode = false
        field.lineBreakMode = .byWordWrapping
        field.maximumNumberOfLines = 0
        return field
    }

    @objc private func closeTapped() { onClose() }

    @objc private func rememberChoiceChanged(_ sender: NSButton) {
        onAction(.toggleRecordingPromptRemember(sender.state == .on))
    }
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
        font = DesktopNotificationCardView.actionFont(weight: .semibold)
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
                .font: DesktopNotificationCardView.actionFont(weight: .semibold),
                .paragraphStyle: paragraph
            ])
        } else {
            layer?.backgroundColor = NSColor.clear.cgColor
            layer?.borderColor = DesktopNotificationCardView.cardBorder(dark: dark).cgColor
            attributedTitle = NSAttributedString(string: title, attributes: [
                .foregroundColor: DesktopNotificationCardView.primaryText(dark: dark),
                .font: DesktopNotificationCardView.actionFont(weight: .medium),
                .paragraphStyle: paragraph
            ])
        }
        // Наблюдаемый эталон: поля кнопки 15 точек по бокам вокруг текста.
        widthConstraint?.isActive = false
        let text = (title as NSString).size(withAttributes: [.font: DesktopNotificationCardView.actionFont(weight: .semibold)]).width
        let width = widthAnchor.constraint(equalToConstant: ceil(text) + 30)
        width.isActive = true
        widthConstraint = width
    }

    private var widthConstraint: NSLayoutConstraint?

    @objc private func fire() { handler() }
}
