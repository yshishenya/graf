import Foundation

public enum DesktopCabinetState: String, CaseIterable, Equatable, Sendable {
    case notConfigured
    case loading
    case ready
    case offline
    case timeout
    case expiredSession
    case workspaceReselectionRequired
    case accessDenied
    case notFound
    case malformedResponse
    case blockedRoute

    private static let localRecordingBoundary = "Запись на этом Mac остаётся доступна."

    public var userMessage: String {
        switch self {
        case .notConfigured:
            return "Подключите рабочее пространство GRAF, чтобы видеть встречи. \(Self.localRecordingBoundary)"
        case .loading:
            return "Загружаем встречи. Управление записью остаётся в приложении."
        case .ready:
            return "Встречи загружены."
        case .offline:
            return "Не удалось загрузить встречи. Проверьте интернет-соединение. \(Self.localRecordingBoundary)"
        case .timeout:
            return "Загрузка встреч заняла слишком много времени. Проверьте интернет-соединение и повторите попытку. \(Self.localRecordingBoundary)"
        case .expiredSession:
            return "Войдите снова, чтобы видеть встречи. \(Self.localRecordingBoundary)"
        case .workspaceReselectionRequired:
            return "Доступ к выбранному пространству больше не подтверждён. Войдите снова и выберите доступное пространство. \(Self.localRecordingBoundary)"
        case .accessDenied:
            return "Не удалось подтвердить доступ к встречам. Обратитесь к владельцу рабочего пространства. \(Self.localRecordingBoundary)"
        case .notFound:
            return "Не удалось подтвердить доступ к этой встрече. Вернитесь к списку встреч. \(Self.localRecordingBoundary)"
        case .malformedResponse:
            return "Не удалось загрузить встречи. Повторите попытку. \(Self.localRecordingBoundary)"
        case .blockedRoute:
            return "Эта функция недоступна внутри приложения. Вернитесь к списку встреч и продолжите работу. \(Self.localRecordingBoundary)"
        }
    }

    public var unavailableTitle: String {
        switch self {
        case .expiredSession:
            return "Нужно войти"
        case .workspaceReselectionRequired:
            return "Нужно выбрать пространство"
        case .accessDenied:
            return "Нет доступа к встречам"
        case .notFound:
            return "Встреча недоступна"
        case .offline, .timeout:
            return "Встречи временно недоступны"
        case .notConfigured:
            return "Встречи не подключены"
        case .blockedRoute:
            return "Функция недоступна"
        case .malformedResponse:
            return "Не удалось загрузить встречи"
        case .loading, .ready:
            return "Встречи"
        }
    }

    public var unavailableSystemImage: String {
        switch self {
        case .expiredSession:
            return "person.crop.circle.badge.exclamationmark"
        case .workspaceReselectionRequired:
            return "person.crop.circle.badge.xmark"
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
        case .workspaceReselectionRequired:
            return "Войти и выбрать пространство"
        case .offline, .timeout, .malformedResponse:
            return "Повторить"
        case .accessDenied, .notFound, .blockedRoute:
            return "К списку встреч"
        default:
            return nil
        }
    }

    public var recoverySystemImage: String {
        switch self {
        case .expiredSession:
            return "person.crop.circle"
        case .workspaceReselectionRequired:
            return "person.crop.circle"
        case .offline, .timeout, .malformedResponse:
            return "arrow.clockwise"
        case .accessDenied, .notFound, .blockedRoute:
            return "arrow.left"
        default:
            return "arrow.right"
        }
    }

    public var shouldShowEmbeddedSurface: Bool {
        switch self {
        case .loading, .ready:
            return true
        case .notConfigured, .offline, .timeout, .expiredSession, .workspaceReselectionRequired, .accessDenied, .notFound, .malformedResponse, .blockedRoute:
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

    public static func state(forHTTPResponse response: HTTPURLResponse) -> DesktopCabinetState? {
        if response.value(forHTTPHeaderField: "X-GRAF-Cabinet-Recovery") == "reselect-space" {
            return .workspaceReselectionRequired
        }
        return state(forHTTPStatus: response.statusCode)
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
        recoveryTarget(
            for: state,
            currentRoute: nil,
            initialRoute: nil,
            configuration: configuration
        )
    }

    /// Returns a safe document route for a recovery action. A failed resource
    /// request must not replace the last useful meeting page with an API URL.
    public static func recoveryTarget(
        for state: DesktopCabinetState,
        currentRoute: URL?,
        initialRoute: URL?,
        configuration: DesktopCabinetConfiguration
    ) -> DesktopCabinetRecoveryTarget? {
        switch state {
        case .expiredSession, .workspaceReselectionRequired:
            let nextRoute = retryableDocumentRoute(
                currentRoute: currentRoute,
                initialRoute: initialRoute,
                configuration: configuration
            )
            return .embedded(loginRoute(configuration: configuration, next: nextRoute.path))
        case .offline, .timeout, .malformedResponse, .blockedRoute:
            return .embedded(
                retryableDocumentRoute(
                    currentRoute: currentRoute,
                    initialRoute: initialRoute,
                    configuration: configuration
                )
            )
        case .accessDenied, .notFound:
            return .embedded(configuration.meetingsURL())
        default:
            return nil
        }
    }

    private static func retryableDocumentRoute(
        currentRoute: URL?,
        initialRoute: URL?,
        configuration: DesktopCabinetConfiguration
    ) -> URL {
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        for route in [currentRoute, initialRoute].compactMap({ $0 }) {
            let decision = policy.decision(for: route)
            if decision.decision == .allow,
               [.meetingList, .meetingDetail, .meetingDeletionReport, .calendarSettings,
                .meetingDetectionSettings].contains(decision.route.kind) {
                return route
            }
        }
        return configuration.meetingsURL()
    }

    public static func calendarSettingsRecoveryTarget(
        for state: DesktopCabinetState,
        configuration: DesktopCabinetConfiguration
    ) -> DesktopCabinetRecoveryTarget? {
        switch state {
        case .expiredSession:
            return .embedded(loginRoute(configuration: configuration, next: "/desktop/settings/integrations/calendar"))
        case .offline, .timeout, .malformedResponse:
            return .embedded(configuration.calendarSettingsURL())
        default:
            return recoveryTarget(for: state, configuration: configuration)
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
        guard [.expiredSession, .workspaceReselectionRequired].contains(state), let configuration else {
            return false
        }
        guard let route = currentRoute ?? initialRoute else {
            return false
        }
        let decision = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL).decision(
            for: route,
            allowExternalAuthProvider: true
        )
        return decision.decision == .allow && [
            .authLogin,
            .authSignup,
            .authProvider,
            .authCallback
        ].contains(decision.route.kind)
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
