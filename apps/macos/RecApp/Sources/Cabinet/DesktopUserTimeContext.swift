import Combine
import Foundation

public struct DesktopUserTimePreference: Equatable {
    public let origin: String
    public let userId: UUID
    public let sessionId: UUID
    public let preferredTimeZone: TimeZone?
}

/// Only a confirmed document can establish the active account. Nothing is restored across launches.
@MainActor
public final class DesktopUserTimeContext: ObservableObject {
    public static let shared = DesktopUserTimeContext()
    @Published public private(set) var preference: DesktopUserTimePreference?
    public private(set) var revision: UInt64 = 0
    public var timeZone: TimeZone { preference?.preferredTimeZone ?? .autoupdatingCurrent }

    public init() {}

    public func reset() {
        revision &+= 1
        preference = nil
    }

    public func prepareForOrigin(_ url: URL) {
        if let preference, preference.origin != Self.originString(url) { reset() }
    }

    @discardableResult
    public func update(from body: Any, origin: URL, expectedRevision: UInt64) -> Bool {
        guard revision == expectedRevision else { return false }
        guard let fields = body as? [String: String],
              let userId = fields["userId"].flatMap(UUID.init(uuidString:)),
              let sessionId = fields["sessionId"].flatMap(UUID.init(uuidString:)),
              let zoneName = fields["timeZone"], zoneName.count <= 100,
              zoneName.isEmpty || ((zoneName == "UTC" || zoneName.contains("/")) && TimeZone(identifier: zoneName) != nil),
              let originString = Self.originString(origin) else {
            reset()
            return false
        }
        revision &+= 1
        preference = DesktopUserTimePreference(origin: originString, userId: userId,
            sessionId: sessionId, preferredTimeZone: zoneName.isEmpty ? nil : TimeZone(identifier: zoneName))
        return true
    }

    private static func originString(_ url: URL) -> String? {
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return nil }
        components.path = ""
        components.query = nil
        components.fragment = nil
        components.user = nil
        components.password = nil
        components.host = components.host?.lowercased()
        if (components.scheme == "https" && components.port == 443) || (components.scheme == "http" && components.port == 80) {
            components.port = nil
        }
        return components.string
    }

    public static func canRead(from url: URL, routePolicy: DesktopCabinetRoutePolicy) -> Bool {
        let decision = routePolicy.decision(for: url)
        guard decision.decision == .allow else { return false }
        return [.meetingList, .meetingDetail, .meetingShare, .meetingDeletionReport,
                .settings, .calendarSettings, .meetingDetectionSettings, .billing].contains(decision.route.kind)
    }

    public static let documentScript = """
    (() => {
      const read = (name) => document.querySelector(`meta[name="${name}"]`)?.content ?? '';
      return {userId: read('graf-time-user'), sessionId: read('graf-time-session'),
        timeZone: read('graf-time-preferred'), documentURL: document.URL};
    })()
    """
}
