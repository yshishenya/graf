import Foundation

public enum DesktopCabinetState: String, CaseIterable, Equatable, Sendable {
    case notConfigured
    case loading
    case ready
    case offline
    case timeout
    case expiredSession
    case accessDenied
    case notFound
    case malformedResponse
    case blockedRoute

    public var userMessage: String {
        switch self {
        case .notConfigured:
            return "Подключите рабочее пространство 2brain Rec, чтобы просматривать встречи здесь. Локальная запись остается доступной."
        case .loading:
            return "Загружаем рабочее пространство встреч. Управление записью остается в приложении."
        case .ready:
            return "Рабочее пространство встреч готово."
        case .offline:
            return "Кабинет встреч недоступен. Проверьте соединение с сервером Rec; локальная запись продолжит работать."
        case .timeout:
            return "Кабинет встреч слишком долго отвечает. Попробуйте еще раз; локальная запись остается доступной."
        case .expiredSession:
            return "Войдите снова, чтобы просматривать встречи. Локальная запись и статус загрузок остаются в приложении."
        case .accessDenied:
            return "Не удалось подтвердить доступ из этой сессии. Локальная запись и статус загрузок не меняются."
        case .notFound:
            return "Не удалось подтвердить доступ к этому обзору из текущей сессии."
        case .malformedResponse:
            return "Кабинет встреч вернул неожиданный ответ. Статус локальной записи не изменился."
        case .blockedRoute:
            return "Это действие остается за пределами встроенного кабинета встреч."
        }
    }
}

public struct NativeShellInvariant: Equatable, Sendable {
    public let recordVisible: Bool
    public let stopVisible: Bool
    public let uploadTruthVisible: Bool
    public let focusCanReachStop: Bool
    public let embeddedSurfaceLoaded: Bool

    public init(
        recordVisible: Bool,
        stopVisible: Bool,
        uploadTruthVisible: Bool,
        focusCanReachStop: Bool,
        embeddedSurfaceLoaded: Bool
    ) {
        self.recordVisible = recordVisible
        self.stopVisible = stopVisible
        self.uploadTruthVisible = uploadTruthVisible
        self.focusCanReachStop = focusCanReachStop
        self.embeddedSurfaceLoaded = embeddedSurfaceLoaded
    }

    public func satisfiesActiveRecordingSafety(cabinetState _: DesktopCabinetState) -> Bool {
        stopVisible && focusCanReachStop && uploadTruthVisible
    }
}

public enum DesktopCabinetAccessibilityIdentifier {
    public static let captureRegion = "desktop-native-capture-region"
    public static let uploadTruthRegion = "desktop-native-upload-truth-region"
    public static let workspace = "desktop-cabinet-workspace"
    public static let embeddedSurface = "desktop-cabinet-embedded-surface"
    public static let unavailableState = "desktop-cabinet-unavailable-state"
    public static let nativeShellRegion = "desktop-native-shell-region"
}

public enum DesktopCabinetWorkspace {
    public static func defaultRoute(configuration: DesktopCabinetConfiguration) -> URL {
        configuration.meetingsURL()
    }

    public static func detailRoute(meetingId: String, configuration: DesktopCabinetConfiguration) -> URL {
        configuration.meetingDetailURL(meetingId: meetingId)
    }
}

public enum DesktopCabinetLayoutSection: String, Equatable, Sendable {
    case capture
    case meetings
    case localAudioReadiness
}

public enum DesktopCabinetLayoutPolicy {
    public static let defaultSectionOrder: [DesktopCabinetLayoutSection] = [
        .capture,
        .meetings,
        .localAudioReadiness
    ]
}
