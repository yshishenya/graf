import AppKit

/// Короткое сообщение о том, что запись не сохранена: та же поверхность, что и
/// у остальных уведомлений GRAF, — карточка в правом верхнем углу рабочей
/// области, которая исчезает сама.
@MainActor
public final class DesktopRecordingNoticePresenter {
    public static let title = "Запись слишком короткая"
    public static let message = "Записи короче 30 секунд не сохраняются."
    /// Сообщение о потере короткой записи живёт дольше обычной подсказки.
    public static let displayDuration: TimeInterval = 20

    private let card: DesktopNotificationCardPresenter
    private weak var broker: DesktopNotificationPresenter?

    public init(card: DesktopNotificationCardPresenter = DesktopNotificationCardPresenter(),
                presenter: DesktopNotificationPresenter? = nil) {
        self.card = card
        self.broker = presenter
    }

    /// Окно сообщения: доступно проверкам поверхности.
    var window: NSWindow? { broker?.card.window ?? card.window }

    public func showShortRecordingDiscarded() {
        if let broker {
            _ = broker.presentShortRecording(title: Self.title,
                                             message: Self.message,
                                             duration: Self.displayDuration)
        } else {
            card.presentShortRecording(title: Self.title,
                                       message: Self.message,
                                       duration: Self.displayDuration)
        }
    }

    public var presentedContent: DesktopNotificationCardContent? {
        broker?.card.presentedContent ?? card.presentedContent
    }

    public func dismiss() {
        if let broker { broker.dismissShortRecording() }
        else { card.dismiss() }
    }
}
