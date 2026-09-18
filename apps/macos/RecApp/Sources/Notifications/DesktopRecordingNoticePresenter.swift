import AppKit

/// Короткое сообщение о том, что запись не сохранена: та же поверхность, что и
/// у остальных уведомлений GRAF, — карточка в правом верхнем углу рабочей
/// области, которая исчезает сама.
@MainActor
public final class DesktopRecordingNoticePresenter {
    public static let title = "Запись не сохранена"
    public static let message = "Запись короче 30 секунд не сохранена."
    /// Сообщение о потере короткой записи живёт дольше обычной подсказки.
    public static let displayDuration: TimeInterval = 30

    private let card: DesktopNotificationCardPresenter

    public init(card: DesktopNotificationCardPresenter = DesktopNotificationCardPresenter()) {
        self.card = card
    }

    /// Окно сообщения: доступно проверкам поверхности.
    var window: NSWindow? { card.window }

    public func showShortRecordingDiscarded() {
        card.presentNotice(title: Self.title,
                           message: Self.message,
                           duration: Self.displayDuration)
    }

    public func dismiss() {
        card.dismiss()
    }
}
