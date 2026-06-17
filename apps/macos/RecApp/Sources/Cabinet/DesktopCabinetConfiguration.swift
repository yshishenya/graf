import Foundation
import TwoBrainRecShared

public struct DesktopCabinetConfiguration: Equatable, Sendable {
    public static let baseURLEnvironmentKey = "TWO_BRAIN_REC_CABINET_BASE_URL"
    public static let fallbackBaseURLEnvironmentKey = "TWO_BRAIN_REC_UPLOAD_BASE_URL"
    public static let baseURLUserDefaultsKey = "TWO_BRAIN_REC_CABINET_BASE_URL"
    public static let fallbackBaseURLUserDefaultsKey = "TWO_BRAIN_REC_UPLOAD_BASE_URL"
    public static let packagedDefaultBaseURL = "https://rec.2brain.pro"
    public static let defaultLoadTimeoutSeconds: TimeInterval = 15

    public let baseURL: URL
    public let headers: [String: String]
    public let loadTimeoutSeconds: TimeInterval
    public let source: String

    public var workspaceId: String? {
        headers["X-Workspace-Id"]
    }

    public init?(
        rawBaseURL: String,
        headers: [String: String],
        loadTimeoutSeconds: TimeInterval = defaultLoadTimeoutSeconds,
        source: String = "provided"
    ) {
        guard let url = URL(string: rawBaseURL),
              let normalized = Self.normalizedHTTPOrigin(url)
        else {
            return nil
        }
        self.baseURL = normalized
        self.headers = headers
        self.loadTimeoutSeconds = max(1, loadTimeoutSeconds)
        self.source = source
    }

    public init(
        baseURL: URL,
        headers: [String: String] = [:],
        loadTimeoutSeconds: TimeInterval = defaultLoadTimeoutSeconds,
        source: String = "provided"
    ) {
        self.baseURL = Self.normalizedHTTPOrigin(baseURL) ?? baseURL
        self.headers = headers
        self.loadTimeoutSeconds = max(1, loadTimeoutSeconds)
        self.source = source
    }

    public static func configured(
        from environment: [String: String],
        defaults: UserDefaults = .standard,
        includePackagedDefault: Bool = true
    ) -> DesktopCabinetConfiguration? {
        guard let candidate = configuredBaseURLCandidate(
            from: environment,
            defaults: defaults,
            includePackagedDefault: includePackagedDefault
        ) else {
            return nil
        }
        return DesktopCabinetConfiguration(
            rawBaseURL: candidate.rawURL,
            headers: configuredHeaders(from: environment),
            source: candidate.source
        )
    }

    public static func configuredFromEnvironment() -> DesktopCabinetConfiguration? {
        configured(from: ProcessInfo.processInfo.environment)
    }

    public static func configuredHeaders(from environment: [String: String]) -> [String: String] {
        DesktopUploadClient.configuredHeaders(from: environment)
    }

    public static func sanitizedHeaderPreview(_ headers: [String: String]) -> [String: String] {
        headers.reduce(into: [:]) { result, pair in
            result[pair.key] = shouldRedactHeader(named: pair.key) ? "<redacted>" : pair.value
        }
    }

    public func meetingsURL() -> URL {
        baseURL.appending(path: "desktop").appending(path: "meetings")
    }

    public func meetingDetailURL(meetingId: String) -> URL {
        meetingsURL().appending(path: Self.safePathComponent(meetingId))
    }

    public func urlRequest(for url: URL? = nil) -> URLRequest {
        var request = URLRequest(url: url ?? meetingsURL())
        request.timeoutInterval = loadTimeoutSeconds
        for (header, value) in headers {
            request.setValue(value, forHTTPHeaderField: header)
        }
        return request
    }

    public func reviewLink(for item: DesktopUploadQueueItem) -> UploadReviewLink {
        UploadReviewLink(item: item, configuration: self)
    }

    public static func safePathComponent(_ value: String) -> String {
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "unknown" }
        if trimmed.rangeOfCharacter(from: allowed.inverted) == nil {
            return trimmed
        }
        return trimmed.addingPercentEncoding(withAllowedCharacters: allowed) ?? "unknown"
    }

    private static func normalizedHTTPOrigin(_ url: URL) -> URL? {
        guard let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              url.host?.isEmpty == false
        else {
            return nil
        }
        var components = URLComponents()
        components.scheme = scheme
        components.host = url.host
        components.port = url.port
        return components.url
    }

    private static func shouldRedactHeader(named name: String) -> Bool {
        let lowered = name.lowercased()
        return lowered.contains("authorization") ||
            lowered.contains("token") ||
            lowered.contains("cookie") ||
            lowered.contains("secret")
    }

    private static func configuredBaseURLCandidate(
        from environment: [String: String],
        defaults: UserDefaults,
        includePackagedDefault: Bool
    ) -> (rawURL: String, source: String)? {
        let candidates: [(String?, String)] = [
            (environment[baseURLEnvironmentKey], baseURLEnvironmentKey),
            (environment[fallbackBaseURLEnvironmentKey], fallbackBaseURLEnvironmentKey),
            (defaults.string(forKey: baseURLUserDefaultsKey), baseURLUserDefaultsKey),
            (defaults.string(forKey: fallbackBaseURLUserDefaultsKey), fallbackBaseURLUserDefaultsKey),
            (includePackagedDefault ? packagedDefaultBaseURL : nil, "packaged_default")
        ]
        for (rawURL, source) in candidates {
            let trimmed = rawURL?.trimmingCharacters(in: .whitespacesAndNewlines)
            if let trimmed, !trimmed.isEmpty {
                return (trimmed, source)
            }
        }
        return nil
    }
}

public enum UploadReviewAvailability: String, Equatable, Sendable {
    case available
    case processingOnly
    case unavailable
}

public struct UploadReviewLink: Equatable, Sendable {
    public let itemId: String
    public let meetingId: String?
    public let state: UploadItemState
    public let destination: URL?
    public let availability: UploadReviewAvailability
    public let reason: String

    public init(item: DesktopUploadQueueItem, configuration: DesktopCabinetConfiguration) {
        let meetingId = item.serverTruth.meetingId
        self.itemId = item.id
        self.meetingId = meetingId
        self.state = item.state
        if let meetingId, item.state == .uploaded {
            self.destination = configuration.meetingDetailURL(meetingId: meetingId)
            self.availability = .available
            self.reason = "server_meeting_available"
        } else if let meetingId, item.state.canAutomaticallyRetry || item.state == .uploading {
            self.destination = configuration.meetingDetailURL(meetingId: meetingId)
            self.availability = .processingOnly
            self.reason = "server_meeting_processing"
        } else if meetingId != nil {
            self.destination = nil
            self.availability = .unavailable
            self.reason = "server_meeting_terminal"
        } else {
            self.destination = nil
            self.availability = .unavailable
            self.reason = "server_meeting_missing"
        }
    }
}
