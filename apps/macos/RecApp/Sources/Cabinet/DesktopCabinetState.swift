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

    public var unavailableTitle: String {
        switch self {
        case .expiredSession:
            return "Нужен вход в кабинет"
        case .accessDenied:
            return "Нет доступа к кабинету"
        case .notFound:
            return "Обзор не найден"
        case .offline, .timeout:
            return "Кабинет временно недоступен"
        case .notConfigured:
            return "Кабинет не настроен"
        case .blockedRoute:
            return "Действие ограничено"
        case .malformedResponse:
            return "Нужна проверка кабинета"
        case .loading, .ready:
            return "Кабинет встреч"
        }
    }

    public var unavailableSystemImage: String {
        switch self {
        case .expiredSession:
            return "person.crop.circle.badge.exclamationmark"
        case .accessDenied:
            return "lock.trianglebadge.exclamationmark"
        case .notFound:
            return "questionmark.folder"
        case .offline, .timeout, .notConfigured:
            return "wifi.slash"
        case .blockedRoute:
            return "hand.raised"
        case .malformedResponse:
            return "exclamationmark.triangle"
        case .loading, .ready:
            return "rectangle.stack.fill"
        }
    }

    public var recoveryActionTitle: String? {
        switch self {
        case .expiredSession:
            return "Войти в кабинет"
        case .offline, .timeout:
            return "Открыть кабинет"
        default:
            return nil
        }
    }

    public var shouldShowEmbeddedSurface: Bool {
        switch self {
        case .loading, .ready:
            return true
        case .notConfigured, .offline, .timeout, .expiredSession, .accessDenied, .notFound, .malformedResponse, .blockedRoute:
            return false
        }
    }

    public static func state(forHTTPStatus statusCode: Int) -> DesktopCabinetState? {
        switch statusCode {
        case 200..<400:
            return nil
        case 401:
            return .expiredSession
        case 403:
            return .accessDenied
        case 404:
            return .notFound
        case 408, 504:
            return .timeout
        case 500..<600:
            return .offline
        default:
            return .malformedResponse
        }
    }

    public static func state(forNavigationError error: Error, currentState: DesktopCabinetState) -> DesktopCabinetState {
        let nsError = error as NSError
        if isExpectedNavigationCancellation(nsError) {
            return currentState
        }
        if nsError.domain == NSURLErrorDomain {
            switch nsError.code {
            case NSURLErrorTimedOut:
                return .timeout
            default:
                return .offline
            }
        }
        return .offline
    }

    private static func isExpectedNavigationCancellation(_ error: NSError) -> Bool {
        if error.domain == NSURLErrorDomain, error.code == NSURLErrorCancelled {
            return true
        }
        // WKError.frameLoadInterruptedByPolicyChange uses code 102 after app-driven cancels.
        if error.domain == "WebKitErrorDomain", error.code == 102 {
            return true
        }
        return false
    }
}

public struct NativeShellInvariant: Equatable, Sendable {
    public let recordVisible: Bool
    public let stopVisible: Bool
    public let uploadTruthVisible: Bool
    public let focusCanReachStop: Bool
    public let embeddedSurfaceLoaded: Bool
    public let workspaceZoomApplied: WorkspaceZoomPreference
    public let nativeShellScaledByWorkspaceZoom: Bool

    public init(
        recordVisible: Bool,
        stopVisible: Bool,
        uploadTruthVisible: Bool,
        focusCanReachStop: Bool,
        embeddedSurfaceLoaded: Bool,
        workspaceZoomApplied: WorkspaceZoomPreference = .default,
        nativeShellScaledByWorkspaceZoom: Bool = false
    ) {
        self.recordVisible = recordVisible
        self.stopVisible = stopVisible
        self.uploadTruthVisible = uploadTruthVisible
        self.focusCanReachStop = focusCanReachStop
        self.embeddedSurfaceLoaded = embeddedSurfaceLoaded
        self.workspaceZoomApplied = workspaceZoomApplied
        self.nativeShellScaledByWorkspaceZoom = nativeShellScaledByWorkspaceZoom
    }

    public func satisfiesActiveRecordingSafety(cabinetState _: DesktopCabinetState) -> Bool {
        recordVisible && stopVisible && focusCanReachStop && uploadTruthVisible && !nativeShellScaledByWorkspaceZoom
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

public enum DesktopCabinetRecoveryTarget: Equatable, Sendable {
    case embedded(URL)
    case external(URL)
}

public enum DesktopCabinetWorkspace {
    public static func defaultRoute(configuration: DesktopCabinetConfiguration) -> URL {
        configuration.meetingsURL()
    }

    public static func loginRoute(configuration: DesktopCabinetConfiguration, next: String = "/desktop/meetings") -> URL {
        var components = URLComponents(url: configuration.baseURL.appending(path: "login"), resolvingAgainstBaseURL: false)
        var queryItems = [URLQueryItem(name: "next", value: next)]
        if let workspaceId = configuration.workspaceId {
            queryItems.append(URLQueryItem(name: "workspace_id", value: workspaceId))
        }
        components?.queryItems = queryItems
        return components?.url ?? configuration.baseURL.appending(path: "login")
    }

    public static func detailRoute(meetingId: String, configuration: DesktopCabinetConfiguration) -> URL {
        configuration.meetingDetailURL(meetingId: meetingId)
    }

    public static func recoveryTarget(
        for state: DesktopCabinetState,
        configuration: DesktopCabinetConfiguration
    ) -> DesktopCabinetRecoveryTarget? {
        switch state {
        case .expiredSession:
            return .embedded(loginRoute(configuration: configuration))
        case .offline, .timeout:
            return .external(configuration.baseURL)
        default:
            return nil
        }
    }

    public static func shouldShowEmbeddedSurface(
        for state: DesktopCabinetState,
        currentRoute: URL?,
        initialRoute: URL?,
        configuration: DesktopCabinetConfiguration?
    ) -> Bool {
        if state.shouldShowEmbeddedSurface {
            return true
        }
        guard state == .expiredSession, let configuration else {
            return false
        }
        guard let route = currentRoute ?? initialRoute else {
            return false
        }
        let decision = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL).decision(for: route)
        return decision.decision == .allow && (decision.route.kind == .authLogin || decision.route.kind == .authSignup)
    }
}

public enum DesktopCabinetLayoutSection: String, Equatable, Sendable {
    case capture
    case meetings
    case localAudioReadiness
}

public enum DesktopCabinetLayoutPolicy {
    public static let defaultSectionOrder: [DesktopCabinetLayoutSection] = [
        .meetings,
        .capture,
        .localAudioReadiness
    ]
}
