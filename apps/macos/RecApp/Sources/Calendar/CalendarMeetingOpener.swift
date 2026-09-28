import Foundation
#if canImport(AppKit)
import AppKit
#endif

/// Conference URLs have different semantics from help links: query and fragment are retained.
public enum CalendarMeetingOpener {
    public static func validatedHTTPS(_ raw: String) -> URL? {
        guard raw.utf8.count <= 8192, !raw.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }),
              let url = URL(string: raw), let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.scheme?.lowercased() == "https", let host = parts.host, !host.isEmpty,
              parts.user == nil, parts.password == nil, parts.port == nil || parts.port == 443 else { return nil }
        let normalizedHost = host.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "."))
        guard normalizedHost.contains("."), !normalizedHost.contains(":"),
              !normalizedHost.hasSuffix(".localhost"), !normalizedHost.hasSuffix(".local"),
              !normalizedHost.allSatisfy({ $0.isNumber || $0 == "." }) else { return nil }
        return url
    }

    public static func nativeCandidate(for url: URL) -> URL? {
        guard validatedHTTPS(url.absoluteString) != nil,
              var parts = URLComponents(url: url, resolvingAgainstBaseURL: false), let host = parts.host?.lowercased() else { return nil }
        if host == "teams.microsoft.com", parts.path.hasPrefix("/l/meetup-join/") {
            parts.scheme = "msteams"
            return parts.url
        }
        if host == "zoom.us" || host.hasSuffix(".zoom.us") || host == "zoom.com" || host.hasSuffix(".zoom.com") {
            let segments = parts.path.split(separator: "/")
            guard segments.count == 2, segments[0] == "j", (9...11).contains(segments[1].count),
                  segments[1].allSatisfy({ $0.isASCII && $0.isNumber }) else { return nil }
            let parameters = (parts.queryItems ?? []).filter { !["action", "confno"].contains($0.name) }
            parts.scheme = "zoommtg"
            parts.path = "/join"
            parts.queryItems = [URLQueryItem(name: "action", value: "join"), URLQueryItem(name: "confno", value: String(segments[1]))] + parameters
            return parts.url
        }
        return nil
    }

    static func nativeApplicationIdentifiers(for url: URL) -> [String] {
        switch nativeCandidate(for: url)?.scheme {
        case "msteams": return ["com.microsoft.teams2", "com.microsoft.teams"]
        case "zoommtg": return ["us.zoom.xos"]
        default: return []
        }
    }

    @MainActor private static var eventOpening = false

    @MainActor
    static func resolveAndOpen(eventID: UUID,
                               resolve: (UUID) async throws -> URL,
                               isCurrent: () -> Bool,
                               open: (URL) async -> Bool) async -> Bool {
        guard !eventOpening, isCurrent() else { return false }
        eventOpening = true
        defer { eventOpening = false }
        do {
            let url = try await resolve(eventID)
            guard !Task.isCancelled, isCurrent(), validatedHTTPS(url.absoluteString) != nil else { return false }
            return await open(url)
        } catch { return false }
    }

    #if canImport(AppKit)
    @MainActor
    public static func openEvent(_ id: String) async -> Bool {
        guard let eventID = UUID(uuidString: id), let client = DesktopUploadClient.configuredFromEnvironment() else { return false }
        let generation = DesktopCabinetSessionBridge.generation
        let origin = client.baseOrigin
        let token = DesktopUploadClient.defaultAuthSessionToken(for: origin)
        return await resolveAndOpen(eventID: eventID,
            resolve: { try await client.calendarJoinTarget(eventID: $0) },
            isCurrent: {
                DesktopCabinetSessionBridge.isCurrentSession(generation)
                    && DesktopUploadClient.defaultAuthSessionToken(for: origin) == token
                    && DesktopUploadClient.configuredFromEnvironment()?.baseOrigin == origin
            }, open: { await Self.open($0) })
    }

    @MainActor
    public static func open(_ url: URL) async -> Bool {
        guard let safe = validatedHTTPS(url.absoluteString) else { return false }
        let workspace = NSWorkspace.shared
        // Telemost accepts conference links through its application URL handler.
        if safe.host?.lowercased() == "telemost.yandex.ru", safe.path.hasPrefix("/j/"),
           let app = workspace.urlForApplication(withBundleIdentifier: "ru.yandex.desktop.telemost") {
            return await withCheckedContinuation { continuation in
                workspace.open([safe], withApplicationAt: app, configuration: NSWorkspace.OpenConfiguration()) { _, error in
                    continuation.resume(returning: error == nil)
                }
            }
        }
        // A registered scheme can point at a removed app or a Parallels proxy.
        // Address the supported native application explicitly; otherwise retain HTTPS.
        if let native = nativeCandidate(for: safe),
           let app = nativeApplicationIdentifiers(for: safe).compactMap({ workspace.urlForApplication(withBundleIdentifier: $0) }).first {
            return await withCheckedContinuation { continuation in
                workspace.open([native], withApplicationAt: app, configuration: NSWorkspace.OpenConfiguration()) { _, error in
                    continuation.resume(returning: error == nil)
                }
            }
        }
        return workspace.open(safe)
    }
    #endif
}
