import Foundation

public enum GrafAppChannel: String, CaseIterable, Equatable, Sendable {
    case production
    case disposableLocal
    case installedDev

    public static let environmentKey = "GRAF_APP_CHANNEL"

    public static var current: GrafAppChannel {
        from(environment: ProcessInfo.processInfo.environment)
    }

    public static func from(environment: [String: String]) -> GrafAppChannel {
        switch environment[environmentKey]?.lowercased() {
        case "dev", "installed-dev":
            return .installedDev
        case "local", "disposable-local":
            return .disposableLocal
        default:
            return DesktopCabinetConfiguration.isLocalAppRequested(from: environment)
                ? .disposableLocal
                : .production
        }
    }

    public var applicationSupportFolderName: String {
        switch self {
        case .production, .disposableLocal:
            return "GRAF"
        case .installedDev:
            return "GRAF Dev"
        }
    }

    public var displayName: String {
        switch self {
        case .production:
            return "GRAF"
        case .disposableLocal:
            return "GRAF Local"
        case .installedDev:
            return "GRAF Dev"
        }
    }

    public var isLoopbackOnly: Bool {
        self != .production
    }
}
