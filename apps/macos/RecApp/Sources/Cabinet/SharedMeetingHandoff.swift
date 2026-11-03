import Foundation

/// A link carries reading authority only. The application's own session remains independent.
public struct SharedMeetingHandoff: Equatable, Sendable {
    public static var applicationScheme: String {
        Bundle.main.bundleIdentifier == "pro.2brain.graf.dev" ? "grafrec-dev" : "grafrec"
    }
    public let workspaceID: UUID
    public let meetingID: UUID?
    public let shareToken: String?
    public let tab: String
    public let positionMS: Int?
    public let mediaVersion: String?

    public init?(url: URL, expectedScheme: String = SharedMeetingHandoff.applicationScheme) {
        guard let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.scheme == expectedScheme, parts.host == "shared-meeting",
              parts.user == nil, parts.password == nil, parts.port == nil,
              parts.percentEncodedPath.isEmpty, parts.fragment == nil,
              let values = Self.values(parts.queryItems, allowed: ["v", "workspace_id", "meeting_id", "share_token", "tab", "position_ms", "media_version"]),
              values["v"] == "1", let workspace = values["workspace_id"].flatMap(UUID.init(uuidString:)),
              let tab = values["tab"], ["outcomes", "recording"].contains(tab)
        else { return nil }
        let token = values["share_token"], meeting = values["meeting_id"].flatMap(UUID.init(uuidString:))
        guard (token != nil) != (meeting != nil),
              values["meeting_id"] == nil || meeting != nil,
              token == nil || Self.safeToken(token!),
              values["media_version"] == nil || Self.safeVersion(values["media_version"]!),
              values["position_ms"] == nil || (tab == "recording" && Self.position(values["position_ms"]!) != nil)
        else { return nil }
        workspaceID = workspace; meetingID = meeting; shareToken = token
        self.tab = tab; positionMS = values["position_ms"].flatMap(Self.position); mediaVersion = values["media_version"]
    }

    public func route(configuration: DesktopCabinetConfiguration) -> URL? {
        var parts = URLComponents(url: configuration.baseURL, resolvingAgainstBaseURL: false)
        parts?.path = shareToken.map { "/api/v1/cabinet/public-shares/\($0)" }
            ?? "/shared-meetings/\(meetingID!.uuidString.lowercased())"
        parts?.queryItems = [URLQueryItem(name: "workspace_id", value: workspaceID.uuidString.lowercased())]
        if let mediaVersion { parts?.queryItems?.append(URLQueryItem(name: "media_version", value: mediaVersion)) }
        parts?.fragment = tab + (positionMS.map { "?position_ms=\($0)" } ?? "")
        return parts?.url
    }

    static func values(_ items: [URLQueryItem]?, allowed: Set<String>) -> [String: String]? {
        guard let items else { return nil }
        var result: [String: String] = [:]
        for item in items {
            guard allowed.contains(item.name), result[item.name] == nil,
                  let value = item.value, !value.isEmpty else { return nil }
            result[item.name] = value
        }
        return result
    }
    static func safeToken(_ value: String) -> Bool {
        (32...128).contains(value.utf8.count) && value.utf8.allSatisfy {
            (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || $0 == 45 || $0 == 95
        }
    }
    static func safeVersion(_ value: String) -> Bool {
        value.utf8.count == 24 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }
    static func position(_ value: String) -> Int? {
        guard !value.isEmpty, value.utf8.count <= 8,
              value.utf8.allSatisfy({ (48...57).contains($0) }), let number = Int(value), number <= 86400000 else { return nil }
        return number
    }
    static func safeFragment(_ value: String?) -> Bool {
        guard let value else { return true }
        if ["outcomes", "recording"].contains(value) { return true }
        let prefix = "recording?position_ms="
        return value.hasPrefix(prefix) && position(String(value.dropFirst(prefix.count))) != nil
    }
}

/// Exactly one cold-launch intent in process memory; never written to preferences or logs.
@MainActor
public final class SharedMeetingHandoffInbox {
    public static let shared = SharedMeetingHandoffInbox()
    private var pending: SharedMeetingHandoff?
    public init() {}
    @discardableResult
    public func receive(_ url: URL, expectedScheme: String = SharedMeetingHandoff.applicationScheme) -> Bool {
        guard let intent = SharedMeetingHandoff(url: url, expectedScheme: expectedScheme) else { return false }
        pending = intent
        return true
    }
    public func take(configuration: DesktopCabinetConfiguration) -> URL? {
        guard let pending else { return nil }
        self.pending = nil
        return pending.route(configuration: configuration)
    }
}

public extension Notification.Name {
    static let grafSharedMeetingHandoffDidArrive = Notification.Name("pro.2brain.graf.sharedMeetingHandoffDidArrive")
}
